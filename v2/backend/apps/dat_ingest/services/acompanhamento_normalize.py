"""
Re-export de funções de normalização para compatibilidade retroativa.

DEPRECATED: Este módulo foi movido para apps.core.services.normalize
Use: from apps.core.services.normalize import norm_text, ...

Este arquivo mantido apenas para compatibilidade com imports existentes.
Será removido em versão futura.
"""

# Re-export all from core.services.normalize for backward compatibility
from apps.core.services.normalize import (
    norm_text,
    normalize_sector,
    normalize_project_alias,
    split_municipios_super,
    parse_date_iso,
    parse_time_iso,
    normalize_email,
    normalize_date_field,
    normalize_time_field,
    hash_event_v2,
)

__all__ = [
    "norm_text",
    "normalize_sector",
    "normalize_project_alias",
    "split_municipios_super",
    "parse_date_iso",
    "parse_time_iso",
    "normalize_email",
    "normalize_date_field",
    "normalize_time_field",
    "hash_event_v2",
]
