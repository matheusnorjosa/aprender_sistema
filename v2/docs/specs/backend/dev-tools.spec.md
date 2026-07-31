---
title: dev_tools — Catálogo de Seeds
status: canonical
last_verified: 2026-07-24
sources_of_truth:
  - v2/backend/apps/dev_tools/__init__.py
  - v2/backend/apps/dev_tools/apps.py
  - v2/backend/config/settings.py
  - v2/backend/apps/dev_tools/management/commands/seed_rbac.py
  - v2/backend/apps/dev_tools/management/commands/seed_e2e_users.py
  - v2/backend/apps/dev_tools/management/commands/seed_frontend_contract_data.py
  - v2/backend/apps/dev_tools/management/commands/seed_gerencias.py
  - v2/backend/apps/dev_tools/management/commands/seed_gerentes.py
  - v2/backend/apps/dev_tools/management/commands/seed_produtos.py
  - v2/backend/apps/dev_tools/management/commands/seed_tipos_evento.py
  - v2/backend/apps/dev_tools/management/commands/seed_projetos_fluxo_from_csv.py
  - v2/backend/apps/dev_tools/management/commands/seed_projetos_fluxo_from_sheets.py
  - v2/backend/apps/dev_tools/management/commands/link_projetos_gerencias.py
  - v2/backend/apps/dev_tools/management/commands/fix_projetos_gerencia.py
  - v2/backend/apps/dev_tools/management/commands/migrate_rbac_groups.py
  - v2/backend/apps/dev_tools/management/commands/backfill_is_online.py
  - v2/backend/apps/dev_tools/management/commands/populate_municipio_coords.py
  - v2/backend/apps/dev_tools/management/commands/cleanup_e2e_data.py
  - v2/backend/apps/dev_tools/middleware/freeze_time.py
  - v2/backend/apps/dev_tools/tests/test_optional_dev_tools.py
  - v2/backend/apps/dev_tools/tests/test_seed_e2e_users.py
  - v2/backend/apps/dev_tools/tests/test_seed_gerentes.py
  - v2/backend/apps/dev_tools/tests/test_seed_frontend_contract_data.py
  - v2/backend/apps/dev_tools/tests/test_projetos_fluxo_seed.py
  - v2/backend/apps/dev_tools/tests/test_freeze_time_middleware.py
owner: backend
supersedes: []
related:
  - v2/docs/specs/infra/deploy.spec.md
  - v2/docs/RBAC_NAMING.md
---

# dev_tools — Catálogo de Seeds

## Propósito

`apps.dev_tools` concentra todas as ferramentas de desenvolvimento do AS v2 — seeds (dados iniciais), backfills (migrações de dados pontuais), fixups (correções únicas) e cleanup de dados de teste E2E — fora do app de produção `apps.core`. Existe para popular bancos de dev, CI e E2E de forma idempotente sem misturar esse código com o domínio operacional, e para garantir que nenhum management command de seed vaze para produção.

O app é **condicional**: só entra em `INSTALLED_APPS` quando `INCLUDE_DEV_TOOLS=true` (default em dev/CI). Em produção, a Cláusula Pétrea CP-08 exige `INCLUDE_DEV_TOOLS=false`, removendo o app inteiro — e com ele todos os comandos `seed_*`, `backfill_*`, `fix_*`, `cleanup_*` e o `FreezeTimeMiddleware`. Desde o #1466 esse `false` **não depende mais do `stack.env`**: `settings.py` força o valor quando `ENVIRONMENT == "production"` (ver §Contratos).

## Fonte de verdade no código

