---
title: dev_tools — Catálogo de Seeds
status: canonical
last_verified: 2026-10-19
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

- Gate de inclusão (CP-08): [`v2/backend/config/settings.py`](../../../backend/config/settings.py) — `INCLUDE_DEV_TOOLS = os.getenv("INCLUDE_DEV_TOOLS", "true").lower() == "true"`; **guard rígido de produção** (`if ENVIRONMENT == "production": ... INCLUDE_DEV_TOOLS = False`, com warning no stderr quando alguém pede `true` explicitamente); o app só é anexado via `if INCLUDE_DEV_TOOLS: INSTALLED_APPS.append("apps.dev_tools")`.
- AppConfig: [`v2/backend/apps/dev_tools/apps.py`](../../../backend/apps/dev_tools/apps.py) (`DevToolsConfig`, sem lógica de gate — o gate vive em `settings.py`).
- Pacote: [`v2/backend/apps/dev_tools/__init__.py`](../../../backend/apps/dev_tools/__init__.py).
- Management commands: `v2/backend/apps/dev_tools/management/commands/*.py` — **15 comandos** (16 arquivos `.py` no total, incluindo `__init__.py`). Os 15 estão na tabela abaixo, 1:1 com os arquivos.
- Middleware auxiliar E2E: [`v2/backend/apps/dev_tools/middleware/freeze_time.py`](../../../backend/apps/dev_tools/middleware/freeze_time.py) (`FreezeTimeMiddleware`, gate duplo `DEBUG_E2E` + `INCLUDE_DEV_TOOLS`).

### Catálogo: comando → o que semeia

