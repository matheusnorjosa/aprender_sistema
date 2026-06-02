"""
Tests para o resolver de Projeto do import do export-contract (Gap C).

Cobre canonicalização determinística (& <-> E, hífen, prefixo PROJETO, vírgula) +
aliases escopados por família (Superativar -> Linguagens, ACerta Brasil -> Língua
Portuguesa, Brincando e Aprendendo Professor) e falha explícita em ambiguidade.

O DB é o SSOT do catálogo (123 projetos). NÃO importa dados — só resolve nomes.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false

from __future__ import annotations

import pytest

from apps.core.models import Projeto
from apps.core.services.export_contract_projeto_resolver import resolve_projeto_export

pytestmark = pytest.mark.django_db


@pytest.fixture
def catalogo():
    """Subconjunto do catálogo canônico do DB (formas exatas armazenadas)."""
    nomes = [
        "Vida & Matemática 6",
        "Superativar Matemática 4",
        "Uni Duni Tê 4",
        "Ler, Ouvir e Contar 1",
        "Escrever Comunicar e Ser",
        "Superativar Linguagens 3",
        "Superativar Linguagens 4",
        "Superativar Linguagens 5",
        "ACerta Brasil Língua Portuguesa",
        "Brincando e Aprendendo",
        "ACerta Português",
        "Avançando Juntos Português",
    ]
    return {n: Projeto.objects.create(nome=n, fluxo="NAO_SUPER") for n in nomes}


def _assert_matches(raw, expected_nome):
    res = resolve_projeto_export(raw)
    assert res.status == "matched", f"{raw!r} -> {res.status} ({res.reason})"
    assert res.projeto is not None
    assert res.projeto.nome == expected_nome, f"{raw!r} -> {res.projeto.nome!r} (esperado {expected_nome!r})"


# ---------- regras determinísticas ----------
def test_e_vira_ampersand(catalogo):
    _assert_matches("VIDA E MATEMATICA 6", "Vida & Matemática 6")


def test_remove_hifen_separador(catalogo):
    _assert_matches("SUPERATIVAR - MATEMATICA 4", "Superativar Matemática 4")


def test_remove_prefixo_projeto(catalogo):
    _assert_matches("PROJETO UNI DUNI TÊ 4", "Uni Duni Tê 4")


def test_normaliza_virgula_add(catalogo):
    _assert_matches("LER OUVIR E CONTAR 1", "Ler, Ouvir e Contar 1")


def test_normaliza_virgula_del(catalogo):
    _assert_matches("ESCREVER, COMUNICAR E SER", "Escrever Comunicar e Ser")


# ---------- aliases escopados ----------
@pytest.mark.parametrize("n", [3, 4, 5])
def test_superativar_portugues_vira_linguagens(catalogo, n):
    _assert_matches(f"SUPERATIVAR - PORTUGUES {n}", f"Superativar Linguagens {n}")


@pytest.mark.parametrize("n", [3, 4, 5])
def test_superativar_lingua_portuguesa_vira_linguagens(catalogo, n):
    _assert_matches(f"SUPERATIVAR LINGUA PORTUGUESA {n}", f"Superativar Linguagens {n}")


def test_acerta_brasil_portugues_vira_lingua_portuguesa(catalogo):
    _assert_matches("ACERTA BRASIL PORTUGUES", "ACerta Brasil Língua Portuguesa")


def test_brincando_professor_vira_brincando(catalogo):
    _assert_matches("BRINCANDO E APRENDENDO PROFESSOR", "Brincando e Aprendendo")


# ---------- NÃO mapear (sem regra global Português) ----------
def test_acerta_portugues_nao_vira_brasil_lingua_portuguesa(catalogo):
    res = resolve_projeto_export("ACERTA PORTUGUES")
    assert res.status == "matched"
    assert res.projeto.nome == "ACerta Português"


def test_avancando_juntos_portugues_nao_vira_lingua_portuguesa(catalogo):
    res = resolve_projeto_export("AVANÇANDO JUNTOS PORTUGUÊS")
    assert res.status == "matched"
    assert res.projeto.nome == "Avançando Juntos Português"


# ---------- ambiguidade falha explícita ----------
def test_ambiguidade_falha_explicita(db):
    # Dois projetos que colapsam para a mesma chave canônica (& <-> E).
    # Raw com hífen NÃO casa nenhum norm exato → cai na chave canônica, que casa os 2 → ambíguo.
    Projeto.objects.create(nome="Vida & Matemática 6", fluxo="NAO_SUPER")
    Projeto.objects.create(nome="Vida E Matemática 6", fluxo="NAO_SUPER")
    res = resolve_projeto_export("VIDA - E - MATEMATICA 6")
    assert res.status == "ambiguous", f"esperado ambiguous, veio {res.status}"
    assert res.projeto is None
    assert len(res.candidates) >= 2


def test_sem_match_retorna_unmatched(catalogo):
    res = resolve_projeto_export("PROJETO TOTALMENTE INEXISTENTE XYZ")
    assert res.status == "unmatched"
    assert res.projeto is None


def test_vazio_retorna_unmatched(catalogo):
    res = resolve_projeto_export("")
    assert res.status == "unmatched"
