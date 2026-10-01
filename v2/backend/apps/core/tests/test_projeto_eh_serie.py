"""Marca explícita de série no Projeto (`Projeto.eh_serie`).

A série/variante (ex.: "A COR DA GENTE 3") não entra na Nova Solicitação nem no Plano Anual (salvo,
no Plano Anual, a série que já tem plano). Antes
a regra era adivinhada pelo nome (termina em número); agora é um campo, editável na tela Projetos.

Cobre: o padrão do campo, a função do preenchimento inicial (migration 0114, a regra antiga sem
exceção), o serializer de admin, os dois endpoints que montam os dropdowns e o seed.

O gate roda com `--no-migrations`: a função da migration é importada e chamada direto; a cadeia
real é exercida pelo job `backend-migrate-integrity`.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false

from __future__ import annotations

import importlib

from django.apps import apps as django_apps
from django.core.cache import cache
from rest_framework.test import APIClient

import pytest

from apps.core.management.commands.seed_projetos_canonicos import seed_projetos_canonicos
from apps.core.models import PlanoFormacoes, Projeto
from apps.core.serializers.organizacao import ProjetoSerializer
from apps.core.tests.factories import MunicipioFactory, ProjetoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def client() -> APIClient:
    cache.clear()  # options/projetos guarda a lista por 5 min
    c = APIClient()
    c.force_authenticate(user=UsuarioFactory(is_superuser=True))
    return c


def _nomes_lookup(client: APIClient, q: str) -> set[str]:
    return {d["label"] for d in client.get(f"/api/lookup/projetos/?q={q}").json()}


def _nomes_options(client: APIClient, params: str = "?exclude_kits=true") -> set[str]:
    return {d["nome"] for d in client.get(f"/api/options/projetos/{params}").json()}


# ── o campo ──────────────────────────────────────────────────────────────────────────────────
def test_projeto_novo_nao_e_serie():
    assert Projeto.objects.create(nome="Projeto Marca Padrão", fluxo="NAO_SUPER").eh_serie is False


def test_preenchimento_inicial_marca_so_nome_terminado_em_numero():
    marcar = importlib.import_module("apps.core.migrations.0114_projeto_eh_serie_backfill").marcar_series
    nomes = ["MARCA X", "MARCA X 3", "MARCA X 12", "MARCA X BEBÊ", "MARCA X 3 anos"]
    for nome in nomes:
        Projeto.objects.create(nome=nome, fluxo="NAO_SUPER")

    marcar(django_apps, None)

    marcados = set(Projeto.objects.filter(nome__in=nomes, eh_serie=True).values_list("nome", flat=True))
    assert marcados == {"MARCA X 3", "MARCA X 12"}


def test_serializer_devolve_e_grava_a_marca():
    projeto = ProjetoFactory(nome="Marca Serializer")
    assert ProjetoSerializer(projeto).data["eh_serie"] is False

    s = ProjetoSerializer(projeto, data={"eh_serie": True}, partial=True)
    assert s.is_valid(), s.errors
    s.save()
    projeto.refresh_from_db()
    assert projeto.eh_serie is True


def test_seed_marca_a_variante_numerada():
    # Banco novo: sem a marca, "Projeto Amma 1" entraria na Nova Solicitação (antes o nome o escondia).
    seed_projetos_canonicos([("Seed Marca", "NAO_SUPER"), ("Seed Marca 4", "NAO_SUPER")])
    assert Projeto.objects.get(nome="Seed Marca").eh_serie is False
    assert Projeto.objects.get(nome="Seed Marca 4").eh_serie is True


# ── os dropdowns leem a marca, não o nome ────────────────────────────────────────────────────
def test_numerado_sem_a_marca_aparece_nos_dois_dropdowns(client):
    ProjetoFactory(nome="Fluir das Emoções 1", eh_serie=False)

    assert "Fluir das Emoções 1" in _nomes_lookup(client, "Fluir")
    assert "Fluir das Emoções 1" in _nomes_options(client)


def test_marcado_sem_numero_some_dos_dois_dropdowns(client):
    ProjetoFactory(nome="BRINCANDO E APRENDENDO BEBÊ", eh_serie=True)

    assert "BRINCANDO E APRENDENDO BEBÊ" not in _nomes_lookup(client, "BRINCANDO")
    assert "BRINCANDO E APRENDENDO BEBÊ" not in _nomes_options(client)


def test_marcado_volta_com_include_kits_e_sem_exclude_kits(client):
    ProjetoFactory(nome="BRINCANDO E APRENDENDO BEBÊ", eh_serie=True)

    lookup = {d["label"] for d in client.get("/api/lookup/projetos/?q=BRINCANDO&include_kits=true").json()}
    assert "BRINCANDO E APRENDENDO BEBÊ" in lookup
    assert "BRINCANDO E APRENDENDO BEBÊ" in _nomes_options(client, "")  # Compras/DAT: todas as variantes


# ── Plano Anual: a série que já tem plano continua na lista (decisão do dono, 02/10) ─────────
def _plano(projeto: Projeto, ano: int = 2026) -> PlanoFormacoes:
    return PlanoFormacoes.objects.create(
        projeto=projeto, municipio=MunicipioFactory(), ano=ano, created_by=UsuarioFactory()
    )


def test_serie_com_plano_vem_no_plano_anual_e_segue_fora_da_nova_solicitacao(client):
    # "Projeto Catavento 2" e "3" continuam série (na Nova Solicitação só aparece "Cataventos"), mas
    # os 17 planos deles não podem sumir do filtro e do formulário do Plano Anual.
    com_plano = ProjetoFactory(nome="Projeto Catavento 2", eh_serie=True)
    ProjetoFactory(nome="Projeto Catavento 9", eh_serie=True)  # série sem plano: continua oculta
    ProjetoFactory(nome="Cataventos", eh_serie=False)
    _plano(com_plano, 2025)
    _plano(com_plano, 2026)

    options = [d["nome"] for d in client.get("/api/options/projetos/?exclude_kits=true").json()]
    assert sorted(n for n in options if "Catavento" in n) == ["Cataventos", "Projeto Catavento 2"]  # 1x só

    assert _nomes_lookup(client, "Catavento") == {"Cataventos"}


def test_serie_com_plano_respeita_ativo_e_is_test(client):
    _plano(ProjetoFactory(nome="Série Inativa 2", eh_serie=True, ativo=False))
    _plano(ProjetoFactory(nome="Série Teste 2", eh_serie=True, is_test=True))

    assert _nomes_options(client).isdisjoint({"Série Inativa 2", "Série Teste 2"})
    assert "Série Teste 2" in _nomes_options(client, "?exclude_kits=true&include_test=true")
