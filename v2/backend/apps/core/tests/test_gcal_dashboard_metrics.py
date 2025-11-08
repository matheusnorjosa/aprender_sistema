"""
Testes Sprint 5 - Dashboard/Monitoring (Backend)

Cobertura:
- GET /api/gcal/dashboard/metrics/ - métricas + recent_errors com filtros start/end
- GET /api/gcal/dashboard/events/ - lista paginada com filtros status/start/end

100% fake/mocked, sem rede real.
"""

import pytest
from datetime import date, timedelta
from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status as http_status

from apps.core.models import Usuario, Solicitacao, Municipio, Projeto, TipoEvento


@pytest.fixture
def usuario_controle():
    """Usuário do grupo Controle"""
    user = Usuario.objects.create_user(
        username="controle_sprint5",
        email="controle_sprint5@test.com",
        password="testpass",
        cpf="11111111111",
    )
    grupo, _ = Group.objects.get_or_create(name="Controle")
    user.groups.add(grupo)
    return user


@pytest.fixture
def municipio():
    """Município de teste"""
    return Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)


@pytest.fixture
def projeto():
    """Projeto de teste"""
    return Projeto.objects.create(nome="Projeto Sprint5", codigo="SP5", fluxo="SUPER", ativo=True)


@pytest.fixture
def tipo_evento():
    """Tipo de evento de teste"""
    return TipoEvento.objects.create(nome="Formação Sprint5")


def create_solicitacao(usuario, municipio, projeto, tipo_evento, gcal_status, data_offset_days, gcal_last_error=""):
    """Helper para criar solicitação com status e data específicos"""
    now = timezone.now()
    inicio = now + timedelta(days=data_offset_days)
    fim = inicio + timedelta(hours=3)

    sol = Solicitacao.objects.create(
        usuario=usuario,
        municipio=municipio,
        projeto=projeto,
        tipo_evento=tipo_evento,
        tipo="evento",
        inicio=inicio,
        fim=fim,
        status="aprovado",
        gcal_status=gcal_status,
    )

    # Setar erro se fornecido
    if gcal_last_error:
        sol.gcal_last_error = gcal_last_error
        sol.save(update_fields=['gcal_last_error'])

    return sol


