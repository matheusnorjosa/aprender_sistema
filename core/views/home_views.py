"""
Views relacionadas à página inicial e dashboard.
"""

from .base import *


def home(request):
    """
    Renderiza a página inicial do sistema.
    """
    return render(request, "core/home.html")


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user"] = self.request.user
        return context
