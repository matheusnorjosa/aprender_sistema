"""
Testes para FEATURE_AUTO_APPLY_ENABLED (Fase 3 - Governança GCal).

Cenários:
- Com FEATURE_AUTO_APPLY_ENABLED=False → task retorna status="SKIPPED"
- Com FEATURE_AUTO_APPLY_ENABLED=True → task executa normalmente (mock call_command)
- AuditLog registrado em ambos os casos
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false

from __future__ import annotations
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
    @patch("django.core.management.call_command")
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
        GCAL_CALENDAR_ID="test-calendar-id",
        FEATURE_FLAGS={"GCAL_MODE": "google"}
    )
    @patch("apps.core.tasks.call_command")
    def test_auto_apply_enabled_allows_execution(
        self,
        mock_call_command
    ):
        """
        Cenário: FEATURE_AUTO_APPLY_ENABLED=True + GCAL_MODE=google
        Espera: Task executa normalmente (chama call_command)
        """
        import json

        # Mock call_command para escrever no stdout (como faz o comando real)
        def call_command_side_effect(command_name, *args, **kwargs):
            stdout = kwargs.get("stdout")
            if stdout and kwargs.get("dry_run"):
                # Simula preview dry-run com total=0 (sem mudanças)
                preview_result = {
                    "status": "SUCCESS",
                    "meta": {"dry_run": True},
                    "totals": {"total": 0, "CREATE": 0, "UPDATE": 0, "DELETE": 0, "ADOPT": 0}
                }
                stdout.write(json.dumps(preview_result))
            elif stdout and not kwargs.get("dry_run"):
                # Simula apply (não será chamado pois preview retorna total=0)
                apply_result = {
                    "status": "SUCCESS",
                    "meta": {"dry_run": False},
                    "totals": {"total": 0}
                }
                stdout.write(json.dumps(apply_result))
            return None

        mock_call_command.side_effect = call_command_side_effect

        result = preview_then_apply_gcal()

        # Task deve executar (chamar call_command para preview)
        assert mock_call_command.call_count >= 1, f"Expected call_command to be called, but was called {mock_call_command.call_count} times"

        # Primeira chamada deve ser dry-run (preview)
        first_call_args = mock_call_command.call_args_list[0][0]  # Positional args
        assert "--dry-run" in first_call_args, f"Expected '--dry-run' in args, got {first_call_args}"
        assert "--json" in first_call_args, f"Expected '--json' in args, got {first_call_args}"

        # Resultado deve ser NOOP (pois total=0, sem mudanças)
        assert result["status"] == "NOOP", f"Expected status NOOP, got {result.get('status')}"
        assert result.get("applied") is False, "Expected applied=False when no changes"
        assert "No changes detected" in result.get("reason", ""), "Expected reason to mention no changes"
