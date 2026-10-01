"""Tests do seed do catalogo canonico de Projetos (create-only, idempotente)."""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false

from __future__ import annotations

from django.core.management import call_command

import pytest

from apps.core.management.commands.seed_projetos_canonicos import (
    PROJETOS_CANONICOS,
    seed_projetos_canonicos,
)
from apps.core.models import Gerencia, Projeto
from apps.core.tests.factories import ProjetoFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def g1() -> Gerencia:
    """SUPER nasce na gerência Superintendência; sem ela o seed rejeita o SUPER (regra do dono,
    30/09 — test_projeto_fluxo_super_so_superintendencia.py)."""
    return Gerencia.objects.create(nome="SUPERINTENDENCIA", nome_setor="Super")


@pytest.mark.usefixtures("g1")
def test_seed_creates():
    stats = seed_projetos_canonicos([("Proj Seed A", "NAO_SUPER"), ("Proj Seed B", "SUPER")])
    assert stats["created"] == 2
    assert Projeto.objects.get(nome="Proj Seed A").fluxo == "NAO_SUPER"
    assert Projeto.objects.get(nome="Proj Seed B").fluxo == "SUPER"


@pytest.mark.usefixtures("g1")
def test_seed_idempotent():
    seed_projetos_canonicos([("Proj Idem Seed", "SUPER")])
    stats = seed_projetos_canonicos([("Proj Idem Seed", "SUPER")])
    assert stats["created"] == 0
    assert stats["existing"] == 1
    assert Projeto.objects.filter(nome="Proj Idem Seed").count() == 1


def test_seed_create_only_no_fluxo_overwrite(g1):
    # Com g1 no banco: sem ela o SUPER seria rejeitado antes e o teste passaria pelo caminho errado.
    ProjetoFactory(nome="Proj Existe Seed", fluxo="NAO_SUPER", gerencia=None)
    stats = seed_projetos_canonicos([("Proj Existe Seed", "SUPER")])
    assert (stats["created"], stats["existing"], stats["rejected"]) == (0, 1, 0)
    existente = Projeto.objects.get(nome="Proj Existe Seed")
    assert (existente.fluxo, existente.gerencia) == ("NAO_SUPER", None)  # nao sobrescreve


def test_seed_skips_canonical_duplicate_different_casing():
    # Regressao: golden dev tem os projetos em UPPERCASE; o catalogo canonico em Title Case.
    # A idempotencia por canon-key (nao por `nome` exato) NAO pode criar quase-duplicata.
    ProjetoFactory(nome="GESTÃO ESCOLAR", fluxo="NAO_SUPER")
    stats = seed_projetos_canonicos([("Gestão Escolar", "NAO_SUPER")])
    assert stats["created"] == 0
    assert stats["existing"] == 1
    assert Projeto.objects.filter(nome__iexact="gestão escolar").count() == 1, "nao pode duplicar por grafia"


@pytest.mark.usefixtures("g1")
def test_seed_rejects_invalid_fluxo_and_empty_name():
    stats = seed_projetos_canonicos([("", "SUPER"), ("Proj Fluxo Ruim", "INVALIDO"), ("Proj Ok Seed", "SUPER")])
    assert stats["created"] == 1
    assert stats["rejected"] == 2
    assert not Projeto.objects.filter(nome="Proj Fluxo Ruim").exists()


def test_constant_well_formed():
    assert len(PROJETOS_CANONICOS) == 38
    nomes = [n for n, _ in PROJETOS_CANONICOS]
    assert len(set(nomes)) == 38, "nomes de projeto devem ser unicos"
    assert all(f in {"SUPER", "NAO_SUPER"} for _, f in PROJETOS_CANONICOS)
    assert sum(1 for _, f in PROJETOS_CANONICOS if f == "SUPER") == 13


@pytest.mark.usefixtures("g1")
def test_command_seeds_catalogo():
    call_command("seed_projetos_canonicos")
    # amostra: um SUPER (caixa alta) e um NAO_SUPER com acento
    tema = Projeto.objects.get(nome="TEMA")
    assert tema.fluxo == "SUPER"
    assert Projeto.objects.get(nome="Superativar Matemática").fluxo == "NAO_SUPER"
    assert Projeto.objects.filter(nome__in=[n for n, _ in PROJETOS_CANONICOS]).count() == 38


def test_command_idempotent(g1):
    call_command("seed_projetos_canonicos")
    assert Projeto.objects.filter(fluxo="SUPER", gerencia=g1).count() == 13  # SUPER nasce na g1
    before = Projeto.objects.count()
    call_command("seed_projetos_canonicos")
    assert Projeto.objects.count() == before  # 2a run nao duplica
