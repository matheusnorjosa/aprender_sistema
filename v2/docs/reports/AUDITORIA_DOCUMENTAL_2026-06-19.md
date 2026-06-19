# Auditoria Documental Completa — 2026-06-19

> Status: report (datado) · Repo @ `cbf10a7` (branch `main`) · Método: auditoria multi-agente read-only (14 agentes)
> Escopo: todos os `.md` versionados e locais. Nenhum arquivo foi movido, apagado ou reescrito.
> Documento-irmão: plano de migração em [`../plans/PLAN_sdd_migration_2026-06-19.md`](../plans/PLAN_sdd_migration_2026-06-19.md).

## 1. Resumo executivo

A documentação do projeto é **abundante e, nos pilares arquiteturais, de alta qualidade** (RBAC, GCal,
disponibilidade, aprovação, imports, backup/DR, CI/deploy têm SSOT claro e alinhado ao código). O problema
não é falta de docs — é **canonicidade ambígua**: 326 arquivos `.md` reais sem metadados que distingam o que
é fonte de verdade viva do que é registro histórico ou já desatualizado.

Achados de maior impacto:

1. **21 documentos `stale`** (desatualizados e *não* marcados como históricos) — alguns em posição canônica/ativa,
   logo enganosos se lidos hoje. Os piores: `docs/guides/etl.md` (ensina 21 comandos ETL que não existem),
   `docs/guides/rbac.md` (ensina o anti-padrão banido e omite o SSOT `apps/core/rbac`), `INDEX_DOCUMENTACAO.md`
   (declara 33 models incluindo `dat_ingest` removido), `docs/architecture/backend.md` e `infrastructure.md`.
2. **31 links markdown relativos quebrados** (de 223 checados); 8 deles em docs canonical/active — destaque para
   `v2/docs/OBSERVABILITY.md` e `v2/docs/ENV_VARS_ETL.md`, arquivos **fantasmas** referenciados por README + INDEX + LOGGING.
3. **Conhecimento crítico vive fora do git**: `CP-07` e `CP-08` (cláusulas pétreas *enforced* por hook/settings)
   só têm definição completa em `.claude/CLAUDE.md`, que é **gitignored**. Pior: o `.gitignore` tem padrões *bare*
   `CLAUDE.md`/`AGENTS.md` que ignoram também o `CLAUDE.md` da raiz e `v2/docs/AGENTS.md` — somem em qualquer clone novo.
4. **`specs/CONSTITUTION.md` não é fonte canônica**: `specs/` não existe nem é versionado (`git ls-files specs` = 0)
   e nenhum doc versionado o referencia. Confirmado e descartado como SSOT.
5. **Lacunas de documentação** em módulos reais: `core.deslocamento` (código substancial, zero doc dedicado) e os
   hooks RBAC do frontend (`usePermissions`/`useCanAccess`, sem doc).

A recomendação é adotar um modelo **SDD (Spec-Driven Development)**: uma camada de *specs* vivas, versionada, com
metadados mínimos (`status` + `last_verified` + `sources_of_truth`), separada de runbooks, ADRs, planos e histórico.
O plano está no documento-irmão.

## 2. Escopo e números do inventário

| Métrica | Valor | Fonte |
|---|---:|---|
| Total `.md` reais (excl. vendor) | **326** | git |
| — `.md` **versionados** | **210** | `git ls-files '*.md'` |
| — `.md` **locais/ignorados** (não-vendor) | **116** | `git ls-files --others --ignored` |
| — `.md` **untracked** (não-ignorados) | **0** | `git ls-files --others --exclude-standard` |
| `.md` em vendor (node_modules/.venv) — fora de escopo | 1065 | git |
| Links relativos checados | **223** | script |
| Links relativos **quebrados** | **31** | script |

Distribuição dos 210 versionados:

| Diretório | Qtd | Diretório | Qtd |
|---|---:|---|---:|
| `v2/docs/` (raiz) | 47 | `docs/architecture/` (inc. ADRs) | 24 |
| `v2/docs/analysis/` | 28 | `docs/` (operations/guides/business-rules/...) | 22 |
| `v2/docs/plans/` | 22 | `v2/backend|frontend|infra|tests/` | 14 |
| `v2/docs/_archive/` | 20 | raiz (README/SECURITY/CONTRIBUTING/...) | 5 |
| `v2/docs/issues/` | 13 | `v2/docs/imports/` | 7 |
| `v2/docs/reports/` | 6 | `v2/docs/audits|adr/` | 2 |

Os **116 locais/ignorados** são quase todos ferramental de agente: `.claude/` (57: CLAUDE.md, commands, cheatsheets,
agents, skills) e `.agents/skills/` (~33). São **regra operacional local**, não contrato versionado.

## 3. Classificação por canonicidade (210 versionados)

