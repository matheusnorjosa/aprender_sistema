"""
M10-01 (#1623) — SSOT de escopo ator×gerência para Solicitacao.

Antes, quem tinha as caps `approve_solicitation` / `approve_solicitation_batch`
(concedidas ao grupo FUNÇÃO "Gerente" inteiro, não só ao aprovador composto)
via/editava/excluía solicitações de QUALQUER gerência — alcance nacional sem
escopo. Um Gerente pedagógico (não-Superintendência) não consegue aprovar (isso
exige o composite), mas conseguia ler/editar/excluir tudo.

Regra:
- GLOBAL (vê tudo): superuser, Controle (`operate_preagenda`), DAT
  (`manage_admin_registries`) e o aprovador composto
  (`access_solicitation_approvals` = Gerente-da-Superintendência OU Assistente
  Administrativo do Controle).
- GESTOR não-global (tem `approve_solicitation*` mas não é global): reduzido de
  nacional para a(s) própria(s) gerência(s) (via EquipeGerencia) + as próprias.
- DEMAIS (Coordenador etc.): apenas as próprias (comportamento inalterado).

Consumido tanto pelo `get_queryset` do `SolicitacaoViewSet` quanto pelo
`IsOwnerOrPrivileged.has_object_permission` (mesma semântica em list e em objeto;
fora do escopo → 404, não distinguível de inexistente).
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingTypeArgument=false

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from typing import Any

from django.db.models import Q, QuerySet

from apps.core.models import EquipeGerencia
from apps.core.rbac.policies import user_has_policy
from apps.core.rbac_helpers import user_has_any_perm

# Caps que hoje concediam alcance nacional de solicitação (vazam para todo Gerente).
_MANAGER_CAPS = ("approve_solicitation", "approve_solicitation_batch")


def user_is_solicitacao_global(user: Any) -> bool:
    """Autoridade que legitimamente enxerga TODAS as solicitações."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    # `approve_solicitation` é EXCLUSIVA do setor Superintendência (o órgão de
    # oversight/aprovação) — visão global legítima. NÃO incluir
    # `approve_solicitation_batch` aqui: essa é concedida ao grupo FUNÇÃO "Gerente"
    # inteiro e é justamente o que vazava alcance nacional p/ Gerente pedagógico
    # (por isso o escopo abaixo). `operate_preagenda`=Controle, `manage_admin_registries`=DAT.
    if user_has_any_perm(user, "operate_preagenda", "manage_admin_registries", "approve_solicitation"):
        return True
    # Aprovador composto (Gerente-da-Superintendência OU Asst-Admin-Controle).
    return user_has_policy(user, "access_solicitation_approvals")


def _user_gerencia_ids(user: Any) -> set[int]:
    return set(EquipeGerencia.vigentes_em().filter(usuario=user).values_list("gerencia_id", flat=True))


def scope_solicitacoes(qs: QuerySet, user: Any) -> QuerySet:
    """Restringe `qs` ao escopo do `user` (ver regra no módulo)."""
    if user_is_solicitacao_global(user):
        return qs
    if user_has_any_perm(user, *_MANAGER_CAPS):
        gerencia_ids = _user_gerencia_ids(user)
        return qs.filter(Q(usuario=user) | Q(projeto__gerencia_id__in=gerencia_ids))
    return qs.filter(usuario=user)


