from django.contrib import admin
from .models import ImportLog


@admin.register(ImportLog)
class ImportLogAdmin(admin.ModelAdmin):
    list_display = (
        "source",
        "status",
        "started_at",
        "finished_at",
        "records_processed",
        "records_created",
    )
    list_filter = ("status", "source")
    search_fields = ("source", "error_message")
    readonly_fields = ("started_at", "finished_at")
