"""
Testes para filtro de indicadores (não-pessoas).

CONTEXTO (PR20 Task 2):
Filtrar tokens como "3º ANO LING" para não criar Participation com usuario_id NULL.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from django.test import TestCase

from apps.dat_ingest.services.indicator_filter import (
    filter_indicators_from_list,
    is_indicator_token,
    should_create_participation,
)


class TestIndicatorFilter(TestCase):
    """Testes para identificação de indicadores vs nomes de pessoas"""

    def test_ano_disciplina_patterns_are_indicators(self):
        """Padrão 'Xº ANO DISCIPLINA' deve ser identificado como indicador"""
        self.assertTrue(is_indicator_token("3º ANO LING"))
        self.assertTrue(is_indicator_token("5º ANO MAT"))
        self.assertTrue(is_indicator_token("1º ANO CIÊNCIAS"))
        self.assertTrue(is_indicator_token("10º ANO PORT"))
        self.assertTrue(is_indicator_token("4ª ANO HISTÓRIA"))

    def test_ano_simple_is_indicator(self):
        """Padrão 'Xº ANO' sem disciplina também é indicador"""
        self.assertTrue(is_indicator_token("3º ANO"))
        self.assertTrue(is_indicator_token("5º ANO"))
        self.assertTrue(is_indicator_token("1ª SÉRIE"))

    def test_generic_groups_are_indicators(self):
        """Grupos genéricos (plural) são indicadores"""
        self.assertTrue(is_indicator_token("Coordenadores"))
        self.assertTrue(is_indicator_token("coordenadores"))
        self.assertTrue(is_indicator_token("COORDENADORES"))
        self.assertTrue(is_indicator_token("Formadores"))
        self.assertTrue(is_indicator_token("Professores"))
        self.assertTrue(is_indicator_token("Gestores"))

    def test_real_names_are_not_indicators(self):
        """Nomes de pessoas reais não devem ser identificados como indicadores"""
        self.assertFalse(is_indicator_token("João Silva"))
        self.assertFalse(is_indicator_token("Maria Santos"))
        self.assertFalse(is_indicator_token("Ana Paula"))
        self.assertFalse(is_indicator_token("José"))
        self.assertFalse(is_indicator_token("Pedro Henrique"))
        self.assertFalse(is_indicator_token("Amanda Arruda"))

    def test_none_and_empty_are_not_indicators(self):
        """None e strings vazias retornam False (não criar Participation de qualquer forma)"""
        self.assertFalse(is_indicator_token(None))
        self.assertFalse(is_indicator_token(""))
        self.assertFalse(is_indicator_token("   "))

    def test_case_insensitive_matching(self):
        """Matching deve ser case-insensitive"""
        self.assertTrue(is_indicator_token("3º ano ling"))
        self.assertTrue(is_indicator_token("3º ANO LING"))
        self.assertTrue(is_indicator_token("coordenadores"))
        self.assertTrue(is_indicator_token("COORDENADORES"))

    def test_filter_indicators_from_list(self):
        """Filtrar lista mista de nomes + indicadores"""
        input_list = [
            "João Silva",
            "3º ANO LING",
            "Maria Santos",
            "Coordenadores",
            "Ana Paula",
            "5º ANO MAT",
        ]
        expected = ["João Silva", "Maria Santos", "Ana Paula"]
        result = filter_indicators_from_list(input_list)
        self.assertEqual(result, expected)

    def test_should_create_participation_for_real_names(self):
        """should_create_participation = True para nomes reais"""
        self.assertTrue(should_create_participation("João Silva"))
        self.assertTrue(should_create_participation("Maria Santos"))

    def test_should_not_create_participation_for_indicators(self):
        """should_create_participation = False para indicadores"""
        self.assertFalse(should_create_participation("3º ANO LING"))
        self.assertFalse(should_create_participation("Coordenadores"))
        self.assertFalse(should_create_participation(None))
        self.assertFalse(should_create_participation(""))

    def test_edge_cases_with_special_characters(self):
        """Testar variações de caracteres especiais (º, ª, °)"""
        self.assertTrue(is_indicator_token("3º ANO LING"))  # º
        self.assertTrue(is_indicator_token("3ª ANO LING"))  # ª
        self.assertTrue(is_indicator_token("3° ANO LING"))  # °
        self.assertTrue(is_indicator_token("3o ANO LING"))  # o minúsculo

    def test_turma_codes_are_indicators(self):
        """Códigos de turma (T301, A5B) são indicadores"""
        self.assertTrue(is_indicator_token("T301"))
        self.assertTrue(is_indicator_token("A5B"))
        self.assertTrue(is_indicator_token("TURMA A"))

    def test_audit_report_real_examples(self):
        """
        Testes com exemplos reais do relatorio_pessoas_pendentes_match.csv

        INDICADORES (devem retornar True):
        - 3º ANO LING
        - 4º ANO MAT
        - Coordenadores

        PESSOAS REAIS (devem retornar False):
        - Alisson Mendonça
        - Amanda Arruda
        - Anna Lúcia
        """
        # Indicadores do relatório
        self.assertTrue(is_indicator_token("3º ANO LING"))
        self.assertTrue(is_indicator_token("3º ANO MAT"))
        self.assertTrue(is_indicator_token("4º ANO LING"))
        self.assertTrue(is_indicator_token("4º ANO MAT"))
        self.assertTrue(is_indicator_token("Coordenadores"))

        # Pessoas reais do relatório
        self.assertFalse(is_indicator_token("Alisson Mendonça"))
        self.assertFalse(is_indicator_token("Amanda Arruda"))
        self.assertFalse(is_indicator_token("Anna Lúcia"))
        self.assertFalse(is_indicator_token("Ana Kariny"))
        self.assertFalse(is_indicator_token("Bruno Teles"))
