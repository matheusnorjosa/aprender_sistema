"""
AS v2 — Standardized API Response Factory (#411)

Provides consistent response format across custom endpoints.
ViewSets continue using DRF standard pagination format.
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false

from __future__ import annotations

from typing import Any

from django.utils import timezone
from rest_framework.response import Response


class APIResponse:
    """Factory for standardized API responses."""

    @staticmethod
    def success(data: dict[str, Any], meta: dict[str, Any] | None = None) -> Response:
        """
        Standardized success response.

        Response format:
        {
            "data": {...},
            "meta": {
                "timestamp": "...",
                ...
            }
        }
        """
        response_data = {
            "data": data,
            "meta": {
                "timestamp": timezone.now().isoformat(),
                **(meta or {})
            }
        }
        return Response(response_data)

    @staticmethod
    def list(
        items: list[Any],
        total: int | None = None,
        meta: dict[str, Any] | None = None
    ) -> Response:
        """
        Standardized list response (non-paginated).

        Response format:
        {
            "data": {
                "items": [...],
                "total": 10
            },
            "meta": {...}
        }
        """
        return APIResponse.success(
            data={
                "items": items,
                "total": total if total is not None else len(items)
            },
            meta=meta
        )

    @staticmethod
    def availability(ok: bool, conflicts: list[Any] | None = None) -> Response:
        """
        Standardized availability check response.

        Response format:
        {
            "data": {
                "available": true,
                "conflicts": []
            },
            "meta": {...}
        }
        """
        return APIResponse.success(
            data={
                "available": ok,
                "conflicts": conflicts or []
            }
        )

