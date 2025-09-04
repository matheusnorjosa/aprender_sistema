"""
Sistema de Notificações Simplificado do Sistema Aprender
SEMANA 3 - DIA 4: Implementação completa de notificações e comunicações

Sistema responsável por:
1. ✅ Notificações em tempo real (sistema interno)
3. ✅ Dashboard de notificações para cada perfil
4. ✅ Preparação para WhatsApp/SMS (código pronto)
5. ✅ Logs de comunicações (visível apenas para admin)

SEM e-mails automáticos (conforme solicitado).
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.contrib.auth.models import Group
from django.utils import timezone

from core.models import (
    EventoGoogleCalendar,
    LogAuditoria,
    LogComunicacao,
    Notificacao,
    Solicitacao,
    SolicitacaoStatus,
    Usuario,
)

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Serviço central de notificações do sistema.
    Foco em notificações internas + preparação WhatsApp/SMS.
    """

    def __init__(self):
        # E-mails desabilitados conforme solicitado
        self.email_enabled = False

        # Preparação para futuro (desabilitados por padrão)
        self.sms_enabled = getattr(settings, "NOTIFICATION_SMS_ENABLED", False)
        self.whatsapp_enabled = getattr(
            settings, "NOTIFICATION_WHATSAPP_ENABLED", False
        )

    # ==================== NOTIFICAÇÕES DE SOLICITAÇÃO ====================

    def notify_solicitacao_created(self, solicitacao: Solicitacao) -> Dict[str, Any]:
        """
        Notifica criação de nova solicitação - APENAS notificações internas.

        Fluxo:
        1. Se projeto vinculado à superintendência → notificar superintendência
        2. Se projeto não vinculado → vai direto para controle (PRE_AGENDA)
        """
        try:
            results = []

            # Nova lógica baseada em setores
            requer_aprovacao = (
                (
                    solicitacao.projeto.setor
                    and solicitacao.projeto.setor.vinculado_superintendencia
                )
                if solicitacao.projeto.setor
                else solicitacao.projeto.vinculado_superintendencia
            )

            if requer_aprovacao:
                # Notificar superintendência
                result = self._notify_superintendencia_nova_solicitacao(solicitacao)
                results.append(result)
            else:
                # Vai direto para controle - notificar grupo controle
                result = self._notify_controle_nova_solicitacao(solicitacao)
                results.append(result)

            # Sempre notificar o solicitante sobre confirmação
            result = self._notify_solicitante_confirmacao(solicitacao)
            results.append(result)

            # Log de auditoria
            LogAuditoria.objects.create(
                usuario=solicitacao.usuario_solicitante,
                acao="RF07: Notificações enviadas - Nova solicitação",
                entidade_afetada_id=solicitacao.id,
                detalhes=f"Solicitação '{solicitacao.titulo_evento}' - "
                f"Notificações enviadas: {len(results)}",
            )

            return {
                "success": True,
                "notifications_sent": len(results),
                "results": results,
            }

        except Exception as e:
            logger.error(
                f"Erro ao notificar criação de solicitação {solicitacao.id}: {e}"
            )
            return {"success": False, "error": str(e)}

    def notify_solicitacao_approved(
        self, solicitacao: Solicitacao, aprovador: Usuario
    ) -> Dict[str, Any]:
        """
        Notifica aprovação de solicitação pela superintendência.
        """
        try:
            results = []

            # 1. Notificar solicitante sobre aprovação
            result = self._notify_solicitante_aprovacao(solicitacao, aprovador)
            results.append(result)

            # 2. Notificar grupo controle sobre nova solicitação em PRE_AGENDA
            result = self._notify_controle_pre_agenda(solicitacao)
            results.append(result)

            # 3. Notificar formadores sobre possível evento
            result = self._notify_formadores_pre_evento(solicitacao)
            results.append(result)

            # Log de auditoria
            LogAuditoria.objects.create(
                usuario=aprovador,
                acao="RF07: Notificações enviadas - Aprovação",
                entidade_afetada_id=solicitacao.id,
                detalhes=f"Solicitação aprovada por {aprovador.username} - "
                f"Notificações enviadas: {len(results)}",
            )

            return {
                "success": True,
                "notifications_sent": len(results),
                "results": results,
            }

        except Exception as e:
            logger.error(
                f"Erro ao notificar aprovação de solicitação {solicitacao.id}: {e}"
            )
            return {"success": False, "error": str(e)}

    def notify_event_created(
        self,
        solicitacao: Solicitacao,
        evento_gc: EventoGoogleCalendar,
        criador: Usuario,
    ) -> Dict[str, Any]:
        """
        Notifica criação de evento no Google Calendar pelo grupo controle.
        """
        try:
            results = []

            # 1. Notificar solicitante sobre evento criado
            result = self._notify_solicitante_evento_criado(solicitacao, evento_gc)
            results.append(result)

            # 2. Notificar formadores com link do Google Meet
            result = self._notify_formadores_evento_criado(solicitacao, evento_gc)
            results.append(result)

            # 3. Notificar superintendência (se aplicável) sobre conclusão
            if solicitacao.projeto.vinculado_superintendencia:
                result = self._notify_superintendencia_evento_criado(
                    solicitacao, evento_gc
                )
                results.append(result)

            # Log de auditoria
            LogAuditoria.objects.create(
                usuario=criador,
                acao="RF07: Notificações enviadas - Evento criado",
                entidade_afetada_id=solicitacao.id,
                detalhes=f"Evento criado no Google Calendar por {criador.username} - "
                f"ID evento: {evento_gc.provider_event_id} - "
                f"Notificações enviadas: {len(results)}",
            )

            return {
                "success": True,
                "notifications_sent": len(results),
                "results": results,
            }

        except Exception as e:
            logger.error(f"Erro ao notificar criação de evento {solicitacao.id}: {e}")
            return {"success": False, "error": str(e)}

    # ==================== MÉTODOS INTERNOS DE NOTIFICAÇÃO ====================

    def _notify_superintendencia_nova_solicitacao(
        self, solicitacao: Solicitacao
    ) -> Dict[str, Any]:
        """Notifica superintendência sobre nova solicitação para análise."""

        superintendencia_group = Group.objects.get(name="superintendencia")
        usuarios_super = superintendencia_group.user_set.filter(is_active=True)

        if not usuarios_super.exists():
            return {
                "success": False,
                "error": "Nenhum usuário ativo na superintendência",
            }

        # Criar notificações internas
        notificacoes_criadas = 0
        for usuario in usuarios_super:
            try:
                notificacao = Notificacao.objects.create(
                    usuario=usuario,
                    tipo="solicitacao_nova",
                    titulo="Nova solicitação para análise",
                    mensagem=f"Nova solicitação '{solicitacao.titulo_evento}' do projeto '{solicitacao.projeto.nome}' aguarda sua análise.",
                    link_acao=f"/aprovacoes/pendentes/",
                    entidade_relacionada_id=solicitacao.id,
                )

                # Log de comunicação
                self._log_communication(
                    tipo="notificacao_sistema",
                    destinatario=usuario,
                    grupo="superintendencia",
                    assunto="Nova solicitação para análise",
                    conteudo=f"Solicitação '{solicitacao.titulo_evento}' aguarda análise.",
                    entidade_id=solicitacao.id,
                    entidade_tipo="solicitacao",
                    status="enviado",
                )

                notificacoes_criadas += 1

            except Exception as e:
                logger.error(f"Erro ao criar notificação para {usuario.username}: {e}")

        return {
            "success": notificacoes_criadas > 0,
            "type": "superintendencia_nova_solicitacao",
            "notifications_created": notificacoes_criadas,
            "target_group": "superintendencia",
        }

    def _notify_controle_nova_solicitacao(
        self, solicitacao: Solicitacao
    ) -> Dict[str, Any]:
        """Notifica controle sobre solicitação que vai direto para PRE_AGENDA."""

        controle_group = Group.objects.get(name="controle")
        usuarios_controle = controle_group.user_set.filter(is_active=True)

        if not usuarios_controle.exists():
            return {"success": False, "error": "Nenhum usuário ativo no controle"}

        # Criar notificações internas
        notificacoes_criadas = 0
        for usuario in usuarios_controle:
            try:
                notificacao = Notificacao.objects.create(
                    usuario=usuario,
                    tipo="pre_agenda_nova",
                    titulo="Nova solicitação em pré-agenda",
                    mensagem=f"Solicitação '{solicitacao.titulo_evento}' está na pré-agenda para criação no Google Calendar.",
                    link_acao=f"/controle/pre-agenda/",
                    entidade_relacionada_id=solicitacao.id,
                )

                # Log de comunicação
                self._log_communication(
                    tipo="notificacao_sistema",
                    destinatario=usuario,
                    grupo="controle",
                    assunto="Nova solicitação em pré-agenda",
                    conteudo=f"Solicitação '{solicitacao.titulo_evento}' está na pré-agenda.",
                    entidade_id=solicitacao.id,
                    entidade_tipo="solicitacao",
                    status="enviado",
                )

                notificacoes_criadas += 1

            except Exception as e:
                logger.error(f"Erro ao criar notificação para {usuario.username}: {e}")

        return {
            "success": notificacoes_criadas > 0,
            "type": "controle_nova_solicitacao",
            "notifications_created": notificacoes_criadas,
            "target_group": "controle",
        }

    def _notify_solicitante_confirmacao(
        self, solicitacao: Solicitacao
    ) -> Dict[str, Any]:
        """Notifica solicitante sobre confirmação de recebimento da solicitação."""

        try:
            # Criar notificação interna
            notificacao = Notificacao.objects.create(
                usuario=solicitacao.usuario_solicitante,
                tipo="solicitacao_confirmacao",
                titulo="Solicitação recebida com sucesso",
                mensagem=f"Sua solicitação '{solicitacao.titulo_evento}' foi recebida e está sendo processada.",
                entidade_relacionada_id=solicitacao.id,
            )

            # Log de comunicação
            self._log_communication(
                tipo="notificacao_sistema",
                destinatario=solicitacao.usuario_solicitante,
                assunto="Solicitação recebida",
                conteudo=f"Solicitação '{solicitacao.titulo_evento}' recebida com sucesso.",
                entidade_id=solicitacao.id,
                entidade_tipo="solicitacao",
                status="enviado",
            )

            # Preparação para WhatsApp/SMS (se habilitado no futuro)
            if self.whatsapp_enabled or self.sms_enabled:
                self._prepare_mobile_notification(
                    usuario=solicitacao.usuario_solicitante,
                    tipo="confirmacao",
                    mensagem=f"✅ Solicitação '{solicitacao.titulo_evento}' recebida!",
                    entidade_id=solicitacao.id,
                )

            return {
                "success": True,
                "type": "solicitante_confirmacao",
                "notifications_created": 1,
                "recipient": solicitacao.usuario_solicitante.username,
            }

        except Exception as e:
            logger.error(
                f"Erro ao notificar solicitante {solicitacao.usuario_solicitante.username}: {e}"
            )
            return {"success": False, "error": str(e)}

    def _notify_solicitante_aprovacao(
        self, solicitacao: Solicitacao, aprovador: Usuario
    ) -> Dict[str, Any]:
        """Notifica solicitante sobre aprovação da solicitação."""

        try:
            # Criar notificação interna
            notificacao = Notificacao.objects.create(
                usuario=solicitacao.usuario_solicitante,
                tipo="solicitacao_aprovada",
                titulo="Solicitação aprovada! ✅",
                mensagem=f"Sua solicitação '{solicitacao.titulo_evento}' foi aprovada por {aprovador.get_full_name() or aprovador.username}.",
                entidade_relacionada_id=solicitacao.id,
            )

            # Log de comunicação
            self._log_communication(
                tipo="notificacao_sistema",
                destinatario=solicitacao.usuario_solicitante,
                assunto="Solicitação aprovada",
                conteudo=f"Solicitação '{solicitacao.titulo_evento}' aprovada por {aprovador.username}.",
                entidade_id=solicitacao.id,
                entidade_tipo="solicitacao",
                status="enviado",
            )

            # Preparação para WhatsApp/SMS
            if self.whatsapp_enabled or self.sms_enabled:
                self._prepare_mobile_notification(
                    usuario=solicitacao.usuario_solicitante,
                    tipo="aprovacao",
                    mensagem=f"🎉 Solicitação '{solicitacao.titulo_evento}' aprovada!",
                    entidade_id=solicitacao.id,
                )

            return {
                "success": True,
                "type": "solicitante_aprovacao",
                "notifications_created": 1,
                "recipient": solicitacao.usuario_solicitante.username,
            }

        except Exception as e:
            logger.error(
                f"Erro ao notificar aprovação para {solicitacao.usuario_solicitante.username}: {e}"
            )
            return {"success": False, "error": str(e)}

    def _notify_controle_pre_agenda(self, solicitacao: Solicitacao) -> Dict[str, Any]:
        """Notifica controle sobre solicitação aprovada que foi para PRE_AGENDA."""

        controle_group = Group.objects.get(name="controle")
        usuarios_controle = controle_group.user_set.filter(is_active=True)

        if not usuarios_controle.exists():
            return {"success": False, "error": "Nenhum usuário ativo no controle"}

        # Criar notificações internas
        notificacoes_criadas = 0
        for usuario in usuarios_controle:
            try:
                notificacao = Notificacao.objects.create(
                    usuario=usuario,
                    tipo="pre_agenda_aprovada",
                    titulo="Solicitação aprovada → Pré-agenda",
                    mensagem=f"Solicitação '{solicitacao.titulo_evento}' foi aprovada e está na pré-agenda.",
                    link_acao=f"/controle/pre-agenda/",
                    entidade_relacionada_id=solicitacao.id,
                )

                # Log de comunicação
                self._log_communication(
                    tipo="notificacao_sistema",
                    destinatario=usuario,
                    grupo="controle",
                    assunto="Solicitação aprovada → Pré-agenda",
                    conteudo=f"Solicitação '{solicitacao.titulo_evento}' aprovada e na pré-agenda.",
                    entidade_id=solicitacao.id,
                    entidade_tipo="solicitacao",
                    status="enviado",
                )

                notificacoes_criadas += 1

            except Exception as e:
                logger.error(f"Erro ao criar notificação para {usuario.username}: {e}")

        return {
            "success": notificacoes_criadas > 0,
            "type": "controle_pre_agenda",
            "notifications_created": notificacoes_criadas,
            "target_group": "controle",
        }

    def _notify_formadores_pre_evento(self, solicitacao: Solicitacao) -> Dict[str, Any]:
        """Notifica formadores sobre possível evento (ainda em PRE_AGENDA)."""

        formadores = solicitacao.formadores.filter(ativo=True)

        if not formadores.exists():
            return {"success": False, "error": "Nenhum formador ativo na solicitação"}

        # Criar notificações internas
        notificacoes_criadas = 0
        for formador in formadores:
            if formador.usuario:
                try:
                    notificacao = Notificacao.objects.create(
                        usuario=formador.usuario,
                        tipo="evento_preparacao",
                        titulo="Evento em preparação",
                        mensagem=f"O evento '{solicitacao.titulo_evento}' está sendo preparado e você foi designado como formador.",
                        entidade_relacionada_id=solicitacao.id,
                    )

                    # Log de comunicação
                    self._log_communication(
                        tipo="notificacao_sistema",
                        destinatario=formador.usuario,
                        grupo="formador",
                        assunto="Evento em preparação",
                        conteudo=f"Evento '{solicitacao.titulo_evento}' em preparação.",
                        entidade_id=solicitacao.id,
                        entidade_tipo="solicitacao",
                        status="enviado",
                    )

                    notificacoes_criadas += 1

                except Exception as e:
                    logger.error(
                        f"Erro ao criar notificação para formador {formador.usuario.username}: {e}"
                    )

        return {
            "success": notificacoes_criadas > 0,
            "type": "formadores_pre_evento",
            "notifications_created": notificacoes_criadas,
            "target_group": "formadores",
        }

    def _notify_formadores_evento_criado(
        self, solicitacao: Solicitacao, evento_gc: EventoGoogleCalendar
    ) -> Dict[str, Any]:
        """Notifica formadores sobre evento criado no Google Calendar com link do Meet."""

        formadores = solicitacao.formadores.filter(ativo=True)

        if not formadores.exists():
            return {"success": False, "error": "Nenhum formador ativo na solicitação"}

        # Criar notificações internas
        notificacoes_criadas = 0
        for formador in formadores:
            if formador.usuario:
                try:
                    notificacao = Notificacao.objects.create(
                        usuario=formador.usuario,
                        tipo="evento_confirmado",
                        titulo="Evento confirmado! 📅",
                        mensagem=f"O evento '{solicitacao.titulo_evento}' foi criado no Google Calendar.",
                        link_acao=evento_gc.html_link,
                        entidade_relacionada_id=solicitacao.id,
                    )

                    # Log de comunicação
                    self._log_communication(
                        tipo="notificacao_sistema",
                        destinatario=formador.usuario,
                        grupo="formador",
                        assunto="Evento confirmado",
                        conteudo=f"Evento '{solicitacao.titulo_evento}' criado no Google Calendar.",
                        entidade_id=solicitacao.id,
                        entidade_tipo="evento",
                        status="enviado",
                        metadados={
                            "google_calendar_link": evento_gc.html_link,
                            "meet_link": evento_gc.meet_link,
                        },
                    )

                    # Preparação para WhatsApp/SMS com link do Meet
                    if self.whatsapp_enabled or self.sms_enabled:
                        meet_info = (
                            f"\n🎥 Google Meet: {evento_gc.meet_link}"
                            if evento_gc.meet_link
                            else ""
                        )
                        self._prepare_mobile_notification(
                            usuario=formador.usuario,
                            tipo="evento_confirmado",
                            mensagem=f"📅 Evento '{solicitacao.titulo_evento}' confirmado!{meet_info}",
                            entidade_id=solicitacao.id,
                        )

                    notificacoes_criadas += 1

                except Exception as e:
                    logger.error(
                        f"Erro ao criar notificação para formador {formador.usuario.username}: {e}"
                    )

        return {
            "success": notificacoes_criadas > 0,
            "type": "formadores_evento_criado",
            "notifications_created": notificacoes_criadas,
            "target_group": "formadores",
        }

    def _notify_solicitante_evento_criado(
        self, solicitacao: Solicitacao, evento_gc: EventoGoogleCalendar
    ) -> Dict[str, Any]:
        """Notifica solicitante sobre evento criado no Google Calendar."""

        try:
            # Criar notificação interna
            notificacao = Notificacao.objects.create(
                usuario=solicitacao.usuario_solicitante,
                tipo="evento_criado",
                titulo="Evento criado com sucesso! 🎉",
                mensagem=f"Seu evento '{solicitacao.titulo_evento}' foi criado no Google Calendar com sucesso!",
                link_acao=evento_gc.html_link,
                entidade_relacionada_id=solicitacao.id,
            )

            # Log de comunicação
            self._log_communication(
                tipo="notificacao_sistema",
                destinatario=solicitacao.usuario_solicitante,
                assunto="Evento criado com sucesso",
                conteudo=f"Evento '{solicitacao.titulo_evento}' criado no Google Calendar.",
                entidade_id=solicitacao.id,
                entidade_tipo="evento",
                status="enviado",
                metadados={
                    "google_calendar_link": evento_gc.html_link,
                    "meet_link": evento_gc.meet_link,
                },
            )

            # Preparação para WhatsApp/SMS
            if self.whatsapp_enabled or self.sms_enabled:
                meet_info = (
                    f"\n🎥 Google Meet: {evento_gc.meet_link}"
                    if evento_gc.meet_link
                    else ""
                )
                self._prepare_mobile_notification(
                    usuario=solicitacao.usuario_solicitante,
                    tipo="evento_criado",
                    mensagem=f"🎉 Evento '{solicitacao.titulo_evento}' criado!{meet_info}",
                    entidade_id=solicitacao.id,
                )

            return {
                "success": True,
                "type": "solicitante_evento_criado",
                "notifications_created": 1,
                "recipient": solicitacao.usuario_solicitante.username,
            }

        except Exception as e:
            logger.error(
                f"Erro ao notificar solicitante {solicitacao.usuario_solicitante.username}: {e}"
            )
            return {"success": False, "error": str(e)}

    def _notify_superintendencia_evento_criado(
        self, solicitacao: Solicitacao, evento_gc: EventoGoogleCalendar
    ) -> Dict[str, Any]:
        """Notifica superintendência sobre conclusão do processo (evento criado)."""

        superintendencia_group = Group.objects.get(name="superintendencia")
        usuarios_super = superintendencia_group.user_set.filter(is_active=True)

        if not usuarios_super.exists():
            return {
                "success": False,
                "error": "Nenhum usuário ativo na superintendência",
            }

        # Criar notificações internas
        notificacoes_criadas = 0
        for usuario in usuarios_super:
            try:
                notificacao = Notificacao.objects.create(
                    usuario=usuario,
                    tipo="processo_concluido",
                    titulo="Processo concluído com sucesso ✅",
                    mensagem=f"A solicitação '{solicitacao.titulo_evento}' foi processada e o evento foi criado no Google Calendar.",
                    link_acao=evento_gc.html_link,
                    entidade_relacionada_id=solicitacao.id,
                )

                # Log de comunicação
                self._log_communication(
                    tipo="notificacao_sistema",
                    destinatario=usuario,
                    grupo="superintendencia",
                    assunto="Processo concluído",
                    conteudo=f"Solicitação '{solicitacao.titulo_evento}' processada e evento criado.",
                    entidade_id=solicitacao.id,
                    entidade_tipo="evento",
                    status="enviado",
                )

                notificacoes_criadas += 1

            except Exception as e:
                logger.error(f"Erro ao criar notificação para {usuario.username}: {e}")

        return {
            "success": notificacoes_criadas > 0,
            "type": "superintendencia_evento_criado",
            "notifications_created": notificacoes_criadas,
            "target_group": "superintendencia",
        }

    # ==================== PREPARAÇÃO WHATSAPP/SMS ====================

    def _prepare_mobile_notification(
        self, usuario: Usuario, tipo: str, mensagem: str, entidade_id: str
    ) -> None:
        """
        Prepara notificação para WhatsApp/SMS (para implementação futura).
        Registra no log de comunicações como 'pendente'.
        """
        try:
            # WhatsApp (se habilitado)
            if self.whatsapp_enabled and usuario.telefone:
                self._log_communication(
                    tipo="whatsapp",
                    destinatario=usuario,
                    endereco=usuario.telefone,
                    assunto=f"Sistema Aprender - {tipo}",
                    conteudo=mensagem,
                    entidade_id=entidade_id,
                    entidade_tipo="solicitacao",
                    status="pendente",  # Aguardando implementação
                    metadados={"preparado_para": "whatsapp_futuro"},
                )

            # SMS (se habilitado)
            if self.sms_enabled and usuario.telefone:
                self._log_communication(
                    tipo="sms",
                    destinatario=usuario,
                    endereco=usuario.telefone,
                    assunto=f"Sistema Aprender - {tipo}",
                    conteudo=mensagem,
                    entidade_id=entidade_id,
                    entidade_tipo="solicitacao",
                    status="pendente",  # Aguardando implementação
                    metadados={"preparado_para": "sms_futuro"},
                )

        except Exception as e:
            logger.error(
                f"Erro ao preparar notificação mobile para {usuario.username}: {e}"
            )

    # ==================== LOG DE COMUNICAÇÕES ====================

    def _log_communication(
        self,
        tipo: str,
        destinatario: Usuario,
        assunto: str,
        conteudo: str,
        entidade_id: str,
        entidade_tipo: str,
        status: str = "enviado",
        grupo: str = "",
        endereco: str = "",
        metadados: dict = None,
    ) -> None:
        """
        Registra comunicação no log (visível apenas para admin).
        """
        try:
            LogComunicacao.objects.create(
                usuario_remetente=None,  # Sistema
                usuario_destinatario=destinatario,
                grupo_destinatario=grupo,
                tipo_comunicacao=tipo,
                assunto=assunto,
                conteudo=conteudo,
                endereco_destinatario=endereco,
                status_envio=status,
                entidade_relacionada_id=entidade_id,
                entidade_relacionada_tipo=entidade_tipo,
                metadados=metadados,
                enviado_em=timezone.now() if status == "enviado" else None,
            )

        except Exception as e:
            logger.error(f"Erro ao registrar log de comunicação: {e}")

    # ==================== MÉTODOS UTILITÁRIOS ====================

    def get_user_notifications(self, usuario: Usuario, limit: int = 10) -> List[Dict]:
        """
        Retorna notificações do usuário para exibição no dashboard.
        """
        notifications = Notificacao.objects.filter(usuario=usuario).order_by(
            "-created_at"
        )[:limit]

        return [
            {
                "id": str(n.id),
                "tipo": n.tipo,
                "titulo": n.titulo,
                "mensagem": n.mensagem,
                "link_acao": n.link_acao,
                "lida": n.lida,
                "created_at": n.created_at.isoformat(),
                "tempo_relativo": self._get_relative_time(n.created_at),
            }
            for n in notifications
        ]

    def mark_notification_as_read(self, notification_id: str, usuario: Usuario) -> bool:
        """
        Marca notificação como lida.
        """
        try:
            notification = Notificacao.objects.get(id=notification_id, usuario=usuario)
            notification.lida = True
            notification.save(update_fields=["lida"])
            return True
        except Notificacao.DoesNotExist:
            return False

    def get_unread_count(self, usuario: Usuario) -> int:
        """
        Retorna quantidade de notificações não lidas do usuário.
        """
        return Notificacao.objects.filter(usuario=usuario, lida=False).count()

    def _get_relative_time(self, dt: datetime) -> str:
        """
        Retorna tempo relativo (ex: "há 2 minutos").
        """
        now = timezone.now()
        diff = now - dt

        if diff.days > 0:
            return f"há {diff.days} dia{'s' if diff.days > 1 else ''}"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"há {hours} hora{'s' if hours > 1 else ''}"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"há {minutes} minuto{'s' if minutes > 1 else ''}"
        else:
            return "agora mesmo"


