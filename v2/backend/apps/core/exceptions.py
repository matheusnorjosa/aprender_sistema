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
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportUnknownArgumentType=false, reportArgumentType=false

from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from django.http import Http404

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler


# =============================================================================
# Custom Exception Classes (#407 Error Handling)
# =============================================================================


class APIError(APIException):
    """
    Base exception for custom API errors.

    Usage:
        raise APIError(code="CUSTOM_ERROR", message="Something went wrong")
    """

    status_code = 400
    default_code = "API_ERROR"
    default_detail = "Ocorreu um erro na API."

    def __init__(
        self,
        code: str | None = None,
        message: str | None = None,
        details: dict[str, Any] | None = None,
        status_code: int | None = None,
    ) -> None:
        self.code = code or self.default_code
        self.message = message or self.default_detail
        self.details = details or {}
        if status_code is not None:
            self.status_code = status_code
        super().__init__(detail=self.message, code=self.code)


class ValidationAPIError(APIError):
    """Validation error with field-level details."""

    status_code = 400
    default_code = "VALIDATION_ERROR"
    default_detail = "Erro de validação nos dados enviados."

    def __init__(
        self,
        message: str | None = None,
        field: str | None = None,
        details: dict[str, Any] | None = None,
        code: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        extra_details = {"field": field} if field else {}
        if details:
            extra_details.update(details)
        if extra:
            extra_details.update(extra)
        super().__init__(
            code=code or self.default_code,
            message=message or self.default_detail,
            details=extra_details,
        )


class NotFoundError(APIError):
    """Resource not found error."""

    status_code = 404
    default_code = "NOT_FOUND"
    default_detail = "Recurso não encontrado."

    def __init__(
        self,
        resource: str | None = None,
        identifier: str | int | None = None,
    ) -> None:
        message = f"{resource} não encontrado." if resource else self.default_detail
        details: dict[str, Any] = {}
        if resource:
            details["resource"] = resource
        if identifier is not None:
            details["identifier"] = str(identifier)
        super().__init__(code=self.default_code, message=message, details=details)


class ServiceUnavailableError(APIError):
    """External service unavailable error (503)."""

    status_code = 503
    default_code = "SERVICE_UNAVAILABLE"
    default_detail = "Serviço externo indisponível."

    def __init__(
        self,
        service: str | None = None,
        details: str | None = None,
    ) -> None:
        message = f"Serviço {service} indisponível." if service else self.default_detail
        extra_details: dict[str, Any] = {}
        if service:
            extra_details["service"] = service
        if details:
            extra_details["error"] = details
        super().__init__(
            code=self.default_code,
            message=message,
            details=extra_details,
            status_code=503,
        )


class ConflictError(APIError):
    """Conflict error (409) for business rule violations."""

    status_code = 409
    default_code = "CONFLICT"
    default_detail = "Conflito com o estado atual do recurso."

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code=self.default_code,
            message=message or self.default_detail,
            details=details,
            status_code=409,
        )


# =============================================================================
# Custom Exception Handler
# =============================================================================


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
    # Handle our custom APIError exceptions first
    if isinstance(exc, APIError):
        data: dict[str, Any] = {
            "detail": exc.message,
            "code": exc.code,
        }
        if exc.details:
            data["errors"] = exc.details
        return Response(data, status=exc.status_code)

    # Call DRF's default handler to get the standard response
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
