"""
Sentinela do invariante de privilégio do AvailabilityBlockViewSet (#1272, RBAC 3.4).

Invariante travado aqui:
  1. `AvailabilityBlockViewSet.permission_classes == [IsAuthenticated]`.
     `view_all_availability` NUNCA pode virar gate de entrada (`permission_classes`)
     — seria a regressão que quebra o fluxo own-block do Formador (RD-02/RD-03: o
     Formador declara o próprio bloqueio SEM ter a capability). A capability é
     bypass de escopo aplicado DENTRO do `get_queryset`.
  2. `is_privileged_user` roteia pela SSOT da Policy (`user_has_policy`) e mantém
     paridade EXATA com a checagem de capability crua: superuser → True; usuário
     com `view_all_availability` → True; sem a cap → False.

Contexto: descoberto na auditoria RBAC (#1254). Tentativas anteriores de exigir
`view_all_availability` em `permission_classes` (Issue #1221) quebraram J06/J07.
Este teste é a rede que impede a re-introdução do bug.

NÃO testa o escopo por gerência em si (coberto por test_multi_sector_permissions,
test_availability_block_idor). Aqui é meta: a forma da autorização.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportUnknownMemberType=false

from __future__ import annotations

from django.contrib.auth.models import Group
from django.core.management import call_command
from rest_framework.permissions import IsAuthenticated

import pytest

from apps.core.models import PermissaoFuncional
from apps.core.tests.factories import UsuarioFactory
from apps.core.views_availability import AvailabilityBlockViewSet, is_privileged_user

pytestmark = pytest.mark.django_db

_CPF = {"i": 0}


def _cpf() -> str:
    _CPF["i"] += 1
    return f"97788{_CPF['i']:06d}"


def _user_with_caps(*codenames: str):
    user = UsuarioFactory(username=f"priv_inv_{_CPF['i']}", password="x", cpf=_cpf())
    if codenames:
        group = Group.objects.create(name=f"grp-priv-inv-{_CPF['i']}")
        user.groups.add(group)
        for code in codenames:
            perm = PermissaoFuncional.objects.filter(codename=code).first()
            assert perm is not None, f"capability '{code}' ausente do seed"
            perm.groups.add(group)
    return user


@pytest.fixture
def seeded(db):
    call_command("seed_rbac")


class TestAvailabilityPrivilegedInvariant:
    def test_viewset_permission_class_stays_isauthenticated(self):
        """
        A GUARDA CENTRAL: permission_classes é exatamente [IsAuthenticated].
        Se alguém trocar por [CanViewAllAvailability] (ou qualquer gate de cap), o
        Formador sem a capability perde o fluxo own-block (RD-02/RD-03). Falha aqui
        com mensagem explícita.
        """
        assert AvailabilityBlockViewSet.permission_classes == [IsAuthenticated], (
            "AvailabilityBlockViewSet.permission_classes DEVE permanecer [IsAuthenticated]. "
            "view_all_availability é bypass de escopo no get_queryset, NUNCA gate de entrada — "
            "movê-lo para permission_classes quebra o own-block do Formador (RD-02/RD-03, #1221)."
        )

    def test_privileged_helper_true_for_view_all_availability(self, seeded):
        user = _user_with_caps("view_all_availability")
        assert is_privileged_user(user) is True

    def test_privileged_helper_false_without_capability(self, seeded):
        # Formador comum (sem view_all_availability) — NÃO é privilegiado.
        user = _user_with_caps()
        assert is_privileged_user(user) is False

    def test_privileged_helper_true_for_superuser(self, seeded):
        user = UsuarioFactory(superuser=True)
        assert is_privileged_user(user) is True

    def test_privileged_helper_routes_through_policy_layer(self, seeded):
        """
        Paridade SSOT: is_privileged_user deve produzir o mesmo resultado que
        user_has_policy('view_all_availability') para todos os atores — provando que
        a checagem roteia pela camada de Policy, não por caminho paralelo.
        """
        from apps.core.rbac.policies import user_has_policy

        priv = _user_with_caps("view_all_availability")
        common = _user_with_caps()
        su = UsuarioFactory(superuser=True)
        for user in (priv, common, su):
            assert is_privileged_user(user) == user_has_policy(user, "view_all_availability")
