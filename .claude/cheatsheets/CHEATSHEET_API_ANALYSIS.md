# API Analysis Report — Aprender Sistema v2

Comparative analysis against REST API best practices (2025).

---

## Executive Summary

| Categoria | Score | Status |
|-----------|-------|--------|
| **URL Design** | 9/10 | Excelente |
| **HTTP Methods** | 9/10 | Excelente |
| **Authentication/RBAC** | 9/10 | Excelente |
| **Documentation (OpenAPI)** | 5/10 | Parcial |
| **Pagination** | 6/10 | Gaps críticos |
| **Error Handling** | 4/10 | Inconsistente |
| **Query Optimization** | 6/10 | N+1 risks |
| **Rate Limiting** | 5/10 | Incompleto |
| **Versioning** | 3/10 | Não implementado |
| **Response Consistency** | 5/10 | Variado |

**Score Global: 6.1/10** — Bom fundamento, mas com gaps importantes.

---

## Estatísticas do Projeto

| Métrica | Valor |
|---------|-------|
| Total de Endpoints | 89+ |
| ViewSets | 20 |
| Serializers | 54+ |
| Permission Classes | 11 |
| Com Paginação | ~60% |
| Com Filtering | ~40% |
| Com select_related | ~30% |
| Com Rate Limiting | ~15% |

---

## Comparativo: Best Practices vs Estado Atual

### 1. URL Design

| Best Practice | Status | Observação |
|---------------|--------|------------|
| Usar substantivos (nouns) | ✅ | `/api/solicitacoes/`, `/api/municipios/` |
| Plural para coleções | ✅ | Consistente em todo projeto |
| Hierarquia lógica | ✅ | `/api/dat/cadastros/`, `/api/dat/acoes-ciclo/` |
| Kebab-case | ✅ | `availability-blocks`, `compras-materiais` |
| Sem verbos na URL | ✅ | Exceto `/api/auth/login/` (aceitável) |

**Score: 9/10** — Excelente aderência.

---

### 2. HTTP Methods

| Method | Uso Correto | Observação |
|--------|-------------|------------|
| GET | ✅ | List, retrieve, options, lookup |
| POST | ✅ | Create, custom actions (approve, publish) |
| PUT/PATCH | ✅ | Update completo/parcial |
| DELETE | ✅ | Destroy (com permissões adequadas) |

**Score: 9/10** — Uso correto dos verbos HTTP.

---

### 3. Authentication & RBAC

| Best Practice | Status | Implementação |
|---------------|--------|---------------|
| Session-based auth | ✅ | Django sessions |
| CSRF protection | ✅ | `/api/csrf/` endpoint |
| Role-based access | ✅ | 11 permission classes |
| Object-level permissions | ✅ | `IsOwnerOrPrivileged` |
| Multi-sector access | ✅ | `HasSectorAccess` (novo) |

**Permission Classes:**
```python
IsSuperintendencia      # Superintendência, DAT, superuser
IsSuperintendenciaOnly  # SOMENTE Superintendência
IsCoordenadorOrDAT      # Coordenadores ou DAT
IsControleOrDAT         # Controle, DAT, Superintendência
IsDATOrSuper            # DAT ou superuser
IsOwnerOrPrivileged     # Dono ou privilegiado
HasSectorAccess         # Acesso multi-setor
```

**Score: 9/10** — RBAC bem implementado.

---

### 4. API Documentation (OpenAPI)

| Best Practice | Status | Observação |
|---------------|--------|------------|
| OpenAPI/Swagger | ✅ | drf-spectacular instalado |
| UI interativa | ✅ | `/api/docs/`, `/api/redoc/` |
| Tags organizadas | ✅ | 8 tags definidas |
| @extend_schema decorators | ❌ | **0 usos** |
| Field descriptions | ❌ | Não documentados |
| Response examples | ❌ | Não definidos |
| Error schemas | ❌ | Não documentados |

**Gaps:**
- Endpoints customizados (reports, metrics) não documentados
- Serializers sem `help_text` nos campos
- Respostas de erro não padronizadas no schema

**Score: 5/10** — Estrutura existe, mas incompleta.

---

### 5. Pagination

| Best Practice | Status | Observação |
|---------------|--------|------------|
| Default pagination | ✅ | PageNumberPagination, 100 items |
| Metadata (count, next, prev) | ✅ | Padrão DRF |
| Max page size limit | ⚠️ | Não definido explicitamente |
| Pagination em todos endpoints | ❌ | **Gaps críticos** |

