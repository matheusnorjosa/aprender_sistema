"""
Suíte completa de testes para o Dashboard com dados reais
Consolida todos os testes implementados nos commits 1-5

Estrutura:
- Testes básicos da API (COMMIT 1)
- Testes do template (COMMIT 2)
- Testes de filtros (COMMIT 3)
- Testes de performance (COMMIT 4)
- Testes de métricas avançadas (COMMIT 5)
- Testes de integração (COMMIT 6)
"""

import json
import time as python_time
import unittest
from datetime import time, timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import (
    Formador,
    FormadoresSolicitacao,
    Municipio,
    Projeto,
    Solicitacao,
    SolicitacaoStatus,
    TipoEvento,
)

User = get_user_model()


class DashboardTestSuite(TestCase):
    """Suíte completa de testes do dashboard com dados reais"""

    @classmethod
    def setUpClass(cls):
        """Setup da classe - executado uma vez para toda a suíte"""
        super().setUpClass()
        cls.test_results = {
            "api_basica": 0,
            "template": 0,
            "filtros": 0,
            "performance": 0,
            "metricas_avancadas": 0,
            "integracao": 0,
            "total_testes": 0,
            "sucessos": 0,
            "falhas": 0,
        }

    def setUp(self):
        """Setup para cada teste individual"""
        # Limpar cache entre testes
        cache.clear()

        # Criar usuário de teste
        self.user = User.objects.create_user(
            username="suite_test_user",
            email="suite@test.com",
            password="testpass123",
            papel="coordenador",
        )

        # Criar dados de teste completos
        self._criar_dados_completos()

        self.client = Client()
        self.client.login(username="suite_test_user", password="testpass123")

    def _criar_dados_completos(self):
        """Criar conjunto completo de dados para testes"""
        # Projetos
        self.projeto1 = Projeto.objects.create(
            nome="Projeto Alpha", descricao="Primeiro projeto"
        )
        self.projeto2 = Projeto.objects.create(
            nome="Projeto Beta", descricao="Segundo projeto"
        )

        # Municípios
        self.municipio1 = Municipio.objects.create(nome="São Paulo", uf="SP")
        self.municipio2 = Municipio.objects.create(nome="Rio de Janeiro", uf="RJ")
        self.municipio3 = Municipio.objects.create(nome="Belo Horizonte", uf="MG")

        # Tipo de evento
        self.tipo_evento = TipoEvento.objects.create(
            nome="Workshop Suite", online=False
        )

        # Formadores
        self.formador1 = Formador.objects.create(
            nome="João Suite", email="joao@suite.com", ativo=True
        )
        self.formador2 = Formador.objects.create(
            nome="Maria Suite", email="maria@suite.com", ativo=True
        )
        self.formador3 = Formador.objects.create(
            nome="Pedro Suite", email="pedro@suite.com", ativo=False
        )

        # Eventos para diferentes cenários
        agora = timezone.now()

        # Cenário 1: Evento aprovado recente (última semana)
        evento1 = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto1,
            municipio=self.municipio1,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento Suite Recente",
            data_solicitacao=agora - timedelta(days=5),
            data_inicio=agora - timedelta(days=2),
            data_fim=agora - timedelta(days=2) + timedelta(hours=4),
            status=SolicitacaoStatus.APROVADO,
        )
        FormadoresSolicitacao.objects.create(
            solicitacao=evento1, formador=self.formador1
        )

        # Cenário 2: Evento aprovado antigo (último mês)
        evento2 = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto2,
            municipio=self.municipio2,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento Suite Mensal",
            data_solicitacao=agora - timedelta(days=25),
            data_inicio=agora - timedelta(days=20),
            data_fim=agora - timedelta(days=20) + timedelta(hours=6),
            status=SolicitacaoStatus.APROVADO,
        )
        FormadoresSolicitacao.objects.create(
            solicitacao=evento2, formador=self.formador2
        )

        # Cenário 3: Solicitação pendente
        evento3 = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto1,
            municipio=self.municipio3,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento Suite Pendente",
            data_solicitacao=agora - timedelta(days=3),
            data_inicio=agora + timedelta(days=5),
            data_fim=agora + timedelta(days=5) + timedelta(hours=2),
            status=SolicitacaoStatus.PENDENTE,
        )
        FormadoresSolicitacao.objects.create(
            solicitacao=evento3, formador=self.formador1
        )

        # Cenário 4: Solicitação reprovada
        evento4 = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto2,
            municipio=self.municipio1,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento Suite Reprovado",
            data_solicitacao=agora - timedelta(days=10),
            data_inicio=agora - timedelta(days=5),
            data_fim=agora - timedelta(days=5) + timedelta(hours=3),
            status=SolicitacaoStatus.REPROVADO,
        )
        FormadoresSolicitacao.objects.create(
            solicitacao=evento4, formador=self.formador2
        )

    # ======================
    # TESTES API BÁSICA (COMMIT 1)
    # ======================

    def test_api_basica_response_structure(self):
        """Teste da estrutura básica da resposta da API"""
        url = reverse("core:dashboard_stats_api")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        # Verificar campos obrigatórios
        required_fields = [
            "timestamp",
            "periodo_referencia",
            "filtros",
            "estatisticas",
            "meta",
        ]
        for field in required_fields:
            self.assertIn(field, data)

        # Verificar estatísticas
        stats = data["estatisticas"]
        stats_fields = [
            "eventos_periodo",
            "formadores_ativos",
            "solicitacoes_pendentes",
            "municipios_atendidos",
        ]
        for field in stats_fields:
            self.assertIn(field, stats)
            self.assertIsInstance(stats[field], int)

        self.__class__.test_results["api_basica"] += 1

    def test_api_basica_authentication(self):
        """Teste de autenticação obrigatória"""
        self.client.logout()
        url = reverse("core:dashboard_stats_api")
        response = self.client.get(url)

        # Deve redirecionar para login
        self.assertEqual(response.status_code, 302)

        self.__class__.test_results["api_basica"] += 1

    # ======================
    # TESTES TEMPLATE (COMMIT 2)
    # ======================

    def test_template_rendering(self):
        """Teste de renderização do template home"""
        url = reverse("core:home")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        # Verificar elementos essenciais
        essential_elements = [
            'id="eventos-count"',
            'id="formadores-count"',
            'id="pendentes-count"',
            'id="municipios-count"',
            "loadDashboardStats",
            "fetch(",
        ]

        for element in essential_elements:
            self.assertContains(response, element)

        self.__class__.test_results["template"] += 1

    def test_template_api_integration(self):
        """Teste de integração template com API"""
        # Verificar se template contém URL da API
        url = reverse("core:home")
        response = self.client.get(url)

        api_url = reverse("core:dashboard_stats_api")
        self.assertContains(response, api_url)

        self.__class__.test_results["template"] += 1

    # ======================
    # TESTES FILTROS (COMMIT 3)
    # ======================

    def test_filtros_periodo(self):
        """Teste de filtros por período"""
        url = reverse("core:dashboard_stats_api")

        # Teste 7 dias
        response = self.client.get(url, {"periodo": "7"})
        data = json.loads(response.content)
        eventos_7d = data["estatisticas"]["eventos_periodo"]

        # Teste 30 dias
        response = self.client.get(url, {"periodo": "30"})
        data = json.loads(response.content)
        eventos_30d = data["estatisticas"]["eventos_periodo"]

        # 30 dias deve ter >= eventos que 7 dias
        self.assertGreaterEqual(eventos_30d, eventos_7d)

        self.__class__.test_results["filtros"] += 1

    def test_filtros_projeto(self):
        """Teste de filtro por projeto"""
        url = reverse("core:dashboard_stats_api")

        # Sem filtro
        response = self.client.get(url, {"periodo": "365"})
        data = json.loads(response.content)
        eventos_total = data["estatisticas"]["eventos_periodo"]

        # Com filtro projeto1
        response = self.client.get(
            url, {"periodo": "365", "projeto": str(self.projeto1.id)}
        )
        data = json.loads(response.content)
        eventos_projeto1 = data["estatisticas"]["eventos_periodo"]

        # Filtrado deve ser <= total
        self.assertLessEqual(eventos_projeto1, eventos_total)

        # Verificar filtro aplicado
        self.assertIn("Projeto: Projeto Alpha", data["filtros"]["filtros_aplicados"])

        self.__class__.test_results["filtros"] += 1

    # ======================
    # TESTES PERFORMANCE (COMMIT 4)
    # ======================

    def test_performance_cache_behavior(self):
        """Teste de comportamento do cache"""
        url = reverse("core:dashboard_stats_api")

        # Primeira requisição (cold cache)
        start_time = python_time.time()
        response1 = self.client.get(url)
        cold_time = python_time.time() - start_time

        data1 = json.loads(response1.content)
        self.assertFalse(data1["meta"]["cache_hit"])

        # Segunda requisição (warm cache)
        start_time = python_time.time()
        response2 = self.client.get(url)
        warm_time = python_time.time() - start_time

        data2 = json.loads(response2.content)
        self.assertTrue(data2["meta"]["cache_hit"])

        # Cache deve ser mais rápido
        self.assertLess(warm_time, cold_time)

        self.__class__.test_results["performance"] += 1

    def test_performance_response_time(self):
        """Teste de tempo de resposta"""
        url = reverse("core:dashboard_stats_api")
        cache.clear()

        start_time = python_time.time()
        response = self.client.get(url)
        end_time = python_time.time()

        response_time = end_time - start_time

        self.assertEqual(response.status_code, 200)
        # API deve responder em menos de 1 segundo
        self.assertLess(response_time, 1.0)

        self.__class__.test_results["performance"] += 1

    # ======================
    # TESTES MÉTRICAS AVANÇADAS (COMMIT 5)
    # ======================

    def test_metricas_avancadas_structure(self):
        """Teste da estrutura das métricas avançadas"""
        url = reverse("core:dashboard_stats_api")
        response = self.client.get(url)

        data = json.loads(response.content)

        # Verificar campo principal
        self.assertIn("metricas_avancadas", data)

        metricas = data["metricas_avancadas"]
        expected_fields = [
            "taxa_aprovacao",
            "top_formadores",
            "top_municipios",
            "tendencia_semanal",
        ]

        for field in expected_fields:
            self.assertIn(field, metricas)

        # Verificar meta flag
        self.assertTrue(data["meta"]["metricas_avancadas"])

        self.__class__.test_results["metricas_avancadas"] += 1

    def test_metricas_taxa_aprovacao(self):
        """Teste do cálculo da taxa de aprovação"""
        url = reverse("core:dashboard_stats_api")
        response = self.client.get(url, {"periodo": "365"})

        data = json.loads(response.content)
        taxa = data["metricas_avancadas"]["taxa_aprovacao"]

        # Verificar campos da taxa
        self.assertIn("percentual", taxa)
        self.assertIn("total_solicitacoes", taxa)
        self.assertIn("aprovadas", taxa)
        self.assertIn("reprovadas", taxa)

        # Verificar cálculo correto
        if taxa["total_solicitacoes"] > 0:
            expected_percentual = round(
                (taxa["aprovadas"] / taxa["total_solicitacoes"]) * 100, 1
            )
            self.assertEqual(taxa["percentual"], expected_percentual)

        self.__class__.test_results["metricas_avancadas"] += 1

    # ======================
    # TESTES INTEGRAÇÃO (COMMIT 6)
    # ======================

    def test_integracao_end_to_end(self):
        """Teste de integração completa end-to-end"""
        # 1. Acessar página home
        home_response = self.client.get(reverse("core:home"))
        self.assertEqual(home_response.status_code, 200)

        # 2. Verificar se template inclui URL da API
        api_url = reverse("core:dashboard_stats_api")
        self.assertContains(home_response, api_url)

        # 3. Chamar API diretamente
        api_response = self.client.get(api_url)
        self.assertEqual(api_response.status_code, 200)

        # 4. Verificar dados consistentes
        data = json.loads(api_response.content)
        self.assertIn("estatisticas", data)
        self.assertIn("metricas_avancadas", data)

        # 5. Testar filtros
        filtered_response = self.client.get(api_url, {"periodo": "7"})
        self.assertEqual(filtered_response.status_code, 200)

        filtered_data = json.loads(filtered_response.content)
        self.assertTrue(filtered_data["meta"]["com_filtros"])

        self.__class__.test_results["integracao"] += 1

    def test_integracao_compatibilidade_retroativa(self):
        """Teste de compatibilidade com versões anteriores"""
        url = reverse("core:dashboard_stats_api")
        response = self.client.get(url)

        data = json.loads(response.content)

        # Campos originais devem existir (compatibilidade)
        original_fields = {
            "timestamp": str,
            "periodo_referencia": dict,
            "filtros": dict,
            "estatisticas": dict,
            "meta": dict,
        }

        for field, expected_type in original_fields.items():
            self.assertIn(field, data)
            self.assertIsInstance(data[field], expected_type)

        # Estatísticas básicas devem estar presentes
        basic_stats = [
            "eventos_periodo",
            "formadores_ativos",
            "solicitacoes_pendentes",
            "municipios_atendidos",
        ]
        for stat in basic_stats:
            self.assertIn(stat, data["estatisticas"])

        self.__class__.test_results["integracao"] += 1

    # ======================
    # TESTES REGRESSÃO
    # ======================

    def test_regressao_dados_consistentes(self):
        """Teste de regressão - dados devem ser consistentes entre calls"""
        url = reverse("core:dashboard_stats_api")

        # Múltiplas chamadas devem retornar dados consistentes
        responses = []
        for _ in range(3):
            cache.clear()  # Forçar recalculo
            response = self.client.get(url)
            data = json.loads(response.content)
            responses.append(data["estatisticas"])

        # Todos devem ser iguais
        first_response = responses[0]
        for response in responses[1:]:
            self.assertEqual(response, first_response)

        self.__class__.test_results["integracao"] += 1

    @classmethod
    def tearDownClass(cls):
        """Relatório final da suíte de testes"""
        super().tearDownClass()

        # Contar totais
        total_tests = sum(cls.test_results.values())

        print("\n" + "=" * 60)
        print("RELATÓRIO DA SUÍTE DE TESTES DO DASHBOARD")
        print("=" * 60)
        print(f"API Básica (COMMIT 1): {cls.test_results['api_basica']} testes")
        print(f"Template (COMMIT 2): {cls.test_results['template']} testes")
        print(f"Filtros (COMMIT 3): {cls.test_results['filtros']} testes")
        print(f"Performance (COMMIT 4): {cls.test_results['performance']} testes")
        print(
            f"Métricas Avançadas (COMMIT 5): {cls.test_results['metricas_avancadas']} testes"
        )
        print(f"Integração (COMMIT 6): {cls.test_results['integracao']} testes")
        print("-" * 60)
        print(f"TOTAL DE TESTES EXECUTADOS: {total_tests}")
        print("=" * 60)


