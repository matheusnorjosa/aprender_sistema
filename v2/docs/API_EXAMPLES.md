# API Examples - Aprender Sistema v2

Exemplos práticos de uso da API para desenvolvedores.

## Autenticacao

### 1. Obter CSRF Token

```bash
# Obter token CSRF necessario para requests POST/PUT/DELETE
curl -s http://localhost:8000/api/csrf/ | jq
```

**Resposta:**
```json
{
  "csrfToken": "abc123..."
}
```

### 2. Login

```bash
CSRF=$(curl -s http://localhost:8000/api/csrf/ | jq -r '.csrfToken')

curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF" \
  -c cookies.txt \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'
```

**Resposta:**
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "grupos": ["DAT", "Coordenador"],
  "setores": ["Superintendencia"],
  "is_superuser": true
}
```

### 3. Verificar Sessao

```bash
curl -s http://localhost:8000/api/me/ \
  -b cookies.txt | jq
```

---

## Solicitacoes

### Criar Solicitacao Presencial

```bash
curl -X POST http://localhost:8000/api/solicitacoes/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF" \
  -b cookies.txt \
  -d '{
    "titulo": "Formacao Fundamental I",
    "inicio": "2026-01-20T09:00:00-03:00",
    "fim": "2026-01-20T12:00:00-03:00",
    "municipio": 1,
    "projeto": 1,
    "tipo_evento": 1,
    "is_online": false,
    "observacoes": "Sala 101"
  }'
```

**Resposta (201):**
```json
{
  "id": 123,
  "titulo": "Formacao Fundamental I",
  "status": "pendente",
  "gcal_status": "NONE",
  "inicio": "2026-01-20T09:00:00-03:00",
  "fim": "2026-01-20T12:00:00-03:00",
  "is_online": false,
  "usuario": {"id": 1, "nome": "Maria Silva"},
  "municipio": {"id": 1, "nome": "Fortaleza"},
  "projeto": {"id": 1, "nome": "Vidas"},
  "tipo_evento": {"id": 1, "nome": "Formacao"}
}
```

### Criar Solicitacao Online

```bash
curl -X POST http://localhost:8000/api/solicitacoes/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF" \
  -b cookies.txt \
  -d '{
    "titulo": "Formacao Online - Fluir",
    "inicio": "2026-01-20T14:00:00-03:00",
    "fim": "2026-01-20T16:00:00-03:00",
    "projeto": 2,
    "tipo_evento": 1,
    "is_online": true,
    "observacoes": "Link Meet sera gerado automaticamente"
  }'
```

### Listar Solicitacoes com Filtros

```bash
# Minhas solicitacoes pendentes
curl -s "http://localhost:8000/api/solicitacoes/?mine=true&status=pendente" \
  -b cookies.txt | jq

# Busca textual
curl -s "http://localhost:8000/api/solicitacoes/?search=fortaleza" \
  -b cookies.txt | jq

# Paginacao
curl -s "http://localhost:8000/api/solicitacoes/?page=2&page_size=20" \
  -b cookies.txt | jq
```

### Aprovar Solicitacao (PA-02)

```bash
curl -X POST http://localhost:8000/api/solicitacoes/123/approve/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF" \
  -b cookies.txt
```

**Resposta (200):**
```json
{
  "detail": "Solicitacao aprovada com sucesso",
  "status": "aprovado"
}
```

### Reprovar Solicitacao

```bash
curl -X POST http://localhost:8000/api/solicitacoes/123/reject/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF" \
  -b cookies.txt \
  -d '{
    "motivo": "Data indisponivel para o formador"
  }'
```

### Aprovar em Lote

```bash
curl -X POST http://localhost:8000/api/solicitacoes/batch-approve/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF" \
  -b cookies.txt \
  -d '{
    "ids": [1, 2, 3, 4, 5]
  }'
```

**Resposta (200):**
```json
{
  "approved": 3,
  "errors": [
    {"id": 4, "error": "Solicitacao ja aprovada"},
    {"id": 5, "error": "Conflito de disponibilidade"}
  ]
}
```

---

## Disponibilidade (RD-01~08)

### Verificar Disponibilidade

```bash
curl -X POST http://localhost:8000/api/availability/check/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF" \
  -b cookies.txt \
  -d '{
    "formador_id": 1,
    "inicio": "2026-01-20T09:00:00-03:00",
    "fim": "2026-01-20T12:00:00-03:00",
    "municipio_id": 1
  }'
```

**Resposta (disponivel):**
```json
{
  "data": {
    "available": true,
    "conflicts": []
  },
  "meta": {
    "timestamp": "2026-01-16T10:30:00Z"
  }
}
```

**Resposta (com conflitos):**
```json
{
  "data": {
    "available": false,
    "conflicts": [
      {
        "type": "overlap",
        "formador_id": 1,
        "formador_nome": "Joao Silva",
        "start": "2026-01-20T09:00:00Z",
        "end": "2026-01-20T12:00:00Z",
        "reason": "Evento ja agendado"
      }
    ]
  }
}
```

### Grade Mensal

```bash
curl -s "http://localhost:8000/api/availability/monthly/?year=2026&month=1&formador_id=1" \
  -b cookies.txt | jq
```

---

## Google Calendar

### Preview antes de Publicar

```bash
curl -s http://localhost:8000/api/solicitacoes/123/preview-gcal/ \
  -b cookies.txt | jq
```

### Publicar no Google Calendar

```bash
curl -X POST http://localhost:8000/api/solicitacoes/123/publish/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF" \
  -b cookies.txt
```

### Publicar em Lote

```bash
curl -X POST http://localhost:8000/api/gcal/publish-batch/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF" \
  -b cookies.txt \
  -d '{
    "ids": [1, 2, 3]
  }'
```

---

## Options (para formularios)

### Listar Municipios

```bash
curl -s http://localhost:8000/api/options/municipios/ \
  -b cookies.txt | jq
```

### Listar Projetos

```bash
curl -s http://localhost:8000/api/options/projetos/ \
  -b cookies.txt | jq
```

### Listar Tipos de Evento

```bash
curl -s http://localhost:8000/api/options/tipos-evento/ \
  -b cookies.txt | jq
```

---

## Tratamento de Erros

### Formato Padrao de Erro

Todos os erros seguem o formato:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Erro de validacao nos dados enviados",
    "details": {
      "fields": {
        "inicio": ["Este campo e obrigatorio"]
      }
    },
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### Codigos de Erro Comuns

| Codigo | HTTP | Descricao |
|--------|------|-----------|
| `VALIDATION_ERROR` | 400 | Dados invalidos |
| `UNAUTHORIZED` | 401 | Autenticacao necessaria |
| `FORBIDDEN` | 403 | Sem permissao |
| `NOT_FOUND` | 404 | Recurso nao encontrado |
| `CONFLICT` | 409 | Conflito de disponibilidade |
| `RATE_LIMITED` | 429 | Limite de requisicoes |
| `SERVICE_UNAVAILABLE` | 503 | Servico externo indisponivel |

---

## Swagger UI Interativo

Acesse `/api/docs/` para testar endpoints interativamente com "Try it out".

## OpenAPI Schema

```bash
curl -s http://localhost:8000/api/schema/ -o openapi.json
```