**Endpoints SEM paginação (RISCO):**
```
/api/gcal/list/           ← Unbounded results
/api/metrics/map/         ← Pode retornar muitos dados
/api/reports/*            ← Aggregations sem limite
/api/pre-agenda/          ← Lista completa
```

**Score: 6/10** — Parcialmente implementado.

---

### 6. Error Handling

| Best Practice | Status | Observação |
|---------------|--------|------------|
| HTTP status codes corretos | ✅ | 400, 401, 403, 404, 500 |
| Formato de erro consistente | ❌ | Varia por endpoint |
| Request ID/Correlation | ❌ | Não implementado |
| Custom exception handler | ❌ | Usa default DRF |
| Error logging estruturado | ⚠️ | Parcial |

**Inconsistências encontradas:**
```python
# GCal health retorna 200 mesmo com erro (!)
{
  "status": "unhealthy",  # Deveria ser HTTP 503
  "details": "..."
}

# Validação de availability retorna estrutura própria
{
  "ok": false,
  "conflicts": [...]
}

# Erros DRF padrão
{
  "detail": "Not found."
}
```

**Score: 4/10** — Precisa padronização.

---

### 7. Query Optimization

| Best Practice | Status | Observação |
|---------------|--------|------------|
| select_related para FK | ⚠️ | 30% dos ViewSets |
| prefetch_related para M2M | ⚠️ | Usado em Solicitacao |
| Evitar N+1 queries | ❌ | **Vulnerabilidades** |
| Annotations para counts | ✅ | Usado em Gerencia |

**N+1 Vulnerabilities:**
```python
# AvailabilityBlockViewSet - SEM otimização
queryset = AvailabilityBlock.objects.all()
# 100 blocks × 2 FKs = 200+ queries extras

# AuditLogViewSet - SEM otimização
queryset = AuditLog.objects.all()
# 100 logs × 3 FKs = 300+ queries extras

# SolicitacaoViewSet._update_formadores() - Loop N+1
for formador_id in to_add:
    usuario = Usuario.objects.get(id=formador_id)  # 1 query/formador
```

**Score: 6/10** — Principais ViewSets otimizados, outros não.

---

### 8. Rate Limiting

| Best Practice | Status | Observação |
|---------------|--------|------------|
| Global rate limiting | ✅ | anon: 100/h, user: 1000/h |
| Scope-based limiting | ⚠️ | Apenas `availability_check` |
| Headers X-RateLimit-* | ❌ | Não expostos |
| Retry-After header | ❌ | Não implementado |

**Endpoints caros SEM throttling específico:**
```
/api/metrics/map/           ← Geo queries
/api/reports/*              ← Aggregations
/api/gcal/list/             ← External API
/api/gcal/publish-batch/    ← External API writes
```

**Score: 5/10** — Básico implementado, avançado faltando.

---

### 9. Versioning

| Best Practice | Status | Observação |
|---------------|--------|------------|
| URL versioning (/v1/, /v2/) | ❌ | Não implementado |
| Header versioning | ❌ | Não implementado |
| Deprecation strategy | ❌ | Não definida |

**Atual:** `/api/solicitacoes/` (sem versão)
**Recomendado:** `/api/v1/solicitacoes/`

**Score: 3/10** — Não implementado.

---

### 10. Response Consistency

| Best Practice | Status | Observação |
|---------------|--------|------------|
| JSON como padrão | ✅ | Content-Type correto |
| Estrutura consistente | ❌ | Varia por tipo de endpoint |
| Envelope pattern | ❌ | Não usado |
| HATEOAS links | ❌ | Não implementado |

**Formatos encontrados:**
```json
// ViewSet padrão (list)
{"count": 10, "next": "...", "results": [...]}

// ViewSet padrão (detail)
{"id": 1, "nome": "...", ...}

// Availability check (custom)
{"ok": true, "conflicts": [...]}

// Metrics (custom)
{"features": {...}, "markers": [...]}

// Reports (custom)
{"pendente": 5, "aprovado": 10, ...}
```

**Score: 5/10** — ViewSets consistentes, custom endpoints não.

---

## Recomendações Priorizadas

### Alta Prioridade (Segurança/Performance)

#### 1. Adicionar Paginação aos Endpoints Sem Limite
```python
# views.py
class GCalListView(APIView):
    pagination_class = PageNumberPagination

# Ou limitar explicitamente
results = queryset[:100]  # Hard limit
```

