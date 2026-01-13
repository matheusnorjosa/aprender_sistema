# Plano: API Best Practices 10/10

**Epic**: #405
**Status**: 🔄 Em Andamento
**Criado**: 2026-01-13
**Baseado em**: Análise real do código (não hipotética)

---

## Objetivo

Elevar todas as categorias de API para score 10/10:

| Categoria | Atual | Meta | Issue |
|-----------|-------|------|-------|
| Query Optimization | 7/10 | 10/10 | #406 |
| Error Handling | 4/10 | 10/10 | #407 |
| Pagination | 7/10 | 10/10 | #408 |
| Rate Limiting | 6/10 | 10/10 | #409 |
| API Versioning | 2/10 | 10/10 | #410 |
| Response Consistency | 5/10 | 10/10 | #411 |
| OpenAPI Documentation | 3/10 | 10/10 | #412 |

---

## Issue 1: Query Optimization (N+1 Fixes)

### Problema Identificado

**Arquivo**: `apps/core/views/availability.py:35`
```python
# ATUAL - SEM otimização
queryset = AvailabilityBlock.objects.all()
```

**Arquivo**: `apps/core/views/solicitacao.py:253-264`
```python
# ATUAL - N+1 em loop
for formador_id in to_add:
    usuario = Usuario.objects.get(id=formador_id)  # 1 query por formador
```

### Solução

**Fix 1: AvailabilityBlockViewSet**
```python
# apps/core/views/availability.py
class AvailabilityBlockViewSet(viewsets.ModelViewSet):
    queryset = AvailabilityBlock.objects.select_related(
        'usuario', 'municipio'
    ).all()
```

**Fix 2: _update_formadores batch**
```python
# apps/core/views/solicitacao.py
def _update_formadores(self, solicitacao, extra):
    new_formador_ids = set(extra.get('formador_ids', []))

    # Batch fetch em vez de loop
    usuarios_map = {
        u.id: u for u in Usuario.objects.filter(id__in=new_formador_ids)
    }

    # Bulk create participations
    participations_to_create = []
    for formador_id in to_add:
        if formador_id and formador_id in usuarios_map:
            participations_to_create.append(
                Participation(
                    solicitacao=solicitacao,
                    usuario=usuarios_map[formador_id],
                    role='FORMADOR'
                )
            )

    if participations_to_create:
        Participation.objects.bulk_create(
            participations_to_create,
            ignore_conflicts=True
        )
```

### Testes
```python
# apps/core/tests/test_query_optimization.py
from django.test.utils import CaptureQueriesContext
from django.db import connection

class TestQueryOptimization(TestCase):
    def test_availability_block_list_no_n_plus_1(self):
        """Listar 100 blocks deve usar ≤5 queries."""
        # Setup: criar 100 blocks
        for i in range(100):
            AvailabilityBlock.objects.create(...)

        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get('/api/availability-blocks/')

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(ctx.captured_queries), 5)

    def test_update_formadores_batch(self):
        """Atualizar 10 formadores deve usar ≤5 queries."""
        formador_ids = [f.id for f in create_formadores(10)]

        with CaptureQueriesContext(connection) as ctx:
            response = self.client.patch(
                f'/api/solicitacoes/{sol.id}/',
                {'extra_participants': {'formador_ids': formador_ids}}
            )

        self.assertLessEqual(len(ctx.captured_queries), 5)
```

---

## Issue 2: Error Handling (Custom Exception Handler)

### Problema Identificado

**Arquivo**: `apps/core/views_gcal/gcal.py:91`
```python
# ATUAL - HTTP 200 para erro
return Response(
    {"status": "unhealthy", "details": f"Error: {str(e)}"},
    status=status.HTTP_200_OK,  # ERRADO!
)
```

**Inconsistência de formatos**:
```json
// Formato 1 (DRF padrão)
{"detail": "Not found."}

// Formato 2 (custom)
{"error": "group_ids must be a list"}

// Formato 3 (availability)
{"ok": false, "conflicts": [...]}
```

### Solução

