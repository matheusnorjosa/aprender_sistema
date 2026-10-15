"""
Custom Admin Site - Restrito a Superusers

Sobrescreve o admin.site para restringir acesso apenas a superusers.
Fase 1 - Plano DAT/GCal 2025-10-29: Admin DAT no frontend substitui uso cotidiano do Django Admin.

Uso:
    from apps.core.admin_site import admin_site
    admin_site.register(Model, ModelAdmin)
"""

from __future__ import annotations

from typing import Any

from django.contrib.admin import AdminSite as BaseAdminSite
from django.contrib.admin.forms import AdminAuthenticationForm
from django.http import HttpRequest

from apps.core.views_auth import conta_bloqueada, limpar_falhas_de_login


class LoginAdminComBloqueioForm(AdminAuthenticationForm):
    """Login do admin com o mesmo bloqueio de conta da API (auditoria 2026-10-14, C1/C2).

    Antes de ``authenticate()``: conta bloqueada recebe o mesmo erro de senha errada, sem
    a senha ser testada. A falha é contada e gravada em ``LOGIN_FAILED`` pelo receptor de
    ``user_login_failed`` (``views_auth.registrar_falha_de_login``), igual à API.
    """

    def clean(self) -> dict[str, Any]:
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")
        request = self.request
        if request is None or not isinstance(username, str) or not isinstance(password, str):
            return super().clean()  # sem credencial completa o Django não autentica
        if conta_bloqueada(request, username, password):
            raise self.get_invalid_login_error()
        cleaned_data = super().clean()
        limpar_falhas_de_login(request, username)
        return cleaned_data


class SuperuserOnlyAdminSite(BaseAdminSite):
    """
    AdminSite customizado que restringe acesso apenas a superusers.

    Rationale:
    - Django Admin passa a ser ferramenta de desenvolvimento/debugging.
    - Gestão cotidiana (DAT) migra para interface React em /dat/admin.
    - Apenas desenvolvedores (superusers) acessam o admin nativo.
    """

    site_header = "AS v2 Admin (Dev Only)"
    site_title = "AS v2 Admin"
    index_title = "Administração (Superusers apenas)"
    login_form = LoginAdminComBloqueioForm

    def has_permission(self, request: HttpRequest) -> bool:
        """
        Restringe acesso apenas a superusers.

        Args:
            request: HttpRequest object

        Returns:
            bool: True se usuário é superuser, False caso contrário
        """
        return bool(request.user.is_active and getattr(request.user, "is_superuser", False))


# Instanciar custom admin site
admin_site = SuperuserOnlyAdminSite(name="superuser_admin")
