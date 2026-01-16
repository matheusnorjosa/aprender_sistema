"""
AS v2 — API Deprecation Utilities (#410)

Provides decorators and utilities for marking endpoints as deprecated.
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false

from __future__ import annotations

import warnings
from functools import wraps
from typing import Any, Callable, TypeVar

from rest_framework.request import Request
from rest_framework.response import Response

F = TypeVar("F", bound=Callable[..., Any])


def deprecated_endpoint(message: str, removal_version: str = "v2") -> Callable[[F], F]:
    """
    Decorator to mark API endpoints as deprecated.

    Adds deprecation headers to the response:
    - X-Deprecated: true
    - X-Deprecated-Message: <message>
    - X-Removal-Version: <version>

    Usage:
        @api_view(["GET"])
        @deprecated_endpoint("Use /api/v1/new-endpoint/ instead", removal_version="v2")
        def old_endpoint(request):
            ...

    Args:
        message: Human-readable deprecation message
        removal_version: API version when endpoint will be removed

    Returns:
        Decorated function that adds deprecation headers
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(request: Request, *args: Any, **kwargs: Any) -> Response:
            response = func(request, *args, **kwargs)
            response["X-Deprecated"] = "true"
            response["X-Deprecated-Message"] = message
            response["X-Removal-Version"] = removal_version
            return response
        return wrapper  # type: ignore[return-value]
    return decorator


def deprecated_view_class(message: str, removal_version: str = "v2") -> Callable[[type], type]:
    """
    Class decorator to mark API view classes as deprecated.

    Wraps the dispatch method to add deprecation headers to all responses.

    Usage:
        @deprecated_view_class("Use NewView instead", removal_version="v2")
        class OldView(APIView):
            ...

    Args:
        message: Human-readable deprecation message
        removal_version: API version when endpoint will be removed

    Returns:
        Decorated class that adds deprecation headers to all responses
    """
    def decorator(cls: type) -> type:
        original_dispatch = cls.dispatch  # type: ignore[attr-defined]

        @wraps(original_dispatch)
        def new_dispatch(self: Any, request: Request, *args: Any, **kwargs: Any) -> Response:
            response = original_dispatch(self, request, *args, **kwargs)
            response["X-Deprecated"] = "true"
            response["X-Deprecated-Message"] = message
            response["X-Removal-Version"] = removal_version
            return response

        cls.dispatch = new_dispatch  # type: ignore[attr-defined]
        return cls
    return decorator
