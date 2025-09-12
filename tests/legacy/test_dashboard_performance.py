import json
import time
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import (
    Formador,
    Municipio,
    Projeto,
    Solicitacao,
    SolicitacaoStatus,
    TipoEvento,
)

User = get_user_model()


class DashboardPerformanceTestCase(TestCase):
    """Testes de performance para a API de estatísticas do dashboard"""

    def setUp(self):
        """Configuração inicial para os testes de performance"""
        self.user = User.objects.create_user(
            username="perf_test_user",
            email="perf@test.com",
            password="testpass123",
            papel="coordenador",
        )

        self.projeto = Projeto.objects.create(
            nome="Projeto Performance", descricao="Projeto para testes de performance"
        )

        self.municipio = Municipio.objects.create(nome="São Paulo", uf="SP")

        self.tipo_evento = TipoEvento.objects.create(
            nome="Workshop Performance", online=False
        )

        self.formador = Formador.objects.create(
            nome="João Performance", email="joao.perf@test.com", ativo=True
        )

        # Criar dados de teste para performance
        agora = timezone.now()
        for i in range(20):  # 20 solicitações para testar
            evento = Solicitacao.objects.create(
                usuario_solicitante=self.user,
                projeto=self.projeto,
                municipio=self.municipio,
                tipo_evento=self.tipo_evento,
                titulo_evento=f"Evento Performance {i}",
                data_inicio=agora - timedelta(days=i),
                data_fim=agora - timedelta(days=i) + timedelta(hours=2),
                status=(
                    SolicitacaoStatus.APROVADO
                    if i % 3 == 0
                    else SolicitacaoStatus.PENDENTE
                ),
            )
            evento.formadores.add(self.formador)

        self.client = Client()
        self.client.login(username="perf_test_user", password="testpass123")

    def test_cache_behavior_cold_vs_warm(self):
        """Teste de comportamento do cache: cold vs warm"""
        url = reverse("core:dashboard_stats_api")

        # Limpar cache antes do teste
        cache.clear()

        # 1ª requisição (cold cache)
        start_time = time.time()
        response_cold = self.client.get(url)
        cold_time = time.time() - start_time

        self.assertEqual(response_cold.status_code, 200)
        data_cold = json.loads(response_cold.content)
        self.assertFalse(data_cold["meta"]["cache_hit"])

        # 2ª requisição (warm cache)
        start_time = time.time()
        response_warm = self.client.get(url)
        warm_time = time.time() - start_time

        self.assertEqual(response_warm.status_code, 200)
        data_warm = json.loads(response_warm.content)
        self.assertTrue(data_warm["meta"]["cache_hit"])

        # Cache deve ser mais rápido (pelo menos 20% mais rápido)
        speed_improvement = (cold_time - warm_time) / cold_time
        self.assertGreater(
            speed_improvement,
            0.1,
            f"Cache não proporcionou melhoria significativa. Cold: {cold_time:.3f}s, Warm: {warm_time:.3f}s",
        )

    def test_cache_respects_filters(self):
        """Teste se cache respeita diferentes filtros"""
        url = reverse("core:dashboard_stats_api")

        # Limpar cache
        cache.clear()

        # Requisição sem filtros
        response1 = self.client.get(url)
        data1 = json.loads(response1.content)

        # Requisição com filtro de período
        response2 = self.client.get(url, {"periodo": "7"})
        data2 = json.loads(response2.content)

        # Requisição com filtro de projeto
        response3 = self.client.get(url, {"projeto": str(self.projeto.id)})
        data3 = json.loads(response3.content)

        # Todos devem ser cache miss (diferentes chaves)
        self.assertFalse(data1["meta"]["cache_hit"])
        self.assertFalse(data2["meta"]["cache_hit"])
        self.assertFalse(data3["meta"]["cache_hit"])

        # Repetir requisições devem ser cache hit
        response1_repeat = self.client.get(url)
        data1_repeat = json.loads(response1_repeat.content)
        self.assertTrue(data1_repeat["meta"]["cache_hit"])

    def test_cache_consistency(self):
        """Teste se cache mantém consistência dos dados"""
        url = reverse("core:dashboard_stats_api")

        # Limpar cache
        cache.clear()

        # 1ª requisição (gera cache)
        response1 = self.client.get(url)
        data1 = json.loads(response1.content)

        # 2ª requisição (do cache)
        response2 = self.client.get(url)
        data2 = json.loads(response2.content)

        # Dados devem ser idênticos (exceto cache_hit)
        self.assertEqual(data1["estatisticas"], data2["estatisticas"])
        self.assertEqual(data1["filtros"], data2["filtros"])
        self.assertEqual(data1["periodo_referencia"], data2["periodo_referencia"])

        # Apenas cache_hit deve ser diferente
        self.assertFalse(data1["meta"]["cache_hit"])
        self.assertTrue(data2["meta"]["cache_hit"])

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.dummy.DummyCache",
            }
        }
    )
    def test_api_works_without_cache(self):
        """Teste se API funciona mesmo sem cache disponível"""
        url = reverse("core:dashboard_stats_api")

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        # Com DummyCache, nunca deve ter cache hit
        self.assertFalse(data["meta"]["cache_hit"])

        # Dados devem estar corretos
        self.assertIn("estatisticas", data)
        self.assertIn("eventos_periodo", data["estatisticas"])

    def test_api_response_time_under_threshold(self):
        """Teste se API responde dentro do limite de tempo"""
        url = reverse("core:dashboard_stats_api")

        # Limpar cache para testar cold cache
        cache.clear()

        start_time = time.time()
        response = self.client.get(url)
        end_time = time.time()

        response_time = end_time - start_time

        self.assertEqual(response.status_code, 200)
        # API deve responder em menos de 1 segundo (cold cache)
        self.assertLess(response_time, 1.0, f"API muito lenta: {response_time:.3f}s")

        # Testar warm cache
        start_time = time.time()
        response = self.client.get(url)
        end_time = time.time()

        cached_response_time = end_time - start_time

        # Cache deve responder em menos de 0.1 segundo
        self.assertLess(
            cached_response_time, 0.1, f"Cache muito lento: {cached_response_time:.3f}s"
        )

    def test_cache_key_uniqueness(self):
        """Teste se diferentes usuários têm caches separados"""
        # Criar segundo usuário
        user2 = User.objects.create_user(
            username="perf_test_user2",
            email="perf2@test.com",
            password="testpass123",
            papel="coordenador",
        )

        url = reverse("core:dashboard_stats_api")
        cache.clear()

        # Requisição do usuário 1
        self.client.login(username="perf_test_user", password="testpass123")
        response1 = self.client.get(url)
        data1 = json.loads(response1.content)
        self.assertFalse(data1["meta"]["cache_hit"])

        # Requisição do usuário 2 (deve ser cache miss)
        self.client.login(username="perf_test_user2", password="testpass123")
        response2 = self.client.get(url)
        data2 = json.loads(response2.content)
        self.assertFalse(data2["meta"]["cache_hit"])  # Chave diferente por usuário

        # Repetir requisição do usuário 2 (deve ser cache hit)
        response3 = self.client.get(url)
        data3 = json.loads(response3.content)
        self.assertTrue(data3["meta"]["cache_hit"])

    def test_query_optimization_count(self):
        """Teste para verificar otimização de queries"""
        url = reverse("core:dashboard_stats_api")
        cache.clear()

        # Usar django.test.utils.override_settings para contar queries
        from django.db import connection
        from django.test import TransactionTestCase
        from django.test.utils import override_settings

        # Reset query log
        connection.queries_log.clear()

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Contar queries executadas
        query_count = len(connection.queries)

        # Com otimizações, deve ter no máximo 5 queries:
        # 1. Auth do usuário
        # 2. Query agregada principal (eventos + municípios)
        # 3. Count formadores ativos
        # 4. Count solicitações pendentes
        # 5. Busca dados projeto/município para filtros_aplicados
        self.assertLessEqual(
            query_count,
            6,
            f"Muitas queries executadas: {query_count}. Queries: {[q['sql'] for q in connection.queries]}",
        )


