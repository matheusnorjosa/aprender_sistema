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


class DashboardStatsAPITestCase(TestCase):
    """Testes para a API de estatísticas do dashboard principal"""
    
    def setUp(self):
        """Configuração inicial para os testes da API"""
        self.user = User.objects.create_user(
            username='api_test_user',
            email='api@test.com',
            password='testpass123',
            papel='coordenador'
        )
        
        self.projeto = Projeto.objects.create(
            nome='Projeto API Teste',
            descricao='Descrição do projeto para testes da API'
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
            nome='Workshop API',
            online=False
        )
        
        self.formador1 = Formador.objects.create(
            nome='João API',
            email='joao.api@test.com',
            ativo=True
        )
        
        self.formador2 = Formador.objects.create(
            nome='Maria API',
            email='maria.api@test.com',
            ativo=True
        )
        
        self.formador_inativo = Formador.objects.create(
            nome='Pedro Inativo',
            email='pedro.inativo@test.com',
            ativo=False
        )
        
        self.client = Client()
        
    def test_dashboard_stats_api_requires_login(self):
        """API deve exigir autenticação"""
        url = reverse('core:dashboard_stats_api')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect para login
        
    def test_dashboard_stats_api_json_schema(self):
        """API deve retornar JSON com schema esperado"""
        self.client.login(username='api_test_user', password='testpass123')
        url = reverse('core:dashboard_stats_api')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        data = json.loads(response.content)
        
        # Verificar estrutura do JSON
        self.assertIn('timestamp', data)
        self.assertIn('periodo_referencia', data)
        self.assertIn('estatisticas', data)
        self.assertIn('meta', data)
        
        # Verificar campos das estatísticas
        stats = data['estatisticas']
        self.assertIn('eventos_mes', stats)
        self.assertIn('formadores_ativos', stats)
        self.assertIn('solicitacoes_pendentes', stats)
        self.assertIn('municipios_atendidos', stats)
        
        # Verificar tipos de dados
        self.assertIsInstance(stats['eventos_mes'], int)
        self.assertIsInstance(stats['formadores_ativos'], int)
        self.assertIsInstance(stats['solicitacoes_pendentes'], int)
        self.assertIsInstance(stats['municipios_atendidos'], int)
        
        # Verificar metadados
        meta = data['meta']
        self.assertEqual(meta['fonte'], 'dados_reais_banco')
        self.assertEqual(meta['cache_ttl'], 300)
        self.assertEqual(meta['usuario'], 'api_test_user')
        
    def test_eventos_mes_calculation(self):
        """Teste do cálculo de eventos do mês"""
        self.client.login(username='api_test_user', password='testpass123')
        
        agora = timezone.now()
        inicio_mes = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Criar evento aprovado no mês atual
        solicitacao_mes = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto,
            municipio=self.municipio1,
            tipo_evento=self.tipo_evento,
            titulo_evento='Evento do Mês',
            data_inicio=agora,
            data_fim=agora + timedelta(hours=2),
            status=SolicitacaoStatus.APROVADO
        )
        solicitacao_mes.formadores.add(self.formador1)
        
        # Criar evento aprovado do mês passado (não deve contar)
        mes_passado = agora - timedelta(days=35)
        solicitacao_mes_passado = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto,
            municipio=self.municipio1,
            tipo_evento=self.tipo_evento,
            titulo_evento='Evento Mês Passado',
            data_inicio=mes_passado,
            data_fim=mes_passado + timedelta(hours=2),
            status=SolicitacaoStatus.APROVADO
        )
        solicitacao_mes_passado.formadores.add(self.formador1)
        
        # Criar evento pendente no mês (não deve contar)
        solicitacao_pendente = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto,
            municipio=self.municipio1,
            tipo_evento=self.tipo_evento,
            titulo_evento='Evento Pendente',
            data_inicio=agora + timedelta(days=5),
            data_fim=agora + timedelta(days=5, hours=2),
            status=SolicitacaoStatus.PENDENTE
        )
        solicitacao_pendente.formadores.add(self.formador1)
        
        url = reverse('core:dashboard_stats_api')
        response = self.client.get(url)
        data = json.loads(response.content)
        
        # Deve contar apenas 1 evento (aprovado do mês atual)
        self.assertEqual(data['estatisticas']['eventos_mes'], 1)
        
    def test_formadores_ativos_count(self):
        """Teste da contagem de formadores ativos"""
        self.client.login(username='api_test_user', password='testpass123')
        
        url = reverse('core:dashboard_stats_api')
        response = self.client.get(url)
        data = json.loads(response.content)
        
        # Deve contar apenas formadores ativos (2)
        self.assertEqual(data['estatisticas']['formadores_ativos'], 2)
        
    def test_solicitacoes_pendentes_count(self):
        """Teste da contagem de solicitações pendentes"""
        self.client.login(username='api_test_user', password='testpass123')
        
        # Criar algumas solicitações com diferentes status
        agora = timezone.now()
        
        # Pendente
        solicitacao_pendente = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto,
            municipio=self.municipio1,
            tipo_evento=self.tipo_evento,
            titulo_evento='Pendente 1',
            data_inicio=agora + timedelta(days=1),
            data_fim=agora + timedelta(days=1, hours=2),
            status=SolicitacaoStatus.PENDENTE
        )
        solicitacao_pendente.formadores.add(self.formador1)
        
        # Aprovada (não deve contar)
        solicitacao_aprovada = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto,
            municipio=self.municipio1,
            tipo_evento=self.tipo_evento,
            titulo_evento='Aprovada 1',
            data_inicio=agora + timedelta(days=2),
            data_fim=agora + timedelta(days=2, hours=2),
            status=SolicitacaoStatus.APROVADO
        )
        solicitacao_aprovada.formadores.add(self.formador1)
        
        url = reverse('core:dashboard_stats_api')
        response = self.client.get(url)
        data = json.loads(response.content)
        
        # Deve contar apenas 1 pendente
        self.assertEqual(data['estatisticas']['solicitacoes_pendentes'], 1)
        
    def test_municipios_atendidos_calculation(self):
        """Teste do cálculo de municípios atendidos (últimos 3 meses)"""
        self.client.login(username='api_test_user', password='testpass123')
        
        agora = timezone.now()
        
        # Evento no último trimestre - Município 1
        evento_trimestre_sp = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto,
            municipio=self.municipio1,  # São Paulo
            tipo_evento=self.tipo_evento,
            titulo_evento='Evento SP Trimestre',
            data_inicio=agora - timedelta(days=60),
            data_fim=agora - timedelta(days=60) + timedelta(hours=2),
            status=SolicitacaoStatus.APROVADO
        )
        evento_trimestre_sp.formadores.add(self.formador1)
        
        # Evento no último trimestre - Município 2
        evento_trimestre_rj = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto,
            municipio=self.municipio2,  # Rio de Janeiro
            tipo_evento=self.tipo_evento,
            titulo_evento='Evento RJ Trimestre',
            data_inicio=agora - timedelta(days=30),
            data_fim=agora - timedelta(days=30) + timedelta(hours=2),
            status=SolicitacaoStatus.APROVADO
        )
        evento_trimestre_rj.formadores.add(self.formador2)
        
        # Evento muito antigo (não deve contar)
        evento_antigo = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto,
            municipio=self.municipio1,
            tipo_evento=self.tipo_evento,
            titulo_evento='Evento Muito Antigo',
            data_inicio=agora - timedelta(days=150),
            data_fim=agora - timedelta(days=150) + timedelta(hours=2),
            status=SolicitacaoStatus.APROVADO
        )
        evento_antigo.formadores.add(self.formador1)
        
        url = reverse('core:dashboard_stats_api')
        response = self.client.get(url)
        data = json.loads(response.content)
        
        # Deve contar 2 municípios distintos nos últimos 3 meses
        self.assertEqual(data['estatisticas']['municipios_atendidos'], 2)