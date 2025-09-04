"""
Views relacionadas às solicitações de eventos.
"""

from django.db import transaction

from .base import *


class SolicitacaoCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = "core.add_solicitacao"
    model = Solicitacao
    form_class = SolicitacaoForm
    template_name = "core/solicitacao_form_enhanced.html"
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
                    f"— Requer aprovação: {'Sim' if requer_aprovacao else 'Não'}",
                )

                # 6. Enviar notificações (SEMANA 3 - DIA 4)
                from core.services.notifications_simplified import (
                    notify_new_solicitacao,
                )

                try:
                    notify_result = notify_new_solicitacao(self.object)
                    if notify_result["success"]:
                        # Log de sucesso das notificações
                        LogAuditoria.objects.create(
                            usuario=self.request.user,
                            acao="RF07: Notificações enviadas",
                            entidade_afetada_id=self.object.id,
                            detalhes=f"Notificações enviadas com sucesso: {notify_result['notifications_sent']}",
                        )
                    else:
                        # Log de erro das notificações (não interrompe o fluxo)
                        LogAuditoria.objects.create(
                            usuario=self.request.user,
                            acao="RF07: Erro ao enviar notificações",
                            entidade_afetada_id=self.object.id,
                            detalhes=f"Erro: {notify_result.get('error', 'Erro desconhecido')}",
                        )
                except Exception as e:
                    # Erro nas notificações não deve interromper o processo principal
                    LogAuditoria.objects.create(
                        usuario=self.request.user,
                        acao="RF07: Erro crítico em notificações",
                        entidade_afetada_id=self.object.id,
                        detalhes=f"Erro crítico ao enviar notificações: {str(e)}",
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
                detalhes=f"ERRO ao criar solicitação: {str(e)}",
            )
            messages.error(self.request, f"Erro ao criar solicitação: {str(e)}")
            return self.form_invalid(form)

    def _requer_aprovacao_superintendencia(self, solicitacao):
        """
        Determina se uma solicitação requer aprovação da superintendência.
        Nova lógica: Projetos do setor Superintendência requerem aprovação.
        """
        if not solicitacao.projeto:
            return False

        # Nova lógica: usar setor.vinculado_superintendencia
        if solicitacao.projeto.setor:
            return solicitacao.projeto.setor.vinculado_superintendencia

        # Fallback para compatibilidade durante transição
        return solicitacao.projeto.vinculado_superintendencia


class SolicitacaoOKView(LoginRequiredMixin, TemplateView):
    template_name = "core/solicitacao_ok.html"
