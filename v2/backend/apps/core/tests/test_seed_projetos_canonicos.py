"""Tests do seed do catalogo canonico de Projetos (create-only, idempotente)."""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false

from __future__ import annotations

from django.core.management import call_command

import pytest

from apps.core.management.commands.seed_projetos_canonicos import (
    PROJETOS_CANONICOS,
    seed_projetos_canonicos,
)
from apps.core.models import Projeto
from apps.core.tests.factories import ProjetoFactory

pytestmark = pytest.mark.django_db


def test_seed_creates():
    stats = seed_projetos_canonicos([("Proj Seed A", "NAO_SUPER"), ("Proj Seed B", "SUPER")])
    assert stats["created"] == 2
    assert Projeto.objects.get(nome="Proj Seed A").fluxo == "NAO_SUPER"
    assert Projeto.objects.get(nome="Proj Seed B").fluxo == "SUPER"


def test_seed_idempotent():
    seed_projetos_canonicos([("Proj Idem Seed", "SUPER")])
    stats = seed_projetos_canonicos([("Proj Idem Seed", "SUPER")])
    assert stats["created"] == 0
    assert stats["existing"] == 1
    assert Projeto.objects.filter(nome="Proj Idem Seed").count() == 1


def test_seed_create_only_no_fluxo_overwrite():
    ProjetoFactory(nome="Proj Existe Seed", fluxo="NAO_SUPER")
    stats = seed_projetos_canonicos([("Proj Existe Seed", "SUPER")])
    assert stats["created"] == 0
    assert Projeto.objects.get(nome="Proj Existe Seed").fluxo == "NAO_SUPER"  # nao sobrescreve


def test_seed_rejects_invalid_fluxo_and_empty_name():
    stats = seed_projetos_canonicos([("", "SUPER"), ("Proj Fluxo Ruim", "INVALIDO"), ("Proj Ok Seed", "SUPER")])
    assert stats["created"] == 1
    assert stats["rejected"] == 2
    assert not Projeto.objects.filter(nome="Proj Fluxo Ruim").exists()


def test_constant_well_formed():
    assert len(PROJETOS_CANONICOS) == 33
    nomes = [n for n, _ in PROJETOS_CANONICOS]
    assert len(set(nomes)) == 33, "nomes de projeto devem ser unicos"
    assert all(f in {"SUPER", "NAO_SUPER"} for _, f in PROJETOS_CANONICOS)
    assert sum(1 for _, f in PROJETOS_CANONICOS if f == "SUPER") == 11


def test_command_seeds_catalogo():
    call_command("seed_projetos_canonicos")
    # amostra: um SUPER (caixa alta) e um NAO_SUPER com acento
    tema = Projeto.objects.get(nome="TEMA")
    assert tema.fluxo == "SUPER"
    assert Projeto.objects.get(nome="Superativar Matemática").fluxo == "NAO_SUPER"
    assert Projeto.objects.filter(nome__in=[n for n, _ in PROJETOS_CANONICOS]).count() == 33


def test_command_idempotent():
    call_command("seed_projetos_canonicos")
    before = Projeto.objects.count()
    call_command("seed_projetos_canonicos")
    assert Projeto.objects.count() == before  # 2a run nao duplica
