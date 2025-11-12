"""
URL configuration for DAT Ingest app (ETL Observability)

Fase 5 - Desligamento gradual de planilhas
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false

from django.urls import path
from .views import EtlReportsLatestView

app_name = 'dat_ingest'

urlpatterns = [
    # ETL Observability
    path('etl/reports/latest/', EtlReportsLatestView.as_view(), name='etl-reports-latest'),
]
