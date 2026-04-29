# Inventário de Importações — Aprender Sistema v2

**Gerado em**: 2026-04-29
**Branch**: `main`
**HEAD**: `8e9e017b76a417e6baaef33ec882b39f6af50aab`
**Escopo**: read-only — mapeamento estático do estado atual (frontend + backend).

> Pós-PR #1298 (municípios IBGE) e PR #1299 (D9 transversal): `view_all_availability`
> está em Controle + DAT (não mais Gerente). Mapping confirmado em
> `apps/core/services/functional_permissions_seed.py` linhas 147–161.

---

## 1. Tabela completa

Todos os endpoints abaixo aceitam `?dry_run=true|false` e payload `multipart/form-data` (campo `file`). Permissions backend são compostas por `IsAuthenticated` + Policy. As Policy classes vivem em `v2/backend/apps/core/rbac/policies.py`. As capabilities elegíveis vêm de `apps/core/rbac/policies.py::ACCESS_POLICIES` e os grupos atribuídos vêm de `apps/core/services/functional_permissions_seed.py`.

| # | Importação | Módulo atual (rota) | Página/rota atual | Componente frontend | Endpoint backend | Método | Permission backend | Capability/policy elegível | Quem acessa hoje | Observações |
|---|------------|---------------------|--------------------|----------------------|-------------------|--------|--------------------|----------------------------|------------------|-------------|
| 1 | Compras | **Duplicado** (Controle, AdminDAT/DATModule) | `/controle` (ControlePage.tsx, ImportUploader linhas 110-118) **e** `/controle/compras`, `/compras-materiais`, `/dat/compras-materiais` (DATModule/ComprasPage.tsx, ImportUploader linhas 739-747) | `ImportUploader` em ambas | `POST /api/controle/import-compras/` (alias: `POST /api/import-compras/`) | POST | `[CanImportCompras]` | `import_compras` = `import_spreadsheet \| manage_purchases_and_materials \| run_daily_operations` | DAT, Controle (+ superuser) | View: `ImportComprasView` em `views_controle_imports.py:77`. Note que `permission_classes` aqui é apenas `[CanImportCompras]` (sem `IsAuthenticated` explícito; o policy já requer auth). |
| 2 | Ações (Controle) | **Duplicado** (Controle, DATModule) | `/controle` (ControlePage.tsx linhas 122-127) **e** `/controle/compras`, `/compras-materiais`, `/dat/compras-materiais` (DATModule/ComprasPage.tsx linhas 750-755) | `ImportUploader` em ambas | `POST /api/controle/import-acoes/` | POST | `[IsAuthenticated, CanImportGenericSpreadsheet]` | `import_generic_spreadsheet` = `import_spreadsheet \| run_daily_operations` | DAT, Controle (+ superuser) | View: `ControleImportAcoesView` em `views_imports.py:77`. |
| 3 | Cadastros DAT | DAT | `/dat/importacao` (DAT/DATPage.tsx linhas 90-99) | `ImportUploader` | `POST /api/dat/import-cadastros/` | POST | `[IsAuthenticated, HasPerm("manage_admin_registries")]` | capability `manage_admin_registries` (single-cap; existe Policy `CanManageAdminRegistries` mas a view usa `HasPerm` direto) | DAT (+ superuser) | View: `DATImportCadastrosView` em `views_imports.py:173`. Único import com sidebar key `dat-importacao`. |
| 4 | Bloqueios (AvailabilityBlock) | Outro (Disponibilidade/Solicitações) | `/disponibilidade`, `/solicitacoes/disponibilidade` (Disponibilidade.tsx linhas 190-198) | `ImportUploader` | `POST /api/disponibilidade/import-bloqueios/` | POST | `[IsAuthenticated, CanImportAvailabilityBlocks]` | `import_availability_blocks` = `import_spreadsheet \| view_all_availability` | DAT, Controle (+ superuser). _Comentário no view sugere "Controle/Gerente/Coord/Apoio", mas seed atual só atribui `view_all_availability` a Controle e DAT_ | View: `ImportBloqueiosView` em `views_import_bloqueios.py:71`. Também exposto via async `POST /api/imports/bloqueios/` (ASQ-005, `views/imports.py`). |
| 5 | Deslocamentos | Outro (Solicitações/Deslocamentos) | `/solicitacoes/deslocamentos` (Deslocamentos/DeslocamentosPage.tsx linhas 607-614) | `ImportUploader` | `POST /api/deslocamentos/import/` | POST | `[IsAuthenticated, CanImportGenericSpreadsheet]` | `import_generic_spreadsheet` = `import_spreadsheet \| run_daily_operations` | DAT, Controle (+ superuser) | View: `ImportDeslocamentosView` em `views_import_deslocamentos.py:68`. |
| 6 | Eventos (Solicitação) | **Duplicado** (Controle, DATModule) | `/controle` (ControlePage.tsx linhas 130-135) **e** `/controle/compras`, `/compras-materiais`, `/dat/compras-materiais` (DATModule/ComprasPage.tsx linhas 757-762) | `ImportUploader` em ambas | `POST /api/solicitacoes/import/` | POST | `[IsAuthenticated, CanImportGenericSpreadsheet]` | `import_generic_spreadsheet` = `import_spreadsheet \| run_daily_operations` | DAT, Controle (+ superuser) | View: `ImportEventosView` em `views_import_eventos.py:76`. |
| 7 | Usuários | AdminDAT | `/dat/admin/usuarios` (AdminDAT/UsuariosPage.tsx linhas 550-558) | `ImportUploader` (embutido na página de cadastro) | `POST /api/usuarios/import/` | POST | `[IsAuthenticated, HasPerm("manage_admin_registries")]` | capability `manage_admin_registries` (single-cap) | DAT (+ superuser) | View: `ImportUsuariosView` em `views_import_usuarios.py:67`. Sem entrada própria no sidebar (acessado via página de cadastro). |
| 8 | Municípios | AdminDAT | `/dat/admin/municipios` (AdminDAT/MunicipiosPage.tsx linhas 423-428) | `ImportUploader` (embutido na página de cadastro) | `POST /api/municipios/import/` | POST | `[IsAuthenticated, HasPerm("manage_admin_registries")]` | capability `manage_admin_registries` (single-cap) | DAT (+ superuser) | View: `ImportMunicipiosView` em `views_import_municipios.py:55`. PR #1298 (mergeado) trata da pipeline IBGE — fora do escopo deste inventário. Sem entrada própria no sidebar. |
| 9 | Coleções | AdminDAT | `/dat/admin/colecoes` (AdminDAT/ColecoesImportPage.tsx linhas 49-54) | `ImportUploader` | `POST /api/colecoes/import/` | POST | `[IsAuthenticated, HasPerm("manage_admin_registries")]` | capability `manage_admin_registries` (single-cap) | DAT (+ superuser) | View: `ImportColecoesView` em `views_import_colecoes.py:55`. Sidebar: "Importar Coleções". |
| 10 | Equipe-Gerência | AdminDAT | `/dat/admin/equipe-gerencia` (AdminDAT/EquipeGerenciaImportPage.tsx linhas 50-55) | `ImportUploader` | `POST /api/equipe-gerencia/import/` | POST | `[IsAuthenticated, HasPerm("manage_admin_registries")]` | capability `manage_admin_registries` (single-cap) | DAT (+ superuser) | View: `ImportEquipeGerenciaView` em `views_import_equipe_gerencia.py:55`. Sidebar: "Importar Vínculos". |
| 11 | Produtos | **Duplicado** (Controle, DATModule) | `/controle` (ControlePage.tsx linhas 138-143) **e** `/controle/compras`, `/compras-materiais`, `/dat/compras-materiais` (DATModule/ComprasPage.tsx linhas 764-769) | `ImportUploader` em ambas | `POST /api/produtos/import/` | POST | `[IsAuthenticated, CanImportGenericSpreadsheet]` | `import_generic_spreadsheet` = `import_spreadsheet \| run_daily_operations` | DAT, Controle (+ superuser) | View: `ImportProdutosView` em `views_import_produtos.py:69`. Comentário no view: "import operacional aceita Controle (run_daily_operations) ou DAT (import_spreadsheet)". |
| 12 | (Async) Bloqueios via ImportJob | Backend-only (não há botão FE dedicado) | n/a | nenhum | `POST /api/imports/bloqueios/` | POST | (ASQ-005 infra; ver `views/imports.py`) | (job-based) | n/a no FE | View: `ImportJobBloqueiosUploadView`. Endpoints relacionados: `GET /api/imports/`, `GET /api/imports/<id>/`. Phase 2 (FE polling + 9 imports async) ainda aberta em #778 — hoje frontend ainda usa endpoints síncronos da linha 4. |

