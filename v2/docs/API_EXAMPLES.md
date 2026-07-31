# API Examples - Aprender Sistema v2

**Ultima verificacao contra o codigo**: 2026-07-24

Exemplos práticos de uso da API para desenvolvedores.
Contrato completo em [API_REFERENCE.md](API_REFERENCE.md); inventario executavel
de rotas em `/api/schema/`.

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

O `username` do sistema e o **CPF** (somente digitos).

**Resposta (`views_auth.py:302-316`):**
```json
{
  "id": 1,
  "username": "11144477735",
  "email": "admin@example.com",
  "name": "Maria Silva",
  "first_name": "Maria",
  "last_name": "Silva",
  "is_superuser": true,
  "is_staff": true,
  "groups": ["DAT", "Coordenador"],
  "is_superintendencia": true
}
```

A chave e `groups` (nao `grupos`), e o login **nao** retorna `setores` — a
separacao Setor/Funcao so aparece em `GET /api/me/`.

### 3. Verificar Sessao

```bash
curl -s http://localhost:8000/api/me/ \
  -b cookies.txt | jq
```

---

## Solicitacoes

O modelo `Solicitacao` **nao tem campo `titulo`** (`models/solicitacao.py:22-97`).
Um `titulo` enviado no corpo e descartado em silencio pelo `ModelSerializer`.
Campos gravaveis: `municipio`, `projeto`, `tipo_evento`, `tipo`, `encontro`,
`segmento`, `coordenador`, `coordenador_acompanha`, `inicio`, `fim`,
`observacoes`, `local`, `is_online` (`serializers/solicitacao.py:59-112`).
`usuario` e `status` sao read-only — o backend os define.

Criar exige a capability `create_solicitation` (`views_solicitacao.py:179-180`).

### Criar Solicitacao Presencial

```bash
curl -X POST http://localhost:8000/api/solicitacoes/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF" \
  -b cookies.txt \
  -d '{
    "inicio": "2026-01-20T09:00:00-03:00",
    "fim": "2026-01-20T12:00:00-03:00",
    "municipio": 1,
    "projeto": 1,
    "tipo_evento": 1,
    "is_online": false,
    "local": "Sala 101",
    "observacoes": "Formacao Fundamental I"
  }'
```

**Resposta (201)** — relacoes saem como **ID** mais um campo `*_nome`
espelhado, nao como objetos aninhados:
```json
{
  "id": 123,
  "status": "pendente",
  "fluxo": "SUPER",
  "gcal_status": "NONE",
  "inicio": "2026-01-20T09:00:00-03:00",
  "fim": "2026-01-20T12:00:00-03:00",
  "is_online": false,
  "local": "Sala 101",
  "usuario": 1,
  "usuario_username": "11144477735",
  "municipio": 1,
  "municipio_nome": "Fortaleza",
  "projeto": 1,
  "projeto_nome": "Vidas",
  "tipo_evento": 1,
  "tipo_evento_nome": "Formacao",
  "participations": [],
  "meet_link": null
}
```

> **`status` inicial depende do projeto**: `projeto.fluxo == "NAO_SUPER"` nasce
> `"aprovado"`; qualquer outro caso nasce `"pendente"`
> (`services/solicitacao_create.py:27-44`). Nao assuma `"pendente"`.

### Criar Solicitacao Online

```bash
curl -X POST http://localhost:8000/api/solicitacoes/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF" \
  -b cookies.txt \
  -d '{
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

# Busca textual (SearchFilter)
curl -s "http://localhost:8000/api/solicitacoes/?search=fortaleza" \
  -b cookies.txt | jq

# Busca ampla manual (municipio/projeto/tipo/observacoes/usuario)
curl -s "http://localhost:8000/api/solicitacoes/?q=fortaleza" \
  -b cookies.txt | jq

# Janela de datas + fluxo
curl -s "http://localhost:8000/api/solicitacoes/?date_from=2026-01-01&date_to=2026-01-31&flow=SUPER" \
  -b cookies.txt | jq

# Paginacao: page_size e IGNORADO nesta rota (paginador global sem
# page_size_query_param, settings.py:485-486). Pagina fixa em 100.
curl -s "http://localhost:8000/api/solicitacoes/?page=2" \
  -b cookies.txt | jq
```

