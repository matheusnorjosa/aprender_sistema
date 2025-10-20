"""
dat_ingest services
"""

from .normalizers import (
    normalize_cpf,
    normalize_email,
    normalize_str,
    normalize_telefone,
    normalize_uf,
    parse_bool,
    titlecase,
)

__all__ = [
    "normalize_str",
    "normalize_email",
    "normalize_cpf",
    "normalize_telefone",
    "titlecase",
    "normalize_uf",
    "parse_bool",
]
