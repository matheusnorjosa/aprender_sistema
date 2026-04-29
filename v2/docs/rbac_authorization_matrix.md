# RBAC Authorization Matrix — SSOT canônica

**Status**: vivo a partir de 2026-04-27 (pós Bug 1 fix do Programa RBAC Access Policy Realignment).
**Versão**: 1.0
**Audiência**: devs revisando PRs que tocam authz, stakeholder validando comportamento esperado, novos integrantes onboarding.

Este documento é a **fonte da verdade declarativa** para autorização no Aprender Sistema v2. Quando código diverge desta matriz, o código está errado (ou esta matriz precisa ser atualizada com decisão consciente do stakeholder). Não interprete intenção a partir de leitura de código — leia este documento.

---

## 1. Princípios fundamentais (NIST RBAC 3-tier)

```text
User → Roles (Groups Django) → Capabilities (PermissaoFuncional) ← Policies (CanXxx) ← Views/Routes
```

**Separação canônica**:

- **Capability** = autorização *por feature* (binária: pode/não pode usar este recurso)
- **Scope** = autorização *por dado* (filtragem: vê só o próprio setor/gerência/queryset)
- **Policy** = composição declarativa de capabilities (`CanXxx` em `apps/core/rbac/policies.py`)
- **Public Policy** = key exposta via `GET /api/me/policies/` (subset de `PUBLIC_POLICY_KEYS`); contrato estável (renomear/remover = breaking)

Ver `RBAC_NAMING.md` para convenção de nomes (verbos canônicos, classe ↔ key, vocabulário).

---

## 2. Atores reconhecidos

### Setores (organizacional, vínculo via grupo Django)

| Setor | Papel resumido | Ator transversal? |
|-------|----------------|-------------------|
| Superintendência | Aprovação executiva | Não (escopo decisório) |
| DAT | Manutenção administrativa, suporte, validação | **Sim** (acessa por motivo "suportar/validar") |
| Diretoria | Decisão executiva (dashboards, mapa) | Não (escopo decisório) |
| Controle | Operação diária do calendário | **Sim** (acessa transversalmente por motivo "operar") |
| Vidas / Fluir / ACerta / Brincando / Sou da Paz / Comercial / Relacionamento / Logística Viagens / Logística Galpão | Setores de produto (escopados por gerência) | Não |

### Funções (papel funcional, ortogonal ao setor)

| Função | Papel resumido | Scope |
|--------|----------------|-------|
| Gerente | Supervisão, aprovação composta com Superintendência | Cross-sector (transversal) |
| Coordenador | Cria solicitações, gerencia bloqueios próprios | Setor vinculado via `EquipeGerencia` |
| Apoio de Coordenação | Mesma regra do Coordenador | Setor vinculado |
| Formador | Declara próprio bloqueio (RD-02/03), participa de eventos | Próprios dados |

### Princípio "ator transversal"

DAT e Controle entram em policies por **motivo legítimo de acesso** (decidir/operar/aprovar/auditar/suportar/validar), não por estar "no mesmo grupo organizacional" do setor que originou a feature. Ver `feedback_motivo_legitimo_acesso.md` (memória interna).

---

## 3. Matriz canônica — atores × recursos

Legenda:
- ✅ — acesso liberado por capability/policy
- 🔒 — bloqueado deliberadamente
- ⚠️ — depende de scope (`HasSectorAccess`, queryset filter, ou self-ownership)
- 🔧 — superuser bypass (sempre)

