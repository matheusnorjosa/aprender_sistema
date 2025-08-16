from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from core.models import (
    Solicitacao, SolicitacaoStatus, Projeto, Municipio, TipoEvento, 
    Formador, DisponibilidadeFormadores
)
from core.forms import SolicitacaoForm

User = get_user_model()


class SolicitacaoModelTest(TestCase):
    """Testes para o modelo Solicitacao"""
    
    def setUp(self):
        """Configuração inicial para os testes"""
        self.user = User.objects.create_user(
            username='coord_test',
            email='coord@test.com',
            password='testpass123',
            papel='coordenador'
        )
        
        self.projeto = Projeto.objects.create(
            nome='Projeto Teste',
            descricao='Descrição do projeto teste'
        )
        
        self.municipio = Municipio.objects.create(
            nome='São Paulo',
            uf='SP'
        )
        
        self.tipo_evento = TipoEvento.objects.create(
            nome='Workshop',
            online=False
        )
        
        self.formador = Formador.objects.create(
            nome='João Silva',
            email='joao@test.com',
            area_atuacao='Matemática'
        )
    
    def test_create_solicitacao(self):
        """Testa a criação de uma solicitação"""
        futuro = timezone.now() + timedelta(days=7)
        solicitacao = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento='Evento Teste',
            data_inicio=futuro,
            data_fim=futuro + timedelta(hours=2),
            numero_encontro_formativo='1º Encontro',
            coordenador_acompanha=True,
            observacoes='Observação teste'
        )
        
        self.assertEqual(solicitacao.titulo_evento, 'Evento Teste')
        self.assertEqual(solicitacao.status, SolicitacaoStatus.PENDENTE)
        self.assertEqual(str(solicitacao), f"Evento Teste ({futuro:%d/%m/%Y %H:%M})")
    
    def test_solicitacao_ordering(self):
        """Testa a ordenação das solicitações"""
        futuro1 = timezone.now() + timedelta(days=7)
        futuro2 = timezone.now() + timedelta(days=8)
        
        sol1 = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento='Evento 1',
            data_inicio=futuro1,
            data_fim=futuro1 + timedelta(hours=2)
        )
        
        sol2 = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento='Evento 2',
            data_inicio=futuro2,
            data_fim=futuro2 + timedelta(hours=2)
        )
        
        # As solicitações devem ser ordenadas por data_solicitacao decrescente
        solicitacoes = list(Solicitacao.objects.all())
        self.assertEqual(solicitacoes[0], sol2)  # Mais recente primeiro
        self.assertEqual(solicitacoes[1], sol1)


