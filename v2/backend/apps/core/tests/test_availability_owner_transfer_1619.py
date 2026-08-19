"""
M08-01 (#1619) — titularidade de AvailabilityBlock é imutável na edição.

Contexto: `AvailabilityBlockViewSet` tratava delegação só no CREATE
(`perform_create`), mas NÃO tinha `perform_update`. O campo write-only
`usuario_id` (attname da FK) chegava intacto ao `ModelSerializer.update()`
default e **reatribuía o dono** do bloco num PATCH/PUT — transferência
silenciosa para um usuário arbitrário, sem policy de delegação e sem AuditLog.
`get_queryset` restringe o comum ao próprio bloco, então ele transferia o
PRÓPRIO bloqueio (aprovado) para outra pessoa.

Invariante: editar um bloqueio altera horário/motivo, NUNCA o dono. A concessão
de titularidade existe apenas no CREATE (perform_create, delegação PR 13).
Tentar mudar `usuario_id` na edição → 403.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

import itertools
from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import AvailabilityBlock, Usuario
from apps.core.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db

_CPF_COUNTER = itertools.count(73000000000)


def _user_in_groups(*group_names: str, label: str = "user", is_active: bool = True) -> Usuario:
    cpf = str(next(_CPF_COUNTER)).zfill(11)
    return UsuarioFactory(
        username=f"{label}_{cpf}",
        email=f"{label}_{cpf}@example.com",
        password="testpass",
        cpf=cpf,
        is_active=is_active,
        groups=list(group_names),
    )


def _formador(label: str = "formador", is_active: bool = True) -> Usuario:
    return _user_in_groups("Formador", label=label, is_active=is_active)


def _make_block(owner: Usuario, created_by: Usuario | None = None) -> AvailabilityBlock:
    inicio = timezone.now() + timedelta(days=1)
    return AvailabilityBlock.objects.create(
        usuario=owner,
        created_by=created_by or owner,
        tipo="T",
        inicio=inicio,
        fim=inicio + timedelta(hours=2),
        status="aprovado",
    )


def _detail(pk: int) -> str:
    return f"/api/availability-blocks/{pk}/"


class TestOwnerTransferBlocked:
    def test_common_user_cannot_transfer_own_block_via_patch(self):
        """RED: hoje o PATCH aplica usuario_id e transfere o dono (200)."""
        owner = _formador(label="owner_patch")
        outro = _formador(label="alvo_patch")
        block = _make_block(owner)

        client = APIClient()
        client.force_authenticate(owner)
        resp = client.patch(_detail(block.id), {"usuario_id": outro.id}, format="json")

        assert resp.status_code == 403, f"esperado 403, obteve {resp.status_code}"
        block.refresh_from_db()
        assert block.usuario_id == owner.id  # RED: virava outro.id

    def test_common_user_cannot_transfer_own_block_via_put(self):
        owner = _formador(label="owner_put")
        outro = _formador(label="alvo_put")
        block = _make_block(owner)

        client = APIClient()
        client.force_authenticate(owner)
        inicio = timezone.now() + timedelta(days=2)
        payload = {
            "tipo": "T",
            "inicio": inicio.isoformat(),
            "fim": (inicio + timedelta(hours=2)).isoformat(),
            "motivo": "editado",
            "usuario_id": outro.id,
        }
        resp = client.put(_detail(block.id), payload, format="json")

        assert resp.status_code == 403
        block.refresh_from_db()
        assert block.usuario_id == owner.id

    def test_transfer_blocked_even_for_superuser(self):
        """A imutabilidade da titularidade é invariante de dados — vale p/ todos.
        Superuser que precise reatribuir exclui e recria."""
        owner = _formador(label="owner_su")
        outro = _formador(label="alvo_su")
        block = _make_block(owner)

        su = UsuarioFactory(superuser=True)
        client = APIClient()
        client.force_authenticate(su)
        resp = client.patch(_detail(block.id), {"usuario_id": outro.id}, format="json")

        assert resp.status_code == 403
        block.refresh_from_db()
        assert block.usuario_id == owner.id


class TestLegitimateEditStillWorks:
    def test_owner_edits_times_without_usuario_id(self):
        """Não-regressão: editar horário do próprio bloqueio funciona; dono intacto."""
        owner = _formador(label="owner_edit")
        block = _make_block(owner)

        client = APIClient()
        client.force_authenticate(owner)
        novo_inicio = timezone.now() + timedelta(days=3)
        resp = client.patch(
            _detail(block.id),
            {"inicio": novo_inicio.isoformat(), "fim": (novo_inicio + timedelta(hours=1)).isoformat()},
            format="json",
        )
        assert resp.status_code == 200, resp.data
        block.refresh_from_db()
        assert block.usuario_id == owner.id
        assert abs((block.inicio - novo_inicio).total_seconds()) < 2

    def test_patch_usuario_id_equal_self_is_noop(self):
        """usuario_id == dono atual não é transferência — passa e mantém o dono."""
        owner = _formador(label="owner_self")
        block = _make_block(owner)

        client = APIClient()
        client.force_authenticate(owner)
        resp = client.patch(_detail(block.id), {"usuario_id": owner.id, "motivo": "ok"}, format="json")

        assert resp.status_code == 200, resp.data
        block.refresh_from_db()
        assert block.usuario_id == owner.id
