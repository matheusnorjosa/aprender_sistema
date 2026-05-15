"""
Hardening: ``_split_city_uf`` substituído por parser por-separador (sem regex
ambígua) para fechar CodeQL py/polynomial-redos #1 e #2 em
``services/resolvers.py:134,137``.

Cobertura:
- Formatos aceitos pelo parser ("Cidade - UF", "/", "(UF)", ",", sem UF).
- Variantes Unicode de hífen (–, —).
- Cap de tamanho previne DoS quando entrada é absurdamente longa.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportCallIssue=false

from __future__ import annotations

import time

import pytest

from apps.core.services.resolvers import _MAX_CITY_UF_LEN, _is_uf, _split_city_uf


class TestSplitCityUf:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("São Paulo - SP", ("São Paulo", "SP")),
            ("São Paulo/SP", ("São Paulo", "SP")),
            ("São Paulo (SP)", ("São Paulo", "SP")),
            ("São Paulo, SP", ("São Paulo", "SP")),
            ("São Paulo", ("São Paulo", None)),
            # Variantes Unicode de hífen
            ("São Paulo – SP", ("São Paulo", "SP")),  # en-dash
            ("São Paulo — SP", ("São Paulo", "SP")),  # em-dash
            # Espaços extras devem ser colapsados
            ("  São   Paulo  -  SP  ", ("São Paulo", "SP")),
            # Caso UF lowercase: normaliza para upper
            ("Fortaleza - ce", ("Fortaleza", "CE")),
            # Cidade com hífen no nome + UF no final: rfind pega o último " - "
            ("Mato Grosso do Sul - MS", ("Mato Grosso do Sul", "MS")),
        ],
    )
    def test_formatos_aceitos(self, raw, expected):
        assert _split_city_uf(raw) == expected

    def test_none_returns_empty(self):
        assert _split_city_uf(None) == ("", None)

    def test_empty_string(self):
        assert _split_city_uf("") == ("", None)
        assert _split_city_uf("   ") == ("", None)

    def test_invalid_uf_returns_no_uf(self):
        # UF com 3 letras não é UF brasileira válida
        assert _split_city_uf("Brasília - DFG") == ("Brasília - DFG", None)
        # UF com dígito
        assert _split_city_uf("Cidade - S1") == ("Cidade - S1", None)

    def test_long_input_capped_no_dos(self):
        """Entrada com 100k espaços deve retornar em <100ms (sem ReDoS)."""
        malicious = "a" + " " * 100_000
        start = time.perf_counter()
        result = _split_city_uf(malicious)
        elapsed_ms = (time.perf_counter() - start) * 1000
        # Defensive cap aplicado: texto cortado e sem UF parseada
        assert result[1] is None
        assert len(result[0]) <= _MAX_CITY_UF_LEN
        # Deve ser muito rápido — sem catastrophic backtracking
        assert elapsed_ms < 100, f"too slow: {elapsed_ms:.1f}ms"

    def test_long_input_exact_boundary(self):
        # Entrada exatamente no limite + 1 é trimmed
        boundary = "a" * (_MAX_CITY_UF_LEN + 50)
        result = _split_city_uf(boundary)
        assert result[1] is None
        assert len(result[0]) == _MAX_CITY_UF_LEN

    def test_paren_uf_does_not_swallow_internal_paren(self):
        # Não deve perder dados se cidade tem parênteses no nome
        # mas última UF é parseada corretamente
        result = _split_city_uf("Cidade (XPTO) (CE)")
        assert result == ("Cidade (XPTO)", "CE")


class TestIsUf:
    @pytest.mark.parametrize("v", ["SP", "ce", "MG", "Rj", "ba"])
    def test_valid_uf(self, v):
        assert _is_uf(v) is True

    @pytest.mark.parametrize("v", ["", "A", "ABC", "S1", "1B", "ção"])
    def test_invalid_uf(self, v):
        assert _is_uf(v) is False
