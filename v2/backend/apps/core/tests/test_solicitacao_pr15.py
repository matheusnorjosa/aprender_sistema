"""
Testes para PR15 - Filtros, Participants e Alias

Valida:
- Filtro mine=true (força filtro por usuário)
- Filtro flow=SUPER|NAO_SUPER
- Filtro status com alias (pending/approved/rejected → pendente/aprovado/reprovado)
- extra_participants payload para criar Participation
- reason como alias para justificativa em approve/reject
- Fallback de get_fluxo para NAO_SUPER
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false

from __future__ import annotations
import pytest
from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.models import (
    Usuario,
    Municipio,
    Projeto,
    TipoEvento,
    Solicitacao,
    Participation,
)


@pytest.fixture
def api_client():
    """Cliente API REST."""
    return APIClient()


@pytest.fixture
def grupos():
    """Cria grupos Django."""
    grupos = {
        'Coordenador': Group.objects.get_or_create(name='Coordenador')[0],
        'Superintendência': Group.objects.get_or_create(name='Superintendência')[0],
        'Controle': Group.objects.get_or_create(name='Controle')[0],
        'DAT': Group.objects.get_or_create(name='DAT')[0],
    }
    return grupos


@pytest.fixture
def usuario_coordenador(grupos):
    """Usuário com perfil Coordenador."""
    user = Usuario.objects.create_user(
        username='coord1',
        password='senha123',
        cpf='11111111111',
        email='coord@test.com'
    )
    user.groups.add(grupos['Coordenador'])
    return user


@pytest.fixture
def usuario_superintendencia(grupos):
    """Usuário com perfil Superintendência."""
    user = Usuario.objects.create_user(
        username='super1',
        password='senha123',
        cpf='22222222222',
        email='super@test.com'
    )
    user.groups.add(grupos['Superintendência'])
    return user


@pytest.fixture
def usuario_controle(grupos):
    """Usuário com perfil Controle."""
    user = Usuario.objects.create_user(
        username='controle1',
        password='senha123',
        cpf='33333333333',
        email='controle@test.com'
    )
    user.groups.add(grupos['Controle'])
    return user


@pytest.fixture
def municipio():
    """Município de teste."""
    return Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)


@pytest.fixture
def projeto_super():
    """Projeto com fluxo SUPER (requer aprovação)."""
    return Projeto.objects.create(
        nome="ACerta",
        codigo="ACERTA",
        fluxo="SUPER",
        ativo=True
    )


@pytest.fixture
def projeto_nao_super():
    """Projeto com fluxo NAO_SUPER (auto-aprovado)."""
    return Projeto.objects.create(
        nome="Alfabetização Ceará",
        codigo="ALFCE",
        fluxo="NAO_SUPER",
        ativo=True
    )


@pytest.fixture
def tipo_evento():
    """TipoEvento de teste."""
    return TipoEvento.objects.create(nome="Formação")


@pytest.mark.django_db
class TestFiltroMine:
    """Testes para filtro mine=true"""

    def test_mine_filters_only_user_solicitacoes(
        self, api_client, usuario_coordenador, usuario_superintendencia,
        municipio, projeto_super, tipo_evento
    ):
        """mine=true retorna apenas solicitações do usuário, mesmo para super."""
        # Criar solicitação do coordenador
        sol_coord = Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=municipio,
            projeto=projeto_super,
            tipo_evento=tipo_evento,
            inicio=timezone.now(),
            fim=timezone.now() + timezone.timedelta(hours=2),
            status='pendente'
        )

        # Criar solicitação da superintendência
        sol_super = Solicitacao.objects.create(
            usuario=usuario_superintendencia,
            municipio=municipio,
            projeto=projeto_super,
            tipo_evento=tipo_evento,
            inicio=timezone.now() + timezone.timedelta(days=1),
            fim=timezone.now() + timezone.timedelta(days=1, hours=2),
            status='pendente'
        )

        # Login como superintendência (que normalmente vê todas)
        api_client.force_authenticate(user=usuario_superintendencia)

        # Sem mine=true, deve ver as duas
        response = api_client.get('/api/solicitacoes/')
        assert response.status_code == 200
        assert response.json()['count'] == 2

        # Com mine=true, deve ver apenas a dela
        response = api_client.get('/api/solicitacoes/?mine=true')
        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 1
        assert data['results'][0]['id'] == sol_super.id


@pytest.mark.django_db
class TestFiltroFlow:
    """Testes para filtro flow=SUPER|NAO_SUPER"""

    def test_flow_super_filters_correctly(
        self, api_client, usuario_coordenador,
        municipio, projeto_super, projeto_nao_super, tipo_evento
    ):
        """flow=SUPER retorna apenas solicitações de projetos SUPER."""
        sol_super = Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=municipio,
            projeto=projeto_super,
            tipo_evento=tipo_evento,
            inicio=timezone.now(),
            fim=timezone.now() + timezone.timedelta(hours=2),
            status='pendente'
        )

        sol_nao_super = Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=municipio,
            projeto=projeto_nao_super,
            tipo_evento=tipo_evento,
            inicio=timezone.now() + timezone.timedelta(days=1),
            fim=timezone.now() + timezone.timedelta(days=1, hours=2),
            status='aprovado'
        )

        api_client.force_authenticate(user=usuario_coordenador)

        # Filtrar por SUPER
        response = api_client.get('/api/solicitacoes/?flow=SUPER')
        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 1
        assert data['results'][0]['id'] == sol_super.id

        # Filtrar por NAO_SUPER
        response = api_client.get('/api/solicitacoes/?flow=NAO_SUPER')
        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 1
        assert data['results'][0]['id'] == sol_nao_super.id


@pytest.mark.django_db
class TestFiltroStatusAlias:
    """Testes para filtro status com alias EN→PT"""

    def test_status_pending_maps_to_pendente(
        self, api_client, usuario_coordenador,
        municipio, projeto_super, tipo_evento
    ):
        """status=pending retorna solicitações pendentes."""
        sol_pendente = Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=municipio,
            projeto=projeto_super,
            tipo_evento=tipo_evento,
            tipo='PRESENCIAL',
            inicio=timezone.now(),
            fim=timezone.now() + timezone.timedelta(hours=2),
            status='pendente'
        )

        api_client.force_authenticate(user=usuario_coordenador)
        response = api_client.get('/api/solicitacoes/?status=pending')
        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 1
        assert data['results'][0]['id'] == sol_pendente.id

    def test_status_approved_maps_to_aprovado(
        self, api_client, usuario_coordenador,
        municipio, projeto_nao_super, tipo_evento
    ):
        """status=approved retorna solicitações aprovadas."""
        sol_aprovado = Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=municipio,
            projeto=projeto_nao_super,
            tipo_evento=tipo_evento,
            tipo='PRESENCIAL',
            inicio=timezone.now(),
            fim=timezone.now() + timezone.timedelta(hours=2),
            status='aprovado'
        )

        api_client.force_authenticate(user=usuario_coordenador)
        response = api_client.get('/api/solicitacoes/?status=approved')
        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 1
        assert data['results'][0]['id'] == sol_aprovado.id

    def test_status_rejected_maps_to_reprovado(
        self, api_client, usuario_coordenador, usuario_superintendencia,
        municipio, projeto_super, tipo_evento
    ):
        """status=rejected retorna solicitações reprovadas."""
        sol_reprovado = Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=municipio,
            projeto=projeto_super,
            tipo_evento=tipo_evento,
            tipo='PRESENCIAL',
            inicio=timezone.now(),
            fim=timezone.now() + timezone.timedelta(hours=2),
            status='reprovado'
        )

        api_client.force_authenticate(user=usuario_coordenador)
        response = api_client.get('/api/solicitacoes/?status=rejected')
        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 1
        assert data['results'][0]['id'] == sol_reprovado.id


@pytest.mark.django_db
class TestExtraParticipants:
    """Testes para extra_participants payload"""

    def test_creates_coordinator_participation(
        self, api_client, usuario_coordenador,
        municipio, projeto_super, tipo_evento
    ):
        """Cria Participation COORDENADOR para request.user."""
        api_client.force_authenticate(user=usuario_coordenador)

        response = api_client.post('/api/solicitacoes/', {
            'municipio': municipio.id,
            'projeto': projeto_super.id,
            'tipo_evento': tipo_evento.id,
            'tipo': 'PRESENCIAL',
            'inicio': timezone.now().isoformat(),
            'fim': (timezone.now() + timezone.timedelta(hours=2)).isoformat(),
            'extra_participants': {
                'formador_ids': [],
                'formador_emails': [],
                'coord_acompanha_ids': [],
                'coord_acompanha_emails': []
            }
        }, format='json')

        assert response.status_code == 201
        sol_id = response.json()['id']

        # Verificar que participation foi criada
        participations = Participation.objects.filter(solicitacao_id=sol_id)
        assert participations.count() == 1
        assert participations.first().usuario == usuario_coordenador
        assert participations.first().role == 'COORDENADOR'

    def test_creates_formador_from_id(
        self, api_client, usuario_coordenador, usuario_controle,
        municipio, projeto_super, tipo_evento
    ):
        """Cria Participation FORMADOR a partir de formador_ids."""
        api_client.force_authenticate(user=usuario_coordenador)

        response = api_client.post('/api/solicitacoes/', {
            'municipio': municipio.id,
            'projeto': projeto_super.id,
            'tipo_evento': tipo_evento.id,
            'tipo': 'PRESENCIAL',
            'inicio': timezone.now().isoformat(),
            'fim': (timezone.now() + timezone.timedelta(hours=2)).isoformat(),
            'extra_participants': {
                'formador_ids': [usuario_controle.id],
                'formador_emails': [],
                'coord_acompanha_ids': [],
                'coord_acompanha_emails': []
            }
        }, format='json')

        assert response.status_code == 201
        sol_id = response.json()['id']

        # Verificar formador participation
        formador_part = Participation.objects.filter(
            solicitacao_id=sol_id,
            usuario=usuario_controle,
            role='FORMADOR'
        )
        assert formador_part.exists()

    def test_creates_formador_from_email_existing_user(
        self, api_client, usuario_coordenador, usuario_controle,
        municipio, projeto_super, tipo_evento
    ):
        """Resolve email para Usuario existente e cria Participation."""
        api_client.force_authenticate(user=usuario_coordenador)

        response = api_client.post('/api/solicitacoes/', {
            'municipio': municipio.id,
            'projeto': projeto_super.id,
            'tipo_evento': tipo_evento.id,
            'tipo': 'PRESENCIAL',
            'inicio': timezone.now().isoformat(),
            'fim': (timezone.now() + timezone.timedelta(hours=2)).isoformat(),
            'extra_participants': {
                'formador_ids': [],
                'formador_emails': ['CONTROLE@TEST.COM'],  # Case-insensitive
                'coord_acompanha_ids': [],
                'coord_acompanha_emails': []
            }
        }, format='json')

        assert response.status_code == 201
        sol_id = response.json()['id']

        # Verificar que resolveu para usuario_controle
        formador_part = Participation.objects.filter(
            solicitacao_id=sol_id,
            usuario=usuario_controle,
            role='FORMADOR'
        )
        assert formador_part.exists()

    def test_creates_guest_email_for_unknown_email(
        self, api_client, usuario_coordenador,
        municipio, projeto_super, tipo_evento
    ):
        """
        Cria Participation com guest_email mantendo papel formal para email desconhecido.

        Regra de Negócio (Issue #69 Categoria 8):
        - Email desconhecido enviado em formador_emails → role='FORMADOR' (não CONVIDADO)
        - guest_email armazena o email externo
        - usuario=null é permitido quando guest_email está preenchido
        - Caso de uso: formador externo não cadastrado no sistema
        """
        api_client.force_authenticate(user=usuario_coordenador)

        response = api_client.post('/api/solicitacoes/', {
            'municipio': municipio.id,
            'projeto': projeto_super.id,
            'tipo_evento': tipo_evento.id,
            'tipo': 'PRESENCIAL',
            'inicio': timezone.now().isoformat(),
            'fim': (timezone.now() + timezone.timedelta(hours=2)).isoformat(),
            'extra_participants': {
                'formador_ids': [],
                'formador_emails': ['externo@example.com'],
                'coord_acompanha_ids': [],
                'coord_acompanha_emails': []
            }
        }, format='json')

        assert response.status_code == 201
        sol_id = response.json()['id']

        # Verificar guest_email mantém role formal (FORMADOR, não CONVIDADO)
        guest_part = Participation.objects.filter(
            solicitacao_id=sol_id,
            guest_email='externo@example.com',
            role='FORMADOR'
        )
        assert guest_part.exists(), (
            "Participation com guest_email deve ter role='FORMADOR' "
            "(papel formal mantido para email em formador_emails)"
        )


@pytest.mark.django_db
class TestReasonAlias:
    """Testes para reason como alias de justificativa"""

    def test_approve_accepts_reason_alias(
        self, api_client, usuario_coordenador, usuario_superintendencia,
        municipio, projeto_super, tipo_evento
    ):
        """approve aceita 'reason' como alias para 'justificativa'."""
        sol = Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=municipio,
            projeto=projeto_super,
            tipo_evento=tipo_evento,
            inicio=timezone.now(),
            fim=timezone.now() + timezone.timedelta(hours=2),
            status='pendente'
        )

        api_client.force_authenticate(user=usuario_superintendencia)
        response = api_client.patch(
            f'/api/solicitacoes/{sol.id}/approve/',
            {'reason': 'Aprovado via PR15'},
            format='json'
        )

        assert response.status_code == 200
        sol.refresh_from_db()
        assert sol.status == 'aprovado'

    def test_reject_accepts_reason_alias(
        self, api_client, usuario_coordenador, usuario_superintendencia,
        municipio, projeto_super, tipo_evento
    ):
        """reject aceita 'reason' como alias para 'justificativa'."""
        sol = Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=municipio,
            projeto=projeto_super,
            tipo_evento=tipo_evento,
            inicio=timezone.now(),
            fim=timezone.now() + timezone.timedelta(hours=2),
            status='pendente'
        )

        api_client.force_authenticate(user=usuario_superintendencia)
        response = api_client.patch(
            f'/api/solicitacoes/{sol.id}/reject/',
            {'reason': 'Conflito de agenda'},
            format='json'
        )

        assert response.status_code == 200
        sol.refresh_from_db()
        assert sol.status == 'reprovado'


@pytest.mark.django_db
class TestFluxoFallback:
    """Testes para fallback de get_fluxo"""

    def test_fluxo_fallback_is_nao_super(
        self, api_client, usuario_coordenador,
        municipio, tipo_evento
    ):
        """Solicitação sem projeto retorna fluxo=NAO_SUPER."""
        sol = Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=municipio,
            projeto=None,  # Sem projeto
            tipo_evento=tipo_evento,
            inicio=timezone.now(),
            fim=timezone.now() + timezone.timedelta(hours=2),
            status='aprovado'  # Deve ser auto-aprovado
        )

        api_client.force_authenticate(user=usuario_coordenador)
        response = api_client.get(f'/api/solicitacoes/{sol.id}/')
        assert response.status_code == 200

        data = response.json()
        assert data['fluxo'] == 'NAO_SUPER'
