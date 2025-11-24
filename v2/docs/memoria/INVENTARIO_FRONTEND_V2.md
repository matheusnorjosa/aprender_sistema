# Frontend React — Aprender Sistema v2

**Data:** 2025-10-20
**Stack:** React 18 + Vite + Ant Design + React Router + Axios

---

## 📋 Sumário Executivo

O frontend v2 é uma **Single Page Application (SPA)** em React que consome a API DRF do backend. Sistema completo com 2 páginas funcionais, componentes reutilizáveis e integração CSRF.

### Status: ~50-60% Completo (2 de 4 páginas principais)

**✅ Funcional:**
- Infraestrutura Vite com Hot Module Replacement (HMR)
- Roteamento com React Router v7
- Autenticação via sessão Django (cookies)
- CSRF token automático (extraído de `csrftoken` cookie)
- 2 páginas implementadas: Disponibilidade (Formadores) e Solicitações (Superintendência)
- Componentes reutilizáveis (BlockForm, MyBlocksTable, RemoteSelect)
- API clients com axios (availability.js, solicitacoes.js)

**❌ Faltando:**
- Página de criação de solicitações (Coordenadores)
- Página de mapa mensal de disponibilidade (calendário E/2/D/P/T/X)
- Testes (Vitest + React Testing Library)
- Modo escuro

---

## 1. Arquitetura Frontend

### 1.1 Stack Tecnológica

**Core:**
- **React 18.3.1** — Biblioteca UI
- **Vite 7.1.7** — Build tool (substituindo Webpack/CRA)
- **React Router 7.9.4** — Roteamento SPA

**UI Library:**
- **Ant Design 5.27.4** — Componentes prontos (Table, Form, Modal, etc.)
- **@ant-design/icons 6.1.0** — Biblioteca de ícones

**HTTP Client:**
- **Axios 1.12.2** — Cliente HTTP com CSRF configurado

**Utilitários:**
- **Day.js 1.11.18** — Manipulação de datas (substituindo Moment.js)

**Dev Dependencies:**
- **ESLint 9.36** — Linter
- **@vitejs/plugin-react 5.0.4** — Plugin Vite para React
- **TypeScript types** — @types/react, @types/react-dom

### 1.2 Estrutura de Diretórios

```
v2/frontend/
├── src/
│   ├── api/                    # API clients
│   │   ├── availability.js     # CRUD de bloqueios + checagem
│   │   └── solicitacoes.js     # CRUD de solicitações + approve/reject
│   ├── components/             # Componentes reutilizáveis
│   │   ├── BlockForm.jsx       # Formulário de bloqueio
│   │   ├── MyBlocksTable.jsx   # Tabela de bloqueios
│   │   └── RemoteSelect.jsx    # Select com busca server-side
│   ├── pages/                  # Páginas/rotas
│   │   ├── Disponibilidade.jsx # Gerenciar bloqueios (Formadores)
│   │   └── Solicitacoes.jsx    # Aprovar/reprovar (Superintendência)
│   ├── assets/                 # Imagens, fontes, etc.
│   ├── App.jsx                 # Componente raiz + roteamento
│   ├── App.css                 # Estilos do App
│   ├── index.css               # Estilos globais
│   └── main.jsx                # Entry point
├── public/                     # Arquivos estáticos
├── dist/                       # Build de produção (gerado)
├── .vite/                      # Cache do Vite
├── node_modules/               # Dependências npm
├── .env                        # Variáveis de ambiente (local, gitignored)
├── .env.example                # Template de variáveis
├── index.html                  # HTML raiz
├── vite.config.js              # Configuração Vite
├── eslint.config.js            # Configuração ESLint
├── package.json                # Dependências
└── README.md                   # Documentação do frontend
```

---

## 2. Páginas Implementadas (2/4)

### 2.1 Disponibilidade (Formadores) — `/disponibilidade`

**Arquivo:** `src/pages/Disponibilidade.jsx` (102 linhas)

**Funcionalidades:**
- ✅ **Criar Bloqueio:** Formulário (BlockForm) para bloqueios Total (T) ou Parcial (P)
- ✅ **Listar Bloqueios:** Tabela (MyBlocksTable) com bloqueios do usuário
- ✅ **Excluir Bloqueio:** Apenas bloqueios com `status=pendente`
- ✅ **Checagem Consultiva:** Botão "Checar Disponibilidade" antes de criar