- Gate de inclusão (CP-08): [`v2/backend/config/settings.py`](../../../backend/config/settings.py) — `INCLUDE_DEV_TOOLS = os.getenv("INCLUDE_DEV_TOOLS", "true").lower() == "true"` (`:126`); **guard rígido de produção em `:137-143`** (`if ENVIRONMENT == "production": ... INCLUDE_DEV_TOOLS = False`, com warning no stderr quando alguém pede `true` explicitamente); o app só é anexado via `if INCLUDE_DEV_TOOLS: INSTALLED_APPS.append("apps.dev_tools")` (`:170-171`).
- AppConfig: [`v2/backend/apps/dev_tools/apps.py`](../../../backend/apps/dev_tools/apps.py) (`DevToolsConfig`, sem lógica de gate — o gate vive em `settings.py`).
- Pacote: [`v2/backend/apps/dev_tools/__init__.py`](../../../backend/apps/dev_tools/__init__.py).
- Management commands: `v2/backend/apps/dev_tools/management/commands/*.py` — **15 comandos** (16 arquivos `.py` no total, incluindo `__init__.py`). Os 15 estão na tabela abaixo, 1:1 com os arquivos.
- Middleware auxiliar E2E: [`v2/backend/apps/dev_tools/middleware/freeze_time.py`](../../../backend/apps/dev_tools/middleware/freeze_time.py) (`FreezeTimeMiddleware`, gate duplo `DEBUG_E2E` + `INCLUDE_DEV_TOOLS`).

### Catálogo: comando → o que semeia

| Comando | O que semeia / faz |
|---------|--------------------|
| `seed_rbac` | Grupos e permissões mínimas. `GROUPS = SETOR_GROUPS + FUNCAO_GROUPS` (`seed_rbac.py:30`) = **13 setores + 5 funções = 18**; o loop de `PERMS_BY_GROUP` (`:127-128`) cria ainda o grupo legado `"Gerência"` (`:89`), fora de `GROUPS`. Idempotente; é a base do RBAC. ⚠️ O docstring do próprio comando (`:3`) ainda diz "FUNCAO_GROUPS (4)" — desatualizado: `apps/core/constants.py:36-45` tem **5** funções desde a inclusão de `Assistente Administrativo`. |
| `seed_e2e_users` | **13** usuários (`coord_e2e`, `super_e2e`, `controle_e2e`, `formador_e2e`, `coord_vidas`, `coord_fluir`, `coord_acerta`, `gerente_vidas`, `dat_e2e`, `super_geral`, `approver_03`, `formador_vidas`, `formador_fluir`) + grupos, **2** municípios (Salvador/BA e Fortaleza/CE, para cobrir RD-04), **2** projetos (`TESTE E2E` fluxo SUPER e `TESTE E2E NAO_SUPER` fluxo NAO_SUPER), além de `TipoEvento` e `Compra`. Idempotente. ⚠️ O docstring do comando (`seed_e2e_users.py:14-17`) ainda anuncia "4 usuários / 1 município / 1 projeto" — desatualizado. |
| `seed_frontend_contract_data` | Dados determinísticos da matriz funcional crítica frontend↔backend (checklist Playwright): usuários, municípios, projetos, compras, solicitações. |
| `seed_gerencias` | Seed inicial de gerências (7 registros). |
| `seed_gerentes` | Vincula gerentes ao grupo função Gerente + `EquipeGerencia.papel=GERENTE`. |
| `seed_produtos` | Seed inicial dos principais produtos. |
| `seed_tipos_evento` | `TipoEvento` com os tipos padrão. Idempotente. |
| `seed_projetos_fluxo_from_csv` | Popula `Projeto.fluxo` a partir de CSV. Idempotente. |
| `seed_projetos_fluxo_from_sheets` | Popula `Projeto.fluxo` a partir de planilhas XLSX. Idempotente. |
| `link_projetos_gerencias` | Vincula projetos existentes às gerências. |
| `fix_projetos_gerencia` | Corrige vinculação de projetos a gerências. Idempotente (fixup). |
| `migrate_rbac_groups` | Migra usuários para a estrutura RBAC atual (Setor + Função). Backfill. |
| `backfill_is_online` | Backfill a partir da coluna G da planilha original; grava **três** campos de `Solicitacao` num só `update`: `tipo`, `is_online` e `tipo_evento` (`backfill_is_online.py:83`). |
| `populate_municipio_coords` | Popula latitude/longitude de `Municipio` a partir de CSV. |
| `cleanup_e2e_data` | Remove os dados E2E criados por `seed_e2e_users` (Playwright). |

