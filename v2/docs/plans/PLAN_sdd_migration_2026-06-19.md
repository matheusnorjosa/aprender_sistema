# Plano de Migração SDD (Spec-Driven Development) — 2026-06-19

> Status: plano ativo (não-iniciado) · Base: [`../reports/AUDITORIA_DOCUMENTAL_2026-06-19.md`](../reports/AUDITORIA_DOCUMENTAL_2026-06-19.md)
> Regra deste plano: **nenhum arquivo é movido nesta etapa**. Isto descreve a estrutura-alvo e as fases.

## 1. Objetivo

Transformar um acervo de **326 `.md`** (210 versionados, 116 locais) — hoje sem sinalização de canonicidade,
com 21 docs `stale` e 31 links quebrados — num modelo **Spec-Driven Development**: cada módulo/contrato vivo tem
uma **spec versionada, datada e rastreável ao código**, claramente separada de runbooks, ADRs, planos e histórico.

Resultado esperado: ler qualquer doc e saber, sem ambiguidade, **se é verdade hoje**, **qual código é a fonte**, e
**quando foi verificado pela última vez**.

## 2. Princípios

1. **Spec = contrato vivo, código = implementação.** A spec descreve o comportamento esperado; o código é o SSOT
   técnico. Toda spec aponta para os arquivos de código que a realizam (`sources_of_truth`).
2. **Canonicidade explícita.** Todo doc vivo declara `status` no frontmatter. Sem frontmatter ⇒ tratar como histórico.
3. **`last_verified` obrigatório.** Doc sem verificação recente é candidato a `stale`, não a `canonical`.
4. **Uma verdade por tópico.** Um SSOT por domínio; os demais docs *linkam*, não duplicam (evita drift de contagens).
5. **Histórico é imutável e isolado.** `analysis/`, `_archive/`, planos concluídos e relatórios datados não se "corrigem" —
   ficam como registro, fora da navegação viva.
6. **Nada crítico fora do git.** Contratos *enforced* (CP-01..08, RBAC) vivem em docs versionados, não em `.claude/`.
7. **Gerar em vez de copiar.** Tabelas que derivam do código (setores/funções, endpoints) são geradas (ex.: `rbac_matrix_doc`),
   não transcritas à mão.
8. **Migração sem perda.** Não apagar; mover para `_archive/` preservando histórico git; corrigir links no mesmo passo.

## 3. Estrutura-alvo

Camada de specs **nova e versionada**, sob `v2/docs/specs/` (sob `v2/docs/`, que é versionado — **não** usar `specs/` na
raiz, que é ambíguo/inexistente). Os diretórios existentes permanecem; o conteúdo migra por fases.

```text
v2/docs/
  specs/                      # NOVO — specs vivas (SSOT por domínio), com frontmatter obrigatório
    domain/                   # regras de negócio (contratos imutáveis)
      clausulas-petreas.spec.md      # CP-01..CP-08 (inclui CP-07/CP-08 hoje fora do git)
      regras-disponibilidade.spec.md # RD-01..RD-08
      politica-aprovacao.spec.md     # PA-01..PA-07
      requisitos-funcionais.spec.md  # RF-xx
    backend/
      rbac.spec.md            availability.spec.md      solicitacao-approval.spec.md
      gcal.spec.md            imports.spec.md           backup-dr.spec.md
      dat.spec.md             notificacoes.spec.md      deslocamento.spec.md   # GAP hoje
    frontend/
      pages.spec.md           hooks-rbac.spec.md        api-clients.spec.md
    infra/
      deploy.spec.md          environments.spec.md      ci.spec.md
  decisions/                  # ADRs (hoje em docs/architecture/project-decisions/) — alvo de consolidação
  runbooks/                   # operacional vivo: RUNBOOK, BACKUP_OPERATIONS, DISASTER_RECOVERY, SCALING
  reference/                  # API_REFERENCE, RBAC_NAMING, SLO_DEFINITIONS, TESTING_MSW
  reports/                    # relatórios datados (esta auditoria mora aqui)
  plans/                      # planos ativos (este plano mora aqui)
  _archive/                   # histórico (analysis/, planos concluídos, snapshots)
```

> Nota de transição: na Fase 1, `specs/` é criada e os docs canônicos existentes **passam a ser linkados** a partir
> dela (índice), sem mover. Os moves físicos para `runbooks/`/`reference/`/`decisions/` só ocorrem nas Fases 5-6,
> sempre corrigindo os links no mesmo commit.

