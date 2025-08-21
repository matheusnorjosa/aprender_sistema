from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import json
from core.models import (
    Solicitacao, SolicitacaoStatus, Projeto, Municipio, TipoEvento, 
    Formador
)

User = get_user_model()


class DashboardFiltersTestCase(TestCase):
    """Testes para os filtros da API de estatísticas do dashboard"""
    
    def setUp(self):
        """Configuração inicial para os testes dos filtros"""
        self.user = User.objects.create_user(
            username='filter_test_user',
            email='filter@test.com',
            password='testpass123',
            papel='coordenador'
        )
        
        self.projeto1 = Projeto.objects.create(
            nome='Projeto Alpha',
            descricao='Primeiro projeto'
        )
        
        self.projeto2 = Projeto.objects.create(
            nome='Projeto Beta',
            descricao='Segundo projeto'
        )
        
        self.municipio1 = Municipio.objects.create(
            nome='São Paulo',
            uf='SP'
        )
        
        self.municipio2 = Municipio.objects.create(
            nome='Rio de Janeiro',
            uf='RJ'
        )
        
        self.tipo_evento = TipoEvento.objects.create(
            nome='Workshop Filtros',
            online=False
        )
        
        self.formador = Formador.objects.create(
            nome='João Filtros',
            email='joao.filtros@test.com',
            ativo=True
        )
        
        self.client = Client()
        
        # Criar eventos de teste
        agora = timezone.now()
        
        # Evento no projeto 1, município 1 (última semana)
        self.evento1 = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto1,
            municipio=self.municipio1,
            tipo_evento=self.tipo_evento,
            titulo_evento='Evento Projeto Alpha SP',
            data_inicio=agora - timedelta(days=5),
            data_fim=agora - timedelta(days=5) + timedelta(hours=2),
            status=SolicitacaoStatus.APROVADO
        )
        self.evento1.formadores.add(self.formador)
        
        # Evento no projeto 2, município 2 (último mês)
        self.evento2 = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto2,
            municipio=self.municipio2,
            tipo_evento=self.tipo_evento,
            titulo_evento='Evento Projeto Beta RJ',
            data_inicio=agora - timedelta(days=20),
            data_fim=agora - timedelta(days=20) + timedelta(hours=2),
            status=SolicitacaoStatus.APROVADO
        )
        self.evento2.formadores.add(self.formador)
        
        # Evento muito antigo (não deve aparecer nos filtros recentes)
        self.evento3 = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto1,
            municipio=self.municipio1,
            tipo_evento=self.tipo_evento,
            titulo_evento='Evento Muito Antigo',
            data_inicio=agora - timedelta(days=400),
            data_fim=agora - timedelta(days=400) + timedelta(hours=2),
            status=SolicitacaoStatus.APROVADO
        )
        self.evento3.formadores.add(self.formador)
        
    def test_filter_by_period_7_days(self):
        """Teste de filtro por período - últimos 7 dias"""
        self.client.login(username='filter_test_user', password='testpass123')
        
        url = reverse('core:dashboard_stats_api')
        response = self.client.get(url, {'periodo': '7'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        # Deve contar apenas o evento1 (último dia 5)
        self.assertEqual(data['estatisticas']['eventos_periodo'], 1)
        self.assertEqual(data['filtros']['periodo_dias'], 7)
        self.assertEqual(data['periodo_referencia']['eventos_periodo'], 'últimos 7 dias')
        
    def test_filter_by_period_30_days(self):
        """Teste de filtro por período - últimos 30 dias"""
        self.client.login(username='filter_test_user', password='testpass123')
        
        url = reverse('core:dashboard_stats_api')
        response = self.client.get(url, {'periodo': '30'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        # Deve contar evento1 e evento2 (ambos nos últimos 30 dias)
        self.assertEqual(data['estatisticas']['eventos_periodo'], 2)
        self.assertEqual(data['filtros']['periodo_dias'], 30)
        
    def test_filter_by_project(self):
        """Teste de filtro por projeto"""
        self.client.login(username='filter_test_user', password='testpass123')
        
        url = reverse('core:dashboard_stats_api')
        response = self.client.get(url, {
            'periodo': '365',  # Último ano para pegar todos
            'projeto': str(self.projeto1.id)
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        # Deve contar apenas eventos do projeto1 (evento1 e evento3)
        self.assertEqual(data['estatisticas']['eventos_periodo'], 2)
        self.assertEqual(data['filtros']['projeto_id'], str(self.projeto1.id))
        self.assertIn('Projeto: Projeto Alpha', data['filtros']['filtros_aplicados'])
        
    def test_filter_by_municipality(self):
        """Teste de filtro por município"""
        self.client.login(username='filter_test_user', password='testpass123')
        
        url = reverse('core:dashboard_stats_api')
        response = self.client.get(url, {
            'periodo': '365',  # Último ano para pegar todos
            'municipio': str(self.municipio2.id)
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        # Deve contar apenas eventos no municipio2 (evento2)
        self.assertEqual(data['estatisticas']['eventos_periodo'], 1)
        self.assertEqual(data['filtros']['municipio_id'], str(self.municipio2.id))
        self.assertIn('Município: Rio de Janeiro/RJ', data['filtros']['filtros_aplicados'])
        
    def test_combined_filters(self):
        """Teste de combinação de filtros"""
        self.client.login(username='filter_test_user', password='testpass123')
        
        url = reverse('core:dashboard_stats_api')
        response = self.client.get(url, {
            'periodo': '30',
            'projeto': str(self.projeto1.id),
            'municipio': str(self.municipio1.id)
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        # Deve contar apenas evento1 (projeto1 + municipio1 + últimos 30 dias)
        self.assertEqual(data['estatisticas']['eventos_periodo'], 1)
        self.assertEqual(data['filtros']['periodo_dias'], 30)
        self.assertEqual(data['filtros']['projeto_id'], str(self.projeto1.id))
        self.assertEqual(data['filtros']['municipio_id'], str(self.municipio1.id))
        
        # Verificar filtros aplicados
        filtros = data['filtros']['filtros_aplicados']
        self.assertIn('Projeto: Projeto Alpha', filtros)
        self.assertIn('Município: São Paulo/SP', filtros)
        
    def test_invalid_filters(self):
        """Teste de filtros inválidos"""
        self.client.login(username='filter_test_user', password='testpass123')
        
        url = reverse('core:dashboard_stats_api')
        response = self.client.get(url, {
            'periodo': 'invalid',
            'projeto': 'invalid-uuid',
            'municipio': 'invalid-uuid'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        # Deve usar valores padrão quando filtros são inválidos
        self.assertEqual(data['filtros']['periodo_dias'], 30)  # padrão
        self.assertIsNone(data['filtros']['projeto_id'])
        self.assertIsNone(data['filtros']['municipio_id'])
        self.assertEqual(data['filtros']['filtros_aplicados'], [])
        
    def test_municipalities_count_respects_project_filter(self):
        """Teste se contagem de municípios respeita filtro de projeto"""
        self.client.login(username='filter_test_user', password='testpass123')
        
        url = reverse('core:dashboard_stats_api')
        
        # Sem filtro de projeto - deve contar 2 municípios
        response = self.client.get(url, {'periodo': '365'})
        data = json.loads(response.content)
        self.assertEqual(data['estatisticas']['municipios_atendidos'], 2)
        
        # Com filtro de projeto1 - deve contar apenas 1 município
        response = self.client.get(url, {
            'periodo': '365',
            'projeto': str(self.projeto1.id)
        })
        data = json.loads(response.content)
        self.assertEqual(data['estatisticas']['municipios_atendidos'], 1)
        
    def test_meta_com_filtros_flag(self):
        """Teste da flag meta.com_filtros"""
        self.client.login(username='filter_test_user', password='testpass123')
        
        url = reverse('core:dashboard_stats_api')
        
        # Sem filtros
        response = self.client.get(url)
        data = json.loads(response.content)
        self.assertFalse(data['meta']['com_filtros'])
        
        # Com filtros
        response = self.client.get(url, {'projeto': str(self.projeto1.id)})
        data = json.loads(response.content)
        self.assertTrue(data['meta']['com_filtros'])