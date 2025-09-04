"""
Views de administração do sistema.
SEMANA 3 - DIA 4: Logs de comunicação e administração avançada.
"""

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import TemplateView


class CommunicationLogsView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Página de visualização dos logs de comunicação.
    Acesso restrito apenas para administradores.
    """

    permission_required = "core.view_logs_comunicacao"
    template_name = "core/admin/communication_logs.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Logs de Comunicação"
        return context