## Contratos e invariantes

- **CP-08 (imutável)**: produção roda com `INCLUDE_DEV_TOOLS=false`. Sem o app, **nenhum** comando de seed/backfill/fix/cleanup fica disponível e `FreezeTimeMiddleware` não é instalado. Texto canônico em `docs/business-rules/clausulas-petreas.md:62-66`.
- **Guard por `ENVIRONMENT` EXISTE** (`settings.py:137-143`, #1466): quando `ENVIRONMENT == "production"`, `INCLUDE_DEV_TOOLS` é **forçado a `False`** independentemente da env var, e um `WARNING` vai ao stderr se alguém tiver pedido `true` explicitamente. Optou-se por forçar o valor em vez de `sys.exit(1)` de propósito — como a stack de produção não define a variável, abortar o boot converteria o footgun em indisponibilidade. Sentinela: `apps/core/tests/test_prod_guard_rails.py:248-263`.
  - O default `true` continua valendo para **qualquer outro `ENVIRONMENT`** (dev, CI, staging), e é lá que mora o risco residual: um ambiente com dados sensíveis rotulado como algo diferente de `production` carrega o app de seeds.
  - ⚠️ O bullet de alerta de `docs/business-rules/clausulas-petreas.md:66` ("não há guard por `ENVIRONMENT`") está **desatualizado**. Esta spec é a referência correta enquanto o doc de CP não for reconciliado.
- **Idempotência**: seeds usam `get_or_create` / lógica idempotente — rodar N vezes não duplica dados. É invariante esperada de todo `seed_*` (validada nos testes).
- **Separação de domínio**: `apps.core` (produção) NÃO depende de `apps.dev_tools`. Toda lógica de produção precisa viver fora deste app, pois ele desaparece em prod.
- **RBAC**: seeds criam grupos por nome, mas a autorização em runtime continua via `permission_classes=[HasPerm("codename")]` — grupos diretos (`user.groups.filter(name=...)`) são banidos por `scripts/rbac_lint.py` fora do código de seed. Ver [RBAC_NAMING.md](../../RBAC_NAMING.md).
- **FreezeTimeMiddleware (gate duplo)**: só ativo com `DEBUG_E2E=true` **e** `INCLUDE_DEV_TOOLS=true`; levanta `RuntimeError` se invocado sem `INCLUDE_DEV_TOOLS`.

## API / Interface

Não há endpoints HTTP — a interface pública são os **management commands** Django:

```bash
# dev / CI (INCLUDE_DEV_TOOLS=true)
docker exec aprender_dev-web-1 python manage.py seed_rbac
docker exec aprender_dev-web-1 python manage.py seed_e2e_users
docker exec aprender_dev-web-1 python manage.py cleanup_e2e_data
```

Em CI o E2E roda com `INCLUDE_DEV_TOOLS=true` + `DEBUG_E2E=true` (ver `.github/workflows/frontend-ci.yml`). O `FreezeTimeMiddleware` congela `timezone.now()` quando a request envia o header `X-E2E-Frozen-Time` (consumido pela fixture `v2/frontend/e2e/fixtures/time.ts`).

## Fluxos principais

1. **Bootstrap de dev** (caminho feliz): `make up` → aplica migrações → roda a sequência canônica de seeds (`seed_rbac` antes de tudo, depois masters como `seed_gerencias`/`seed_produtos`/`seed_tipos_evento`, vínculos `seed_gerentes`/`link_projetos_gerencias`, e fixos como `fix_projetos_gerencia`). Idempotente: re-rodar não duplica.
2. **E2E (Playwright)**: `seed_rbac` → `seed_e2e_users` (ou `seed_frontend_contract_data` para a matriz de contrato) → suíte roda → `cleanup_e2e_data` remove o que `seed_e2e_users` criou.
3. **Backfill pontual**: `migrate_rbac_groups` / `backfill_is_online` / `populate_municipio_coords` rodam uma vez para corrigir/preencher dados existentes.
4. **Erro esperado em prod**: com `INCLUDE_DEV_TOOLS=false`, `manage.py seed_rbac` falha com "Unknown command" — o app não está em `INSTALLED_APPS`. Esse é o comportamento desejado (CP-08).

## Decisões relacionadas (ADRs)

- CP-08 (Cláusula Pétrea) — `INCLUDE_DEV_TOOLS=false` em produção. Texto canônico em `docs/business-rules/clausulas-petreas.md`.
- Histórico de design do app: `v2/docs/_archive/plans/PLAN_dev_tools_app.md` (arquivado).

## Testes que cobrem

- [`tests/test_optional_dev_tools.py`](../../../backend/apps/dev_tools/tests/test_optional_dev_tools.py) — prova o gate: default `True`, app em `INSTALLED_APPS` quando ligado, comandos disponíveis/indisponíveis conforme `INCLUDE_DEV_TOOLS` (CP-08).
- [`tests/test_seed_e2e_users.py`](../../../backend/apps/dev_tools/tests/test_seed_e2e_users.py) — idempotência e dados criados pelo seed E2E.
- [`tests/test_seed_gerentes.py`](../../../backend/apps/dev_tools/tests/test_seed_gerentes.py) — vínculo Gerente + `EquipeGerencia`.
- [`tests/test_seed_frontend_contract_data.py`](../../../backend/apps/dev_tools/tests/test_seed_frontend_contract_data.py) — matriz de contrato funcional.
- [`tests/test_projetos_fluxo_seed.py`](../../../backend/apps/dev_tools/tests/test_projetos_fluxo_seed.py) — `seed_projetos_fluxo_from_csv`/`_from_sheets`.
- [`tests/test_freeze_time_middleware.py`](../../../backend/apps/dev_tools/tests/test_freeze_time_middleware.py) — gate duplo `DEBUG_E2E`+`INCLUDE_DEV_TOOLS` e `RuntimeError` sem o flag.

## Pontos de atenção / dívidas conhecidas

- **Risco residual do default `true`**: o failsafe por `ENVIRONMENT=production` **já existe** (#1466, `settings.py:137-143`) — a versão anterior desta spec dizia que faltava. O que sobra é o default `true` para qualquer outro rótulo de ambiente: um staging com dados reais e `ENVIRONMENT=staging` carrega `apps.dev_tools`. Auditar via [deploy.spec.md](../infra/deploy.spec.md).
- **Docstrings de comando são fonte não-confiável**: `seed_rbac.py:3` e `seed_e2e_users.py:14-17` descrevem números que o código já não produz (4 funções, 4 usuários). Ao atualizar um seed, atualizar o docstring **e** esta tabela.
- **Gate fora do app**: o gate vive em `config/settings.py`, não em `apps/dev_tools/apps.py` — quem audita o app precisa olhar settings. (Esta spec corrige a expectativa de que o gate estaria em `apps.py`.)
- **Comandos não-seed na mesma pasta**: `backfill_*`, `fix_*`, `migrate_rbac_groups` e `populate_municipio_coords` são one-shot/legados; alguns dependem de planilhas/CSV externos (ex.: `backfill_is_online` lê coluna G da planilha original) e podem estar obsoletos após os data-fixes manuais do golden dataset. Confirmar relevância antes de rodar.
- **`seed_rbac` é pré-requisito**: várias suítes e seeds assumem grupos/permissões já criados; rodar seeds dependentes antes de `seed_rbac` falha. A sequência canônica está documentada na memória de seed order do projeto.
