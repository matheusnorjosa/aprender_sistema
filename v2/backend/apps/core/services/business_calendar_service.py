"""
Calendar service for business day calculations (issue #870).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache


class BusinessCalendarService:
    """
    Handles business-day arithmetic for BR/CE/Fortaleza scope.
    """

    @staticmethod
    def easter_sunday(year: int) -> date:
        """
        Computes Easter Sunday (Gregorian algorithm).
        """
        a = year % 19
        b = year // 100
        c = year % 100
        d = b // 4
        e = b % 4
        f = (b + 8) // 25
        g = (b - f + 1) // 3
        h = (19 * a + b - d - g + 15) % 30
        i = c // 4
        k = c % 4
        ell = (32 + 2 * e + 2 * i - h - k) % 7
        m = (a + 11 * h + 22 * ell) // 451
        month = (h + ell - 7 * m + 114) // 31
        day = ((h + ell - 7 * m + 114) % 31) + 1
        return date(year, month, day)

    @classmethod
    @lru_cache(maxsize=64)
    def _base_holidays_for_year(cls, year: int) -> frozenset[date]:
        easter = cls.easter_sunday(year)
        good_friday = easter - timedelta(days=2)

        # Feriados nacionais (Brasil)
        national = {
            date(year, 1, 1),  # Confraternizacao Universal
            good_friday,  # Paixao de Cristo
            date(year, 4, 21),  # Tiradentes
            date(year, 5, 1),  # Dia do Trabalho
            date(year, 9, 7),  # Independencia do Brasil
            date(year, 10, 12),  # Nossa Senhora Aparecida
            date(year, 11, 2),  # Finados
            date(year, 11, 15),  # Proclamacao da Republica
            date(year, 11, 20),  # Dia da Consciencia Negra (nacional)
            date(year, 12, 25),  # Natal
        }

        # Feriados estaduais (Ceara)
        ceara = {
            date(year, 3, 19),  # Sao Jose
            date(year, 3, 25),  # Data Magna do Ceara
        }

        # Feriados municipais (Fortaleza)
        fortaleza = {
            date(year, 4, 13),  # Aniversario de Fortaleza
            date(year, 8, 15),  # Nossa Senhora da Assuncao
            date(year, 12, 8),  # Nossa Senhora da Conceicao
        }

        return frozenset(national | ceara | fortaleza)

    @classmethod
    def get_holidays(cls, year: int, *, include_db: bool = True) -> set[date]:
        holidays: set[date] = set(cls._base_holidays_for_year(year))
        if not include_db:
            return holidays

        from apps.core.models import FeriadoLocal

        custom_dates = FeriadoLocal.objects.filter(ativo=True, data__year=year).values_list("data", flat=True)
        holidays.update(custom_dates)
        return holidays

    @classmethod
    def is_business_day(cls, day: date, *, include_db: bool = True) -> bool:
        if day.weekday() >= 5:
            return False
        return day not in cls.get_holidays(day.year, include_db=include_db)

    @classmethod
    def add_business_days(cls, anchor: date, days: int, *, include_db: bool = True) -> date:
        if days < 0:
            raise ValueError("days must be >= 0")
        if days == 0:
            return anchor

        current = anchor
        counted = 0
        while counted < days:
            current += timedelta(days=1)
            if cls.is_business_day(current, include_db=include_db):
                counted += 1
        return current
