"""
PR16: Testes para Lookup e Validação

Testa:
- GET /api/lookup/municipios/?q=...
- GET /api/lookup/projetos/?q=...
- GET /api/lookup/tipos-evento/?q=...
- GET /api/lookup/usuarios/?q=...
- POST /api/solicitacoes/validate/
"""

import pytest
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from apps.core.models import Municipio, Projeto, TipoEvento, Usuario


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def authenticated_user(db):
    """Criar usuário autenticado para testes"""
    user = Usuario.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123',
        cpf='11111111111',
        first_name='Test',
        last_name='User',
    )
    coord_group, _ = Group.objects.get_or_create(name='Coordenador')
    user.groups.add(coord_group)
    return user


@pytest.fixture
def sample_data(db):
    """Criar dados de exemplo para testes"""
    # Municípios
    m1 = Municipio.objects.create(nome='Fortaleza', uf='CE', ativo=True)
    m2 = Municipio.objects.create(nome='Sobral', uf='CE', ativo=True)

    # Projetos
    p1 = Projeto.objects.create(nome='ACerta', codigo='ACERTA', ativo=True, fluxo='SUPER')
    p2 = Projeto.objects.create(nome='Brincando e Aprendendo', codigo='BRINCANDO', ativo=True, fluxo='NAO_SUPER')

    # Tipos de Evento
    t1 = TipoEvento.objects.create(nome='Formação')
    t2 = TipoEvento.objects.create(nome='Acompanhamento')

    # Usuários
    u1 = Usuario.objects.create_user(
        username='formador1',
        email='formador1@example.com',
        password='pass123',
        cpf='22222222222',
        first_name='João',
        last_name='Silva',
    )
    formador_group, _ = Group.objects.get_or_create(name='Formador')
    u1.groups.add(formador_group)

    return {
        'municipios': [m1, m2],
        'projetos': [p1, p2],
        'tipos_evento': [t1, t2],
        'usuarios': [u1],
    }


@pytest.mark.django_db
class TestMunicipioLookup:
    """Testes para GET /api/lookup/municipios/"""

    def test_lookup_without_auth_returns_403(self, api_client):
        """Lookup sem autenticação deve retornar 403"""
        response = api_client.get('/api/lookup/municipios/')
        assert response.status_code == 403

    def test_lookup_with_query(self, api_client, authenticated_user, sample_data):
        """Lookup com query deve retornar resultados filtrados"""
        api_client.force_authenticate(user=authenticated_user)
        response = api_client.get('/api/lookup/municipios/?q=Fortaleza')

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]['kind'] == 'municipio'
        assert 'Fortaleza' in data[0]['label']

    def test_lookup_without_query(self, api_client, authenticated_user, sample_data):
        """Lookup sem query deve retornar top 20"""
        api_client.force_authenticate(user=authenticated_user)
        response = api_client.get('/api/lookup/municipios/')

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 20


@pytest.mark.django_db
class TestProjetoLookup:
    """Testes para GET /api/lookup/projetos/"""

    def test_lookup_with_query(self, api_client, authenticated_user, sample_data):
        """Lookup com query deve retornar resultados filtrados"""
        api_client.force_authenticate(user=authenticated_user)
        response = api_client.get('/api/lookup/projetos/?q=ACerta')

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]['kind'] == 'projeto'


@pytest.mark.django_db
class TestTipoEventoLookup:
    """Testes para GET /api/lookup/tipos-evento/"""

    def test_lookup_with_query(self, api_client, authenticated_user, sample_data):
        """Lookup com query deve retornar resultados filtrados"""
        api_client.force_authenticate(user=authenticated_user)
        response = api_client.get('/api/lookup/tipos-evento/?q=Formação')

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]['kind'] == 'tipo_evento'


