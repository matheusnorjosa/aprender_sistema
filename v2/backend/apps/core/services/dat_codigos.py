"""
Cálculo de `DATRegistro.nr_codigos` por linha de compra (contrato v5).

Os 10% são bônus POR compra de professor, arredondando cada compra para cima e
só depois somando — difere do agregado quando uma variante tem 2+ compras de
professor. Kit de aluno usa `ceil(qtde / divisor)`, sem 10%. `conta_para_codigos`
exclui as compras que a planilha não conta (ex.: kits AVALIAR de GESTÃO ESCOLAR).

Aritmética `Decimal` (nunca `float`): `float(Decimal("1.1")) == 1.1000000000000001`
faz o `ceil` estourar +1. Ver `REGRA-10-PORCENTO-CODIGOS.md` §6.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportOperatorIssue=false, reportCallIssue=false, reportUnnecessaryComparison=false

from __future__ import annotations

from decimal import ROUND_CEILING, Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.core.models.dat_compra import DATCompra
    from apps.core.models.dat_registro import DATRegistro
    from apps.core.models.organizacao import ProjetoGeral


def codigos_da_compra(compra: DATCompra, pg: ProjetoGeral) -> int:
    """Códigos gerados por UMA compra, segundo a regra do projeto_geral do registro."""
    if not compra.conta_para_codigos:
        return 0
    tipo_calc = pg.tipo_calculo_codigos
    if tipo_calc == "por_aluno":
        if compra.tipo != "Aluno" or not pg.divisor_aluno:
            return 0
        base = Decimal(compra.quantidade) / Decimal(pg.divisor_aluno)
    elif tipo_calc == "por_professor":
        if compra.tipo != "Professor" or not pg.multiplicador_professor:
            return 0
        base = Decimal(compra.quantidade) * pg.multiplicador_professor
    else:  # nao_aplicavel
        return 0
    return int(base.to_integral_value(rounding=ROUND_CEILING))


def calcular_nr_codigos(registro: DATRegistro) -> int | None:
    """
    Soma dos códigos das compras do registro (município × projeto, ativas).

    Cohort anual (decisão do dono): quando `registro.ano` está definido, conta SÓ as
    compras cujo `ano_uso` bate — cada ano tem seu número, sem inflar o total somando
    2026 + 2027 + sem-ano no mesmo balde. `ano` nulo (transição) mantém o comportamento
    antigo (soma todos os anos).

    `None` quando o projeto_geral não gera códigos (`nao_aplicavel`) ou não existe —
    preserva a semântica de "em branco" da planilha. A regra vem SEMPRE do
    `registro.projeto_geral` (FK NOT NULL), nunca da compra.
    """
    if not registro.projeto_geral_id:
        return None
    pg = registro.projeto_geral
    if pg.tipo_calculo_codigos == "nao_aplicavel":
        return None

    from apps.core.models.dat_compra import DATCompra

    compras = DATCompra.objects.filter(municipio_id=registro.municipio_id, projeto_id=registro.projeto_id, ativo=True)
    if registro.ano is not None:
        compras = compras.filter(ano_uso=registro.ano)
    return sum(codigos_da_compra(c, pg) for c in compras)


def recompute_registros(municipio_id: int, projeto_id: int) -> int:
    """
    Recalcula `nr_codigos` dos registros do par (município, projeto) via `bulk_update`.

    Usado pela passada final do importer, pelos hooks do `DATCompraViewSet` e pelo
    command de backfill. `bulk_update` não re-dispara `save()` (sem recursão).
    Retorna quantos registros foram atualizados.
    """
    from apps.core.models.dat_registro import DATRegistro

    regs = list(
        DATRegistro.objects.filter(municipio_id=municipio_id, projeto_id=projeto_id).select_related("projeto_geral")
    )
    for reg in regs:
        reg.nr_codigos = calcular_nr_codigos(reg)
    if regs:
        DATRegistro.objects.bulk_update(regs, ["nr_codigos"])
    return len(regs)


def recompute_all() -> int:
    """
    Recalcula `nr_codigos` de TODOS os registros. Retorna quantos foram alterados.

    Usado pela passada final do importer (após dat_compra/dat_registro) e pelo command
    de backfill. `ponytail:` faz 1 query de compras por registro (N+1) — aceitável para
    um passo de import/backfill (rodado raramente, ~1000 registros).
    """
    from apps.core.models.dat_registro import DATRegistro

    regs = list(DATRegistro.objects.select_related("projeto_geral"))
    alterados = 0
    for reg in regs:
        novo = calcular_nr_codigos(reg)
        if reg.nr_codigos != novo:
            reg.nr_codigos = novo
            alterados += 1
    if regs:
        DATRegistro.objects.bulk_update(regs, ["nr_codigos"])
    return alterados