**1. Criar exception handler customizado**:
```python
# apps/core/exceptions.py
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import uuid
import logging

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Base exception for API errors."""
    def __init__(self, code: str, message: str, details: dict = None, status_code: int = 400):
        self.code = code
        self.message = message
        self.details = details or {}
        self.status_code = status_code
        super().__init__(message)


class ValidationError(APIError):
    def __init__(self, message: str, field: str = None, details: dict = None):
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            details={"field": field, **(details or {})},
            status_code=400
        )


class NotFoundError(APIError):
    def __init__(self, resource: str, identifier: str = None):
        super().__init__(
            code="NOT_FOUND",
            message=f"{resource} não encontrado",
            details={"resource": resource, "identifier": identifier},
            status_code=404
        )


class ServiceUnavailableError(APIError):
    def __init__(self, service: str, details: str = None):
        super().__init__(
            code="SERVICE_UNAVAILABLE",
            message=f"Serviço {service} indisponível",
            details={"service": service, "error": details},
            status_code=503
        )


def custom_exception_handler(exc, context):
    """
    Custom exception handler que padroniza todas as respostas de erro.

    Formato padrão:
    {
        "error": {
            "code": "ERROR_CODE",
            "message": "Human-readable message",
            "details": {...},
            "request_id": "uuid"
        }
    }
    """
    # Get request_id from middleware
    request = context.get('request')
    request_id = getattr(request, 'id', str(uuid.uuid4())) if request else str(uuid.uuid4())

    # Handle our custom APIError
    if isinstance(exc, APIError):
        logger.warning(
            f"API Error: {exc.code}",
            extra={
                "error_code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "request_id": request_id,
            }
        )
        return Response(
            {
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                    "request_id": request_id,
                }
            },
            status=exc.status_code
        )

    # Call DRF's default handler first
    response = exception_handler(exc, context)

    if response is not None:
        # Transform DRF errors to standard format
        error_data = response.data

        if isinstance(error_data, dict):
            if 'detail' in error_data:
                # Single error (404, 403, etc.)
                code = _get_error_code(response.status_code)
                message = str(error_data['detail'])
            else:
                # Validation errors (field: [errors])
                code = "VALIDATION_ERROR"
                message = "Erro de validação nos dados enviados"
                error_data = {"fields": error_data}
        else:
            code = _get_error_code(response.status_code)
            message = str(error_data)
            error_data = {}

        response.data = {
            "error": {
                "code": code,
                "message": message,
                "details": error_data if isinstance(error_data, dict) else {},
                "request_id": request_id,
            }
        }

    return response


def _get_error_code(status_code: int) -> str:
    """Map HTTP status code to error code."""
    mapping = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        429: "RATE_LIMITED",
        500: "INTERNAL_ERROR",
        503: "SERVICE_UNAVAILABLE",
    }
    return mapping.get(status_code, "UNKNOWN_ERROR")
```

**2. Registrar no settings.py**:
```python
# config/settings.py
REST_FRAMEWORK = {
    ...
    "EXCEPTION_HANDLER": "apps.core.exceptions.custom_exception_handler",
}
```

**3. Corrigir gcal_health**:
```python
# apps/core/views_gcal/gcal.py
from apps.core.exceptions import ServiceUnavailableError

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def gcal_health(request: Request) -> Response:
    try:
        client, _ = get_gcal_client_and_calendar_id()
        health_status = client.health_check()

        if health_status.get("status") == "unhealthy":
            raise ServiceUnavailableError(
                service="Google Calendar",
                details=health_status.get("details")
            )

        return Response(health_status, status=status.HTTP_200_OK)

    except ServiceUnavailableError:
        raise  # Re-raise for custom handler
    except Exception as e:
        raise ServiceUnavailableError(
            service="Google Calendar",
            details=str(e)
        )
```

### Testes
```python
# apps/core/tests/test_error_handling.py
class TestErrorHandling(TestCase):
    def test_error_response_format(self):
        """Todos os erros devem seguir formato padrão."""
        response = self.client.get('/api/solicitacoes/999999/')

        self.assertEqual(response.status_code, 404)
        self.assertIn('error', response.json())
        error = response.json()['error']
        self.assertIn('code', error)
        self.assertIn('message', error)
        self.assertIn('request_id', error)

    def test_gcal_health_unhealthy_returns_503(self):
        """gcal_health deve retornar 503 quando unhealthy."""
        with mock.patch('...get_gcal_client_and_calendar_id') as m:
            m.return_value[0].health_check.return_value = {"status": "unhealthy"}
            response = self.client.get('/api/gcal/health/')

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['error']['code'], 'SERVICE_UNAVAILABLE')
```

---

## Issue 3: Pagination (Unbounded Endpoints)

### Problema Identificado

