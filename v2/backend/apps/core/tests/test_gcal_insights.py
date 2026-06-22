"""
Testes para SuccessRateView e TopInsightsView (Issue #99).

Validam:
- RBAC (autenticação + Controle/Super)
- Cálculo correto de success rate (published / (published + error))
- Top N municípios/projetos com contagens e rates
- Validação de parâmetros (metric, limit)
- Filtros timezone-aware com bordas inclusivas
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.test import TestCase
from rest_framework.test import APIClient

from apps.core.models import Solicitacao
from apps.core.tests.factories import (
    GroupFactory,
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)


class TestGCalInsights(TestCase):
    """
    Testes para GET /api/gcal/dashboard/insights/success-rate/ e /api/gcal/dashboard/insights/top/

    Casos de teste:
    1. test_success_rate_requires_authentication
    2. test_success_rate_requires_controle_or_super
    3. test_success_rate_counts_and_rate
    4. test_top_municipios_basic_counts_and_rate
    5. test_top_projetos_basic_counts_and_rate
    6. test_top_metric_invalid_returns_400
    7. test_top_limit_bounds
    8. test_filters_respected_boundaries
    """

    def setUp(self):
        """Setup comum para todos os testes."""
        self.client = APIClient()
        self.url_success_rate = "/api/gcal/dashboard/insights/success-rate/"
        self.url_top = "/api/gcal/dashboard/insights/top/"

        # Timezone local
        self.tz_local = ZoneInfo("America/Fortaleza")

        # Criar grupos
        self.group_controle = GroupFactory(name="Controle")
        self.group_coordenador = GroupFactory(name="Coordenador")

        # Criar usuários (com CPFs únicos para evitar unique constraint violation)
        self.user_controle = UsuarioFactory(
            username="controle_insights",
            email="controle_insights@example.com",
            password="password123",
            cpf="33333333333",
        )
        self.user_controle.groups.add(self.group_controle)

        self.user_coordenador = UsuarioFactory(
            username="coordenador_insights",
            email="coordenador_insights@example.com",
            password="password123",
            cpf="44444444444",
        )
        self.user_coordenador.groups.add(self.group_coordenador)

        # Criar fixtures (municipios, projetos, tipo_evento)
        self.municipio_fortaleza = MunicipioFactory(nome="Fortaleza - CE")
        self.municipio_caucaia = MunicipioFactory(nome="Caucaia - CE")
        self.projeto_super = ProjetoFactory(nome="Projeto SUPER", fluxo="SUPER")
        self.projeto_outros = ProjetoFactory(nome="Projeto OUTROS", fluxo="NAO_SUPER")
        self.tipo_evento = TipoEventoFactory(nome="Formação")

    def test_success_rate_requires_authentication(self):
        """
        Teste 1: Endpoint success-rate deve retornar 403 para usuário anônimo.
        """
        response = self.client.get(self.url_success_rate)
        self.assertEqual(response.status_code, 403)

    def test_success_rate_requires_controle_or_super(self):
        """
        Teste 2: Endpoint success-rate deve retornar 403 para perfil sem Controle/Super.
        """
        self.client.force_authenticate(user=self.user_coordenador)
        response = self.client.get(self.url_success_rate)
        self.assertEqual(response.status_code, 403)

    def test_success_rate_counts_and_rate(self):
        """
        Teste 3: Success rate calculado corretamente.

        Cria 6 eventos aprovados:
        - 4 PUBLISHED
        - 2 ERROR
        - 1 PENDING
        - 1 NONE

        Rate esperado: 4 / (4 + 2) = 0.6667
        """
        # Data fixa timezone-aware (2025-02-15)
        ref_date = datetime(2025, 2, 15, 10, 0, 0, tzinfo=self.tz_local)

        # Criar 4 PUBLISHED
        for i in range(4):
            SolicitacaoFactory(
                status="aprovado",
                inicio=ref_date.replace(hour=10 + i),
                fim=ref_date.replace(hour=11 + i),
                municipio=self.municipio_fortaleza,
                projeto=self.projeto_super,
                tipo_evento=self.tipo_evento,
                usuario=self.user_controle,
                coordenador=self.user_coordenador,
                gcal_status=Solicitacao.GCalStatus.PUBLISHED,
            )

        # Criar 2 ERROR
        for i in range(2):
            SolicitacaoFactory(
                status="aprovado",
                inicio=ref_date.replace(hour=14 + i),
                fim=ref_date.replace(hour=15 + i),
                municipio=self.municipio_fortaleza,
                projeto=self.projeto_super,
                tipo_evento=self.tipo_evento,
                usuario=self.user_controle,
                coordenador=self.user_coordenador,
                gcal_status=Solicitacao.GCalStatus.ERROR,
            )

        # Criar 1 PENDING
        SolicitacaoFactory(
            status="aprovado",
            inicio=ref_date.replace(hour=16),
            fim=ref_date.replace(hour=17),
            municipio=self.municipio_fortaleza,
            projeto=self.projeto_super,
            tipo_evento=self.tipo_evento,
            usuario=self.user_controle,
            coordenador=self.user_coordenador,
            gcal_status=Solicitacao.GCalStatus.PENDING,
        )

        # Criar 1 NONE
        SolicitacaoFactory(
            status="aprovado",
            inicio=ref_date.replace(hour=18),
            fim=ref_date.replace(hour=19),
            municipio=self.municipio_fortaleza,
            projeto=self.projeto_super,
            tipo_evento=self.tipo_evento,
            usuario=self.user_controle,
            coordenador=self.user_coordenador,
            gcal_status=Solicitacao.GCalStatus.NONE,
        )

        # Autenticar como Controle
        self.client.force_authenticate(user=self.user_controle)

        # Request sem filtros (todos os eventos)
        response = self.client.get(self.url_success_rate)

        # Validar response
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["published"], 4)
        self.assertEqual(data["error"], 2)
        self.assertEqual(data["pending"], 1)
        self.assertEqual(data["none"], 1)
        self.assertEqual(data["rate"], 0.6667)  # 4 / (4 + 2) = 0.6667 (arredondado)
        self.assertIsNone(data["window"]["start"])
        self.assertIsNone(data["window"]["end"])

    def test_top_municipios_basic_counts_and_rate(self):
        """
        Teste 4: Top municípios com contagens e rate corretos.

        Cria eventos em 2 municípios:
        - Fortaleza: 3 PUBLISHED, 1 ERROR (rate = 0.75)
        - Caucaia: 1 PUBLISHED, 2 ERROR (rate = 0.3333)

        Ordenação: -error (Caucaia primeiro), -count (desempate)
        """
        ref_date = datetime(2025, 2, 15, 10, 0, 0, tzinfo=self.tz_local)

        # Fortaleza: 3 PUBLISHED, 1 ERROR
        for i in range(3):
            SolicitacaoFactory(
                status="aprovado",
                inicio=ref_date.replace(hour=10 + i),
                fim=ref_date.replace(hour=11 + i),
                municipio=self.municipio_fortaleza,
                projeto=self.projeto_super,
                tipo_evento=self.tipo_evento,
                usuario=self.user_controle,
                coordenador=self.user_coordenador,
                gcal_status=Solicitacao.GCalStatus.PUBLISHED,
            )

        SolicitacaoFactory(
            status="aprovado",
            inicio=ref_date.replace(hour=14),
            fim=ref_date.replace(hour=15),
            municipio=self.municipio_fortaleza,
            projeto=self.projeto_super,
            tipo_evento=self.tipo_evento,
            usuario=self.user_controle,
            coordenador=self.user_coordenador,
            gcal_status=Solicitacao.GCalStatus.ERROR,
        )

        # Caucaia: 1 PUBLISHED, 2 ERROR
        SolicitacaoFactory(
            status="aprovado",
            inicio=ref_date.replace(hour=10),
            fim=ref_date.replace(hour=11),
            municipio=self.municipio_caucaia,
            projeto=self.projeto_super,
            tipo_evento=self.tipo_evento,
            usuario=self.user_controle,
            coordenador=self.user_coordenador,
            gcal_status=Solicitacao.GCalStatus.PUBLISHED,
        )

        for i in range(2):
            SolicitacaoFactory(
                status="aprovado",
                inicio=ref_date.replace(hour=12 + i),
                fim=ref_date.replace(hour=13 + i),
                municipio=self.municipio_caucaia,
                projeto=self.projeto_super,
                tipo_evento=self.tipo_evento,
                usuario=self.user_controle,
                coordenador=self.user_coordenador,
                gcal_status=Solicitacao.GCalStatus.ERROR,
            )

        # Autenticar como Controle
        self.client.force_authenticate(user=self.user_controle)

        # Request top municipios
        response = self.client.get(self.url_top, {"metric": "municipios", "limit": 5})

        # Validar response
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["metric"], "municipios")
        self.assertEqual(data["limit"], 5)
        self.assertEqual(len(data["items"]), 2)

        # Primeiro: Caucaia (2 erros, rate 0.3333)
        self.assertEqual(data["items"][0]["name"], "Caucaia - CE")
        self.assertEqual(data["items"][0]["count"], 3)
        self.assertEqual(data["items"][0]["published"], 1)
        self.assertEqual(data["items"][0]["error"], 2)
        self.assertEqual(data["items"][0]["rate"], 0.3333)

        # Segundo: Fortaleza (1 erro, rate 0.75)
        self.assertEqual(data["items"][1]["name"], "Fortaleza - CE")
        self.assertEqual(data["items"][1]["count"], 4)
        self.assertEqual(data["items"][1]["published"], 3)
        self.assertEqual(data["items"][1]["error"], 1)
        self.assertEqual(data["items"][1]["rate"], 0.75)

    def test_top_projetos_basic_counts_and_rate(self):
        """
        Teste 5: Top projetos com contagens e rate corretos.

        Cria eventos em 2 projetos:
        - SUPER: 2 PUBLISHED, 0 ERROR (rate = 1.0)
        - OUTROS: 0 PUBLISHED, 1 ERROR (rate = 0.0)

        Ordenação: -error (OUTROS primeiro), -count (desempate)
        """
        ref_date = datetime(2025, 2, 15, 10, 0, 0, tzinfo=self.tz_local)

        # SUPER: 2 PUBLISHED
        for i in range(2):
            SolicitacaoFactory(
                status="aprovado",
                inicio=ref_date.replace(hour=10 + i),
                fim=ref_date.replace(hour=11 + i),
                municipio=self.municipio_fortaleza,
                projeto=self.projeto_super,
                tipo_evento=self.tipo_evento,
                usuario=self.user_controle,
                coordenador=self.user_coordenador,
                gcal_status=Solicitacao.GCalStatus.PUBLISHED,
            )

        # OUTROS: 1 ERROR
        SolicitacaoFactory(
            status="aprovado",
            inicio=ref_date.replace(hour=14),
            fim=ref_date.replace(hour=15),
            municipio=self.municipio_fortaleza,
            projeto=self.projeto_outros,
            tipo_evento=self.tipo_evento,
            usuario=self.user_controle,
            coordenador=self.user_coordenador,
            gcal_status=Solicitacao.GCalStatus.ERROR,
        )

        # Autenticar como Controle
        self.client.force_authenticate(user=self.user_controle)

        # Request top projetos
        response = self.client.get(self.url_top, {"metric": "projetos", "limit": 5})

        # Validar response
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["metric"], "projetos")
        self.assertEqual(data["limit"], 5)
        self.assertEqual(len(data["items"]), 2)

        # Primeiro: OUTROS (1 erro, rate 0.0)
        self.assertEqual(data["items"][0]["name"], "Projeto OUTROS")
        self.assertEqual(data["items"][0]["count"], 1)
        self.assertEqual(data["items"][0]["published"], 0)
        self.assertEqual(data["items"][0]["error"], 1)
        self.assertEqual(data["items"][0]["rate"], 0.0)

        # Segundo: SUPER (0 erros, rate 1.0)
        self.assertEqual(data["items"][1]["name"], "Projeto SUPER")
        self.assertEqual(data["items"][1]["count"], 2)
        self.assertEqual(data["items"][1]["published"], 2)
        self.assertEqual(data["items"][1]["error"], 0)
        self.assertEqual(data["items"][1]["rate"], 1.0)

    def test_top_metric_invalid_returns_400(self):
        """
        Teste 6: Parâmetro metric inválido retorna 400.
        """
        self.client.force_authenticate(user=self.user_controle)

        # Request com metric inválido
        response = self.client.get(self.url_top, {"metric": "usuarios"})

        # Validar response
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("inválido", data["detail"])

    def test_top_limit_bounds(self):
        """
        Teste 7: Parâmetro limit é clampado entre 1 e 20.

        Cria 25 municípios, valida que:
        - limit=-5 → retorna 1 item (min)
        - limit=25 → retorna 20 itens (max)
        """
        ref_date = datetime(2025, 2, 15, 10, 0, 0, tzinfo=self.tz_local)

        # Criar 25 municípios com 1 evento ERROR cada
        for i in range(25):
            municipio = MunicipioFactory(nome=f"Municipio {i}")
            SolicitacaoFactory(
                status="aprovado",
                inicio=ref_date,
                fim=ref_date + timedelta(hours=1),
                municipio=municipio,
                projeto=self.projeto_super,
                tipo_evento=self.tipo_evento,
                usuario=self.user_controle,
                coordenador=self.user_coordenador,
                gcal_status=Solicitacao.GCalStatus.ERROR,
            )

        # Autenticar como Controle
        self.client.force_authenticate(user=self.user_controle)

        # Teste 1: limit=-5 → clamp para 1
        response = self.client.get(self.url_top, {"metric": "municipios", "limit": -5})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["limit"], 1)
        self.assertEqual(len(data["items"]), 1)

        # Teste 2: limit=25 → clamp para 20
        response = self.client.get(self.url_top, {"metric": "municipios", "limit": 25})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["limit"], 20)
        self.assertEqual(len(data["items"]), 20)

    def test_filters_respected_boundaries(self):
        """
        Teste 8: Filtros start/end são respeitados com bordas inclusivas.

        Cria eventos:
        - 2025-02-20 10:00 (incluir) - PUBLISHED
        - 2025-02-19 10:00 (excluir) - ERROR
        - 2025-02-21 10:00 (excluir) - ERROR

        Valida que start=end=2025-02-20 inclui apenas o primeiro.
        Rate esperado: 1 / (1 + 0) = 1.0
        """
        # Data de referência
        ref_date = datetime(2025, 2, 20, 10, 0, 0, tzinfo=self.tz_local)

        # Evento dentro do período (incluir)
        SolicitacaoFactory(
            status="aprovado",
            inicio=ref_date,
            fim=ref_date + timedelta(hours=2),
            municipio=self.municipio_fortaleza,
            projeto=self.projeto_super,
            tipo_evento=self.tipo_evento,
            usuario=self.user_controle,
            coordenador=self.user_coordenador,
            gcal_status=Solicitacao.GCalStatus.PUBLISHED,
        )

        # Evento um dia antes (excluir)
        SolicitacaoFactory(
            status="aprovado",
            inicio=ref_date - timedelta(days=1),
            fim=ref_date - timedelta(days=1, hours=-1),
            municipio=self.municipio_fortaleza,
            projeto=self.projeto_super,
            tipo_evento=self.tipo_evento,
            usuario=self.user_controle,
            coordenador=self.user_coordenador,
            gcal_status=Solicitacao.GCalStatus.ERROR,
        )

        # Evento um dia depois (excluir)
        SolicitacaoFactory(
            status="aprovado",
            inicio=ref_date + timedelta(days=1),
            fim=ref_date + timedelta(days=1, hours=1),
            municipio=self.municipio_fortaleza,
            projeto=self.projeto_super,
            tipo_evento=self.tipo_evento,
            usuario=self.user_controle,
            coordenador=self.user_coordenador,
            gcal_status=Solicitacao.GCalStatus.ERROR,
        )

        # Autenticar como Controle
        self.client.force_authenticate(user=self.user_controle)

        # Request com start=end=2025-02-20
        response = self.client.get(self.url_success_rate, {"start": "2025-02-20", "end": "2025-02-20"})

        # Validar response
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Deve incluir apenas o evento de 2025-02-20
        self.assertEqual(data["published"], 1)
        self.assertEqual(data["error"], 0)
        self.assertEqual(data["pending"], 0)
        self.assertEqual(data["none"], 0)
        self.assertEqual(data["rate"], 1.0)  # 1 / (1 + 0) = 1.0
        self.assertEqual(data["window"]["start"], "2025-02-20")
        self.assertEqual(data["window"]["end"], "2025-02-20")
