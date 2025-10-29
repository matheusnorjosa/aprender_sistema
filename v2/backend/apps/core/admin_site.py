"""
Custom Admin Site - Restrito a Superusers

Sobrescreve o admin.site para restringir acesso apenas a superusers.
Fase 1 - Plano DAT/GCal 2025-10-29: Admin DAT no frontend substitui uso cotidiano do Django Admin.

Uso:
    from apps.core.admin_site import admin_site
    admin_site.register(Model, ModelAdmin)
"""

from django.contrib.admin import AdminSite as BaseAdminSite


class SuperuserOnlyAdminSite(BaseAdminSite):
    """
    AdminSite customizado que restringe acesso apenas a superusers.

    Rationale:
    - Django Admin passa a ser ferramenta de desenvolvimento/debugging.
    - Gestão cotidiana (DAT) migra para interface React em /admin-dat.
    - Apenas desenvolvedores (superusers) acessam o admin nativo.
    """

    site_header = "AS v2 Admin (Dev Only)"
    site_title = "AS v2 Admin"
    index_title = "Administração (Superusers apenas)"

    def has_permission(self, request):
        """
        Restringe acesso apenas a superusers.

        Args:
            request: HttpRequest object

        Returns:
            bool: True se usuário é superuser, False caso contrário
        """
        return request.user.is_active and request.user.is_superuser


# Instanciar custom admin site
admin_site = SuperuserOnlyAdminSite(name='superuser_admin')
