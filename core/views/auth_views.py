"""
Views relacionadas à autenticação de usuários.
"""

from .base import *
from core.forms import CPFAuthenticationForm, CPFUserCreationForm


class CustomLoginView(LoginView):
    """
    View de login customizada usando CPF como username
    """
    form_class = CPFAuthenticationForm
    template_name = "core/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        next_url = self.request.GET.get("next")
        if next_url:
            return next_url
        return reverse_lazy("core:home")

    def form_valid(self, form):
        user = form.get_user()
        # Usar nome completo ou CPF se nome não estiver disponível
        nome_usuario = user.get_full_name() or f"CPF {user.cpf}" or user.username
        messages.success(
            self.request,
            f"Bem-vindo(a), {nome_usuario}!",
        )
        return super().form_valid(form)


class CPFSignupView(CreateView):
    """
    View de cadastro usando CPF
    """
    form_class = CPFUserCreationForm
    template_name = "core/signup.html"
    success_url = reverse_lazy("core:login")

    def form_valid(self, form):
        messages.success(
            self.request,
            "Usuário criado com sucesso! Faça login com seu CPF."
        )
        return super().form_valid(form)
