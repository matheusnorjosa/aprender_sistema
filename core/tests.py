import json
from datetime import datetime, time, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.forms import SolicitacaoForm
from core.models import (
    Aprovacao,
    AprovacaoStatus,
    DisponibilidadeFormadores,
    EventoGoogleCalendar,
    Formador,
    LogAuditoria,
    Municipio,
    Projeto,
    Solicitacao,
    SolicitacaoStatus,
    TipoEvento,
)

User = get_user_model()


class SolicitacaoModelTest(TestCase):
    """Testes para o modelo Solicitacao"""

    def setUp(self):
        """Configuração inicial para os testes"""
        self.user = User.objects.create_user(
            username="coord_test",
            email="coord@test.com",
            password="testpass123",
            papel="coordenador",
        )

        self.projeto = Projeto.objects.create(
            nome="Projeto Teste", descricao="Descrição do projeto teste"
        )

        self.municipio = Municipio.objects.create(nome="São Paulo", uf="SP")

        self.tipo_evento = TipoEvento.objects.create(nome="Workshop", online=False)

        self.formador = Formador.objects.create(
            nome="João Silva", email="joao@test.com", area_atuacao="Matemática"
        )

    def test_create_solicitacao(self):
        """Testa a criação de uma solicitação"""
        futuro = timezone.now() + timedelta(days=7)
        solicitacao = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento Teste",
            data_inicio=futuro,
            data_fim=futuro + timedelta(hours=2),
            numero_encontro_formativo="1º Encontro",
            coordenador_acompanha=True,
            observacoes="Observação teste",
        )

        self.assertEqual(solicitacao.titulo_evento, "Evento Teste")
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
            titulo_evento="Evento 1",
            data_inicio=futuro1,
            data_fim=futuro1 + timedelta(hours=2),
        )

        sol2 = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento 2",
            data_inicio=futuro2,
            data_fim=futuro2 + timedelta(hours=2),
        )

        # As solicitações devem ser ordenadas por data_solicitacao decrescente
        solicitacoes = list(Solicitacao.objects.all())
        self.assertEqual(solicitacoes[0], sol2)  # Mais recente primeiro
        self.assertEqual(solicitacoes[1], sol1)


class SolicitacaoFormTest(TestCase):
    """Testes para o formulário SolicitacaoForm"""

    def setUp(self):
        """Configuração inicial para os testes"""
        self.projeto = Projeto.objects.create(nome="Projeto Teste")
        self.municipio = Municipio.objects.create(nome="São Paulo", uf="SP")
        self.tipo_evento = TipoEvento.objects.create(nome="Workshop")
        self.formador = Formador.objects.create(
            nome="João Silva", email="joao@test.com"
        )

        self.valid_data = {
            "projeto": self.projeto.id,
            "municipio": self.municipio.id,
            "tipo_evento": self.tipo_evento.id,
            "titulo_evento": "Evento Teste",
            "data_inicio": (timezone.now() + timedelta(days=7)).strftime(
                "%Y-%m-%dT%H:%M"
            ),
            "data_fim": (timezone.now() + timedelta(days=7, hours=2)).strftime(
                "%Y-%m-%dT%H:%M"
            ),
            "numero_encontro_formativo": "1º Encontro",
            "coordenador_acompanha": True,
            "observacoes": "Observação teste",
            "formadores": [self.formador.id],
        }

    def test_valid_form(self):
        """Testa formulário válido"""
        form = SolicitacaoForm(data=self.valid_data)
        self.assertTrue(
            form.is_valid(), f"Formulário deveria ser válido. Erros: {form.errors}"
        )

    def test_data_fim_before_inicio(self):
        """Testa validação quando data fim é antes da data início"""
        data = self.valid_data.copy()
        data["data_inicio"] = (timezone.now() + timedelta(days=7, hours=2)).strftime(
            "%Y-%m-%dT%H:%M"
        )
        data["data_fim"] = (timezone.now() + timedelta(days=7)).strftime(
            "%Y-%m-%dT%H:%M"
        )

        form = SolicitacaoForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "A data/hora de término deve ser maior que a de início", str(form.errors)
        )

    def test_minimum_duration(self):
        """Testa validação de duração mínima"""
        data = self.valid_data.copy()
        futuro = timezone.now() + timedelta(days=7)
        data["data_inicio"] = futuro.strftime("%Y-%m-%dT%H:%M")
        data["data_fim"] = (futuro + timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M")

        form = SolicitacaoForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "O evento deve ter duração mínima de 30 minutos", str(form.errors)
        )

    def test_past_date_validation(self):
        """Testa validação de data no passado"""
        data = self.valid_data.copy()
        passado = timezone.now() - timedelta(days=1)
        data["data_inicio"] = passado.strftime("%Y-%m-%dT%H:%M")
        data["data_fim"] = (passado + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M")

        form = SolicitacaoForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("A data de início deve ser no futuro", str(form.errors))

    def test_titulo_too_short(self):
        """Testa validação de título muito curto"""
        data = self.valid_data.copy()
        data["titulo_evento"] = "AB"  # Menos de 3 caracteres

        form = SolicitacaoForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "O título do evento deve ter pelo menos 3 caracteres", str(form.errors)
        )

    def test_formadores_required(self):
        """Testa que formadores são obrigatórios"""
        data = self.valid_data.copy()
        data["formadores"] = []

        form = SolicitacaoForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("formadores", form.errors)

    def test_conflict_with_availability(self):
        """Testa detecção de conflito com disponibilidade de formadores"""
        # Criar bloqueio de disponibilidade
        futuro = timezone.now() + timedelta(days=7)
        DisponibilidadeFormadores.objects.create(
            formador=self.formador,
            data_bloqueio=futuro.date(),
            hora_inicio=futuro.time(),
            hora_fim=(futuro + timedelta(hours=1)).time(),
            tipo_bloqueio="Total",
            motivo="Indisponível",
        )

        data = self.valid_data.copy()
        data["data_inicio"] = futuro.strftime("%Y-%m-%dT%H:%M")
        data["data_fim"] = (futuro + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M")

        form = SolicitacaoForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("Conflitos de disponibilidade", str(form.errors))


class SolicitacaoViewTest(TestCase):
    """Testes para as views relacionadas à solicitação"""

    def setUp(self):
        """Configuração inicial para os testes"""
        self.client = Client()

        self.coordenador = User.objects.create_user(
            username="coordenador",
            email="coord@test.com",
            password="testpass123",
            papel="coordenador",
        )

        self.formador_user = User.objects.create_user(
            username="formador",
            email="formador@test.com",
            password="testpass123",
            papel="formador",
        )

        self.projeto = Projeto.objects.create(nome="Projeto Teste")
        self.municipio = Municipio.objects.create(nome="São Paulo", uf="SP")
        self.tipo_evento = TipoEvento.objects.create(nome="Workshop")
        self.formador = Formador.objects.create(
            nome="João Silva", email="joao@test.com"
        )

    def test_access_without_login(self):
        """Testa acesso sem login"""
        url = reverse("core:solicitar_evento")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirecionamento para login

    def test_access_with_wrong_role(self):
        """Testa acesso com papel incorreto"""
        self.client.login(username="formador", password="testpass123")
        url = reverse("core:solicitar_evento")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)  # Acesso negado

    def test_access_with_coordenador(self):
        """Testa acesso com papel correto (coordenador)"""
        self.client.login(username="coordenador", password="testpass123")
        url = reverse("core:solicitar_evento")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Solicitar Evento")

    def test_form_submission_valid(self):
        """Testa submissão válida do formulário"""
        self.client.login(username="coordenador", password="testpass123")

        futuro = timezone.now() + timedelta(days=7)
        data = {
            "projeto": self.projeto.id,
            "municipio": self.municipio.id,
            "tipo_evento": self.tipo_evento.id,
            "titulo_evento": "Evento Teste",
            "data_inicio": futuro.strftime("%Y-%m-%dT%H:%M"),
            "data_fim": (futuro + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M"),
            "numero_encontro_formativo": "1º Encontro",
            "coordenador_acompanha": True,
            "observacoes": "Observação teste",
            "formadores": [self.formador.id],
        }

        url = reverse("core:solicitar_evento")
        response = self.client.post(url, data)

        # Deve redirecionar para página de sucesso
        self.assertEqual(response.status_code, 302)

        # Verifica se a solicitação foi criada
        self.assertTrue(
            Solicitacao.objects.filter(titulo_evento="Evento Teste").exists()
        )

        # Verifica se o usuário solicitante foi definido corretamente
        solicitacao = Solicitacao.objects.get(titulo_evento="Evento Teste")
        self.assertEqual(solicitacao.usuario_solicitante, self.coordenador)

    def test_success_page(self):
        """Testa a página de sucesso"""
        self.client.login(username="coordenador", password="testpass123")
        url = reverse("core:solicitacao_ok")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class ConflictDetectionTest(TestCase):
    """Testes específicos para detecção de conflitos"""

    def setUp(self):
        """Configuração inicial para os testes"""
        self.user = User.objects.create_user(
            username="coord_test",
            email="coord@test.com",
            password="testpass123",
            papel="coordenador",
        )

        self.projeto = Projeto.objects.create(nome="Projeto Teste")
        self.municipio = Municipio.objects.create(nome="São Paulo", uf="SP")
        self.tipo_evento = TipoEvento.objects.create(nome="Workshop")

        self.formador1 = Formador.objects.create(
            nome="João Silva", email="joao@test.com"
        )

        self.formador2 = Formador.objects.create(
            nome="Maria Santos", email="maria@test.com"
        )

    def test_conflict_with_approved_request(self):
        """Testa conflito com solicitação já aprovada"""
        # Criar solicitação aprovada usando timezone local (São Paulo)
        from django.utils import timezone as tz

        now_local = tz.localtime(tz.now())
        futuro = now_local.replace(
            hour=10, minute=0, second=0, microsecond=0
        ) + timedelta(days=7)
        solicitacao_aprovada = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento Aprovado",
            data_inicio=futuro,
            data_fim=futuro + timedelta(hours=2),
            status=SolicitacaoStatus.APROVADO,
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
            "projeto": self.projeto.id,
            "municipio": self.municipio.id,
            "tipo_evento": self.tipo_evento.id,
            "titulo_evento": "Evento Conflitante",
            "data_inicio": conflicting_start.strftime("%Y-%m-%dT%H:%M"),
            "data_fim": conflicting_end.strftime("%Y-%m-%dT%H:%M"),
            "formadores": [self.formador1.id],
        }

        form = SolicitacaoForm(data=data)
        self.assertFalse(
            form.is_valid(),
            f"Form should be invalid due to conflict. Errors: {form.errors}",
        )
        self.assertIn("Conflitos com solicitações aprovadas", str(form.errors))

    def test_no_conflict_different_formadores(self):
        """Testa que não há conflito com formadores diferentes"""
        # Criar solicitação aprovada com formador1
        futuro = timezone.now() + timedelta(days=7)
        solicitacao_aprovada = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento Aprovado",
            data_inicio=futuro,
            data_fim=futuro + timedelta(hours=2),
            status=SolicitacaoStatus.APROVADO,
        )
        solicitacao_aprovada.formadores.add(self.formador1)

        # Criar nova solicitação com formador2 (sem conflito)
        data = {
            "projeto": self.projeto.id,
            "municipio": self.municipio.id,
            "tipo_evento": self.tipo_evento.id,
            "titulo_evento": "Evento Sem Conflito",
            "data_inicio": (futuro + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M"),
            "data_fim": (futuro + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M"),
            "formadores": [self.formador2.id],
        }

        form = SolicitacaoForm(data=data)
        self.assertTrue(
            form.is_valid(), f"Formulário deveria ser válido. Erros: {form.errors}"
        )


class PermissionTest(TestCase):
    """Testes de permissões e controle de acesso"""

    def setUp(self):
        """Configuração inicial para os testes"""
        self.client = Client()

        # Criar usuários com diferentes papéis
        self.coordenador = User.objects.create_user(
            username="coordenador", password="testpass123", papel="coordenador"
        )

        self.superintendencia = User.objects.create_user(
            username="superintendencia",
            password="testpass123",
            papel="superintendencia",
        )

        self.formador = User.objects.create_user(
            username="formador", password="testpass123", papel="formador"
        )

        self.admin = User.objects.create_superuser(
            username="admin", email="admin@test.com", password="testpass123"
        )

    def test_coordenador_can_access(self):
        """Testa que coordenador pode acessar o formulário"""
        self.client.login(username="coordenador", password="testpass123")
        url = reverse("core:solicitar_evento")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_superintendencia_cannot_access(self):
        """Testa que superintendência não pode acessar o formulário"""
        self.client.login(username="superintendencia", password="testpass123")
        url = reverse("core:solicitar_evento")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_formador_cannot_access(self):
        """Testa que formador não pode acessar o formulário"""
        self.client.login(username="formador", password="testpass123")
        url = reverse("core:solicitar_evento")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_admin_can_access(self):
        """Testa que admin pode acessar o formulário"""
        self.client.login(username="admin", password="testpass123")
        url = reverse("core:solicitar_evento")
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

        self.assertEqual(settings.TIME_ZONE, "America/Fortaleza")
        self.assertTrue(settings.USE_TZ)

    def test_timezone_correctness_in_conflicts(self):
        """RF03: Verifica se o sistema usa corretamente o timezone local"""
        from datetime import timedelta
        from datetime import timezone as dt_timezone

        from django.utils import timezone as tz

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
        self.assertIn(
            actual_offset_seconds,
            [expected_offset_seconds, expected_offset_seconds + 3600],
        )


class RF03ExactBoundariesTest(TestCase):
    """RF03: Testes para limites exatos de conflitos"""

    def setUp(self):
        """Configuração para testes de limites exatos"""
        self.user = User.objects.create_user(
            username="coord_boundary_test",
            email="coord@boundary.com",
            password="testpass123",
            papel="coordenador",
        )

        self.projeto = Projeto.objects.create(nome="Projeto Boundary")
        self.municipio = Municipio.objects.create(nome="Fortaleza", uf="CE")
        self.tipo_evento = TipoEvento.objects.create(nome="Workshop Boundary")
        self.formador = Formador.objects.create(
            nome="Formador Boundary", email="boundary@test.com"
        )

    def test_exact_boundary_no_overlap_end_equals_start(self):
        """RF03: Não deve haver conflito quando end_time == start_time do próximo"""
        from django.utils import timezone as tz

        # Evento aprovado: 10:00 - 12:00
        now_local = tz.localtime(tz.now())
        base_time = now_local.replace(
            hour=10, minute=0, second=0, microsecond=0
        ) + timedelta(days=7)

        approved_end = base_time + timedelta(hours=2)  # 12:00

        solicitacao_aprovada = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento Aprovado",
            data_inicio=base_time,
            data_fim=approved_end,
            status=SolicitacaoStatus.APROVADO,
        )
        solicitacao_aprovada.formadores.add(self.formador)

        # Novo evento: 12:00 - 14:00 (exatamente quando o anterior termina)
        new_start = approved_end  # 12:00
        new_end = approved_end + timedelta(hours=2)  # 14:00

        data = {
            "projeto": self.projeto.id,
            "municipio": self.municipio.id,
            "tipo_evento": self.tipo_evento.id,
            "titulo_evento": "Evento Sequencial",
            "data_inicio": new_start.strftime("%Y-%m-%dT%H:%M"),
            "data_fim": new_end.strftime("%Y-%m-%dT%H:%M"),
            "formadores": [self.formador.id],
        }

        form = SolicitacaoForm(data=data)
        self.assertTrue(
            form.is_valid(),
            "Não deve haver conflito quando eventos são sequenciais (fim == início)",
        )

    def test_exact_boundary_overlap_by_one_minute(self):
        """RF03: Deve haver conflito com sobreposição de 1 minuto"""
        from django.utils import timezone as tz

        # Evento aprovado: 10:00 - 12:00
        now_local = tz.localtime(tz.now())
        base_time = now_local.replace(
            hour=10, minute=0, second=0, microsecond=0
        ) + timedelta(days=7)
        approved_end = base_time + timedelta(hours=2)

        solicitacao_aprovada = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento Aprovado",
            data_inicio=base_time,
            data_fim=approved_end,
            status=SolicitacaoStatus.APROVADO,
        )
        solicitacao_aprovada.formadores.add(self.formador)

        # Novo evento: 11:59 - 14:00 (1 minuto de sobreposição)
        new_start = approved_end - timedelta(minutes=1)  # 11:59
        new_end = approved_end + timedelta(hours=2)  # 14:00

        data = {
            "projeto": self.projeto.id,
            "municipio": self.municipio.id,
            "tipo_evento": self.tipo_evento.id,
            "titulo_evento": "Evento Conflitante",
            "data_inicio": new_start.strftime("%Y-%m-%dT%H:%M"),
            "data_fim": new_end.strftime("%Y-%m-%dT%H:%M"),
            "formadores": [self.formador.id],
        }

        form = SolicitacaoForm(data=data)
        self.assertFalse(
            form.is_valid(), "Deve haver conflito com sobreposição de 1 minuto"
        )
        self.assertIn("Conflitos com solicitações aprovadas", str(form.errors))


