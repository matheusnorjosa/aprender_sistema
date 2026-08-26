---
title: Monólito modular para maintainer solo
status: draft
last_verified: 2026-08-26
owner: docs
related:
  - ../../docs/architecture/project-decisions/ADR-018-pull-based-deploy.md
  - ../audits/ACHADOS_REAIS.md
  - ../specs/backend/rbac.spec.md
  - ../specs/backend/imports.spec.md
  - ../specs/infra/deploy.spec.md
  - ../../../CLAUDE.md
---

# Plan: Monólito modular (sem fatiar Django)

## TL;DR

Não extrair `apps.*` novos. Tratar `apps.core` como monólito modular (fronteiras de import + writers únicos), alinhar o tooling Claude/Cursor ao D2 do graphify, e nesta janela: promover a `main` de forma consciente, fechar residual ator×alvo em participantes/grade, e fazer o import passar pelos mesmos services da API. Microserviço e segundo `INSTALLED_APPS` ficam congelados até existir dono, release ou carga distintos.

## Decisions

| # | Decisão | Escolha |
|---|---|---|
| D1 | Fatiar em apps Django (`apps.dat`, `apps.solicitacao`, …) | **Não nesta série.** Custo de migration/`AUTH_USER_MODEL`/imports cruzados sem ganho de escala (1 maintainer, 1 compose, 148 usuários). |
| D2 | Microserviços / APIs internas | **Fora.** Já há SPA + Django + Celery; isso basta. |
| D3 | Quando extrair um segundo app | Só se um domínio tiver **ciclo de release, dono ou carga** diferentes. Candidatos tardios (não agendados): notificações 32 Passos, GCal — e ainda assim *app Django no mesmo compose*. |
| D4 | Promoção a produção | **Ato humano** (`promote.yml` + Environment `production`). Este plano descreve o checklist; não dispara o workflow. |
| D5 | Graphify | Ferramenta **sob demanda** (raiz `CLAUDE.md` D2). Hook não pode falhar fechado nem obrigar grafo canônico. |
| D6 | Policy ator×alvo em participantes | Alvo arbitrário ativo ainda vira `FORMADOR`/`COORD_ACOMPANHA` (`views_solicitacao.py` `_create_participants`). Fechar o residual de `M10-04` / épico **#1656** / **#1666**. Regra de negócio (quem pode apontar quem) precisa de uma linha explícita no PR — default proposto: só usuários com papel Formador/Coordenador **vigente** na gerência do `projeto` da solicitação; guests por e-mail continuam, mas não viram papel interno. |
| D7 | `HasSectorAccess` sem `gerencia_id` | Residual `M14-01`: qualquer vínculo `EquipeGerencia` vigente libera a grade (`permissions.py` ~300–310). Default proposto: exigir `papel` em `{FORMADOR, COORDENADOR, APOIO, GERENTE}` **ou** capability já composta (`CanViewAllAvailability`). Confirmar no PR se DAT sem esses papéis deve ver grade. |
| D8 | Import vs invariantes | Épico **#1659** não cabe numa PR. Onda 4 = **um** writer (primeiro: `Compra`/`DATCompra` ou o import que o autor mais usa) roteado pelo mesmo service/serializer da API. Demais entidades = issues filhas. |
| D9 | DR drill (#1662) | **Fora deste plano** (não estava nos 4 pontos). Não misturar. |

Delegado (“discricionário do implementador”): nomes de teste, tamanho exato do grafo de imports permitidos na Onda 2, desde que o teste seja determinístico e sem falso-positivo na `main` atual.

## Phases (Wave-based)

Cada onda cabe num contexto fresco. Não começar a Onda N+1 com a Onda N vermelha.

### Onda 0 — Congelar o anti-objetivo (docs, 1 PR)

Objetivo: ninguém “aproveita” a série para criar `apps.foo`.

- [ ] **0.1** Parágrafo curto em `v2/docs/specs/backend/README.md` (ou ADR one-pager se preferir não tocar README de specs): *AS v2 é monólito modular em `apps.core`; segundo app Django só com D3.* Apontar este plano.
- [ ] **0.2** Critério D3 em 5 linhas (release / dono / carga). Sem código.

**Verificação:** `python v2/backend/scripts/check_doc_links.py` (ou o job docs-quality) no que mudou. Zero `INSTALLED_APPS` novos.

### Onda 1 — Operar o que já existe (paralelo: humano + tooling)

#### 1.A Promoção (humano; sem código)

Último snapshot de prod confirmado na auditoria: `v2026.07.18-94f2765`. A `main` recente já tem tag de build (ex. `v2026.08.26-77e80f3` no corte desta análise — **reler a tag atual** no momento de promover).

- [ ] **1.A.1** Diff mental: o que entrou desde 20/07 (RBAC, restore `.age`, gates). Migrations sobem sozinhas e são **bloqueantes** (serviço `migrate` no compose). Forward-only.
- [ ] **1.A.2** Confirmar tag no GitHub Releases e imagens `norjosamatheus/aprender-*`.
- [ ] **1.A.3** `gh workflow run promote.yml -f release=<tag>` atrás do Environment `production`.
- [ ] **1.A.4** VM01: deployer/applier; `GET /api/readyz/` e `/api/version/` em localhost. Anotar SHA em prod. **Não** PUT no Portainer na mão.

Se a promoção for grande demais para um sábado: promover mesmo assim um SHA conhecido, ou **não** misturar Onda 3/4 no mesmo dia do promote (regressão + migrate no mesmo empurrão).

**Verificação:** `/api/version/` = tag promovida; login; criar solicitação NAO_SUPER; mapa mensal.

#### 1.B Graphify / hooks / AGENTS (PR pequena, não-runtime)

Causa do bloqueio no Cursor: `.claude/hooks/graphify-reminder.ps1` **não imprime JSON** quando o comando não é grep/rg (stdout vazio → “invalid JSON” → ferramenta bloqueada). Isso contradiz `CLAUDE.md` D2. `AGENTS.md` ainda manda ler `GRAPH_REPORT.md` em toda pergunta de arquitetura.

- [ ] **1.B.1** `graphify-reminder.ps1`: **sempre** stdout JSON válido e `exit 0`. Se for grep **e** existir `graphify-out/graph.json`, `additionalContext` opcional (“grafo existe; use se quiser”). Nunca fail-closed. Nunca exigir leitura do grafo.
- [ ] **1.B.2** Teste em `.claude/hooks/test_hooks.py` (ou bats): stdin vazio, stdin comando `ls`, stdin `rg foo` com e sem `graphify-out/graph.json` — os quatro devolvem JSON parseável.
- [ ] **1.B.3** `AGENTS.md` seção graphify: espelhar D2 da raiz (`CLAUDE.md`). Grafo = exploração; specs = verdade.
- [ ] **1.B.4** Avaliar `graphify-sync.ps1` no Stop: manter best-effort `exit 0` se o binário existir; não falhar a sessão.

**Verificação:** no Cursor, um `ls` no terminal do agente não é bloqueado pelo hook. `python .claude/hooks/test_hooks.py` (caminho real do teste) verde.

Staging-gate: docs + `.claude/` + `AGENTS.md` = não-runtime; pular `make staging-full` se o gate do projeto assim definir.

### Onda 2 — Fronteiras dentro de `apps.core` (teste, sem split)

Objetivo: o monólito ganha **portas**, não pastas Django novas.

Hoje `apps/core/tests/test_architecture_boundaries.py` só prova que `apps.dat_ingest` morreu.

- [ ] **2.1** Inventariar pacotes lógicos já existentes (não criar): `rbac/`, `services/solicitacao_*`, `services/availability*`, `services/gcal/`, `imports/` + `services/*_import.py`, `models/` por arquivo de domínio.
- [ ] **2.2** Regra mecânica v1 (uma só, para não inventar um linter de sonhos):
  - **Writers de persistência de domínio** (ViewSet `perform_create`/`update`, commands `import_*`, `views_import_*`) não podem `Model.objects.create/update` em entidades que já têm service canônico — lista explícita no teste (começar com `Solicitacao` + `Participation`; expandir na Onda 4).
  - Allowlist de arquivos (ex. migrations, factories, seeds `dev_tools`).
- [ ] **2.3** Estender `test_architecture_boundaries.py` (AST ou grep de call-sites) para essa allowlist. **Calibrar na `main` atual:** se já está vermelho, a Onda 2 **só lista** os ofensores e abre issues; **não** promove o teste a `[required]` até a Onda 3/4 limpar. Skill `gate-calibration`: precisão alta, limpar antes de trancar.

**Verificação:** `docker exec aprender_dev-web-1 pytest apps/core/tests/test_architecture_boundaries.py -v` (ou equivalente). Se o teste for advisory, documentar no `ci.spec.md` como `[info]` até limpar.

### Onda 3 — Ator × alvo (código + testes)

Depende de D6/D7 confirmados. Issues: **#1656**, **#1666**, residual `M10-04`, `M14-01`.

- [ ] **3.1 Participantes** — `SolicitacaoViewSet._create_participants` (`views_solicitacao.py` ~351+). Depois do filtro `is_active=True`, recusar id cujo usuário **não** tenha papel ocupante na gerência do `solicitacao.projeto` (EquipeGerencia vigente). 400 com código estável (`invalid_participant` / similar). Não aceitar “qualquer ativo”.
- [ ] **3.2 Update** — o commit de `M10-04` deixou reconciliação de participantes no PATCH **fora**. Se o update ainda substitui listas sem a mesma policy, aplicar o mesmo helper (um service, dois call-sites: create e update).
- [ ] **3.3 Testes** — RED primeiro em `test_extra_participants_validation_1626.py` (ou irmão `*_1656.py`): coordenador DAT (ou perfil sem vínculo) tenta meter um Formador de outra gerência → 400; formador da mesma gerência → 201. Convidar e-mail guest → permitido (D6).
- [ ] **3.4 Grade** — `HasSectorAccess.has_permission` (`rbac/permissions.py` ~280–332): no ramo `gerencia_id is None`, filtrar `papel__in=...` (D7) além de `vigentes_em()`. Testes em `test_availability_monthly_rbac.py`.
- [ ] **3.5 Docs** — uma linha em `rbac.spec.md` Divergências: `M10-04`/`M14-01` status. Não reabrir P0 de auto-escalação (#1610).

**Verificação:**

```text
docker exec aprender_dev-web-1 pytest apps/core/tests/test_extra_participants_validation_1626.py apps/core/tests/test_availability_monthly_rbac.py apps/core/tests/test_solicitacao_gerencia_scope_1623.py -v --no-migrations
cd v2/backend && pyright apps/core/views_solicitacao.py apps/core/rbac/permissions.py
```

PR de runtime → `make staging-full` 8/8 + marcadores do staging-gate.

### Onda 4 — Import pelo mesmo writer (fatia)

Épico **#1659**. Não “consertar todos os imports”.

- [ ] **4.1** Escolher **uma** entidade (sugerido: a que o autor for usar no próximo `--apply`; senão `DATCompra`/`Compra` pelos invariantes já testados em `test_dat_compra_invariantes.py`).
- [ ] **4.2** O caminho `views_import_*` / `export_contract_importer` dessa entidade chama o **mesmo** service/serializer que o CRUD (dry-run continua fail-closed via `parse_dry_run`).
- [ ] **4.3** Teste: linha que o CRUD rejeitaria (quantidade ≤0, etc.) o import em `--apply` também rejeita; dry-run classifica sem persistir.
- [ ] **4.4** Atualizar allowlist da Onda 2 para essa entidade; se o teste de fronteira ficou limpo, considerar promovê-lo a required no agregador **só desta regra** (gate-calibration de novo).

**Verificação:** pytest dos testes de import da entidade + `test_architecture_boundaries.py`. `--apply` real em dados de produção **continua proibido** até dry-run verde + autorização (RF01).

### Onda 5 — Explicitamente não fazer (registro)

- [ ] **5.1** Não criar `apps.dat` / `apps.gcal` / `apps.notificacoes`.
- [ ] **5.2** Revisitar D3 só se aparecer segundo maintainer, ou um serviço com SLO de carga isolado (improvável neste hardware).

## Relevant Code

- `v2/backend/config/settings.py` — `INSTALLED_APPS` = `apps.core` (+ `dev_tools` condicional). Não expandir.
- `v2/backend/apps/core/tests/test_architecture_boundaries.py` — hoje só `dat_ingest` ausente; alvo da Onda 2.
- `v2/backend/apps/core/views_solicitacao.py` — `_ExtraParticipantsSerializer` (shape, `M10-04`); `_create_participants` (policy ausente, ~351).
- `v2/backend/apps/core/rbac/permissions.py` — `HasSectorAccess` (~280–332), residual `M14-01`.
- `v2/backend/apps/core/services/solicitacao_availability.py` — `enforce_solicitacao_availability` (já no create/update/approve; import ainda pode desviar).
- `v2/backend/apps/core/imports/request_params.py` — `parse_dry_run` fail-closed.
- `.claude/hooks/graphify-reminder.ps1` — stdout vazio fora de grep.
- `.claude/settings.json` — PreToolUse Bash → graphify-reminder.
- `CLAUDE.md` (raiz) D2 vs `AGENTS.md` seção graphify (contraditório).
- `.github/workflows/promote.yml` — promoção.
- `v2/docs/audits/ACHADOS_REAIS.md` — `M10-04`, `M14-01`, #1656, #1659, #1666.
- `v2/docs/specs/backend/imports.spec.md` — RF01 never-overwrite / allowlist `--apply`.

## Verification (série inteira)

| Onda | Prova |
|---|---|
| 0 | Nenhum app novo; texto D1–D3 visível |
| 1.A | `/api/version/` em prod = tag promovida |
| 1.B | Hook JSON sempre; `ls` não bloqueia |
| 2 | Teste de fronteira verde **ou** advisory com lista de ofensores |
| 3 | pytest listados + staging-full se runtime |
| 4 | Import da fatia respeita invariante do CRUD |
| 5 | `INSTALLED_APPS` inalterado |

## Scope Boundaries

**IN**

- Congelar “não fatiar Django”.
- Promoção humana documentada + executada por você.
- Hook graphify + `AGENTS.md` alinhados a D2.
- Teste de fronteira (writers) em `apps.core`.
- Policy ator×alvo em participantes + ajuste `HasSectorAccess`.
- Uma fatia de import pelo writer da API.

**OUT**

- Novo `INSTALLED_APPS` de domínio.
- Microserviços, filas extras, “plataforma de módulos”.
- Drill de DR / `.age` ponta a ponta (#1662).
- `--apply` em massa no banco de produção.
- Fechar os 23 épicos abertos no GitHub.
- Reescrever histórico do `abiatarprado`.
- Redesign do frontend dual RBAC (legacy flags) — outro plano.

## Ordem sugerida no calendário (solo)

1. **Meio dia:** Onda 1.B (hook) — desbloqueia o agente no Windows.
2. **Quando couber risco de prod:** Onda 1.A (promote), sozinha.
3. **1–2 PRs:** Onda 0 + Onda 2 (docs + teste advisory).
4. **PR de produto:** Onda 3 (RBAC/participantes).
5. **PR de produto:** Onda 4 (um import).

Não empilhar 3+4+promote no mesmo dia.

## Riscos

- Promover a distância julho→agosto: migrate bloqueante; ter rollback via `promote.yml` `rollback: true` na tag anterior (sequence ainda sobe).
- D6/D7 errados quebram fluxo real (convidar formador de outro município/gerência que o negócio permite). Validar com um caso real antes de trancar o teste.
- Teste de fronteira Onda 2 amplo demais → CI vermelha eterna. Começar advisory.
- Hook: se o Cursor exigir um schema diferente do Claude Code, o JSON “sempre válido” precisa ser testado **neste** IDE, não só no `test_hooks.py`.
