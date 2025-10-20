from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from core.models import Formador, Municipio, Projeto, TipoEvento

User = get_user_model()


class DashboardTemplateTestCase(TestCase):
    """Testes para verificar se o template do dashboard renderiza corretamente"""

    def setUp(self):
        """Configuração inicial para os testes do template"""
        self.user = User.objects.create_user(
            username="template_test_user",
            email="template@test.com",
            password="testpass123",
            papel="coordenador",
        )

        # Criar alguns dados básicos para evitar erros
        self.projeto = Projeto.objects.create(
            nome="Projeto Template Teste",
            descricao="Descrição do projeto para testes do template",
        )

        self.municipio = Municipio.objects.create(nome="São Paulo", uf="SP")

        self.tipo_evento = TipoEvento.objects.create(
            nome="Workshop Template", online=False
        )

        self.formador = Formador.objects.create(
            nome="João Template", email="joao.template@test.com", ativo=True
        )

        self.client = Client()

    def test_home_template_renders_successfully(self):
        """Teste se o template home.html renderiza sem erro"""
        self.client.login(username="template_test_user", password="testpass123")

        url = reverse("core:home")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dashboard")
        self.assertContains(response, "Eventos Este Mês")
        self.assertContains(response, "Formadores Ativos")
        self.assertContains(response, "Solicitações Pendentes")
        self.assertContains(response, "Municípios Atendidos")

    def test_home_template_contains_api_url(self):
        """Teste se o template contém a URL da API para JavaScript"""
        self.client.login(username="template_test_user", password="testpass123")

        url = reverse("core:home")
        response = self.client.get(url)

        # Verificar se contém a URL da API
        api_url = reverse("core:dashboard_stats_api")
        self.assertContains(response, api_url)

    def test_home_template_contains_javascript_functions(self):
        """Teste se o template contém as funções JavaScript necessárias"""
        self.client.login(username="template_test_user", password="testpass123")

        url = reverse("core:home")
        response = self.client.get(url)

        # Verificar se contém as funções JavaScript
        self.assertContains(response, "loadDashboardStats")
        self.assertContains(response, "animateCounter")
        self.assertContains(response, "fetch(")

    def test_home_template_has_csrf_token(self):
        """Teste se o template inclui CSRF token para requisições AJAX"""
        self.client.login(username="template_test_user", password="testpass123")

        url = reverse("core:home")
        response = self.client.get(url)

        # Verificar se contém CSRF token
        self.assertContains(response, "X-CSRFToken")
        self.assertContains(response, "csrf_token")

    def test_home_template_contains_css_animations(self):
        """Teste se o template contém as animações CSS necessárias"""
        self.client.login(username="template_test_user", password="testpass123")

        url = reverse("core:home")
        response = self.client.get(url)

        # Verificar se contém as animações CSS
        self.assertContains(response, "@keyframes pulse")
        self.assertContains(response, "loading-shimmer")
        self.assertContains(response, ".stat-card.loading")

    def test_home_template_has_stat_card_elements(self):
        """Teste se o template tem os elementos necessários para os contadores"""
        self.client.login(username="template_test_user", password="testpass123")

        url = reverse("core:home")
        response = self.client.get(url)

        # Verificar se contém os IDs dos contadores
        self.assertContains(response, 'id="eventos-count"')
        self.assertContains(response, 'id="formadores-count"')
        self.assertContains(response, 'id="pendentes-count"')
        self.assertContains(response, 'id="municipios-count"')

    def test_home_template_error_handling(self):
        """Teste se o template tem tratamento de erro adequado"""
        self.client.login(username="template_test_user", password="testpass123")

        url = reverse("core:home")
        response = self.client.get(url)

        # Verificar se contém tratamento de erro
        self.assertContains(response, "catch (error)")
        self.assertContains(response, "error-indicator")
        self.assertContains(response, "fallbackStats")
