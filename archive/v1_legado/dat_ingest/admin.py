"""
Django Admin para modelos de Staging (dat_ingest)

App: dat_ingest
Stack: Python 3.13 | Django 5.2 | PostgreSQL 15

Registra todos os modelos de staging com list_display e search_fields úteis.
"""

from django.contrib import admin

from .models import (
    StgControleUnificado,
    StgDispBloqueio,
    StgDispDeslocamento,
    StgEvento,
    StgEventoPessoa,
)


@admin.register(StgEvento)
class StgEventoAdmin(admin.ModelAdmin):
    """Admin para StgEvento (eventos da agenda)"""

    list_display = (
        "external_hash_short",
        "municipio",
        "data",
        "hora_inicio",
        "hora_fim",
        "projeto",
        "tipo",
        "status_temporal",
        "updated_at",
    )

    list_filter = (
        "status_temporal",
        "fluxo",
        "aprovado_futuro",
        "data",
        "projeto",
    )

    search_fields = (
        "external_hash",
        "municipio",
        "projeto",
        "tipo",
        "coordenador",
        "solicitante",
    )

    readonly_fields = (
        "external_hash",
        "created_at",
        "updated_at",
    )

    date_hierarchy = "data"

    fieldsets = (
        (
            "Identificação",
            {
                "fields": ("external_hash", "planilha", "aba", "fluxo"),
            },
        ),
        (
            "Aprovação",
            {
                "fields": ("aprovacao", "aprovado_futuro", "criado_na_agenda"),
            },
        ),
        (
            "Localização e Tempo",
            {
                "fields": ("municipio", "data", "hora_inicio", "hora_fim", "encontro"),
            },
        ),
        (
            "Evento",
            {
                "fields": ("tipo", "projeto", "segmento"),
            },
        ),
        (
            "Participantes",
            {
                "fields": (
                    "coordenador",
                    "coord_acompanha",
                    "formadores",
                    "convidados",
                    "solicitante",
                ),
            },
        ),
        (
            "Status",
            {
                "fields": ("status_temporal", "tempo_alerta", "cancelado_info"),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )

    def external_hash_short(self, obj):
        """Exibe os primeiros 8 caracteres do hash"""
        return obj.external_hash[:8] if obj.external_hash else "-"

    external_hash_short.short_description = "Hash"


@admin.register(StgEventoPessoa)
class StgEventoPessoaAdmin(admin.ModelAdmin):
    """Admin para StgEventoPessoa (pessoas por evento)"""

    list_display = (
        "row_hash_short",
        "event_hash_short",
        "role",
        "name",
        "matched",
        "email",
        "cargo",
        "updated_at",
    )

    list_filter = (
        "role",
        "matched",
        "cargo",
    )

    search_fields = (
        "row_hash",
        "name",
        "email",
        "cargo",
        "gerencia",
    )

    readonly_fields = (
        "row_hash",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Identificação",
            {
                "fields": ("row_hash", "event_external_hash"),
            },
        ),
        (
            "Pessoa",
            {
                "fields": ("role", "name", "matched", "email"),
            },
        ),
        (
            "Organização",
            {
                "fields": ("cargo", "gerencia"),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )

    def row_hash_short(self, obj):
        """Exibe os primeiros 8 caracteres do hash"""
        return obj.row_hash[:8] if obj.row_hash else "-"

    row_hash_short.short_description = "Row Hash"

    def event_hash_short(self, obj):
        """Exibe os primeiros 8 caracteres do hash do evento"""
        return obj.event_external_hash_id[:8] if obj.event_external_hash_id else "-"

    event_hash_short.short_description = "Event Hash"


@admin.register(StgDispBloqueio)
class StgDispBloqueioAdmin(admin.ModelAdmin):
    """Admin para StgDispBloqueio (bloqueios de disponibilidade)"""

    list_display = (
        "row_hash_short",
        "responsavel",
        "data_inicial",
        "data_final",
        "tipo",
        "updated_at",
    )

    list_filter = (
        "tipo",
        "data_inicial",
        "data_final",
    )

    search_fields = (
        "row_hash",
        "responsavel",
        "tipo",
    )

    readonly_fields = (
        "row_hash",
        "created_at",
        "updated_at",
    )

    date_hierarchy = "data_inicial"

    fieldsets = (
        (
            "Identificação",
            {
                "fields": ("row_hash",),
            },
        ),
        (
            "Bloqueio",
            {
                "fields": ("responsavel", "data_inicial", "data_final", "tipo"),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )

    def row_hash_short(self, obj):
        """Exibe os primeiros 8 caracteres do hash"""
        return obj.row_hash[:8] if obj.row_hash else "-"

    row_hash_short.short_description = "Hash"


@admin.register(StgDispDeslocamento)
class StgDispDeslocamentoAdmin(admin.ModelAdmin):
    """Admin para StgDispDeslocamento (deslocamentos)"""

    list_display = (
        "row_hash_short",
        "responsavel",
        "origem",
        "destino",
        "data",
        "updated_at",
    )

    list_filter = (
        "data",
        "origem",
        "destino",
    )

    search_fields = (
        "row_hash",
        "responsavel",
        "origem",
        "destino",
    )

    readonly_fields = (
        "row_hash",
        "created_at",
        "updated_at",
    )

    date_hierarchy = "data"

    fieldsets = (
        (
            "Identificação",
            {
                "fields": ("row_hash",),
            },
        ),
        (
            "Deslocamento",
            {
                "fields": ("responsavel", "origem", "destino", "data"),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )

    def row_hash_short(self, obj):
        """Exibe os primeiros 8 caracteres do hash"""
        return obj.row_hash[:8] if obj.row_hash else "-"

    row_hash_short.short_description = "Hash"


@admin.register(StgControleUnificado)
class StgControleUnificadoAdmin(admin.ModelAdmin):
    """Admin para StgControleUnificado (controle consolidado)"""

    list_display = (
        "row_hash_short",
        "municipio",
        "projeto",
        "uf",
        "gerencia",
        "qtd_compras",
        "soma_quant",
        "updated_at",
    )

    list_filter = (
        "uf",
        "gerencia",
        "projeto",
    )

    search_fields = (
        "row_hash",
        "municipio",
        "projeto",
        "uf",
        "gerencia",
    )

    readonly_fields = (
        "row_hash",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Identificação",
            {
                "fields": ("row_hash",),
            },
        ),
        (
            "Localização",
            {
                "fields": ("municipio", "uf", "projeto", "gerencia"),
            },
        ),
        (
            "Compras",
            {
                "fields": ("qtd_compras", "soma_quant"),
            },
        ),
        (
            "Datas",
            {
                "fields": (
                    "primeira_data_compra",
                    "data_entrega",
                    "data_carta",
                    "data_reuniao_alinhamento",
                ),
            },
        ),
        (
            "Textos",
            {
                "fields": ("contato_inicial", "observacao_concat"),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )

    def row_hash_short(self, obj):
        """Exibe os primeiros 8 caracteres do hash"""
        return obj.row_hash[:8] if obj.row_hash else "-"

    row_hash_short.short_description = "Hash"
