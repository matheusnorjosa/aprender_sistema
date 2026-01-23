"""
Re-export de funções de resolução de FKs para compatibilidade retroativa.

DEPRECATED: Este módulo foi movido para apps.core.services.resolvers
Use: from apps.core.services.resolvers import resolve_municipio, ...

Este arquivo mantido apenas para compatibilidade com imports existentes.
Será removido em versão futura.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportPrivateUsage=false

# Re-export all from core.services.resolvers for backward compatibility

from __future__ import annotations

from apps.core.services.resolvers import (
    _nfkd,
    _split_city_uf,
    normalize_projeto_name,
    resolve_municipio,
    resolve_projeto,
    resolve_tipo_evento,
    resolve_user_by_email,
    resolve_user_by_name,
)

__all__ = [
    "resolve_user_by_email",
    "resolve_user_by_name",
    "resolve_municipio",
    "resolve_projeto",
    "resolve_tipo_evento",
    "normalize_projeto_name",
    "_nfkd",
    "_split_city_uf",
]
