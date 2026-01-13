"""
Testes para Issue #96 - Export CSV/JSON no Dashboard GCal

Endpoint: GET /api/gcal/dashboard/events/export/

Testes obrigatórios:
1. test_export_requires_authentication → 403 anônimo
2. test_export_requires_controle_or_super → 403 para perfil não Controle/Super
3. test_export_csv_headers_and_rows → 200, CSV com BOM, cabeçalhos exatos, linhas
4. test_export_json_structure → 200, JSON com {count, results}, filtros
5. test_export_filters_respected → start/end/status filtram corretamente
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false

from __future__ import annotations
import csv
import io
import json
from datetime import date, datetime, timedelta
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from apps.core.models import (
    Solicitacao,
    Municipio,
    Projeto,
    TipoEvento,
    Usuario,
)

User = get_user_model()


class TestGCalExport(TestCase):
    """
    Testes para export CSV/JSON do Dashboard GCal (Issue #96)
    """

    def setUp(self):
        """Setup comum para todos os testes"""
        # Usar data fixa para evitar problemas com timezone
        # Data no meio do dia para evitar edge cases de timezone
        self.now = timezone.make_aware(datetime(2025, 1, 15, 12, 0, 0))

        # Criar grupos
        self.grupo_controle, _ = Group.objects.get_or_create(name='Controle')
        self.grupo_super, _ = Group.objects.get_or_create(name='Superintendência')
        self.grupo_coordenador, _ = Group.objects.get_or_create(name='Coordenador')

        # Criar usuários (Usuario é o User customizado com cpf obrigatório)
        self.user_controle = User.objects.create_user(
            username='controle_user',
            password='testpass123',
            cpf='11111111111'  # CPF único para evitar constraint violation
        )
        self.user_controle.groups.add(self.grupo_controle)

        self.user_super = User.objects.create_user(
            username='super_user',
            password='testpass123',
            cpf='22222222222'  # CPF único
        )
        self.user_super.groups.add(self.grupo_super)

        self.user_coordenador = User.objects.create_user(
            username='coordenador_user',
            password='testpass123',
            cpf='33333333333'  # CPF único
        )
        self.user_coordenador.groups.add(self.grupo_coordenador)

        # Criar dados de teste
        self.municipio = Municipio.objects.create(
            nome='Fortaleza',
            uf='CE'
        )

        self.projeto = Projeto.objects.create(
            nome='ACERTA',
            fluxo='SUPER'
        )

        self.tipo_evento = TipoEvento.objects.create(
            nome='Fundamental I Online'
        )

        # Criar solicitações aprovadas com gcal_status diferentes
        self.sol_published = Solicitacao.objects.create(
            status='aprovado',
            inicio=self.now + timedelta(days=1),
            fim=self.now + timedelta(days=1, hours=2),
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            usuario=self.user_controle,
            coordenador=self.user_coordenador,
            gcal_status=Solicitacao.GCalStatus.PUBLISHED,
            external_event_id='asv2-123',
            meet_link='https://meet.google.com/abc-def-ghi'
        )

        self.sol_error = Solicitacao.objects.create(
            status='aprovado',
            inicio=self.now + timedelta(days=2),
            fim=self.now + timedelta(days=2, hours=2),
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            usuario=self.user_controle,
            coordenador=self.user_coordenador,
            gcal_status=Solicitacao.GCalStatus.ERROR,
            gcal_last_error='500 Internal Server Error'
        )

        self.sol_none = Solicitacao.objects.create(
            status='aprovado',
            inicio=self.now + timedelta(days=3),
            fim=self.now + timedelta(days=3, hours=2),
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            usuario=self.user_controle,
            coordenador=self.user_coordenador,
            gcal_status=Solicitacao.GCalStatus.NONE
        )

        # Cliente API
        self.client = APIClient()
        self.url = reverse('core:gcal-dashboard-events-export')

    def test_export_requires_authentication(self):
        """
        Teste 1: Export deve retornar 403 para usuário anônimo
        """
        self.client.logout()
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_export_requires_controle_or_super(self):
        """
        Teste 2: Export deve retornar 403 para perfil não Controle/Super
        """
        self.client.force_authenticate(user=self.user_coordenador)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_export_csv_headers_and_rows(self):
        """
        Teste 3: Export CSV deve ter:
        - Status 200
        - Content-Type: text/csv; charset=utf-8
        - BOM UTF-8
        - Cabeçalhos exatos
        - Linhas com dados corretos
        """
        self.client.force_authenticate(user=self.user_controle)
        response = self.client.get(self.url, {'export_format': 'csv'})

        # Verificar status
        self.assertEqual(response.status_code, 200)

        # Verificar Content-Type
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')

        # Verificar Content-Disposition
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn('gcal_events_', response['Content-Disposition'])

        # Verificar BOM UTF-8
        content = response.content.decode('utf-8')
        self.assertTrue(content.startswith('\ufeff'))

        # Parse CSV
        csv_content = content.lstrip('\ufeff')
        reader = csv.reader(io.StringIO(csv_content))
        rows = list(reader)

        # Verificar cabeçalhos (ordem exata da especificação)
        expected_headers = [
            'id',
            'municipio',
            'projeto',
            'tipo_evento',
            'inicio',
            'fim',
            'usuario',
            'coordenador',
            'fluxo',
            'gcal_status',
            'external_event_id',
            'gcal_last_sync_at',
            'gcal_last_error',
            'meet_link',
            'gcal_payload_hash',
            'updated_at'
        ]
        self.assertEqual(rows[0], expected_headers)

        # Verificar presença de linhas de dados (pelo menos 3 solicitações)
        self.assertGreaterEqual(len(rows), 4)  # 1 header + 3 data rows

        # Verificar conteúdo de uma linha (sol_published)
        # Encontrar linha com ID correto
        data_rows = rows[1:]
        sol_pub_row = None
        for row in data_rows:
            if row[0] == str(self.sol_published.id):
                sol_pub_row = row
                break

        self.assertIsNotNone(sol_pub_row)
        self.assertEqual(sol_pub_row[1], 'Fortaleza')  # municipio
        self.assertEqual(sol_pub_row[2], 'ACERTA')  # projeto
        self.assertEqual(sol_pub_row[3], 'Fundamental I Online')  # tipo_evento
        self.assertEqual(sol_pub_row[6], 'controle_user')  # usuario
        self.assertEqual(sol_pub_row[7], 'coordenador_user')  # coordenador
        self.assertEqual(sol_pub_row[8], 'SUPER')  # fluxo
        self.assertEqual(sol_pub_row[9], 'PUBLISHED')  # gcal_status
        self.assertEqual(sol_pub_row[10], 'asv2-123')  # external_event_id
        self.assertIn('meet.google.com', sol_pub_row[13])  # meet_link

    def test_export_json_structure(self):
        """
        Teste 4: Export JSON deve ter:
        - Status 200
        - Content-Type: application/json
        - Estrutura {count, results}
        - Respeitando filtros
        """
        self.client.force_authenticate(user=self.user_super)
        response = self.client.get(self.url, {'export_format': 'json'})

        # Verificar status
        self.assertEqual(response.status_code, 200)

        # Verificar Content-Type
        self.assertEqual(response['Content-Type'], 'application/json')

        # Parse JSON
        data = response.json()

        # Verificar estrutura
        self.assertIn('count', data)
        self.assertIn('results', data)
        self.assertEqual(data['count'], len(data['results']))

        # Verificar que tem pelo menos 3 solicitações
        self.assertGreaterEqual(data['count'], 3)

        # Verificar estrutura de um resultado
        first_result = data['results'][0]
        self.assertIn('id', first_result)
        self.assertIn('gcal_status', first_result)
        self.assertIn('municipio', first_result)
        self.assertIn('projeto', first_result)

    def test_export_filters_respected(self):
        """
        Teste 5: Filtros (status, start, end) devem ser respeitados
        """
        self.client.force_authenticate(user=self.user_controle)

        # Teste filtro por status=ERROR
        response = self.client.get(self.url, {'export_format': 'json', 'status': 'ERROR'})
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['gcal_status'], 'ERROR')

        # Teste filtro por status=PUBLISHED
        response = self.client.get(self.url, {'export_format': 'json', 'status': 'PUBLISHED'})
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['gcal_status'], 'PUBLISHED')

        # Teste filtro por start (apenas eventos futuros +2 dias)
        # Issue #124: Agora com helper timezone-aware, deve retornar corretamente
        start_date = (self.now + timedelta(days=2)).strftime('%Y-%m-%d')
        response = self.client.get(self.url, {'export_format': 'json', 'start': start_date})
        data = response.json()
        self.assertEqual(response.status_code, 200)
        # Deve retornar sol_error (dia+2) e sol_none (dia+3)
        self.assertEqual(data['count'], 2)

        # Teste filtro por end (apenas eventos até +1 dia)
        end_date = (self.now + timedelta(days=1)).strftime('%Y-%m-%d')
        response = self.client.get(self.url, {'export_format': 'json', 'end': end_date})
        data = response.json()
        self.assertEqual(response.status_code, 200)
        # Deve retornar apenas sol_published (1 evento)
        self.assertEqual(data['count'], 1)

        # Teste combinação de filtros (status + start + end)
        response = self.client.get(self.url, {
            'export_format': 'json',
            'status': 'PUBLISHED',
            'start': (self.now + timedelta(days=0)).strftime('%Y-%m-%d'),
            'end': (self.now + timedelta(days=1)).strftime('%Y-%m-%d')
        })
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['id'], self.sol_published.id)

    def test_export_edge_cases_timezone_boundaries(self):
        """
        Teste 6: Casos de borda timezone-aware (Issue #124)

        Valida que eventos exatamente em 00:00 e 23:59:59 são incluídos
        corretamente na janela local (America/Fortaleza).
        """
        from zoneinfo import ZoneInfo
        from django.utils import timezone as django_tz

        # Timezone local
        tz_local = ZoneInfo('America/Fortaleza')

        # Data de referência para o teste
        ref_date = datetime(2025, 2, 10, 0, 0, 0, tzinfo=tz_local)

        # Evento exatamente às 00:00 (início do dia)
        sol_midnight = Solicitacao.objects.create(
            status='aprovado',
            inicio=ref_date,  # 2025-02-10 00:00 BRT
            fim=ref_date + timedelta(hours=1),
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            usuario=self.user_controle,
            coordenador=self.user_coordenador,
            gcal_status=Solicitacao.GCalStatus.PUBLISHED
        )

        # Evento exatamente às 23:59:59 (fim do dia)
        sol_eod = Solicitacao.objects.create(
            status='aprovado',
            inicio=ref_date.replace(hour=23, minute=59, second=59),  # 2025-02-10 23:59:59 BRT
            fim=ref_date.replace(hour=23, minute=59, second=59) + timedelta(hours=1),
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            usuario=self.user_controle,
            coordenador=self.user_coordenador,
            gcal_status=Solicitacao.GCalStatus.ERROR
        )

        # Evento um dia antes (deve ser excluído quando start=2025-02-10)
        sol_before = Solicitacao.objects.create(
            status='aprovado',
            inicio=ref_date - timedelta(days=1),  # 2025-02-09
            fim=ref_date - timedelta(days=1) + timedelta(hours=2),
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            usuario=self.user_controle,
            coordenador=self.user_coordenador,
            gcal_status=Solicitacao.GCalStatus.PUBLISHED
        )

        # Evento um dia depois (deve ser excluído quando end=2025-02-10)
        sol_after = Solicitacao.objects.create(
            status='aprovado',
            inicio=ref_date + timedelta(days=1),  # 2025-02-11
            fim=ref_date + timedelta(days=1) + timedelta(hours=2),
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            usuario=self.user_controle,
            coordenador=self.user_coordenador,
            gcal_status=Solicitacao.GCalStatus.NONE
        )

        # Teste 1: Filtro start=2025-02-10 deve incluir midnight e eod, excluir before
        self.client.force_authenticate(user=self.user_controle)
        response = self.client.get(self.url, {
            'export_format': 'json',
            'start': '2025-02-10'
        })
        data = response.json()
        self.assertEqual(response.status_code, 200)
        # Deve incluir: sol_midnight, sol_eod, sol_after, e os 3 do setUp (6 total)
        # mas excluir sol_before (1 evento)
        returned_ids = [item['id'] for item in data['results']]
        self.assertIn(sol_midnight.id, returned_ids, "Evento às 00:00 deve ser incluído")
        self.assertIn(sol_eod.id, returned_ids, "Evento às 23:59:59 deve ser incluído")
        self.assertIn(sol_after.id, returned_ids, "Evento depois deve ser incluído")
        self.assertNotIn(sol_before.id, returned_ids, "Evento antes deve ser excluído")

        # Teste 2: Filtro end=2025-02-10 deve incluir midnight e eod, excluir after
        response = self.client.get(self.url, {
            'export_format': 'json',
            'end': '2025-02-10'
        })
        data = response.json()
        self.assertEqual(response.status_code, 200)
        returned_ids = [item['id'] for item in data['results']]
        self.assertIn(sol_midnight.id, returned_ids, "Evento às 00:00 deve ser incluído")
        self.assertIn(sol_eod.id, returned_ids, "Evento às 23:59:59 deve ser incluído")
        self.assertIn(sol_before.id, returned_ids, "Evento antes deve ser incluído")
        self.assertNotIn(sol_after.id, returned_ids, "Evento depois deve ser excluído")

        # Teste 3: Janela exata (start=end=2025-02-10) deve incluir apenas midnight e eod
        response = self.client.get(self.url, {
            'export_format': 'json',
            'start': '2025-02-10',
            'end': '2025-02-10'
        })
        data = response.json()
        self.assertEqual(response.status_code, 200)
        returned_ids = [item['id'] for item in data['results']]
        self.assertIn(sol_midnight.id, returned_ids)
        self.assertIn(sol_eod.id, returned_ids)
        self.assertNotIn(sol_before.id, returned_ids)
        self.assertNotIn(sol_after.id, returned_ids)
        # Deve ter exatamente 2 eventos (midnight + eod)
        self.assertEqual(data['count'], 2)