**Arquivo**: `apps/core/views_gcal/summary.py:99`
```python
# ATUAL - Hard limit sem paginação
qs = qs[:500]
```

**Arquivo**: `apps/core/views_metrics.py:97`
```python
# ATUAL - Top 50 sem controle
.order_by("-eventos")[:50]
```

### Solução

**1. Criar paginação customizada com limite máximo**:
```python
# apps/core/pagination.py
from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """Paginação padrão com limite máximo."""
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 500


class LargePagination(PageNumberPagination):
    """Paginação para endpoints que precisam de mais dados."""
    page_size = 200
    page_size_query_param = 'page_size'
    max_page_size = 1000
```

**2. Aplicar em GCalListView**:
```python
# apps/core/views_gcal/summary.py
from apps.core.pagination import LargePagination

class GCalListView(APIView):
    permission_classes = [IsAuthenticated, IsControleOrSuper]
    pagination_class = LargePagination

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        qs = Solicitacao.objects.filter(status='aprovado').select_related(
            'usuario', 'municipio', 'tipo_evento', 'projeto'
        )
        qs = _apply_common_filters(qs, request)
        qs = qs.order_by('-inicio', '-id')

        # Usar paginação
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)

        if page is not None:
            serializer = SolicitacaoSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        # Fallback (não deve acontecer)
        serializer = SolicitacaoSerializer(qs[:500], many=True)
        return Response({'results': serializer.data, 'count': len(serializer.data)})
```

**3. Adicionar parâmetro limit em metrics**:
```python
# apps/core/views_metrics.py
@api_view(["GET"])
@permission_classes([IsControleOrDAT])
def metrics_map(request: Request) -> Response:
    # Parâmetro limit com default e máximo
    limit = min(int(request.query_params.get('limit', 50)), 100)

    by_municipio = (
        queryset
        .values(...)
        .annotate(...)
        .order_by("-eventos")[:limit]
    )

    return Response({
        "meta": {
            "limit": limit,
            "max_limit": 100,
            ...
        },
        ...
    })
```

### Testes
```python
# apps/core/tests/test_pagination.py
class TestPagination(TestCase):
    def test_gcal_list_paginated(self):
        """GCalListView deve retornar resposta paginada."""
        # Criar 600 solicitações
        for i in range(600):
            Solicitacao.objects.create(status='aprovado', ...)

        response = self.client.get('/api/gcal/list/')
        data = response.json()

        self.assertIn('count', data)
        self.assertIn('next', data)
        self.assertIn('results', data)
        self.assertLessEqual(len(data['results']), 200)  # max_page_size

    def test_metrics_map_respects_limit(self):
        """metrics_map deve respeitar parâmetro limit."""
        response = self.client.get('/api/metrics/map/?limit=10')
        data = response.json()

        self.assertLessEqual(len(data['by_municipio']), 10)
```

---

## Issue 4: Rate Limiting (Advanced Throttling)

### Problema Identificado

**Arquivo**: `config/settings.py:337-341`
```python
# ATUAL - Apenas 1 scope customizado
"DEFAULT_THROTTLE_RATES": {
    "anon": "100/hour",
    "user": "1000/hour",
    "availability_check": "60/min",  # Único!
}
```

### Solução

**1. Adicionar scopes para endpoints caros**:
```python
# config/settings.py
REST_FRAMEWORK = {
    ...
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
        # Scopes existentes
        "availability_check": "60/min",
        # Novos scopes para endpoints caros
        "metrics": "30/min",           # Geo queries + aggregations
        "reports": "30/min",           # Heavy aggregations
        "gcal_read": "60/min",         # Google Calendar reads
        "gcal_write": "10/min",        # Google Calendar writes (publish)
        "export": "10/min",            # CSV/JSON exports
    },
}
```

**2. Aplicar nos endpoints**:
```python
# apps/core/views_metrics.py
@api_view(["GET"])
@permission_classes([IsControleOrDAT])
@throttle_classes([ScopedRateThrottle])
def metrics_map(request: Request) -> Response:
    ...

metrics_map.throttle_scope = 'metrics'

# apps/core/views_reports.py
@api_view(["GET"])
@permission_classes([IsControleOrDAT])
@throttle_classes([ScopedRateThrottle])
def reports_status_counts(request: Request) -> Response:
    ...

reports_status_counts.throttle_scope = 'reports'

# apps/core/views_gcal/batch.py
class GCalPublishBatchView(APIView):
    permission_classes = [IsAuthenticated, IsControleOrSuper]
    throttle_scope = 'gcal_write'
```

