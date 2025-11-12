from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any

from django.contrib import admin
from django.conf import settings
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse

# Fase 1 - Plano DAT/GCal: Admin restrito a superusers
from .admin_site import admin_site

from .models import (
    AcaoControle,
    AcaoDAT,
    AuditLog,
    AvailabilityBlock,
    Compra,
    Deslocamento,
    Municipio,
    Participation,
    Projeto,
    Solicitacao,
    TipoEvento,
    Usuario,
)


class CPFFilter(admin.SimpleListFilter):
    """Filtro para CPF ausente/preenchido."""
    title = "CPF"
    parameter_name = "cpf_status"

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[Any, str]]:
        return [
            ("missing", "Ausente"),
            ("filled", "Preenchido"),
        ]

    def queryset(self, request: HttpRequest, queryset: QuerySet[Any]) -> QuerySet[Any] | None:
        if self.value() == "missing":
            return queryset.filter(cpf__isnull=True) | queryset.filter(cpf="")
        if self.value() == "filled":
            return queryset.exclude(cpf__isnull=True).exclude(cpf="")
        return queryset


class UsuarioAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "cpf", "cargo", "is_active")
    search_fields = ("username", "email", "cpf", "first_name", "last_name")
    list_filter = ("is_active", "is_staff", "cargo", CPFFilter)
    actions = ["export_usuarios_sem_cpf"]

    @admin.action(description="Exportar usuários sem CPF (CSV)")
    def export_usuarios_sem_cpf(self, request: HttpRequest, queryset: QuerySet[Usuario]) -> HttpResponse:
        """Exporta usuários sem CPF para CSV."""
        # Filtrar apenas usuários sem CPF no queryset selecionado
        usuarios_sem_cpf = queryset.filter(cpf__isnull=True) | queryset.filter(cpf="")

        # Gerar CSV em memória
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="usuarios_sem_cpf.csv"'

        writer = csv.writer(response)
        writer.writerow(["Username", "Email", "Nome Completo", "CPF", "Cargo", "Ativo"])

        for user in usuarios_sem_cpf:
            nome_completo = f"{user.first_name} {user.last_name}".strip()
            writer.writerow([
                user.username,
                user.email,
                nome_completo,
                user.cpf or "",
                user.cargo or "",
                "Sim" if user.is_active else "Não",
            ])

        # Também salvar em out_etl para auditoria
        try:
            out_dir = Path(settings.ETL_OUTPUT_DIR)
            out_dir.mkdir(parents=True, exist_ok=True)
            csv_path = out_dir / "usuarios_sem_cpf.csv"

            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer_file = csv.writer(f)
                writer_file.writerow(["Username", "Email", "Nome Completo", "CPF", "Cargo", "Ativo"])
                for user in usuarios_sem_cpf:
                    nome_completo = f"{user.first_name} {user.last_name}".strip()
                    writer_file.writerow([
                        user.username,
                        user.email,
                        nome_completo,
                        user.cpf or "",
                        user.cargo or "",
                        "Sim" if user.is_active else "Não",
                    ])
        except Exception as e:
            # Se falhar ao salvar em out_etl, apenas retornar o CSV via HTTP
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to save audit file to {settings.ETL_OUTPUT_DIR}: {e}")

        return response


class MunicipioAdmin(admin.ModelAdmin):
    list_display = ("nome", "uf", "ativo")
    search_fields = ("nome", "uf")
    list_filter = ("uf", "ativo")


class ProjetoAdmin(admin.ModelAdmin):
    list_display = ("nome", "ativo")
    search_fields = ("nome", "descricao")
    list_filter = ("ativo",)


class TipoEventoAdmin(admin.ModelAdmin):
    list_display = ("nome", "cor", "descricao")
    search_fields = ("nome", "descricao")
    list_filter = ()


class AvailabilityBlockAdmin(admin.ModelAdmin):
    list_display = ("usuario", "tipo", "inicio", "fim", "status", "created_at")
    search_fields = ("usuario__username", "usuario__email", "motivo")
    list_filter = ("tipo", "status", "created_at")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "inicio"


class SolicitacaoAdmin(admin.ModelAdmin):
    list_display = (
        "usuario",
        "tipo_evento",
        "municipio",
        "inicio",
        "fim",
        "status",
        "created_at",
    )
    search_fields = (
        "usuario__username",
        "usuario__email",
        "tipo_evento__nome",
        "observacoes",
    )
    list_filter = ("status", "tipo_evento", "created_at")
    readonly_fields = ("created_at", "updated_at", "external_event_id")
    date_hierarchy = "inicio"


