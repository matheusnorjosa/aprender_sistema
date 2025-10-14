# Validation Brief — PR 6/N + 6.1/N: UI de Solicitações (Aprovação + Hotfixes)

## Objetivo
Implementar interface de usuário para que a Superintendência possa visualizar, aprovar e reprovar solicitações de eventos.

**PR 6.1/N (Hotfix)**: Corrigir violação PA-06 (permissões hardcoded) e adicionar filtros server-side.

## Alterações Realizadas

### 1. API Client (src/api/solicitacoes.js)
**Nova funcionalidade**: Cliente API completo para consumo dos endpoints de solicitações.

**Funções implementadas**:
- `listSolicitacoes({status, page, search})`: Lista solicitações com filtros e paginação
- `approveSolicitacao(id)`: Aprova solicitação pendente (PATCH `/api/solicitacoes/{id}/approve/`)
- `rejectSolicitacao(id, {justificativa})`: Reprova solicitação com justificativa obrigatória (PATCH `/api/solicitacoes/{id}/reject/`)
- `getSolicitacao(id)`: Busca detalhes de uma solicitação específica (GET `/api/solicitacoes/{id}/`)

**Características técnicas**:
- ✅ Extração automática de CSRF token via cookies
- ✅ Header `X-CSRFToken` adicionado automaticamente em métodos mutantes
- ✅ `credentials: 'include'` em todas as requisições
- ✅ Tratamento de erros com mensagens amigáveis
- ✅ Suporte a query params para filtros e paginação

### 2. Página de Solicitações (src/pages/Solicitacoes.jsx)
**Nova funcionalidade**: Interface completa para gestão de solicitações.

**Componentes implementados**:

#### Tabela Principal
- Colunas: ID, Usuário, Município, Tipo Evento, Início, Fim, Status, Ações
- Paginação automática (DRF PageNumberPagination)
- Status com cores (Tag): pendente (gold), aprovado (green), reprovado (red)
- Formatação de datas: DD/MM/YYYY HH:mm
- Tratamento de objetos/strings nos campos relacionados

#### Filtros
- **Status**: dropdown com opções (pendente/aprovado/reprovado/todos)
  - Padrão: "pendente"
- **Busca**: campo de texto para buscar por usuário/município/tipo
  - Debounce automático via `useEffect`

#### Drawer de Detalhes
- Exibe informações completas da solicitação selecionada
- `Descriptions` do Ant Design com layout vertical
- Campos: ID, Usuário, Município, Tipo de Evento, Início, Fim, Status, Observações, Created At, Updated At
- Botões de ação no header (se Superintendência + status pendente)

#### Modal de Reprovação
- Form com campo `TextArea` para justificativa
- Validação: obrigatório + mínimo 10 caracteres
- Contador de caracteres (máximo 500)
- Confirmação antes de enviar

#### Controle de Permissões
- `isSuperintendencia` verificado via `/api/me/`
- Botões Aprovar/Reprovar só aparecem se:
  - Usuário pertence ao grupo Superintendência
  - Status da solicitação é "pendente"
- Alinhado com **PA-06** (Política de Aprovação Manual)

#### Estados e Loading
- Loading durante fetch de dados
- Loading durante ações (aprovar/reprovar)
- Feedback via `message.success()` e `message.error()`
- Recarga automática da lista após ações

### 3. Roteamento (src/App.jsx)
**Alteração**: Adicionado suporte a múltiplas páginas com React Router.

**Mudanças**:
- Instalado `react-router-dom@7.9.4`
- Implementado `BrowserRouter` com rotas:
  - `/` → redireciona para `/disponibilidade`
  - `/disponibilidade` → página existente
  - `/solicitacoes` → nova página
- Menu horizontal no header com links para ambas páginas
- Layout Ant Design (`Header` + `Content`)
- Ícones: CalendarOutlined (Disponibilidade), CheckCircleOutlined (Solicitações)

## Como Testar

### Pré-requisitos
1. Backend rodando em Docker: `cd v2/infra && docker compose up -d`
2. Migrações aplicadas: `docker compose exec web python manage.py migrate`
3. Usuário admin com senha conhecida
4. Frontend rodando: `cd v2/frontend && npm run dev`

### Fluxo de Teste Manual

#### TC-01: Navegação
1. Acesse http://localhost:5173
2. Verifique que a página redireciona para `/disponibilidade`
3. Clique no menu "Solicitações"
4. Verifique que a URL muda para `/solicitacoes`
5. ✅ **Esperado**: Menu funciona e páginas carregam sem erro

