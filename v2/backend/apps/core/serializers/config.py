"""
AS v2 — Config Serializers

Serializers para Config.
Type-checked with Pyright (strict mode).
"""
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportUntypedBaseClass=false

from __future__ import annotations

from rest_framework import serializers  # type: ignore[attr-defined]


class ConfigSerializer(serializers.Serializer):  # type: ignore[misc]
    """
    Serializer para leitura/escrita de configurações consolidadas.

    Issue #187: UI para Configurações do Sistema.

    Categorias:
    - Disponibilidade (RD-04, RD-05): TRAVEL_BUFFER_MINUTES, AVAILABILITY_DAILY_LIMIT_HOURS
    - GCal (RF05/RF06): BATCH_SIZE, LOCK_TTL_SECONDS, AUTO_RETRY_ON_ERROR, MAX_RETRIES, SEND_UPDATES
    - Sessões/UX: SESSION_COOKIE_AGE, SESSION_WARNING_THRESHOLD, AUTOCOMPLETE_DEBOUNCE_MS
    - Features: ENABLE_MULTI_CALENDAR, ENABLE_BATCH_ACTIONS, ENABLE_ADVANCED_FILTERS
    """

    # Disponibilidade (RD-04, RD-05)
    TRAVEL_BUFFER_MINUTES = serializers.IntegerField(min_value=0, default=120)
    AVAILABILITY_DAILY_LIMIT_HOURS = serializers.IntegerField(min_value=1, max_value=12, default=8)
    ALLOW_ADJACENT_EVENTS = serializers.BooleanField(default=True)
    BLOCK_AUTO_APPROVE = serializers.BooleanField(default=True)

    # GCal (RF05/RF06)
    BATCH_SIZE = serializers.IntegerField(min_value=50, max_value=500, default=200)
    LOCK_TTL_SECONDS = serializers.IntegerField(min_value=60, max_value=600, default=300)
    AUTO_RETRY_ON_ERROR = serializers.BooleanField(default=True)
    MAX_RETRIES = serializers.IntegerField(min_value=1, max_value=5, default=3)
    SEND_UPDATES = serializers.ChoiceField(choices=["none", "all", "externalOnly"], default="none")

    # Sessões/UX
    SESSION_COOKIE_AGE = serializers.IntegerField(min_value=300, default=1800)
    SESSION_WARNING_THRESHOLD = serializers.IntegerField(min_value=60, default=300)
    AUTOCOMPLETE_DEBOUNCE_MS = serializers.IntegerField(min_value=100, max_value=1000, default=300)

    # Features
    ENABLE_MULTI_CALENDAR = serializers.BooleanField(default=False)
    ENABLE_BATCH_ACTIONS = serializers.BooleanField(default=False)
    ENABLE_ADVANCED_FILTERS = serializers.BooleanField(default=False)
