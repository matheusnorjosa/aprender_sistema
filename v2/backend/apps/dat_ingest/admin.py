from __future__ import annotations

from django.contrib import admin

from .models import ImportLog


@admin.register(ImportLog)
class ImportLogAdmin(admin.ModelAdmin[ImportLog]):
    list_display = (
        "file",
        "ok",
        "started_at",
        "finished_at",
        "rows_processed",
        "rows_success",
        "rows_failed",
    )
    list_filter = ("ok", "started_at")
    search_fields = ("file", "error_message")
    readonly_fields = ("started_at", "finished_at", "sha256", "duration")
