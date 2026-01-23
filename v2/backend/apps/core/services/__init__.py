"""
Core Services — AS v2

Serviços de lógica de negócio que substituem as 82K fórmulas Excel:
- ConflictChecker: Verificação de conflitos (RD-01 a RD-07)
- DisponibilidadeService: Mapa mensal (códigos D/P/T/E/M/X)
- ApprovalWorkflow: Fluxo de aprovações
- normalize: Funções de normalização de texto/datas/horas
- resolvers: Funções para resolver FKs por nome/email
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false

from __future__ import annotations

# Normalize functions (moved from dat_ingest for decoupling)
from .normalize import (
    hash_event_v2,
    norm_text,
    normalize_date_field,
    normalize_email,
    normalize_project_alias,
    normalize_sector,
    normalize_time_field,
    parse_date_iso,
    parse_time_iso,
    split_municipios_super,
)

# Resolver functions (moved from dat_ingest for decoupling)
from .resolvers import (
    normalize_projeto_name,
    resolve_municipio,
    resolve_projeto,
    resolve_tipo_evento,
    resolve_user_by_email,
    resolve_user_by_name,
)

__all__ = [
    # Normalize
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
    # Resolvers
    "resolve_user_by_email",
    "resolve_user_by_name",
    "resolve_municipio",
    "resolve_projeto",
    "resolve_tipo_evento",
    "normalize_projeto_name",
]
