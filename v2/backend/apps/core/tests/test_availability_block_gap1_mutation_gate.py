"""
GAP-1 (auditoria object-level authz #1, 2026-09-14): mutar bloqueio de TERCEIRO
exige o MESMO gate estreito do create delegado (`user_can_delegate_availability_block`).

Furo medido: `AvailabilityBlockViewSet.get_queryset` dá `.all()` a quem tem
`view_all_availability` (LEITURA; seed → Controle/DAT) ANTES de escopar update/destroy,
então um Controle-PURO (privilegiado na leitura, mas SEM poder de delegação) editava/
apagava bloqueio de qualquer um. Assimétrico com o create (PR 13), que exige
`user_can_delegate_availability_block` para agir sobre terceiro.

Decisão do dono (2026-09-14): IGUALAR update/destroy ao create — quem NÃO pode criar
bloqueio de terceiro também NÃO edita nem apaga. Delegantes (superuser, Assistente
Administrativo do Controle, DAT) seguem podendo, e a mutação de terceiro gera AuditLog.
Own-block segue livre para todos.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false

from __future__ import annotations

import itertools
from datetime import timedelta

from django.contrib.auth.models import Group
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog, AvailabilityBlock, PermissaoFuncional, Usuario
from apps.core.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db

_CPF_COUNTER = itertools.count(81000000000)


@pytest.fixture
def seeded(db):
    call_command("seed_rbac")


def _user_with_caps(*codenames: str, label: str = "gap1") -> Usuario:
    cpf = str(next(_CPF_COUNTER)).zfill(11)
    user = UsuarioFactory(username=f"{label}_{cpf}", password="x", cpf=cpf)
    if codenames:
        group = Group.objects.create(name=f"grp-{label}-{cpf}")
        user.groups.add(group)
        for code in codenames:
            perm = PermissaoFuncional.objects.filter(codename=code).first()
            assert perm is not None, f"capability '{code}' ausente do seed"
            perm.groups.add(group)
    return user


def _block_owned_by(owner: Usuario, motivo: str = "Bloqueio do dono") -> AvailabilityBlock:
    agora = timezone.now()
    return AvailabilityBlock.objects.create(
        usuario=owner,
        tipo="T",
        inicio=agora + timedelta(days=1),
        fim=agora + timedelta(days=1, hours=4),
        motivo=motivo,
    )


class TestGap1MutationGate:
    """Update/destroy de bloqueio de terceiro seguem o gate de delegação (não o de leitura)."""

    def test_privileged_nondelegate_cannot_update_other_block(self, seeded):
        controle_puro = _user_with_caps("view_all_availability", label="controle")
        dono = UsuarioFactory(username="dono_u", cpf=str(next(_CPF_COUNTER)).zfill(11))
        bloco = _block_owned_by(dono)

        client = APIClient()
        client.force_authenticate(controle_puro)
        resp = client.patch(f"/api/availability-blocks/{bloco.id}/", {"motivo": "invasao"}, format="json")

        assert resp.status_code == 403
        bloco.refresh_from_db()
        assert bloco.motivo == "Bloqueio do dono"

    def test_privileged_nondelegate_cannot_delete_other_block(self, seeded):
        controle_puro = _user_with_caps("view_all_availability", label="controle")
        dono = UsuarioFactory(username="dono_d", cpf=str(next(_CPF_COUNTER)).zfill(11))
        bloco = _block_owned_by(dono)

        client = APIClient()
        client.force_authenticate(controle_puro)
        resp = client.delete(f"/api/availability-blocks/{bloco.id}/")

        assert resp.status_code == 403
        assert AvailabilityBlock.objects.filter(id=bloco.id).exists()

    def test_delegate_can_update_other_block_and_audits(self, seeded):
        delegado = _user_with_caps("view_all_availability", "manage_admin_registries", label="dat")
        dono = UsuarioFactory(username="dono_du", cpf=str(next(_CPF_COUNTER)).zfill(11))
        bloco = _block_owned_by(dono)

        client = APIClient()
        client.force_authenticate(delegado)
        resp = client.patch(f"/api/availability-blocks/{bloco.id}/", {"motivo": "ajuste DAT"}, format="json")

        assert resp.status_code == 200
        bloco.refresh_from_db()
        assert bloco.motivo == "ajuste DAT"
        assert AuditLog.objects.filter(action=AuditLog.Action.DELEGATE_BLOCK_UPDATE, usuario=delegado).exists()

    def test_delegate_can_delete_other_block_and_audits(self, seeded):
        delegado = _user_with_caps("view_all_availability", "manage_admin_registries", label="dat")
        dono = UsuarioFactory(username="dono_dd", cpf=str(next(_CPF_COUNTER)).zfill(11))
        bloco = _block_owned_by(dono)
        block_id = bloco.id

        client = APIClient()
        client.force_authenticate(delegado)
        resp = client.delete(f"/api/availability-blocks/{block_id}/")

        assert resp.status_code == 204
        assert not AvailabilityBlock.objects.filter(id=block_id).exists()
        assert AuditLog.objects.filter(action=AuditLog.Action.DELEGATE_BLOCK_DELETE, usuario=delegado).exists()

    def test_superuser_can_delete_other_block(self, seeded):
        admin = UsuarioFactory(superuser=True)
        dono = UsuarioFactory(username="dono_su", cpf=str(next(_CPF_COUNTER)).zfill(11))
        bloco = _block_owned_by(dono)
        block_id = bloco.id

        client = APIClient()
        client.force_authenticate(admin)
        resp = client.delete(f"/api/availability-blocks/{block_id}/")

        assert resp.status_code == 204
        assert not AvailabilityBlock.objects.filter(id=block_id).exists()

    def test_owner_updates_own_block_no_delegate_audit(self, seeded):
        formador = UsuarioFactory(username="form_own", cpf=str(next(_CPF_COUNTER)).zfill(11))
        bloco = _block_owned_by(formador, motivo="Meu bloqueio")

        client = APIClient()
        client.force_authenticate(formador)
        resp = client.patch(f"/api/availability-blocks/{bloco.id}/", {"motivo": "atualizado"}, format="json")

        assert resp.status_code == 200
        bloco.refresh_from_db()
        assert bloco.motivo == "atualizado"
        assert not AuditLog.objects.filter(action=AuditLog.Action.DELEGATE_BLOCK_UPDATE).exists()
