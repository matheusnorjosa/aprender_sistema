# 📡 API Reference — Aprender Sistema v2

**Última Atualização**: 2026-01-13
**Total de Endpoints**: 87+
**ViewSets**: 26

---

## 🔐 Autenticação

Todos os endpoints (exceto `/auth/` e `/csrf/`) requerem autenticação via session cookie.

### Endpoints de Auth

| Método | Endpoint | Descrição | Permissão |
|--------|----------|-----------|-----------|
| POST | `/auth/login/` | Login com username/password | AllowAny |
| POST | `/auth/logout/` | Logout e invalidação de sessão | IsAuthenticated |
| GET | `/csrf/` | Obter CSRF token | AllowAny |
| GET | `/api/ping/` | Health check simples | AllowAny |
| GET | `/api/me/` | Dados do usuário logado + RBAC | IsAuthenticated |

### Headers Obrigatórios

```http
Content-Type: application/json
X-CSRFToken: <csrf_token>
Cookie: sessionid=<session_id>
```

---

## 📋 Solicitações

### CRUD Principal

| Método | Endpoint | Descrição | Permissão |
|--------|----------|-----------|-----------|
| GET | `/api/solicitacoes/` | Listar solicitações (paginado) | IsAuthenticated |
| POST | `/api/solicitacoes/` | Criar nova solicitação | IsAuthenticated |
| GET | `/api/solicitacoes/{id}/` | Detalhes de uma solicitação | IsAuthenticated |
| PUT | `/api/solicitacoes/{id}/` | Atualizar solicitação completa | IsAuthenticated |
| PATCH | `/api/solicitacoes/{id}/` | Atualizar parcialmente | IsAuthenticated |
| DELETE | `/api/solicitacoes/{id}/` | Excluir solicitação | IsAuthenticated |

### Ações de Aprovação (PA-01 a PA-07)

| Método | Endpoint | Descrição | Permissão |
|--------|----------|-----------|-----------|
| POST | `/api/solicitacoes/{id}/approve/` | Aprovar solicitação SUPER | IsSuperintendencia |
| POST | `/api/solicitacoes/{id}/reject/` | Reprovar solicitação SUPER | IsSuperintendencia |

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

| Método | Endpoint | Descrição | Permissão |
|--------|----------|-----------|-----------|
| GET | `/api/availability/check/` | Verificar conflitos (individual) | IsAuthenticated |
| POST | `/api/availability/check-many/` | Verificar conflitos em lote | IsAuthenticated |
| GET | `/api/availability/monthly/` | Grade mensal de disponibilidade | IsControleOrSuper |

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

| Método | Endpoint | Descrição | Permissão |
|--------|----------|-----------|-----------|
| GET | `/api/availability/blocks/` | Listar bloqueios | IsAuthenticated |
| POST | `/api/availability/blocks/` | Criar bloqueio | IsAuthenticated |
| DELETE | `/api/availability/blocks/{id}/` | Remover bloqueio | IsAuthenticated |

---

## 📆 Google Calendar (RF05/RF06)

### Preview e Publicação

| Método | Endpoint | Descrição | Permissão |
|--------|----------|-----------|-----------|
| POST | `/api/gcal/preview/` | Preview do payload (dry-run) | IsControleOrSuper |
| POST | `/api/gcal/publish/` | Publicar no Google Calendar | IsControleOrSuper |
| POST | `/api/gcal/publish-batch/` | Publicar múltiplas solicitações | IsControleOrSuper |
| POST | `/api/gcal/resync/{id}/` | Resincronizar evento | IsControleOrSuper |
| POST | `/api/gcal/cancel/{id}/` | Cancelar evento no GCal | IsControleOrSuper |

### Dashboards e Métricas

| Método | Endpoint | Descrição | Permissão |
|--------|----------|-----------|-----------|
| GET | `/api/gcal/dashboard/summary/` | Resumo de publicações | IsControleOrSuper |
| GET | `/api/gcal/dashboard/pending/` | Solicitações pendentes | IsControleOrSuper |
| GET | `/api/gcal/dashboard/errors/` | Erros de publicação | IsControleOrSuper |
| GET | `/api/gcal/dashboard/insights/` | Insights de uso | IsControleOrSuper |

