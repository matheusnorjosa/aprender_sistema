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
| Assistente Administrativo | Função formal criada em PR 3 hardening RBAC (#1308). Sem poder desde o PR 8 (D23); a aprovação pelo par com o Setor `Controle` saiu no PR 11 (D26). | Setor vinculado |
| Formador | Declara próprio bloqueio (RD-02/03), participa de eventos | Próprios dados |

### Composites Setor × Função (PR 3 hardening RBAC, 2026-04-29)

| Composite | Setor | Função | Capacidade ganha |
|-----------|-------|--------|------------------|
| **Gerente da Superintendência** | `Superintendência` | `Gerente` | Aprovação de solicitações (individual + lote) — o par de grupos não aprova desde o PR 11 (D26); desde o PR B1 a aprovação vem do **vínculo** `EquipeGerencia` GERENTE vigente na gerência `SUPERINTENDENCIA`, sem grupo (D18) |
| **Assistente Administrativo do Controle** | `Controle` | `Assistente Administrativo` | Até o PR 11: aprovação de solicitações. Desde o PR 11 (D26) quem aprova é o vínculo EQUIPE/GERENTE na gerência `CONTROLE` (pacote); o par de grupos sozinho não aprova |
| **Gerente pedagógico** | `Vidas` / `Fluir` / etc. (não-Sup) | `Gerente` | Cria/edita solicitação (`create_solicitation`); **não aprova** |

### Princípio "ator transversal"

DAT e Controle entram em policies por **motivo legítimo de acesso** (decidir/operar/aprovar/auditar/suportar/validar), não por estar "no mesmo grupo organizacional" do setor que originou a feature. Ver `feedback_motivo_legitimo_acesso.md` (memória interna).

---

## 3. Matriz canônica — atores × recursos

A matriz abaixo é **autogerada** a partir de `apps/core/rbac/matrix.py` (PR 14
hardening RBAC, 2026-05-04). Espelha exatamente os gates de autorização
testados pelo PR 8 (`test_rbac_matrix_living.py`) e o snapshot literal do
PR 9 (`test_rbac_matrix_contract.py`).

Para atualizar:

1. Editar `apps/core/rbac/matrix.py` (entry de `ACCESS_MATRIX`).
2. Rodar `python manage.py rbac_matrix_doc --write` no container backend.
3. Commitar as duas mudanças juntas.

CI valida sync com `python manage.py rbac_matrix_doc --check` — drift
silencioso entre Markdown e Python falha o pipeline.

> Recursos não listados na matriz Python (Bloqueios, Reports,
> Ações Internas, Solicitações Criar, Dashboard Geral isolado) ficam fora
> deste contrato auto-sync. Suas regras vivem nos respectivos
> `permission_classes` e em testes dedicados; expansão de
> `ACCESS_MATRIX` para cobri-los é incremental.

<!-- BEGIN AUTOGEN: ACCESS_MATRIX -->

<!-- Bloco autogerado por `python manage.py rbac_matrix_doc --write`. Não editar manualmente — atualize `apps/core/rbac/matrix.py` -->

Legenda dos status codes (matriz executável):

- ✅ — `ALLOW` (HTTP 200) — gate aprova
- 🔒 — `DENY` (HTTP 403) — gate nega
- ⚠️ 400 — `ALLOW_PAYLOAD_INVALID` (HTTP 400) — gate aprova; serviço rejeita payload por motivo não-RBAC (ex: `ids: []` em batch-approve)

| Recurso (método URL) | Superuser | DAT | Controle | Diretoria | Gerente | Gerente da Superintendência | Assistente Administrativo do Controle | Coordenador | Apoio de Coordenação | Formador |
|---|---|---|---|---|---|---|---|---|---|---|
| **grade_mensal** (`GET /api/availability/monthly/`) | ✅ | ✅ | ✅ | 🔒 | ✅ | ✅ | ✅ | ✅ | ✅ | 🔒 |
| **deslocamentos** (`GET /api/deslocamentos/`) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **dashboard_compras** (`GET /api/dat/compras-materiais/dashboard/`) | ✅ | ✅ | 🔒 | ✅ | 🔒 | 🔒 | 🔒 | 🔒 | 🔒 | 🔒 |
| **metrics_team_productivity** (`GET /api/metrics/team/productivity/`) | ✅ | ✅ | ✅ | ✅ | 🔒 | 🔒 | ✅ | 🔒 | 🔒 | 🔒 |
| **ciclos_acoes** (`GET /api/ciclos-acoes/`) | ✅ | 🔒 | 🔒 | 🔒 | 🔒 | 🔒 | 🔒 | 🔒 | 🔒 | 🔒 |
| **audit_logs** (`GET /api/audit-logs/`) | ✅ | ✅ | ✅ | 🔒 | 🔒 | 🔒 | ✅ | 🔒 | 🔒 | 🔒 |
| **me_events** (`GET /api/me/events/`) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **solicitacoes_list** (`GET /api/solicitacoes/`) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **solicitacoes_batch_approve** (`POST /api/solicitacoes/batch-approve/`) | ⚠️ 400 | ⚠️ 400 | ⚠️ 400 | 🔒 | 🔒 | ⚠️ 400 | ⚠️ 400 | 🔒 | 🔒 | 🔒 |
| **produtos_list** (`GET /api/produtos/`) | ✅ | ✅ | ✅ | 🔒 | 🔒 | 🔒 | ✅ | 🔒 | 🔒 | 🔒 |
| **usuario_lookup** (`GET /api/lookup/usuarios/`) | ✅ | ✅ | 🔒 | 🔒 | ✅ | ✅ | 🔒 | ✅ | ✅ | 🔒 |
| **import_pela_tela** (`POST /api/controle/import-compras/`) | ⚠️ 400 | 🔒 | 🔒 | 🔒 | 🔒 | 🔒 | 🔒 | 🔒 | 🔒 | 🔒 |

*Para atualizar este bloco: edite `apps/core/rbac/matrix.py` e rode `python manage.py rbac_matrix_doc --write` no container backend.*

<!-- END AUTOGEN: ACCESS_MATRIX -->

---

## 4. Capability ↔ grupo (estado canônico pós migration 0080)

Estado autoritativo após `0080_redistribute_view_all_availability` (2026-04-28, que substituiu a 0078) e `0125_funcoes_sem_capacidade` (PR 8 das permissões, 15/10/2026: grupo de função sem capacidade; criar, editar e publicar vêm do papel vigente, `DIREITOS_PAPEL`; ver D23). Mudanças exigem migration data-only nova + atualização desta tabela.

| Capability | Grupos atribuídos | Justificativa |
|------------|-------------------|---------------|
| `approve_solicitation` | Superintendência | Aprovação executiva final (PA-02) |
| `create_solicitation` | — (papel COORDENADOR, APOIO ou GERENTE vigente, D23) | Quem cria pedido de evento |
| `edit_solicitation_as_owner_or_privileged` | — (papel COORDENADOR, APOIO ou GERENTE vigente, D23) | Edição da própria solicitação ou de qualquer com privilégio |
| `execute_restricted_operations` | Superintendência | Operações irreversíveis (bloqueio executivo) |
| `import_spreadsheet` | DAT | Sem efeito em endpoint desde 02/10/2026 (D20): nenhuma capability abre importação pela tela, só superusuário. O grupo segue atribuído, mas a capability não libera rota nem tela |
| `manage_admin_registries` | DAT | Manutenção de cadastros administrativos |
| `manage_purchases_and_materials` | DAT, Controle | Compras e materiais (DAT operacionaliza, Controle audita uso). A função Assistente Administrativo saiu no PR 8 (D23) |
| `operate_preagenda` | Controle | Operação diária do calendário. A função Assistente Administrativo saiu no PR 8 (D23) |
| `run_daily_operations` | Controle | Workflow diário do Controle (a função Assistente Administrativo saiu no PR 8, D23). Não abre importação pela tela desde 02/10/2026 (D20): só superusuário |
| `supervise_operations` | Diretoria | Visão executiva consolidada |
| **`view_all_availability`** | **Controle, DAT** *(Gerente perdeu a cap global na 0080 e cai em scope via EquipeGerencia; Coord/Apoio idem — D9)* | **Visão transversal sem restrição** (decisão D9, pós migration 0080) |
| `view_compras_dashboard` | Diretoria | Decisão executiva de compras |
| `view_map_metrics` | Diretoria, DAT | Métricas geográficas executivas. DAT: matriz de produção (D21) |
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
| D10 | Aprovação de solicitações = composite Setor × Função (Gerente da Sup OU Asst Admin do Controle) | 2026-04-29 (PR 3 #1308) | Consolidação da regra: PA-02 Adaptada (Sup OR DAT aprovavam) descontinuada. Após PR 3, `CanAccessSolicitationApprovals` exige composite Setor × Função. DAT/Sup pura/Gerente pedagógico não aprovam mais. Função formal `Assistente Administrativo` adicionada a `FUNCAO_GROUPS`. Policy nova `access_solicitation_approvals` em `PUBLIC_POLICY_KEYS`. |
| D11 | ProdutoViewSet list/retrieve = capability gate (DAT/Controle) | 2026-04-30 (PR 4 #1309) | Endpoint estava em `IsAuthenticated` puro por bug em `get_permissions()` override. Composite `manage_admin_registries OR manage_purchases_and_materials OR run_daily_operations`. Dropdowns/selects de Coord/Apoio/Diretoria continuam via `/api/options/produtos/`. |
| D12 | UsuarioLookup = capability gate, sem hardcode de grupos | 2026-04-30 (PR 5 #1310) | Endpoint era `IsAuthenticated` puro; SEC-ENUM-02 usava hardcode `_EMAIL_SEARCH_ROLES` (anti-pattern). Composition `create_solicitation OR manage_admin_registries`. SEC-ENUM-01 (email fora do payload) preservado. **S5 (2026-10-16, auditoria C6):** o login é o CPF, então a busca é por nome (e por e-mail só com termo sem dígito); `manage_admin_registries` e superuser acham também por CPF (qualquer grafia) ou e-mail, só com o valor exato. O rótulo de conta sem nome é `Usuario #id`, nunca o login. |
| D13 | AuditLog policy reduzida a DAT (admin) + Controle (operação) | 2026-04-30 (PR 6 #1311) | Antes incluía `approve_solicitation` e `approve_solicitation_batch` (Sup, Gerente). Removidos: Gerente pedagógico, Sup pura e Gerente da Sup não acessam mais. Auditoria por aprovador volta como escopo isolado se necessário em onda futura. SEC-AUDIT-01 (PII redaction) preservado. |
| D14 | Projeto.fluxo obrigatório explicitamente em criação | 2026-04-30 (PR 7 #1312) | Field tinha `default="NAO_SUPER"` que era aplicado silenciosamente quando ausente. Serializer + Admin form agora exigem `ChoiceField(required=True)` antes do DB. CheckConstraint preservado. Default no model preservado para fixtures internos. |
| D15 | Matriz Viva expandida com atores composite e novos recursos | 2026-04-30 (PR 8 #1313) | Atores `Gerente da Superintendência` e `Assistente Administrativo do Controle` adicionados ao `ACTOR_GROUPS`. Recursos `solicitacoes_batch_approve`, `produtos_list`, `usuario_lookup` adicionados a `RESOURCES`. Constante `ALLOW_PAYLOAD_INVALID = 400` adicionada para POSTs onde gate aprova mas payload é rejeitado por validação de serviço (não-RBAC). |
| D16 | Sentinela de drift da Matriz Viva (snapshot literal + endpoint coverage) | 2026-04-30 (PR 9) | `test_rbac_matrix_contract.py` congela `ACCESS_MATRIX` literalmente. `test_rbac_matrix_endpoint_coverage.py` exige que cada endpoint `/api/*` esteja em `MATRIX_ENDPOINT_COVERAGE` (recurso da matriz) ou `RBAC_MATRIX_EXEMPT_PREFIXES` (whitelist com motivo). Endpoint novo sem classificação → CI vermelho. Whitelist muda proibida — todo prefixo isento precisa de motivo declarado. |
| D17 | Atribuição **Group × Capability é admin-driven** pós-PR 16 (**substituída pela D21**) | 2026-05-04 (PR 16) | Capability codenames continuam SSOT em `apps/core/services/functional_permissions_seed.py` (16 itens, validados em `_validate_seed`). A relação Group × Capability migra para Django Admin superuser-only (`PermissaoFuncionalAdmin`). Migrations e seed futuros **só devem criar/remover/renomear** capability — não devem usar `groups.set()`/`groups.clear()` para sobrescrever atribuições admin. Reset de defaults, se necessário, vira comando explícito (não automático). Cada operação Admin emite AuditLog `GROUP_CAPABILITY_CHANGED` consolidado por capability (com `actor_user_id`, `capability_codename`, `added_groups`, `removed_groups`, `groups_after`). Cache funcional invalidado automaticamente via signal `m2m_changed`. Guardas estritos no Admin: add/delete bloqueados; codename, label, description, category, is_system read-only. |
| D18 | Aprovação pela **gerência** (vínculo) + **segregação** (PR B1) | 2026-09-29 | Aprova quem tem `EquipeGerencia` vigente com papel GERENTE na gerência `Gerencia.nome == "SUPERINTENDENCIA"` (`GERENCIA_APROVADORA_NOME`) — ninguém de g1 tinha o par de grupos. SSOT `solicitation_approval_basis` (`superuser` / `gerente_superintendencia` / `asst_admin_controle` / `grupo_superintendencia_gerente`), gravada em `AuditLog.details.autoridade`. Chave = `nome` (rótulos e `setor_canonico` são editáveis/reescritos; id muda entre ambientes); `Gerencia.ativo` não é checado. Segregação: ninguém decide a própria solicitação (403 `self_approval_forbidden`; lote → `errors[]`); superuser pode, marcado `details.autoaprovacao`. Anti-escalada no mesmo PR: importers recusam criar/reativar o vínculo aprovador, `validate_nome` protege a chave, lotação audita concessão/revogação. `is_superintendencia` não muda. O composite de grupos sai no B2. |
| D19 | **Escopo da aprovadora por vínculo** + trava de cadastro de projeto SUPER (regra do dono) | 2026-09-30 | A base `gerente_superintendencia` aprova/reprova (individual e lote), edita, exclui e cria **só** solicitação de projeto do fluxo SUPER da gerência `SUPERINTENDENCIA` (`projeto_no_escopo_da_superintendencia`, fail-closed). Fora: decidir → 403 `out_of_approval_scope` (lote → `errors[]`); editar/excluir → 403; criar/mover → 400 em `projeto`. **Ver não muda** (lista, detalhe, prévia). As próprias seguem editáveis como para qualquer coordenador. Não mudam: superuser, par Controle + Assistente Administrativo, par legado (sai no B2) e quem é global por capability (Controle/DAT) para editar/excluir. Exceção: 2º vínculo vigente de GERENTE dela em outra gerência (COORDENADOR, APOIO e FORMADOR não) abre criar/editar/excluir/mover naquela gerência, não decidir. Racional: o B1 pôs a policy em `user_is_solicitacao_global` e devolveu o `M10-01` para as 5 aprovadoras. Trava de cadastro: `fluxo = SUPER` só em projeto da `SUPERINTENDENCIA` (API 400, admin, import não cria SUPER, seed cria na g1) — toda pendente SUPER fica no escopo delas. |
| D21 | **Matriz Group × Capability muda só por PR** (D4 do [ADR-020](adr/ADR-020-lugar-onde-trabalha-da-o-poder.md)) | 2026-10-14 (PR A da arquitetura de permissões) | Substitui a D17. `FUNCTIONAL_PERMISSIONS_SEED[*].group_names` é a matriz, alinhada à de produção medida em 02/10 (DAT + `view_map_metrics`; Assistente Administrativo + `manage_purchases_and_materials`, `operate_preagenda`, `run_daily_operations`). Mudar = seed + migration de dados com `# noqa: RBAC-migration-allowed`, com `rbac_diff` no PR. `PermissaoFuncionalAdmin` só leitura (`has_change_permission → False`); `GroupSerializer` responde 400 quando `permissao_funcional_ids` difere do conjunto atual e nunca grava; a tela de Grupos mostra as permissões só para leitura. `rbac_diff --auditar` (checklist pós-deploy) sai com exit 1 se banco ≠ seed ou se houver gerência com perfil ≠ PADRAO fora de `PERFIL_PERMITIDO`. No mesmo PR: `Gerencia.perfil` (sem efeito até o PR B), trava dos importadores para EQUIPE/GERENTE em gerência com pacote (`vinculo_com_pacote_bloqueado`) e lint V004/V005. |
| D20 | **Importação pela tela = só superusuário** | 2026-10-02 (decisão do dono) | Nenhuma importação pela tela na liberação: as cargas passam por script (`import_export_contract`), com ensaio. As 13 rotas de upload de planilha (12 endpoints + 1 alias, `/api/import-compras/`) trocam `HasPerm("import_spreadsheet")` / `HasPerm("manage_admin_registries")` / `CanImportGenericSpreadsheet` por `[IsAuthenticated, SuperuserOnly]`; nenhuma capability abre. Recurso `import_pela_tela` na Matriz Viva (representado por `POST /api/controle/import-compras/`); rota a rota em `test_imports_pela_tela_so_superusuario.py`, com sentinela para view nova que receba arquivo (`APIView`, `@api_view` ou rota de `ViewSet`; sinais: "import" na rota, parser de arquivo declarado, `request.FILES` lido no próprio handler ou `serializer_class` com campo de arquivo). A sentinela é uma rede auxiliar, não a garantia: ela **não pega** (a) a view que entrega o `request` a função de outro módulo sem ler arquivo no próprio handler, (b) o serializer escolhido só por `get_serializer_class()` e (c) a permissão definida só por `get_permissions()`. A garantia real são os testes por rota (cada perfil contra cada uma das 13 rotas) e a Matriz Viva (recurso `import_pela_tela`). No frontend, o item DAT > Importações, as rotas `/dat/importacoes`, `/dat/admin/colecoes` e `/dat/admin/equipe-gerencia` e os uploads dentro de Municípios e Usuários só aparecem para superusuário. Substitui a regra do PR-A1 DAT-Imports (2026-04-29, "DAT importa"). |
| D22 | **Front decide acesso só por policy** (PR 7 das permissões) | 2026-10-15 | Menu, rotas, botões e Página Inicial leem só `/api/me/policies/` (`useAcesso().caps`) e, onde a regra é o superusuário (importação pela tela, PA-02 do próprio, campos só dele, debug), o helper `ehSuperusuario`. Sem mudar poder: 5 policies públicas novas — `access_monthly_availability`, `access_availability_blocks`, `access_travel` (compostas, `TELAS_DE_ESCOPO`: `view_all_availability` OU o grupo que o front lia OU vínculo GERENTE/COORDENADOR/APOIO vigente em gerência ativa; provadas pessoa a pessoa em `test_rbac_politicas_de_tela.py`), `execute_restricted_operations` e `create_solicitation_without_purchase` (a capacidade de mesmo nome). Matriz persona × tela (menu e rotas) igual para os 10 atores; exceções aprovadas pelo dono só na Página Inicial: E1 "Enviar"/"Minhas Solicitações" por `create_solicitation` (DAT sai, Gerente entra), E2 "Desempenho da Equipe" por `view_team_dashboard` (Diretoria/DAT entram, Gerente do setor Gerência sai), E3 bloco Administração só do superusuário. Deploy: `rbac_diff --comparar` mostra só `+ policies` destas 5 chaves (o superusuário e quem tem Grade, Bloqueios ou Deslocamentos), 0 perdas e nada em grupos, capacidades ou vínculos (`TestRbacDiffDoDeploy`). Delta de tela fora de E1–E3, medido em `DELTA_MEDIDO` (`test_rbac_politicas_de_tela.py`) e pendente do aval do dono: Compras (`view_compras_stats`) abre para a função Assistente Administrativo sem o setor Controle e para vínculo EQUIPE ou GERENTE (os papéis com pacote) no CONTROLE e no ADMIN_OPERACIONAL; Editar solicitação abre para EQUIPE ou GERENTE no ADMIN_OPERACIONAL; o cartão do Google na Pré-agenda e a consulta periódica ao Google (`access_controle_section`) passam a valer para a função Assistente Administrativo sem o Controle e para EQUIPE ou GERENTE no CONTROLE; a página de Deslocamentos (`access_travel`, que inclui `view_all_availability`) passa a abrir lista e formulário para EQUIPE no CONTROLE e no ADMIN_OPERACIONAL, que antes chegavam pela rota e pelo menu (`view_all_availability`) e viam "Sem permissão" no check da própria página (o GERENTE já abria pelo vínculo de gestão). As APIs já autorizavam essas pessoas (`DeslocamentoViewSet` devolve tudo a quem tem `view_all_availability`); antes, Compras era link morto no submenu Controle para elas. `usePermissions`/`useCanAccess` apagados; trava `acessoSoPorPolicy.test.ts`. Os grupos de função saem das telas de escopo no PR 8. |
| D23 | **O papel dá o poder, não o cargo** (PR 8 das permissões) | 2026-10-15 | Grupo de FUNÇÃO sem capacidade (migration `0125`); `approve_solicitation_batch` e `IsGerenteSuperintendencia` apagadas. Criar, editar e publicar vêm do papel vigente em gerência ativa (`DIREITOS_PAPEL`; GERENTE não publica, O8-4); gestora de solicitação alheia = papel GERENTE; telas compostas por papel; bloqueio em nome de outra pessoa = `operate_preagenda` ∨ `manage_admin_registries` (Controle puro passa a delegar, O8-7); deslocamento em nome do formador da gerência para GERENTE e COORDENADOR vigentes (P16, O8-5); coordenador padrão e filtro `role` pelo papel. Matriz viva: o ator Formador passou a ter o papel FORMADOR, como em produção, e a API da grade mensal responde 200 a ele (`HasSectorAccess` aceita qualquer vínculo com escopo; já era assim em produção, a D8 só valia porque a fixture não tinha o vínculo). A tela da grade segue fechada para ele (policy `access_monthly_availability` = G/C/A). Estreitar a API é poder: PR 9, com medição. Aprovação por cargo (`APPROVER_COMPOSITES`) segue até o PR 11 |
| D24 | **Escopo por gerência** (PR 9 das permissões) | 2026-10-16 | O alcance é a gerência do projeto (`projeto.gerencia_id`), não o texto do setor; cada superfície conta só o papel vigente certo em gerência ativa: gestora de alheias = GERENTE (C9), publicação = APOIO, criar/mover, participantes, responsável (COORDENADOR), lookups, Grade, opções de formador e painel = G/C/A (`EquipeGerencia.gerencias_de_atuacao`). Fail-closed (projeto sem gerência, criador sem papel G/C/A). Decisões do dono (15/10): P9-5 (num evento da gerência A só entram pessoas da A) e P9-1 (a formadora vê só os próprios bloqueios e deslocamentos). Matriz viva: a API da grade mensal volta a responder 403 ao ator Formador (`HasSectorAccess` pede G/C/A, a mesma regra da tela). Lint V006 proíbe o setor nos arquivos de escopo |
| D25 | **DAT = administrador operacional** (PR 10 das permissões) | 2026-10-16 | Pacote `ADMIN_OPERACIONAL` final (aprova pela base 5 `capacidade_aprovar`, cria/edita/exclui em qualquer projeto, sem a regra da compra, Pré-agenda e seção Controle; sem `import_spreadsheet`); migration `0126` tira `import_spreadsheet` do grupo DAT e as capacidades do grupo Superintendência. Matriz viva: o ator DAT tem o vínculo EQUIPE na gerência DAT, como em produção, e `solicitacoes_batch_approve` vira `ALLOW_PAYLOAD_INVALID` para ele. Segregação (PA-02): ninguém decide a própria, a de autor cuja conta alterou nos 30 dias nem a que editou. **Contas (S4, substitui a decisão de 14/10):** o DAT altera todas, inclusive aprovadoras, outro DAT, Apoio e Controle; só a de superusuário fica protegida (`can_admin_mutate_target`). Diretoria fora do painel do Google. Troca de fluxo de projeto e evento auto-aprovado ficam no AuditLog. |
| D26 | **Uma fonte só para quem aprova** (PR 11 das permissões) | 2026-10-17 | O pacote `CONTROLE` ganha `approve_solicitation` (D1 de 06/10: todo o Controle aprova, pelo vínculo EQUIPE/GERENTE na gerência `CONTROLE`, decide qualquer evento como o DAT). Saem as bases por grupo `asst_admin_controle` (par Controle + Assistente Administrativo) e `grupo_superintendencia_gerente` (par Superintendência + Gerente): `solicitation_approval_basis` fica com `superuser`, `gerente_superintendencia` e `capacidade_aprovar`. Nenhum grupo tem nem dá a aprovação; o grupo Controle sem vínculo não aprova. Saem `APPROVER_COMPOSITES`, os helpers do par, `IsAssistenteAdministrativoControle`, o system check `rbac/checks.py` e a trava #2071 do par legado no formulário. Matriz viva: o ator Assistente Administrativo do Controle ganha o vínculo EQUIPE no Controle (expectativa ALLOW mantida, agora pelo vínculo). Sem migration. Em produção só a u7 muda de rótulo (mesmo poder); a Home dela passa a mostrar os eventos futuros de todas as gerências. Até o PR 12, `approve_solicitation` num grupo voltaria a dar aprovação pela união; travas: tela de Grupos só leitura, `test_nenhum_grupo_do_banco_aprova` (`-m migrations`) e `rbac_diff --auditar`. |
| D27 | **O corte: o poder vem só do lugar** (PR 12a e PR 12 das permissões) | 2026-10-17 | PR 12: `settings.RBAC_FONTE` com padrão `lotacao` (ausente ou vazia também; inválida derruba a subida). Grupo não soma capacidade nem abre Grade, Bloqueios ou Deslocamentos; `grupos_dao_poder()` guarda os dois pontos que liam grupo e a chave do cache inclui a fonte. `RBAC_FONTE=uniao` é a volta de emergência (DEPLOY_CHECKLIST §9). `PERFIL_PERMITIDO` ganha `DIRETORIA`. A Matriz Viva não muda no PR 12: os atores já trazem o vínculo de produção desde o 12a. Testes da mecânica grupo → capacidade usam a fixture `modo_uniao`. PR 12a, preparação: O ator Controle ganha o vínculo EQUIPE na gerência `CONTROLE` e o ator Diretoria o vínculo EQUIPE na gerência `DIRETORIA` (perfil `DIRETORIA`, pacote igual ao grupo do seed), como o DAT (D25) e o Assistente Administrativo do Controle (D26) já tinham. `solicitacoes_batch_approve` vira `ALLOW_PAYLOAD_INVALID` para o ator Controle (o pacote `CONTROLE` aprova, D1 de 06/10); as demais células não mudam. `ACTOR_GROUPS` fica como etiqueta. Nos testes, `UsuarioFactory(groups=[...])` com DAT, Controle ou Diretoria cria também o vínculo do pacote (`groups__vinculo=False` = só o grupo); os seeds `controle_e2e` e `dat_matrix` ganham o vínculo, e o seed de contrato deixa de pôr `view_compras_dashboard` no grupo DAT. |

---

## 7. Pendências conhecidas (rastreadas em ondas)

### Onda 1 — Críticos (próximo PR)

| # | Recurso | Problema | Fix |
|---|---------|----------|-----|
| C2 | Deslocamentos sidebar | UI mostra para Coord/DAT, backend exige `view_all_availability` (Controle/DAT após 0080) | Alinhar gate (esconder pra Coord) ou alargar backend (decisão pendente) |

### Onda 2 — Altos

| # | Recurso | Problema | Fix |
|---|---------|----------|-----|
| A3 | 4 viewsets com `[IsAuthenticated]` apenas | Confiando 100% em queryset filter; sem capability check explícito | Adicionar `CanAccessBlocks` ou similar |

### Concluído (entregue — antes rastreado aqui como pendência)

- **C1 — Dashboards no menu** e **A2 — Dashboard Compras**: o menu lê as policies
  (`view_team_dashboard`, `view_map_metrics`, `view_gcal_dashboard`, `view_compras_dashboard`) desde o
  #1270; as flags de organograma (`usePermissions`) foram apagadas no PR 7 (D22).

- **C3 — Ações Internas**: `[IsAdminUser]` substituído pela capability `manage_internal_actions`
  (migration `0079_add_manage_internal_actions`); `CicloAcoesViewSet`/`AcaoInstanciaViewSet` usam
  `HasPerm("manage_internal_actions")`.
- **A1 — `SolicitacaoViewSet.create`**: a action `create` já exige `HasPerm("create_solicitation")`.
- **Onda 3 — Matriz Viva**: entregue — `apps/core/rbac/matrix.py` é o SSOT lido pelos testes
  sentinela (`test_rbac_matrix_living.py`, `test_rbac_matrix_contract.py`,
  `test_rbac_matrix_endpoint_coverage.py`, `test_rbac_matrix_scope.py`); o bloco AUTOGEN desta
  página é gerado dele.

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
- `apps/core/rbac/permissions.py` — `HasPerm`, `HasSectorAccess`, `IsOwnerOrPrivileged` (`IsGerenteSuperintendencia` saiu no PR 8)
- `v2/frontend/src/contexts/AcessoContext.ts` — fonte única de acesso no front (`useAcesso`, `ehSuperusuario`; D22)
- `v2/frontend/src/hooks/useCapabilities.ts` — uma flag por policy pública
- `v2/frontend/src/components/access/RequirePolicy.tsx` — wrapper de rota