| Comando | O que semeia / faz |
|---------|--------------------|
| `seed_rbac` | Grupos e permissões mínimas. `GROUPS = SETOR_GROUPS + FUNCAO_GROUPS` (`seed_rbac.py`) = **13 setores + 5 funções = 18**; o loop de `PERMS_BY_GROUP` cria ainda o grupo legado `"Gerência"`, fora de `GROUPS`. Idempotente; é a base do RBAC. |
| `seed_e2e_users` | **13** usuários (`coord_e2e`, `super_e2e`, `controle_e2e`, `formador_e2e`, `coord_vidas`, `coord_fluir`, `coord_acerta`, `gerente_vidas`, `dat_e2e`, `super_geral`, `approver_03`, `formador_vidas`, `formador_fluir`) + grupos, **2** municípios (Salvador/BA e Fortaleza/CE, para cobrir RD-04), **2** projetos (`TESTE E2E` fluxo SUPER na gerência `Super` (`SUPERINTENDENCIA`), como em produção desde o PR 11, e `TESTE E2E NAO_SUPER` fluxo NAO_SUPER na gerência Vidas; desde o PR 9 das permissões quem cria precisa atuar na gerência do projeto, e quem cria no E2E é `coord_vidas`, que tem papel nas duas), além de `TipoEvento` e das `DATCompra` que liberam os 4 pares (regra da compra, 14/10/2026), gravadas em nome da conta inativa `compras_e2e@test.com`, fora das personas, para que `cleanup_e2e_data` e os testes que apagam personas não esbarrem no `created_by` (PROTECT). Vínculos `EquipeGerencia` (papel @ gerência), que são a fonte do poder (lotação; o grupo é etiqueta): `coord_e2e` COORDENADOR e `formador_e2e` FORMADOR na `GERENCIA E2E` (perfil PADRAO, sem pacote); `coord_vidas` COORDENADOR, `gerente_vidas` GERENTE e `formador_vidas` FORMADOR em Vidas; `coord_fluir` COORDENADOR e `formador_fluir` FORMADOR em Fluir; `coord_acerta` COORDENADOR em ACerta; `coord_vidas` COORDENADOR e `formador_vidas` FORMADOR também na `Super` (PR 11, para criar e participar do projeto SUPER); `super_e2e`, `super_geral` e `approver_03` GERENTE na `Super` (desde o PR B1, a base que aprova o SUPER); `dat_e2e` EQUIPE na `GERENCIA DAT` (perfil ADMIN_OPERACIONAL, PR 10: aprova qualquer evento, exclui, Pré-agenda); `controle_e2e` EQUIPE na gerência `CONTROLE` (perfil CONTROLE, PR 12a: aprova qualquer evento). O seed cria as gerências `GERENCIA E2E`, `GERENCIA DAT` e `CONTROLE` se faltarem. Idempotente. |
| `seed_frontend_contract_data` | Dados determinísticos do checklist Playwright. Roda `seed_e2e_users` e cria a matriz funcional crítica frontend↔backend (`dat_matrix`, Matrizopolis, a Compra `MATRIX-PEND-001` e o DATCompra "KIT MATRIX CONTRACT"). Para o spec "sem rolagem horizontal" (Programa C), cria também o superusuário `admin_matrix@test.com`, único perfil que abre as rotas cuja policy não vem do pacote nem do papel de nenhuma persona do seed (`manage_internal_actions`; `view_overview_dashboard` é do pacote DIRETORIA, sem persona), e uma linha com texto de 80+ caracteres (prefixo "Aaa", para cair na 1ª página) em cada tabela: pessoa, município (com coordenadas, para a vista Lista do Mapa), projeto, projeto geral, produto, tipo de evento, gerência inativa, grupo, solicitações pendente e aprovada, bloqueio, deslocamento, ação/coordenador/plano/cadastro/registro DAT, ação interna e notificação. Nenhuma dessas linhas aponta para Matrizopolis, `dat_matrix` ou `controle_e2e`, que o teste do seed apaga. Idempotente. |
| `seed_gerencias` | Seed inicial de gerências (7 registros). |
| `seed_gerentes` | Vincula gerentes ao grupo função Gerente + `EquipeGerencia.papel=GERENTE`. A lista vem de um JSON do operador guardado **fora do git** (`--arquivo`; sem ele, `CommandError`); a saída identifica as contas por `u<id>`. Desde 16/10/2026 (F5 do scan de segurança) o código não traz CPF, nome nem e-mail de pessoa real. |
| `seed_produtos` | Seed inicial dos principais produtos. |
| `seed_tipos_evento` | `TipoEvento` com os tipos padrão. Idempotente. |
| `seed_projetos_fluxo_from_csv` | Popula `Projeto.fluxo` a partir de CSV. Idempotente. |
| `seed_projetos_fluxo_from_sheets` | Popula `Projeto.fluxo` a partir de planilhas XLSX. Idempotente. |
| `link_projetos_gerencias` | Vincula projetos existentes às gerências. |
| `fix_projetos_gerencia` | Corrige vinculação de projetos a gerências. Idempotente (fixup). |
| `migrate_rbac_groups` | **OBSOLETO desde o PR 12**: só põe o grupo `Gerente`, que não dá poder no modo `lotacao` (só somaria no modo de emergência `uniao`); o papel é o vínculo `EquipeGerencia` GERENTE vigente. |
| `backfill_is_online` | Backfill a partir da coluna G da planilha original; grava **três** campos de `Solicitacao` num só `update`: `tipo`, `is_online` e `tipo_evento` (`backfill_is_online.py`). |
| `populate_municipio_coords` | Popula latitude/longitude de `Municipio` a partir de CSV. |
| `cleanup_e2e_data` | Limpeza **parcial** do que `seed_e2e_users` cria (Playwright): apaga só as **4 personas legadas** (`coord_e2e`, `super_e2e`, `controle_e2e`, `formador_e2e`), com as solicitações, participações e vínculos `EquipeGerencia` delas (FK PROTECT), o município Salvador e o projeto `TESTE E2E` quando não têm dependência. Ficam no banco as outras 9 personas com os vínculos, inclusive contas com poder: `dat_e2e` (EQUIPE na `GERENCIA DAT`, ADMIN_OPERACIONAL) e as aprovadoras `super_geral` e `approver_03` (GERENTE na `Super`); ficam também as gerências `GERENCIA E2E`, `GERENCIA DAT` e `CONTROLE` e as `DATCompra` do seed. ⚠️ O passo do município falha quando há compra no município (FK PROTECT; desde 14/10/2026 as `DATCompra` do seed) — defeito anterior ao PR B1, não corrigido. Como os passos rodam num só `transaction.atomic`, essa falha desfaz também a remoção das personas: logo depois de `seed_e2e_users`, o comando (fora do `--dry-run`) não apaga nada. |