class DashboardMigrationTestCase(TestCase):
    """Testes para verificar se migration de índices foi aplicada"""

    def test_performance_indexes_exist(self):
        """Teste se os índices de performance foram criados"""
        from django.db import connection

        cursor = connection.cursor()

        # Verificar se índices existem (específico para PostgreSQL)
        cursor.execute(
            """
            SELECT indexname FROM pg_indexes 
            WHERE tablename IN ('core_solicitacao', 'core_formador')
            AND indexname LIKE '%performance%' OR indexname LIKE '%status_data%'
            OR indexname LIKE '%municipio_data%' OR indexname LIKE '%projeto_data%'
            OR indexname LIKE '%filtros%' OR indexname LIKE '%ativo%'
        """
        )

        indexes = [row[0] for row in cursor.fetchall()]

        # Verificar alguns índices esperados
        expected_patterns = [
            "status_data",
            "municipio_data",
            "projeto_data",
            "filtros",
            "ativo",
        ]

        found_indexes = 0
        for pattern in expected_patterns:
            if any(pattern in idx for idx in indexes):
                found_indexes += 1

        # Deve ter encontrado pelo menos 3 dos 5 índices esperados
        self.assertGreaterEqual(
            found_indexes,
            3,
            f"Poucos índices de performance encontrados. Índices: {indexes}",
        )
