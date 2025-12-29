"""
Issue #248: Add GIN index for JSONField in AuditLog.

This index optimizes queries that filter on details->solicitacao_id,
which is used in SolicitacaoSerializer to fetch GCal sync logs.

Uses AddIndexConcurrently with GinIndex for safe index creation.
"""

from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations


class Migration(migrations.Migration):
    """Add GIN index for AuditLog.details JSONField."""

    atomic = False  # Required for CONCURRENTLY operations

    dependencies = [
        ("core", "0049_add_local_to_solicitacao"),
    ]

    operations = [
        AddIndexConcurrently(
            model_name="auditlog",
            index=GinIndex(
                fields=["details"],
                name="idx_auditlog_details_gin",
            ),
        ),
    ]
