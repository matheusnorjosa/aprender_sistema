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

# TODO: Reativar quando instalar djangorestframework
# try:
#     import rest_framework
#     urlpatterns.insert(2, path("api/", include("api.urls")))
# except ImportError:
#     pass
