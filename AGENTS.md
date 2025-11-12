Aprender Sistema v2 — Contexto Consolidado para o Agente

Este arquivo fornece ao agente (Codex/MCP) o contexto permanente do projeto v2, para ser carregado automaticamente a cada sessão. Use-o como referência para decisões, nomes, convenções e restrições. Não repita trechos extensos em mensagens; apenas siga estas diretrizes.

Visão Geral
- Projeto v2. Docker‑first obrigatório.
- Backend: Django 5.1.x + DRF; Celery (worker + beat); PostgreSQL 15; Redis 7.
- Frontend: React (Vite), Tailwind. Dev server com proxy `vite` para `/api` → backend.
- Compose oficial: `v2/infra/docker-compose.yml` com `COMPOSE_PROJECT_NAME=aprender_v2`.
- TZ: America/Fortaleza (armazenamento UTC, exibição local).

Domínio & Modelos (core)
- Usuario (custom), Municipio, Projeto (fluxo=SUPER|NAO_SUPER), TipoEvento.
- Solicitacao (pré‑agenda): `inicio/fim` aware; status `pendente|aprovado|reprovado`.
- AvailabilityBlock (tipo T/P; status aprovado).
- Participation (COORDENADOR, FORMADOR, COORD_ACOMPANHA, CONVIDADO). `guest_email` suportado. Dedup por participação.
- AuditLog (usuario, action, model_name, details, created_at).
- Compra (ETL Compras; idempotência por `external_hash`).
- Deslocamento (D/D1 na grade mensal; período por `start_date/end_date`; idempotência por `external_hash`).
- AcaoControle (AÇÕES — Controle) e AcaoDAT (CADASTROS — DAT); idempotência por `external_hash` estável.

Regras de Disponibilidade & Monthly API
- Endpoint: `GET /api/availability/monthly/?year=&month=&role[&sector][&q]`.
- Retorno: `days`, `legend`, `people`, `cells`, `details_index`.
- Códigos por dia/pessoa: `E` (1 evento), `2` (≥2 eventos), `P` (bloqueio parcial), `T` (bloqueio total), `X` (evento + bloqueio), `D` (deslocamento), `D1` (evento + deslocamento).
- `details_index` chave “row:col” (0‑based) com lista de detalhes contendo `municipio`, `data`, `inicio`, `fim`, `tipo` (ou `mov` para deslocamento).
- Cache Redis: 5 min. Ranking denso por CH mês.

Pré‑agenda (PR4/PR5)
- Actions no ViewSet: `preview_gcal` e `publish`.
- `approve`/`reject`: somente Superintendência; grava AuditLog (`APPROVE`/`REJECT` com `prev_status/new_status` e IP).
- `preview_gcal`: retorna `preview` com `event_id` e `payload`; grava AuditLog `PREVIEW_GCAL`.
- `publish`: enfileira Celery task; retorna 202 quando permitido; respeita `apply_blocked` (retorna 409 quando `GCAL_CLIENT != "google"` sem override).

Google Calendar (PR8)
- Idempotência por `eventId=asv2-{id}`; `sendUpdates='none'` sempre.
- Cliente real via Service Account (`GOOGLE_SERVICE_ACCOUNT_FILE|JSON`). Retry/backoff para 429/5xx; 404 idempotente.
- Factory seleciona Fake/Google por `GCAL_CLIENT`. `/api/features/` expõe `apply_blocked = (GCAL_CLIENT != "google")`.

RBAC & Permissões
- Grupos: Superintendência, Controle, Coordenador, Formador, DAT, Gerência.
- `IsSuperintendencia`: approve/reject.
- `IsControleOrSuper`: pré‑agenda preview/publish e import‑compras.
- `IsCoordenadorOrDAT`: criação de solicitações.
- `IsDATOrSuper`: endpoints DAT (AcaoDAT list/create).
- Superuser sempre tem acesso.

