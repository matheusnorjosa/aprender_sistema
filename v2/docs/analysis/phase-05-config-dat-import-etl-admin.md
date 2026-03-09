# Phase 05 — Config/DAT/Importações/Admin/ETL (v2)

Data: 2026-02-04
Escopo: Configurações do sistema, Admin DAT, Módulo DAT (Registros e Operações), Importações via API, ETL e Observabilidade.

## Status
Concluído.

## Notas de Execução (Alto Nível)
1. Mapeei documentação v2 relacionada a Config/DAT/ETL/Admin e identifiquei requisitos esperados.
2. Cruzei documentação com backend (models, serializers, views, urls, permissões).
3. Cruzei frontend (rotas, páginas, APIs) com backend e docs.
4. Rodei suíte de testes focada em Admin/Config/DAT/Import/ETL.

## Explorado (Log Alto Nível)
Read: `v2/docs/GUIA_ADMIN_RBAC.md`
Read: `v2/docs/USERS_CPF_GUIDE.md`
Read: `v2/docs/ENV_VARS_ETL.md`
Read: `v2/docs/SPEC_DAT_REGISTROS.md`
Read: `v2/docs/plans/PLAN_import_pages.md`
Read: `v2/docs/analysis/ANALISE_planilhas_completa.md`
Read: `v2/docs/API_REFERENCE.md`
Read: `v2/docs/AGENTS.md`
Read: `v2/backend/apps/core/models/config.py`
Read: `v2/backend/apps/core/services/config_service.py`
Read: `v2/backend/apps/core/views_config.py`
Read: `v2/backend/apps/core/serializers/config.py`
Read: `v2/backend/apps/core/views/admin.py`
Read: `v2/backend/apps/core/serializers/usuario.py`
Read: `v2/backend/apps/core/permissions.py`
Read: `v2/backend/apps/core/models/organizacao.py`
Read: `v2/backend/apps/core/models/dat_registro.py`
Read: `v2/backend/apps/core/models/dat_acao.py`
Read: `v2/backend/apps/core/models/dat_cadastro.py`
Read: `v2/backend/apps/core/models/workflow.py`
Read: `v2/backend/apps/core/views/dat.py`
Read: `v2/backend/apps/core/views/dat_module.py`
Read: `v2/backend/apps/core/views_controle_dat.py`
Read: `v2/backend/apps/core/views_imports.py`
Read: `v2/backend/apps/core/views_controle_imports.py`
Read: `v2/backend/apps/core/views_import_bloqueios.py`
Read: `v2/backend/apps/core/views_options.py`
Read: `v2/backend/apps/core/urls.py`
Read: `v2/backend/apps/dat_ingest/views.py`
Read: `v2/backend/apps/dat_ingest/services/etl_observability.py`
Read: `v2/backend/apps/dat_ingest/urls.py`
Read: `v2/backend/config/urls.py`
Read: `v2/backend/apps/dat_ingest/management/commands/*`
Read: `v2/frontend/src/App.tsx`
Read: `v2/frontend/src/api/adminDAT.ts`
Read: `v2/frontend/src/api/datModule.ts`
Read: `v2/frontend/src/api/ops.ts`
Read: `v2/frontend/src/api/etl.ts`
Read: `v2/frontend/src/hooks/useConfig.ts`
Read: `v2/frontend/src/pages/AdminDAT/AdminDATHomePage.tsx`
Read: `v2/frontend/src/pages/AdminDAT/UsuariosPage.tsx`
Read: `v2/frontend/src/pages/AdminDAT/GruposPage.tsx`
Read: `v2/frontend/src/pages/AdminDAT/MunicipiosPage.tsx`
Read: `v2/frontend/src/pages/AdminDAT/ProjetosPage.tsx`
Read: `v2/frontend/src/pages/AdminDAT/ConfiguracoesPage.tsx`
Read: `v2/frontend/src/pages/DAT/DATPage.tsx`
Read: `v2/frontend/src/pages/DATModule/AcoesPage.tsx`
Read: `v2/frontend/src/pages/DATModule/CadastrosPage.tsx`
Read: `v2/frontend/src/pages/DATModule/DATRegistrosPage.tsx`
Read: `v2/frontend/src/pages/Controle/EtlReportsPage.tsx`

