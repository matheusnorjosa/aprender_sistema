# Contratos de Importação — `sheets.banco` → Aprender Sistema v2

Status: **PR 1 — documentação e contratos (revisada 2026-07-24 contra código real)**
Versão: 2026-07-24 v0.3
Origem: `sheets.banco` (planilha consolidada externa)
Destino: PostgreSQL (`apps.core`) via endpoints HTTP DRF (síncronos `POST /api/<recurso>/import/`) ou async (`POST /api/imports/<tipo>/` — ASQ-005 Fase 1, apenas `bloqueios` por enquanto)

> ⚠️ **Atualização v0.2 (2026-05-05)**: a versão inicial v0.1 tratou como "futuro" várias coisas que **já existem no código**. Esta versão corrige o drift, lista paths reais, e reorienta o roadmap. Ver §3.1 "Estado real do código" e §8 "Roadmap revisto".

> 🔴 **Atualização v0.3 (2026-07-24)** — varredura pós-auditoria modular M00–M28. A v0.2 errou no
> sentido oposto ao da v0.1: descreveu **garantias que o código não dá**. Corrigidos nesta versão:
> §2.1 (targets `make etl-*` não existem — ETL removido; `dry_run` desconhecido = apply),
> §2.2 (SHA-1, não SHA-256; nem todo import tem hash; reimport sobrescreve),
> §2.3 (gate não tem noção de alvo), §2.4 (**não existe `AuditLog` em import síncrono**),
> §2.6 (3 das 5 garantias eram falsas), §3.1 (resolvers escolhem em vez de rejeitar),
> §6 e §7 (paths inexistentes removidos).
> Documento vivo dos achados: [../audits/ACHADOS_REAIS.md](../audits/ACHADOS_REAIS.md).

---

## 1. Propósito

Este diretório define **contratos de importação** entre a planilha externa `sheets.banco` e o sistema Aprender Sistema v2. Cobre:

- Formato esperado das colunas em cada CSV.
- Normalizações exigidas antes do upload.
- Validações que o sistema aplica.
- Idempotência (regras de duplicidade e `external_hash`).
- Models, services e endpoints do backend envolvidos.
- O que **não** deve acontecer automaticamente (gates de revisão humana).
- Como auditar o resultado.

Esta PR (PR 1) entrega **apenas a documentação e templates fictícios**. Não cria endpoints novos, não altera models, não importa dados reais.

---

## 2. Princípios gerais (válidos para os 4 tipos)

### 2.1 Dry-run obrigatório antes de apply

Toda importação tem 2 etapas:

1. **Dry-run** — valida + retorna preview, **não persiste**.
2. **Apply** — só após dry-run sem erros bloqueantes.

> 🔴 **Corrigido em 2026-07-24**: o **ETL legado foi removido**. Nenhum target `make etl-*` existe
> (`v2/Makefile` — os únicos alvos de import são `import-compras-dry`, `import-acoes-dry`,
> `import-cadastros-dry`, `:15,56,69,82`), e não há management command `etl_*.py`
> (`apps/core/management/commands/` — ver §7).

Comandos que **existem hoje**:
- `make import-compras-dry FILE=...` → `curl POST /api/controle/import-compras/?dry_run=true` (`v2/Makefile:56-67`).
- `make import-acoes-dry FILE=...` → `POST /api/controle/import-acoes/?dry_run=true` (`v2/Makefile:69-80`).
- `make import-cadastros-dry FILE=...` → `POST /api/dat/import-cadastros/?dry_run=true` (`v2/Makefile:82-93`).
- `python manage.py import_export_contract` — dry-run por padrão, `--apply` com allowlist
  (`apps/core/management/commands/import_export_contract.py`). É o caminho canônico que substituiu o ETL.

