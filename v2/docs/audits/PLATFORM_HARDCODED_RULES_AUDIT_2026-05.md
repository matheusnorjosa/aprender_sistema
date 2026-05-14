# Auditoria de Regras Hardcoded da Plataforma — 2026-05

Status: Backlog / sem urgência operacional
Origem: pós-Programa Hardening RBAC
Resultado: nenhum P0 encontrado
Próxima ação recomendada: retomar após férias, começando por lint preventivo D17

---

## 1. Resumo executivo

| Métrica | Valor |
|---|---|
| Total de achados reportados | ~50 |
| **P0 (vazamento/bypass real)** | **0** |
| P1 (regra crítica fora da camada / risco preventivo D17) | 4 |
| P2 (acoplamento, magic numbers, duplicação relevante) | ~15 |
| P3 (cosmético, type alias redundante, doc legado marcado) | ~30 |
| Falsos positivos identificados | 1 (F-020 — cross-check confirmou alinhamento) |

**Recomendação geral**: planejar depois, não há urgência. O Hardening RBAC fechou as frentes de segurança; os achados restantes são higiene de código (constantes, enum AuditAction, Policies pra composições 3-ternárias, getMe→context). Top-3 prioridades: (B1) AuditAction TextChoices, (D1) lint/CI guard preventivo D17, (F1) deslocar `getMe()` de página para context.

**Áreas com mais débito**: regras de negócio (status/fluxo/magic numbers) > frontend (`getMe()` em página) > backend RBAC (composição ternária ainda não elevada a Policy).

**Áreas limpas**: documentação RBAC (deprecated marcado), menu↔rota (sem divergência), helpers RBAC (noqa whitelist funcionando), fixtures (não há JSON com atribuição grupo→capability), management commands de seed (manuais, não-automáticos).

---

## 2. Achados principais