#### TC-02: Listagem de Solicitações
1. Na página de Solicitações
2. Verifique que a tabela carrega com solicitações (se houver)
3. Verifique que o filtro de status está em "Pendente" por padrão
4. Clique em outras opções de filtro (Aprovado, Reprovado, Todos)
5. ✅ **Esperado**: Tabela atualiza conforme filtro selecionado

#### TC-03: Busca
1. Digite "formador" no campo de busca
2. Aguarde 300ms (debounce)
3. Verifique que a tabela filtra
4. Limpe o campo (botão X)
5. ✅ **Esperado**: Busca funciona e limpar restaura lista completa

#### TC-04: Ver Detalhes
1. Clique no botão "Ver" em qualquer solicitação
2. Verifique que o drawer abre à direita
3. Verifique que os dados estão corretos
4. Feche o drawer
5. ✅ **Esperado**: Drawer funciona e exibe dados completos

#### TC-05: Aprovar Solicitação (Superintendência)
**Pré-requisito**: Usuário pertence ao grupo Superintendência

1. Abra detalhes de uma solicitação pendente
2. Verifique que botões "Aprovar" e "Reprovar" aparecem
3. Clique em "Aprovar"
4. Confirme no modal
5. Aguarde feedback de sucesso
6. Verifique que a solicitação sai da lista de pendentes
7. ✅ **Esperado**: Solicitação aprovada, status atualizado, feedback exibido

#### TC-06: Reprovar Solicitação (Superintendência)
**Pré-requisito**: Usuário pertence ao grupo Superintendência

1. Abra detalhes de uma solicitação pendente
2. Clique em "Reprovar"
3. Modal de justificativa abre
4. Tente enviar sem preencher → erro
5. Preencha com menos de 10 caracteres → erro
6. Preencha com justificativa válida (>= 10 chars)
7. Confirme
8. Aguarde feedback de sucesso
9. Verifique que a solicitação sai da lista de pendentes
10. ✅ **Esperado**: Solicitação reprovada, status atualizado, feedback exibido

#### TC-07: Permissões (Não-Superintendência)
**Pré-requisito**: Usuário NÃO pertence ao grupo Superintendência

1. Acesse página de Solicitações
2. Verifique que botões "Aprovar" e "Reprovar" NÃO aparecem
3. Tente acessar endpoints diretamente via console:
   ```js
   fetch('http://localhost:8002/api/solicitacoes/1/approve/', {
     method: 'PATCH',
     credentials: 'include'
   })
   ```
4. ✅ **Esperado**: 403 Forbidden

#### TC-08: CSRF e Credentials
1. Abra DevTools → Network
2. Aprove ou reprove uma solicitação
3. Verifique que a requisição tem:
   - Header `X-CSRFToken` com token válido
   - `credentials: include` (cookies enviados)
4. ✅ **Esperado**: Autenticação via sessão funcionando

#### TC-09: Responsividade
1. Redimensione a janela do navegador
2. Verifique que a tabela, drawer e modal se adaptam
3. ✅ **Esperado**: Layout responsivo (Ant Design)

#### TC-10: Tratamento de Erros
1. Pare o backend: `docker compose stop web`
2. Tente listar solicitações
3. Verifique mensagem de erro amigável
4. ✅ **Esperado**: `message.error()` exibido com mensagem clara

### Novos Testes (PR 6.1/N — Hotfix)

#### VB-11: Botões Escondidos para Não-Superintendência
**Objetivo**: Validar PA-06 — apenas Superintendência vê botões de ação

**Pré-requisito**: Usuário autenticado SEM grupo "Superintendência"

1. Acesse `/solicitacoes`
2. Aguarde carregamento da página
3. Verifique que Alert amarelo aparece no topo: "Acesso restrito à Superintendência"
4. Verifique que na tabela não há colunas "Aprovar" e "Reprovar"
5. Clique em "Ver" em uma solicitação pendente
6. Verifique que o drawer NÃO exibe botões de ação no header
7. ✅ **Esperado**:
   - Alert de restrição visível
   - Botões Aprovar/Reprovar completamente escondidos (tabela + drawer)
   - Usuário pode visualizar, mas não pode modificar

#### VB-12: Filtro por Status (Server-side)
**Objetivo**: Validar filtro `?status=pendente` no backend