### Aprovar Solicitacao (PA-02)

O metodo e **PATCH**, nao POST (`views_solicitacao.py:629-634`). POST retorna 405.

```bash
curl -X PATCH http://localhost:8000/api/solicitacoes/123/approve/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF" \
  -b cookies.txt \
  -d '{"reason": "Agenda confirmada com o municipio"}'
```

**Resposta (200):**
```json
{
  "detail": "Solicitacao aprovada com sucesso.",
  "solicitacao": { "id": 123, "status": "aprovado", "...": "demais campos do SolicitacaoSerializer" }
}
```

### Reprovar Solicitacao

Tambem **PATCH** (`views_solicitacao.py:671-676`). A justificativa vai em
`reason` (alias aceito: `justificativa`) — **nao** em `motivo`.

```bash
curl -X PATCH http://localhost:8000/api/solicitacoes/123/reject/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF" \
  -b cookies.txt \
  -d '{
    "reason": "Data indisponivel para o formador"
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

**Resposta (200)** — a chave de cada erro e `detail`, nao `error`
(`services/solicitacao_approval.py:96-98`, `:307`):
```json
{
  "approved": 3,
  "errors": [
    {"id": 4, "detail": "Status ja e 'aprovado'"},
    {"id": 5, "detail": "Conflito de disponibilidade para o participante X"}
  ]
}
```

`ids` vazio retorna **400** (`code: ids_required`); acima de 100 itens retorna
400 (`code: batch_limit_exceeded`). Existe tambem
`POST /api/solicitacoes/batch-reject/` com o mesmo contrato, devolvendo
`{"rejected": N, "errors": [...]}`.

---

## Disponibilidade (RD-01~08)

### Verificar Disponibilidade (individual)

E **GET com query params**, nao POST com corpo. O parametro e `usuario_id`
(nao `formador_id`) — `views_availability.py:263-278`.

```bash
curl -s -G http://localhost:8000/api/availability/check/ \
  -b cookies.txt \
  --data-urlencode "usuario_id=1" \
  --data-urlencode "inicio=2026-01-20T09:00:00-03:00" \
  --data-urlencode "fim=2026-01-20T12:00:00-03:00" \
  --data-urlencode "municipio_id=1" | jq
```

**Resposta (disponivel)** — objeto plano, chave `ok` (nao `available`), sem
envelope `data`/`meta` (`views_availability.py:341-347`):
```json
{
  "ok": true,
  "conflicts": []
}
```

**Resposta (com conflitos)** — cada conflito tem `code`/`title`/`detail`/`ref_id`
(`services/availability_service.py:35-49`):
```json
{
  "ok": false,
  "conflicts": [
    {
      "code": "X",
      "title": "Sobreposicao",
      "detail": "Conflita com evento aprovado #88 (20/01/2026 09:00-12:00)",
      "ref_id": 88
    }
  ]
}
```

### Verificar Disponibilidade (lote)

```bash
curl -X POST http://localhost:8000/api/availability/check-many/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF" \
  -b cookies.txt \
  -d '{
    "usuarios_ids": [1, 2],
    "inicio": "2026-01-20T09:00:00-03:00",
    "fim": "2026-01-20T12:00:00-03:00",
    "municipio_id": 1
  }'
