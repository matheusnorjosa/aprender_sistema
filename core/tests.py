from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from core.models import (
    Solicitacao, SolicitacaoStatus, Projeto, Municipio, TipoEvento, 
    Formador, DisponibilidadeFormadores, Aprovacao, AprovacaoStatus, LogAuditoria
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


# =========================
# RF03 - Specific Tests
# =========================

class RF03TimezoneTest(TestCase):
    """RF03: Testes específicos para timezone America/Fortaleza"""
    
    def test_timezone_setting(self):
        """RF03: Verifica se o timezone está configurado como America/Fortaleza"""
        from django.conf import settings
        self.assertEqual(settings.TIME_ZONE, 'America/Fortaleza')
        self.assertTrue(settings.USE_TZ)
    
    def test_timezone_correctness_in_conflicts(self):
        """RF03: Verifica se o sistema usa corretamente o timezone local"""
        from django.utils import timezone as tz
        from datetime import timezone as dt_timezone, timedelta
        
        # Verificar se timezone.now() retorna Fortaleza timezone quando localizado
        now_utc = tz.now()
        now_local = tz.localtime(now_utc)
        
        # Fortaleza é UTC-3 (pode ser UTC-2 durante horário de verão)
        expected_offset_hours = -3  # UTC-3
        expected_offset = dt_timezone(timedelta(hours=expected_offset_hours))
        
        # Verificar se o offset está correto (UTC-3 ou UTC-2 para horário de verão)
        actual_offset_seconds = now_local.utcoffset().total_seconds()
        expected_offset_seconds = expected_offset.utcoffset(None).total_seconds()
        
        # Aceitar tanto UTC-3 quanto UTC-2 (horário de verão)
        self.assertIn(actual_offset_seconds, [expected_offset_seconds, expected_offset_seconds + 3600])


class RF03ExactBoundariesTest(TestCase):
    """RF03: Testes para limites exatos de conflitos"""
    
    def setUp(self):
        """Configuração para testes de limites exatos"""
        self.user = User.objects.create_user(
            username='coord_boundary_test',
            email='coord@boundary.com',
            password='testpass123',
            papel='coordenador'
        )
        
        self.projeto = Projeto.objects.create(nome='Projeto Boundary')
        self.municipio = Municipio.objects.create(nome='Fortaleza', uf='CE')
        self.tipo_evento = TipoEvento.objects.create(nome='Workshop Boundary')
        self.formador = Formador.objects.create(
            nome='Formador Boundary',
            email='boundary@test.com'
        )
    
    def test_exact_boundary_no_overlap_end_equals_start(self):
        """RF03: Não deve haver conflito quando end_time == start_time do próximo"""
        from django.utils import timezone as tz
        
        # Evento aprovado: 10:00 - 12:00
        now_local = tz.localtime(tz.now())
        base_time = now_local.replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=7)
        
        approved_end = base_time + timedelta(hours=2)  # 12:00
        
        solicitacao_aprovada = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento='Evento Aprovado',
            data_inicio=base_time,
            data_fim=approved_end,
            status=SolicitacaoStatus.APROVADO
        )
        solicitacao_aprovada.formadores.add(self.formador)
        
        # Novo evento: 12:00 - 14:00 (exatamente quando o anterior termina)
        new_start = approved_end  # 12:00
        new_end = approved_end + timedelta(hours=2)  # 14:00
        
        data = {
            'projeto': self.projeto.id,
            'municipio': self.municipio.id,
            'tipo_evento': self.tipo_evento.id,
            'titulo_evento': 'Evento Sequencial',
            'data_inicio': new_start.strftime('%Y-%m-%dT%H:%M'),
            'data_fim': new_end.strftime('%Y-%m-%dT%H:%M'),
            'formadores': [self.formador.id]
        }
        
        form = SolicitacaoForm(data=data)
        self.assertTrue(form.is_valid(), "Não deve haver conflito quando eventos são sequenciais (fim == início)")
    
    def test_exact_boundary_overlap_by_one_minute(self):
        """RF03: Deve haver conflito com sobreposição de 1 minuto"""
        from django.utils import timezone as tz
        
        # Evento aprovado: 10:00 - 12:00
        now_local = tz.localtime(tz.now())
        base_time = now_local.replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=7)
        approved_end = base_time + timedelta(hours=2)
        
        solicitacao_aprovada = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento='Evento Aprovado',
            data_inicio=base_time,
            data_fim=approved_end,
            status=SolicitacaoStatus.APROVADO
        )
        solicitacao_aprovada.formadores.add(self.formador)
        
        # Novo evento: 11:59 - 14:00 (1 minuto de sobreposição)
        new_start = approved_end - timedelta(minutes=1)  # 11:59
        new_end = approved_end + timedelta(hours=2)  # 14:00
        
        data = {
            'projeto': self.projeto.id,
            'municipio': self.municipio.id,
            'tipo_evento': self.tipo_evento.id,
            'titulo_evento': 'Evento Conflitante',
            'data_inicio': new_start.strftime('%Y-%m-%dT%H:%M'),
            'data_fim': new_end.strftime('%Y-%m-%dT%H:%M'),
            'formadores': [self.formador.id]
        }
        
        form = SolicitacaoForm(data=data)
        self.assertFalse(form.is_valid(), "Deve haver conflito com sobreposição de 1 minuto")
        self.assertIn('Conflitos com solicitações aprovadas', str(form.errors))