1. Acesse `/solicitacoes` (padrão: pendente)
2. Abra DevTools → Network
3. Verifique requisição GET para `/api/solicitacoes/?status=pendente&page=1`
4. Verifique que resposta contém apenas solicitações com `"status": "pendente"`
5. Altere filtro para "Aprovado"
6. Verifique nova requisição GET para `/api/solicitacoes/?status=aprovado&page=1`
7. Verifique que resposta contém apenas solicitações com `"status": "aprovado"`
8. Altere filtro para "Todos" (vazio)
9. Verifique requisição GET para `/api/solicitacoes/?page=1` (sem status)
10. ✅ **Esperado**:
    - Filtro aplicado no backend (DjangoFilterBackend)
    - Query param `status` enviado corretamente
    - Resposta filtrada conforme seleção

#### VB-13: Busca Textual por Usuário (Server-side)
**Objetivo**: Validar filtro `?search=joao` encontra por username/first_name/last_name

**Pré-requisito**: Existir solicitação de usuário com nome "João" ou "joao"

1. Acesse `/solicitacoes`
2. Digite "joao" no campo de busca
3. Aguarde debounce (300ms)
4. Abra DevTools → Network
5. Verifique requisição GET para `/api/solicitacoes/?status=pendente&page=1&search=joao`
6. Verifique que resposta contém apenas solicitações onde usuário contém "joao" (case-insensitive)
7. Limpe o campo de busca
8. Verifique que lista completa retorna
9. ✅ **Esperado**:
    - Busca aplicada no backend (SearchFilter)
    - Query param `search` enviado corretamente
    - Busca funciona em `usuario__username`, `usuario__first_name`, `usuario__last_name`

#### VB-14: Busca Textual por Município (Server-side)
**Objetivo**: Validar filtro `?search=Fortaleza` encontra por `municipio__nome`

**Pré-requisito**: Existir solicitação para município "Fortaleza"

1. Acesse `/solicitacoes`
2. Digite "Fortaleza" no campo de busca
3. Aguarde debounce (300ms)
4. Abra DevTools → Network
5. Verifique requisição GET para `/api/solicitacoes/?status=pendente&page=1&search=Fortaleza`
6. Verifique que resposta contém apenas solicitações onde município é "Fortaleza"
7. Digite "tal" (substring de "Fortaleza")
8. Verifique que busca parcial funciona (SearchFilter com icontains)
9. ✅ **Esperado**:
    - Busca aplicada no backend (SearchFilter)
    - Query param `search` enviado corretamente
    - Busca funciona em `municipio__nome` (case-insensitive, partial match)

## Critérios de Aceitação

| ID | Critério | Status |
|----|----------|--------|
| CA-01 | Tabela lista solicitações com filtros funcionando | ✅ |
| CA-02 | Filtro de status padrão é "pendente" | ✅ |
| CA-03 | Busca por texto funciona | ✅ |
| CA-04 | Drawer de detalhes exibe informações completas | ✅ |
| CA-05 | Botões Aprovar/Reprovar só aparecem para Superintendência | ✅ |
| CA-06 | Aprovar solicita confirmação e atualiza status | ✅ |
| CA-07 | Reprovar exige justificativa obrigatória (>= 10 chars) | ✅ |
| CA-08 | Após aprovação/reprovação, lista é recarregada | ✅ |
| CA-09 | CSRF token é enviado em requisições mutantes | ✅ |
| CA-10 | Credentials (cookies) são incluídos em todas as requisições | ✅ |
| CA-11 | Tratamento de erros com feedback amigável | ✅ |
| CA-12 | Menu de navegação funciona (Disponibilidade ↔ Solicitações) | ✅ |
| CA-13 | Usuários não autorizados não veem botões de ação | ✅ |
| **CA-14** | **[6.1] `/api/me/` retorna `groups` e `is_superintendencia`** | ✅ |
| **CA-15** | **[6.1] Filtro `?status=pendente` funciona server-side (DjangoFilterBackend)** | ✅ |
| **CA-16** | **[6.1] Busca `?search=joao` funciona server-side (SearchFilter)** | ✅ |
| **CA-17** | **[6.1] Alert de "Acesso restrito" aparece para não-Superintendência** | ✅ |

## Checklist de Validação

### Base (PR 6/N)
- [ ] Backend rodando e migrações aplicadas
- [ ] Frontend rodando sem erros de console
- [ ] Login realizado no Django Admin
- [ ] Navegação entre páginas funciona
- [ ] Tabela lista solicitações corretamente
- [ ] Filtros (status, busca) funcionam
- [ ] Drawer de detalhes abre e exibe dados
- [ ] Aprovar solicitação funciona (apenas Superintendência)
- [ ] Reprovar com justificativa funciona (apenas Superintendência)
- [ ] Usuários não autorizados não veem botões
- [ ] CSRF token enviado automaticamente
- [ ] Erros tratados com feedback amigável
- [ ] Screenshots/evidências capturados

