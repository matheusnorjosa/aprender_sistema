"""
AS v2 — Availability Views (shim de compatibilidade)

Este módulo existia como cópia mais fraca das views de disponibilidade
(AvailabilityCheckView/AvailabilityCheckManyView com [IsAuthenticated] e
AvailabilityBlockViewSet owner-scoped) que NUNCA foram roteadas — o urls.py
importa de `apps.core.views_availability`. A facade `views/__init__.py`
reexportava por engano as cópias fracas.

Agora reexporta as views ATIVAS e protegidas de `apps.core.views_availability`
(fonte única). Sem import circular: `views_availability` não importa de
`apps.core.views`.
"""

from apps.core.views_availability import (  # noqa: F401
    AvailabilityBlockViewSet,
    AvailabilityCheckManyView,
    AvailabilityCheckView,
)