**3. Adicionar Rate Limit headers via middleware**:
```python
# apps/core/middleware_ratelimit.py
from rest_framework.throttling import SimpleRateThrottle


class RateLimitHeadersMiddleware:
    """Adiciona headers X-RateLimit-* nas respostas."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Tentar extrair info de throttling do request
        throttle_info = getattr(request, '_throttle_info', None)
        if throttle_info:
            response['X-RateLimit-Limit'] = throttle_info.get('limit', '')
            response['X-RateLimit-Remaining'] = throttle_info.get('remaining', '')
            response['X-RateLimit-Reset'] = throttle_info.get('reset', '')

        return response
```

### Testes
```python
# apps/core/tests/test_rate_limiting.py
class TestRateLimiting(TestCase):
    def test_metrics_throttled(self):
        """metrics_map deve ter throttle de 30/min."""
        # Fazer 31 requests
        for i in range(31):
            response = self.client.get('/api/metrics/map/')
            if response.status_code == 429:
                break

        self.assertEqual(response.status_code, 429)
        self.assertIn('error', response.json())
        self.assertEqual(response.json()['error']['code'], 'RATE_LIMITED')
```

---

## Issue 5: API Versioning

### Problema Identificado

```
Atual:     /api/solicitacoes/
Esperado:  /api/v1/solicitacoes/
```

### Solução

**1. Configurar versioning no DRF**:
```python
# config/settings.py
REST_FRAMEWORK = {
    ...
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.URLPathVersioning",
    "DEFAULT_VERSION": "v1",
    "ALLOWED_VERSIONS": ["v1"],
    "VERSION_PARAM": "version",
}
```

**2. Reorganizar URLs**:
```python
# config/urls.py
urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.core.urls", namespace="core-v1")),
    # Redirect /api/ para /api/v1/ para backward compatibility
    path("api/", RedirectView.as_view(url="/api/v1/", permanent=False)),
    # Prometheus metrics
    path("", include("django_prometheus.urls")),
]
```

**3. Atualizar apps/core/urls.py**:
```python
# apps/core/urls.py
app_name = "core"  # Mantém o mesmo

# Nenhuma mudança necessária nos paths internos
# O prefixo /api/v1/ vem do config/urls.py
```

**4. Documentar deprecation strategy**:
```python
# apps/core/deprecation.py
import warnings
from functools import wraps


def deprecated_endpoint(message: str, removal_version: str = "v2"):
    """Decorator para marcar endpoints deprecated."""
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            response = func(request, *args, **kwargs)
            response['X-Deprecated'] = 'true'
            response['X-Deprecated-Message'] = message
            response['X-Removal-Version'] = removal_version
            return response
        return wrapper
    return decorator
```

### Testes
```python
# apps/core/tests/test_versioning.py
class TestVersioning(TestCase):
    def test_v1_endpoint_works(self):
        """Endpoints v1 devem funcionar."""
        response = self.client.get('/api/v1/solicitacoes/')
        self.assertEqual(response.status_code, 200)

    def test_api_redirects_to_v1(self):
        """GET /api/ deve redirecionar para /api/v1/."""
        response = self.client.get('/api/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/api/v1/')
```

---

## Issue 6: Response Consistency

### Problema Identificado

```json
// Formato 1: Paginação DRF
{"count": 10, "next": "...", "results": [...]}

// Formato 2: GCalListView
{"results": [...], "count": 150}

// Formato 3: Availability
{"ok": true, "conflicts": [...]}

// Formato 4: Reports
{"range": {...}, "items": [...]}
```

### Solução

**1. Criar envelope padrão para respostas customizadas**:
```python
# apps/core/responses.py
from rest_framework.response import Response
from django.utils import timezone


class APIResponse:
    """Factory para respostas padronizadas."""

    @staticmethod
    def success(data: dict, meta: dict = None) -> Response:
        """
        Resposta de sucesso padronizada.

        {
            "data": {...},
            "meta": {
                "timestamp": "...",
                ...
            }
        }
        """
        response_data = {
            "data": data,
            "meta": {
                "timestamp": timezone.now().isoformat(),
                **(meta or {})
            }
        }
        return Response(response_data)

    @staticmethod
    def list(items: list, total: int = None, meta: dict = None) -> Response:
        """
        Resposta de lista padronizada (não paginada).

        {
            "data": {
                "items": [...],
                "total": 10
            },
            "meta": {...}
        }
        """
        return APIResponse.success(
            data={
                "items": items,
                "total": total if total is not None else len(items)
            },
            meta=meta
        )

    @staticmethod
    def availability(ok: bool, conflicts: list = None) -> Response:
        """
        Resposta de availability check padronizada.

        {
            "data": {
                "available": true,
                "conflicts": []
            },
            "meta": {...}
        }
        """
        return APIResponse.success(
            data={
                "available": ok,
                "conflicts": conflicts or []
            }
        )
```

