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

from apps.core.models import Projeto, Solicitacao
from apps.core.services.solicitacao_projetos import (
    VAGAS,
    grupo_de_projetos_invalido,
    projetos_do_evento,
    q_tem_projeto,
)

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

    # #2036 e VIR-17: nos eventos com a duplicata em qualquer vaga, ela vira o sobrevivente. Se ele já estava
    # no evento, fica na vaga mais à frente entre a dele e a da duplicata, a outra sai e as de trás sobem
    # ((dup, x, s) vira (s, x); sem vaga vazia no meio nem projeto repetido, as constraints
    # `solicitacao_projeto_2_valido` e `_3_valido`): o conjunto é desfeito. Se o grupo novo for inválido
    # (gerência ou fluxo diferente), recusa antes de mudar qualquer coisa: o fluxo divergente faria o evento
    # escapar da aprovação SUPER (PA-01).
    eventos = Solicitacao.objects.filter(q_tem_projeto(pk=dup.pk)).select_related(*VAGAS).order_by("pk")
    if apply:
        # VIR17A-M5: o UPDATE abaixo regrava as três vagas com o que foi lido aqui. O lock (até o fim do
        # transaction.atomic de `merge_projeto_duplicates`) impede que uma edição no meio se perca.
        eventos = eventos.select_for_update(of=("self",))
    novas_vagas: list[tuple[int, list[Projeto]]] = []
    entry["conjunto_desfeito"] = 0
    for s in eventos:
        antes = projetos_do_evento(s)
        depois = list({p.pk: p for p in (survivor if p.pk == dup.pk else p for p in antes)}.values())
        motivo = grupo_de_projetos_invalido(*depois)
        if motivo:
            raise ValueError(f"o merge quebraria o par ou trio de projetos do evento s{s.pk}: {motivo}")
        entry["conjunto_desfeito"] += len(depois) < len(antes)
        novas_vagas.append((s.pk, depois))
    n_trocados = len(novas_vagas) - entry["conjunto_desfeito"]

    reparented: dict[str, int] = {"Solicitacao": n_trocados} if n_trocados else {}
    if apply:
        for pk, depois in novas_vagas:
            vagas = depois + [None] * (len(VAGAS) - len(depois))
            Solicitacao.objects.filter(pk=pk).update(**dict(zip(VAGAS, vagas, strict=True)))

    for rel in Projeto._meta.related_objects:
        field_name = rel.field.name
        rel_model = rel.related_model
        if rel_model is Solicitacao and field_name in VAGAS:
            continue  # trocadas acima, evento a evento
        qs = rel_model.objects.filter(**{field_name: dup})
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
