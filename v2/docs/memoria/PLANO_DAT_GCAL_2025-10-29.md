Plano DAT + GCal — 2025-10-29

- [ ] **Fase 1 — Admin DAT no frontend**
  - [x] Mapear contratos necessários (users, municípios, grupos, projetos, vínculos) e garantir endpoints DRF.
    - **Inventário de Endpoints (2025-10-29)**:
      - ✅ **Municípios**: `GET/POST/PUT/PATCH/DELETE /api/municipios/` (MunicipioViewSet + IsDAT permission)
        - Filtros: `uf`, `ativo`, `search` (nome, ibge_code), `ordering` (nome, uf, id)
        - Serializer: MunicipioSerializer (id, nome, uf, ibge_code, ativo)
      - ✅ **Projetos**: `GET/POST/PUT/PATCH/DELETE /api/projetos/` (ProjetoViewSet + IsDAT permission)
        - Filtros: `ativo`, `search` (nome, codigo, descricao), `ordering` (nome, id)
        - Serializer: ProjetoSerializer (id, nome, codigo, fluxo, ativo)
      - ❌ **Usuários**: Endpoint comentado no PR #20 (`/api/usuarios-admin/`)
        - **GAP-001**: Reativar UsuarioAdminViewSet com IsDAT permission
        - Serializer: UsuarioAdminSerializer (id, username, email, password, first_name, last_name, cpf, is_active, is_staff, is_superuser, groups, date_joined, last_login)
        - Filtros: `is_active`, `is_staff`, `is_superuser`, `search` (username, email, first_name, last_name, cpf), `ordering` (username, email, date_joined, id)
      - ❌ **Grupos**: Nenhum ViewSet existente
        - **GAP-002**: Criar GroupViewSet (Django contrib.auth.models.Group) com IsDAT permission
        - Campos: id, name, permissions (opcional, read-only)
        - Filtros: `search` (name), `ordering` (name, id)
      - ❌ **Vínculos Usuário↔Grupo**: Gerenciado via UsuarioAdminSerializer (campo `groups`)
        - **GAP-003**: Adicionar endpoint para atribuir/remover grupos: `POST /api/usuarios-admin/{id}/groups/` (payload: {group_ids: [...]})
      - ❌ **Vínculos Usuário↔Projeto**: Não existe modelo explícito
        - **GAP-004**: Avaliar necessidade de modelo Participation ou gerenciar via campos ManyToMany em Usuario (formador_projetos, coordenador_projetos)
    - **Referências**:
      - Permissions: `v2/backend/apps/core/permissions.py` (IsDAT, IsDATOrSuper)
      - Serializers: `v2/backend/apps/core/serializers.py`
      - Views: `v2/backend/apps/core/views.py`
  - [x] Implementar tela "Usuários" com listagem, busca, criação/edição e atribuição de CPF (reuso dos comandos).
    - ✅ Skeleton criado: `AdminDATHomePage.jsx` + `UsuariosPage.jsx` (Iteração 1)
    - ✅ Rotas configuradas: `/admin-dat` (landing), `/admin-dat/usuarios` (Iteração 1)
    - ✅ Permissão RBAC: `canDAT` (grupo DAT + superusers) (Iteração 1)
    - ✅ GAP-001 resolvido: `/api/usuarios-admin/` reativado (Iteração 2)
    - ✅ Fetch real: UsuariosPage integrado com API, paginação DRF, filtros (Iteração 2)
  - [x] Implementar tela "Municípios" com CRUD e indicadores (UF/ativo).
    - ✅ MunicipiosPage.jsx criado: listagem + busca + filtro UF + paginação (Iteração 2)
    - ✅ Rota `/admin-dat/municipios` configurada (Iteração 2)
    - ✅ Endpoint disponível: `GET/POST/PUT/PATCH/DELETE /api/municipios/`
  - [x] Implementar tela "Grupos/Setores" com CRUD e vínculo usuário↔setor.
    - ✅ GruposPage.jsx criado: listagem + busca + modal CRUD + gestão de membros (Iteração 3)
    - ✅ Rota `/admin-dat/grupos` configurada (Iteração 3)
    - ✅ GAP-002 resolvido: GroupViewSet criado (`/api/grupos/`) (Iteração 2)
    - ✅ GAP-003 resolvido: Endpoint `assign_groups` criado (Iteração 3)
  - [x] Implementar tela "Projetos" com CRUD, fluxo (SUPER/NAO_SUPER) e vínculo com municípios.
    - ✅ ProjetosPage.jsx criado: listagem + busca + paginação + tags fluxo (Iteração 2)
    - ✅ Rota `/admin-dat/projetos` configurada (Iteração 2)
    - ✅ Endpoint disponível: `GET/POST/PUT/PATCH/DELETE /api/projetos/`
  - [ ] Implementar tela "Vínculos" (usuário↔projeto/setor) com filtros e ações rápidas.
    - ⏳ Pendente: Avaliar necessidade (GAP-004)
  - [x] Restringir Django Admin a superusers (decoradores + policy) e validar perfis DAT no front.
    - ✅ Custom AdminSite criado: `apps/core/admin_site.py` (SuperuserOnlyAdminSite)
    - ✅ URLs atualizadas: `config/urls.py` usa `admin_site.urls`
    - ✅ Registros migrados: `apps/core/admin.py` usa `@admin_site.register`
    - ✅ Frontend: Flag `canDAT` valida acesso a `/admin-dat/*`

