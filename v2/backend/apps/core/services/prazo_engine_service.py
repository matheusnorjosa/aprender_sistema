"""
Prazo engine for action instances (issue #870).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from apps.core.models.acoes_notificacao import EstadoAcaoChoices, TipoAncoraChoices
from apps.core.services.business_calendar_service import BusinessCalendarService

if TYPE_CHECKING:
    from apps.core.models import AcaoInstancia, CicloAcoes


class PrazoEngineService:
    """
    Calculates anchor, due-date and operational state for actions.
    """

    SEMESTRE_ANCHOR_BY_CODE: dict[str, tuple[int, int]] = {
        "1S": (3, 1),
        "2S": (8, 1),
    }

    @classmethod
    def semestre_anchor_date(cls, *, semestre: str, ano: int) -> date | None:
        month_day = cls.SEMESTRE_ANCHOR_BY_CODE.get(semestre)
        if month_day is None:
            return None
        month, day = month_day
        return date(ano, month, day)

    @classmethod
    def resolve_anchor_date(
        cls,
        action_instance: "AcaoInstancia",
        *,
        explicit_anchor_date: date | None = None,
    ) -> date | None:
        if explicit_anchor_date is not None:
            return explicit_anchor_date

        template = action_instance.template
        anchor_type = template.tipo_ancora

        if anchor_type == TipoAncoraChoices.EVENTO_EXTERNO:
            return action_instance.data_ancora

        if anchor_type == TipoAncoraChoices.ACAO_ANTERIOR:
            ref_template_id = template.ref_acao_template_id
            if ref_template_id is None:
                return None

            from apps.core.models import AcaoInstancia

            ref_action = AcaoInstancia.objects.filter(
                ciclo_id=action_instance.ciclo_id,
                template_id=ref_template_id,
            ).first()
            if ref_action is None:
                return None
            return ref_action.data_realizacao

        if anchor_type == TipoAncoraChoices.MARCO_CALENDARIO:
            return cls.semestre_anchor_date(
                semestre=action_instance.ciclo.semestre,
                ano=action_instance.ciclo.ano,
            )

        return None

    @classmethod
    def calculate_due_date(cls, *, anchor_date: date, business_days: int) -> date:
        return BusinessCalendarService.add_business_days(anchor_date, business_days)

    @classmethod
    def evaluate_state(
        cls,
        action_instance: "AcaoInstancia",
        *,
        reference_date: date | None = None,
    ) -> str:
        if action_instance.estado == EstadoAcaoChoices.CONCLUIDA:
            return EstadoAcaoChoices.CONCLUIDA

        if action_instance.data_ancora is None or action_instance.data_vencimento is None:
            return EstadoAcaoChoices.AGUARDANDO_ANCORA

        today = reference_date or timezone.localdate()
        if today > action_instance.data_vencimento:
            return EstadoAcaoChoices.ATRASADA
        return EstadoAcaoChoices.EM_ANDAMENTO

    @classmethod
    def recalculate_action(
        cls,
        action_instance: "AcaoInstancia",
        *,
        explicit_anchor_date: date | None = None,
        reference_date: date | None = None,
        save: bool = True,
    ) -> "AcaoInstancia":
        resolved_anchor = cls.resolve_anchor_date(
            action_instance,
            explicit_anchor_date=explicit_anchor_date,
        )

        if resolved_anchor is None:
            action_instance.data_ancora = None
            action_instance.data_vencimento = None
        else:
            action_instance.data_ancora = resolved_anchor
            action_instance.data_vencimento = cls.calculate_due_date(
                anchor_date=resolved_anchor,
                business_days=action_instance.template.dias_prazo_uteis,
            )

        if action_instance.estado != EstadoAcaoChoices.CONCLUIDA:
            action_instance.estado = cls.evaluate_state(
                action_instance,
                reference_date=reference_date,
            )

        if save:
            update_fields = [
                "data_ancora",
                "data_vencimento",
                "updated_at",
            ]
            if action_instance.estado != EstadoAcaoChoices.CONCLUIDA:
                update_fields.append("estado")
            action_instance.save(update_fields=update_fields)

        return action_instance

    @classmethod
    def recalculate_cycle(
        cls,
        ciclo: "CicloAcoes",
        *,
        reference_date: date | None = None,
    ) -> None:
        from apps.core.models import AcaoInstancia

        actions = AcaoInstancia.objects.select_related("template", "ciclo").filter(ciclo=ciclo).order_by("ordem")
        with transaction.atomic():
            for action in actions:
                cls.recalculate_action(action, reference_date=reference_date, save=True)

    @classmethod
    def recalculate_dependents(
        cls,
        source_action: "AcaoInstancia",
        *,
        reference_date: date | None = None,
    ) -> int:
        from apps.core.models import AcaoInstancia

        dependents = AcaoInstancia.objects.select_related("template", "ciclo").filter(
            ciclo_id=source_action.ciclo_id,
            template__ref_acao_template_id=source_action.template_id,
        )
        updated = 0
        with transaction.atomic():
            for action in dependents:
                cls.recalculate_action(action, reference_date=reference_date, save=True)
                updated += 1
        return updated
