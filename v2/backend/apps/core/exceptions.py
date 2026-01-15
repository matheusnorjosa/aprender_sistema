"""
AS v2 — Custom Exception Handler for standardized API error responses.

All API errors follow this format:
{
    "detail": "Human-readable error message",
    "code": "ERROR_CODE",
    "errors": {...}  // Optional, for field-level validation errors
}

Usage: Configure in settings.py:
    REST_FRAMEWORK = {
        'EXCEPTION_HANDLER': 'apps.core.exceptions.custom_exception_handler'
    }
"""

from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from django.http import Http404

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """
    Custom exception handler that standardizes error response format.

    All errors return:
    {
        "detail": str,  # Human-readable message
        "code": str,    # Machine-readable error code
        "errors": dict  # Optional field-level errors (validation only)
    }
    """
    # First, call DRF's default handler to get the standard response
    response = exception_handler(exc, context)

    # If DRF didn't handle it, handle common Django exceptions
    if response is None:
        if isinstance(exc, Http404):
            response = Response(
                {
                    "detail": "Recurso não encontrado.",
                    "code": "NOT_FOUND",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        elif isinstance(exc, PermissionDenied):
            response = Response(
                {
                    "detail": "Você não tem permissão para realizar esta ação.",
                    "code": "PERMISSION_DENIED",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        elif isinstance(exc, DjangoValidationError):
            response = Response(
                {
                    "detail": "Erro de validação.",
                    "code": "VALIDATION_ERROR",
                    "errors": exc.message_dict if hasattr(exc, "message_dict") else {"__all__": exc.messages},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        else:
            # Unknown exception - return generic 500
            return None

    # Standardize the response format
    if response is not None:
        response.data = _standardize_error_response(exc, response.data)

    return response


def _standardize_error_response(exc: Exception, data: dict[str, Any] | list[Any] | str) -> dict[str, Any]:
    """
    Convert various error formats to standard format.

    Handles:
    - {"detail": "..."} → standard format
    - {"non_field_errors": [...]} → standard format with errors
    - {"field": [...]} → standard format with errors
    - {"error": "..."} → standard format
    - {"message": "..."} → standard format
    - [...] → list of errors
    - "string" → detail message
    """
    # Get error code from exception
    code = _get_error_code(exc)

    # Handle string responses
    if isinstance(data, str):
        return {
            "detail": data,
            "code": code,
        }

    # Handle list responses (e.g., non_field_errors)
    if isinstance(data, list):
        return {
            "detail": "; ".join(str(e) for e in data),
            "code": code,
            "errors": {"__all__": data},
        }

    # Already a dict - standardize keys
    result: dict[str, Any] = {"code": code}

    # Extract detail message
    if "detail" in data:
        result["detail"] = data["detail"]
    elif "error" in data:
        result["detail"] = data["error"]
    elif "message" in data:
        result["detail"] = data["message"]
    elif "non_field_errors" in data:
        errors_list = data["non_field_errors"]
        result["detail"] = "; ".join(str(e) for e in errors_list) if isinstance(errors_list, list) else str(errors_list)
    else:
        # Build detail from field errors
        result["detail"] = "Erro de validação."

    # Extract field-level errors
    errors = {}
    for key, value in data.items():
        if key not in ("detail", "error", "message", "code"):
            errors[key] = value

    if errors:
        result["errors"] = errors

    return result


def _get_error_code(exc: Exception) -> str:
    """Get machine-readable error code from exception."""
    # DRF exceptions have default_code
    if isinstance(exc, APIException) and hasattr(exc, "default_code"):
        return str(exc.default_code).upper()

    # Map common exception types to codes
    exception_codes = {
        "NotAuthenticated": "NOT_AUTHENTICATED",
        "AuthenticationFailed": "AUTHENTICATION_FAILED",
        "PermissionDenied": "PERMISSION_DENIED",
        "NotFound": "NOT_FOUND",
        "MethodNotAllowed": "METHOD_NOT_ALLOWED",
        "NotAcceptable": "NOT_ACCEPTABLE",
        "UnsupportedMediaType": "UNSUPPORTED_MEDIA_TYPE",
        "Throttled": "THROTTLED",
        "ValidationError": "VALIDATION_ERROR",
        "ParseError": "PARSE_ERROR",
    }

    exc_name = type(exc).__name__
    return exception_codes.get(exc_name, "ERROR")