### Calendários

| Método | Endpoint | Descrição | Permissão |
|--------|----------|-----------|-----------|
| GET | `/api/gcal/calendars/` | Listar calendários disponíveis | IsControleOrSuper |

### OAuth (por usuário)

| Método | Endpoint | Descrição | Permissão |
|--------|----------|-----------|-----------|
| GET | `/api/gcal/oauth/status/` | Status da conexão OAuth | IsAuthenticated |
| POST | `/api/gcal/oauth/authorize/` | Iniciar fluxo OAuth | IsAuthenticated |
| POST | `/api/gcal/oauth/callback/` | Callback do OAuth | IsAuthenticated |
| POST | `/api/gcal/oauth/revoke/` | Revogar credenciais | IsAuthenticated |

---

## 🏢 Administração

### Usuários

| Método | Endpoint | Descrição | Permissão |
|--------|----------|-----------|-----------|
| GET | `/api/usuarios-admin/` | Listar usuários | IsDAT |
| POST | `/api/usuarios-admin/` | Criar usuário | IsDAT |
| GET | `/api/usuarios-admin/{id}/` | Detalhes do usuário | IsDAT |
| PATCH | `/api/usuarios-admin/{id}/` | Atualizar usuário | IsDAT |

### Municípios

| Método | Endpoint | Descrição | Permissão |
|--------|----------|-----------|-----------|
| GET | `/api/municipios/` | Listar municípios | IsAuthenticated |
| POST | `/api/municipios/` | Criar município | IsDAT |
| GET | `/api/municipios/{id}/` | Detalhes do município | IsAuthenticated |
| PATCH | `/api/municipios/{id}/` | Atualizar município | IsDAT |

### Projetos

| Método | Endpoint | Descrição | Permissão |
|--------|----------|-----------|-----------|
| GET | `/api/projetos/` | Listar projetos | IsAuthenticated |
| POST | `/api/projetos/` | Criar projeto | IsDAT |
| GET | `/api/projetos/{id}/` | Detalhes do projeto | IsAuthenticated |
| PATCH | `/api/projetos/{id}/` | Atualizar projeto | IsDAT |

### Grupos (RBAC)

| Método | Endpoint | Descrição | Permissão |
|--------|----------|-----------|-----------|
| GET | `/api/grupos/` | Listar grupos Django | IsDAT |
| GET | `/api/grupos/{id}/` | Detalhes do grupo | IsDAT |

### Tipos de Evento

| Método | Endpoint | Descrição | Permissão |
|--------|----------|-----------|-----------|
| GET | `/api/tipos-evento/` | Listar tipos de evento | IsAuthenticated |
| POST | `/api/tipos-evento/` | Criar tipo de evento | IsDAT |

### Gerências

| Método | Endpoint | Descrição | Permissão |
|--------|----------|-----------|-----------|
| GET | `/api/gerencias/` | Listar gerências | IsAuthenticated |
| GET | `/api/gerencias/{id}/` | Detalhes da gerência | IsAuthenticated |

---

## 📊 Módulo DAT

### Registros

| Método | Endpoint | Descrição | Permissão |
|--------|----------|-----------|-----------|
| GET | `/api/dat/registros/` | Listar registros DAT | IsDATOrSuper |
| POST | `/api/dat/registros/` | Criar registro | IsDATOrSuper |
| GET | `/api/dat/registros/{id}/` | Detalhes do registro | IsDATOrSuper |
| PATCH | `/api/dat/registros/{id}/` | Atualizar registro | IsDATOrSuper |

### Ações

| Método | Endpoint | Descrição | Permissão |
|--------|----------|-----------|-----------|
| GET | `/api/dat/acoes/` | Listar ações DAT | IsDATOrSuper |
| POST | `/api/dat/acoes/` | Criar ação | IsDATOrSuper |
| PATCH | `/api/dat/acoes/{id}/` | Atualizar ação | IsDATOrSuper |

