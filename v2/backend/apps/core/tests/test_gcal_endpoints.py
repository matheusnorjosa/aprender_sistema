"""
P0.1 - Testes para Endpoints de Google Calendar (Preview/Apply)

LEGADO v1: Este arquivo referencia rotas antigas (/api/pre-agenda/...).
No v2, os testes de pré-agenda estão em test_preagenda_*.py.

Valida que endpoints de GCal tratam erros corretamente:
- Validam GCAL_CALENDAR_ID
- Parsam output JSON do comando
- Retornam HTTP 400 em caso de erro
- Registram falhas em AuditLog com status="ERROR"
"""

import pytest
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status as http_status

from apps.core.models import Usuario, Solicitacao, Municipio, Projeto, TipoEvento, AuditLog
from django.contrib.auth.models import Group

# Marcar todo o módulo como skip (legacy v1)
pytestmark = pytest.mark.skip(reason="Legacy endpoints (v1); coberto por test_preagenda_* no v2")


class GCalEndpointsTests(TestCase):
    """Testes de segurança e robustez para endpoints de GCal"""

    def setUp(self):
        """Setup: criar usuário Controle, solicitação, e grupos"""
        # Criar grupo Controle
        self.group_controle, _ = Group.objects.get_or_create(name="Controle")

        # Criar usuário Controle
        self.user_controle = Usuario.objects.create_user(
            username="controle_user",
            email="controle@example.com",
            password="senha123",
        )
        self.user_controle.groups.add(self.group_controle)

        # Criar entidades necessárias
        self.municipio = Municipio.objects.create(nome="Fortaleza", uf="CE")
        self.projeto = Projeto.objects.create(nome="Projeto Teste", codigo="TESTE")
        self.tipo_evento = TipoEvento.objects.create(nome="Formação")

        # Criar solicitação aprovada
        self.solicitacao = Solicitacao.objects.create(
            usuario=self.user_controle,
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            tipo="formacao",
            inicio="2025-12-01T09:00:00-03:00",
            fim="2025-12-01T12:00:00-03:00",
            status="aprovado",
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user_controle)

    def test_preview_fails_when_gcal_calendar_id_missing(self):
        """
        P0.1 - Preview endpoint DEVE retornar 400 se GCAL_CALENDAR_ID ausente

        Cenário:
        - GCAL_MODE='google' (modo real)
        - GCAL_CALENDAR_ID='' (vazio)
        - Controle tenta fazer preview

        Expectativa:
        - HTTP 400 Bad Request
        - Mensagem: "Google Calendar não configurado"
        """
        with override_settings(
            FEATURE_FLAGS={"GCAL_MODE": "google", "PREVIEW_ONLY": False},
            GCAL_CALENDAR_ID="",  # Vazio
        ):
            response = self.client.post(
                f"/api/pre-agenda/{self.solicitacao.id}/preview-gcal/"
            )

            # Validar resposta
            self.assertEqual(response.status_code, http_status.HTTP_400_BAD_REQUEST)
            self.assertIn("Google Calendar não configurado", response.json()["detail"])

    def test_preview_logs_error_in_auditlog_on_command_failure(self):
        """
        P0.1 - Preview DEVE registrar erro em AuditLog quando comando falha

        Cenário:
        - call_command retorna JSON com {"error": true, "errors": [...]}
        - Preview detecta erro no output

        Expectativa:
        - HTTP 400 Bad Request
        - AuditLog criado com action="GCAL_PREVIEW", details.error=true
        """
        with override_settings(
            FEATURE_FLAGS={"GCAL_MODE": "google", "PREVIEW_ONLY": False},
            GCAL_CALENDAR_ID="test-calendar@example.com",
        ):
            # Mock call_command para retornar erro
            with patch("django.core.management.call_command") as mock_call:
                with patch("io.StringIO") as mock_stringio:
                    # Simular output JSON com erro
                    mock_stdout = MagicMock()
                    mock_stdout.getvalue.return_value = (
                        '{"error": true, "message": "Calendário não encontrado", '
                        '"errors": ["Calendar ID inválido"]}'
                    )
                    mock_stringio.return_value = mock_stdout

                    response = self.client.post(
                        f"/api/pre-agenda/{self.solicitacao.id}/preview-gcal/"
                    )

                    # Validar resposta HTTP
                    self.assertEqual(response.status_code, http_status.HTTP_400_BAD_REQUEST)
                    self.assertIn("Calendário não encontrado", response.json()["detail"])

                    # Validar AuditLog
                    log = AuditLog.objects.filter(action="GCAL_PREVIEW").first()
                    self.assertIsNotNone(log)
                    self.assertTrue(log.details.get("error"))
                    self.assertEqual(
                        log.details.get("message"), "Calendário não encontrado"
                    )
                    self.assertIn("Calendar ID inválido", log.details.get("errors"))

    def test_apply_returns_403_when_preview_only_flag_active(self):
        """
        P0.2 - Apply endpoint DEVE retornar 403 quando PREVIEW_ONLY=True

        Cenário:
        - PREVIEW_ONLY=True (flag de segurança ativa)
        - Controle tenta aplicar mudanças no GCal

        Expectativa:
        - HTTP 403 Forbidden
        - Mensagem: "Apply bloqueado: PREVIEW_ONLY mode está ativo"
        """
        with override_settings(
            FEATURE_FLAGS={"GCAL_MODE": "google", "PREVIEW_ONLY": True},
            GCAL_CALENDAR_ID="test-calendar@example.com",
        ):
            response = self.client.post(
                f"/api/pre-agenda/{self.solicitacao.id}/apply-gcal/"
            )

            # Validar resposta
            self.assertEqual(response.status_code, http_status.HTTP_403_FORBIDDEN)
            self.assertIn("PREVIEW_ONLY", response.json()["detail"])
            self.assertIn("bloqueado", response.json()["detail"])

    def test_preview_parses_json_output_correctly(self):
        """
        P0.1 - Preview DEVE parsear JSON do comando corretamente

        Cenário:
        - call_command retorna JSON válido
        - Preview parseia e retorna totals

        Expectativa:
        - HTTP 200 OK
        - Response contém totals.CREATE, totals.UPDATE, etc.
        """
        with override_settings(
            FEATURE_FLAGS={"GCAL_MODE": "google", "PREVIEW_ONLY": False},
            GCAL_CALENDAR_ID="test-calendar@example.com",
        ):
            # Mock call_command para retornar sucesso
            with patch("django.core.management.call_command") as mock_call:
                with patch("io.StringIO") as mock_stringio:
                    # Simular output JSON com sucesso
                    mock_stdout = MagicMock()
                    mock_stdout.getvalue.return_value = (
                        '{"error": false, "totals": {"CREATE": 3, "UPDATE": 1}, '
                        '"meta": {"preview": true}}'
                    )
                    mock_stringio.return_value = mock_stdout

                    response = self.client.post(
                        f"/api/pre-agenda/{self.solicitacao.id}/preview-gcal/"
                    )

                    # Validar resposta HTTP
                    self.assertEqual(response.status_code, http_status.HTTP_200_OK)

                    # Validar que JSON foi parseado corretamente
                    response_data = response.json()
                    self.assertTrue(response_data.get("success"))
                    preview = response_data["preview"]
                    self.assertFalse(preview.get("error", True))
                    self.assertEqual(preview["totals"]["CREATE"], 3)
                    self.assertEqual(preview["totals"]["UPDATE"], 1)
                    self.assertTrue(preview["meta"]["preview"])

    def test_apply_succeeds_when_flags_allow(self):
        """
        P0.1/P0.2 - Apply DEVE funcionar quando flags permitem

        Cenário:
        - PREVIEW_ONLY=False (apply permitido)
        - GCAL_MODE='google'
        - GCAL_CALENDAR_ID configurado
        - call_command retorna sucesso

        Expectativa:
        - HTTP 200 OK
        - AuditLog criado com action="GCAL_APPLY", status="SUCCESS"
        """
        with override_settings(
            FEATURE_FLAGS={"GCAL_MODE": "google", "PREVIEW_ONLY": False},
            GCAL_CALENDAR_ID="test-calendar@example.com",
        ):
            # Mock call_command para retornar sucesso
            with patch("django.core.management.call_command") as mock_call:
                with patch("io.StringIO") as mock_stringio:
                    # Simular output JSON com sucesso
                    mock_stdout = MagicMock()
                    mock_stdout.getvalue.return_value = (
                        '{"error": false, "totals": {"CREATE": 1}, "applied": true}'
                    )
                    mock_stringio.return_value = mock_stdout

                    response = self.client.post(
                        f"/api/pre-agenda/{self.solicitacao.id}/apply-gcal/"
                    )

                    # Validar resposta HTTP
                    self.assertEqual(response.status_code, http_status.HTTP_200_OK)

                    # Validar AuditLog
                    log = AuditLog.objects.filter(action="GCAL_APPLY").first()
                    self.assertIsNotNone(log)
                    self.assertFalse(log.details.get("dry_run", True))
