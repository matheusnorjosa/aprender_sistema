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
    return set(EquipeGerencia.objects.vigente_em().filter(usuario=user).values_list("gerencia_id", flat=True))


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
