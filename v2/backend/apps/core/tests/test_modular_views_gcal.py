"""
Test backwards compatibility for modular views_gcal package.

Ensures all views and helpers are importable from apps.core.views_gcal
after refactoring from views_gcal.py + views_gcal_dashboard.py to views_gcal/ package.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations
import pytest


class TestViewsGCalBackwardsCompatibility:
    """Test that all views_gcal exports remain accessible."""

    def test_gcal_calendars_importable(self):
        """gcal_calendars should be importable from views_gcal."""
        from apps.core.views_gcal import gcal_calendars
        assert callable(gcal_calendars)

    def test_gcal_health_importable(self):
        """gcal_health should be importable from views_gcal."""
        from apps.core.views_gcal import gcal_health
        assert callable(gcal_health)

    def test_gcal_status_summary_view_importable(self):
        """GCalStatusSummaryView should be importable from views_gcal."""
        from apps.core.views_gcal import GCalStatusSummaryView
        assert GCalStatusSummaryView is not None

    def test_gcal_list_view_importable(self):
        """GCalListView should be importable from views_gcal."""
        from apps.core.views_gcal import GCalListView
        assert GCalListView is not None

    def test_gcal_drift_view_importable(self):
        """GCalDriftView should be importable from views_gcal."""
        from apps.core.views_gcal import GCalDriftView
        assert GCalDriftView is not None

    def test_gcal_publish_batch_view_importable(self):
        """GCalPublishBatchView should be importable from views_gcal."""
        from apps.core.views_gcal import GCalPublishBatchView
        assert GCalPublishBatchView is not None

    def test_dashboard_metrics_view_importable(self):
        """DashboardMetricsView should be importable from views_gcal."""
        from apps.core.views_gcal import DashboardMetricsView
        assert DashboardMetricsView is not None

    def test_dashboard_events_view_importable(self):
        """DashboardEventsView should be importable from views_gcal."""
        from apps.core.views_gcal import DashboardEventsView
        assert DashboardEventsView is not None

    def test_alerts_summary_view_importable(self):
        """AlertsSummaryView should be importable from views_gcal."""
        from apps.core.views_gcal import AlertsSummaryView
        assert AlertsSummaryView is not None

    def test_dashboard_events_export_view_importable(self):
        """DashboardEventsExportView should be importable from views_gcal."""
        from apps.core.views_gcal import DashboardEventsExportView
        assert DashboardEventsExportView is not None

    def test_gcal_batch_reapply_view_importable(self):
        """GCalBatchReapplyView should be importable from views_gcal."""
        from apps.core.views_gcal import GCalBatchReapplyView
        assert GCalBatchReapplyView is not None

    def test_gcal_batch_resync_view_importable(self):
        """GCalBatchResyncView should be importable from views_gcal."""
        from apps.core.views_gcal import GCalBatchResyncView
        assert GCalBatchResyncView is not None

    def test_event_detail_api_view_importable(self):
        """EventDetailAPIView should be importable from views_gcal."""
        from apps.core.views_gcal import EventDetailAPIView
        assert EventDetailAPIView is not None

    def test_success_rate_view_importable(self):
        """SuccessRateView should be importable from views_gcal."""
        from apps.core.views_gcal import SuccessRateView
        assert SuccessRateView is not None

    def test_top_insights_view_importable(self):
        """TopInsightsView should be importable from views_gcal."""
        from apps.core.views_gcal import TopInsightsView
        assert TopInsightsView is not None

    def test_dashboard_events_pagination_importable(self):
        """DashboardEventsPagination should be importable from views_gcal."""
        from apps.core.views_gcal import DashboardEventsPagination
        assert DashboardEventsPagination is not None

    def test_filter_events_queryset_helper_importable(self):
        """_filter_events_queryset should be importable from views_gcal."""
        from apps.core.views_gcal import _filter_events_queryset
        assert callable(_filter_events_queryset)

    def test_apply_common_filters_helper_importable(self):
        """_apply_common_filters should be importable from views_gcal."""
        from apps.core.views_gcal import _apply_common_filters
        assert callable(_apply_common_filters)


class TestViewsGCalModuleStructure:
    """Test that views_gcal package has correct structure."""

    def test_package_has_all_attribute(self):
        """views_gcal package should have __all__ attribute."""
        import apps.core.views_gcal as views_gcal
        assert hasattr(views_gcal, '__all__')
        assert len(views_gcal.__all__) == 18  # 2 core + 3 helpers + 4 summary + 3 batch + 4 detail + 2 insights

    def test_submodules_exist(self):
        """All submodules should be importable."""
        from apps.core.views_gcal import gcal
        from apps.core.views_gcal import helpers
        from apps.core.views_gcal import summary
        from apps.core.views_gcal import batch
        from apps.core.views_gcal import detail
        from apps.core.views_gcal import insights

        assert gcal is not None
        assert helpers is not None
        assert summary is not None
        assert batch is not None
        assert detail is not None
        assert insights is not None
