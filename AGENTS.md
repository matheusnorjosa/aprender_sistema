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
7. **Merge na `main` = DEPLOY EM PROD** via Portainer (sem staging). Confirme CI verde + evidência do staging gate antes de promover o PR a Ready.

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
3 VMs (App: Nginx/Gunicorn/Celery/React · DB: PostgreSQL 15 · Red: Redis 7). Deploy: merge na `main` → GitHub Actions builda imagem → redeploy via **Portainer CE API** (sem staging). Mudança de compose exige update manual no Portainer Editor.

## Delegação a subagents
Tarefa que lê muitos arquivos → delegar e ficar só com a conclusão (não com o dump). Contexto principal = síntese e decisão.

## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- For cross-module "how does X relate to Y" questions, prefer `graphify query "<question>"`, `graphify path "<A>" "<B>"`, or `graphify explain "<concept>"` over grep - these traverse the graph's EXTRACTED + INFERRED edges instead of scanning files
- After modifying code files in this session, run `graphify update .` to keep the graph current (AST-only, no API cost)
