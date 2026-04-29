"""
Cache helpers for static options endpoints.
"""

from __future__ import annotations

from django.core.cache import cache

MUNICIPIOS_OPTIONS_CACHE_KEY = "static_endpoint:municipios_options"


def invalidate_municipios_options_cache() -> None:
    """Clear cached municipio options used by dropdowns/selects."""
    cache.delete(MUNICIPIOS_OPTIONS_CACHE_KEY)
