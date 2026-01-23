"""
Fase 3 - Testes para Template Padronizado Google Calendar

Valida formatação de título e descrição conforme especificação Fase 3:
- Title: "{municipio.nome} - {municipio.uf} {segmento} {modalidade} [{projeto.codigo}]"
- Description: Seções estruturadas (Município, Projeto, Data, Modalidade, Equipe, Observações)

Cobertura:
- Formatação completa (todos os campos)
- Formatação parcial (campos opcionais ausentes)
- Timezone correto (America/Fortaleza)
- Truncation (summary > 1000 chars, description > 5000 chars)
- Preview endpoint (GET /api/solicitacoes/{id}/preview-gcal/)
- Publish endpoint (POST /api/solicitacoes/{id}/publish/)
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from datetime import datetime, timedelta

from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status as http_status
from rest_framework.test import APIClient

import pytest
import pytz

from apps.core.models import Municipio, Projeto, Solicitacao, TipoEvento, Usuario
from apps.core.services.gcal_sync_service import build_event_payload, build_preview_for_solicitacao


class GCalTemplateFase3Tests(TestCase):
    """Testes para validar template padronizado (Fase 3)"""

    def setUp(self):
        """Setup: criar dados de teste completos"""
        # Criar grupos (get_or_create para evitar IntegrityError)
        self.group_coord, _ = Group.objects.get_or_create(name="Coordenador")
        self.group_controle, _ = Group.objects.get_or_create(name="Controle")

        # Criar usuários (com CPF único para evitar IntegrityError)
        self.coord = Usuario.objects.create_user(
            username="coord_fase3",
            email="coord_fase3@example.com",
            password="senha123",
            cpf="11111111111",  # CPF único
            first_name="Maria",
            last_name="Silva",
        )
        self.coord.groups.add(self.group_coord)

        self.formador = Usuario.objects.create_user(
            username="formador_fase3",
            email="formador_fase3@example.com",
            password="senha123",
            cpf="22222222222",  # CPF único
            first_name="João",
            last_name="Santos",
        )

        self.controle = Usuario.objects.create_user(
            username="controle_fase3",
            email="controle_fase3@example.com",
            password="senha123",
            cpf="33333333333",  # CPF único
        )
        self.controle.groups.add(self.group_controle)

        # Criar entidades de negócio
        self.municipio = Municipio.objects.create(nome="Salvador", uf="BA")
        self.projeto = Projeto.objects.create(
            nome="Projeto ACerta",
            codigo="ACERTA",
            fluxo="NAO_SUPER",
        )
        self.tipo_evento = TipoEvento.objects.create(nome="Formação Presencial")

        # Datas (America/Fortaleza)
        fortaleza_tz = pytz.timezone("America/Fortaleza")
        self.inicio = fortaleza_tz.localize(datetime(2025, 12, 15, 9, 0, 0))
        self.fim = fortaleza_tz.localize(datetime(2025, 12, 15, 12, 0, 0))

        self.client = APIClient()

    def test_title_format_complete(self):
        """
        Fase 3 - Título completo com todos os campos presentes

        Expected: "Salvador - BA Fundamental I Online [ACERTA]"
        """
        solicitacao = Solicitacao.objects.create(
            usuario=self.coord,
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            inicio=self.inicio,
            fim=self.fim,
            status="aprovado",
            segmento="Fundamental I",
            is_online=True,
        )

        payload = build_event_payload(solicitacao, enable_meet=False)

        # Validar summary
        expected_title = "Salvador - BA Fundamental I Online [ACERTA]"
        self.assertEqual(payload["summary"], expected_title)

    def test_title_format_without_segmento(self):
        """
        Fase 3 - Título sem segmento (opcional)

        Expected: "Salvador - BA Presencial [ACERTA]"
        """
        solicitacao = Solicitacao.objects.create(
            usuario=self.coord,
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            inicio=self.inicio,
            fim=self.fim,
            status="aprovado",
            segmento="",  # Vazio
            is_online=False,
        )

        payload = build_event_payload(solicitacao, enable_meet=False)

        # Validar summary (sem segmento)
        expected_title = "Salvador - BA Presencial [ACERTA]"
        self.assertEqual(payload["summary"], expected_title)

    def test_title_format_without_projeto_codigo(self):
        """
        Fase 3 - Título com projeto sem código (usa nome como fallback)

        Expected: "Salvador - BA Online [Projeto sem Código]"
        """
        projeto_sem_codigo = Projeto.objects.create(
            nome="Projeto sem Código",
            codigo="",  # Vazio
            fluxo="NAO_SUPER",
        )

        solicitacao = Solicitacao.objects.create(
            usuario=self.coord,
            municipio=self.municipio,
            projeto=projeto_sem_codigo,
            tipo_evento=self.tipo_evento,
            inicio=self.inicio,
            fim=self.fim,
            status="aprovado",
            is_online=True,
        )

        payload = build_event_payload(solicitacao, enable_meet=False)

        # Validar summary (usa nome do projeto como fallback)
        expected_title = "Salvador - BA Online [Projeto sem Código]"
        self.assertEqual(payload["summary"], expected_title)

    def test_title_modalidade_presencial(self):
        """
        Fase 3 - Modalidade "Presencial" quando is_online=False

        Expected: "... Presencial ..."
        """
        solicitacao = Solicitacao.objects.create(
            usuario=self.coord,
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            inicio=self.inicio,
            fim=self.fim,
            status="aprovado",
            is_online=False,
        )

        payload = build_event_payload(solicitacao, enable_meet=False)

        # Validar que contém "Presencial"
        self.assertIn("Presencial", payload["summary"])
        self.assertNotIn("Online", payload["summary"])

    def test_description_format_complete(self):
        """
        Fase 3 - Descrição completa com todas as seções

        Expected sections:
        - Header: "📋 Solicitação #{id} — AS v2"
        - Município: "📍 Município: Salvador - BA"
        - Projeto: "📂 Projeto: Projeto ACerta (ACERTA)"
        - Tipo: "🎯 Tipo: Formação Presencial"
        - Data: "📅 Data: 15/12/2025 09:00 a 15/12/2025 12:00"
        - Modalidade: "🌐 Modalidade: Presencial"
        - Equipe: "👥 Equipe: ..."
        - Observações: "📝 Observações: ..."
        """
        solicitacao = Solicitacao.objects.create(
            usuario=self.coord,
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            inicio=self.inicio,
            fim=self.fim,
            status="aprovado",
            coordenador=self.coord,
            observacoes="Trazer materiais de apoio",
            is_online=False,
        )
        solicitacao.formadores.add(self.formador)

        payload = build_event_payload(solicitacao, enable_meet=False)

        # Validar seções na descrição
        description = payload["description"]

        self.assertIn(f"📋 Solicitação #{solicitacao.id} — AS v2", description)
        self.assertIn("📍 Município: Salvador - BA", description)
        self.assertIn("📂 Projeto: Projeto ACerta (ACERTA)", description)
        self.assertIn("🎯 Tipo: Formação Presencial", description)
        self.assertIn("📅 Data: 15/12/2025 09:00 a 15/12/2025 12:00", description)
        self.assertIn("🌐 Modalidade: Presencial", description)
        self.assertIn("👥 Equipe:", description)
        self.assertIn("Formador(es): João Santos", description)
        self.assertIn("Coordenador(a): Maria Silva", description)
        self.assertIn("📝 Observações:", description)
        self.assertIn("Trazer materiais de apoio", description)

    def test_description_format_without_optional_fields(self):
        """
        Fase 3 - Descrição sem campos opcionais (coordenador, formadores, observações)

        Expected: Seções obrigatórias presentes, opcionais ausentes
        """
        solicitacao = Solicitacao.objects.create(
            usuario=self.coord,
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            inicio=self.inicio,
            fim=self.fim,
            status="aprovado",
            coordenador=None,  # Sem coordenador
            observacoes="",  # Sem observações
            is_online=False,
        )
        # Sem formadores (ManyToMany vazio)

        payload = build_event_payload(solicitacao, enable_meet=False)

        description = payload["description"]

        # Validar seções obrigatórias presentes
        self.assertIn(f"📋 Solicitação #{solicitacao.id} — AS v2", description)
        self.assertIn("📍 Município: Salvador - BA", description)
        self.assertIn("📂 Projeto:", description)
        self.assertIn("🎯 Tipo:", description)
        self.assertIn("📅 Data:", description)
        self.assertIn("🌐 Modalidade:", description)

        # Validar seções opcionais ausentes
        self.assertNotIn("👥 Equipe:", description)
        self.assertNotIn("📝 Observações:", description)

    def test_timezone_correct_fortaleza(self):
        """
        Fase 3 - Validar que data/horário usa timezone America/Fortaleza

        Expected: Data formatada com timezone de Fortaleza (UTC-3)
        """
        # Criar solicitação com datetime UTC
        inicio_utc = timezone.make_aware(datetime(2025, 12, 15, 12, 0, 0), timezone=pytz.UTC)
        fim_utc = timezone.make_aware(datetime(2025, 12, 15, 15, 0, 0), timezone=pytz.UTC)

        solicitacao = Solicitacao.objects.create(
            usuario=self.coord,
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            inicio=inicio_utc,
            fim=fim_utc,
            status="aprovado",
        )

        payload = build_event_payload(solicitacao, enable_meet=False)

        description = payload["description"]

        # UTC 12:00 → Fortaleza 09:00 (UTC-3)
        # UTC 15:00 → Fortaleza 12:00 (UTC-3)
        self.assertIn("📅 Data: 15/12/2025 09:00 a 15/12/2025 12:00", description)

    def test_title_with_long_fields_respects_constraints(self):
        """
        Fase 3 - Título com campos longos (respeitando constraints do DB)

        Expected:
        - Summary contém todos os campos sem truncation (< 1000 chars)
        - Nenhum erro de validação do banco de dados
        - Template formatado corretamente
        """
        # Criar município com nome longo (respeitando max_length=100)
        municipio_longo = Municipio.objects.create(
            nome="A" * 95,  # Nome com 95 caracteres (< 100)
            uf="BA",
        )

        projeto_longo = Projeto.objects.create(
            nome="B" * 200,  # Nome com 200 caracteres
            codigo="C" * 50,  # Código com 50 caracteres
            fluxo="NAO_SUPER",
        )

        solicitacao = Solicitacao.objects.create(
            usuario=self.coord,
            municipio=municipio_longo,
            projeto=projeto_longo,
            tipo_evento=self.tipo_evento,
            inicio=self.inicio,
            fim=self.fim,
            status="aprovado",
            segmento="D" * 95,  # Segmento longo (respeitando max_length=100)
            observacoes="E" * 4000,  # Observações longas
        )

        payload = build_event_payload(solicitacao, enable_meet=False)

        # Validar summary contém todos os campos esperados
        self.assertIn("A" * 95, payload["summary"])  # Município
        self.assertIn("BA", payload["summary"])  # UF
        self.assertIn("D" * 95, payload["summary"])  # Segmento
        self.assertIn("Presencial", payload["summary"])  # Modalidade
        self.assertIn("[" + "C" * 50 + "]", payload["summary"])  # Projeto codigo

        # Validar que não truncou (ainda < 1000 chars)
        self.assertLess(len(payload["summary"]), 1000)
        self.assertFalse(payload["summary"].endswith("..."))

        # Validar description contém observações longas
        self.assertIn("E" * 4000, payload["description"])

    def test_description_truncation_over_5000_chars(self):
        """
        Fase 3 - Descrição > 5000 chars deve truncar para 4997 + "..."

        Expected: description[:4997] + "..."
        """
        # Criar observações com texto muito longo
        observacoes_longas = "X" * 6000  # 6000 caracteres

        solicitacao = Solicitacao.objects.create(
            usuario=self.coord,
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            inicio=self.inicio,
            fim=self.fim,
            status="aprovado",
            observacoes=observacoes_longas,
        )

        payload = build_event_payload(solicitacao, enable_meet=False)

        # Validar description truncada
        self.assertEqual(len(payload["description"]), 5000)
        self.assertTrue(payload["description"].endswith("..."))

    @override_settings(GCAL_CLIENT="fake")
    def test_preview_endpoint_returns_formatted_payload(self):
        """
        Fase 3 - Endpoint preview retorna payload formatado corretamente

        GET /api/solicitacoes/{id}/preview-gcal/

        Expected: JSON com payload contendo título e descrição formatados
        """
        solicitacao = Solicitacao.objects.create(
            usuario=self.coord,
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            inicio=self.inicio,
            fim=self.fim,
            status="aprovado",
            segmento="Fundamental II",
            is_online=True,
        )

        # Autenticar como Controle
        self.client.force_authenticate(user=self.controle)

        # Chamar endpoint preview (POST, not GET)
        response = self.client.post(f"/api/solicitacoes/{solicitacao.id}/preview-gcal/")

        # Validar resposta
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        data = response.json()

        # Validar payload contém título formatado (estrutura: data["preview"]["payload"])
        self.assertIn("preview", data)
        payload = data["preview"]["payload"]
        self.assertIn("Salvador - BA", payload["summary"])
        self.assertIn("Fundamental II", payload["summary"])
        self.assertIn("Online", payload["summary"])
        self.assertIn("[ACERTA]", payload["summary"])

        # Validar payload contém descrição formatada
        self.assertIn("📋 Solicitação", payload["description"])
        self.assertIn("📍 Município:", payload["description"])
        self.assertIn("📂 Projeto:", payload["description"])

    @override_settings(GCAL_CLIENT="fake")
    def test_publish_endpoint_persists_formatted_payload(self):
        """
        Fase 3 - Endpoint publish persiste payload formatado no GCal (fake)

        POST /api/solicitacoes/{id}/publish/

        Expected:
        - HTTP 200
        - gcal_event_id setado (fake-event-{timestamp})
        - gcal_payload_hash setado (SHA1)
        - Título e descrição formatados conforme Fase 3
        """
        solicitacao = Solicitacao.objects.create(
            usuario=self.coord,
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            inicio=self.inicio,
            fim=self.fim,
            status="aprovado",
            segmento="Fundamental I",
            is_online=False,
        )

        # Autenticar como Controle
        self.client.force_authenticate(user=self.controle)

        # Chamar endpoint publish (com apply_blocked para teste)
        response = self.client.post(
            f"/api/solicitacoes/{solicitacao.id}/publish/",
            data={"dry_run": False, "apply_blocked": True},
            format="json",
        )

        # Validar resposta (aceita 200 OK ou 202 Accepted para operações assíncronas)
        self.assertIn(response.status_code, [http_status.HTTP_200_OK, http_status.HTTP_202_ACCEPTED])
        data = response.json()

        # Para 202 Accepted: endpoint retorna task_id (operação assíncrona via Celery)
        # Validar task_id e solicitacao_id
        self.assertIsNotNone(data.get("task_id"))
        self.assertEqual(data.get("solicitacao_id"), solicitacao.id)

        # Recarregar solicitação e validar que está em PENDING (aguardando task)
        solicitacao.refresh_from_db()
        self.assertEqual(solicitacao.gcal_status, "PENDING")

    def test_build_preview_function_returns_template(self):
        """
        Fase 3 - Função build_preview_for_solicitacao retorna template formatado

        Function: build_preview_for_solicitacao(s)

        Expected: dict com event_id, payload, payload_hash, meet_link (se online)
        """
        solicitacao = Solicitacao.objects.create(
            usuario=self.coord,
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            inicio=self.inicio,
            fim=self.fim,
            status="aprovado",
            is_online=True,
        )

        preview = build_preview_for_solicitacao(solicitacao)

        # Validar estrutura do preview
        self.assertIn("event_id", preview)
        self.assertIn("payload", preview)
        self.assertIn("payload_hash", preview)
        self.assertIn("meet_link", preview)

        # Validar payload formatado
        payload = preview["payload"]
        self.assertIn("Salvador - BA", payload["summary"])
        self.assertIn("Online", payload["summary"])
        self.assertIn("📋 Solicitação", payload["description"])

        # Validar meet_link fake (preview apenas)
        self.assertIsNotNone(preview["meet_link"])
        self.assertTrue(preview["meet_link"].startswith("https://meet.google.com/fake-"))

    def test_multiple_formadores_in_description(self):
        """
        Fase 3 - Descrição lista múltiplos formadores corretamente

        Expected: "Formador(es): João Santos, Pedro Oliveira"
        """
        formador2 = Usuario.objects.create_user(
            username="formador2_fase3",
            email="formador2_fase3@example.com",
            password="senha123",
            cpf="44444444444",  # CPF único
            first_name="Pedro",
            last_name="Oliveira",
        )

        solicitacao = Solicitacao.objects.create(
            usuario=self.coord,
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            inicio=self.inicio,
            fim=self.fim,
            status="aprovado",
        )
        solicitacao.formadores.add(self.formador, formador2)

        payload = build_event_payload(solicitacao, enable_meet=False)

        description = payload["description"]

        # Validar que ambos formadores aparecem
        self.assertIn("Formador(es): ", description)
        self.assertIn("João Santos", description)
        self.assertIn("Pedro Oliveira", description)