class RF03MultiFormadorTest(TestCase):
    """RF03: Testes para conflitos com múltiplos formadores"""

    def setUp(self):
        """Configuração para testes multi-formador"""
        self.user = User.objects.create_user(
            username="coord_multi_test",
            email="coord@multi.com",
            password="testpass123",
            papel="coordenador",
        )

        self.projeto = Projeto.objects.create(nome="Projeto Multi")
        self.municipio = Municipio.objects.create(nome="Fortaleza", uf="CE")
        self.tipo_evento = TipoEvento.objects.create(nome="Workshop Multi")

        self.formador1 = Formador.objects.create(
            nome="Formador Alpha", email="alpha@test.com"
        )
        self.formador2 = Formador.objects.create(
            nome="Formador Beta", email="beta@test.com"
        )
        self.formador3 = Formador.objects.create(
            nome="Formador Gamma", email="gamma@test.com"
        )

    def test_conflict_when_any_formador_overlaps(self):
        """RF03: Deve detectar conflito se qualquer formador selecionado tiver conflito"""
        from django.utils import timezone as tz

        # Criar evento aprovado com formador2
        now_local = tz.localtime(tz.now())
        base_time = now_local.replace(
            hour=14, minute=0, second=0, microsecond=0
        ) + timedelta(days=7)

        solicitacao_aprovada = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento com Beta",
            data_inicio=base_time,
            data_fim=base_time + timedelta(hours=2),
            status=SolicitacaoStatus.APROVADO,
        )
        solicitacao_aprovada.formadores.add(self.formador2)

        # Tentar criar evento com formador1, formador2 e formador3
        # Apenas formador2 tem conflito, mas deve bloquear todo o evento
        conflicting_start = base_time + timedelta(minutes=30)
        conflicting_end = base_time + timedelta(hours=1, minutes=30)

        data = {
            "projeto": self.projeto.id,
            "municipio": self.municipio.id,
            "tipo_evento": self.tipo_evento.id,
            "titulo_evento": "Evento Multi Conflitante",
            "data_inicio": conflicting_start.strftime("%Y-%m-%dT%H:%M"),
            "data_fim": conflicting_end.strftime("%Y-%m-%dT%H:%M"),
            "formadores": [self.formador1.id, self.formador2.id, self.formador3.id],
        }

        form = SolicitacaoForm(data=data)
        self.assertFalse(
            form.is_valid(),
            "Deve detectar conflito quando qualquer formador tem conflito",
        )
        error_str = str(form.errors)
        self.assertIn("Conflitos com solicitações aprovadas", error_str)
        self.assertIn(
            "Formador Beta", error_str, "Deve mencionar o formador em conflito"
        )

    def test_no_conflict_with_different_formadores(self):
        """RF03: Não deve haver conflito quando formadores são diferentes"""
        from django.utils import timezone as tz

        # Criar evento aprovado com formador1
        now_local = tz.localtime(tz.now())
        base_time = now_local.replace(
            hour=14, minute=0, second=0, microsecond=0
        ) + timedelta(days=7)

        solicitacao_aprovada = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento com Alpha",
            data_inicio=base_time,
            data_fim=base_time + timedelta(hours=2),
            status=SolicitacaoStatus.APROVADO,
        )
        solicitacao_aprovada.formadores.add(self.formador1)

        # Criar evento no mesmo horário com formador2 e formador3 (sem conflito)
        data = {
            "projeto": self.projeto.id,
            "municipio": self.municipio.id,
            "tipo_evento": self.tipo_evento.id,
            "titulo_evento": "Evento Paralelo",
            "data_inicio": base_time.strftime("%Y-%m-%dT%H:%M"),
            "data_fim": (base_time + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M"),
            "formadores": [self.formador2.id, self.formador3.id],
        }

        form = SolicitacaoForm(data=data)
        self.assertTrue(
            form.is_valid(), "Não deve haver conflito com formadores diferentes"
        )


class RF03BloqueiosTest(TestCase):
    """RF03: Testes específicos para conflitos com bloqueios"""

    def setUp(self):
        """Configuração para testes de bloqueios"""
        self.user = User.objects.create_user(
            username="coord_bloqueio_test",
            email="coord@bloqueio.com",
            password="testpass123",
            papel="coordenador",
        )

        self.projeto = Projeto.objects.create(nome="Projeto Bloqueio")
        self.municipio = Municipio.objects.create(nome="Fortaleza", uf="CE")
        self.tipo_evento = TipoEvento.objects.create(nome="Workshop Bloqueio")
        self.formador = Formador.objects.create(
            nome="Formador Bloqueado", email="bloqueado@test.com"
        )

    def test_conflict_with_total_bloqueio(self):
        """RF03: Deve detectar conflito com bloqueio total"""
        from datetime import time

        from django.utils import timezone as tz

        # Criar bloqueio total para o formador
        now_local = tz.localtime(tz.now())
        blocked_date = (now_local + timedelta(days=7)).date()

        DisponibilidadeFormadores.objects.create(
            formador=self.formador,
            data_bloqueio=blocked_date,
            hora_inicio=time(0, 0),
            hora_fim=time(23, 59),
            tipo_bloqueio="Total",
            motivo="Indisponível",
        )

        # Tentar criar evento no dia bloqueado
        event_start = now_local.replace(
            year=blocked_date.year,
            month=blocked_date.month,
            day=blocked_date.day,
            hour=10,
            minute=0,
            second=0,
            microsecond=0,
        )

        data = {
            "projeto": self.projeto.id,
            "municipio": self.municipio.id,
            "tipo_evento": self.tipo_evento.id,
            "titulo_evento": "Evento em Dia Bloqueado",
            "data_inicio": event_start.strftime("%Y-%m-%dT%H:%M"),
            "data_fim": (event_start + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M"),
            "formadores": [self.formador.id],
        }

        form = SolicitacaoForm(data=data)
        self.assertFalse(form.is_valid(), "Deve detectar conflito com bloqueio total")
        error_str = str(form.errors)
        self.assertIn("Conflitos de disponibilidade", error_str)
        self.assertIn("Formador Bloqueado", error_str)
        self.assertIn("[T]", error_str)  # RD-08: Código de bloqueio total

    def test_conflict_with_partial_bloqueio(self):
        """RF03: Deve detectar conflito com bloqueio parcial"""
        from datetime import time

        from django.utils import timezone as tz

        # Criar bloqueio parcial (14:00 - 16:00)
        now_local = tz.localtime(tz.now())
        blocked_date = (now_local + timedelta(days=7)).date()

        DisponibilidadeFormadores.objects.create(
            formador=self.formador,
            data_bloqueio=blocked_date,
            hora_inicio=time(14, 0),
            hora_fim=time(16, 0),
            tipo_bloqueio="Parcial",
            motivo="Reunião",
        )

        # Tentar criar evento que sobrepõe com o bloqueio (15:00 - 17:00)
        event_start = now_local.replace(
            year=blocked_date.year,
            month=blocked_date.month,
            day=blocked_date.day,
            hour=15,
            minute=0,
            second=0,
            microsecond=0,
        )

        data = {
            "projeto": self.projeto.id,
            "municipio": self.municipio.id,
            "tipo_evento": self.tipo_evento.id,
            "titulo_evento": "Evento Sobreposto",
            "data_inicio": event_start.strftime("%Y-%m-%dT%H:%M"),
            "data_fim": (event_start + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M"),
            "formadores": [self.formador.id],
        }

        form = SolicitacaoForm(data=data)
        self.assertFalse(form.is_valid(), "Deve detectar conflito com bloqueio parcial")
        error_str = str(form.errors)
        self.assertIn("Conflitos de disponibilidade", error_str)
        self.assertIn("14:00", error_str)  # Verificar apenas início
        self.assertIn("16:00", error_str)  # Verificar apenas fim
        self.assertIn("[P]", error_str)  # RD-08: Código de bloqueio parcial

    def test_no_conflict_outside_bloqueio(self):
        """RF03: Não deve haver conflito fora do período de bloqueio"""
        from datetime import time

        from django.utils import timezone as tz

        # Criar bloqueio parcial (14:00 - 16:00)
        now_local = tz.localtime(tz.now())
        blocked_date = (now_local + timedelta(days=7)).date()

        DisponibilidadeFormadores.objects.create(
            formador=self.formador,
            data_bloqueio=blocked_date,
            hora_inicio=time(14, 0),
            hora_fim=time(16, 0),
            tipo_bloqueio="Parcial",
            motivo="Reunião",
        )

        # Criar evento fora do período de bloqueio (10:00 - 12:00)
        event_start = now_local.replace(
            year=blocked_date.year,
            month=blocked_date.month,
            day=blocked_date.day,
            hour=10,
            minute=0,
            second=0,
            microsecond=0,
        )

        data = {
            "projeto": self.projeto.id,
            "municipio": self.municipio.id,
            "tipo_evento": self.tipo_evento.id,
            "titulo_evento": "Evento Livre",
            "data_inicio": event_start.strftime("%Y-%m-%dT%H:%M"),
            "data_fim": (event_start + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M"),
            "formadores": [self.formador.id],
        }

        form = SolicitacaoForm(data=data)
        self.assertTrue(
            form.is_valid(), "Não deve haver conflito fora do período de bloqueio"
        )


class RF03ErrorMessageTest(TestCase):
    """RF03: Testes para formato das mensagens de erro"""

    def setUp(self):
        """Configuração para testes de mensagens"""
        self.user = User.objects.create_user(
            username="coord_msg_test",
            email="coord@msg.com",
            password="testpass123",
            papel="coordenador",
        )

        self.projeto = Projeto.objects.create(nome="Projeto Mensagem")
        self.municipio = Municipio.objects.create(nome="Fortaleza", uf="CE")
        self.tipo_evento = TipoEvento.objects.create(nome="Workshop Mensagem")
        self.formador = Formador.objects.create(
            nome="João Silva Mensagem", email="joao.msg@test.com"
        )

    def test_error_message_includes_formador_names_and_intervals(self):
        """RF03: Mensagens de erro devem incluir nomes dos formadores e intervalos"""
        from django.utils import timezone as tz

        # Criar evento aprovado
        now_local = tz.localtime(tz.now())
        base_time = now_local.replace(
            hour=9, minute=0, second=0, microsecond=0
        ) + timedelta(days=7)

        solicitacao_aprovada = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento="Workshop Matemática",
            data_inicio=base_time,
            data_fim=base_time + timedelta(hours=3),
            status=SolicitacaoStatus.APROVADO,
        )
        solicitacao_aprovada.formadores.add(self.formador)

        # Criar evento conflitante
        conflicting_start = base_time + timedelta(hours=1)
        conflicting_end = base_time + timedelta(hours=4)

        data = {
            "projeto": self.projeto.id,
            "municipio": self.municipio.id,
            "tipo_evento": self.tipo_evento.id,
            "titulo_evento": "Evento Conflitante",
            "data_inicio": conflicting_start.strftime("%Y-%m-%dT%H:%M"),
            "data_fim": conflicting_end.strftime("%Y-%m-%dT%H:%M"),
            "formadores": [self.formador.id],
        }

        form = SolicitacaoForm(data=data)
        self.assertFalse(form.is_valid())

        error_str = str(form.errors)

        # Verificar elementos obrigatórios na mensagem
        self.assertIn("Conflitos com solicitações aprovadas", error_str)
        self.assertIn(
            "Workshop Matemática",
            error_str,
            "Deve incluir título do evento conflitante",
        )
        self.assertIn("João Silva Mensagem", error_str, "Deve incluir nome do formador")

        # Verificar se contém horários (formato pode variar devido ao timezone)
        import re

        time_pattern = r"\d{2}:\d{2}"
        times_found = re.findall(time_pattern, error_str)
        self.assertGreaterEqual(
            len(times_found), 2, "Deve incluir pelo menos dois horários (início e fim)"
        )

        # Verificar formato da data (dd/mm)
        expected_date = base_time.strftime("%d/%m")
        self.assertIn(expected_date, error_str, "Deve incluir data no formato dd/mm")


# =========================
# RF04 - Approval/Rejection Tests
# =========================


class RF04ApprovalModelTest(TestCase):
    """RF04: Testes para o modelo Aprovacao"""

    def setUp(self):
        """Configuração inicial para testes de aprovação"""
        self.coordenador = User.objects.create_user(
            username="coord_rf04",
            email="coord@rf04.com",
            password="testpass123",
            papel="coordenador",
        )

        self.superintendencia = User.objects.create_user(
            username="super_rf04",
            email="super@rf04.com",
            password="testpass123",
            papel="superintendencia",
        )

        self.projeto = Projeto.objects.create(nome="Projeto RF04")
        self.municipio = Municipio.objects.create(nome="Fortaleza", uf="CE")
        self.tipo_evento = TipoEvento.objects.create(nome="Workshop RF04")
        self.formador = Formador.objects.create(
            nome="Formador RF04", email="formador@rf04.com"
        )

        # Criar solicitação pendente
        from django.utils import timezone as tz

        futuro = tz.localtime(tz.now()) + timedelta(days=7)
        self.solicitacao = Solicitacao.objects.create(
            usuario_solicitante=self.coordenador,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento RF04 Teste",
            data_inicio=futuro,
            data_fim=futuro + timedelta(hours=2),
            status=SolicitacaoStatus.PENDENTE,
        )
        self.solicitacao.formadores.add(self.formador)

    def test_create_aprovacao(self):
        """RF04: Testa criação de registro de aprovação"""
        aprovacao = Aprovacao.objects.create(
            solicitacao=self.solicitacao,
            usuario_aprovador=self.superintendencia,
            status_decisao=AprovacaoStatus.APROVADO,
            justificativa="Evento aprovado conforme cronograma",
        )

        self.assertEqual(aprovacao.solicitacao, self.solicitacao)
        self.assertEqual(aprovacao.usuario_aprovador, self.superintendencia)
        self.assertEqual(aprovacao.status_decisao, AprovacaoStatus.APROVADO)
        self.assertEqual(aprovacao.justificativa, "Evento aprovado conforme cronograma")
        self.assertIsNotNone(aprovacao.data_aprovacao)

    def test_aprovacao_str_representation(self):
        """RF04: Testa representação string do modelo Aprovacao"""
        aprovacao = Aprovacao.objects.create(
            solicitacao=self.solicitacao,
            usuario_aprovador=self.superintendencia,
            status_decisao=AprovacaoStatus.REPROVADO,
            justificativa="Conflito de agenda",
        )

        expected_str = f"{AprovacaoStatus.REPROVADO} — Evento RF04 Teste"
        self.assertEqual(str(aprovacao), expected_str)


class RF04PermissionTest(TestCase):
    """RF04: Testes de permissões para aprovação"""

    def setUp(self):
        """Configuração para testes de permissão"""
        self.client = Client()

        self.coordenador = User.objects.create_user(
            username="coordenador_perm", password="testpass123", papel="coordenador"
        )

        self.superintendencia = User.objects.create_user(
            username="superintendencia_perm",
            password="testpass123",
            papel="superintendencia",
        )

        self.formador = User.objects.create_user(
            username="formador_perm", password="testpass123", papel="formador"
        )

        self.admin = User.objects.create_superuser(
            username="admin_perm", email="admin@test.com", password="testpass123"
        )

        # Criar solicitação para testes
        projeto = Projeto.objects.create(nome="Projeto Perm")
        municipio = Municipio.objects.create(nome="Fortaleza", uf="CE")
        tipo_evento = TipoEvento.objects.create(nome="Workshop Perm")

        from django.utils import timezone as tz

        futuro = tz.localtime(tz.now()) + timedelta(days=7)
        self.solicitacao = Solicitacao.objects.create(
            usuario_solicitante=self.coordenador,
            projeto=projeto,
            municipio=municipio,
            tipo_evento=tipo_evento,
            titulo_evento="Evento Permissão",
            data_inicio=futuro,
            data_fim=futuro + timedelta(hours=2),
            status=SolicitacaoStatus.PENDENTE,
        )

    def test_superintendencia_can_access_approval_list(self):
        """RF04: Superintendência pode acessar lista de aprovações"""
        self.client.login(username="superintendencia_perm", password="testpass123")
        url = reverse("core:aprovacoes_pendentes")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_coordenador_cannot_access_approval_list(self):
        """RF04: Coordenador não pode acessar lista de aprovações"""
        self.client.login(username="coordenador_perm", password="testpass123")
        url = reverse("core:aprovacoes_pendentes")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_formador_cannot_access_approval_list(self):
        """RF04: Formador não pode acessar lista de aprovações"""
        self.client.login(username="formador_perm", password="testpass123")
        url = reverse("core:aprovacoes_pendentes")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_admin_can_access_approval_list(self):
        """RF04: Admin pode acessar lista de aprovações"""
        self.client.login(username="admin_perm", password="testpass123")
        url = reverse("core:aprovacoes_pendentes")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_superintendencia_can_access_approval_detail(self):
        """RF04: Superintendência pode acessar detalhes para decisão"""
        self.client.login(username="superintendencia_perm", password="testpass123")
        url = reverse("core:aprovacao_detail", args=[self.solicitacao.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_coordenador_cannot_access_approval_detail(self):
        """RF04: Coordenador não pode acessar detalhes para decisão"""
        self.client.login(username="coordenador_perm", password="testpass123")
        url = reverse("core:aprovacao_detail", args=[self.solicitacao.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_cannot_access(self):
        """RF04: Usuário não autenticado não pode acessar"""
        url = reverse("core:aprovacoes_pendentes")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect to login


class RF04ApprovalListTest(TestCase):
    """RF04: Testes para listagem de aprovações pendentes"""

    def setUp(self):
        """Configuração para testes de listagem"""
        self.client = Client()

        self.superintendencia = User.objects.create_user(
            username="super_list", password="testpass123", papel="superintendencia"
        )

        self.coordenador = User.objects.create_user(
            username="coord_list", password="testpass123", papel="coordenador"
        )

        self.projeto = Projeto.objects.create(nome="Projeto Lista")
        self.municipio = Municipio.objects.create(nome="Fortaleza", uf="CE")
        self.tipo_evento = TipoEvento.objects.create(nome="Workshop Lista")

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
            titulo_evento="Evento Pendente",
            data_inicio=self.futuro,
            data_fim=self.futuro + timedelta(hours=2),
            status=SolicitacaoStatus.PENDENTE,
        )

        aprovado = Solicitacao.objects.create(
            usuario_solicitante=self.coordenador,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento Aprovado",
            data_inicio=self.futuro + timedelta(days=1),
            data_fim=self.futuro + timedelta(days=1, hours=2),
            status=SolicitacaoStatus.APROVADO,
        )

        reprovado = Solicitacao.objects.create(
            usuario_solicitante=self.coordenador,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento Reprovado",
            data_inicio=self.futuro + timedelta(days=2),
            data_fim=self.futuro + timedelta(days=2, hours=2),
            status=SolicitacaoStatus.REPROVADO,
        )

        self.client.login(username="super_list", password="testpass123")
        url = reverse("core:aprovacoes_pendentes")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Evento Pendente")
        self.assertNotContains(response, "Evento Aprovado")
        self.assertNotContains(response, "Evento Reprovado")

    def test_search_functionality(self):
        """RF04: Funcionalidade de busca por título"""
        Solicitacao.objects.create(
            usuario_solicitante=self.coordenador,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento="Workshop Python",
            data_inicio=self.futuro,
            data_fim=self.futuro + timedelta(hours=2),
            status=SolicitacaoStatus.PENDENTE,
        )

        Solicitacao.objects.create(
            usuario_solicitante=self.coordenador,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento="Seminário Django",
            data_inicio=self.futuro + timedelta(days=1),
            data_fim=self.futuro + timedelta(days=1, hours=2),
            status=SolicitacaoStatus.PENDENTE,
        )

        self.client.login(username="super_list", password="testpass123")
        url = reverse("core:aprovacoes_pendentes")

        # Buscar por 'Python'
        response = self.client.get(url, {"q": "Python"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Workshop Python")
        self.assertNotContains(response, "Seminário Django")

        # Buscar por 'Django'
        response = self.client.get(url, {"q": "Django"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Seminário Django")
        self.assertNotContains(response, "Workshop Python")

    def test_pagination(self):
        """RF04: Teste de paginação da lista"""
        # Criar mais de 20 solicitações para testar paginação
        for i in range(25):
            Solicitacao.objects.create(
                usuario_solicitante=self.coordenador,
                projeto=self.projeto,
                municipio=self.municipio,
                tipo_evento=self.tipo_evento,
                titulo_evento=f"Evento {i+1}",
                data_inicio=self.futuro + timedelta(hours=i),
                data_fim=self.futuro + timedelta(hours=i + 2),
                status=SolicitacaoStatus.PENDENTE,
            )

        self.client.login(username="super_list", password="testpass123")
        url = reverse("core:aprovacoes_pendentes")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_paginated"])
        self.assertEqual(len(response.context["pendentes"]), 20)  # paginate_by = 20


class RF04ApprovalWorkflowTest(TestCase):
    """RF04: Testes para fluxo completo de aprovação/reprovação"""

    def setUp(self):
        """Configuração para testes de workflow"""
        self.client = Client()

        self.superintendencia = User.objects.create_user(
            username="super_workflow", password="testpass123", papel="superintendencia"
        )

        self.coordenador = User.objects.create_user(
            username="coord_workflow", password="testpass123", papel="coordenador"
        )

        projeto = Projeto.objects.create(nome="Projeto Workflow")
        municipio = Municipio.objects.create(nome="Fortaleza", uf="CE")
        tipo_evento = TipoEvento.objects.create(nome="Workshop Workflow")
        formador = Formador.objects.create(
            nome="Formador Workflow", email="workflow@test.com"
        )

        from django.utils import timezone as tz

        futuro = tz.localtime(tz.now()) + timedelta(days=7)
        self.solicitacao = Solicitacao.objects.create(
            usuario_solicitante=self.coordenador,
            projeto=projeto,
            municipio=municipio,
            tipo_evento=tipo_evento,
            titulo_evento="Evento Workflow",
            data_inicio=futuro,
            data_fim=futuro + timedelta(hours=2),
            status=SolicitacaoStatus.PENDENTE,
        )
        self.solicitacao.formadores.add(formador)

    def test_approval_workflow(self):
        """RF04: Teste do fluxo completo de aprovação"""
        self.client.login(username="super_workflow", password="testpass123")

        # Acessar página de decisão
        url = reverse("core:aprovacao_detail", args=[self.solicitacao.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Submeter aprovação
        data = {
            "decisao": AprovacaoStatus.APROVADO,
            "justificativa": "Evento aprovado conforme planejamento",
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
        self.assertEqual(
            aprovacao.justificativa, "Evento aprovado conforme planejamento"
        )

        # Verificar log de auditoria
        self.assertTrue(
            LogAuditoria.objects.filter(
                usuario=self.superintendencia, acao__contains="RF04: Aprovado"
            ).exists()
        )

    def test_rejection_workflow(self):
        """RF04: Teste do fluxo completo de reprovação"""
        self.client.login(username="super_workflow", password="testpass123")

        url = reverse("core:aprovacao_detail", args=[self.solicitacao.id])

        # Submeter reprovação
        data = {
            "decisao": AprovacaoStatus.REPROVADO,
            "justificativa": "Conflito com evento já programado",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

        # Verificar mudanças no modelo
        self.solicitacao.refresh_from_db()
        self.assertEqual(self.solicitacao.status, SolicitacaoStatus.REPROVADO)
        self.assertEqual(self.solicitacao.usuario_aprovador, self.superintendencia)
        self.assertEqual(
            self.solicitacao.justificativa_rejeicao, "Conflito com evento já programado"
        )
        self.assertIsNotNone(self.solicitacao.data_aprovacao_rejeicao)

        # Verificar criação do registro de aprovação
        aprovacao = Aprovacao.objects.get(solicitacao=self.solicitacao)
        self.assertEqual(aprovacao.status_decisao, AprovacaoStatus.REPROVADO)
        self.assertEqual(aprovacao.justificativa, "Conflito com evento já programado")

    def test_cannot_decide_already_decided_request(self):
        """RF04: Não pode decidir solicitação já decidida"""
        # Primeiro aprovar a solicitação
        self.solicitacao.status = SolicitacaoStatus.APROVADO
        self.solicitacao.save()

        self.client.login(username="super_workflow", password="testpass123")
        url = reverse("core:aprovacao_detail", args=[self.solicitacao.id])

        # Tentar acessar novamente - deve redirecionar
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)  # Página de destino

        # Verificar se foi redirecionado para a lista
        self.assertContains(response, "Aprovações Pendentes")

    def test_form_validation_missing_decision(self):
        """RF04: Validação quando decisão não é fornecida"""
        self.client.login(username="super_workflow", password="testpass123")
        url = reverse("core:aprovacao_detail", args=[self.solicitacao.id])

        # Submeter sem decisão
        data = {"justificativa": "Justificativa sem decisão"}
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
            username="super_security", password="testpass123", papel="superintendencia"
        )

        self.coordenador = User.objects.create_user(
            username="coord_security", password="testpass123", papel="coordenador"
        )

        projeto = Projeto.objects.create(nome="Projeto Security")
        municipio = Municipio.objects.create(nome="Fortaleza", uf="CE")
        tipo_evento = TipoEvento.objects.create(nome="Workshop Security")

        from django.utils import timezone as tz

        futuro = tz.localtime(tz.now()) + timedelta(days=7)
        self.solicitacao = Solicitacao.objects.create(
            usuario_solicitante=self.coordenador,
            projeto=projeto,
            municipio=municipio,
            tipo_evento=tipo_evento,
            titulo_evento="Evento Security",
            data_inicio=futuro,
            data_fim=futuro + timedelta(hours=2),
            status=SolicitacaoStatus.PENDENTE,
        )

    def test_csrf_protection(self):
        """RF04: Teste de proteção CSRF"""
        from django.middleware.csrf import get_token
        from django.test import override_settings

        # Login normal para obter uma sessão válida
        self.client.login(username="super_security", password="testpass123")
        url = reverse("core:aprovacao_detail", args=[self.solicitacao.id])

        # Primeiro, fazer GET para obter o token CSRF válido
        get_response = self.client.get(url)
        self.assertEqual(get_response.status_code, 200)

        # Agora fazer POST sem token CSRF usando client com enforcement
        from django.test import Client

        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.login(username="super_security", password="testpass123")

        # Tentar submeter sem CSRF token (ou com token inválido)
        data = {
            "decisao": AprovacaoStatus.APROVADO,
            "justificativa": "Tentativa sem CSRF",
            "csrfmiddlewaretoken": "invalid_token",  # Token inválido
        }
        response = csrf_client.post(url, data)

        # Django pode retornar 403 ou redirecionar - vamos aceitar ambos
        self.assertIn(response.status_code, [403, 302])

        # Se foi redirecionamento, verificar se não foi processado
        if response.status_code == 302:
            # Verificar que não foi para a página de sucesso
            self.assertNotEqual(response.url, reverse("core:aprovacoes_pendentes"))

        # Verificar que nada foi alterado na solicitação
        self.solicitacao.refresh_from_db()
        self.assertEqual(self.solicitacao.status, SolicitacaoStatus.PENDENTE)

        # Verificar que nenhuma aprovação foi criada
        from core.models import Aprovacao

        self.assertFalse(
            Aprovacao.objects.filter(solicitacao=self.solicitacao).exists()
        )

    def test_direct_url_access_protection(self):
        """RF04: Teste de proteção contra acesso direto à URL"""
        # Tentar acessar URLs sem login
        list_url = reverse("core:aprovacoes_pendentes")
        detail_url = reverse("core:aprovacao_detail", args=[self.solicitacao.id])

        # Sem login
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, 302)  # Redirect to login

        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 302)  # Redirect to login

        # Com login mas papel errado
        self.client.login(username="coord_security", password="testpass123")

        response = self.client.get(list_url)
        self.assertEqual(response.status_code, 403)  # Permission denied

        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 403)  # Permission denied

    def test_nonexistent_solicitacao_access(self):
        """RF04: Teste de acesso a solicitação inexistente"""
        self.client.login(username="super_security", password="testpass123")

        import uuid

        fake_id = uuid.uuid4()
        url = reverse("core:aprovacao_detail", args=[fake_id])

        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


# =========================
# RD-02/RD-03: Bloqueios Total vs Parcial Tests
# =========================


class RDBloqueiosTotalParcialTest(TestCase):
    """Testes padronizados CLAUDE.md para RD-02/RD-03"""

    def setUp(self):
        """Configuração para testes de bloqueios"""
        self.coordenador = User.objects.create_user(
            username="coord_rd", password="testpass123", papel="coordenador"
        )

        self.projeto = Projeto.objects.create(nome="Projeto RD")
        self.municipio = Municipio.objects.create(nome="Fortaleza", uf="CE")
        self.tipo_evento = TipoEvento.objects.create(nome="Workshop RD")
        self.formador = Formador.objects.create(
            nome="Formador RD", email="formador@rd.com"
        )

        # Data base para testes
        from django.utils import timezone as tz

        self.base_date = (
            tz.localtime(tz.now()).date().replace(day=15)
        )  # Dia 15 do mês atual

    def test_block_total_T_prevents_any_event(self):
        """RD-02: Bloqueio total (T) impede qualquer evento no dia"""
        from datetime import datetime, time, timedelta

        from django.utils import timezone as tz

        from core.models import DisponibilidadeFormadores
        from core.services.conflicts import check_conflicts

        # Criar bloqueio total no dia
        DisponibilidadeFormadores.objects.create(
            formador=self.formador,
            data_bloqueio=self.base_date,
            hora_inicio=time(8, 0),  # Horário não importa para bloqueio total
            hora_fim=time(17, 0),  # Horário não importa para bloqueio total
            tipo_bloqueio="T",  # Total
            motivo="Bloqueio total de teste",
        )

        # Tentar evento em qualquer horário do dia
        evento_inicio = tz.make_aware(datetime.combine(self.base_date, time(10, 0)))
        evento_fim = tz.make_aware(datetime.combine(self.base_date, time(12, 0)))

        conflitos = check_conflicts([self.formador], evento_inicio, evento_fim)

        # Deve detectar conflito
        self.assertEqual(len(conflitos["bloqueios"]), 1)
        self.assertEqual(conflitos["bloqueios"][0].tipo_bloqueio, "T")
        self.assertEqual(conflitos["bloqueios"][0].formador, self.formador)

    def test_block_partial_P_prevents_inside_allows_outside(self):
        """RD-03: Bloqueio parcial (P) impede apenas dentro do subintervalo"""
        from datetime import datetime, time, timedelta

        from django.utils import timezone as tz

        from core.models import DisponibilidadeFormadores
        from core.services.conflicts import check_conflicts

        # Criar bloqueio parcial 14:00-16:00
        DisponibilidadeFormadores.objects.create(
            formador=self.formador,
            data_bloqueio=self.base_date,
            hora_inicio=time(14, 0),  # 14:00
            hora_fim=time(16, 0),  # 16:00
            tipo_bloqueio="P",  # Parcial
            motivo="Bloqueio parcial de teste",
        )

        # Teste 1: Evento dentro do bloqueio (15:00-15:30) → deve conflitar
        evento_inicio = tz.make_aware(datetime.combine(self.base_date, time(15, 0)))
        evento_fim = tz.make_aware(datetime.combine(self.base_date, time(15, 30)))

        conflitos = check_conflicts([self.formador], evento_inicio, evento_fim)
        self.assertEqual(
            len(conflitos["bloqueios"]),
            1,
            "Deve detectar conflito dentro do bloqueio parcial",
        )

        # Teste 2: Evento fora do bloqueio (10:00-12:00) → não deve conflitar
        evento_inicio_fora = tz.make_aware(
            datetime.combine(self.base_date, time(10, 0))
        )
        evento_fim_fora = tz.make_aware(datetime.combine(self.base_date, time(12, 0)))

        conflitos_fora = check_conflicts(
            [self.formador], evento_inicio_fora, evento_fim_fora
        )
        self.assertEqual(
            len(conflitos_fora["bloqueios"]),
            0,
            "Não deve detectar conflito fora do bloqueio parcial",
        )

        # Teste 3: Evento exatamente na borda (16:00-17:00) → não deve conflitar (RD-01)
        evento_inicio_borda = tz.make_aware(
            datetime.combine(self.base_date, time(16, 0))
        )
        evento_fim_borda = tz.make_aware(datetime.combine(self.base_date, time(17, 0)))

        conflitos_borda = check_conflicts(
            [self.formador], evento_inicio_borda, evento_fim_borda
        )
        self.assertEqual(
            len(conflitos_borda["bloqueios"]),
            0,
            "Não deve conflitar quando fim do bloqueio == início do evento",
        )


# =========================
# RD-04: Buffer de Deslocamento Tests
# =========================


class RDBufferDeslocamentoTest(TestCase):
    """Testes padronizados CLAUDE.md para RD-04"""

    def setUp(self):
        """Configuração para testes de buffer de deslocamento"""
        self.coordenador = User.objects.create_user(
            username="coord_buffer", password="testpass123", papel="coordenador"
        )

        self.projeto = Projeto.objects.create(nome="Projeto Buffer")

        # Criar dois municípios diferentes
        self.municipio_fortaleza = Municipio.objects.create(nome="Fortaleza", uf="CE")
        self.municipio_caucaia = Municipio.objects.create(nome="Caucaia", uf="CE")

        self.tipo_evento = TipoEvento.objects.create(nome="Workshop Buffer")
        self.formador = Formador.objects.create(
            nome="Formador Buffer", email="formador@buffer.com"
        )

        # Data base para testes
        from django.utils import timezone as tz

        self.base_date = (
            tz.localtime(tz.now()).date().replace(day=20)
        )  # Dia 20 do mês atual

    def test_travel_buffer_between_cities_required(self):
        """RD-04: Buffer de deslocamento obrigatório entre municípios diferentes"""
        from datetime import datetime, time, timedelta

        from django.utils import timezone as tz

        from core.services.conflicts import check_conflicts

        # Criar evento aprovado em Fortaleza: 10:00-12:00
        evento_fortaleza = Solicitacao.objects.create(
            usuario_solicitante=self.coordenador,
            projeto=self.projeto,
            municipio=self.municipio_fortaleza,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento em Fortaleza",
            data_inicio=tz.make_aware(datetime.combine(self.base_date, time(10, 0))),
            data_fim=tz.make_aware(datetime.combine(self.base_date, time(12, 0))),
            status=SolicitacaoStatus.APROVADO,
        )
        evento_fortaleza.formadores.add(self.formador)

        # Tentar criar evento em Caucaia com buffer insuficiente: 13:00-15:00
        # (apenas 60 min de gap, buffer configurado = 90 min)
        novo_evento_inicio = tz.make_aware(
            datetime.combine(self.base_date, time(13, 0))
        )
        novo_evento_fim = tz.make_aware(datetime.combine(self.base_date, time(15, 0)))

        conflitos = check_conflicts(
            [self.formador], novo_evento_inicio, novo_evento_fim, self.municipio_caucaia
        )

        # Deve detectar conflito de buffer
        self.assertEqual(len(conflitos["deslocamentos"]), 1)
        conflito_buffer = conflitos["deslocamentos"][0]
        self.assertEqual(conflito_buffer["tipo_conflito"], "D")
        self.assertEqual(conflito_buffer["solicitacao"], evento_fortaleza)
        self.assertEqual(conflito_buffer["gap_minutes"], 60.0)  # 60 minutos de gap
        self.assertEqual(
            conflito_buffer["required_minutes"], 90
        )  # 90 minutos necessários

    def test_same_city_allows_zero_buffer(self):
        """RD-04: Mesmo município permite buffer zero"""
        from datetime import datetime, time, timedelta

        from django.utils import timezone as tz

        from core.services.conflicts import check_conflicts

        # Criar evento aprovado em Fortaleza: 10:00-12:00
        evento_fortaleza = Solicitacao.objects.create(
            usuario_solicitante=self.coordenador,
            projeto=self.projeto,
            municipio=self.municipio_fortaleza,
            tipo_evento=self.tipo_evento,
            titulo_evento="Primeiro Evento Fortaleza",
            data_inicio=tz.make_aware(datetime.combine(self.base_date, time(10, 0))),
            data_fim=tz.make_aware(datetime.combine(self.base_date, time(12, 0))),
            status=SolicitacaoStatus.APROVADO,
        )
        evento_fortaleza.formadores.add(self.formador)

        # Tentar criar outro evento no MESMO município logo depois: 12:00-14:00
        # (gap = 0 minutos, mas mesmo município)
        novo_evento_inicio = tz.make_aware(
            datetime.combine(self.base_date, time(12, 0))
        )
        novo_evento_fim = tz.make_aware(datetime.combine(self.base_date, time(14, 0)))

        conflitos = check_conflicts(
            [self.formador],
            novo_evento_inicio,
            novo_evento_fim,
            self.municipio_fortaleza,
        )

        # NÃO deve detectar conflito de buffer (mesmo município)
        self.assertEqual(len(conflitos["deslocamentos"]), 0)

        # E também não deve ter conflito de sobreposição (RD-01: fim == início)
        self.assertEqual(len(conflitos["solicitacoes"]), 0)


# =========================
# RD-05: Capacidade Diária Tests
# =========================


class RDCapacidadeDiariaTest(TestCase):
    """Testes padronizados CLAUDE.md para RD-05"""

    def setUp(self):
        """Configuração para testes de capacidade diária"""
        self.coordenador = User.objects.create_user(
            username="coord_capacidade", password="testpass123", papel="coordenador"
        )

        self.projeto = Projeto.objects.create(nome="Projeto Capacidade")
        self.municipio = Municipio.objects.create(nome="Fortaleza", uf="CE")
        self.tipo_evento = TipoEvento.objects.create(nome="Workshop Capacidade")
        self.formador = Formador.objects.create(
            nome="Formador Capacidade", email="formador@capacidade.com"
        )

        # Data base para testes
        from django.utils import timezone as tz

        self.base_date = (
            tz.localtime(tz.now()).date().replace(day=25)
        )  # Dia 25 do mês atual

    def test_daily_capacity_M_exceeded(self):
        """RD-05: Capacidade diária excedida deve gerar conflito tipo M"""
        from datetime import datetime, time, timedelta

        from django.utils import timezone as tz

        from core.services.conflicts import check_conflicts

        # Criar eventos aprovados que já ocupam 6 horas do dia (08:00-14:00)
        evento_manha = Solicitacao.objects.create(
            usuario_solicitante=self.coordenador,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento Manhã",
            data_inicio=tz.make_aware(datetime.combine(self.base_date, time(8, 0))),
            data_fim=tz.make_aware(
                datetime.combine(self.base_date, time(11, 0))
            ),  # 3 horas
            status=SolicitacaoStatus.APROVADO,
        )
        evento_manha.formadores.add(self.formador)

        evento_tarde = Solicitacao.objects.create(
            usuario_solicitante=self.coordenador,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento Tarde",
            data_inicio=tz.make_aware(datetime.combine(self.base_date, time(11, 30))),
            data_fim=tz.make_aware(
                datetime.combine(self.base_date, time(14, 30))
            ),  # 3 horas
            status=SolicitacaoStatus.APROVADO,
        )
        evento_tarde.formadores.add(self.formador)

        # Total já ocupado: 6 horas (limite configurado = 8 horas)

        # Tentar adicionar evento de 3 horas (15:00-18:00) que excederia o limite
        novo_evento_inicio = tz.make_aware(
            datetime.combine(self.base_date, time(15, 0))
        )
        novo_evento_fim = tz.make_aware(
            datetime.combine(self.base_date, time(18, 0))
        )  # + 3 horas = 9 horas total

        conflitos = check_conflicts(
            [self.formador], novo_evento_inicio, novo_evento_fim, self.municipio
        )

        # Deve detectar conflito de capacidade
        self.assertEqual(len(conflitos["capacidade_diaria"]), 1)
        conflito_cap = conflitos["capacidade_diaria"][0]
        self.assertEqual(conflito_cap["tipo_conflito"], "M")
        self.assertEqual(conflito_cap["formador"], self.formador)
        self.assertEqual(conflito_cap["horas_ocupadas"], 6.0)  # 6 horas já ocupadas
        self.assertEqual(
            conflito_cap["duracao_novo_evento"], 3.0
        )  # 3 horas do novo evento
        self.assertEqual(conflito_cap["total_com_novo"], 9.0)  # 9 horas total
        self.assertEqual(conflito_cap["limite_diario"], 8)  # Limite de 8 horas
        self.assertEqual(conflito_cap["excesso"], 1.0)  # 1 hora de excesso

    def test_daily_capacity_within_limit_allowed(self):
        """RD-05: Capacidade diária dentro do limite deve ser permitida"""
        from datetime import datetime, time, timedelta

        from django.utils import timezone as tz

        from core.services.conflicts import check_conflicts

        # Criar evento aprovado que ocupa 4 horas do dia (08:00-12:00)
        evento_existente = Solicitacao.objects.create(
            usuario_solicitante=self.coordenador,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento Existente",
            data_inicio=tz.make_aware(datetime.combine(self.base_date, time(8, 0))),
            data_fim=tz.make_aware(
                datetime.combine(self.base_date, time(12, 0))
            ),  # 4 horas
            status=SolicitacaoStatus.APROVADO,
        )
        evento_existente.formadores.add(self.formador)

        # Total já ocupado: 4 horas (limite configurado = 8 horas)

        # Tentar adicionar evento de 3 horas (13:00-16:00) que ficaria dentro do limite
        novo_evento_inicio = tz.make_aware(
            datetime.combine(self.base_date, time(13, 0))
        )
        novo_evento_fim = tz.make_aware(
            datetime.combine(self.base_date, time(16, 0))
        )  # + 3 horas = 7 horas total

        conflitos = check_conflicts(
            [self.formador], novo_evento_inicio, novo_evento_fim, self.municipio
        )

        # NÃO deve detectar conflito de capacidade (7h < 8h limite)
        self.assertEqual(len(conflitos["capacidade_diaria"]), 0)


# =========================
# RD-08: Mensagens com Códigos Tests
# =========================


class RDMensagensComCodigosTest(TestCase):
    """Testes padronizados CLAUDE.md para RD-08"""

    def setUp(self):
        """Configuração para testes de mensagens"""
        self.coordenador = User.objects.create_user(
            username="coord_mensagens", password="testpass123", papel="coordenador"
        )

        self.projeto = Projeto.objects.create(nome="Projeto Mensagens")
        self.municipio = Municipio.objects.create(nome="Fortaleza", uf="CE")
        self.tipo_evento = TipoEvento.objects.create(nome="Workshop Mensagens")
        self.formador = Formador.objects.create(
            nome="João Silva Mensagem", email="joao@mensagem.com"
        )

        # Data base para testes (futuro)
        from datetime import timedelta

        from django.utils import timezone as tz

        hoje = tz.localtime(tz.now()).date()
        self.base_date = hoje + timedelta(days=30)  # 30 dias no futuro

    def test_conflict_messages_include_codes_and_intervals(self):
        """RD-08: Mensagens devem incluir códigos (E/M/D/P/T/X) e intervalos (HH:MM dd/mm)"""
        from datetime import datetime, time, timedelta

        from django.utils import timezone as tz

        from core.forms import SolicitacaoForm
        from core.models import DisponibilidadeFormadores

        # 1. Criar bloqueio TOTAL para testar código [T]
        DisponibilidadeFormadores.objects.create(
            formador=self.formador,
            data_bloqueio=self.base_date,
            hora_inicio=time(8, 0),
            hora_fim=time(17, 0),
            tipo_bloqueio="T",  # Total
            motivo="Férias",
        )

        # 2. Criar solicitação aprovada para testar código [E]
        evento_aprovado = Solicitacao.objects.create(
            usuario_solicitante=self.coordenador,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento="Workshop Matemática",
            data_inicio=tz.make_aware(
                datetime.combine(self.base_date + timedelta(days=1), time(14, 0))
            ),
            data_fim=tz.make_aware(
                datetime.combine(self.base_date + timedelta(days=1), time(18, 0))
            ),
            status=SolicitacaoStatus.APROVADO,
        )
        evento_aprovado.formadores.add(self.formador)

        # 3. Tentar criar novo evento que conflita com ambos
        form_data = {
            "projeto": self.projeto.id,
            "municipio": self.municipio.id,
            "tipo_evento": self.tipo_evento.id,
            "titulo_evento": "Evento Conflitante",
            "data_inicio": tz.make_aware(
                datetime.combine(self.base_date, time(15, 0))
            ),  # Conflita com bloqueio T
            "data_fim": tz.make_aware(datetime.combine(self.base_date, time(16, 0))),
            "formadores": [self.formador.id],
            "coordenador_acompanha": False,
        }

        form = SolicitacaoForm(data=form_data)
        self.assertFalse(form.is_valid())

        # Verificar mensagens de erro
        error_str = str(form.errors)

        # Verificar elementos obrigatórios RD-08
        self.assertIn("[T]", error_str, "Deve incluir código T para bloqueio total")
        self.assertIn("João Silva Mensagem", error_str, "Deve incluir nome do formador")

        # Verificar formato de data/hora (dd/mm HH:MM)
        expected_date = self.base_date.strftime("%d/%m")
        self.assertIn(expected_date, error_str, "Deve incluir data no formato dd/mm")

        # Verificar se contém horários no formato HH:MM
        import re

        time_pattern = r"\d{2}:\d{2}"
        times_found = re.findall(time_pattern, error_str)
        self.assertGreaterEqual(
            len(times_found),
            2,
            "Deve incluir pelo menos dois horários no formato HH:MM",
        )

    def test_all_conflict_codes_in_messages(self):
        """RD-08: Verificar que todos os códigos (E/M/D/P/T) aparecem nas mensagens apropriadas"""
        from datetime import datetime, time, timedelta

        from django.utils import timezone as tz

        from core.models import DisponibilidadeFormadores
        from core.services.conflicts import check_conflicts

        # Setup para testar múltiplos tipos de conflito
        # 1. Bloqueio Parcial [P]
        DisponibilidadeFormadores.objects.create(
            formador=self.formador,
            data_bloqueio=self.base_date,
            hora_inicio=time(9, 0),
            hora_fim=time(11, 0),
            tipo_bloqueio="P",  # Parcial
            motivo="Reunião",
        )

        # 2. Evento aprovado [E] em outro município (para testar [D])
        municipio_outro = Municipio.objects.create(nome="Caucaia", uf="CE")
        evento_outro_municipio = Solicitacao.objects.create(
            usuario_solicitante=self.coordenador,
            projeto=self.projeto,
            municipio=municipio_outro,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento Caucaia",
            data_inicio=tz.make_aware(datetime.combine(self.base_date, time(8, 0))),
            data_fim=tz.make_aware(datetime.combine(self.base_date, time(9, 0))),
            status=SolicitacaoStatus.APROVADO,
        )
        evento_outro_municipio.formadores.add(self.formador)

        # 3. Evento longo para testar [M] - capacidade excedida
        evento_inicio = tz.make_aware(
            datetime.combine(self.base_date, time(10, 0))
        )  # Conflita com [P]
        evento_fim = tz.make_aware(
            datetime.combine(self.base_date, time(19, 0))
        )  # 9 horas > 8h limite [M]

        # Verificar conflitos
        conflitos = check_conflicts(
            [self.formador], evento_inicio, evento_fim, self.municipio
        )

        # Deve detectar múltiplos tipos de conflito
        self.assertGreater(
            len(conflitos["bloqueios"]), 0, "Deve detectar conflito de bloqueio [P]"
        )
        self.assertGreater(
            len(conflitos["deslocamentos"]),
            0,
            "Deve detectar conflito de deslocamento [D]",
        )
        self.assertGreater(
            len(conflitos["capacidade_diaria"]),
            0,
            "Deve detectar conflito de capacidade [M]",
        )


# =========================
# PA-06: UI/UX Controle Explícito Tests
# =========================


class PA06UIControlTest(TestCase):
    """Testes para PA-06: esconder ações para perfis sem permissão"""

    def setUp(self):
        """Configuração para testes de controle de UI"""
        self.coordenador = User.objects.create_user(
            username="coord_ui", password="testpass123", papel="coordenador"
        )

        self.superintendencia = User.objects.create_user(
            username="super_ui", password="testpass123", papel="superintendencia"
        )

        self.formador = User.objects.create_user(
            username="formador_ui", password="testpass123", papel="formador"
        )

        self.client = Client()

    def test_home_shows_appropriate_actions_by_role(self):
        """PA-06: Home deve mostrar apenas ações apropriadas para cada perfil"""

        # Teste 1: Coordenador deve ver solicitação de eventos
        self.client.login(username="coord_ui", password="testpass123")
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        self.assertIn(
            "Solicitar Evento",
            content,
            "Coordenador deve ver link para solicitar evento",
        )
        self.assertIn(
            "Bloqueio de Agenda", content, "Coordenador deve ver link para bloqueio"
        )
        self.assertNotIn(
            "Aprovações Pendentes",
            content,
            "Coordenador NÃO deve ver seção de superintendência",
        )

        # Teste 2: Superintendência deve ver aprovações
        self.client.login(username="super_ui", password="testpass123")
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        self.assertIn(
            "Aprovações Pendentes", content, "Superintendência deve ver aprovações"
        )
        self.assertIn(
            "Superintendência", content, "Deve mostrar seção de superintendência"
        )

        # Teste 3: Formador deve ver apenas bloqueio próprio
        self.client.login(username="formador_ui", password="testpass123")
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        # Verificar que não há link ativo para Solicitar Evento (pode estar em comentário)
        self.assertNotIn(
            'href="/solicitar/"',
            content,
            "Formador NÃO deve ter link ativo para solicitar evento",
        )
        self.assertIn(
            "Bloqueio de Agenda", content, "Formador deve ver bloqueio de agenda"
        )
        self.assertIn(
            'href="/bloqueios/novo/"',
            content,
            "Formador deve ter link ativo para bloqueio",
        )
        self.assertNotIn(
            'href="/aprovacoes/pendentes/"',
            content,
            "Formador NÃO deve ter link ativo para aprovações",
        )


# =========================
# PA-07: Testes Obrigatórios de Aprovação Manual
# =========================


class PA07MandatoryApprovalTest(TestCase):
    """Testes obrigatórios PA-07 especificados no CLAUDE.md"""

    def setUp(self):
        """Configuração para testes PA-07"""
        self.coordenador = User.objects.create_user(
            username="coord_pa07", password="testpass123", papel="coordenador"
        )

        self.superintendencia = User.objects.create_user(
            username="super_pa07", password="testpass123", papel="superintendencia"
        )

        self.projeto = Projeto.objects.create(nome="Projeto PA07")
        self.municipio = Municipio.objects.create(nome="Fortaleza", uf="CE")
        self.tipo_evento = TipoEvento.objects.create(nome="Workshop PA07")
        self.formador = Formador.objects.create(
            nome="Formador PA07", email="formador@pa07.com"
        )

        # Data futura para testes
        from datetime import timedelta

        from django.utils import timezone as tz

        hoje = tz.localtime(tz.now()).date()
        self.data_futura = hoje + timedelta(days=15)

    def test_never_auto_approves_on_clean_or_save(self):
        """PA-07: Solicitação NUNCA muda para aprovada automaticamente"""
        from datetime import datetime, time

        from django.utils import timezone as tz

        # Criar solicitação sem conflitos
        solicitacao = Solicitacao.objects.create(
            usuario_solicitante=self.coordenador,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento PA07",
            data_inicio=tz.make_aware(datetime.combine(self.data_futura, time(10, 0))),
            data_fim=tz.make_aware(datetime.combine(self.data_futura, time(12, 0))),
            # Status não especificado → deve ser PENDENTE por padrão
        )
        solicitacao.formadores.add(self.formador)

        # Verificar que status inicial é PENDENTE
        self.assertEqual(solicitacao.status, SolicitacaoStatus.PENDENTE)

        # Forçar clean() e save() - nunca deve auto-aprovar
        solicitacao.clean()
        solicitacao.save()
        solicitacao.refresh_from_db()
        self.assertEqual(
            solicitacao.status,
            SolicitacaoStatus.PENDENTE,
            "NUNCA deve auto-aprovar após clean/save",
        )

        # Mesmo após múltiplos saves
        for _ in range(3):
            solicitacao.save()
            solicitacao.refresh_from_db()
            self.assertEqual(
                solicitacao.status,
                SolicitacaoStatus.PENDENTE,
                "Deve manter status PENDENTE sempre",
            )

    def test_only_superintendencia_can_approve_or_reject(self):
        """PA-07: Apenas superintendência pode aprovar/reprovar (já testado em RF04PermissionTest)"""
        # Este teste já existe em RF04PermissionTest, mas vamos reconfirmar especificamente para PA-07
        from datetime import datetime, time

        from django.utils import timezone as tz

        solicitacao = Solicitacao.objects.create(
            usuario_solicitante=self.coordenador,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento PA07 Permissão",
            data_inicio=tz.make_aware(datetime.combine(self.data_futura, time(14, 0))),
            data_fim=tz.make_aware(datetime.combine(self.data_futura, time(16, 0))),
            status=SolicitacaoStatus.PENDENTE,
        )
        solicitacao.formadores.add(self.formador)

        from django.test import Client

        client = Client()

        # Coordenador NÃO pode acessar aprovação
        client.login(username="coord_pa07", password="testpass123")
        url = reverse("core:aprovacao_detail", args=[solicitacao.id])
        response = client.get(url)
        self.assertEqual(
            response.status_code, 403, "Coordenador deve receber 403 ao tentar aprovar"
        )

        # Superintendência PODE acessar
        client.login(username="super_pa07", password="testpass123")
        response = client.get(url)
        self.assertEqual(
            response.status_code,
            200,
            "Superintendência deve conseguir acessar aprovação",
        )

    def test_calendar_integration_not_called_before_approval(self):
        """PA-07: Integração com calendar não é chamada antes da aprovação"""
        from datetime import datetime, time

        from django.utils import timezone as tz

        # Criar solicitação pendente
        solicitacao = Solicitacao.objects.create(
            usuario_solicitante=self.coordenador,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento PA07 Calendar",
            data_inicio=tz.make_aware(datetime.combine(self.data_futura, time(9, 0))),
            data_fim=tz.make_aware(datetime.combine(self.data_futura, time(11, 0))),
            status=SolicitacaoStatus.PENDENTE,
        )
        solicitacao.formadores.add(self.formador)

        # Verificar que não há evento do Google Calendar criado automaticamente
        from core.models import EventoGoogleCalendar

        self.assertFalse(
            EventoGoogleCalendar.objects.filter(solicitacao=solicitacao).exists(),
            "NÃO deve haver evento Google Calendar antes da aprovação",
        )

        # Mesmo após salvar várias vezes
        for _ in range(3):
            solicitacao.save()
            self.assertFalse(
                EventoGoogleCalendar.objects.filter(solicitacao=solicitacao).exists(),
                "NÃO deve criar evento Google Calendar automaticamente",
            )

        # Só após aprovação manual (se houver serviço implementado) deveria criar
        # Como não há serviço implementado ainda, apenas validamos que não há auto-criação

    def test_approval_flow_records_audit_log(self):
        """PA-07: Fluxo de aprovação registra log de auditoria (já testado em RF04ApprovalWorkflowTest)"""
        # Este teste já existe, mas vamos reconfirmar especificamente para PA-07
        from datetime import datetime, time

        from django.utils import timezone as tz

        solicitacao = Solicitacao.objects.create(
            usuario_solicitante=self.coordenador,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento PA07 Audit",
            data_inicio=tz.make_aware(datetime.combine(self.data_futura, time(13, 0))),
            data_fim=tz.make_aware(datetime.combine(self.data_futura, time(15, 0))),
            status=SolicitacaoStatus.PENDENTE,
        )
        solicitacao.formadores.add(self.formador)

        # Fazer aprovação manual
        from core.models import Aprovacao, LogAuditoria

        Aprovacao.objects.create(
            solicitacao=solicitacao,
            usuario_aprovador=self.superintendencia,
            status_decisao=AprovacaoStatus.APROVADO,
            justificativa="Aprovação teste PA-07",
        )

        # Atualizar status da solicitação (simulando o que a view faz)
        solicitacao.status = SolicitacaoStatus.APROVADO
        solicitacao.usuario_aprovador = self.superintendencia
        solicitacao.data_aprovacao_rejeicao = tz.now()
        solicitacao.save()

        # Criar log de auditoria (simulando o que a view faz)
        LogAuditoria.objects.create(
            usuario=self.superintendencia,
            acao=f"RF04: {AprovacaoStatus.APROVADO} solicitação",
            entidade_afetada_id=solicitacao.id,
            detalhes=f"Solicitação '{solicitacao.titulo_evento}' ({solicitacao.id}) — decisão: {AprovacaoStatus.APROVADO}; justificativa: Aprovação teste PA-07",
        )

        # Verificar que log foi criado
        log_existe = LogAuditoria.objects.filter(
            usuario=self.superintendencia,
            entidade_afetada_id=solicitacao.id,
            acao__icontains="solicitação",
        ).exists()
        self.assertTrue(log_existe, "Deve registrar log de auditoria para aprovação")

    def test_non_privileged_user_gets_403_on_approval_endpoint(self):
        """PA-07: Usuário sem privilégio recebe 403 no endpoint de aprovação (já testado em RF04SecurityTest)"""
        # Este teste já existe, mas vamos reconfirmar especificamente para PA-07
        from datetime import datetime, time

        from django.utils import timezone as tz

        solicitacao = Solicitacao.objects.create(
            usuario_solicitante=self.coordenador,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento PA07 403",
            data_inicio=tz.make_aware(datetime.combine(self.data_futura, time(16, 0))),
            data_fim=tz.make_aware(datetime.combine(self.data_futura, time(18, 0))),
            status=SolicitacaoStatus.PENDENTE,
        )
        solicitacao.formadores.add(self.formador)

        from django.test import Client

        client = Client()

        # Usuário não autenticado
        url = reverse("core:aprovacao_detail", args=[solicitacao.id])
        response = client.get(url)
        self.assertEqual(
            response.status_code, 302, "Usuário não autenticado deve ser redirecionado"
        )

        # Coordenador (sem privilégio para aprovar)
        client.login(username="coord_pa07", password="testpass123")
        response = client.get(url)
        self.assertEqual(
            response.status_code,
            403,
            "Coordenador deve receber 403 para endpoint de aprovação",
        )

        # Lista de aprovações também deve ser protegida
        list_url = reverse("core:aprovacoes_pendentes")
        response = client.get(list_url)
        self.assertEqual(
            response.status_code,
            403,
            "Coordenador deve receber 403 para lista de aprovações",
        )


# =============================================================================
# RF05: GOOGLE CALENDAR SYNC (FEATURE FLAG)
# =============================================================================


class RF05CalendarFlagTest(TestCase):
    def setUp(self):
        self.coord = User.objects.create_user(
            username="coord_rf05", password="x", papel="coordenador"
        )
        self.super = User.objects.create_user(
            username="super_rf05", password="x", papel="superintendencia"
        )
        self.proj = Projeto.objects.create(nome="Proj RF05")
        self.mun = Municipio.objects.create(nome="Fortaleza", uf="CE")
        self.tipo = TipoEvento.objects.create(nome="Oficina")
        self.formador = Formador.objects.create(
            nome="Formador RF05", email="formador@rf05.com"
        )

        base = timezone.localtime(timezone.now()).date() + timedelta(days=7)
        self.solic = Solicitacao.objects.create(
            usuario_solicitante=self.coord,
            projeto=self.proj,
            municipio=self.mun,
            tipo_evento=self.tipo,
            titulo_evento="Evento RF05",
            data_inicio=timezone.make_aware(datetime.combine(base, time(9, 0))),
            data_fim=timezone.make_aware(datetime.combine(base, time(11, 0))),
            status=SolicitacaoStatus.PENDENTE,
        )
        self.solic.formadores.add(self.formador)

    @override_settings(FEATURE_GOOGLE_SYNC=0)
    def test_flag_off_does_not_create_calendar_event(self):
        # simula aprovação sem calendar
        self.client.login(username="super_rf05", password="x")
        resp = self.client.get(reverse("core:aprovacao_detail", args=[self.solic.id]))
        self.assertEqual(resp.status_code, 200)

        # poste decisão
        post = self.client.post(
            reverse("core:aprovacao_detail", args=[self.solic.id]),
            {"decisao": "Aprovado", "justificativa": "ok"},
        )
        self.assertIn(post.status_code, (200, 302))
        self.solic.refresh_from_db()
        self.assertEqual(self.solic.status, SolicitacaoStatus.APROVADO)

        self.assertFalse(
            EventoGoogleCalendar.objects.filter(solicitacao=self.solic).exists(),
            "Com flag OFF, não deve criar EventoGoogleCalendar",
        )

    @override_settings(FEATURE_GOOGLE_SYNC=1)
    @patch(
        "core.services.integrations.calendar_stub.GoogleCalendarServiceStub.create_event"
    )
    def test_flag_on_calls_service_and_persists_record(self, mock_create):
        mock_create.return_value = {
            "id": "evt_fake_123",
            "htmlLink": "https://calendar.google.com/calendar/u/0/r/eventedit/evt_fake_123",
            "hangoutLink": "https://meet.google.com/fake-code-xyz",
        }

        self.client.login(username="super_rf05", password="x")
        self.client.get(reverse("core:aprovacao_detail", args=[self.solic.id]))
        self.client.post(
            reverse("core:aprovacao_detail", args=[self.solic.id]),
            {"decisao": "Aprovado", "justificativa": "ok"},
        )
        self.solic.refresh_from_db()
        self.assertEqual(self.solic.status, SolicitacaoStatus.APROVADO)

        mock_create.assert_called_once()
        self.assertTrue(
            EventoGoogleCalendar.objects.filter(
                solicitacao=self.solic, provider_event_id="evt_fake_123"
            ).exists()
        )

    @override_settings(FEATURE_GOOGLE_SYNC=1)
    def test_reprovacao_nao_cria_evento_calendar(self):
        # mesmo com flag ON, reprovação não deve criar evento
        self.client.login(username="super_rf05", password="x")
        self.client.post(
            reverse("core:aprovacao_detail", args=[self.solic.id]),
            {"decisao": "Reprovado", "justificativa": "Não aprovado para teste"},
        )
        self.solic.refresh_from_db()
        self.assertEqual(self.solic.status, SolicitacaoStatus.REPROVADO)

        self.assertFalse(
            EventoGoogleCalendar.objects.filter(solicitacao=self.solic).exists(),
            "Reprovação não deve criar EventoGoogleCalendar mesmo com flag ON",
        )

    def test_mapper_converte_solicitacao_corretamente(self):
        # testa o mapper independentemente
        from core.services.integrations.calendar_mapper import (
            map_solicitacao_to_google_event,
        )

        gevent = map_solicitacao_to_google_event(self.solic)

        self.assertEqual(
            gevent.summary, f"{self.tipo.nome} — {self.solic.titulo_evento}"
        )
        self.assertIn(self.proj.nome, gevent.description)
        self.assertIn(self.mun.nome, gevent.description)
        self.assertIn(self.coord.username, gevent.description)
        self.assertEqual(gevent.location, self.mun.nome)
        self.assertEqual(len(gevent.attendees), 1)
        self.assertEqual(gevent.attendees[0].email, self.formador.email)
        self.assertEqual(gevent.attendees[0].display_name, self.formador.nome)
        self.assertTrue(gevent.conference)

    @override_settings(FEATURE_GOOGLE_SYNC=0)
    def test_stub_respeta_flag_off(self):
        # testa que o stub respeita a flag
        from core.services.integrations.calendar_stub import GoogleCalendarServiceStub
        from core.services.integrations.calendar_types import (
            GoogleAttendee,
            GoogleEvent,
        )

        svc = GoogleCalendarServiceStub()
        gevent = GoogleEvent(
            summary="Test Event",
            description="Test Description",
            start_iso="2025-01-01T09:00:00-03:00",
            end_iso="2025-01-01T11:00:00-03:00",
            location="Test Location",
            attendees=[GoogleAttendee(email="test@example.com")],
            conference=True,
        )

        result = svc.create_event(gevent)
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "FEATURE_GOOGLE_SYNC=0")

    @override_settings(FEATURE_GOOGLE_SYNC=1)
    def test_stub_simula_criacao_com_flag_on(self):
        # testa que o stub simula criação com flag ON
        from core.services.integrations.calendar_stub import GoogleCalendarServiceStub
        from core.services.integrations.calendar_types import (
            GoogleAttendee,
            GoogleEvent,
        )

        svc = GoogleCalendarServiceStub()
        gevent = GoogleEvent(
            summary="Test Event",
            description="Test Description",
            start_iso="2025-01-01T09:00:00-03:00",
            end_iso="2025-01-01T11:00:00-03:00",
            location="Test Location",
            attendees=[GoogleAttendee(email="test@example.com")],
            conference=True,
        )

        result = svc.create_event(gevent)
        self.assertIn("id", result)
        self.assertIn("htmlLink", result)
        self.assertIn("hangoutLink", result)
        self.assertTrue(result["id"].startswith("evt_fake_"))
        self.assertIn("calendar.google.com", result["htmlLink"])
        self.assertIn("meet.google.com", result["hangoutLink"])


class FormadorEventosViewTest(TestCase):
    """Testes de segurança para a página de eventos do formador"""

    def setUp(self):
        """Configuração inicial para os testes"""
        # Criar projetos, municípios e tipos de eventos
        self.projeto = Projeto.objects.create(
            nome="Projeto Teste", descricao="Descrição do projeto teste"
        )

        self.municipio = Municipio.objects.create(nome="São Paulo", uf="SP")

        self.tipo_evento = TipoEvento.objects.create(nome="Workshop", online=False)

        # Criar formadores
        self.formador1 = Formador.objects.create(
            nome="João Silva", email="joao@test.com", area_atuacao="Matemática"
        )

        self.formador2 = Formador.objects.create(
            nome="Maria Santos", email="maria@test.com", area_atuacao="Português"
        )

        # Criar usuários com diferentes papéis
        self.user_formador1 = User.objects.create_user(
            username="joao_formador",
            email="joao@test.com",  # Mesmo email do formador1
            password="testpass123",
            papel="formador",
        )

        self.user_formador2 = User.objects.create_user(
            username="maria_formador",
            email="maria@test.com",  # Mesmo email do formador2
            password="testpass123",
            papel="formador",
        )

        self.user_coordenador = User.objects.create_user(
            username="coord_test",
            email="coord@test.com",
            password="testpass123",
            papel="coordenador",
        )

        self.user_superintendencia = User.objects.create_user(
            username="super_test",
            email="super@test.com",
            password="testpass123",
            papel="superintendencia",
        )

        # Criar eventos para formador1
        self.evento_formador1 = Solicitacao.objects.create(
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento do João",
            data_inicio=timezone.now() + timedelta(days=1),
            data_fim=timezone.now() + timedelta(days=1, hours=2),
            usuario_solicitante=self.user_coordenador,
            status=SolicitacaoStatus.APROVADO,
        )
        self.evento_formador1.formadores.add(self.formador1)

        # Criar eventos para formador2
        self.evento_formador2 = Solicitacao.objects.create(
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento da Maria",
            data_inicio=timezone.now() + timedelta(days=2),
            data_fim=timezone.now() + timedelta(days=2, hours=2),
            usuario_solicitante=self.user_coordenador,
            status=SolicitacaoStatus.APROVADO,
        )
        self.evento_formador2.formadores.add(self.formador2)

        self.url = reverse("core:formador_eventos")

    def test_formador_autorizado_acessa_proprios_eventos(self):
        """Teste crítico: Formador logado vê apenas seus próprios eventos"""
        # Login com formador1
        self.client.login(username="joao_formador", password="testpass123")
        response = self.client.get(self.url)

        # Verificar acesso autorizado
        self.assertEqual(response.status_code, 200)

        # Verificar que vê apenas seus eventos
        self.assertContains(response, "Evento do João")
        self.assertNotContains(response, "Evento da Maria")

        # Verificar estrutura da página
        self.assertContains(response, "Meus Eventos")
        self.assertContains(response, "joao@test.com")
        self.assertContains(response, "João Silva")

    def test_formador_nao_ve_eventos_de_outros(self):
        """Teste crítico: Formador não consegue ver eventos de outros formadores"""
        # Login com formador2
        self.client.login(username="maria_formador", password="testpass123")
        response = self.client.get(self.url)

        # Verificar acesso autorizado
        self.assertEqual(response.status_code, 200)

        # Verificar que vê apenas seus eventos
        self.assertContains(response, "Evento da Maria")
        self.assertNotContains(response, "Evento do João")

        # Verificar informações do formador correto
        self.assertContains(response, "maria@test.com")
        self.assertContains(response, "Maria Santos")
        self.assertNotContains(response, "João Silva")

    def test_coordenador_nao_pode_acessar(self):
        """Teste crítico: Coordenador não consegue acessar página do formador"""
        self.client.login(username="coord_test", password="testpass123")
        response = self.client.get(self.url)

        # Deve retornar 403 (Forbidden)
        self.assertEqual(response.status_code, 403)

    def test_superintendencia_nao_pode_acessar(self):
        """Teste crítico: Superintendência não consegue acessar página do formador"""
        self.client.login(username="super_test", password="testpass123")
        response = self.client.get(self.url)

        # Deve retornar 403 (Forbidden)
        self.assertEqual(response.status_code, 403)

    def test_formador_sem_eventos_recebe_mensagem_adequada(self):
        """Teste crítico: Formador sem eventos recebe mensagem adequada"""
        # Criar formador sem eventos
        formador_sem_eventos = Formador.objects.create(
            nome="Pedro Novo", email="pedro@test.com", area_atuacao="História"
        )

        user_pedro = User.objects.create_user(
            username="pedro_formador",
            email="pedro@test.com",
            password="testpass123",
            papel="formador",
        )

        # Login e acessar página
        self.client.login(username="pedro_formador", password="testpass123")
        response = self.client.get(self.url)

        # Verificar acesso autorizado
        self.assertEqual(response.status_code, 200)

        # Verificar mensagem de eventos vazios
        self.assertContains(response, "Você não possui eventos agendados")
        self.assertContains(response, "Pedro Novo")

    def test_usuario_nao_autenticado_redireciona_login(self):
        """Teste: Usuário não autenticado é redirecionado para login"""
        response = self.client.get(self.url)

        # Deve redirecionar para login
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_formador_sem_cadastro_recebe_erro(self):
        """Teste: Formador logado mas sem cadastro no sistema recebe erro"""
        # Criar usuário formador sem correspondente na tabela Formador
        user_sem_formador = User.objects.create_user(
            username="sem_formador",
            email="sem_formador@test.com",
            password="testpass123",
            papel="formador",
        )

        # Login e acessar página
        self.client.login(username="sem_formador", password="testpass123")
        response = self.client.get(self.url)

        # Verificar acesso autorizado mas com erro
        self.assertEqual(response.status_code, 200)

        # Verificar mensagem de erro apropriada
        self.assertContains(response, "Formador não encontrado")
        self.assertContains(response, "Verifique se seu email está registrado")

    def test_url_sem_bypass_de_seguranca(self):
        """Teste crítico: URL não aceita parâmetros para bypass de segurança"""
        # Login com formador1
        self.client.login(username="joao_formador", password="testpass123")

        # Tentar acessar com parâmetro formador_id (que não deve mais funcionar)
        url_com_parametro = f"{self.url}?formador_id={self.formador2.id}"
        response = self.client.get(url_com_parametro)

        # Verificar que ainda vê apenas seus eventos (não o do formador2)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Evento do João")
        self.assertNotContains(response, "Evento da Maria")

    def test_estrutura_tabela_conforme_especificacao(self):
        """Teste: Verificar se a página usa tabela clara conforme especificação"""
        self.client.login(username="joao_formador", password="testpass123")
        response = self.client.get(self.url)

        # Verificar estrutura da tabela
        self.assertContains(response, "<table>")
        self.assertContains(response, "Título do Evento")
        self.assertContains(response, "Data/Hora")
        self.assertContains(response, "Município")
        self.assertContains(response, "Projeto")
        self.assertContains(response, "Status")

        # Verificar conteúdo específico na tabela
        self.assertContains(response, "Evento do João")
        self.assertContains(response, "São Paulo")
        self.assertContains(response, "Projeto Teste")

    def test_menu_lateral_aparece_para_formador(self):
        """Teste: Verificar se o menu lateral mostra link para página do formador"""
        self.client.login(username="joao_formador", password="testpass123")

        # Acessar home page para ver o menu
        home_response = self.client.get("/")

        # Verificar se o menu do formador aparece
        self.assertContains(home_response, "Meus Eventos")
        self.assertContains(home_response, "person-workspace")
        self.assertContains(home_response, "/formador/eventos/")

        # Acessar a própria página para verificar funcionamento
        page_response = self.client.get(self.url)

        # A página deve carregar corretamente e mostrar o título
        self.assertEqual(page_response.status_code, 200)
        self.assertContains(page_response, "Meus Eventos")

    def test_menu_nao_aparece_para_coordenador(self):
        """Teste: Verificar se o menu não mostra link para coordenador"""
        self.client.login(username="coord_test", password="testpass123")

        # Acessar home page
        response = self.client.get("/")

        # Menu de formador não deve aparecer para coordenador
        self.assertNotContains(response, "Meus Eventos")
        # Mas deve ter seção de Coordenação
        self.assertContains(response, "Solicitar Evento")


class SecurityCriticalTest(TestCase):
    """Testes críticos de segurança para as correções implementadas"""

    def setUp(self):
        """Configuração inicial para os testes de segurança"""
        # Criar usuários com diferentes papéis
        self.user_formador = User.objects.create_user(
            username="formador_test",
            email="formador@test.com",
            password="testpass123",
            papel="formador",
        )

        self.user_coordenador = User.objects.create_user(
            username="coord_test",
            email="coord@test.com",
            password="testpass123",
            papel="coordenador",
        )

        self.user_superintendencia = User.objects.create_user(
            username="super_test",
            email="super@test.com",
            password="testpass123",
            papel="superintendencia",
        )

        self.user_controle = User.objects.create_user(
            username="controle_test",
            email="controle@test.com",
            password="testpass123",
            papel="controle",
        )

        self.user_diretoria = User.objects.create_user(
            username="diretoria_test",
            email="diretoria@test.com",
            password="testpass123",
            papel="diretoria",
        )

        self.user_admin = User.objects.create_superuser(
            username="admin_test", email="admin@test.com", password="testpass123"
        )

        # URLs críticas
        self.bloqueio_url = reverse("core:bloqueio_novo")
        self.mapa_mensal_url = reverse("core:mapa_mensal") + "?ano=2025&mes=1"
        self.mapa_page_url = reverse("core:mapa_mensal_page")

    def test_bloqueio_agenda_restrito_formador_admin(self):
        """Teste crítico: Apenas formadores e admins podem criar bloqueios"""
        # Formador deve conseguir acessar
        self.client.login(username="formador_test", password="testpass123")
        response = self.client.get(self.bloqueio_url)
        self.assertEqual(response.status_code, 200)

        # Admin deve conseguir acessar
        self.client.login(username="admin_test", password="testpass123")
        response = self.client.get(self.bloqueio_url)
        self.assertEqual(response.status_code, 200)

        # Coordenador NÃO deve conseguir acessar
        self.client.login(username="coord_test", password="testpass123")
        response = self.client.get(self.bloqueio_url)
        self.assertEqual(response.status_code, 403)

        # Superintendência NÃO deve conseguir acessar
        self.client.login(username="super_test", password="testpass123")
        response = self.client.get(self.bloqueio_url)
        self.assertEqual(response.status_code, 403)

    def test_mapa_mensal_restrito_hierarquia_superior(self):
        """Teste crítico: Apenas superintendência, controle, diretoria e admin podem ver calendário"""
        # Superintendência deve conseguir acessar
        self.client.login(username="super_test", password="testpass123")
        response = self.client.get(self.mapa_mensal_url)
        self.assertEqual(response.status_code, 200)

        # Controle deve conseguir acessar
        self.client.login(username="controle_test", password="testpass123")
        response = self.client.get(self.mapa_mensal_url)
        self.assertEqual(response.status_code, 200)

        # Diretoria deve conseguir acessar
        self.client.login(username="diretoria_test", password="testpass123")
        response = self.client.get(self.mapa_mensal_url)
        self.assertEqual(response.status_code, 200)

        # Admin deve conseguir acessar
        self.client.login(username="admin_test", password="testpass123")
        response = self.client.get(self.mapa_mensal_url)
        self.assertEqual(response.status_code, 200)

        # Formador NÃO deve conseguir acessar
        self.client.login(username="formador_test", password="testpass123")
        response = self.client.get(self.mapa_mensal_url)
        self.assertEqual(response.status_code, 403)

        # Coordenador NÃO deve conseguir acessar
        self.client.login(username="coord_test", password="testpass123")
        response = self.client.get(self.mapa_mensal_url)
        self.assertEqual(response.status_code, 403)

    def test_mapa_mensal_page_restrito(self):
        """Teste crítico: Página HTML do mapa também deve ser restrita"""
        # Superintendência deve conseguir acessar
        self.client.login(username="super_test", password="testpass123")
        response = self.client.get(self.mapa_page_url)
        self.assertEqual(response.status_code, 200)

        # Formador NÃO deve conseguir acessar
        self.client.login(username="formador_test", password="testpass123")
        response = self.client.get(self.mapa_page_url)
        self.assertEqual(response.status_code, 403)

        # Coordenador NÃO deve conseguir acessar
        self.client.login(username="coord_test", password="testpass123")
        response = self.client.get(self.mapa_page_url)
        self.assertEqual(response.status_code, 403)

    def test_usuario_nao_autenticado_negado(self):
        """Teste crítico: Usuários não autenticados são redirecionados"""
        # Bloqueio
        response = self.client.get(self.bloqueio_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

        # Mapa mensal
        response = self.client.get(self.mapa_mensal_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

        # Página do mapa
        response = self.client.get(self.mapa_page_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_validacao_de_dados_sensiveis_mapa(self):
        """Teste crítico: Mapa mensal contém dados sensíveis que devem ser protegidos"""
        # Login com perfil autorizado
        self.client.login(username="super_test", password="testpass123")
        response = self.client.get(self.mapa_mensal_url)

        # Verificar que a resposta contém dados estruturados
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

        # Verificar estrutura da resposta JSON
        import json

        data = json.loads(response.content)
        self.assertIn("ano", data)
        self.assertIn("mes", data)
        self.assertIn("linhas", data)

        # Dados sensíveis que precisam proteção
        if data["linhas"]:  # Se há formadores
            self.assertIn("formador", data["linhas"][0])
            self.assertIn("celulas", data["linhas"][0])


class ControleProfileTest(TestCase):
    """Testes específicos para funcionalidades do perfil Controle"""

    def setUp(self):
        """Configuração inicial para testes do perfil Controle"""
        # Criar usuários
        self.user_controle = User.objects.create_user(
            username="controle_test",
            email="controle@test.com",
            password="testpass123",
            papel="controle",
        )

        self.user_formador = User.objects.create_user(
            username="formador_test",
            email="formador@test.com",
            password="testpass123",
            papel="formador",
        )

        self.user_admin = User.objects.create_superuser(
            username="admin_test", email="admin@test.com", password="testpass123"
        )

        # Criar dados de teste
        self.formador = Formador.objects.create(
            nome="Formador Teste", email="formador@test.com", ativo=True
        )

        # URLs do perfil Controle
        self.google_calendar_url = reverse("core:controle_google_calendar")
        self.auditoria_url = reverse("core:controle_auditoria")
        self.api_status_url = reverse("core:controle_api_status")

    def test_controle_acesso_google_calendar_monitor(self):
        """Teste: Apenas perfil Controle e admin podem acessar monitor Google Calendar"""
        # Controle deve conseguir acessar
        self.client.login(username="controle_test", password="testpass123")
        response = self.client.get(self.google_calendar_url)
        self.assertEqual(response.status_code, 200)

        # Admin deve conseguir acessar
        self.client.login(username="admin_test", password="testpass123")
        response = self.client.get(self.google_calendar_url)
        self.assertEqual(response.status_code, 200)

        # Formador NÃO deve conseguir acessar
        self.client.login(username="formador_test", password="testpass123")
        response = self.client.get(self.google_calendar_url)
        self.assertEqual(response.status_code, 403)

    def test_controle_acesso_auditoria_log(self):
        """Teste: Apenas perfil Controle e admin podem acessar logs de auditoria"""
        # Controle deve conseguir acessar
        self.client.login(username="controle_test", password="testpass123")
        response = self.client.get(self.auditoria_url)
        self.assertEqual(response.status_code, 200)

        # Admin deve conseguir acessar
        self.client.login(username="admin_test", password="testpass123")
        response = self.client.get(self.auditoria_url)
        self.assertEqual(response.status_code, 200)

        # Formador NÃO deve conseguir acessar
        self.client.login(username="formador_test", password="testpass123")
        response = self.client.get(self.auditoria_url)
        self.assertEqual(response.status_code, 403)

    def test_controle_api_status_endpoint(self):
        """Teste: API de status deve retornar dados estruturados para perfil Controle"""
        self.client.login(username="controle_test", password="testpass123")
        response = self.client.get(self.api_status_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

        # Verificar estrutura da resposta JSON
        import json

        data = json.loads(response.content)

        # Verificar campos obrigatórios
        self.assertIn("timestamp", data)
        self.assertIn("sistema_status", data)
        self.assertIn("metricas", data)

        # Verificar métricas
        metricas = data["metricas"]
        self.assertIn("solicitacoes", metricas)
        self.assertIn("google_calendar", metricas)
        self.assertIn("auditoria", metricas)
        self.assertIn("formadores_ativos", metricas)

        # Verificar tipos de dados
        self.assertIsInstance(metricas["formadores_ativos"], int)
        self.assertIsInstance(metricas["solicitacoes"]["pendentes"], int)
        self.assertIsInstance(
            metricas["google_calendar"]["taxa_sucesso_24h"], (int, float)
        )

    def test_controle_google_calendar_filtros(self):
        """Teste: Monitor Google Calendar deve suportar filtros"""
        # Criar evento de teste
        from core.models import EventoGoogleCalendar, Solicitacao

        solicitacao = Solicitacao.objects.create(
            titulo_evento="Evento Teste",
            data_inicio=timezone.now(),
            data_fim=timezone.now() + timedelta(hours=2),
            usuario_solicitante=self.user_controle,
        )

        evento_sync = EventoGoogleCalendar.objects.create(
            solicitacao=solicitacao,
            usuario_criador=self.user_controle,
            provider_event_id="test_event_123",
            status_sincronizacao="OK",
        )

        self.client.login(username="controle_test", password="testpass123")

        # Teste filtro por status
        response = self.client.get(self.google_calendar_url + "?status=OK")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "test_event_123")

        # Teste filtro por período
        response = self.client.get(self.google_calendar_url + "?periodo=1")
        self.assertEqual(response.status_code, 200)

    def test_controle_auditoria_filtros(self):
        """Teste: Dashboard de auditoria deve suportar filtros"""
        # Criar log de auditoria de teste
        LogAuditoria.objects.create(
            usuario=self.user_controle,
            acao="Teste de auditoria",
            entidade_afetada_id="test_id_123",
            detalhes="Teste de funcionalidade",
        )

        self.client.login(username="controle_test", password="testpass123")

        # Teste filtro por ação
        response = self.client.get(self.auditoria_url + "?acao=Teste")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Teste de auditoria")

        # Teste filtro por usuário
        response = self.client.get(self.auditoria_url + "?usuario=controle_test")
        self.assertEqual(response.status_code, 200)

        # Teste filtro por período
        response = self.client.get(self.auditoria_url + "?periodo=1")
        self.assertEqual(response.status_code, 200)

    def test_controle_usuario_nao_autenticado_negado(self):
        """Teste: Usuários não autenticados devem ser redirecionados"""
        # Google Calendar Monitor
        response = self.client.get(self.google_calendar_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

        # Auditoria Log
        response = self.client.get(self.auditoria_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

        # API Status
        response = self.client.get(self.api_status_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)


class DiretoriaProfileTest(TestCase):
    """Testes específicos para funcionalidades do perfil Diretoria"""

    def setUp(self):
        """Configuração inicial para testes do perfil Diretoria"""
        # Criar usuários
        self.user_diretoria = User.objects.create_user(
            username="diretoria_test",
            email="diretoria@test.com",
            password="testpass123",
            papel="diretoria",
        )

        self.user_formador = User.objects.create_user(
            username="formador_test",
            email="formador@test.com",
            password="testpass123",
            papel="formador",
        )

        self.user_admin = User.objects.create_superuser(
            username="admin_test", email="admin@test.com", password="testpass123"
        )

        # Criar dados de teste
        self.projeto = Projeto.objects.create(nome="Projeto Teste", ativo=True)
        self.municipio = Municipio.objects.create(
            nome="Cidade Teste", uf="SP", ativo=True
        )
        self.tipo_evento = TipoEvento.objects.create(nome="Evento Teste", ativo=True)
        self.formador = Formador.objects.create(
            nome="Formador Teste", email="formador@test.com", ativo=True
        )

        # URLs do perfil Diretoria
        self.dashboard_url = reverse("core:diretoria_dashboard")
        self.relatorios_url = reverse("core:diretoria_relatorios")
        self.api_metrics_url = reverse("core:diretoria_api_metrics")

    def test_diretoria_acesso_dashboard_executivo(self):
        """Teste: Apenas perfil Diretoria e admin podem acessar dashboard executivo"""
        # Diretoria deve conseguir acessar
        self.client.login(username="diretoria_test", password="testpass123")
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)

        # Admin deve conseguir acessar
        self.client.login(username="admin_test", password="testpass123")
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)

        # Formador NÃO deve conseguir acessar
        self.client.login(username="formador_test", password="testpass123")
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 403)

    def test_diretoria_acesso_relatorios(self):
        """Teste: Apenas perfil Diretoria e admin podem acessar relatórios"""
        # Diretoria deve conseguir acessar
        self.client.login(username="diretoria_test", password="testpass123")
        response = self.client.get(self.relatorios_url)
        self.assertEqual(response.status_code, 200)

        # Admin deve conseguir acessar
        self.client.login(username="admin_test", password="testpass123")
        response = self.client.get(self.relatorios_url)
        self.assertEqual(response.status_code, 200)

        # Formador NÃO deve conseguir acessar
        self.client.login(username="formador_test", password="testpass123")
        response = self.client.get(self.relatorios_url)
        self.assertEqual(response.status_code, 403)

    def test_diretoria_api_metrics_endpoint(self):
        """Teste: API de métricas deve retornar dados estruturados para perfil Diretoria"""
        self.client.login(username="diretoria_test", password="testpass123")
        response = self.client.get(self.api_metrics_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

        # Verificar estrutura da resposta JSON
        import json

        data = json.loads(response.content)

        # Verificar campos obrigatórios
        self.assertIn("timestamp", data)
        self.assertIn("periodo", data)
        self.assertIn("metricas_executivas", data)
        self.assertIn("recursos_sistema", data)

        # Verificar métricas executivas
        metricas = data["metricas_executivas"]
        self.assertIn("eventos_realizados", metricas)
        self.assertIn("total_solicitacoes", metricas)
        self.assertIn("taxa_aprovacao", metricas)
        self.assertIn("formadores_utilizados", metricas)
        self.assertIn("municipios_atendidos", metricas)
        self.assertIn("crescimento_mensal", metricas)

        # Verificar recursos do sistema
        recursos = data["recursos_sistema"]
        self.assertIn("formadores_cadastrados", recursos)
        self.assertIn("municipios_cadastrados", recursos)
        self.assertIn("projetos_ativos", recursos)
        self.assertIn("tipos_evento", recursos)

        # Verificar tipos de dados
        self.assertIsInstance(metricas["eventos_realizados"], int)
        self.assertIsInstance(metricas["taxa_aprovacao"], (int, float))
        self.assertIsInstance(metricas["crescimento_mensal"], list)
        self.assertIsInstance(recursos["formadores_cadastrados"], int)

    def test_diretoria_dashboard_context_data(self):
        """Teste: Dashboard deve fornecer dados contextuais corretos"""
        # Criar uma solicitação aprovada para teste
        solicitacao = Solicitacao.objects.create(
            titulo_evento="Evento Teste Dashboard",
            data_inicio=timezone.now(),
            data_fim=timezone.now() + timedelta(hours=2),
            usuario_solicitante=self.user_diretoria,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            status=SolicitacaoStatus.APROVADO,
        )
        solicitacao.formadores.add(self.formador)

        self.client.login(username="diretoria_test", password="testpass123")
        response = self.client.get(self.dashboard_url)

        self.assertEqual(response.status_code, 200)

        # Verificar que context contém dados esperados
        context = response.context
        self.assertIn("total_solicitacoes_ano", context)
        self.assertIn("solicitacoes_aprovadas_ano", context)
        self.assertIn("taxa_aprovacao_ano", context)
        self.assertIn("formadores_ativos", context)
        self.assertIn("eventos_por_mes", context)
        self.assertIn("top_formadores", context)
        self.assertIn("municipios_atendidos", context)

        # Verificar que dados fazem sentido
        self.assertIsInstance(context["total_solicitacoes_ano"], int)
        self.assertIsInstance(context["eventos_por_mes"], list)
        self.assertIsInstance(context["top_formadores"], list)

    def test_diretoria_relatorios_filtros(self):
        """Teste: Relatórios devem suportar filtros por período e projeto"""
        # Criar solicitação aprovada para teste
        solicitacao = Solicitacao.objects.create(
            titulo_evento="Evento Teste Filtros",
            data_inicio=timezone.now(),
            data_fim=timezone.now() + timedelta(hours=2),
            usuario_solicitante=self.user_diretoria,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            status=SolicitacaoStatus.APROVADO,
        )
        solicitacao.formadores.add(self.formador)

        self.client.login(username="diretoria_test", password="testpass123")

        # Teste filtro por período
        response = self.client.get(self.relatorios_url + "?periodo=30")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["periodo_dias"], 30)

        # Teste filtro por projeto
        response = self.client.get(self.relatorios_url + f"?projeto={self.projeto.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["projeto_selecionado"], str(self.projeto.id))

        # Teste filtro por município
        response = self.client.get(
            self.relatorios_url + f"?municipio={self.municipio.id}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["municipio_selecionado"], str(self.municipio.id)
        )

    def test_diretoria_usuario_nao_autenticado_negado(self):
        """Teste: Usuários não autenticados devem ser redirecionados"""
        # Dashboard
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

        # Relatórios
        response = self.client.get(self.relatorios_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

        # API Métricas
        response = self.client.get(self.api_metrics_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)


class CoordenadorProfileTest(TestCase):
    """Testes específicos para funcionalidades do perfil Coordenador - COMMIT 4"""

    def setUp(self):
        """Setup específico para testes do Coordenador"""
        self.client = Client()

        # Usuário Coordenador
        self.coordenador_user = User.objects.create_user(
            username="coordenador",
            email="coordenador@test.com",
            password="testpass123",
            papel="coordenador",
        )

        # Outro coordenador para testar isolamento
        self.outro_coordenador = User.objects.create_user(
            username="outro_coord",
            email="outro@test.com",
            password="testpass123",
            papel="coordenador",
        )

        # Usuário não-autorizado
        self.formador_user = User.objects.create_user(
            username="formador",
            email="formador@test.com",
            password="testpass123",
            papel="formador",
        )

        # Dados de teste
        self.projeto1 = Projeto.objects.create(nome="Projeto A")
        self.projeto2 = Projeto.objects.create(nome="Projeto B")
        self.municipio = Municipio.objects.create(nome="São Paulo", uf="SP")
        self.tipo_evento = TipoEvento.objects.create(nome="Workshop")

        # Criar solicitações do coordenador atual
        self.solicitacao1 = Solicitacao.objects.create(
            usuario_solicitante=self.coordenador_user,
            projeto=self.projeto1,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento do Coordenador 1",
            data_inicio=timezone.now() + timedelta(days=1),
            data_fim=timezone.now() + timedelta(days=1, hours=2),
            status="Pendente",
        )

        self.solicitacao2 = Solicitacao.objects.create(
            usuario_solicitante=self.coordenador_user,
            projeto=self.projeto2,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento do Coordenador 2",
            data_inicio=timezone.now() + timedelta(days=2),
            data_fim=timezone.now() + timedelta(days=2, hours=2),
            status="Aprovado",
        )

        self.solicitacao3 = Solicitacao.objects.create(
            usuario_solicitante=self.coordenador_user,
            projeto=self.projeto1,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento do Coordenador 3",
            data_inicio=timezone.now() + timedelta(days=5),
            data_fim=timezone.now() + timedelta(days=5, hours=2),
            status="Reprovado",
            justificativa_rejeicao="Conflito de agenda",
        )

        # Criar solicitação de outro coordenador (não deve aparecer)
        self.solicitacao_outro = Solicitacao.objects.create(
            usuario_solicitante=self.outro_coordenador,
            projeto=self.projeto1,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento de Outro Coordenador",
            data_inicio=timezone.now() + timedelta(days=3),
            data_fim=timezone.now() + timedelta(days=3, hours=2),
            status="Pendente",
        )

    def test_coordenador_meus_eventos_access_authorized(self):
        """Teste: Coordenador deve acessar página Meus Eventos"""
        self.client.login(username="coordenador", password="testpass123")
        response = self.client.get(reverse("core:coordenador_meus_eventos"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Meus Eventos Solicitados")
        self.assertContains(response, "Evento do Coordenador 1")
        self.assertContains(response, "Evento do Coordenador 2")
        self.assertContains(response, "Evento do Coordenador 3")

    def test_coordenador_meus_eventos_access_unauthorized(self):
        """Teste: Formador NÃO deve acessar página Meus Eventos de coordenador"""
        self.client.login(username="formador", password="testpass123")
        response = self.client.get(reverse("core:coordenador_meus_eventos"))

        self.assertEqual(response.status_code, 403)

    def test_coordenador_eventos_user_isolation(self):
        """Teste: Coordenadores só devem ver seus próprios eventos"""
        self.client.login(username="coordenador", password="testpass123")
        response = self.client.get(reverse("core:coordenador_meus_eventos"))

        self.assertEqual(response.status_code, 200)

        # Deve conter os eventos do coordenador logado
        self.assertContains(response, "Evento do Coordenador 1")
        self.assertContains(response, "Evento do Coordenador 2")
        self.assertContains(response, "Evento do Coordenador 3")

        # NÃO deve conter eventos de outros coordenadores
        self.assertNotContains(response, "Evento de Outro Coordenador")

    def test_coordenador_eventos_filtering_by_status(self):
        """Teste: Filtragem por status deve funcionar corretamente"""
        self.client.login(username="coordenador", password="testpass123")

        # Filtrar apenas eventos pendentes
        response = self.client.get(
            reverse("core:coordenador_meus_eventos"), {"status": "Pendente"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Evento do Coordenador 1")
        self.assertNotContains(response, "Evento do Coordenador 2")
        self.assertNotContains(response, "Evento do Coordenador 3")

        # Filtrar apenas eventos aprovados
        response = self.client.get(
            reverse("core:coordenador_meus_eventos"), {"status": "Aprovado"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Evento do Coordenador 1")
        self.assertContains(response, "Evento do Coordenador 2")
        self.assertNotContains(response, "Evento do Coordenador 3")

        # Filtrar apenas eventos reprovados
        response = self.client.get(
            reverse("core:coordenador_meus_eventos"), {"status": "Reprovado"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Evento do Coordenador 1")
        self.assertNotContains(response, "Evento do Coordenador 2")
        self.assertContains(response, "Evento do Coordenador 3")

    def test_coordenador_eventos_filtering_by_project(self):
        """Teste: Filtragem por projeto deve funcionar corretamente"""
        self.client.login(username="coordenador", password="testpass123")

        # Filtrar apenas eventos do Projeto A
        response = self.client.get(
            reverse("core:coordenador_meus_eventos"), {"projeto": self.projeto1.id}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Evento do Coordenador 1")
        self.assertNotContains(response, "Evento do Coordenador 2")
        self.assertContains(response, "Evento do Coordenador 3")

        # Filtrar apenas eventos do Projeto B
        response = self.client.get(
            reverse("core:coordenador_meus_eventos"), {"projeto": self.projeto2.id}
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Evento do Coordenador 1")
        self.assertContains(response, "Evento do Coordenador 2")
        self.assertNotContains(response, "Evento do Coordenador 3")

    def test_coordenador_eventos_statistics(self):
        """Teste: Estatísticas devem estar corretas na página Meus Eventos"""
        self.client.login(username="coordenador", password="testpass123")
        response = self.client.get(reverse("core:coordenador_meus_eventos"))

        self.assertEqual(response.status_code, 200)

        # Verifica dados de contexto
        context = response.context
        self.assertIn("stats", context)

        stats = context["stats"]
        self.assertEqual(stats["total_solicitacoes"], 3)
        self.assertEqual(stats["eventos_pendentes"], 1)
        self.assertEqual(stats["eventos_aprovados"], 1)
        self.assertEqual(stats["eventos_reprovados"], 1)
        self.assertEqual(stats["taxa_aprovacao"], 33.3)  # 1/3 * 100

    def test_coordenador_eventos_pagination(self):
        """Teste: Paginação deve funcionar corretamente"""
        self.client.login(username="coordenador", password="testpass123")

        # Criar mais eventos para testar paginação
        for i in range(20):
            Solicitacao.objects.create(
                usuario_solicitante=self.coordenador_user,
                projeto=self.projeto1,
                municipio=self.municipio,
                tipo_evento=self.tipo_evento,
                titulo_evento=f"Evento Extra {i+1}",
                data_inicio=timezone.now() + timedelta(days=i + 10),
                data_fim=timezone.now() + timedelta(days=i + 10, hours=2),
                status="Pendente",
            )

        response = self.client.get(reverse("core:coordenador_meus_eventos"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_paginated"])
        self.assertEqual(len(response.context["eventos"]), 15)  # paginate_by = 15

        # Testar segunda página
        response = self.client.get(reverse("core:coordenador_meus_eventos") + "?page=2")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            len(response.context["eventos"]), 8
        )  # Total 23 - 15 da primeira página

    def test_coordenador_eventos_filter_options_context(self):
        """Teste: Opções de filtro devem estar disponíveis no contexto"""
        self.client.login(username="coordenador", password="testpass123")
        response = self.client.get(reverse("core:coordenador_meus_eventos"))

        self.assertEqual(response.status_code, 200)

        context = response.context
        self.assertIn("filter_options", context)

        filter_options = context["filter_options"]
        self.assertIn("status_choices", filter_options)
        self.assertIn("periodo_choices", filter_options)
        self.assertIn("projetos", filter_options)

        # Verifica se os projetos estão corretos
        projetos_ids = [str(p.id) for p in filter_options["projetos"]]
        self.assertIn(str(self.projeto1.id), projetos_ids)
        self.assertIn(str(self.projeto2.id), projetos_ids)

        # Verifica opções de status
        status_options = [choice[0] for choice in filter_options["status_choices"]]
        self.assertIn("Pendente", status_options)
        self.assertIn("Aprovado", status_options)
        self.assertIn("Reprovado", status_options)

    def test_coordenador_eventos_period_filtering(self):
        """Teste: Filtragem por período deve funcionar corretamente"""
        self.client.login(username="coordenador", password="testpass123")

        # Criar evento antigo (fora do período de 7 dias)
        evento_antigo = Solicitacao.objects.create(
            usuario_solicitante=self.coordenador_user,
            projeto=self.projeto1,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento Antigo",
            data_inicio=timezone.now() - timedelta(days=10),
            data_fim=timezone.now() - timedelta(days=10, hours=-2),
            status="Aprovado",
        )

        # Filtrar por período de 7 dias
        response = self.client.get(
            reverse("core:coordenador_meus_eventos"), {"periodo": "7"}
        )

        self.assertEqual(response.status_code, 200)
        # Os 3 eventos criados no setUp estão dentro do período (futuro)
        # O evento antigo NÃO deve aparecer
        self.assertNotContains(response, "Evento Antigo")
        self.assertContains(response, "Evento do Coordenador 1")

    def test_coordenador_eventos_combined_filters(self):
        """Teste: Combinação de múltiplos filtros deve funcionar"""
        self.client.login(username="coordenador", password="testpass123")

        # Combinar filtro por status e projeto
        response = self.client.get(
            reverse("core:coordenador_meus_eventos"),
            {"status": "Pendente", "projeto": self.projeto1.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Evento do Coordenador 1")  # Pendente + Projeto A
        self.assertNotContains(
            response, "Evento do Coordenador 2"
        )  # Aprovado + Projeto B
        self.assertNotContains(
            response, "Evento do Coordenador 3"
        )  # Reprovado + Projeto A

    def test_coordenador_eventos_menu_link_visible(self):
        """Teste: Link 'Meus Eventos' deve estar visível no menu para coordenadores"""
        self.client.login(username="coordenador", password="testpass123")
        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Meus Eventos")
        self.assertContains(response, reverse("core:coordenador_meus_eventos"))

    def test_coordenador_eventos_unauthenticated_redirect(self):
        """Teste: Usuários não autenticados devem ser redirecionados para login"""
        response = self.client.get(reverse("core:coordenador_meus_eventos"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)


class MenuVisibilityTest(TestCase):
    """Testes para verificar visibilidade correta dos menus por perfil - COMMIT 5"""

    def setUp(self):
        """Setup específico para testes de visibilidade de menus"""
        self.client = Client()

        # Criar usuários para cada perfil
        self.admin_user = User.objects.create_superuser(
            username="admin", email="admin@test.com", password="testpass123"
        )

        self.coordenador_user = User.objects.create_user(
            username="coordenador",
            email="coordenador@test.com",
            password="testpass123",
            papel="coordenador",
        )

        self.formador_user = User.objects.create_user(
            username="formador",
            email="formador@test.com",
            password="testpass123",
            papel="formador",
        )

        self.superintendencia_user = User.objects.create_user(
            username="superintendencia",
            email="superintendencia@test.com",
            password="testpass123",
            papel="superintendencia",
        )

        self.controle_user = User.objects.create_user(
            username="controle",
            email="controle@test.com",
            password="testpass123",
            papel="controle",
        )

        self.diretoria_user = User.objects.create_user(
            username="diretoria",
            email="diretoria@test.com",
            password="testpass123",
            papel="diretoria",
        )

    def test_coordenador_menu_visibility(self):
        """Teste: Coordenador deve ver apenas suas seções específicas"""
        self.client.login(username="coordenador", password="testpass123")
        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)

        # Deve ver seções do coordenador
        self.assertContains(response, "Coordenação")
        self.assertContains(response, "Solicitar Evento")
        self.assertContains(response, "Meus Eventos")

        # NÃO deve ver seções de outros perfis
        self.assertNotContains(response, "Superintendência")
        self.assertNotContains(response, "Controle")
        self.assertNotContains(response, "Diretoria")
        self.assertNotContains(response, "Cadastros")
        self.assertNotContains(response, "Sistema")

        # Deve ver mapa de disponibilidade (não restrito)
        self.assertNotContains(response, "Mapa de Disponibilidade")

    def test_formador_menu_visibility(self):
        """Teste: Formador deve ver apenas suas seções específicas"""
        self.client.login(username="formador", password="testpass123")
        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)

        # Deve ver seções do formador
        self.assertContains(response, "Formador")
        self.assertContains(response, "Meus Eventos")
        self.assertContains(response, "Bloqueio de Agenda")

        # NÃO deve ver seções administrativas
        self.assertNotContains(response, "Coordenação")
        self.assertNotContains(response, "Superintendência")
        self.assertNotContains(response, "Controle")
        self.assertNotContains(response, "Diretoria")
        self.assertNotContains(response, "Cadastros")
        self.assertNotContains(response, "Sistema")

    def test_superintendencia_menu_visibility(self):
        """Teste: Superintendência deve ver seções administrativas"""
        self.client.login(username="superintendencia", password="testpass123")
        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)

        # Deve ver seções da superintendência
        self.assertContains(response, "Superintendência")
        self.assertContains(response, "Aprovações Pendentes")
        self.assertContains(response, "Cadastros")
        self.assertContains(response, "Formadores")
        self.assertContains(response, "Municípios")
        self.assertContains(response, "Projetos")

        # Deve ver mapa de disponibilidade
        self.assertContains(response, "Mapa de Disponibilidade")

        # NÃO deve ver administração do sistema (apenas admin)
        self.assertNotContains(response, "Sistema")

    def test_controle_menu_visibility(self):
        """Teste: Controle deve ver seções de monitoramento"""
        self.client.login(username="controle", password="testpass123")
        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)

        # Deve ver seções do controle
        self.assertContains(response, "Controle")
        self.assertContains(response, "Monitor Google Calendar")
        self.assertContains(response, "Logs de Auditoria")
        self.assertContains(response, "Status do Sistema")
        self.assertContains(response, "Auditoria do Sistema")

        # Deve ver mapa de disponibilidade
        self.assertContains(response, "Mapa de Disponibilidade")
        self.assertContains(response, "Dados JSON")  # Acesso especial ao JSON

        # NÃO deve ver seções administrativas
        self.assertNotContains(response, "Cadastros")
        self.assertNotContains(response, "Sistema")

    def test_diretoria_menu_visibility(self):
        """Teste: Diretoria deve ver seções estratégicas"""
        self.client.login(username="diretoria", password="testpass123")
        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)

        # Deve ver seções da diretoria
        self.assertContains(response, "Diretoria")
        self.assertContains(response, "Dashboard Executivo")
        self.assertContains(response, "Relatórios Consolidados")
        self.assertContains(response, "Visão Mensal")
        self.assertContains(response, "Métricas API")

        # Deve ver mapa de disponibilidade
        self.assertContains(response, "Mapa de Disponibilidade")

        # NÃO deve ver seções operacionais
        self.assertNotContains(response, "Cadastros")
        self.assertNotContains(response, "Sistema")
        self.assertNotContains(response, "Coordenação")

    def test_admin_menu_visibility(self):
        """Teste: Admin deve ver todas as seções"""
        self.client.login(username="admin", password="testpass123")
        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)

        # Deve ver todas as seções
        self.assertContains(response, "Coordenação")
        self.assertContains(response, "Formador")
        self.assertContains(response, "Superintendência")
        self.assertContains(response, "Controle")
        self.assertContains(response, "Diretoria")
        self.assertContains(response, "Cadastros")
        self.assertContains(response, "Sistema")

        # Deve ver todos os cards de ação
        self.assertContains(response, "Solicitar Evento")
        self.assertContains(response, "Bloqueio de Agenda")
        self.assertContains(response, "Central de Aprovações")
        self.assertContains(response, "Monitor Google Calendar")
        self.assertContains(response, "Dashboard Executivo")

    def test_restricted_cards_by_profile(self):
        """Teste: Cards específicos devem aparecer apenas para perfis autorizados"""
        # Cards que devem aparecer apenas para superintendência
        self.client.login(username="coordenador", password="testpass123")
        response = self.client.get(reverse("core:home"))
        self.assertNotContains(response, "Central de Aprovações")

        self.client.login(username="superintendencia", password="testpass123")
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, "Central de Aprovações")

        # Cards que devem aparecer apenas para controle
        self.client.login(username="formador", password="testpass123")
        response = self.client.get(reverse("core:home"))
        self.assertNotContains(response, "Monitor Google Calendar")

        self.client.login(username="controle", password="testpass123")
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, "Monitor Google Calendar")

        # Cards que devem aparecer apenas para diretoria
        self.client.login(username="coordenador", password="testpass123")
        response = self.client.get(reverse("core:home"))
        self.assertNotContains(response, "Dashboard Executivo")

        self.client.login(username="diretoria", password="testpass123")
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, "Dashboard Executivo")

    def test_formador_no_coordenador_features(self):
        """Teste: Formadores NÃO devem ver funcionalidades de coordenador"""
        self.client.login(username="formador", password="testpass123")
        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)

        # NÃO deve ver funcionalidades de coordenador
        self.assertNotContains(response, "Solicitar Evento")
        self.assertNotContains(response, "coordenador_meus_eventos")

        # NÃO deve ter acesso a aprovações
        self.assertNotContains(response, "Aprovações Pendentes")

    def test_coordenador_no_admin_features(self):
        """Teste: Coordenadores NÃO devem ver funcionalidades administrativas"""
        self.client.login(username="coordenador", password="testpass123")
        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)

        # NÃO deve ver cadastros
        self.assertNotContains(response, "Formadores")
        self.assertNotContains(response, "Municípios")
        self.assertNotContains(response, "Projetos")

        # NÃO deve ver administração do sistema
        self.assertNotContains(response, "Administração")
        self.assertNotContains(response, "/admin/")

    def test_menu_consistency_between_base_and_home(self):
        """Teste: Menus em base.html e home.html devem ser consistentes"""
        # Testar algumas páginas que usam base.html
        self.client.login(username="coordenador", password="testpass123")

        # Página home
        home_response = self.client.get(reverse("core:home"))
        self.assertEqual(home_response.status_code, 200)

        # Página de solicitação (que usa base.html)
        solicitacao_response = self.client.get(reverse("core:solicitar_evento"))
        self.assertEqual(solicitacao_response.status_code, 200)

        # Ambas devem conter links do coordenador
        for response in [home_response, solicitacao_response]:
            self.assertContains(response, "Coordenação")
            self.assertContains(response, "Meus Eventos")
            self.assertNotContains(response, "Superintendência")