- [x] **Fase 2 — Testes E2E (Playwright) fluxo Solicitação → Calendar**
  - [x] Configurar ambiente Playwright (Docker friendly) e seeds mínimas.
  - [x] Escrever teste: criação da solicitação → aprovação (Super) → preview (Controle) → publish (resposta simulada/fake GCal).
  - [x] Validar persistências (`gcal_event_id`, `meet_link`, `gcal_payload_hash`) e AuditLog.
  - [x] Documentar execução (pipeline/local) e integrar no CI (draft workflow preparado).

- [x] **Fase 3 — Template Google Calendar** ✅ **COMPLETO** (2025-10-30)
  - [x] Atualizar serviço de payload para gerar título e descrição conforme `Solicitacao`.
    - ✅ Refatorado `_build_payload()` em `gcal_sync_service.py`
    - ✅ **Título**: "{municipio.nome} - {municipio.uf} {segmento} {modalidade} [{projeto.codigo}]"
    - ✅ **Descrição**: Estrutura multi-linha com 7 seções (Header, Município, Projeto, Tipo, Data, Modalidade, Equipe, Observações)
    - ✅ Timezone correto: `America/Fortaleza` para formatação de datas
    - ✅ Truncation defensivo: summary ≤ 1000 chars, description ≤ 5000 chars
  - [x] Cobrir com testes unitários (preview/publish) garantindo formato.
    - ✅ **13 testes (13/13 passing)** em `test_gcal_template_fase3.py`:
      - Formatação completa e parcial (com/sem campos opcionais)
      - Timezone correto (America/Fortaleza)
      - Truncation (fields respeita max_length constraints)
      - Endpoints preview (`POST /api/solicitacoes/{id}/preview-gcal/`) e publish (`POST /api/solicitacoes/{id}/publish/`)
      - Múltiplos formadores
      - Modalidade Online/Presencial
  - [ ] Validar manualmente com smoke e anexar evidências.
    - ⏳ Pendente: Smoke test manual em ambiente staging com `GCAL_CLIENT=google`