# Funções de conveniência para usar nos views
def notify_new_solicitacao(solicitacao: Solicitacao) -> Dict[str, Any]:
    """
    Função de conveniência para notificar nova solicitação.
    """
    service = NotificationService()
    return service.notify_solicitacao_created(solicitacao)


def notify_solicitacao_approved(
    solicitacao: Solicitacao, aprovador: Usuario
) -> Dict[str, Any]:
    """
    Função de conveniência para notificar aprovação.
    """
    service = NotificationService()
    return service.notify_solicitacao_approved(solicitacao, aprovador)


def notify_event_created(
    solicitacao: Solicitacao, evento_gc: EventoGoogleCalendar, criador: Usuario
) -> Dict[str, Any]:
    """
    Função de conveniência para notificar evento criado.
    """
    service = NotificationService()
    return service.notify_event_created(solicitacao, evento_gc, criador)


def get_user_notifications(usuario: Usuario, limit: int = 10) -> List[Dict]:
    """
    Função de conveniência para obter notificações do usuário.
    """
    service = NotificationService()
    return service.get_user_notifications(usuario, limit)


def get_unread_notifications_count(usuario: Usuario) -> int:
    """
    Função de conveniência para obter contagem de não lidas.
    """
    service = NotificationService()
    return service.get_unread_count(usuario)
