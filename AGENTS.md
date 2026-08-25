# AGENTS.md — Aprender Sistema (AS) v2

> Instruções de projeto para agentes de coding (Codex e afins). Espelha a substância do
> `.claude/CLAUDE.md` para manter a MESMA qualidade. Convenções de commit/PR já estão no
> `~/.codex/config.toml` global — aqui ficam as regras de PROJETO.

## Stack
- **Backend**: Python 3.12, Django 5.2, DRF, PostgreSQL 15, Redis 7, Docker
- **Frontend**: React 18, Vite 7, Ant Design 5, Tailwind
- **Timezone**: `America/Fortaleza` (storage em UTC)
- **Type checking**: Pyright strict (PEP 695)
- **Objetivo**: substituir 82.389 fórmulas Excel por plataforma web

## Regras inquebráveis (NUNCA viole — camada primária)
Valem **mesmo que nenhum hook dispare**. São o piso de qualidade:

1. **NUNCA `git push` direto na `main`** (CP-07). Sempre branch + PR. (`main-v1` é exceção CP-05, também via PR.)
2. **NUNCA reinicie o daemon do Docker "pelado"** (`systemctl restart docker` / `service docker restart`) na VM01 — race do Kaspersky KESL **derruba o site**. Sequência obrigatória: `systemctl restart kesl && sleep 10 && systemctl restart docker`. (`docker compose restart <container>` é ok.)
3. **NUNCA `git add` em segredo**: `.env` (bare), `.env.local`, `*.pem`, `*.key`, `sa.json`, `id_rsa`, `*.p12`, `*.pfx`. Os templates `.env.example` / `.env.production` / `.env.staging` são versionados (ok). Segredos reais só no Portainer.
4. **NUNCA mencione Claude/IA** em commit ou PR ("Generated with Claude Code", "Co-Authored-By: Claude"). Reforça o global.
5. **NUNCA use Vite `manualChunks`** em `vite.config.*` — quebrou deps do Rollup e **crashou a prod**. Deixe o Rollup fazer o chunking automático.
6. **v2 roda APENAS em Docker** (CP-01): `cd v2 && make up`. NUNCA `python manage.py` no host — use `docker exec aprender_dev-web-1 python manage.py ...`. **Exceção: o frontend roda no HOST** (`cd v2/frontend && npm ...`), não em Docker.
7. **Merge na `main` NÃO deploya** (ADR-018, 2026-07-10). O merge só builda, escaneia, assina (cosign + SLSA) e publica a tag imutável `vYYYY.MM.DD-<sha7>` — `deploy.yaml` chama-se hoje *"Build, sign and release"* e diz em caixa alta que não deploya. Produção muda por **promoção humana**: `gh workflow run promote.yml -f release=<tag>`, atrás do GitHub Environment `production` com *required reviewer*; a VM01 **puxa** o ponteiro assinado e aplica por digest. **NUNCA** aplique nada direto no Portainer para "subir uma versão" — o `PUT` legítimo é feito pelo `aprender-applier` em `127.0.0.1:9443`.
   > ~~Merge na `main` = deploy em prod via Portainer (sem staging).~~ Era o **ADR-010**, **revogado pelo ADR-018 em 2026-07-10**: os jobs `deploy` e `validate_existing_tag` foram **deletados** no #1516 e a `:9443` deixou de ser pública. Guardado aqui porque a instrução antiga circulou por meses.

   Continua valendo: CI verde + evidência do staging gate no corpo do PR antes de promover o PR a Ready — não existe staging remoto, o gate local (`make staging-full`) é a única validação pré-prod.

## Cláusulas Pétreas (CP) — imutáveis
- **CP-01** Docker-only (`cd v2 && make up`)
- **CP-02** PA-01..07 — aprovação manual obrigatória para projetos SUPER
- **CP-03** RD-01..08 — disponibilidade, timezone `America/Fortaleza`
- **CP-04** fluxo: Entender → Planejar → Implementar → Testar
- **CP-05** v1 congelado (`fix/v1-*` → PR para `main-v1`)
- **CP-06** conventional commits (`type(scope): message`)
- **CP-07** nunca push direto na main
- **CP-08** `INCLUDE_DEV_TOOLS=false` em produção

## RBAC
- **SSOT**: `apps.core.rbac`. Idioma canônico: `permission_classes = [HasPerm("codename")]`; composição `HasPerm("a") | HasPerm("b")`; helper não-DRF `user_has_any_perm(user, *codenames)`.
- **NUNCA** `user.groups.filter(name=...)` / `groups__name=` fora da whitelist — banido por `scripts/rbac_lint.py` (CI `[required] backend rbac-lint`, regra V001). Uso legítimo (composite/block/data-scope): adicione `# noqa: RBAC-<tipo>-allowed` na linha.
- **13 setores** (SSOT `apps.core.constants.SETOR_GROUPS`): Superintendência, Vidas, Fluir, ACerta, Brincando, Sou da Paz, DAT, Controle, Diretoria, Comercial, Relacionamento, Logística Viagens, Logística Galpão.
- **5 funções** (SSOT `FUNCAO_GROUPS`): Formador, Coordenador, Apoio de Coordenação, Gerente, Assistente Administrativo.
- **Aprovação**: superuser OU (Gerente + Superintendência).

