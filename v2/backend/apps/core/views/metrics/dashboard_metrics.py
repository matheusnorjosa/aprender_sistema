"""
Dashboard Metrics Views - §9 Epic #459

Productivity and quality metrics for dashboard monitoring.
Extracted from views_metrics.py.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations

from datetime import timedelta

from django.db.models import Avg, Case, Count, F, When
from django.utils import timezone
from rest_framework import status as http_status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.core.models import AuditLog, Solicitacao
from apps.core.permissions import HasPerm


@api_view(["GET"])
@permission_classes([HasPerm("run_daily_operations") | HasPerm("supervise_operations")])
@throttle_classes([ScopedRateThrottle])
def productivity_metrics(request: Request) -> Response:
    """
    Productivity metrics for the last N days (Issue #189).

    Query params:
        days (int): Number of days to look back (default: 7)

    Returns:
        {
            "period": "7d",
            "events_created": 120,
            "events_approved": 95,
            "events_rejected": 10,
            "approval_rate": 79.17,
            "avg_approval_time_hours": 18.5,
            "gcal_published": 85,
            "gcal_error_rate": 5.26
        }

    Calculations:
        - approval_rate = (approved / total) * 100 (0.0 if division by zero)
        - avg_approval_time_hours = avg(updated_at - created_at).total_seconds() / 3600
        - gcal_error_rate = (errors / approved) * 100 (0.0 if division by zero)

    Permissions: HasPerm("run_daily_operations") | HasPerm("supervise_operations") (only authorized users)
    """
    days = int(request.GET.get("days", 7))
    cutoff = timezone.now() - timedelta(days=days)

    # Query all solicitações in the period
    qs = Solicitacao.objects.filter(created_at__gte=cutoff)

    # Aggregate counts by status
    stats = qs.aggregate(
        total=Count("id"),
        approved=Count(Case(When(status="aprovado", then=1))),
        rejected=Count(Case(When(status="reprovado", then=1))),
    )

    # Calculate approval rate (avoid division by zero)
    total = stats["total"] or 0
    approved = stats["approved"] or 0
    rejected = stats["rejected"] or 0
    approval_rate = (approved / total * 100) if total > 0 else 0.0

    # Approved-only stats in a single query: avg time + gcal counts (#781)
    approved_qs = qs.filter(status="aprovado")
    approved_stats = approved_qs.aggregate(
        avg_time=Avg(
            (F("updated_at") - F("created_at")),
            output_field=None,
        ),
        published=Count(Case(When(gcal_status="PUBLISHED", then=1))),
        errors=Count(Case(When(gcal_status="ERROR", then=1))),
    )

    # Convert timedelta to hours (handle None case)
    avg_time_seconds = approved_stats["avg_time"]
    if avg_time_seconds is not None:
        avg_approval_time_hours = round(avg_time_seconds.total_seconds() / 3600, 2)
    else:
        avg_approval_time_hours = 0.0

    gcal_published = approved_stats["published"] or 0
    gcal_errors = approved_stats["errors"] or 0
    gcal_error_rate = (gcal_errors / approved * 100) if approved > 0 else 0.0

    return Response(
        {
            "period": f"{days}d",
            "events_created": total,
            "events_approved": approved,
            "events_rejected": rejected,
            "approval_rate": round(approval_rate, 2),
            "avg_approval_time_hours": avg_approval_time_hours,
            "gcal_published": gcal_published,
            "gcal_error_rate": round(gcal_error_rate, 2),
        },
        status=http_status.HTTP_200_OK,
    )


# Throttle scope for productivity_metrics (#409)
productivity_metrics.throttle_scope = "metrics"  # type: ignore[attr-defined]


@api_view(["GET"])
@permission_classes([HasPerm("run_daily_operations") | HasPerm("supervise_operations")])
@throttle_classes([ScopedRateThrottle])
def quality_metrics(request: Request) -> Response:
    """
    Quality metrics for the last N days (Issue #189).

    Query params:
        days (int): Number of days to look back (default: 30)

    Returns:
        {
            "period": "30d",
            "rejection_rate": 8.3,
            "conflict_rate": 5.2,
            "rework_rate": 12.1,
            "avg_approval_time_hours": 18.5,
            "avg_publish_time_minutes": 3.2
        }

    Calculations:
        - rejection_rate = (rejected / total) * 100
        - conflict_rate = (with conflicts / total) * 100 (count solicitações with 'conflict' in observacoes)
        - rework_rate = (edited after creation / total) * 100 (check AuditLog for UPDATE actions)
        - avg_approval_time_hours = avg(updated_at - created_at).total_seconds() / 3600
        - avg_publish_time_minutes = avg(gcal_last_sync_at - updated_at).total_seconds() / 60

    Permissions: HasPerm("run_daily_operations") | HasPerm("supervise_operations") (only authorized users)
    """
    days = int(request.GET.get("days", 30))
    cutoff = timezone.now() - timedelta(days=days)

    # Query all solicitações in the period
    qs = Solicitacao.objects.filter(created_at__gte=cutoff)

    # Aggregate counts
    stats = qs.aggregate(
        total=Count("id"),
        rejected=Count(Case(When(status="reprovado", then=1))),
        # Count solicitações with "conflict" keyword in observacoes (case-insensitive)
        with_conflicts=Count(Case(When(observacoes__icontains="conflict", then=1))),
    )

    total = stats["total"] or 0
    rejected = stats["rejected"] or 0
    with_conflicts = stats["with_conflicts"] or 0

    # Rejection rate
    rejection_rate = (rejected / total * 100) if total > 0 else 0.0

    # Conflict rate
    conflict_rate = (with_conflicts / total * 100) if total > 0 else 0.0

    # Rework rate: count solicitações that have UPDATE actions in AuditLog
    # (edited after creation)
    reworked_ids = (
        AuditLog.objects.filter(
            action="UPDATE",
            model_name="Solicitacao",
            created_at__gte=cutoff,
        )
        .values_list("details__solicitacao_id", flat=True)
        .distinct()
    )
    reworked_count = reworked_ids.count()
    rework_rate = (reworked_count / total * 100) if total > 0 else 0.0

    # Average approval time (approved events only)
    approved_qs = qs.filter(status="aprovado")
    avg_approval_time_seconds = approved_qs.aggregate(
        avg_time=Avg(
            (F("updated_at") - F("created_at")),
            output_field=None,
        )
    )["avg_time"]

    if avg_approval_time_seconds is not None:
        avg_approval_time_hours = round(avg_approval_time_seconds.total_seconds() / 3600, 2)
    else:
        avg_approval_time_hours = 0.0

    # Average publish time (PUBLISHED events only, exclude None gcal_last_sync_at)
    published_qs = approved_qs.filter(
        gcal_status="PUBLISHED",
        gcal_last_sync_at__isnull=False,
    )
    avg_publish_time_seconds = published_qs.aggregate(
        avg_time=Avg(
            (F("gcal_last_sync_at") - F("updated_at")),
            output_field=None,
        )
    )["avg_time"]

    if avg_publish_time_seconds is not None:
        avg_publish_time_minutes = round(avg_publish_time_seconds.total_seconds() / 60, 2)
    else:
        avg_publish_time_minutes = 0.0

    return Response(
        {
            "period": f"{days}d",
            "rejection_rate": round(rejection_rate, 2),
            "conflict_rate": round(conflict_rate, 2),
            "rework_rate": round(rework_rate, 2),
            "avg_approval_time_hours": avg_approval_time_hours,
            "avg_publish_time_minutes": avg_publish_time_minutes,
        },
        status=http_status.HTTP_200_OK,
    )


# Throttle scope for quality_metrics (#409)
quality_metrics.throttle_scope = "metrics"  # type: ignore[attr-defined]