class SolicitacaoFormTest(TestCase):
    """Testes para o formulário SolicitacaoForm"""
    
    def setUp(self):
        """Configuração inicial para os testes"""
        self.projeto = Projeto.objects.create(nome='Projeto Teste')
        self.municipio = Municipio.objects.create(nome='São Paulo', uf='SP')
        self.tipo_evento = TipoEvento.objects.create(nome='Workshop')
        self.formador = Formador.objects.create(
            nome='João Silva',
            email='joao@test.com'
        )
        
        self.valid_data = {
            'projeto': self.projeto.id,
            'municipio': self.municipio.id,
            'tipo_evento': self.tipo_evento.id,
            'titulo_evento': 'Evento Teste',
            'data_inicio': (timezone.now() + timedelta(days=7)).strftime('%Y-%m-%dT%H:%M'),
            'data_fim': (timezone.now() + timedelta(days=7, hours=2)).strftime('%Y-%m-%dT%H:%M'),
            'numero_encontro_formativo': '1º Encontro',
            'coordenador_acompanha': True,
            'observacoes': 'Observação teste',
            'formadores': [self.formador.id]
        }
    
    def test_valid_form(self):
        """Testa formulário válido"""
        form = SolicitacaoForm(data=self.valid_data)
        self.assertTrue(form.is_valid(), f"Formulário deveria ser válido. Erros: {form.errors}")
    
    def test_data_fim_before_inicio(self):
        """Testa validação quando data fim é antes da data início"""
        data = self.valid_data.copy()
        data['data_inicio'] = (timezone.now() + timedelta(days=7, hours=2)).strftime('%Y-%m-%dT%H:%M')
        data['data_fim'] = (timezone.now() + timedelta(days=7)).strftime('%Y-%m-%dT%H:%M')
        
        form = SolicitacaoForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('A data/hora de término deve ser maior que a de início', str(form.errors))
    
    def test_minimum_duration(self):
        """Testa validação de duração mínima"""
        data = self.valid_data.copy()
        futuro = timezone.now() + timedelta(days=7)
        data['data_inicio'] = futuro.strftime('%Y-%m-%dT%H:%M')
        data['data_fim'] = (futuro + timedelta(minutes=15)).strftime('%Y-%m-%dT%H:%M')
        
        form = SolicitacaoForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('O evento deve ter duração mínima de 30 minutos', str(form.errors))
    
    def test_past_date_validation(self):
        """Testa validação de data no passado"""
        data = self.valid_data.copy()
        passado = timezone.now() - timedelta(days=1)
        data['data_inicio'] = passado.strftime('%Y-%m-%dT%H:%M')
        data['data_fim'] = (passado + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M')
        
        form = SolicitacaoForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('A data de início deve ser no futuro', str(form.errors))
    
    def test_titulo_too_short(self):
        """Testa validação de título muito curto"""
        data = self.valid_data.copy()
        data['titulo_evento'] = 'AB'  # Menos de 3 caracteres
        
        form = SolicitacaoForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('O título do evento deve ter pelo menos 3 caracteres', str(form.errors))
    
    def test_formadores_required(self):
        """Testa que formadores são obrigatórios"""
        data = self.valid_data.copy()
        data['formadores'] = []
        
        form = SolicitacaoForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('formadores', form.errors)
    
    def test_conflict_with_availability(self):
        """Testa detecção de conflito com disponibilidade de formadores"""
        # Criar bloqueio de disponibilidade
        futuro = timezone.now() + timedelta(days=7)
        DisponibilidadeFormadores.objects.create(
            formador=self.formador,
            data_bloqueio=futuro.date(),
            hora_inicio=futuro.time(),
            hora_fim=(futuro + timedelta(hours=1)).time(),
            tipo_bloqueio='Total',
            motivo='Indisponível'
        )
        
        data = self.valid_data.copy()
        data['data_inicio'] = futuro.strftime('%Y-%m-%dT%H:%M')
        data['data_fim'] = (futuro + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M')
        
        form = SolicitacaoForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('Conflitos de disponibilidade', str(form.errors))


class SolicitacaoViewTest(TestCase):
    """Testes para as views relacionadas à solicitação"""
    
    def setUp(self):
        """Configuração inicial para os testes"""
        self.client = Client()
        
        self.coordenador = User.objects.create_user(
            username='coordenador',
            email='coord@test.com',
            password='testpass123',
            papel='coordenador'
        )
        
        self.formador_user = User.objects.create_user(
            username='formador',
            email='formador@test.com',
            password='testpass123',
            papel='formador'
        )
        
        self.projeto = Projeto.objects.create(nome='Projeto Teste')
        self.municipio = Municipio.objects.create(nome='São Paulo', uf='SP')
        self.tipo_evento = TipoEvento.objects.create(nome='Workshop')
        self.formador = Formador.objects.create(
            nome='João Silva',
            email='joao@test.com'
        )
    
    def test_access_without_login(self):
        """Testa acesso sem login"""
        url = reverse('core:solicitar_evento')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirecionamento para login
    
    def test_access_with_wrong_role(self):
        """Testa acesso com papel incorreto"""
        self.client.login(username='formador', password='testpass123')
        url = reverse('core:solicitar_evento')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)  # Acesso negado
    
    def test_access_with_coordenador(self):
        """Testa acesso com papel correto (coordenador)"""
        self.client.login(username='coordenador', password='testpass123')
        url = reverse('core:solicitar_evento')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Solicitar Evento')
    
    def test_form_submission_valid(self):
        """Testa submissão válida do formulário"""
        self.client.login(username='coordenador', password='testpass123')
        
        futuro = timezone.now() + timedelta(days=7)
        data = {
            'projeto': self.projeto.id,
            'municipio': self.municipio.id,
            'tipo_evento': self.tipo_evento.id,
            'titulo_evento': 'Evento Teste',
            'data_inicio': futuro.strftime('%Y-%m-%dT%H:%M'),
            'data_fim': (futuro + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M'),
            'numero_encontro_formativo': '1º Encontro',
            'coordenador_acompanha': True,
            'observacoes': 'Observação teste',
            'formadores': [self.formador.id]
        }
        
        url = reverse('core:solicitar_evento')
        response = self.client.post(url, data)
        
        # Deve redirecionar para página de sucesso
        self.assertEqual(response.status_code, 302)
        
        # Verifica se a solicitação foi criada
        self.assertTrue(Solicitacao.objects.filter(titulo_evento='Evento Teste').exists())
        
        # Verifica se o usuário solicitante foi definido corretamente
        solicitacao = Solicitacao.objects.get(titulo_evento='Evento Teste')
        self.assertEqual(solicitacao.usuario_solicitante, self.coordenador)
    
    def test_success_page(self):
        """Testa a página de sucesso"""
        self.client.login(username='coordenador', password='testpass123')
        url = reverse('core:solicitacao_ok')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class ConflictDetectionTest(TestCase):
    """Testes específicos para detecção de conflitos"""
    
    def setUp(self):
        """Configuração inicial para os testes"""
        self.user = User.objects.create_user(
            username='coord_test',
            email='coord@test.com',
            password='testpass123',
            papel='coordenador'
        )
        
        self.projeto = Projeto.objects.create(nome='Projeto Teste')
        self.municipio = Municipio.objects.create(nome='São Paulo', uf='SP')
        self.tipo_evento = TipoEvento.objects.create(nome='Workshop')
        
        self.formador1 = Formador.objects.create(
            nome='João Silva',
            email='joao@test.com'
        )
        
        self.formador2 = Formador.objects.create(
            nome='Maria Santos',
            email='maria@test.com'
        )
    
    def test_conflict_with_approved_request(self):
        """Testa conflito com solicitação já aprovada"""
        # Criar solicitação aprovada usando timezone local (São Paulo)
        from django.utils import timezone as tz
        now_local = tz.localtime(tz.now())
        futuro = now_local.replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=7)
        solicitacao_aprovada = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento='Evento Aprovado',
            data_inicio=futuro,
            data_fim=futuro + timedelta(hours=2),
            status=SolicitacaoStatus.APROVADO
        )
        solicitacao_aprovada.formadores.add(self.formador1)
        solicitacao_aprovada.save()
        
        # Verificar que a solicitação foi realmente criada e associada
        self.assertEqual(solicitacao_aprovada.formadores.count(), 1)
        self.assertEqual(solicitacao_aprovada.formadores.first(), self.formador1)
        
        # Tentar criar nova solicitação com conflito - mesmo formador, horário sobreposto
        conflicting_start = futuro + timedelta(minutes=30)
        conflicting_end = futuro + timedelta(hours=1, minutes=30)
        
        data = {
            'projeto': self.projeto.id,
            'municipio': self.municipio.id,
            'tipo_evento': self.tipo_evento.id,
            'titulo_evento': 'Evento Conflitante',
            'data_inicio': conflicting_start.strftime('%Y-%m-%dT%H:%M'),
            'data_fim': conflicting_end.strftime('%Y-%m-%dT%H:%M'),
            'formadores': [self.formador1.id]
        }
        
        form = SolicitacaoForm(data=data)
        self.assertFalse(form.is_valid(), f"Form should be invalid due to conflict. Errors: {form.errors}")
        self.assertIn('Conflitos com solicitações aprovadas', str(form.errors))
    
    def test_no_conflict_different_formadores(self):
        """Testa que não há conflito com formadores diferentes"""
        # Criar solicitação aprovada com formador1
        futuro = timezone.now() + timedelta(days=7)
        solicitacao_aprovada = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento='Evento Aprovado',
            data_inicio=futuro,
            data_fim=futuro + timedelta(hours=2),
            status=SolicitacaoStatus.APROVADO
        )
        solicitacao_aprovada.formadores.add(self.formador1)
        
        # Criar nova solicitação com formador2 (sem conflito)
        data = {
            'projeto': self.projeto.id,
            'municipio': self.municipio.id,
            'tipo_evento': self.tipo_evento.id,
            'titulo_evento': 'Evento Sem Conflito',
            'data_inicio': (futuro + timedelta(minutes=30)).strftime('%Y-%m-%dT%H:%M'),
            'data_fim': (futuro + timedelta(hours=3)).strftime('%Y-%m-%dT%H:%M'),
            'formadores': [self.formador2.id]
        }
        
        form = SolicitacaoForm(data=data)
        self.assertTrue(form.is_valid(), f"Formulário deveria ser válido. Erros: {form.errors}")


