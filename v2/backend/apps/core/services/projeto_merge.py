"""
Merge de Projetos duplicados (datafix do golden DB).

3 pares VIDA nascem repartidos: o nome canônico (caps) carrega planos/DATAcao e uma
linha operacional na forma "&" carrega compra/solic/datcompra. É o MESMO projeto real
— divisão herdada de imports com formas de nome diferentes antes de o resolver (#1372)
rodar de ponta a ponta. Este serviço reparenta TODAS as relações da duplicata para o
sobrevivente (que já tem o nome canônico — não renomeia) e deleta a duplicata.

Segurança:
- **dry-run é o default** (`apply=False`): só conta o que faria, não escreve nada.
- `apply=True` roda tudo numa transação única (all-or-nothing).
- reparent acontece ANTES do delete — relações `on_delete=PROTECT` (ex.: Produto)
  bloqueariam um delete cego.
- idempotente: duplicata ausente = já mesclada = skip.
- survivor ausente ou colisão O2O/M2M = falha alto (não silencia).

Os pares Superativar do RELAY 26 são AMBÍGUOS (operacional num balde genérico
`Superativar`, não separado por Linguagens/Matemática) e ficam FORA daqui até decisão
do dono/sheets.banco (v15). Os "resíduos para deletar" do RELAY 26 têm dados reais
(Solicitacao/Compra) e também NÃO entram aqui.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportGeneralTypeIssues=false

from __future__ import annotations

from typing import Any

from django.db import transaction
from django.db.models import Q

from apps.core.models import Projeto, Solicitacao
from apps.core.services.solicitacao_projetos import par_de_projetos_invalido

# (sobrevivente_canonico, duplicata_a_absorver) — verificados ao vivo no golden DB 2026-08-27.
DEFAULT_PAIRS: list[tuple[str, str]] = [
    ("VIDA E MATEMÁTICA", "Vida & Matemática"),
    ("VIDA E LINGUAGEM", "Vida & Linguagem"),
    ("VIDA E CIÊNCIAS", "Vida & Ciências"),
]


def _merge_one(survivor_name: str, dup_name: str, apply: bool) -> dict[str, Any]:
    entry: dict[str, Any] = {"survivor": survivor_name, "dup": dup_name}

    dup = Projeto.objects.filter(nome=dup_name).first()
    if dup is None:
        entry["status"] = "skip"
        entry["reason"] = "duplicata ausente (já mesclada?)"
        return entry

    try:
        survivor = Projeto.objects.get(nome=survivor_name)
    except Projeto.DoesNotExist as exc:
        raise ValueError(f"survivor ausente: {survivor_name!r}") from exc

    if survivor.pk == dup.pk:
        entry["status"] = "skip"
        entry["reason"] = "survivor == dup"
        return entry

    # #2036: evento de dois projetos com o par {survivor, dup}, nas duas direções. Depois do reparent as duas
    # vagas seriam o mesmo projeto (constraint `solicitacao_projeto_2_valido`): a vaga 2 sai antes do laço e
    # o evento fica só com o sobrevivente.
    par = Solicitacao.objects.filter(Q(projeto=survivor, projeto_2=dup) | Q(projeto=dup, projeto_2=survivor))
    entry["conjunto_desfeito"] = par.count()
    if apply and entry["conjunto_desfeito"]:
        par.update(projeto_2=None)

    # #2036: a duplicata em par com um terceiro projeto passa a formar par com o sobrevivente. Se esse par for
    # inválido (gerência ou fluxo diferente), recusa antes de mudar qualquer coisa: o fluxo divergente faria o
    # evento escapar da aprovação SUPER (PA-01).
    com_terceiro = Solicitacao.objects.filter(
        (Q(projeto=dup) & Q(projeto_2__isnull=False) & ~Q(projeto_2=survivor))
        | (Q(projeto_2=dup) & ~Q(projeto=survivor))
    ).select_related("projeto", "projeto_2")
    for s in com_terceiro:
        terceiro = s.projeto_2 if s.projeto_id == dup.pk else s.projeto
        motivo = par_de_projetos_invalido(survivor, terceiro) if terceiro is not None else None
        if motivo:
            raise ValueError(f"o merge quebraria o par do evento s{s.pk}: {motivo}")

    reparented: dict[str, int] = {}
    for rel in Projeto._meta.related_objects:
        field_name = rel.field.name
        rel_model = rel.related_model
        qs = rel_model.objects.filter(**{field_name: dup})
        if rel_model is Solicitacao and field_name == "projeto_2":
            qs = qs.exclude(projeto=survivor)  # o par desfeito acima (o dry-run conta igual ao apply)
        n = qs.count()
        if not n:
            continue
        if rel.many_to_many:
            raise NotImplementedError(f"M2M não suportado no merge: {rel_model.__name__}.{field_name} ({n})")
        if getattr(rel, "one_to_one", False) and rel_model.objects.filter(**{field_name: survivor}).exists():
            raise ValueError(f"O2O colidiria: {rel_model.__name__}.{field_name}")
        reparented[rel_model.__name__] = reparented.get(rel_model.__name__, 0) + n
        if apply:
            qs.update(**{field_name: survivor})

    entry["survivor_id"] = survivor.pk
    entry["dup_id"] = dup.pk
    entry["reparented"] = reparented
    if apply:
        dup.delete()
        entry["status"] = "merged"
    else:
        entry["status"] = "would_merge"
    return entry


def merge_projeto_duplicates(pairs: list[tuple[str, str]] | None = None, apply: bool = False) -> dict[str, Any]:
    """Mescla `pairs` (default: os 3 pares VIDA). Dry-run por padrão."""
    pairs = pairs if pairs is not None else DEFAULT_PAIRS
    report: dict[str, Any] = {"apply": apply, "pairs": []}

    if apply:
        with transaction.atomic():
            for survivor_name, dup_name in pairs:
                report["pairs"].append(_merge_one(survivor_name, dup_name, apply=True))
    else:
        for survivor_name, dup_name in pairs:
            report["pairs"].append(_merge_one(survivor_name, dup_name, apply=False))

    return report
