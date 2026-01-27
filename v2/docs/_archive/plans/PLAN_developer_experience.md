# Plano: Developer Experience (DX) Improvements

**Epic**: #414
**Status**: 🔄 Em Andamento
**Criado**: 2026-01-13
**Baseado em**: Análise de DevDocs, FastAPI, Public-APIs

---

## Objetivo

Implementar melhorias de Developer Experience inspiradas em repositórios de referência:
- **DevDocs** (38k stars) → Offline-first, busca instantânea
- **FastAPI** (94k stars) → Documentação automática, exemplos executáveis
- **Public-APIs** (390k stars) → Organização, badges de status

---

## Issues do Plano

| Issue | Categoria | Prioridade | Estimativa |
|-------|-----------|------------|------------|
| #415 | Interactive API Docs with Examples | Alta | 4h |
| #416 | Service Worker Offline Support | Média | 6h |
| #418 | Client-Side Instant Search | Média | 4h |
| #417 | API Status Badges | Média | 2h |

**Nota**: Issue #412 (OpenAPI @extend_schema) já cobre documentação automática.

---

## Issue 1: Interactive API Docs with Examples

### Problema

A documentação OpenAPI existe (`/api/docs/`) mas:
- Sem exemplos de request/response
- Sem casos de uso reais
- Sem código copiável

### Solução

**1. Adicionar exemplos em @extend_schema**

```python
# apps/core/views/solicitacao.py
from drf_spectacular.utils import extend_schema, OpenApiExample

@extend_schema(
    summary="Criar solicitação",
    description="""
    Cria nova solicitação de evento.

    ## Fluxo
    1. Frontend envia dados do wizard
    2. Backend valida disponibilidade (RD-01~08)
    3. Status inicial: `pendente` (SUPER) ou `aprovado` (NAO_SUPER)

    ## Exemplo de Uso
    ```bash
    curl -X POST /api/v1/solicitacoes/ \\
      -H "Content-Type: application/json" \\
      -H "X-CSRFToken: $CSRF" \\
      -d '{"titulo": "Formação", "inicio": "2026-01-20T09:00:00", ...}'
    ```
    """,
    request=SolicitacaoCreateSerializer,
    responses={201: SolicitacaoSerializer},
    examples=[
        OpenApiExample(
            "Evento Presencial",
            summary="Criar evento presencial em Fortaleza",
            value={
                "titulo": "Formação Fundamental I",
                "inicio": "2026-01-20T09:00:00-03:00",
                "fim": "2026-01-20T12:00:00-03:00",
                "municipio_id": 1,
                "projeto_id": 1,
                "tipo_evento_id": 1,
                "is_online": False,
                "observacoes": "Sala 101"
            },
            request_only=True,
        ),
        OpenApiExample(
            "Evento Online",
            summary="Criar evento online com Meet",
            value={
                "titulo": "Formação Online",
                "inicio": "2026-01-20T14:00:00-03:00",
                "fim": "2026-01-20T16:00:00-03:00",
                "is_online": True,
                "observacoes": "Link será gerado automaticamente"
            },
            request_only=True,
        ),
        OpenApiExample(
            "Resposta Sucesso",
            summary="Solicitação criada",
            value={
                "id": 123,
                "titulo": "Formação Fundamental I",
                "status": "pendente",
                "gcal_status": "NONE",
                "created_at": "2026-01-13T10:00:00-03:00"
            },
            response_only=True,
            status_codes=["201"],
        ),
    ],
    tags=["solicitacoes"],
)
def create(self, request):
    ...
```

**2. Criar página de exemplos estáticos**

```markdown
# v2/docs/API_EXAMPLES.md

## Autenticação

### Login
```bash
# 1. Obter CSRF token
CSRF=$(curl -s http://localhost:8000/api/csrf/ | jq -r '.csrfToken')

# 2. Login
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF" \
  -c cookies.txt \
  -d '{"username": "admin", "password": "admin123"}'
```

### Criar Solicitação
```bash
curl -X POST http://localhost:8000/api/v1/solicitacoes/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF" \
  -b cookies.txt \
  -d '{
    "titulo": "Formação",
    "inicio": "2026-01-20T09:00:00-03:00",
    "fim": "2026-01-20T12:00:00-03:00",
    "municipio_id": 1,
    "projeto_id": 1
  }'
```
```

**3. Configurar Swagger UI com exemplos**

```python
# config/settings.py
SPECTACULAR_SETTINGS = {
    ...
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayOperationId": True,
        "filter": True,
        "tryItOutEnabled": True,  # Habilitar "Try it out"
    },
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "REDOC_DIST": "SIDECAR",
}
```

