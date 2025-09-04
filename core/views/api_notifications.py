"""
APIs de Notificações em Tempo Real
SEMANA 3 - DIA 4: Sistema de notificações e comunicações

Endpoints para:
1. ✅ Obter notificações do usuário (dashboard)
2. ✅ Marcar notificações como lidas
3. ✅ Contagem de não lidas (para badge)
4. ✅ Polling em tempo real
5. ✅ Logs de comunicação (apenas admin)
"""

import json
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from core.models import LogComunicacao, Notificacao, Usuario
from core.services.notifications_simplified import (
    get_unread_notifications_count,
    get_user_notifications,
)


@method_decorator(login_required, name="dispatch")
class UserNotificationsAPI(View):
    """
    API para obter notificações do usuário logado.
    GET: Lista notificações (para dashboard)
    """

    def get(self, request):
        """Retorna notificações do usuário para exibição no dashboard."""
        try:
            # Parâmetros
            limit = int(request.GET.get("limit", 10))
            limit = min(limit, 50)  # Máximo 50 por vez

            offset = int(request.GET.get("offset", 0))
            apenas_nao_lidas = request.GET.get("unread_only", "false").lower() == "true"

            # Query base
            notifications = Notificacao.objects.filter(usuario=request.user)

            # Filtro apenas não lidas
            if apenas_nao_lidas:
                notifications = notifications.filter(lida=False)

            # Paginação
            notifications = notifications.order_by("-created_at")[
                offset : offset + limit
            ]

            # Serializar
            data = []
            for n in notifications:
                data.append(
                    {
                        "id": str(n.id),
                        "tipo": n.tipo,
                        "tipo_display": n.get_tipo_display(),
                        "titulo": n.titulo,
                        "mensagem": n.mensagem,
                        "link_acao": n.link_acao,
                        "lida": n.lida,
                        "created_at": n.created_at.isoformat(),
                        "tempo_relativo": self._get_relative_time(n.created_at),
                        "icon": self._get_notification_icon(n.tipo),
                    }
                )

            # Contadores
            total_count = Notificacao.objects.filter(usuario=request.user).count()
            unread_count = Notificacao.objects.filter(
                usuario=request.user, lida=False
            ).count()

            return JsonResponse(
                {
                    "success": True,
                    "notifications": data,
                    "total_count": total_count,
                    "unread_count": unread_count,
                    "has_more": (offset + limit) < total_count,
                    "next_offset": (
                        offset + limit if (offset + limit) < total_count else None
                    ),
                }
            )

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)

    def _get_relative_time(self, dt):
        """Retorna tempo relativo."""
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

    def _get_notification_icon(self, tipo):
        """Retorna ícone baseado no tipo de notificação."""
        icons = {
            "solicitacao_nova": "bi-plus-circle",
            "solicitacao_confirmacao": "bi-check-circle",
            "solicitacao_aprovada": "bi-check-circle-fill text-success",
            "solicitacao_reprovada": "bi-x-circle-fill text-danger",
            "pre_agenda_nova": "bi-calendar-plus",
            "pre_agenda_aprovada": "bi-calendar-check",
            "evento_preparacao": "bi-hourglass-split",
            "evento_confirmado": "bi-calendar-event",
            "evento_criado": "bi-calendar-check-fill text-success",
            "evento_cancelado": "bi-calendar-x text-danger",
            "processo_concluido": "bi-check-all text-success",
            "sistema_manutencao": "bi-tools",
            "sistema_atualizacao": "bi-arrow-up-circle",
        }
        return icons.get(tipo, "bi-info-circle")


@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(login_required, name="dispatch")
class MarkNotificationReadAPI(View):
    """
    API para marcar notificação como lida.
    POST: Marcar como lida
    """

    def post(self, request):
        """Marca notificação como lida."""
        try:
            data = json.loads(request.body)
            notification_id = data.get("notification_id")

            if not notification_id:
                return JsonResponse(
                    {"success": False, "error": "ID da notificação é obrigatório"},
                    status=400,
                )

            # Buscar notificação do usuário
            try:
                notification = Notificacao.objects.get(
                    id=notification_id, usuario=request.user
                )

                if not notification.lida:
                    notification.lida = True
                    notification.save(update_fields=["lida"])

                # Nova contagem de não lidas
                unread_count = Notificacao.objects.filter(
                    usuario=request.user, lida=False
                ).count()

                return JsonResponse(
                    {
                        "success": True,
                        "message": "Notificação marcada como lida",
                        "unread_count": unread_count,
                    }
                )

            except Notificacao.DoesNotExist:
                return JsonResponse(
                    {"success": False, "error": "Notificação não encontrada"},
                    status=404,
                )

        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "error": "Dados JSON inválidos"}, status=400
            )
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)


