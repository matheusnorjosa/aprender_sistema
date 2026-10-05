"""
Tests para o resolver de Projeto do import do export-contract (Gap C).

Cobre canonicalização determinística (& <-> E, hífen, prefixo PROJETO, vírgula) +
aliases escopados por família (Superativar -> Linguagens, ACerta Brasil -> ACerta, Fluir das
Emoções -> Fluir das Emoções (Antigo), Brincando e Aprendendo Professor) e falha explícita em
ambiguidade. Os apelidos de ACerta Brasil e de Fluir são testados nos dois estados do catálogo:
antes e depois do script de dados que junta/renomeia o projeto.

O DB é o SSOT do catálogo (123 projetos). NÃO importa dados — só resolve nomes.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false

from __future__ import annotations

import pytest

from apps.core.services.export_contract_projeto_resolver import resolve_projeto_export
from apps.core.tests.factories import ProjetoFactory

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
    return {n: ProjetoFactory(nome=n, fluxo="NAO_SUPER") for n in nomes}


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


def test_acerta_brasil_portugues_vira_acerta_portugues(catalogo):
    # Decisão do dono (02/10): ACerta Brasil é juntado em ACerta. O alvo antigo do apelido
    # ("ACerta Brasil Língua Portuguesa") nunca existiu em prod.
    _assert_matches("ACERTA BRASIL PORTUGUES", "ACerta Português")


def test_brincando_professor_vira_brincando(catalogo):
    _assert_matches("BRINCANDO E APRENDENDO PROFESSOR", "Brincando e Aprendendo")


# ---------- nome exato vence apelido (RELAY-53, defeito B) ----------
@pytest.fixture
def catalogo_prod_acerta():
    """Catálogo ACerta como está em prod (2026-10-01): existe 'ACERTA BRASIL PORTUGUES' (id 45) e
    NÃO existe 'ACerta Brasil Língua Portuguesa', o alvo do apelido escopado."""
    nomes = ["ACERTA BRASIL PORTUGUES", "ACERTA BRASIL MATEMATICA", "ACerta Português", "ACerta Matemática"]
    return {n: ProjetoFactory(nome=n, fluxo="NAO_SUPER") for n in nomes}


def test_nome_exato_resolve_quando_alvo_do_apelido_nao_existe(catalogo_prod_acerta):
    # Antes: o apelido apontava para um nome ausente do catálogo e devolvia `unmatched`,
    # sombreando o projeto de nome idêntico — 31 compras (11.049 unidades, 12 municípios) e
    # 12 linhas de dat_registro ficaram de fora em prod.
    _assert_matches("ACERTA BRASIL PORTUGUES", "ACERTA BRASIL PORTUGUES")


def test_apelido_com_alvo_ausente_nao_sombreia_regra_canonica(catalogo_prod_acerta):
    # Com hífen não há match exato; o apelido (chave canônica) aponta para nome ausente e
    # não pode encerrar a busca — a regra determinística ainda casa o projeto existente.
    _assert_matches("ACERTA BRASIL - PORTUGUES", "ACERTA BRASIL PORTUGUES")


def test_nome_exato_vence_apelido_mesmo_com_alvo_existente(db):
    exato = ProjetoFactory(nome="Brincando e Aprendendo Professor", fluxo="NAO_SUPER")
    ProjetoFactory(nome="Brincando e Aprendendo", fluxo="NAO_SUPER")
    res = resolve_projeto_export("BRINCANDO E APRENDENDO PROFESSOR")
    assert res.status == "matched"
    assert res.projeto == exato
    assert res.matched_via == "norm"


def test_antes_da_fusao_grafia_com_hifen_fica_no_projeto_antigo(catalogo_prod_acerta):
    # O PR pode ir para prod ANTES do script de fusão: enquanto "ACERTA BRASIL ..." existir, nenhuma
    # grafia da planilha pode ser desviada para "ACerta ..." pelo apelido (compra iria para o projeto
    # errado e viraria would_create). Nome no catálogo (exato ou canônico) vence o apelido.
    _assert_matches("ACERTA BRASIL MATEMATICA", "ACERTA BRASIL MATEMATICA")
    _assert_matches("ACERTA BRASIL - MATEMATICA", "ACERTA BRASIL MATEMATICA")
    _assert_matches("PROJETO ACERTA BRASIL PORTUGUES", "ACERTA BRASIL PORTUGUES")


# ---------- ACerta Brasil juntado em ACerta (decisão do dono, 02/10) ----------
@pytest.fixture
def catalogo_acerta_pos_fusao():
    """Depois do script de dados: "ACERTA BRASIL MATEMATICA/PORTUGUES" não existem mais."""
    nomes = ["ACerta Português", "ACerta Matemática"]
    return {n: ProjetoFactory(nome=n, fluxo="NAO_SUPER") for n in nomes}


@pytest.mark.parametrize(
    ("raw", "esperado"),
    [
        ("ACERTA BRASIL MATEMATICA", "ACerta Matemática"),
        ("ACERTA BRASIL - MATEMATICA", "ACerta Matemática"),
        ("ACERTA BRASIL PORTUGUES", "ACerta Português"),
        ("ACERTA BRASIL PORTUGUÊS", "ACerta Português"),
        ("ACERTA BRASIL LINGUA PORTUGUESA", "ACerta Português"),
        ("ACerta Brasil Língua Portuguesa", "ACerta Português"),
    ],
)
def test_depois_da_fusao_acerta_brasil_cai_em_acerta(catalogo_acerta_pos_fusao, raw, esperado):
    res = resolve_projeto_export(raw)
    assert res.status == "matched", f"{raw!r} -> {res.status} ({res.reason})"
    assert res.projeto.nome == esperado
    assert res.matched_via == "alias"


# ---------- Fluir das Emoções renomeado para "(Antigo)" (decisão do dono, 02/10) ----------
_FLUIR_SERIES = ["Fluir das Emoções 1", "Fluir das Emoções 2", "Fluir das Emoções 3"]


def test_fluir_antes_do_rename_resolve_pelo_nome_exato(db):
    for n in ["Fluir das Emoções", *_FLUIR_SERIES]:
        ProjetoFactory(nome=n, fluxo="NAO_SUPER")
    res = resolve_projeto_export("FLUIR DAS EMOÇÕES")
    assert res.projeto.nome == "Fluir das Emoções"
    assert res.matched_via == "norm"


def test_fluir_depois_do_rename_resolve_para_o_antigo(db):
    # A planilha continua mandando "FLUIR DAS EMOÇÕES"; sem o apelido o nome viraria `unmatched`
    # e o master `projeto` recriaria o projeto sem "(Antigo)".
    for n in ["Fluir das Emoções (Antigo)", *_FLUIR_SERIES]:
        ProjetoFactory(nome=n, fluxo="NAO_SUPER")
    res = resolve_projeto_export("FLUIR DAS EMOÇÕES")
    assert res.status == "matched", res.reason
    assert res.projeto.nome == "Fluir das Emoções (Antigo)"
    assert res.matched_via == "alias"


@pytest.mark.parametrize("antigo", ["Fluir das Emoções", "Fluir das Emoções (Antigo)"])
@pytest.mark.parametrize("n", [1, 2, 3])
def test_fluir_numerado_nunca_cai_no_antigo(db, antigo, n):
    for nome in [antigo, *_FLUIR_SERIES]:
        ProjetoFactory(nome=nome, fluxo="NAO_SUPER")
    _assert_matches(f"FLUIR DAS EMOÇÕES - {n}", f"Fluir das Emoções {n}")
    _assert_matches(f"FLUIR DAS EMOÇÕES {n}", f"Fluir das Emoções {n}")


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
    ProjetoFactory(nome="Vida & Matemática 6", fluxo="NAO_SUPER")
    ProjetoFactory(nome="Vida E Matemática 6", fluxo="NAO_SUPER")
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


# ---------- nomes antigos que não existem mais em prod (decisão do dono, 05/10) ----------
@pytest.fixture
def catalogo_pos_renomeacao_05_10():
    """Prod depois dos scripts de 05/10: os nomes antigos foram apagados/renomeados."""
    nomes = [
        "ECS",
        "ED FINANCEIRA 1",
        "ED FINANCEIRA 2",
        "ED FINANCEIRA 3",
        "ED FINANCEIRA 4",
        "PROJETO AMMA 1",
        "PROJETO AMMA 2",
    ]
    return {n: ProjetoFactory(nome=n, fluxo="NAO_SUPER") for n in nomes}


@pytest.mark.parametrize(
    ("raw", "esperado"),
    [
        ("ESCREVER, COMUNICAR E SER", "ECS"),
        ("ESCREVER COMUNICAR E SER", "ECS"),
        ("EDUCAÇÃO FINANCEIRA LIVRO 1", "ED FINANCEIRA 1"),
        ("EDUCAÇÃO FINANCEIRA LIVRO 2", "ED FINANCEIRA 2"),
        ("EDUCAÇÃO FINANCEIRA LIVRO 3", "ED FINANCEIRA 3"),
        ("EDUCACAO FINANCEIRA LIVRO 4", "ED FINANCEIRA 4"),
        ("APRENDENDO MAIS MATEMÁTICA 1", "PROJETO AMMA 1"),
        ("APRENDENDO MAIS MATEMATICA 2", "PROJETO AMMA 2"),
    ],
)
def test_nome_antigo_cai_no_nome_de_prod(catalogo_pos_renomeacao_05_10, raw, esperado):
    # Sem o apelido o nome antigo vira `unmatched` e o master `projeto` de um pacote velho o recriaria.
    res = resolve_projeto_export(raw)
    assert res.status == "matched", f"{raw!r} -> {res.status} ({res.reason})"
    assert res.projeto.nome == esperado
    assert res.matched_via == "alias"


def test_nome_antigo_ainda_no_catalogo_vence_o_apelido(db):
    # Antes do script que apaga o projeto antigo, o nome exato continua casando nele.
    antigo = ProjetoFactory(nome="ESCREVER COMUNICAR E SER", fluxo="NAO_SUPER")
    ProjetoFactory(nome="ECS", fluxo="NAO_SUPER")
    res = resolve_projeto_export("ESCREVER, COMUNICAR E SER")
    assert res.projeto == antigo
