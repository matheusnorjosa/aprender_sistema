"""
Testes para FEATURE_AUTO_APPLY_ENABLED (Fase 3 - Governança GCal).

Cenários:
- Com FEATURE_AUTO_APPLY_ENABLED=False → task retorna status="SKIPPED"
- Com FEATURE_AUTO_APPLY_ENABLED=True → task executa normalmente (mock call_command)
- AuditLog registrado em ambos os casos
"""

import pytest
from unittest.mock import patch, MagicMock
from django.test import override_settings

from apps.core.tasks import preview_then_apply_gcal
from apps.core.models import AuditLog


@pytest.mark.django_db
class TestCeleryAutoApplyDisabled:
    """Testes da guarda FEATURE_AUTO_APPLY_ENABLED."""

    @override_settings(FEATURE_AUTO_APPLY_ENABLED=False)
    def test_auto_apply_disabled_returns_skipped(self):
        """
        Cenário: FEATURE_AUTO_APPLY_ENABLED=False
        Espera: Task retorna status="SKIPPED" sem executar sync
        """
        result = preview_then_apply_gcal()

        assert result["status"] == "SKIPPED"
        assert "FEATURE_AUTO_APPLY_ENABLED=False" in result["reason"]
        assert "governança via /pre-agenda" in result["reason"]

        # Verificar AuditLog registrado
        audit_log = AuditLog.objects.filter(
            action="CELERY_GCAL_SYNC"
        ).order_by("-created_at").first()

        assert audit_log is not None
        assert audit_log.details["status"] == "SKIPPED"
        assert "FEATURE_AUTO_APPLY_ENABLED=False" in audit_log.details["reason"]

    @override_settings(FEATURE_AUTO_APPLY_ENABLED=False)
    @patch("apps.core.tasks.management.call_command")
    def test_auto_apply_disabled_does_not_call_command(self, mock_call_command):
        """
        Cenário: FEATURE_AUTO_APPLY_ENABLED=False
        Espera: call_command NÃO é chamado
        """
        result = preview_then_apply_gcal()

        assert result["status"] == "SKIPPED"
        # call_command NÃO deve ser chamado
        mock_call_command.assert_not_called()

    @override_settings(
        FEATURE_AUTO_APPLY_ENABLED=True,
        GCAL_CALENDAR_ID="test-calendar-id"
    )
    @patch("apps.core.tasks.feature_flags.get")
    @patch("apps.core.tasks.management.call_command")
    def test_auto_apply_enabled_allows_execution(
        self,
        mock_call_command,
        mock_feature_flags_get
    ):
        """
        Cenário: FEATURE_AUTO_APPLY_ENABLED=True + GCAL_MODE=google
        Espera: Task executa normalmente (chama call_command)
        """
        # Mock feature_flags para retornar GCAL_MODE=google
        def feature_flags_side_effect(key, default=None):
            if key == "GCAL_MODE":
                return "google"
            return default

        mock_feature_flags_get.side_effect = feature_flags_side_effect

        # Mock call_command para simular preview dry-run
        def call_command_side_effect(command_name, *args, **kwargs):
            if kwargs.get("dry_run"):
                # Retorna resultado de preview
                return {
                    "status": "SUCCESS",
                    "meta": {"dry_run": True},
                    "totals": {"total": 0}  # Sem mudanças
                }
            return {"status": "SUCCESS"}

        mock_call_command.side_effect = call_command_side_effect

        result = preview_then_apply_gcal()

        # Task deve executar (chamar call_command)
        assert mock_call_command.call_count >= 1
        # Primeira chamada deve ser dry-run (preview)
        first_call_kwargs = mock_call_command.call_args_list[0][1]
        assert first_call_kwargs.get("dry_run") is True

        # Resultado deve ser SUCCESS (noop, pois total=0)
        assert result["status"] == "SUCCESS"