@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(login_required, name="dispatch")
class MarkAllNotificationsReadAPI(View):
    """
    API para marcar todas as notificações como lidas.
    """

    def post(self, request):
        """Marca todas as notificações do usuário como lidas."""
        try:
            # Atualizar todas as não lidas
            updated_count = Notificacao.objects.filter(
                usuario=request.user, lida=False
            ).update(lida=True)

            return JsonResponse(
                {
                    "success": True,
                    "message": f"{updated_count} notificações marcadas como lidas",
                    "updated_count": updated_count,
                    "unread_count": 0,
                }
            )

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)


@method_decorator(login_required, name="dispatch")
class NotificationCountAPI(View):
    """
    API para obter apenas a contagem de notificações não lidas.
    Útil para polling rápido (atualização do badge).
    """

    def get(self, request):
        """Retorna contagem de notificações não lidas."""
        try:
            unread_count = Notificacao.objects.filter(
                usuario=request.user, lida=False
            ).count()

            return JsonResponse({"success": True, "unread_count": unread_count})

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)


@method_decorator(login_required, name="dispatch")
class RealtimeNotificationsAPI(View):
    """
    API para polling de notificações em tempo real.
    Retorna apenas notificações novas desde o último timestamp.
    """

    def get(self, request):
        """Retorna notificações novas desde timestamp."""
        try:
            # Timestamp da última verificação
            since_timestamp = request.GET.get("since")

            # Query base
            notifications = Notificacao.objects.filter(usuario=request.user)

            # Filtro por timestamp se fornecido
            if since_timestamp:
                try:
                    from datetime import datetime

                    since_dt = datetime.fromisoformat(
                        since_timestamp.replace("Z", "+00:00")
                    )
                    notifications = notifications.filter(created_at__gt=since_dt)
                except ValueError:
                    return JsonResponse(
                        {"success": False, "error": "Formato de timestamp inválido"},
                        status=400,
                    )

            # Ordenar e limitar
            notifications = notifications.order_by("-created_at")[:20]

            # Serializar
            data = []
            for n in notifications:
                data.append(
                    {
                        "id": str(n.id),
                        "tipo": n.tipo,
                        "tipo_display": n.get_tipo_display(),
                        "titulo": n.titulo,
                        "mensagem": n.mensagem,
                        "link_acao": n.link_acao,
                        "lida": n.lida,
                        "created_at": n.created_at.isoformat(),
                        "tempo_relativo": self._get_relative_time(n.created_at),
                        "icon": self._get_notification_icon(n.tipo),
                    }
                )

            # Contagem atual de não lidas
            unread_count = Notificacao.objects.filter(
                usuario=request.user, lida=False
            ).count()

            return JsonResponse(
                {
                    "success": True,
                    "new_notifications": data,
                    "unread_count": unread_count,
                    "server_timestamp": timezone.now().isoformat(),
                    "has_new": len(data) > 0,
                }
            )

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)

    def _get_relative_time(self, dt):
        """Retorna tempo relativo."""
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

    def _get_notification_icon(self, tipo):
        """Retorna ícone baseado no tipo de notificação."""
        icons = {
            "solicitacao_nova": "bi-plus-circle",
            "solicitacao_confirmacao": "bi-check-circle",
            "solicitacao_aprovada": "bi-check-circle-fill text-success",
            "solicitacao_reprovada": "bi-x-circle-fill text-danger",
            "pre_agenda_nova": "bi-calendar-plus",
            "pre_agenda_aprovada": "bi-calendar-check",
            "evento_preparacao": "bi-hourglass-split",
            "evento_confirmado": "bi-calendar-event",
            "evento_criado": "bi-calendar-check-fill text-success",
            "evento_cancelado": "bi-calendar-x text-danger",
            "processo_concluido": "bi-check-all text-success",
            "sistema_manutencao": "bi-tools",
            "sistema_atualizacao": "bi-arrow-up-circle",
        }
        return icons.get(tipo, "bi-info-circle")


# ==================== LOGS DE COMUNICAÇÃO (APENAS ADMIN) ====================


