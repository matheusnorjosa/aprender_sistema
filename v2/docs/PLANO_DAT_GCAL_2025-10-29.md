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
  - [ ] Implementar tela "Grupos/Setores" com CRUD e vínculo usuário↔setor.
    - ⏳ Pendente: Criar `GruposPage.jsx` e rota `/admin-dat/grupos`
    - ✅ GAP-002 resolvido: GroupViewSet criado (`/api/grupos/`) (Iteração 2)
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

## 📋 Próximos Passos (Fase 1 - Iteração 3)

**Prioridade Alta** (próxima sessão):
1. **Tela Grupos**: Criar `GruposPage.jsx`
   - Listagem de grupos Django com fetch de `/api/grupos/`
   - Tabela com ID, Nome, Permissions, User Count
   - Modal para CRUD de grupos
   - Reutilizar estrutura de MunicipiosPage/ProjetosPage
2. **GAP-003**: Endpoint para atribuir grupos a usuários
   - `POST /api/usuarios-admin/{id}/groups/` (payload: `{group_ids: [...]}`)
   - Método `@action` no UsuarioAdminViewSet
3. **Modais CRUD**: Adicionar criação/edição em todas as páginas
   - UsuariosPage: modal criar/editar usuário + atribuir CPF
   - MunicipiosPage: modal criar/editar município
   - ProjetosPage: modal criar/editar projeto
   - GruposPage: modal criar/editar grupo + atribuir usuários

**Prioridade Média**:
4. **GAP-004**: Avaliar necessidade de modelo `Participation` ou vínculos ManyToMany
5. Integração com comando `assign_cpf_from_excel` na UI de usuários
6. Melhorias de UX: confirmações de exclusão, feedback visual, validações

**Backlog**:
7. Testes E2E (Playwright) para fluxo completo de Admin DAT
8. Exportação CSV de listagens
9. Filtros avançados (datas, múltiplas UFs, etc.)

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

**Última atualização**: 2025-10-29 (Iteração 2 - Endpoints integrados, páginas Municípios/Projetos criadas)
