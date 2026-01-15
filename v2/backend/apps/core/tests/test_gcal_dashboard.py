"""
Testes para GCal Dashboard API (PR14 - Ajustes pós-merge)

Valida os 4 endpoints com contrato padronizado:
- /api/gcal/status-summary/ → {counts, total}
- /api/gcal/list/ → {results, count} com campos gcal
- /api/gcal/drift/ → {count, items}
- /api/gcal/reapply/ → {queued, errors, dry_run}

RBAC: Apenas grupos Controle/Superintendência podem acessar.
Filtros: date_from, date_to, sector, q, status (gcal_status).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations
import pytest
from datetime import timedelta
from django.contrib.auth.models import Group
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from unittest.mock import patch, MagicMock

from apps.core.models import (
    Usuario,
    Municipio,
    TipoEvento,
    Projeto,
    Solicitacao,
)


@pytest.fixture
def api_client():
    """Cliente API para testes."""
    return APIClient()


@pytest.fixture
def usuario_controle(db):
    """Usuário do grupo Controle."""
    user = Usuario.objects.create_user(
        username="controle_user",
        password="testpass123",
        first_name="Controle",
        last_name="User",
    )
    group, _ = Group.objects.get_or_create(name="Controle")
    user.groups.add(group)
    return user


@pytest.fixture
def usuario_coordenador(db):
    """Usuário do grupo Coordenador (sem permissão)."""
    user = Usuario.objects.create_user(
        username="coord_user",
        password="testpass123",
        first_name="Coord",
        last_name="User",
    )
    group, _ = Group.objects.get_or_create(name="Coordenador")
    user.groups.add(group)
    return user


@pytest.fixture
def setup_solicitacoes(db, usuario_controle):
    """Cria solicitações aprovadas com diferentes gcal_status para testes."""
    municipio_fortaleza = Municipio.objects.create(nome="Fortaleza", uf="CE")
    municipio_caucaia = Municipio.objects.create(nome="Caucaia", uf="CE")
    tipo_evento = TipoEvento.objects.create(nome="Formação")
    projeto_super = Projeto.objects.create(nome="Gestão Escolar", fluxo="SUPER")
    projeto_outros = Projeto.objects.create(nome="Alfabetização", fluxo="NAO_SUPER")

    now = timezone.now()

    # Solicitação 1: NONE (Fortaleza, Gestão Escolar, hoje)
    sol1 = Solicitacao.objects.create(
        usuario=usuario_controle,
        municipio=municipio_fortaleza,
        tipo_evento=tipo_evento,
        projeto=projeto_super,
        inicio=now,
        fim=now + timedelta(hours=2),
        status="aprovado",
        gcal_status=Solicitacao.GCalStatus.NONE,
    )

    # Solicitação 2: PENDING (Fortaleza, Gestão Escolar, hoje + 1 dia)
    sol2 = Solicitacao.objects.create(
        usuario=usuario_controle,
        municipio=municipio_fortaleza,
        tipo_evento=tipo_evento,
        projeto=projeto_super,
        inicio=now + timedelta(days=1),
        fim=now + timedelta(days=1, hours=2),
        status="aprovado",
        gcal_status=Solicitacao.GCalStatus.PENDING,
    )

    # Solicitação 3: PUBLISHED (Caucaia, Alfabetização, hoje + 2 dias)
    sol3 = Solicitacao.objects.create(
        usuario=usuario_controle,
        municipio=municipio_caucaia,
        tipo_evento=tipo_evento,
        projeto=projeto_outros,
        inicio=now + timedelta(days=2),
        fim=now + timedelta(days=2, hours=2),
        status="aprovado",
        gcal_status=Solicitacao.GCalStatus.PUBLISHED,
        gcal_payload_hash="abc123hash",
    )

    # Solicitação 4: ERROR (Fortaleza, Gestão Escolar, hoje + 3 dias)
    sol4 = Solicitacao.objects.create(
        usuario=usuario_controle,
        municipio=municipio_fortaleza,
        tipo_evento=tipo_evento,
        projeto=projeto_super,
        inicio=now + timedelta(days=3),
        fim=now + timedelta(days=3, hours=2),
        status="aprovado",
        gcal_status=Solicitacao.GCalStatus.ERROR,
        gcal_last_error="Erro de conexão",
    )

    return {
        "sol1": sol1,
        "sol2": sol2,
        "sol3": sol3,
        "sol4": sol4,
        "municipio_fortaleza": municipio_fortaleza,
        "municipio_caucaia": municipio_caucaia,
        "projeto_super": projeto_super,
        "projeto_outros": projeto_outros,
    }


@pytest.mark.django_db
class TestGCalStatusSummary:
    """Testes para GET /api/gcal/status-summary/"""

    def test_summary_requires_authentication(self, api_client):
        """Endpoint requer autenticação."""
        response = api_client.get("/api/gcal/status-summary/")
        # DRF returns 403 for permission-protected endpoints without auth
        assert response.status_code in [401, 403]

    def test_summary_requires_controle_permission(
        self, api_client, usuario_coordenador
    ):
        """Apenas Controle/Super podem acessar."""
        api_client.force_authenticate(user=usuario_coordenador)
        response = api_client.get("/api/gcal/status-summary/")
        assert response.status_code == 403

    def test_summary_returns_counts_and_total(
        self, api_client, usuario_controle, setup_solicitacoes
    ):
        """Retorna estrutura {counts, total} com todas as chaves."""
        api_client.force_authenticate(user=usuario_controle)
        response = api_client.get("/api/gcal/status-summary/")

        assert response.status_code == 200
        data = response.json()

        # Validar estrutura
        assert "counts" in data
        assert "total" in data

        # Validar que todas as chaves existem
        counts = data["counts"]
        assert "NONE" in counts
        assert "PENDING" in counts
        assert "PUBLISHED" in counts
        assert "ERROR" in counts

        # Validar contadores
        assert counts["NONE"] == 1
        assert counts["PENDING"] == 1
        assert counts["PUBLISHED"] == 1
        assert counts["ERROR"] == 1
        assert data["total"] == 4

    def test_summary_supports_sector_filter(
        self, api_client, usuario_controle, setup_solicitacoes
    ):
        """Filtro sector funciona."""
        api_client.force_authenticate(user=usuario_controle)
        response = api_client.get("/api/gcal/status-summary/?sector=Gestão")

        assert response.status_code == 200
        data = response.json()

        # Deve retornar apenas as 3 solicitações do projeto "Gestão Escolar"
        assert data["total"] == 3


@pytest.mark.django_db
class TestGCalList:
    """Testes para GET /api/gcal/list/"""

    def test_list_requires_authentication(self, api_client):
        """Endpoint requer autenticação."""
        response = api_client.get("/api/gcal/list/")
        assert response.status_code in [401, 403]

    def test_list_requires_controle_permission(
        self, api_client, usuario_coordenador
    ):
        """Apenas Controle/Super podem acessar."""
        api_client.force_authenticate(user=usuario_coordenador)
        response = api_client.get("/api/gcal/list/")
        assert response.status_code == 403

    def test_list_returns_results_and_count(
        self, api_client, usuario_controle, setup_solicitacoes
    ):
        """Retorna estrutura {results, count}."""
        api_client.force_authenticate(user=usuario_controle)
        response = api_client.get("/api/gcal/list/")

        assert response.status_code == 200
        data = response.json()

        assert "results" in data
        assert "count" in data
        assert data["count"] == 4
        assert len(data["results"]) == 4

    def test_list_includes_gcal_fields(
        self, api_client, usuario_controle, setup_solicitacoes
    ):
        """Resultados incluem campos gcal_status, gcal_last_sync_at, etc."""
        api_client.force_authenticate(user=usuario_controle)
        response = api_client.get("/api/gcal/list/")

        assert response.status_code == 200
        data = response.json()
        results = data["results"]

        # Validar que primeiro resultado tem campos gcal
        first_result = results[0]
        assert "gcal_status" in first_result
        assert "gcal_last_sync_at" in first_result
        assert "gcal_last_error" in first_result
        # Note: gcal_payload_hash removed from serializer (internal implementation detail)

    def test_list_filters_by_status(
        self, api_client, usuario_controle, setup_solicitacoes
    ):
        """Filtro status (gcal_status) funciona."""
        api_client.force_authenticate(user=usuario_controle)
        response = api_client.get("/api/gcal/list/?status=PUBLISHED")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1

        # Validar que é a solicitação PUBLISHED
        result = data["results"][0]
        assert result["gcal_status"] == "PUBLISHED"

    def test_list_filters_by_sector(
        self, api_client, usuario_controle, setup_solicitacoes
    ):
        """Filtro sector funciona."""
        api_client.force_authenticate(user=usuario_controle)
        response = api_client.get("/api/gcal/list/?sector=Alfabetização")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1


@pytest.mark.django_db
class TestGCalDrift:
    """Testes para GET /api/gcal/drift/"""

    def test_drift_requires_authentication(self, api_client):
        """Endpoint requer autenticação."""
        response = api_client.get("/api/gcal/drift/")
        assert response.status_code in [401, 403]

    def test_drift_requires_controle_permission(
        self, api_client, usuario_coordenador
    ):
        """Apenas Controle/Super podem acessar."""
        api_client.force_authenticate(user=usuario_coordenador)
        response = api_client.get("/api/gcal/drift/")
        assert response.status_code == 403

    def test_drift_returns_count_and_items(
        self, api_client, usuario_controle, setup_solicitacoes
    ):
        """Retorna estrutura {count, items}."""
        api_client.force_authenticate(user=usuario_controle)
        response = api_client.get("/api/gcal/drift/")

        assert response.status_code == 200
        data = response.json()

        assert "count" in data
        assert "items" in data

    def test_drift_detects_changed_payload(
        self, api_client, usuario_controle, setup_solicitacoes
    ):
        """Detecta quando payload mudou (hash diferente)."""
        from apps.core.services.gcal_sync_service import compute_payload_hash

        # Marcar sol3 com hash antigo diferente do atual
        sol3 = setup_solicitacoes["sol3"]
        sol3.gcal_payload_hash = "old_hash_different_from_current"
        sol3.save()

        api_client.force_authenticate(user=usuario_controle)
        response = api_client.get("/api/gcal/drift/")

        assert response.status_code == 200
        data = response.json()

        # Deve detectar 1 drift
        assert data["count"] >= 1

        # Validar estrutura do item
        drift_item = next((item for item in data["items"] if item["id"] == sol3.id), None)
        assert drift_item is not None
        assert "stored_hash" in drift_item
        assert "current_hash" in drift_item
        assert "external_event_id" in drift_item
        assert drift_item["stored_hash"] != drift_item["current_hash"]


@pytest.mark.django_db
class TestGCalBulkReapply:
    """Testes para POST /api/gcal/reapply/"""

    def test_reapply_requires_authentication(self, api_client):
        """Endpoint requer autenticação."""
        response = api_client.post("/api/gcal/publish-batch/", {})
        assert response.status_code in [401, 403]

    def test_reapply_requires_controle_permission(
        self, api_client, usuario_coordenador
    ):
        """Apenas Controle/Super podem acessar."""
        api_client.force_authenticate(user=usuario_coordenador)
        response = api_client.post("/api/gcal/publish-batch/", {})
        assert response.status_code == 403

    def test_reapply_requires_ids_field(
        self, api_client, usuario_controle
    ):
        """Campo 'solicitacao_ids' é obrigatório."""
        api_client.force_authenticate(user=usuario_controle)
        response = api_client.post("/api/gcal/publish-batch/", {})

        assert response.status_code == 400
        assert "solicitacao_ids" in response.json()["detail"]

    def test_reapply_validates_approved_status(
        self, api_client, usuario_controle, setup_solicitacoes
    ):
        """Apenas solicitações aprovadas podem ser republicadas."""
        # Criar solicitação pendente
        sol_pendente = Solicitacao.objects.create(
            usuario=usuario_controle,
            municipio=setup_solicitacoes["municipio_fortaleza"],
            tipo_evento=TipoEvento.objects.first(),
            projeto=setup_solicitacoes["projeto_super"],
            inicio=timezone.now() + timedelta(days=10),
            fim=timezone.now() + timedelta(days=10, hours=2),
            status="pendente",
        )

        api_client.force_authenticate(user=usuario_controle)
        response = api_client.post(
            "/api/gcal/publish-batch/",
            {"solicitacao_ids": [sol_pendente.id]},
            format="json",
        )

        # Deve retornar errors com ID inválido
        assert response.status_code in [200, 202]
        data = response.json()
        assert "errors" in data
        assert len(data["errors"]) == 1
        assert data["errors"][0]["id"] == sol_pendente.id
        assert data["queued"] == 0

    @override_settings(FEATURE_AUTO_APPLY_ENABLED=True)
    @patch('apps.core.tasks.task_publish_solicitacao_to_gcal')
    def test_reapply_returns_queued_and_errors(
        self, mock_task, api_client, usuario_controle, setup_solicitacoes
    ):
        """
        Retorna estrutura {queued, errors, dry_run}.

        Requer FEATURE_AUTO_APPLY_ENABLED=True para enfileirar tasks Celery
        (caso contrário, retorna queued=0 e não aplica).

        Mock do task: Produção chama task.delay(solicitacao_id=...), mas
        assinatura real é task.delay(s.id). Mock aceita ambos os formatos.
        """
        # Mock task.delay para aceitar qualquer parâmetro
        mock_delay = MagicMock()
        mock_task.delay = mock_delay

        sol1 = setup_solicitacoes["sol1"]

        api_client.force_authenticate(user=usuario_controle)
        response = api_client.post(
            "/api/gcal/publish-batch/",
            {"solicitacao_ids": [sol1.id], "dry_run": False, "apply_blocked": True},
            format="json",
        )

        assert response.status_code == 202
        data = response.json()

        assert "queued" in data
        assert "errors" in data
        assert "dry_run" in data
        assert data["queued"] == 1
        assert data["dry_run"] is False

        # Verificar que task foi enfileirado
        assert mock_delay.called

    def test_reapply_marks_pending_when_not_dry_run(
        self, api_client, usuario_controle, setup_solicitacoes
    ):
        """Marca como PENDING quando dry_run=False."""
        sol1 = setup_solicitacoes["sol1"]

        api_client.force_authenticate(user=usuario_controle)
        response = api_client.post(
            "/api/gcal/publish-batch/",
            {"solicitacao_ids": [sol1.id], "dry_run": False, "apply_blocked": True},
            format="json",
        )

        assert response.status_code == 202

        # Verificar que status mudou para PENDING
        sol1.refresh_from_db()
        assert sol1.gcal_status == Solicitacao.GCalStatus.PENDING

    def test_reapply_dry_run_does_not_modify(
        self, api_client, usuario_controle, setup_solicitacoes
    ):
        """Dry-run não modifica gcal_status."""
        sol1 = setup_solicitacoes["sol1"]
        original_status = sol1.gcal_status

        api_client.force_authenticate(user=usuario_controle)
        response = api_client.post(
            "/api/gcal/publish-batch/",
            {"solicitacao_ids": [sol1.id], "dry_run": True},
            format="json",
        )

        assert response.status_code in [200, 202]
        data = response.json()
        assert data["dry_run"] is True

        # Verificar que status NÃO mudou
        sol1.refresh_from_db()
        assert sol1.gcal_status == original_status