class CommunicationLogsAPI(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    API para visualizar logs de comunicação.
    Visível apenas para administradores.
    """

    permission_required = "core.view_logs_comunicacao"

    def get(self, request):
        """Retorna logs de comunicação (apenas admin)."""
        try:
            # Parâmetros de filtro
            limit = int(request.GET.get("limit", 20))
            limit = min(limit, 100)  # Máximo 100 por vez

            offset = int(request.GET.get("offset", 0))
            tipo_filter = request.GET.get("type", "")
            status_filter = request.GET.get("status", "")
            usuario_filter = request.GET.get("user", "")

            # Query base
            logs = LogComunicacao.objects.all()

            # Filtros
            if tipo_filter:
                logs = logs.filter(tipo_comunicacao=tipo_filter)

            if status_filter:
                logs = logs.filter(status_envio=status_filter)

            if usuario_filter:
                logs = logs.filter(
                    Q(usuario_destinatario__username__icontains=usuario_filter)
                    | Q(usuario_destinatario__first_name__icontains=usuario_filter)
                    | Q(usuario_destinatario__last_name__icontains=usuario_filter)
                )

            # Ordenar e paginar
            logs = logs.order_by("-created_at")[offset : offset + limit]

            # Serializar
            data = []
            for log in logs:
                data.append(
                    {
                        "id": str(log.id),
                        "tipo": log.tipo_comunicacao,
                        "tipo_display": log.get_tipo_comunicacao_display(),
                        "destinatario": (
                            {
                                "username": (
                                    log.usuario_destinatario.username
                                    if log.usuario_destinatario
                                    else None
                                ),
                                "nome": (
                                    log.usuario_destinatario.get_full_name()
                                    if log.usuario_destinatario
                                    else None
                                ),
                                "email": (
                                    log.usuario_destinatario.email
                                    if log.usuario_destinatario
                                    else None
                                ),
                            }
                            if log.usuario_destinatario
                            else None
                        ),
                        "grupo_destinatario": log.grupo_destinatario,
                        "endereco_destinatario": log.endereco_destinatario,
                        "assunto": log.assunto,
                        "conteudo": (
                            log.conteudo[:200] + "..."
                            if len(log.conteudo) > 200
                            else log.conteudo
                        ),
                        "conteudo_completo": log.conteudo,
                        "status": log.status_envio,
                        "status_display": log.get_status_envio_display(),
                        "erro_envio": log.erro_envio,
                        "created_at": log.created_at.isoformat(),
                        "enviado_em": (
                            log.enviado_em.isoformat() if log.enviado_em else None
                        ),
                        "entidade_relacionada": (
                            {
                                "id": (
                                    str(log.entidade_relacionada_id)
                                    if log.entidade_relacionada_id
                                    else None
                                ),
                                "tipo": log.entidade_relacionada_tipo,
                            }
                            if log.entidade_relacionada_id
                            else None
                        ),
                        "metadados": log.metadados,
                    }
                )

            # Estatísticas
            total_count = LogComunicacao.objects.count()

            stats = {
                "total": total_count,
                "por_tipo": dict(
                    LogComunicacao.objects.values("tipo_comunicacao")
                    .annotate(count=Count("id"))
                    .values_list("tipo_comunicacao", "count")
                ),
                "por_status": dict(
                    LogComunicacao.objects.values("status_envio")
                    .annotate(count=Count("id"))
                    .values_list("status_envio", "count")
                ),
                "ultimas_24h": LogComunicacao.objects.filter(
                    created_at__gte=timezone.now() - timedelta(days=1)
                ).count(),
            }

            return JsonResponse(
                {
                    "success": True,
                    "logs": data,
                    "total_count": total_count,
                    "has_more": (offset + limit) < total_count,
                    "next_offset": (
                        offset + limit if (offset + limit) < total_count else None
                    ),
                    "stats": stats,
                }
            )

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)


class CommunicationStatsAPI(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    API para estatísticas de comunicações (apenas admin).
    """

    permission_required = "core.view_logs_comunicacao"

    def get(self, request):
        """Retorna estatísticas de comunicações."""
        try:
            # Estatísticas gerais
            now = timezone.now()

            stats = {
                "total_comunicacoes": LogComunicacao.objects.count(),
                "ultimas_24h": LogComunicacao.objects.filter(
                    created_at__gte=now - timedelta(days=1)
                ).count(),
                "ultima_semana": LogComunicacao.objects.filter(
                    created_at__gte=now - timedelta(days=7)
                ).count(),
                "ultimo_mes": LogComunicacao.objects.filter(
                    created_at__gte=now - timedelta(days=30)
                ).count(),
                # Por tipo
                "por_tipo": dict(
                    LogComunicacao.objects.values("tipo_comunicacao")
                    .annotate(count=Count("id"))
                    .values_list("tipo_comunicacao", "count")
                ),
                # Por status
                "por_status": dict(
                    LogComunicacao.objects.values("status_envio")
                    .annotate(count=Count("id"))
                    .values_list("status_envio", "count")
                ),
                # Usuários mais ativos (destinatários)
                "usuarios_mais_notificados": list(
                    LogComunicacao.objects.filter(usuario_destinatario__isnull=False)
                    .values(
                        "usuario_destinatario__username",
                        "usuario_destinatario__first_name",
                    )
                    .annotate(count=Count("id"))
                    .order_by("-count")[:10]
                ),
                # Grupos mais ativos
                "grupos_mais_notificados": list(
                    LogComunicacao.objects.exclude(grupo_destinatario="")
                    .values("grupo_destinatario")
                    .annotate(count=Count("id"))
                    .order_by("-count")[:10]
                ),
            }

            return JsonResponse({"success": True, "stats": stats})

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)
