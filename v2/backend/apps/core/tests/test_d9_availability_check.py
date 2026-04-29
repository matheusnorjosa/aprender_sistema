"""Tests para D9 fix: AvailabilityCheckView libera consulta para Coord/Gerente Sup."""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false, reportPrivateUsage=false, reportUnusedFunction=false

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.management import call_command
from rest_framework.test import APIClient

import pytest

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _seed():
    call_command("seed_rbac")
    cache.clear()
    yield
    cache.clear()


_cpf_counter = [0]


def _next_cpf():
    _cpf_counter[0] += 1
    return f"99988{_cpf_counter[0]:06d}"


def _make_user_with_caps(username, group_names, cap_codenames):
    from apps.core.models import PermissaoFuncional

    user = User.objects.create_user(username=username, email=f"{username}@t.com", password="x", cpf=_next_cpf())
    for gn in group_names:
        g, _ = Group.objects.get_or_create(name=gn)
        user.groups.add(g)
        for code in cap_codenames:
            p = PermissaoFuncional.objects.filter(codename=code).first()
            assert p is not None
            p.groups.add(g)
    return user


def _make_target():
    return User.objects.create_user(
        username=f"target_{_cpf_counter[0]}", email=f"t{_cpf_counter[0]}@t.com", password="x", cpf=_next_cpf()
    )


def _check(user, target_id, municipio_id=None):
    client = APIClient()
    client.force_authenticate(user=user)
    qs = f"?usuario_id={target_id}&inicio=2026-05-15T11:30:00-03:00&fim=2026-05-15T13:30:00-03:00"
    if municipio_id:
        qs += f"&municipio_id={municipio_id}"
    return client.get("/api/availability/check/" + qs)


class TestD9CheckAvailabilityForOthers:
    """D9 (PR 2 RBAC hardening): expandir consulta de conflito para Coord/Gerente Sup."""

    def test_super_geral_consulta_formador(self):
        """Gerente + Sup com approve_solicitation_batch: consulta formador → 200."""
        user = _make_user_with_caps(
            "super_geral_check",
            ["Gerente", "Superintendência"],
            ["approve_solicitation_batch", "create_solicitation"],
        )
        target = _make_target()
        res = _check(user, target.id)
        assert res.status_code == 200, f"Got {res.status_code}: {res.content[:200]}"

    def test_coord_consulta_formador(self):
        """Coord com create_solicitation: consulta formador → 200."""
        user = _make_user_with_caps("coord_check", ["Coordenador"], ["create_solicitation"])
        target = _make_target()
        res = _check(user, target.id)
        assert res.status_code == 200, f"Got {res.status_code}: {res.content[:200]}"

    def test_apoio_consulta_formador(self):
        """Apoio com create_solicitation: consulta formador → 200."""
        user = _make_user_with_caps("apoio_check", ["Apoio de Coordenação"], ["create_solicitation"])
        target = _make_target()
        res = _check(user, target.id)
        assert res.status_code == 200, f"Got {res.status_code}: {res.content[:200]}"

    def test_formador_consulta_outro_formador_403(self):
        """Formador sem nenhuma cap: tenta consultar outro → 403."""
        user = _make_user_with_caps("formador_check", ["Formador"], [])
        target = _make_target()
        res = _check(user, target.id)
        assert res.status_code == 403, f"Got {res.status_code}: {res.content[:200]}"

    def test_dat_consulta_formador(self):
        """DAT com view_all_availability (D9): consulta → 200."""
        user = _make_user_with_caps("dat_check", ["DAT"], ["view_all_availability"])
        target = _make_target()
        res = _check(user, target.id)
        assert res.status_code == 200, f"Got {res.status_code}: {res.content[:200]}"

    def test_user_sem_grupos_sem_cap_403(self):
        """User autenticado sem grupos/caps: tenta consultar outro → 403."""
        user = _make_user_with_caps("naked_user", [], [])
        target = _make_target()
        res = _check(user, target.id)
        assert res.status_code == 403, f"Got {res.status_code}: {res.content[:200]}"

    def test_block_viewset_nao_afetado_para_coord(self):
        """REGRESSION GUARD: AvailabilityBlockViewSet.get_queryset NÃO foi afetado.
        Coord sem view_all_availability NÃO deve ver bloqueios cross-gerência."""
        from apps.core.views_availability import is_privileged_user

        coord = _make_user_with_caps("coord_block", ["Coordenador"], ["create_solicitation"])
        # Coord tem create_solicitation mas NÃO tem view_all_availability
        # is_privileged_user deve retornar False (semântica preservada).
        assert not is_privileged_user(coord), "Coord NÃO deve ser privilegiado para bloqueios"
