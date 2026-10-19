"""
Migration 0129: as descriptions de `create_solicitation_without_purchase` e `manage_internal_actions`
no banco acompanham o seed (`functional_permissions_seed.py`).

A primeira dizia "só o superusuário passa", mas desde o PR 10 a capacidade está no pacote do perfil
administrador operacional. A segunda mandava "atribuir via admin UI", e desde a D4 do ADR-020 a matriz
só muda por PR.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false

from __future__ import annotations

import importlib

from django.apps import apps as django_apps

import pytest

from apps.core.models import PermissaoFuncional
from apps.core.services.functional_permissions_seed import FUNCTIONAL_PERMISSIONS_SEED

migracao = importlib.import_module("apps.core.migrations.0129_descricoes_rbac_atuais")

DO_SEED = {s.codename: s.description for s in FUNCTIONAL_PERMISSIONS_SEED}


@pytest.fixture
def capacidades_com_texto_antigo(db):
    for codename, antiga in migracao.DESCRICOES_ANTIGAS.items():
        PermissaoFuncional.objects.update_or_create(
            codename=codename, defaults={"label": codename, "description": antiga, "category": "solicitacao"}
        )


@pytest.mark.migrations
@pytest.mark.django_db
class TestDescricoesRbacMigration:
    def test_forwards_grava_o_texto_do_seed(self, capacidades_com_texto_antigo):
        migracao.forwards(django_apps, None)
        for codename in migracao.DESCRICOES_NOVAS:
            assert PermissaoFuncional.objects.get(codename=codename).description == DO_SEED[codename]

    def test_backwards_volta_o_texto_antigo(self, capacidades_com_texto_antigo):
        migracao.forwards(django_apps, None)
        migracao.backwards(django_apps, None)
        for codename, antiga in migracao.DESCRICOES_ANTIGAS.items():
            assert PermissaoFuncional.objects.get(codename=codename).description == antiga

    def test_so_mexe_na_description(self, capacidades_com_texto_antigo):
        antes = {p.codename: (p.label, p.category) for p in PermissaoFuncional.objects.all()}
        migracao.forwards(django_apps, None)
        depois = {p.codename: (p.label, p.category) for p in PermissaoFuncional.objects.all()}
        assert depois == antes
