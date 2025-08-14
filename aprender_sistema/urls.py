# aprender_sistema/aprender_sistema/urls.py

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")), # Inclui as URLs de autenticação
    path("", include("core.urls")),
]