**2. Aplicar nos endpoints customizados**:
```python
# apps/core/views_reports.py
from apps.core.responses import APIResponse

@api_view(["GET"])
@permission_classes([IsControleOrDAT])
def reports_status_counts(request: Request) -> Response:
    ...

    return APIResponse.success(
        data={
            "counts": {
                "pendente": counts_dict.get("pendente", 0),
                "aprovado": counts_dict.get("aprovado", 0),
                "reprovado": counts_dict.get("reprovado", 0),
            },
            "total": queryset.count(),
        },
        meta={
            "range": {
                "start": str(start_date),
                "end": str(end_date)
            }
        }
    )
```

**3. Manter backward compatibility**:
```python
# Os ViewSets continuam usando o padrão DRF (já consistente)
# Apenas endpoints customizados são padronizados
```

### Testes
```python
# apps/core/tests/test_response_consistency.py
class TestResponseConsistency(TestCase):
    def test_custom_endpoints_have_data_key(self):
        """Endpoints customizados devem ter chave 'data'."""
        endpoints = [
            '/api/v1/reports/status-counts/',
            '/api/v1/reports/top-projects/',
            '/api/v1/metrics/map/',
        ]

        for endpoint in endpoints:
            response = self.client.get(endpoint)
            data = response.json()
            self.assertIn('data', data, f"{endpoint} missing 'data' key")
            self.assertIn('meta', data, f"{endpoint} missing 'meta' key")
```

---

## Issue 7: OpenAPI Documentation (@extend_schema)

### Problema Identificado

```
@extend_schema usados: 0
drf-spectacular instalado mas não utilizado
```

### Solução

**1. Documentar ViewSets principais**:
```python
# apps/core/views/solicitacao.py
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

@extend_schema_view(
    list=extend_schema(
        summary="Lista solicitações",
        description="Retorna lista paginada de solicitações filtradas por status, projeto, etc.",
        parameters=[
            OpenApiParameter("status", OpenApiTypes.STR, description="Filtrar por status (pendente/aprovado/reprovado)"),
            OpenApiParameter("search", OpenApiTypes.STR, description="Busca textual em usuário, município, observações"),
        ],
        responses={200: SolicitacaoSerializer(many=True)},
        tags=["solicitacoes"],
    ),
    retrieve=extend_schema(
        summary="Detalhe da solicitação",
        description="Retorna detalhes completos de uma solicitação específica.",
        responses={200: SolicitacaoSerializer},
        tags=["solicitacoes"],
    ),
    create=extend_schema(
        summary="Criar solicitação",
        description="Cria nova solicitação de evento. Status inicial: pendente (PA-01).",
        request=SolicitacaoSerializer,
        responses={201: SolicitacaoSerializer},
        tags=["solicitacoes"],
    ),
    approve=extend_schema(
        summary="Aprovar solicitação",
        description="Aprova uma solicitação pendente. Apenas Superintendência (PA-02).",
        request=None,
        responses={
            200: OpenApiExample(
                "Sucesso",
                value={"detail": "Solicitação aprovada com sucesso.", "solicitacao": {...}}
            ),
            400: OpenApiExample(
                "Já aprovada",
                value={"error": {"code": "BAD_REQUEST", "message": "Solicitação já está aprovada."}}
            ),
        },
        tags=["solicitacoes"],
    ),
)
class SolicitacaoViewSet(viewsets.ModelViewSet):
    ...
```

