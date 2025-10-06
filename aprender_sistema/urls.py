from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("api/", include("api.urls")),  # API REST + healthcheck
    path("api/reports/", include("backend.reports.urls")),  # Reports API (conflitos + workload)
    path("", include("core.urls")),  # Core URLs (Hotfix Dia 3: reabilitado)
]

# ========================================
# ROTAS PROTEGIDAS POR FEATURE FLAGS
# ========================================

# MCP Tools - Apenas se habilitado
if getattr(settings, "MCP_TOOLS_ENABLED", False):
    try:
        urlpatterns.append(path("mcp/", include("core.mcp.urls")))
    except ImportError:
        # MCP URLs não disponíveis
        pass

# APIs Experimentais - Apenas se habilitado
if getattr(settings, "EXPERIMENTAL_APIS_ENABLED", False):
    try:
        urlpatterns.append(path("experimental/", include("core.experimental.urls")))
    except ImportError:
        # APIs experimentais não disponíveis
        pass