```

A chave e `usuarios_ids` (`views_availability.py:382`). Lista vazia => 400.

### Grade Mensal

`role` e **obrigatorio** (`FORMADOR` ou `COORDENADOR`); sem ele a resposta e 400
(`views_availability_monthly.py:153-158`). Nao existe `formador_id` nesta rota —
o recorte por pessoa e feito por `gerencia_id`/`sector`/`q`.

```bash
curl -s "http://localhost:8000/api/availability/monthly/?year=2026&month=1&role=FORMADOR" \
  -b cookies.txt | jq
```

### Bloqueios de Disponibilidade

A rota e `/api/availability-blocks/` (nao `/api/availability/blocks/`).

```bash
curl -s http://localhost:8000/api/availability-blocks/ -b cookies.txt | jq
```

---

## Google Calendar

Todas as rotas abaixo exigem a policy `use_gcal` (`CanUseGcal`).

### Preview antes de Publicar

E **POST**, nao GET (`views_solicitacao.py:698-704`).

```bash
curl -X POST http://localhost:8000/api/solicitacoes/123/preview-gcal/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF" \
  -b cookies.txt | jq
```

Resposta 200: `{"detail": "...", "preview": { ... }}`.

### Publicar no Google Calendar

```bash
curl -X POST http://localhost:8000/api/solicitacoes/123/publish/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF" \
  -b cookies.txt \
  -d '{"dry_run": false, "apply_blocked": false}'
```

Resposta **202 Accepted** (processamento via Celery):
`{"detail": "...", "task_id": "...", "solicitacao_id": 123}`.

Relacionadas, mesmo contrato 202:
`POST /api/solicitacoes/{id}/resync-gcal/` e
`POST /api/solicitacoes/{id}/cancel-gcal/`.

### Publicar em Lote

A chave e **`solicitacao_ids`**, nao `ids` — `ids` resulta em
`400 {"detail": "solicitacao_ids deve ser um array nao-vazio de IDs"}`
(`views_gcal/batch.py:82-90`). Limite: 500 por requisicao.

```bash
curl -X POST http://localhost:8000/api/gcal/publish-batch/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF" \
  -b cookies.txt \
  -d '{
    "solicitacao_ids": [1, 2, 3],
    "dry_run": false,
    "apply_blocked": false
  }'
```

Resposta 202:
`{"queued": 2, "errors": [{"id": 3, "detail": "..."}], "dry_run": false, "apply_blocked": false}`.

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

O `custom_exception_handler` devolve um objeto **plano** com `detail` + `code`
(+ `errors` quando ha erro de campo). Nao existe envelope `error`, nem
`message`, nem `request_id` na resposta — `apps/core/exceptions.py:162-281`.

```json
{
  "detail": "Erro de validacao.",
  "code": "INVALID",
  "errors": {
    "inicio": ["Este campo e obrigatorio."]
  }
}
```

### Codigos de Erro Comuns

`code` vem de `_get_error_code` (`exceptions.py:284-305`): para excecoes do DRF e
o `default_code` em MAIUSCULAS (por isso o `ValidationError` do serializer vira
`INVALID`, nao `VALIDATION_ERROR`).

| Codigo | HTTP | Descricao |
|--------|------|-----------|
| `INVALID` | 400 | Dados invalidos (serializer DRF) |
| `VALIDATION_ERROR` | 400 | `ValidationError` do Django (nao-DRF) |
| `NOT_AUTHENTICATED` | 401 | Autenticacao necessaria |
| `PERMISSION_DENIED` | 403 | Sem permissao |
| `NOT_FOUND` | 404 | Recurso nao encontrado |
| `METHOD_NOT_ALLOWED` | 405 | Metodo errado (ex.: POST em `approve/`) |
| `THROTTLED` | 429 | Limite de requisicoes |

Erros de negocio levantados por `APIError` trazem o `code` proprio do dominio
(ex.: `ids_required`, `batch_limit_exceeded`).

---

## Swagger UI Interativo

Acesse `/api/docs/` para testar endpoints interativamente com "Try it out".

## OpenAPI Schema

```bash
curl -s http://localhost:8000/api/schema/ -o openapi.json
```

