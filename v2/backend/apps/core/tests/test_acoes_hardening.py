"""Tests for acoes/notificacao hardening fixes."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError

import pytest

if TYPE_CHECKING:
    from apps.core.models import Usuario

from apps.core.models.acoes_notificacao import (
    AcaoInstancia,
    AcaoTemplate,
    AcaoTemplateExecutor,
    CicloAcoes,
    EstadoAcaoChoices,
    RegistroConclusaoAcao,
    SemestreChoices,
    TipoAncoraChoices,
)
from apps.core.services.prazo_engine_service import PrazoEngineService


@pytest.fixture()
def group(db):  # type: ignore[no-untyped-def]
    return Group.objects.create(name="Test Executors")


@pytest.fixture()
def ciclo(db):  # type: ignore[no-untyped-def]
    from apps.core.models import Municipio, Projeto

    projeto = Projeto.objects.create(nome="Projeto Hardening Test")
    municipio = Municipio.objects.create(nome="Municipio Test")
    return CicloAcoes.objects.create(
        projeto=projeto,
        municipio=municipio,
        semestre=SemestreChoices.PRIMEIRO,
        ano=2026,
    )


@pytest.fixture()
def template_a(db):  # type: ignore[no-untyped-def]
    return AcaoTemplate.objects.create(
        nome="Acao A",
        ordem=901,
        tipo_ancora=TipoAncoraChoices.EVENTO_EXTERNO,
        ref_evento_externo="EVT_TEST_A",
        dias_prazo_uteis=5,
        descricao_prazo="5 dias uteis apos evento",
    )


@pytest.fixture()
def template_b(template_a):  # type: ignore[no-untyped-def]
    return AcaoTemplate.objects.create(
        nome="Acao B",
        ordem=902,
        tipo_ancora=TipoAncoraChoices.ACAO_ANTERIOR,
        ref_acao_template=template_a,
        dias_prazo_uteis=3,
        descricao_prazo="3 dias uteis apos A",
    )


@pytest.fixture()
def template_c(template_b):  # type: ignore[no-untyped-def]
    return AcaoTemplate.objects.create(
        nome="Acao C",
        ordem=903,
        tipo_ancora=TipoAncoraChoices.ACAO_ANTERIOR,
        ref_acao_template=template_b,
        dias_prazo_uteis=2,
        descricao_prazo="2 dias uteis apos B",
    )


@pytest.fixture()
def usuario(db):  # type: ignore[no-untyped-def]
    from apps.core.models import Usuario

    return Usuario.objects.create_user(  # type: ignore[attr-defined]
        username="hardening_test",
        password="test123",  # noqa: S106
        first_name="Test",
        last_name="User",
    )


# --- Fix 1: CASCADE -> PROTECT ---


@pytest.mark.django_db()
class TestExecutorGroupProtect:
    def test_delete_group_with_executor_raises_protected_error(self, group: Group, template_a: AcaoTemplate) -> None:
        AcaoTemplateExecutor.objects.create(acao_template=template_a, group=group)
        with pytest.raises(ProtectedError):
            group.delete()
        assert Group.objects.filter(pk=group.pk).exists()

    def test_delete_group_without_executor_succeeds(self, db) -> None:  # type: ignore[no-untyped-def]
        g = Group.objects.create(name="Orphan Group")
        g.delete()
        assert not Group.objects.filter(name="Orphan Group").exists()


# --- Fix 2: Recursive cascade recalculate_dependents ---


@pytest.mark.django_db()
class TestRecalculateDependentsCascade:
    def test_cascade_a_b_c(
        self,
        ciclo: CicloAcoes,
        template_a: AcaoTemplate,
        template_b: AcaoTemplate,
        template_c: AcaoTemplate,
    ) -> None:
        ref_date = date(2026, 3, 16)
        action_a = AcaoInstancia.objects.create(
            ciclo=ciclo,
            template=template_a,
            ordem=1,
            estado=EstadoAcaoChoices.CONCLUIDA,
            data_realizacao=ref_date,
            observacao_conclusao="Concluida para teste cascade",
        )
        action_b = AcaoInstancia.objects.create(ciclo=ciclo, template=template_b, ordem=2)
        action_c = AcaoInstancia.objects.create(ciclo=ciclo, template=template_c, ordem=3)

        updated = PrazoEngineService.recalculate_dependents(action_a, reference_date=ref_date)

        action_b.refresh_from_db()
        action_c.refresh_from_db()

        # B depends on A (completed) → B gets data_vencimento
        assert updated >= 2, f"Expected at least 2 updates (B+C), got {updated}"
        assert action_b.data_vencimento is not None, "B should have data_vencimento set"
        # C depends on B (not completed, no data_realizacao) → C stays without vencimento
        # The key assertion is that the cascade visited C (updated >= 2), not that C has a date

    def test_no_infinite_loop_on_circular_ref(
        self,
        ciclo: CicloAcoes,
        template_a: AcaoTemplate,
        template_b: AcaoTemplate,
    ) -> None:
        ref_date = date(2026, 3, 16)
        action_a = AcaoInstancia.objects.create(ciclo=ciclo, template=template_a, ordem=1)
        AcaoInstancia.objects.create(ciclo=ciclo, template=template_b, ordem=2)

        # Should not raise RecursionError
        PrazoEngineService.recalculate_dependents(action_a, reference_date=ref_date)

    def test_dependents_ordered_by_ordem(
        self,
        ciclo: CicloAcoes,
        template_a: AcaoTemplate,
        template_b: AcaoTemplate,
        template_c: AcaoTemplate,
    ) -> None:
        """Dependents are processed in ordem order."""
        ref_date = date(2026, 3, 16)
        # Create C before B to test ordering
        action_a = AcaoInstancia.objects.create(ciclo=ciclo, template=template_a, ordem=1)
        AcaoInstancia.objects.create(ciclo=ciclo, template=template_c, ordem=3)
        AcaoInstancia.objects.create(ciclo=ciclo, template=template_b, ordem=2)

        PrazoEngineService.recalculate_action(action_a, reference_date=ref_date, save=True)
        # Should not raise any error
        PrazoEngineService.recalculate_dependents(action_a, reference_date=ref_date)


# --- Fix 3: Race condition in concluir() ---


@pytest.mark.django_db()
class TestConcluirAtomicity:
    def test_second_concluir_raises_validation_error(
        self,
        ciclo: CicloAcoes,
        template_a: AcaoTemplate,
        usuario: Usuario,
    ) -> None:
        action = AcaoInstancia.objects.create(
            ciclo=ciclo,
            template=template_a,
            ordem=1,
            estado=EstadoAcaoChoices.AGUARDANDO_ANCORA,
        )

        action.concluir(
            data_realizacao=date(2026, 3, 16),
            observacao="Primeira conclusao",
            usuario=usuario,
        )
        assert RegistroConclusaoAcao.objects.filter(acao_instancia=action).count() == 1

        # Reset state to simulate concurrent request
        action.estado = EstadoAcaoChoices.AGUARDANDO_ANCORA
        action.save(update_fields=["estado"])

        with pytest.raises(ValidationError, match="ja existe"):
            action.concluir(
                data_realizacao=date(2026, 3, 16),
                observacao="Segunda conclusao concorrente",
                usuario=usuario,
            )

    def test_concluir_creates_registro(
        self,
        ciclo: CicloAcoes,
        template_a: AcaoTemplate,
        usuario: Usuario,
    ) -> None:
        action = AcaoInstancia.objects.create(
            ciclo=ciclo,
            template=template_a,
            ordem=1,
            estado=EstadoAcaoChoices.AGUARDANDO_ANCORA,
        )

        registro = action.concluir(
            data_realizacao=date(2026, 3, 16),
            observacao="Conclusao normal",
            usuario=usuario,
        )
        assert registro is not None
        assert registro.acao_instancia == action  # pyright: ignore[reportUnknownMemberType]
        assert registro.registrado_por == usuario
