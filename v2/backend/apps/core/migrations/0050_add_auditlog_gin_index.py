"""
Issue #248: Add GIN index for JSONField in AuditLog.

This index optimizes queries that filter on details->solicitacao_id,
which is used in SolicitacaoSerializer to fetch GCal sync logs.

Uses CONCURRENTLY to avoid locking the table during index creation.
"""

from django.db import migrations


class Migration(migrations.Migration):
    """Add GIN index for AuditLog.details JSONField."""

    atomic = False  # Required for CREATE INDEX CONCURRENTLY

    dependencies = [
        ("core", "0049_add_local_to_solicitacao"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS
            idx_auditlog_details_gin
            ON core_auditlog USING GIN (details);
            """,
            reverse_sql="DROP INDEX IF EXISTS idx_auditlog_details_gin;",
        ),
    ]