## 4. Metadados mínimos por documento vivo (frontmatter)

Todo doc em `specs/`, `runbooks/`, `reference/` e `decisions/` deve começar com:

```yaml
---
title: Disponibilidade (RD-01..08)
status: canonical          # canonical | active | draft | stale | historical
last_verified: 2026-06-19  # data da última checagem contra o código
sources_of_truth:          # arquivos de código que esta spec descreve
  - v2/backend/apps/core/services/availability_service.py
  - v2/backend/apps/core/views_availability.py
owner: backend             # área responsável
supersedes: []             # docs que esta spec substitui (a serem arquivados)
related:                   # links a specs/ADRs relacionados
  - ../infra/deploy.spec.md
---
```

Regra de lint (Fase 6): doc vivo sem `status`/`last_verified` falha o gate; `last_verified` > 180 dias vira aviso.

## 5. Template de documentação por módulo (`*.spec.md`)

```markdown
# <Módulo> — Spec
<frontmatter acima>

## Propósito
O que este módulo faz e por que existe (1-2 parágrafos).

## Fonte de verdade no código
Arquivos/serviços que implementam (com caminhos clicáveis).

## Contratos e invariantes
Regras que NÃO podem ser violadas (RD/PA/CP aplicáveis; limites; idempotência).

## API / Interface
Endpoints, comandos, ou props públicas (linkar API_REFERENCE quando houver).

## Fluxos principais
Passo-a-passo dos caminhos felizes + erros relevantes.

## Decisões relacionadas (ADRs)
Links para decisions/.

## Testes que cobrem
Arquivos de teste que provam os contratos acima.

## Pontos de atenção / dívidas conhecidas
Gaps, TOCTOU, itens de backlog (linkar issues).
```

## 6. Lista de módulos a documentar (do mapa de módulos)

Prioridade por lacuna/risco (do relatório §8):

| Spec-alvo | Estado hoje | Ação |
|---|---|---|
| `backend/deslocamento.spec.md` | **Sem doc** (GAP) | **Criar do zero** (view 10.5K + import + página FE). |
| `frontend/hooks-rbac.spec.md` | **Sem doc** (GAP) | **Criar** (`usePermissions`/`useCanAccess`/`useGoogleGuard`/polling). |
| `infra/deploy.spec.md` | `infrastructure.md` stale ("GitHub Pages") | Reescrever via ADR-010 (Portainer→prod). |
| `backend/rbac.spec.md` | `docs/guides/rbac.md` stale (anti-padrão) | Reescrever via `RBAC_NAMING`/`apps/core/rbac`. |
| `backend/imports.spec.md` | `docs/guides/etl.md` stale (21 cmds) | Substituir ETL por imports DRF (`v2/docs/imports/`). |
| `domain/clausulas-petreas.spec.md` | versionado só CP-01..06 | Adicionar CP-07/CP-08 (hoje só em `.claude/`). |
| `backend/{availability,gcal,approval,backup-dr,dat}.spec.md` | doc canônico existe | Migrar conteúdo + frontmatter (Fase 3). |
| `frontend/pages.spec.md` | 6/14 documentadas | Completar + corrigir "45+ pages". |
| `apps.dev_tools` (catálogo seed) | só plano `_archive` | Catálogo versionado dos 15 commands. |

## 7. Fases de execução

> Cada fase = 1 PR (CP-06, squash). Nenhum move sem correção de links no mesmo commit.

- **Fase 0 — Fundação (sem mover):** criar `v2/docs/specs/` + `INDEX_SDD.md` (índice vivo) + convenção de frontmatter.
  Corrigir os **8 links quebrados** de canonical/active (fantasmas `OBSERVABILITY.md`/`ENV_VARS_ETL.md`, `OAUTH_ENV_VARIABLES`,
  `infra/README`). **Saída:** esqueleto + zero link quebrado em canonical/active.
- **Fase 1 — Contratos para o git:** promover **CP-07/CP-08** ao `clausulas-petreas.md`; decidir `.gitignore` de
  `CLAUDE.md`/`AGENTS.md` (escopar para `/.claude/`); ADR de "documentação SDD".
- **Fase 2 — Reconciliar stale crítico:** reescrever/deprecar `docs/guides/etl.md`, `docs/guides/rbac.md`,
  `docs/architecture/backend.md`, `infrastructure.md`, `overview.md`, `INDEX_DOCUMENTACAO.md`; corrigir versões
  (`TESTING_POLICY` 3.12; `index.md` DRF 3.17; staging vs ADR-010).