ETLs (fontes locais CSV/XLSX; relatórios em `out_etl/*.json`)
- Acompanhamento (Solicitacao + Participation), Compras, Deslocamento, Ações (Controle), Cadastros (DAT).
- Idempotência por `external_hash` estável (não incluir campos mutáveis). Em updates, detectar changes antes de salvar.

URLs & Convenções
- App `apps.core.urls` NUNCA prefixa `api/` — o prefixo é adicionado por `config/urls.py`.
- Rotas relevantes: `/api/me/`, `/api/features/`, `/api/solicitacoes/`, `/api/availability/monthly/`, `/api/controle/acoes/`, `/api/dat/acoes/`.
- `/api/me/` inclui `id, username, email, first_name, last_name, name, groups, is_superuser, is_superintendencia`.

Frontend (v2/frontend)
- Dev: Vite com proxy `/api` → `http://localhost:8002` (evita CORS/CSRF). Fetch sempre `/api/...` com `credentials:'include'`.
- Páginas chave:
  - Pré‑agenda: approve/reject (Super), preview/publish (Controle), features.apply_blocked.
  - Grade Mensal: duas grades (“Formadores” e “Coordenadores”), filtros compartilhados (ano/mês/sector/q), virtualização de linhas, detalhes por “row:col”, export CSV por grade, fins de semana em cinza e “hoje” destacado.
  - Controle/DAT: uploads CSV/XLSX (dry-run/apply) e listagens com filtros; preview do report JSON direto para validação.
  - Qualidade: `/qualidade/pendencias` para resolver EtlPending, `/qualidade/aliases` para CRUD dos aliases.

Ops/DX
- Subir stack: `cd v2 && make up`.
- Health: `make readyz` / `curl http://localhost:8002/api/features/`.
- Celery: `make up-worker`, `make up-beat`, `make logs-worker-last`.
- Seeds: `make seed-rbac`.
- ETL Acompanhamento: `make etl-acomp-dry` / `make etl-acomp-apply`.
- ETL Compras: POST `/api/controle/import-compras/?dry_run=true` (upload); relatório em `out_etl/import_compras_report.json`.
- ETL Deslocamento/Ações/DAT: targets específicos no Makefile; relatórios em `out_etl/`.

Gotchas
- Sempre `COMPOSE_PROJECT_NAME=aprender_v2` (evitar stacks paralelos).
- Rebuild `web` quando criar/alterar arquivos copiados no build.
- Respeitar `TZ` e formatação local em monthly; armazenamento UTC no DB.
- Attendees no GCal derivam das Participation (roles citados). `T` (coluna de convidados da planilha) não vira Participation.
- `external_hash` (ETL) e `eventId` (GCal) são as chaves de idempotência — manter cálculo consistente (dry‑run e apply).

Histórico de PRs (estado atual)
- PR1..PR6: base de modelos, ETLs e endpoints — OK.
- PR7: Deslocamento (modelo + ETL + D/D1 na Monthly) — OK.
- PR8: GoogleCalendarClient real + factory + testes — OK.
- PR9: Ações (Controle) / Cadastros (DAT) — modelos, ETL, APIs — OK.
- PR10: /api/me (name) + filtros adicionais em `/api/solicitacoes/` + UI Pré‑agenda — OK.
- PR11: UI Grade Mensal (duas grades) — OK.

Padrões de Código
- Imports backend: `apps.core...`, `apps.dat_ingest...` (evitar `v2/backend` nos módulos).
- Relatórios ETL: `Path(settings.BASE_DIR)/"out_etl"`.
- URLs no app sem `api/` (prefixado no `config/urls.py`).
- Use `Q()` para compor filtros com OR (evitar unir QuerySets com `|`).

Planejamento Futuro (sugestões)
- UI Controle/DAT (listas + criação manual completa).
- Insights/Dashboard DAT (agregações e export CSV).
- OpenAPI/Docs (drf‑spectacular) com exemplos e erros (403/409).
- Observabilidade ETLs (AuditLog por execução + endpoint de últimos relatórios).