# Testes específicos de casos extremos
class DashboardEdgeCasesTestCase(TestCase):
    """Testes para casos extremos e situações especiais"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="edge_case_user",
            email="edge@test.com",
            password="testpass123",
            papel="coordenador",
        )
        self.client = Client()
        self.client.login(username="edge_case_user", password="testpass123")

    def test_dados_vazios(self):
        """Teste com banco de dados vazio"""
        url = reverse("core:dashboard_stats_api")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        # Deve retornar zeros, não erros
        stats = data["estatisticas"]
        self.assertEqual(stats["eventos_periodo"], 0)
        self.assertEqual(stats["municipios_atendidos"], 0)

        # Métricas avançadas devem existir mas vazias
        metricas = data["metricas_avancadas"]
        self.assertEqual(metricas["taxa_aprovacao"]["percentual"], 0.0)
        self.assertEqual(len(metricas["top_formadores"]), 0)

    def test_filtros_invalidos(self):
        """Teste com parâmetros de filtro inválidos"""
        url = reverse("core:dashboard_stats_api")

        invalid_params = [
            {"periodo": "invalid"},
            {"periodo": "-10"},
            {"projeto": "not-a-uuid"},
            {"municipio": "12345"},
            {"periodo": "0"},
        ]

        for params in invalid_params:
            response = self.client.get(url, params)
            self.assertEqual(response.status_code, 200)  # Não deve quebrar

            data = json.loads(response.content)
            self.assertIn("estatisticas", data)  # Deve ter resposta válida

    @override_settings(
        CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}
    )
    def test_sem_cache_disponivel(self):
        """Teste quando cache não está disponível"""
        url = reverse("core:dashboard_stats_api")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        # Deve funcionar normalmente mesmo sem cache
        self.assertFalse(data["meta"]["cache_hit"])
        self.assertIn("estatisticas", data)