@pytest.mark.django_db
class TestDashboardMetrics:
    """Testes para GET /api/gcal/dashboard/metrics/"""

    def test_metrics_counts_all_statuses(self, usuario_controle, municipio, projeto, tipo_evento):
        """
        Caso 1: Metrics deve retornar counts para NONE/PENDING/PUBLISHED/ERROR
        """
        # Criar solicitações com diferentes status
        create_solicitacao(usuario_controle, municipio, projeto, tipo_evento, Solicitacao.GCalStatus.NONE, 1)
        create_solicitacao(usuario_controle, municipio, projeto, tipo_evento, Solicitacao.GCalStatus.NONE, 2)
        create_solicitacao(usuario_controle, municipio, projeto, tipo_evento, Solicitacao.GCalStatus.PENDING, 3)
        create_solicitacao(usuario_controle, municipio, projeto, tipo_evento, Solicitacao.GCalStatus.PUBLISHED, 4)
        create_solicitacao(usuario_controle, municipio, projeto, tipo_evento, Solicitacao.GCalStatus.PUBLISHED, 5)
        create_solicitacao(usuario_controle, municipio, projeto, tipo_evento, Solicitacao.GCalStatus.PUBLISHED, 6)
        create_solicitacao(usuario_controle, municipio, projeto, tipo_evento, Solicitacao.GCalStatus.ERROR, 7, "Erro teste")

        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        response = client.get("/api/gcal/dashboard/metrics/")

        assert response.status_code == http_status.HTTP_200_OK
        data = response.data

        # Validar estrutura
        assert 'counts' in data
        assert 'recent_errors' in data
        assert 'window' in data

        # Validar counts
        counts = data['counts']
        assert counts['NONE'] == 2
        assert counts['PENDING'] == 1
        assert counts['PUBLISHED'] == 3
        assert counts['ERROR'] == 1

    def test_metrics_recent_errors_top_5(self, usuario_controle, municipio, projeto, tipo_evento):
        """
        Caso 2: recent_errors deve retornar top 5 erros ordenados por updated_at desc
        """
        # Criar 7 solicitações com erro (deve retornar apenas 5 mais recentes)
        for i in range(7):
            create_solicitacao(
                usuario_controle, municipio, projeto, tipo_evento,
                Solicitacao.GCalStatus.ERROR, i, f"Erro {i}"
            )

        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        response = client.get("/api/gcal/dashboard/metrics/")

        assert response.status_code == http_status.HTTP_200_OK
        recent_errors = response.data['recent_errors']

        # Deve retornar apenas 5
        assert len(recent_errors) == 5

        # Validar estrutura de cada erro
        for error in recent_errors:
            assert 'id' in error
            assert 'summary' in error
            assert 'gcal_last_error' in error
            assert 'updated_at' in error

    def test_metrics_window_filter_start_end(self, usuario_controle, municipio, projeto, tipo_evento):
        """
        Caso 3: Filtros start/end devem filtrar por data do evento
        """
        today = date.today()

        # Dentro da janela
        create_solicitacao(usuario_controle, municipio, projeto, tipo_evento, Solicitacao.GCalStatus.NONE, 5)
        create_solicitacao(usuario_controle, municipio, projeto, tipo_evento, Solicitacao.GCalStatus.PUBLISHED, 10)

        # Fora da janela (antes)
        create_solicitacao(usuario_controle, municipio, projeto, tipo_evento, Solicitacao.GCalStatus.NONE, -10)

        # Fora da janela (depois)
        create_solicitacao(usuario_controle, municipio, projeto, tipo_evento, Solicitacao.GCalStatus.PUBLISHED, 50)

        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        start = (today + timedelta(days=1)).isoformat()
        end = (today + timedelta(days=15)).isoformat()

        response = client.get(f"/api/gcal/dashboard/metrics/?start={start}&end={end}")

        assert response.status_code == http_status.HTTP_200_OK
        data = response.data

        # Apenas 2 eventos dentro da janela
        total = sum(data['counts'].values())
        assert total == 2

        # Validar window retornado
        assert data['window']['start'] == start
        assert data['window']['end'] == end

    def test_metrics_requires_authentication(self, usuario_controle, municipio, projeto, tipo_evento):
        """
        Caso 4: Endpoint exige autenticação

        Nota: DRF retorna 403 (Forbidden) quando permission classes são checadas
        antes de autenticação. Ambos 401 e 403 indicam acesso negado corretamente.
        """
        client = APIClient()

        response = client.get("/api/gcal/dashboard/metrics/")

        # DRF pode retornar 403 ao invés de 401 com IsControleOrSuper + IsAuthenticated
        assert response.status_code in [http_status.HTTP_401_UNAUTHORIZED, http_status.HTTP_403_FORBIDDEN]

    def test_metrics_requires_controle_or_super(self, municipio, projeto, tipo_evento):
        """
        Caso 5: Endpoint exige permissão Controle ou Superintendência
        """
        # Usuário sem grupo Controle/Super
        user = Usuario.objects.create_user(
            username="coordenador_sprint5",
            email="coordenador@test.com",
            password="testpass",
            cpf="22222222222",
        )
        grupo_coord, _ = Group.objects.get_or_create(name="Coordenador")
        user.groups.add(grupo_coord)

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get("/api/gcal/dashboard/metrics/")

        assert response.status_code == http_status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestDashboardEvents:
    """Testes para GET /api/gcal/dashboard/events/"""

    def test_events_pagination_default(self, usuario_controle, municipio, projeto, tipo_evento):
        """
        Caso 1: Paginação padrão (20 itens por página)
        """
        # Criar 25 solicitações
        for i in range(25):
            create_solicitacao(usuario_controle, municipio, projeto, tipo_evento, Solicitacao.GCalStatus.PUBLISHED, i)

        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        response = client.get("/api/gcal/dashboard/events/")

        assert response.status_code == http_status.HTTP_200_OK
        data = response.data

        # Estrutura paginada
        assert 'count' in data
        assert 'next' in data
        assert 'previous' in data
        assert 'results' in data

        # Deve retornar 20 itens (página 1)
        assert len(data['results']) == 20
        assert data['count'] == 25
        assert data['next'] is not None
        assert data['previous'] is None

    def test_events_pagination_custom_page_size(self, usuario_controle, municipio, projeto, tipo_evento):
        """
        Caso 2: page_size customizado
        """
        # Criar 15 solicitações
        for i in range(15):
            create_solicitacao(usuario_controle, municipio, projeto, tipo_evento, Solicitacao.GCalStatus.PUBLISHED, i)

        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        response = client.get("/api/gcal/dashboard/events/?page_size=5")

        assert response.status_code == http_status.HTTP_200_OK
        data = response.data

        # Deve retornar 5 itens
        assert len(data['results']) == 5
        assert data['count'] == 15
        assert data['next'] is not None

    def test_events_filter_by_status(self, usuario_controle, municipio, projeto, tipo_evento):
        """
        Caso 3: Filtro por gcal_status
        """
        create_solicitacao(usuario_controle, municipio, projeto, tipo_evento, Solicitacao.GCalStatus.NONE, 1)
        create_solicitacao(usuario_controle, municipio, projeto, tipo_evento, Solicitacao.GCalStatus.NONE, 2)
        create_solicitacao(usuario_controle, municipio, projeto, tipo_evento, Solicitacao.GCalStatus.PUBLISHED, 3)
        create_solicitacao(usuario_controle, municipio, projeto, tipo_evento, Solicitacao.GCalStatus.ERROR, 4, "Erro")

        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        # Filtrar apenas NONE
        response = client.get("/api/gcal/dashboard/events/?status=NONE")

        assert response.status_code == http_status.HTTP_200_OK
        assert len(response.data['results']) == 2

        # Filtrar apenas ERROR
        response = client.get("/api/gcal/dashboard/events/?status=ERROR")

        assert response.status_code == http_status.HTTP_200_OK
        assert len(response.data['results']) == 1

    def test_events_filter_by_date_window(self, usuario_controle, municipio, projeto, tipo_evento):
        """
        Caso 4: Filtro por janela de datas (start/end)
        """
        today = date.today()

        # Dentro da janela
        create_solicitacao(usuario_controle, municipio, projeto, tipo_evento, Solicitacao.GCalStatus.PUBLISHED, 5)
        create_solicitacao(usuario_controle, municipio, projeto, tipo_evento, Solicitacao.GCalStatus.PUBLISHED, 10)

        # Fora da janela
        create_solicitacao(usuario_controle, municipio, projeto, tipo_evento, Solicitacao.GCalStatus.PUBLISHED, -10)
        create_solicitacao(usuario_controle, municipio, projeto, tipo_evento, Solicitacao.GCalStatus.PUBLISHED, 50)

        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        start = (today + timedelta(days=1)).isoformat()
        end = (today + timedelta(days=15)).isoformat()

        response = client.get(f"/api/gcal/dashboard/events/?start={start}&end={end}")

        assert response.status_code == http_status.HTTP_200_OK
        # Apenas 2 eventos dentro da janela
        assert len(response.data['results']) == 2

    def test_events_ordered_by_updated_at_desc(self, usuario_controle, municipio, projeto, tipo_evento):
        """
        Caso 5: Ordenação por updated_at desc (mais recentes primeiro)
        """
        # Criar solicitações em ordem
        sol1 = create_solicitacao(usuario_controle, municipio, projeto, tipo_evento, Solicitacao.GCalStatus.PUBLISHED, 1)
        sol2 = create_solicitacao(usuario_controle, municipio, projeto, tipo_evento, Solicitacao.GCalStatus.PUBLISHED, 2)
        sol3 = create_solicitacao(usuario_controle, municipio, projeto, tipo_evento, Solicitacao.GCalStatus.PUBLISHED, 3)

        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        response = client.get("/api/gcal/dashboard/events/")

        assert response.status_code == http_status.HTTP_200_OK
        results = response.data['results']

        # Mais recente primeiro
        assert results[0]['id'] == sol3.id
        assert results[1]['id'] == sol2.id
        assert results[2]['id'] == sol1.id

    def test_events_requires_authentication(self):
        """
        Caso 6: Endpoint exige autenticação

        Nota: DRF retorna 403 (Forbidden) quando permission classes são checadas
        antes de autenticação. Ambos 401 e 403 indicam acesso negado corretamente.
        """
        client = APIClient()

        response = client.get("/api/gcal/dashboard/events/")

        # DRF pode retornar 403 ao invés de 401 com IsControleOrSuper + IsAuthenticated
        assert response.status_code in [http_status.HTTP_401_UNAUTHORIZED, http_status.HTTP_403_FORBIDDEN]

    def test_events_requires_controle_or_super(self):
        """
        Caso 7: Endpoint exige permissão Controle ou Superintendência
        """
        # Usuário sem grupo Controle/Super
        user = Usuario.objects.create_user(
            username="formador_sprint5",
            email="formador@test.com",
            password="testpass",
            cpf="33333333333",
        )
        grupo_formador, _ = Group.objects.get_or_create(name="Formador")
        user.groups.add(grupo_formador)

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get("/api/gcal/dashboard/events/")

        assert response.status_code == http_status.HTTP_403_FORBIDDEN
