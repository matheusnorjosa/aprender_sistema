"""
Tests for PrazoEngineService (issue #870).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from datetime import date

from django.utils import timezone

import pytest

from apps.core.models import AcaoInstancia, AcaoTemplate, CicloAcoes
from apps.core.services.prazo_engine_service import PrazoEngineService
from apps.core.tests.factories import MunicipioFactory, ProjetoFactory, UsuarioFactory


@pytest.fixture
def usuario(db):
    return UsuarioFactory(
        username="prazo_user",
        email="prazo_user@example.com",
        password="testpass123",
        cpf="12312312312",
    )


@pytest.fixture
def ciclo(db, usuario):
    projeto = ProjetoFactory(nome="Projeto Prazo Engine")
    municipio = MunicipioFactory(nome="Municipio Prazo Engine", uf="CE")
    return CicloAcoes.objects.create(
        projeto=projeto,
        municipio=municipio,
        semestre="1S",
        ano=2026,
        created_by=usuario,
    )


@pytest.fixture
def template_evento(db):
    return AcaoTemplate.objects.create(
        ordem=201,
        nome="Acao Evento Externo",
        descricao_prazo="Teste prazo 2 dias uteis",
        tipo_ancora="EVENTO_EXTERNO",
        ref_evento_externo="EVENTO_TESTE",
        dias_prazo_uteis=2,
    )


@pytest.fixture
def acao_evento(ciclo, template_evento):
    return AcaoInstancia.objects.create(
        ciclo=ciclo,
        template=template_evento,
        ordem=201,
        estado="AGUARDANDO_ANCORA",
    )


@pytest.mark.django_db
def test_recalculate_without_anchor_keeps_aguardando(acao_evento):
    PrazoEngineService.recalculate_action(acao_evento)
    acao_evento.refresh_from_db()
    assert acao_evento.estado == "AGUARDANDO_ANCORA"
    assert acao_evento.data_ancora is None
    assert acao_evento.data_vencimento is None


@pytest.mark.django_db
def test_recalculate_with_explicit_anchor_sets_due_and_em_andamento(acao_evento):
    PrazoEngineService.recalculate_action(
        acao_evento,
        explicit_anchor_date=date(2026, 3, 16),
        reference_date=date(2026, 3, 17),
    )
    acao_evento.refresh_from_db()
    assert acao_evento.data_ancora == date(2026, 3, 16)
    assert acao_evento.data_vencimento == date(2026, 3, 18)
    assert acao_evento.estado == "EM_ANDAMENTO"


@pytest.mark.django_db
def test_marks_atrasada_when_reference_date_after_due(acao_evento):
    PrazoEngineService.recalculate_action(
        acao_evento,
        explicit_anchor_date=date(2026, 3, 16),
        reference_date=date(2026, 3, 21),
    )
    acao_evento.refresh_from_db()
    assert acao_evento.estado == "ATRASADA"


@pytest.mark.django_db
def test_action_anterior_uses_previous_action_completion(ciclo, usuario):
    template_a = AcaoTemplate.objects.create(
        ordem=202,
        nome="Acao Base",
        descricao_prazo="Sem prazo relevante",
        tipo_ancora="EVENTO_EXTERNO",
        ref_evento_externo="EVENTO_BASE",
        dias_prazo_uteis=1,
    )
    template_b = AcaoTemplate.objects.create(
        ordem=203,
        nome="Acao Dependente",
        descricao_prazo="2 dias apos acao anterior",
        tipo_ancora="ACAO_ANTERIOR",
        ref_acao_template=template_a,
        dias_prazo_uteis=2,
    )

    acao_a = AcaoInstancia.objects.create(ciclo=ciclo, template=template_a, ordem=202, estado="AGUARDANDO_ANCORA")
    acao_b = AcaoInstancia.objects.create(ciclo=ciclo, template=template_b, ordem=203, estado="AGUARDANDO_ANCORA")

    PrazoEngineService.recalculate_action(acao_b)
    acao_b.refresh_from_db()
    assert acao_b.estado == "AGUARDANDO_ANCORA"
    assert acao_b.data_ancora is None

    acao_a.registrar_ancora(data_ancora=timezone.localdate(), usuario=usuario, observacao="ancora base")
    acao_a.concluir(
        data_realizacao=timezone.localdate(),
        observacao="base concluida",
        usuario=usuario,
    )
    acao_b.refresh_from_db()

    assert acao_b.data_ancora == timezone.localdate()
    assert acao_b.data_vencimento is not None
    assert acao_b.estado in {"EM_ANDAMENTO", "ATRASADA"}


@pytest.mark.django_db
def test_marco_calendario_uses_semestre_anchor(ciclo):
    template = AcaoTemplate.objects.create(
        ordem=204,
        nome="Acao Marco Calendario",
        descricao_prazo="1 dia util apos inicio semestre",
        tipo_ancora="MARCO_CALENDARIO",
        ref_evento_externo="INICIO_SEMESTRE",
        dias_prazo_uteis=1,
    )
    action = AcaoInstancia.objects.create(
        ciclo=ciclo,
        template=template,
        ordem=204,
        estado="AGUARDANDO_ANCORA",
    )

    PrazoEngineService.recalculate_action(
        action,
        reference_date=date(2026, 3, 1),
    )
    action.refresh_from_db()
    assert action.data_ancora == date(2026, 3, 1)
    assert action.data_vencimento == date(2026, 3, 2)
    assert action.estado == "EM_ANDAMENTO"


@pytest.mark.django_db
def test_registrar_ancora_recalculates_due_immediately(acao_evento, usuario):
    # Use future dates to avoid flaky ATRASADA state when test date passes vencimento
    today = timezone.localdate()
    anchor_date = today
    acao_evento.registrar_ancora(
        data_ancora=anchor_date,
        usuario=usuario,
        observacao="registro manual",
    )
    acao_evento.refresh_from_db()
    assert acao_evento.data_vencimento is not None
    assert acao_evento.data_vencimento > anchor_date
    assert acao_evento.estado == "EM_ANDAMENTO"
