"""
Views relacionadas à autenticação de usuários.
"""

from .base import *


class CustomLoginView(LoginView):
    template_name = "core/login.html"
    redirect_authenticated_user = True
    
    def get_success_url(self):
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return reverse_lazy('core:home')
    
    def form_valid(self, form):
        messages.success(self.request, f"Bem-vindo(a), {form.get_user().get_full_name() or form.get_user().username}!")
        return super().form_valid(form)