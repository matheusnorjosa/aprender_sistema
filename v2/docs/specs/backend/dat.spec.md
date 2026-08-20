---
title: Módulo DAT
status: canonical
last_verified: 2026-08-20
sources_of_truth:
  - v2/backend/apps/core/services/controle_acoes_import.py
  - v2/backend/apps/core/models/dat_acao.py
  - v2/backend/apps/core/models/dat_cadastro.py
  - v2/backend/apps/core/models/dat_compra.py
  - v2/backend/apps/core/models/dat_coordenador.py
  - v2/backend/apps/core/models/dat_formacao.py
  - v2/backend/apps/core/models/dat_registro.py
  - v2/backend/apps/core/models/workflow.py
  - v2/backend/apps/core/views/dat_module.py
  - v2/backend/apps/core/views/dat.py
  - v2/backend/apps/core/views_controle_dat.py
  - v2/backend/apps/core/urls.py
  - v2/backend/apps/core/services/dat_cadastros_import.py
  - v2/backend/apps/core/rbac/matrix.py
  - v2/backend/apps/core/rbac/policies.py
owner: backend
supersedes:
  - v2/docs/_archive/SPEC_DAT_REGISTROS.md
related:
  - v2/docs/specs/backend/rbac.spec.md
  - v2/docs/API_REFERENCE.md
  - v2/docs/RBAC_NAMING.md
---

# Módulo DAT

## Propósito

O módulo DAT (Departamento de Apoio Técnico/Tecnologia) gerencia o ciclo operacional de implantação dos projetos nos municípios: o acompanhamento da chegada do projeto (ações em 4 etapas), o cadastro de turmas/cursos nas plataformas externas **FORMAR** e **AVALIAR**, as formações/treinamentos dados aos professores, as compras de materiais e o cadastro dos coordenadores responsáveis. É o "back-office" transversal que dá suporte a todos os setores de produto.

No código convivem **dois conjuntos de models** com a mesma origem de dados (planilha DAT), mas finalidades diferentes — o que segue a distinção legacy×operacional do projeto:

- **Operacional (UI/CRUD via DRF):** `DATAcao`, `DATCadastro`, `DATCompra`, `DATFormacao`, `DATCoordenador`/`DATArea`, `DATRegistro` (tabelas `core_dat_*`). É o que esta spec governa.
- **Legacy (histórico de import ETL):** `AcaoDAT` em [`workflow.py:135`](../../../backend/apps/core/models/workflow.py) (tabela `core_acao_dat`), com o enum de choices `TipoAcaoDAT` (`workflow.py:124`, `models.TextChoices` — **não é model**). Alimentado por importação por `external_hash`; não é o caminho de edição da UI nova. **`AcaoControle` foi REMOVIDO na Onda 1** (o import de ações — `POST /api/controle/import-acoes/` — grava em `DATAcao`): a tabela `core_acao_controle`, o endpoint legacy `/controle/acoes/`, o serializer e o admin foram apagados (ver [`docs/plans/PLANO_IMPORTS_ORFAOS.md`](../../plans/PLANO_IMPORTS_ORFAOS.md)).

## Fonte de verdade no código

Models operacionais (um arquivo por entidade):

- [`models/dat_acao.py`](../../../backend/apps/core/models/dat_acao.py) — `DATAcao` (ciclo de 4 etapas).
- [`models/dat_cadastro.py`](../../../backend/apps/core/models/dat_cadastro.py) — `DATCadastro` (FORMAR/AVALIAR).
- [`models/dat_compra.py`](../../../backend/apps/core/models/dat_compra.py) — `DATCompra` (materiais/estoque).
- [`models/dat_formacao.py`](../../../backend/apps/core/models/dat_formacao.py) — `DATFormacao` (formações/calendário).
- [`models/dat_coordenador.py`](../../../backend/apps/core/models/dat_coordenador.py) — `DATArea` (referência) + `DATCoordenador`.
- [`models/dat_registro.py`](../../../backend/apps/core/models/dat_registro.py) — `DATRegistro` (acompanhamento de turmas FORMAR/AVALIAR; depende de `ProjetoGeral`).

Model legacy:

- [`models/workflow.py`](../../../backend/apps/core/models/workflow.py) — `AcaoDAT` (`:135`) + o enum `TipoAcaoDAT` (`:124`).

