"""
Wave B (H2) — guarda de drift dos composites aprovadores.

A detecção de "aprovador" é por NOME de grupo (composite Setor×Função); uma
capability não expressa AND-de-2-grupos. A robustez a rename vem daqui: se um
grupo do composite for renomeado (em `constants.py`) sem atualizar a SSOT
`APPROVER_COMPOSITES`, o sistema deixaria de reconhecer aprovadores em SILÊNCIO
(fail-open em `can_admin_mutate_target`). Estas guardas transformam esse silêncio
em falha ALTA:

- **system check estático** (`check_approver_composites`, em memória, sem DB):
  todo nome em `APPROVER_COMPOSITES` tem que estar em `SETOR_GROUPS`/`FUNCAO_GROUPS`
  → roda em `manage.py check` (deploy/CI) e falha se houver drift;
- **sentinela de seed** (DB): o `seed_rbac` cria um Group para cada nome do composite.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false, reportMissingTypeStubs=false

from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth.models import Group
from django.core.management import call_command

import pytest

from apps.core.rbac import helpers
from apps.core.rbac.checks import check_approver_composites


class TestApproverCompositesStaticCheck:
    def test_config_limpa_sem_erros(self):
        """A config real (APPROVER_COMPOSITES ⊆ SETOR/FUNCAO_GROUPS) não gera erro."""
        assert check_approver_composites(app_configs=None) == []

    def test_setor_renomeado_gera_erro(self):
        """RED: setor fora de SETOR_GROUPS (rename sem atualizar a SSOT) → Error."""
        bad = (("Setor Renomeado XYZ", "Gerente"),)
        with patch.object(helpers, "APPROVER_COMPOSITES", bad):
            errors = check_approver_composites(app_configs=None)
        assert errors, "drift de setor deveria gerar erro"
        assert any("Setor Renomeado XYZ" in e.msg for e in errors)

    def test_funcao_renomeada_gera_erro(self):
        bad = (("Superintendência", "Funcao Renomeada XYZ"),)
        with patch.object(helpers, "APPROVER_COMPOSITES", bad):
            errors = check_approver_composites(app_configs=None)
        assert errors, "drift de função deveria gerar erro"
        assert any("Funcao Renomeada XYZ" in e.msg for e in errors)


@pytest.mark.django_db
class TestApproverCompositesSeededGroups:
    def test_seed_cria_grupo_para_cada_nome_do_composite(self):
        call_command("seed_rbac")
        for setor, funcao in helpers.APPROVER_COMPOSITES:
            assert Group.objects.filter(name=setor).exists(), f"seed_rbac não criou o setor '{setor}'"
            assert Group.objects.filter(name=funcao).exists(), f"seed_rbac não criou a função '{funcao}'"
