"""
URLs para Ingestão de CSVs ETL via REST API

App: dat_ingest
Stack: Python 3.13 | Django 5.2 | DRF

Prefixo: /api/ingest/

Endpoints:
    POST /api/ingest/agenda/ - Upload events.csv + event_people.csv
    POST /api/ingest/disponibilidade/ - Upload disp_blocks.csv + disp_travels.csv
    POST /api/ingest/controle/ - Upload controle_unificado.csv
    GET /api/ingest/health/ - Health check com contagens
"""

from django.urls import path

from . import views

app_name = "dat_ingest"

urlpatterns = [
    # POST endpoints (requer IsAdminUser)
    path("agenda/", views.ingest_agenda, name="ingest-agenda"),
    path(
        "disponibilidade/", views.ingest_disponibilidade, name="ingest-disponibilidade"
    ),
    path("controle/", views.ingest_controle, name="ingest-controle"),
    # GET endpoint (requer IsAuthenticated)
    path("health/", views.health_check, name="health-check"),
]