ViewSets / Views:

- [`views/dat_module.py`](../../../backend/apps/core/views/dat_module.py) — `DATArea/DATCoordenador/DATAcao/DATCompra/DATCadastro/DATFormacao` ViewSets.
- [`views/dat.py`](../../../backend/apps/core/views/dat.py) — `DATRegistroViewSet` + `ProjetoGeralViewSet`.
- [`views_controle_dat.py`](../../../backend/apps/core/views_controle_dat.py) — `DATAcoesListCreateView` (legacy `AcaoDAT`).

Roteamento: [`urls.py`](../../../backend/apps/core/urls.py). Serviço de import legacy: [`services/dat_cadastros_import.py`](../../../backend/apps/core/services/dat_cadastros_import.py).

## Contratos e invariantes

- **Unicidade (constraints de BD, não podem ser violadas):**
  - `DATAcao`: único por `(municipio, projeto)` — `unique_dat_acao_municipio_projeto`.
  - `DATCadastro`: único por `(municipio, projeto_geral, plataforma)` — `unique_dat_cadastro_mun_proj_plat`.
  - `DATRegistro`: único por `(municipio, projeto_geral, projeto)`; `external_hash` é unique (idempotência de import).
  - `AcaoDAT` (legacy): `external_hash` unique = `SHA1(municipio_id|projeto_id|tipo_acao|responsavel_id)`.
- **Campos derivados em `DATRegistro.save()`:** `usa_avaliar` espelha `projeto_geral.usa_avaliar`; se `usa_avaliar=False`, os 3 status AVALIAR viram `nao_aplicavel`. UI/import nunca devem gravar esses campos manualmente.
- **`nr_codigos` = SOMA por linha de compra** (contrato v5, `services/dat_codigos.py`): das `DATCompra` do par `(municipio, projeto)` com `conta_para_codigos=True`, `ceil` **por compra** em Decimal, por kit (`tipo=Aluno` → `ceil(qtde/divisor_aluno)`, `tipo=Professor` → `ceil(qtde*multiplicador)`); `nao_aplicavel`/sem PG → `None`. Difere do agregado quando uma variante tem 2+ compras de professor (~29 códigos, by-design). Recalculado no `save()` do registro, nos `perform_*` do `DATCompraViewSet`, na passada final do importer (`recompute_all`) e pelo command `recalcular_nr_codigos_dat`. `nr_codigos_planilha` guarda o valor cru da planilha para reconciliação (não é autoridade). `DATCompra.tipo`/`conta_para_codigos` (migration 0087) são a base do cálculo, resolvidos pelo Tipo do SKU no export-contract.
- **Auto-status em `DATCompra.save()`** (`dat_compra.py:145-153`): `status_uso` é derivado das quantidades (`quantidade_utilizada >= quantidade` → `esgotado`; `> 0` → `em_uso`; senão `disponivel`) — sobrescrito **a cada save**, então o choice `DEVOLVIDO` (`:41`) nunca é produzido por este caminho. `disponivel` **não é campo**: é `@property` (`:135-138`, `max(0, quantidade - quantidade_utilizada)`) e portanto não é filtrável/ordenável no ORM.
- **Workflow de 4 etapas (`DATAcao`):** Carta → Contato → Reunião → Entrega. Cada etapa tem status `pendente|em_andamento|concluido|cancelado`. `progresso` e `etapa_atual` são derivados (primeira não concluída).
- **Auditoria obrigatória:** todos os models gravam `created_by` (PROTECT) e `updated_by` via `perform_create`/`perform_update`; FKs para `Municipio`/`Projeto`/`ProjetoGeral` são `PROTECT` (não deletar mestre com dependentes).
- **SEC-007:** export CSV de `DATRegistro` passa por `sanitize_csv_value` (anti CSV-injection) — `views/dat.py:202,237-252`. Não remover. (Esta cláusula **não** é a CP-08: CP-08 é `INCLUDE_DEV_TOOLS=false` em produção — ver `docs/business-rules/clausulas-petreas.md:62-66` e [dev-tools.spec](./dev-tools.spec.md).)
- **Disciplina de import (CP / memória do projeto):** o caminho de import real é via `import_export_contract` (dry-run por padrão; `--apply` exige allowlist). Re-import cego sobrescreveria data-fixes manuais — **não importar dados reais sem dry-run verde + autorização**.

