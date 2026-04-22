"""Dev-only middlewares. Registered in settings.MIDDLEWARE only when
INCLUDE_DEV_TOOLS=true AND the specific feature flag is enabled.
"""
from __future__ import annotations

from apps.dev_tools.middleware.freeze_time import FreezeTimeMiddleware, is_time_frozen

__all__ = ["FreezeTimeMiddleware", "is_time_frozen"]
