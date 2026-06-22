"""
PR 13 hardening RBAC (2026-05-04): delegated AvailabilityBlock creation.

Endpoint coberto:
- POST /api/availability-blocks/

Regra de negócio:
- Sem `usuario_id` (ou == request.user.id): comportamento atual (próprio).
- Com `usuario_id` diferente: requer permissão de delegar.
  - ✅ Superuser
  - ✅ Assistente Administrativo do Controle (composite Setor × Função)
  - ✅ DAT (via capability `manage_admin_registries`)
  - ❌ Coordenador, Apoio, Gerente Sup, Gerente pedagógico, Diretoria,
       Controle puro, Formador
- Target precisa ser Formador ativo (após autorizar requester).
- Anti-enumeração: requester não autorizado recebe 403 ANTES de qualquer
  lookup do target. ID inexistente vs existente vs inativo é
  indistinguível para requester sem permissão.
- AuditLog `DELEGATE_BLOCK_CREATE` registra delegate_user_id e
  target_formador_id quando delegação ocorre.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportMissingTypeStubs=false, reportUnusedFunction=false, reportIndexIssue=false

from __future__ import annotations

import itertools
from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog, AvailabilityBlock, Usuario
from apps.core.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db


_CPF_COUNTER = itertools.count(72000000000)


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


def _make_block_payload(usuario_id: int | None = None) -> dict:
    inicio = timezone.now() + timedelta(days=1)
    fim = inicio + timedelta(hours=2)
    payload: dict = {
        "tipo": "T",
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat(),
        "motivo": "Teste delegação",
    }
    if usuario_id is not None:
        payload["usuario_id"] = usuario_id
    return payload


def _post(client: APIClient, payload: dict):
    return client.post("/api/availability-blocks/", payload, format="json")


# ============================================================================
# Comportamento original (sem usuario_id)
# ============================================================================


class TestSelfCreate:
    def test_formador_cria_bloqueio_proprio_sem_usuario_id(self):
        formador = _formador()
        client = APIClient()
        client.force_authenticate(formador)
        response = _post(client, _make_block_payload())
        assert response.status_code == 201
        block = AvailabilityBlock.objects.get(pk=response.data["id"])
        assert block.usuario_id == formador.id
        assert block.created_by_id == formador.id

    def test_formador_self_target_com_proprio_id_funciona(self):
        formador = _formador()
        client = APIClient()
        client.force_authenticate(formador)
        response = _post(client, _make_block_payload(usuario_id=formador.id))
        assert response.status_code == 201
        block = AvailabilityBlock.objects.get(pk=response.data["id"])
        assert block.usuario_id == formador.id
        assert block.created_by_id == formador.id


# ============================================================================
# Delegação autorizada
# ============================================================================


class TestDelegationAllowed:
    def test_assistente_administrativo_controle_delega_para_formador(self):
        delegate = _user_in_groups("Controle", "Assistente Administrativo", label="asst")
        target = _formador(label="target_asst")
        client = APIClient()
        client.force_authenticate(delegate)
        response = _post(client, _make_block_payload(usuario_id=target.id))
        assert response.status_code == 201
        block = AvailabilityBlock.objects.get(pk=response.data["id"])
        assert block.usuario_id == target.id
        assert block.created_by_id == delegate.id

    def test_dat_delega_para_formador(self):
        # DAT possui capability `manage_admin_registries` atribuída via seed
        # de migrations (`0077_realign_funcperm_groups.py` + descendentes).
        delegate = _user_in_groups("DAT", label="dat")
        target = _formador(label="target_dat")
        client = APIClient()
        client.force_authenticate(delegate)
        response = _post(client, _make_block_payload(usuario_id=target.id))
        assert response.status_code == 201
        block = AvailabilityBlock.objects.get(pk=response.data["id"])
        assert block.usuario_id == target.id
        assert block.created_by_id == delegate.id

    def test_superuser_delega_para_formador(self):
        delegate = UsuarioFactory(superuser=True)
        target = _formador(label="target_su")
        client = APIClient()
        client.force_authenticate(delegate)
        response = _post(client, _make_block_payload(usuario_id=target.id))
        assert response.status_code == 201
        block = AvailabilityBlock.objects.get(pk=response.data["id"])
        assert block.usuario_id == target.id
        assert block.created_by_id == delegate.id


# ============================================================================
# Delegação NÃO autorizada (anti-enumeração: 403 antes de lookup)
# ============================================================================


class TestDelegationDenied:
    @pytest.mark.parametrize(
        "groups,label",
        [
            (("Controle",), "controle_puro"),  # Controle SEM Asst Admin
            (("Coordenador",), "coord"),
            (("Apoio de Coordenação",), "apoio"),
            (("Gerente", "Superintendência"), "gerente_sup"),
            (("Gerente", "Vidas"), "gerente_pedagogico"),
            (("Diretoria",), "diretoria"),
            (("Formador",), "formador_outro"),
        ],
    )
    def test_perfil_nao_autorizado_recebe_403(self, groups, label):
        delegate = _user_in_groups(*groups, label=label)
        target = _formador(label=f"target_{label}")
        client = APIClient()
        client.force_authenticate(delegate)
        response = _post(client, _make_block_payload(usuario_id=target.id))
        assert response.status_code == 403, f"Perfil {label} deveria receber 403 mas obteve {response.status_code}"

    def test_assistente_administrativo_fora_do_controle_recebe_403(self):
        # Função sem o Setor — composite não passa.
        delegate = _user_in_groups("Vidas", "Assistente Administrativo", label="asst_vidas")
        target = _formador(label="target_asst_vidas")
        client = APIClient()
        client.force_authenticate(delegate)
        response = _post(client, _make_block_payload(usuario_id=target.id))
        assert response.status_code == 403

    def test_anti_enumeracao_target_inexistente_para_nao_autorizado(self):
        # Anti-enumeração: 403 mesmo com ID inexistente.
        delegate = _user_in_groups("Coordenador", label="coord_anti_enum")
        client = APIClient()
        client.force_authenticate(delegate)
        response = _post(client, _make_block_payload(usuario_id=99999999))
        assert response.status_code == 403, (
            "Não autorizado deve receber 403 antes de qualquer lookup — "
            "ID inexistente NÃO pode vazar enumeração via 400/404."
        )


# ============================================================================
# Validação de target (apenas para requester autorizado)
# ============================================================================


class TestTargetValidation:
    def test_target_inexistente_recebe_400_para_autorizado(self):
        delegate = _user_in_groups("Controle", "Assistente Administrativo", label="asst_inex")
        client = APIClient()
        client.force_authenticate(delegate)
        response = _post(client, _make_block_payload(usuario_id=99999999))
        assert response.status_code == 400
        # Project-wide error envelope: {code, detail, errors: {field: msg}}.
        errors = response.data.get("errors", response.data)
        assert "usuario_id" in errors

    def test_target_nao_formador_recebe_400(self):
        delegate = _user_in_groups("Controle", "Assistente Administrativo", label="asst_nf")
        non_formador = _user_in_groups("Coordenador", label="non_formador_target")
        client = APIClient()
        client.force_authenticate(delegate)
        response = _post(client, _make_block_payload(usuario_id=non_formador.id))
        assert response.status_code == 400
        # Project-wide error envelope: {code, detail, errors: {field: msg}}.
        errors = response.data.get("errors", response.data)
        assert "usuario_id" in errors

    def test_target_inativo_recebe_400(self):
        delegate = _user_in_groups("Controle", "Assistente Administrativo", label="asst_inativo")
        target = _formador(label="target_inativo", is_active=False)
        client = APIClient()
        client.force_authenticate(delegate)
        response = _post(client, _make_block_payload(usuario_id=target.id))
        assert response.status_code == 400
        # Project-wide error envelope: {code, detail, errors: {field: msg}}.
        errors = response.data.get("errors", response.data)
        assert "usuario_id" in errors


# ============================================================================
# AuditLog
# ============================================================================


class TestAuditLog:
    def test_delegacao_cria_auditlog_com_ids(self):
        delegate = _user_in_groups("Controle", "Assistente Administrativo", label="asst_audit")
        target = _formador(label="target_audit")
        client = APIClient()
        client.force_authenticate(delegate)
        response = _post(client, _make_block_payload(usuario_id=target.id))
        assert response.status_code == 201
        block_id = response.data["id"]

        log = AuditLog.objects.filter(action="DELEGATE_BLOCK_CREATE").latest("created_at")
        assert log.usuario_id == delegate.id
        assert log.model_name == "AvailabilityBlock"
        assert log.details["delegate_user_id"] == delegate.id
        assert log.details["target_formador_id"] == target.id
        assert log.details["block_id"] == block_id
        assert log.details["origem"] == "delegated"
        assert "inicio" in log.details
        assert "fim" in log.details
        # Anti-PII: motivo não deve estar no AuditLog.
        assert "motivo" not in log.details

    def test_self_create_nao_cria_auditlog_de_delegacao(self):
        formador = _formador(label="self_no_audit")
        client = APIClient()
        client.force_authenticate(formador)
        response = _post(client, _make_block_payload())
        assert response.status_code == 201
        assert not AuditLog.objects.filter(action="DELEGATE_BLOCK_CREATE").exists()


# ============================================================================
# Queryset não vaza bloqueios
# ============================================================================


class TestQuerysetIsolation:
    def test_formador_lista_apenas_proprio_bloqueio_apos_delegacao(self):
        delegate = _user_in_groups("Controle", "Assistente Administrativo", label="asst_ql")
        formador_a = _formador(label="form_a")
        formador_b = _formador(label="form_b")

        # Asst Admin cria bloqueio em nome de A.
        client_admin = APIClient()
        client_admin.force_authenticate(delegate)
        resp = _post(client_admin, _make_block_payload(usuario_id=formador_a.id))
        assert resp.status_code == 201

        # Formador A vê o próprio bloqueio.
        client_a = APIClient()
        client_a.force_authenticate(formador_a)
        resp_a = client_a.get("/api/availability-blocks/")
        assert resp_a.status_code == 200
        # DRF paginated ou lista direta — checagem agnóstica.
        results_a = resp_a.data.get("results", resp_a.data)
        assert len(results_a) == 1

        # Formador B NÃO vê o bloqueio do A.
        client_b = APIClient()
        client_b.force_authenticate(formador_b)
        resp_b = client_b.get("/api/availability-blocks/")
        assert resp_b.status_code == 200
        results_b = resp_b.data.get("results", resp_b.data)
        assert len(results_b) == 0