## API / Interface

Rotas DRF (prefixo `/api/`, registradas em [`urls.py`](../../../backend/apps/core/urls.py)). Detalhe consolidado: [`API_REFERENCE.md`](../../API_REFERENCE.md).

| Recurso | Rota | ViewSet/View | Extras |
|---|---|---|---|
| Áreas (ref.) | `dat/areas/` | `DATAreaViewSet` (ReadOnly) | `?minimal=true` |
| Coordenadores | `dat/coordenadores/` | `DATCoordenadorViewSet` | `@action alocacoes` |
| Ações (ciclo) | `dat/acoes-ciclo/` | `DATAcaoViewSet` | `@action stats` |
| Compras/materiais | `dat/compras-materiais/` | `DATCompraViewSet` | `@action stats / dashboard / pendencias` |
| Cadastros FORMAR/AVALIAR | `dat/cadastros/` | `DATCadastroViewSet` | `@action stats / etapa` |
| Formações | `dat/formacoes/` | `DATFormacaoViewSet` | `@action stats / calendario` |
| Registros (turmas) | `dat/registros/` | `DATRegistroViewSet` | `@action export(CSV) / stats` |
| Projetos Gerais | `projetos-gerais/` | `ProjetoGeralViewSet` | `@action projetos` |
| Ações DAT (legacy) | `dat/acoes/` | `DATAcoesListCreateView` | model `AcaoDAT` |

**RBAC (idioma `permission_classes=[HasPerm("codename")]`; ver [rbac.spec](rbac.spec.md)):**

**O gate NÃO é uniforme entre os ViewSets.** Estado real (`views/dat_module.py` e `views/dat.py`):

| ViewSet | Gate padrão | `destroy` | Prova |
|---|---|---|---|
| `DATAreaViewSet` (ReadOnly) | `IsAuthenticated` — **sem capability** | — | `dat_module.py:84` |
| `DATCoordenadorViewSet` | `manage_admin_registries \| run_daily_operations` | `execute_restricted_operations` | `dat_module.py:142-151` |
| `DATAcaoViewSet` | idem | idem | `dat_module.py:249-257` |
| `DATFormacaoViewSet` | idem | idem | `dat_module.py:930-938` |
| `DATCompraViewSet` | **`CanViewComprasStats`** para tudo (list/retrieve/create/update/stats); `dashboard` → `CanViewComprasDashboard`; `pendencias` → `CanViewComprasPendencias` | `execute_restricted_operations` | `dat_module.py:387-400` |
| `DATCadastroViewSet` | só `manage_admin_registries` | `execute_restricted_operations` | `dat_module.py:756-760` |
| `DATRegistroViewSet` | só `manage_admin_registries` | `execute_restricted_operations` | `dat.py:174-185` |
| `ProjetoGeralViewSet` | `list`/`retrieve`/`projetos` → `IsAuthenticated`; resto → `manage_admin_registries` | `execute_restricted_operations` | `dat.py:351-362` |

Notas: a composition OR do #1220 vale só para Coordenador/Ação/Formação. Em Compras, a Policy `CanViewComprasStats` (#1233) governa o **CRUD inteiro**, não apenas a action `stats` — mantém paridade de capabilities com a OR anterior, mas o nome sugere escopo menor do que o real. Ver [`rbac/policies.py`](../../../backend/apps/core/rbac/policies.py) e [`rbac/matrix.py`](../../../backend/apps/core/rbac/matrix.py).

## Fluxos principais

**Ação DAT (ciclo de implantação):** cria-se `DATAcao` para `(municipio, projeto)` → preenche as 4 etapas (status + data + observação) → `progresso`/`etapa_atual` refletem o avanço → `stats` agrega por etapa/projeto/coordenador. A constraint impede duplicar a mesma dupla município/projeto. A `DATAcao` pode ser criada pela UI **ou** pelo import de ações (`POST /api/controle/import-acoes/`, dry-run por padrão) — que faz upsert pela chave natural `(municipio, projeto)`, mapeia o coordenador da origem para `DATCoordenador` (email→nome→null) e **deriva o status de cada etapa da presença da data** (tem data → concluído; senão pendente). Ver Onda 1 em [`docs/plans/PLANO_IMPORTS_ORFAOS.md`](../../plans/PLANO_IMPORTS_ORFAOS.md).