**Layout:**
- 2 colunas responsivas (Card de Criação + Card de Listagem)
- Grid Ant Design (Row/Col com breakpoints xs/lg)

**Handlers:**
- `handleCreate(data)` — linha 40 — POST `/api/availability-blocks/`
- `handleDelete(id)` — linha 56 — DELETE `/api/availability-blocks/{id}/`
- `fetchBlocks()` — linha 23 — GET `/api/availability-blocks/?owner=me`

**Validações:**
- Data/hora início < Data/hora fim
- Campos obrigatórios: inicio, fim, tipo
- Tipo: T (Total) ou P (Parcial)

### 2.2 Solicitações (Superintendência) — `/solicitacoes`

**Arquivo:** `src/pages/Solicitacoes.jsx` (480 linhas)

**Funcionalidades:**
- ✅ **Listar Solicitações:** Tabela paginada (10 por página)
- ✅ **Filtros:**
  - Por status: pendente/aprovado/reprovado/todos
  - Por texto: busca em usuário/município/tipo evento (server-side)
- ✅ **Ver Detalhes:** Drawer lateral com informações completas (Descriptions)
- ✅ **Aprovar:** Modal de confirmação (PA-02: apenas Superintendência)
- ✅ **Reprovar:** Modal com TextArea para justificativa opcional

**Controle de Permissões (PA-06):**
- linha 93-114 — `fetchCurrentUser()` verifica grupo "Superintendência" ou `is_superuser`
- linha 334-342 — Alert para usuários não-autorizados (podem ver, mas não aprovar/reprovar)
- linha 295-317 — Botões "Aprovar" e "Reprovar" só aparecem se:
  - `isSuperintendencia === true`
  - `record.status === 'pendente'`

**Handlers:**
- `fetchSolicitacoes(page)` — linha 119 — GET `/api/solicitacoes/?status=...&page=...&search=...`
- `handleViewDetails(record)` — linha 158 — GET `/api/solicitacoes/{id}/`
- `handleApprove(id)` — linha 175 — PATCH `/api/solicitacoes/{id}/approve/`
- `handleReject(values)` — linha 208 — PATCH `/api/solicitacoes/{id}/reject/` (com justificativa)

**Colunas da Tabela (linha 229-321):**
- ID, Usuário, Município, Tipo Evento, Início, Fim, Status, Ações
- Status com Tags coloridas: gold (pendente), green (aprovado), red (reprovado)
- Ações: Ver (todos), Aprovar/Reprovar (apenas Super + pendente)

**Validações:**
- Justificativa: máximo 500 caracteres (opcional)
- Confirmação antes de aprovar
- Feedback visual de sucesso/erro
- Recarga automática da lista após ações

---

## 3. Componentes Reutilizáveis

### 3.1 BlockForm.jsx

**Funcionalidades:**
- Form.Item para inicio/fim (DatePicker do Ant Design)
- Select para tipo (Total/Parcial)
- TextArea para motivo (opcional)
- Botão "Checar Disponibilidade" (consultivo, não bloqueia submit)
- Botão "Criar Bloqueio"

**Validação:**
- fim deve ser > inicio
- Campos obrigatórios: inicio, fim, tipo

### 3.2 MyBlocksTable.jsx

**Funcionalidades:**
- Table do Ant Design com colunas: Início, Fim, Tipo, Status, Motivo, Ações
- Filtros por Tipo (T/P) e Status (pendente/aprovado/reprovado)
- Ordenação por data
- Botão "Excluir" (apenas para `status=pendente`)
- Estados: loading, empty

### 3.3 RemoteSelect.jsx

**Funcionalidades:**
- Select com busca server-side (debounce)
- Usado para dropdowns de Municípios, Projetos, Formadores, etc.
- Lazy loading de opções

---

## 4. API Clients (axios)

### 4.1 availability.js

**Base URL:** `import.meta.env.VITE_API_URL` (default: `http://localhost:8002/api`)

**Funções:**

#### `getBlocks(params)`
- **GET** `/api/availability-blocks/`
- **Params:** `{ owner: 'me' }` ou `{ status: 'pendente' }`
- **Retorna:** Array de bloqueios

#### `createBlock(data)`
- **POST** `/api/availability-blocks/`
- **Body:** `{ inicio, fim, tipo, motivo }`
- **Retorna:** Bloqueio criado

#### `deleteBlock(id)`
- **DELETE** `/api/availability-blocks/{id}/`
- **Retorna:** Status 204

