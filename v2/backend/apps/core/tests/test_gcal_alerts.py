"""
Testes para AlertsSummaryView (Issue #97).

Validam:
- RBAC (autenticação + Controle/Super)
- Contagens corretas por gcal_status
- Filtros timezone-aware com bordas inclusivas
- Window null quando sem parâmetros
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.test import TestCase
from rest_framework.test import APIClient

from apps.core.models import Solicitacao
from apps.core.tests.factories import (
    GroupFactory,
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)


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
        self.url = "/api/gcal/dashboard/alerts/summary/"

        # Timezone local
        self.tz_local = ZoneInfo("America/Fortaleza")

        # Criar grupos
        self.group_controle = GroupFactory(name="Controle")
        self.group_coordenador = GroupFactory(name="Coordenador")

        # Criar usuários com IDs únicos (xdist-safe)
        uid = uuid.uuid4().hex[:8]
        self.user_controle = UsuarioFactory(
            username=f"controle_alerts_{uid}",
            email=f"controle_{uid}@example.com",
            password="password123",
            cpf=f"111{uid[:8].ljust(8, '0')}",
        )
        self.user_controle.groups.add(self.group_controle)

        self.user_coordenador = UsuarioFactory(
            username=f"coordenador_alerts_{uid}",
            email=f"coordenador_{uid}@example.com",
            password="password123",
            cpf=f"222{uid[:8].ljust(8, '0')}",
        )
        self.user_coordenador.groups.add(self.group_coordenador)

        # Criar fixtures com nomes únicos (xdist-safe)
        self.municipio = MunicipioFactory(nome=f"Fortaleza_{uid}")
        self.projeto = ProjetoFactory(nome=f"Projeto Teste_{uid}", fluxo="SUPER")
        self.tipo_evento = TipoEventoFactory(nome=f"Formação_{uid}")

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
        sol_error_1 = SolicitacaoFactory(
            status="aprovado",
            inicio=ref_date,
            fim=ref_date + timedelta(hours=2),
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            usuario=self.user_controle,
            coordenador=self.user_coordenador,
            gcal_status=Solicitacao.GCalStatus.ERROR,
        )

        sol_error_2 = SolicitacaoFactory(
            status="aprovado",
            inicio=ref_date.replace(hour=14),
            fim=ref_date.replace(hour=16),
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            usuario=self.user_controle,
            coordenador=self.user_coordenador,
            gcal_status=Solicitacao.GCalStatus.ERROR,
        )

        sol_pending = SolicitacaoFactory(
            status="aprovado",
            inicio=ref_date.replace(hour=18),
            fim=ref_date.replace(hour=20),
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            usuario=self.user_controle,
            coordenador=self.user_coordenador,
            gcal_status=Solicitacao.GCalStatus.PENDING,
        )

        sol_published = SolicitacaoFactory(
            status="aprovado",
            inicio=ref_date.replace(hour=22),
            fim=ref_date.replace(hour=23, minute=30),
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            usuario=self.user_controle,
            coordenador=self.user_coordenador,
            gcal_status=Solicitacao.GCalStatus.PUBLISHED,
        )

        # Autenticar como Controle
        self.client.force_authenticate(user=self.user_controle)

        # Request com start=end=2025-02-15
        response = self.client.get(self.url, {"start": "2025-02-15", "end": "2025-02-15"})

        # Validar response
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["errors"], 2)
        self.assertEqual(data["pending"], 1)
        self.assertEqual(data["published"], 1)
        self.assertEqual(data["none"], 0)
        self.assertEqual(data["window"]["start"], "2025-02-15")
        self.assertEqual(data["window"]["end"], "2025-02-15")

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
        sol_midnight = SolicitacaoFactory(
            status="aprovado",
            inicio=ref_date,
            fim=ref_date + timedelta(hours=1),
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            usuario=self.user_controle,
            coordenador=self.user_coordenador,
            gcal_status=Solicitacao.GCalStatus.ERROR,
        )

        # Evento exatamente às 23:59:59 (fim do dia)
        sol_eod = SolicitacaoFactory(
            status="aprovado",
            inicio=ref_date.replace(hour=23, minute=59, second=59),
            fim=ref_date.replace(hour=23, minute=59, second=59) + timedelta(hours=1),
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            usuario=self.user_controle,
            coordenador=self.user_coordenador,
            gcal_status=Solicitacao.GCalStatus.PENDING,
        )

        # Evento um dia antes (excluir)
        sol_before = SolicitacaoFactory(
            status="aprovado",
            inicio=ref_date - timedelta(days=1, hours=1),
            fim=ref_date - timedelta(days=1),
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            usuario=self.user_controle,
            coordenador=self.user_coordenador,
            gcal_status=Solicitacao.GCalStatus.ERROR,
        )

        # Evento um dia depois (excluir)
        sol_after = SolicitacaoFactory(
            status="aprovado",
            inicio=ref_date + timedelta(days=1, hours=1),
            fim=ref_date + timedelta(days=1, hours=2),
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            usuario=self.user_controle,
            coordenador=self.user_coordenador,
            gcal_status=Solicitacao.GCalStatus.PUBLISHED,
        )

        # Autenticar como Controle
        self.client.force_authenticate(user=self.user_controle)

        # Request com start=end=2025-02-20
        response = self.client.get(self.url, {"start": "2025-02-20", "end": "2025-02-20"})

        # Validar response
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Deve incluir apenas sol_midnight (ERROR) e sol_eod (PENDING)
        self.assertEqual(data["errors"], 1)  # sol_midnight
        self.assertEqual(data["pending"], 1)  # sol_eod
        self.assertEqual(data["published"], 0)  # sol_after excluído
        self.assertEqual(data["none"], 0)

    def test_alerts_no_params_returns_counts_and_window_null(self):
        """
        Teste 5: Sem start/end, retorna window: {start:null, end:null} com contagens globais.

        Cria 3 eventos aprovados em datas diferentes e valida que sem filtros
        todos são contabilizados.
        """
        # Criar 3 eventos em datas diferentes
        now = datetime.now(self.tz_local)

        sol_1 = SolicitacaoFactory(
            status="aprovado",
            inicio=now,
            fim=now + timedelta(hours=2),
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            usuario=self.user_controle,
            coordenador=self.user_coordenador,
            gcal_status=Solicitacao.GCalStatus.ERROR,
        )

        sol_2 = SolicitacaoFactory(
            status="aprovado",
            inicio=now + timedelta(days=5),
            fim=now + timedelta(days=5, hours=2),
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            usuario=self.user_controle,
            coordenador=self.user_coordenador,
            gcal_status=Solicitacao.GCalStatus.PUBLISHED,
        )

        sol_3 = SolicitacaoFactory(
            status="aprovado",
            inicio=now + timedelta(days=10),
            fim=now + timedelta(days=10, hours=2),
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            usuario=self.user_controle,
            coordenador=self.user_coordenador,
            gcal_status=Solicitacao.GCalStatus.NONE,
        )

        # Autenticar como Controle
        self.client.force_authenticate(user=self.user_controle)

        # Request sem parâmetros
        response = self.client.get(self.url)

        # Validar response
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Validar contagens mínimas (xdist-safe: outros testes podem criar dados)
        self.assertGreaterEqual(data["errors"], 1)
        self.assertGreaterEqual(data["published"], 1)
        self.assertGreaterEqual(data["none"], 1)

        # Validar window null
        self.assertIsNone(data["window"]["start"])
        self.assertIsNone(data["window"]["end"])