class ParticipationAdmin(admin.ModelAdmin):
    list_display = ("solicitacao", "usuario", "role", "ch_horas", "created_at")
    list_filter = ("role",)
    search_fields = (
        "usuario__email",
        "usuario__first_name",
        "usuario__last_name",
        "guest_email",
        "solicitacao__id",
    )
    autocomplete_fields = ("usuario", "solicitacao")
    list_select_related = ("solicitacao", "usuario")


class CompraAdmin(admin.ModelAdmin):
    list_display = ("codigo", "municipio", "projeto", "quantidade", "data", "uso")
    list_filter = ("projeto", "data")
    search_fields = ("codigo", "municipio__nome", "projeto__nome", "uso")
    autocomplete_fields = ("municipio", "projeto")
    list_select_related = ("municipio", "projeto")
    date_hierarchy = "data"


class DeslocamentoAdmin(admin.ModelAdmin):
    list_display = ("usuario", "origem", "destino", "start_date", "end_date")
    list_filter = ("usuario", "start_date")
    search_fields = ("origem", "destino", "usuario__username")
    autocomplete_fields = ("usuario",)
    list_select_related = ("usuario",)
    date_hierarchy = "start_date"


class AcaoControleAdmin(admin.ModelAdmin):
    list_display = (
        "municipio",
        "projeto",
        "coordenador",
        "data_entrega",
        "data_carta",
        "contato_inicial",
        "data_reuniao",
    )
    list_filter = ("projeto",)
    search_fields = (
        "municipio__nome",
        "projeto__nome",
        "coordenador__email",
        "coordenador__first_name",
        "coordenador__last_name",
    )
    autocomplete_fields = ("municipio", "projeto", "coordenador")
    list_select_related = ("municipio", "projeto", "coordenador")
    date_hierarchy = "data_reuniao"


class AcaoDATAdmin(admin.ModelAdmin):
    list_display = ("municipio", "projeto", "tipo_acao", "responsavel", "data_registro")
    list_filter = ("projeto", "tipo_acao")
    search_fields = ("municipio__nome", "projeto__nome", "tipo_acao", "responsavel__email")
    autocomplete_fields = ("municipio", "projeto", "responsavel")
    list_select_related = ("municipio", "projeto", "responsavel")
    date_hierarchy = "data_registro"


class AuditLogAdmin(admin.ModelAdmin):
    """
    AuditLog Admin - Somente Leitura

    Registro de auditoria para rastreamento de ações críticas (RF07).
    Não permite edição/exclusão via admin.
    """
    list_display = ("id", "usuario", "action", "model_name", "created_at")
    list_filter = ("action", "model_name", "created_at")
    search_fields = ("usuario__username", "usuario__email", "action", "model_name")
    readonly_fields = ("usuario", "action", "model_name", "details", "created_at")
    date_hierarchy = "created_at"
    list_select_related = ("usuario",)

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Desabilita adição manual de logs de auditoria."""
        return False

    def has_change_permission(self, request: HttpRequest, obj: AuditLog | None = None) -> bool:
        """Desabilita edição de logs de auditoria."""
        return False

    def has_delete_permission(self, request: HttpRequest, obj: AuditLog | None = None) -> bool:
        """Desabilita exclusão de logs de auditoria."""
        return False


# Registro funcional (evita problemas de importação circular com decoradores)
admin_site.register(Usuario, UsuarioAdmin)
admin_site.register(Municipio, MunicipioAdmin)
admin_site.register(Projeto, ProjetoAdmin)
admin_site.register(TipoEvento, TipoEventoAdmin)
admin_site.register(AvailabilityBlock, AvailabilityBlockAdmin)
admin_site.register(Solicitacao, SolicitacaoAdmin)
admin_site.register(Participation, ParticipationAdmin)
admin_site.register(Compra, CompraAdmin)
admin_site.register(Deslocamento, DeslocamentoAdmin)
admin_site.register(AcaoControle, AcaoControleAdmin)
admin_site.register(AcaoDAT, AcaoDATAdmin)
admin_site.register(AuditLog, AuditLogAdmin)
