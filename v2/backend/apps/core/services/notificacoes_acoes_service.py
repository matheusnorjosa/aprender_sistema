"""
Services for daily in-app notifications of action instances (issue #871).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportArgumentType=false

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING, Iterable

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.models import AcaoInstancia, AuditLog, NotificacaoInterna, Usuario
from apps.core.models.acoes_notificacao import (
    EstadoAcaoChoices,
    NivelNotificacaoChoices,
    PrioridadeNotificacaoChoices,
    StatusCicloChoices,
    TipoNotificacaoChoices,
)
from apps.core.services.business_calendar_service import BusinessCalendarService
from apps.core.services.prazo_engine_service import PrazoEngineService

if TYPE_CHECKING:
    from django.db.models import QuerySet


@dataclass(frozen=True)
class EscalonamentoRule:
    fase_disparo: str
    business_days_until_due: int
    tipo: str
    nivel: str
    prioridade: str


class EscalonamentoService:
    """
    Resolves notification/escalation phase from due-date and reference date.
    """

    RULES_BY_BUSINESS_DAYS_TO_DUE: dict[int, EscalonamentoRule] = {
        7: EscalonamentoRule(
            fase_disparo="D-7",
            business_days_until_due=7,
            tipo=TipoNotificacaoChoices.LEMBRETE,
            nivel=NivelNotificacaoChoices.RESPONSAVEL,
            prioridade=PrioridadeNotificacaoChoices.MEDIA,
        ),
        3: EscalonamentoRule(
            fase_disparo="D-3",
            business_days_until_due=3,
            tipo=TipoNotificacaoChoices.LEMBRETE,
            nivel=NivelNotificacaoChoices.RESPONSAVEL,
            prioridade=PrioridadeNotificacaoChoices.ALTA,
        ),
        1: EscalonamentoRule(
            fase_disparo="D-1",
            business_days_until_due=1,
            tipo=TipoNotificacaoChoices.LEMBRETE,
            nivel=NivelNotificacaoChoices.RESPONSAVEL,
            prioridade=PrioridadeNotificacaoChoices.ALTA,
        ),
        0: EscalonamentoRule(
            fase_disparo="D0",
            business_days_until_due=0,
            tipo=TipoNotificacaoChoices.VENCIMENTO,
            nivel=NivelNotificacaoChoices.RESPONSAVEL,
            prioridade=PrioridadeNotificacaoChoices.CRITICA,
        ),
        -1: EscalonamentoRule(
            fase_disparo="D+1",
            business_days_until_due=-1,
            tipo=TipoNotificacaoChoices.ESCALONAMENTO,
            nivel=NivelNotificacaoChoices.COORDENADOR,
            prioridade=PrioridadeNotificacaoChoices.CRITICA,
        ),
        -3: EscalonamentoRule(
            fase_disparo="D+3",
            business_days_until_due=-3,
            tipo=TipoNotificacaoChoices.ESCALONAMENTO,
            nivel=NivelNotificacaoChoices.GERENTE,
            prioridade=PrioridadeNotificacaoChoices.CRITICA,
        ),
    }

    @classmethod
    def resolve_rule(
        cls,
        action_instance: AcaoInstancia,
        *,
        reference_date: date,
    ) -> EscalonamentoRule | None:
        if action_instance.estado == EstadoAcaoChoices.CONCLUIDA:
            return None

        due_date = action_instance.data_vencimento
        if due_date is None:
            return None

        business_days_until_due = BusinessCalendarService.business_days_between(reference_date, due_date)
        return cls.RULES_BY_BUSINESS_DAYS_TO_DUE.get(business_days_until_due)


class NotificationService:
    """
    Creates in-app notifications with recipient resolution and deduplication.
    """

    ROLE_GROUPS_BY_LEVEL: dict[str, tuple[str, ...]] = {
        NivelNotificacaoChoices.RESPONSAVEL: ("Coordenador", "Gerente"),
        NivelNotificacaoChoices.COORDENADOR: ("Coordenador",),
        NivelNotificacaoChoices.GERENTE: ("Gerente",),
        NivelNotificacaoChoices.DAT: ("DAT",),
    }

    @classmethod
    def _active_users_for_executor_and_roles(
        cls,
        *,
        executor_group_ids: Iterable[int],
        role_group_names: Iterable[str],
    ) -> QuerySet[Usuario]:
        executor_user_ids = Usuario.objects.filter(
            is_active=True,
            groups__id__in=list(executor_group_ids),
        ).values_list("id", flat=True)
        return Usuario.objects.filter(
            is_active=True,
            id__in=executor_user_ids,
            groups__name__in=list(role_group_names),
        ).distinct()

    @classmethod
    def _active_users_by_roles(cls, *, role_group_names: Iterable[str]) -> QuerySet[Usuario]:
        return Usuario.objects.filter(
            is_active=True,
            groups__name__in=list(role_group_names),
        ).distinct()

    @classmethod
    def _resolve_recipients(
        cls,
        *,
        action_instance: AcaoInstancia,
        base_level: str,
    ) -> tuple[list[Usuario], str, bool]:
        executor_group_ids = list(
            action_instance.template.executores.filter(ativo=True).values_list("group_id", flat=True)
        )
        role_groups = cls.ROLE_GROUPS_BY_LEVEL.get(base_level, ("Coordenador", "Gerente"))

        primary_qs = cls._active_users_for_executor_and_roles(
            executor_group_ids=executor_group_ids,
            role_group_names=role_groups,
        )
        primary_users = list(primary_qs)
        if primary_users:
            return primary_users, base_level, False

        # Fallback deterministico:
        # 1) Para D+1 (coordenador), tenta gerente do mesmo executor
        if base_level == NivelNotificacaoChoices.COORDENADOR and executor_group_ids:
            manager_qs = cls._active_users_for_executor_and_roles(
                executor_group_ids=executor_group_ids,
                role_group_names=("Gerente",),
            )
            manager_users = list(manager_qs)
            if manager_users:
                return manager_users, NivelNotificacaoChoices.GERENTE, True

        # 2) Gerentes globais
        global_manager_users = list(cls._active_users_by_roles(role_group_names=("Gerente",)))
        if global_manager_users:
            return global_manager_users, NivelNotificacaoChoices.GERENTE, True

        # 3) Fallback final: DAT
        dat_users = list(cls._active_users_by_roles(role_group_names=("DAT",)))
        if dat_users:
            return dat_users, NivelNotificacaoChoices.DAT, True

        return [], base_level, True

    @classmethod
    def _build_notification_payload(
        cls,
        *,
        action_instance: AcaoInstancia,
        rule: EscalonamentoRule,
        nivel: str,
    ) -> tuple[str, str]:
        ciclo = action_instance.ciclo
        due = action_instance.data_vencimento.isoformat() if action_instance.data_vencimento else "-"
        titulo = f"[{rule.fase_disparo}] Acao {action_instance.ordem:02d} - {action_instance.template.nome}"
        mensagem = (
            f"Ação {action_instance.ordem:02d} no ciclo "
            f"{ciclo.projeto.nome}/{ciclo.municipio.nome} ({ciclo.semestre}/{ciclo.ano}) "
            f"com vencimento em {due}. Nível: {nivel}."
        )
        return titulo, mensagem

    @classmethod
    def dispatch_for_action(
        cls,
        *,
        action_instance: AcaoInstancia,
        rule: EscalonamentoRule,
        reference_date: date,
    ) -> dict[str, int | bool]:
        recipients, effective_level, fallback_used = cls._resolve_recipients(
            action_instance=action_instance,
            base_level=rule.nivel,
        )
        if not recipients:
            return {"created": 0, "deduplicated": 0, "fallback_used": int(fallback_used)}

        titulo, mensagem = cls._build_notification_payload(
            action_instance=action_instance,
            rule=rule,
            nivel=effective_level,
        )

        created = 0
        deduplicated = 0
        with transaction.atomic():
            for user in recipients:
                try:
                    _, was_created = NotificacaoInterna.objects.get_or_create(
                        destinatario=user,
                        acao_instancia=action_instance,
                        fase_disparo=rule.fase_disparo,
                        referencia_data=reference_date,
                        defaults={
                            "titulo": titulo,
                            "mensagem": mensagem,
                            "tipo": rule.tipo,
                            "nivel": effective_level,
                            "prioridade": rule.prioridade,
                        },
                    )
                except IntegrityError:
                    was_created = False

                if was_created:
                    created += 1
                else:
                    deduplicated += 1

        return {"created": created, "deduplicated": deduplicated, "fallback_used": int(fallback_used)}


class AcoesNotificacaoDailyService:
    """
    Daily processor for action reminders/escalations.
    """

    @classmethod
    def run(
        cls,
        *,
        reference_date: date | None = None,
    ) -> dict[str, object]:
        ref_date = reference_date or timezone.localdate()

        actions_qs = (
            AcaoInstancia.objects.select_related(
                "template",
                "ciclo",
                "ciclo__projeto",
                "ciclo__municipio",
            )
            .prefetch_related("template__executores")
            .filter(
                ciclo__status=StatusCicloChoices.EM_ANDAMENTO,
                data_vencimento__isnull=False,
                template__ativo=True,
            )
            .exclude(estado=EstadoAcaoChoices.CONCLUIDA)
            .order_by("id")
        )

        metrics: dict[str, object] = {
            "reference_date": ref_date.isoformat(),
            "actions_evaluated": 0,
            "actions_triggered": 0,
            "notifications_created": 0,
            "notifications_deduplicated": 0,
            "fallback_actions": 0,
            "phases": {},
        }
        phases_count: dict[str, int] = {}

        for action in actions_qs:
            metrics["actions_evaluated"] = int(metrics["actions_evaluated"]) + 1

            action = PrazoEngineService.recalculate_action(
                action,
                reference_date=ref_date,
                save=True,
            )
            if action.estado == EstadoAcaoChoices.CONCLUIDA:
                continue

            rule = EscalonamentoService.resolve_rule(action, reference_date=ref_date)
            if rule is None:
                continue

            result = NotificationService.dispatch_for_action(
                action_instance=action,
                rule=rule,
                reference_date=ref_date,
            )
            metrics["actions_triggered"] = int(metrics["actions_triggered"]) + 1
            metrics["notifications_created"] = int(metrics["notifications_created"]) + int(result["created"])
            metrics["notifications_deduplicated"] = int(metrics["notifications_deduplicated"]) + int(
                result["deduplicated"]
            )
            metrics["fallback_actions"] = int(metrics["fallback_actions"]) + int(result["fallback_used"])
            phases_count[rule.fase_disparo] = phases_count.get(rule.fase_disparo, 0) + 1

        metrics["phases"] = phases_count

        AuditLog.objects.create(
            usuario=None,
            action="ACOES_NOTIFICACOES_DAILY",
            model_name="AcaoInstancia",
            details=metrics,
        )
        return metrics
