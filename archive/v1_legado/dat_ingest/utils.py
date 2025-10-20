"""
Utilitários para Ingestão de CSVs ETL

App: dat_ingest
Stack: Python 3.13 | Django 5.2 | PostgreSQL 15

Funções puras para parsing de dados e geração de hashes idempotentes.
"""

import hashlib
import unicodedata
from datetime import date, time
from typing import Optional


def normalize_string(s: str) -> str:
    """
    Normaliza string: NFKD → ASCII (strip accents) → lower → strip.

    Args:
        s: String para normalizar

    Returns:
        String normalizada (minúscula, sem acentos, sem espaços nas pontas)

    Examples:
        >>> normalize_string("José Maria")
        'jose maria'
        >>> normalize_string("  FORTALEZA-CE  ")
        'fortaleza-ce'
    """
    if not s:
        return ""
    nfkd = unicodedata.normalize("NFKD", s)
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
    return ascii_str.lower().strip()


def sha1_join(*parts: str) -> str:
    """
    Gera SHA1 hash a partir de partes concatenadas com "|".

    Cada parte é normalizada (normalize_string) antes de concatenar.
    Útil para gerar chaves únicas idempotentes.

    Args:
        *parts: Partes variáveis para concatenar

    Returns:
        SHA1 hash hexadecimal (40 caracteres)

    Examples:
        >>> sha1_join("Fortaleza", "2025-01-15", "08:00")
        'a1b2c3...' (40 chars)
        >>> sha1_join("  José  ", "Maria  ") == sha1_join("jose", "maria")
        True
    """
    normalized_parts = [normalize_string(str(p)) for p in parts if p]
    joined = "|".join(normalized_parts)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()


def parse_date(value: str) -> Optional[date]:
    """
    Parseia data no formato YYYY-MM-DD para objeto date.

    Args:
        value: String no formato "YYYY-MM-DD" ou vazio

    Returns:
        Objeto date ou None se vazio/inválido

    Examples:
        >>> parse_date("2025-01-15")
        date(2025, 1, 15)
        >>> parse_date("")
        None
        >>> parse_date("invalid")
        None
    """
    if not value or not value.strip():
        return None

    value = value.strip()

    try:
        # Formato esperado: YYYY-MM-DD
        parts = value.split("-")
        if len(parts) != 3:
            return None

        year = int(parts[0])
        month = int(parts[1])
        day = int(parts[2])

        return date(year, month, day)
    except (ValueError, IndexError):
        return None


def parse_time(value: str) -> Optional[time]:
    """
    Parseia hora no formato HH:MM[:SS] para objeto time.

    Args:
        value: String no formato "HH:MM" ou "HH:MM:SS" ou vazio

    Returns:
        Objeto time ou None se vazio/inválido

    Examples:
        >>> parse_time("08:30")
        time(8, 30, 0)
        >>> parse_time("14:45:30")
        time(14, 45, 30)
        >>> parse_time("")
        None
        >>> parse_time("invalid")
        None
    """
    if not value or not value.strip():
        return None

    value = value.strip()

    try:
        # Formato esperado: HH:MM ou HH:MM:SS
        parts = value.split(":")
        if len(parts) < 2:
            return None

        hour = int(parts[0])
        minute = int(parts[1])
        second = int(parts[2]) if len(parts) >= 3 else 0

        return time(hour, minute, second)
    except (ValueError, IndexError):
        return None


def safe_int(value: str, default: int = 0) -> int:
    """
    Converte string para int, retorna default se falhar.

    Args:
        value: String para converter
        default: Valor padrão se conversão falhar

    Returns:
        Inteiro convertido ou default

    Examples:
        >>> safe_int("123")
        123
        >>> safe_int("")
        0
        >>> safe_int("invalid", -1)
        -1
    """
    if not value or not value.strip():
        return default

    try:
        return int(value.strip())
    except (ValueError, TypeError):
        return default


def safe_bool(value: str) -> bool:
    """
    Converte string para boolean.

    Considera "1", "true", "yes", "sim" como True (case-insensitive).
    Tudo mais é False.

    Args:
        value: String para converter

    Returns:
        Boolean

    Examples:
        >>> safe_bool("1")
        True
        >>> safe_bool("TRUE")
        True
        >>> safe_bool("0")
        False
        >>> safe_bool("")
        False
    """
    if not value:
        return False

    value_lower = value.strip().lower()
    return value_lower in ("1", "true", "yes", "sim")
