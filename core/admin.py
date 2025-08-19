from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    Usuario, Projeto, Municipio, TipoEvento,
    Formador, Solicitacao, FormadoresSolicitacao,
    Aprovacao, EventoGoogleCalendar,
    DisponibilidadeFormadores, LogAuditoria, Deslocamento
)

# Customizar o admin do Usuario para incluir o campo 'papel'
@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'papel', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('papel', 'is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('username',)
    
    # Adicionar o campo 'papel' aos fieldsets
    fieldsets = UserAdmin.fieldsets + (
        ('Perfil do Sistema', {'fields': ('papel',)}),
    )
    
    # Adicionar o campo 'papel' ao formulário de criação
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Perfil do Sistema', {'fields': ('papel',)}),
    )

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

@admin.register(Formador)
class FormadorAdmin(admin.ModelAdmin):
    list_display = ("nome", "email", "area_atuacao", "ativo")
    list_filter = ("ativo",)
    search_fields = ("nome", "email", "area_atuacao")

class FormadoresSolicitacaoInline(admin.TabularInline):
    model = FormadoresSolicitacao
    extra = 0

@admin.register(Solicitacao)
class SolicitacaoAdmin(admin.ModelAdmin):
    list_display = ("titulo_evento", "projeto", "municipio", "tipo_evento",
                    "data_inicio", "data_fim", "status")
    list_filter = ("status", "projeto", "tipo_evento", "municipio")
    search_fields = ("titulo_evento", "observacoes")
    date_hierarchy = "data_inicio"
    inlines = [FormadoresSolicitacaoInline]

@admin.register(Aprovacao)
class AprovacaoAdmin(admin.ModelAdmin):
    list_display = ("solicitacao", "usuario_aprovador", "status_decisao", "data_aprovacao")
    list_filter = ("status_decisao", "data_aprovacao")
    search_fields = ("solicitacao__titulo_evento", "justificativa")

@admin.register(EventoGoogleCalendar)
class EventoGoogleCalendarAdmin(admin.ModelAdmin):
    list_display = ("solicitacao", "provider_event_id", "status_sincronizacao", "data_criacao")
    list_filter = ("status_sincronizacao",)
    search_fields = ("provider_event_id", "html_link", "meet_link")

@admin.register(DisponibilidadeFormadores)
class DisponibilidadeFormadoresAdmin(admin.ModelAdmin):
    list_display = ("formador", "data_bloqueio", "hora_inicio", "hora_fim", "tipo_bloqueio")
    list_filter = ("tipo_bloqueio", "data_bloqueio")
    search_fields = ("formador__nome", "motivo")

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
