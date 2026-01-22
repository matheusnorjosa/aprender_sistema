"""
Testes para módulo constants.

Valida que constantes ETL estão definidas e têm valores esperados.

Issue #54: Extrair magic numbers para constantes.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations
from decimal import Decimal

from apps.dat_ingest import constants


def test_constants_are_defined():
    """Todas as constantes ETL estão definidas."""
    assert hasattr(constants, 'NAME_MATCH_JACCARD_MIN')
    assert hasattr(constants, 'NAME_MATCH_SCORE_SUBSET')
    assert hasattr(constants, 'NAME_MATCH_SCORE_FIRST_LAST')
    assert hasattr(constants, 'TOP_UNKNOWN_USERS_LIMIT')
    assert hasattr(constants, 'AUDIT_MIN_FREQUENCY')
    assert hasattr(constants, 'AUDIT_MULTI_SECTOR_THRESHOLD')


def test_matching_constants_are_decimal():
    """Constantes de matching são Decimal para precisão."""
    assert isinstance(constants.NAME_MATCH_JACCARD_MIN, Decimal)
    assert isinstance(constants.NAME_MATCH_SCORE_SUBSET, Decimal)
    assert isinstance(constants.NAME_MATCH_SCORE_FIRST_LAST, Decimal)


def test_matching_constants_in_valid_range():
    """Scores de matching estão no intervalo [0, 1]."""
    assert 0 <= constants.NAME_MATCH_JACCARD_MIN <= 1
    assert 0 <= constants.NAME_MATCH_SCORE_SUBSET <= 1
    assert 0 <= constants.NAME_MATCH_SCORE_FIRST_LAST <= 1


def test_top_limit_is_positive_integer():
    """TOP_UNKNOWN_USERS_LIMIT é inteiro positivo."""
    assert isinstance(constants.TOP_UNKNOWN_USERS_LIMIT, int)
    assert constants.TOP_UNKNOWN_USERS_LIMIT > 0


def test_audit_thresholds_are_positive():
    """Thresholds de auditoria são inteiros positivos."""
    assert isinstance(constants.AUDIT_MIN_FREQUENCY, int)
    assert isinstance(constants.AUDIT_MULTI_SECTOR_THRESHOLD, int)
    assert constants.AUDIT_MIN_FREQUENCY > 0
    assert constants.AUDIT_MULTI_SECTOR_THRESHOLD > 0


def test_constants_values():
    """Valores esperados das constantes (baseline)."""
    # Matching scores (valores atuais do código)
    assert constants.NAME_MATCH_JACCARD_MIN == Decimal('0.60')
    assert constants.NAME_MATCH_SCORE_SUBSET == Decimal('0.90')
    assert constants.NAME_MATCH_SCORE_FIRST_LAST == Decimal('0.85')

    # Limits
    assert constants.TOP_UNKNOWN_USERS_LIMIT == 20

    # Audit thresholds
    assert constants.AUDIT_MIN_FREQUENCY == 5
    assert constants.AUDIT_MULTI_SECTOR_THRESHOLD == 2