### Arquivos a Criar/Modificar

- [ ] `apps/core/views/solicitacao.py` - Adicionar exemplos
- [ ] `apps/core/views/availability.py` - Adicionar exemplos
- [ ] `apps/core/views_gcal/batch.py` - Adicionar exemplos
- [ ] `v2/docs/API_EXAMPLES.md` - CRIAR
- [ ] `config/settings.py` - Swagger UI settings

### Testes

```python
def test_openapi_examples_present(self):
    """Verificar que exemplos estão no schema."""
    response = self.client.get('/api/v1/schema/')
    schema = response.json()

    create_op = schema['paths']['/api/v1/solicitacoes/']['post']
    self.assertIn('examples', create_op['requestBody']['content']['application/json'])
```

---

## Issue 2: Service Worker Offline Support

### Problema

Formadores frequentemente trabalham em áreas com conexão instável. O sistema não funciona offline.

### Solução

**1. Criar Service Worker**

```javascript
// v2/frontend/public/sw.js

const CACHE_NAME = 'aprender-v2-cache-v1';
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/assets/index.js',
  '/assets/index.css',
  '/manifest.json',
];

const API_CACHE_NAME = 'aprender-v2-api-cache';
const CACHEABLE_API_ROUTES = [
  '/api/v1/options/',
  '/api/v1/me/',
  '/api/v1/config/',
];

// Install: cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

// Activate: clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME && name !== API_CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    })
  );
  self.clients.claim();
});

// Fetch: network-first for API, cache-first for static
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // API requests: network-first with cache fallback
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirstWithCache(request));
    return;
  }

  // Static assets: cache-first
  event.respondWith(cacheFirstWithNetwork(request));
});

async function networkFirstWithCache(request) {
  try {
    const response = await fetch(request);

    // Cache GET requests for cacheable routes
    if (request.method === 'GET' && isCacheableApiRoute(request.url)) {
      const cache = await caches.open(API_CACHE_NAME);
      cache.put(request, response.clone());
    }

    return response;
  } catch (error) {
    // Offline: try cache
    const cached = await caches.match(request);
    if (cached) {
      return cached;
    }

    // Return offline response for non-cached API
    return new Response(
      JSON.stringify({ error: { code: 'OFFLINE', message: 'Você está offline' } }),
      { status: 503, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

async function cacheFirstWithNetwork(request) {
  const cached = await caches.match(request);
  if (cached) {
    return cached;
  }

  try {
    const response = await fetch(request);
    const cache = await caches.open(CACHE_NAME);
    cache.put(request, response.clone());
    return response;
  } catch (error) {
    // Return offline page
    return caches.match('/offline.html');
  }
}

function isCacheableApiRoute(url) {
  return CACHEABLE_API_ROUTES.some(route => url.includes(route));
}
```

**2. Registrar Service Worker**

```javascript
// v2/frontend/src/main.jsx
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js')
      .then((registration) => {
        console.log('SW registered:', registration.scope);
      })
      .catch((error) => {
        console.log('SW registration failed:', error);
      });
  });
}
```

**3. Criar manifest.json para PWA**

```json
// v2/frontend/public/manifest.json
{
  "name": "Aprender Sistema v2",
  "short_name": "AS v2",
  "description": "Sistema de gestão de eventos de formação",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#1890ff",
  "icons": [
    {
      "src": "/icons/icon-192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/icons/icon-512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}
```

**4. Criar página offline**

```html
<!-- v2/frontend/public/offline.html -->
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Offline - Aprender Sistema</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      margin: 0;
      background: #f5f5f5;
    }
    .container {
      text-align: center;
      padding: 2rem;
    }
    h1 { color: #1890ff; }
    p { color: #666; }
    button {
      background: #1890ff;
      color: white;
      border: none;
      padding: 12px 24px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 16px;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>📡 Você está offline</h1>
    <p>Verifique sua conexão e tente novamente.</p>
    <button onclick="location.reload()">Tentar Novamente</button>
  </div>
</body>
</html>
```

**5. Hook para detectar status de conexão**

```javascript
// v2/frontend/src/hooks/useOnlineStatus.js
import { useState, useEffect } from 'react';

export function useOnlineStatus() {
  const [isOnline, setIsOnline] = useState(navigator.onLine);

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return isOnline;
}
```

**6. Componente de aviso offline**