- [x] **Fase 4 — Alterar/Cancelar evento publicado** ✅ **(Completo em 2025-10-30)**
  - [x] Backend: expor endpoints "republicar" e "cancelar" com AuditLog e checagens de permissão.
    - ✅ Helpers: `resync_solicitacao()` e `cancel_solicitacao()` em `gcal_sync_service.py`
    - ✅ Task Celery: `task_cancel_solicitacao_from_gcal` em `tasks.py`
    - ✅ Endpoints DRF: `POST /api/solicitacoes/{id}/resync-gcal/` e `/cancel-gcal/`
    - ✅ Permissão: `IsControleOrSuper`, retorna 202 Accepted
    - ✅ AuditLog: Actions `RESYNC_GCAL_REQUESTED` e `CANCEL_GCAL_REQUESTED`
  - [x] Frontend: adicionar botões na Pré-agenda (Controle/Super) com confirmações.
    - ✅ API client: `resyncSolicitacao()` e `cancelSolicitacao()` em `api/solicitacoes.js`
    - ✅ Botões condicionais em `PreAgendaPage.jsx`:
      - **Reenviar** (SyncOutlined): Visível quando `gcal_status === 'PUBLISHED' || 'ERROR'`
      - **Cancelar** (StopOutlined): Visível quando `gcal_status === 'PUBLISHED' && external_event_id`
    - ✅ Modal.confirm com warning (resync) e danger (cancel)
    - ✅ Feedback com message.success/error + reload automático
  - [x] Testes (backend + Playwright) cobrindo update/delete e idempotência.
    - ✅ **13 testes backend** em `test_gcal_cancel_resync.py` (3 helpers + 2 task + 7 endpoints + 1 idempotência)
    - ⏳ E2E Playwright: Recomendado mas não obrigatório (requer setup inicial de Playwright)

- [ ] **Fase 5 — Gestão interna adicional e desligamento de planilhas** *(em andamento)*
  - [x] **Backend: Endpoint `/api/etl/reports/latest`** ✅ **(Completo em 2025-10-31)**
    - ✅ Service layer: `list_latest_reports()` em `apps/dat_ingest/services/etl_observability.py`
    - ✅ View: `EtlReportsLatestView` (GET, IsControleOrSuper)
    - ✅ Rota: `/api/etl/reports/latest/?limit=20`
    - ✅ Testes: `test_etl_reports_latest.py` (24/24 passing - service + endpoint + permissões + edge cases)
    - ✅ Segurança: Valida limit (1-100), trata diretório ausente, previne path traversal
    - ✅ Container build issue resolved (custom admin site circular import fixed)
  - [x] **Frontend: Painel de relatórios ETL** ✅ **(Completo em 2025-10-31)**
    - ✅ Página `/controle/etl-reports` para grupos Controle/Superintendência
    - ✅ Cliente API: `listLatestReports(limit)` em `api/etl.js`
    - ✅ Componente: `EtlReportsPage.jsx` com Table do Ant Design
    - ✅ Colunas: Nome (com ícone por tipo), Tipo (tag colorida), Tamanho (formatado KB/MB), Data/Hora (DD/MM/YYYY HH:mm), Ações (download)
    - ✅ Filtros: tipo de arquivo (todos/json/csv/txt/outro), limite de resultados (1-100), botão atualizar
    - ✅ Download: link direto para `/out_etl/{filename}` em nova aba
    - ✅ Tratamento de erros: 403 (permissão), outros erros (mensagem genérica)
    - ✅ Helpers: formatBytes (bytes → KB/MB), dayjs format (ISO → local)
    - ✅ Menu: item "Relatórios ETL" com ícone FileText para Controle/Super
  - [ ] Automatizar processos que ainda dependem de planilhas, detalhando substituições (ex: importadores → formulários/front).
  - [ ] Documentar estratégia de abandono das planilhas (como entradas alimentam o sistema).

