"""
Testes para endpoint POST /api/gcal/publish-batch/ (Fase 2)

Cenários:
- 202 com IDs aprovados → queued=N, errors=[]
- Mistura com pendente → pendente em errors
- apply_blocked exigido quando GCAL_CLIENT != 'google' e dry_run=false
- RBAC: 403 para usuário sem Controle/Super
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false

from __future__ import annotations
import os
from unittest.mock import patch, MagicMock

import pytest
from django.contrib.auth.models import Group
from django.test import override_settings
from rest_framework.test import APIClient

from apps.core.models import Usuario, Solicitacao, Projeto, Municipio, TipoEvento


@pytest.fixture
def api_client():
    """Cliente API para testes."""
    return APIClient()


@pytest.fixture
def grupo_controle(db):
    """Cria grupo Controle."""
    return Group.objects.get_or_create(name='Controle')[0]


@pytest.fixture
def usuario_controle(db, grupo_controle):
    """Cria usuário com grupo Controle."""
    user = Usuario.objects.create_user(
        username='controle_user',
        email='controle@test.com',
        password='testpass123',
        cpf='12345678901'  # CPF único
    )
    user.groups.add(grupo_controle)
    return user


@pytest.fixture
def usuario_comum(db):
    """Cria usuário sem permissões especiais."""
    return Usuario.objects.create_user(
        username='comum_user',
        email='comum@test.com',
        password='testpass123',
        cpf='98765432109'  # CPF único diferente
    )


@pytest.fixture
def projeto(db):
    """Cria projeto de teste."""
    return Projeto.objects.create(
        nome='Projeto Teste',
        codigo='PROJ001',
        fluxo='SUPER'
    )


@pytest.fixture
def municipio(db):
    """Cria município de teste."""
    return Municipio.objects.create(
        nome='Fortaleza',
        uf='CE',
        ibge_code='2304400'
    )


@pytest.fixture
def tipo_evento(db):
    """Cria tipo de evento de teste."""
    return TipoEvento.objects.create(
        nome='Formação'
    )


@pytest.fixture
def solicitacao_aprovada(db, usuario_controle, projeto, municipio, tipo_evento):
    """Cria solicitação aprovada."""
    return Solicitacao.objects.create(
        usuario=usuario_controle,
        projeto=projeto,
        municipio=municipio,
        tipo_evento=tipo_evento,
        inicio='2025-11-15T08:00:00-03:00',
        fim='2025-11-15T12:00:00-03:00',
        status='aprovado',
        gcal_status='NONE'
    )


@pytest.fixture
def solicitacao_pendente(db, usuario_controle, projeto, municipio, tipo_evento):
    """Cria solicitação pendente."""
    return Solicitacao.objects.create(
        usuario=usuario_controle,
        projeto=projeto,
        municipio=municipio,
        tipo_evento=tipo_evento,
        inicio='2025-11-16T08:00:00-03:00',
        fim='2025-11-16T12:00:00-03:00',
        status='pendente',
        gcal_status='NONE'
    )


@pytest.mark.django_db
class TestGCalPublishBatchEndpoint:
    """Testes do endpoint POST /api/gcal/publish-batch/."""

    @patch('apps.core.tasks.task_publish_solicitacao_to_gcal')
    @override_settings(GCAL_CLIENT='google')
    def test_batch_publish_aprovados_sucesso(
        self,
        mock_task,
        api_client,
        usuario_controle,
        solicitacao_aprovada
    ):
        """
        Cenário: 2 IDs aprovados com GCAL_CLIENT=google
        Espera: 202 com queued=2, errors=[]
        """
        # Criar segunda solicitação aprovada
        sol2 = Solicitacao.objects.create(
            usuario=usuario_controle,
            projeto=solicitacao_aprovada.projeto,
            municipio=solicitacao_aprovada.municipio,
            tipo_evento=solicitacao_aprovada.tipo_evento,
            inicio='2025-11-17T08:00:00-03:00',
            fim='2025-11-17T12:00:00-03:00',
            status='aprovado',
            gcal_status='NONE'
        )

        # Mock task
        mock_task.delay = MagicMock()

        # Autenticar
        api_client.force_authenticate(user=usuario_controle)

        # Request
        response = api_client.post(
            '/api/gcal/publish-batch/',
            {
                'solicitacao_ids': [solicitacao_aprovada.id, sol2.id],
                'dry_run': False,
                'apply_blocked': False
            },
            format='json'
        )

        # Asserts
        assert response.status_code == 202
        data = response.json()
        assert data['queued'] == 2
        assert data['errors'] == []
        assert data['dry_run'] is False
        assert data['apply_blocked'] is False

        # Verificar task foi chamada 2x
        assert mock_task.delay.call_count == 2

        # Verificar gcal_status foi atualizado para PENDING
        solicitacao_aprovada.refresh_from_db()
        sol2.refresh_from_db()
        assert solicitacao_aprovada.gcal_status == 'PENDING'
        assert sol2.gcal_status == 'PENDING'

    @patch('apps.core.tasks.task_publish_solicitacao_to_gcal')
    @override_settings(GCAL_CLIENT='google')
    def test_batch_publish_mistura_aprovado_pendente(
        self,
        mock_task,
        api_client,
        usuario_controle,
        solicitacao_aprovada,
        solicitacao_pendente
    ):
        """
        Cenário: 1 aprovado + 1 pendente
        Espera: queued=1, errors=[{id: pendente, detail: "..."}]
        """
        # Mock task
        mock_task.delay = MagicMock()

        # Autenticar
        api_client.force_authenticate(user=usuario_controle)

        # Request
        response = api_client.post(
            '/api/gcal/publish-batch/',
            {
                'solicitacao_ids': [solicitacao_aprovada.id, solicitacao_pendente.id],
                'dry_run': False,
                'apply_blocked': False
            },
            format='json'
        )

        # Asserts
        assert response.status_code == 202
        data = response.json()
        assert data['queued'] == 1
        assert len(data['errors']) == 1

        # Verificar erro do pendente
        error = data['errors'][0]
        assert error['id'] == solicitacao_pendente.id
        assert 'aprovado' in error['detail']
        assert 'pendente' in error['detail']

        # Task chamada apenas 1x (aprovado)
        assert mock_task.delay.call_count == 1

        # Aprovado marcado como PENDING
        solicitacao_aprovada.refresh_from_db()
        assert solicitacao_aprovada.gcal_status == 'PENDING'

        # Pendente não mudou
        solicitacao_pendente.refresh_from_db()
        assert solicitacao_pendente.gcal_status == 'NONE'

    @override_settings(GCAL_CLIENT='fake')
    def test_batch_publish_requer_apply_blocked_quando_fake(
        self,
        api_client,
        usuario_controle,
        solicitacao_aprovada
    ):
        """
        Cenário: GCAL_CLIENT=fake + dry_run=false + apply_blocked=false
        Espera: errors com mensagem sobre apply_blocked
        """
        # Autenticar
        api_client.force_authenticate(user=usuario_controle)

        # Request SEM apply_blocked
        response = api_client.post(
            '/api/gcal/publish-batch/',
            {
                'solicitacao_ids': [solicitacao_aprovada.id],
                'dry_run': False,
                'apply_blocked': False
            },
            format='json'
        )

        # Asserts
        assert response.status_code == 202
        data = response.json()
        assert data['queued'] == 0
        assert len(data['errors']) == 1

        error = data['errors'][0]
        assert error['id'] == solicitacao_aprovada.id
        assert 'GCAL_CLIENT=fake' in error['detail']
        assert 'apply_blocked=true' in error['detail']

    @patch('apps.core.tasks.task_publish_solicitacao_to_gcal')
    @override_settings(GCAL_CLIENT='fake')
    def test_batch_publish_com_apply_blocked_true(
        self,
        mock_task,
        api_client,
        usuario_controle,
        solicitacao_aprovada
    ):
        """
        Cenário: GCAL_CLIENT=fake + apply_blocked=true
        Espera: queued=1 (permite com fake client quando apply_blocked=true)
        """
        # Mock task
        mock_task.delay = MagicMock()

        # Autenticar
        api_client.force_authenticate(user=usuario_controle)

        # Request COM apply_blocked=true
        response = api_client.post(
            '/api/gcal/publish-batch/',
            {
                'solicitacao_ids': [solicitacao_aprovada.id],
                'dry_run': False,
                'apply_blocked': True
            },
            format='json'
        )

        # Asserts
        assert response.status_code == 202
        data = response.json()
        assert data['queued'] == 1
        assert data['errors'] == []
        assert data['apply_blocked'] is True

        # Task chamada
        assert mock_task.delay.call_count == 1

    def test_batch_publish_rbac_403_sem_permissao(
        self,
        api_client,
        usuario_comum,
        solicitacao_aprovada
    ):
        """
        Cenário: Usuário sem grupo Controle/Super
        Espera: 403 Forbidden
        """
        # Autenticar com usuário comum
        api_client.force_authenticate(user=usuario_comum)

        # Request
        response = api_client.post(
            '/api/gcal/publish-batch/',
            {
                'solicitacao_ids': [solicitacao_aprovada.id],
                'dry_run': False,
                'apply_blocked': False
            },
            format='json'
        )

        # Assert: 403 Forbidden
        assert response.status_code == 403

    def test_batch_publish_array_vazio(
        self,
        api_client,
        usuario_controle
    ):
        """
        Cenário: solicitacao_ids vazio
        Espera: 400 Bad Request
        """
        # Autenticar
        api_client.force_authenticate(user=usuario_controle)

        # Request com array vazio
        response = api_client.post(
            '/api/gcal/publish-batch/',
            {
                'solicitacao_ids': [],
                'dry_run': False
            },
            format='json'
        )

        # Assert: 400
        assert response.status_code == 400
        assert 'não-vazio' in response.json()['detail']

    @patch('apps.core.tasks.task_publish_solicitacao_to_gcal')
    @override_settings(GCAL_CLIENT='google')
    def test_batch_publish_dry_run_nao_persiste(
        self,
        mock_task,
        api_client,
        usuario_controle,
        solicitacao_aprovada
    ):
        """
        Cenário: dry_run=true
        Espera: queued=1 mas gcal_status NÃO muda e task NÃO é chamada
        """
        # Mock task
        mock_task.delay = MagicMock()

        # Autenticar
        api_client.force_authenticate(user=usuario_controle)

        # Request com dry_run=true
        response = api_client.post(
            '/api/gcal/publish-batch/',
            {
                'solicitacao_ids': [solicitacao_aprovada.id],
                'dry_run': True,
                'apply_blocked': False
            },
            format='json'
        )

        # Asserts
        assert response.status_code == 202
        data = response.json()
        assert data['queued'] == 1
        assert data['dry_run'] is True

        # Task NÃO foi chamada
        mock_task.delay.assert_not_called()

        # gcal_status NÃO mudou
        solicitacao_aprovada.refresh_from_db()
        assert solicitacao_aprovada.gcal_status == 'NONE'

    def test_batch_publish_id_inexistente(
        self,
        api_client,
        usuario_controle
    ):
        """
        Cenário: ID que não existe
        Espera: errors com "não encontrada"
        """
        # Autenticar
        api_client.force_authenticate(user=usuario_controle)

        # Request com ID inexistente
        response = api_client.post(
            '/api/gcal/publish-batch/',
            {
                'solicitacao_ids': [99999],
                'dry_run': False,
                'apply_blocked': False
            },
            format='json'
        )

        # Asserts
        assert response.status_code == 202
        data = response.json()
        assert data['queued'] == 0
        assert len(data['errors']) == 1

        error = data['errors'][0]
        assert error['id'] == 99999
        assert 'não encontrada' in error['detail']
