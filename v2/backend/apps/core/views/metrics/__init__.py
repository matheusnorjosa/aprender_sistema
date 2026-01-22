"""
Metrics Views Package - §9 Epic #459

Modularized metrics endpoints for dashboard and monitoring.
Re-exports all views for backward compatibility with urls.py.
"""

from .dashboard_metrics import productivity_metrics, quality_metrics
from .formador_metrics import formadores_metrics
from .map_metrics import metrics_map, metrics_map_coordinators

__all__ = [
    "metrics_map",
    "metrics_map_coordinators",
    "productivity_metrics",
    "formadores_metrics",
    "quality_metrics",
]