> ✅ **`dry_run` é fail-closed** (corrigido em [#1649](https://github.com/matheusnorjosa/aprender_sistema/issues/1649),
> achado `M04-05`). O default (parâmetro ausente) **e** qualquer valor desconhecido permanecem em
> dry-run (preview); só um token de apply explícito (`false`/`0`/`no`/…) persiste. Detalhe em
> [dry_run_response_contract.md](./dry_run_response_contract.md).

### 2.2 Idempotência via `external_hash`

Onde existe hash, é **SHA-1** — nunca SHA-256. O helper canônico é
`apps/core/imports/hashing.py::stable_import_hash` (`:37-60`), e o algoritmo é **congelado por
ADR-012** (`v2/docs/adr/ADR-012-sha1-idempotency-hashes.md`): trocar quebraria os `external_hash`
já gravados em `Compra`, `Solicitacao`, `Deslocamento`, `AcaoControle`, `AcaoDAT` e `Acompanhamento`
(`apps/core/imports/hashing.py:4-11`).

⚠️ **Nem todo import usa hash.** `usuarios` reconcilia por CPF (campo unique) e `bloqueios` por
tupla natural `(usuario, inicio, fim, tipo)` — nenhum dos dois calcula `external_hash`, apesar de a
docstring de `bloqueios_import.py:4` afirmar o contrário. Tabela por service em
[dry_run_response_contract.md](./dry_run_response_contract.md) §2.

⚠️ **"Re-rodar não duplica" não significa "re-rodar não muda nada".** Três imports usam
`update_or_create` e **sobrescrevem** o registro existente: eventos (status/owner/datas —
[#1628](https://github.com/matheusnorjosa/aprender_sistema/issues/1628)), compras e ações/cadastros.
Ver §2.6.

### 2.3 RBAC — quem pode importar

Gates efetivos, lidos nas views (tabela completa em §3.1):

- `HasPerm("import_spreadsheet")` — solicitações, bloqueios, produtos, compras, ações de controle.
- `HasPerm("manage_admin_registries")` — usuários, municípios, coleções, equipe/gerência, cadastros DAT.

No seed (`apps/core/services/functional_permissions_seed.py`), **ambas** as capabilities são
atribuídas apenas ao grupo **DAT** (`:93-94`, `:97-102`). As policies públicas
`import_availability_blocks`, `import_compras` e `import_generic_spreadsheet` existem para
**exposição em `/api/me/policies/`** e não são o gate destes endpoints.

Atribuição via Django Admin (D17 — admin-driven, ratificado 2026-05-04). Não automático em deploy.
Como é admin-driven, **o conjunto real em produção depende de verificação humana** no Django Admin.

**O gate responde "pode importar?", nunca "pode importar *este alvo*?".** Não existe política
ator×alvo abrangente nos imports; o resíduo desse padrão (demais writers) é rastreado pelo épico
[#1656](https://github.com/matheusnorjosa/aprender_sistema/issues/1656). O caso concreto do import
de usuários — a coluna `grupos` concedia qualquer grupo sem gate, permitindo auto-escalação — **era**
o furo de [#1610](https://github.com/matheusnorjosa/aprender_sistema/issues/1610) e foi **corrigido**
(`ccbe1e05`): a concessão de grupos no import passou a ser gated por superuser
(`_actor_pode_atribuir_grupos`, `usuarios_import.py:273-283`) — ver [usuarios.md](./usuarios.md).

### 2.4 Audit trail — 🔴 **não existe nos imports síncronos**

Corrigido em 2026-07-24. As ações `IMPORT_USUARIOS`, `IMPORT_COMPRAS`, `IMPORT_AGENDA`,
`IMPORT_AVAILABILITY_BLOCKS` e `IMPORT_PRODUTOS_CONTROLE` **nunca existiram**.
`AuditLog.Action` (`apps/core/models/auditoria.py:72-73`) define apenas:

- `IMPORT_JOB_COMPLETED`
- `IMPORT_JOB_FAILED`

e as duas são emitidas **só** pelo caminho assíncrono (`apps/core/tasks.py:634,669`), que hoje
cobre exclusivamente `bloqueios`. Nenhuma das 10 views síncronas nem nenhum dos 11 services grava
`AuditLog`.

Consequência: **um apply síncrono não deixa rastro de quem rodou, com qual arquivo, nem do que
mudou.** É o que ainda torna #1628 silencioso. (A auto-escalação de grupos que #1610 explorava foi
**corrigida** em `ccbe1e05` — concessão gated por superuser —, mas a lacuna de auditoria do apply
síncrono permanece.)

`ImportBatch` nunca foi criado; o modelo real é `ImportJob`
([apps/core/models/import_job.py](../../backend/apps/core/models/import_job.py)).

### 2.5 Timezone

Datas de calendário (Solicitação, AvailabilityBlock) **são armazenadas em UTC** e comparadas em **`America/Fortaleza`** (RD-06). Toda data/hora vinda do CSV deve ser tratada como horário local Fortaleza antes de virar UTC.

### 2.6 Efeitos colaterais — o que é garantido e o que **não** é

> 🔴 Corrigido em 2026-07-24. A lista original afirmava cinco garantias; **três eram falsas**.
> Todas as linhas ❌ foram reconfirmadas vivas em produção pela auditoria M00–M28
> ([../audits/ACHADOS_REAIS.md](../audits/ACHADOS_REAIS.md)).

| Garantia alegada | Real | Prova |
|---|---|---|
| Nunca publica no Google Calendar | ✅ verdadeiro | nenhum service de import importa client GCal |
| Nunca cria usuário com `is_superuser=True` | ✅ verdadeiro | o campo não é entrada de `usuarios_import` |
| Nunca altera conta superuser existente | ✅ verdadeiro | `usuarios_import.py:291-300` (P0-0) |
| ~~Nunca aprova solicitações~~ | ❌ **falso** | `fluxo == NAO_SUPER` grava `status='aprovado'` **sem o hard gate de disponibilidade** — `M08-12` / [#1620](https://github.com/matheusnorjosa/aprender_sistema/issues/1620). (SUPER continua nascendo `pendente`, isso é verdade.) |
| Nunca atribui `Gerente`/`Superintendência` por ator não-superuser | ✅ **verdadeiro** (corrigido) | **era** falso — a coluna `grupos` concedia qualquer grupo sem gate; **corrigido** por `M03-01`/[#1610](https://github.com/matheusnorjosa/aprender_sistema/issues/1610) (`ccbe1e05`): concessão de grupos gated por superuser (`usuarios_import.py:273-283`, decisão `:362`, `_assign_groups:495-496`); ator não-superuser recebe `grupos_ignorados`. Resíduo ator×alvo amplo → [#1656](https://github.com/matheusnorjosa/aprender_sistema/issues/1656) |
| ~~Nunca sobrescreve sem match confirmado~~ | ❌ **falso** | o match **é** o gatilho da sobrescrita: `update_or_create` apaga status, owner e datas e reporta `unchanged` — `M10-07` / [#1628](https://github.com/matheusnorjosa/aprender_sistema/issues/1628) |
| (não alegado) Nunca resolve pessoa/município errado | ⚠️ **parcial** | `M02-09`/[#1613](https://github.com/matheusnorjosa/aprender_sistema/issues/1613) **✅ resolvido**: `resolve_projeto`/`resolve_tipo_evento` rejeitam ambiguidade (não mais `.first()`) + import DAT com norm simétrica. **Seguem abertos**: `M22-14`/[#1643](https://github.com/matheusnorjosa/aprender_sistema/issues/1643) (`resolve_user_by_name` substring de pessoa), `M15-05`/[#1635](https://github.com/matheusnorjosa/aprender_sistema/issues/1635), `M04-01`/[#1615](https://github.com/matheusnorjosa/aprender_sistema/issues/1615) — épico [#1658](https://github.com/matheusnorjosa/aprender_sistema/issues/1658) |
| (não alegado) Nunca grava linha inválida | ❌ **falso** | compras aceita quantidade vazia/negativa/decimal e data ausente — `M15-04` / [#1634](https://github.com/matheusnorjosa/aprender_sistema/issues/1634) |

Épico de causa raiz para os itens de invariante:
[#1659](https://github.com/matheusnorjosa/aprender_sistema/issues/1659) (import bypassa invariantes).

---

## 3. Tipos de importação cobertos

| Tipo | Documento | Template CSV | Backend implementado | Endpoint |
|---|---|---|---|---|
| Usuários | [usuarios.md](./usuarios.md) | [templates/usuarios.template.csv](./templates/usuarios.template.csv) | ✅ Sim | `POST /api/usuarios/import/` |
| Produtos / Controle / Compras | [produtos_controle.md](./produtos_controle.md) | [templates/produtos_controle.template.csv](./templates/produtos_controle.template.csv) | ✅ Sim | `POST /api/produtos/import/` + `POST /api/controle/import-compras/` |
| Agenda / Solicitações / Eventos | [agenda_solicitacoes.md](./agenda_solicitacoes.md) | [templates/agenda_solicitacoes.template.csv](./templates/agenda_solicitacoes.template.csv) | ✅ Sim, com PA-01 | `POST /api/solicitacoes/import/` |
| Disponibilidade / Bloqueios | [disponibilidade.md](./disponibilidade.md) | [templates/disponibilidade.template.csv](./templates/disponibilidade.template.csv) | ✅ Tipos T/P (D pendente) | `POST /api/disponibilidade/import-bloqueios/` (sync) + `POST /api/imports/bloqueios/` (async, ImportJob) |

Ordem de execução: [ordem_de_importacao.md](./ordem_de_importacao.md).

**Auditoria de shape de retorno** (PR 2, 2026-05-05): [dry_run_response_contract.md](./dry_run_response_contract.md) — análise dos 11 services + contrato padrão proposto + plano de migração em 5 fases.

---

## 3.1 Estado real do código (auditoria 2026-05-05)

Para os 4 tipos acima, o backend **já tem implementação funcional** em produção. Os contratos deste diretório descrevem o formato esperado da planilha `sheets.banco` e servem para **alinhar a geração de CSV externa com o que o backend já aceita** — não para projetar funcionalidades inexistentes.

### Services (11 já implementados em `apps/core/services/`)

| Service | Função pública | Idempotência | Dry-run |
|---|---|---|---|
| `usuarios_import.py` | `import_usuarios_from_file(path, dry_run=True)` | CPF (unique) | ✅ |
| `eventos_import.py` | `import_eventos_from_file(path, dry_run=True)` | `external_hash` + Participation M2M | ✅ |
| `bloqueios_import.py` | `import_bloqueios_from_file(path, dry_run=True)` | tupla (usuario, inicio, fim, tipo) | ✅ |
| `produtos_import.py` | `import_produtos_from_file(...)` | `Produto.codigo` | ✅ |
| `colecoes_import.py` | `import_colecoes_from_file(...)` | — | ✅ |
| `municipios_import.py` | `import_municipios_from_file(...)` | — | ✅ |
| `equipe_gerencia_import.py` | `import_equipe_gerencia_from_file(...)` | — | ✅ |
| `controle_imports.py` | `import_compras_from_file(...)` (alimenta **`Compra`**) | SHA1 `external_hash` | ✅ |
| `controle_acoes_import.py` | `import_acoes_controle(...)` | SHA1 | ✅ |
| `dat_cadastros_import.py` | `import_dat_cadastros(...)` | SHA1 | ✅ |
| `deslocamentos_import.py` | `import_deslocamentos(...)` | SHA1 | ✅ |

Helpers de reconciliação compartilhados em `apps/core/services/resolvers.py`:

- `resolve_user_by_email(email)` (`:32-53`), `resolve_user_by_name(name)` (`:56-98`).
- `resolve_municipio(nome)` (`:181-227`) — aceita `"Cidade"`, `"Cidade - UF"`, `"Cidade (UF)"`, `"Cidade/UF"`; normaliza com NFKD.
- `resolve_projeto(nome)` (`:312-369`) — aceita código ou nome; aplica `normalize_projeto_name` com aliases (IDEB→GESTÃO ESCOLAR, "Nível 1"→N1, "Vida &"→"VIDA E", etc.).
- `resolve_tipo_evento(nome)` (`:372-397`).
- `_nfkd(value)` (`:101-112`) para normalização case-insensitive sem acento.
- Texto base em `apps/core/services/normalize.py::norm_text()`.

> 🔴 **Todos estes resolvers escolhem em vez de rejeitar** (épico
> [#1658](https://github.com/matheusnorjosa/aprender_sistema/issues/1658), "resolvers por rótulo
> humano"). Dois padrões se repetem:
>
> 1. **`.first()` em ambiguidade** — `resolve_user_by_email:53`, `resolve_user_by_name:75,87,93`,
>    `resolve_municipio:208,213`, `resolve_projeto:335,340`, `resolve_tipo_evento:397`.
>    Dois registros que casam ⇒ pega um e segue, sem pendência e sem log.
> 2. **Fallback por substring** — `resolve_user_by_name:87,93` usa `first_name__icontains` /
>    `last_name__icontains`; a terceira tentativa (`:93`) é um **OR**, que casa com qualquer
>    pessoa que compartilhe um pedaço do primeiro *ou* do último nome.
>
> Efeitos já confirmados: bloqueio auto-aprovado na agenda da pessoa errada
> ([#1643](https://github.com/matheusnorjosa/aprender_sistema/issues/1643)), Gerência duplicada
> ([#1615](https://github.com/matheusnorjosa/aprender_sistema/issues/1615)), município homônimo em
> UF errada ([#1635](https://github.com/matheusnorjosa/aprender_sistema/issues/1635)).
> A correção estrutural é **rejeitar ambiguidade como pendência**, não melhorar a heurística.

### Endpoints HTTP

**Síncronos** (10 endpoints, retornam `{stats, pendencias, dry_run, file}`):

| Endpoint | View | Gate RBAC |
|---|---|---|
| `POST /api/usuarios/import/` | `ImportUsuariosView` | `HasPerm("manage_admin_registries")` |
| `POST /api/solicitacoes/import/` | `ImportEventosView` | `HasPerm("import_spreadsheet")` |
| `POST /api/disponibilidade/import-bloqueios/` | `ImportBloqueiosView` | `HasPerm("import_spreadsheet")` |
| `POST /api/produtos/import/` | `ImportProdutosView` | `HasPerm("import_spreadsheet")` |
| `POST /api/municipios/import/` | `ImportMunicipiosView` | `HasPerm("manage_admin_registries")` |
| `POST /api/colecoes/import/` | `ImportColecoesView` | `HasPerm("manage_admin_registries")` |
| `POST /api/equipe-gerencia/import/` | `ImportEquipeGerenciaView` | `HasPerm("manage_admin_registries")` |
| `POST /api/controle/import-compras/` | `ImportComprasView` | `HasPerm("import_spreadsheet")` |
| `POST /api/controle/import-acoes/` | `ControleImportAcoesView` | `HasPerm("import_spreadsheet")` |
| `POST /api/dat/import-cadastros/` | `DATImportCadastrosView` | `HasPerm("manage_admin_registries")` |

Todos aceitam `?dry_run=true|false` (default `true`). O parse é **fail-closed** (§2.1, #1649): valor desconhecido permanece em dry-run (preview); só `false`/`0`/`no`/… aplicam.

> ⚠️ **`POST /api/dat/import-cadastros/` grava `AcaoDAT`, que nenhuma tela lê.** O card "Importar
> CADASTROS DAT" do frontend chama este endpoint (`v2/frontend/src/api/ops.ts:253`), e o service
> `dat_cadastros_import.py` alimenta o model **`AcaoDAT`** (legacy). Mas a tela de Cadastros
> (`v2/frontend/src/pages/DATModule/CadastrosPage.tsx:49-58`) lê `/dat/cadastros/`
> (`v2/frontend/src/api/datModule.ts:275-277`) — outro model, outro workflow (FORMAR/AVALIAR).
> A única função de frontend que consome `/dat/acoes/` é `listCadastros` em
> `v2/frontend/src/api/ops.ts:387-391`, **que nenhuma página importa** (é sombreada pela homônima
> de `datModule.ts`). Resultado: o operador importa, recebe 200, e o dado some de vista.
> Achado `M17-01`, issue [#1640](https://github.com/matheusnorjosa/aprender_sistema/issues/1640).

> ⚠️ **`POST /api/equipe-gerencia/import/` pode criar Gerência duplicada.**
> `_get_or_create_gerencia` (`apps/core/services/equipe_gerencia_import.py:248-278`) tenta três
> lookups (`nome_setor__iexact`, `nome__iexact` do setor, `nome__iexact` do nome gerado) e, se
> nenhum casar, cria com o nome derivado de `_generate_gerencia_nome`. Variações de rótulo humano
> na planilha geram gerências novas em vez de reaproveitar a existente.
> Achado `M04-01`, issue [#1615](https://github.com/matheusnorjosa/aprender_sistema/issues/1615).

**Assíncronos (ASQ-005 Fase 1)** — apenas `bloqueios` por enquanto:

- `POST /api/imports/bloqueios/` — cria `ImportJob` + dispatcha Celery task; retorna `202 Accepted` com `job_id`.
- `GET /api/imports/<id>/` — status + stats + pendencias do job.
- `GET /api/imports/` — lista jobs do usuário (filtros `type=`, `status=`).

### Model `ImportJob` ([apps/core/models/import_job.py](../../backend/apps/core/models/import_job.py))

Modelo de rastreabilidade de execuções async. Campos:

- `user` (FK Usuario, PROTECT), `import_type` (TextChoices — hoje só `BLOQUEIOS`), `status` (QUEUED|RUNNING|SUCCESS|FAILED).
- `file` (FileField em `imports/%Y/%m/%d/`), `original_filename`.
- `dry_run` (Boolean), `stats` (JSON), `pendencias` (JSON).
- `error_message` (≤500c), `error_traceback` (não exposto via API).
- `celery_task_id`, `duration_ms`, timestamps + métodos `mark_running/success/failed`.

Comentário do código: **"Fase 2 migrará USUARIOS, COMPRAS, ACOES, DESLOCAMENTOS, EVENTOS, PRODUTOS, MUNICIPIOS, COLECOES, EQUIPE_GERENCIA"** — esse é o backlog real.

### Frontend (3 páginas confirmadas; mais provavelmente)

- `v2/frontend/src/pages/DAT/ImportacoesPage.tsx` — hub `/dat/importacoes`.
- `v2/frontend/src/pages/AdminDAT/ColecoesImportPage.tsx`.
- `v2/frontend/src/pages/AdminDAT/EquipeGerenciaImportPage.tsx`.
- Páginas adjacentes de cadastro AdminDAT (Usuarios, Municipios, Produtos, Projetos, Grupos, Setores, Funcoes, Gerencias) — gerenciam CRUD, **não confirmado** se cada uma tem botão de upload de planilha.

### Makefile (chama endpoints HTTP via curl)

Targets atuais em `v2/Makefile:15,56,69,82` (`import-compras-dry`, `import-acoes-dry`,
`import-cadastros-dry`) **chamam `curl` para `/api/<recurso>/import/?dry_run=true`**.
**Não** existem management commands `etl_*.py` — o ETL legado foi removido. O único management
command de import é `import_export_contract.py`. Qualquer referência a `make etl-*` em outros docs
do projeto é histórica e **não funciona**.

---

## 4. Convenções dos templates CSV

- **Encoding**: UTF-8 (sem BOM).
- **Separador**: `,` (vírgula).
- **Quote**: aspas duplas em campos com vírgula/espaço/linha.
- **Decimal**: ponto (`12.50`, não `12,50`).
- **Data**: `dd/mm/yyyy` (BR) — normalizada para ISO no service.
- **Hora**: `HH:MM` (24h).
- **Boolean** (quando aplicável): `sim`/`não`, `true`/`false`, `1`/`0`.
- **CPF**: 11 dígitos sem máscara (vai ser normalizado).
- **Telefone**: dígitos puros ou com máscara — será normalizado.
- **Cabeçalho**: snake_case ou nomes da planilha original (documento explicita por tipo).

Todos os templates contêm **uma linha fictícia** com CPF `00000000000` e email `*.exemplo@example.com` — **não usar como dado real**.

---

## 5. Como propor mudanças de contrato

1. Editar o markdown do tipo afetado nesta pasta.
2. Atualizar o template CSV correspondente.
3. Documentar a mudança em "Histórico de versões" do próprio arquivo.
4. PR com label `documentation` + revisão obrigatória do dono da etapa.
5. Após merge, atualizar service correspondente (PR separada).

Mudanças que quebram contrato (renomear coluna obrigatória, mudar tipo de dado, mudar regra de hash) exigem deprecation period: aceitar formato antigo por 1 release com warning, derrubar no seguinte.

---

## 6. Pendências cross-cutting (para Matheus)

> 🔴 **Fila real de correção** — os itens ainda abertos abaixo são achados vivos em produção, não
> pendências de design. Detalhe e evidência em [../audits/ACHADOS_REAIS.md](../audits/ACHADOS_REAIS.md).

1. ✅ **Gate de concessão de grupos no import de usuários** — **feito**
   ([#1610](https://github.com/matheusnorjosa/aprender_sistema/issues/1610), `ccbe1e05`): a concessão
   de grupos no import passou a ser gated por superuser (`_actor_pode_atribuir_grupos`,
   `usuarios_import.py:273-283`; decisão `:362`; `_assign_groups:495-496`) — ator não-superuser recebe
   `grupos_ignorados`; o importer export-contract concede apenas a allowlist `ALLOWED_USER_GROUPS`
   (`export_contract_importer.py:1077-1082`). Resíduo: política ator×alvo abrangente nos demais
   writers → épico [#1656](https://github.com/matheusnorjosa/aprender_sistema/issues/1656).
2. **Resolvers devem rejeitar ambiguidade em vez de escolher com `.first()`** — épico
   [#1658](https://github.com/matheusnorjosa/aprender_sistema/issues/1658)
   (✅ #1613 feito p/ `resolve_projeto`/`resolve_tipo_evento`; #1615, #1635, #1643 abertos). Inclui a pergunta antiga: qual chave usar para Formador 1..5 na
   planilha de Agenda, já que CPF não aparece lá.
3. **Import não pode bypassar invariante de domínio** — épico
   [#1659](https://github.com/matheusnorjosa/aprender_sistema/issues/1659) (#1620, #1628, #1634, #1640).
4. ✅ **`dry_run` fail-closed** ([#1649](https://github.com/matheusnorjosa/aprender_sistema/issues/1649)) — **feito** (2026-08-25, helper `parse_dry_run`).
   Resta a **auditoria do apply** (§2.4).
5. **Mapeamento Cargo → Função RBAC**: `usuarios.md` propõe tabela; **não implementado**. Falta
   confirmar os termos reais da planilha antes de decidir se vale implementar.
6. **Disponibilidade**: tipo `D` e recorrência continuam sem contrato — ver
   [disponibilidade.md](./disponibilidade.md) §14.
7. **Decisão D17 e Imports**: imports não devem atribuir capabilities (admin-driven). ✅ Confirmado
   — nenhum service de import toca `PermissaoFuncional`; o import de usuários mexe em `Group`, mas
   essa concessão passou a ser gated por superuser (#1610, `ccbe1e05`), fechando a auto-escalação
   que **era** o problema. `seed_rbac` é um command de `apps/dev_tools`, manual, fora do pipeline de
   import.

---

## 7. Referências internas

- [../audits/ACHADOS_REAIS.md](../audits/ACHADOS_REAIS.md) — **documento vivo** dos achados da auditoria M00–M28.
- [../RBAC_NAMING.md](../RBAC_NAMING.md) — convenção RBAC.
- [../IMPLEMENTACAO_PA.md](../IMPLEMENTACAO_PA.md) — política de aprovação (PA-01..07).
- [../GUIDE_AVAILABILITY.md](../GUIDE_AVAILABILITY.md) — grade mensal e bloqueios.
- [../GUIDE_GCAL.md](../GUIDE_GCAL.md) — integração GCal.
- [../adr/ADR-012-sha1-idempotency-hashes.md](../adr/ADR-012-sha1-idempotency-hashes.md) — SHA-1 congelado.
- `apps/core/imports/hashing.py` — `stable_import_hash`, helper canônico de `external_hash`.
- `apps/core/services/resolvers.py` — resolvers compartilhados (ver aviso em §3.1).
- `apps/core/management/commands/import_export_contract.py` — command canônico (dry-run + `--apply`).

*(Removidas em 2026-07-24: `v2/docs/MAPEAMENTO_COMPLETO_SETORES_GERENCIAS.md`, que não existe, e
`apps/core/management/commands/etl_*.py`, que não existem — ETL legado removido. O SSOT de
Setor/Função é `apps/core/constants.py:16-45`.)*

---

## 8. Roadmap das próximas PRs (revisto 2026-05-05)

> ⚠️ O roadmap anterior (v0.1) propunha "criar do zero" coisas que já existem. Esta versão alinha o backlog ao código real.

| PR | Escopo | Justificativa | Risco |
|---|---|---|---|
| PR 1 | Documentação e contratos + templates (este PR, revisado) | Alinhar `sheets.banco` com formato aceito hoje | Nenhum (docs-only) |
| PR 2 | **Auditar e padronizar shape de retorno de dry-run** nos 11 services existentes | Cada service hoje retorna estrutura ligeiramente diferente (`stats/pendencias`, `relatório`, `created_ids`, etc.); contrato único facilita frontend e testes | Baixo (não muda comportamento) |
| PR 3 | **Consolidar helpers de normalização** em `apps/core/imports/normalization.py` extraindo o que já existe em `services/resolvers.py` + `services/normalize.py` | Hoje há helpers úteis (`resolve_municipio`, `resolve_projeto`, `_nfkd`, `norm_text`) mas falta `normalize_cpf`, `normalize_phone`, `parse_br_date`, `parse_bool_ptbr`, `build_import_hash` como API pública | Baixo (refactor) |
| PR 4 | **Migrar 9 imports síncronos restantes para `ImportJob` async** (ASQ-005 Fase 2) — usuários, compras, ações, deslocamentos, eventos, produtos, municípios, coleções, equipe_gerencia. Um tipo por sub-PR | Padroniza upload + rastreabilidade; já há infra pronta para `bloqueios` | Médio (Celery + auditoria) |
| PR 5 | **Adicionar botões "Baixar template"** nas páginas de import existentes (`ImportacoesPage.tsx`, `ColecoesImportPage.tsx`, `EquipeGerenciaImportPage.tsx`, e demais que aceitem upload) — apontando para `v2/docs/imports/templates/*.csv` | UX: hoje **não confirmado** se algum botão existe | Baixo (frontend simples) |
| PR 6 (talvez desnecessária) | Reforçar **validadores específicos** apenas se PR 2 identificar lacuna | Cada service já tem suas validações; provavelmente bastam ajustes pontuais | A definir após PR 2 |

### Ordem sugerida

1. **PR 2** (auditar shape de retorno) — barata, esclarece estado real.
2. **PR 3** (consolidar normalizadores) — refactor seguro com testes.
3. **PR 5** (botões de template) — paralelizável com 2 e 3.
4. **PR 4** (migração async, 1 tipo por sub-PR) — depende de PR 2 estabilizar contrato.
5. **PR 6** só se PR 2 expuser regras divergentes.

### Coisas que **NÃO** precisam virar PR

- Criar `ImportBatch` (já existe `ImportJob`).
- Criar dry-run (todos os services já implementam).
- Criar services `*_import.py` (11 já existem).
- Criar endpoints (10 síncronos + 3 async já existem).
- Criar `normalize_text_key`, `resolve_municipio`, `resolve_projeto` (já existem em `resolvers.py`/`normalize.py`).