## Implementação vs Documentação (Resumo)
1. `SPEC_DAT_REGISTROS.md` está marcado como “Planejamento”. Implementação existe para `ProjetoGeral` e `DATRegistro` (models, serializers, views, stats/export), mas modelos opcionais `Regiao` e `Estado` não existem. Permissões descritas no spec não batem com o código em `DATRegistroViewSet`.
2. `ENV_VARS_ETL.md` descreve `ETL_OUTPUT_DIR` e `ETL_DATA_DIR`. No código, `audit_agenda_users`, `assign_cpf_from_excel` e o export do admin usam `ETL_OUTPUT_DIR`, mas vários comandos ainda gravam direto em `BASE_DIR/out_etl` e não há uso de `ETL_DATA_DIR` nos comandos de importação.
3. `ANALISE_planilhas_completa.md` lista ETLs “a criar” (produtos, equipe/gerência). Os comandos `etl_import_produtos.py` e `etl_import_equipe_gerencia.py` existem, indicando documentação desatualizada.
4. `PLAN_import_pages.md` prevê importação web para Bloqueios, Deslocamentos e Eventos. Bloqueios foi implementado, mas Deslocamentos e Eventos não foram encontrados.
5. `API_REFERENCE.md` indica `/api/config/` como IsAuthenticated e `/api/tipos-evento/` CRUD. No código, `/api/config/` exige DAT ou Superintendência e não existe endpoint CRUD `/api/tipos-evento/`.
6. `GUIA_ADMIN_RBAC.md` não menciona o grupo “Diretoria”, mas ele existe em `ALLOWED_USER_GROUPS` e é usado no frontend para dashboards.

## Backend — Módulos, Tabelas e Regras

### Configurações do Sistema
Tabela: `core_config`.
Endpoints: `GET/PUT /api/config/` em `v2/backend/apps/core/views_config.py`.
Permissões: `IsDAT | IsSuperintendencia`.
Regras: validação por `ConfigSerializer`, cache via `config_service.py`, invalidado por signal.
Gap: documentação de permissão em `v2/docs/API_REFERENCE.md` indica IsAuthenticated, divergindo do código.

### Admin DAT (CRUD de Cadastros Base)
Tabelas principais: `core_municipio`, `core_projeto`, `core_produto`, `core_gerencia`, `auth_group`, `core_auditlog`, `core_usuario`.
Endpoints: `/api/usuarios-admin/`, `/api/municipios/`, `/api/projetos/`, `/api/produtos/`, `/api/gerencias/`, `/api/grupos/`, `/api/audit-logs/` em `v2/backend/apps/core/views/admin.py`.
Regras: filtros por search/order, permissões de escrita para DAT, leitura para autenticados em alguns endpoints.
Segurança: `UsuarioAdminSerializer` restringe grupos via whitelist e impede auto-modificação de grupos.
Gap: endpoint `assign_groups` ignora essas validações (ver achados).

### DAT Registros (ProjetoGeral + DATRegistro)
Tabelas: `core_projeto_geral`, `core_dat_registro`.
Endpoints: `/api/projetos-gerais/`, `/api/dat/registros/`, `/api/dat/registros/stats/`, `/api/dat/registros/export/` em `v2/backend/apps/core/views/dat.py`.
Regras: validação de projeto ↔ projeto_geral, cálculo de códigos, status geral, filtros por UF, projeto, status_formar.
Permissões: list/retrieve/create/update/export/stats → `IsDATOrSuper`; delete → `IsSuperintendenciaOnly`.
Gap: docs citam visualização/export para “qualquer autenticado”, mas o código restringe a DAT/Super.

### DAT Module (Ações, Cadastros, Compras, Coordenadores, Formações, Áreas)
Tabelas: `core_dat_acao`, `core_dat_cadastro`, `core_dat_compra`, `core_dat_coordenador`, `core_dat_formacao`, `core_dat_area`.
Endpoints: `/api/dat/acoes-ciclo/`, `/api/dat/cadastros/`, `/api/dat/compras-materiais/`, `/api/dat/coordenadores/`, `/api/dat/formacoes/`, `/api/dat/areas/` em `v2/backend/apps/core/views/dat_module.py`.
Regras: CRUD + stats + ações específicas (etapa, calendário), com `IsDATOrSuper` e delete restrito à Superintendência.

