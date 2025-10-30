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

- [ ] **Fase 2 — Testes E2E (Playwright) fluxo Solicitação → Calendar**
  - [ ] Configurar ambiente Playwright (Docker friendly) e seeds mínimas.
  - [ ] Escrever teste: criação da solicitação → aprovação (Super) → preview (Controle) → publish (resposta simulada/fake GCal).
  - [ ] Validar persistências (`gcal_event_id`, `meet_link`, `gcal_payload_hash`) e AuditLog.
  - [ ] Documentar execução (pipeline/local) e integrar no CI.

- [ ] **Fase 3 — Template Google Calendar**
  - [ ] Atualizar serviço de payload para gerar título e descrição conforme `Solicitacao`.
  - [ ] Cobrir com testes unitários (preview/publish) garantindo formato.
  - [ ] Validar manualmente com smoke e anexar evidências.

- [ ] **Fase 4 — Alterar/Cancelar evento publicado**
  - [ ] Backend: expor endpoints “republicar” e “cancelar” com AuditLog e checagens de permissão.
  - [ ] Frontend: adicionar botões na Pré-agenda (Controle/Super) com confirmações.
  - [ ] Testes (backend + Playwright) cobrindo update/delete e idempotência.

- [ ] **Fase 5 — Gestão interna adicional e desligamento de planilhas**
  - [ ] Implementar endpoint `/api/etl/reports/latest` e painel simples para arquivos recentes (read-only).
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

**Última atualização**: 2025-10-29 (Iteração 4 - Modais CRUD completos para Municípios e Projetos)