| Classe | Qtd | Definição |
|---|---:|---|
| `canonical` | 34 | Fonte única de verdade, autoritativa hoje, casa com o código. |
| `active` | 59 | Útil/atual e mantido, mas não é o SSOT. |
| `historical` | 96 | Arquivo intencional (`_archive/`, `analysis/`, planos concluídos, relatórios datados). |
| `stale` | 21 | Desatualizado/contradiz o código e **não** marcado como histórico → enganoso. |
| `local` | (116) | Não versionado / máquina-específico (`.claude/`, `.agents/`). |

> Observação: **46% do acervo versionado é histórico** (`analysis/` + `_archive/` + planos concluídos). Isso é
> saudável como registro, mas hoje está misturado com o conteúdo vivo no mesmo nível de navegação, sem sinalização.

## 4. Fontes canônicas atuais (SSOT por domínio)

| Domínio | Documento(s) canônico(s) | Casa com código? |
|---|---|---|
| RBAC | `v2/docs/RBAC_NAMING.md`, `v2/docs/rbac_authorization_matrix.md`, `v2/backend/apps/core/rbac/README.md` | Sim (HasPerm/Policy) |
| Google Calendar | `v2/docs/GUIDE_GCAL.md`, ADR-008 | Sim |
| Disponibilidade (RD-01..08) | `v2/docs/GUIDE_AVAILABILITY.md`, `docs/business-rules/regras-disponibilidade.md`, ADR-003 | Sim |
| Aprovação (PA-01..07) | `docs/business-rules/politica-aprovacao.md`, ADR-002 | Sim |
| Imports | `v2/backend/apps/core/imports/README.md`, `v2/docs/imports/*`, ADR-012 (SHA-1) | Sim |
| Backup/DR | `v2/docs/BACKUP_OPERATIONS.md`, `GUIDE_DR.md`, `DISASTER_RECOVERY.md` | Sim |
| Concorrência | `v2/docs/ACID_POLICY.md`, `RUNBOOK_concurrency.md` | Sim |
| Testes | `v2/docs/TESTING_MSW.md`, `analysis/COVERAGE_POLICY.md` | Sim |
| DAT | `v2/docs/SPEC_DAT_REGISTROS.md` | Sim |
| Infra/Deploy | ADR-001 (Docker-only), ADR-010 (Portainer→prod), `v2/infra/ENVIRONMENTS.md`, `RUNBOOK.md` | Parcial (ver §6) |
| Decisões | `docs/architecture/project-decisions/ADR-001..014` | Sim |
| Cláusulas pétreas | `docs/business-rules/clausulas-petreas.md` | **Incompleto: só CP-01..06** (ver §6) |

## 5. Documentos locais ou não canônicos

- **`.claude/` (gitignored, `.gitignore:570`)** — 57 `.md`. Contém `CLAUDE.md` (índice operacional do projeto),
  `CLAUDE-principles.md`, commands, cheatsheets, agents, skills. **Risco:** carrega contratos que não existem
  versionados (CP-07/CP-08; ver §6). Um exemplo "Bom" em `CLAUDE-principles.md` ainda ensina o anti-padrão
  `user.groups.filter(name=...)` (banido por `scripts/rbac_lint.py`).
- **`.agents/skills/` (gitignored)** — ~33 `.md`. **Não é espelho** de `.claude/skills/`: 7 SKILL.md divergem em
  conteúdo + 8 `source-command-*` só existem aqui. Duplicação local divergente.
- **`specs/`** — **inexistente e não versionado**. `specs/CONSTITUTION.md` **não deve ser tratado como fonte
  canônica** (não existe). Nenhum doc versionado o referencia (sem risco de link quebrado em outra máquina).

## 6. Achados de staleness (os 21 `stale` + divergências)

### 6.1 Críticos (canonical/active, enganam se lidos hoje)

