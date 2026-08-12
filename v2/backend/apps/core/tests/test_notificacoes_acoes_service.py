"""
Tests for daily action notifications/escalation service (issue #871).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from datetime import date

import pytest

from apps.core.models import (
    AcaoInstancia,
    AcaoTemplate,
    AcaoTemplateExecutor,
    AuditLog,
    CicloAcoes,
    NotificacaoInterna,
    Usuario,
)
from apps.core.services.notificacoes_acoes_service import AcoesNotificacaoDailyService
from apps.core.services.prazo_engine_service import PrazoEngineService
from apps.core.tasks import processar_notificacoes_acoes_diarias
from apps.core.tests.factories import (
    GroupFactory,
    MunicipioFactory,
    ProjetoFactory,
    UsuarioFactory,
)


@pytest.fixture
def user_factory(db):
    counter = {"n": 0}

    def _create(*, prefix: str, groups: list[str]) -> Usuario:
        counter["n"] += 1
        idx = counter["n"]
        return UsuarioFactory(
            username=f"{prefix}_{idx}",
            email=f"{prefix}_{idx}@example.com",
            cpf=f"{idx:011d}",
            groups=groups,
        )

    return _create


@pytest.fixture
def base_context(db, user_factory):
    creator = user_factory(prefix="creator", groups=["DAT"])
    projeto = ProjetoFactory(nome="Projeto Notificacoes")
    municipio = MunicipioFactory(nome="Fortaleza", uf="CE")
    ciclo = CicloAcoes.objects.create(
        projeto=projeto,
        municipio=municipio,
        semestre="1S",
        ano=2026,
        created_by=creator,
    )
    return {"ciclo": ciclo}


def _create_action(*, ciclo: CicloAcoes, ordem: int, anchor: date, executor_group: str) -> AcaoInstancia:
    template = AcaoTemplate.objects.create(
        ordem=ordem,
        nome=f"Acao {ordem}",
        descricao_prazo="Teste notificacao",
        tipo_ancora="EVENTO_EXTERNO",
        ref_evento_externo=f"EVENT_{ordem}",
        dias_prazo_uteis=1,
    )
    group = GroupFactory(name=executor_group)
    AcaoTemplateExecutor.objects.create(acao_template=template, group=group, ativo=True)

    action = AcaoInstancia.objects.create(
        ciclo=ciclo,
        template=template,
        ordem=ordem,
        estado="EM_ANDAMENTO",
        data_ancora=anchor,
    )
    PrazoEngineService.recalculate_action(action, reference_date=anchor, save=True)
    return action


@pytest.mark.django_db
def test_d_minus_3_creates_notifications_and_deduplicates_same_day(base_context, user_factory):
    ciclo = base_context["ciclo"]
    action = _create_action(ciclo=ciclo, ordem=501, anchor=date(2026, 3, 12), executor_group="Comercial")

    coordinator = user_factory(prefix="coord", groups=["Comercial", "Coordenador"])
    manager = user_factory(prefix="manager", groups=["Comercial", "Gerente"])

    metrics_first = AcoesNotificacaoDailyService.run(reference_date=date(2026, 3, 10))
    assert metrics_first["notifications_created"] == 2
    assert metrics_first["notifications_deduplicated"] == 0
    assert metrics_first["actions_triggered"] == 1
    assert metrics_first["phases"] == {"D-3": 1}

    notifications = list(NotificacaoInterna.objects.filter(acao_instancia=action).order_by("destinatario__username"))
    assert [n.destinatario_id for n in notifications] == [coordinator.id, manager.id]
    assert all(n.fase_disparo == "D-3" for n in notifications)

    metrics_second = AcoesNotificacaoDailyService.run(reference_date=date(2026, 3, 10))
    assert metrics_second["notifications_created"] == 0
    assert metrics_second["notifications_deduplicated"] == 2
    assert NotificacaoInterna.objects.filter(acao_instancia=action, fase_disparo="D-3").count() == 2


@pytest.mark.django_db
def test_d_plus_1_notifies_coordinator_level(base_context, user_factory):
    ciclo = base_context["ciclo"]
    action = _create_action(ciclo=ciclo, ordem=502, anchor=date(2026, 3, 9), executor_group="Relacionamento")

    coordinator = user_factory(prefix="coord", groups=["Relacionamento", "Coordenador"])
    user_factory(prefix="manager", groups=["Relacionamento", "Gerente"])

    metrics = AcoesNotificacaoDailyService.run(reference_date=date(2026, 3, 11))
    assert metrics["phases"] == {"D+1": 1}

    notifications = list(NotificacaoInterna.objects.filter(acao_instancia=action))
    assert len(notifications) == 1
    notification = notifications[0]
    assert notification.destinatario_id == coordinator.id
    assert notification.nivel == "COORDENADOR"
    assert notification.fase_disparo == "D+1"


@pytest.mark.django_db
def test_d_plus_3_notifies_manager_level(base_context, user_factory):
    ciclo = base_context["ciclo"]
    action = _create_action(ciclo=ciclo, ordem=503, anchor=date(2026, 3, 9), executor_group="Comercial")

    user_factory(prefix="coord", groups=["Comercial", "Coordenador"])
    manager = user_factory(prefix="manager", groups=["Comercial", "Gerente"])

    metrics = AcoesNotificacaoDailyService.run(reference_date=date(2026, 3, 13))
    assert metrics["phases"] == {"D+3": 1}

    notifications = list(NotificacaoInterna.objects.filter(acao_instancia=action))
    assert len(notifications) == 1
    notification = notifications[0]
    assert notification.destinatario_id == manager.id
    assert notification.nivel == "GERENTE"
    assert notification.fase_disparo == "D+3"


@pytest.mark.django_db
def test_fallback_to_global_manager_when_executor_has_no_eligible_user(base_context, user_factory):
    ciclo = base_context["ciclo"]
    action = _create_action(ciclo=ciclo, ordem=504, anchor=date(2026, 3, 12), executor_group="Logística Viagens")

    global_manager = user_factory(prefix="global_manager", groups=["Gerente"])

    metrics = AcoesNotificacaoDailyService.run(reference_date=date(2026, 3, 12))
    assert metrics["phases"] == {"D-1": 1}
    assert metrics["fallback_actions"] == 1

    notifications = list(NotificacaoInterna.objects.filter(acao_instancia=action))
    assert len(notifications) == 1
    notification = notifications[0]
    assert notification.destinatario_id == global_manager.id
    assert notification.nivel == "GERENTE"
    assert notification.fase_disparo == "D-1"


@pytest.mark.django_db
def test_concluded_action_does_not_generate_notifications(base_context, user_factory):
    ciclo = base_context["ciclo"]
    action = _create_action(ciclo=ciclo, ordem=505, anchor=date(2026, 3, 12), executor_group="Comercial")

    action.estado = "CONCLUIDA"
    action.data_realizacao = date(2026, 3, 12)
    action.observacao_conclusao = "Concluida"
    action.save(update_fields=["estado", "data_realizacao", "observacao_conclusao", "updated_at"])

    user_factory(prefix="coord", groups=["Comercial", "Coordenador"])
    user_factory(prefix="manager", groups=["Comercial", "Gerente"])

    metrics = AcoesNotificacaoDailyService.run(reference_date=date(2026, 3, 12))
    assert metrics["actions_triggered"] == 0
    assert NotificacaoInterna.objects.filter(acao_instancia=action).count() == 0


@pytest.mark.django_db
def test_task_wrapper_returns_metrics_and_writes_audit_log(base_context, user_factory):
    ciclo = base_context["ciclo"]
    _create_action(ciclo=ciclo, ordem=506, anchor=date(2026, 3, 12), executor_group="Comercial")

    user_factory(prefix="coord", groups=["Comercial", "Coordenador"])
    user_factory(prefix="manager", groups=["Comercial", "Gerente"])

    result = processar_notificacoes_acoes_diarias(reference_date_iso="2026-03-10")
    assert result["reference_date"] == "2026-03-10"
    assert result["notifications_created"] == 2

    audit = AuditLog.objects.filter(action="ACOES_NOTIFICACOES_DAILY").order_by("-created_at").first()
    assert audit is not None
    assert audit.details["reference_date"] == "2026-03-10"
    assert audit.details["notifications_created"] == 2


@pytest.mark.django_db
def test_run_skips_non_business_day_weekend(base_context, user_factory):
    """#1721: a distancia em dias uteis ate um vencimento util e IDENTICA para
    sexta, sabado e domingo. Como a task diaria roda todo dia do calendario e a
    chave de dedupe inclui referencia_data, cada fase (D-7/D-3/D-1) dispararia
    ate 3x no fim de semana. Rodar num dia nao-util deve PULAR (0 notificacoes)."""
    ciclo = base_context["ciclo"]
    # data_vencimento = add_business_days(anchor, 1) = 2026-03-18 (quarta-feira).
    action = _create_action(ciclo=ciclo, ordem=510, anchor=date(2026, 3, 17), executor_group="Comercial")
    user_factory(prefix="coord", groups=["Comercial", "Coordenador"])
    user_factory(prefix="manager", groups=["Comercial", "Gerente"])

    # Sanidade: sexta 2026-03-13 e dia util e esta a 3 dias uteis do vencimento -> D-3 dispara (2 notifs).
    metrics_friday = AcoesNotificacaoDailyService.run(reference_date=date(2026, 3, 13))
    assert metrics_friday["phases"] == {"D-3": 1}
    assert metrics_friday["notifications_created"] == 2

    # Sabado 2026-03-14 tambem esta a 3 dias uteis do vencimento (o bug criaria +2 duplicatas).
    metrics_saturday = AcoesNotificacaoDailyService.run(reference_date=date(2026, 3, 14))
    assert metrics_saturday["notifications_created"] == 0
    assert metrics_saturday.get("skipped_non_business_day") is True

    # Apenas as 2 notificacoes de sexta permanecem.
    assert NotificacaoInterna.objects.filter(acao_instancia=action).count() == 2

    # O skip continua auditado (nao cega o monitoramento de "a task rodou?").
    audit = AuditLog.objects.filter(action="ACOES_NOTIFICACOES_DAILY").order_by("-created_at").first()
    assert audit is not None
    assert audit.details.get("skipped_non_business_day") is True