### Ciclos de Ação

| Método | Endpoint | Descrição | Permissão |
|--------|----------|-----------|-----------|
| GET | `/api/dat/acoes-ciclo/` | Listar ciclos de ação | IsDATOrSuper |

### Cadastros

| Método | Endpoint | Descrição | Permissão |
|--------|----------|-----------|-----------|
| GET | `/api/dat/cadastros/` | Listar cadastros | IsDATOrSuper |
| POST | `/api/dat/cadastros/` | Criar cadastro | IsDATOrSuper |
| PATCH | `/api/dat/cadastros/{id}/` | Atualizar cadastro | IsDATOrSuper |

### Compras DAT

| Método | Endpoint | Descrição | Permissão |
|--------|----------|-----------|-----------|
| GET | `/api/dat/compras/` | Listar compras | IsDATOrSuper |
| POST | `/api/dat/compras/` | Registrar compra | IsDATOrSuper |
| PATCH | `/api/dat/compras/{id}/` | Atualizar compra | IsDATOrSuper |

### Coordenadores DAT

| Método | Endpoint | Descrição | Permissão |
|--------|----------|-----------|-----------|
| GET | `/api/dat/coordenadores/` | Listar coordenadores | IsDATOrSuper |
| POST | `/api/dat/coordenadores/` | Criar coordenador | IsDATOrSuper |

### Áreas DAT

| Método | Endpoint | Descrição | Permissão |
|--------|----------|-----------|-----------|
| GET | `/api/dat/areas/` | Listar áreas | IsDATOrSuper |
| POST | `/api/dat/areas/` | Criar área | IsDATOrSuper |

---

## 📈 Métricas e Dashboards

### Mapa do Brasil

| Método | Endpoint | Descrição | Permissão |
|--------|----------|-----------|-----------|
| GET | `/api/metrics/map/` | Dados para mapa | IsAuthenticated |
| GET | `/api/metrics/map/summary/` | Resumo por estado | IsAuthenticated |

### Métricas de Coordenadores

| Método | Endpoint | Descrição | Permissão |
|--------|----------|-----------|-----------|
| GET | `/api/metrics/coordinators/` | Métricas de coordenadores | IsControleOrSuper |
| GET | `/api/metrics/coordinators/{id}/` | Métricas de coordenador específico | IsControleOrSuper |

### Qualidade de Dados

| Método | Endpoint | Descrição | Permissão |
|--------|----------|-----------|-----------|
| GET | `/api/metrics/quality/` | Indicadores de qualidade | IsControleOrSuper |

---

## 🔧 Options (Lookups)

Endpoints para popular dropdowns e selects no frontend.

| Método | Endpoint | Descrição | Permissão |
|--------|----------|-----------|-----------|
| GET | `/api/options/municipios/` | Lista simplificada de municípios | IsAuthenticated |
| GET | `/api/options/projetos/` | Lista simplificada de projetos | IsAuthenticated |
| GET | `/api/options/usuarios/` | Lista de usuários para select | IsAuthenticated |
| GET | `/api/options/formadores/` | Lista de formadores | IsAuthenticated |
| GET | `/api/options/coordenadores/` | Lista de coordenadores | IsAuthenticated |
| GET | `/api/options/tipos-evento/` | Tipos de evento para select | IsAuthenticated |
| GET | `/api/options/gerencias/` | Gerências para select | IsAuthenticated |

---

## ❤️ Health Checks

| Método | Endpoint | Descrição | Permissão |
|--------|----------|-----------|-----------|
| GET | `/api/healthz/` | Health check básico | AllowAny |
| GET | `/api/readyz/` | Readiness (DB + Redis) | AllowAny |
| GET | `/api/features/` | Feature flags ativas | AllowAny |
| GET | `/api/config/` | Configurações públicas | IsAuthenticated |

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
