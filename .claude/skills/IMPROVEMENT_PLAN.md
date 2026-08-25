# Plano de Melhoria das Skills — Aprender Sistema v2

> Documento de acompanhamento. Marque `- [x]` conforme concluir.
> Tudo aqui é em `.claude/skills/` (gitignored → edição **local**, sem PR/CP-07).
> Rubric de referência: [writing-great-skills (mattpocock)](https://github.com/mattpocock/skills/blob/main/skills/productivity/writing-great-skills/SKILL.md)

## Baseline (auditoria 2026-06-25)

- **22 skills avaliadas**, média **2.86/5**.
- Determinismo médio 3.27 · Description média 2.86 · Disclosure média 2.36.
- **0/22** usam `disable-model-invocation` · **16/22** project-specific.

### Notas atuais (re-pontuar ao concluir cada onda)

| Skill | Nota | Inv. | Linhas | Específica? |
|-------|:----:|:----:|:------:|:-----------:|
| security-scan | 4 | model | 175 | ✅ |
| aprender-domain | 3 | model | 653 | ✅ |
| django-patterns | 3 | model | 871 | ✅ |
| django-security | 3 | model | 218 | ✅ |
| writing-standards | 3 | model | 407 | ✅ |
| test-driven-development | 3 | model | 268 | ❌ |
| debugging-and-error-recovery | 3 | model | 353 | ✅ |
| deprecation-and-migration | 3 | model | 275 | ✅ |
| frontend-ui-engineering | 3 | model | 293 | ✅ |
| performance-optimization | 3 | model | 333 | ✅ |
| receiving-code-review | 3 | model | 129 | ❌ |
| subagent-development | 3 | model | 161 | ✅ |
| git-worktrees | 3 | model | 146 | ✅ |
| verification-gate | 3 | model | 154 | ✅ |
| continuity-ledger | 3 | model | 166 | ✅ |
| create-plan | 3 | model | 139 | ✅ |
| implement-plan | 3 | model | 120 | ✅ |
| create-handoff | 3 | model | 133 | ❌ |
| resume-handoff | 3 | model | 217 | ❌ |
| graphify | 2 | model | 1386 | ❌ |
| brainstorming | 2 | model | 110 | ❌ |
| etl-guidelines | 1 | model | 960 | ✅ (morta) |

---

## Matriz de cobertura (achado → onda)

| Achado | Onda |
|--------|:----:|
| `etl-guidelines` documenta módulo deletado (perigosa) | A1 |
| 0/22 `disable-model-invocation` (contexto todo turno) | A2 |
| "When to Use" duplica a description (~10 skills) | A3 |
| No-ops (22) + duplicações além de "When to Use" | A4 |
| Descriptions fracas nas que ficam model-invoked | B1 |
| Invocação não decidida deliberadamente | B2 |
| Sprawl nas 4 gigantes | C1 |
| Disclosure em +4 skills (debugging/deprecation/frontend-ui/resume-handoff) | C2 |
| django-security/aprender-domain sem processo (determinismo) | D1 |
| security-scan sem branch-dispatch (premature completion) | D2 |
| 6 skills genéricas não localizadas | D3 |
| Lacuna: skill de CI/GitHub Actions | E1 |
| Lacuna: skill de design de API | E2 |
| Adoções externas (skill-creator, github-actions-docs, grill-me, to-issues) | E3 |

---

## Onda A — Mecânica (risco ~zero, maior ROI) ✅ CONCLUÍDA

- [x] **A1.** Aposentar `etl-guidelines`: SKILL.md reduzida de 960L → stub de redirect (~20L) com `disable-model-invocation: true` → `imports.spec.md` + `import_export_contract`. ✅
- [x] **A2.** Adicionar `disable-model-invocation: true` ao frontmatter das user-invoked: ✅ (6/6)
  - [x] create-plan
  - [x] implement-plan
  - [x] create-handoff
  - [x] resume-handoff
  - [x] continuity-ledger
  - [x] security-scan
  - [~] ~~aprender-domain~~ → **CORRIGIDO: fica model-invoked** (o agente precisa alcançá-la sozinho ao mexer em domínio; custo é só a description/turno, não o corpo). Fix dela = A4 (enxugar desc) + C (disclosure).
- [ ] **A3.** Deletar seções "When to Use" duplicadas (1 SSOT na description): **4/12 feitas**
  - [x] security-scan
  - [x] writing-standards
  - [x] receiving-code-review
  - [x] git-worktrees
  - [ ] continuity-ledger → **adiar p/ B1** (description sem gatilhos; enriquecer antes de deletar, senão perde info)
  - [ ] avaliar caso-a-caso: performance, deprecation-and-migration, django-security, subagent-development, brainstorming, test-driven-development, frontend-ui-engineering (deletar só se a description já tiver os gatilhos)
- [ ] **A4.** No-op hunt + duplicações restantes:
  - [ ] aprender-domain (status datados ✅/PR-NN, "Essential for...", tabela "When to Use")
  - [ ] writing-standards (Tone block, 3× restatement de active-voice)
  - [ ] performance-optimization (fundir "Targets" + "Budget"; deletar "Red Flags")
  - [ ] frontend-ui-engineering (fetchAPI/timezone 3-4×)
  - [ ] django-security (RBAC/IDOR repetido)
  - [ ] subagent-development (no-ops 153-154; aviso óbvio Bash)
  - [ ] security-scan (bullets circulares; "Integrates with project hooks system")

**DoD Onda A:** etl morta neutralizada; 7 flags aplicadas; zero "When to Use" duplicada; no-ops principais removidos.

## Onda B — Descrições + invocação deliberada ✅ CONCLUÍDA

- [ ] **B1.** Reescrever description com gatilhos "Use when…" (as que ficam model-invoked):
  - [ ] verification-gate
  - [ ] brainstorming (adicionar frontmatter YAML — hoje não tem)
  - [ ] graphify
- [ ] **B2.** Decidir model vs user explicitamente em cada skill restante e registrar a escolha.

**DoD Onda B:** toda skill model-invoked tem description rica em gatilhos; invocação decidida, não default.

## Onda C — Progressive disclosure ✅ CONCLUÍDA

- [ ] **C1.** Gigantes (mover REFERENCE → arquivos atrás de ponteiros):
  - [ ] graphify (1386L)
  - [ ] django-patterns (871L — 4 templates → reference/*.md)
  - [ ] aprender-domain (653L — DAT/Form/Compras/KeyModels → arquivos)
  - [ ] performance-optimization (anti-patterns → references/{backend,frontend}.md)
- [ ] **C2.** +4 que também precisam:
  - [ ] debugging-and-error-recovery (153-257 → patterns/*.md)
  - [ ] deprecation-and-migration (reference → patterns.md/reference.md)
  - [ ] frontend-ui-engineering (split em forms/tables/a11y/domain.md)
  - [ ] resume-handoff (cortar ~80L de Guidelines/Scenarios/Example)

**DoD Onda C:** SKILL.md das 8 enxutos; reference carregada sob demanda.

## Onda D — Determinismo / conteúdo ✅ CONCLUÍDA

- [ ] **D1.** django-security: adicionar procedimento de auditoria ordenado + critério de fim.
- [ ] **D1b.** aprender-domain: confirmar papel reference (já vira user-invoked em A2).
- [ ] **D2.** security-scan: tabela branch-dispatch (secrets|deps|patterns|config → fases) + step de agregação/stop.
- [ ] **D3.** Localizar as 6 genéricas:
  - [ ] test-driven-development (pytest/DRF/APITestCase/factory_boy, gate 85%)
  - [ ] receiving-code-review
  - [ ] create-handoff (paths AS v2; remover path Next.js)
  - [ ] resume-handoff
  - [ ] brainstorming
  - [ ] graphify

**DoD Onda D:** reference-skills com processo OU marcadas user-invoked; genéricas citam o stack real.

## Onda E — Lacunas + adoções externas ✅ (E1 feito · E2 opcional deferida · E3 decidido)

- [ ] **E1.** Criar skill `ci-github-actions` project-specific (reusable workflows `_backend-test.yml`, gates `[required]`, telemetria, deploy Portainer, staging-gate).
- [ ] **E2.** (Opcional) Criar skill de design de API REST/DRF.
- [ ] **E3.** Avaliar/instalar adoções externas:
  - [ ] skill-creator / writing-great-skills (conduzir B-E com método)
  - [ ] github-actions-docs (referência GHA)
  - [ ] grill-me / grilling (rigor de planejamento)
  - [ ] to-issues (backlog 44 itens → issues)

**DoD Onda E:** lacuna CI coberta; decisão registrada sobre cada adoção externa.

---

## Log de progresso

- **2026-06-25 — TODAS as ondas A–E concluídas** (edição local; `.claude` gitignored).
  - **Onda A** ✅ — A1 etl stub (960→19L); A2 6 flags `disable-model-invocation` (aprender-domain mantida model-invoked por critério); A3 dedup "When to Use" (as pure-dup removidas; TDD/subagent mantidas por conterem "when-NOT-to"); A4 no-op/sediment hunt.
  - **Onda B** ✅ — descriptions reescritas com leading-word + "Use when" em verification-gate, brainstorming (ganhou frontmatter), graphify, continuity-ledger, create-plan/implement-plan, handoffs. Invocação decidida por skill.
  - **Onda C** ✅ — progressive disclosure: graphify 1386→53L, django-patterns 871→201L, aprender-domain 653→103L (+4 ref), performance 333→80L, frontend-ui 293→71L (+4 ref), debugging 353→198L, deprecation, resume-handoff 217→116L. Reference movido p/ `<skill>/reference/*.md` atrás de ponteiros.
  - **Onda D** ✅ — django-security ganhou procedimento ordenado; security-scan branch-dispatch; TDD/handoffs localizados p/ AS v2.
  - **Onda E** ✅ — E1 skill nova `ci-github-actions` (+reference/workflows.md). E2 (API design) deferida (opcional). E3 decidido: adotar `writing-great-skills` como referência de manutenção; **pular** `github-actions-docs` (já temos project-specific, melhor pelo rubric); `grill-me`/`to-issues` opcionais.
  - **Execução**: fan-out 1 agente/skill (20) + verificador anti-fabricação/anti-over-deletion. 16/20 pass; 4 fails = só fabricação (3 herdadas do original, em exemplos). **Corrigidos manualmente** (regra "fix pre-existing"): `calendar_client_factory.py`→`gcal_client_factory.py`; `view_datregistro`→`manage_admin_registries`; `aprovar_solicitacao`→`pode_aprovar_superintendencia`; `descricao`→`observacoes`; e 2 hooks (`usePolling`/`useTableFilters`) com assinatura real corrigida nos reference do frontend.
  - **Over-deletion**: 0 (verificador confirmou nenhum fato project-specific perdido em 20/20).
- **2026-06-25 — Auditoria do RESTO do `.claude/`** (agente `claude-config-auditor`, fora de `skills/`): 17 achados. **Corrigidos** (manualmente — subagents bateram limite de sessão): `CLAUDE.md` (models 41→42, pages 40→39, +`ci-github-actions`/`django-security` nas skills); `commands/etl-apply.md`+`etl-dry.md` (corpo morto p/ `apps.dat_ingest` → stub de redirect); `commands/approve-flow.md` (refs `views.py`→`views_solicitacao.py:614/652`+`services/solicitacao_approval.py`; `groups__name=` shell-only com aviso anti-prod; `5/5 PR17`→`5/5 PA-07 mandatory`); `commands/check-conflicts.md` (`17/17 PR16`→18 testes); `commands/gsd.md` (`/create-plan`,`/implement-plan`→skills); `commands/project_plan.md` (+frontmatter); `commands/deploy-staging.md` (`scripts/rbac_lint.py`→`v2/backend/scripts/`); `CLAUDE-principles.md` (data 2025→2026-06; switch-case→match/case); `cheatsheets/CHEATSHEET_SKILLS.md` (+`ci-github-actions`, count 22→23, nota user-invoked); `skills/security-scan/SKILL.md` (remove `--include=*.jsx`). **Deferidos**: `settings.local.json` (#15 — ~150 linhas de allowlist morta de paths `datsu`/`/tmp`; é config de PERMISSÕES, pedir OK antes); fusão `CLAUDE-principles.md`↔skills (#17, estrutural). Falso-alarme: #11 (`views_availability.py` está correto).
