"""
Metrics API Views

§9 Epic #459: Refactored to delegate to modular views.

This module re-exports all views from views/metrics/ for backward compatibility.
Original views extracted to:
- views/metrics/map_metrics.py (metrics_map, metrics_map_coordinators)
- views/metrics/dashboard_metrics.py (productivity_metrics, quality_metrics)
- views/metrics/formador_metrics.py (formadores_metrics)

Issue #189: Team Metrics Endpoints (productivity, formadores, quality)
"""

# §9 Epic #459: Re-export from modular views for backward compatibility
from apps.core.views.metrics import (
    formadores_metrics,
    metrics_map,
    metrics_map_coordinators,
    productivity_metrics,
    quality_metrics,
)

__all__ = [
    "metrics_map",
    "metrics_map_coordinators",
    "productivity_metrics",
    "formadores_metrics",
    "quality_metrics",
]