class RF03MultiFormadorTest(TestCase):
    """RF03: Testes para conflitos com múltiplos formadores"""
    
    def setUp(self):
        """Configuração para testes multi-formador"""
        self.user = User.objects.create_user(
            username='coord_multi_test',
            email='coord@multi.com',
            password='testpass123',
            papel='coordenador'
        )
        
        self.projeto = Projeto.objects.create(nome='Projeto Multi')
        self.municipio = Municipio.objects.create(nome='Fortaleza', uf='CE')
        self.tipo_evento = TipoEvento.objects.create(nome='Workshop Multi')
        
        self.formador1 = Formador.objects.create(
            nome='Formador Alpha',
            email='alpha@test.com'
        )
        self.formador2 = Formador.objects.create(
            nome='Formador Beta',
            email='beta@test.com'
        )
        self.formador3 = Formador.objects.create(
            nome='Formador Gamma',
            email='gamma@test.com'
        )
    
    def test_conflict_when_any_formador_overlaps(self):
        """RF03: Deve detectar conflito se qualquer formador selecionado tiver conflito"""
        from django.utils import timezone as tz
        
        # Criar evento aprovado com formador2
        now_local = tz.localtime(tz.now())
        base_time = now_local.replace(hour=14, minute=0, second=0, microsecond=0) + timedelta(days=7)
        
        solicitacao_aprovada = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento='Evento com Beta',
            data_inicio=base_time,
            data_fim=base_time + timedelta(hours=2),
            status=SolicitacaoStatus.APROVADO
        )
        solicitacao_aprovada.formadores.add(self.formador2)
        
        # Tentar criar evento com formador1, formador2 e formador3
        # Apenas formador2 tem conflito, mas deve bloquear todo o evento
        conflicting_start = base_time + timedelta(minutes=30)
        conflicting_end = base_time + timedelta(hours=1, minutes=30)
        
        data = {
            'projeto': self.projeto.id,
            'municipio': self.municipio.id,
            'tipo_evento': self.tipo_evento.id,
            'titulo_evento': 'Evento Multi Conflitante',
            'data_inicio': conflicting_start.strftime('%Y-%m-%dT%H:%M'),
            'data_fim': conflicting_end.strftime('%Y-%m-%dT%H:%M'),
            'formadores': [self.formador1.id, self.formador2.id, self.formador3.id]
        }
        
        form = SolicitacaoForm(data=data)
        self.assertFalse(form.is_valid(), "Deve detectar conflito quando qualquer formador tem conflito")
        error_str = str(form.errors)
        self.assertIn('Conflitos com solicitações aprovadas', error_str)
        self.assertIn('Formador Beta', error_str, "Deve mencionar o formador em conflito")
    
    def test_no_conflict_with_different_formadores(self):
        """RF03: Não deve haver conflito quando formadores são diferentes"""
        from django.utils import timezone as tz
        
        # Criar evento aprovado com formador1
        now_local = tz.localtime(tz.now())
        base_time = now_local.replace(hour=14, minute=0, second=0, microsecond=0) + timedelta(days=7)
        
        solicitacao_aprovada = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento='Evento com Alpha',
            data_inicio=base_time,
            data_fim=base_time + timedelta(hours=2),
            status=SolicitacaoStatus.APROVADO
        )
        solicitacao_aprovada.formadores.add(self.formador1)
        
        # Criar evento no mesmo horário com formador2 e formador3 (sem conflito)
        data = {
            'projeto': self.projeto.id,
            'municipio': self.municipio.id,
            'tipo_evento': self.tipo_evento.id,
            'titulo_evento': 'Evento Paralelo',
            'data_inicio': base_time.strftime('%Y-%m-%dT%H:%M'),
            'data_fim': (base_time + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M'),
            'formadores': [self.formador2.id, self.formador3.id]
        }
        
        form = SolicitacaoForm(data=data)
        self.assertTrue(form.is_valid(), "Não deve haver conflito com formadores diferentes")


class RF03BloqueiosTest(TestCase):
    """RF03: Testes específicos para conflitos com bloqueios"""
    
    def setUp(self):
        """Configuração para testes de bloqueios"""
        self.user = User.objects.create_user(
            username='coord_bloqueio_test',
            email='coord@bloqueio.com',
            password='testpass123',
            papel='coordenador'
        )
        
        self.projeto = Projeto.objects.create(nome='Projeto Bloqueio')
        self.municipio = Municipio.objects.create(nome='Fortaleza', uf='CE')
        self.tipo_evento = TipoEvento.objects.create(nome='Workshop Bloqueio')
        self.formador = Formador.objects.create(
            nome='Formador Bloqueado',
            email='bloqueado@test.com'
        )
    
    def test_conflict_with_total_bloqueio(self):
        """RF03: Deve detectar conflito com bloqueio total"""
        from django.utils import timezone as tz
        from datetime import time
        
        # Criar bloqueio total para o formador
        now_local = tz.localtime(tz.now())
        blocked_date = (now_local + timedelta(days=7)).date()
        
        DisponibilidadeFormadores.objects.create(
            formador=self.formador,
            data_bloqueio=blocked_date,
            hora_inicio=time(0, 0),
            hora_fim=time(23, 59),
            tipo_bloqueio='Total',
            motivo='Indisponível'
        )
        
        # Tentar criar evento no dia bloqueado
        event_start = now_local.replace(
            year=blocked_date.year,
            month=blocked_date.month,
            day=blocked_date.day,
            hour=10,
            minute=0,
            second=0,
            microsecond=0
        )
        
        data = {
            'projeto': self.projeto.id,
            'municipio': self.municipio.id,
            'tipo_evento': self.tipo_evento.id,
            'titulo_evento': 'Evento em Dia Bloqueado',
            'data_inicio': event_start.strftime('%Y-%m-%dT%H:%M'),
            'data_fim': (event_start + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M'),
            'formadores': [self.formador.id]
        }
        
        form = SolicitacaoForm(data=data)
        self.assertFalse(form.is_valid(), "Deve detectar conflito com bloqueio total")
        error_str = str(form.errors)
        self.assertIn('Conflitos de disponibilidade', error_str)
        self.assertIn('Formador Bloqueado', error_str)
        self.assertIn('Total', error_str)
    
    def test_conflict_with_partial_bloqueio(self):
        """RF03: Deve detectar conflito com bloqueio parcial"""
        from django.utils import timezone as tz
        from datetime import time
        
        # Criar bloqueio parcial (14:00 - 16:00)
        now_local = tz.localtime(tz.now())
        blocked_date = (now_local + timedelta(days=7)).date()
        
        DisponibilidadeFormadores.objects.create(
            formador=self.formador,
            data_bloqueio=blocked_date,
            hora_inicio=time(14, 0),
            hora_fim=time(16, 0),
            tipo_bloqueio='Parcial',
            motivo='Reunião'
        )
        
        # Tentar criar evento que sobrepõe com o bloqueio (15:00 - 17:00)
        event_start = now_local.replace(
            year=blocked_date.year,
            month=blocked_date.month,
            day=blocked_date.day,
            hour=15,
            minute=0,
            second=0,
            microsecond=0
        )
        
        data = {
            'projeto': self.projeto.id,
            'municipio': self.municipio.id,
            'tipo_evento': self.tipo_evento.id,
            'titulo_evento': 'Evento Sobreposto',
            'data_inicio': event_start.strftime('%Y-%m-%dT%H:%M'),
            'data_fim': (event_start + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M'),
            'formadores': [self.formador.id]
        }
        
        form = SolicitacaoForm(data=data)
        self.assertFalse(form.is_valid(), "Deve detectar conflito com bloqueio parcial")
        error_str = str(form.errors)
        self.assertIn('Conflitos de disponibilidade', error_str)
        self.assertIn('14:00', error_str)  # Verificar apenas início
        self.assertIn('16:00', error_str)  # Verificar apenas fim
        self.assertIn('Parcial', error_str)
    
    def test_no_conflict_outside_bloqueio(self):
        """RF03: Não deve haver conflito fora do período de bloqueio"""
        from django.utils import timezone as tz
        from datetime import time
        
        # Criar bloqueio parcial (14:00 - 16:00)
        now_local = tz.localtime(tz.now())
        blocked_date = (now_local + timedelta(days=7)).date()
        
        DisponibilidadeFormadores.objects.create(
            formador=self.formador,
            data_bloqueio=blocked_date,
            hora_inicio=time(14, 0),
            hora_fim=time(16, 0),
            tipo_bloqueio='Parcial',
            motivo='Reunião'
        )
        
        # Criar evento fora do período de bloqueio (10:00 - 12:00)
        event_start = now_local.replace(
            year=blocked_date.year,
            month=blocked_date.month,
            day=blocked_date.day,
            hour=10,
            minute=0,
            second=0,
            microsecond=0
        )
        
        data = {
            'projeto': self.projeto.id,
            'municipio': self.municipio.id,
            'tipo_evento': self.tipo_evento.id,
            'titulo_evento': 'Evento Livre',
            'data_inicio': event_start.strftime('%Y-%m-%dT%H:%M'),
            'data_fim': (event_start + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M'),
            'formadores': [self.formador.id]
        }
        
        form = SolicitacaoForm(data=data)
        self.assertTrue(form.is_valid(), "Não deve haver conflito fora do período de bloqueio")


class RF03ErrorMessageTest(TestCase):
    """RF03: Testes para formato das mensagens de erro"""
    
    def setUp(self):
        """Configuração para testes de mensagens"""
        self.user = User.objects.create_user(
            username='coord_msg_test',
            email='coord@msg.com',
            password='testpass123',
            papel='coordenador'
        )
        
        self.projeto = Projeto.objects.create(nome='Projeto Mensagem')
        self.municipio = Municipio.objects.create(nome='Fortaleza', uf='CE')
        self.tipo_evento = TipoEvento.objects.create(nome='Workshop Mensagem')
        self.formador = Formador.objects.create(
            nome='João Silva Mensagem',
            email='joao.msg@test.com'
        )
    
    def test_error_message_includes_formador_names_and_intervals(self):
        """RF03: Mensagens de erro devem incluir nomes dos formadores e intervalos"""
        from django.utils import timezone as tz
        
        # Criar evento aprovado
        now_local = tz.localtime(tz.now())
        base_time = now_local.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=7)
        
        solicitacao_aprovada = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento='Workshop Matemática',
            data_inicio=base_time,
            data_fim=base_time + timedelta(hours=3),
            status=SolicitacaoStatus.APROVADO
        )
        solicitacao_aprovada.formadores.add(self.formador)
        
        # Criar evento conflitante
        conflicting_start = base_time + timedelta(hours=1)
        conflicting_end = base_time + timedelta(hours=4)
        
        data = {
            'projeto': self.projeto.id,
            'municipio': self.municipio.id,
            'tipo_evento': self.tipo_evento.id,
            'titulo_evento': 'Evento Conflitante',
            'data_inicio': conflicting_start.strftime('%Y-%m-%dT%H:%M'),
            'data_fim': conflicting_end.strftime('%Y-%m-%dT%H:%M'),
            'formadores': [self.formador.id]
        }
        
        form = SolicitacaoForm(data=data)
        self.assertFalse(form.is_valid())
        
        error_str = str(form.errors)
        
        # Verificar elementos obrigatórios na mensagem
        self.assertIn('Conflitos com solicitações aprovadas', error_str)
        self.assertIn('Workshop Matemática', error_str, "Deve incluir título do evento conflitante")
        self.assertIn('João Silva Mensagem', error_str, "Deve incluir nome do formador")
        
        # Verificar se contém horários (formato pode variar devido ao timezone)
        import re
        time_pattern = r'\d{2}:\d{2}'
        times_found = re.findall(time_pattern, error_str)
        self.assertGreaterEqual(len(times_found), 2, "Deve incluir pelo menos dois horários (início e fim)")
        
        # Verificar formato da data (dd/mm)
        expected_date = base_time.strftime('%d/%m')
        self.assertIn(expected_date, error_str, "Deve incluir data no formato dd/mm")


# =========================
# RF04 - Approval/Rejection Tests
# =========================

class RF04ApprovalModelTest(TestCase):
    """RF04: Testes para o modelo Aprovacao"""
    
    def setUp(self):
        """Configuração inicial para testes de aprovação"""
        self.coordenador = User.objects.create_user(
            username='coord_rf04',
            email='coord@rf04.com',
            password='testpass123',
            papel='coordenador'
        )
        
        self.superintendencia = User.objects.create_user(
            username='super_rf04',
            email='super@rf04.com',
            password='testpass123',
            papel='superintendencia'
        )
        
        self.projeto = Projeto.objects.create(nome='Projeto RF04')
        self.municipio = Municipio.objects.create(nome='Fortaleza', uf='CE')
        self.tipo_evento = TipoEvento.objects.create(nome='Workshop RF04')
        self.formador = Formador.objects.create(nome='Formador RF04', email='formador@rf04.com')
        
        # Criar solicitação pendente
        from django.utils import timezone as tz
        futuro = tz.localtime(tz.now()) + timedelta(days=7)
        self.solicitacao = Solicitacao.objects.create(
            usuario_solicitante=self.coordenador,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento='Evento RF04 Teste',
            data_inicio=futuro,
            data_fim=futuro + timedelta(hours=2),
            status=SolicitacaoStatus.PENDENTE
        )
        self.solicitacao.formadores.add(self.formador)
    
    def test_create_aprovacao(self):
        """RF04: Testa criação de registro de aprovação"""
        aprovacao = Aprovacao.objects.create(
            solicitacao=self.solicitacao,
            usuario_aprovador=self.superintendencia,
            status_decisao=AprovacaoStatus.APROVADO,
            justificativa='Evento aprovado conforme cronograma'
        )
        
        self.assertEqual(aprovacao.solicitacao, self.solicitacao)
        self.assertEqual(aprovacao.usuario_aprovador, self.superintendencia)
        self.assertEqual(aprovacao.status_decisao, AprovacaoStatus.APROVADO)
        self.assertEqual(aprovacao.justificativa, 'Evento aprovado conforme cronograma')
        self.assertIsNotNone(aprovacao.data_aprovacao)
    
    def test_aprovacao_str_representation(self):
        """RF04: Testa representação string do modelo Aprovacao"""
        aprovacao = Aprovacao.objects.create(
            solicitacao=self.solicitacao,
            usuario_aprovador=self.superintendencia,
            status_decisao=AprovacaoStatus.REPROVADO,
            justificativa='Conflito de agenda'
        )
        
        expected_str = f"{AprovacaoStatus.REPROVADO} — Evento RF04 Teste"
        self.assertEqual(str(aprovacao), expected_str)


class RF04PermissionTest(TestCase):
    """RF04: Testes de permissões para aprovação"""
    
    def setUp(self):
        """Configuração para testes de permissão"""
        self.client = Client()
        
        self.coordenador = User.objects.create_user(
            username='coordenador_perm',
            password='testpass123',
            papel='coordenador'
        )
        
        self.superintendencia = User.objects.create_user(
            username='superintendencia_perm',
            password='testpass123',
            papel='superintendencia'
        )
        
        self.formador = User.objects.create_user(
            username='formador_perm',
            password='testpass123',
            papel='formador'
        )
        
        self.admin = User.objects.create_superuser(
            username='admin_perm',
            email='admin@test.com',
            password='testpass123'
        )
        
        # Criar solicitação para testes
        projeto = Projeto.objects.create(nome='Projeto Perm')
        municipio = Municipio.objects.create(nome='Fortaleza', uf='CE')
        tipo_evento = TipoEvento.objects.create(nome='Workshop Perm')
        
        from django.utils import timezone as tz
        futuro = tz.localtime(tz.now()) + timedelta(days=7)
        self.solicitacao = Solicitacao.objects.create(
            usuario_solicitante=self.coordenador,
            projeto=projeto,
            municipio=municipio,
            tipo_evento=tipo_evento,
            titulo_evento='Evento Permissão',
            data_inicio=futuro,
            data_fim=futuro + timedelta(hours=2),
            status=SolicitacaoStatus.PENDENTE
        )
    
    def test_superintendencia_can_access_approval_list(self):
        """RF04: Superintendência pode acessar lista de aprovações"""
        self.client.login(username='superintendencia_perm', password='testpass123')
        url = reverse('core:aprovacoes_pendentes')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_coordenador_cannot_access_approval_list(self):
        """RF04: Coordenador não pode acessar lista de aprovações"""
        self.client.login(username='coordenador_perm', password='testpass123')
        url = reverse('core:aprovacoes_pendentes')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
    
    def test_formador_cannot_access_approval_list(self):
        """RF04: Formador não pode acessar lista de aprovações"""
        self.client.login(username='formador_perm', password='testpass123')
        url = reverse('core:aprovacoes_pendentes')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
    
    def test_admin_can_access_approval_list(self):
        """RF04: Admin pode acessar lista de aprovações"""
        self.client.login(username='admin_perm', password='testpass123')
        url = reverse('core:aprovacoes_pendentes')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_superintendencia_can_access_approval_detail(self):
        """RF04: Superintendência pode acessar detalhes para decisão"""
        self.client.login(username='superintendencia_perm', password='testpass123')
        url = reverse('core:aprovacao_detail', args=[self.solicitacao.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_coordenador_cannot_access_approval_detail(self):
        """RF04: Coordenador não pode acessar detalhes para decisão"""
        self.client.login(username='coordenador_perm', password='testpass123')
        url = reverse('core:aprovacao_detail', args=[self.solicitacao.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
    
    def test_unauthenticated_cannot_access(self):
        """RF04: Usuário não autenticado não pode acessar"""
        url = reverse('core:aprovacoes_pendentes')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect to login


class RF04ApprovalListTest(TestCase):
    """RF04: Testes para listagem de aprovações pendentes"""
    
    def setUp(self):
        """Configuração para testes de listagem"""
        self.client = Client()
        
        self.superintendencia = User.objects.create_user(
            username='super_list',
            password='testpass123',
            papel='superintendencia'
        )
        
        self.coordenador = User.objects.create_user(
            username='coord_list',
            password='testpass123',
            papel='coordenador'
        )
        
        self.projeto = Projeto.objects.create(nome='Projeto Lista')
        self.municipio = Municipio.objects.create(nome='Fortaleza', uf='CE')
        self.tipo_evento = TipoEvento.objects.create(nome='Workshop Lista')
        
        from django.utils import timezone as tz
        self.futuro = tz.localtime(tz.now()) + timedelta(days=7)
    
    def test_shows_only_pending_requests(self):
        """RF04: Lista mostra apenas solicitações pendentes"""
        # Criar solicitações com diferentes status
        pendente = Solicitacao.objects.create(
            usuario_solicitante=self.coordenador,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento='Evento Pendente',
            data_inicio=self.futuro,
            data_fim=self.futuro + timedelta(hours=2),
            status=SolicitacaoStatus.PENDENTE
        )
        
        aprovado = Solicitacao.objects.create(
            usuario_solicitante=self.coordenador,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento='Evento Aprovado',
            data_inicio=self.futuro + timedelta(days=1),
            data_fim=self.futuro + timedelta(days=1, hours=2),
            status=SolicitacaoStatus.APROVADO
        )
        
        reprovado = Solicitacao.objects.create(
            usuario_solicitante=self.coordenador,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento='Evento Reprovado',
            data_inicio=self.futuro + timedelta(days=2),
            data_fim=self.futuro + timedelta(days=2, hours=2),
            status=SolicitacaoStatus.REPROVADO
        )
        
        self.client.login(username='super_list', password='testpass123')
        url = reverse('core:aprovacoes_pendentes')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Evento Pendente')
        self.assertNotContains(response, 'Evento Aprovado')
        self.assertNotContains(response, 'Evento Reprovado')
    
    def test_search_functionality(self):
        """RF04: Funcionalidade de busca por título"""
        Solicitacao.objects.create(
            usuario_solicitante=self.coordenador,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento='Workshop Python',
            data_inicio=self.futuro,
            data_fim=self.futuro + timedelta(hours=2),
            status=SolicitacaoStatus.PENDENTE
        )
        
        Solicitacao.objects.create(
            usuario_solicitante=self.coordenador,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento='Seminário Django',
            data_inicio=self.futuro + timedelta(days=1),
            data_fim=self.futuro + timedelta(days=1, hours=2),
            status=SolicitacaoStatus.PENDENTE
        )
        
        self.client.login(username='super_list', password='testpass123')
        url = reverse('core:aprovacoes_pendentes')
        
        # Buscar por 'Python'
        response = self.client.get(url, {'q': 'Python'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Workshop Python')
        self.assertNotContains(response, 'Seminário Django')
        
        # Buscar por 'Django'
        response = self.client.get(url, {'q': 'Django'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Seminário Django')
        self.assertNotContains(response, 'Workshop Python')
    
    def test_pagination(self):
        """RF04: Teste de paginação da lista"""
        # Criar mais de 20 solicitações para testar paginação
        for i in range(25):
            Solicitacao.objects.create(
                usuario_solicitante=self.coordenador,
                projeto=self.projeto,
                municipio=self.municipio,
                tipo_evento=self.tipo_evento,
                titulo_evento=f'Evento {i+1}',
                data_inicio=self.futuro + timedelta(hours=i),
                data_fim=self.futuro + timedelta(hours=i+2),
                status=SolicitacaoStatus.PENDENTE
            )
        
        self.client.login(username='super_list', password='testpass123')
        url = reverse('core:aprovacoes_pendentes')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_paginated'])
        self.assertEqual(len(response.context['pendentes']), 20)  # paginate_by = 20


class RF04ApprovalWorkflowTest(TestCase):
    """RF04: Testes para fluxo completo de aprovação/reprovação"""
    
    def setUp(self):
        """Configuração para testes de workflow"""
        self.client = Client()
        
        self.superintendencia = User.objects.create_user(
            username='super_workflow',
            password='testpass123',
            papel='superintendencia'
        )
        
        self.coordenador = User.objects.create_user(
            username='coord_workflow',
            password='testpass123',
            papel='coordenador'
        )
        
        projeto = Projeto.objects.create(nome='Projeto Workflow')
        municipio = Municipio.objects.create(nome='Fortaleza', uf='CE')
        tipo_evento = TipoEvento.objects.create(nome='Workshop Workflow')
        formador = Formador.objects.create(nome='Formador Workflow', email='workflow@test.com')
        
        from django.utils import timezone as tz
        futuro = tz.localtime(tz.now()) + timedelta(days=7)
        self.solicitacao = Solicitacao.objects.create(
            usuario_solicitante=self.coordenador,
            projeto=projeto,
            municipio=municipio,
            tipo_evento=tipo_evento,
            titulo_evento='Evento Workflow',
            data_inicio=futuro,
            data_fim=futuro + timedelta(hours=2),
            status=SolicitacaoStatus.PENDENTE
        )
        self.solicitacao.formadores.add(formador)
    
    def test_approval_workflow(self):
        """RF04: Teste do fluxo completo de aprovação"""
        self.client.login(username='super_workflow', password='testpass123')
        
        # Acessar página de decisão
        url = reverse('core:aprovacao_detail', args=[self.solicitacao.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Submeter aprovação
        data = {
            'decisao': AprovacaoStatus.APROVADO,
            'justificativa': 'Evento aprovado conforme planejamento'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)  # Redirect após sucesso
        
        # Verificar mudanças no modelo
        self.solicitacao.refresh_from_db()
        self.assertEqual(self.solicitacao.status, SolicitacaoStatus.APROVADO)
        self.assertEqual(self.solicitacao.usuario_aprovador, self.superintendencia)
        self.assertIsNotNone(self.solicitacao.data_aprovacao_rejeicao)
        
        # Verificar criação do registro de aprovação
        aprovacao = Aprovacao.objects.get(solicitacao=self.solicitacao)
        self.assertEqual(aprovacao.usuario_aprovador, self.superintendencia)
        self.assertEqual(aprovacao.status_decisao, AprovacaoStatus.APROVADO)
        self.assertEqual(aprovacao.justificativa, 'Evento aprovado conforme planejamento')
        
        # Verificar log de auditoria
        self.assertTrue(LogAuditoria.objects.filter(
            usuario=self.superintendencia,
            acao__contains='RF04: Aprovado'
        ).exists())
    
    def test_rejection_workflow(self):
        """RF04: Teste do fluxo completo de reprovação"""
        self.client.login(username='super_workflow', password='testpass123')
        
        url = reverse('core:aprovacao_detail', args=[self.solicitacao.id])
        
        # Submeter reprovação
        data = {
            'decisao': AprovacaoStatus.REPROVADO,
            'justificativa': 'Conflito com evento já programado'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        
        # Verificar mudanças no modelo
        self.solicitacao.refresh_from_db()
        self.assertEqual(self.solicitacao.status, SolicitacaoStatus.REPROVADO)
        self.assertEqual(self.solicitacao.usuario_aprovador, self.superintendencia)
        self.assertEqual(self.solicitacao.justificativa_rejeicao, 'Conflito com evento já programado')
        self.assertIsNotNone(self.solicitacao.data_aprovacao_rejeicao)
        
        # Verificar criação do registro de aprovação
        aprovacao = Aprovacao.objects.get(solicitacao=self.solicitacao)
        self.assertEqual(aprovacao.status_decisao, AprovacaoStatus.REPROVADO)
        self.assertEqual(aprovacao.justificativa, 'Conflito com evento já programado')
    
    def test_cannot_decide_already_decided_request(self):
        """RF04: Não pode decidir solicitação já decidida"""
        # Primeiro aprovar a solicitação
        self.solicitacao.status = SolicitacaoStatus.APROVADO
        self.solicitacao.save()
        
        self.client.login(username='super_workflow', password='testpass123')
        url = reverse('core:aprovacao_detail', args=[self.solicitacao.id])
        
        # Tentar acessar novamente - deve redirecionar
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)  # Página de destino
        
        # Verificar se foi redirecionado para a lista
        self.assertContains(response, 'Aprovações Pendentes')
    
    def test_form_validation_missing_decision(self):
        """RF04: Validação quando decisão não é fornecida"""
        self.client.login(username='super_workflow', password='testpass123')
        url = reverse('core:aprovacao_detail', args=[self.solicitacao.id])
        
        # Submeter sem decisão
        data = {
            'justificativa': 'Justificativa sem decisão'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)  # Volta para a página com erro
        
        # Verificar que o status não mudou
        self.solicitacao.refresh_from_db()
        self.assertEqual(self.solicitacao.status, SolicitacaoStatus.PENDENTE)


class RF04SecurityTest(TestCase):
    """RF04: Testes de segurança para aprovações"""
    
    def setUp(self):
        """Configuração para testes de segurança"""
        self.client = Client()
        
        self.superintendencia = User.objects.create_user(
            username='super_security',
            password='testpass123',
            papel='superintendencia'
        )
        
        self.coordenador = User.objects.create_user(
            username='coord_security',
            password='testpass123',
            papel='coordenador'
        )
        
        projeto = Projeto.objects.create(nome='Projeto Security')
        municipio = Municipio.objects.create(nome='Fortaleza', uf='CE')
        tipo_evento = TipoEvento.objects.create(nome='Workshop Security')
        
        from django.utils import timezone as tz
        futuro = tz.localtime(tz.now()) + timedelta(days=7)
        self.solicitacao = Solicitacao.objects.create(
            usuario_solicitante=self.coordenador,
            projeto=projeto,
            municipio=municipio,
            tipo_evento=tipo_evento,
            titulo_evento='Evento Security',
            data_inicio=futuro,
            data_fim=futuro + timedelta(hours=2),
            status=SolicitacaoStatus.PENDENTE
        )
    
    def test_csrf_protection(self):
        """RF04: Teste de proteção CSRF"""
        from django.middleware.csrf import get_token
        from django.test import override_settings
        
        # Login normal para obter uma sessão válida
        self.client.login(username='super_security', password='testpass123')
        url = reverse('core:aprovacao_detail', args=[self.solicitacao.id])
        
        # Primeiro, fazer GET para obter o token CSRF válido
        get_response = self.client.get(url)
        self.assertEqual(get_response.status_code, 200)
        
        # Agora fazer POST sem token CSRF usando client com enforcement
        from django.test import Client
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.login(username='super_security', password='testpass123')
        
        # Tentar submeter sem CSRF token (ou com token inválido)
        data = {
            'decisao': AprovacaoStatus.APROVADO,
            'justificativa': 'Tentativa sem CSRF',
            'csrfmiddlewaretoken': 'invalid_token'  # Token inválido
        }
        response = csrf_client.post(url, data)
        
        # Django pode retornar 403 ou redirecionar - vamos aceitar ambos
        self.assertIn(response.status_code, [403, 302])
        
        # Se foi redirecionamento, verificar se não foi processado
        if response.status_code == 302:
            # Verificar que não foi para a página de sucesso
            self.assertNotEqual(response.url, reverse('core:aprovacoes_pendentes'))
        
        # Verificar que nada foi alterado na solicitação
        self.solicitacao.refresh_from_db()
        self.assertEqual(self.solicitacao.status, SolicitacaoStatus.PENDENTE)
        
        # Verificar que nenhuma aprovação foi criada
        from core.models import Aprovacao
        self.assertFalse(Aprovacao.objects.filter(solicitacao=self.solicitacao).exists())
    
    def test_direct_url_access_protection(self):
        """RF04: Teste de proteção contra acesso direto à URL"""
        # Tentar acessar URLs sem login
        list_url = reverse('core:aprovacoes_pendentes')
        detail_url = reverse('core:aprovacao_detail', args=[self.solicitacao.id])
        
        # Sem login
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
        # Com login mas papel errado
        self.client.login(username='coord_security', password='testpass123')
        
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, 403)  # Permission denied
        
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 403)  # Permission denied
    
    def test_nonexistent_solicitacao_access(self):
        """RF04: Teste de acesso a solicitação inexistente"""
        self.client.login(username='super_security', password='testpass123')
        
        import uuid
        fake_id = uuid.uuid4()
        url = reverse('core:aprovacao_detail', args=[fake_id])
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
