# Mapa Atual de Permissões — Aprender Sistema v2

**Gerado em**: 2026-04-27
**Branch**: main (`73cfaa0` — pós-stabilization)

## 0. Estado pós-Stabilization

Sistema pós-**RBAC Access Policy Realignment** (11 PRs, 2026-04-26) + **Stabilization** (6 PRs, 2026-04-27). As "lacunas críticas" C1-C3 e altos A1-A3 listadas em análise anterior **foram corrigidas** pelas Ondas 1-2 (PRs #1250, #1256).

**16 capabilities, 15 policies, 8 atores** mapeados em SSOT canônica. Matriz Viva implementada (PR #1283, 74+ tests).

**Pendência conhecida**: issue #1284 (HomeStats `upcoming_events` fail-safe scope, P0) está coberta pelo PR aberto **#1286** (não mergeado neste momento) — ver §6.

---

## 1. Catálogo de 16 Capabilities Funcionais

**SSOT**: `v2/backend/apps/core/services/functional_permissions_seed.py` (linhas 36-159)

| Codename | Label | Categoria | Grupos | Usado em Policy | Status |
|----------|-------|-----------|--------|-----------------|--------|
| `approve_solicitation` | Aprovar solicitações | solicitacao | Superintendência | `access_audit_logs`, `manage_solicitacao_status` | OK — D1 |
| `approve_solicitation_batch` | Aprovar lote | solicitacao | Gerente, Superintendência | `access_audit_logs`, `manage_solicitacao_status` | OK — D1 |
| `create_solicitation` | Criar solicitações | solicitacao | Coordenador, Apoio, Gerente | — | OK — Onda 1 A1 |
| `edit_solicitation_as_owner_or_privileged` | Editar próprias | solicitacao | Gerente, Coordenador, Apoio | — | OK — D5 |
| `execute_restricted_operations` | Operações restritas | solicitacao | Superintendência | — | Reservado |
| `import_spreadsheet` | Importar planilhas | importacao | DAT | `import_*` | OK — D2 |
| `manage_admin_registries` | Administrar cadastros | cadastros_administrativos | DAT | `access_audit_logs`, `view_compras_*` | OK — D2 |
| `manage_purchases_and_materials` | Administrar compras | cadastros_administrativos | DAT, Controle | `view_compras_stats` | OK — D2 |
| `operate_preagenda` | Operar pré-agenda | operacao | Controle | `access_audit_logs`, `manage_solicitacao_status` | OK — D1 |
| `run_daily_operations` | Rotinas operacionais | operacao | Controle | `view_compras_*`, `import_compras` | OK — D1 |
| `supervise_operations` | Supervisão gerencial | supervisao | Diretoria | — | Reservado |
| `view_all_availability` | Ver todas disponibilidades | operacao | **Controle, Gerente** | `import_availability_blocks` | OK — Bug 1 fix |
| `view_compras_dashboard` | Dashboard compras | dashboard | Diretoria | `view_compras_dashboard` | OK — D7 |
| `view_map_metrics` | Métricas geográficas | dashboard | Diretoria | `view_map_metrics` | OK — D7 |
| `view_overview_dashboard` | Dashboard geral | dashboard | Diretoria | `view_overview_dashboard` | OK — D7 |
| `manage_internal_actions` | Ações internas | cadastros_administrativos | **(zero grupos)** | — | OK — Onda 1 C3 |

---

## 2. Catálogo de 15 Policies Públicas

**SSOT**: `v2/backend/apps/core/rbac/policies.py` (`PUBLIC_POLICY_KEYS`)

| Policy Key | Classe | Composição (OR) | Endpoint | Status |
|-----------|--------|-----------------|---------|--------|
| `access_audit_logs` | `CanAccessAuditLogs` | `manage_admin_registries \| operate_preagenda \| approve_solicitation \| approve_solicitation_batch` | AuditLogViewSet | OK — D1 |
| `manage_solicitacao_status` | `CanManageSolicitacaoStatus` | `operate_preagenda \| approve_solicitation` | GCal | OK — D1 |
| `view_compras_dashboard` | `CanViewComprasDashboard` | `view_compras_dashboard \| manage_admin_registries` | ComprasViewSet | OK — Onda 2 A2 |
| `view_compras_pendencias` | `CanViewComprasPendencias` | 4 caps | ComprasViewSet.pendencias | OK — D2 |
| `view_compras_stats` | `CanViewComprasStats` | `manage_purchases_and_materials \| run_daily_operations` | ComprasViewSet.stats | OK — D2 |
| `view_overview_dashboard` | `CanViewOverviewDashboard` | `view_overview_dashboard` | Frontend | OK — Onda 1 C1 |
| `view_map_metrics` | `CanViewMapMetrics` | `view_map_metrics` | Frontend | OK — Onda 1 C1 |
| `view_reports` | `CanViewReports` | 3 caps | Reports | OK — D2 |
| `use_gcal` | `CanUseGcal` | `operate_preagenda \| approve_solicitation` | GCal | OK — D1 |
| `view_all_availability` | `CanViewAllAvailability` | `view_all_availability` | MonthlyAvailabilityView | OK — Bug 1, D6 |
| `import_availability_blocks` | `CanImportAvailabilityBlocks` | `import_spreadsheet \| view_all_availability` | Imports | OK — D2 |
| `import_compras` | `CanImportCompras` | 3 caps | Compras | OK — D2 |
| `import_generic_spreadsheet` | `CanImportGenericSpreadsheet` | `import_spreadsheet \| run_daily_operations` | SpreadsheetImportView | OK — D2 |
| `manage_admin_registries` | `CanManageAdminRegistries` | `manage_admin_registries` | Admin | OK — D2 |
| `manage_purchases_and_materials` | `CanManagePurchasesAndMaterials` | `manage_purchases_and_materials` | Admin | OK — D2 |

---

## 3. Páginas Frontend (14 principais)

| Página | Rota | Condição Real (pós-fix) | Status |
|--------|------|------------------------|--------|
| Home | `/home` | `IsAuthenticated` | OK |
| Aprovações | `/solicitacoes/aprovacoes` | Estado atual: `useCanAccess` consome capability `approve_solicitation_batch` (não há policy pública dedicada). Futuro ideal: criar policy `access_solicitation_approvals` que componha `approve_solicitation \| approve_solicitation_batch` e expor em `PUBLIC_POLICY_KEYS`. | OK funcional — backlog de hardening |
| Bloqueios | `/solicitacoes/bloqueios` | `IsAuthenticated` (queryset scoped) | OK — D6 |
| Deslocamentos | `/solicitacoes/deslocamentos` | `IsAuthenticated` (`get_queryset` scoped) | OK — Onda 1 C2 |
| Grade Mensal | `/solicitacoes/disponibilidade` | `CanViewAllAvailability \| HasSectorAccess` | OK — Bug 1 |
| Meus Eventos | `/solicitacoes/meus-eventos` | `IsAuthenticated` | OK |
| Dashboard Geral | `/dashboards` | `is_superuser \| inDiretoria` | OK — Onda 1 C1 |
| Dashboard Compras | `/dashboards/compras` | `useCanAccess.can('view_compras_dashboard')` | OK — Onda 2 A2 |
| Dashboard Equipe | `/dashboards/equipe` | `is_superuser \| inDiretoria \| inDAT` | OK — Onda 1 C1 |
| Dashboard GCal | `/dashboards/gcal` | `is_superuser \| inDiretoria \| inDAT \| inControle` | OK — Onda 1 C1 |
| Mapa Brasil | `/mapa-brasil` | `is_superuser \| inDiretoria \| inDAT` | OK — Onda 1 C1 |
| Ações Internas | `/acoes-internas` | `is_superuser` (capability sem grupos) | OK — Onda 1 C3 |
| DAT / Admin | `/dat/admin` | `canDAT` | OK — D2 |
| Controle / Menu | `/controle` | `canControle` | OK — D1 |

---

## 4. Endpoints Backend (principais)

| Endpoint | Método | `permission_classes` | Status |
|----------|--------|---------------------|--------|
| `/api/auth/users/` | GET/POST | `HasPerm("manage_admin_registries")` | OK |
| `/api/audit-logs/` | GET | `CanAccessAuditLogs` | OK — D1 |
| `/api/ciclos-acoes/` | GET/POST | `HasPerm("manage_internal_actions")` | OK — Onda 1 C3 |
| `/api/acoes-instancia/` | GET | `HasPerm("manage_internal_actions")` | OK — Onda 1 C3 |
| `/api/availability/blocks/` | GET/POST | `IsAuthenticated` | OK — D5 |
| `/api/availability/monthly/` | GET | `IsAuthenticated, CanViewAllAvailability \| HasSectorAccess` | OK — Bug 1, D6 |
| `/api/deslocamentos/` | GET | `IsAuthenticated` (`get_queryset` scoped) | OK — Onda 1 C2 |
| `/api/dat-area/` | GET/POST | `HasPerm("manage_admin_registries")` | OK — D2 |
| `/api/dat-compra/dashboard/` | GET | `CanViewComprasDashboard` | OK — Onda 2 A2 |
| `/api/dat-compra/stats/` | GET | `CanViewComprasStats` | OK — D2 |
| `/api/solicitacoes/` | POST | `HasPerm("create_solicitation")` via `get_permissions` | OK — Onda 1 A1 |
| `/api/solicitacoes/{id}/approve/` | POST | `CanManageSolicitacaoStatus` | OK — D1 |
| `/api/me/events/` | GET | `IsAuthenticated` | OK — Epic 2 |
| `/api/me/policies/` | GET | `IsAuthenticated` | OK — Epic 4.4 |

> Endpoints críticos mapeados e sem lacunas críticas conhecidas; backlog de hardening ainda aberto (ver §7).

---

## 5. Matriz Ator → Permissions (8 atores)

| Ator | Capabilities | Policies | Status |
|------|--------------|----------|--------|
| **Superuser** | **(todas — bypass)** | **(todas)** | Escape hatch |
| **DAT** | `manage_admin_registries`, `import_spreadsheet`, `manage_purchases_and_materials` | 9/15 | OK — D2 (transversal) |
| **Controle** | `manage_purchases_and_materials`, `operate_preagenda`, `run_daily_operations`, `view_all_availability` | 8/15 | OK — D1 (transversal) |
| **Diretoria** | `view_compras_dashboard`, `supervise_operations`, `view_overview_dashboard`, `view_map_metrics` | 5/15 | OK — D7 |
| **Gerente** | `approve_solicitation_batch`, `create_solicitation`, `edit_solicitation_as_owner_or_privileged`, `view_all_availability` | 4/15 | OK — D1 |
| **Coordenador** | `create_solicitation`, `edit_solicitation_as_owner_or_privileged` | 0/15 | OK — D6 (EquipeGerencia) |
| **Apoio Coord** | `create_solicitation`, `edit_solicitation_as_owner_or_privileged` | 0/15 | OK — D6 |
| **Formador** | **(zero)** | 0/15 | OK — caso especial |

---

## 6. Lacunas REAIS (validadas em código)

Todas as divergências C1-C3/A1-A3 foram corrigidas:

- **C1 (Dashboards hardcoded)** ✅ Onda 1 PR #1250
- **C2 (Deslocamentos scope)** ✅ Onda 1 PR #1250
- **C3 (Ações Internas IsAdminUser)** ✅ Onda 1 PR #1250
- **A1 (SolicitacaoViewSet.create)** ✅ Onda 1 PR #1250
- **A2 (Dashboard Compras)** ✅ Onda 2 PR #1256
- **A3 (Queryset-only)** ✅ Por design D6

**Lacuna crítica em PR aberto (não mergeado neste momento)**:

- **#1284 — HomeStats `upcoming_events` fail-safe scope (P0)** → corrigido no PR **#1286** (`OPEN`, base `main`). Endereça também #1260 (HomeStatsView remove hardcode de grupos). Quando #1286 mergear, esta entrada migra para "histórico".

---

## 7. Backlog de hardening ainda aberto

Itens identificados durante a Stabilization que **não bloqueiam produção** mas estão registrados para hardening incremental:

| Issue | Tipo | Tema | Estado |
|-------|------|------|--------|
| **#1258** | A1 — backend gate | `ProdutoViewSet.list` exige capability operacional explícita (hoje só `IsAuthenticated`) | OPEN |
| **#1259** | A2 — backend gate | `UsuarioLookup` exige capability (hoje só `IsAuthenticated`) | OPEN |
| **#1260** | A4 — frontend cleanup | `HomeStatsView` remove hardcode de grupos | OPEN (coberta por PR #1286) |
| **#1261** | A5 — test meta | Test sentinela meta para `SolicitacaoViewSet` permission resolution | OPEN |
| **#1276** | governança | Gerar Markdown a partir de `apps/core/rbac/matrix.py` (doc auto-sync) | OPEN |
| **#1284** | A6 — P0 fix | `HomeStats upcoming_events` fail-safe scope | OPEN (coberta por PR #1286) |

> Backlog conservador: priorizar #1284/#1260 (já em PR #1286), depois #1258/#1259 (capability gates faltando) numa onda 4 e #1261/#1276 em governança contínua.

---

## 8. Matriz Página × Funcionalidade × Acesso

Esta seção aprofunda o mapeamento do §3 (Páginas), descendo ao nível de funcionalidades internas (botões, formulários, ações) e mapeando quais endpoints backend cada uma invoca. Diferencia-se do §3 por não apenas registrar visibilidade de rota, mas detalhar o contrato API funcional em nível de UI.

**Nota sobre Status**: `INCERTO` indica que não foi possível confirmar 100% via leitura estática de código — recomenda-se validação manual. A quantidade limitada de `INCERTO` reflete a maturidade do RBAC pós-Realignment + Stabilization.

---

### 8.1 Home — `/home`

**Componente**: [HomePage.tsx](../frontend/src/pages/Home/HomePage.tsx)
**Visibilidade**: `IsAuthenticated` (cards renderizados condicionalmente conforme `usePermissions` / `useCanAccess`)

| Funcionalidade | UI | Endpoint | `permission_classes` | Quem acessa | Scope | Status |
|---|---|---|---|---|---|---|
| Listar KPIs (stats) | Cards com badges | `GET /api/stats/home/` | `IsAuthenticated` | Todos | self via `request.user` | OK |
| Link "Meu Painel" | Card | — (navegação) | — | Todos autenticados | — | OK |
| Link "Enviar Solicitação" | Card | — (navegação) | `canCoordenador` (condicional) | Coord, Apoio, Gerente | — | OK |
| Link "Minhas Solicitações" | Card com badge | — (navegação) | `canCoordenador` | Coord, Apoio, Gerente | — | OK |
| Link "Aprovações" | Card | — (navegação) | `canApproveSuper` | Superintendência, DAT | — | OK |
| Link "Dashboard Geral" | Card "Análises" | — (navegação) | `isAdmin` | DAT, Superuser | — | OK |
| Link "Dashboard Equipe" | Card | — (navegação) | `isManager` | Gerente | — | OK |
| Exibir "Aprovações Pendentes" | KPI Card (red) | `GET /api/stats/home/` | `IsAuthenticated` | Se `canApproveSuper` | self | INCERTO — issue #1284 (HomeStats `upcoming_events` fail-safe scope) coberta por PR #1286 |

---

### 8.2 Solicitações (Minhas) — `/solicitacoes/minhas`

**Componente**: [MySolicitacoesPage.tsx](../frontend/src/pages/Solicitacoes/MySolicitacoesPage.tsx)
**Visibilidade**: `IsAuthenticated` (queryset scoped a `request.user`)

| Funcionalidade | UI | Endpoint | `permission_classes` | Quem acessa | Scope | Status |
|---|---|---|---|---|---|---|
| Listar próprias solicitações | Tabela | `GET /api/solicitacoes/?mine=true` | `IsAuthenticated` | Todos | `usuario=request.user` em queryset | OK |
| Filtrar por status | Select | — (client-side) | — | Todos | — | OK |
| Buscar por município/projeto | `Input.Search` | `GET /api/solicitacoes/?mine=true&q=...` | `IsAuthenticated` | Todos | `usuario=request.user` | OK |
| Botão "Nova Solicitação" | Button primária | navega `/solicitacoes/nova` | `canCoordenador` (frontend) | Coord, Apoio, Gerente | — | OK |
| Editar solicitação | `EditOutlined` por linha | `PATCH /api/solicitacoes/{id}/` | `IsOwnerOrPrivileged` | Owner ou DAT/Super | owner check | OK |
| Excluir solicitação | `DeleteOutlined` + `Popconfirm` | `DELETE /api/solicitacoes/{id}/` | `IsOwnerOrPrivileged` | Owner ou DAT/Super | owner check + state validation | OK |
| Ver Google Meet | Hyperlink | — (URL externa) | — | Todos (se aprovado) | — | OK |

---

### 8.3 Aprovações — `/solicitacoes/aprovacoes`

**Componente**: [ApprovalsPage.tsx](../frontend/src/pages/Aprovacoes/ApprovalsPage.tsx)
**Visibilidade**: `useCanAccess` consome capability `approve_solicitation_batch` (não há policy pública dedicada — ver §3 e §9 sobre `access_solicitation_approvals` ideal)

| Funcionalidade | UI | Endpoint | `permission_classes` | Quem acessa | Scope | Status |
|---|---|---|---|---|---|---|
| Listar SUPER pendentes | Tabela | `GET /api/solicitacoes/?flow=SUPER&status=pendente` | `IsAuthenticated` | Todos (filtrado por backend) | — | OK |
| Filtrar por status | Select | — (query param) | — | Todos | — | OK |
| Buscar por município/projeto/autor | `Input.Search` | `GET /api/solicitacoes/?q=...&flow=SUPER` | `IsAuthenticated` | Todos | — | OK |
| Preview payload GCal | `EyeOutlined` | `POST /api/solicitacoes/{id}/preview-gcal/` | `CanUseGcal` | Controle, Superintendência | — | OK |
| Aprovar (individual) | `CheckOutlined` | `PATCH /api/solicitacoes/{id}/approve/` | `HasPerm("approve_solicitation")` | Superintendência | — | OK |
| Reprovar (individual) | `CloseOutlined` (danger) | `PATCH /api/solicitacoes/{id}/reject/` | `HasPerm("approve_solicitation")` | Superintendência | — | OK |
| Selecionar múltiplas | Checkbox table selection | — (state) | — | Approvers | — | OK |
| Aprovar em lote | Button "Aprovar Selecionadas" | `POST /api/solicitacoes/batch-approve/` | `HasPerm("approve_solicitation")` (via `@action permission_classes`) | Superintendência (+ superuser via bypass) | Service usa `select_for_update(skip_locked)`; limite 100 IDs | OK |
| Reprovar em lote | Button "Reprovar Selecionadas" | `POST /api/solicitacoes/batch-reject/` | `HasPerm("approve_solicitation")` (via `@action permission_classes`) | Superintendência (+ superuser via bypass) | Idem batch-approve | OK |

> **Observação registrada (não bloqueante)**: a capability `approve_solicitation_batch` existe no seed e está atribuída a Gerente + Superintendência, mas os endpoints `batch-approve` / `batch-reject` exigem a capability `approve_solicitation` (mais restrita, hoje só Superintendência). Em consequência, **Gerente não consegue usar batch endpoints com a configuração atual**. Pode ser intent (batch = paridade com aprovação individual) ou divergência semântica de naming. Decisão de negócio fica para issue futura `RBAC: decidir semântica de approve_solicitation_batch nos endpoints batch` — não mexer no código sem essa decisão.

---

### 8.4 Bloqueios — `/solicitacoes/bloqueios`

**Componente**: [Solicitacoes.tsx](../frontend/src/pages/Solicitacoes.tsx) → painel "Bloqueios"
**Visibilidade**: `IsAuthenticated` (queryset scoped; privilegiados veem todos; ver D6)

| Funcionalidade | UI | Endpoint | `permission_classes` | Quem acessa | Scope | Status |
|---|---|---|---|---|---|---|
| Listar bloqueios | `MyBlocksTable` | `GET /api/solicitacoes/bloqueios/` | `IsAuthenticated` | Todos | owner=`request.user` ou gerência | OK |
| Criar novo bloqueio | `BlockForm` + Button | `POST /api/solicitacoes/bloqueios/` | `IsAuthenticated` | Todos (Formador, Coord) | auto `usuario=request.user` | OK — RD-02/RD-03 |
| Preencher datas/tipo | Form inputs | — (state) | — | — | — | OK |
| Excluir bloqueio | Delete por linha | `DELETE /api/solicitacoes/bloqueios/{id}/` | `IsAuthenticated` (owner check) | Owner ou privilegiados | owner via `get_queryset` | OK |
| Importar bloqueios CSV/XLSX | `ImportUploader` | `POST /api/imports/bloqueios/` | `CanImportAvailabilityBlocks` | DAT, Controle | — | OK |

---

### 8.5 Grade Mensal (Disponibilidade) — `/solicitacoes/disponibilidade`

**Componente**: [Disponibilidade.tsx](../frontend/src/pages/Disponibilidade.tsx) + [MonthlyPage.tsx](../frontend/src/pages/Disponibilidade/MonthlyPage.tsx)
**Visibilidade**: `IsAuthenticated, CanViewAllAvailability | HasSectorAccess` (Bug 1 fix, D6)

| Funcionalidade | UI | Endpoint | `permission_classes` | Quem acessa | Scope | Status |
|---|---|---|---|---|---|---|
| Visualizar grade mensal | Grid interativo | `GET /api/availability/monthly/?year=...&month=...` | `CanViewAllAvailability \| HasSectorAccess` | Todos (scope por gerência) | gerência do user ou todos se privilegiado | OK |
| Filtro por usuário | Dropdown | — (query param) | — | Gerente, Coord | filtra por `EquipeGerencia` | OK |
| Filtro por projeto/setor | Select | — (query param) | — | Todos | — | OK |
| Detalhes em célula | `DetailsDrawer` | — (modal client-side) | — | — | — | OK |
| Criar bloqueio | Form interno | `POST /api/availability-blocks/` | `IsAuthenticated` | Todos (Formador) | auto `usuario=request.user` | OK |
| Listar próprios bloqueios | Seção "Meus Bloqueios" | `GET /api/availability-blocks/?owner=me` | `IsAuthenticated` | Todos | self | OK |
| Excluir bloqueio próprio | Delete em lista | `DELETE /api/availability-blocks/{id}/` | `IsAuthenticated` (owner check) | Owner | self via `get_queryset` | OK |
| Importar disponibilidades | `ImportUploader` | `POST /api/imports/bloqueios/` | `CanImportAvailabilityBlocks` | DAT, Controle | — | OK |

---

### 8.6 Deslocamentos — `/solicitacoes/deslocamentos`

**Componente**: [DeslocamentosPage.tsx](../frontend/src/pages/Deslocamentos/DeslocamentosPage.tsx)
**Visibilidade**: `IsAuthenticated` (queryset scoped, Onda 1 C2)

| Funcionalidade | UI | Endpoint | `permission_classes` | Quem acessa | Scope | Status |
|---|---|---|---|---|---|---|
| Listar deslocamentos | Tabela paginada | `GET /api/deslocamentos/` | `IsAuthenticated` | Todos (Controle, DAT, Coord) | filtro por usuário/gerência (Onda 1 C2 — `EquipeGerencia`) | OK |
| Filtro por usuário | Select | `?usuario_id=...` | `IsAuthenticated` | Coord, Controle, DAT | filtra por `EquipeGerencia` ou todos se privilegiado | OK |
| Filtro por data range | RangePicker | `?data_inicio=...&data_fim=...` | `IsAuthenticated` | Todos | — | OK |
| Filtro origem/destino | Input | `?origem=...&destino=...` | `IsAuthenticated` | Todos | — | OK |
| Criar deslocamento | Modal form + `PlusOutlined` | `POST /api/deslocamentos/` | `IsAuthenticated` | Controle, Coord | auto `usuario=request.user` ou selecionado | OK |
| Editar | `EditOutlined` | `PUT /api/deslocamentos/{id}/` | `IsAuthenticated` (owner check) | Owner ou privilegiados | owner via `get_queryset` | OK |
| Excluir | `DeleteOutlined` + `Popconfirm` | `DELETE /api/deslocamentos/{id}/` | `IsAuthenticated` (owner check) | Owner ou privilegiados | owner via `get_queryset` | OK |
| Importar deslocamentos | `ImportUploader` | `POST /api/imports/deslocamentos/` | `HasPerm("import_spreadsheet")` | Controle, DAT | — | OK |

---

### 8.7 Meus Eventos — `/solicitacoes/meus-eventos`

**Componente**: [MeusEventosPage.tsx](../frontend/src/pages/MeusEventos/MeusEventosPage.tsx)
**Visibilidade**: `IsAuthenticated` (Epic 2 — feature criada no Realignment)

| Funcionalidade | UI | Endpoint | `permission_classes` | Quem acessa | Scope | Status |
|---|---|---|---|---|---|---|
| Listar eventos como participante | Tabela paginada | `GET /api/me/events/?page=...` | `IsAuthenticated` | Todos (Formador primário) | `request.user` em `Solicitacao.aprovado` | OK |
| Paginação | Pagination | — (query param) | — | — | — | OK |
| Colunas (data, horário, município, projeto, tipo, local, Meet) | denormalized | — | — | — | — | OK |
| Link Google Meet | Hyperlink | — (URL externa) | — | Todos | — | OK |

---

### 8.8 Dashboard Geral — `/dashboards`

**Componente**: [DashboardsPage.tsx](../frontend/src/pages/Dashboards/DashboardsPage.tsx)
**Visibilidade**: `is_superuser \| inDiretoria` (Onda 1 C1, alinhado com D7)

| Funcionalidade | UI | Endpoint | `permission_classes` | Quem acessa | Scope | Status |
|---|---|---|---|---|---|---|
| KPIs (Eventos Futuros, Aprovados, Participantes, Pendentes) | Cards `Statistic` | `GET /api/dashboard/overview/` | `HasPerm("view_overview_dashboard")` | Diretoria, Superuser | — | OK |
| Gráfico eventos por fluxo | Bar chart | — (denormalized) | — | Diretoria | — | OK |
| Gráfico eventos por gerência | Pie/Bar | — (denormalized) | — | Diretoria | — | OK |
| Top coordenadores | Lista/tabela | — (denormalized) | — | Diretoria | — | OK |
| Recarregar | `ReloadOutlined` | `GET /api/dashboard/overview/` (refetch) | `HasPerm("view_overview_dashboard")` | Diretoria | — | OK |
| Exportar CSV (stub) | `DownloadOutlined` | — (não implementado) | — | Diretoria | — | pendente |

---

### 8.9 Dashboard Compras — `/dashboards/compras`

**Componente**: [ComprasDashboardPage.tsx](../frontend/src/pages/Dashboards/ComprasDashboardPage.tsx)
**Visibilidade**: `useCanAccess.can('view_compras_dashboard')` (Onda 2 A2)

| Funcionalidade | UI | Endpoint | `permission_classes` | Quem acessa | Scope | Status |
|---|---|---|---|---|---|---|
| Métricas agregadas | Cards com `Progress` | `GET /api/dat-compra/dashboard/` | `CanViewComprasDashboard` | Diretoria, DAT | — | OK |
| Filtro por projeto | Select | — (query param) | — | Diretoria, DAT | — | OK |
| Filtro por UF | Select | — (query param) | — | Diretoria, DAT | — | OK |
| Rankings (Top produtos, municípios) | Tabelas | — (denormalized) | — | Diretoria, DAT | — | OK |
| Painel de pendências | Tabela | `GET /api/dat-compra/pendencias/` | `CanViewComprasPendencias` | DAT, Controle, Diretoria | — | OK |
| Recarregar | `ReloadOutlined` | refetch dashboard | `CanViewComprasDashboard` | Diretoria, DAT | — | OK |

---

### 8.10 Dashboard Equipe — `/dashboards/equipe`

**Componente**: [EquipeDashboardPage.tsx](../frontend/src/pages/Dashboards/EquipeDashboardPage.tsx)
**Visibilidade**: `is_superuser \| inDiretoria \| inDAT` (Onda 1 C1)
**API consumida**: 3 endpoints distintos de [teamMetrics.ts](../frontend/src/api/teamMetrics.ts) — não há `/api/dashboard/equipe/` único.

| Funcionalidade | UI | Endpoint | `permission_classes` | Quem acessa | Scope | Status |
|---|---|---|---|---|---|---|
| Métricas de produtividade (eventos criados, tempo médio aprovação, taxa erro GCal) | Cards `Statistic` | `GET /api/metrics/team/productivity/?days=N` | composition β `run_daily_operations \| supervise_operations \| manage_admin_registries` | Controle, Diretoria, DAT | filtro `days` (7/15/30) | OK — Onda 2 A3 (β preserva Lote 4.2.b2) |
| Ranking de formadores | Bar chart + tabela com export CSV | `GET /api/metrics/team/formadores/?days=N` | composition β (idem) | Controle, Diretoria, DAT | filtro `days` | OK — Onda 2 A3 |
| Métricas de qualidade (rejeição, conflitos, re-trabalho, tempo publicação) | Cards `Statistic` com Progress | `GET /api/metrics/team/quality/?days=N` | composition β (idem) | Controle, Diretoria, DAT | filtro `days` | OK — Onda 2 A3 |
| Filtro de período (7/15/30 dias) | `Select` | aplicado nos 3 endpoints como `?days=N` | — | — | — | OK |
| Exportar CSV | `DownloadOutlined` | client-side (gera CSV a partir de `formadoresData`) | — | Controle, Diretoria, DAT | — | OK |

> Tests RBAC: [test_metrics_team_rbac.py](../backend/apps/core/tests/test_metrics_team_rbac.py) cobre os 3 endpoints com a composition β.

---

### 8.11 Dashboard GCal — `/dashboards/gcal`

**Componente**: [GCalDashboardPage.tsx](../frontend/src/pages/Dashboards/GCalDashboardPage.tsx)
**Visibilidade**: `is_superuser \| inDiretoria \| inDAT \| inControle` (Onda 1 C1)

| Funcionalidade | UI | Endpoint | `permission_classes` | Quem acessa | Scope | Status |
|---|---|---|---|---|---|---|
| Métricas GCal (success rate, drift, erros) | Cards/charts | `GET /api/gcal/dashboard/` | `CanUseGcal \| IsAdmin` | Controle, Diretoria, DAT | — | OK |
| Alertas de erro | `Alert` | — (denormalized) | — | Controle, Diretoria | — | OK |
| Retry batch failed | Button | `POST /api/gcal/dashboard/batch/reapply/` | `IsAuthenticated, CanUseGcal` (`operate_preagenda \| approve_solicitation`) | Controle, Superintendência | throttle `gcal_write` 10/min; OAuth check (sem `GoogleOAuthCredential` → 403 `google_not_connected` quando `GCAL_AUTH_MODE=oauth`); limite 500 IDs | OK |

---

### 8.12 Mapa Brasil — `/mapa-brasil`

**Componente**: [MapaBrasilPage.tsx](../frontend/src/pages/MapaBrasil/MapaBrasilPage.tsx)
**Visibilidade**: `CanViewMapMetrics` (Diretoria, alinhado com D7)

| Funcionalidade | UI | Endpoint | `permission_classes` | Quem acessa | Scope | Status |
|---|---|---|---|---|---|---|
| Mapa com municípios e eventos | Leaflet + GeoJSON | `GET /api/metrics/map/?...` | `CanViewMapMetrics` | Diretoria | — | OK |
| Filtro por projeto | Select | `?projeto=...` | — | Diretoria | — | OK |
| Filtro por data range | DatePicker | `?date_from=...&date_to=...` | — | Diretoria | — | OK |
| Toggle Map/List | Radio | — (client-side) | — | Diretoria | — | OK |
| Tabela de estados | `Table` | — (denormalized) | — | Diretoria | — | OK |
| Collapse por município | `Collapse` | — (client-side) | — | Diretoria | — | OK |
| Detalhes de coordenador | List | — (nested) | — | Diretoria | — | OK |

---

### 8.13 Ações Internas — `/acoes-internas`

**Componente**: [DATModule/AcoesPage.tsx](../frontend/src/pages/DATModule/AcoesPage.tsx)
**Visibilidade**: `HasPerm("manage_internal_actions")` — capability **zero-groups** (apenas Superuser bypassa hoje; pattern documentado em `feedback_capability_zero_groups_dev_feature.md`)

| Funcionalidade | UI | Endpoint | `permission_classes` | Quem acessa | Scope | Status |
|---|---|---|---|---|---|---|
| Listar ciclos de ação | Tabela com filtros | `GET /api/ciclos-acoes/` | `HasPerm("manage_internal_actions")` | Superuser | — | OK |
| Filtro por município | Select | `?municipio=...` | — | Superuser | — | OK |
| Filtro por projeto | Select | `?projeto=...` | — | Superuser | — | OK |
| Filtro por status (Carta/Contato/Reunião/Entrega) | Select | `?status=...` | — | Superuser | — | OK |
| Busca textual | `Input.Search` | `?q=...` | — | Superuser | — | OK |
| Criar nova ação | Modal + `PlusOutlined` | `POST /api/ciclos-acoes/` | `HasPerm("manage_internal_actions")` | Superuser | — | OK |
| Editar ação | `EditOutlined` | `PUT /api/ciclos-acoes/{id}/` | `HasPerm("manage_internal_actions")` | Superuser | — | OK |
| Excluir ação | `DeleteOutlined` + `Popconfirm` | `DELETE /api/ciclos-acoes/{id}/` | `HasPerm("manage_internal_actions")` | Superuser | — | OK |
| Exportar lista (stub) | `DownloadOutlined` | — (não implementado) | — | Superuser | — | pendente |

---

### 8.14 DAT / Admin — `/dat/admin`

**Componente**: [AdminDATHomePage.tsx](../frontend/src/pages/AdminDAT/AdminDATHomePage.tsx)
**Visibilidade**: `HasPerm("manage_admin_registries")` (DAT, Superuser; D2 — DAT é ator transversal)

| Funcionalidade | UI | Endpoint | `permission_classes` | Quem acessa | Scope | Status |
|---|---|---|---|---|---|---|
| Cartão "Usuários" | Card + link | navega `/dat/admin/usuarios` | `CanManageAdminRegistries` | DAT | — | OK |
| Cartão "Municípios" | Card | — (navegação) | `CanManageAdminRegistries` | DAT | — | OK |
| Cartão "Setores" | Card | — (navegação) | `CanManageAdminRegistries` | DAT | — | OK |
| Cartão "Funções" | Card | — (navegação) | `CanManageAdminRegistries` | DAT | — | OK |
| Cartão "Gerências" | Card | — (navegação) | `CanManageAdminRegistries` | DAT | — | OK |
| Cartão "Produtos" | Card | — (navegação) | `CanManageAdminRegistries` | DAT | — | OK |
| Cartão "Projetos" | Card | — (navegação) | `CanManageAdminRegistries` | DAT | — | OK |
| Cartão "Configurações" | Card | — (navegação) | `CanManageAdminRegistries` | DAT | — | OK |
| Sub-CRUD Usuários | Tabela + Form modal | `GET/POST/PUT/DELETE /api/users/` | `HasPerm("manage_admin_registries")` | DAT | — | OK — CPF write-only LGPD (Bug 3 PR #1285) |
| Sub-CRUD Municípios | Tabela + Form modal | `GET/POST/PUT/DELETE /api/municipios/` | `HasPerm("manage_admin_registries")` | DAT | — | OK |
| Sub-CRUD Projetos | Tabela + Form modal | `GET/POST/PUT/DELETE /api/projetos/` | `HasPerm("manage_admin_registries")` | DAT | — | OK |
| Sub-CRUD Cadastros (Ações, Compras, …) | Tabelas + importers | `GET/POST /api/cadastros/...` + `POST /api/imports/...` | `HasPerm("manage_admin_registries")` | DAT | — | OK |
| Listagem `ProdutoViewSet.list` | Tabela | `GET /api/produtos/` | `IsAuthenticated` | Todos autenticados | — | revisar — issue #1258 (capability operacional faltando) |
| Lookup `UsuarioLookup` | Autocomplete | `GET /api/lookup/usuario/` | `IsAuthenticated` | Todos autenticados | — | revisar — issue #1259 |

---

### 8.15 Controle — `/controle`

**Componente**: [ControlePage.tsx](../frontend/src/pages/Controle/ControlePage.tsx)
**Visibilidade**: `HasPerm("operate_preagenda")` (Controle, Superuser; D1)

| Funcionalidade | UI | Endpoint | `permission_classes` | Quem acessa | Scope | Status |
|---|---|---|---|---|---|---|
| Upload Compras | `ImportUploader` | `POST /api/imports/compras/` (validate + apply) | `CanImportCompras` | Controle, DAT | — | OK |
| Upload Ações | `ImportUploader` | `POST /api/imports/acoes/` (validate + apply) | `CanImportGenericSpreadsheet` | Controle, DAT | — | OK |
| Upload Eventos | `ImportUploader` | `POST /api/solicitacoes/import/` (validate + apply) | `IsAuthenticated, CanImportGenericSpreadsheet` (`import_spreadsheet \| run_daily_operations`) | Controle, DAT | — | OK |
| Upload Produtos | `ImportUploader` | `POST /api/produtos/import/` (validate + apply) | `IsAuthenticated, CanImportGenericSpreadsheet` (idem) | Controle, DAT | — | OK |
| Listar compras (pós-import) | Tabela com filtros | `GET /api/controle/compras/?...` | `HasPerm("run_daily_operations")` | Controle | — | OK |
| Filtro município/projeto/UF | Select dropdowns | query params | — | Controle | — | OK |
| Filtro data range | DatePicker | `?from=...&to=...` | — | Controle | — | OK |
| Busca por código/uso | `Input.Search` | `?q=...` | — | Controle | — | OK |

---

### 8.16 Resumo da Matriz

**Páginas mapeadas**: 15/15 (100%)
**Funcionalidades total**: ~100

**Distribuição de status** (após verificação cirúrgica dos INCERTO em 2026-04-27):

| Status | Aprox. | Observações |
|--------|--------|-------------|
| OK | ~93% | Alinhado com decisões D1-D7 |
| INCERTO | 0% | Todos os 5 INCERTO da varredura inicial foram resolvidos: 3 eram bugs de doc (paths errados), 2 viraram OK com permission corrigida (Aprovações batch — ver observação inline em §8.3) |
| revisar | ~3% | Issues #1258 (`ProdutoViewSet.list`), #1259 (`UsuarioLookup`) — backlog §7 |
| pendente | ~4% | Stubs de export CSV (Dashboard Geral, Ações Internas) |

**Top-3 páginas com mais funcionalidades**:
1. **DAT/Admin** — 14+ (cards + sub-CRUDs)
2. **Controle** — 8 (uploads + listagem)
3. **Aprovações** — 9 (preview, aprovar/reprovar individual e batch)

**INCERTO resolvidos** (verificação cirúrgica 2026-04-27):

| Item | Resultado |
|------|-----------|
| `/api/solicitacoes/batch-approve/` e `/batch-reject/` | Existem em [views_solicitacao.py:812-882](../backend/apps/core/views_solicitacao.py#L812-L882). Permission é `HasPerm("approve_solicitation")` (não `_batch`). Sub-finding: Gerente pode não ter acesso — registrado como observação em §8.3, decisão de produto pendente |
| `/api/dashboard/equipe/` | Não existe — frontend chama 3 endpoints `/api/metrics/team/{productivity,formadores,quality}/` com composition β (Onda 2 A3) |
| `/api/gcal/batch-reapply/` | Path real: `/api/gcal/dashboard/batch/reapply/` em [views_gcal/batch.py:154](../backend/apps/core/views_gcal/batch.py#L154); permission `IsAuthenticated, CanUseGcal` |
| `/api/imports/eventos/` | Path real: `/api/solicitacoes/import/` em [views_import_eventos.py:43](../backend/apps/core/views_import_eventos.py#L43); permission `CanImportGenericSpreadsheet` |
| `/api/imports/produtos/` | Path real: `/api/produtos/import/` em [views_import_produtos.py:42](../backend/apps/core/views_import_produtos.py#L42); permission `CanImportGenericSpreadsheet` |

---

## 9. Recomendações Finais

**Pode usar hoje sem código**: criar grupos via admin + atribuir capabilities + validar via `GET /api/me/policies/`.

**Exige cuidado**:
- Não misturar Coordenador com capabilities transversais (rompe D6 — escopo via `EquipeGerencia`).
- Não atribuir grupo a `manage_internal_actions` antes da feature estar madura (pattern capability-zero-groups documentado).
- Linha "Aprovações" usa capability como flag: aceitável tatícamente, mas backlog ideal é criar policy pública `access_solicitation_approvals` (composição `approve_solicitation \| approve_solicitation_batch`) e expor em `PUBLIC_POLICY_KEYS` — alinha contrato externo com a regra real (Gerente OR Superintendência).

**Exige PR futuro**:
- Onda 4 (capability gates faltando: #1258, #1259).
- Onda 5 governança (#1261 sentinela, #1276 doc auto-sync).
- Expansão da Matriz Viva para scope cases (não apenas autorização binária).

---

## Estatísticas

| Métrica | Contagem | Status |
|---------|----------|--------|
| Capabilities | 16 | ✅ Todas validadas no seed |
| Policies | 15 | ✅ Todas em `PUBLIC_POLICY_KEYS` |
| Endpoints | 50+ | Críticos mapeados; sem lacunas críticas conhecidas; backlog aberto |
| Páginas | 14 | ✅ Funcional; 1 com pendência de policy dedicada (Aprovações) |
| Atores | 8 | ✅ SSOT completo |
| Lacunas críticas mergeadas | 6/6 | ✅ Ondas 1-2 (PRs #1250, #1256) |
| Lacunas críticas em PR aberto | 1 | PR #1286 (cobre #1284 + #1260) |
| Backlog de hardening aberto | 6 issues | #1258, #1259, #1260, #1261, #1276, #1284 |
| Tests Matriz Viva | 74+ | ✅ PR #1283 |

**Validação**: Leitura de código contra seed, policies, 5+ views, 2 hooks. Findings cross-referenciadas contra memórias do projeto e decision matrix (D1-D7).