```javascript
// v2/frontend/src/components/OfflineBanner.jsx
import { Alert } from 'antd';
import { WifiOutlined } from '@ant-design/icons';
import { useOnlineStatus } from '../hooks/useOnlineStatus';

export function OfflineBanner() {
  const isOnline = useOnlineStatus();

  if (isOnline) return null;

  return (
    <Alert
      message="Você está offline"
      description="Algumas funcionalidades podem estar limitadas."
      type="warning"
      icon={<WifiOutlined />}
      banner
      closable={false}
    />
  );
}
```

### Arquivos a Criar

- [ ] `v2/frontend/public/sw.js` - Service Worker
- [ ] `v2/frontend/public/manifest.json` - PWA manifest
- [ ] `v2/frontend/public/offline.html` - Página offline
- [ ] `v2/frontend/public/icons/` - Ícones PWA
- [ ] `v2/frontend/src/hooks/useOnlineStatus.js` - Hook
- [ ] `v2/frontend/src/components/OfflineBanner.jsx` - Banner

### Arquivos a Modificar

- [ ] `v2/frontend/src/main.jsx` - Registrar SW
- [ ] `v2/frontend/index.html` - Link manifest
- [ ] `v2/frontend/src/App.jsx` - Adicionar OfflineBanner

### Testes

```javascript
// v2/frontend/e2e/offline.spec.ts
test('shows offline banner when disconnected', async ({ page, context }) => {
  await page.goto('/');

  // Simulate offline
  await context.setOffline(true);

  // Should show offline banner
  await expect(page.locator('.ant-alert-warning')).toBeVisible();
  await expect(page.locator('text=Você está offline')).toBeVisible();
});
```

---

## Issue 3: Client-Side Instant Search

### Problema

A busca atual faz requisição ao servidor a cada keystroke, causando latência e carga desnecessária.

### Solução

**1. Criar índice local de dados frequentes**

```javascript
// v2/frontend/src/services/searchIndex.js
import Fuse from 'fuse.js';

class SearchIndex {
  constructor() {
    this.indices = {};
    this.data = {};
  }

  // Indexar dados de um endpoint
  async index(key, data, options = {}) {
    this.data[key] = data;
    this.indices[key] = new Fuse(data, {
      keys: options.keys || ['nome', 'titulo', 'descricao'],
      threshold: options.threshold || 0.3,
      includeScore: true,
      includeMatches: true,
    });
  }

  // Buscar em um índice específico
  search(key, query, limit = 10) {
    const index = this.indices[key];
    if (!index) return [];

    return index.search(query).slice(0, limit).map(result => ({
      ...result.item,
      _score: result.score,
      _matches: result.matches,
    }));
  }

  // Buscar em todos os índices
  searchAll(query, limit = 10) {
    const results = {};
    for (const key of Object.keys(this.indices)) {
      results[key] = this.search(key, query, limit);
    }
    return results;
  }

  // Limpar índice
  clear(key) {
    if (key) {
      delete this.indices[key];
      delete this.data[key];
    } else {
      this.indices = {};
      this.data = {};
    }
  }
}

export const searchIndex = new SearchIndex();
```

**2. Hook de busca instantânea**

```javascript
// v2/frontend/src/hooks/useInstantSearch.js
import { useState, useEffect, useMemo } from 'react';
import { useDebouncedValue } from './useDebouncedValue';
import { searchIndex } from '../services/searchIndex';

export function useInstantSearch(indexKey, query, options = {}) {
  const { debounceMs = 150, limit = 10, minLength = 2 } = options;

  const debouncedQuery = useDebouncedValue(query, debounceMs);
  const [results, setResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);

  useEffect(() => {
    if (!debouncedQuery || debouncedQuery.length < minLength) {
      setResults([]);
      return;
    }

    setIsSearching(true);

    // Busca local é síncrona e instantânea
    const searchResults = searchIndex.search(indexKey, debouncedQuery, limit);
    setResults(searchResults);
    setIsSearching(false);
  }, [debouncedQuery, indexKey, limit, minLength]);

  return { results, isSearching, query: debouncedQuery };
}
```

**3. Pré-carregar dados no login**

