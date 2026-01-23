"""
Core schemas - Estruturas de dados padronizadas
"""

from .etl_report import ETL_REPORT_SCHEMA_EXAMPLE, ETLError, ETLMetrics, ETLReport

__all__ = ["ETLReport", "ETLMetrics", "ETLError", "ETL_REPORT_SCHEMA_EXAMPLE"]
