"""
Tests for seed_acoes_notificacao command (issue #869).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from django.contrib.auth.models import Group
from django.core.management import call_command

import pytest

from apps.core.constants import ALLOWED_USER_GROUPS
from apps.core.models import AcaoTemplate, AcaoTemplateExecutor
from apps.core.services.acoes_notificacao_seed import GROUPS_TO_ENSURE


def _executor_snapshot() -> list[tuple[int, str, bool]]:
    return list(
        AcaoTemplateExecutor.objects.order_by("acao_template__ordem", "group__name").values_list(
            "acao_template__ordem",
            "group__name",
            "ativo",
        )
    )


@pytest.fixture
def clean_seed_state(db):
    AcaoTemplateExecutor.objects.all().delete()
    for template in AcaoTemplate.objects.order_by("-ordem"):
        template.delete()
    Group.objects.filter(name__in=GROUPS_TO_ENSURE).delete()


@pytest.mark.django_db
def test_seed_acoes_notificacao_creates_groups_and_templates(clean_seed_state):
    call_command("seed_acoes_notificacao")

    for group_name in GROUPS_TO_ENSURE:
        assert Group.objects.filter(name=group_name).exists(), f"Grupo não criado: {group_name}"

    templates = AcaoTemplate.objects.order_by("ordem")
    assert templates.count() == 32
    assert list(templates.values_list("ordem", flat=True)) == list(range(1, 33))
    assert templates.filter(ativo=True).count() == 32


@pytest.mark.django_db
def test_seed_acoes_notificacao_executor_mapping_and_rbac_validity(clean_seed_state):
    call_command("seed_acoes_notificacao")

    executor_groups = set(AcaoTemplateExecutor.objects.values_list("group__name", flat=True))
    invalid_groups = executor_groups - ALLOWED_USER_GROUPS
    assert not invalid_groups, f"Executores fora do RBAC: {sorted(invalid_groups)}"

    # Nenhuma ação pode ficar sem executor.
    for template in AcaoTemplate.objects.order_by("ordem"):
        assert template.executores.exists(), f"Ação {template.ordem} sem executor"

    # Mapeamento inicial fechado pelo negócio para #869.
    expected_ordem_1 = {"Logística Galpão"}
    expected_ordem_2 = {"Comercial", "Relacionamento", "DAT"}
    expected_default = {"Coordenador", "Gerente"}

    def executors_of(ordem: int) -> set[str]:
        return set(
            AcaoTemplateExecutor.objects.filter(acao_template__ordem=ordem).values_list("group__name", flat=True)
        )

    assert executors_of(1) == expected_ordem_1
    assert executors_of(2) == expected_ordem_2
    for ordem in range(3, 33):
        assert executors_of(ordem) == expected_default


@pytest.mark.django_db
def test_seed_acoes_notificacao_is_idempotent(clean_seed_state):
    call_command("seed_acoes_notificacao")
    snapshot_first = _executor_snapshot()
    count_templates_first = AcaoTemplate.objects.count()
    count_links_first = AcaoTemplateExecutor.objects.count()

    call_command("seed_acoes_notificacao")
    snapshot_second = _executor_snapshot()
    count_templates_second = AcaoTemplate.objects.count()
    count_links_second = AcaoTemplateExecutor.objects.count()

    assert count_templates_first == 32
    assert count_templates_second == 32
    assert count_links_first == count_links_second
    assert snapshot_first == snapshot_second
