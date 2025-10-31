"""
URL configuration for AS v2 project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from apps.core.admin_site import admin_site  # Custom admin site (superusers only)


def healthz(request):
    """Health check endpoint for Docker/K8s"""
    return JsonResponse(
        {
            "status": "ok",
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
            "timezone": settings.TIME_ZONE,
        }
    )


urlpatterns = [
    # Admin (Custom - Superusers only, Fase 1 Plano DAT/GCal)
    path("admin/", admin_site.urls),
    # Health check
    path("healthz/", healthz, name="healthz"),
    # API
    path("api/", include("apps.core.urls")),
]

# Static/Media files (development only)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
