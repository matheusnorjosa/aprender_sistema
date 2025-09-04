"""
Sistema de Notificações do Sistema Aprender
SEMANA 3 - DIA 4: Implementação completa de notificações e comunicações

Sistema responsável por:
1. Notificações em tempo real (WebSocket/polling)
2. E-mails automáticos para mudanças de status
3. Preparação para WhatsApp/SMS
4. Logs de comunicações
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from django.core.mail import send_mail, send_mass_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import Group

from core.models import (
    Usuario, Solicitacao, LogAuditoria, SolicitacaoStatus, 
    EventoGoogleCalendar, Notificacao, LogComunicacao
)

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Serviço central de notificações do sistema.
    Gerencia todos os tipos de comunicação com usuários.
    """
    
    def __init__(self):
        self.email_enabled = getattr(settings, 'NOTIFICATION_EMAIL_ENABLED', True)
        self.sms_enabled = getattr(settings, 'NOTIFICATION_SMS_ENABLED', False)
        self.whatsapp_enabled = getattr(settings, 'NOTIFICATION_WHATSAPP_ENABLED', False)
    
    # ==================== NOTIFICAÇÕES DE SOLICITAÇÃO ====================
    
    def notify_solicitacao_created(self, solicitacao: Solicitacao) -> Dict[str, Any]:
        """
        Notifica criação de nova solicitação.
        
        Fluxo:
        1. Se projeto vinculado à superintendência → notificar superintendência
        2. Se projeto não vinculado → vai direto para controle (PRE_AGENDA)
        """
        try:
            results = []
            
            # Nova lógica baseada em setores
            requer_aprovacao = (
                solicitacao.projeto.setor and solicitacao.projeto.setor.vinculado_superintendencia
            ) if solicitacao.projeto.setor else solicitacao.projeto.vinculado_superintendencia
            
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
                        f"Notificações enviadas: {len(results)}"
            )
            
            return {
                'success': True,
                'notifications_sent': len(results),
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Erro ao notificar criação de solicitação {solicitacao.id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def notify_solicitacao_approved(self, solicitacao: Solicitacao, aprovador: Usuario) -> Dict[str, Any]:
        """
        Notifica aprovação de solicitação pela superintendência.
        
        Fluxo: Superintendência aprova → PRE_AGENDA → notificar controle
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
                        f"Notificações enviadas: {len(results)}"
            )
            
            return {
                'success': True,
                'notifications_sent': len(results),
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Erro ao notificar aprovação de solicitação {solicitacao.id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def notify_solicitacao_rejected(self, solicitacao: Solicitacao, reprovador: Usuario, motivo: str = '') -> Dict[str, Any]:
        """
        Notifica reprovação de solicitação.
        """
        try:
            results = []
            
            # 1. Notificar solicitante sobre reprovação
            result = self._notify_solicitante_reprovacao(solicitacao, reprovador, motivo)
            results.append(result)
            
            # 2. Se havia formadores envolvidos, notificar sobre cancelamento
            if solicitacao.formadores.exists():
                result = self._notify_formadores_cancelamento(solicitacao, motivo)
                results.append(result)
            
            # Log de auditoria
            LogAuditoria.objects.create(
                usuario=reprovador,
                acao="RF07: Notificações enviadas - Reprovação",
                entidade_afetada_id=solicitacao.id,
                detalhes=f"Solicitação reprovada por {reprovador.username} - "
                        f"Motivo: {motivo} - Notificações enviadas: {len(results)}"
            )
            
            return {
                'success': True,
                'notifications_sent': len(results),
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Erro ao notificar reprovação de solicitação {solicitacao.id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # ==================== NOTIFICAÇÕES DE GOOGLE CALENDAR ====================
    
    def notify_event_created(self, solicitacao: Solicitacao, evento_gc: EventoGoogleCalendar, criador: Usuario) -> Dict[str, Any]:
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
                result = self._notify_superintendencia_evento_criado(solicitacao, evento_gc)
                results.append(result)
            
            # Log de auditoria
            LogAuditoria.objects.create(
                usuario=criador,
                acao="RF07: Notificações enviadas - Evento criado",
                entidade_afetada_id=solicitacao.id,
                detalhes=f"Evento criado no Google Calendar por {criador.username} - "
                        f"ID evento: {evento_gc.provider_event_id} - "
                        f"Notificações enviadas: {len(results)}"
            )
            
            return {
                'success': True,
                'notifications_sent': len(results),
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Erro ao notificar criação de evento {solicitacao.id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # ==================== MÉTODOS INTERNOS DE NOTIFICAÇÃO ====================
    
    def _notify_superintendencia_nova_solicitacao(self, solicitacao: Solicitacao) -> Dict[str, Any]:
        """Notifica superintendência sobre nova solicitação para análise."""
        
        superintendencia_group = Group.objects.get(name='superintendencia')
        usuarios_super = superintendencia_group.user_set.filter(is_active=True)
        
        if not usuarios_super.exists():
            return {'success': False, 'error': 'Nenhum usuário ativo na superintendência'}
        
        # Template de e-mail
        subject = f"[SISTEMA APRENDER] Nova Solicitação para Análise - {solicitacao.titulo_evento}"
        
        context = {
            'solicitacao': solicitacao,
            'url_aprovacao': f"{settings.BASE_URL}/aprovacoes/pendentes/",
            'projeto_vinculado': True
        }
        
        html_message = render_to_string('core/emails/nova_solicitacao_superintendencia.html', context)
        plain_message = strip_tags(html_message)
        
        # Enviar para todos da superintendência
        emails_sent = 0
        for usuario in usuarios_super:
            if usuario.email:
                try:
                    send_mail(
                        subject=subject,
                        message=plain_message,
                        html_message=html_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[usuario.email],
                        fail_silently=False
                    )
                    
                    # Criar notificação no sistema
                    Notificacao.objects.create(
                        usuario=usuario,
                        tipo='solicitacao_nova',
                        titulo="Nova solicitação para análise",
                        mensagem=f"Nova solicitação '{solicitacao.titulo_evento}' aguarda sua análise.",
                        link_acao=f"/aprovacoes/pendentes/",
                        entidade_relacionada_id=solicitacao.id
                    )
                    
                    emails_sent += 1
                    
                except Exception as e:
                    logger.error(f"Erro ao enviar e-mail para {usuario.email}: {e}")
        
        return {
            'success': emails_sent > 0,
            'type': 'superintendencia_nova_solicitacao',
            'emails_sent': emails_sent,
            'target_group': 'superintendencia'
        }
    
    def _notify_controle_nova_solicitacao(self, solicitacao: Solicitacao) -> Dict[str, Any]:
        """Notifica controle sobre solicitação que vai direto para PRE_AGENDA."""
        
        controle_group = Group.objects.get(name='controle')
        usuarios_controle = controle_group.user_set.filter(is_active=True)
        
        if not usuarios_controle.exists():
            return {'success': False, 'error': 'Nenhum usuário ativo no controle'}
        
        # Template de e-mail
        subject = f"[SISTEMA APRENDER] Nova Solicitação em Pré-Agenda - {solicitacao.titulo_evento}"
        
        context = {
            'solicitacao': solicitacao,
            'url_pre_agenda': f"{settings.BASE_URL}/controle/pre-agenda/",
            'projeto_direto': True
        }
        
        html_message = render_to_string('core/emails/nova_solicitacao_controle.html', context)
        plain_message = strip_tags(html_message)
        
        # Enviar para todos do controle
        emails_sent = 0
        for usuario in usuarios_controle:
            if usuario.email:
                try:
                    send_mail(
                        subject=subject,
                        message=plain_message,
                        html_message=html_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[usuario.email],
                        fail_silently=False
                    )
                    
                    # Criar notificação no sistema
                    Notificacao.objects.create(
                        usuario=usuario,
                        tipo='pre_agenda_nova',
                        titulo="Nova solicitação em pré-agenda",
                        mensagem=f"Solicitação '{solicitacao.titulo_evento}' está na pré-agenda para criação no Google Calendar.",
                        link_acao=f"/controle/pre-agenda/",
                        entidade_relacionada_id=solicitacao.id
                    )
                    
                    emails_sent += 1
                    
                except Exception as e:
                    logger.error(f"Erro ao enviar e-mail para {usuario.email}: {e}")
        
        return {
            'success': emails_sent > 0,
            'type': 'controle_nova_solicitacao',
            'emails_sent': emails_sent,
            'target_group': 'controle'
        }
    
    def _notify_solicitante_confirmacao(self, solicitacao: Solicitacao) -> Dict[str, Any]:
        """Notifica solicitante sobre confirmação de recebimento da solicitação."""
        
        if not solicitacao.usuario_solicitante.email:
            return {'success': False, 'error': 'Solicitante não possui e-mail'}
        
        # Template de e-mail
        subject = f"[SISTEMA APRENDER] Solicitação Recebida - {solicitacao.titulo_evento}"
        
        context = {
            'solicitacao': solicitacao,
            'fluxo_superintendencia': solicitacao.projeto.vinculado_superintendencia,
            'usuario': solicitacao.usuario_solicitante
        }
        
        html_message = render_to_string('core/emails/confirmacao_solicitacao.html', context)
        plain_message = strip_tags(html_message)
        
        try:
            send_mail(
                subject=subject,
                message=plain_message,
                html_message=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[solicitacao.usuario_solicitante.email],
                fail_silently=False
            )
            
            # Criar notificação no sistema
            Notificacao.objects.create(
                usuario=solicitacao.usuario_solicitante,
                tipo='solicitacao_confirmacao',
                titulo="Solicitação recebida com sucesso",
                mensagem=f"Sua solicitação '{solicitacao.titulo_evento}' foi recebida e está sendo processada.",
                entidade_relacionada_id=solicitacao.id
            )
            
            return {
                'success': True,
                'type': 'solicitante_confirmacao',
                'emails_sent': 1,
                'recipient': solicitacao.usuario_solicitante.email
            }
            
        except Exception as e:
            logger.error(f"Erro ao enviar confirmação para solicitante {solicitacao.usuario_solicitante.email}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _notify_solicitante_aprovacao(self, solicitacao: Solicitacao, aprovador: Usuario) -> Dict[str, Any]:
        """Notifica solicitante sobre aprovação da solicitação."""
        
        if not solicitacao.usuario_solicitante.email:
            return {'success': False, 'error': 'Solicitante não possui e-mail'}
        
        # Template de e-mail
        subject = f"[SISTEMA APRENDER] ✅ Solicitação Aprovada - {solicitacao.titulo_evento}"
        
        context = {
            'solicitacao': solicitacao,
            'aprovador': aprovador,
            'usuario': solicitacao.usuario_solicitante
        }
        
        html_message = render_to_string('core/emails/solicitacao_aprovada.html', context)
        plain_message = strip_tags(html_message)
        
        try:
            send_mail(
                subject=subject,
                message=plain_message,
                html_message=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[solicitacao.usuario_solicitante.email],
                fail_silently=False
            )
            
            # Criar notificação no sistema
            Notificacao.objects.create(
                usuario=solicitacao.usuario_solicitante,
                tipo='solicitacao_aprovada',
                titulo="Solicitação aprovada! ✅",
                mensagem=f"Sua solicitação '{solicitacao.titulo_evento}' foi aprovada por {aprovador.get_full_name() or aprovador.username}.",
                entidade_relacionada_id=solicitacao.id
            )
            
            return {
                'success': True,
                'type': 'solicitante_aprovacao',
                'emails_sent': 1,
                'recipient': solicitacao.usuario_solicitante.email
            }
            
        except Exception as e:
            logger.error(f"Erro ao enviar aprovação para solicitante {solicitacao.usuario_solicitante.email}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _notify_solicitante_reprovacao(self, solicitacao: Solicitacao, reprovador: Usuario, motivo: str) -> Dict[str, Any]:
        """Notifica solicitante sobre reprovação da solicitação."""
        
        if not solicitacao.usuario_solicitante.email:
            return {'success': False, 'error': 'Solicitante não possui e-mail'}
        
        # Template de e-mail
        subject = f"[SISTEMA APRENDER] ❌ Solicitação Não Aprovada - {solicitacao.titulo_evento}"
        
        context = {
            'solicitacao': solicitacao,
            'reprovador': reprovador,
            'motivo': motivo,
            'usuario': solicitacao.usuario_solicitante
        }
        
        html_message = render_to_string('core/emails/solicitacao_reprovada.html', context)
        plain_message = strip_tags(html_message)
        
        try:
            send_mail(
                subject=subject,
                message=plain_message,
                html_message=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[solicitacao.usuario_solicitante.email],
                fail_silently=False
            )
            
            # Criar notificação no sistema
            Notificacao.objects.create(
                usuario=solicitacao.usuario_solicitante,
                tipo='solicitacao_reprovada',
                titulo="Solicitação não aprovada ❌",
                mensagem=f"Sua solicitação '{solicitacao.titulo_evento}' não foi aprovada. Motivo: {motivo}",
                entidade_relacionada_id=solicitacao.id
            )
            
            return {
                'success': True,
                'type': 'solicitante_reprovacao',
                'emails_sent': 1,
                'recipient': solicitacao.usuario_solicitante.email
            }
            
        except Exception as e:
            logger.error(f"Erro ao enviar reprovação para solicitante {solicitacao.usuario_solicitante.email}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _notify_controle_pre_agenda(self, solicitacao: Solicitacao) -> Dict[str, Any]:
        """Notifica controle sobre solicitação aprovada que foi para PRE_AGENDA."""
        
        controle_group = Group.objects.get(name='controle')
        usuarios_controle = controle_group.user_set.filter(is_active=True)
        
        if not usuarios_controle.exists():
            return {'success': False, 'error': 'Nenhum usuário ativo no controle'}
        
        # Template de e-mail
        subject = f"[SISTEMA APRENDER] Solicitação Aprovada → Pré-Agenda - {solicitacao.titulo_evento}"
        
        context = {
            'solicitacao': solicitacao,
            'url_pre_agenda': f"{settings.BASE_URL}/controle/pre-agenda/",
        }
        
        html_message = render_to_string('core/emails/aprovacao_para_pre_agenda.html', context)
        plain_message = strip_tags(html_message)
        
        # Enviar para todos do controle
        emails_sent = 0
        for usuario in usuarios_controle:
            if usuario.email:
                try:
                    send_mail(
                        subject=subject,
                        message=plain_message,
                        html_message=html_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[usuario.email],
                        fail_silently=False
                    )
                    
                    # Criar notificação no sistema
                    Notificacao.objects.create(
                        usuario=usuario,
                        tipo='pre_agenda_aprovada',
                        titulo="Solicitação aprovada → Pré-agenda",
                        mensagem=f"Solicitação '{solicitacao.titulo_evento}' foi aprovada e está na pré-agenda.",
                        link_acao=f"/controle/pre-agenda/",
                        entidade_relacionada_id=solicitacao.id
                    )
                    
                    emails_sent += 1
                    
                except Exception as e:
                    logger.error(f"Erro ao enviar e-mail para {usuario.email}: {e}")
        
        return {
            'success': emails_sent > 0,
            'type': 'controle_pre_agenda',
            'emails_sent': emails_sent,
            'target_group': 'controle'
        }
    
    def _notify_formadores_pre_evento(self, solicitacao: Solicitacao) -> Dict[str, Any]:
        """Notifica formadores sobre possível evento (ainda em PRE_AGENDA)."""
        
        formadores = solicitacao.formadores.filter(ativo=True)
        
        if not formadores.exists():
            return {'success': False, 'error': 'Nenhum formador ativo na solicitação'}
        
        # Template de e-mail
        subject = f"[SISTEMA APRENDER] Evento em Preparação - {solicitacao.titulo_evento}"
        
        emails_sent = 0
        for formador in formadores:
            if formador.usuario and formador.usuario.email:
                try:
                    context = {
                        'solicitacao': solicitacao,
                        'formador': formador,
                        'usuario': formador.usuario
                    }
                    
                    html_message = render_to_string('core/emails/formador_pre_evento.html', context)
                    plain_message = strip_tags(html_message)
                    
                    send_mail(
                        subject=subject,
                        message=plain_message,
                        html_message=html_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[formador.usuario.email],
                        fail_silently=False
                    )
                    
                    # Criar notificação no sistema
                    Notificacao.objects.create(
                        usuario=formador.usuario,
                        tipo='evento_preparacao',
                        titulo="Evento em preparação",
                        mensagem=f"O evento '{solicitacao.titulo_evento}' está sendo preparado e você foi designado como formador.",
                        entidade_relacionada_id=solicitacao.id
                    )
                    
                    emails_sent += 1
                    
                except Exception as e:
                    logger.error(f"Erro ao enviar e-mail para formador {formador.usuario.email}: {e}")
        
        return {
            'success': emails_sent > 0,
            'type': 'formadores_pre_evento',
            'emails_sent': emails_sent,
            'target_group': 'formadores'
        }
    
    def _notify_formadores_evento_criado(self, solicitacao: Solicitacao, evento_gc: EventoGoogleCalendar) -> Dict[str, Any]:
        """Notifica formadores sobre evento criado no Google Calendar com link do Meet."""
        
        formadores = solicitacao.formadores.filter(ativo=True)
        
        if not formadores.exists():
            return {'success': False, 'error': 'Nenhum formador ativo na solicitação'}
        
        # Template de e-mail
        subject = f"[SISTEMA APRENDER] 📅 Evento Confirmado - {solicitacao.titulo_evento}"
        
        emails_sent = 0
        for formador in formadores:
            if formador.usuario and formador.usuario.email:
                try:
                    context = {
                        'solicitacao': solicitacao,
                        'evento_gc': evento_gc,
                        'formador': formador,
                        'usuario': formador.usuario
                    }
                    
                    html_message = render_to_string('core/emails/formador_evento_criado.html', context)
                    plain_message = strip_tags(html_message)
                    
                    send_mail(
                        subject=subject,
                        message=plain_message,
                        html_message=html_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[formador.usuario.email],
                        fail_silently=False
                    )
                    
                    # Criar notificação no sistema
                    Notificacao.objects.create(
                        usuario=formador.usuario,
                        tipo='evento_confirmado',
                        titulo="Evento confirmado! 📅",
                        mensagem=f"O evento '{solicitacao.titulo_evento}' foi criado no Google Calendar.",
                        link_acao=evento_gc.html_link,
                        entidade_relacionada_id=solicitacao.id
                    )
                    
                    emails_sent += 1
                    
                except Exception as e:
                    logger.error(f"Erro ao enviar e-mail para formador {formador.usuario.email}: {e}")
        
        return {
            'success': emails_sent > 0,
            'type': 'formadores_evento_criado',
            'emails_sent': emails_sent,
            'target_group': 'formadores'
        }
    
    def _notify_solicitante_evento_criado(self, solicitacao: Solicitacao, evento_gc: EventoGoogleCalendar) -> Dict[str, Any]:
        """Notifica solicitante sobre evento criado no Google Calendar."""
        
        if not solicitacao.usuario_solicitante.email:
            return {'success': False, 'error': 'Solicitante não possui e-mail'}
        
        # Template de e-mail
        subject = f"[SISTEMA APRENDER] 🎉 Evento Confirmado no Google Calendar - {solicitacao.titulo_evento}"
        
        context = {
            'solicitacao': solicitacao,
            'evento_gc': evento_gc,
            'usuario': solicitacao.usuario_solicitante
        }
        
        html_message = render_to_string('core/emails/solicitante_evento_criado.html', context)
        plain_message = strip_tags(html_message)
        
        try:
            send_mail(
                subject=subject,
                message=plain_message,
                html_message=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[solicitacao.usuario_solicitante.email],
                fail_silently=False
            )
            
            # Criar notificação no sistema
            Notificacao.objects.create(
                usuario=solicitacao.usuario_solicitante,
                tipo='evento_criado',
                titulo="Evento criado com sucesso! 🎉",
                mensagem=f"Seu evento '{solicitacao.titulo_evento}' foi criado no Google Calendar com sucesso!",
                link_acao=evento_gc.html_link,
                entidade_relacionada_id=solicitacao.id
            )
            
            return {
                'success': True,
                'type': 'solicitante_evento_criado',
                'emails_sent': 1,
                'recipient': solicitacao.usuario_solicitante.email
            }
            
        except Exception as e:
            logger.error(f"Erro ao enviar confirmação de evento para solicitante {solicitacao.usuario_solicitante.email}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _notify_superintendencia_evento_criado(self, solicitacao: Solicitacao, evento_gc: EventoGoogleCalendar) -> Dict[str, Any]:
        """Notifica superintendência sobre conclusão do processo (evento criado)."""
        
        superintendencia_group = Group.objects.get(name='superintendencia')
        usuarios_super = superintendencia_group.user_set.filter(is_active=True)
        
        if not usuarios_super.exists():
            return {'success': False, 'error': 'Nenhum usuário ativo na superintendência'}
        
        # Template de e-mail
        subject = f"[SISTEMA APRENDER] ✅ Processo Concluído - {solicitacao.titulo_evento}"
        
        context = {
            'solicitacao': solicitacao,
            'evento_gc': evento_gc,
        }
        
        html_message = render_to_string('core/emails/superintendencia_evento_criado.html', context)
        plain_message = strip_tags(html_message)
        
        # Enviar para todos da superintendência
        emails_sent = 0
        for usuario in usuarios_super:
            if usuario.email:
                try:
                    send_mail(
                        subject=subject,
                        message=plain_message,
                        html_message=html_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[usuario.email],
                        fail_silently=False
                    )
                    
                    # Criar notificação no sistema
                    Notificacao.objects.create(
                        usuario=usuario,
                        tipo='processo_concluido',
                        titulo="Processo concluído com sucesso ✅",
                        mensagem=f"A solicitação '{solicitacao.titulo_evento}' foi processada e o evento foi criado no Google Calendar.",
                        link_acao=evento_gc.html_link,
                        entidade_relacionada_id=solicitacao.id
                    )
                    
                    emails_sent += 1
                    
                except Exception as e:
                    logger.error(f"Erro ao enviar e-mail para {usuario.email}: {e}")
        
        return {
            'success': emails_sent > 0,
            'type': 'superintendencia_evento_criado',
            'emails_sent': emails_sent,
            'target_group': 'superintendencia'
        }
    
    def _notify_formadores_cancelamento(self, solicitacao: Solicitacao, motivo: str) -> Dict[str, Any]:
        """Notifica formadores sobre cancelamento de evento."""
        
        formadores = solicitacao.formadores.filter(ativo=True)
        
        if not formadores.exists():
            return {'success': False, 'error': 'Nenhum formador ativo na solicitação'}
        
        # Template de e-mail
        subject = f"[SISTEMA APRENDER] ❌ Evento Cancelado - {solicitacao.titulo_evento}"
        
        emails_sent = 0
        for formador in formadores:
            if formador.usuario and formador.usuario.email:
                try:
                    context = {
                        'solicitacao': solicitacao,
                        'formador': formador,
                        'motivo': motivo,
                        'usuario': formador.usuario
                    }
                    
                    html_message = render_to_string('core/emails/formador_evento_cancelado.html', context)
                    plain_message = strip_tags(html_message)
                    
                    send_mail(
                        subject=subject,
                        message=plain_message,
                        html_message=html_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[formador.usuario.email],
                        fail_silently=False
                    )
                    
                    # Criar notificação no sistema
                    Notificacao.objects.create(
                        usuario=formador.usuario,
                        tipo='evento_cancelado',
                        titulo="Evento cancelado ❌",
                        mensagem=f"O evento '{solicitacao.titulo_evento}' foi cancelado. Motivo: {motivo}",
                        entidade_relacionada_id=solicitacao.id
                    )
                    
                    emails_sent += 1
                    
                except Exception as e:
                    logger.error(f"Erro ao enviar e-mail para formador {formador.usuario.email}: {e}")
        
        return {
            'success': emails_sent > 0,
            'type': 'formadores_cancelamento',
            'emails_sent': emails_sent,
            'target_group': 'formadores'
        }
    
    # ==================== MÉTODOS UTILITÁRIOS ====================
    
    def get_user_notifications(self, usuario: Usuario, limit: int = 10) -> List[Dict]:
        """
        Retorna notificações do usuário para exibição no dashboard.
        """
        notifications = Notificacao.objects.filter(
            usuario=usuario
        ).order_by('-created_at')[:limit]
        
        return [
            {
                'id': str(n.id),
                'tipo': n.tipo,
                'titulo': n.titulo,
                'mensagem': n.mensagem,
                'link_acao': n.link_acao,
                'lida': n.lida,
                'created_at': n.created_at.isoformat(),
                'tempo_relativo': self._get_relative_time(n.created_at)
            }
            for n in notifications
        ]
    
    def mark_notification_as_read(self, notification_id: str, usuario: Usuario) -> bool:
        """
        Marca notificação como lida.
        """
        try:
            notification = Notificacao.objects.get(
                id=notification_id,
                usuario=usuario
            )
            notification.lida = True
            notification.save(update_fields=['lida'])
            return True
        except Notificacao.DoesNotExist:
            return False
    
    def get_unread_count(self, usuario: Usuario) -> int:
        """
        Retorna quantidade de notificações não lidas do usuário.
        """
        return Notificacao.objects.filter(
            usuario=usuario,
            lida=False
        ).count()
    
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


def notify_solicitacao_approved(solicitacao: Solicitacao, aprovador: Usuario) -> Dict[str, Any]:
    """
    Função de conveniência para notificar aprovação.
    """
    service = NotificationService()
    return service.notify_solicitacao_approved(solicitacao, aprovador)


def notify_solicitacao_rejected(solicitacao: Solicitacao, reprovador: Usuario, motivo: str = '') -> Dict[str, Any]:
    """
    Função de conveniência para notificar reprovação.
    """
    service = NotificationService()
    return service.notify_solicitacao_rejected(solicitacao, reprovador, motivo)


def notify_event_created(solicitacao: Solicitacao, evento_gc: EventoGoogleCalendar, criador: Usuario) -> Dict[str, Any]:
    """
    Função de conveniência para notificar evento criado.
    """
    service = NotificationService()
    return service.notify_event_created(solicitacao, evento_gc, criador)