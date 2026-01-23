from __future__ import annotations

from django.apps import AppConfig


class DatIngestConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.dat_ingest"
    verbose_name = "Data Ingestion"
