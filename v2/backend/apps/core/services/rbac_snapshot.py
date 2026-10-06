"""
Retrato do poder de cada pessoa, para o simulador `rbac_diff` (PR 1, ADR-020). Somente leitura.

Antes de cada PR que muda poder, roda-se em produção e o dono vê quem ganha e quem perde.
Nada aqui grava no banco nem no cache: as capacidades de hoje vêm de consulta direta (a mesma de
`rbac_permissions.get_user_functional_permissions`, sem o cache), e as policies são calculadas
sobre essas capacidades (`resolve_public_policies(..., capacidades=...)`).

Sem dado pessoal: a pessoa é só `u<id>`. Nunca username (é o CPF), nome, e-mail nem telefone.

`capacidades_de` é o ponto de extensão dos PRs seguintes: passa-se a fórmula nova e compara-se o
retrato simulado com o de hoje, contra o banco real.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from typing import Any

from django.db.models import Q, QuerySet

from apps.core.constants import SETOR_GROUPS
from apps.core.models import EquipeGerencia, Gerencia, PermissaoFuncional, Usuario
from apps.core.rbac.policies import resolve_public_policies

Snapshot = dict[str, dict[str, Any]]

# Ordem fixa dos campos no diff e na saída do comando.
CAMPOS: tuple[str, ...] = ("superusuario", "grupos", "capacidades", "policies", "gerencias_escopo", "vinculos")


def capacidades_de_hoje(usuario: Any) -> set[str]:
    """Capacidades de hoje, por consulta direta: a de `get_user_functional_permissions`, sem cache."""
    return set(PermissaoFuncional.objects.filter(groups__user__id=usuario.id).values_list("codename", flat=True))


def _uid(usuario_id: int) -> str:
    return f"u{usuario_id}"


def snapshot_de_poder(
    usuarios: QuerySet[Usuario] | None = None,
    capacidades_de: Callable[[Any], set[str]] | None = None,
) -> Snapshot:
    """Poder de cada pessoa ATIVA: superusuário, grupos, capacidades, policies, escopo e vínculos."""
    calcular = capacidades_de or capacidades_de_hoje
    qs = (usuarios if usuarios is not None else Usuario.objects.all()).filter(is_active=True)
    qs = qs.prefetch_related("groups").order_by("id")

    vinculos: dict[int, set[tuple[int, str]]] = {}
    escopo: dict[int, set[int]] = {}
    ids = list(qs.values_list("id", flat=True))
    for uid, gid, papel in (
        EquipeGerencia.vigentes_em().filter(usuario_id__in=ids).values_list("usuario_id", "gerencia_id", "papel")
    ):
        vinculos.setdefault(uid, set()).add((gid, papel))
    for uid, gid in (
        EquipeGerencia.vigentes_com_escopo_em().filter(usuario_id__in=ids).values_list("usuario_id", "gerencia_id")
    ):
        escopo.setdefault(uid, set()).add(gid)

    snapshot: Snapshot = {}
    for usuario in qs:
        capacidades = set(calcular(usuario))
        snapshot[_uid(usuario.id)] = {
            "superusuario": bool(usuario.is_superuser),
            "grupos": sorted(g.name for g in usuario.groups.all()),
            "capacidades": sorted(capacidades),
            "policies": resolve_public_policies(usuario, capacidades=capacidades),
            "gerencias_escopo": sorted(escopo.get(usuario.id, set())),
            "vinculos": [list(v) for v in sorted(vinculos.get(usuario.id, set()))],
        }
    return snapshot


def _itens(pessoa: dict[str, Any] | None, campo: str) -> set[Any]:
    """Conjunto comparável do campo; vínculo vira tupla e superusuário vira {"superusuario"}."""
    if pessoa is None:
        return set()
    valor = pessoa.get(campo)
    if campo == "superusuario":
        return {"superusuario"} if valor else set()
    if campo == "vinculos":
        return {tuple(v) for v in valor or []}
    return set(valor or [])


def _lista(itens: set[Any]) -> list[Any]:
    return [list(i) if isinstance(i, tuple) else i for i in sorted(itens)]


def _ordem(chave: str) -> tuple[int, str]:
    return (int(chave[1:]), chave) if chave[1:].isdigit() else (-1, chave)


def diff_snapshots(antes: Snapshot, depois: Snapshot) -> dict[str, Any]:
    """Ganhos e perdas por pessoa e por campo. Quem entra ganha tudo; quem sai perde tudo."""
    pessoas: dict[str, dict[str, dict[str, list[Any]]]] = {}
    ganhos = perdas = 0
    for chave in sorted(set(antes) | set(depois), key=_ordem):
        mudancas: dict[str, dict[str, list[Any]]] = {}
        for campo in CAMPOS:
            a, d = _itens(antes.get(chave), campo), _itens(depois.get(chave), campo)
            if a != d:
                mudancas[campo] = {"ganha": _lista(d - a), "perde": _lista(a - d)}
                ganhos += len(d - a)
                perdas += len(a - d)
        if mudancas:
            pessoas[chave] = mudancas
    entram = sorted(set(depois) - set(antes), key=_ordem)
    saem = sorted(set(antes) - set(depois), key=_ordem)
    return {
        "pessoas": pessoas,
        "entram": entram,
        "saem": saem,
        "resumo": {
            "ganhos": ganhos,
            "perdas": perdas,
            "pessoas_com_mudanca": len(pessoas),
            "entram": len(entram),
            "saem": len(saem),
        },
    }


def diagnostico_de_lotacao() -> dict[str, Any]:
    """Medições do PR 1 (relatório de arquitetura de permissões, seção 4). Sem dado pessoal.

    "Grupo de setor sem vínculo": pessoa ativa num grupo de `SETOR_GROUPS` sem vínculo vigente
    (qualquer papel, inclusive EQUIPE) numa gerência daquele setor. Gerência do setor = a de
    `setor_canonico` igual ao nome do grupo, o mesmo casamento de `setor_group_for`.
    """
    gerencias = list(Gerencia.objects.order_by("id").values_list("id", "setor_canonico"))
    gerencias_do_setor: dict[str, set[int]] = {}
    for gid, setor in gerencias:
        gerencias_do_setor.setdefault((setor or "").strip(), set()).add(gid)

    vigentes = list(
        EquipeGerencia.vigentes_em().filter(usuario__is_active=True).values_list("usuario_id", "gerencia_id")
    )
    por_pessoa = Counter(uid for uid, _ in vigentes)
    gerencias_por_pessoa: dict[int, set[int]] = {}
    for uid, gid in vigentes:
        gerencias_por_pessoa.setdefault(uid, set()).add(gid)

    sem_vinculo: dict[str, list[str]] = {}
    for setor in SETOR_GROUPS:
        do_setor = gerencias_do_setor.get(setor, set())
        membros = Usuario.objects.filter(is_active=True, groups__name=setor).values_list("id", flat=True)
        faltam = [_uid(uid) for uid in sorted(set(membros)) if not gerencias_por_pessoa.get(uid, set()) & do_setor]
        if faltam:
            sem_vinculo[setor] = faltam

    return {
        "setor_canonico": {str(gid): setor or "" for gid, setor in gerencias},
        "gerencias_controle_diretoria": {
            nome: sorted(
                Gerencia.objects.filter(Q(nome__iexact=nome) | Q(setor_canonico__iexact=nome)).values_list(
                    "id", flat=True
                )
            )
            for nome in ("CONTROLE", "DIRETORIA")
        },
        "pessoas_com_mais_de_um_vinculo": sum(1 for n in por_pessoa.values() if n > 1),
        "pessoas_em_mais_de_uma_gerencia": sum(1 for gs in gerencias_por_pessoa.values() if len(gs) > 1),
        "gerencias_por_setor": {s: sorted(gerencias_do_setor.get(s, set())) for s in SETOR_GROUPS},
        "grupo_de_setor_sem_vinculo": sem_vinculo,
    }
