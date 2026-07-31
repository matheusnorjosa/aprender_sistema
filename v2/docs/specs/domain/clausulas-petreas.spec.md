---
title: Cláusulas Pétreas (CP-01..CP-08)
status: canonical
last_verified: 2026-07-24
sources_of_truth:
  - docs/business-rules/clausulas-petreas.md
  - v2/backend/config/settings.py
  - v2/backend/apps/core/services/usuarios_import.py
  - v2/backend/apps/dev_tools/apps.py
  - .github/workflows/ci.yaml
  - v2/scripts/ban_v1.sh
  - docs/architecture/project-decisions/ADR-001-docker-only-deployment.md
  - docs/architecture/project-decisions/ADR-002-approval-policy-manual.md
  - docs/architecture/project-decisions/ADR-003-availability-rules-timezone.md
  - docs/architecture/project-decisions/ADR-004-conventional-commits-branch-protection.md
owner: domain
supersedes:
  - docs/business-rules/clausulas-petreas.md
related:
  - ../../INDEX_SDD.md
  - ./politica-aprovacao.spec.md
  - ./regras-disponibilidade.spec.md
  - ../infra/deploy.spec.md
  - ../../RBAC_NAMING.md
---

# Cláusulas Pétreas (CP-01..CP-08)

## Propósito

As Cláusulas Pétreas são os **8 contratos imutáveis** do Aprender Sistema v2: invariantes de plataforma (onde o sistema roda, como dados sensíveis são tratados) e de processo (como o código entra no repositório). Diferente de RF (funcionais) e RD/PA (domínio), uma CP **não pode ser flexibilizada por feature** — quando há conflito entre uma CP e qualquer outra regra, a CP vence.

Esta spec é o **índice canônico** das CPs: lista cada cláusula com seu **enforcement real no código** (não a intenção). Onde a CP delega a outro domínio (CP-02 → PA, CP-03 → RD), ela apenas aponta para a spec canônica desse domínio. O doc-fonte legível é [`docs/business-rules/clausulas-petreas.md`](../../../../docs/business-rules/clausulas-petreas.md); esta spec é o contrato técnico que casa cada CP com o arquivo que a faz cumprir.

## Fonte de verdade no código