### Importações via API
Endpoints:
1. `/api/controle/import-acoes/` em `v2/backend/apps/core/views_imports.py`.
2. `/api/dat/import-cadastros/` em `v2/backend/apps/core/views_imports.py`.
3. `/api/controle/import-compras/` em `v2/backend/apps/core/views_controle_imports.py`.
4. `/api/disponibilidade/import-bloqueios/` em `v2/backend/apps/core/views_import_bloqueios.py`.
Regras: `dry_run=true|false`, upload multipart.
Gap: `ImportComprasView` não valida tamanho/MIME; demais endpoints validam.

### ETL e Observabilidade
Endpoints: `/api/etl/reports/latest/` em `v2/backend/apps/dat_ingest/views.py` com `IsControleOrSuper`.
Serviço: `list_latest_reports` em `v2/backend/apps/dat_ingest/services/etl_observability.py` usa `ETL_OUTPUT_DIR`.
Regras: listagem limitada, proteção contra path traversal.
Gap: frontend espera download em `/out_etl/<arquivo>`, mas não há endpoint de download no backend.

## Frontend — Páginas, Rotas e APIs

### Admin DAT
Rotas: `/dat/admin/*` em `v2/frontend/src/App.tsx`.
Páginas: `AdminDATHomePage`, `UsuariosPage`, `MunicipiosPage`, `ProjetosPage`, `GruposPage`, `ConfiguracoesPage`.
Gaps:
1. Links “Voltar para Admin DAT” usam `/admin-dat`, rota inexistente.
2. `UsuariosPage` usa `cpf` para exibição/edição, mas backend retorna `cpf_masked` e `cpf` é write-only.
3. `SETOR_GROUPS` não inclui “Diretoria”, impossibilitando atribuição via UI.

### DAT Importação (AcaoDAT)
Página: `v2/frontend/src/pages/DAT/DATPage.tsx`.
API: `importCadastros` e `listCadastros` em `v2/frontend/src/api/ops.ts` usa `/api/dat/import-cadastros/` e `/api/dat/acoes/`.
Observação: nomenclatura “cadastros” se refere a `AcaoDAT` (modelo legado), diferente de `DATCadastro` do DAT Module.

### DAT Module
Páginas: `AcoesPage`, `CadastrosPage`, `ComprasPage`, `CoordenadoresPage`, `DATRegistrosPage`, `FormacoesPage`, `PlanoFormacoesPage`.
API: `v2/frontend/src/api/datModule.ts`.
Gap crítico: `CadastrosPage` envia campos `quantidade_alunos`, `quantidade_professores`, `quantidade_codigos` não aceitos por `DATCadastroSerializer`, gerando 400 em create/update.
Gap adicional: `listProdutosDAT` usa `/api/dat/produtos/`, endpoint não existe no backend.

### ETL Reports
Página: `v2/frontend/src/pages/Controle/EtlReportsPage.tsx`.
Permissão esperada: Controle/Super.
Gap: rota está protegida por `canDAT`, mas backend exige Controle/Super, gerando 403 para DAT-only.
Gap adicional: download via `/out_etl/<arquivo>` não é servido pelo backend.

## Achados (Prioritizados)
1. [Alto] `assign_groups` ignora whitelist e bloqueio de auto-modificação de grupos.
Evidência: `v2/backend/apps/core/views/admin.py` e `v2/backend/apps/core/serializers/usuario.py`.
Impacto: possível atribuição de grupos fora da política e alteração de grupos pelo próprio usuário via endpoint dedicado.
Recomendação: reaproveitar validação do serializer no `assign_groups` ou validar `ALLOWED_USER_GROUPS` e auto-modificação no endpoint.

2. [Alto] `ImportComprasView` sem validação de tamanho/MIME.
Evidência: `v2/backend/apps/core/views_controle_imports.py` vs `v2/backend/apps/core/views_imports.py` e `v2/backend/apps/core/views_import_bloqueios.py`.
Impacto: risco de DoS por upload grande ou arquivo malicioso.
Recomendação: aplicar as mesmas validações de `views_imports.py`.

