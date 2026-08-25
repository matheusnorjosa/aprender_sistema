---
description: Pre-flight do release (gate local staging-full) + promoção humana para produção via promote.yml (ADR-018)
argument-hint: [optional: deployment type - 'full' or 'hotfix']
---

# Deploy — Pre-Flight Checklist

Deployment type: ${ARGUMENTS:-full}

## 🎯 Overview

**There is NO dedicated staging environment** in AS v2, e **merge na `main` NÃO deploya**.
O fluxo tem dois atos deliberados:

1. **Validar localmente** com `make staging-full` (stack prod-like) — precisa fechar **8/8 PASS**.
2. **Merge (squash) na `main`** → dispara `deploy.yaml` (*"Build, sign and release"*): build → scan →
   push no Docker Hub → **assina** (cosign keyless + provenance SLSA) → cria a tag imutável
   `vYYYY.MM.DD-<sha7>` + GitHub Release. **Produção não muda aqui.**
3. **Promover** a tag: `promote.yml` (`workflow_dispatch`), atrás do GitHub Environment `production`
   com *required reviewer*. A VM01 **puxa** o ponteiro assinado e aplica **por digest**.
4. **Verificar** `/api/version/` + `/api/readyz/` depois que a VM01 aplicar (~60s de timer).

"Staging" aqui significa o **gate local prod-like**, não um servidor remoto.
**NUNCA pule o gate local** — ele é a única validação pré-produção que existe.

> [!warning] Procedimento revogado — não volte a ele
> Até o **ADR-018 (2026-07-10)** este comando ensinava: *"merge na `main` → deploy automático em
> produção via Portainer"*, com rollback por *redeploy da tag anterior no Portainer*. Era o
> **ADR-010**. Ele foi **superseded**: os jobs `deploy` e `validate_existing_tag` do `deploy.yaml`
> foram **deletados** no **#1516**, e a `:9443` deixou de ser pública (o `PUT` legítimo é do
> `aprender-applier`, em `127.0.0.1:9443`). Quem seguir o texto antigo vai procurar um deploy que
> não acontece, ou tentar mexer no Portainer à mão — que é exatamente o que o modelo novo remove.
> Registro: `docs/architecture/project-decisions/ADR-018-pull-based-deploy.md`.

---

## 📋 Pre-Deployment Checklist

### Phase 1: Code Quality (Local, Docker — CP-01)

- [ ] **All backend tests passing** (Docker-only)
  ```bash
  docker exec aprender_dev-web-1 pytest apps/core/tests/ -v
  # Expected: All tests GREEN
  ```

- [ ] **Coverage threshold met** (gate = 85%)
  ```bash
  docker exec aprender_dev-web-1 pytest --cov=apps --cov-fail-under=85
  # Expected: Coverage >= 85%
  ```

- [ ] **Type check clean** (Pyright strict)
  ```bash
  cd v2/backend && pyright apps/core config
  # Expected: 0 errors
  ```

- [ ] **Linting clean** (flake8, black, isort)
  ```bash
  docker exec aprender_dev-web-1 flake8 apps/
  docker exec aprender_dev-web-1 black --check apps/
  docker exec aprender_dev-web-1 isort --check apps/
  # Expected: No errors
  ```