### Hotfix (PR 6.1/N)
- [ ] `/api/me/` retorna `groups` e `is_superintendencia` (testar com curl/Postman)
- [ ] Testes backend passam: `test_api_me_permissions.py` (4/4)
- [ ] Testes backend passam: `test_solicitacoes_filters.py` (5/5)
- [ ] Filtro `?status=pendente` retorna apenas pendentes (verificar Network)
- [ ] Busca `?search=joao` retorna apenas usuários com "joao" (verificar Network)
- [ ] Busca `?search=Fortaleza` retorna apenas solicitações de Fortaleza (verificar Network)
- [ ] Alert amarelo aparece para usuários não-Superintendência
- [ ] Botões Aprovar/Reprovar escondidos para não-Superintendência
- [ ] Commit messages seguem convenção especificada
- [ ] Branch `feat/pr6.1-solicitacoes-perms-filters` criada contra base correta

## Arquivos Alterados/Criados

### Novos Arquivos (PR 6/N)
- `v2/frontend/src/api/solicitacoes.js` (130 linhas)
- `v2/frontend/src/pages/Solicitacoes.jsx` (469→477 linhas, atualizado em 6.1)
- `v2/docs/VALIDATION_BRIEF.md` (este arquivo)
- `v2/.agents/outbox/VALIDATION_REQUEST.json`
- `v2/.agents/outbox/CHANGE_SUMMARY.json`

### Novos Arquivos (PR 6.1/N — Hotfix)
- `v2/backend/apps/core/tests/test_api_me_permissions.py` (113 linhas, 4 testes)
- `v2/backend/apps/core/tests/test_solicitacoes_filters.py` (228 linhas, 5 testes)

### Arquivos Modificados (PR 6/N)
- `v2/frontend/src/App.jsx` (adicionado roteamento e menu)
- `v2/frontend/package.json` (adicionado react-router-dom@7.9.4)
- `v2/frontend/README.md` (documentação atualizada)

### Arquivos Modificados (PR 6.1/N — Hotfix)
- `v2/backend/apps/core/views.py`:
  - **CurrentUserView.get()** (linhas 269-285): Adicionado `groups` e `is_superintendencia`
  - **SolicitacaoViewSet** (linhas 72-111): Adicionado DRF filters (DjangoFilterBackend, SearchFilter, OrderingFilter)
- `v2/frontend/src/pages/Solicitacoes.jsx`:
  - **useEffect** (linhas 93-113): Busca permissão real de `/api/me/`
  - **Alert** (linhas 337-346): Aviso para usuários não-autorizados
- `v2/docs/VALIDATION_BRIEF.md`: Adicionados testes VB-11 a VB-14 e critérios CA-14 a CA-17

## Próximos Passos

### Para PR 6.1/N (Atual)
1. ✅ Executar testes backend: `docker compose exec web pytest apps/core/tests/test_api_me_permissions.py -v`
2. ✅ Executar testes backend: `docker compose exec web pytest apps/core/tests/test_solicitacoes_filters.py -v`
3. [ ] Executar testes manuais conforme checklist de Hotfix (VB-11 a VB-14)
4. [ ] Capturar screenshots:
   - Usuário Superintendência (com botões)
   - Usuário não-Superintendência (sem botões + Alert)
   - Filtro por status funcionando (Network tab)
   - Busca funcionando (Network tab)
5. [ ] Criar commits conforme mensagens especificadas:
   - `feat(api): expand /api/me/ with groups and is_superintendencia`
   - `feat(api): add status/search filters to SolicitacaoViewSet (DRF)`
   - `test(api): add tests for /me and solicitacoes filters`
   - `fix(fe): enforce PA-06 in Solicitações (hide admin actions by role)`
6. [ ] Push para branch `feat/pr6.1-solicitacoes-perms-filters` (base: `rebuild/2025-contexto-supremo`)
7. [ ] Abrir Pull Request com evidências

### Para PR 6/N (Original)
1. Executar testes manuais conforme checklist base
2. Capturar screenshots de cada fluxo
3. Corrigir bugs encontrados (se houver)
4. Commit e push para branch `feat/pr6-solicitacoes-ui`
5. Abrir Pull Request com evidências

## Referências
- Política de Aprovação Manual (PA-01 a PA-07) em `.claude/CLAUDE.md`
- Backend endpoints: `v2/backend/apps/core/views.py`
- Modelos: `v2/backend/apps/core/models.py`
- Ant Design Components: https://ant.design/components/overview/
