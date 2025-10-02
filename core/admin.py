from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    Aprovacao,
    AprovacaoHistorico,
    Deslocamento,
    DisponibilidadeFormadores,
    EventoGoogleCalendar,
    FormadoresSolicitacao,
    LogAuditoria,
    MarcadorPlanilha,
    Municipio,
    Participante,
    Projeto,
    Solicitacao,
    TipoEvento,
    Usuario,
    VinculoUsuarioSetor,
)


# Customizar o admin do Usuario para mostrar grupos (roles)
@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "get_roles",
        # "formador_ativo",
        "cargo",
        "is_staff",
        "is_active",
        "date_joined",
    )
    list_filter = (
        "groups",
        # "formador_ativo",
        "cargo",
        "area_atuacao",
        "is_staff",
        "is_superuser",
        "is_active",
        "date_joined"
    )
    search_fields = ("username", "first_name", "last_name", "email", "cpf")
    ordering = ("username",)

    def get_roles(self, obj):
        """Display user's roles (groups) in list view"""
        return ", ".join([group.name for group in obj.groups.all()]) or "Nenhum"

    get_roles.short_description = "Papéis"

    # Expandir fieldsets para incluir campos de formador
    fieldsets = UserAdmin.fieldsets + (
        ('Informações Pessoais', {
            'fields': ('cpf', 'telefone', 'municipio')
        }),
        ('Estrutura Organizacional', {
            'fields': ('setor', 'cargo')
        }),
        ('Dados de Formador', {
            'fields': ('area_especializacao', 'anos_experiencia', 'observacoes_formador'),
            'classes': ('collapse',)
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets


@admin.register(Projeto)
class ProjetoAdmin(admin.ModelAdmin):
    list_display = ("nome", "ativo")
    list_filter = ("ativo",)
    search_fields = ("nome",)


@admin.register(Municipio)
class MunicipioAdmin(admin.ModelAdmin):
    list_display = ("nome", "uf", "ativo")
    list_filter = ("uf", "ativo")
    search_fields = ("nome", "uf")


@admin.register(TipoEvento)
class TipoEventoAdmin(admin.ModelAdmin):
    list_display = ("nome", "online", "ativo")
    list_filter = ("online", "ativo")
    search_fields = ("nome",)


class FormadoresSolicitacaoInline(admin.TabularInline):
    model = FormadoresSolicitacao
    extra = 0


@admin.register(Solicitacao)
class SolicitacaoAdmin(admin.ModelAdmin):
    list_display = (
        "titulo_evento",
        "projeto",
        "municipio",
        "tipo_evento",
        "data_inicio",
        "data_fim",
        "status",
    )
    list_filter = ("status", "projeto", "tipo_evento", "municipio")
    search_fields = ("titulo_evento", "observacoes")
    date_hierarchy = "data_inicio"
    inlines = [FormadoresSolicitacaoInline]


@admin.register(Aprovacao)
class AprovacaoAdmin(admin.ModelAdmin):
    list_display = (
        "solicitacao",
        "usuario_aprovador",
        "status_decisao",
        "data_aprovacao",
    )
    list_filter = ("status_decisao", "data_aprovacao")
    search_fields = ("solicitacao__titulo_evento", "justificativa")


@admin.register(EventoGoogleCalendar)
class EventoGoogleCalendarAdmin(admin.ModelAdmin):
    list_display = (
        "solicitacao",
        "provider_event_id",
        "status_sincronizacao",
        "tentativas",
        "request_id_short",
        "data_criacao",
    )
    list_filter = ("status_sincronizacao", "tentativas")
    search_fields = ("provider_event_id", "html_link", "meet_link", "request_id", "hash_payload")
    readonly_fields = ("data_criacao", "ultima_tentativa", "tentativas")

    def request_id_short(self, obj):
        """Display first 12 chars of request_id"""
        return f"{obj.request_id[:12]}..." if obj.request_id else ""
    request_id_short.short_description = "Request ID"


@admin.register(DisponibilidadeFormadores)
class DisponibilidadeFormadoresAdmin(admin.ModelAdmin):
    list_display = (
        "usuario",
        "data_bloqueio",
        "hora_inicio",
        "hora_fim",
        "tipo_bloqueio",
    )
    list_filter = ("tipo_bloqueio", "data_bloqueio")
    search_fields = ("usuario__first_name", "usuario__last_name", "usuario__username", "motivo")


@admin.register(LogAuditoria)
class LogAuditoriaAdmin(admin.ModelAdmin):
    list_display = ("data_hora", "usuario", "acao", "entidade_afetada_id")
    list_filter = ("data_hora",)
    search_fields = ("acao", "detalhes")


@admin.register(Deslocamento)
class DeslocamentoAdmin(admin.ModelAdmin):
    list_display = ("data", "origem", "destino")
    list_filter = ("data",)
    search_fields = ("origem", "destino", "formadores__nome")
    filter_horizontal = ("formadores",)


# ====================================
# NOVOS MODELOS CANÔNICOS
# ====================================

@admin.register(VinculoUsuarioSetor)
class VinculoUsuarioSetorAdmin(admin.ModelAdmin):
    list_display = ("usuario", "setor", "papel", "ativo", "created_at")
    search_fields = ("usuario__username", "usuario__first_name", "usuario__last_name", "usuario__cpf", "setor__nome")
    list_filter = ("papel", "setor", "ativo")
    date_hierarchy = "created_at"


@admin.register(Participante)
class ParticipanteAdmin(admin.ModelAdmin):
    list_display = ("solicitacao", "usuario", "papel", "created_at")
    search_fields = ("solicitacao__titulo_evento", "usuario__username", "usuario__first_name", "usuario__last_name", "usuario__cpf")
    list_filter = ("papel",)
    date_hierarchy = "created_at"


@admin.register(MarcadorPlanilha)
class MarcadorPlanilhaAdmin(admin.ModelAdmin):
    list_display = ("origem_aba", "linha", "external_hash_short", "cancelado_flag", "created_at")
    search_fields = ("external_hash", "origem_aba", "linha", "gid")
    list_filter = ("origem_aba", "cancelado_flag", "created_at")
    date_hierarchy = "created_at"
    readonly_fields = ("external_hash", "created_at", "updated_at")

    def external_hash_short(self, obj):
        """Display first 12 chars of hash"""
        return f"{obj.external_hash[:12]}..." if obj.external_hash else ""
    external_hash_short.short_description = "Hash (resumido)"


@admin.register(AprovacaoHistorico)
class AprovacaoHistoricoAdmin(admin.ModelAdmin):
    list_display = ("solicitacao", "usuario", "status_anterior", "status_novo", "decisao", "origem", "data_decisao")
    list_filter = ("decisao", "origem", "status_anterior", "status_novo", "data_decisao")
    search_fields = ("solicitacao__titulo_evento", "usuario__username", "justificativa")
    date_hierarchy = "data_decisao"
    readonly_fields = ("data_decisao",)
