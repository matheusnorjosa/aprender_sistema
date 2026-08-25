# 📡 API Reference — Aprender Sistema v2

**Última Atualização**: 2026-07-24 (varredura de veracidade contra o código)
**Base canônica**: `/api`
**ViewSets registrados no router**: 24 (`v2/backend/apps/core/urls.py:118-156`)
**Contagem total de endpoints**: não re-derivada nesta varredura — a fonte
executável é o schema OpenAPI em `/api/schema/`.

> Esta referência é **curada**, não gerada. Ela cobre os endpoints de uso
> corrente; não é a lista exaustiva de rotas. Para o inventário completo e
> sempre atualizado, use `/api/schema/` (drf-spectacular).
> Para "quem pode o quê", o SSOT é [rbac_authorization_matrix.md](rbac_authorization_matrix.md);
> aqui registramos apenas a **permission class / capability** que cada rota exige.

> **Legenda de Status**: ![Stable](https://img.shields.io/badge/-stable-green) Estável | ![Beta](https://img.shields.io/badge/-beta-yellow) Beta | ![Deprecated](https://img.shields.io/badge/-deprecated-red) Deprecated | ![Internal](https://img.shields.io/badge/-internal-gray) Interno

---

## Status dos Endpoints (badges)

| Badge | Significado | Uso |
|-------|-------------|-----|
| **Stable** (verde) | Endpoint estável, sem mudanças planejadas | Maioria dos endpoints |
| **Beta** (amarelo) | Pode mudar sem aviso prévio | Features novas |
| **Deprecated** (vermelho) | Será removido na próxima versão | Endpoints antigos |
| **Internal** (cinza) | Uso interno, não documentado publicamente | Admin tools |

### Critérios de classificação

#### Stable

- Endpoint em produção há mais de 30 dias
- Contrato de API não mudou nas últimas 3 releases
- Cobertura de testes > 80%

#### Beta

- Feature nova ou experimental
- Pode ter breaking changes sem deprecation period
- Feedback de usuários ainda sendo coletado

#### Deprecated

- Será removido em versão futura
- Alternativa documentada disponível
- Período de deprecation: mínimo 1 release

#### Internal

- Uso apenas por ferramentas internas
- Não coberto por garantias de estabilidade
- Pode mudar a qualquer momento

---

## 🧭 Política Canônica de Rotas

- **Base path canônico oficial**: `/api/`
- **Alias deprecated**: `/api/v1/` (retorna headers `Deprecation: true` + `Sunset`)

Regras:

- Toda documentação nova deve usar `/api/*`.
- Todo código novo (frontend/backend/tests/scripts) deve usar `/api/*`.
- CI bloqueia novas referências a `/api/v1/` fora do allowlist (#796).
- `/api/v1/*` existe apenas para compatibilidade e será removido após a janela de deprecação.

### Plano de corte do `/api/v1/` (#797)

| Fase | Data | Ação |
|------|------|------|
| Deprecation headers | 2026-04-15 | Headers RFC 8594 em todas as respostas `/api/v1/` |
| CI guard rail | 2026-04-15 | Bloqueia novo código com `/api/v1/` |
| Service worker migrado | 2026-04-15 | SW usa `/api/` (cache v3 força refresh) |
| Monitoramento | 2026-04-15 a 2026-06-14 | Observar se há tráfego residual em `/api/v1/` |
| Remoção do alias | Após 2026-06-14 | Remover `path("api/v1/", ...)` de `config/urls.py` |

**Estado em 2026-07-24**: o alias **ainda existe** — `v2/backend/config/urls.py:110`
mantém `path("api/v1/", include("apps.core.urls", namespace="core-v1"))`. A última
linha do plano acima está pendente.

Observação:

- Quando um endpoint aparecer como `/alguma-rota/` nesta referência, ele é relativo ao base path canônico (`/api/alguma-rota/`).

---

## 🔐 Autenticação

Autenticação é por **session cookie**. Os únicos endpoints `AllowAny` sob `/api/`
são `/auth/login/`, `/csrf/`, `/readyz/` e `/version/`. Todo o resto exige sessão
autenticada — e a maior parte exige, além disso, uma **capability**.
Atenção: `/auth/ping/` e `/api/features/` **não** são públicos (ver as seções
correspondentes).

### Endpoints de Auth

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| POST | `/auth/login/` | ![Stable](https://img.shields.io/badge/-stable-green) | Login com `username` (CPF) + `password` | AllowAny |
| POST | `/auth/logout/` | ![Stable](https://img.shields.io/badge/-stable-green) | Logout e invalidação de sessão | IsAuthenticated |
| GET | `/csrf/` | ![Stable](https://img.shields.io/badge/-stable-green) | Obter CSRF token | AllowAny |
| POST | `/auth/ping/` | ![Stable](https://img.shields.io/badge/-stable-green) | Keep-alive de sessão (CP5) | IsAuthenticated |
| GET | `/me/` | ![Stable](https://img.shields.io/badge/-stable-green) | Dados do usuário logado + RBAC | IsAuthenticated |
| GET | `/me/policies/` | ![Stable](https://img.shields.io/badge/-stable-green) | Policies públicas do usuário (SSOT do frontend) | IsAuthenticated |
| GET | `/me/events/` | ![Stable](https://img.shields.io/badge/-stable-green) | Eventos em que o usuário participa | IsAuthenticated |
| POST | `/me/change-password/` | ![Stable](https://img.shields.io/badge/-stable-green) | Troca de senha self-service | IsAuthenticated |

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
| GET | `/api/solicitacoes/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar solicitações (paginado, queryset com escopo) | IsAuthenticated |
| POST | `/api/solicitacoes/` | ![Stable](https://img.shields.io/badge/-stable-green) | Criar nova solicitação | `HasPerm("create_solicitation")` |
| GET | `/api/solicitacoes/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Detalhes de uma solicitação | IsAuthenticated |
| PUT | `/api/solicitacoes/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Atualizar solicitação completa | `IsOwnerOrPrivileged` |
| PATCH | `/api/solicitacoes/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Atualizar parcialmente | `IsOwnerOrPrivileged` |
| DELETE | `/api/solicitacoes/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Excluir solicitação | `IsOwnerOrPrivileged` |
| POST | `/api/solicitacoes/validate/` | ![Stable](https://img.shields.io/badge/-stable-green) | Validar payload antes de criar | IsAuthenticated |

Gates em `views_solicitacao.py:164-183`. `IsOwnerOrPrivileged` é object-level:
libera o dono do registro **ou** quem tem `edit_solicitation_as_owner_or_privileged`.

> **PA-01 / fluxo**: o status inicial **não é sempre `pendente`**. `perform_create`
> delega a `resolve_initial_status(projeto=...)`: projeto com `fluxo=SUPER` nasce
> `pendente`; `fluxo=NAO_SUPER` nasce `aprovado` (`views_solicitacao.py:296-301`).

### Ações de Aprovação (PA-01 a PA-07)

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| **PATCH** | `/api/solicitacoes/{id}/approve/` | ![Stable](https://img.shields.io/badge/-stable-green) | Aprovar solicitação SUPER | `CanAccessSolicitationApprovals` |
| **PATCH** | `/api/solicitacoes/{id}/reject/` | ![Stable](https://img.shields.io/badge/-stable-green) | Reprovar solicitação SUPER | `CanAccessSolicitationApprovals` |
| POST | `/api/solicitacoes/batch-approve/` | ![Stable](https://img.shields.io/badge/-stable-green) | Aprovar em lote (máx. 100 `ids`) | `CanAccessSolicitationApprovals` |
| POST | `/api/solicitacoes/batch-reject/` | ![Stable](https://img.shields.io/badge/-stable-green) | Reprovar em lote (máx. 100 `ids`) | `CanAccessSolicitationApprovals` |

`approve`/`reject` são **PATCH**, não POST (`views_solicitacao.py:629-634` e
`:671-676`). POST nessas rotas retorna `405 Method Not Allowed`.

Corpo opcional de `approve`/`reject`: `{"reason": "..."}` (aceita também
`justificativa` como alias). Resposta 200:
`{"detail": "...", "solicitacao": { ...SolicitacaoSerializer... }}`.

### Filtros Disponíveis

`filterset_fields` está **vazio** — os filtros são tratados manualmente em
`get_queryset` (`views_solicitacao.py:153`, `:185-278`). Só existem estes:

```
?mine=true                       # força escopo ao próprio usuário
?status=pendente|aprovado|reprovado
?status=pending|approved|rejected # aliases em inglês (mapeados)
?flow=SUPER|NAO_SUPER            # fluxo do projeto
?sector=Vidas                    # projeto.gerencia.nome_setor (iexact)
?date_from=2026-01-01            # inicio__date__gte
?date_to=2026-12-31              # inicio__date__lte
?q=texto                         # municipio/projeto/tipo_evento/observacoes/usuário
?search=texto                    # SearchFilter (usuário, município, observações)
?ordering=inicio|fim|id          # únicos campos ordenáveis (aceita prefixo "-")
```

Não existem `?projeto=`, `?municipio=`, `?usuario=`, `?data_inicio__gte=`,
`?data_inicio__lte=` nem `?ordering=-created_at` — são ignorados silenciosamente.

---

## 📅 Disponibilidade (RD-01 a RD-08)

### Verificação de Conflitos

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/availability/check/` | ![Stable](https://img.shields.io/badge/-stable-green) | Verificar conflitos (individual) | `view_all_availability` OU `create_solicitation` OU `approve_solicitation_batch` |
| POST | `/api/availability/check-many/` | ![Stable](https://img.shields.io/badge/-stable-green) | Verificar conflitos em lote | idem acima |
| GET | `/api/availability/monthly/` | ![Stable](https://img.shields.io/badge/-stable-green) | Grade mensal de disponibilidade | `IsAuthenticated` + (`CanViewAllAvailability` \| `HasSectorAccess`) |

Gates: `views_availability.py:233-235` e `:376-378`; `views_availability_monthly.py:80`.
Além do gate de entrada, `check/` e `check-many/` aplicam filtro em runtime: consultar
outro usuário exige `can_check_availability_for_others` (`views_availability.py:291`, `:392`).

### Parâmetros de Check (GET `/api/availability/check/`)

```
?usuario_id={id}        # obrigatório — usuário a verificar
?inicio=2026-01-15T09:00:00   # obrigatório, ISO8601
?fim=2026-01-15T12:00:00      # obrigatório, ISO8601
?municipio_id={id}      # opcional — cálculo de buffer (RD-04)
```

Não existe `exclude_id` (nenhuma ocorrência no backend).

Corpo de `POST /api/availability/check-many/`:
`{"usuarios_ids": [1, 2], "inicio": "...", "fim": "...", "municipio_id": 1}`
— a chave é `usuarios_ids` (`views_availability.py:382`).

Parâmetros da grade mensal (`views_availability_monthly.py:133-174`):
`year` (obrigatório), `month` (obrigatório), `role` (**obrigatório**:
`FORMADOR` ou `COORDENADOR`), `gerencia_id`, `sector`, `q` (opcionais).

### Resposta de Conflito

A chave é `ok`, não `available` (`views_availability.py:341-347`):

```json
{
  "ok": false,
  "conflicts": [
    {
      "code": "T",
      "title": "Bloqueio total",
      "detail": "Conflita com bloqueio total 15/01/2026 09:00-12:00",
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

A rota é `/api/availability-blocks/` (registrada no router como
`availability-blocks`, `v2/backend/apps/core/urls.py:119-123`). **Não** existe
`/api/availability/blocks/`.

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/availability-blocks/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar bloqueios (escopo aplicado no queryset) | IsAuthenticated |
| POST | `/api/availability-blocks/` | ![Stable](https://img.shields.io/badge/-stable-green) | Criar bloqueio (auto-aprovado) | IsAuthenticated |
| GET | `/api/availability-blocks/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Detalhe do bloqueio | IsAuthenticated |
| PUT/PATCH | `/api/availability-blocks/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Atualizar bloqueio próprio | IsAuthenticated |
| DELETE | `/api/availability-blocks/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Remover bloqueio | IsAuthenticated |

É um `ModelViewSet` completo com `permission_classes = [IsAuthenticated]`
(`views_availability.py:91`, `:112`). A restrição real é de **dado**, no
`get_queryset`: privilegiados veem todos; usuários comuns só os próprios ou os
da mesma gerência (`:114-136`).

Delegação: enviar `usuario_id` diferente do próprio no POST exige
`user_can_delegate_availability_block` e o alvo precisa ser Formador ativo —
caso contrário 403/400 (`views_availability.py:162-183`).

---

## 📆 Google Calendar (RF05/RF06)

### Preview e Publicação

As transições por solicitação são **actions do `SolicitacaoViewSet`**, não rotas
sob `/api/gcal/`. Todas exigem `CanUseGcal` (policy `use_gcal` =
`operate_preagenda` OU `approve_solicitation`) — `views_solicitacao.py:698-836`.

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| POST | `/api/solicitacoes/{id}/preview-gcal/` | ![Stable](https://img.shields.io/badge/-stable-green) | Preview do payload (não publica) | `CanUseGcal` |
| POST | `/api/solicitacoes/{id}/publish/` | ![Stable](https://img.shields.io/badge/-stable-green) | Publicar no Google Calendar (202) | `CanUseGcal` |
| POST | `/api/solicitacoes/{id}/resync-gcal/` | ![Beta](https://img.shields.io/badge/-beta-yellow) | Resincronizar evento (202) | `CanUseGcal` |
| POST | `/api/solicitacoes/{id}/cancel-gcal/` | ![Stable](https://img.shields.io/badge/-stable-green) | Cancelar evento no GCal (202) | `CanUseGcal` |
| POST | `/api/gcal/publish-batch/` | ![Stable](https://img.shields.io/badge/-stable-green) | Publicar múltiplas solicitações (202) | `IsAuthenticated` + `CanUseGcal` |

`POST /api/gcal/publish-batch/` espera **`solicitacao_ids`** (não `ids`), máx. 500;
opcionais `dry_run` e `apply_blocked` (`views_gcal/batch.py:80-94`).
Resposta 202: `{"queued": N, "errors": [...], "dry_run": bool, "apply_blocked": bool}`.

Não existem `/api/gcal/preview/`, `/api/gcal/publish/`, `/api/gcal/resync/{id}/`
nem `/api/gcal/cancel/{id}/`.

### Dashboards e Métricas

Todas com `permission_classes = [IsAuthenticated, CanUseGcal]`.

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/gcal/status-summary/` | ![Stable](https://img.shields.io/badge/-stable-green) | Resumo por `gcal_status` | `CanUseGcal` |
| GET | `/api/gcal/list/` | ![Stable](https://img.shields.io/badge/-stable-green) | Lista de eventos sincronizados | `CanUseGcal` |
| GET | `/api/gcal/drift/` | ![Beta](https://img.shields.io/badge/-beta-yellow) | Divergências entre AS e GCal | `CanUseGcal` |
| GET | `/api/gcal/dashboard/metrics/` | ![Stable](https://img.shields.io/badge/-stable-green) | Métricas de publicação | `CanUseGcal` |
| GET | `/api/gcal/dashboard/events/` | ![Stable](https://img.shields.io/badge/-stable-green) | Eventos (paginado, filtros) | `CanUseGcal` |
| GET | `/api/gcal/dashboard/events/{id}/detail/` | ![Stable](https://img.shields.io/badge/-stable-green) | Detalhe + timeline do evento | `CanUseGcal` |
| GET | `/api/gcal/dashboard/events/export/` | ![Stable](https://img.shields.io/badge/-stable-green) | Export CSV/JSON | `CanUseGcal` |
| GET | `/api/gcal/dashboard/alerts/summary/` | ![Stable](https://img.shields.io/badge/-stable-green) | Resumo de alertas (badge/toast) | `CanUseGcal` |
| GET | `/api/gcal/dashboard/insights/success-rate/` | ![Beta](https://img.shields.io/badge/-beta-yellow) | Taxa de sucesso | `CanUseGcal` |
| GET | `/api/gcal/dashboard/insights/top/` | ![Beta](https://img.shields.io/badge/-beta-yellow) | Top 5 insights | `CanUseGcal` |
| POST | `/api/gcal/dashboard/batch/reapply/` | ![Beta](https://img.shields.io/badge/-beta-yellow) | Reaplicar em lote | `CanUseGcal` |
| POST | `/api/gcal/dashboard/batch/resync/` | ![Beta](https://img.shields.io/badge/-beta-yellow) | Resincronizar em lote | `CanUseGcal` |

Não existem `/api/gcal/dashboard/summary/`, `/pending/`, `/errors/` nem `/insights/`.

### Calendários e saúde

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/gcal/calendars/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar calendários disponíveis | `CanUseGcal` |
| GET | `/api/gcal/health/` | ![Stable](https://img.shields.io/badge/-stable-green) | Saúde da integração | `CanUseGcal` |
| GET | `/api/gcal/circuit-breaker/` | ![Internal](https://img.shields.io/badge/-internal-gray) | Estado do circuit breaker | `CanUseGcal` |

### OAuth (por usuário)

As rotas OAuth ficam sob `/api/oauth/google/` e `/api/integrations/google/` —
**não** sob `/api/gcal/oauth/` (`v2/backend/apps/core/urls.py:176-182`).

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/oauth/google/start/` | ![Stable](https://img.shields.io/badge/-stable-green) | Iniciar fluxo OAuth (redirect) | `CanUseGcal` + throttle `oauth` |
| GET | `/api/oauth/google/callback/` | ![Stable](https://img.shields.io/badge/-stable-green) | Callback do Google (redirect p/ frontend) | sem `permission_classes` (usa o default do DRF) |
| GET | `/api/integrations/google/status/` | ![Stable](https://img.shields.io/badge/-stable-green) | Status da conexão OAuth | `CanUseGcal` |
| POST | `/api/integrations/google/disconnect/` | ![Stable](https://img.shields.io/badge/-stable-green) | Revogar/desconectar credenciais | `CanUseGcal` |
| GET | `/api/integrations/google/calendars/` | ![Stable](https://img.shields.io/badge/-stable-green) | Calendários da conta conectada | `CanUseGcal` |
| POST | `/api/integrations/google/select-calendar/` | ![Stable](https://img.shields.io/badge/-stable-green) | Escolher calendário de trabalho | `CanUseGcal` |
| GET | `/api/integrations/google/events/` | ![Stable](https://img.shields.io/badge/-stable-green) | Eventos da conta conectada | `CanUseGcal` |

---

## 🏢 Administração

### Usuários

`UsuarioAdminViewSet` é `ModelViewSet` com
`permission_classes = [HasPerm("manage_admin_registries")]` para **todas** as
actions, inclusive leitura (`views/admin.py:363`).

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/usuarios-admin/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar usuários | `manage_admin_registries` |
| POST | `/api/usuarios-admin/` | ![Stable](https://img.shields.io/badge/-stable-green) | Criar usuário | `manage_admin_registries` |
| GET | `/api/usuarios-admin/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Detalhes do usuário | `manage_admin_registries` |
| PUT/PATCH | `/api/usuarios-admin/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Atualizar usuário | `manage_admin_registries` |
| DELETE | `/api/usuarios-admin/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Excluir usuário | `manage_admin_registries` |

### Municípios

`MunicipioViewSet.permission_classes = [HasPerm("manage_admin_registries")]`
sem `get_permissions()` — o gate vale também para leitura (`views/admin.py:69`).
Consumidores que só precisam popular selects devem usar `/api/options/municipios/`.

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/municipios/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar municípios | `manage_admin_registries` |
| POST | `/api/municipios/` | ![Stable](https://img.shields.io/badge/-stable-green) | Criar município | `manage_admin_registries` |
| GET | `/api/municipios/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Detalhes do município | `manage_admin_registries` |
| PUT/PATCH | `/api/municipios/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Atualizar município | `manage_admin_registries` |

### Projetos

Mesma regra dos municípios: `permission_classes = [HasPerm("manage_admin_registries")]`
para todas as actions (`views/admin.py:199`). Selects usam `/api/options/projetos/`.

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/projetos/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar projetos | `manage_admin_registries` |
| POST | `/api/projetos/` | ![Stable](https://img.shields.io/badge/-stable-green) | Criar projeto (`fluxo` obrigatório, D14) | `manage_admin_registries` |
| GET | `/api/projetos/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Detalhes do projeto | `manage_admin_registries` |
| PUT/PATCH | `/api/projetos/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Atualizar projeto | `manage_admin_registries` |

### Produtos

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/produtos/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar produtos | `manage_admin_registries` \| `manage_purchases_and_materials` \| `run_daily_operations` |
| POST/PUT/PATCH/DELETE | `/api/produtos/` | ![Stable](https://img.shields.io/badge/-stable-green) | Escrita de produto | `IsAuthenticated` + `manage_purchases_and_materials` |

Gate em `views/admin.py:250-272` (D11). Selects abertos ficam em `/api/options/produtos/`.

### Grupos (RBAC)

`GroupViewSet.get_permissions()` (`views/admin.py:494-500`): `list`/`retrieve`
exigem `manage_purchases_and_materials`; **toda** outra action é `SuperuserOnly`.

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/grupos/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar grupos Django | `manage_purchases_and_materials` |
| GET | `/api/grupos/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Detalhes do grupo | `manage_purchases_and_materials` |
| POST/PUT/PATCH/DELETE | `/api/grupos/{id}/` | ![Internal](https://img.shields.io/badge/-internal-gray) | Escrita de grupo | `SuperuserOnly` |

Relacionados: `GET /api/permissoes-funcionais/` (read-only,
`manage_admin_registries`) e `GET /api/rbac/meta/` (`manage_admin_registries`).

### Tipos de Evento

**Não existe** ViewSet `/api/tipos-evento/` — não há registro no router
(`v2/backend/apps/core/urls.py:118-156`). Tipos de evento são expostos apenas
como lookup de leitura:

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/options/tipos-evento/` | ![Stable](https://img.shields.io/badge/-stable-green) | Tipos de evento para select | IsAuthenticated |
| GET | `/api/lookup/tipos-evento/` | ![Stable](https://img.shields.io/badge/-stable-green) | Autocomplete de tipos de evento | IsAuthenticated |

CRUD de `TipoEvento` só pelo Django Admin (superuser).

### Gerências

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/gerencias/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar gerências | IsAuthenticated |
| GET | `/api/gerencias/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Detalhes da gerência | IsAuthenticated |
| POST/PUT/PATCH/DELETE | `/api/gerencias/` | ![Stable](https://img.shields.io/badge/-stable-green) | Escrita de gerência | `IsAuthenticated` + `manage_purchases_and_materials` |

Gate em `views/admin.py:302-306`.

### Auditoria

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/audit-logs/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar AuditLog (read-only) | `CanAccessAuditLogs` (`manage_admin_registries` \| `operate_preagenda`) |

---

## 📊 Módulo DAT

### Registros

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/dat/registros/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar registros DAT | `manage_admin_registries` |
| POST | `/api/dat/registros/` | ![Stable](https://img.shields.io/badge/-stable-green) | Criar registro | `manage_admin_registries` |
| GET | `/api/dat/registros/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Detalhes do registro | `manage_admin_registries` |
| PUT/PATCH | `/api/dat/registros/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Atualizar registro | `manage_admin_registries` |
| DELETE | `/api/dat/registros/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Excluir registro | `execute_restricted_operations` |
| GET | `/api/dat/registros/export/` | ![Stable](https://img.shields.io/badge/-stable-green) | Exportar registros | `manage_admin_registries` |
| GET | `/api/dat/registros/stats/` | ![Stable](https://img.shields.io/badge/-stable-green) | Estatísticas | `manage_admin_registries` |

Gate em `views/dat.py:174-185`.

### Ações

`/api/dat/acoes/` é uma `ListCreateAPIView` (`views_controle_dat.py:100`), não um
ViewSet: só existem **GET** e **POST** na rota de coleção. **Não** existe
`/api/dat/acoes/{id}/` — logo, não há `PATCH` nesse caminho.

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/dat/acoes/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar ações DAT | `manage_admin_registries` |
| POST | `/api/dat/acoes/` | ![Stable](https://img.shields.io/badge/-stable-green) | Criar ação | `manage_admin_registries` |

### Ciclos de Ação

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/dat/acoes-ciclo/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar ciclos de ação | `manage_admin_registries` \| `run_daily_operations` |
| POST | `/api/dat/acoes-ciclo/` | ![Stable](https://img.shields.io/badge/-stable-green) | Criar ciclo | `manage_admin_registries` \| `run_daily_operations` |
| PUT/PATCH | `/api/dat/acoes-ciclo/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Atualizar ciclo | `manage_admin_registries` \| `run_daily_operations` |
| DELETE | `/api/dat/acoes-ciclo/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Excluir ciclo | `execute_restricted_operations` |
| GET | `/api/dat/acoes-ciclo/stats/` | ![Stable](https://img.shields.io/badge/-stable-green) | Estatísticas | `manage_admin_registries` \| `run_daily_operations` |

Gate em `views/dat_module.py:249-257`.

> **Atenção ao ler o código do módulo DAT**: vários `@action(...)` declaram
> `permission_classes=[...]` no decorator, mas os ViewSets sobrescrevem
> `get_permissions()` — e o override **vence**. Quem decide é o `get_permissions()`
> da classe, não o decorator (o próprio código anota isso em
> `views/dat_module.py:413-415`, `:460-462`, `:608-610`).

### Cadastros

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/dat/cadastros/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar cadastros | `manage_admin_registries` |
| POST | `/api/dat/cadastros/` | ![Stable](https://img.shields.io/badge/-stable-green) | Criar cadastro | `manage_admin_registries` |
| PUT/PATCH | `/api/dat/cadastros/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Atualizar cadastro | `manage_admin_registries` |
| DELETE | `/api/dat/cadastros/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Excluir cadastro | `execute_restricted_operations` |

Gate em `views/dat_module.py:756-760`.

### Compras DAT

A rota é `/api/dat/compras-materiais/` (`v2/backend/apps/core/urls.py:148`).
**Não** existe `/api/dat/compras/`. O CRUD genérico de `Compra` (outro modelo)
fica em `/api/compras/`.

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/dat/compras-materiais/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar compras/materiais | `CanViewComprasStats` |
| POST | `/api/dat/compras-materiais/` | ![Stable](https://img.shields.io/badge/-stable-green) | Registrar compra | `CanViewComprasStats` |
| PUT/PATCH | `/api/dat/compras-materiais/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Atualizar compra | `CanViewComprasStats` |
| DELETE | `/api/dat/compras-materiais/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Excluir compra | `execute_restricted_operations` |
| GET | `/api/dat/compras-materiais/dashboard/` | ![Stable](https://img.shields.io/badge/-stable-green) | Dashboard de compras | `CanViewComprasDashboard` |
| GET | `/api/dat/compras-materiais/pendencias/` | ![Stable](https://img.shields.io/badge/-stable-green) | Painel de pendências | `CanViewComprasPendencias` |

Gate em `views/dat_module.py:387-399`. `CanViewComprasStats` =
`manage_admin_registries` \| `manage_purchases_and_materials` \| `run_daily_operations`
(`rbac/policies.py:113-119`) — ou seja, **escrita de compra também é liberada a
Controle**, não só a DAT.

### Coordenadores DAT

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/dat/coordenadores/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar coordenadores | `manage_admin_registries` \| `run_daily_operations` |
| POST | `/api/dat/coordenadores/` | ![Stable](https://img.shields.io/badge/-stable-green) | Criar coordenador | `manage_admin_registries` \| `run_daily_operations` |
| PUT/PATCH | `/api/dat/coordenadores/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Atualizar coordenador | `manage_admin_registries` \| `run_daily_operations` |
| DELETE | `/api/dat/coordenadores/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Excluir coordenador | `execute_restricted_operations` |
| GET | `/api/dat/coordenadores/{id}/alocacoes/` | ![Stable](https://img.shields.io/badge/-stable-green) | Alocações do coordenador | `manage_admin_registries` \| `run_daily_operations` |

Gate em `views/dat_module.py:142-151`.

### Formações DAT

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET/POST | `/api/dat/formacoes/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar / criar formação | `manage_admin_registries` \| `run_daily_operations` |
| GET/PUT/PATCH | `/api/dat/formacoes/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Detalhe / atualizar formação | `manage_admin_registries` \| `run_daily_operations` |
| DELETE | `/api/dat/formacoes/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Excluir formação | `execute_restricted_operations` |
| GET | `/api/dat/formacoes/stats/` | ![Stable](https://img.shields.io/badge/-stable-green) | Estatísticas | `manage_admin_registries` \| `run_daily_operations` |
| GET | `/api/dat/formacoes/calendario/` | ![Stable](https://img.shields.io/badge/-stable-green) | Dados para calendário | `manage_admin_registries` \| `run_daily_operations` |

Gate em `views/dat_module.py:930-938`.

### Áreas DAT — READ-ONLY

`DATAreaViewSet` é `viewsets.ReadOnlyModelViewSet` (`views/dat_module.py:72`):
**só existem GET de lista e de detalhe**. `POST`, `PUT`, `PATCH` e `DELETE`
retornam `405 Method Not Allowed` — a doc anterior anunciava um `POST` que a rota
nunca aceitou. Cadastro de área é feito pelo Django Admin.

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/dat/areas/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar áreas (`?minimal=true` p/ select) | IsAuthenticated |
| GET | `/api/dat/areas/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Detalhe da área | IsAuthenticated |

`permission_classes = [IsAuthenticated]` (`views/dat_module.py:84`) — não exige
capability de DAT. A lista já vem filtrada por `ativo=True`.

---

## 📈 Métricas e Dashboards

### Mapa do Brasil

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/metrics/map/` | ![Stable](https://img.shields.io/badge/-stable-green) | Dados para mapa | `HasPerm("view_map_metrics")` |
| GET | `/api/metrics/map/coordinators/` | ![Stable](https://img.shields.io/badge/-stable-green) | Mapa por coordenador | `HasPerm("view_map_metrics")` |

Gate em `views/metrics/map_metrics.py:179-181` e `:373-375`. **Não** existe
`/api/metrics/map/summary/`, nem `/api/metrics/coordinators/`, nem
`/api/metrics/coordinators/{id}/`.

### Métricas de Equipe

Todas sob `/api/metrics/team/`, com a mesma composition
`run_daily_operations | supervise_operations | manage_admin_registries`
(`views/metrics/dashboard_metrics.py:26-38`, `:125-137`;
`views/metrics/formador_metrics.py:26-34`).

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/metrics/team/productivity/` | ![Beta](https://img.shields.io/badge/-beta-yellow) | Produtividade da equipe | `run_daily_operations` \| `supervise_operations` \| `manage_admin_registries` |
| GET | `/api/metrics/team/formadores/` | ![Beta](https://img.shields.io/badge/-beta-yellow) | Métricas por formador | idem |
| GET | `/api/metrics/team/quality/` | ![Beta](https://img.shields.io/badge/-beta-yellow) | Indicadores de qualidade | idem |

**Não** existe `/api/metrics/quality/` — o caminho correto é
`/api/metrics/team/quality/`.

### Relatórios

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/reports/status-counts/` | ![Stable](https://img.shields.io/badge/-stable-green) | Contagem por status | `CanViewReports` |
| GET | `/api/reports/top-projects/` | ![Stable](https://img.shields.io/badge/-stable-green) | Projetos com mais eventos | `CanViewReports` |
| GET | `/api/reports/weekly-approved/` | ![Stable](https://img.shields.io/badge/-stable-green) | Aprovações por semana | `CanViewReports` |
| GET | `/api/reports/by-uf/` | ![Stable](https://img.shields.io/badge/-stable-green) | Distribuição por UF | `CanViewReports` |
| GET | `/api/dashboard/overview/` | ![Stable](https://img.shields.io/badge/-stable-green) | Painel executivo geral | `HasPerm("view_overview_dashboard")` |
| GET | `/api/stats/home/` | ![Stable](https://img.shields.io/badge/-stable-green) | Contadores da home | IsAuthenticated |
| GET | `/api/pre-agenda/` | ![Stable](https://img.shields.io/badge/-stable-green) | Fila da pré-agenda (list-only) | `HasPerm("operate_preagenda")` |

`CanViewReports` = `operate_preagenda` \| `approve_solicitation` \|
`manage_admin_registries` (`rbac/policies.py:126`).

---

## 📥 Imports (planilhas)

Todos são `POST` `multipart/form-data` com o arquivo no campo **`file`**, e todos
usam o throttle scope `import` (30/min). O modo de execução vem no query param
**`dry_run`** — o default é `true` (preview); `?dry_run=false` aplica
(`views_import_usuarios.py:93-94`).

| Endpoint | Permissão |
|----------|-----------|
| `/api/usuarios/import/` | `IsAuthenticated` + `manage_admin_registries` |
| `/api/municipios/import/` | `IsAuthenticated` + `manage_admin_registries` |
| `/api/colecoes/import/` | `IsAuthenticated` + `manage_admin_registries` |
| `/api/equipe-gerencia/import/` | `IsAuthenticated` + `manage_admin_registries` |
| `/api/dat/import-cadastros/` | `IsAuthenticated` + `manage_admin_registries` |
| `/api/solicitacoes/import/` | `IsAuthenticated` + `import_spreadsheet` |
| `/api/produtos/import/` | `IsAuthenticated` + `import_spreadsheet` |
| `/api/deslocamentos/import/` | `IsAuthenticated` + `import_spreadsheet` |
| `/api/disponibilidade/import-bloqueios/` | `IsAuthenticated` + `import_spreadsheet` |
| `/api/controle/import-acoes/` | `IsAuthenticated` + `import_spreadsheet` |
| `/api/controle/import-compras/` (alias `/api/import-compras/`) | `IsAuthenticated` + `import_spreadsheet` |

Imports assíncronos (ASQ-005): `POST /api/imports/bloqueios/`
(`IsAuthenticated` + `CanImportGenericSpreadsheet`), `GET /api/imports/` e
`GET /api/imports/{id}/` (`IsAuthenticated`, queryset filtrado por dono).

> ✅ Resolvido em #1649 (achado `M04-05`): o parse de `dry_run` é **fail-closed** — valor
> desconhecido permanece em dry-run (preview); só `false`/`0`/`no`/… disparam APPLY.

---

## 🔧 Options (Lookups)

Endpoints para popular dropdowns e selects no frontend.

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/options/municipios/` | ![Stable](https://img.shields.io/badge/-stable-green) | Lista simplificada de municípios | IsAuthenticated |
| GET | `/api/options/projetos/` | ![Stable](https://img.shields.io/badge/-stable-green) | Lista simplificada de projetos | IsAuthenticated |
| GET | `/api/options/usuarios/` | ![Stable](https://img.shields.io/badge/-stable-green) | Lista de usuários para select | IsAuthenticated |
| GET | `/api/options/formadores-do-setor/` | ![Stable](https://img.shields.io/badge/-stable-green) | Formadores do setor do usuário | IsAuthenticated |
| GET | `/api/options/coordenadores/` | ![Stable](https://img.shields.io/badge/-stable-green) | Lista de coordenadores | IsAuthenticated |
| GET | `/api/options/tipos-evento/` | ![Stable](https://img.shields.io/badge/-stable-green) | Tipos de evento para select | IsAuthenticated |
| GET | `/api/options/produtos/` | ![Stable](https://img.shields.io/badge/-stable-green) | Produtos para select | IsAuthenticated |
| GET | `/api/options/areas/` | ![Stable](https://img.shields.io/badge/-stable-green) | Áreas DAT para select | IsAuthenticated |

Registro das rotas em `v2/backend/apps/core/urls.py:328-335`. **Não** existem
`/api/options/formadores/` (o nome é `formadores-do-setor`) nem
`/api/options/gerencias/` — para gerências use `GET /api/gerencias/`
(IsAuthenticated na leitura).

### Lookup (autocomplete)

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/lookup/municipios/` | ![Stable](https://img.shields.io/badge/-stable-green) | Autocomplete de municípios | IsAuthenticated |
| GET | `/api/lookup/projetos/` | ![Stable](https://img.shields.io/badge/-stable-green) | Autocomplete de projetos | IsAuthenticated |
| GET | `/api/lookup/tipos-evento/` | ![Stable](https://img.shields.io/badge/-stable-green) | Autocomplete de tipos de evento | IsAuthenticated |
| GET | `/api/lookup/usuarios/` | ![Stable](https://img.shields.io/badge/-stable-green) | Autocomplete de usuários | `create_solicitation` \| `manage_admin_registries` |

`UsuarioLookup` é o único com gate de capability (`views_lookup.py:209`, D12).

---

## ❤️ Health Checks

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/healthz/` | ![Stable](https://img.shields.io/badge/-stable-green) | Health check básico — **na raiz, fora de `/api/`** | público |
| GET | `/healthz/detailed/` | ![Internal](https://img.shields.io/badge/-internal-gray) | DB + Redis + circuit breaker — superuser ou IP interno | 403 caso contrário |
| GET | `/api/readyz/` | ![Stable](https://img.shields.io/badge/-stable-green) | Readiness (DB + Redis) | AllowAny |
| GET | `/api/version/` | ![Stable](https://img.shields.io/badge/-stable-green) | SHA/tag da build em execução | AllowAny |
| GET | `/api/features/` | ![Stable](https://img.shields.io/badge/-stable-green) | Feature flags ativas | **IsAuthenticated** |
| GET/PUT | `/api/config/` | ![Stable](https://img.shields.io/badge/-stable-green) | Configurações operacionais (leitura **e escrita**) | `manage_purchases_and_materials` \| `approve_solicitation` |

Provas: `/healthz/` e `/healthz/detailed/` estão em `v2/backend/config/urls.py:103-104`
(fora do `include("apps.core.urls")` da linha 108) — `/api/healthz/` **não existe**.
`/api/features/` usa `@permission_classes([IsAuthenticated])` (`views_health.py:99-101`),
não `AllowAny`. `/api/config/` aceita `GET` e `PUT` e é gateado por capability
(`views_config.py:62-63`), não por `IsAuthenticated`.

---

## 🔐 Permissões

### Classes de Permissão

As classes `IsSuperintendencia`, `IsControleOrSuper`, `IsDATOrSuper` e `IsDAT`
**não existem no código** — o padrão "permission class por nome de grupo" é
banido pelo `rbac_lint` (`v2/backend/apps/core/rbac/__init__.py:24-27`;
`apps/core/tests/test_rbac_lint.py`). Autorização é por **capability**, não por
grupo. O que existe:

| Classe | Onde | Semântica |
|--------|------|-----------|
| `AllowAny` | DRF | Acesso público |
| `IsAuthenticated` | DRF | Usuário logado |
| `HasPerm("<codename>")` | `rbac/permissions.py:39` | Exige a capability; suporta OR (`HasPerm("a") \| HasPerm("b")`) |
| `SuperuserOnly` | `rbac/permissions.py:128` | Só superuser |
| `IsOwnerOrPrivileged` | `rbac/permissions.py:212` | Object-level: dono do registro ou `edit_solicitation_as_owner_or_privileged` |
| `HasSectorAccess` | `rbac/permissions.py:240` | Escopo por gerência (`EquipeGerencia`) para a grade mensal |
| `Can*` (Policy) | `rbac/policies.py:78-162` | Policy nomeada = OR de capabilities com semântica única |

Policies usadas nesta referência (`rbac/policies.py`):

| Policy | Capabilities aceitas |
|--------|----------------------|
| `CanUseGcal` | `operate_preagenda`, `approve_solicitation` |
| `CanAccessAuditLogs` | `manage_admin_registries`, `operate_preagenda` |
| `CanViewComprasStats` | `manage_admin_registries`, `manage_purchases_and_materials`, `run_daily_operations` |
| `CanViewComprasDashboard` | `view_compras_dashboard`, `manage_admin_registries` |
| `CanViewComprasPendencias` | as 3 de stats + `view_compras_dashboard` |
| `CanViewReports` | `operate_preagenda`, `approve_solicitation`, `manage_admin_registries` |
| `CanViewAllAvailability` | `view_all_availability` |
| `CanAccessSolicitationApprovals` | **composite Setor × Função** (não é OR de capabilities) |

Quais **grupos** têm cada capability é assunto de outro documento — o SSOT é
[rbac_authorization_matrix.md](rbac_authorization_matrix.md) §4. Desde a decisão
D17 (PR 16), a relação Grupo × Capability é **admin-driven** (editável no Django
Admin por superuser), então não replique essa tabela aqui: ela pode mudar sem
alteração de código.

### Regra de Aprovação SUPER

> **Atualização hardening RBAC (2026-04-29 — PR 3 #1308 e PR 10 #1315):**
> a regra atual é `access_solicitation_approvals` (composite Setor × Função).
> O campo `can_approve_super` permanece no payload de `/api/me/` por compat
> externa, mas não é fonte de decisão no frontend.

```python
# Atual — policy `access_solicitation_approvals` (Gerente Sup OU Asst Admin Controle)
access_solicitation_approvals = is_superuser OR (
    ("Gerente" IN funcoes AND "Superintendência" IN setores)
    OR
    ("Assistente Administrativo" IN funcoes AND "Controle" IN setores)
)

# [legacy] mantido em /api/me/ por compat externa; não usar para decisão nova.
# Desde o PR 3 (#1308) o flag foi alinhado à policy — inclui também o
# Assistente Administrativo do Controle. Prova: views_basic.py:107-109.
can_approve_super = is_superuser
    OR ("Gerente" IN funcoes AND "Superintendência" IN setores)
    OR ("Assistente Administrativo" IN funcoes AND "Controle" IN setores)
```

Para decisão nova, consuma `GET /api/me/policies/` e leia
`access_solicitation_approvals` (`rbac/policies.py:333-337`).

---

## 📄 Paginação

O padrão global é `rest_framework.pagination.PageNumberPagination` com
`PAGE_SIZE: 100` (`v2/backend/config/settings.py:485-486`). Essa classe **não
define `page_size_query_param`**, então **`?page_size=` é ignorado** na maioria
das listagens — a página vem sempre com 100 itens. Só `?page=` funciona.

`StandardPagination` (`apps/core/pagination.py:12`), que aceitaria `page_size`,
existe mas **não está ligada a nenhuma view** — nenhum
`pagination_class = StandardPagination` no backend.

Exceções que **aceitam** `?page_size=`, por terem paginador próprio:

| Endpoint | Classe | Default | Máx. |
|---|---|---:|---:|
| `/api/deslocamentos/` | `DeslocamentoPagination` (`views_deslocamento.py:75-80`) | 50 | 100 |
| `/api/gcal/list/` | `LargePagination` (`pagination.py:26-39`) | 200 | 1000 |
| `/api/gcal/dashboard/events/` | `DashboardEventsPagination` (`views_gcal/helpers.py:149-154`) | 20 | 100 |

Endpoints de `/api/options/*` não são paginados (`pagination_class = None`).

### Request

```
GET /api/solicitacoes/?page=2
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

`custom_exception_handler` normaliza **toda** resposta de erro para um objeto
plano com `detail` + `code` (+ `errors` quando há erro de campo) —
`apps/core/exceptions.py:162-281`. `code` vem em **MAIÚSCULAS**
(`_get_error_code`, `:284-296`).

```json
{
  "detail": "<mensagem da permission class>",
  "code": "PERMISSION_DENIED"
}
```

### Erros de Validação

Os erros de campo **não** ficam na raiz: são agrupados sob `errors`
(`exceptions.py:272-279`). Para o `ValidationError` do DRF (o caso comum de
serializer), `code` é `INVALID` — vem do `default_code` da exceção, não do mapa
de nomes (`exceptions.py:287-288`).

```json
{
  "detail": "Erro de validação.",
  "code": "INVALID",
  "errors": {
    "inicio": ["Este campo é obrigatório."],
    "non_field_errors": ["Erro geral"]
  }
}
```

---

## 🚀 Rate Limiting

Valores de produção — `v2/backend/config/settings.py:495-516`.

| Escopo | Limite | Descrição |
|--------|--------|-----------|
| `anon` | 100/hour | Usuários não autenticados |
| `user` | 1000/hour | Usuários autenticados |
| `availability_check` | 60/min | Verificação de conflitos |
| `metrics` | 30/min | Métricas (geo + agregações) |
| `reports` | 30/min | Relatórios (agregações pesadas) |
| `gcal_write` | 10/min | Escritas no Google Calendar (publish/batch) |
| `export` | 10/min | Exports CSV/JSON |
| `import` | 30/min | Uploads de importação (balde único por usuário) |
| `login` | 10/minute | Anti brute-force no `/auth/login/` |
| `change_password` | 20/min | Troca de senha self-service |
| `oauth` | 10/hour | `/api/oauth/google/start/` |

**Nota**: fora de produção os limites são relaxados (`settings.py:572-587`) —
não são exatamente "10x" para todos os escopos (`login` vai a `1000/minute`).

---

## 📚 Documentação Swagger

Quando habilitado (drf-spectacular):

| URL | Descrição |
|-----|-----------|
| `/api/schema/` | OpenAPI 3.0 Schema (JSON/YAML) |
| `/api/docs/` | Swagger UI interativo |
| `/api/redoc/` | ReDoc (alternativa) |

---

**Mantido por**: Equipe AS v2
