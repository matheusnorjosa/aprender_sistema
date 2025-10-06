from django.urls import path
from . import views

app_name = "reports"

urlpatterns = [
    path("conflitos", views.conflitos, name="conflitos"),
    path("workload", views.workload, name="workload"),
]