#### 2. Corrigir N+1 Queries
```python
# AvailabilityBlockViewSet
queryset = AvailabilityBlock.objects.select_related(
    'usuario', 'municipio'
).all()

# AuditLogViewSet
queryset = AuditLog.objects.select_related(
    'usuario'
).all()

# _update_formadores - batch fetch
usuarios = {u.id: u for u in Usuario.objects.filter(id__in=to_add)}
for formador_id in to_add:
    usuario = usuarios.get(formador_id)
```

#### 3. Throttling em Endpoints Caros
```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_RATES': {
        'metrics': '30/min',
        'reports': '30/min',
        'gcal_write': '10/min',
    }
}

# views.py
class MetricsMapView(APIView):
    throttle_scope = 'metrics'
```

### Média Prioridade (Qualidade)

#### 4. Padronizar Error Responses
```python
# exceptions.py
class StandardErrorResponse:
    def __init__(self, code, message, details=None):
        self.code = code
        self.message = message
        self.details = details or {}

# Formato padronizado
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid date range",
        "details": {
            "field": "inicio",
            "reason": "Must be in the future"
        },
        "request_id": "abc-123"
    }
}
```

#### 5. Documentar APIs com @extend_schema
```python
from drf_spectacular.utils import extend_schema, OpenApiParameter

class SolicitacaoViewSet(viewsets.ModelViewSet):
    @extend_schema(
        summary="Lista solicitações",
        description="Retorna solicitações filtradas por status, projeto, etc.",
        parameters=[
            OpenApiParameter("status", str, description="Filter by status"),
        ],
        responses={200: SolicitacaoSerializer(many=True)}
    )
    def list(self, request):
        ...
```

#### 6. Implementar API Versioning
```python
# urls.py
urlpatterns = [
    path('api/v1/', include('apps.core.urls_v1')),
    path('api/v2/', include('apps.core.urls_v2')),  # Future
]

# settings.py
REST_FRAMEWORK = {
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.URLPathVersioning',
    'DEFAULT_VERSION': 'v1',
    'ALLOWED_VERSIONS': ['v1'],
}
```

### Baixa Prioridade (Nice to Have)

#### 7. Rate Limit Headers
```python
# middleware.py ou custom throttle
response['X-RateLimit-Limit'] = '1000'
response['X-RateLimit-Remaining'] = '950'
response['X-RateLimit-Reset'] = '1609459200'
```

#### 8. Request ID para Tracing
```python
# middleware.py
import uuid

class RequestIDMiddleware:
    def __call__(self, request):
        request.id = str(uuid.uuid4())
        response = self.get_response(request)
        response['X-Request-ID'] = request.id
        return response
```

#### 9. HATEOAS Links (opcional)
```python
# serializers.py
class SolicitacaoSerializer(serializers.ModelSerializer):
    links = serializers.SerializerMethodField()

    def get_links(self, obj):
        return {
            "self": f"/api/v1/solicitacoes/{obj.id}/",
            "approve": f"/api/v1/solicitacoes/{obj.id}/approve/",
            "publish": f"/api/v1/solicitacoes/{obj.id}/publish/",
        }
```

---

## Checklist de Implementação

### Fase 1: Critical Fixes (1-2 dias)
- [ ] Adicionar paginação em `/api/gcal/list/`
- [ ] Adicionar paginação em `/api/metrics/map/`
- [ ] Corrigir N+1 em `AvailabilityBlockViewSet`
- [ ] Corrigir N+1 em `AuditLogViewSet`
- [ ] Corrigir N+1 em `_update_formadores()`

### Fase 2: Quality Improvements (3-5 dias)
- [ ] Criar custom exception handler
- [ ] Padronizar formato de erro
- [ ] Adicionar throttling em endpoints caros
- [ ] Documentar principais endpoints com @extend_schema

### Fase 3: Best Practices (1 semana)
- [ ] Implementar API versioning (/v1/)
- [ ] Adicionar Request ID middleware
- [ ] Expor Rate Limit headers
- [ ] Completar documentação OpenAPI

---

## Fontes

- [Microsoft Azure - Web API Design Best Practices](https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design)
- [Stack Overflow - Best practices for REST API design](https://stackoverflow.blog/2020/03/02/best-practices-for-rest-api-design/)
- [ByteByteGo - REST API Design Cheatsheet](https://blog.bytebytego.com/p/ep161-a-cheatsheet-on-rest-api-design)
- [Django REST Framework - Documenting your API](https://www.django-rest-framework.org/topics/documenting-your-api/)
- [drf-spectacular Documentation](https://drf-spectacular.readthedocs.io/)
- [Postman - REST API Best Practices](https://blog.postman.com/rest-api-best-practices/)