```javascript
// v2/frontend/src/services/preloadSearchData.js
import { searchIndex } from './searchIndex';
import { api } from '../api';

export async function preloadSearchData() {
  try {
    // Carregar dados em paralelo
    const [municipios, projetos, usuarios, tiposEvento] = await Promise.all([
      api.get('/api/v1/options/municipios/'),
      api.get('/api/v1/options/projetos/'),
      api.get('/api/v1/options/usuarios/'),
      api.get('/api/v1/options/tipos-evento/'),
    ]);

    // Indexar para busca instantânea
    await searchIndex.index('municipios', municipios.data, {
      keys: ['nome', 'uf'],
    });

    await searchIndex.index('projetos', projetos.data, {
      keys: ['nome', 'codigo'],
    });

    await searchIndex.index('usuarios', usuarios.data, {
      keys: ['nome', 'email', 'username'],
    });

    await searchIndex.index('tiposEvento', tiposEvento.data, {
      keys: ['nome'],
    });

    console.log('Search index loaded:', {
      municipios: municipios.data.length,
      projetos: projetos.data.length,
      usuarios: usuarios.data.length,
      tiposEvento: tiposEvento.data.length,
    });
  } catch (error) {
    console.error('Failed to preload search data:', error);
  }
}
```

**4. Componente de busca global**

```javascript
// v2/frontend/src/components/GlobalSearch.jsx
import { useState } from 'react';
import { Input, List, Typography, Tag } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { useInstantSearch } from '../hooks/useInstantSearch';

const { Text } = Typography;

export function GlobalSearch({ onSelect }) {
  const [query, setQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState('municipios');

  const { results, isSearching } = useInstantSearch(activeIndex, query);

  return (
    <div className="global-search">
      <Input
        prefix={<SearchOutlined />}
        placeholder="Buscar municípios, projetos, usuários..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        allowClear
      />

      {query.length >= 2 && (
        <div className="search-results">
          <div className="search-tabs">
            {['municipios', 'projetos', 'usuarios'].map(key => (
              <Tag
                key={key}
                color={activeIndex === key ? 'blue' : 'default'}
                onClick={() => setActiveIndex(key)}
                style={{ cursor: 'pointer' }}
              >
                {key}
              </Tag>
            ))}
          </div>

          <List
            size="small"
            loading={isSearching}
            dataSource={results}
            renderItem={(item) => (
              <List.Item
                onClick={() => onSelect?.(item, activeIndex)}
                style={{ cursor: 'pointer' }}
              >
                <Text>{item.nome || item.titulo}</Text>
                {item._score && (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {Math.round((1 - item._score) * 100)}% match
                  </Text>
                )}
              </List.Item>
            )}
          />
        </div>
      )}
    </div>
  );
}
```

### Dependências

```bash
npm install fuse.js
```

### Arquivos a Criar

- [ ] `v2/frontend/src/services/searchIndex.js` - Índice Fuse.js
- [ ] `v2/frontend/src/services/preloadSearchData.js` - Pré-carregamento
- [ ] `v2/frontend/src/hooks/useInstantSearch.js` - Hook de busca
- [ ] `v2/frontend/src/hooks/useDebouncedValue.js` - Hook debounce
- [ ] `v2/frontend/src/components/GlobalSearch.jsx` - Componente

### Arquivos a Modificar

- [ ] `v2/frontend/src/App.jsx` - Chamar preload no login
- [ ] `v2/frontend/package.json` - Adicionar fuse.js

### Testes

```javascript
// v2/frontend/src/__tests__/searchIndex.test.js
import { searchIndex } from '../services/searchIndex';

describe('SearchIndex', () => {
  beforeEach(() => {
    searchIndex.clear();
  });

  test('indexes and searches data', async () => {
    const data = [
      { id: 1, nome: 'Fortaleza' },
      { id: 2, nome: 'São Paulo' },
      { id: 3, nome: 'Fortal' },
    ];

    await searchIndex.index('cities', data, { keys: ['nome'] });

    const results = searchIndex.search('cities', 'Fort');

    expect(results.length).toBe(2);
    expect(results[0].nome).toBe('Fortaleza');
  });

  test('returns empty for short queries', () => {
    const results = searchIndex.search('cities', 'F');
    expect(results).toEqual([]);
  });
});
```

---

## Issue 4: API Status Badges

### Problema

Não há indicação visual de quais endpoints estão deprecated, beta, ou stable no API_REFERENCE.md.

### Solução

**1. Definir badges padrão**

```markdown
<!-- v2/docs/API_BADGES.md -->

# API Status Badges

## Definições

| Badge | Significado | Uso |
|-------|-------------|-----|
| ![Stable](https://img.shields.io/badge/status-stable-green) | Endpoint estável, sem mudanças planejadas | Maioria dos endpoints |
| ![Beta](https://img.shields.io/badge/status-beta-yellow) | Pode mudar sem aviso prévio | Features novas |
| ![Deprecated](https://img.shields.io/badge/status-deprecated-red) | Será removido na próxima versão | Endpoints antigos |
| ![Internal](https://img.shields.io/badge/status-internal-gray) | Uso interno, não documentado publicamente | Admin tools |

## Formato de Uso

```markdown
### POST /api/v1/solicitacoes/ ![Stable](https://img.shields.io/badge/status-stable-green)
```
```