- [ ] **Migrations valid**
  ```bash
  docker exec aprender_dev-web-1 python manage.py makemigrations --check
  docker exec aprender_dev-web-1 python manage.py check
  # Expected: No issues detected
  ```
  > Em produção as migrations rodam **sozinhas e bloqueantes** (serviço one-shot `migrate`, #1456):
  > `web`/`worker`/`beat` só sobem com `depends_on: service_completed_successfully`. Uma migration
  > quebrada **trava o deploy** em vez de servir schema meio-migrado — por isso validar aqui é o
  > que impede a promoção de morrer no meio.

- [ ] **RBAC lint clean** (bans user.groups.filter(name=...))
  ```bash
  python v2/backend/scripts/rbac_lint.py
  # Expected: No violations (CI job: [required] backend rbac-lint)
  ```

### Phase 2: Local Staging-Full Gate (the real "staging")

- [ ] **Run the full prod-like validation** — must end **8/8 PASS**
  ```bash
  make staging-full
  # Expected: ALL 8 CHECKS PASSED
  ```
  > On GnuWin32/Windows, `$(MAKE)` recursion can break — run the staging-precheck/build/up/test/down
  > steps individually if `make staging-full` fails on the make-recursion (not on a real check).

- [ ] **Attach evidence + staging-gate markers to the PR body** (exact literals, no accents)
  - `make staging-full ... (8/8 PASS)`
  - `Evidencia anexada no PR`
  - `ALL 8 CHECKS PASSED`
  > The staging gate matches these literal strings (regex `Evidencia` — no accent). A `Evidência`
  > body fails the gate; fix via `gh pr edit --body`. Draft PRs skip the gate.

### Phase 3: Version Control & PR

- [ ] **Branch up-to-date with main**
  ```bash
  git fetch origin main
  gh pr update-branch   # if base moved; re-trigger required checks
  # Expected: branch in sync, CI re-runs
  ```

- [ ] **No uncommitted changes**
  ```bash
  git status
  # Expected: "nothing to commit, working tree clean"
  ```

- [ ] **PR green and ready**
  - All conversations resolved
  - At least 1 approval
  - All `[required]` checks passing (GitHub Actions)
  - Staging-gate markers present in body (Phase 2)
  - Conventional commit title (CP-06): `type(scope): message`

### Phase 4: Merge → Release (NÃO é deploy)

- [ ] **Squash-merge the PR into `main`**
  ```bash
  gh pr merge <PR> --squash
  # Merge dispara build/scan/push + cosign + SLSA + tag imutavel. Producao NAO muda.
  ```

- [ ] **Acompanhar o build/assinatura**
  ```bash
  gh run watch          # ou: gh run list --workflow=deploy.yaml --limit 1
  # O run precisa terminar verde nos jobs: prepare, build_and_push, sign, tag_and_release.
  ```
  > `blob unknown to registry` no `buildx --push` é **flake transitório** do Docker Hub:
  > `gh run rerun <id> --failed`. Produção intacta — ela nem foi tocada.

- [ ] **Anotar a tag imutável gerada**
  ```bash
  gh release list --limit 3
  # Formato: vYYYY.MM.DD-<sha7>. E essa string que a promocao recebe.
  ```

### Phase 5: Promoção para produção (ato humano, gated)

- [ ] **Confirmar que as imagens estão assinadas** — o `promote.yml` **exige** isso e falha se não
      estiverem (`slsa-provenance.yml`). Não há como promover um artefato não assinado.

- [ ] **Disparar a promoção**
  ```bash
  gh workflow run promote.yml -f release=v2026.MM.DD-<sha7>
  ```

- [ ] **Aprovar no gate** — o job pausa no GitHub Environment `production` esperando o
      *required reviewer*. Sem a aprovação, nada sai do lugar.

- [ ] **Confirmar o ponteiro publicado**
  ```bash
  gh run list --workflow=promote.yml --limit 1
  # O workflow resolve tag->digest, monta e assina o production.json (sequence monotonica,
  # expires_at) e publica no branch protegido `deploy-pointer`. Ele TAMBEM nao deploya.
  ```

- [ ] **Esperar a VM01 puxar** (~60s, systemd timer). `aprender-deployer` lê o ponteiro *tokenless*,
      verifica a assinatura contra trusted-root pinado offline e os digests das imagens; entrega ao
      `aprender-applier`, que confere anti-rollback (selo monotônico), drift do compose, exige
      **backup de DB fresco**, faz o `PUT` em `127.0.0.1:9443` e confirma em `localhost`.
      Cada degrau é **fail-closed** — um `REFUSE` significa que produção **não** mudou.

### Phase 6: Post-Promotion Validation

- [ ] **Version/health check**
  ```bash
  curl -s https://<prod-host>/api/version/   # {"version": "<release>"} -- casa com production.json?
  curl -s https://<prod-host>/api/readyz/    # 200
  ```
  > A verdade do que roda em produção é o **digest verificado no `PUT`**, não a cor de um job de CI.
  > **Mas o `/api/version/` não devolve digest**: o payload é `{"version": ...}`, com `git_sha` e
  > `build_date` só para `is_staff` (`v2/backend/apps/core/views_health.py:93-99`). Daqui a
  > evidência possível é a **tag** — compare com o `release` do `production.json`. O digest fica no
  > selo que o applier grava dentro da VM.
  > O applier já confirmou de **dentro** da VM (`/api/readyz/` + `/api/version/` em `localhost`),
  > o que torna a confirmação imune ao *false-red* do `:9443`. Se o probe **externo** der HTTP 000
  > (Kaspersky/KESL nas Golden VMs), isso não indica deploy quebrado — confira o selo do applier /
  > o `/api/version/` interno em vez de concluir pela borda.

- [ ] **Spot-check a critical endpoint** (with auth)
  - Frontend loads (homepage renders)
  - Login works → redirects to dashboard
  - `/api/solicitacoes/` returns data

### Phase 7: Rollback Plan (If Needed)

**Rollback é uma promoção PARA TRÁS, pelo mesmo gate.** Não existe mais "redeploy da tag anterior
no Portainer", nem `gh workflow run deploy.yaml -f rollback_tag=...`.

- [ ] **Promover a tag imutável anterior**
  ```bash
  gh workflow run promote.yml -f release=v2026.MM.DD-<sha7-anterior> -f rollback=true
  # `rollback: true` marca o downgrade como intencional e assinado.
  # Ainda exige `sequence` maior que o selo -- o anti-rollback nao e desligado.
  ```
- [ ] **Aprovar no Environment `production`** (mesmo required reviewer).
- [ ] **Se uma migration quebrou prod**: **não há auto-rollback** — migrations são *forward-only*.
      Restaurar do backup conforme `v2/docs/DISASTER_RECOVERY.md` / `BACKUP_OPERATIONS.md`.
- [ ] **Abrir PR de revert** se o fix é de código (nunca push direto na `main` — CP-07).
- [ ] **Nunca `systemctl restart docker`** nas VMs (race do Kaspersky derruba o site).

---

## 🚨 Critical Checks (NEVER Skip)

1. ✅ **`make staging-full` 8/8 PASS** — não existe staging remoto; o gate local é a única rede
   de proteção antes de a tag ficar promovível.
2. ✅ **All required CI checks green** + staging-gate markers in the PR body.
3. ✅ **Migrations validadas localmente** — em prod elas são bloqueantes e travam o deploy.
4. ✅ **Promoção aprovada no Environment `production`** — merge não basta, e não é para bastar.
5. ✅ **Pós-promoção: `/api/version/` mostra o release esperado** — a rota devolve a **tag**, não o
   digest; compare com o `release` do `production.json`.
6. ✅ **Rollback path conhecido** — `promote.yml` com `rollback: true` + backup de DB recente.

---

## 🔧 Deployment Types

### Full Deployment

**Use when**: multiple PRs, major feature, breaking changes, or schema changes.
**Extra care**: full `make staging-full` run + smoke completo dos fluxos tocados; confirmar o
`release` do `/api/version/` contra o `production.json` depois da promoção (a rota não devolve digest).

### Hotfix Deployment

**Use when**: critical bug fix, security patch, urgent prod issue.
**Streamlined**: o gate local continua não-negociável (`make staging-full`), mas o smoke cobre só a
área corrigida. O caminho **não** encurta: merge → tag → `promote.yml` → aprovação. Não existe
atalho "direto pra prod" — a `:9443` não é mais pública.

**Example**:
```bash
git checkout -b hotfix/critical-bug
# ... fix bug ...
git commit -m "fix(critical): resolve [issue]"
git push origin hotfix/critical-bug
# ... PR with staging-gate markers, approved, required checks green ...
gh pr merge <PR> --squash                                   # -> build + sign + tag
gh workflow run promote.yml -f release=v2026.MM.DD-<sha7>   # -> gate `production` -> VM01 puxa
```

---

## 📊 Environment Reality

- **No remote staging server.** Validation is **local** (`make staging-full`, prod-like Docker stack).
- **Prod = 3 Golden VMs**: VM01_App (Nginx/Gunicorn/Celery/React), VM02_DB (PostgreSQL 15),
  VM03_Red (Redis 7).
- **Produção puxa; o CI não empurra** (ADR-018). O `PUT` sai do `aprender-applier` para
  `127.0.0.1:9443`; o `aprender-deployer`, que faz o parsing do que vem da internet, **não** detém
  o token do Portainer (separação de privilégio entre dois usuários de sistema).
- **Migrations**: automáticas e bloqueantes no deploy (serviço one-shot `migrate`, #1456).
  Rodar `manage.py migrate` a mão em produção está **revogado**.
- **Compose**: `docker-compose.prod.yml` no repo é a *intenção*; a verdade é o Editor do Portainer,
  e o que o applier reenvia é o `trust/compose.pinned.yml` da VM. Mudou o compose? atualize no
  Editor **e** re-capture o pinado, senão `compose_check_drift` **recusa** o próximo deploy
  (comportamento desejado).
- **Secrets** live in **Portainer** (Golden VMs); `.env.production` in the repo are dev templates.
- **External health probe may be HTTP 000** (Kaspersky/KESL) — a confirmação canônica é a do
  applier, feita de dentro da VM.

---

## 🧪 Manual QA Checklist (RF Validation)

Run against the **local prod-like stack** before merge (and spot-check prod after promoting):

- [ ] RF02: Create solicitação (wizard completes)
- [ ] RF03: Check conflicts (displays conflicts correctly)
- [ ] RF04: Approve/reject (superuser OR Gerente + Superintendência — PA-01)
- [ ] RF05: Google Calendar preview (payload generated)
- [ ] RF06: Meet link generation (field populated)
- [ ] RF07: Audit log (actions recorded)
- [ ] RF08: Monthly grid (data displays correctly)

> Data import is **not ETL** anymore. The import path is `import_export_contract` (mgmt command,
> dry-run by default; `--apply` requires an allowlist) + the DRF endpoints
> `POST /api/controle/import-compras/`, `/api/controle/import-acoes/`, `/api/dat/import-cadastros/`
> (helpers: `make import-compras-dry` / `import-acoes-dry` / `import-cadastros-dry`).
> See `v2/docs/specs/backend/imports.spec.md`.

**Cross-browser** (if UI changes): Chrome, Firefox, Safari, Edge, Mobile Chrome.

---

## 📚 Reference

- **SSOT do fluxo**: `v2/docs/specs/infra/deploy.spec.md`
- **Decisão**: `docs/architecture/project-decisions/ADR-018-pull-based-deploy.md`
  (supersede o `ADR-010-deploy-portainer-direct-to-prod.md`)
- **Agente da VM01**: `v2/infra/deployer/README.md`
- **Checklist operacional**: `v2/docs/DEPLOY_CHECKLIST.md`
- **Imports spec**: `v2/docs/specs/backend/imports.spec.md`
- **Backup/DR**: `v2/docs/DISASTER_RECOVERY.md`, `v2/docs/BACKUP_OPERATIONS.md`
- **Migration command**: `.claude/commands/migrate.md`
- **Testing command**: `.claude/commands/test-coverage.md`
- **Project Context**: `.claude/CLAUDE.md`

---

## ✅ Output

**If all checks pass**:
```
✅ RELEASE PROMOVIDO (ADR-018, pull-based)

Validation: make staging-full → ALL 8 CHECKS PASSED
CI: all [required] checks green
Merge: PR #<n> squash-merged to main → build + sign + release
Tag: v2026.MM.DD-<sha> (imagens assinadas: cosign + SLSA)

Promocao:
- promote.yml aprovado no Environment `production` por <reviewer>
- production.json assinado, sequence <n>, publicado em `deploy-pointer`
- VM01 aplicou por digest; applier selou a sequence

Prod:
- /api/version/  → version = v2026.MM.DD-<sha>, casa com o release do production.json ✓
- /api/readyz/   → 200 ✓
- Smoke: RF02 / RF03 / RF04 ✓

Status: Live in production
```

**If checks fail**:
```
❌ FALHOU — em que degrau?

[ ] gate local (staging-full check N)   → nada foi buildado
[ ] CI [required]                       → nada foi buildado
[ ] deploy.yaml (build/sign/release)    → nenhuma tag promovivel; prod INTACTA
[ ] promote.yml (assinatura/gate)       → ponteiro nao publicado; prod INTACTA
[ ] applier na VM01 (REFUSE <motivo>)   → fail-closed; prod INTACTA (ver motivo:
                                          anti-rollback / compose_drift / backup ausente)
[ ] pos-promocao (/api/version/)        → prod MUDOU e esta ruim → rollback

Rollback (so no ultimo caso):
gh workflow run promote.yml -f release=<tag-anterior> -f rollback=true
+ aprovacao no Environment `production`
(DB: migrations sao forward-only — restaurar backup conforme DISASTER_RECOVERY.md)
Revert PR se o fix e de codigo (sem push direto na main — CP-07)

Next: corrigir a causa, re-rodar make staging-full (8/8), re-merge, re-promover
```

---

**Focus**: gate local (`make staging-full` 8/8) → merge = **build/sign/release** → `promote.yml`
aprovado no Environment `production` → VM01 **puxa** e aplica por digest → verificar `/api/version/`
→ rollback = promover a tag anterior com `rollback: true`.
