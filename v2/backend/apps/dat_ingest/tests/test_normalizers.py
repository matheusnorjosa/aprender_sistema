"""
Tests: Normalizers
Valida funções de normalização de dados (services/normalizers.py).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false

from __future__ import annotations
import datetime

import pytest

from apps.dat_ingest.services.normalizers import (
    generate_cpf_from_email,
    make_iso_datetime,
    make_sha256_hash,
    normalize_cpf,
    normalize_email,
    normalize_str,
    normalize_telefone,
    normalize_text,
    normalize_uf,
    parse_bool,
    parse_datetime,
    parse_time,
    split_municipio_uf,
    titlecase,
    validate_row_data,
)


class TestNormalizeStr:
    """Testes para normalize_str()"""

    def test_removes_leading_trailing_spaces(self):
        assert normalize_str("  João Silva  ") == "João Silva"

    def test_collapses_multiple_spaces(self):
        assert normalize_str("João    Silva") == "João Silva"

    def test_returns_empty_string_for_none(self):
        assert normalize_str(None) == ""

    def test_converts_to_string(self):
        assert normalize_str(123) == "123"

    def test_handles_empty_string(self):
        assert normalize_str("") == ""


class TestNormalizeCpf:
    """Testes para normalize_cpf()"""

    def test_removes_formatting(self):
        assert normalize_cpf("123.456.789-01") == "12345678901"

    def test_handles_cpf_without_formatting(self):
        assert normalize_cpf("12345678901") == "12345678901"

    def test_pads_with_zeros_if_less_than_11_digits(self):
        assert normalize_cpf("123456789") == "00123456789"

    def test_handles_float_cpf(self):
        # Planilhas podem retornar CPF como float
        assert normalize_cpf(12345678901.0) == "12345678901"

    def test_returns_empty_string_for_none(self):
        assert normalize_cpf(None) == ""

    def test_truncates_if_more_than_11_digits(self):
        assert normalize_cpf("123456789012345") == "12345678901"


class TestNormalizeTelefone:
    """Testes para normalize_telefone()"""

    def test_removes_formatting(self):
        assert normalize_telefone("(85) 99999-9999") == "85999999999"

    def test_handles_telefone_without_formatting(self):
        assert normalize_telefone("85999999999") == "85999999999"

    def test_handles_float_telefone(self):
        assert normalize_telefone(85999999999.0) == "85999999999"

    def test_returns_empty_string_for_none(self):
        assert normalize_telefone(None) == ""

    def test_removes_spaces_and_hyphens(self):
        assert normalize_telefone("85 9 9999-9999") == "85999999999"


class TestNormalizeEmail:
    """Testes para normalize_email()"""

    def test_converts_to_lowercase(self):
        assert normalize_email("JoAo@EXAMPLE.COM") == "joao@example.com"

    def test_removes_leading_trailing_spaces(self):
        assert normalize_email("  joao@example.com  ") == "joao@example.com"

    def test_returns_empty_string_for_none(self):
        assert normalize_email(None) == ""

    def test_handles_valid_email(self):
        assert normalize_email("joao.silva@example.com") == "joao.silva@example.com"


class TestNormalizeUf:
    """Testes para normalize_uf()"""

    def test_converts_ceara_to_ce(self):
        assert normalize_uf("Ceará") == "CE"

    def test_converts_sao_paulo_to_sp(self):
        assert normalize_uf("São Paulo") == "SP"

    def test_handles_sigla_already(self):
        assert normalize_uf("CE") == "CE"

    def test_handles_lowercase_sigla(self):
        assert normalize_uf("ce") == "CE"

    def test_returns_empty_string_for_unknown(self):
        assert normalize_uf("Unknown") == ""

    def test_returns_empty_string_for_none(self):
        assert normalize_uf(None) == ""


class TestTitlecase:
    """Testes para titlecase()"""

    def test_capitalizes_first_letter_of_words(self):
        assert titlecase("joão silva") == "João Silva"

    def test_preserves_conectores_lowercase(self):
        assert titlecase("prefeitura de fortaleza") == "Prefeitura de Fortaleza"

    def test_handles_multiple_conectores(self):
        assert titlecase("secretaria da educação do ceará") == "Secretaria da Educação do Ceará"

    def test_returns_empty_string_for_none(self):
        assert titlecase(None) == ""


class TestParseBool:
    """Testes para parse_bool()"""

    def test_parses_sim_as_true(self):
        assert parse_bool("Sim") is True

    def test_parses_nao_as_false(self):
        assert parse_bool("Não") is False

    def test_parses_1_as_true(self):
        assert parse_bool(1) is True
        assert parse_bool("1") is True

    def test_parses_0_as_false(self):
        assert parse_bool(0) is False
        assert parse_bool("0") is False

    def test_parses_true_false_strings(self):
        assert parse_bool("true") is True
        assert parse_bool("false") is False

    def test_case_insensitive(self):
        assert parse_bool("SIM") is True
        assert parse_bool("NÃO") is False


class TestNormalizeText:
    """Testes para normalize_text()"""

    def test_removes_accents(self):
        assert normalize_text("João José") == "joao jose"

    def test_removes_special_characters(self):
        assert normalize_text("Olá! Como vai?") == "ola como vai"

    def test_converts_to_lowercase(self):
        assert normalize_text("JOÃO SILVA") == "joao silva"

    def test_collapses_spaces(self):
        assert normalize_text("João    Silva") == "joao silva"

    def test_returns_empty_string_for_none(self):
        assert normalize_text(None) == ""


class TestParseTime:
    """Testes para parse_time()"""

    def test_parses_hhmm_format(self):
        time_obj = parse_time("14:30")
        assert time_obj.hour == 14
        assert time_obj.minute == 30

    def test_parses_hh_format(self):
        time_obj = parse_time("14")
        assert time_obj.hour == 14
        assert time_obj.minute == 0

    def test_parses_excel_float(self):
        # 0.5 = 12:00 (meio-dia)
        time_obj = parse_time(0.5)
        assert time_obj.hour == 12
        assert time_obj.minute == 0

    def test_returns_none_for_invalid(self):
        assert parse_time("invalid") is None

    def test_returns_none_for_none(self):
        assert parse_time(None) is None


class TestParseDatetime:
    """Testes para parse_datetime()"""

    def test_parses_date_and_time_strings(self):
        dt = parse_datetime("2025-01-15", "14:30")
        assert dt.year == 2025
        assert dt.month == 1
        assert dt.day == 15
        assert dt.hour == 14
        assert dt.minute == 30

    def test_returns_none_if_date_is_none(self):
        assert parse_datetime(None, "14:30") is None

    def test_defaults_to_00_00_if_time_is_none(self):
        dt = parse_datetime("2025-01-15", None)
        assert dt.hour == 0
        assert dt.minute == 0


class TestSplitMunicipioUf:
    """Testes para split_municipio_uf()"""

    def test_splits_municipio_uf_with_hyphen(self):
        nome, uf = split_municipio_uf("Fortaleza - CE")
        assert nome == "Fortaleza"
        assert uf == "CE"

    def test_splits_municipio_uf_with_slash(self):
        nome, uf = split_municipio_uf("Fortaleza/CE")
        assert nome == "Fortaleza"
        assert uf == "CE"

    def test_returns_none_uf_if_no_separator(self):
        nome, uf = split_municipio_uf("Fortaleza")
        assert nome == "Fortaleza"
        assert uf == ""

    def test_returns_empty_strings_for_none(self):
        nome, uf = split_municipio_uf(None)
        assert nome == ""
        assert uf == ""


class TestMakeSha256Hash:
    """Testes para make_sha256_hash()"""

    def test_generates_consistent_hash(self):
        hash1 = make_sha256_hash("joao@example.com", "2025-01-15")
        hash2 = make_sha256_hash("joao@example.com", "2025-01-15")
        assert hash1 == hash2

    def test_different_inputs_generate_different_hashes(self):
        hash1 = make_sha256_hash("joao@example.com", "2025-01-15")
        hash2 = make_sha256_hash("maria@example.com", "2025-01-15")
        assert hash1 != hash2

    def test_hash_is_64_chars(self):
        hash_value = make_sha256_hash("test")
        assert len(hash_value) == 64

    def test_handles_none_values(self):
        # Deve converter None para string vazia
        hash1 = make_sha256_hash("test", None)
        hash2 = make_sha256_hash("test", "")
        assert hash1 == hash2


class TestGenerateCpfFromEmail:
    """Testes para generate_cpf_from_email()"""

    def test_generates_11_digit_cpf(self):
        cpf = generate_cpf_from_email("joao@example.com")
        assert len(cpf) == 11
        assert cpf.isdigit()

    def test_generates_consistent_cpf_for_same_email(self):
        cpf1 = generate_cpf_from_email("joao@example.com")
        cpf2 = generate_cpf_from_email("joao@example.com")
        assert cpf1 == cpf2

    def test_different_emails_generate_different_cpfs(self):
        cpf1 = generate_cpf_from_email("joao@example.com")
        cpf2 = generate_cpf_from_email("maria@example.com")
        assert cpf1 != cpf2


class TestMakeIsoDatetime:
    """Testes para make_iso_datetime()"""

    def test_converts_datetime_to_iso_string(self):
        dt = datetime.datetime(2025, 1, 15, 14, 30)
        iso_str = make_iso_datetime(dt)
        assert iso_str == "2025-01-15T14:30:00"

    def test_returns_empty_string_for_none(self):
        assert make_iso_datetime(None) == ""


class TestValidateRowData:
    """Testes para validate_row_data()"""

    def test_returns_true_for_valid_row(self):
        row = {"nome": "João", "email": "joao@example.com"}
        fields = ["nome", "email"]
        assert validate_row_data(row, fields) is True

    def test_returns_false_if_required_field_missing(self):
        row = {"nome": "João"}
        fields = ["nome", "email"]
        assert validate_row_data(row, fields) is False

    def test_returns_false_if_required_field_is_empty(self):
        row = {"nome": "", "email": "joao@example.com"}
        fields = ["nome", "email"]
        assert validate_row_data(row, fields) is False

    def test_returns_false_if_required_field_is_none(self):
        row = {"nome": None, "email": "joao@example.com"}
        fields = ["nome", "email"]
        assert validate_row_data(row, fields) is False
