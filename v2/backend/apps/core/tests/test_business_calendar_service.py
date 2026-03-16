"""
Tests for BusinessCalendarService (issue #870).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from datetime import date

import pytest

from apps.core.models import FeriadoLocal
from apps.core.services.business_calendar_service import BusinessCalendarService


@pytest.mark.django_db
def test_is_business_day_false_for_weekend():
    assert BusinessCalendarService.is_business_day(date(2026, 3, 14)) is False  # Saturday
    assert BusinessCalendarService.is_business_day(date(2026, 3, 15)) is False  # Sunday


@pytest.mark.django_db
def test_is_business_day_false_for_national_holiday():
    # Dia da Consciencia Negra (nacional)
    assert BusinessCalendarService.is_business_day(date(2026, 11, 20)) is False


@pytest.mark.django_db
def test_holidays_include_ce_and_fortaleza():
    holidays = BusinessCalendarService.get_holidays(2026)
    assert date(2026, 3, 19) in holidays  # Sao Jose (CE)
    assert date(2026, 3, 25) in holidays  # Data Magna (CE)
    assert date(2026, 4, 13) in holidays  # Aniversario de Fortaleza


@pytest.mark.django_db
def test_add_business_days_skips_weekend_and_holiday():
    # 19/03 (feriado CE) e fim de semana devem ser ignorados.
    due = BusinessCalendarService.add_business_days(date(2026, 3, 18), 2)
    assert due == date(2026, 3, 23)


@pytest.mark.django_db
def test_custom_feriado_local_affects_due_date():
    FeriadoLocal.objects.create(
        data=date(2026, 3, 20),
        nome="Feriado de Teste",
        abrangencia="MUNICIPAL_FORTALEZA",
        ativo=True,
    )
    BusinessCalendarService.invalidate_cache()
    due = BusinessCalendarService.add_business_days(date(2026, 3, 18), 1)
    assert due == date(2026, 3, 23)


@pytest.mark.django_db
def test_business_days_between_future():
    # 11,12,13 => 3 dias uteis
    diff = BusinessCalendarService.business_days_between(date(2026, 3, 10), date(2026, 3, 13))
    assert diff == 3


@pytest.mark.django_db
def test_business_days_between_past():
    # 11,12,13 => -3 dias uteis (direcao inversa)
    diff = BusinessCalendarService.business_days_between(date(2026, 3, 13), date(2026, 3, 10))
    assert diff == -3


@pytest.mark.django_db
def test_carnaval_monday_is_holiday():
    # 2026 Easter = April 5, Carnaval Monday = Feb 16
    assert BusinessCalendarService.is_business_day(date(2026, 2, 16)) is False


@pytest.mark.django_db
def test_carnaval_tuesday_is_holiday():
    # 2026 Carnaval Tuesday = Feb 17
    assert BusinessCalendarService.is_business_day(date(2026, 2, 17)) is False


@pytest.mark.django_db
def test_corpus_christi_is_holiday():
    # 2026 Corpus Christi = Easter + 60 = June 4
    assert BusinessCalendarService.is_business_day(date(2026, 6, 4)) is False


@pytest.mark.django_db
def test_get_holidays_cache_avoids_repeated_queries(django_assert_num_queries):
    BusinessCalendarService.invalidate_cache()
    # First call hits DB
    with django_assert_num_queries(1):
        BusinessCalendarService.get_holidays(2026)
    # Second call uses cache — no DB queries
    with django_assert_num_queries(0):
        BusinessCalendarService.get_holidays(2026)
    BusinessCalendarService.invalidate_cache()