#### `checkAvailability(params)`
- **GET** `/api/availability/check/`
- **Params:** `{ usuario_id, inicio, fim, municipio_id }`
- **Retorna:** `{ ok: bool, conflicts: [...] }`

#### `getMe()`
- **GET** `/api/me/`
- **Retorna:** `{ id, username, email, groups, is_superuser, is_superintendencia }`

**CSRF Protection:**
```javascript
// Extrai token do cookie csrftoken
function getCsrfToken() {
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : null;
}

// Adiciona header X-CSRFToken em todos os requests
axios.defaults.headers.common['X-CSRFToken'] = getCsrfToken();
```

**Credentials:**
```javascript
axios.defaults.withCredentials = true; // Envia cookies (sessão)
```

### 4.2 solicitacoes.js

**Funções:**

#### `listSolicitacoes(params)`
- **GET** `/api/solicitacoes/`
- **Params:** `{ status, page, search }`
- **Retorna:** `{ count, next, previous, results: [...] }`

#### `getSolicitacao(id)`
- **GET** `/api/solicitacoes/{id}/`
- **Retorna:** Detalhes da solicitação

#### `approveSolicitacao(id, data)`
- **PATCH** `/api/solicitacoes/{id}/approve/`
- **Body:** `{ justificativa }` (opcional)
- **Retorna:** Solicitação aprovada

#### `rejectSolicitacao(id, data)`
- **PATCH** `/api/solicitacoes/{id}/reject/`
- **Body:** `{ justificativa }` (opcional)
- **Retorna:** Solicitação reprovada

---

## 5. Roteamento (React Router v7)

**Arquivo:** `src/App.jsx` (54 linhas)

**Rotas:**

```jsx
<Routes>
  <Route path="/" element={<Navigate to="/disponibilidade" replace />} />
  <Route path="/disponibilidade" element={<Disponibilidade />} />
  <Route path="/solicitacoes" element={<Solicitacoes />} />
</Routes>
```

**Navegação:**
- Header fixo com Menu do Ant Design (theme="dark")
- Logo "AS v2" + 2 itens de menu:
  - **Disponibilidade** (CalendarOutlined) → `/disponibilidade`
  - **Solicitações** (CheckCircleOutlined) → `/solicitacoes`

**Locale:**
- `ConfigProvider` do Ant Design com `locale={ptBR}`
- Datas, mensagens e validações em português

---

## 6. Autenticação e Segurança

### 6.1 Autenticação via Sessão Django

**Fluxo:**
1. Usuário faz login no Django Admin (`http://localhost:8002/admin`)
2. Django cria sessão e define cookie `sessionid`
3. Frontend envia cookie `sessionid` em todos os requests (`withCredentials: true`)
4. Backend valida sessão e retorna dados

**Endpoint de Usuário Atual:**
- **GET** `/api/me/` — Retorna dados do usuário logado
- Usado para verificar permissões (Superintendência) e exibir nome/grupo

### 6.2 CSRF Protection

**Extração Automática:**
```javascript
// availability.js
function getCsrfToken() {
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : null;
}

axios.defaults.headers.common['X-CSRFToken'] = getCsrfToken();
```

**Header Enviado:**
- **X-CSRFToken:** Token extraído do cookie `csrftoken`
- Obrigatório para POST/PUT/PATCH/DELETE
- Django valida token antes de processar request

### 6.3 Controle de Permissões (PA-06)

**Solicitacoes.jsx (linha 99-105):**
```javascript
const isSuper =
  user?.is_superuser ||
  user?.is_superintendencia ||
  user?.groups?.includes('Superintendência') ||
  false;
```

**Conditional Rendering:**
- linha 295-317 — Botões "Aprovar" e "Reprovar" só aparecem se `isSuperintendencia && status === 'pendente'`
- linha 334-342 — Alert para usuários não-autorizados

**Alinhamento com Backend (PA-02):**
- Backend: Decorator `@permission_classes([IsSuperintendencia])` em `approve/reject`
- Frontend: Esconde botões para usuários sem permissão
- Double validation (frontend + backend)

---

## 7. Variáveis de Ambiente

### 7.1 .env.example

```env
# URL base da API backend
VITE_API_URL=http://localhost:8002/api
```

### 7.2 Uso no Código

```javascript
// availability.js
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8002/api';
```

**Nota:** Vite expõe variáveis com prefixo `VITE_*` em `import.meta.env`.