| CP | Enforcement real | Arquivo |
|----|------------------|---------|
| CP-01 | Guard de runtime + CI seta `REQUIRE_DOCKER=1` | [`v2/backend/config/settings.py`](../../../backend/config/settings.py) (linhas ~19-27), [`.github/workflows/ci.yaml`](../../../../.github/workflows/ci.yaml) |
| CP-02 | Política de aprovação (PA-01..PA-07) | → [`politica-aprovacao.spec.md`](./politica-aprovacao.spec.md) |
| CP-03 | Regras de disponibilidade (RD-01..RD-08) | → [`regras-disponibilidade.spec.md`](./regras-disponibilidade.spec.md) |
| CP-04 | Workflow de sub-agents (convenção; **sem gate de CI**) | [`docs/business-rules/clausulas-petreas.md`](../../../../docs/business-rules/clausulas-petreas.md) §CP-04 |
| CP-05 | v1 congelado (convenção/branch protection; **sem script dedicado**) | [`docs/business-rules/clausulas-petreas.md`](../../../../docs/business-rules/clausulas-petreas.md) §CP-05 |
| CP-06 | Conventional commits (convenção; **sem commit-lint em CI**) | [ADR-004](../../../../docs/architecture/project-decisions/ADR-004-conventional-commits-branch-protection.md) |
| CP-07 | Hook local `PreToolUse` + branch protection da `main` | `.claude/settings.json` (bloco `PreToolUse`, local) |
| CP-08 | Gate de `INSTALLED_APPS` por `INCLUDE_DEV_TOOLS` + guard rígido por `ENVIRONMENT` (#1466) | [`v2/backend/config/settings.py`](../../../backend/config/settings.py) (linhas 126, 137-143, 170-171) |

## Contratos e invariantes

- **CP-01 — REQUIRE_DOCKER**: v2 roda **apenas em Docker**. Quando `REQUIRE_DOCKER=1` e o processo **não** vê `/.dockerenv`, `settings.py` aborta com `sys.exit(1)`. Em dev a variável fica desligada (`"0"`); o job de integração da CI exporta `REQUIRE_DOCKER=1` e migra/roda dentro do container.
- **CP-02 — Aprovação manual SUPER**: nenhum fluxo SUPER auto-aprova (nem evento passado, fix #1370); aprovam superuser OU (Gerente + Superintendência) OU (Assistente Administrativo + Controle); integrações (GCal) só disparam **após** aprovação. Contrato detalhado em PA-01..PA-07. ⚠️ A **imutabilidade** desta autoridade não é cumprida hoje — ver §Divergências (`M03-01`).
- **CP-03 — Disponibilidade**: não-sobreposição, bloqueios T/P, buffer de deslocamento (D) e capacidade diária (M), timezone `America/Fortaleza` (storage UTC). Contrato detalhado em RD-01..RD-08.
- **CP-04 — Workflow**: agentes autônomos seguem a ordem **Entender → Planejar → Implementar → Testar** (Infra/ETL/UI como fases subsequentes). É disciplina de processo, **não** verificada por CI.
- **CP-05 — v1 congelado**: v1 só muda por branch `fix/v1-*` + PR para `main-v1`, com aprovação. Não há script que bloqueie edição de v1 — o backstop é a separação de branches + revisão.
- **CP-06 — Conventional commits**: commits seguem `type(scope): message` (`feat|fix|chore|docs|test|refactor`); branches `type/nome`; PR exige aprovação + CI verde. Convenção formalizada em ADR-004 (não há job de commit-lint que reprove o título).
- **CP-07 — Nunca push direto na `main`**: sempre via branch + PR (squash-merge após CI verde). Hook local `PreToolUse` em `.claude/settings.json` bloqueia `git push ... origin main`; o backstop **autoritativo** é o ruleset de branch protection da `main` no GitHub.
- **CP-08 — dev_tools off em produção**: `apps.dev_tools` (seeds/backfills/fixtures/`FreezeTimeMiddleware`) só entra em `INSTALLED_APPS` se `INCLUDE_DEV_TOOLS != "false"` ([`settings.py:126`](../../../backend/config/settings.py), `:170-171`). **Default é `true`**, mas desde o #1466 há guard rígido: `if ENVIRONMENT == "production": INCLUDE_DEV_TOOLS = False` (`:137-143`), aplicado **independentemente** da env var. Pedir `INCLUDE_DEV_TOOLS=true` em produção emite warning e é ignorado. O guard força o valor em vez de `sys.exit(1)` de propósito — como a stack de produção não define a variável, abortar o boot converteria o footgun em indisponibilidade no primeiro deploy.

## API / Interface

As CPs não expõem endpoints próprios; são invariantes atravessando o sistema. Pontos de controle:

- **Variáveis de ambiente** (gate de runtime): `REQUIRE_DOCKER` (CP-01), `INCLUDE_DEV_TOOLS` (CP-08), `DEBUG_E2E` (gate duplo com `INCLUDE_DEV_TOOLS`).
- **Hook do harness** (CP-07): `PreToolUse` → `Bash` em `.claude/settings.json`; `git push:*` também está na lista `ask` de permissões.
- **CI gates relacionados**: job `[required] backend rbac-lint` (ci.yaml) reforça o idioma RBAC `permission_classes = [HasPerm("codename")]` via [`v2/backend/scripts/rbac_lint.py`](../../../backend/scripts/rbac_lint.py) — não é uma CP, mas é o guard que protege o modelo de capabilities citado no contexto de CP-02.

## Fluxos principais

1. **Boot do backend (CP-01 + CP-08)**: `settings.py` lê `REQUIRE_DOCKER` → se `1` e fora de container, aborta. Em seguida lê `INCLUDE_DEV_TOOLS` → se `≠ "false"`, anexa `apps.dev_tools` a `INSTALLED_APPS`; `FreezeTimeMiddleware` só é inserido com `DEBUG_E2E and INCLUDE_DEV_TOOLS` (gate duplo).
2. **Tentativa de push na main (CP-07)**: o comando é interceptado pelo hook `PreToolUse`; se casar `push ... origin main`, falha com `CP-07 VIOLADO`. Mesmo que o hook não exista (clone novo), a branch protection da `main` recusa o push sem PR.
3. **Aprovação de evento SUPER (CP-02)**: solicitação → aprovação manual por papel autorizado → só então a integração (GCal) executa. Erro relevante: SUPER tentando auto-aprovar é negado (PA-01).
4. **Erro comum (CP-08), fechado pelo #1466**: `stack.env` de produção sem `INCLUDE_DEV_TOOLS` → default `true` → `apps.dev_tools` era carregado em prod (CP-08 violado silenciosamente). Hoje o guard por `ENVIRONMENT == "production"` (`settings.py:137-143`) zera a variável antes do `INSTALLED_APPS`, então a omissão deixou de ser um footgun. Setar `INCLUDE_DEV_TOOLS=false` explicitamente continua sendo boa higiene, mas não é mais a única linha de defesa.

## Decisões relacionadas (ADRs)

- [ADR-001 — Docker-only deployment](../../../../docs/architecture/project-decisions/ADR-001-docker-only-deployment.md) (CP-01)
- [ADR-002 — Approval policy manual](../../../../docs/architecture/project-decisions/ADR-002-approval-policy-manual.md) (CP-02)
- [ADR-003 — Availability rules / timezone](../../../../docs/architecture/project-decisions/ADR-003-availability-rules-timezone.md) (CP-03)
- [ADR-004 — Conventional commits & branch protection](../../../../docs/architecture/project-decisions/ADR-004-conventional-commits-branch-protection.md) (CP-06, CP-07)

## Testes que cobrem

- **CP-02 / CP-03**: cobertos pelas suítes de PA e RD (ver as specs `politica-aprovacao.spec.md` e `regras-disponibilidade.spec.md`); o skill `/approve-flow` e `/check-conflicts` exercitam PA-01..PA-07 e RD-01..RD-08.
- **CP-01 / CP-08**: gates de configuração em `settings.py` — verificados em runtime/CI (job de integração com `REQUIRE_DOCKER=1`), não por teste unitário dedicado.
- **CP-07**: enforcement por hook + branch protection — verificação operacional (comportamento do harness/GitHub), sem teste de código.
- **CP-04 / CP-05 / CP-06**: convenções de processo — sem cobertura automatizada (ver Pontos de atenção).

## Divergências entre a cláusula e o código

> Reconfirmadas por execução contra `main d08acfa5` e **vivas em produção**. Fonte:
> [`ACHADOS_REAIS.md`](../../audits/ACHADOS_REAIS.md).

### `M03-01` — CP-02: a autoridade de aprovação é auto-concedível

**Severidade P0 · aberto · issue #1610 · vivo em produção.**

CP-02 declara a autoridade de aprovação imutável. O import de usuários a torna concedível por quem já tem `manage_admin_registries` (grupo **DAT** — 3 contas ativas não-superuser em produção):

- Gate: `permission_classes = [IsAuthenticated, HasPerm("manage_admin_registries")]` ([`views_import_usuarios.py:66`](../../../backend/apps/core/views_import_usuarios.py)).
- `_assign_groups` ([`usuarios_import.py:374-382`](../../../backend/apps/core/services/usuarios_import.py)) faz `usuario.groups.add(grupo)` para **qualquer** grupo resolvido por nome, sem allowlist e sem comparar ator × alvo.

`POST /api/usuarios/import/?dry_run=false` com o próprio CPF e `grupos="Gerente,Superintendencia"` devolve **HTTP 200** e concede os dois grupos — exatamente o composite exigido por `_user_has_solicitation_approvals` ([`policies.py:415-418`](../../../backend/apps/core/rbac/policies.py)).

Efeito sobre a cláusula: CP-02 continua correta como *regra pretendida* e correta no *ponto de decisão* (o gate de `approve` de fato exige o composite), mas **falsa como invariante** — o conjunto de quem pode aprovar não é fixo. Detalhe do fluxo em [`politica-aprovacao.spec.md`](./politica-aprovacao.spec.md) §Divergências.

CP-03 também tem divergências vivas (`M08-07`, `M08-09`, épico #1664) — ver [`regras-disponibilidade.spec.md`](./regras-disponibilidade.spec.md) §Divergencias.

## Pontos de atenção / dívidas conhecidas

- **CP-04, CP-05, CP-06 não têm enforcement automatizado**: são convenções. Não há commit-lint em CI (CP-06), nem script que proteja v1 (CP-05), nem gate de workflow (CP-04). O cumprimento depende de revisão humana + branch protection.
- **`v2/scripts/ban_v1.sh` NÃO é o enforcement de CP-05**: apesar do nome, o script faz **limpeza de containers/redes/volumes Docker** do projeto legado (`project=aprendersistema`), não bane edições de código v1. Não citar como guard de CP-05.
- **CP-07 — hook é gitignored**: `.claude/settings.json` vive em `.claude/` (não herdado por clone novo); o enforcement **confiável** é a branch protection da `main` no GitHub. O hook é defesa-em-profundidade local.
- **CP-08 — resolvido pelo #1466**: o hardening que esta spec recomendava (`if ENVIRONMENT == "production": INCLUDE_DEV_TOOLS = False`) **existe** em `settings.py:137-143`. O default de `INCLUDE_DEV_TOOLS` continua `true`, mas ele só vale fora de produção. Resta a dívida menor de o default ser inseguro para qualquer `ENVIRONMENT` que não seja exatamente `"production"` (ex.: staging escrito com outro rótulo).
- **CP-01 — guard só dispara com `REQUIRE_DOCKER=1`**: rodar v2 fora de Docker com a variável ausente (`"0"`) não aborta. A garantia em prod vem do compose/imagem, não do guard isolado.
