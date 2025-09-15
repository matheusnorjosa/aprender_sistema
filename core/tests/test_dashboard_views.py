from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from core.models import Solicitacao, SolicitacaoStatus
from django.utils import timezone

class DashboardViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username='testuser', password='testpass', is_staff=True
        )
        self.user.user_permissions.add(*self.user.get_all_permissions())
        self.client.login(username='testuser', password='testpass')

    def test_executive_dashboard_view_status_code(self):
        url = reverse('diretoria_executive_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_dashboard_stats_api(self):
        url = reverse('dashboard_stats_api')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('total_solicitacoes', response.json())

    def test_dashboard_charts_api_monthly_evolution(self):
        url = reverse('dashboard_charts_api') + '?chart=monthly_evolution'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('data', response.json())