---

## 8. Scripts npm

### 8.1 package.json (scripts)

```json
{
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "lint": "eslint .",
    "preview": "vite preview"
  }
}
```

### 8.2 Comandos

#### Desenvolvimento (com HMR)
```bash
cd v2/frontend
npm install  # Instala dependências
npm run dev  # Inicia dev server na porta 5173
```

**URL:** http://localhost:5173

#### Build para Produção
```bash
npm run build
```

**Output:** `dist/` (HTML + JS + CSS otimizados)

#### Preview do Build
```bash
npm run preview
```

**URL:** http://localhost:4173 (serve `dist/`)

#### Lint
```bash
npm run lint
```

---

## 9. Fluxos de Usuário

### 9.1 Formador Cria Bloqueio de Disponibilidade

1. Acessa `/disponibilidade`
2. Preenche formulário: Data/hora início, Data/hora fim, Tipo (T/P), Motivo (opcional)
3. (Opcional) Clica "Checar Disponibilidade" → Modal com conflitos (X/T/P/D/M)
4. Clica "Criar Bloqueio"
5. Sistema cria bloqueio com `status=pendente` (PA-01)
6. Bloqueio aparece na tabela "Meus Bloqueios"
7. Formador pode excluir se `status=pendente`

### 9.2 Superintendência Aprova Solicitação

1. Acessa `/solicitacoes`
2. Vê lista paginada de solicitações
3. Filtra por `status=pendente`
4. Clica "Ver" em uma solicitação → Drawer com detalhes
5. Clica "Aprovar" → Modal de confirmação
6. Confirma → Sistema:
   - Altera `status=aprovado` (PA-02)
   - Gera log de auditoria (PA-05)
   - Agenda sincronização GCal (PA-03)
7. Tabela é recarregada automaticamente
8. Mensagem de sucesso aparece (Toast)

### 9.3 Superintendência Reprova Solicitação

1. Acessa `/solicitacoes`
2. Filtra por `status=pendente`
3. Clica "Reprovar" → Modal com TextArea
4. (Opcional) Escreve justificativa (máx 500 chars)
5. Clica "Reprovar" → Sistema:
   - Altera `status=reprovado` (PA-02)
   - Registra justificativa em log (PA-05)
6. Tabela é recarregada
7. Mensagem de sucesso aparece

---

## 10. Páginas Faltando (TODO)

### 10.1 Criação de Solicitações (Coordenadores) — `/solicitacoes/nova`

**Funcionalidades Necessárias:**
- Formulário com campos:
  - Município (RemoteSelect com busca server-side)
  - Projeto (RemoteSelect)
  - Tipo de Evento (RemoteSelect)
  - Data/hora início
  - Data/hora fim
  - Observações (TextArea opcional)
- **Permissão:** IsCoordenadorOrDAT (backend: permissions.py:31)
- Checagem consultiva de disponibilidade antes de criar
- Lista de formadores sugeridos (futura: com modelo Participation)
- Validação: fim > inicio

**Endpoint:**
- **POST** `/api/solicitacoes/`
- **Body:** `{ municipio, projeto, tipo_evento, inicio, fim, observacoes }`
- **Response:** Solicitação criada com `status=pendente`

### 10.2 Mapa Mensal de Disponibilidade — `/disponibilidade/mensal`

**Funcionalidades Necessárias:**
- Calendário mensal (Grid 7x5 ou similar)
- Seletor de Ano/Mês
- Códigos por formador/dia:
  - **E** (evento confirmado)
  - **2** (múltiplos eventos)
  - **D** (deslocamento)
  - **D1** (deslocamento 1 dia)
  - **P** (bloqueio parcial)
  - **T** (bloqueio total)
  - **X** (conflito)
- Cores diferenciadas por código (como nas planilhas originais)
- Filtros: por formador, por município, por projeto

**Endpoint (faltando no backend):**
- **GET** `/api/availability/monthly/?ano=YYYY&mes=MM`
- **Response:**
  ```json
  {
    "formadores": [
      {
        "id": 1,
        "nome": "João Silva",
        "dias": [
          {"dia": 1, "codigo": "E"},
          {"dia": 2, "codigo": "2"},
          {"dia": 5, "codigo": "D"}
        ]
      }
    ]
  }
  ```