3. [Médio] `CadastrosPage` envia campos não suportados por `DATCadastroSerializer`.
Evidência: `v2/frontend/src/pages/DATModule/CadastrosPage.tsx` e `v2/backend/apps/core/serializers/dat_module/dat_cadastro.py`.
Impacto: falha de criação/edição via UI (HTTP 400).
Recomendação: alinhar payload do frontend com os campos reais (`quantidade_chaves`, `quantidade_recebidos`, etc) ou estender serializer/model.

4. [Médio] Permissões de `/api/etl/reports/latest/` não batem com rota frontend.
Evidência: `v2/frontend/src/App.tsx` e `v2/backend/apps/dat_ingest/views.py`.
Impacto: DAT-only recebe 403 em “Relatórios ETL”.
Recomendação: ajustar RBAC no frontend ou ampliar permissão no backend se desejado.

5. [Médio] Diretoria ausente em UI de grupos/usuários.
Evidência: `v2/frontend/src/pages/AdminDAT/UsuariosPage.tsx` e `v2/backend/config/settings.py`.
Impacto: não é possível atribuir/exibir Diretoria via Admin DAT UI.
Recomendação: incluir “Diretoria” em `SETOR_GROUPS`.

6. [Médio] Downloads de relatórios ETL não possuem endpoint/backend dedicado.
Evidência: `v2/frontend/src/api/etl.ts` e ausência de rota de download em `v2/backend/apps/dat_ingest/urls.py`.
Impacto: links podem falhar (404) sem configuração externa para servir `ETL_OUTPUT_DIR`.
Recomendação: criar endpoint de download usando `get_report_path` ou servir diretório via Nginx/STATIC.

7. [Baixo] Links “Voltar para Admin DAT” usam rota inexistente.
Evidência: `v2/frontend/src/pages/AdminDAT/*Page.tsx`.
Impacto: navegação quebrada.
Recomendação: trocar para `/dat/admin`.

8. [Baixo] Documentação desatualizada em `API_REFERENCE.md` e `ENV_VARS_ETL.md`.
Evidência: `v2/docs/API_REFERENCE.md`, `v2/docs/ENV_VARS_ETL.md`, código em backend.
Impacto: divergência em permissões e endpoints, confusão operacional.
Recomendação: atualizar docs com permissões reais e endpoints vigentes.

9. [Baixo] `listProdutosDAT` aponta para endpoint inexistente.
Evidência: `v2/frontend/src/api/datModule.ts` e `v2/backend/apps/core/urls.py`.
Impacto: dead code e potencial erro futuro se usado.
Recomendação: remover função ou criar endpoint.

## Testes Executados
Comando:
```
docker compose -f v2/infra/docker-compose.yml exec -T web pytest \
  apps/core/tests/test_admin_api.py \
  apps/core/tests/test_admin_user_security.py \
  apps/core/tests/test_assign_groups.py \
  apps/core/tests/test_config_api.py \
  apps/core/tests/test_config_service.py \
  apps/core/tests/test_controle_dat_api.py \
  apps/core/tests/test_dat_module.py \
  apps/core/tests/test_dat_registros.py \
  apps/core/tests/test_import_bloqueios.py \
  apps/core/tests/test_import_compras.py \
  apps/core/tests/test_import_endpoints.py \
  apps/core/tests/test_etl_acoes_controle.py \
  apps/core/tests/test_etl_dat_cadastros.py \
  apps/core/tests/test_upload_validation.py \
  apps/core/tests/test_assign_cpf_command.py \
  apps/dat_ingest/tests/test_etl_reports_latest.py \
  apps/dat_ingest/tests/test_audit_agenda_users.py -q
```
Resultado: 232 passed, 2 skipped, 148 warnings.

## Próximos Passos Sugeridos
1. Corrigir `assign_groups` para respeitar whitelist e auto-modificação.
2. Aplicar validações de upload em `ImportComprasView`.
3. Ajustar `CadastrosPage` para enviar apenas campos suportados pelo backend.
4. Corrigir rotas `/admin-dat` para `/dat/admin`.
5. Alinhar RBAC de ETL Reports (frontend vs backend) e adicionar endpoint de download.
6. Atualizar documentação de API e ETL.
