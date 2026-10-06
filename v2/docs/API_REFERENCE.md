# 📡 API Reference — Aprender Sistema v2

**Última Atualização**: 2026-09-29 (PR A: `/me/.gerencias`, nomes da gerência, `gerencia_id`; última varredura de veracidade 2026-07-24)
**Base canônica**: `/api`
**ViewSets registrados no router**: 24 (bloco `router.register(...)`, `v2/backend/apps/core/urls.py`)
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

**Estado em 2026-07-24**: o alias **ainda existe** — a rota `api/v1/` (namespace `core-v1`) em `v2/backend/config/urls.py`
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

**Troca obrigatória de senha (primeiro acesso).** `GET /me/` inclui `deve_trocar_senha`
(bool): `true` quando a senha em uso foi definida por um administrador (`POST`/`PATCH
/usuarios-admin/` com `password`, por alguém que não a própria pessoa). Enquanto estiver
`true`, a API só aceita `GET /me/`, `GET /csrf/`, `POST /me/change-password/`,
`POST /auth/logout/` e `POST /auth/login/` (entrar de novo não desliga a marca); qualquer
outra rota (inclusive `/api/v1/*` e `/admin/`) responde `403` com `code: PASSWORD_CHANGE_REQUIRED`. `POST /me/change-password/`
(`old_password`, `new_password`) desliga a marca e mantém a sessão; a senha nova tem de ser
diferente da atual e da recebida no primeiro acesso (também em trocas futuras), ter 8+ caracteres, não ser só números nem senha comum e não parecer com
nome, CPF ou e-mail da pessoa (erros em `errors.old_password` / `errors.new_password`). O
campo não é gravável por nenhuma rota. Regra completa:
[rbac.spec](./specs/backend/rbac.spec.md).

**Limite de tentativas.** `POST /auth/login/` e `GET /csrf/` respondem `429` com
`code: THROTTLED` e cabeçalho `Retry-After` (segundos). Senha errada e bloqueio por
tentativas respondem o mesmo `400` genérico (o bloqueio não é revelado).

`GET /me/` inclui `gerencias: [{id, rotulo, papeis[]}]` (PR A, 2026-09-29): vínculos
`EquipeGerencia` vigentes (`vigentes_em()`) em gerência ativa, um item por gerência,
ordenados pelo `rotulo`. É por ele que a Grade Mensal escolhe a gerência de quem não tem
`view_all_availability`. `setores`, `is_superintendencia` e `can_approve_super` não mudaram
(continuam vindo dos grupos). Construído em `views_basic.py` (`_gerencias_do_vinculo`).

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

Gates em `SolicitacaoViewSet.get_permissions` (`views_solicitacao.py`). `IsOwnerOrPrivileged` é object-level:
libera o dono do registro **ou** quem tem `edit_solicitation_as_owner_or_privileged` **dentro do escopo**
(`user_can_access_solicitacao`). A gerência da Superintendência por vínculo vê tudo, mas só edita/exclui
as próprias e as do alcance dela, que é o fluxo SUPER da Superintendência mais as gerências de um 2º
vínculo de GERENTE dela (fora: 403), e só cria ou move para projeto desse alcance (fora: 400 em
`projeto`) — regra do dono, 2026-09-30.

> **PA-01 / fluxo**: o status inicial **não é sempre `pendente`**. `perform_create`
> delega a `resolve_initial_status(projeto=...)`: projeto com `fluxo=SUPER` nasce
> `pendente`; `fluxo=NAO_SUPER` nasce `aprovado` (`SolicitacaoViewSet.perform_create`, `views_solicitacao.py`).

> **Responsável e perguntas (decisão do dono, 05/10/2026)** — detalhe em
> [`solicitacao-approval.spec.md`](specs/backend/solicitacao-approval.spec.md):
> - `coordenador` (id): sem valor, quem cria se tem a função Coordenador; senão **400** no campo.
>   Mesmo escopo de setor dos formadores. Recebe o convite do Google mesmo sem acompanhar.
> - `coordenador_acompanha` (bool): **obrigatório no POST** (ausente ou `null` → 400). Só com `true`
>   a agenda do responsável é conferida; trocar para `true` com conflito → 400 `availability_conflict`.
> - `pretende_avaliar_formador` (bool|null) e `formador_avaliado` (id|null): obrigatórios quando a
>   gerência do projeto pergunta e há formador avaliável (Formador sem a função Coordenador); `true`
>   exige um formador avaliável do evento; fora disso, resposta nova não nula → 400. No `PATCH`,
>   resposta já dada não se apaga nem se troca quando a pergunta deixa de valer (400), e tirar da
>   lista o formador escolhido → 400; pergunta que passa a valer exige resposta. Leitura em
>   `GET` (lista e detalhe), com `formador_avaliado_nome`; `avaliaveis_ids` e
>   `projeto_pergunta_avaliar_formador` só no detalhe (null na lista).
> - `extra_participants.coord_acompanha_ids`/`coord_acompanha_emails` com itens → 400 (a lista saiu;
>   coordenador que atua vai em `formador_ids`).

