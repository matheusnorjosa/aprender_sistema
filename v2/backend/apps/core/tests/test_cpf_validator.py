"""
Testes do validador de CPF (mod-11) — #1578.

O importer export-contract (e futuros callers) precisam REJEITAR CPF
estruturalmente inválido, não só checar comprimento (`len == 11`). Este módulo
(`apps.core.validators`) é o SSOT da validação; os testes fixam o contrato:

- ``is_valid_cpf``      : 11 dígitos + dígitos verificadores mod-11 conferem.
- ``is_cpf_placeholder``: sequências de dígito repetido (00000000000..99999999999).
- ``classify_cpf``      : ``absent`` (vazio/placeholder) | ``valid`` | ``invalid``.

CPFs abaixo são SINTÉTICOS (dígitos verificadores calculados), não são de pessoas
reais — não há PII aqui.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false

from __future__ import annotations

import pytest

from apps.core.validators import (
    CPF_ABSENT,
    CPF_INVALID,
    CPF_VALID,
    classify_cpf,
    is_cpf_placeholder,
    is_valid_cpf,
    normalize_cpf,
)

# Válidos: dígitos verificadores conferem (mod-11).
VALID_CPFS = ["11144477735", "22255588846", "33366699957"]
# Inválidos por checksum: 11 dígitos, NÃO placeholder, DV errado. Inclui os CPFs
# que a suíte antiga usava como se fossem válidos (11122233344, 55566677788).
INVALID_CHECKSUM_CPFS = ["12345678900", "11122233344", "55566677788", "12398712399"]
# Placeholders: dígito repetido (passam no checksum mas são inválidos por definição).
PLACEHOLDER_CPFS = ["00000000000", "11111111111", "99999999999"]


class TestIsValidCpf:
    @pytest.mark.parametrize("cpf", VALID_CPFS)
    def test_accepts_valid(self, cpf):
        assert is_valid_cpf(cpf) is True

    @pytest.mark.parametrize("cpf", INVALID_CHECKSUM_CPFS)
    def test_rejects_bad_checksum(self, cpf):
        assert is_valid_cpf(cpf) is False

    @pytest.mark.parametrize("cpf", PLACEHOLDER_CPFS)
    def test_rejects_placeholder(self, cpf):
        assert is_valid_cpf(cpf) is False

    def test_rejects_wrong_length(self):
        assert is_valid_cpf("123") is False
        assert is_valid_cpf("111444777350") is False  # 12 dígitos
        assert is_valid_cpf("") is False

    def test_accepts_masked_input(self):
        # Aceita máscara — conta só os dígitos (reusa normalize_cpf_digits).
        assert is_valid_cpf("111.444.777-35") is True

    def test_none_is_not_valid(self):
        assert is_valid_cpf(None) is False


class TestIsCpfPlaceholder:
    @pytest.mark.parametrize("cpf", PLACEHOLDER_CPFS)
    def test_repeated_digits_are_placeholder(self, cpf):
        assert is_cpf_placeholder(cpf) is True

    def test_real_cpf_is_not_placeholder(self):
        assert is_cpf_placeholder("11144477735") is False

    def test_short_repeated_is_not_placeholder(self):
        # Placeholder exige 11 dígitos; "000" não é.
        assert is_cpf_placeholder("000") is False


class TestClassifyCpf:
    @pytest.mark.parametrize("cpf", VALID_CPFS)
    def test_valid(self, cpf):
        assert classify_cpf(cpf) == CPF_VALID

    @pytest.mark.parametrize("cpf", INVALID_CHECKSUM_CPFS + ["123"])
    def test_invalid(self, cpf):
        # DV errado ou comprimento errado (não-placeholder) → inválido.
        assert classify_cpf(cpf) == CPF_INVALID

    @pytest.mark.parametrize("cpf", ["", "   ", None])
    def test_empty_is_absent(self, cpf):
        assert classify_cpf(cpf) == CPF_ABSENT

    @pytest.mark.parametrize("cpf", PLACEHOLDER_CPFS)
    def test_placeholder_is_absent(self, cpf):
        # Item 4 da #1578: placeholder tratado como AUSENTE, não "inválido".
        assert classify_cpf(cpf) == CPF_ABSENT


def test_normalize_cpf_strips_mask_and_tolerates_none():
    assert normalize_cpf("111.444.777-35") == "11144477735"
    assert normalize_cpf(None) == ""
    assert normalize_cpf("  111 444 777 35 ") == "11144477735"
