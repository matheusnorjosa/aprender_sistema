"""
AS v2 — GCal Views Package

Modular package containing all GCal views, organized by domain:
- gcal: Core GCal operations (list calendars, health check)
- helpers: Helper functions and pagination classes
- summary: Status summaries, metrics, and alerts
- batch: Batch operations (publish, reapply, resync)
- detail: Event details, listing, export, and drift detection
- insights: Analytics (success rate, top insights)

Backwards-compatible re-exports for existing imports.
"""

# Batch views
from apps.core.views_gcal.batch import GCalBatchReapplyView, GCalBatchResyncView, GCalPublishBatchView

# Detail views
from apps.core.views_gcal.detail import (
    DashboardEventsExportView,
    DashboardEventsView,
    EventDetailAPIView,
    GCalDriftView,
)

# Core GCal views (from old views_gcal.py)
from apps.core.views_gcal.gcal import gcal_calendars, gcal_health

# Helpers
from apps.core.views_gcal.helpers import DashboardEventsPagination, _apply_common_filters, _filter_events_queryset

# Insights views
from apps.core.views_gcal.insights import SuccessRateView, TopInsightsView

# Summary views
from apps.core.views_gcal.summary import AlertsSummaryView, DashboardMetricsView, GCalListView, GCalStatusSummaryView

__all__ = [
    # Core GCal
    "gcal_calendars",
    "gcal_health",
    # Helpers
    "DashboardEventsPagination",
    "_apply_common_filters",
    "_filter_events_queryset",
    # Summary
    "AlertsSummaryView",
    "DashboardMetricsView",
    "GCalListView",
    "GCalStatusSummaryView",
    # Batch
    "GCalBatchReapplyView",
    "GCalBatchResyncView",
    "GCalPublishBatchView",
    # Detail
    "DashboardEventsExportView",
    "DashboardEventsView",
    "EventDetailAPIView",
    "GCalDriftView",
    # Insights
    "SuccessRateView",
    "TopInsightsView",
]