| ID | Sev | Área | Arquivo:linha | Hit | Por que é risco | Recomendação | PR sugerido |
|---|---|---|---|---|---|---|---|
| B1 | P1 | Auditoria | `apps/core/models/auditlog.py` + ~50 call sites | `AuditLog.objects.create(action="APPROVE")` strings literais | Sem enum central → ortografia/divergência futura ("APPROVAL" vs "APPROVE"), drift silencioso, audit não pesquisável | `class AuditAction(TextChoices)` com tudo que existe hoje, codemod das call sites | PR B |
| B2 | P1 | GCal | `services/gcal/payload.py:232`, `gcal_fake_client.py:57`, `views_gcal/detail.py:305` | `eventId=f"asv2-{id}"` | Formato eventId é contrato com Google — divergência entre client real e fake quebra idempotência | `GCAL_EVENT_ID_PREFIX = "asv2"` em constants/settings + helper `gcal_event_id(s)` | PR B |
| B3 | P1 | Disponibilidade | `availability_service.py:154,161` + outras views | `filter(status="aprovado")` | Status hardcoded em hot path RD-01..08; renomear status quebra silenciosamente | `Solicitacao.Status.APROVADO` (TextChoices) onde já existe; helper `get_approved_qs()` | PR B |
| D1 | P1 | Migrations preventivo | (não há violação atual — risco prospectivo) | Falta lint/CI guard para `Group.permissions.set/clear/add` em migrations novas | D17 hoje é regra documentada, não enforced — futuro PR pode regredir sem CI quebrar | Adicionar regra ao `scripts/rbac_lint.py` (ou novo lint de migrations) que fail-fast se nova migration `0NNN_*.py` chamar `permissions.set\|clear\|add` em `PermissaoFuncional.groups` | PR E |
| R1-R3 | P2 | RBAC composição | `views/metrics/dashboard_metrics.py:36`, `formador_metrics.py:32`, `views/admin.py:251` | `HasPerm("a") \| HasPerm("b") \| HasPerm("c")` (3 caps) | Pelo guideline da própria sessão (memória `feedback_composition_or_is_tactical.md`): ≥3 caps = candidato a Policy | Elevar a `CanViewMetrics` / `CanManageProductCatalog` em Capability Policy Layer | PR A |
| B4 | P2 | Magic numbers | `views_reports.py:52,137,255` | `timedelta(days=30)` x3 | Mesmo valor de janela em 3 funções; mudar política exige edição em 3 arquivos | `REPORT_LOOKBACK_DAYS = 30` em constants ou settings | PR C |
| B5 | P2 | Magic numbers | `preagenda_to_gcal.py:159,169` | `timedelta(days=90)` e `days=180` | Janelas de sync GCal; críticas pra integridade do calendário | `GCAL_SYNC_LOOKBACK_DAYS`, `GCAL_SYNC_AHEAD_DAYS` em settings | PR C |
| B6 | P2 | GCal | `gcal_fake_client.py:56,79`, `gcal_google_client.py:194,227` | `conferenceDataVersion=1` x4 | Versão API hardcoded em 4 lugares; divergência fake↔real | `GCAL_CONFERENCE_DATA_VERSION = 1` em constants | PR B |
| B7 | P2 | Importação | `services/dat_cadastros_import.py:301`, `controle_acoes_import.py:265`, `controle_imports.py:36`, `deslocamentos_import.py:257` | `hashlib.sha1(...).hexdigest()` x4 | Algoritmo idempotência replicado; mudança de algoritmo quebra dedup em todos | `services/hash_utils.py::compute_external_hash(key)` | PR C |
| B8 | P2 | Status/fluxo | `views_solicitacao.py:559` | `if projeto.fluxo == "SUPER"` em view | Lógica de fluxo em view (deveria estar em service de aprovação) | Mover pra `solicitacao_approval.py` ou novo `flow_service.py` | PR B |
| B9 | P2 | Status/fluxo | `views_preagenda.py:51,54` | `filter(projeto__fluxo="SUPER")` x2 | Filtro duplicado | Helper QuerySet `get_super_solicitations_queryset()` | PR B |
| F1 | P2 | Frontend acoplamento | `pages/Solicitacoes.tsx:106`, `pages/Solicitacoes/NewSolicitacaoWizard.tsx:147`, `pages/PreAgenda/PreAgendaPage.tsx:164`, `pages/Disponibilidade/FiltersBar.tsx:57` | `getMe()` chamado em useEffect de página | Estado de usuário em múltiplos lugares → desincronização possível, requests duplicadas | Subir `me`+`policies` para context (já existe parcial); páginas consomem via `useUser()`/`useCanAccess()` | PR D |
| F2 | P2 | Frontend acoplamento | `pages/Aprovacoes/ApprovalsPage.tsx:155-167` | `computeAccess(policies)` chamado em página | Cálculo fora do `useCanAccess` central; nova policy não atualiza página | Substituir por `useCanAccess()` | PR D |
| F3 | P2 | Validação divergente | `pages/AdminDAT/UsuariosPage.tsx:618-620,649,654,658` | `pattern: /^[0-9]{11}$/`, `maxLength={100}` (cargo) | Validação frontend pode divergir de `serializers.UsuarioSerializer` (max_length, regex) | Criar `constants/validation.ts` mirror do backend; documentar contrato | PR D |
| B10 | P3 | Cache TTL | `availability_service.py:115` | `@cache_availability_check(timeout=300)` | TTL hardcoded no decorator | `settings.CACHE_AVAILABILITY_TTL_SECS` | PR C |
| B11 | P3 | Type alias redundante | `apps/core/types.py:54,74` | `ApprovalStatus = Literal["pendente","aprovado","reprovado"]` | Duplica `Solicitacao.Status` choices | Remover, usar `Solicitacao.Status.values` | PR C |
| B12 | P3 | GCal status | views_gcal/*.py (5+ locais) | `["NONE","PENDING","PUBLISHED","ERROR"]` literal | Lista de status enumerada em filtros | `Solicitacao.GCalStatus.values` ou helper `GCAL_STATUS_ALL` | PR C |

---

## 3. Categorias obrigatórias

### 3.1 RBAC/permissões (backend)
- **Sem P0/P1**. `rbac_lint.py` ativo no CI bloqueia regressões.
- **P2**: 3 composições ternárias (R1-R3) candidatas a Policy.
- **P3**: 9 ocorrências de `groups.filter(name=...)` todas com `# noqa: RBAC-*-allowed` apropriado e dentro de paths whitelisted (`rbac/helpers.py`, `rbac/permissions.py`, `rbac/policies.py`, `views/stats.py`).
- **Padrão excelente**: fail-safe `else: qs.none()` em `views/stats.py:134` (fix #1284) — replicar.

### 3.2 Setor/Função/Grupo hardcoded
- **Backend**: SSOT em `apps/core/constants.py:16-45` (SETOR_GROUPS / FUNCAO_GROUPS). Hits fora dela são whitelisted ou em data-scope (`COORDENADOR_ROLE_GROUPS` em dropdowns).
- **Frontend**: SSOT em `hooks/usePermissions.ts:80-89` derivando de `me.groups`. Único hit fora: `pages/Disponibilidade/FiltersBar.tsx:41-44` (`GROUP_TO_NOME_SETOR`) — P3 aceitável (1 local, mapeamento label).

### 3.3 Status/fluxo hardcoded
- **B1, B3, B8, B9** (acima). `pendente/aprovado/reprovado` aparece em ~10 locais fora do model — maior parte é UI/log/teste (aceitável); 2-3 são lógica de fluxo (suspeito).

### 3.4 Frontend menu/rota/UX
- **Sem divergência**: `AppSidebar.tsx` ↔ `AppRoutes.tsx` cruzados — todas as rotas filhas de `/dat/admin` herdam guard `canDAT` do pai. Aprovações: menu (linha 287) e rota (linha 125) usam mesma `access.canAccessApprovals`.
- **F-020 falso positivo confirmado**: cross-check de `views_solicitacao.py` mostra que `approve/reject/preview-gcal/publish` (linhas 611, 649, 815, 851) usam `CanAccessSolicitationApprovals` — mesma policy que o frontend consome via `/api/me/policies/`.

### 3.5 Imports/ETL
- **B7** (hash SHA1 replicado em 4 services).
- **Sem P0/P1**: lógica de validação centralizada em `services/dat_*_import.py` por domínio.

### 3.6 Solicitações/Aprovações
- **B8, B9**: fluxo SUPER hardcoded em view.
- Endpoints alinhados com policy correta (cross-check confirmou).

### 3.7 Disponibilidade/Deslocamentos
- **B3** (`status="aprovado"` hardcoded em hot path).
- **B10** (cache TTL hardcoded).
- RD-01..08 centralizados em `availability_service.py` — sem duplicação fora.

### 3.8 Compras/Produtos
- Nenhum achado relevante. Modelo dual `Compra` vs `DATCompra` é decisão de arquitetura, não duplicação de regra.
- **R3**: ProdutoViewSet (admin.py:251) com 3 caps OR — candidato a Policy.

### 3.9 GCal/Dashboards/Relatórios
- **B2** (eventId asv2-), **B5** (sync windows), **B6** (conferenceDataVersion), **B12** (lista de gcal_status).
- Maior concentração de magic numbers e formatos hardcoded.

### 3.10 Docs/scripts/migrations
- **Docs**: limpos. `RBAC_NAMING.md` §3, §5, §9 marcam padrões legacy explicitamente como `❌ DeprecationWarning` ou `❌ NÃO FAZER após PR 16`. Sem drift silencioso.
- **Migrations** (0074/0075/0077/0078/0080 com `permissions.set/add/clear`): todas pré-2026-05-04 (data ratificação D17). Historicamente aceitáveis. Migrations posteriores (0079, 0081, 0082) limpas.
- **Management commands** (`seed_rbac`, `migrate_rbac_groups`): manuais, não-automáticos em deploy. **D1 é risco prospectivo** — não há lint que bloqueie nova migration usar `.set()` em PermissaoFuncional.groups.
- **Fixtures JSON**: não existem (projeto usa seed via management commands idempotentes).
- **Tests**: `test_rbac_permissions.py:70-239` testa `can_approve_super` legacy via endpoint — é teste de contrato OpenAPI, não bootstrap RBAC; aceitável.

---

## 4. Falsos positivos e itens aceitáveis

| Item | Arquivo:linha | Por que parece suspeito | Por que é aceitável |
|---|---|---|---|
| F-020 — endpoint approve "aberto" | `pages/Aprovacoes/ApprovalsPage.tsx` botão escondido por policy | Suspeita de "botão front escondido / endpoint back aberto" | Cross-check: `views_solicitacao.py:611,649,815,851` usa `CanAccessSolicitationApprovals` — mesma policy do front |
| Migrations 0074/0075/0077/0078/0080 com `permissions.set/add` | `apps/core/migrations/` | Aparenta violar D17 | Pré-2026-05-04 (D17 ratificada); estado inicial histórico aceitável |
| `groups.filter(name=...)` x9 com `# noqa: RBAC-*-allowed` | rbac/helpers.py, rbac/policies.py, rbac/permissions.py, views/stats.py, views_options.py | Pattern banido pelo lint | Whitelisted explicitamente; usados em data-scope ou composite documentado |
| `usePermissions.ts:80-89` com `funcoes.includes('Coordenador')` etc | frontend hook | Strings de grupo no front | SSOT centralizado; flags derivadas (`canControle`, `isCoordenador`) consumidas no resto |
| `ApprovalsPage.tsx:64-76` `STATUS_LABELS = { pendente: 'Pendente' }` | UI labels | Hardcode de status | UX/badge — aceitável; tipo central em `types/solicitacao.ts:18` |
| Type aliases `ApprovalStatus` em `types.py:54,74` | backend | Redundante com `Solicitacao.Status` | P3 — refactor desejável, sem impacto operacional |
| `bloco autogen` em `rbac_authorization_matrix.md` | docs | Strings de grupo "hardcoded" | Gerado por `python manage.py rbac_matrix_doc --check` no CI; SSOT |
| Tests com `user.groups.add(group)` no setup | `tests/test_rbac_*.py` | Pattern banido | Setup de teste, não autorização runtime; aceitável |

---

## 5. Possíveis PRs de correção

### PR A — Capability Policy Layer (Epic 4.2.c) — P2

- **Escopo**: elevar 3 composições ternárias a Policy classes. `CanViewMetrics` (dashboard_metrics + formador_metrics) e `CanManageProductCatalog` (admin.py:251).
- **Arquivos**: `rbac/policies.py` (novas Policies), `rbac/__init__.py` (export), `views/metrics/*.py`, `views/admin.py`, `rbac/matrix.py` (atualizar matriz), `tests/test_rbac_policies_contract.py`.
- **Testes**: matriz viva absorve as novas keys; sentinela detecta drift.
- **Risco**: baixo (refactor não-funcional, mesmo gate efetivo).

### PR B — Status/fluxo/eventId TextChoices + service consolidation — P1

- **Escopo**: `AuditAction` TextChoices (B1), helper `gcal_event_id()` (B2), `Solicitacao.Status.APROVADO` em RD service (B3), service de fluxo SUPER (B8/B9), `conferenceDataVersion` constante (B6).
- **Arquivos**: `models/auditlog.py` (TextChoices), `constants.py` (GCAL_*), `services/solicitacao_approval.py` (extract fluxo), `services/availability_service.py`, `views_solicitacao.py`, `views_preagenda.py`, `views_gcal/*.py`, `services/gcal/*.py`, ~50 call sites do `AuditLog.objects.create(action=...)`.
- **Testes**: snapshot dos AuditLog.action existentes (não pode mudar valor); RD tests passam.
- **Risco**: alto blast-radius (codemod amplo); precisa de PR cuidadoso. Considerar dividir B1 em PR próprio.

### PR C — Magic numbers + hash utility — P2/P3

- **Escopo**: `REPORT_LOOKBACK_DAYS`, `GCAL_SYNC_*_DAYS`, `services/hash_utils.py::compute_external_hash`, `CACHE_AVAILABILITY_TTL_SECS`.
- **Arquivos**: `constants.py` ou `settings.py`, `views_reports.py`, `preagenda_to_gcal.py`, `services/*_import.py` x4, `availability_service.py`.
- **Testes**: import jobs ainda dedup pelo mesmo hash.
- **Risco**: baixo (constantes equivalentes).

### PR D — Frontend: getMe() para context + validation mirror — P2

- **Escopo**: subir `me`/`policies` ao context (se não já estiver completo), refatorar páginas `Solicitacoes.tsx`, `NewSolicitacaoWizard.tsx`, `PreAgendaPage.tsx`, `FiltersBar.tsx`, `ApprovalsPage.tsx` para consumir via `useUser()`/`useCanAccess()`. Criar `constants/validation.ts` mirror do backend.
- **Arquivos**: `contexts/UserContext.tsx`, `hooks/useCanAccess.ts`, ~5 páginas, `constants/validation.ts`.
- **Testes**: páginas mantêm comportamento atual; loading state OK.
- **Risco**: médio (atinge fluxo de auth/context — testar bem).

### PR E — Lint guard preventivo D17 + sentinela — P1 preventivo

- **Escopo**: regra em `scripts/rbac_lint.py` (ou novo `scripts/migration_lint.py`) que detecta `permissions.set\|clear\|add` em migrations de `apps/core` criadas após data-cutoff. CI job já existente `[required] backend rbac-lint` herda.
- **Arquivos**: `scripts/rbac_lint.py`, possivelmente `tests/test_migration_lint.py`.
- **Testes**: criar migration fake violadora → lint falha; fixture de migration legítima → lint passa.
- **Risco**: baixo (preventivo).

---

## 6. Perguntas para decisão de produto

| Pergunta | Contexto | Opções | Recomendação |
|---|---|---|---|
| `CACHE_AVAILABILITY_TTL_SECS` deve ser settings ou Configuracao model? | Time pode querer mudar runtime sem deploy | (a) settings.py (deploy-only) (b) `Configuracao` (admin runtime) | (a) — TTL de cache é decisão técnica, não negócio |
| `REPORT_LOOKBACK_DAYS = 30` é configurável por usuário ou global? | Hoje é hardcoded em 3 funções | (a) constante global (b) query param na API | (a) primeiro; (b) depois se houver demanda |
| `AuditAction` TextChoices deve preservar valores atuais ou normalizar? | Hoje há ~50 strings; pode haver inconsistência (`PUBLISH_GCAL` vs `PUBLISH_GCAL_REQUESTED`) | (a) preservar tudo (zero migração de dados) (b) normalizar (precisa migration de UPDATE) | (a) — auditoria é histórico imutável; novos enum entries para futuro |

---

## 7. Conclusão

- **P0?** Não.
- **P1?** Sim — 4 (B1 AuditAction, B2 eventId asv2-, B3 status="aprovado" no RD service, D1 lint preventivo D17).
- **3 primeiros itens a atacar**:
  1. **PR E (D1)** — guard preventivo D17. Mais barato, evita regressão futura.
  2. **PR B parcial (B1)** — `AuditAction` TextChoices. Maior pay-off de longo prazo (auditoria pesquisável + validação de domínio).
  3. **PR A (R1-R3)** — elevar composições 3-ternárias a Policy. Fecha o ciclo do Hardening RBAC com consistência arquitetural.
- **Pode ficar para depois**:
  - PR C (magic numbers) — agrupar com qualquer PR que toque essas áreas.
  - PR D (getMe→context) — só se houver bug real de desincronização; refactor "porque sim" não justifica blast-radius.
  - B11/B12/B10 (P3 cosmético) — cleanup oportunista.
- **Não mexer**:
  - Migrations históricas 0074/0075/0077/0078/0080 (estado inicial; mexer reabre questão D17).
  - Whitelist de `groups.filter(name=...)` em `rbac/helpers.py`, `rbac/policies.py`, `rbac/permissions.py`, `views/stats.py`, `views_options.py` (todas com noqa correto).
  - `usePermissions.ts:80-89` (SSOT do frontend funcionando).
  - `RBAC_NAMING.md` §3, §5, §9 (deprecated marker correto).
  - Bloco autogen em `rbac_authorization_matrix.md` (gerado por `rbac_matrix_doc`).

---

## 8. Validação da auditoria

### Comandos principais usados pelos agentes

```bash
# Backend RBAC
rg "groups\.filter\(name|groups__name|group\.name|request\.user\.groups" v2/backend/apps --type py
rg '"(Controle|DAT|Diretoria|Gerente|Coordenador|Formador|Superintendência|Apoio de Coordenação|Assistente Administrativo|ACerta|Brincando|Fluir|Sou da Paz|Vidas)"' v2/backend/apps --type py
rg "permission_classes = \[" v2/backend/apps/core/views --type py
rg "HasPerm.*\|.*HasPerm.*\|" v2/backend/apps/core --type py
rg "noqa.*RBAC" v2/backend/apps --type py

# Backend business rules
rg '"(pendente|aprovado|reprovado)"' v2/backend/apps/core --type py --glob '!*models*' --glob '!*test*'
rg 'fluxo\s*==\s*"(SUPER|NAO_SUPER)"' v2/backend/apps/core/views --type py
rg 'timedelta\(days?=\d+\)' v2/backend/apps/core --type py --glob '!*test*'
rg 'action\s*=\s*"[A-Z_]+"' v2/backend/apps/core --type py
rg 'asv2-|f".*asv2' v2/backend/apps/core --type py --glob '!*test*'

# Frontend
rg "inDAT|inControle|inDiretoria|isGerente|isCoordenador|isFormador" v2/frontend/src --glob '!*types*' --glob '!*test*'
rg "getMe\(\)" v2/frontend/src/pages
rg "me\.policies|me\.groups|access\.can" v2/frontend/src/pages
rg "'(pendente|aprovado|reprovado)'" v2/frontend/src --glob '!*types*' --glob '!*test*'

# D17 / migrations
ls v2/backend/apps/core/migrations/00{75..82}*.py
rg "groups\.set\(|groups\.clear\(|permissions\.(set|add|clear)\(" v2/backend/apps/core/migrations
rg "can_approve_super|approve_super" v2/docs docs *.md
```

### Limites da auditoria

- **Não analisado em profundidade**: `apps/dat_imports/` (escopo do programa DAT-Imports recém-fechado, presumido limpo) — verificar se há viewsets além dos cobertos.
- **Não analisado**: `e2e/journeys/*.spec.ts` — Playwright tests podem ter strings de grupo, mas são fixtures de teste (aceitável).
- **Truncado**: agente 4 (D17) misclassificou inicialmente as migrations 0077/0078/0080 como "P0/P1" antes de re-classificar como histórico aceitável. A análise final está consistente.
- **Cross-check feito ad-hoc** apenas para F-020 (ApprovalsPage). Outras suspeitas frontend↔backend não foram cruzadas individualmente — mas a matriz viva (rbac/matrix.py) + sentinela já cobrem isso prospectivamente.

---

**Conclusão operacional**: Plataforma em bom estado de saúde RBAC e arquitetura. Não há urgência. Próximo passo recomendado é PR E (lint preventivo D17, ~30 min de trabalho) seguido de PR A (Policies das composições 3-ternárias, ~2h) — ambos de baixo risco e alto valor de longo prazo.
