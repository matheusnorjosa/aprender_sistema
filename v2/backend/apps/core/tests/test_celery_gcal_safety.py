"""
P0.3 - Testes de Segurança para Celery GCal Task

Valida que a task preview_then_apply_gcal respeita flags de segurança:
- FEATURE_AUTO_APPLY_ENABLED: guarda inicial (GUARDA 0)
- GCAL_MODE: só executa se 'google' (GUARDA 1)
- GCAL_CALENDAR_ID: só executa se configurado (GUARDA 2)
- PREVIEW_ONLY: nunca aplica mudanças
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false

from __future__ import annotations
from unittest.mock import patch, MagicMock
import pytest
from django.test import TestCase, override_settings

from apps.core.tasks import preview_then_apply_gcal
from apps.core.models import AuditLog


@pytest.fixture
def enable_auto_apply(settings):
    """
    Fixture para habilitar FEATURE_AUTO_APPLY_ENABLED.

    Necessária para testes que precisam passar da GUARDA 0 e chegar
    nas validações subsequentes (GCAL_MODE, GCAL_CALENDAR_ID, PREVIEW_ONLY).
    """
    settings.FEATURE_AUTO_APPLY_ENABLED = True
    yield


class CeleryGCalSafetyTests(TestCase):
    """Testes de segurança para task Celery de sincronização GCal"""

    @pytest.mark.usefixtures("enable_auto_apply")
    def test_task_noop_when_preview_only(self):
        """
        P0.3 - Task NÃO deve aplicar mudanças quando PREVIEW_ONLY=True

        Cenário:
        - FEATURE_AUTO_APPLY_ENABLED=True (passa GUARDA 0)
        - GCAL_MODE='google' (passa GUARDA 1)
        - GCAL_CALENDAR_ID configurado (passa GUARDA 2)
        - PREVIEW_ONLY=True (bloqueia apply)
        - Preview detecta mudanças

        Expectativa:
        - Task retorna applied=False
        - AuditLog registra "PREVIEW_ONLY bloqueou apply"
        - call_command só chamado com --dry-run (nunca sem)
        """
        with override_settings(
            FEATURE_FLAGS={"PREVIEW_ONLY": True, "GCAL_MODE": "google"},
            GCAL_CALENDAR_ID="test-calendar-id@example.com",
        ):
            # Mock call_command para retornar preview com mudanças
            with patch("apps.core.tasks.call_command") as mock_call:
                # Simular preview com mudanças detectadas
                mock_call.return_value = None

                # Simular stdout do preview
                with patch("apps.core.tasks.StringIO") as mock_stringio:
                    mock_stdout = MagicMock()
                    mock_stdout.getvalue.return_value = (
                        '{"totals": {"CREATE": 5, "UPDATE": 2}, "meta": {}}'
                    )
                    mock_stringio.return_value = mock_stdout

                    # Executar task
                    result = preview_then_apply_gcal()

                    # Validações
                    self.assertFalse(result["applied"])
                    self.assertIn("PREVIEW_ONLY", result["reason"])

                    # Verificar que call_command foi chamado APENAS com --dry-run
                    self.assertEqual(mock_call.call_count, 1)
                    call_args = mock_call.call_args[0]
                    self.assertIn("--dry-run", call_args)

                    # Verificar AuditLog
                    log = AuditLog.objects.filter(action="CELERY_GCAL_SYNC").first()
                    self.assertIsNotNone(log)
                    self.assertEqual(log.details["status"], "SUCCESS")
                    self.assertFalse(log.details["applied"])
                    self.assertIn("PREVIEW_ONLY", log.details["reason"])

    @pytest.mark.usefixtures("enable_auto_apply")
    def test_task_noop_when_calendar_unconfigured(self):
        """
        P0.3 - Task NÃO deve executar quando GCAL_CALENDAR_ID ausente

        Cenário:
        - FEATURE_AUTO_APPLY_ENABLED=True (passa GUARDA 0)
        - GCAL_MODE='google' (passa GUARDA 1)
        - GCAL_CALENDAR_ID='' (vazio) → SKIPPED na GUARDA 2

        Expectativa:
        - Task retorna status='SKIPPED'
        - AuditLog registra "GCAL_CALENDAR_ID não configurado"
        - call_command NUNCA é chamado (curto-circuito)
        """
        with override_settings(
            FEATURE_FLAGS={"GCAL_MODE": "google"},
            GCAL_CALENDAR_ID="",  # Vazio
        ):
            with patch("apps.core.tasks.call_command") as mock_call:
                # Executar task
                result = preview_then_apply_gcal()

                # Validações
                self.assertEqual(result["status"], "SKIPPED")
                self.assertIn("GCAL_CALENDAR_ID", result["reason"])

                # Verificar que call_command NUNCA foi chamado
                mock_call.assert_not_called()

                # Verificar AuditLog
                log = AuditLog.objects.filter(action="CELERY_GCAL_SYNC").first()
                self.assertIsNotNone(log)
                self.assertEqual(log.details["status"], "SKIPPED")
                self.assertIn("GCAL_CALENDAR_ID", log.details["reason"])

    @pytest.mark.usefixtures("enable_auto_apply")
    def test_task_noop_when_gcal_mode_not_google(self):
        """
        P0.3 - Task NÃO deve executar quando GCAL_MODE != 'google'

        Cenário:
        - FEATURE_AUTO_APPLY_ENABLED=True (passa GUARDA 0)
        - GCAL_MODE='fake' → SKIPPED na GUARDA 1
        - GCAL_CALENDAR_ID configurado (não chega nesta validação)

        Expectativa:
        - Task retorna status='SKIPPED'
        - AuditLog registra "GCAL_MODE=fake (esperado: 'google')"
        - call_command NUNCA é chamado (curto-circuito)
        """
        with override_settings(
            FEATURE_FLAGS={"GCAL_MODE": "fake"},
            GCAL_CALENDAR_ID="test-calendar@example.com",
        ):
            with patch("apps.core.tasks.call_command") as mock_call:
                # Executar task
                result = preview_then_apply_gcal()

                # Validações
                self.assertEqual(result["status"], "SKIPPED")
                self.assertIn("GCAL_MODE", result["reason"])
                self.assertIn("fake", result["reason"])

                # Verificar que call_command NUNCA foi chamado
                mock_call.assert_not_called()

                # Verificar AuditLog
                log = AuditLog.objects.filter(action="CELERY_GCAL_SYNC").first()
                self.assertIsNotNone(log)
                self.assertEqual(log.details["status"], "SKIPPED")
                self.assertIn("GCAL_MODE", log.details["reason"])

    @pytest.mark.usefixtures("enable_auto_apply")
    def test_task_preview_only_does_not_apply(self):
        """
        P0.3 - Mesmo com mudanças detectadas, PREVIEW_ONLY=True bloqueia apply

        Cenário completo:
        - FEATURE_AUTO_APPLY_ENABLED=True (passa GUARDA 0)
        - GCAL_MODE='google' (passa GUARDA 1)
        - GCAL_CALENDAR_ID configurado (passa GUARDA 2)
        - PREVIEW_ONLY=True (bloqueia apply)
        - Preview detecta 10 mudanças (CREATE + UPDATE)

        Expectativa:
        - Task executa preview
        - Task detecta 10 mudanças
        - Task NÃO executa apply (bloqueado por PREVIEW_ONLY)
        - AuditLog registra "10 mudanças detectadas, mas PREVIEW_ONLY bloqueou"
        """
        with override_settings(
            FEATURE_FLAGS={"PREVIEW_ONLY": True, "GCAL_MODE": "google"},
            GCAL_CALENDAR_ID="test-calendar@example.com",
        ):
            with patch("apps.core.tasks.call_command") as mock_call:
                # Simular preview com MUITAS mudanças
                with patch("apps.core.tasks.StringIO") as mock_stringio:
                    mock_stdout = MagicMock()
                    mock_stdout.getvalue.return_value = (
                        '{"totals": {"CREATE": 7, "UPDATE": 3, "DELETE": 0}, "meta": {}}'
                    )
                    mock_stringio.return_value = mock_stdout

                    # Executar task
                    result = preview_then_apply_gcal()

                    # Validações
                    self.assertFalse(result["applied"])
                    self.assertIn("PREVIEW_ONLY", result["reason"])
                    self.assertIn("mudanças detectadas", result["reason"])

                    # Verificar que call_command foi chamado APENAS 1x (preview)
                    self.assertEqual(mock_call.call_count, 1)

                    # Verificar AuditLog
                    log = AuditLog.objects.filter(action="CELERY_GCAL_SYNC").first()
                    self.assertIsNotNone(log)
                    self.assertEqual(log.details["status"], "SUCCESS")
                    self.assertFalse(log.details["applied"])
                    self.assertEqual(log.details["total_changes"], 10)
                    self.assertIn("PREVIEW_ONLY bloqueou apply", log.details["reason"])

    @pytest.mark.usefixtures("enable_auto_apply")
    def test_task_logs_error_when_preview_fails(self):
        """
        P0.3 - Task DEVE logar erro quando preview retorna {"error": true}

        Cenário:
        - FEATURE_AUTO_APPLY_ENABLED=True (passa GUARDA 0)
        - GCAL_MODE='google' (passa GUARDA 1)
        - GCAL_CALENDAR_ID configurado (passa GUARDA 2)
        - Preview retorna {"error": true, "message": "Permission denied"}

        Expectativa:
        - Task retorna status="ERROR", phase="preview"
        - AuditLog registra status="ERROR"
        - call_command chamado APENAS 1x (preview, apply NÃO executa)
        """
        with override_settings(
            FEATURE_FLAGS={"GCAL_MODE": "google"},
            GCAL_CALENDAR_ID="test-calendar@example.com",
        ):
            with patch("apps.core.tasks.call_command") as mock_call:
                # Simular preview COM ERRO
                with patch("apps.core.tasks.StringIO") as mock_stringio:
                    mock_stdout = MagicMock()
                    mock_stdout.getvalue.return_value = (
                        '{"error": true, "message": "Permission denied", '
                        '"errors": ["Calendar API error"], "totals": {}}'
                    )
                    mock_stringio.return_value = mock_stdout

                    # Executar task
                    result = preview_then_apply_gcal()

                    # Validações
                    self.assertEqual(result["status"], "ERROR")
                    self.assertEqual(result["phase"], "preview")
                    self.assertTrue(result["error"])
                    self.assertIn("Permission denied", result["message"])

                    # Verificar que call_command foi chamado APENAS 1x (preview)
                    self.assertEqual(mock_call.call_count, 1)

                    # Verificar AuditLog com erro
                    log = AuditLog.objects.filter(action="CELERY_GCAL_SYNC").first()
                    self.assertIsNotNone(log)
                    self.assertEqual(log.details["status"], "ERROR")
                    self.assertEqual(log.details["phase"], "preview")
                    self.assertTrue(log.details["error"])

    @pytest.mark.usefixtures("enable_auto_apply")
    def test_task_logs_error_when_apply_fails(self):
        """
        P0.3 - Task DEVE logar erro quando apply retorna {"error": true}

        Cenário:
        - FEATURE_AUTO_APPLY_ENABLED=True (passa GUARDA 0)
        - GCAL_MODE='google' (passa GUARDA 1)
        - GCAL_CALENDAR_ID configurado (passa GUARDA 2)
        - PREVIEW_ONLY=False (permite apply)
        - Preview bem-sucedido (detecta mudanças)
        - Apply retorna {"error": true, "message": "Calendar API error"}

        Expectativa:
        - Task retorna status="ERROR", phase="apply"
        - AuditLog registra status="ERROR"
        - applied=False (não foi aplicado com sucesso)
        """
        with override_settings(
            FEATURE_FLAGS={"GCAL_MODE": "google"},
            GCAL_CALENDAR_ID="test-calendar@example.com",
        ):
            with patch("apps.core.tasks.call_command") as mock_call:
                with patch("apps.core.tasks.StringIO") as mock_stringio:
                    # Simular 2 chamadas: preview OK, apply COM ERRO
                    mock_stdout1 = MagicMock()
                    mock_stdout1.getvalue.return_value = (
                        '{"error": false, "totals": {"CREATE": 5}, "meta": {}}'
                    )

                    mock_stdout2 = MagicMock()
                    mock_stdout2.getvalue.return_value = (
                        '{"error": true, "message": "Calendar API error", '
                        '"errors": ["Quota exceeded"], "totals": {}}'
                    )

                    mock_stringio.side_effect = [mock_stdout1, mock_stdout2]

                    # Executar task
                    result = preview_then_apply_gcal()

                    # Validações
                    self.assertEqual(result["status"], "ERROR")
                    self.assertEqual(result["phase"], "apply")
                    self.assertTrue(result["error"])
                    self.assertFalse(result["applied"])
                    self.assertIn("Calendar API error", result["message"])

                    # Verificar que call_command foi chamado 2x (preview + apply)
                    self.assertEqual(mock_call.call_count, 2)

                    # Verificar AuditLog com erro
                    log = AuditLog.objects.filter(action="CELERY_GCAL_SYNC").first()
                    self.assertIsNotNone(log)
                    self.assertEqual(log.details["status"], "ERROR")
                    self.assertEqual(log.details["phase"], "apply")
                    self.assertTrue(log.details["error"])