**Cadastro de plataforma:** cria-se `DATCadastro` para `(municipio, projeto_geral, plataforma)` → workflow FORMAR (Criação Curso → Chaves → Instruções → Envio) ou AVALIAR (Recebimento → Validação → Importação) → `POST {id}/etapa/` atualiza uma etapa específica (`etapa` inválida → **400**) → `progresso` por plataforma.

**Registro de turma:** cria-se `DATRegistro` → `save()` deriva `usa_avaliar`/`nr_codigos` → seções FORMAR e (condicionalmente) AVALIAR → `status_geral` = `completo | pendente_formar | pendente_avaliar` → `export/` gera CSV sanitizado.

**Formação:** cria-se `DATFormacao` (data/horário/modalidade/participantes/docs) → `calendario/` exige `data_inicio`+`data_fim` (faltando → **400**) → `taxa_presenca`/`documentacao_completa` derivados.

**Erros relevantes:** sem permissão → **403**; etapa/parâmetro inválido → **400**; violação de unicidade → **IntegrityError** (400/409).

## Decisões relacionadas (ADRs)

- Issue #1220 — Controle edita ações/formações/coordenadores DAT via `run_daily_operations` (composition OR).
- Issues #1222/#1233 (Epic 4.2.b1) — `pendencias` é operacional; `dashboard` agregado fica restrito (Diretoria); cada action mapeada para Policy nomeada de Compras.
- PR #1361 — `stats_qs = qs.order_by()` antes de `values_list().annotate(Count())` para evitar fragmentação de GROUP BY (aplicado a todos os `stats` do módulo).
- Pipeline export-contract — `dat_acao` + `plano_formacao` no importer dedicado (PR #1384, dry-run); ver [export-contract](../../../backend/apps/core/services/export_contract_importer.py).

## Testes que cobrem

- [`tests/test_dat_module.py`](../../../backend/apps/core/tests/test_dat_module.py) — models + serializers + ViewSets das 6 entidades operacionais.
- [`tests/test_dat_registros.py`](../../../backend/apps/core/tests/test_dat_registros.py) — `DATRegistro`/`ProjetoGeral` (cálculo de códigos, `usa_avaliar`, stats, export).
- [`tests/test_controle_dat_api.py`](../../../backend/apps/core/tests/test_controle_dat_api.py) — RBAC e filtros de `/api/dat/acoes/` (legacy `AcaoDAT`).
- [`tests/test_dat_tipo_acao_choices.py`](../../../backend/apps/core/tests/test_dat_tipo_acao_choices.py) — choices/normalização de `TipoAcaoDAT` + data migration `0057`.
- [`tests/test_etl_dat_cadastros.py`](../../../backend/apps/core/tests/test_etl_dat_cadastros.py) — import legacy idempotente.
- [`tests/test_dat_imports_dat_only.py`](../../../backend/apps/core/tests/test_dat_imports_dat_only.py) — escopo de import restrito a DAT.

## Pontos de atenção / dívidas conhecidas

> ⚠️ **Drift FE↔BE reconfirmado vivo em produção** (`ACHADOS_REAIS.md`, épicos #1655 e #1654). Os quatro itens abaixo descrevem o comportamento **real**, não o pretendido.

- **Datas do formulário de Registros não chegam ao banco** (`M16-07`, issue #1638). Duas falhas distintas:
  - *FORMAR* — `handleSave` (`v2/frontend/src/pages/DATModule/DATRegistrosPage.tsx:223-228`) formata **apenas** `reuniao_dat`; `chaves_inscricao_data` (`:662`), `instrucoes_data` (`:677`) e `envio_codigos_data` (`:692`) são `DatePicker` que caem no spread `...values` como objeto Dayjs e viram datetime ISO completo no JSON. O `DateField` do DRF (`models/dat_registro.py:119,124,129`) só aceita `YYYY-MM-DD` → **400**.
  - *AVALIAR* — o form usa os nomes **no singular** `alunos_recebidos_data` (`:738`), `alunos_validados_data` (`:758`), `alunos_importados_data` (`:778`), enquanto model e serializer têm `alunos_recebidos_datas` / `alunos_validados_datas` / `alunos_importados_datas` (`JSONField` de lista, `models/dat_registro.py:145,155,160`). Chave desconhecida → DRF **descarta em silêncio**, sem erro e sem gravar.
  - O serializer **não** é a causa: os 7 campos estão declarados corretamente em `serializers/dat_registro.py` (List `:51-70`, Create `:111-126`, Update `:183-198`).
- **Choices de status divergem entre UI e backend** (`M16-08`, issue #1639). Backend: `STATUS_CHOICES` tem 5 valores (`concluido, pendente, em_andamento, nao_aplicavel, erro` — `models/dat_registro.py:47-53`) e `TURMA_STATUS_CHOICES` tem 3 (`criada, pendente, erro` — `:55-59`). Frontend: `STATUS_OPTIONS` oferece 3 (`pendente, em_andamento, concluido` — `DATRegistros/constants.tsx:43-47`). Consequências: (a) `nao_aplicavel` e `erro` aparecem na legenda mas não são selecionáveis; (b) o campo `turma_formar_status` usa `STATUS_OPTIONS` (`DATRegistrosPage.tsx:630`) em vez das choices de turma — escolher "Em Andamento"/"Concluído" viola os choices do model e retorna **400**.
- **Editar pelo modal apaga as datas** (`M17-02`, issue #1641; causa raiz "list-serializer como fonte de detalhe", épico #1654). Os serializers de LIST de `DATCadastro` e `DATAcao` **não incluem** os campos `data_*` (`serializers/dat_module/dat_cadastro.py`, `.../dat_acao.py`), e `get_serializer_class` só devolve o Full fora do `list` (`views/dat_module.py:750-754` e `:243-247`). O modal é populado a partir do registro da LIST (`CadastrosPage.tsx:195-208`, `AcoesPage.tsx:210-220`), então as datas chegam `undefined` — e o `handleSave` envia **`null` explícito** para cada uma (`CadastrosPage.tsx:212-221`, `AcoesPage.tsx:224-230`). É PATCH (`api/datModule.ts:290-293`, `:172-175`), mas com `null` explícito o backend grava NULL. Resultado: uma edição de status zera as 7 datas do cadastro / 4 datas da ação.
- **O card "Importar CADASTROS DAT" alimenta o model legacy** (`M17-01`, issue #1640). `POST /api/dat/import-cadastros/` (`urls.py:225-228`, view em `views_imports.py:148`) chama `services/dat_cadastros_import.py`, que grava `AcaoDAT` (`:303,329` → tabela `core_acao_dat`), **não** `DATCadastro`. Quem lê `AcaoDAT` é apenas `GET /api/dat/acoes/` (`views_controle_dat.py:100-144`), exposto no front por `api/ops.ts:388` — função sem nenhuma página consumidora. A tela operacional "Cadastros" usa `/dat/cadastros/` (`DATCadastro`). Ou seja: o import não alimenta a tela que o operador espera.
- **Dois `DATAcao`/`AcaoDAT` coexistentes:** operacional (`core_dat_acao`, `dat/acoes-ciclo/`) vs legacy (`core_acao_dat`, `dat/acoes/`). Não confundir ao escrever queries/migrações; ver memória "Legacy vs Operational models". Docstrings dos ViewSets ainda citam as rotas antigas `/api/dat/acoes/` e `/api/dat/compras/` (`views/dat_module.py:9-10,219-225,353-358`) — as reais são `acoes-ciclo/` e `compras-materiais/`.
- **`DATCoordenador.area` é `CharField` livre**, não FK para `DATArea` (a tabela de referência existe mas não é amarrada). Divergência de grafia silenciosa é possível.
- **REGIAO_UFS duplicado:** o mapa em [`views/dat.py`](../../../backend/apps/core/views/dat.py) deve casar com `REGIAO_UFS` do frontend (`DATModule/DATRegistros/constants.tsx`); divergência quebra o filtro `regiao`.
- **Doc detalhado arquivado:** `SPEC_DAT_REGISTROS.md` está em `v2/docs/_archive/` (não atualizado com o estado atual); esta spec passa a ser o índice canônico do módulo, mas o detalhe de Registros ainda referencia o arquivo arquivado.
- **`DAT-01..DAT-04` não são IDs formais** de RD/PA/CP no código — são rótulos descritivos do escopo (workflow / registros / cadastros FORMAR-AVALIAR / coordenadores-áreas). Não citar como cláusula imutável.
