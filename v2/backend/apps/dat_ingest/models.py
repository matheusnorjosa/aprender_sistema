"""
Data Ingestion models
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false

from __future__ import annotations

from django.db import models


class ImportLog(models.Model):
    """Log de importações ETL"""

    source = models.CharField(max_length=100, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("running", "Running"),
            ("success", "Success"),
            ("failed", "Failed"),
        ],
        default="running",
    )
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    records_processed = models.IntegerField(default=0)
    records_created = models.IntegerField(default=0)
    records_updated = models.IntegerField(default=0)
    records_failed = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = "dat_ingest_import_log"
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"{self.source} - {self.status} ({self.started_at})"