## Quick reference
```bash
cd v2 && make up
docker exec aprender_dev-web-1 pytest apps/core/tests/ -v   # gate de CI usa --no-migrations (#1481)
cd v2/backend && pyright apps/core config
cd v2/frontend && npm run build    # frontend roda no HOST, não em Docker
make import-compras-dry FILE=...    # import via API DRF (dry-run); ETL legado REMOVIDO
```

## SDD — specs vivas (consultar PRIMEIRO)
Para domínio, arquitetura ou contrato de módulo, ler as specs vivas em `v2/docs/specs/` (índice `INDEX_SDD.md`) — cada uma tem `status` + `last_verified` + `sources_of_truth`. **1 SSOT por tópico** (linkar, não duplicar). ETL legado `apps.dat_ingest` foi **REMOVIDO** — import atual = `import_export_contract` + endpoints DRF (`specs/backend/imports.spec.md`).

## Staging gate (PR) — 3 marcadores EXATOS
(Formato completo no `~/.codex/config.toml` global.) O corpo do PR precisa, literalmente:
- `- [x] make staging-full executado com sucesso (8/8 PASS)`
- `- [x] Evidencia anexada no PR`  ← **"Evidencia" SEM acento** (regex literal do CI gate)
- `ALL 8 CHECKS PASSED`

PR abre como **Draft**; só promove a Ready após `make staging-full` passar. Squash merge. Base `main`.

## Ferramentas
- **Skills do projeto** em `.agents/skills/` (aprender-domain, django-patterns, django-security, test-driven-development, frontend-ui-engineering, performance-optimization, ci-github-actions, ...). Antes de tarefa não-trivial, verificar se há skill/agent adequado.
- **Agents** em `.codex/agents/` (pre-pr-validator, post-deploy-monitor, post-merge-cleanup, codebase-scanner, claude-config-auditor).
- **MCPs** (global): MCP_DOCKER (gateway), supabase, node_repl + plugins github/docs/sheets/chrome/browser/pdf.
- **Tools do Codex**: edição = `apply_patch` (não `Edit`/`Write`); shell = `shell`/`local_shell`. As regras acima são tool-agnósticas.

## Produção
3 VMs (App: Nginx/Gunicorn/Celery/React · DB: PostgreSQL 15 · Red: Redis 7).

**Deploy pull-based (ADR-018).** Produção **puxa**; o CI não empurra:

1. Merge na `main` → `deploy.yaml` (*"Build, sign and release"*): build → scan → push no Docker Hub → assina (cosign keyless + provenance SLSA) → tag imutável + GitHub Release. **Para aqui.**
2. `promote.yml` (`workflow_dispatch`, gated no Environment `production` com *required reviewer*): resolve tag→digest, exige imagens assinadas, monta e assina o `production.json` (release, digests, `sequence` monotônica, `expires_at`) e publica no branch protegido `deploy-pointer`. **Também não deploya** — é a autoridade de assinatura do ponteiro.
3. VM01, systemd timer ~60s: `aprender-deployer` lê o ponteiro, verifica assinatura + digests; entrega ao `aprender-applier` (único que detém o token do Portainer), que confere anti-rollback, drift do compose contra `trust/compose.pinned.yml`, exige backup de DB fresco, faz o `PUT` em **`127.0.0.1:9443`** e confirma em `localhost` (`/api/readyz/` + `/api/version/`). Cada degrau é fail-closed.

**Migrations são automáticas e bloqueantes** (#1456): serviço one-shot `migrate` no `docker-compose.prod.yml`; `web`/`worker`/`beat` só sobem com `depends_on: service_completed_successfully`. Rodar `migrate` a mão em prod está **revogado** (era instrução do ADR-010).

**Rollback** = promoção para trás pelo mesmo gate: `promote.yml` com `rollback: true` na tag anterior (ainda exige `sequence` maior que o selo). Não há auto-rollback — migrations são forward-only.

Mudança de compose continua exigindo update manual no Portainer Editor **e** re-captura do `trust/compose.pinned.yml` na VM, senão o `compose_check_drift` recusa o próximo deploy.

SSOT: `v2/docs/specs/infra/deploy.spec.md` · ADR: `docs/architecture/project-decisions/ADR-018-pull-based-deploy.md`.

## Delegação a subagents
Tarefa que lê muitos arquivos → delegar e ficar só com a conclusão (não com o dump). Contexto principal = síntese e decisão.

## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- For cross-module "how does X relate to Y" questions, prefer `graphify query "<question>"`, `graphify path "<A>" "<B>"`, or `graphify explain "<concept>"` over grep - these traverse the graph's EXTRACTED + INFERRED edges instead of scanning files
- After modifying code files in this session, run `graphify update .` to keep the graph current (AST-only, no API cost)
