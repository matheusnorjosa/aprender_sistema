from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("conflitos", views.conflitos, name="conflitos"),
    path("workload", views.workload, name="workload"),
    path("kpis", views.kpis, name="kpis"),
    path("series", views.series, name="series"),
]
