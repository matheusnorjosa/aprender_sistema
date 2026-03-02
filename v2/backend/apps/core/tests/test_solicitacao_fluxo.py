"""
Testes para fluxo de solicitações baseado em Projeto.fluxo

PR 13/N - Classificação de Projetos

Valida:
- SUPER: status inicial = 'pendente', requer aprovação
- NAO_SUPER: status inicial = 'aprovado', auto-aprovado
- coordenador_acompanha NÃO determina fluxo (apenas informativo)
- Serializer retorna fluxo do projeto
- Pré-agenda filtra por fluxo corretamente
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from datetime import date

from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import Compra, Municipio, Projeto, Solicitacao, TipoEvento, Usuario


@pytest.fixture
def api_client():
    """Cliente API REST."""
    return APIClient()


@pytest.fixture
def grupos():
    """Cria grupos Django."""
    grupos = {
        "Coordenador": Group.objects.get_or_create(name="Coordenador")[0],
        "Superintendência": Group.objects.get_or_create(name="Superintendência")[0],
        "Controle": Group.objects.get_or_create(name="Controle")[0],
        "DAT": Group.objects.get_or_create(name="DAT")[0],
    }
    return grupos


@pytest.fixture
def usuario_coordenador(grupos):
    """Usuário com perfil Coordenador."""
    user = Usuario.objects.create_user(
        username="coord1", password="senha123", cpf="11111111111", email="coord@test.com"
    )
    user.groups.add(grupos["Coordenador"])
    return user


@pytest.fixture
def usuario_superintendencia(grupos):
    """Usuário com perfil Superintendência."""
    user = Usuario.objects.create_user(
        username="super1", password="senha123", cpf="22222222222", email="super@test.com"
    )
    user.groups.add(grupos["Superintendência"])
    return user


@pytest.fixture
def municipio():
    """Município de teste."""
    return Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)


@pytest.fixture
def projeto_super():
    """Projeto com fluxo SUPER (requer aprovação)."""
    return Projeto.objects.create(nome="ACerta", codigo="ACERTA", fluxo="SUPER", ativo=True)


@pytest.fixture
def projeto_outros():
    """Projeto com fluxo NAO_SUPER (auto-aprovado)."""
    return Projeto.objects.create(nome="Alfabetização Ceará", codigo="ALFCE", fluxo="NAO_SUPER", ativo=True)


@pytest.fixture
def tipo_evento():
    """Tipo de evento de teste."""
    return TipoEvento.objects.create(nome="Formação Inicial")


@pytest.fixture
def compras_fluxo_base(municipio, projeto_super, projeto_outros):
    """Semear compras para liberar criação de solicitação por município+projeto."""
    Compra.objects.create(
        codigo="COMP-FLUXO-SUPER",
        projeto=projeto_super,
        municipio=municipio,
        quantidade=10,
        data=date(2026, 1, 10),
        uso="Teste fluxo SUPER",
        external_hash="test-solicitacao-fluxo-super",
    )
    Compra.objects.create(
        codigo="COMP-FLUXO-OUTROS",
        projeto=projeto_outros,
        municipio=municipio,
        quantidade=10,
        data=date(2026, 1, 11),
        uso="Teste fluxo NAO_SUPER",
        external_hash="test-solicitacao-fluxo-outros",
    )


@pytest.mark.django_db
@pytest.mark.usefixtures("compras_fluxo_base")
class TestSolicitacaoFluxoSUPER:
    """
    Testes para solicitações de projetos com fluxo SUPER.
    """

    def test_projeto_super_cria_solicitacao_pendente(
        self, api_client, usuario_coordenador, municipio, projeto_super, tipo_evento
    ):
        """
        Teste PR 13/N-T1: Projeto SUPER → status inicial = 'pendente'.

        Expectativa:
        - Solicitação criada com status='pendente'
        - Aguarda aprovação da Superintendência
        """
        api_client.force_authenticate(user=usuario_coordenador)

        # Criar solicitação para projeto SUPER
        payload = {
            "municipio": municipio.id,
            "projeto": projeto_super.id,
            "tipo": "evento",
            "tipo_evento": tipo_evento.id,
            "inicio": (timezone.now() + timezone.timedelta(days=7)).isoformat(),
            "fim": (timezone.now() + timezone.timedelta(days=7, hours=2)).isoformat(),
            "coordenador_acompanha": False,
        }

        response = api_client.post("/api/solicitacoes/", payload, format="json")

        assert response.status_code == 201
        assert response.data["status"] == "pendente"

        # Verificar no banco
        solicitacao = Solicitacao.objects.get(id=response.data["id"])
        assert solicitacao.status == "pendente"
        assert solicitacao.projeto.fluxo == "SUPER"

    def test_coordenador_acompanha_nao_afeta_fluxo_super(
        self, api_client, usuario_coordenador, municipio, projeto_super, tipo_evento
    ):
        """
        Teste PR 13/N-T2: coordenador_acompanha NÃO determina fluxo.

        Expectativa:
        - Mesmo com coordenador_acompanha=True, se projeto.fluxo=SUPER → pendente
        - Campo coordenador_acompanha é apenas informativo
        """
        api_client.force_authenticate(user=usuario_coordenador)

        payload = {
            "municipio": municipio.id,
            "projeto": projeto_super.id,
            "tipo": "evento",
            "tipo_evento": tipo_evento.id,
            "inicio": (timezone.now() + timezone.timedelta(days=7)).isoformat(),
            "fim": (timezone.now() + timezone.timedelta(days=7, hours=2)).isoformat(),
            "coordenador_acompanha": True,  # ← True, mas não afeta fluxo
            "coordenador": usuario_coordenador.id,
        }

        response = api_client.post("/api/solicitacoes/", payload, format="json")

        assert response.status_code == 201
        assert response.data["status"] == "pendente"  # Ainda pendente!
        assert response.data["coordenador_acompanha"] is True

    def test_super_requer_aprovacao_superintendencia(
        self, api_client, usuario_coordenador, usuario_superintendencia, municipio, projeto_super, tipo_evento
    ):
        """
        Teste PR 13/N-T3: Projeto SUPER requer aprovação da Superintendência.

        Expectativa:
        - Solicitação criada como 'pendente'
        - Apenas Superintendência pode aprovar
        - Após aprovação → status='aprovado'
        """
        # 1. Coordenador cria solicitação
        api_client.force_authenticate(user=usuario_coordenador)

        payload = {
            "municipio": municipio.id,
            "projeto": projeto_super.id,
            "tipo": "evento",
            "tipo_evento": tipo_evento.id,
            "inicio": (timezone.now() + timezone.timedelta(days=7)).isoformat(),
            "fim": (timezone.now() + timezone.timedelta(days=7, hours=2)).isoformat(),
            "coordenador_acompanha": False,
        }

        response = api_client.post("/api/solicitacoes/", payload, format="json")
        solicitacao_id = response.data["id"]

        assert response.status_code == 201
        assert response.data["status"] == "pendente"

        # 2. Coordenador NÃO pode aprovar (403 esperado)
        response_forbidden = api_client.patch(f"/api/solicitacoes/{solicitacao_id}/approve/", format="json")
        assert response_forbidden.status_code == 403

        # 3. Superintendência aprova
        api_client.force_authenticate(user=usuario_superintendencia)

        response_approve = api_client.patch(
            f"/api/solicitacoes/{solicitacao_id}/approve/", {"justificativa": "Aprovado para teste"}, format="json"
        )

        assert response_approve.status_code == 200
        assert response_approve.data["solicitacao"]["status"] == "aprovado"


@pytest.mark.django_db
@pytest.mark.usefixtures("compras_fluxo_base")
class TestSolicitacaoFluxoNaoSuper:
    """
    Testes para solicitações de projetos com fluxo NAO_SUPER.
    """

    def test_projeto_outros_cria_solicitacao_aprovada(
        self, api_client, usuario_coordenador, municipio, projeto_outros, tipo_evento
    ):
        """
        Teste PR 13/N-T4: Projeto NAO_SUPER → status inicial = 'aprovado'.

        Expectativa:
        - Solicitação criada com status='aprovado' (auto-aprovada)
        - Vai direto para pré-agenda
        - NÃO requer aprovação da Superintendência
        """
        api_client.force_authenticate(user=usuario_coordenador)

        payload = {
            "municipio": municipio.id,
            "projeto": projeto_outros.id,
            "tipo": "evento",
            "tipo_evento": tipo_evento.id,
            "inicio": (timezone.now() + timezone.timedelta(days=7)).isoformat(),
            "fim": (timezone.now() + timezone.timedelta(days=7, hours=2)).isoformat(),
            "coordenador_acompanha": False,
        }

        response = api_client.post("/api/solicitacoes/", payload, format="json")

        assert response.status_code == 201
        assert response.data["status"] == "aprovado"  # Auto-aprovado!

        # Verificar no banco
        solicitacao = Solicitacao.objects.get(id=response.data["id"])
        assert solicitacao.status == "aprovado"
        assert solicitacao.projeto.fluxo == "NAO_SUPER"

    def test_coordenador_acompanha_nao_afeta_fluxo_outros(
        self, api_client, usuario_coordenador, municipio, projeto_outros, tipo_evento
    ):
        """
        Teste PR 13/N-T5: coordenador_acompanha NÃO determina fluxo (NAO_SUPER).

        Expectativa:
        - Mesmo com coordenador_acompanha=False, se projeto.fluxo=NAO_SUPER → aprovado
        - Campo coordenador_acompanha é apenas informativo
        """
        api_client.force_authenticate(user=usuario_coordenador)

        payload = {
            "municipio": municipio.id,
            "projeto": projeto_outros.id,
            "tipo": "evento",
            "tipo_evento": tipo_evento.id,
            "inicio": (timezone.now() + timezone.timedelta(days=7)).isoformat(),
            "fim": (timezone.now() + timezone.timedelta(days=7, hours=2)).isoformat(),
            "coordenador_acompanha": False,  # ← False, mas não afeta fluxo
        }

        response = api_client.post("/api/solicitacoes/", payload, format="json")

        assert response.status_code == 201
        assert response.data["status"] == "aprovado"  # Auto-aprovado!
        assert response.data["coordenador_acompanha"] is False


@pytest.mark.django_db
class TestPreAgendaFiltroPorFluxo:
    """
    Testes para endpoint /api/pre-agenda/ com filtro por fluxo.
    """

    def test_pre_agenda_filtra_por_super(
        self, api_client, usuario_coordenador, grupos, municipio, projeto_super, projeto_outros, tipo_evento
    ):
        """
        Teste PR 13/N-T6: Pré-agenda filtra por fluxo corretamente.

        Expectativa:
        - ?super=1 retorna apenas projetos SUPER
        - ?super=0 retorna apenas projetos NAO_SUPER
        - Sem filtro retorna ambos
        """
        # Criar usuário Controle (tem acesso à pré-agenda)
        usuario_controle = Usuario.objects.create_user(
            username="controle1", password="senha123", cpf="33333333333", email="controle@test.com"
        )
        usuario_controle.groups.add(grupos["Controle"])

        # Criar 2 solicitações: 1 SUPER (pendente→aprovado) + 1 NAO_SUPER (auto-aprovado)
        sol_super = Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=municipio,
            projeto=projeto_super,
            tipo="evento",
            tipo_evento=tipo_evento,
            inicio=timezone.now() + timezone.timedelta(days=7),
            fim=timezone.now() + timezone.timedelta(days=7, hours=2),
            status="aprovado",  # Manualmente aprovada para teste
        )

        sol_outros = Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=municipio,
            projeto=projeto_outros,
            tipo="evento",
            tipo_evento=tipo_evento,
            inicio=timezone.now() + timezone.timedelta(days=8),
            fim=timezone.now() + timezone.timedelta(days=8, hours=2),
            status="aprovado",
        )

        api_client.force_authenticate(user=usuario_controle)

        # Teste 1: Filtro super=1 (apenas SUPER)
        response_super = api_client.get("/api/pre-agenda/?super=1")
        assert response_super.status_code == 200
        assert response_super.data["count"] == 1
        assert response_super.data["results"][0]["id"] == sol_super.id

        # Teste 2: Filtro super=0 (apenas NAO_SUPER)
        response_outros = api_client.get("/api/pre-agenda/?super=0")
        assert response_outros.status_code == 200
        assert response_outros.data["count"] == 1
        assert response_outros.data["results"][0]["id"] == sol_outros.id

        # Teste 3: Sem filtro (ambos)
        response_ambos = api_client.get("/api/pre-agenda/")
        assert response_ambos.status_code == 200
        assert response_ambos.data["count"] == 2


@pytest.mark.django_db
class TestSerializerFluxo:
    """
    Testes para serializers retornarem fluxo do projeto.
    """

    def test_serializer_retorna_fluxo_do_projeto(
        self, api_client, usuario_coordenador, grupos, municipio, projeto_super, tipo_evento
    ):
        """
        Teste PR 13/N-T7: Serializer retorna fluxo do projeto vinculado.

        Expectativa:
        - Endpoint /api/pre-agenda/ retorna campo 'fluxo'
        - Valor = Projeto.fluxo (SUPER ou NAO_SUPER)
        """
        # Criar usuário Controle
        usuario_controle = Usuario.objects.create_user(
            username="controle1", password="senha123", cpf="33333333333", email="controle@test.com"
        )
        usuario_controle.groups.add(grupos["Controle"])

        # Criar solicitação SUPER aprovada
        sol = Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=municipio,
            projeto=projeto_super,
            tipo="evento",
            tipo_evento=tipo_evento,
            inicio=timezone.now() + timezone.timedelta(days=7),
            fim=timezone.now() + timezone.timedelta(days=7, hours=2),
            status="aprovado",
        )

        api_client.force_authenticate(user=usuario_controle)

        # Buscar na pré-agenda
        response = api_client.get("/api/pre-agenda/")

        assert response.status_code == 200
        assert response.data["count"] == 1

        item = response.data["results"][0]
        assert item["fluxo"] == "SUPER"  # Fluxo do projeto

    def test_serializer_fallback_outros(self, api_client, usuario_coordenador, grupos, municipio, tipo_evento):
        """
        Teste PR 13/N-T8: Serializer usa fallback NAO_SUPER se projeto não tem fluxo.

        Expectativa:
        - Solicitação sem projeto → fluxo='NAO_SUPER' (fallback)
        """
        # Criar usuário Controle
        usuario_controle = Usuario.objects.create_user(
            username="controle2", password="senha123", cpf="44444444444", email="controle2@test.com"
        )
        usuario_controle.groups.add(grupos["Controle"])

        # Criar solicitação SEM projeto (cenário raro, mas testável)
        sol = Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=municipio,
            projeto=None,  # Sem projeto
            tipo="reuniao",
            tipo_evento=tipo_evento,
            inicio=timezone.now() + timezone.timedelta(days=7),
            fim=timezone.now() + timezone.timedelta(days=7, hours=2),
            status="aprovado",
        )

        api_client.force_authenticate(user=usuario_controle)

        # Buscar na pré-agenda
        response = api_client.get("/api/pre-agenda/")

        assert response.status_code == 200
        item = response.data["results"][0]
        assert item["fluxo"] == "NAO_SUPER"  # Fallback


@pytest.mark.django_db
class TestProjetoSemFluxo:
    """
    Testes para projetos sem campo fluxo definido (edge case).
    """

    def test_projeto_sem_fluxo_usa_padrao_outros(self, api_client, usuario_coordenador, municipio, tipo_evento):
        """
        Teste PR 13/N-T9: Projeto sem fluxo definido usa padrão NAO_SUPER.

        Expectativa:
        - Projeto criado sem especificar fluxo → default='NAO_SUPER'
        - Solicitação criada → status='aprovado' (auto-aprovado)
        """
        # Criar projeto sem especificar fluxo (usa default)
        projeto_default = Projeto.objects.create(
            nome="Projeto Default",
            ativo=True,
            # fluxo não especificado → usa default do modelo
        )

        assert projeto_default.fluxo == "NAO_SUPER"

        Compra.objects.create(
            codigo="COMP-FLUXO-DEFAULT",
            projeto=projeto_default,
            municipio=municipio,
            quantidade=10,
            data=date(2026, 1, 12),
            uso="Teste fluxo default",
            external_hash="test-solicitacao-fluxo-default",
        )

        api_client.force_authenticate(user=usuario_coordenador)

        payload = {
            "municipio": municipio.id,
            "projeto": projeto_default.id,
            "tipo": "evento",
            "tipo_evento": tipo_evento.id,
            "inicio": (timezone.now() + timezone.timedelta(days=7)).isoformat(),
            "fim": (timezone.now() + timezone.timedelta(days=7, hours=2)).isoformat(),
            "coordenador_acompanha": False,
        }

        response = api_client.post("/api/solicitacoes/", payload, format="json")

        assert response.status_code == 201
        assert response.data["status"] == "aprovado"
