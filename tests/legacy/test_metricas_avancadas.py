import json
from datetime import time, timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
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


class MetricasAvancadasTestCase(TestCase):
    """Testes para as métricas avançadas da API dashboard"""

    def setUp(self):
        """Configuração inicial para os testes das métricas avançadas"""
        self.user = User.objects.create_user(
            username="metricas_test_user",
            email="metricas@test.com",
            password="testpass123",
            papel="coordenador",
        )

        self.projeto1 = Projeto.objects.create(
            nome="Projeto Métricas Alpha", descricao="Primeiro projeto para métricas"
        )

        self.projeto2 = Projeto.objects.create(
            nome="Projeto Métricas Beta", descricao="Segundo projeto para métricas"
        )

        self.municipio1 = Municipio.objects.create(nome="São Paulo", uf="SP")

        self.municipio2 = Municipio.objects.create(nome="Rio de Janeiro", uf="RJ")

        self.municipio3 = Municipio.objects.create(nome="Belo Horizonte", uf="MG")

        self.tipo_evento = TipoEvento.objects.create(
            nome="Workshop Métricas", online=False
        )

        self.formador1 = Formador.objects.create(
            nome="João Métricas", email="joao.metricas@test.com", ativo=True
        )

        self.formador2 = Formador.objects.create(
            nome="Maria Métricas", email="maria.metricas@test.com", ativo=True
        )

        self.formador3 = Formador.objects.create(
            nome="Pedro Métricas", email="pedro.metricas@test.com", ativo=True
        )

        # Criar dados de teste específicos para métricas
        self._criar_dados_teste()

        self.client = Client()
        self.client.login(username="metricas_test_user", password="testpass123")

    def _criar_dados_teste(self):
        """Criar dados específicos para testar métricas"""
        agora = timezone.now()

        # Evento 1: João - 4 horas (aprovado) - SP
        evento1 = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto1,
            municipio=self.municipio1,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento João 4h",
            data_solicitacao=agora - timedelta(days=10),
            data_inicio=agora - timedelta(days=5),
            data_fim=agora - timedelta(days=5) + timedelta(hours=4),
            status=SolicitacaoStatus.APROVADO,
        )
        FormadoresSolicitacao.objects.create(
            solicitacao=evento1, formador=self.formador1
        )

        # Evento 2: Maria - 2 horas (aprovado) - RJ
        evento2 = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto1,
            municipio=self.municipio2,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento Maria 2h",
            data_solicitacao=agora - timedelta(days=8),
            data_inicio=agora - timedelta(days=3),
            data_fim=agora - timedelta(days=3) + timedelta(hours=2),
            status=SolicitacaoStatus.APROVADO,
        )
        FormadoresSolicitacao.objects.create(
            solicitacao=evento2, formador=self.formador2
        )

        # Evento 3: João - 6 horas (aprovado) - SP (mais um para SP)
        evento3 = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto2,
            municipio=self.municipio1,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento João 6h",
            data_solicitacao=agora - timedelta(days=7),
            data_inicio=agora - timedelta(days=2),
            data_fim=agora - timedelta(days=2) + timedelta(hours=6),
            status=SolicitacaoStatus.APROVADO,
        )
        FormadoresSolicitacao.objects.create(
            solicitacao=evento3, formador=self.formador1
        )

        # Evento 4: Pedro - 3 horas (reprovado) - não deve contar nas métricas
        evento4 = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto1,
            municipio=self.municipio3,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento Pedro Reprovado",
            data_solicitacao=agora - timedelta(days=6),
            data_inicio=agora - timedelta(days=1),
            data_fim=agora - timedelta(days=1) + timedelta(hours=3),
            status=SolicitacaoStatus.REPROVADO,
        )
        FormadoresSolicitacao.objects.create(
            solicitacao=evento4, formador=self.formador3
        )

        # Evento 5: Maria - 8 horas (pendente) - para taxa de aprovação
        evento5 = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto2,
            municipio=self.municipio3,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento Maria Pendente",
            data_solicitacao=agora - timedelta(days=4),
            data_inicio=agora + timedelta(days=1),
            data_fim=agora + timedelta(days=1) + timedelta(hours=8),
            status=SolicitacaoStatus.PENDENTE,
        )
        FormadoresSolicitacao.objects.create(
            solicitacao=evento5, formador=self.formador2
        )

    def test_taxa_aprovacao_calculation(self):
        """Teste do cálculo da taxa de aprovação"""
        url = reverse("core:dashboard_stats_api")
        response = self.client.get(url, {"periodo": "30"})

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        metricas = data["metricas_avancadas"]
        taxa = metricas["taxa_aprovacao"]

        # 5 solicitações no total: 3 aprovadas, 1 reprovada, 1 pendente
        # Taxa = (3 / 5) * 100 = 60%
        self.assertEqual(taxa["total_solicitacoes"], 5)
        self.assertEqual(taxa["aprovadas"], 3)
        self.assertEqual(taxa["reprovadas"], 1)
        self.assertEqual(taxa["percentual"], 60.0)

    def test_top_formadores_por_horas(self):
        """Teste do ranking de formadores por horas trabalhadas"""
        url = reverse("core:dashboard_stats_api")
        response = self.client.get(url, {"periodo": "30"})

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        top_formadores = data["metricas_avancadas"]["top_formadores"]

        # Deve ter no máximo 5 formadores
        self.assertLessEqual(len(top_formadores), 5)

        # João deve ser o primeiro (10 horas total: 4h + 6h)
        self.assertEqual(top_formadores[0]["nome"], "João Métricas")
        self.assertEqual(top_formadores[0]["total_horas"], 10.0)

        # Maria deve ser a segunda (2 horas)
        self.assertEqual(top_formadores[1]["nome"], "Maria Métricas")
        self.assertEqual(top_formadores[1]["total_horas"], 2.0)

        # Pedro não deve aparecer (evento reprovado)
        nomes_formadores = [f["nome"] for f in top_formadores]
        self.assertNotIn("Pedro Métricas", nomes_formadores)

    def test_top_municipios_por_volume(self):
        """Teste do ranking de municípios por volume de eventos"""
        url = reverse("core:dashboard_stats_api")
        response = self.client.get(url, {"periodo": "30"})

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        top_municipios = data["metricas_avancadas"]["top_municipios"]

        # São Paulo deve ser o primeiro (2 eventos aprovados)
        self.assertEqual(top_municipios[0]["nome"], "São Paulo")
        self.assertEqual(top_municipios[0]["uf"], "SP")
        self.assertEqual(top_municipios[0]["total_eventos"], 2)

        # Rio de Janeiro deve ser o segundo (1 evento aprovado)
        self.assertEqual(top_municipios[1]["nome"], "Rio de Janeiro")
        self.assertEqual(top_municipios[1]["uf"], "RJ")
        self.assertEqual(top_municipios[1]["total_eventos"], 1)

        # Belo Horizonte não deve aparecer (eventos não aprovados)
        nomes_municipios = [m["nome"] for m in top_municipios]
        self.assertNotIn("Belo Horizonte", nomes_municipios)

    def test_tendencia_semanal_structure(self):
        """Teste da estrutura da tendência semanal"""
        url = reverse("core:dashboard_stats_api")
        response = self.client.get(url, {"periodo": "30"})

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        tendencia = data["metricas_avancadas"]["tendencia_semanal"]

        # Deve ter até 4 semanas
        self.assertLessEqual(len(tendencia), 4)

        # Cada item deve ter estrutura correta
        for item in tendencia:
            self.assertIn("semana", item)
            self.assertIn("eventos", item)
            self.assertIsInstance(item["eventos"], int)

    def test_metricas_respeitam_filtros(self):
        """Teste se métricas respeitam filtros aplicados"""
        url = reverse("core:dashboard_stats_api")

        # Filtrar apenas projeto 1
        response = self.client.get(
            url, {"periodo": "30", "projeto": str(self.projeto1.id)}
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        top_municipios = data["metricas_avancadas"]["top_municipios"]

        # Com filtro do projeto1, deve ter:
        # - SP: 1 evento (evento1)
        # - RJ: 1 evento (evento2)
        # - (evento3 não conta porque é projeto2)

        municipios_projeto1 = {m["nome"]: m["total_eventos"] for m in top_municipios}
        self.assertEqual(municipios_projeto1.get("São Paulo"), 1)
        self.assertEqual(municipios_projeto1.get("Rio de Janeiro"), 1)

    def test_metricas_avancadas_campo_presente(self):
        """Teste se o campo metricas_avancadas está presente na resposta"""
        url = reverse("core:dashboard_stats_api")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        # Verificar se campo existe
        self.assertIn("metricas_avancadas", data)

        # Verificar estrutura das métricas
        metricas = data["metricas_avancadas"]
        self.assertIn("taxa_aprovacao", metricas)
        self.assertIn("top_formadores", metricas)
        self.assertIn("top_municipios", metricas)
        self.assertIn("tendencia_semanal", metricas)

        # Verificar meta flag
        self.assertTrue(data["meta"]["metricas_avancadas"])

    def test_metricas_periodo_vazio(self):
        """Teste de métricas quando não há dados no período"""
        # Criar usuário e fazer requisição para período futuro
        user_vazio = User.objects.create_user(
            username="user_vazio",
            email="vazio@test.com",
            password="testpass123",
            papel="coordenador",
        )

        client_vazio = Client()
        client_vazio.login(username="user_vazio", password="testpass123")

        url = reverse("core:dashboard_stats_api")
        response = client_vazio.get(url, {"periodo": "7"})  # Últimos 7 dias

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        metricas = data["metricas_avancadas"]

        # Taxa de aprovação deve ser 0 quando não há dados
        self.assertEqual(metricas["taxa_aprovacao"]["percentual"], 0.0)
        self.assertEqual(metricas["taxa_aprovacao"]["total_solicitacoes"], 0)

        # Listas devem estar vazias
        self.assertEqual(len(metricas["top_formadores"]), 0)
        self.assertEqual(len(metricas["top_municipios"]), 0)

    def test_compatibilidade_api_anterior(self):
        """Teste se adição de métricas não quebra API anterior"""
        url = reverse("core:dashboard_stats_api")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        # Campos originais ainda devem existir
        self.assertIn("timestamp", data)
        self.assertIn("periodo_referencia", data)
        self.assertIn("filtros", data)
        self.assertIn("estatisticas", data)
        self.assertIn("meta", data)

        # Estatísticas básicas ainda devem funcionar
        stats = data["estatisticas"]
        self.assertIn("eventos_periodo", stats)
        self.assertIn("formadores_ativos", stats)
        self.assertIn("solicitacoes_pendentes", stats)
        self.assertIn("municipios_atendidos", stats)

        # Deve ser possível processar response sem quebrar
        self.assertIsInstance(stats["eventos_periodo"], int)
        self.assertIsInstance(stats["formadores_ativos"], int)
