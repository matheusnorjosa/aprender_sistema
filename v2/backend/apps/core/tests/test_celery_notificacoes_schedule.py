"""
Tests for celery beat schedule entries related to action notifications (#871).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from config.celery import app


def test_celery_schedule_contains_daily_action_notifications_task():
    schedule = app.conf.beat_schedule
    assert "acoes-notificacoes-diarias" in schedule
    entry = schedule["acoes-notificacoes-diarias"]
    assert entry["task"] == "apps.core.tasks.processar_notificacoes_acoes_diarias"


def test_celery_schedule_keeps_backup_tasks():
    schedule = app.conf.beat_schedule
    assert "daily-database-backup" in schedule
    assert "weekly-backup-health-check" in schedule
