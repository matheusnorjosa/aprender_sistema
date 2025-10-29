import csv
import logging
from pathlib import Path
from django.contrib import admin
from django.conf import settings
from django.http import HttpResponse

from .models import (
    AcaoControle,
    AcaoDAT,
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

    def lookups(self, request, model_admin):
        return (
            ("missing", "Ausente"),
            ("filled", "Preenchido"),
        )

    def queryset(self, request, queryset):
        if self.value() == "missing":
            return queryset.filter(cpf__isnull=True) | queryset.filter(cpf="")
        if self.value() == "filled":
            return queryset.exclude(cpf__isnull=True).exclude(cpf="")
        return queryset


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "cpf", "cargo", "is_active")
    search_fields = ("username", "email", "cpf", "first_name", "last_name")
    list_filter = ("is_active", "is_staff", "cargo", CPFFilter)
    actions = ["export_usuarios_sem_cpf"]

    @admin.action(description="Exportar usuários sem CPF (CSV)")
    def export_usuarios_sem_cpf(self, request, queryset):
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


@admin.register(Municipio)
class MunicipioAdmin(admin.ModelAdmin):
    list_display = ("nome", "uf", "ativo")
    search_fields = ("nome", "uf")
    list_filter = ("uf", "ativo")


@admin.register(Projeto)
class ProjetoAdmin(admin.ModelAdmin):
    list_display = ("nome", "ativo")
    search_fields = ("nome", "descricao")
    list_filter = ("ativo",)


@admin.register(TipoEvento)
class TipoEventoAdmin(admin.ModelAdmin):
    list_display = ("nome", "cor", "descricao")
    search_fields = ("nome", "descricao")
    list_filter = ()


@admin.register(AvailabilityBlock)
class AvailabilityBlockAdmin(admin.ModelAdmin):
    list_display = ("usuario", "tipo", "inicio", "fim", "status", "created_at")
    search_fields = ("usuario__username", "usuario__email", "motivo")
    list_filter = ("tipo", "status", "created_at")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "inicio"


@admin.register(Solicitacao)
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


@admin.register(Participation)
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


@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ("codigo", "municipio", "projeto", "quantidade", "data", "uso")
    list_filter = ("projeto", "data")
    search_fields = ("codigo", "municipio__nome", "projeto__nome", "uso")
    autocomplete_fields = ("municipio", "projeto")
    list_select_related = ("municipio", "projeto")
    date_hierarchy = "data"


@admin.register(Deslocamento)
class DeslocamentoAdmin(admin.ModelAdmin):
    list_display = ("usuario", "origem", "destino", "start_date", "end_date")
    list_filter = ("usuario", "start_date")
    search_fields = ("origem", "destino", "usuario__username")
    autocomplete_fields = ("usuario",)
    list_select_related = ("usuario",)
    date_hierarchy = "start_date"


@admin.register(AcaoControle)
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


@admin.register(AcaoDAT)
class AcaoDATAdmin(admin.ModelAdmin):
    list_display = ("municipio", "projeto", "tipo_acao", "responsavel", "data_registro")
    list_filter = ("projeto", "tipo_acao")
    search_fields = ("municipio__nome", "projeto__nome", "tipo_acao", "responsavel__email")
    autocomplete_fields = ("municipio", "projeto", "responsavel")
    list_select_related = ("municipio", "projeto", "responsavel")
    date_hierarchy = "data_registro"