| Doc | Problema | Recomendação |
|---|---|---|
| `docs/guides/etl.md` | Documenta **21 comandos ETL** (`import_usuarios/formadores/projetos/solicitacoes`...) que **não existem**; único command real é `import_export_contract`. ETL backend (`dat_ingest`) foi removido (#967/#971). Está na nav do MkDocs. | Reescrever apontando para imports via endpoints DRF (`v2/docs/imports/`) ou remover da nav + banner de deprecação. |
| `docs/guides/rbac.md` | Ensina modelo **legacy** (grupos + `views_basic.py`), **omite o SSOT** `apps/core/rbac` (HasPerm/Policy). Lista 9 setores/4 funções (real: 13/5). | Reescrever para HasPerm/Policy; apontar `RBAC_NAMING.md`; sincronizar contagens com `constants.py`. |
| `v2/docs/INDEX_DOCUMENTACAO.md` | Declara "33 models (28 core + **5 dat_ingest**)" e lista `dat_ingest` como app vivo; "9 setores"; métricas datadas. + 2 links quebrados (§7). | Atualizar para apps reais (core + dev_tools), 13 setores; corrigir links. |
| `docs/architecture/backend.md` | Cita `models/availability.py` (inexistente — vive em `organizacao.py`/`agenda.py`), `approval_service.py` (real: `solicitacao_approval.py`), "rotinas ETL". | Corrigir nomes de arquivos; remover ETL. |
| `docs/architecture/infrastructure.md` | Diz que o deploy é "**GitHub Pages**"; real é Portainer→prod (ADR-010); omite `deploy.yaml`. | Reescrever a seção de deploy citando ADR-010. |
| `docs/architecture/overview.md` | Mostra `dat_ingest/` na árvore de apps. | Remover a linha; deixar core + dev_tools. |
| `docs/architecture/dependency-guardrails.md` / `ADR-012-dependency-guardrails.md` | Referenciam `dat_ingest` como guardrail vivo. | Marcar a parte de `dat_ingest` como histórica (módulo removido). |

### 6.2 Divergências de versão/stack

A grande maioria está **correta** (React 18 consistente — *nenhum* "React 19"; PostgreSQL 15, Redis 7, Vite 7, Antd 5,
Node 20, Django 5.2, MSW 2.x fiéis). Divergências reais:

- `v2/docs/TESTING_POLICY.md` diz **Python 3.11** no CI; real é **3.12** (todos os workflows + Dockerfiles). *(médio)*
- `deploy.md` / `RUNBOOK.md` / `DEPLOY_CHECKLIST.md` descrevem **staging remoto** via Portainer, contradizendo
  **ADR-010** (Accepted: sem staging remoto; merge=prod). O `deploy.yaml` de fato seta `target_environment=staging`
  no push — então os docs casam com o *workflow* mas batem de frente com o ADR + realidade. **Reconciliar.** *(médio)*
- `docs/index.md`: "DRF 3.16" (real 3.17.1); `RUNBOOK.md`: "Django 5.2.1" (real 5.2.15). *(baixo)*
- `docs/guides/observability.md`: stack real (Sentry + django-prometheus + Grafana), só versões defasadas. *(baixo)*
- `BACKLOG_MAPA_BRASIL.md`: snippet com `jest.fn()` (projeto usa Vitest/MSW); `BACKLOG_FRONTEND_CODE_SPLITTING.md`
  sugere `manualChunks` (anti-padrão que quebrou prod). *(baixo, são backlogs datados)*

### 6.3 Divergências entre camadas (`.claude` × `docs` × `v2/docs`)

- **CP-07/CP-08 fora do git** *(alto):* `docs/business-rules/clausulas-petreas.md` para em **CP-06**. CP-07 (no push main)
  e CP-08 (`INCLUDE_DEV_TOOLS=false`) só têm texto completo em `.claude/CLAUDE.md` (gitignored). ADR-004 e INDEX os
  *citam* sem definir. **Promover CP-07/CP-08 ao SSOT versionado.**
- **`.gitignore` bare `CLAUDE.md`/`AGENTS.md`** *(alto):* ignora também o `CLAUDE.md` da raiz e `v2/docs/AGENTS.md`.
  Decidir: versionar (escopar ignore para `/.claude/`) ou migrar o conteúdo crítico para docs versionados.
- **Funções 5 vs 4** *(médio):* `constants.py` tem 5 (`FUNCAO_GROUPS`, inclui "Assistente Administrativo"); `.claude/CLAUDE.md`
  e INDEX dizem 4. **Setores 13 vs 9** *(médio):* código/`.claude` = 13; INDEX/MAPEAMENTO ainda dizem 9.
- **RBAC_NAMING importa de caminhos legados** *(médio):* ensina `from apps.core.permissions import HasPerm` e
  `apps.core.rbac_helpers`, enquanto o SSOT declarado é `apps.core.rbac` (os legados ainda existem como shim).

## 7. Links quebrados relevantes (8 de 31, em canonical/active)

| Origem | Alvo | Diagnóstico |
|---|---|---|
| `v2/README.md` | `docs/OBSERVABILITY.md` | Alvo **inexistente** (`v2/docs/OBSERVABILITY.md`). |
| `v2/docs/INDEX_DOCUMENTACAO.md` | `./OBSERVABILITY.md` | Mesmo arquivo fantasma. |
| `v2/docs/INDEX_DOCUMENTACAO.md` | `./ENV_VARS_ETL.md` | Fantasma; provável resíduo da remoção do ETL. |
| `v2/docs/LOGGING.md` | `./OBSERVABILITY.md` (x2) | Mesmo fantasma. |
| `v2/OAUTH_ENV_VARIABLES.md` | `../docs/GUIDE_GCAL.md` | Um `../` a mais — alvo real é `docs/GUIDE_GCAL.md` (= `v2/docs/`). |
| `v2/OAUTH_ENV_VARIABLES.md` | `../docs/fechar_plano_gcal.md` | Inexistente em todo o repo. |
| `v2/infra/README.md` | `../docs/PLAN_infrastructure_scaling.md` | Movido para `v2/docs/_archive/plans/`. |

Os outros 23 são históricos: 1 em `PLANO_MELHORIAS_DETALHADO.md` e **22 em `v2/docs/analysis/rbac_system_inventory.md`**
(todos com o mesmo bug de profundidade `../` — faltou um nível; os arquivos-alvo existem). Correção mecânica única.

## 8. Mapa dos módulos reais × documentação

**Backend real = APENAS `apps/core` (28 models) + `apps/dev_tools`.** `apps.dat_ingest` foi removido; `INCLUDE_ETL` é ignorado.

| Camada | Módulo/subsistema | Doc? | Observação |
|---|---|:--:|---|
| Backend | RBAC, GCal, Disponibilidade, Aprovação, Imports, Backup/DR, DAT, Concorrência | ✅ | Cobertura canônica forte, casa com código. |
| Backend | **`core.deslocamento`** | ❌ | **GAP**: `views_deslocamento.py` (10.5K) + import service + página FE dedicada; **zero** doc, zero menção no `API_REFERENCE`. |
| Backend | `core.acoes_notificacao` | ⚠️ | Só `PLANO_NOTIFICACOES_TIMING.md` (plano, não runbook). |
| Backend | `apps.dev_tools` (15 seed commands) | ⚠️ | Design só em plano `_archive`; sem catálogo versionado por comando. |
| Frontend | 14 pages | ⚠️ | `frontend.md` cobre ~6/14; CLAUDE.md diz "45+ lazy pages" (real: 14 dirs → número inflado/stale). |
| Frontend | 14 hooks (`usePermissions`/`useCanAccess`...) | ❌ | **GAP**: hooks RBAC-críticos sem doc. |
| Frontend | ~21 components | ⚠️ | Só `RemoteSelect`/`MeetLink` documentados. |
| Frontend | 15 api clients | ✅ | Contrato via `API_REFERENCE` + ADR-013 (axios→fetch). |
| Infra | compose/docker, scripts/systemd, CI workflows | ✅ | `RUNBOOK.md` (42.9K), `ENVIRONMENTS.md`, ADRs, docs xdist-canary frescos (2026-06). |

**Docs que descrevem o inexistente:** `docs/guides/etl.md`, `INDEX_DOCUMENTACAO.md`, `docs/architecture/backend.md`,
`docs/architecture/infrastructure.md` (ver §6). Menções a `dat_ingest` em `_archive/`, `analysis/`, `PLAN_remove_etl_backend`,
`RELEASE_NOTES`, `ADR-012` são **históricas/intencionais** — não acionáveis.

## 9. Recomendações operacionais

Prioridade (alta → baixa):

1. **Corrigir os fantasmas + stale crítico** (alto): criar/remover refs a `OBSERVABILITY.md`/`ENV_VARS_ETL.md`;
   reescrever ou deprecar `docs/guides/etl.md` e `docs/guides/rbac.md`; corrigir `backend.md`/`infrastructure.md`/`overview.md`/INDEX.
2. **Versionar os contratos críticos** (alto): promover **CP-07/CP-08** para `docs/business-rules/clausulas-petreas.md`;
   decidir o destino de `CLAUDE.md`/`AGENTS.md` (escopar `.gitignore`).
3. **Adotar metadados de canonicidade** (alto): frontmatter `status` + `last_verified` + `sources_of_truth` em todo doc vivo.
4. **Preencher gaps** (médio): spec de `core.deslocamento`; doc dos hooks RBAC do frontend; catálogo de seed commands.
5. **Sincronizar contagens** (médio): 13 setores / 5 funções (gerar a partir de `constants.py`/`rbac_matrix_doc`).
6. **Automatizar** (médio): gate de **links relativos quebrados** no CI (o script desta auditoria é reaproveitável).
7. **Separar histórico do vivo** (baixo): consolidar `analysis/` + planos concluídos sob `_archive/` e sinalizar na nav.

A execução estruturada está no plano SDD: [`../plans/PLAN_sdd_migration_2026-06-19.md`](../plans/PLAN_sdd_migration_2026-06-19.md).

---

_Gerado por auditoria read-only (14 agentes; ~1M tokens). Nenhum arquivo de documentação existente foi alterado por esta auditoria além da criação deste relatório, do plano-irmão e da atualização dos índices `reports/README.md` e `plans/README.md`._