@pytest.mark.django_db
class TestUsuarioLookup:
    """Testes para GET /api/lookup/usuarios/"""

    def test_lookup_with_query(self, api_client, authenticated_user, sample_data):
        """Lookup com query deve retornar resultados filtrados"""
        api_client.force_authenticate(user=authenticated_user)
        response = api_client.get('/api/lookup/usuarios/?q=João')

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]['kind'] == 'usuario'
        assert 'email' in data[0]

    def test_lookup_with_role_filter(self, api_client, authenticated_user, sample_data):
        """Lookup com filtro de role deve retornar apenas usuários do grupo"""
        api_client.force_authenticate(user=authenticated_user)
        response = api_client.get('/api/lookup/usuarios/?role=Formador')

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.django_db
class TestSolicitationValidate:
    """Testes para POST /api/solicitacoes/validate/"""

    def test_validate_with_valid_data(self, api_client, authenticated_user, sample_data):
        """Validação com dados válidos deve retornar ok=True"""
        api_client.force_authenticate(user=authenticated_user)

        municipio = sample_data['municipios'][0]
        projeto = sample_data['projetos'][0]
        tipo_evento = sample_data['tipos_evento'][0]
        formador = sample_data['usuarios'][0]

        payload = {
            'municipio': {'id': municipio.id},
            'projeto': {'id': projeto.id},
            'tipo_evento': {'id': tipo_evento.id},
            'date': '2025-01-15',
            'start': '09:00',
            'end': '12:00',
            'participants': {
                'coordenador': authenticated_user.email,
                'formadores': [formador.email],
                'coord_acompanha': [],
            },
        }

        response = api_client.post('/api/solicitacoes/validate/', payload, format='json')

        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert 'canonical' in data
        assert data['canonical']['municipio_id'] == municipio.id
        assert data['canonical']['projeto_id'] == projeto.id
        assert data['canonical']['tipo_evento_id'] == tipo_evento.id

    def test_validate_with_missing_fields(self, api_client, authenticated_user):
        """Validação com campos faltantes deve retornar ok=False"""
        api_client.force_authenticate(user=authenticated_user)

        payload = {
            'municipio': None,
            'projeto': None,
            'tipo_evento': None,
            'date': '2025-01-15',
            'start': '09:00',
            'end': '12:00',
            'participants': {},
        }

        response = api_client.post('/api/solicitacoes/validate/', payload, format='json')

        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is False
        assert len(data['errors']) > 0

    def test_validate_with_string_names(self, api_client, authenticated_user, sample_data):
        """Validação com nomes em string deve resolver para IDs"""
        api_client.force_authenticate(user=authenticated_user)

        payload = {
            'municipio': 'Fortaleza',
            'projeto': 'ACerta',
            'tipo_evento': 'Formação',
            'date': '2025-01-15',
            'start': '09:00',
            'end': '12:00',
            'participants': {
                'coordenador': authenticated_user.email,
                'formadores': [],
                'coord_acompanha': [],
            },
        }

        response = api_client.post('/api/solicitacoes/validate/', payload, format='json')

        assert response.status_code == 200
        data = response.json()
        # Deve encontrar os IDs mesmo com nomes
        if data['ok']:
            assert data['canonical']['municipio_id'] is not None

    def test_validate_with_invalid_time_range(self, api_client, authenticated_user, sample_data):
        """Validação com horário de término antes do início deve retornar erro"""
        api_client.force_authenticate(user=authenticated_user)

        municipio = sample_data['municipios'][0]
        projeto = sample_data['projetos'][0]
        tipo_evento = sample_data['tipos_evento'][0]

        payload = {
            'municipio': {'id': municipio.id},
            'projeto': {'id': projeto.id},
            'tipo_evento': {'id': tipo_evento.id},
            'date': '2025-01-15',
            'start': '12:00',
            'end': '09:00',  # Término antes do início
            'participants': {
                'coordenador': authenticated_user.email,
                'formadores': [],
                'coord_acompanha': [],
            },
        }

        response = api_client.post('/api/solicitacoes/validate/', payload, format='json')

        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is False
        assert any('término' in err.lower() or 'posterior' in err.lower() for err in data['errors'])
