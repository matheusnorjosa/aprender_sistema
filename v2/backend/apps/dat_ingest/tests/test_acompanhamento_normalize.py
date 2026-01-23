"""
Testes para funções de normalização do ETL de Acompanhamento.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from datetime import date, time

from apps.dat_ingest.services.acompanhamento_normalize import (
    norm_text,
    normalize_sector,
    parse_date_iso,
    parse_time_iso,
    split_municipios_super,
)


def test_norm_text():
    """Testa normalização de texto."""
    assert norm_text("  Fortaleza   ") == "fortaleza"
    assert norm_text("São Paulo") == "sao paulo"
    assert norm_text("MÚLTIPLOS  ESPAÇOS") == "multiplos espacos"


def test_normalize_sector():
    """Testa mapeamento de setores."""
    assert normalize_sector("ACerta", "") == "ACerta"
    assert normalize_sector("Brincando", "") == "Brincando"
    assert normalize_sector("Vidas", "") == "Vidas"
    assert normalize_sector("Super", "") == "Super"
    assert normalize_sector("Outros", "IDEB") == "Gestão Escolar"
    assert normalize_sector("Outros", "Vidas L") == "Vida & Linguagem"
    assert normalize_sector("Outros", "Vidas M") == "Vida & Matemática"
    assert normalize_sector("Outros", "Vidas C") == "Vida & Ciências"
    assert normalize_sector("Outros", "Outro Projeto") == "Outros"


def test_split_municipios_super():
    """Testa split de múltiplos municípios."""
    assert split_municipios_super("Fortaleza; Caucaia") == ["Fortaleza", "Caucaia"]
    assert split_municipios_super("A, B / C | D") == ["A", "B", "C", "D"]
    assert split_municipios_super("") == []


def test_parse_date_iso():
    """Testa parse de data ISO."""
    assert parse_date_iso("2025-01-15") == date(2025, 1, 15)
    assert parse_date_iso("invalid") is None
    assert parse_date_iso("") is None


def test_parse_time_iso():
    """Testa parse de hora ISO."""
    assert parse_time_iso("14:30") == time(14, 30, 0)
    assert parse_time_iso("14:30:45") == time(14, 30, 45)
    assert parse_time_iso("invalid") is None
    assert parse_time_iso("") is None
