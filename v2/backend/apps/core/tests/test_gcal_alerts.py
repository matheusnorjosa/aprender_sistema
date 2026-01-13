"""
Testes para AlertsSummaryView (Issue #97).

Validam:
- RBAC (autenticação + Controle/Super)
- Contagens corretas por gcal_status
- Filtros timezone-aware com bordas inclusivas
- Window null quando sem parâmetros
"""
# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false

from __future__ import annotations
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.test import APIClient

from apps.core.models import Solicitacao, Municipio, Projeto, TipoEvento
from django.contrib.auth import get_user_model

User = get_user_model()


class TestGCalAlerts(TestCase):
    """
    Testes para GET /api/gcal/dashboard/alerts/summary/

    Casos de teste:
    1. test_alerts_requires_authentication
    2. test_alerts_requires_controle_or_super
    3. test_alerts_counts_within_window
    4. test_alerts_filters_respected_boundaries
    5. test_alerts_no_params_returns_counts_and_window_null
    """

    def setUp(self):
        """Setup comum para todos os testes."""
        self.client = APIClient()
        self.url = '/api/gcal/dashboard/alerts/summary/'

        # Timezone local
        self.tz_local = ZoneInfo('America/Fortaleza')

        # Criar grupos
        self.group_controle = Group.objects.get_or_create(name='Controle')[0]
        self.group_coordenador = Group.objects.get_or_create(name='Coordenador')[0]

        # Criar usuários (com CPFs únicos para evitar unique constraint violation)
        self.user_controle = User.objects.create_user(
            username='controle_user',
            email='controle@example.com',
            password='password123',
            cpf='11111111111'
        )
        self.user_controle.groups.add(self.group_controle)

        self.user_coordenador = User.objects.create_user(
            username='coordenador_user',
            email='coordenador@example.com',
            password='password123',
            cpf='22222222222'
        )
        self.user_coordenador.groups.add(self.group_coordenador)

        # Criar fixtures (municipio, projeto, tipo_evento)
        self.municipio = Municipio.objects.create(nome='Fortaleza')
        self.projeto = Projeto.objects.create(nome='Projeto Teste', fluxo='SUPER')
        self.tipo_evento = TipoEvento.objects.create(nome='Formação')

    def test_alerts_requires_authentication(self):
        """
        Teste 1: Endpoint deve retornar 403 para usuário anônimo.
        """
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_alerts_requires_controle_or_super(self):
        """
        Teste 2: Endpoint deve retornar 403 para perfil sem Controle/Super.
        """
        self.client.force_authenticate(user=self.user_coordenador)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_alerts_counts_within_window(self):
        """
        Teste 3: Contagens corretas por gcal_status dentro de janela TZ-aware.

        Cria 4 eventos aprovados no mesmo dia (2025-02-15):
        - 2 ERROR
        - 1 PENDING
        - 1 PUBLISHED

        Valida contagens com start=end=2025-02-15.
        """
        # Data fixa timezone-aware (2025-02-15 10:00 BRT)
        ref_date = datetime(2025, 2, 15, 10, 0, 0, tzinfo=self.tz_local)

        # Criar 4 eventos aprovados no mesmo dia
        sol_error_1 = Solicitacao.objects.create(
            status='aprovado',
            inicio=ref_date,
            fim=ref_date + timedelta(hours=2),
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            usuario=self.user_controle,
            coordenador=self.user_coordenador,
            gcal_status=Solicitacao.GCalStatus.ERROR
        )

        sol_error_2 = Solicitacao.objects.create(
            status='aprovado',
            inicio=ref_date.replace(hour=14),
            fim=ref_date.replace(hour=16),
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            usuario=self.user_controle,
            coordenador=self.user_coordenador,
            gcal_status=Solicitacao.GCalStatus.ERROR
        )

        sol_pending = Solicitacao.objects.create(
            status='aprovado',
            inicio=ref_date.replace(hour=18),
            fim=ref_date.replace(hour=20),
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            usuario=self.user_controle,
            coordenador=self.user_coordenador,
            gcal_status=Solicitacao.GCalStatus.PENDING
        )

        sol_published = Solicitacao.objects.create(
            status='aprovado',
            inicio=ref_date.replace(hour=22),
            fim=ref_date.replace(hour=23, minute=30),
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            usuario=self.user_controle,
            coordenador=self.user_coordenador,
            gcal_status=Solicitacao.GCalStatus.PUBLISHED
        )

        # Autenticar como Controle
        self.client.force_authenticate(user=self.user_controle)

        # Request com start=end=2025-02-15
        response = self.client.get(self.url, {
            'start': '2025-02-15',
            'end': '2025-02-15'
        })

        # Validar response
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data['errors'], 2)
        self.assertEqual(data['pending'], 1)
        self.assertEqual(data['published'], 1)
        self.assertEqual(data['none'], 0)
        self.assertEqual(data['window']['start'], '2025-02-15')
        self.assertEqual(data['window']['end'], '2025-02-15')

    def test_alerts_filters_respected_boundaries(self):
        """
        Teste 4: Bordas (00:00 e 23:59:59) são inclusivas.

        Cria eventos:
        - 2025-02-20 00:00 (incluir)
        - 2025-02-20 23:59:59 (incluir)
        - 2025-02-19 23:00 (excluir)
        - 2025-02-21 01:00 (excluir)

        Valida que start=end=2025-02-20 inclui apenas os 2 primeiros.
        """
        # Data de referência
        ref_date = datetime(2025, 2, 20, 0, 0, 0, tzinfo=self.tz_local)

        # Evento exatamente às 00:00 (início do dia)
        sol_midnight = Solicitacao.objects.create(
            status='aprovado',
            inicio=ref_date,
            fim=ref_date + timedelta(hours=1),
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            usuario=self.user_controle,
            coordenador=self.user_coordenador,
            gcal_status=Solicitacao.GCalStatus.ERROR
        )

        # Evento exatamente às 23:59:59 (fim do dia)
        sol_eod = Solicitacao.objects.create(
            status='aprovado',
            inicio=ref_date.replace(hour=23, minute=59, second=59),
            fim=ref_date.replace(hour=23, minute=59, second=59) + timedelta(hours=1),
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            usuario=self.user_controle,
            coordenador=self.user_coordenador,
            gcal_status=Solicitacao.GCalStatus.PENDING
        )

        # Evento um dia antes (excluir)
        sol_before = Solicitacao.objects.create(
            status='aprovado',
            inicio=ref_date - timedelta(days=1, hours=1),
            fim=ref_date - timedelta(days=1),
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            usuario=self.user_controle,
            coordenador=self.user_coordenador,
            gcal_status=Solicitacao.GCalStatus.ERROR
        )

        # Evento um dia depois (excluir)
        sol_after = Solicitacao.objects.create(
            status='aprovado',
            inicio=ref_date + timedelta(days=1, hours=1),
            fim=ref_date + timedelta(days=1, hours=2),
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            usuario=self.user_controle,
            coordenador=self.user_coordenador,
            gcal_status=Solicitacao.GCalStatus.PUBLISHED
        )

        # Autenticar como Controle
        self.client.force_authenticate(user=self.user_controle)

        # Request com start=end=2025-02-20
        response = self.client.get(self.url, {
            'start': '2025-02-20',
            'end': '2025-02-20'
        })

        # Validar response
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Deve incluir apenas sol_midnight (ERROR) e sol_eod (PENDING)
        self.assertEqual(data['errors'], 1)  # sol_midnight
        self.assertEqual(data['pending'], 1)  # sol_eod
        self.assertEqual(data['published'], 0)  # sol_after excluído
        self.assertEqual(data['none'], 0)

    def test_alerts_no_params_returns_counts_and_window_null(self):
        """
        Teste 5: Sem start/end, retorna window: {start:null, end:null} com contagens globais.

        Cria 3 eventos aprovados em datas diferentes e valida que sem filtros
        todos são contabilizados.
        """
        # Criar 3 eventos em datas diferentes
        now = datetime.now(self.tz_local)

        sol_1 = Solicitacao.objects.create(
            status='aprovado',
            inicio=now,
            fim=now + timedelta(hours=2),
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            usuario=self.user_controle,
            coordenador=self.user_coordenador,
            gcal_status=Solicitacao.GCalStatus.ERROR
        )

        sol_2 = Solicitacao.objects.create(
            status='aprovado',
            inicio=now + timedelta(days=5),
            fim=now + timedelta(days=5, hours=2),
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            usuario=self.user_controle,
            coordenador=self.user_coordenador,
            gcal_status=Solicitacao.GCalStatus.PUBLISHED
        )

        sol_3 = Solicitacao.objects.create(
            status='aprovado',
            inicio=now + timedelta(days=10),
            fim=now + timedelta(days=10, hours=2),
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            usuario=self.user_controle,
            coordenador=self.user_coordenador,
            gcal_status=Solicitacao.GCalStatus.NONE
        )

        # Autenticar como Controle
        self.client.force_authenticate(user=self.user_controle)

        # Request sem parâmetros
        response = self.client.get(self.url)

        # Validar response
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Validar contagens (todos os eventos criados)
        self.assertEqual(data['errors'], 1)
        self.assertEqual(data['published'], 1)
        self.assertEqual(data['none'], 1)
        self.assertEqual(data['pending'], 0)

        # Validar window null
        self.assertIsNone(data['window']['start'])
        self.assertIsNone(data['window']['end'])