def user_can_access_solicitacao(user: Any, obj: Any) -> bool:
    """True sse `user` pode acessar a Solicitacao `obj` (mesma regra do queryset)."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if user_is_solicitacao_global(user):
        return True
    if getattr(obj, "usuario_id", None) == getattr(user, "id", None):
        return True
    if user_has_any_perm(user, *_MANAGER_CAPS):
        gerencia_id = getattr(getattr(obj, "projeto", None), "gerencia_id", None)
        return gerencia_id is not None and gerencia_id in _user_gerencia_ids(user)
    return False


def user_setores(user: Any) -> set[str]:
    """Setores (`Gerencia.setor_canonico`) das gerências vigentes do `user`.

    SSOT do "setor do ator" para o escopo de participantes (M10-04/#1656 Wave 1).
    ⚑ Setor ≠ Gerencia: o modelo `Gerencia` é fino (Vidas L/M/C são registros
    distintos) e colapsa em um SETOR por `setor_canonico`. Usa a mesma vigência
    (`vigentes_em()`) do resto do módulo e descarta `setor_canonico` vazio/nulo
    (gerência sem setor não define escopo).
    """
    return set(
        EquipeGerencia.vigentes_em()
        .filter(usuario=user)
        .exclude(gerencia__setor_canonico="")
        .exclude(gerencia__setor_canonico__isnull=True)
        .values_list("gerencia__setor_canonico", flat=True)
    )


def _setores_por_usuario(user_ids: list[int]) -> dict[int, set[str]]:
    """Mapa user_id → setores (1 query) para checar vários participantes de uma vez."""
    out: dict[int, set[str]] = defaultdict(set)
    if not user_ids:
        return out
    rows = (
        EquipeGerencia.vigentes_em()
        .filter(usuario_id__in=user_ids)
        .exclude(gerencia__setor_canonico="")
        .exclude(gerencia__setor_canonico__isnull=True)
        .values_list("usuario_id", "gerencia__setor_canonico")
    )
    for uid, setor in rows:
        out[uid].add(setor)
    return out


def participants_out_of_setor(creator: Any, users: Sequence[Any]) -> list[Any]:
    """Retorna os `users` cujo SETOR é disjunto do setor do `creator`.

    M10-04/#1656 Wave 1: o coordenador regular só adiciona formador/coord do próprio
    setor. Medido em prod (2026-09-15): 0 cross-setor para coordenador regular; os 3
    cross-setor reais são todos da Superintendência (isenta abaixo).

    - Criador GLOBAL/privilegiado (`user_is_solicitacao_global`: superuser,
      Superintendência, Controle, DAT) → isento → lista vazia.
    - Criador SEM setor → fail-open (não dá p/ escopar; 0 em prod) → lista vazia.
    - Caso contrário: participante sem setor OU de setor disjunto = fora do escopo
      (fail-closed para o participante).
    """
    if not users:
        return []
    if user_is_solicitacao_global(creator):
        return []
    creator_setores = user_setores(creator)
    if not creator_setores:
        return []
    smap = _setores_por_usuario([u.id for u in users])
    return [u for u in users if not (smap.get(u.id, set()) & creator_setores)]


def scope_usuarios_by_setor(qs: QuerySet, user: Any) -> QuerySet:
    """Restringe um queryset de `Usuario` aos que compartilham SETOR com `user`.

    Espelho de LEITURA do `participants_out_of_setor` (write-path): alimenta o
    `/lookup/usuarios/` para o picker do wizard já oferecer só o setor do
    coordenador (M10-04/#1656 Wave 1) — assim o FE nunca mostra opção que o
    backend recusaria (contrato FE-first satisfeito pela fonte de dados).

    - Global/privilegiado (`user_is_solicitacao_global`: superuser, Superintendência,
      Controle, DAT) → sem filtro.
    - `user` sem setor → sem filtro (fail-open; espelha o write-path).
    - Caso contrário: só usuários com vínculo vigente em algum desses setores.
    """
    if user_is_solicitacao_global(user):
        return qs
    setores = user_setores(user)
    if not setores:
        return qs
    vigentes = (
        EquipeGerencia.vigentes_em().filter(gerencia__setor_canonico__in=setores).values_list("usuario_id", flat=True)
    )
    return qs.filter(id__in=vigentes)


def scope_projetos_by_setor(qs: QuerySet, user: Any) -> QuerySet:
    """Restringe um queryset de `Projeto` aos do SETOR do `user` (S2, épico #1656).

    Mesma regra do participante, eixo projeto: alimenta o `/lookup/projetos/` para o
    wizard só oferecer projetos do setor do coordenador. `Projeto.setor` casa com
    `Gerencia.setor_canonico` por igualdade (o mesmo de-para v15).
    - Global/privilegiado (`user_is_solicitacao_global`) → sem filtro.
    - `user` sem setor → sem filtro (fail-open).
    - Projeto SEM setor → incluído (fail-open; `Projeto.setor` é gap conhecido).
    """
    if user_is_solicitacao_global(user):
        return qs
    setores = user_setores(user)
    if not setores:
        return qs
    return qs.filter(Q(setor__in=[*setores, ""]) | Q(setor__isnull=True))


def projeto_out_of_setor(creator: Any, projeto: Any) -> bool:
    """True sse `projeto` é de um SETOR ao qual o `creator` regular não pertence.

    Write-path do S2 (create/update de Solicitacao). Fail-open (False) quando:
    criador global/privilegiado, criador sem setor, `projeto` None, ou projeto sem
    setor (gap de dado). Só barra quando o criador TEM setor e o projeto tem um
    setor diferente.
    """
    if projeto is None or user_is_solicitacao_global(creator):
        return False
    creator_setores = user_setores(creator)
    if not creator_setores:
        return False
    proj_setor = getattr(projeto, "setor", "") or ""
    if not proj_setor:
        return False
    return proj_setor not in creator_setores
