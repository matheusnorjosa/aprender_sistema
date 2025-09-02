"""
Views relacionadas às solicitações de eventos.
"""

from django.db import transaction
from .base import *


class SolicitacaoCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = 'core.add_solicitacao'
    model = Solicitacao
    form_class = SolicitacaoForm
    template_name = "core/solicitacao_form.html"
    success_url = reverse_lazy("core:solicitar_evento")

    @transaction.atomic
    def form_valid(self, form):
        """
        Processa criação de solicitação usando transação atômica.
        Garante que a solicitação seja criada com auditoria completa.
        """
        try:
            with transaction.atomic():
                # 1. Configurar dados básicos
                form.instance.usuario_solicitante = self.request.user
                
                # 2. Determinar fluxo de aprovação
                solicitacao = form.instance
                requer_aprovacao = self._requer_aprovacao_superintendencia(solicitacao)
                
                # 3. Definir status inicial
                if requer_aprovacao:
                    solicitacao.status = SolicitacaoStatus.PENDENTE
                    message = "Solicitação registrada com sucesso. Aguardando aprovação da superintendência."
                else:
                    solicitacao.status = SolicitacaoStatus.PRE_AGENDA
                    message = "Solicitação registrada e enviada para pré-agenda. Aguarde criação no Google Calendar pelo controle."
                
                # 4. Salvar solicitação
                response = super().form_valid(form)
                
                # 5. Registrar auditoria
                LogAuditoria.objects.create(
                    usuario=self.request.user,
                    acao="RF02: Criar solicitação",
                    entidade_afetada_id=self.object.id,
                    detalhes=f"Solicitação '{self.object.titulo_evento}' criada "
                             f"— Status: {self.object.status} "
                             f"— Requer aprovação: {'Sim' if requer_aprovacao else 'Não'}"
                )
                
                # 6. Validar dados salvos
                if not self.object.pk:
                    raise ValueError("Falha ao salvar solicitação")
                
                # 7. Mensagem de sucesso
                messages.success(self.request, message)
                
                return response
                
        except Exception as e:
            # Log do erro
            LogAuditoria.objects.create(
                usuario=self.request.user,
                acao="RF02: ERRO na criação",
                entidade_afetada_id=None,
                detalhes=f"ERRO ao criar solicitação: {str(e)}"
            )
            messages.error(self.request, f"Erro ao criar solicitação: {str(e)}")
            return self.form_invalid(form)
    
    def _requer_aprovacao_superintendencia(self, solicitacao):
        """
        Determina se uma solicitação requer aprovação da superintendência.
        Critério: Projetos vinculados à superintendência
        """
        return solicitacao.projeto and solicitacao.projeto.vinculado_superintendencia


class SolicitacaoOKView(LoginRequiredMixin, TemplateView):
    template_name = "core/solicitacao_ok.html"