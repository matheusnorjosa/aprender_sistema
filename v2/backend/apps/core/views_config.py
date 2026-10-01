"""
Config API View — GET/PUT /api/config/

Issue #187: UI para Configurações do Sistema

Endpoints:
- GET /api/config/ - Retorna configurações consolidadas (flat dict)
- PUT /api/config/ - Atualiza configurações + AuditLog

Permissions:
- HasPerm("manage_purchases_and_materials") | HasPerm("approve_solicitation") (RBAC)

Cache:
- Invalidação automática via signal post_save (apps/core/signals.py)
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false

from __future__ import annotations

from typing import Any

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema

from apps.core.api_schemas import COMMON_ERROR_RESPONSES
from apps.core.models import AuditLog, Config
from apps.core.permissions import HasPerm
from apps.core.serializers import ConfigSerializer
from apps.core.services.config_service import bust_cfg, get_cfg, parametros_disponibilidade

# Chaves do serializer por registro de Config. O JSON de cada registro pode ter outras
# chaves (ex.: `features` guarda overrides lidos por /api/features/), que o PUT preserva.
_CAMPOS_POR_CHAVE: dict[str, tuple[str, ...]] = {
    "availability": (
        "TRAVEL_BUFFER_MINUTES",
        "AVAILABILITY_DAILY_LIMIT_HOURS",
        "ALLOW_ADJACENT_EVENTS",
        "BLOCK_AUTO_APPROVE",
    ),
    "gcal_sync": ("BATCH_SIZE", "LOCK_TTL_SECONDS", "AUTO_RETRY_ON_ERROR", "MAX_RETRIES", "SEND_UPDATES"),
    "session_settings": ("SESSION_COOKIE_AGE", "SESSION_WARNING_THRESHOLD", "AUTOCOMPLETE_DEBOUNCE_MS"),
    "features": ("ENABLE_MULTI_CALENDAR", "ENABLE_BATCH_ACTIONS", "ENABLE_ADVANCED_FILTERS"),
}


def _config_atual() -> dict[str, Any]:
    """Configurações vigentes em formato flat (lidas do Config model via get_cfg, com cache)."""
    availability = get_cfg("availability", {})
    disponibilidade = parametros_disponibilidade()  # a mesma fonte que o motor (RD-04/RD-05) aplica
    gcal_sync = get_cfg("gcal_sync", {})
    session_settings = get_cfg("session_settings", {})
    features = get_cfg("features", {})

    return {
        # Availability
        "TRAVEL_BUFFER_MINUTES": disponibilidade["TRAVEL_BUFFER_MINUTES"],
        "AVAILABILITY_DAILY_LIMIT_HOURS": disponibilidade["AVAILABILITY_DAILY_LIMIT_HOURS"],
        "ALLOW_ADJACENT_EVENTS": availability.get("ALLOW_ADJACENT_EVENTS", True),
        "BLOCK_AUTO_APPROVE": availability.get("BLOCK_AUTO_APPROVE", True),
        # GCal
        "BATCH_SIZE": gcal_sync.get("BATCH_SIZE", 200),
        "LOCK_TTL_SECONDS": gcal_sync.get("LOCK_TTL_SECONDS", 300),
        "AUTO_RETRY_ON_ERROR": gcal_sync.get("AUTO_RETRY_ON_ERROR", True),
        "MAX_RETRIES": gcal_sync.get("MAX_RETRIES", 3),
        "SEND_UPDATES": gcal_sync.get("SEND_UPDATES", "none"),
        # Session
        "SESSION_COOKIE_AGE": session_settings.get("SESSION_COOKIE_AGE", 1800),
        "SESSION_WARNING_THRESHOLD": session_settings.get("SESSION_WARNING_THRESHOLD", 300),
        "AUTOCOMPLETE_DEBOUNCE_MS": session_settings.get("AUTOCOMPLETE_DEBOUNCE_MS", 300),
        # Features
        "ENABLE_MULTI_CALENDAR": features.get("ENABLE_MULTI_CALENDAR", False),
        "ENABLE_BATCH_ACTIONS": features.get("ENABLE_BATCH_ACTIONS", False),
        "ENABLE_ADVANCED_FILTERS": features.get("ENABLE_ADVANCED_FILTERS", False),
    }


@extend_schema(
    methods=["GET"],
    summary="Ler configurações do sistema",
    description="Retorna configurações consolidadas em formato flat para uso do frontend.",
    responses={
        200: ConfigSerializer,
        401: COMMON_ERROR_RESPONSES[401],
        403: COMMON_ERROR_RESPONSES[403],
    },
    tags=["config"],
)
@extend_schema(
    methods=["PUT"],
    summary="Atualizar configurações do sistema",
    description=(
        "Valida e persiste as chaves enviadas, registrando AuditLog. "
        "Chave ausente mantém o valor atual (não volta ao padrão)."
    ),
    request=ConfigSerializer,
    responses={
        200: ConfigSerializer,
        400: COMMON_ERROR_RESPONSES[400],
        401: COMMON_ERROR_RESPONSES[401],
        403: COMMON_ERROR_RESPONSES[403],
    },
    tags=["config"],
)
@api_view(["GET", "PUT"])
@permission_classes([HasPerm("manage_purchases_and_materials") | HasPerm("approve_solicitation")])
def config_view(request: Request) -> Response:
    """
    GET: Lê configurações consolidadas do Config model.
    PUT: Atualiza as chaves enviadas + cria AuditLog. Chave ausente mantém o valor atual.

    Permissions: HasPerm("manage_purchases_and_materials") | HasPerm("approve_solicitation")

    GET Response (200):
        {
            "TRAVEL_BUFFER_MINUTES": 120,
            "AVAILABILITY_DAILY_LIMIT_HOURS": 8,
            ...
        }

    PUT Request:
        {
            "TRAVEL_BUFFER_MINUTES": 90,
            "AVAILABILITY_DAILY_LIMIT_HOURS": 10,
            ...
        }

    PUT Response (200):
        {
            "TRAVEL_BUFFER_MINUTES": 90,
            "AVAILABILITY_DAILY_LIMIT_HOURS": 10,
            ...
        }

    PUT Response (400):
        {
            "TRAVEL_BUFFER_MINUTES": ["Ensure this value is greater than or equal to 0."],
            ...
        }
    """

    if request.method == "GET":
        return Response(ConfigSerializer(_config_atual()).data)

    elif request.method == "PUT":
        # Campo ausente mantém o valor atual (auditoria UX 30/09): sem `partial`, o
        # serializer completava o que não veio com `default=` e o save zerava o resto.
        serializer = ConfigSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        enviados: dict[str, Any] = dict(serializer.validated_data)
        vd: dict[str, Any] = {**_config_atual(), **enviados}

        # Grava só as chaves enviadas, por cima do JSON guardado (auditoria UX 30/09, rodada
        # 2): regravar o resto com o valor lido no começo desfazia a edição de outra pessoa
        # feita no meio do caminho, e apagava as chaves que o serializer não conhece. Lido do
        # banco, não do cache, para pegar também o que foi gravado sem passar pelo signal.
        for chave, campos in _CAMPOS_POR_CHAVE.items():
            mudou = {campo: enviados[campo] for campo in campos if campo in enviados}
            if not mudou:
                continue
            registro = Config.objects.filter(key=chave).first()
            guardado = registro.value if registro and isinstance(registro.value, dict) else {}
            Config.objects.update_or_create(
                key=chave,
                defaults={"value": {**guardado, **mudou}, "effective_at": timezone.now()},
            )

        # AuditLog (Issue #187 requirement)
        AuditLog.objects.create(
            usuario=request.user,
            action=AuditLog.Action.UPDATE_CONFIG,
            model_name="Config",
            details={
                "changed_fields": list(enviados.keys()),
                "ip_address": request.META.get("REMOTE_ADDR", "unknown"),
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:200],
            },
        )

        # Invalidar cache (automático via signal, mas garantir)
        for key in ["availability", "gcal_sync", "session_settings", "features"]:
            bust_cfg(key)

        return Response(ConfigSerializer(vd).data, status=status.HTTP_200_OK)

    # Should never reach here due to @api_view decorator
    return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
