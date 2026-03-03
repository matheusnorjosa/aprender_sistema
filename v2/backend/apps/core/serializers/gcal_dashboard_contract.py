"""
OpenAPI contract serializers for dashboard and GCal endpoints.

These serializers are used only to declare explicit request/response schemas
for drf-spectacular contract gates.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations

from rest_framework import serializers

from apps.core.serializers.solicitacao import SolicitacaoSerializer


class DashboardWindowSerializer(serializers.Serializer):
    start = serializers.DateField(allow_null=True, required=False)
    end = serializers.DateField(allow_null=True, required=False)


class GCalStatusCountsSerializer(serializers.Serializer):
    NONE = serializers.IntegerField()
    PENDING = serializers.IntegerField()
    PUBLISHED = serializers.IntegerField()
    ERROR = serializers.IntegerField()


class GCalStatusSummaryResponseSerializer(serializers.Serializer):
    counts = GCalStatusCountsSerializer()
    total = serializers.IntegerField()


class GCalRecentErrorSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    summary = serializers.CharField()
    gcal_last_error = serializers.CharField(allow_blank=True)
    updated_at = serializers.DateTimeField(allow_null=True)


class DashboardMetricsResponseSerializer(serializers.Serializer):
    counts = GCalStatusCountsSerializer()
    recent_errors = GCalRecentErrorSerializer(many=True)
    window = DashboardWindowSerializer()


class AlertsSummaryResponseSerializer(serializers.Serializer):
    errors = serializers.IntegerField()
    pending = serializers.IntegerField()
    published = serializers.IntegerField()
    none = serializers.IntegerField()
    window = DashboardWindowSerializer()


class SuccessRateResponseSerializer(serializers.Serializer):
    published = serializers.IntegerField()
    error = serializers.IntegerField()
    pending = serializers.IntegerField()
    none = serializers.IntegerField()
    rate = serializers.FloatField()
    window = DashboardWindowSerializer()


class TopInsightsItemSerializer(serializers.Serializer):
    name = serializers.CharField()
    count = serializers.IntegerField()
    published = serializers.IntegerField()
    error = serializers.IntegerField()
    rate = serializers.FloatField()


class TopInsightsResponseSerializer(serializers.Serializer):
    items = TopInsightsItemSerializer(many=True)
    window = DashboardWindowSerializer()
    metric = serializers.ChoiceField(choices=["municipios", "projetos"])
    limit = serializers.IntegerField(min_value=1, max_value=20)


class DetailMessageSerializer(serializers.Serializer):
    detail = serializers.CharField()
    code = serializers.CharField(required=False)


class BatchActionRequestSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField(min_value=1), allow_empty=False, max_length=500)
    dry_run = serializers.BooleanField(required=False, default=False)
    apply_blocked = serializers.BooleanField(required=False, default=False)


class BatchActionErrorSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    detail = serializers.CharField()


class BatchActionResponseSerializer(serializers.Serializer):
    queued = serializers.IntegerField()
    errors = BatchActionErrorSerializer(many=True)
    dry_run = serializers.BooleanField()
    apply_blocked = serializers.BooleanField()


class PaginatedSolicitacaoResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = SolicitacaoSerializer(many=True)


class DashboardOverviewKpisSerializer(serializers.Serializer):
    eventos_futuros = serializers.IntegerField()
    eventos_aprovados = serializers.IntegerField()
    total_formadores = serializers.IntegerField()
    aprovacoes_pendentes = serializers.IntegerField()


class DashboardOverviewFluxoItemSerializer(serializers.Serializer):
    fluxo = serializers.CharField()
    quantidade = serializers.IntegerField()


class DashboardOverviewGerenciaItemSerializer(serializers.Serializer):
    gerencia = serializers.CharField()
    quantidade = serializers.IntegerField()
    porcentagem = serializers.FloatField()


class DashboardOverviewCoordenadorItemSerializer(serializers.Serializer):
    nome = serializers.CharField()
    eventos = serializers.IntegerField()


class DashboardOverviewResponseSerializer(serializers.Serializer):
    kpis = DashboardOverviewKpisSerializer()
    por_fluxo = DashboardOverviewFluxoItemSerializer(many=True)
    por_gerencia = DashboardOverviewGerenciaItemSerializer(many=True)
    top_coordenadores = DashboardOverviewCoordenadorItemSerializer(many=True)