---

## 2. Resumo

- **Total de importações distintas (FE)**: 11 (sem contar duplicações de UI; `importCompras`, `importAcoes`, `importEventos`, `importProdutos` aparecem em duas páginas cada).
- **Total de funções `import*` em `api/ops.ts`**: 11 (`importCompras`, `importAcoes`, `importCadastros`, `importBloqueios`, `importDeslocamentos`, `importEventos`, `importUsuarios`, `importMunicipios`, `importColecoes`, `importEquipeGerencia`, `importProdutos`).
- **Total de endpoints síncronos FE-facing**: 11 paths em `apps/core/urls.py` (linhas 198-267) + 1 alias (`/api/import-compras/`, linha 204) usado apenas em testes RBAC.
- **Endpoints async (ASQ-005)**: 1 upload (`/api/imports/bloqueios/`) + 2 leitura (`/api/imports/`, `/api/imports/<id>/`).

### Por módulo (rota onde o botão hoje vive)

- **DAT** (`/dat/*`): 1 (Cadastros DAT em `/dat/importacao`).
- **AdminDAT** (`/dat/admin/*`): 4 (Usuários, Municípios, Coleções, Equipe-Gerência).
- **Controle** (`/controle*`): 4 (Compras, Ações, Eventos, Produtos) — todos também aparecem em DATModule.
- **Outro**:
  - Bloqueios em `/disponibilidade` e `/solicitacoes/disponibilidade` (Disponibilidade.tsx).
  - Deslocamentos em `/solicitacoes/deslocamentos` (DeslocamentosPage.tsx).
