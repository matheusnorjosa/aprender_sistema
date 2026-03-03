"""
OpenAPI contract serializers for critical frontend endpoints (#703).

These serializers exist only to provide explicit, stable API contracts in
drf-spectacular for CI gate assertions.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations

from rest_framework import serializers


class HomeStatsResponseSerializer(serializers.Serializer):
    pending_approvals = serializers.IntegerField(allow_null=True)
    upcoming_events = serializers.IntegerField()
    my_requests = serializers.IntegerField(allow_null=True)


class MonthlyAvailabilityPersonSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    email = serializers.EmailField(allow_blank=True)
    ch_month = serializers.FloatField()
    ch_year = serializers.FloatField()
    position_month = serializers.IntegerField()


class MonthlyAvailabilityResponseSerializer(serializers.Serializer):
    days = serializers.ListField(child=serializers.IntegerField())
    legend = serializers.DictField(child=serializers.CharField())
    people = MonthlyAvailabilityPersonSerializer(many=True)
    cells = serializers.ListField(child=serializers.ListField(child=serializers.CharField(allow_blank=True)))
    details_index = serializers.DictField(child=serializers.ListField(child=serializers.JSONField()))


class MonthlyAvailabilityErrorResponseSerializer(serializers.Serializer):
    error = serializers.CharField()


class ImportFileUploadRequestSerializer(serializers.Serializer):
    file = serializers.FileField()


class ImportOperationResponseSerializer(serializers.Serializer):
    stats = serializers.DictField(child=serializers.JSONField(), required=False)
    pendencias = serializers.DictField(child=serializers.JSONField(), required=False)
    dry_run = serializers.BooleanField(required=False)
    file = serializers.CharField(required=False)
    path = serializers.CharField(required=False)
    created_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
    ts = serializers.CharField(required=False)
    detail = serializers.CharField(required=False)


class ImportOperationErrorResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