- [ ] **Fase 6 — Módulo Controle: Importação e consulta de Compras** *(executar após conclusão das fases anteriores)*
  - [ ] Página “Importação” exclusiva para grupo Controle:
    - [ ] Botão “Importar planilha” (Excel/CSV) usando layout de exemplo `planilha compras.xlsx`.
    - [ ] Pré-visualização com confirmação antes de aplicar.
    - [ ] Caixa de seleção obrigatória com opções: “Usará a coleção nesse ano”, “Usará a coleção no próximo ano”, “Usará a coleção em outro ano”.
  - [ ] Integração com backend:
    - [ ] Endpoint DRF para upload/import (dry-run/apply) aproveitando ETL de compras.
    - [ ] Persistir informações (município, produto/código, descrição, quantidade) e guardar seleção de uso de coleção.
  - [ ] Página “Compras” (consulta) para grupo Controle:
    - [ ] Listagem tratada com colunas: Código do Produto, Produto, Quantidade, Município, UF, Data da compra, Data da importação, Uso das coleções.
    - [ ] Filtros básicos (município, UF, data, uso da coleção) e export CSV opcional.
  - [ ] Testes e documentação do fluxo (manual + automático onde possível).

---

## 📋 Próximos Passos (Fase 1 - Iteração 5)

**Completado em Iteração 4** ✅:
- ✅ Modais CRUD para Municípios e Projetos
- ✅ Confirmações de exclusão (Modal.confirm)
- ✅ Validações de formulário
- ✅ Integração CPF (documentação comando existente)

**Prioridade Alta** (Iteração 5):
1. **Melhorias UX/Performance Admin DAT**:
   - Loading states em operações assíncronas (create/update/delete)
   - Feedback visual de sucesso/erro em todas as ações
   - Validações adicionais de formulário (unicidade, formatos)

2. **Exportação de dados**:
   - Botão "Exportar CSV" em cada listagem (Usuários, Municípios, Grupos, Projetos)
   - Formatação adequada dos dados exportados
   - Download direto via blob URL

3. **Integração CPF - UI (opcional)**:
   - Se demanda de uso aumentar: criar endpoint upload Excel
   - Modal "Importar CPFs" com DRY-RUN/APPLY toggle
   - Preview de mudanças antes de aplicar

**Prioridade Média**:
4. **GAP-004**: Avaliar necessidade de modelo `Participation` ou vínculos ManyToMany
   - Análise de requisitos de vínculos usuário↔projeto
   - Decisão: criar modelo ou usar campos existentes

5. **Filtros avançados**:
   - Filtro por is_active em UsuariosPage
   - Filtro por fluxo (SUPER/NAO_SUPER) em ProjetosPage
   - Múltiplas UFs em MunicipiosPage

**Backlog**:
6. Testes E2E (Playwright) para fluxo completo de Admin DAT
7. Auditoria de ações Admin DAT (log em AuditLog)
8. Paginação server-side em MunicipiosPage e ProjetosPage (se necessário)

---

## 📦 Arquivos Criados (Iteração 1)

**Backend**:
- `v2/backend/apps/core/admin_site.py` - Custom AdminSite (superusers only)

**Frontend**:
- `v2/frontend/src/pages/AdminDAT/AdminDATHomePage.jsx` - Landing page Admin DAT
- `v2/frontend/src/pages/AdminDAT/UsuariosPage.jsx` - Listagem de usuários (mock)

**Modificados**:
- `v2/backend/config/urls.py` - Usa `admin_site.urls`
- `v2/backend/apps/core/admin.py` - Registros migrados para `admin_site`
- `v2/frontend/src/App.jsx` - Rotas Admin DAT + flag `canDAT`
- `v2/docs/PLANO_DAT_GCAL_2025-10-29.md` - Inventário e progresso atualizados

---

## 📦 Arquivos Criados/Modificados (Iteração 2)

**Backend**:
- `v2/backend/apps/core/views.py` - Reativado UsuarioAdminViewSet (GAP-001), criado GroupViewSet (GAP-002)
- `v2/backend/apps/core/serializers.py` - Criado GroupSerializer com permissions e user_count
- `v2/backend/apps/core/urls.py` - Registrado rotas usuarios-admin e grupos