- **Duplicado** (mesmo `import*` chamado em ≥2 páginas):
  - `importCompras` → `Controle/ControlePage.tsx` **+** `DATModule/ComprasPage.tsx`.
  - `importAcoes` → `Controle/ControlePage.tsx` **+** `DATModule/ComprasPage.tsx`.
  - `importEventos` → `Controle/ControlePage.tsx` **+** `DATModule/ComprasPage.tsx`.
  - `importProdutos` → `Controle/ControlePage.tsx` **+** `DATModule/ComprasPage.tsx`.
  - (`DATModule/ComprasPage.tsx` é o componente lazy `DATComprasPage` mapeado em **3 rotas**: `/controle/compras`, `/compras-materiais`, `/dat/compras-materiais`.)

### Endpoints sem botão frontend dedicado

- `POST /api/imports/bloqueios/` (async) — endpoint backend está pronto (`ImportJobBloqueiosUploadView`), mas hoje a UI ainda fala com `POST /api/disponibilidade/import-bloqueios/` (síncrono). Phase 2 do ASQ-005 (#778) trataria a migração FE.
- `GET /api/imports/`, `GET /api/imports/<id>/` — sem consumidor frontend identificado.
- `POST /api/import-compras/` — alias declarado em `urls.py:204` apenas para `test_rbac_seed.py`. Sem caller frontend.

### Botões frontend chamando endpoint inexistente

- Nenhum encontrado. Cada função `import*` em `ops.ts` casa 1:1 com um path em `apps/core/urls.py`.

### Importações usando `CanImportGenericSpreadsheet`

- Ações (`/api/controle/import-acoes/`) — `views_imports.py:77`.
- Eventos (`/api/solicitacoes/import/`) — `views_import_eventos.py:76`.
- Deslocamentos (`/api/deslocamentos/import/`) — `views_import_deslocamentos.py:68`.
- Produtos (`/api/produtos/import/`) — `views_import_produtos.py:69`.

### Importações NÃO protegidas por DAT/superuser hoje

Todas as importações exigem ou DAT ou Controle (+ superuser bypass). Não há nenhum endpoint de import com `[IsAuthenticated]` puro nem com permissão a roles fora desse par. Ranking de "amplitude":

- **Mais amplo (DAT + Controle)**: Compras, Ações, Eventos, Produtos, Deslocamentos, Bloqueios.
- **Mais restrito (DAT only)**: Cadastros DAT, Usuários, Municípios, Coleções, Equipe-Gerência.

---

## 3. Pontos de atenção (sem corrigir)

1. **Importações fora do menu "DAT"**: Compras, Ações, Eventos, Produtos hoje têm botão em `/controle` (ControlePage.tsx) — coerente com a permission `import_generic_spreadsheet | import_compras` que liga DAT+Controle, mas há sobreposição visual com a mesma UI em `/controle/compras` (DATModule/ComprasPage.tsx). Bloqueios e Deslocamentos ficam fora tanto de Controle quanto de DAT (estão em `/disponibilidade` e `/solicitacoes/deslocamentos`).
2. **Duplicação 4× de UI**: ControlePage.tsx (linhas 110-143) e DATModule/ComprasPage.tsx (linhas 739-769) renderizam **as mesmas 4 importações** (Compras, Ações, Eventos, Produtos). DATModule/ComprasPage.tsx ainda é re-mapeado em **3 rotas** (`/controle/compras`, `/compras-materiais`, `/dat/compras-materiais`), multiplicando o ponto de entrada visual.
3. **`manage_admin_registries` é single-cap mas a view usa `HasPerm` direto, não a Policy**: Existe `CanManageAdminRegistries` em `policies.py:251`, mas todas as 5 views que protegem registros administrativos (Cadastros DAT, Usuários, Municípios, Coleções, Equipe-Gerência) usam `HasPerm("manage_admin_registries")`. Não é bug — é apenas idioma misto entre Policy class e HasPerm direto para o mesmo predicado.
4. **`ImportComprasView` quebra padrão de `permission_classes`**: É a única que usa `permission_classes = [CanImportCompras]` sem incluir `IsAuthenticated` explícito (`views_controle_imports.py:77`). Funcionalmente equivalente porque o policy bloqueia anônimos, mas diverge dos outros 10 views.
5. **Comentário desatualizado em `views_import_bloqueios.py:68-70`**: O comentário diz "função operacional de gestão de availability (Controle/Gerente/Coord/Apoio)", mas a policy `import_availability_blocks` resolve (via seed atual) apenas para **Controle + DAT** — Gerente, Coordenador e Apoio não têm `view_all_availability` nem `import_spreadsheet` desde a Onda 1 / D9. O texto não reflete o seed.
6. **Endpoint async existe mas FE não consome**: `POST /api/imports/bloqueios/` (ASQ-005 Phase 1 entregue em #1162) está plumbed no backend e tem testes de integração (`test_import_job_integration.py`), mas nenhum chamador frontend. Phase 2 (#778) é o trabalho restante para mover o FE para o modelo job-based.
7. **Path divergente entre Compras vs resto**: Padrão dominante é `/<dominio>/import/` (deslocamentos, solicitacoes, usuarios, produtos, municipios, colecoes, equipe-gerencia). Compras usa `/controle/import-compras/` (não `/controle/compras/import/`), Ações usa `/controle/import-acoes/`, Cadastros DAT usa `/dat/import-cadastros/`, Bloqueios usa `/disponibilidade/import-bloqueios/`. Endpoint alias `/api/import-compras/` (linha 204) declarado apenas para teste RBAC.
8. **Registros de Turmas (DAT/registros)**: Sidebar tem `dat-registros` apontando para `/dat/registros` mas **não existe** import correspondente — é página de listagem, não importação. (Mantido fora do inventário, conforme instrução.)
9. **Municípios IBGE pipeline (#1298)**: Já mergeado. Inventário lista `importMunicipios` apenas como item #8; pipeline IBGE não é reorganização de importação (é qualidade de dados).

---

## 4. Fontes consultadas

### Frontend

- `v2/frontend/src/api/ops.ts` (linhas 1-293) — todas as 11 funções `import*` + `postMultipart` helper.
- `v2/frontend/src/components/ImportUploader.tsx:67-76` — componente reutilizado.
- `v2/frontend/src/components/AppRoutes.tsx:115-167` — rotas e gates `canDAT`, `canControle`, `canCoordenador`, `canDisponibilidade`, `access.can('view_all_availability')`.
- `v2/frontend/src/components/AppSidebar.tsx:26-96` (mappings) e linhas 322-374 (render do menu DAT, Controle, Solicitações, Disponibilidade, Deslocamentos).
- `v2/frontend/src/hooks/usePermissions.ts:93-122` — definição de `canDAT`, `canControle`, `canCoordenador`, `canDisponibilidade`.
- `v2/frontend/src/pages/Controle/ControlePage.tsx:12, 14-15, 110-143`.
- `v2/frontend/src/pages/DATModule/ComprasPage.tsx:54-63, 739-769`.
- `v2/frontend/src/pages/DAT/DATPage.tsx:10-11, 90-99`.
- `v2/frontend/src/pages/Disponibilidade.tsx:17-19, 190-198`.
- `v2/frontend/src/pages/Deslocamentos/DeslocamentosPage.tsx:53-54, 607-614`.
- `v2/frontend/src/pages/AdminDAT/UsuariosPage.tsx:38, 40-41, 550-558`.
- `v2/frontend/src/pages/AdminDAT/MunicipiosPage.tsx:22-24, 423-428`.
- `v2/frontend/src/pages/AdminDAT/ColecoesImportPage.tsx:8-10, 49-54`.
- `v2/frontend/src/pages/AdminDAT/EquipeGerenciaImportPage.tsx:8-10, 50-55`.

### Backend

- `v2/backend/apps/core/urls.py:198-283` — declaração dos 11 paths síncronos + 1 alias + 3 paths async (ASQ-005).
- `v2/backend/apps/core/views_controle_imports.py:74-77` — `ImportComprasView` (`CanImportCompras`).
- `v2/backend/apps/core/views_imports.py:77, 173` — `ControleImportAcoesView` (`CanImportGenericSpreadsheet`), `DATImportCadastrosView` (`HasPerm("manage_admin_registries")`).
- `v2/backend/apps/core/views_import_bloqueios.py:67-71` — `ImportBloqueiosView` (`CanImportAvailabilityBlocks`).
- `v2/backend/apps/core/views_import_deslocamentos.py:67-68` — `ImportDeslocamentosView` (`CanImportGenericSpreadsheet`).
- `v2/backend/apps/core/views_import_eventos.py:75-76` — `ImportEventosView` (`CanImportGenericSpreadsheet`).
- `v2/backend/apps/core/views_import_usuarios.py:67` — `ImportUsuariosView` (`HasPerm("manage_admin_registries")`).
- `v2/backend/apps/core/views_import_municipios.py:55` — `ImportMunicipiosView` (`HasPerm("manage_admin_registries")`).
- `v2/backend/apps/core/views_import_colecoes.py:55` — `ImportColecoesView` (`HasPerm("manage_admin_registries")`).
- `v2/backend/apps/core/views_import_equipe_gerencia.py:55` — `ImportEquipeGerenciaView` (`HasPerm("manage_admin_registries")`).
- `v2/backend/apps/core/views_import_produtos.py:68-69` — `ImportProdutosView` (`CanImportGenericSpreadsheet`).
- `v2/backend/apps/core/views/imports.py:1-200+` — ASQ-005 async (`ImportJobBloqueiosUploadView`, `ImportJobListView`, `ImportJobDetailView`).
- `v2/backend/apps/core/rbac/policies.py:118-136` — `ACCESS_POLICIES` mapping (`import_availability_blocks`, `import_compras`, `import_generic_spreadsheet`, `manage_admin_registries`).
- `v2/backend/apps/core/rbac/policies.py:239-252` — classes `CanImportAvailabilityBlocks`, `CanImportCompras`, `CanImportGenericSpreadsheet`, `CanManageAdminRegistries`.
- `v2/backend/apps/core/rbac/policies.py:294-300` — `PUBLIC_POLICY_KEYS` (inclui as 3 keys de import + `manage_admin_registries`).
- `v2/backend/apps/core/services/functional_permissions_seed.py:65-160` — capabilities `import_spreadsheet` (DAT), `manage_admin_registries` (DAT), `manage_purchases_and_materials` (DAT, Controle), `run_daily_operations` (Controle), `view_all_availability` (Controle, DAT).
- `v2/backend/apps/core/services/`: arquivos de serviço `bloqueios_import.py`, `colecoes_import.py`, `controle_acoes_import.py`, `controle_imports.py`, `dat_cadastros_import.py`, `deslocamentos_import.py`, `equipe_gerencia_import.py`, `eventos_import.py`, `municipios_import.py`, `produtos_import.py`, `usuarios_import.py` — implementam a lógica de cada importação (não inspecionados em profundidade neste inventário).
