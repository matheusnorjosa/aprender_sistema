"""
Testes para helper project_normalizer.py.

Valida:
- normalize_project_name() com variantes conhecidas
- is_known_variant() edge cases
- get_canonical_name() comportamento correto
- list_all_variants() completude

Issue: #150
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

import pytest

from apps.core.services.project_normalizer import (
    CANONICAL_PROJECT_NAMES,
    get_canonical_name,
    is_known_variant,
    list_all_variants,
    normalize_project_name,
)


class TestNormalizeProjectName:
    """Testes para função normalize_project_name()."""

    def test_normalizes_leio_variant_without_commas(self) -> None:
        """Deve normalizar 'LEIO ESCREVO E CALCULO' para versão com vírgulas."""
        result = normalize_project_name("LEIO ESCREVO E CALCULO")
        assert result == "LEIO, ESCREVO E CALCULO"

    def test_normalizes_leio_variant_lowercase(self) -> None:
        """Deve normalizar 'leio escrevo e calculo' (lowercase) para versão canônica."""
        result = normalize_project_name("leio escrevo e calculo")
        assert result == "LEIO, ESCREVO E CALCULO"

    def test_normalizes_leio_variant_with_whitespace(self) -> None:
        """Deve normalizar '  LEIO ESCREVO E CALCULO  ' (com espaços) para versão canônica."""
        result = normalize_project_name("  LEIO ESCREVO E CALCULO  ")
        assert result == "LEIO, ESCREVO E CALCULO"

    def test_normalizes_gestao_escolar_mixed_case(self) -> None:
        """Deve normalizar 'Gestão Escolar' para 'GESTÃO ESCOLAR'."""
        result = normalize_project_name("Gestão Escolar")
        assert result == "GESTÃO ESCOLAR"

    def test_normalizes_gestao_escolar_without_accents(self) -> None:
        """Deve normalizar 'GESTAO ESCOLAR' (sem acentos) para 'GESTÃO ESCOLAR'."""
        result = normalize_project_name("GESTAO ESCOLAR")
        assert result == "GESTÃO ESCOLAR"

    def test_normalizes_ideb10_legacy_name(self) -> None:
        """Deve normalizar 'IDEB10' (nome antigo) para 'GESTÃO ESCOLAR'."""
        result = normalize_project_name("IDEB10")
        assert result == "GESTÃO ESCOLAR"

    def test_normalizes_ler_ouvir_variant_without_commas(self) -> None:
        """Deve normalizar 'LER OUVIR E CONTAR' para versão com vírgulas."""
        result = normalize_project_name("LER OUVIR E CONTAR")
        assert result == "LER, OUVIR E CONTAR"

    def test_returns_canonical_unchanged(self) -> None:
        """Deve retornar nome canônico sem modificações."""
        canonical = "LEIO, ESCREVO E CALCULO"
        result = normalize_project_name(canonical)
        assert result == canonical

    def test_returns_unknown_project_uppercased(self) -> None:
        """Deve retornar projeto desconhecido em uppercase."""
        result = normalize_project_name("projeto desconhecido")
        assert result == "PROJETO DESCONHECIDO"

    def test_handles_empty_string(self) -> None:
        """Deve retornar string vazia quando entrada é vazia."""
        result = normalize_project_name("")
        assert result == ""

    def test_handles_whitespace_only(self) -> None:
        """Deve retornar string vazia quando entrada é apenas espaços."""
        result = normalize_project_name("   ")
        assert result == ""


class TestIsKnownVariant:
    """Testes para função is_known_variant()."""

    def test_returns_true_for_leio_variant(self) -> None:
        """Deve retornar True para variante conhecida 'LEIO ESCREVO E CALCULO'."""
        assert is_known_variant("LEIO ESCREVO E CALCULO") is True

    def test_returns_true_for_gestao_variant_without_accents(self) -> None:
        """Deve retornar True para variante conhecida 'GESTAO ESCOLAR' (sem acentos)."""
        assert is_known_variant("GESTAO ESCOLAR") is True

    def test_returns_true_for_ideb10_legacy(self) -> None:
        """Deve retornar True para nome antigo 'IDEB10'."""
        assert is_known_variant("IDEB10") is True

    def test_returns_false_for_canonical_leio(self) -> None:
        """Deve retornar False para nome canônico 'LEIO, ESCREVO E CALCULO'."""
        assert is_known_variant("LEIO, ESCREVO E CALCULO") is False

    def test_returns_false_for_canonical_gestao(self) -> None:
        """Deve retornar False para nome canônico 'GESTÃO ESCOLAR'."""
        assert is_known_variant("GESTÃO ESCOLAR") is False

    def test_returns_false_for_unknown_project(self) -> None:
        """Deve retornar False para projeto desconhecido."""
        assert is_known_variant("PROJETO DESCONHECIDO") is False

    def test_case_insensitive_check(self) -> None:
        """Deve funcionar com case insensitive."""
        assert is_known_variant("leio escrevo e calculo") is True
        assert is_known_variant("LEIO ESCREVO E CALCULO") is True


class TestGetCanonicalName:
    """Testes para função get_canonical_name()."""

    def test_returns_canonical_for_leio_variant(self) -> None:
        """Deve retornar nome canônico para variante 'LEIO ESCREVO E CALCULO'."""
        result = get_canonical_name("LEIO ESCREVO E CALCULO")
        assert result == "LEIO, ESCREVO E CALCULO"

    def test_returns_canonical_for_gestao_variant_without_accents(self) -> None:
        """Deve retornar nome canônico para variante 'GESTAO ESCOLAR' (sem acentos)."""
        result = get_canonical_name("GESTAO ESCOLAR")
        assert result == "GESTÃO ESCOLAR"

    def test_returns_none_for_gestao_with_accents(self) -> None:
        """Deve retornar None para 'Gestão Escolar' (normaliza via .upper() automaticamente)."""
        result = get_canonical_name("Gestão Escolar")
        assert result is None  # Não é variant explícito, mas normalize_project_name() funciona

    def test_returns_canonical_for_ideb10(self) -> None:
        """Deve retornar nome canônico para 'IDEB10'."""
        result = get_canonical_name("IDEB10")
        assert result == "GESTÃO ESCOLAR"

    def test_returns_none_for_canonical_name(self) -> None:
        """Deve retornar None quando nome já é canônico."""
        result = get_canonical_name("LEIO, ESCREVO E CALCULO")
        assert result is None

    def test_returns_none_for_unknown_project(self) -> None:
        """Deve retornar None para projeto desconhecido."""
        result = get_canonical_name("PROJETO DESCONHECIDO")
        assert result is None

    def test_case_insensitive_lookup(self) -> None:
        """Deve funcionar com case insensitive."""
        result1 = get_canonical_name("leio escrevo e calculo")
        result2 = get_canonical_name("LEIO ESCREVO E CALCULO")
        assert result1 == result2 == "LEIO, ESCREVO E CALCULO"


class TestListAllVariants:
    """Testes para função list_all_variants()."""

    def test_returns_dict_with_all_canonical_names(self) -> None:
        """Deve retornar dicionário com todos os nomes canônicos."""
        result = list_all_variants()

        assert isinstance(result, dict)
        assert "LEIO, ESCREVO E CALCULO" in result
        assert "GESTÃO ESCOLAR" in result
        assert "LER, OUVIR E CONTAR" in result

    def test_returns_copy_not_reference(self) -> None:
        """Deve retornar cópia, não referência para dicionário interno."""
        result = list_all_variants()
        original_len = len(CANONICAL_PROJECT_NAMES)

        # Modificar resultado não deve afetar dicionário original
        result["FAKE_PROJECT"] = ["variant1"]

        assert len(CANONICAL_PROJECT_NAMES) == original_len
        assert "FAKE_PROJECT" not in CANONICAL_PROJECT_NAMES

    def test_each_canonical_has_variants_list(self) -> None:
        """Deve retornar lista de variantes para cada canônico."""
        result = list_all_variants()

        for canonical, variants in result.items():
            assert isinstance(variants, list)
            assert len(variants) > 0
            assert all(isinstance(v, str) for v in variants)

    def test_leio_has_expected_variants(self) -> None:
        """Deve incluir variantes esperadas para 'LEIO, ESCREVO E CALCULO'."""
        result = list_all_variants()
        leio_variants = result["LEIO, ESCREVO E CALCULO"]

        assert "LEIO ESCREVO E CALCULO" in leio_variants
        assert "LEIO,ESCREVO E CALCULO" in leio_variants

    def test_gestao_includes_ideb10_and_without_accents(self) -> None:
        """Deve incluir 'IDEB10' e variantes sem acentos nas variantes de 'GESTÃO ESCOLAR'."""
        result = list_all_variants()
        gestao_variants = result["GESTÃO ESCOLAR"]

        assert "IDEB10" in gestao_variants
        assert "GESTAO ESCOLAR" in gestao_variants  # Sem acentos
        assert "Gestao Escolar" in gestao_variants  # Mixed case sem acentos
        # "Gestão Escolar" (com acentos) não está na lista pois normaliza via .upper()


class TestNormalizerIntegration:
    """Testes de integração para combinações de funções."""

    def test_all_variants_normalize_to_canonical(self) -> None:
        """Todas as variantes devem normalizar para seus canônicos."""
        all_variants = list_all_variants()

        for canonical, variants in all_variants.items():
            for variant in variants:
                normalized = normalize_project_name(variant)
                assert normalized == canonical, (
                    f"Variant '{variant}' should normalize to '{canonical}', " f"got '{normalized}'"
                )

    def test_all_variants_are_known(self) -> None:
        """Todas as variantes devem ser reconhecidas por is_known_variant()."""
        all_variants = list_all_variants()

        for canonical, variants in all_variants.items():
            for variant in variants:
                assert is_known_variant(variant) is True, f"Variant '{variant}' should be recognized as known variant"

    def test_all_variants_return_canonical_via_get(self) -> None:
        """Todas as variantes devem retornar canônico via get_canonical_name()."""
        all_variants = list_all_variants()

        for canonical, variants in all_variants.items():
            for variant in variants:
                result = get_canonical_name(variant)
                assert result == canonical, (
                    f"Variant '{variant}' should return canonical '{canonical}', " f"got '{result}'"
                )

    def test_canonical_names_not_variants_of_themselves(self) -> None:
        """Nomes canônicos não devem ser variantes de si mesmos."""
        all_variants = list_all_variants()

        for canonical in all_variants.keys():
            assert is_known_variant(canonical) is False, f"Canonical name '{canonical}' should NOT be a variant"
            assert (
                get_canonical_name(canonical) is None
            ), f"Canonical name '{canonical}' should return None from get_canonical_name()"