## Contratos e invariantes

- **CP-08 (imutável)**: produção roda com `INCLUDE_DEV_TOOLS=false`. Sem o app, **nenhum** comando de seed/backfill/fix/cleanup fica disponível e `FreezeTimeMiddleware` não é instalado. Texto canônico em `docs/business-rules/clausulas-petreas.md`.
- **Guard por `ENVIRONMENT` EXISTE** (`settings.py`, `INCLUDE_DEV_TOOLS`, #1466): quando `ENVIRONMENT == "production"`, `INCLUDE_DEV_TOOLS` é **forçado a `False`** independentemente da env var, e um `WARNING` vai ao stderr se alguém tiver pedido `true` explicitamente. Optou-se por forçar o valor em vez de `sys.exit(1)` de propósito — como a stack de produção não define a variável, abortar o boot converteria o footgun em indisponibilidade. Sentinela: `apps/core/tests/test_prod_guard_rails.py` (`DevToolsProductionGuardTests`).
  - O default `true` continua valendo para **qualquer outro `ENVIRONMENT`** (dev, CI, staging), e é lá que mora o risco residual: um ambiente com dados sensíveis rotulado como algo diferente de `production` carrega o app de seeds.
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

1. **Bootstrap de dev** (caminho feliz): `make up` → aplica migrações → roda a sequência canônica de seeds (`seed_rbac` antes de tudo, depois masters como `seed_gerencias`/`seed_produtos`/`seed_tipos_evento`, vínculos `seed_gerentes --arquivo <json fora do git>`/`link_projetos_gerencias`, e fixos como `fix_projetos_gerencia`). Idempotente: re-rodar não duplica.
2. **E2E (Playwright)**: `seed_rbac` → `seed_e2e_users` (ou `seed_frontend_contract_data` para a matriz de contrato) → suíte roda → `cleanup_e2e_data` remove só as 4 personas legadas e os dados delas; as demais personas (entre elas `dat_e2e`, que administra, e `super_geral`/`approver_03`, que aprovam o SUPER) seguem no banco com o poder dos vínculos; e, com as `DATCompra` do seed em Salvador, o comando falha e não apaga nada (ver o catálogo).
3. **Backfill pontual**: `backfill_is_online` / `populate_municipio_coords` rodam uma vez para corrigir/preencher dados existentes.
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

- **Risco residual do default `true`**: o failsafe por `ENVIRONMENT=production` **já existe** (#1466, `settings.py`, `INCLUDE_DEV_TOOLS`) — a versão anterior desta spec dizia que faltava. O que sobra é o default `true` para qualquer outro rótulo de ambiente: um staging com dados reais e `ENVIRONMENT=staging` carrega `apps.dev_tools`. Auditar via [deploy.spec.md](../infra/deploy.spec.md).
- **Docstrings de comando**: os de `seed_rbac.py` e `seed_e2e_users.py` foram conferidos em 19/10/2026 e batem com o código. Ao mudar um seed, atualizar o docstring **e** esta tabela.
- **Gate fora do app**: o gate vive em `config/settings.py`, não em `apps/dev_tools/apps.py` — quem audita o app precisa olhar settings. (Esta spec corrige a expectativa de que o gate estaria em `apps.py`.)
- **Comandos não-seed na mesma pasta**: `backfill_*`, `fix_*`, `migrate_rbac_groups` e `populate_municipio_coords` são one-shot/legados; alguns dependem de planilhas/CSV externos (ex.: `backfill_is_online` lê coluna G da planilha original) e podem estar obsoletos após os data-fixes manuais do golden dataset. Confirmar relevância antes de rodar.
- **`seed_rbac` é pré-requisito**: várias suítes e seeds assumem grupos/permissões já criados; rodar seeds dependentes antes de `seed_rbac` falha. A sequência canônica está documentada na memória de seed order do projeto.