**2. Atualizar API_REFERENCE.md com badges**

```markdown
<!-- v2/docs/API_REFERENCE.md -->

## 📋 Solicitações

### CRUD Principal

| Método | Endpoint | Status | Descrição |
|--------|----------|--------|-----------|
| GET | `/api/v1/solicitacoes/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar solicitações |
| POST | `/api/v1/solicitacoes/` | ![Stable](https://img.shields.io/badge/-stable-green) | Criar solicitação |
| GET | `/api/v1/solicitacoes/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Detalhes |
| POST | `/api/v1/solicitacoes/{id}/approve/` | ![Stable](https://img.shields.io/badge/-stable-green) | Aprovar (PA-02) |

### Endpoints Beta

| Método | Endpoint | Status | Descrição |
|--------|----------|--------|-----------|
| GET | `/api/v1/gcal/dashboard/insights/` | ![Beta](https://img.shields.io/badge/-beta-yellow) | Insights GCal |
| POST | `/api/v1/gcal/batch/resync/` | ![Beta](https://img.shields.io/badge/-beta-yellow) | Resync em lote |

### Endpoints Deprecated

| Método | Endpoint | Status | Migrar Para |
|--------|----------|--------|-------------|
| GET | `/api/pre-agenda/` | ![Deprecated](https://img.shields.io/badge/-deprecated-red) | `/api/v1/gcal/list/` |
```

**3. Criar script para validar badges**

```python
# scripts/validate_api_badges.py
"""
Valida que todos os endpoints no API_REFERENCE.md têm badges de status.
"""
import re
from pathlib import Path

def validate_api_reference():
    api_ref = Path('v2/docs/API_REFERENCE.md').read_text()

    # Encontrar todas as linhas com endpoints
    endpoint_pattern = r'\| (GET|POST|PUT|PATCH|DELETE) \| `([^`]+)` \|'
    endpoints = re.findall(endpoint_pattern, api_ref)

    # Verificar se cada endpoint tem badge
    badge_pattern = r'!\[.*\]\(https://img\.shields\.io/badge/.*\)'

    missing_badges = []
    for method, endpoint in endpoints:
        line_pattern = rf'\| {method} \| `{re.escape(endpoint)}` \|[^|]*\|'
        match = re.search(line_pattern, api_ref)
        if match and not re.search(badge_pattern, match.group()):
            missing_badges.append(f"{method} {endpoint}")

    if missing_badges:
        print("❌ Endpoints sem badge de status:")
        for ep in missing_badges:
            print(f"  - {ep}")
        return False

    print("✅ Todos os endpoints têm badge de status")
    return True

if __name__ == '__main__':
    validate_api_reference()
```

**4. Adicionar ao CI**

```yaml
# .github/workflows/docs.yml
- name: Validate API badges
  run: python scripts/validate_api_badges.py
```

### Arquivos a Criar

- [ ] `v2/docs/API_BADGES.md` - Definições de badges
- [ ] `scripts/validate_api_badges.py` - Script de validação

### Arquivos a Modificar

- [ ] `v2/docs/API_REFERENCE.md` - Adicionar badges em todos endpoints
- [ ] `.github/workflows/docs.yml` - Adicionar validação

### Testes

```bash
python scripts/validate_api_badges.py
```

---

## Ordem de Implementação

| Ordem | Issue | Dependências | Estimativa |
|-------|-------|--------------|------------|
| 1 | API Status Badges | Nenhuma | 2h |
| 2 | Interactive API Docs | #412 (OpenAPI) | 4h |
| 3 | Client-Side Instant Search | Nenhuma | 4h |
| 4 | Service Worker Offline | Nenhuma | 6h |

**Total**: ~16h de implementação

---

## Validação Final

```bash
# 1. Verificar badges
python scripts/validate_api_badges.py

# 2. Testar Swagger UI
curl http://localhost:8000/api/v1/docs/

# 3. Testar busca instantânea
npm run test -- searchIndex

# 4. Testar Service Worker
npm run test:e2e -- offline.spec.ts

# 5. Lighthouse PWA audit
npm run lighthouse
```

---

## Referências

- [DevDocs - Service Worker Implementation](https://github.com/freeCodeCamp/devdocs)
- [FastAPI - OpenAPI Examples](https://fastapi.tiangolo.com/tutorial/schema-extra-example/)
- [Fuse.js - Fuzzy Search Library](https://fusejs.io/)
- [MDN - Service Worker API](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API)
