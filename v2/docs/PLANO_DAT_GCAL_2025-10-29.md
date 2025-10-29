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
    - ✅ Skeleton criado: `AdminDATHomePage.jsx` + `UsuariosPage.jsx`
    - ✅ Rotas configuradas: `/admin-dat` (landing), `/admin-dat/usuarios` (listagem mock)
    - ✅ Permissão RBAC: `canDAT` (grupo DAT + superusers)
    - ⏳ Pendente: Reativar `/api/usuarios-admin/` (GAP-001) e integrar fetch real
  - [ ] Implementar tela "Municípios" com CRUD e indicadores (UF/ativo).
    - ⏳ Pendente: Criar `MunicipiosPage.jsx` e rota `/admin-dat/municipios`
    - ✅ Endpoint disponível: `GET/POST/PUT/PATCH/DELETE /api/municipios/`
  - [ ] Implementar tela "Grupos/Setores" com CRUD e vínculo usuário↔setor.
    - ⏳ Pendente: Criar `GruposPage.jsx` e rota `/admin-dat/grupos`
    - ❌ GAP-002: Criar GroupViewSet (`/api/grupos/`)
  - [ ] Implementar tela "Projetos" com CRUD, fluxo (SUPER/NAO_SUPER) e vínculo com municípios.
    - ⏳ Pendente: Criar `ProjetosPage.jsx` e rota `/admin-dat/projetos`
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

---

## 📋 Próximos Passos (Fase 1 - Iteração 2)

**Prioridade Alta** (próxima sessão):
1. **GAP-001**: Reativar `UsuarioAdminViewSet` em `v2/backend/apps/core/views.py`
   - Descomentar ViewSet (linhas 698-719)
   - Descomentar registro em `urls.py` (linha 71)
   - Integrar fetch real em `UsuariosPage.jsx`
   - Adicionar modal de CRUD (criar/editar usuário)
2. **GAP-002**: Criar `GroupViewSet` para gestão de grupos Django
   - Serializer: `GroupSerializer` (id, name, permissions read-only)
   - ViewSet com IsDAT permission
   - Registrar em `urls.py` como `/api/grupos/`
3. **Telas Municípios e Projetos**: Criar `MunicipiosPage.jsx` e `ProjetosPage.jsx`
   - Reutilizar estrutura de `UsuariosPage.jsx` (tabela + filtros + modal CRUD)
   - Endpoints já existem e estão funcionais

**Prioridade Média**:
4. **GAP-003**: Endpoint para atribuir grupos a usuários
   - `POST /api/usuarios-admin/{id}/groups/` (payload: `{group_ids: [...]}`)
   - Método `@action` no UsuarioAdminViewSet
5. **Tela Grupos**: Criar `GruposPage.jsx`
   - Listagem de grupos Django
   - Modal para atribuir usuários a grupos (reuso GAP-003)

**Backlog**:
6. **GAP-004**: Avaliar necessidade de modelo `Participation` ou vínculos ManyToMany
7. Integração com comando `assign_cpf_from_excel` na UI de usuários
8. Testes E2E (Playwright) para fluxo completo de Admin DAT

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

**Última atualização**: 2025-10-29 (Iteração 1 - Skeleton concluído)
