"""
Tests: Deslocamento CRUD API — Issue #188

Test Coverage:
- test_deslocamento_list: List with filters (usuario_id, data_inicio, data_fim, origem, destino)
- test_deslocamento_create: Create with validation (start_date < end_date, origem != destino)
- test_deslocamento_update: Update and AuditLog
- test_deslocamento_delete: Delete and AuditLog
- test_deslocamento_validation: Validation errors (start_date >= end_date, origem == destino)
- test_deslocamento_rbac: Only Controle/Coordenador/DAT can access

Permissions:
- HasPerm("operate_preagenda") (Controle, DAT, Superintendência)
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from datetime import date, timedelta

from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog, Deslocamento, Usuario
from apps.core.tests.conftest import get_field_errors


@pytest.fixture
def grupos(db):
    """Create necessary groups."""
    controle, _ = Group.objects.get_or_create(name="Controle")
    dat, _ = Group.objects.get_or_create(name="DAT")
    coordenador, _ = Group.objects.get_or_create(name="Coordenador")
    formador, _ = Group.objects.get_or_create(name="Formador")
    return {
        "controle": controle,
        "dat": dat,
        "coordenador": coordenador,
        "formador": formador,
    }


@pytest.fixture
def user_controle(db, grupos):
    """User with Controle permission."""
    user = Usuario.objects.create_user(
        username="controle1", email="controle1@example.com", password="testpass123", cpf="12345678901"
    )
    user.groups.add(grupos["controle"])
    return user


@pytest.fixture
def user_dat(db, grupos):
    """User with DAT permission."""
    user = Usuario.objects.create_user(
        username="dat1", email="dat1@example.com", password="testpass123", cpf="98765432109"
    )
    user.groups.add(grupos["dat"])
    return user


@pytest.fixture
def user_formador(db, grupos):
    """User with Formador permission (no access to Deslocamentos)."""
    user = Usuario.objects.create_user(
        username="formador1",
        email="formador1@example.com",
        password="testpass123",
        first_name="João",
        last_name="Silva",
        cpf="11122233344",
    )
    user.groups.add(grupos["formador"])
    return user


@pytest.fixture
def deslocamento_sample(db, user_formador):
    """Sample Deslocamento for testing."""
    return Deslocamento.objects.create(
        usuario=user_formador,
        origem="Fortaleza",
        destino="Sobral",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=1),
        observacao="Viagem de formação",
    )


@pytest.mark.django_db
class TestDeslocamentoAPI:
    """
    Tests for Deslocamento CRUD API (Issue #188).
    """

    def test_deslocamento_list(self, user_controle, user_formador):
        """
        Test: List deslocamentos with filters.

        Filters:
        - usuario_id
        - data_inicio (start_date >= value)
        - data_fim (end_date <= value)
        - origem (case-insensitive partial match)
        - destino (case-insensitive partial match)

        Ordering:
        - Default: -start_date (most recent first)
        """
        # Create test data
        Deslocamento.objects.create(
            usuario=user_formador,
            origem="Fortaleza",
            destino="Sobral",
            start_date=date(2025, 1, 10),
            end_date=date(2025, 1, 12),
        )
        Deslocamento.objects.create(
            usuario=user_formador,
            origem="Sobral",
            destino="Fortaleza",
            start_date=date(2025, 1, 15),
            end_date=date(2025, 1, 17),
        )
        Deslocamento.objects.create(
            usuario=user_controle,
            origem="Fortaleza",
            destino="Juazeiro do Norte",
            start_date=date(2025, 1, 20),
            end_date=date(2025, 1, 22),
        )

        client = APIClient()
        client.force_authenticate(user=user_controle)

        # Test 1: List all
        response = client.get("/api/deslocamentos/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 3

        # Test 2: Filter by usuario_id
        response = client.get(f"/api/deslocamentos/?usuario_id={user_formador.id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2

        # Test 3: Filter by data_inicio (start_date >= 2025-01-15)
        response = client.get("/api/deslocamentos/?data_inicio=2025-01-15")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2  # 2025-01-15 and 2025-01-20

        # Test 4: Filter by data_fim (end_date <= 2025-01-17)
        response = client.get("/api/deslocamentos/?data_fim=2025-01-17")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2  # 2025-01-12 and 2025-01-17

        # Test 5: Filter by origem (case-insensitive partial match)
        response = client.get("/api/deslocamentos/?origem=Sobral")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1

        # Test 6: Filter by destino (case-insensitive partial match)
        response = client.get("/api/deslocamentos/?destino=fortaleza")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1

        # Test 7: Ordering (default: -start_date)
        response = client.get("/api/deslocamentos/")
        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert results[0]["start_date"] == "2025-01-20"  # Most recent first

    def test_deslocamento_create(self, user_controle, user_formador):
        """
        Test: Create deslocamento with validation.

        Validation:
        - start_date < end_date
        - origem != destino

        AuditLog:
        - action: CREATE_DESLOCAMENTO
        - details: deslocamento_id, usuario_id, origem, destino, start_date, end_date
        """
        client = APIClient()
        client.force_authenticate(user=user_controle)

        # Test 1: Valid creation
        payload = {
            "usuario": user_formador.id,
            "origem": "Fortaleza",
            "destino": "Sobral",
            "start_date": "2025-02-10",
            "end_date": "2025-02-12",
            "observacao": "Viagem de formação",
        }
        response = client.post("/api/deslocamentos/", payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["origem"] == "Fortaleza"
        assert response.data["destino"] == "Sobral"
        assert response.data["usuario_nome"] == "João Silva"

        # Test 2: AuditLog created
        deslocamento_id = response.data["id"]
        audit_log = AuditLog.objects.filter(
            action="CREATE_DESLOCAMENTO", details__deslocamento_id=deslocamento_id
        ).first()
        assert audit_log is not None
        assert audit_log.usuario == user_controle
        assert audit_log.details["origem"] == "Fortaleza"

    def test_deslocamento_update(self, user_controle, deslocamento_sample):
        """
        Test: Update deslocamento and AuditLog.

        AuditLog:
        - action: UPDATE_DESLOCAMENTO
        - details: deslocamento_id, changed_fields, prev_values, new_values
        """
        client = APIClient()
        client.force_authenticate(user=user_controle)

        # Update destino
        payload = {"destino": "Juazeiro do Norte"}
        response = client.patch(f"/api/deslocamentos/{deslocamento_sample.id}/", payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["destino"] == "Juazeiro do Norte"

        # Check AuditLog
        audit_log = AuditLog.objects.filter(
            action="UPDATE_DESLOCAMENTO", details__deslocamento_id=deslocamento_sample.id
        ).first()
        assert audit_log is not None
        assert audit_log.usuario == user_controle
        assert "destino" in audit_log.details["changed_fields"]
        assert audit_log.details["prev_values"]["destino"] == "Sobral"
        assert audit_log.details["new_values"]["destino"] == "Juazeiro do Norte"

    def test_deslocamento_delete(self, user_controle, deslocamento_sample):
        """
        Test: Delete deslocamento and AuditLog.

        AuditLog:
        - action: DELETE_DESLOCAMENTO
        - details: deslocamento_id, usuario_id, origem, destino, start_date, end_date
        """
        client = APIClient()
        client.force_authenticate(user=user_controle)

        deslocamento_id = deslocamento_sample.id

        # Delete
        response = client.delete(f"/api/deslocamentos/{deslocamento_id}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Check deleted
        assert not Deslocamento.objects.filter(id=deslocamento_id).exists()

        # Check AuditLog
        audit_log = AuditLog.objects.filter(
            action="DELETE_DESLOCAMENTO", details__deslocamento_id=deslocamento_id
        ).first()
        assert audit_log is not None
        assert audit_log.usuario == user_controle
        assert audit_log.details["origem"] == "Fortaleza"
        assert audit_log.details["destino"] == "Sobral"

    def test_deslocamento_validation(self, user_controle, user_formador):
        """
        Test: Validation errors.

        Validation errors:
        - end_date <= start_date → "Data fim deve ser posterior à data início"
        - origem == destino → "Origem e destino devem ser diferentes"
        """
        client = APIClient()
        client.force_authenticate(user=user_controle)

        # Test 1: end_date <= start_date
        payload = {
            "usuario": user_formador.id,
            "origem": "Fortaleza",
            "destino": "Sobral",
            "start_date": "2025-02-12",
            "end_date": "2025-02-10",  # Before start_date
        }
        response = client.post("/api/deslocamentos/", payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        errors = get_field_errors(response)
        assert "end_date" in errors
        assert "Data fim deve ser posterior à data início" in str(errors["end_date"])

        # Test 2: origem == destino
        payload = {
            "usuario": user_formador.id,
            "origem": "Fortaleza",
            "destino": "fortaleza",  # Same as origem (case-insensitive)
            "start_date": "2025-02-10",
            "end_date": "2025-02-12",
        }
        response = client.post("/api/deslocamentos/", payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        errors = get_field_errors(response)
        assert "destino" in errors
        assert "Origem e destino devem ser diferentes" in str(errors["destino"])

    def test_deslocamento_rbac(self, user_formador, user_controle, user_dat, deslocamento_sample):
        """
        Test: RBAC - Acesso baseado em `view_all_availability` (Issue #1221 Epic 1).

        Após Issue 1.3, /deslocamentos usa `HasPerm("view_all_availability")`:
        - Formador: 403 (não tem perm por design)
        - Controle: 200 (tem `view_all_availability` via seed)
        - DAT: 403 (DAT não gerencia disponibilidade — não tem a perm)

        Na Issue 1.4 (seed realign), Gerente/Coordenador/Apoio Coord também
        ganharão `view_all_availability` → testes adicionais para cobrir esses
        papéis serão criados em Issue 1.4.
        """
        # Onda 1 C2 (PR fix/rbac-critical-divergences-wave1, 2026-04-27):
        # Permission_classes virou `[IsAuthenticated]` + scope filter por
        # gerência via EquipeGerencia. Comportamento esperado:
        # - Anonymous → 401/403
        # - Autenticado SEM EquipeGerencia → 200 + lista vazia (fail-safe)
        # - Autenticado COM EquipeGerencia + sem capability → 200 + scope
        # - Capability `view_all_availability` (Controle/Gerente) → 200 + tudo
        # Cobertura granular do scope em test_deslocamento_rbac.py (Onda 1 C2).
        client = APIClient()

        # Formador autenticado sem EquipeGerencia → 200 + 0 deslocamentos
        # (antes: 403; bloqueio agora vira fail-safe via scope filter)
        client.force_authenticate(user=user_formador)
        response = client.get("/api/deslocamentos/")
        assert response.status_code == status.HTTP_200_OK
        results = response.json().get("results", response.json())
        assert results == []

        # Controle → 200 + tudo (capability view_all_availability libera)
        client.force_authenticate(user=user_controle)
        response = client.get("/api/deslocamentos/")
        assert response.status_code == status.HTTP_200_OK

        # D9 (2026-04-28, PR 2 RBAC hardening): DAT recebe `view_all_availability`
        # global no seed 0080 (papel transversal admin). Mesma cap libera bypass
        # de scope em views_deslocamento.py — DAT passa a ver todos os
        # deslocamentos como Controle.
        client.force_authenticate(user=user_dat)
        response = client.get("/api/deslocamentos/")
        assert response.status_code == status.HTTP_200_OK