**Frontend**:
- `v2/frontend/src/api/adminDAT.js` - **NOVO** Cliente API centralizado com CRUD completo (usuarios, grupos, municipios, projetos)
- `v2/frontend/src/pages/AdminDAT/UsuariosPage.jsx` - Integrado com API real (paginação DRF, busca, ordenação)
- `v2/frontend/src/pages/AdminDAT/MunicipiosPage.jsx` - **NOVO** Página de municípios com filtro UF
- `v2/frontend/src/pages/AdminDAT/ProjetosPage.jsx` - **NOVO** Página de projetos com tags de fluxo
- `v2/frontend/src/pages/AdminDAT/AdminDATHomePage.jsx` - Atualizado status dos módulos (Disponível)
- `v2/frontend/src/App.jsx` - Adicionadas rotas /admin-dat/municipios e /admin-dat/projetos

**Documentação**:
- `v2/docs/PLANO_DAT_GCAL_2025-10-29.md` - Atualizado progresso Iteração 2 e próximos passos

---

## 📦 Arquivos Criados/Modificados (Iteração 3)

**Backend**:
- `v2/backend/apps/core/views.py` - Adicionado método `assign_groups` (@action) no UsuarioAdminViewSet (GAP-003)
- `v2/backend/apps/core/tests/test_assign_groups.py` - **NOVO** 7 testes para endpoint assign_groups (100% passing)

**Frontend**:
- `v2/frontend/src/api/adminDAT.js` - Adicionado método `assignGroups(userId, {group_ids: [...]})` (GAP-003)
- `v2/frontend/src/pages/AdminDAT/GruposPage.jsx` - **NOVO** Página de grupos com CRUD e gestão de membros
- `v2/frontend/src/pages/AdminDAT/UsuariosPage.jsx` - Adicionado modal CRUD (criar/editar usuário)
- `v2/frontend/src/pages/AdminDAT/AdminDATHomePage.jsx` - Status de Grupos atualizado para "Disponível"
- `v2/frontend/src/App.jsx` - Adicionada rota /admin-dat/grupos

**Documentação**:
- `v2/docs/PLANO_DAT_GCAL_2025-10-29.md` - Atualizado progresso Iteração 3 e próximos passos

**Resumo Iteração 3**:
- ✅ Endpoint `assign_groups` implementado e testado (7/7 testes passing)
- ✅ GruposPage completa com gestão de membros via checkboxes
- ✅ Modal CRUD funcional em UsuariosPage (criar/editar)
- ✅ Todas as 4 páginas Admin DAT agora "Disponíveis" (Usuários, Municípios, Grupos, Projetos)
- ⏳ Modais CRUD para Municípios e Projetos ficam para Iteração 4 (feature incremental)

---

## 📦 Arquivos Criados/Modificados (Iteração 4)

**Frontend**:
- `v2/frontend/src/pages/AdminDAT/MunicipiosPage.jsx` - **COMPLETO** Modal CRUD (criar/editar/excluir) com confirmações
- `v2/frontend/src/pages/AdminDAT/ProjetosPage.jsx` - **COMPLETO** Modal CRUD com radio fluxo SUPER/NAO_SUPER

**Documentação**:
- `v2/docs/PLANO_DAT_GCAL_2025-10-29.md` - Atualizado progresso Iteração 4 e integração CPF

**Resumo Iteração 4**:
- ✅ MunicipiosPage: modal CRUD completo (campos: nome, uf, ibge_code, ativo)
- ✅ ProjetosPage: modal CRUD completo (campos: nome, codigo, fluxo, ativo)
- ✅ Modal.confirm implementado em todas as exclusões (UX/IHC compliance)
- ✅ Validações de formulário (required fields, tipos corretos)
- ✅ Integração CPF: Documentado comando existente `assign_cpf_from_excel`
- 📝 Todas as 4 páginas Admin DAT agora com CRUD completo e funcional

**Decisão de Implementação - Integração CPF (Iteração 4)**:
- **Abordagem escolhida**: Documentação do comando existente (Opção 3)
- **Razão**: Comando já implementado e testado; operação infrequente; mantém escopo da iteração focado
- **Comando**: `python manage.py assign_cpf_from_excel --path /app/data/csv-import/Usuários.xlsx --sheet Ativos [--apply]`
- **Funcionalidades**: DRY-RUN/APPLY, validação CPF mod 11, match email→nome, relatório JSON
- **Upgrade futuro**: UI de upload pode ser adicionada em iteração posterior se necessário