class PermissionTest(TestCase):
    """Testes de permissões e controle de acesso"""
    
    def setUp(self):
        """Configuração inicial para os testes"""
        self.client = Client()
        
        # Criar usuários com diferentes papéis
        self.coordenador = User.objects.create_user(
            username='coordenador',
            password='testpass123',
            papel='coordenador'
        )
        
        self.superintendencia = User.objects.create_user(
            username='superintendencia',
            password='testpass123',
            papel='superintendencia'
        )
        
        self.formador = User.objects.create_user(
            username='formador',
            password='testpass123',
            papel='formador'
        )
        
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
    
    def test_coordenador_can_access(self):
        """Testa que coordenador pode acessar o formulário"""
        self.client.login(username='coordenador', password='testpass123')
        url = reverse('core:solicitar_evento')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_superintendencia_cannot_access(self):
        """Testa que superintendência não pode acessar o formulário"""
        self.client.login(username='superintendencia', password='testpass123')
        url = reverse('core:solicitar_evento')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
    
    def test_formador_cannot_access(self):
        """Testa que formador não pode acessar o formulário"""
        self.client.login(username='formador', password='testpass123')
        url = reverse('core:solicitar_evento')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
    
    def test_admin_can_access(self):
        """Testa que admin pode acessar o formulário"""
        self.client.login(username='admin', password='testpass123')
        url = reverse('core:solicitar_evento')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
