from django.contrib import admin

from .models import (
    AvailabilityBlock,
    Compra,
    Municipio,
    Participation,
    Projeto,
    Solicitacao,
    TipoEvento,
    Usuario,
)


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "cpf", "cargo", "is_active")
    search_fields = ("username", "email", "cpf", "first_name", "last_name")
    list_filter = ("is_active", "is_staff", "cargo")


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