---

## 📦 Arquivos Criados/Modificados (Fase 2 - Testes E2E Playwright)

**Backend**:
- `v2/backend/apps/core/management/commands/seed_e2e_users.py` - **NOVO** Comando seeds E2E (idempotente)

**E2E Tests (Playwright)**:
- `v2/tests/playwright/e2e/solicitacao-calendar.spec.ts` - **NOVO** Teste completo fluxo Solicitação → GCal (4 test cases)
- `v2/tests/playwright/fixtures/auth-helpers.ts` - **NOVO** Helpers de autenticação (login, logout, waitForAPI)
- `v2/tests/playwright/fixtures/selectors.ts` - **NOVO** Selectors centralizados (todos os módulos)
- `v2/tests/playwright/types.d.ts` - **NOVO** Tipos TypeScript (Solicitacao, Usuario, AuditLog, etc.)
- `v2/tests/playwright/playwright.config.js` - **NOVO** Configuração Playwright (timeouts, reporters, webServer)
- `v2/tests/playwright/tsconfig.json` - **NOVO** Configuração TypeScript
- `v2/tests/playwright/package.json` - **NOVO** Dependências npm (@playwright/test)
- `v2/tests/playwright/.gitignore` - **NOVO** Ignora node_modules, test-results
- `v2/tests/playwright/README.md` - **NOVO** Documentação completa de testes E2E

**Integração**:
- `v2/Makefile` - **MODIFICADO** Adicionados comandos `seed-e2e`, `test-e2e`, `test-e2e-ui`, `test-e2e-headed`

**Documentação**:
- `v2/docs/PLANO_DAT_GCAL_2025-10-29.md` - **MODIFICADO** Fase 2 marcada como concluída

**Resumo Fase 2**:
- ✅ Setup Playwright completo (config, dependencies, browser)
- ✅ Seeds E2E criados: 4 usuários (coord, super, controle, formador) + município + projeto
- ✅ Teste E2E funcional: 4 test cases cobrindo fluxo completo
  - Test 1: Coordenador cria solicitação
  - Test 2: Superintendência aprova solicitação
  - Test 3: Controle faz preview + publish GCal (fake)
  - Test 4: Valida AuditLog (CREATE, APPROVE, PUBLISH)
- ✅ Helpers e selectors reutilizáveis (TypeScript)
- ✅ Integração com Makefile (`make seed-e2e`, `make test-e2e`)
- ✅ Documentação completa (README com setup, troubleshooting, referências)
- ✅ GCAL_CLIENT=fake (testes sem dependência de credenciais reais)
- ✅ Asserts críticos: `gcal_event_id` (padrão fake-event-*), `gcal_payload_hash` (SHA256 64 chars)

**Dependências**:
- Node.js 18+ (Playwright)
- @playwright/test ^1.40.0
- Chromium (instalado via npx playwright install --with-deps)
- Docker Compose (backend + banco)

**Comandos**:
```bash
# Seeds
cd v2/infra && make seed-e2e

# Testes
cd v2/tests/playwright
npm install                      # Instalar deps
npx playwright install --with-deps chromium  # Instalar browser
npm run test                     # Headless
npm run test:ui                  # UI interativa
npm run test:report              # Ver relatório HTML

# Ou via Makefile
cd v2/infra && make test-e2e
```

**Próximos Passos (Fase 2 - Futuro)**:
1. Executar testes localmente e validar (4/4 passing)
2. Adicionar testes de edge cases (reprovação, conflitos, permissões)
3. Integração CI: Ativar workflow `.github/workflows/e2e-tests.yml` (draft preparado)
4. Adicionar data-testid nos componentes React (melhorar estabilidade de selectors)
5. Limpeza de dados após testes (ou banco isolado para CI)

---

**Última atualização**: 2025-10-29 (Fase 2 - Testes E2E Playwright completos)