**2. Documentar endpoints customizados**:
```python
# apps/core/views_availability.py
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

class AvailabilityCheckView(APIView):
    @extend_schema(
        summary="Verificar disponibilidade",
        description="""
        Verifica se um usuário está disponível em determinado período.

        Regras verificadas (RD-01 a RD-08):
        - RD-01: Não-sobreposição com eventos existentes
        - RD-02: Bloqueio total (T) impede eventos
        - RD-03: Bloqueio parcial (P) impede subintervalo
        - RD-04: Buffer de deslocamento (D) entre municípios
        - RD-05: Capacidade diária (M) por formador
        """,
        parameters=[
            OpenApiParameter("usuario_id", OpenApiTypes.INT, required=True, description="ID do usuário"),
            OpenApiParameter("inicio", OpenApiTypes.DATETIME, required=True, description="Data/hora início (ISO8601)"),
            OpenApiParameter("fim", OpenApiTypes.DATETIME, required=True, description="Data/hora fim (ISO8601)"),
            OpenApiParameter("municipio_id", OpenApiTypes.INT, required=False, description="ID do município"),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "properties": {
                            "available": {"type": "boolean"},
                            "conflicts": {"type": "array", "items": {"type": "object"}}
                        }
                    },
                    "meta": {"type": "object"}
                }
            }
        },
        tags=["availability"],
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        ...
```

**3. Documentar schemas de erro**:
```python
# apps/core/schemas.py
from drf_spectacular.utils import OpenApiExample

ERROR_RESPONSES = {
    400: OpenApiExample(
        "Validation Error",
        value={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Erro de validação nos dados enviados",
                "details": {"fields": {"campo": ["erro"]}},
                "request_id": "uuid"
            }
        }
    ),
    401: OpenApiExample(
        "Unauthorized",
        value={
            "error": {
                "code": "UNAUTHORIZED",
                "message": "Autenticação necessária",
                "details": {},
                "request_id": "uuid"
            }
        }
    ),
    403: OpenApiExample(
        "Forbidden",
        value={
            "error": {
                "code": "FORBIDDEN",
                "message": "Permissão negada",
                "details": {},
                "request_id": "uuid"
            }
        }
    ),
    404: OpenApiExample(
        "Not Found",
        value={
            "error": {
                "code": "NOT_FOUND",
                "message": "Recurso não encontrado",
                "details": {},
                "request_id": "uuid"
            }
        }
    ),
}
```

### Testes
```python
# apps/core/tests/test_openapi.py
class TestOpenAPI(TestCase):
    def test_schema_generates_without_errors(self):
        """Schema OpenAPI deve gerar sem erros."""
        from drf_spectacular.generators import SchemaGenerator

        generator = SchemaGenerator(patterns=[])
        schema = generator.get_schema()

        self.assertIn('paths', schema)
        self.assertIn('components', schema)

    def test_all_endpoints_have_descriptions(self):
        """Todos endpoints devem ter descrição."""
        response = self.client.get('/api/v1/schema/')
        schema = response.json()

        for path, methods in schema['paths'].items():
            for method, details in methods.items():
                if method in ['get', 'post', 'put', 'patch', 'delete']:
                    self.assertIn('summary', details, f"{method.upper()} {path} missing summary")
```

---

## Ordem de Implementação

| Ordem | Issue | Dependências | Estimativa |
|-------|-------|--------------|------------|
| 1 | Query Optimization | Nenhuma | 2h |
| 2 | Error Handling | Nenhuma | 4h |
| 3 | Rate Limiting | Error Handling | 2h |
| 4 | Pagination | Nenhuma | 2h |
| 5 | Response Consistency | Error Handling | 3h |
| 6 | API Versioning | Nenhuma | 3h |
| 7 | OpenAPI Documentation | Todos anteriores | 6h |

**Total estimado**: ~22h de implementação

---

## Validação Final

Após implementação, executar:

```bash
# 1. Testes unitários
docker exec aprender_v2-web-1 pytest apps/core/tests/test_*.py -v

# 2. Type check
cd v2/backend && pyright apps/core

# 3. Verificar schema OpenAPI
curl http://localhost:8000/api/v1/schema/ | python -m json.tool

# 4. Performance check (N+1)
docker exec aprender_v2-web-1 pytest apps/core/tests/test_query_optimization.py -v

# 5. Rate limiting check
for i in {1..35}; do curl -s http://localhost:8000/api/v1/metrics/map/ | head -1; done
```

---

## Referências

- [Microsoft Azure - Web API Design Best Practices](https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design)
- [Stack Overflow - Best practices for REST API design](https://stackoverflow.blog/2020/03/02/best-practices-for-rest-api-design/)
- [drf-spectacular Documentation](https://drf-spectacular.readthedocs.io/)
- [Django REST Framework - Throttling](https://www.django-rest-framework.org/api-guide/throttling/)
