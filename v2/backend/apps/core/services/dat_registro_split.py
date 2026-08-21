"""
Split per-year de DATRegistro: deriva um registro por ano de uso a partir das compras.

O import cria um registro "flat" por (município, projeto) sem ano — no ENTITY_ORDER
`dat_registro` vem antes de `dat_compra`, então o ano só se conhece depois. Este passo,
rodado APÓS o import das compras, faz o fan-out do flat em um registro por ano de uso
(`DATCompra.ano_uso`), com um bucket pendente (`ano=None`) para as compras NÃO_CLASSIFICADAS.
Idempotente.

Os atributos do flat (aluno_qtde/professor_qtde) ficam no ano PRIMÁRIO (2026 se houver, senão
o maior ano real); os anos secundários nascem sem esses campos. `nr_codigos` é recomputado por
ano no `save()` (ver `dat_codigos.calcular_nr_codigos`, que filtra por `ano_uso=registro.ano`).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportArgumentType=false

from __future__ import annotations

from collections import defaultdict

from django.db import transaction

from apps.core.models.dat_compra import DATCompra
from apps.core.models.dat_registro import DATRegistro


def _primary_ano(anos: set[int | None]) -> int | None:
    """Ano que carrega os atributos do flat: 2026 se presente, senão o maior ano real, senão None."""
    reais = sorted(a for a in anos if a is not None)
    if 2026 in reais:
        return 2026
    return reais[-1] if reais else None


@transaction.atomic
def split_dat_registros(dry_run: bool = False) -> dict[str, int]:
    """
    Garante um DATRegistro por (município, projeto, ano de uso das compras).

    Para cada par (município, projeto) que tem registro: lê os `ano_uso` distintos das compras
    ativas (inclui None = NÃO_CLASSIFICADO); reatribui o registro-flat ao ano primário (preservando
    atributos) e cria os anos que faltam. Pares sem compra ficam como estão (não deleta). Retorna
    contadores (pares, criados, reatribuidos).
    """
    compra_anos: dict[tuple[int, int], set[int | None]] = defaultdict(set)
    for mid, pid, ano in DATCompra.objects.filter(ativo=True).values_list("municipio_id", "projeto_id", "ano_uso"):
        compra_anos[(mid, pid)].add(ano)

    pares = criados = reatribuidos = 0
    par_registro = set(DATRegistro.objects.values_list("municipio_id", "projeto_id").distinct())
    for mid, pid in sorted(par_registro):
        target = compra_anos.get((mid, pid))
        if not target:
            continue  # sem compras: registro pendente/órfão fica como está (não deleta)
        pares += 1
        regs = list(DATRegistro.objects.filter(municipio_id=mid, projeto_id=pid))
        existing: dict[int | None, DATRegistro] = {r.ano: r for r in regs}
        primary = _primary_ano(target)

        # 1. Garante o registro PRIMÁRIO (carrega os atributos do flat).
        if primary not in existing:
            anchor = max(regs, key=lambda r: ((r.aluno_qtde or 0) + (r.professor_qtde or 0), int(r.pk)))
            reatribuidos += 1
            existing.pop(anchor.ano, None)
            if not dry_run:
                anchor.ano = primary
                anchor.save()  # recomputa nr_codigos para o ano primário
            existing[primary] = anchor
        primary_reg = existing[primary]

        # 2. Cria um registro para cada OUTRO ano de uso (atributos só no primário).
        for ano in sorted(target, key=lambda a: (a is None, a or 0)):
            if ano in existing:
                continue
            criados += 1
            if not dry_run:
                novo = DATRegistro(
                    municipio_id=mid,
                    projeto_id=pid,
                    projeto_geral_id=primary_reg.projeto_geral_id,
                    ano=ano,
                    aluno_qtde=None,
                    professor_qtde=None,
                    created_by_id=primary_reg.created_by_id,
                )
                novo.save()  # recomputa nr_codigos para o ano
                existing[ano] = novo
            else:
                existing[ano] = primary_reg  # placeholder só p/ a contagem do dry-run

    # Pares com compra ativa mas SEM nenhum registro (anomalia de origem: a planilha dat_registro
    # não tem linha para o par, então o split não tem o que fan-out e a compra fica sem rastreamento).
    # Reportados para reconciliação — nunca criados em silêncio.
    orfaos = sorted(par for par in compra_anos if par not in par_registro)
    return {
        "pares": pares,
        "criados": criados,
        "reatribuidos": reatribuidos,
        "compras_sem_registro": len(orfaos),
    }