| Recurso | Superuser | DAT | Diretoria | Controle | Gerente | Coordenador / Apoio | Formador |
|---------|-----------|-----|-----------|----------|---------|---------------------|----------|
| **Dashboard Geral** (`/dashboards`) | 🔧 | 🔒 | ✅ | 🔒 | 🔒 | 🔒 | 🔒 |
| **Dashboard Compras** (`/dashboards/compras`) | 🔧 | ✅ (suportar) | ✅ (decidir) | 🔒 | 🔒 | 🔒 | 🔒 |
| **Dashboard Equipe** (`/dashboards/equipe`) | 🔧 | ✅ (validar) | ✅ (decidir) | 🔒 | 🔒 | 🔒 | 🔒 |
| **Dashboard GCal** (`/dashboards/gcal`) | 🔧 | ✅ (suportar) | ✅ (decidir) | ✅ (operar) | 🔒 | 🔒 | 🔒 |
| **Mapa do Brasil** (`/mapa-brasil`) | 🔧 | ✅ (validar) | ✅ (decidir) | 🔒 | 🔒 | 🔒 | 🔒 |
| **Grade Mensal** (`/api/availability/monthly/`) | 🔧 | ⚠️ scope | 🔒 | ✅ `view_all_availability` | ✅ `view_all_availability` | ⚠️ scope `EquipeGerencia` | 🔒 (não é grade — usa `/me/events`) |
| **Aprovações** (`/solicitacoes/{id}/approve\|reject`) | 🔧 | 🔒 | ✅ Superintendência | 🔒 | ✅ batch (composite) | 🔒 | 🔒 |
| **Bloqueios** (`AvailabilityBlockViewSet`) | 🔧 | 🔒 | 🔒 | ⚠️ scope ampla | ⚠️ scope ampla | ⚠️ próprios + scope | ⚠️ apenas próprios (RD-02/03) |
| **Deslocamentos** (`DeslocamentoViewSet`) | 🔧 | 🔒 | 🔒 | ✅ `view_all_availability` | ✅ `view_all_availability` | ⚠️ scope (Onda 1 — alinhar) | 🔒 |
| **DAT Compras** (`DATCompraViewSet`) | 🔧 | ✅ `manage_purchases_and_materials` | ✅ dashboard | ✅ `manage_purchases_and_materials` | 🔒 | 🔒 | 🔒 |
| **Reports** (`views_reports.py`) | 🔧 | ✅ `manage_admin_registries` | 🔒 | ✅ `operate_preagenda` | ✅ Super (auditar) | 🔒 | 🔒 |
| **Admin Registries** (Municípios, Projetos, Produtos, etc.) | 🔧 | ✅ `manage_admin_registries` | 🔒 | 🔒 | 🔒 | 🔒 | 🔒 |
| **Imports** (planilhas) | 🔧 | ✅ `import_spreadsheet` | 🔒 | 🔒 | 🔒 | 🔒 | 🔒 |
| **Ações Internas** (`CicloAcoes`, `AcaoInstancia`) | 🔧 | ✅ (Onda 1 — substituir `IsAdminUser`) | 🔒 | 🔒 | 🔒 | 🔒 | 🔒 |
| **Solicitações — Criar** (`POST /solicitacoes/`) | 🔧 | 🔒 (não é função de DAT) | 🔒 | 🔒 | ✅ `create_solicitation` | ✅ `create_solicitation` | 🔒 |
| **Solicitações — Próprias** (`/solicitacoes/minhas`) | 🔧 | ⚠️ owner | ⚠️ owner | ⚠️ owner | ⚠️ owner | ⚠️ owner | ⚠️ via `/me/events` |
| **/api/me/events/** (eventos onde participa) | 🔧 | ⚠️ self | ⚠️ self | ⚠️ self | ⚠️ self | ⚠️ self | ✅ caso primário |
| **/api/me/policies/** | 🔧 todas | ✅ subset | ✅ subset | ✅ subset | ✅ subset | ✅ subset | ✅ vazio ou mínimo |

---

## 4. Capability ↔ grupo (estado canônico pós migration 0078)

Estado autoritativo após `0078_scope_view_all_availability` (2026-04-27). Mudanças exigem migration data-only nova + atualização desta tabela.

| Capability | Grupos atribuídos | Justificativa |
|------------|-------------------|---------------|
| `approve_solicitation` | Superintendência | Aprovação executiva final (PA-02) |
| `approve_solicitation_batch` | Gerente, Superintendência | Composição da regra "Gerente + Super" |
| `create_solicitation` | Coordenador, Apoio de Coordenação, Gerente | Quem cria pedido de evento |
| `edit_solicitation_as_owner_or_privileged` | Gerente, Coordenador, Apoio de Coordenação | Edição da própria solicitação ou de qualquer com privilégio |
| `execute_restricted_operations` | Superintendência | Operações irreversíveis (bloqueio executivo) |
| `import_spreadsheet` | DAT | Único setor que faz importação massa |
| `manage_admin_registries` | DAT | Manutenção de cadastros administrativos |
| `manage_purchases_and_materials` | DAT, Controle | Compras e materiais (DAT operacionaliza, Controle audita uso) |
| `operate_preagenda` | Controle | Operação diária do calendário |
| `run_daily_operations` | Controle | Imports operacionais e workflow diário |
| `supervise_operations` | Diretoria | Visão executiva consolidada |
| **`view_all_availability`** | **Controle, Gerente** *(NÃO inclui Coord/Apoio — caem em scope)* | **Visão transversal sem restrição** (decisão pós Bug 1) |
| `view_compras_dashboard` | Diretoria | Decisão executiva de compras |
| `view_map_metrics` | Diretoria | Métricas geográficas executivas |
| `view_overview_dashboard` | Diretoria | Painel executivo geral |

---

## 5. Padrões idiomáticos para `permission_classes`

### 5.1 Single capability (preferido quando a regra cabe em uma capability)

```python
permission_classes = [HasPerm("approve_solicitation")]
```

### 5.2 Composition OR via Policy class (quando há semântica unificada)

```python
permission_classes = [CanAccessAuditLogs]   # 4 caps internas, semântica única
```

### 5.3 Composition OR ad-hoc (quando ainda não estabilizou em Policy)

```python
permission_classes = [HasPerm("a") | HasPerm("b")]   # sites <3, intent fluido
```

### 5.4 Capability + scope (autorização por feature + por dado)

```python
permission_classes = [IsAuthenticated, CanViewAllAvailability | HasSectorAccess]
```

Quem tem capability bypassa scope; quem não tem cai no scope. **Padrão correto para Grade Mensal e Deslocamentos** (após Onda 1).

### 5.5 Anti-padrões (lint guarda)

```python
permission_classes = [IsDAT]                          # ❌ identidade, não capacidade
user.groups.filter(name="Controle").exists()          # ❌ bypass do RBAC
permission_classes = [IsAdminUser]                    # ❌ DRF built-in fora da camada Policy
```

---

## 6. Decisões consolidadas (não revisitar sem motivo novo)

| # | Decisão | Data | Rationale |
|---|---------|------|-----------|
| D1 | Capability Policy Layer NIST 3-tier (não admin-driven full) | 2026-04-26 | Single-tenant + single-dev → admin-driven full é over-engineering. Ver `feedback_admin_driven_overengineering.md` |
| D2 | DAT é ator transversal (entra em policies por motivo, não por origem organizacional) | 2026-04-26 | Authoring AuditLog quebrava se DAT fosse tratado como "setor de importação" — múltiplos motivos legítimos coexistem |
| D3 | `PUBLIC_POLICY_KEYS` é registro explícito (não dinâmico via subclasses) | 2026-04-26 | Controle consciente do contrato externo; previne leakage acidental de policy interna |
| D4 | `_PolicyPermission.has_permission` delega para `user_has_policy` (DRY) | 2026-04-26 | Fonte única de verdade da semântica — view, tests e helpers compartilham avaliação |
| D5 | Frontend tem **camada de tradução semântica** (`canAccessApprovals` etc.) | 2026-04-26 | Componentes não conhecem origem (policy vs legacy) — migrar p/ Epic 4.6 = 1 linha sem ripple |
| D6 | Coordenador/Apoio são SCOPED (não recebem `view_all_availability`) | 2026-04-27 (Bug 1) | E2E J05 protegia regra de privacidade legítima; capability deve ser literal "ver TODAS sem restrição" |
| D7 | Dashboards = Diretoria + DAT + superuser only | 2026-04-26 | `project_rbac_invariants.md` — Controle não vê Dashboards (Onda 1 corrige `usePermissions` hardcoded) |
| D8 | Formador, DAT e Diretoria **não acessam** Grade Mensal; Coord/Apoio só com `EquipeGerencia` ativa | 2026-04-28 (issue #1287) | Formador é caso especial RD-02/RD-03 (acessa só Meus Eventos + Bloqueios). DAT/Diretoria não têm motivo legítimo de consultar grade. Antes do fix, frontend `canDisponibilidade=!inControle` (lógica invertida) e backend `HasSectorAccess` retornava True sem `gerencia_id` — Formador via menu e abria página com 200. Reescrita como lista positiva no frontend + endurecimento no backend (sem `gerencia_id` exige vínculo de gerência) |
| D9 | Grade Mensal — **DAT recebe** `view_all_availability` global; **Gerente perde** cap global e cai em scope via `EquipeGerencia` (igual Coord/Apoio) | 2026-04-28 (PR 2 RBAC hardening) | Refina D8: DAT é ator transversal admin (suporte/validação cross-setor) — motivo legítimo para grade global. Gerente pedagógico (ACerta, Vidas, Fluir, Brincando, Sou da Paz, Gestão Escolar) e Gerente da Superintendência devem ver apenas a própria gerência via `EquipeGerencia` — não devem receber visão global apenas por ter função "Gerente". Migration 0080 redistribui `view_all_availability` de `[Controle, Gerente]` para `[Controle, DAT]`. Diretoria mantém DENY (D8). Formador mantém DENY (D8). Distinção semântica entre subtipos de Gerente (pedagógico vs Sup vs DAT) fica em PR 8 (Matriz Viva escopo) |

---

## 7. Pendências conhecidas (rastreadas em ondas)

### Onda 1 — Críticos (próximo PR)

| # | Recurso | Problema | Fix |
|---|---------|----------|-----|
| C1 | Dashboards sidebar | `usePermissions.canDashboardEquipe`/`canMapaBrasil`/`canDashboardGcal` hardcoded inclui Controle, contra D7 | Restringir a Diretoria/DAT/superuser |
| C2 | Deslocamentos sidebar | UI mostra para Coord/DAT, backend exige `view_all_availability` (Controle/Gerente only após D6) | Alinhar gate (esconder pra Coord/DAT) ou alargar backend (decisão pendente) |
| C3 | Ações Internas | `[IsAdminUser]` bypassa Capability Policy Layer (D1 violado) | Substituir por `[CanManageAdminRegistries]` ou nova policy específica |

### Onda 2 — Altos

| # | Recurso | Problema | Fix |
|---|---------|----------|-----|
| A1 | `SolicitacaoViewSet.create` | Aceita qualquer authenticated, sem `HasPerm("create_solicitation")` explícito | Adicionar permission class |
| A2 | `usePermissions.canDashboardCompras` | Hardcoded em vez de consumir policy `view_compras_dashboard` (que está em PUBLIC_POLICY_KEYS) | Migrar para `useCanAccess` derived flag |
| A3 | 4 viewsets com `[IsAuthenticated]` apenas | Confiando 100% em queryset filter; sem capability check explícito | Adicionar `CanAccessBlocks` ou similar |

### Onda 3 — Matriz Viva (governance)

Implementar testes parametrizados que **falham CI** se um (ator × recurso) ganha/perde acesso inesperado. Estrutura proposta:

- `apps/core/tests/test_rbac_matrix_living.py` — backend pytest parametrize sobre `(actor_groups, resource_url, method) → expected_status`
- `v2/frontend/src/__tests__/rbac_matrix.test.ts` — vitest parametrize sobre `(policies, menu_key) → visibility`
- `apps/core/rbac/matrix.py` (NEW) — SSOT lido pelos 2 tests, espelha esta tabela canônica em formato Python

Ver memória `project_rbac_access_policy_realignment.md` para detalhes do escopo das ondas.

---

## 8. Como manter este documento

1. **Toda mudança de capability ↔ grupo** → migration data-only (`groups.set(...)` idempotente) + atualização da tabela §4
2. **Toda nova policy pública** → atualizar `PUBLIC_POLICY_KEYS` + linha na §3 + entrada no §4 se for nova capability
3. **Toda nova decisão arquitetural** → linha em §6 com data + rationale (não apaga decisões antigas)
4. **Mudança de pendência (onda)** → atualizar §7 (mover para concluído com link para PR)
5. **Stability rule**: keys públicas em §4 são imutáveis após release. Renomear = breaking, exige deprecation period (2 releases mantendo aliases). Ver `RBAC_NAMING.md §9`.

---

## 9. Referências cruzadas

- `RBAC_NAMING.md` — convenção de nomes (codenames, labels, classes)
- `apps/core/rbac/policies.py` — SSOT do código (`ACCESS_POLICIES`, `PUBLIC_POLICY_KEYS`, `Can*` classes, `user_has_policy`)
- `apps/core/services/functional_permissions_seed.py` — SSOT do seed (mestre da §4)
- `apps/core/migrations/0077_realign_funcperm_groups.py` + `0078_scope_view_all_availability.py` — realinhamentos data-only aplicados
- `apps/core/rbac/permissions.py` — `HasPerm`, `HasSectorAccess`, `IsGerenteSuperintendencia`, `IsOwnerOrPrivileged`
- `v2/frontend/src/hooks/usePermissions.ts` — flags derivadas legacy (em migração para `useCanAccess`)
- `v2/frontend/src/hooks/useCanAccess.ts` — camada de tradução semântica (D5)
- `v2/frontend/src/components/access/RequirePolicy.tsx` — wrapper de rota