**Gap Crítico:** Backend precisa implementar este endpoint antes (PR #3 do inventário principal).

---

## 11. Testes (Não Implementados)

**Status:** ❌ Nenhum teste encontrado

**Framework Recomendado:**
- **Vitest** — Test runner (compatível com Vite)
- **React Testing Library** — Testes de componentes
- **MSW (Mock Service Worker)** — Mock de API

**Testes Necessários:**
- `BlockForm.test.jsx` — Validação de datas, submit
- `MyBlocksTable.test.jsx` — Renderização, filtros, delete
- `Disponibilidade.test.jsx` — Fluxo completo de criar/listar/excluir
- `Solicitacoes.test.jsx` — Fluxo de aprovar/reprovar, controle de permissões (PA-06)
- `availability.js.test.js` — API clients, CSRF token
- `solicitacoes.js.test.js` — API clients

---

## 12. Configuração Vite

**Arquivo:** `vite.config.js`

```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8002',
        changeOrigin: true,
      }
    }
  }
})
```

**Proxy (opcional):**
- Redireciona `/api` para `http://localhost:8002/api`
- Evita problemas de CORS em desenvolvimento
- Não recomendado se backend já tem CORS configurado

---

## 13. Dependências (package.json)

### 13.1 Production

```json
{
  "@ant-design/icons": "^6.1.0",
  "antd": "^5.27.4",
  "axios": "^1.12.2",
  "dayjs": "^1.11.18",
  "react": "^18.3.1",
  "react-dom": "^18.3.1",
  "react-router-dom": "^7.9.4"
}
```

### 13.2 Development

```json
{
  "@eslint/js": "^9.36.0",
  "@types/react": "^18.3.26",
  "@types/react-dom": "^18.3.7",
  "@vitejs/plugin-react": "^5.0.4",
  "eslint": "^9.36.0",
  "eslint-plugin-react-hooks": "^5.2.0",
  "eslint-plugin-react-refresh": "^0.4.22",
  "globals": "^16.4.0",
  "vite": "^7.1.7"
}
```

---

## 14. Alinhamento com Cláusulas Pétreas

### 14.1 PA-01 (Sem Auto-Aprovação)
✅ **Cumprido:** Formulário de bloqueio cria com `status=pendente` (backend garante).

### 14.2 PA-02 (Apenas Superintendência Aprova)
✅ **Cumprido:**
- Backend: Decorator `@permission_classes([IsSuperintendencia])`
- Frontend: Botões "Aprovar" e "Reprovar" só aparecem se `isSuperintendencia === true` (linha 295-317)

### 14.3 PA-05 (Auditoria)
✅ **Cumprido:** Backend gera `AuditLog` ao aprovar/reprovar. Frontend não interfere.

### 14.4 PA-06 (UX/Controle Explícito)
✅ **Cumprido:**
- Botões de ação escondidos para usuários sem permissão (ISO 9241-110)
- Alert explicativo para não-autorizados (linha 334-342)
- Feedback visual claro (messages, modais de confirmação)

### 14.5 RD-01 a RD-08 (Regras de Disponibilidade)
✅ **Parcialmente Cumprido:**
- Frontend chama `checkAvailability()` consultivo (linha 156 de BlockForm)
- Backend valida e retorna conflitos (availability_service.py)
- Mapa mensal com códigos E/2/D/P/T/X **ainda não implementado** (frontend + backend)

---

## 15. Troubleshooting

### 15.1 Erro: "VITE_API_URL não definido"

**Solução:**
```bash
cp .env.example .env
```

Editar `.env`:
```env
VITE_API_URL=http://localhost:8002/api
```

### 15.2 Erro: "Unauthorized" ou "CSRF token missing"

**Causa:** Usuário não está logado no Django Admin.

**Solução:**
1. Acesse http://localhost:8002/admin
2. Faça login com credenciais
3. Volte para http://localhost:5173
4. Recarregue a página

**Verificação:**
```javascript
// No console do navegador
document.cookie // Deve conter csrftoken e sessionid
```

### 15.3 Erro: "Network Error" ou "CORS"

**Causa:** Backend não está rodando ou CORS não configurado.

**Solução:**
1. Verificar se backend está rodando:
   ```bash
   cd v2/infra
   docker-compose ps
   ```
2. Verificar URL da API no `.env`:
   ```env
   VITE_API_URL=http://localhost:8002/api
   ```
3. Backend deve ter CORS configurado para `http://localhost:5173` em `settings.py`:
   ```python
   CORS_ALLOWED_ORIGINS = ["http://localhost:5173"]
   ```

### 15.4 Erro: "npm install" lento no WSL1

**Causa:** WSL1 tem lentidão com operações de I/O intensivas.

**Solução (Recomendada):**
- Rodar `npm` diretamente no Windows host:
  ```powershell
  # No PowerShell/CMD do Windows
  cd C:\path\to\projeto\v2\frontend
  npm install
  npm run dev
  ```

**Solução Alternativa:**
- Migrar para WSL2 (muito mais rápido)

---

## 16. Próximos Passos (Roadmap Frontend)

### PR #F1 — Criação de Solicitações (Coordenadores) — 2 dias
- **Escopo:**
  - Criar página `/solicitacoes/nova`
  - Formulário com RemoteSelects (Município, Projeto, Tipo Evento)
  - Integração com `/api/solicitacoes/` (POST)
  - Checagem consultiva antes de criar
  - Navegação de volta para lista após criar
- **Critérios de Aceitação:**
  - Formulário funcional
  - Validações (fim > inicio, campos obrigatórios)
  - Mensagens de sucesso/erro
  - Permissão: IsCoordenadorOrDAT

### PR #F2 — Mapa Mensal de Disponibilidade — 3-4 dias
- **Escopo:**
  - Criar página `/disponibilidade/mensal`
  - Calendário mensal (Grid ou Ant Design Calendar)
  - Seletor Ano/Mês
  - Consumir endpoint `/api/availability/monthly` (faltante no backend)
  - Exibir códigos E/2/D/D1/P/T/X com cores
  - Filtros por formador/município/projeto
- **Critérios de Aceitação:**
  - Calendário renderiza corretamente
  - Códigos coloridos (como planilhas)
  - Performance com muitos formadores (>50)
  - Cache (Redux/Zustand ou cache do axios)
- **Bloqueador:** Backend precisa implementar endpoint `/api/availability/monthly` (PR #3 do backend)

### PR #F3 — Testes Automatizados — 2-3 dias
- **Escopo:**
  - Configurar Vitest + React Testing Library
  - Testes de componentes (BlockForm, MyBlocksTable)
  - Testes de páginas (Disponibilidade, Solicitacoes)
  - Testes de API clients (mocks com MSW)
  - Coverage mínimo: 80%
- **Critérios de Aceitação:**
  - `npm run test` executa todos os testes
  - Coverage report gerado
  - CI/CD executa testes automaticamente

### PR #F4 — Melhorias de UX — 1-2 dias
- **Escopo:**
  - Modo escuro (Ant Design theme switcher)
  - Breadcrumbs para navegação
  - Loading states consistentes
  - Empty states customizados
  - Skeleton loaders (Ant Design Skeleton)
- **Critérios de Aceitação:**
  - Modo escuro funcional (toggle no header)
  - Breadcrumbs em todas as páginas
  - Loading/Empty states em todos os componentes

---

## 17. Documentação Existente

### 17.1 README.md

**Arquivo:** `v2/frontend/README.md` (242 linhas)

**Conteúdo:**
- Tecnologias usadas
- Pré-requisitos (Node.js 18+, backend rodando)
- Configuração (`.env.example`)
- Scripts npm (dev, build, preview, lint)
- Autenticação (sessão Django + CSRF)
- Estrutura de pastas
- Funcionalidades por página
- Endpoints consumidos
- Componentes principais
- Troubleshooting
- Próximos passos (TODO)

**Status:** ✅ Completo e atualizado

---

## 18. Métricas do Frontend

### 18.1 Linhas de Código

```
src/
├── api/               ~300 linhas
├── components/        ~400 linhas
├── pages/             ~600 linhas
├── App.jsx            ~50 linhas
└── main.jsx           ~10 linhas

Total: ~1360 linhas de código (excluindo node_modules)
```

### 18.2 Bundle Size (Production)

**Estimativa:**
- **Ant Design:** ~500 KB (gzip)
- **React + ReactDOM:** ~150 KB (gzip)
- **Axios + Day.js:** ~30 KB (gzip)
- **Código próprio:** ~20 KB (gzip)

**Total estimado:** ~700 KB (gzip)

**Otimizações Futuras:**
- Tree-shaking de componentes Ant Design não usados
- Code splitting por rota (React.lazy)
- Compressão adicional (Brotli)

### 18.3 Performance

**Dev Server (Vite):**
- HMR: <100ms (instantâneo)
- Cold start: ~2s

**Build:**
- `npm run build`: ~15-20s (sem cache)
- Output otimizado: HTML + JS minificado + CSS extraído

---

## 19. Alinhamento Backend ↔ Frontend

### 19.1 Endpoints Consumidos (Implementados)

| Endpoint | Método | Status Backend | Status Frontend |
|----------|--------|----------------|-----------------|
| `/api/me/` | GET | ✅ Implementado | ✅ Usado (Solicitacoes.jsx:96) |
| `/api/availability-blocks/` | GET | ✅ Implementado | ✅ Usado (Disponibilidade.jsx:26) |
| `/api/availability-blocks/` | POST | ✅ Implementado | ✅ Usado (Disponibilidade.jsx:42) |
| `/api/availability-blocks/{id}/` | DELETE | ✅ Implementado | ✅ Usado (Disponibilidade.jsx:58) |
| `/api/availability/check/` | GET | ✅ Implementado | ✅ Usado (BlockForm.jsx) |
| `/api/solicitacoes/` | GET | ✅ Implementado | ✅ Usado (Solicitacoes.jsx:122) |
| `/api/solicitacoes/{id}/` | GET | ✅ Implementado | ✅ Usado (Solicitacoes.jsx:162) |
| `/api/solicitacoes/{id}/approve/` | PATCH | ✅ Implementado | ✅ Usado (Solicitacoes.jsx:184) |
| `/api/solicitacoes/{id}/reject/` | PATCH | ✅ Implementado | ✅ Usado (Solicitacoes.jsx:211) |

### 19.2 Endpoints Faltando (Backend + Frontend)

| Endpoint | Necessário Para | PR Backend | PR Frontend |
|----------|-----------------|------------|-------------|
| `/api/solicitacoes/` (POST) | Criação de solicitações | ✅ Implementado | ❌ Página faltando | #F1 |
| `/api/availability/monthly/` | Mapa mensal | ❌ Não implementado | ❌ Página faltando | #3, #F2 |

---

## 20. Considerações de Segurança

### 20.1 CSRF Protection ✅
- Token extraído automaticamente de cookie `csrftoken`
- Header `X-CSRFToken` em todos os requests mutantes

### 20.2 XSS Protection ✅
- React escapa HTML automaticamente (JSX)
- Ant Design sanitiza inputs

### 20.3 Session Hijacking ⚠️
- **Mitigação:** HTTPS obrigatório em produção
- **Backend:** `SESSION_COOKIE_SECURE = True` em produção
- **Backend:** `SESSION_COOKIE_HTTPONLY = True` (já configurado)

### 20.4 CORS ✅
- Backend configura `CORS_ALLOWED_ORIGINS`
- Frontend usa `withCredentials: true`

### 20.5 Permissões (PA-06) ✅
- Double validation: frontend (UI) + backend (decorator)
- Botões escondidos para usuários sem permissão
- Backend sempre valida, mesmo se frontend burlar

---

## 21. Conclusão

O **frontend React v2** está **~50-60% completo**, com 2 das 4 páginas principais implementadas:

✅ **Funcional:**
- Disponibilidade (Formadores): criar/listar/excluir bloqueios
- Solicitações (Superintendência): aprovar/reprovar com controle de permissões (PA-06)

❌ **Faltando:**
- Criação de solicitações (Coordenadores) — PR #F1
- Mapa mensal de disponibilidade (E/2/D/P/T/X) — PR #F2 (depende de backend PR #3)
- Testes automatizados — PR #F3
- Melhorias de UX (modo escuro, etc.) — PR #F4

**Estimativa para MVP completo (frontend):** ~7-10 dias de desenvolvimento.

**Roadmap combinado (Backend + Frontend):**
1. **Backend PR #1** → Fix Participation model (1 dia)
2. **Backend PR #2** → ETL Acompanhamento (3-5 dias)
3. **Backend PR #3** → API `/api/availability/monthly` (2-3 dias)
4. **Frontend PR #F1** → Criação de solicitações (2 dias)
5. **Frontend PR #F2** → Mapa mensal (3-4 dias) — **depende de Backend PR #3**
6. **Frontend PR #F3** → Testes (2-3 dias)

**Total:** ~15-20 dias para MVP completo (backend + frontend).

---

**Gerado por:** Claude Code
**Data:** 2025-10-20
**Versão:** 1.0
