# 📡 API Reference — Aprender Sistema v2

**Última Atualização**: 2026-03-06
**Total de Endpoints**: 139 (base canônica `/api`)
**ViewSets**: 26

> **Legenda de Status**: ![Stable](https://img.shields.io/badge/-stable-green) Estável | ![Beta](https://img.shields.io/badge/-beta-yellow) Beta | ![Deprecated](https://img.shields.io/badge/-deprecated-red) Deprecated | ![Internal](https://img.shields.io/badge/-internal-gray) Interno
>
> Ver [API_BADGES.md](./API_BADGES.md) para detalhes.

---

## 🧭 Política Canônica de Rotas

- **Base path canônico oficial**: `/api/`
- **Alias de compatibilidade temporário**: `/api/v1/`

Regras:

- Toda documentação nova deve usar `/api/*`.
- Todo código novo (frontend/backend/tests/scripts) deve usar `/api/*`.
- `/api/v1/*` existe apenas para compatibilidade e não deve ser usado em novas integrações.

Observação:

- Quando um endpoint aparecer como `/alguma-rota/` nesta referência, ele é relativo ao base path canônico (`/api/alguma-rota/`).

---

## 🔐 Autenticação

Todos os endpoints (exceto `/auth/` e `/csrf/`) requerem autenticação via session cookie.

### Endpoints de Auth

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| POST | `/auth/login/` | ![Stable](https://img.shields.io/badge/-stable-green) | Login com username/password | AllowAny |
| POST | `/auth/logout/` | ![Stable](https://img.shields.io/badge/-stable-green) | Logout e invalidação de sessão | IsAuthenticated |
| GET | `/csrf/` | ![Stable](https://img.shields.io/badge/-stable-green) | Obter CSRF token | AllowAny |
| GET | `/auth/ping/` | ![Stable](https://img.shields.io/badge/-stable-green) | Health check simples | AllowAny |
| GET | `/me/` | ![Stable](https://img.shields.io/badge/-stable-green) | Dados do usuário logado + RBAC | IsAuthenticated |

### Headers Obrigatórios

```http
Content-Type: application/json
X-CSRFToken: <csrf_token>
Cookie: sessionid=<session_id>
```

---

## 📋 Solicitações

### CRUD Principal

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/solicitacoes/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar solicitações (paginado) | IsAuthenticated |
| POST | `/api/solicitacoes/` | ![Stable](https://img.shields.io/badge/-stable-green) | Criar nova solicitação | IsAuthenticated |
| GET | `/api/solicitacoes/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Detalhes de uma solicitação | IsAuthenticated |
| PUT | `/api/solicitacoes/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Atualizar solicitação completa | IsAuthenticated |
| PATCH | `/api/solicitacoes/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Atualizar parcialmente | IsAuthenticated |
| DELETE | `/api/solicitacoes/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Excluir solicitação | IsAuthenticated |

### Ações de Aprovação (PA-01 a PA-07)

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| POST | `/api/solicitacoes/{id}/approve/` | ![Stable](https://img.shields.io/badge/-stable-green) | Aprovar solicitação SUPER | IsSuperintendencia |
| POST | `/api/solicitacoes/{id}/reject/` | ![Stable](https://img.shields.io/badge/-stable-green) | Reprovar solicitação SUPER | IsSuperintendencia |

### Filtros Disponíveis

```
?status=pendente|aprovado|reprovado
?projeto={id}
?municipio={id}
?usuario={id}
?data_inicio__gte=2025-01-01
?data_inicio__lte=2025-12-31
?ordering=-created_at
```

---

## 📅 Disponibilidade (RD-01 a RD-08)

### Verificação de Conflitos

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/availability/check/` | ![Stable](https://img.shields.io/badge/-stable-green) | Verificar conflitos (individual) | IsAuthenticated |
| POST | `/api/availability/check-many/` | ![Stable](https://img.shields.io/badge/-stable-green) | Verificar conflitos em lote | IsAuthenticated |
| GET | `/api/availability/monthly/` | ![Stable](https://img.shields.io/badge/-stable-green) | Grade mensal de disponibilidade | IsControleOrSuper |

### Parâmetros de Check

```
?usuario_id={id}        # Formador a verificar
?inicio=2025-01-15T09:00:00
?fim=2025-01-15T12:00:00
?municipio_id={id}      # Para cálculo de buffer (RD-04)
?exclude_id={id}        # Excluir solicitação específica
```

### Resposta de Conflito

```json
{
  "available": false,
  "conflicts": [
    {
      "code": "T",
      "title": "Bloqueio total",
      "detail": "Maria Silva - 15/01/2025 09:00-12:00",
      "ref_id": 123
    }
  ]
}
```

### Códigos de Conflito

| Código | Título | Descrição |
|--------|--------|-----------|
| X | Sobreposição | Evento conflita com outro aprovado |
| T | Bloqueio total | Formador bloqueado completamente |
| P | Bloqueio parcial | Subintervalo bloqueado |
| D | Deslocamento | Buffer de viagem insuficiente |
| M | Capacidade diária | Limite de horas/dia excedido |

### Bloqueios de Disponibilidade

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/availability/blocks/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar bloqueios | IsAuthenticated |
| POST | `/api/availability/blocks/` | ![Stable](https://img.shields.io/badge/-stable-green) | Criar bloqueio | IsAuthenticated |
| DELETE | `/api/availability/blocks/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Remover bloqueio | IsAuthenticated |

---

## 📆 Google Calendar (RF05/RF06)

### Preview e Publicação

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| POST | `/api/gcal/preview/` | ![Stable](https://img.shields.io/badge/-stable-green) | Preview do payload (dry-run) | IsControleOrSuper |
| POST | `/api/gcal/publish/` | ![Stable](https://img.shields.io/badge/-stable-green) | Publicar no Google Calendar | IsControleOrSuper |
| POST | `/api/gcal/publish-batch/` | ![Stable](https://img.shields.io/badge/-stable-green) | Publicar múltiplas solicitações | IsControleOrSuper |
| POST | `/api/gcal/resync/{id}/` | ![Beta](https://img.shields.io/badge/-beta-yellow) | Resincronizar evento | IsControleOrSuper |
| POST | `/api/gcal/cancel/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Cancelar evento no GCal | IsControleOrSuper |

### Dashboards e Métricas

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/gcal/dashboard/summary/` | ![Stable](https://img.shields.io/badge/-stable-green) | Resumo de publicações | IsControleOrSuper |
| GET | `/api/gcal/dashboard/pending/` | ![Stable](https://img.shields.io/badge/-stable-green) | Solicitações pendentes | IsControleOrSuper |
| GET | `/api/gcal/dashboard/errors/` | ![Stable](https://img.shields.io/badge/-stable-green) | Erros de publicação | IsControleOrSuper |
| GET | `/api/gcal/dashboard/insights/` | ![Beta](https://img.shields.io/badge/-beta-yellow) | Insights de uso | IsControleOrSuper |

### Calendários

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/gcal/calendars/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar calendários disponíveis | IsControleOrSuper |

### OAuth (por usuário)

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/gcal/oauth/status/` | ![Stable](https://img.shields.io/badge/-stable-green) | Status da conexão OAuth | IsAuthenticated |
| POST | `/api/gcal/oauth/authorize/` | ![Stable](https://img.shields.io/badge/-stable-green) | Iniciar fluxo OAuth | IsAuthenticated |
| POST | `/api/gcal/oauth/callback/` | ![Stable](https://img.shields.io/badge/-stable-green) | Callback do OAuth | IsAuthenticated |
| POST | `/api/gcal/oauth/revoke/` | ![Stable](https://img.shields.io/badge/-stable-green) | Revogar credenciais | IsAuthenticated |

---

## 🏢 Administração

### Usuários

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/usuarios-admin/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar usuários | IsDAT |
| POST | `/api/usuarios-admin/` | ![Stable](https://img.shields.io/badge/-stable-green) | Criar usuário | IsDAT |
| GET | `/api/usuarios-admin/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Detalhes do usuário | IsDAT |
| PATCH | `/api/usuarios-admin/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Atualizar usuário | IsDAT |

### Municípios

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/municipios/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar municípios | IsAuthenticated |
| POST | `/api/municipios/` | ![Stable](https://img.shields.io/badge/-stable-green) | Criar município | IsDAT |
| GET | `/api/municipios/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Detalhes do município | IsAuthenticated |
| PATCH | `/api/municipios/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Atualizar município | IsDAT |

### Projetos

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/projetos/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar projetos | IsAuthenticated |
| POST | `/api/projetos/` | ![Stable](https://img.shields.io/badge/-stable-green) | Criar projeto | IsDAT |
| GET | `/api/projetos/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Detalhes do projeto | IsAuthenticated |
| PATCH | `/api/projetos/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Atualizar projeto | IsDAT |

### Grupos (RBAC)

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/grupos/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar grupos Django | IsDAT |
| GET | `/api/grupos/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Detalhes do grupo | IsDAT |

### Tipos de Evento

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/tipos-evento/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar tipos de evento | IsAuthenticated |
| POST | `/api/tipos-evento/` | ![Stable](https://img.shields.io/badge/-stable-green) | Criar tipo de evento | IsDAT |

### Gerências

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/gerencias/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar gerências | IsAuthenticated |
| GET | `/api/gerencias/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Detalhes da gerência | IsAuthenticated |

---

## 📊 Módulo DAT

### Registros

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/dat/registros/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar registros DAT | IsDATOrSuper |
| POST | `/api/dat/registros/` | ![Stable](https://img.shields.io/badge/-stable-green) | Criar registro | IsDATOrSuper |
| GET | `/api/dat/registros/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Detalhes do registro | IsDATOrSuper |
| PATCH | `/api/dat/registros/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Atualizar registro | IsDATOrSuper |

### Ações

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/dat/acoes/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar ações DAT | IsDATOrSuper |
| POST | `/api/dat/acoes/` | ![Stable](https://img.shields.io/badge/-stable-green) | Criar ação | IsDATOrSuper |
| PATCH | `/api/dat/acoes/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Atualizar ação | IsDATOrSuper |

### Ciclos de Ação

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/dat/acoes-ciclo/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar ciclos de ação | IsDATOrSuper |

### Cadastros

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/dat/cadastros/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar cadastros | IsDATOrSuper |
| POST | `/api/dat/cadastros/` | ![Stable](https://img.shields.io/badge/-stable-green) | Criar cadastro | IsDATOrSuper |
| PATCH | `/api/dat/cadastros/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Atualizar cadastro | IsDATOrSuper |

### Compras DAT

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/dat/compras/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar compras | IsDATOrSuper |
| POST | `/api/dat/compras/` | ![Stable](https://img.shields.io/badge/-stable-green) | Registrar compra | IsDATOrSuper |
| PATCH | `/api/dat/compras/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Atualizar compra | IsDATOrSuper |

### Coordenadores DAT

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/dat/coordenadores/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar coordenadores | IsDATOrSuper |
| POST | `/api/dat/coordenadores/` | ![Stable](https://img.shields.io/badge/-stable-green) | Criar coordenador | IsDATOrSuper |

### Áreas DAT

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/dat/areas/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar áreas | IsDATOrSuper |
| POST | `/api/dat/areas/` | ![Stable](https://img.shields.io/badge/-stable-green) | Criar área | IsDATOrSuper |

---

## 📈 Métricas e Dashboards

### Mapa do Brasil

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/metrics/map/` | ![Stable](https://img.shields.io/badge/-stable-green) | Dados para mapa | IsAuthenticated |
| GET | `/api/metrics/map/summary/` | ![Stable](https://img.shields.io/badge/-stable-green) | Resumo por estado | IsAuthenticated |

### Métricas de Coordenadores

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/metrics/coordinators/` | ![Beta](https://img.shields.io/badge/-beta-yellow) | Métricas de coordenadores | IsControleOrSuper |
| GET | `/api/metrics/coordinators/{id}/` | ![Beta](https://img.shields.io/badge/-beta-yellow) | Métricas de coordenador específico | IsControleOrSuper |

### Qualidade de Dados

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/metrics/quality/` | ![Beta](https://img.shields.io/badge/-beta-yellow) | Indicadores de qualidade | IsControleOrSuper |

---

## 🔧 Options (Lookups)

Endpoints para popular dropdowns e selects no frontend.

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/options/municipios/` | ![Stable](https://img.shields.io/badge/-stable-green) | Lista simplificada de municípios | IsAuthenticated |
| GET | `/api/options/projetos/` | ![Stable](https://img.shields.io/badge/-stable-green) | Lista simplificada de projetos | IsAuthenticated |
| GET | `/api/options/usuarios/` | ![Stable](https://img.shields.io/badge/-stable-green) | Lista de usuários para select | IsAuthenticated |
| GET | `/api/options/formadores/` | ![Stable](https://img.shields.io/badge/-stable-green) | Lista de formadores | IsAuthenticated |
| GET | `/api/options/coordenadores/` | ![Stable](https://img.shields.io/badge/-stable-green) | Lista de coordenadores | IsAuthenticated |
| GET | `/api/options/tipos-evento/` | ![Stable](https://img.shields.io/badge/-stable-green) | Tipos de evento para select | IsAuthenticated |
| GET | `/api/options/gerencias/` | ![Stable](https://img.shields.io/badge/-stable-green) | Gerências para select | IsAuthenticated |

---

## ❤️ Health Checks

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/healthz/` | ![Stable](https://img.shields.io/badge/-stable-green) | Health check básico | AllowAny |
| GET | `/api/readyz/` | ![Stable](https://img.shields.io/badge/-stable-green) | Readiness (DB + Redis) | AllowAny |
| GET | `/api/features/` | ![Stable](https://img.shields.io/badge/-stable-green) | Feature flags ativas | AllowAny |
| GET | `/api/config/` | ![Stable](https://img.shields.io/badge/-stable-green) | Configurações públicas | IsAuthenticated |

---

## 🔐 Permissões

### Classes de Permissão

| Classe | Descrição | Grupos |
|--------|-----------|--------|
| `AllowAny` | Acesso público | - |
| `IsAuthenticated` | Usuário logado | Todos |
| `IsSuperintendencia` | Superintendência ou superuser | Superintendência |
| `IsControleOrSuper` | Controle ou Superintendência | Controle, Superintendência |
| `IsDATOrSuper` | DAT ou Superintendência | DAT, Superintendência |
| `IsDAT` | Apenas DAT | DAT |

### Regra de Aprovação SUPER

```python
can_approve_super = is_superuser OR (
    "Gerente" IN funcoes AND "Superintendência" IN setores
)
```

---

## 📄 Paginação

Todos os endpoints de listagem usam paginação padrão.

### Request

```
GET /api/solicitacoes/?page=1&page_size=20
```

### Response

```json
{
  "count": 150,
  "next": "http://api/solicitacoes/?page=2",
  "previous": null,
  "results": [...]
}
```

---

## ⚠️ Erros

### Códigos HTTP

| Código | Significado |
|--------|-------------|
| 200 | Sucesso |
| 201 | Criado com sucesso |
| 202 | Aceito (processamento assíncrono) |
| 400 | Erro de validação |
| 401 | Não autenticado |
| 403 | Sem permissão |
| 404 | Não encontrado |
| 409 | Conflito (ex: evento já publicado) |
| 429 | Rate limit excedido |
| 500 | Erro interno |

### Formato de Erro

```json
{
  "detail": "Você não tem permissão para executar esta ação.",
  "code": "permission_denied"
}
```

### Erros de Validação

```json
{
  "field_name": ["Mensagem de erro 1", "Mensagem de erro 2"],
  "non_field_errors": ["Erro geral"]
}
```

---

## 🚀 Rate Limiting

| Escopo | Limite | Descrição |
|--------|--------|-----------|
| `anon` | 100/hour | Usuários não autenticados |
| `user` | 1000/hour | Usuários autenticados |
| `availability_check` | 60/min | Verificação de conflitos |

**Nota**: Em desenvolvimento, limites são 10x mais permissivos.

---

## 📚 Documentação Swagger

Quando habilitado (drf-spectacular):

| URL | Descrição |
|-----|-----------|
| `/api/schema/` | OpenAPI 3.0 Schema (JSON/YAML) |
| `/api/docs/` | Swagger UI interativo |
| `/api/redoc/` | ReDoc (alternativa) |

---

**Mantido por**: Claude Code + Equipe AS v2