### Ações de Aprovação (PA-01 a PA-07)

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| **PATCH** | `/api/solicitacoes/{id}/approve/` | ![Stable](https://img.shields.io/badge/-stable-green) | Aprovar solicitação SUPER | `CanAccessSolicitationApprovals` |
| **PATCH** | `/api/solicitacoes/{id}/reject/` | ![Stable](https://img.shields.io/badge/-stable-green) | Reprovar solicitação SUPER | `CanAccessSolicitationApprovals` |
| POST | `/api/solicitacoes/batch-approve/` | ![Stable](https://img.shields.io/badge/-stable-green) | Aprovar em lote (máx. 100 `ids`); item barrado por agenda vem em `errors[]` com `code: availability_conflict`, `detail` (quem e por quê) e `blocked_participants` | `CanAccessSolicitationApprovals` |
| POST | `/api/solicitacoes/batch-reject/` | ![Stable](https://img.shields.io/badge/-stable-green) | Reprovar em lote (máx. 100 `ids`) | `CanAccessSolicitationApprovals` |

`approve`/`reject` são **PATCH**, não POST (actions `SolicitacaoViewSet.approve` e
`SolicitacaoViewSet.reject`, `views_solicitacao.py`). POST nessas rotas retorna `405 Method Not Allowed`.

Corpo opcional de `approve`/`reject`: `{"reason": "..."}` (aceita também
`justificativa` como alias). Resposta 200:
`{"detail": "...", "solicitacao": { ...SolicitacaoSerializer... }}`.

Erros de quem decide: a própria solicitação → 403 `self_approval_forbidden`; para a gerência da
Superintendência por vínculo, solicitação que não é do fluxo SUPER da Superintendência → 403
`out_of_approval_scope`. Nos lotes, os dois viram `errors[]` com `{id, code, detail}` e o resto segue.

### Filtros Disponíveis

`filterset_fields` está **vazio** — os filtros são tratados manualmente em
`get_queryset` (`filterset_fields` e `SolicitacaoViewSet.get_queryset`, `views_solicitacao.py`). Só existem estes:

```
?mine=true                       # força escopo ao próprio usuário
?publishable=true                # só o que o usuário pode publicar no Google Agenda (#1656); use com status=aprovado
?status=pendente|aprovado|reprovado
?status=pending|approved|rejected # aliases em inglês (mapeados)
?flow=SUPER|NAO_SUPER            # fluxo do projeto
?sector=Vidas                    # projeto.gerencia.nome_setor (iexact) — legado, ainda aceito
?gerencia_id=4                   # projeto.gerencia_id (PR A; o mesmo do /gcal/status-summary/); não numérico é ignorado
?date_from=2026-01-01            # inicio__date__gte
?date_to=2026-12-31              # inicio__date__lte
?q=texto                         # municipio/projeto/tipo_evento/observacoes/usuário
?search=texto                    # SearchFilter (usuário, município, observações)
?ordering=inicio|fim|id          # campos ordenáveis (aceita prefixo "-"); default -inicio
?ordering=proximidade            # de hoje em diante (início do dia em America/Fortaleza), do mais próximo
                                 # ao mais distante; depois os passados, do mais recente ao mais antigo;
                                 # desempate por id. É a ordem da tela de Aprovações. Sem prefixo "-".
?page=1&page_size=20             # paginação (default 100, máximo 500); página inexistente → 404
```

Não existem `?projeto=`, `?municipio=`, `?usuario=`, `?data_inicio__gte=`,
`?data_inicio__lte=` nem `?ordering=-created_at` — são ignorados silenciosamente (um `ordering`
desconhecido cai no default `-inicio`).

---

## 📅 Disponibilidade (RD-01 a RD-08)

### Verificação de Conflitos

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/availability/check/` | ![Stable](https://img.shields.io/badge/-stable-green) | Verificar conflitos (individual) | `view_all_availability` OU `create_solicitation` OU `approve_solicitation_batch` |
| POST | `/api/availability/check-many/` | ![Stable](https://img.shields.io/badge/-stable-green) | Verificar conflitos em lote | idem acima |
| GET | `/api/availability/monthly/` | ![Stable](https://img.shields.io/badge/-stable-green) | Grade mensal de disponibilidade | `IsAuthenticated` + (`CanViewAllAvailability` \| `HasSectorAccess`) |

Gates: `AvailabilityCheckView` e `AvailabilityCheckManyView` (`views_availability.py`); `MonthlyAvailabilityView` (`views_availability_monthly.py`).
Além do gate de entrada, `check/` e `check-many/` aplicam filtro em runtime: consultar
outro usuário exige `can_check_availability_for_others` (`AvailabilityCheckView.get` e `AvailabilityCheckManyView.post`, `views_availability.py`).

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
— a chave é `usuarios_ids` (`AvailabilityCheckManyView.post`, `views_availability.py`).

Parâmetros da grade mensal (`MonthlyAvailabilityView.get`, `views_availability_monthly.py`):
`year` (obrigatório), `month` (obrigatório), `role` (**obrigatório**:
`FORMADOR` ou `COORDENADOR`), `gerencia_id`, `sector`, `q` (opcionais).

### Resposta de Conflito

A chave é `ok`, não `available` (`AvailabilityCheckView.get`, `views_availability.py`).
`conflicts` traz o que barra; `warnings` é o canal do que só avisa e não muda `ok` — hoje vem
sempre vazio (o limite diário `M` saiu em 05/10/2026, decisão do dono).
No `check-many/`, cada item de `results` tem as mesmas três chaves, mais `usuario_id`:

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
  ],
  "warnings": []
}
```

O erro 400 `availability_conflict` de criar, editar e aprovar segue o mesmo corte: `errors.conflicts`
e a mensagem só falam do que barra; `errors.warnings` e `errors.blocked_participants[].warnings`
são aditivas e trazem os avisos calculados na mesma checagem (hoje, nenhum).

### Códigos de Conflito

| Código | Título | Descrição |
|--------|--------|-----------|
| X | Sobreposição | Evento conflita com outro aprovado |
| T | Bloqueio total | Formador bloqueado completamente |
| P | Bloqueio parcial | Subintervalo bloqueado |
| D | Deslocamento | Buffer de viagem insuficiente |
| M | Limite diário (removido) | **Não é mais emitido** desde 05/10/2026 (decisão do dono). O parâmetro `AVAILABILITY_DAILY_LIMIT_HOURS` virou o teto por evento da contagem de horas de formação (`ch_month`/`ch_year` da grade, `horas_trabalhadas` do painel de Equipe). Cliente antigo que ainda receba `M` deve tratá-lo como aviso |

### Bloqueios de Disponibilidade

A rota é `/api/availability-blocks/` (registrada no router como
`availability-blocks`, `v2/backend/apps/core/urls.py`; basename `availability-block`). **Não** existe
`/api/availability/blocks/`.

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/availability-blocks/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar bloqueios (escopo aplicado no queryset) | IsAuthenticated |
| POST | `/api/availability-blocks/` | ![Stable](https://img.shields.io/badge/-stable-green) | Criar bloqueio (auto-aprovado) | IsAuthenticated |
| GET | `/api/availability-blocks/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Detalhe do bloqueio | IsAuthenticated |
| PUT/PATCH | `/api/availability-blocks/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Atualizar bloqueio próprio | IsAuthenticated |
| DELETE | `/api/availability-blocks/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Remover bloqueio | IsAuthenticated |

É um `ModelViewSet` completo com `permission_classes = [IsAuthenticated]`
(`AvailabilityBlockViewSet`, `views_availability.py`). A restrição real é de **dado**, no
`get_queryset`: privilegiados veem todos; usuários comuns só os próprios ou os
da mesma gerência (`AvailabilityBlockViewSet.get_queryset`, `views_availability.py`).

Delegação: enviar `usuario_id` diferente do próprio no POST exige
`user_can_delegate_availability_block` e o alvo precisa ser Formador ativo —
caso contrário 403/400 (`AvailabilityBlockViewSet.perform_create`, `views_availability.py`).

---

## 📆 Google Calendar (RF05/RF06)

### Preview e Publicação

As transições por solicitação são **actions do `SolicitacaoViewSet`**, não rotas
sob `/api/gcal/`. Exigem `CanUseGcal` (policy `use_gcal` =
`operate_preagenda` OU `approve_solicitation`) **ou** `CanPublishSetorSolicitacao` — actions `preview_gcal`/`publish`/`resync_gcal`/`cancel_gcal` do `SolicitacaoViewSet` (`views_solicitacao.py`).
Com `CanPublishSetorSolicitacao` (Apoio de Coordenação) só vale evento **aprovado do próprio setor**: `Projeto.setor` do evento ∈ setores do vínculo vigente da pessoa (`can_publish_solicitacao`); fora disso, 404.
Em modo OAuth, publish/resync/cancel recusam **antes** de marcar PENDING: 403 `google_not_connected` (sem credencial Google) e 409 `google_calendar_not_configured` (sem calendário de publicação — nem o pino `GCAL_OAUTH_CALENDAR_ID`, nem escolha na credencial; ver `GUIDE_GCAL.md`).

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| POST | `/api/solicitacoes/{id}/preview-gcal/` | ![Stable](https://img.shields.io/badge/-stable-green) | Preview do payload (não publica) | `CanUseGcal` ou `CanPublishSetorSolicitacao` |
| POST | `/api/solicitacoes/{id}/publish/` | ![Stable](https://img.shields.io/badge/-stable-green) | Publicar no Google Calendar (202) | `CanUseGcal` ou `CanPublishSetorSolicitacao` |
| POST | `/api/solicitacoes/{id}/resync-gcal/` | ![Beta](https://img.shields.io/badge/-beta-yellow) | Resincronizar evento (202) | `CanUseGcal` ou `CanPublishSetorSolicitacao` |
| POST | `/api/solicitacoes/{id}/cancel-gcal/` | ![Stable](https://img.shields.io/badge/-stable-green) | Cancelar evento no GCal (202) | `CanUseGcal` ou `CanPublishSetorSolicitacao` |
| POST | `/api/gcal/publish-batch/` | ![Stable](https://img.shields.io/badge/-stable-green) | Publicar múltiplas solicitações (202) | `IsAuthenticated` + `CanUseGcal` |

`POST /api/gcal/publish-batch/` espera **`solicitacao_ids`** (não `ids`), máx. 500;
opcionais `dry_run` e `apply_blocked` (`GCalPublishBatchView.post`, `views_gcal/batch.py`).
Resposta 202: `{"queued": N, "errors": [...], "dry_run": bool, "apply_blocked": bool}`.
Em modo OAuth (`GCAL_AUTH_MODE=oauth`), igual a reapply/resync: exige a credencial Google de quem chama
(senão 403 `{"code": "google_not_connected"}`, sem alterar nenhuma linha) e passa `operator_user_id` à task.

Não existem `/api/gcal/preview/`, `/api/gcal/publish/`, `/api/gcal/resync/{id}/`
nem `/api/gcal/cancel/{id}/`.

### Dashboards e Métricas

Todas com `permission_classes = [IsAuthenticated, CanUseGcal]`.

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/gcal/status-summary/` | ![Stable](https://img.shields.io/badge/-stable-green) | Resumo por `gcal_status` (só aprovados). Filtros `date_from`, `date_to`, `sector` (`projeto__nome__icontains`), `gerencia_id` (`projeto__gerencia_id`, PR A), `q`, `status` (= `gcal_status`, não o status da solicitação) | `CanUseGcal` |
| GET | `/api/gcal/list/` | ![Stable](https://img.shields.io/badge/-stable-green) | Lista de eventos sincronizados | `CanUseGcal` |
| GET | `/api/gcal/drift/` | ![Beta](https://img.shields.io/badge/-beta-yellow) | Divergências entre AS e GCal | `CanUseGcal` |
| GET | `/api/gcal/dashboard/metrics/` | ![Stable](https://img.shields.io/badge/-stable-green) | Métricas de publicação | `CanUseGcal` |
| GET | `/api/gcal/dashboard/events/` | ![Stable](https://img.shields.io/badge/-stable-green) | Eventos (paginado, filtros) | `CanUseGcal` |
| GET | `/api/gcal/dashboard/events/{id}/detail/` | ![Stable](https://img.shields.io/badge/-stable-green) | Detalhe + timeline do evento | `CanUseGcal` |
| GET | `/api/gcal/dashboard/events/export/` | ![Stable](https://img.shields.io/badge/-stable-green) | Export CSV/JSON | `CanUseGcal` |
| GET | `/api/gcal/dashboard/alerts/summary/` | ![Stable](https://img.shields.io/badge/-stable-green) | Resumo de alertas (badge/toast) + `google_reconnect` | `CanUseGcal` |
| GET | `/api/gcal/dashboard/insights/success-rate/` | ![Beta](https://img.shields.io/badge/-beta-yellow) | Taxa de sucesso | `CanUseGcal` |
| GET | `/api/gcal/dashboard/insights/top/` | ![Beta](https://img.shields.io/badge/-beta-yellow) | Top 5 insights | `CanUseGcal` |
| POST | `/api/gcal/dashboard/batch/reapply/` | ![Beta](https://img.shields.io/badge/-beta-yellow) | Reaplicar em lote | `CanUseGcal` |
| POST | `/api/gcal/dashboard/batch/resync/` | ![Beta](https://img.shields.io/badge/-beta-yellow) | Resincronizar em lote | `CanUseGcal` |

Não existem `/api/gcal/dashboard/summary/`, `/pending/`, `/errors/` nem `/insights/`.

`alerts/summary` (#2039) traz, além das contagens por `gcal_status` (que respeitam `start`/`end`),
quem precisa reconectar a conta Google, sem depender da janela:

```json
{
  "errors": 2, "pending": 0, "published": 40, "none": 3,
  "window": {"start": null, "end": null},
  "google_reconnect": {"count": 1, "users": [{"id": 12, "nome": "Ana Souza"}]}
}
```

`users`: pessoas ativas cuja conexão o sistema removeu (`invalid_grant`, no job diário ou num
publish) e que não reconectaram depois. O "Desconectar" manual não entra. Ordenado por nome; só `id`
e `nome` (o nome, ou `Usuario #<id>` sem nome), sem e-mail nem CPF.

### Calendários e saúde

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/gcal/calendars/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar calendários disponíveis | `CanUseGcal` |
| GET | `/api/gcal/health/` | ![Stable](https://img.shields.io/badge/-stable-green) | Saúde da integração | `CanUseGcal` |
| GET | `/api/gcal/circuit-breaker/` | ![Internal](https://img.shields.io/badge/-internal-gray) | Estado do circuit breaker | `CanUseGcal` |

### OAuth (por usuário)

As rotas OAuth ficam sob `/api/oauth/google/` e `/api/integrations/google/` —
**não** sob `/api/gcal/oauth/` (paths `google-oauth-*`, `v2/backend/apps/core/urls.py`).

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/oauth/google/start/` | ![Stable](https://img.shields.io/badge/-stable-green) | Iniciar fluxo OAuth (redirect) | `CanUseGcal \| CanPublishSetorSolicitacao` + throttle `oauth`; sem setor vigente → 403 `no_setor_scope` |
| GET | `/api/oauth/google/callback/` | ![Stable](https://img.shields.io/badge/-stable-green) | Callback do Google (redirect p/ frontend) | `CanUseGcal \| CanPublishSetorSolicitacao` |
| GET | `/api/integrations/google/status/` | ![Stable](https://img.shields.io/badge/-stable-green) | Status da conexão OAuth + `publish_ready`/`publish_block_reason`/`reconnect_required` | `CanUseGcal \| CanPublishSetorSolicitacao` |
| POST | `/api/integrations/google/disconnect/` | ![Stable](https://img.shields.io/badge/-stable-green) | Revogar/desconectar credenciais | `CanUseGcal \| CanPublishSetorSolicitacao` |
| GET | `/api/integrations/google/calendars/` | ![Stable](https://img.shields.io/badge/-stable-green) | Calendários da conta conectada | `CanUseGcal` |
| POST | `/api/integrations/google/select-calendar/` | ![Stable](https://img.shields.io/badge/-stable-green) | Escolher calendário de trabalho | `CanUseGcal` |
| GET | `/api/integrations/google/events/` | ![Stable](https://img.shields.io/badge/-stable-green) | Eventos da conta conectada | `CanUseGcal` |

A Apoio de Coordenação (`CanPublishSetorSolicitacao`, #1656) conecta a própria conta, mas não escolhe
calendário nem lista eventos: publica sempre no calendário da organização. `return_to` padrão:
`/pre-agenda` para quem tem `use_gcal`; `/solicitacoes/publicacao` para os demais (vale também para os
redirects de erro do callback). `publish_block_reason` do `status`: `no_setor_scope` (sem setor vigente),
`google_not_connected`, `google_calendar_not_configured` ou `null` (pode publicar; `publish_ready=true`).

`reconnect_required` do `status` (#2039): `true` quando não há credencial **e** o último evento de
conexão da pessoa foi uma remoção feita pelo sistema (o Google recusou o refresh token com
`invalid_grant`), sem reconexão depois. Nunca conectou ou clicou em "Desconectar": `false`. Com
credencial: sempre `false`. A remoção vem do job diário `probe_google_credentials` (05:00) ou de um
publish/cancel. Exemplo de conta removida pelo sistema:

```json
{
  "connected": false, "google_email": null, "token_expiry": null, "expires_in_days": null,
  "is_expired": false, "default_calendar_id": null,
  "publish_ready": false, "publish_block_reason": "google_not_connected",
  "reconnect_required": true
}
```

---

## 🏢 Administração

### Usuários

`UsuarioAdminViewSet` é `ModelViewSet` com
`permission_classes = [HasPerm("manage_admin_registries")]` para **todas** as
actions, inclusive leitura (`UsuarioAdminViewSet`, `views/admin.py`).

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/usuarios-admin/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar usuários | `manage_admin_registries` |
| POST | `/api/usuarios-admin/` | ![Stable](https://img.shields.io/badge/-stable-green) | Criar usuário | `manage_admin_registries` |
| GET | `/api/usuarios-admin/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Detalhes do usuário | `manage_admin_registries` |
| PUT/PATCH | `/api/usuarios-admin/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Atualizar usuário | `manage_admin_registries` |
| DELETE | `/api/usuarios-admin/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Excluir usuário | `manage_admin_registries` |

### Municípios

`MunicipioViewSet.permission_classes = [HasPerm("manage_admin_registries")]`
sem `get_permissions()` — o gate vale também para leitura (`MunicipioViewSet`, `views/admin.py`).
Consumidores que só precisam popular selects devem usar `/api/options/municipios/`.

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/municipios/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar municípios | `manage_admin_registries` |
| POST | `/api/municipios/` | ![Stable](https://img.shields.io/badge/-stable-green) | Criar município | `manage_admin_registries` |
| GET | `/api/municipios/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Detalhes do município | `manage_admin_registries` |
| PUT/PATCH | `/api/municipios/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Atualizar município | `manage_admin_registries` |

### Projetos

Mesma regra dos municípios: `permission_classes = [HasPerm("manage_admin_registries")]`
para todas as actions (`ProjetoViewSet`, `views/admin.py`). Selects usam `/api/options/projetos/`.

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/projetos/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar projetos | `manage_admin_registries` |
| POST | `/api/projetos/` | ![Stable](https://img.shields.io/badge/-stable-green) | Criar projeto (`fluxo` obrigatório, D14; `SUPER` só com `gerencia` = Superintendência, senão 400 — D19) | `manage_admin_registries` |
| GET | `/api/projetos/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Detalhes do projeto | `manage_admin_registries` |
| PUT/PATCH | `/api/projetos/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Atualizar projeto (gravar `fluxo`/`gerencia` que deixe um `SUPER` fora da Superintendência → 400 — D19) | `manage_admin_registries` |

### Produtos

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/produtos/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar produtos | `manage_admin_registries` \| `manage_purchases_and_materials` \| `run_daily_operations` |
| POST/PUT/PATCH/DELETE | `/api/produtos/` | ![Stable](https://img.shields.io/badge/-stable-green) | Escrita de produto | `IsAuthenticated` + `manage_purchases_and_materials` |

Gate em `ProdutoViewSet.get_permissions` (`views/admin.py`, D11). Selects abertos ficam em `/api/options/produtos/`.

### Grupos (RBAC)

`GroupViewSet.get_permissions()` (`views/admin.py`): `list`/`retrieve`
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
(bloco `router.register(...)`, `v2/backend/apps/core/urls.py`). Tipos de evento são expostos apenas
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

Gate em `GerenciaViewSet.get_permissions` (`views/admin.py`). Campo `pergunta_avaliar_formador` (bool,
padrão `true`; 05/10/2026): `false` tira da Nova Solicitação a pergunta "pretende avaliar o formador?"
nos eventos de projetos da gerência.

Filtros: `?ativo=true|false`, `?search=` (`nome`, `nome_setor`, `nome_exibicao`),
`?ordering=nome|nome_setor|rotulo_ordem` (default `nome_setor`). Sem `ativo` a lista traz
as inativas (a tela de Gerências reativa); as listas de escolha pedem `?ativo=true`.

Os quatro nomes de uma gerência (PR A, 2026-09-29 — um papel por campo):

| Campo | Papel | Quem altera |
|---|---|---|
| `nome` | código interno (seed; aprovação do PR B usa `SUPERINTENDENCIA`) | ninguém, pela tela |
| `nome_setor` | rótulo nas planilhas (chave do import) | import ou admin |
| `setor_canonico` | gate de escopo (Wave 1) | import ou admin |
| `nome_exibicao` | nome que a tela mostra (vazio = usa `nome_setor`) | admin (GerenciasPage) |

`rotulo` (somente leitura) = `nome_exibicao or nome_setor` — nunca cai para `nome`. O
`ProjetoSerializer.gerencia_nome` e o `gerencia_atual.rotulo` de `/api/usuarios-admin/`
usam o mesmo rótulo. No form de usuário (`/api/usuarios-admin/`), `gerencia_id` inativa dá 400,
exceto quando é a lotação atual exibida (`gerencia_atual`), que o form reenvia a cada edição.
Carga inicial dos 13 nomes de prod: comando
`definir_nome_exibicao_gerencias` (dry-run por padrão; `--apply` grava).

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

Gate em `DATRegistroViewSet.get_permissions` (`views/dat.py`).

### Ações

`/api/dat/acoes/` é uma `ListCreateAPIView` (`DATAcoesListCreateView`, `views_controle_dat.py`), não um
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

Gate em `DATAcaoViewSet.get_permissions` (`views/dat_module.py`).

> **Atenção ao ler o código do módulo DAT**: vários `@action(...)` declaram
> `permission_classes=[...]` no decorator, mas os ViewSets sobrescrevem
> `get_permissions()` — e o override **vence**. Quem decide é o `get_permissions()`
> da classe, não o decorator (o próprio código anota isso em
> `DATCompraViewSet.stats`, `DATCompraViewSet.dashboard` e `DATCompraViewSet.pendencias`, `views/dat_module.py`).

### Cadastros

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/dat/cadastros/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar cadastros | `manage_admin_registries` |
| POST | `/api/dat/cadastros/` | ![Stable](https://img.shields.io/badge/-stable-green) | Criar cadastro | `manage_admin_registries` |
| PUT/PATCH | `/api/dat/cadastros/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Atualizar cadastro | `manage_admin_registries` |
| DELETE | `/api/dat/cadastros/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Excluir cadastro | `execute_restricted_operations` |

Gate em `DATCadastroViewSet.get_permissions` (`views/dat_module.py`).

### Compras DAT

A rota é `/api/dat/compras-materiais/` (basename `dat-compra-material`, `v2/backend/apps/core/urls.py`).
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

Gate em `DATCompraViewSet.get_permissions` (`views/dat_module.py`). `CanViewComprasStats` =
`manage_admin_registries` \| `manage_purchases_and_materials` \| `run_daily_operations`
(`rbac/policies.py`) — ou seja, **escrita de compra também é liberada a
Controle**, não só a DAT.

### Coordenadores DAT

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/dat/coordenadores/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar coordenadores | `manage_admin_registries` \| `run_daily_operations` |
| POST | `/api/dat/coordenadores/` | ![Stable](https://img.shields.io/badge/-stable-green) | Criar coordenador | `manage_admin_registries` \| `run_daily_operations` |
| PUT/PATCH | `/api/dat/coordenadores/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Atualizar coordenador | `manage_admin_registries` \| `run_daily_operations` |
| DELETE | `/api/dat/coordenadores/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Excluir coordenador | `execute_restricted_operations` |
| GET | `/api/dat/coordenadores/{id}/alocacoes/` | ![Stable](https://img.shields.io/badge/-stable-green) | Alocações do coordenador | `manage_admin_registries` \| `run_daily_operations` |

Gate em `DATCoordenadorViewSet.get_permissions` (`views/dat_module.py`).

### Áreas DAT — READ-ONLY

`DATAreaViewSet` é `viewsets.ReadOnlyModelViewSet` (`views/dat_module.py`):
**só existem GET de lista e de detalhe**. `POST`, `PUT`, `PATCH` e `DELETE`
retornam `405 Method Not Allowed` — a doc anterior anunciava um `POST` que a rota
nunca aceitou. Cadastro de área é feito pelo Django Admin.

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/dat/areas/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar áreas (`?minimal=true` p/ select) | IsAuthenticated |
| GET | `/api/dat/areas/{id}/` | ![Stable](https://img.shields.io/badge/-stable-green) | Detalhe da área | IsAuthenticated |

`permission_classes = [IsAuthenticated]` (`DATAreaViewSet`, `views/dat_module.py`) — não exige
capability de DAT. A lista já vem filtrada por `ativo=True`.

---

## 📈 Métricas e Dashboards

### Mapa do Brasil

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/api/metrics/map/` | ![Stable](https://img.shields.io/badge/-stable-green) | Dados para mapa | `HasPerm("view_map_metrics")` |
| GET | `/api/metrics/map/coordinators/` | ![Stable](https://img.shields.io/badge/-stable-green) | Mapa por coordenador | `HasPerm("view_map_metrics")` |

Gate em `metrics_map` e `metrics_map_coordinators` (`views/metrics/map_metrics.py`). **Não** existe
`/api/metrics/map/summary/`, nem `/api/metrics/coordinators/`, nem
`/api/metrics/coordinators/{id}/`.

### Métricas de Equipe

Todas sob `/api/metrics/team/`, com a mesma composition
`run_daily_operations | supervise_operations | manage_admin_registries`
(`productivity_metrics` e `quality_metrics`, `views/metrics/dashboard_metrics.py`;
`formadores_metrics`, `views/metrics/formador_metrics.py`).

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
`manage_admin_registries` (`rbac/policies.py`).

---

## 📥 Imports (planilhas)

Todos são `POST` `multipart/form-data` com o arquivo no campo **`file`**, e todos
usam o throttle scope `import` (30/min). O modo de execução vem no query param
**`dry_run`** — o default é `true` (preview); `?dry_run=false` aplica
(`ImportUsuariosView.post`, `views_import_usuarios.py`).

Importação pela tela é só do superusuário (decisão do dono, 02/10/2026): nenhuma capability abre estes endpoints, e os demais perfis recebem 403.

| Endpoint | Permissão |
|----------|-----------|
| `/api/usuarios/import/` | `IsAuthenticated` + `SuperuserOnly` |
| `/api/municipios/import/` | `IsAuthenticated` + `SuperuserOnly` |
| `/api/equipe-gerencia/import/` | `IsAuthenticated` + `SuperuserOnly` |
| `/api/dat/import-cadastros/` | `IsAuthenticated` + `SuperuserOnly` |
| `/api/solicitacoes/import/` | `IsAuthenticated` + `SuperuserOnly` |
| `/api/produtos/import/` | `IsAuthenticated` + `SuperuserOnly` |
| `/api/deslocamentos/import/` | `IsAuthenticated` + `SuperuserOnly` |
| `/api/disponibilidade/import-bloqueios/` | `IsAuthenticated` + `SuperuserOnly` |
| `/api/controle/import-acoes/` | `IsAuthenticated` + `SuperuserOnly` |
| `/api/controle/import-compras/` (alias `/api/import-compras/`) | `IsAuthenticated` + `SuperuserOnly` |

Imports assíncronos (ASQ-005): `POST /api/imports/bloqueios/`
(`IsAuthenticated` + `SuperuserOnly`), `GET /api/imports/` e
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

Registro das rotas em `v2/backend/apps/core/urls.py` (paths `options-*`). **Não** existem
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

`UsuarioLookup` é o único com gate de capability (`views_lookup.py`, D12).

Desde 05/10/2026: `/api/lookup/projetos/` devolve `pergunta_avaliar_formador` por projeto (da gerência;
`true` sem gerência); `/api/lookup/usuarios/` aceita vários papéis em `role` separados por vírgula
(`?role=Formador,Coordenador`, OU) e devolve `avaliavel` (função Formador sem a função Coordenador).

---

## ❤️ Health Checks

| Método | Endpoint | Status | Descrição | Permissão |
|--------|----------|--------|-----------|-----------|
| GET | `/healthz/` | ![Stable](https://img.shields.io/badge/-stable-green) | Health check básico — **na raiz, fora de `/api/`** | público |
| GET | `/healthz/detailed/` | ![Internal](https://img.shields.io/badge/-internal-gray) | DB + Redis + circuit breaker — superuser ou IP interno | 403 caso contrário |
| GET | `/api/readyz/` | ![Stable](https://img.shields.io/badge/-stable-green) | Readiness (DB + Redis) | AllowAny |
| GET | `/api/version/` | ![Stable](https://img.shields.io/badge/-stable-green) | SHA/tag da build em execução | AllowAny |
| GET | `/api/features/` | ![Stable](https://img.shields.io/badge/-stable-green) | Feature flags ativas | **IsAuthenticated** |
| GET/PUT | `/api/config/` | ![Stable](https://img.shields.io/badge/-stable-green) | Configurações operacionais (leitura **e escrita**; o PUT grava só as chaves enviadas: chave ausente mantém o valor atual e chaves que o serializer não conhece ficam no JSON) | `manage_purchases_and_materials` \| `approve_solicitation` |

Provas: `/healthz/` e `/healthz/detailed/` estão em `v2/backend/config/urls.py`
(fora do `include("apps.core.urls")` do path `api/`) — `/api/healthz/` **não existe**.
`/api/features/` usa `@permission_classes([IsAuthenticated])` (view `features`, `views_health.py`),
não `AllowAny`. `/api/config/` aceita `GET` e `PUT` e é gateado por capability
(`config_view`, `views_config.py`), não por `IsAuthenticated`.

---

## 🔐 Permissões

### Classes de Permissão

As classes `IsSuperintendencia`, `IsControleOrSuper`, `IsDATOrSuper` e `IsDAT`
**não existem no código** — o padrão "permission class por nome de grupo" é
banido pelo `rbac_lint` (`v2/backend/apps/core/rbac/__init__.py`, docstring "Nunca fazer";
`apps/core/tests/test_rbac_lint.py`). Autorização é por **capability**, não por
grupo. O que existe:

| Classe | Onde | Semântica |
|--------|------|-----------|
| `AllowAny` | DRF | Acesso público |
| `IsAuthenticated` | DRF | Usuário logado |
| `HasPerm("<codename>")` | `rbac/permissions.py` | Exige a capability; suporta OR (`HasPerm("a") \| HasPerm("b")`) |
| `SuperuserOnly` | `rbac/permissions.py` | Só superuser |
| `IsOwnerOrPrivileged` | `rbac/permissions.py` | Object-level: dono do registro ou `edit_solicitation_as_owner_or_privileged` dentro do escopo (`user_can_access_solicitacao`) |
| `HasSectorAccess` | `rbac/permissions.py` | Escopo por gerência (`EquipeGerencia`) para a grade mensal |
| `Can*` (Policy) | `rbac/policies.py` | Policy nomeada = OR de capabilities com semântica única |

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
# Assistente Administrativo do Controle. Prova: cálculo de `can_approve_super` em `views_basic.py`.
can_approve_super = is_superuser
    OR ("Gerente" IN funcoes AND "Superintendência" IN setores)
    OR ("Assistente Administrativo" IN funcoes AND "Controle" IN setores)
```

Para decisão nova, consuma `GET /api/me/policies/` e leia
`access_solicitation_approvals` (`rbac/policies.py`).

---

## 📄 Paginação

O padrão global é `apps.core.pagination.StandardPagination` (`apps/core/pagination.py`),
ligada via `REST_FRAMEWORK["DEFAULT_PAGINATION_CLASS"]` em `config/settings.py`. Default
`page_size=100` e **honra `?page_size=` até 500** em toda listagem que não sobrescreve
`pagination_class` (#1653). `?page=` também funciona.

> Antes de 2026-08-20 o padrão era `PageNumberPagination` cru (ignorava `?page_size` e
> capava em 100). O #1653 trocou o default global — a descrição antiga é texto legado.

Endpoints com paginador próprio (default/teto diferentes do global):

| Endpoint | Classe | Default | Máx. |
|---|---|---:|---:|
| `/api/deslocamentos/` | `DeslocamentoPagination` (`views_deslocamento.py`) | 50 | 100 |
| `/api/gcal/list/` | `LargePagination` (`pagination.py`) | 200 | 1000 |
| `/api/gcal/dashboard/events/` | `DashboardEventsPagination` (`views_gcal/helpers.py`) | 20 | 100 |
| `/api/usuarios-admin/` | `LargePagination` (`pagination.py`) | 200 | 1000 |

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
| 409 | Conflito (ex: evento já publicado; excluir registro em uso: o `ProtectedError` vira 409 `CONFLICT` com os tipos de registro vinculados no `detail`, nunca os registros) |
| 429 | Rate limit excedido |
| 500 | Erro interno |

### Formato de Erro

`custom_exception_handler` normaliza **toda** resposta de erro para um objeto
plano com `detail` + `code` (+ `errors` quando há erro de campo) —
`apps/core/exceptions.py`. `code` vem em **MAIÚSCULAS**
(`_get_error_code`, `apps/core/exceptions.py`).

```json
{
  "detail": "<mensagem da permission class>",
  "code": "PERMISSION_DENIED"
}
```

### Erros de Validação

Os erros de campo **não** ficam na raiz: são agrupados sob `errors`
(`_standardize_error_response`, `exceptions.py`). Para o `ValidationError` do DRF (o caso comum de
serializer), `code` é `INVALID` — vem do `default_code` da exceção, não do mapa
de nomes (`_get_error_code`, `exceptions.py`).

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

Valores de produção — `REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]` (`v2/backend/config/settings.py`).

| Escopo | Limite | Descrição |
|--------|--------|-----------|
| `anon` | 1000/hour | Usuários não autenticados (por IP) |
| `user` | 6000/hour | Usuários autenticados (por pessoa) |
| `availability_check` | 60/min | Verificação de conflitos |
| `metrics` | 30/min | Métricas (geo + agregações) |
| `reports` | 30/min | Relatórios (agregações pesadas) |
| `gcal_write` | 10/min | Escritas no Google Calendar (publish/batch) |
| `export` | 10/min | Exports CSV/JSON |
| `import` | 30/min | Uploads de importação (balde único por usuário) |
| `login` | 30/minute | `/auth/login/`, por IP |
| `change_password` | 20/min | Troca de senha self-service |
| `oauth` | 10/hour | `/api/oauth/google/start/` |

**Por que estes valores (2026-10)**: `user` precisa caber as telas que se atualizam sozinhas — Pré-agenda
(3 pedidos a cada 20 s), Aprovações (1 a cada 20 s) e Grade Mensal (2 a cada 30 s) somam ~960/h com as três
abertas; 1000/h estourava em ~25 min de Pré-agenda aberta. `anon` e `login` são **por IP**, e o escritório
inteiro sai pelo mesmo endereço. Quem barra força bruta de senha é o bloqueio **por conta**
(`ACCOUNT_LOCKOUT_THRESHOLD` = 10 erros → 15 min; 50 erros somando todos os IPs → 30 min, `views_auth.py`),
que não mudou. O 429 do DRF traz o cabeçalho `Retry-After` (segundos); o frontend o lê em `fetchAPI`
(`error.retryAfter`) e Aprovações, Pré-agenda e Grade Mensal pausam o polling por esse tempo. Antes do Django há o `limit_req`
do nginx do frontend (30 r/s por cliente, rajada de 60, resposta 429 sem `Retry-After`) — ver
[deploy.spec](specs/infra/deploy.spec.md).

**Nota**: fora de produção os limites são relaxados (override em `ENVIRONMENT == "development"` de `REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]`, `settings.py`) —
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
