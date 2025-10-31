"""
URL configuration for DAT Ingest app (ETL Observability)

Fase 5 - Desligamento gradual de planilhas
"""

from django.urls import path
from .views import EtlReportsLatestView

app_name = 'dat_ingest'

urlpatterns = [
    # ETL Observability
    path('etl/reports/latest/', EtlReportsLatestView.as_view(), name='etl-reports-latest'),
]
