# aprender_sistema/aprender_sistema/urls.py

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "accounts/", include("django.contrib.auth.urls")
    ),  # Inclui as URLs de autenticação
    path("mcp/", include("mcp_server.urls")),  # Django MCP Server
    path("", include("core.urls")),
]

# API REST Framework - Temporariamente desabilitada devido a problemas de compatibilidade
# TODO: Corrigir problema com coreapi.Field no DRF 3.16.1
# try:
#     import rest_framework
#     urlpatterns.insert(2, path("api/", include("api.urls")))
#     print("✅ API REST Framework ativada com sucesso")
# except ImportError:
#     print("⚠️ Django REST Framework não instalado - API desabilitada")
