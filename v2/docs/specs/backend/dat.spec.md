---
title: Módulo DAT
status: canonical
last_verified: 2026-06-19
sources_of_truth:
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
- **Legacy (histórico de import ETL):** `AcaoDAT` + `TipoAcaoDAT` em [`workflow.py`](../../../backend/apps/core/models/workflow.py) (tabela `core_acao_dat`). Alimentado por importação por `external_hash`; não é o caminho de edição da UI nova.

## Fonte de verdade no código

Models operacionais (um arquivo por entidade):

- [`models/dat_acao.py`](../../../backend/apps/core/models/dat_acao.py) — `DATAcao` (ciclo de 4 etapas).
- [`models/dat_cadastro.py`](../../../backend/apps/core/models/dat_cadastro.py) — `DATCadastro` (FORMAR/AVALIAR).
- [`models/dat_compra.py`](../../../backend/apps/core/models/dat_compra.py) — `DATCompra` (materiais/estoque).
- [`models/dat_formacao.py`](../../../backend/apps/core/models/dat_formacao.py) — `DATFormacao` (formações/calendário).
- [`models/dat_coordenador.py`](../../../backend/apps/core/models/dat_coordenador.py) — `DATArea` (referência) + `DATCoordenador`.
- [`models/dat_registro.py`](../../../backend/apps/core/models/dat_registro.py) — `DATRegistro` (acompanhamento de turmas FORMAR/AVALIAR; depende de `ProjetoGeral`).

Model legacy:

- [`models/workflow.py`](../../../backend/apps/core/models/workflow.py) — `AcaoDAT` + `TipoAcaoDAT`.

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
- **Campos derivados em `DATRegistro.save()` (sempre recalculados):** `usa_avaliar` espelha `projeto_geral.usa_avaliar`; `nr_codigos` é calculado por `tipo_calculo_codigos` (`por_aluno` = ceil(alunos/divisor), `por_professor` = ceil(profs*mult), `nao_aplicavel` = None); se `usa_avaliar=False`, os 3 status AVALIAR viram `nao_aplicavel`. UI/import nunca devem gravar esses campos manualmente.
- **Auto-status em `DATCompra.save()`:** `status_uso` é derivado de quantidades (`>= adquirida` → `esgotado`; `> 0` → `em_uso`; senão `disponivel`). `disponivel = max(0, quantidade - quantidade_utilizada)`.
- **Workflow de 4 etapas (`DATAcao`):** Carta → Contato → Reunião → Entrega. Cada etapa tem status `pendente|em_andamento|concluido|cancelado`. `progresso` e `etapa_atual` são derivados (primeira não concluída).
- **Auditoria obrigatória:** todos os models gravam `created_by` (PROTECT) e `updated_by` via `perform_create`/`perform_update`; FKs para `Municipio`/`Projeto`/`ProjetoGeral` são `PROTECT` (não deletar mestre com dependentes).
- **CP-08 / SEC-007:** export CSV de `DATRegistro` passa por `sanitize_csv_value` (anti CSV-injection). Não remover.
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

- Leitura/escrita do CRUD operacional: `HasPerm("manage_admin_registries") | HasPerm("run_daily_operations")` (DAT + Controle/Assistente; composition OR, issue #1220).
- `destroy`: `HasPerm("execute_restricted_operations")` (Superintendência/superuser).
- Compras têm Policies dedicadas: `CanViewComprasStats` (stats), `CanViewComprasDashboard` (dashboard executivo — Diretoria), `CanViewComprasPendencias` (operacional). Ver [`rbac/policies.py`](../../../backend/apps/core/rbac/policies.py) e [`rbac/matrix.py`](../../../backend/apps/core/rbac/matrix.py).
- `DATRegistro`/`DATCadastro` usam só `manage_admin_registries` (sem `run_daily_operations`).

## Fluxos principais

**Ação DAT (ciclo de implantação):** cria-se `DATAcao` para `(municipio, projeto)` → preenche as 4 etapas (status + data + observação) → `progresso`/`etapa_atual` refletem o avanço → `stats` agrega por etapa/projeto/coordenador. A constraint impede duplicar a mesma dupla município/projeto.

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

- **Dois `DATAcao`/`AcaoDAT` coexistentes:** operacional (`core_dat_acao`, `dat/acoes-ciclo/`) vs legacy (`core_acao_dat`, `dat/acoes/`). Não confundir ao escrever queries/migrações; ver memória "Legacy vs Operational models".
- **`DATCoordenador.area` é `CharField` livre**, não FK para `DATArea` (a tabela de referência existe mas não é amarrada). Divergência de grafia silenciosa é possível.
- **REGIAO_UFS duplicado:** o mapa em [`views/dat.py`](../../../backend/apps/core/views/dat.py) deve casar com `REGIAO_UFS` do frontend (`DATModule/DATRegistros/constants.tsx`); divergência quebra o filtro `regiao`.
- **Doc detalhado arquivado:** `SPEC_DAT_REGISTROS.md` está em `v2/docs/_archive/` (não atualizado com o estado atual); esta spec passa a ser o índice canônico do módulo, mas o detalhe de Registros ainda referencia o arquivo arquivado.
- **`DAT-01..DAT-04` não são IDs formais** de RD/PA/CP no código — são rótulos descritivos do escopo (workflow / registros / cadastros FORMAR-AVALIAR / coordenadores-áreas). Não citar como cláusula imutável.
