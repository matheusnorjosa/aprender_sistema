"""
AS v2 — OpenAPI Schema Definitions (#412)

Provides standardized response schemas and examples for API documentation.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false

from __future__ import annotations

from drf_spectacular.utils import OpenApiExample, OpenApiResponse

# ============================================================================
# ERROR RESPONSE SCHEMAS
# ============================================================================

ERROR_400_RESPONSE = OpenApiResponse(
    description="Erro de validação",
    examples=[
        OpenApiExample(
            "Validation Error",
            value={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Erro de validação nos dados enviados",
                    "details": {"fields": {"campo": ["erro específico"]}},
                    "request_id": "550e8400-e29b-41d4-a716-446655440000",
                }
            },
        )
    ],
)

ERROR_401_RESPONSE = OpenApiResponse(
    description="Autenticação necessária",
    examples=[
        OpenApiExample(
            "Unauthorized",
            value={
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Autenticação necessária",
                    "details": {},
                    "request_id": "550e8400-e29b-41d4-a716-446655440000",
                }
            },
        )
    ],
)

ERROR_403_RESPONSE = OpenApiResponse(
    description="Permissão negada",
    examples=[
        OpenApiExample(
            "Forbidden",
            value={
                "error": {
                    "code": "FORBIDDEN",
                    "message": "Você não tem permissão para acessar este recurso",
                    "details": {},
                    "request_id": "550e8400-e29b-41d4-a716-446655440000",
                }
            },
        )
    ],
)

ERROR_404_RESPONSE = OpenApiResponse(
    description="Recurso não encontrado",
    examples=[
        OpenApiExample(
            "Not Found",
            value={
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Recurso não encontrado",
                    "details": {},
                    "request_id": "550e8400-e29b-41d4-a716-446655440000",
                }
            },
        )
    ],
)

ERROR_409_RESPONSE = OpenApiResponse(
    description="Conflito de dados",
    examples=[
        OpenApiExample(
            "Conflict",
            value={
                "error": {
                    "code": "CONFLICT",
                    "message": "Conflito de disponibilidade detectado",
                    "details": {"conflicts": []},
                    "request_id": "550e8400-e29b-41d4-a716-446655440000",
                }
            },
        )
    ],
)

ERROR_429_RESPONSE = OpenApiResponse(
    description="Limite de requisições excedido",
    examples=[
        OpenApiExample(
            "Rate Limited",
            value={
                "error": {
                    "code": "RATE_LIMITED",
                    "message": "Limite de requisições excedido. Tente novamente em 60 segundos.",
                    "details": {"retry_after": 60},
                    "request_id": "550e8400-e29b-41d4-a716-446655440000",
                }
            },
        )
    ],
)

ERROR_503_RESPONSE = OpenApiResponse(
    description="Serviço indisponível",
    examples=[
        OpenApiExample(
            "Service Unavailable",
            value={
                "error": {
                    "code": "SERVICE_UNAVAILABLE",
                    "message": "Serviço Google Calendar indisponível",
                    "details": {"service": "Google Calendar", "error": "Connection timeout"},
                    "request_id": "550e8400-e29b-41d4-a716-446655440000",
                }
            },
        )
    ],
)

# Common error responses for reuse
COMMON_ERROR_RESPONSES = {
    400: ERROR_400_RESPONSE,
    401: ERROR_401_RESPONSE,
    403: ERROR_403_RESPONSE,
    404: ERROR_404_RESPONSE,
    429: ERROR_429_RESPONSE,
}

# ============================================================================
# SUCCESS RESPONSE EXAMPLES
# ============================================================================

AVAILABILITY_OK_EXAMPLE = OpenApiExample(
    "Disponível", value={"data": {"available": True, "conflicts": []}, "meta": {"timestamp": "2026-01-16T10:30:00Z"}}
)

AVAILABILITY_CONFLICT_EXAMPLE = OpenApiExample(
    "Com conflitos",
    value={
        "data": {
            "available": False,
            "conflicts": [
                {
                    "type": "overlap",
                    "formador_id": 123,
                    "formador_nome": "João Silva",
                    "start": "2026-01-20T09:00:00Z",
                    "end": "2026-01-20T12:00:00Z",
                    "reason": "Evento já agendado",
                }
            ],
        },
        "meta": {"timestamp": "2026-01-16T10:30:00Z"},
    },
)

PAGINATED_LIST_EXAMPLE = OpenApiExample(
    "Lista paginada",
    value={
        "count": 150,
        "next": "https://api.exemplo.com/api/v1/solicitacoes/?page=2",
        "previous": None,
        "results": [
            {
                "id": 1,
                "status": "aprovado",
                "usuario": {"id": 1, "nome": "Maria Silva"},
                "inicio": "2026-01-20T09:00:00Z",
                "fim": "2026-01-20T12:00:00Z",
            }
        ],
    },
)

REPORTS_COUNTS_EXAMPLE = OpenApiExample(
    "Contagens por status",
    value={
        "data": {"counts": {"pendente": 10, "aprovado": 50, "reprovado": 5, "publicado": 0}, "total": 65},
        "meta": {"timestamp": "2026-01-16T10:30:00Z", "range": {"start": "2025-12-17", "end": "2026-01-16"}},
    },
)

# ============================================================================
# SOLICITACAO EXAMPLES (Issue #415)
# ============================================================================

SOLICITACAO_CREATE_PRESENCIAL_EXAMPLE = OpenApiExample(
    "Evento Presencial",
    summary="Criar evento presencial em Fortaleza",
    value={
        "titulo": "Formacao Fundamental I",
        "inicio": "2026-01-20T09:00:00-03:00",
        "fim": "2026-01-20T12:00:00-03:00",
        "municipio": 1,
        "projeto": 1,
        "tipo_evento": 1,
        "is_online": False,
        "observacoes": "Sala 101",
    },
    request_only=True,
)

SOLICITACAO_CREATE_ONLINE_EXAMPLE = OpenApiExample(
    "Evento Online",
    summary="Criar evento online com Google Meet",
    value={
        "titulo": "Formacao Online - Fluir",
        "inicio": "2026-01-20T14:00:00-03:00",
        "fim": "2026-01-20T16:00:00-03:00",
        "projeto": 2,
        "tipo_evento": 1,
        "is_online": True,
        "observacoes": "Link Google Meet sera gerado automaticamente",
    },
    request_only=True,
)

SOLICITACAO_CREATED_EXAMPLE = OpenApiExample(
    "Solicitacao Criada",
    summary="Resposta de solicitacao criada (PA-01: status pendente)",
    value={
        "id": 123,
        "titulo": "Formacao Fundamental I",
        "status": "pendente",
        "gcal_status": "NONE",
        "inicio": "2026-01-20T09:00:00-03:00",
        "fim": "2026-01-20T12:00:00-03:00",
        "is_online": False,
        "usuario": {"id": 1, "nome": "Maria Silva"},
        "municipio": {"id": 1, "nome": "Fortaleza"},
        "projeto": {"id": 1, "nome": "Vidas"},
        "tipo_evento": {"id": 1, "nome": "Formacao"},
        "created_at": "2026-01-13T10:00:00-03:00",
    },
    response_only=True,
    status_codes=["201"],
)

SOLICITACAO_APPROVED_EXAMPLE = OpenApiExample(
    "Solicitacao Aprovada",
    summary="Resposta de aprovacao (PA-02)",
    value={"detail": "Solicitacao aprovada com sucesso", "status": "aprovado"},
    response_only=True,
    status_codes=["200"],
)

SOLICITACAO_REJECTED_EXAMPLE = OpenApiExample(
    "Solicitacao Reprovada",
    summary="Resposta de reprovacao com motivo",
    value={
        "detail": "Solicitacao reprovada",
        "status": "reprovado",
        "motivo_reprovacao": "Data indisponivel para o formador",
    },
    response_only=True,
    status_codes=["200"],
)

SOLICITACAO_BATCH_APPROVE_REQUEST = OpenApiExample(
    "Aprovar em Lote",
    summary="Aprovar multiplas solicitacoes",
    value={"ids": [1, 2, 3, 4, 5]},
    request_only=True,
)

SOLICITACAO_BATCH_APPROVE_RESPONSE = OpenApiExample(
    "Resultado do Lote",
    summary="Resposta de aprovacao em lote",
    value={
        "detail": "3 solicitacoes aprovadas",
        "approved": 3,
        "failed": 2,
        "errors": [{"id": 4, "error": "Solicitacao ja aprovada"}, {"id": 5, "error": "Conflito de disponibilidade"}],
    },
    response_only=True,
    status_codes=["200"],
)