- **Fase 3 — Specs canônicas:** migrar conteúdo dos canônicos vivos (rbac, gcal, availability, approval, imports,
  backup-dr, dat) para `specs/` com frontmatter; deixar redirects/links nos antigos (ainda sem deletar).
- **Fase 4 — Preencher gaps:** `deslocamento.spec.md`, `hooks-rbac.spec.md`, catálogo dev_tools, pages restantes.
- **Fase 5 — Histórico:** mover `analysis/` + planos concluídos para `_archive/`; corrigir os 22 links de
  `rbac_system_inventory.md`; isolar histórico da nav viva.
- **Fase 6 — Automação:** gate CI de **links relativos quebrados** (reusar o script da auditoria) + lint de
  frontmatter (`status`/`last_verified`) + geração de tabelas RBAC a partir de `constants.py`.

## 8. Backlog inicial (acionável)

1. [F0] Criar `v2/docs/specs/INDEX_SDD.md` + 4 subdirs.
2. [F0] Remover/recriar refs a `v2/docs/OBSERVABILITY.md` (README + INDEX + LOGGING) — decidir: criar a spec de
   observability ou apontar para `docs/guides/observability.md`.
3. [F0] Remover ref a `v2/docs/ENV_VARS_ETL.md` no INDEX (resíduo de ETL removido).
4. [F0] Corrigir `OAUTH_ENV_VARIABLES.md` (2 links: `../docs/`→`docs/`; remover `fechar_plano_gcal.md`).
5. [F0] Repontar `v2/infra/README.md` → `../docs/_archive/plans/PLAN_infrastructure_scaling.md`.
6. [F1] Adicionar CP-07 e CP-08 a `docs/business-rules/clausulas-petreas.md`.
7. [F1] Escopar `.gitignore` (`/.claude/` em vez de bare `CLAUDE.md`/`AGENTS.md`) **ou** documentar local-only.
8. [F2] Deprecar/reescrever `docs/guides/etl.md` e `docs/guides/rbac.md`.
9. [F2] Corrigir árvore de apps (remover `dat_ingest`) em `overview.md`/`backend.md`/INDEX; deploy em `infrastructure.md`.
10. [F2] Sincronizar 13 setores / 5 funções em INDEX/MAPEAMENTO.
11. [F4] **Criar `deslocamento.spec.md`** e **`hooks-rbac.spec.md`** (gaps).
12. [F6] Job CI de links quebrados + lint de frontmatter.

## 9. Riscos

- **Docs locais não existem em outras máquinas** (`.claude/`, `.agents/`): qualquer plano que dependa deles quebra num
  clone limpo. Mitigação: Fase 1 leva os contratos para o git.
- **Mover arquivos quebra links** (MkDocs nav, links relativos): mitigação — mover + corrigir no mesmo commit; gate de links na Fase 6.
- **Drift de contagens** (setores/funções/endpoints) reaparece se transcrito à mão: mitigação — gerar do código.
- **Sobre-engenharia**: SDD com fricção demais para um dev solo. Mitigação — frontmatter mínimo (3 campos) e specs só para
  módulos vivos, não para histórico.
- **MkDocs nav** (`mkdocs.yml`) precisa acompanhar moves para não publicar links mortos.

## 10. Critérios de conclusão

- [ ] Todo módulo backend/frontend/infra **vivo** tem uma `*.spec.md` com `status` + `last_verified` + `sources_of_truth`.
- [ ] **0** docs `stale` em posição canonical/active (os 21 atuais reconciliados ou arquivados).
- [ ] **0** links relativos quebrados em docs canonical/active (e gate de CI impedindo regressão).
- [ ] **CP-01..CP-08** definidos no SSOT versionado (`clausulas-petreas.md`).
- [ ] Contagens (setores/funções) **geradas** do código, não transcritas.
- [ ] Histórico (`analysis/`/`_archive/`/planos concluídos) isolado da navegação viva e sinalizado.
- [ ] `CLAUDE.md`/`AGENTS.md`: decisão explícita (versionar ou local-only documentado).

---

_Plano derivado da auditoria de 2026-06-19. Execução por fases, 1 PR por fase (CP-06), sem mover arquivos fora de um commit que também corrige os links afetados._
