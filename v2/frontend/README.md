# AS v2 - Frontend React

Interface React para gerenciamento de disponibilidade no sistema Aprender Sistema (AS v2).

## 🚀 Tecnologias

- **React 18** + **Vite** - Build tool moderno e rápido
- **Ant Design** - Biblioteca de componentes UI
- **React Router** - Roteamento entre páginas
- **Axios** - Cliente HTTP (configurado com CSRF)
- **Day.js** - Manipulação de datas

## 📋 Pré-requisitos

- **Node.js 18+** e **npm**
- **Backend AS v2** rodando em `http://localhost:8002`
- **Autenticação**: Usuário deve estar logado no Django Admin (sessão/cookie)

## ⚙️ Configuração

### 1. Variáveis de Ambiente

Copie o arquivo `.env.example` para `.env`:

```bash
cp .env.example .env
```

**⚠️ Nota para usuários WSL1**: Se você estiver usando WSL1, é recomendado rodar o `npm` diretamente no Windows host para melhor performance, já que WSL1 pode ter lentidão com operações de I/O intensivas no sistema de arquivos.

**Variáveis disponíveis**:

```env
# URL base da API backend
VITE_API_URL=http://localhost:8002/api
```

### 2. Instalação

```bash
npm install
```

### 3. Desenvolvimento

```bash
npm run dev
```

Aplicação estará disponível em: **http://localhost:5173**

### 4. Build para Produção

```bash
npm run build
```

Output em: `dist/`

### 5. Preview do Build

```bash
npm run preview
```

## 🧪 Execução E2E Canônica (Playwright + Docker)

Para evitar drift de runtime (libs de browser no host e browser ausente no container frontend),
o caminho canônico de E2E é o runner Docker `frontend-e2e` (imagem oficial Playwright).

No diretório `v2/frontend`:

```bash
npm run test:e2e:docker -- e2e/z-auth.spec.ts --project=chromium --reporter=line
```

Esse comando:
- sobe `db/redis/web` via Docker Compose;
- aplica migrations;
- executa `seed_e2e_users`;
- roda Playwright no runner canônico com web server Vite interno + proxy para `http://web:8000`.

Para rodar a suíte chromium padrão:

```bash
npm run test:e2e:docker
```

Após finalizar, se quiser limpar o ambiente:

```bash
cd ../infra
docker compose -p aprender_v2 -f docker-compose.yml down
```

## 🔐 Autenticação

O frontend utiliza **sessão/cookie do Django** para autenticação. Para testar localmente:

1. Acesse o Django Admin: http://localhost:8002/admin
2. Faça login com suas credenciais
3. Abra o frontend: http://localhost:5173

**CSRF**: O token CSRF é extraído automaticamente do cookie `csrftoken` e enviado em todos os requests POST/PUT/PATCH/DELETE via header `X-CSRFToken`.

## 📂 Estrutura de Pastas

```
v2/frontend/
├── src/
│   ├── api/              # Clientes de API
│   │   ├── availability.js
│   │   └── solicitacoes.js
│   ├── components/       # Componentes reutilizáveis
│   │   ├── BlockForm.jsx
│   │   └── MyBlocksTable.jsx
│   ├── pages/            # Páginas/rotas
│   │   ├── Disponibilidade.jsx
│   │   └── Solicitacoes.jsx
│   ├── App.jsx           # Componente raiz (com roteamento)
│   └── main.jsx          # Entry point
├── .env.example          # Exemplo de variáveis de ambiente
├── .env                  # Variáveis de ambiente (local)
├── vite.config.js        # Configuração Vite
└── package.json          # Dependências
```

## 📱 Funcionalidades

### Página de Disponibilidade (Formadores)

**URL**: `/disponibilidade`

**Recursos**:

- ✅ **Criar Bloqueio**: Formulário para criar bloqueios de disponibilidade (Total ou Parcial)
- ✅ **Listar Bloqueios**: Tabela com todos os bloqueios do usuário atual
- ✅ **Excluir Bloqueio**: Apenas bloqueios com `status=pendente` podem ser excluídos

**Validações**:

- Data/hora início < Data/hora fim
- Campos obrigatórios: `inicio`, `fim`, `tipo`
- Tipo de bloqueio: `T` (Total) ou `P` (Parcial)

**Nota sobre Conflitos**: Para projetos SUPER, a decisão de disponibilidade é feita manualmente pela Superintendência através da Grade Mensal (/disponibilidade), não há checagem automática em tempo real.

### Página de Solicitações (Superintendência)

**URL**: `/solicitacoes`

**Acesso**: Apenas usuários do grupo **Superintendência**

**Recursos**:

- ✅ **Listar Solicitações**: Tabela paginada com todas as solicitações
- ✅ **Filtros**:
  - Por status (pendente/aprovado/reprovado/todos)
  - Por texto (busca em usuário/município/tipo evento)
- ✅ **Ver Detalhes**: Drawer com informações completas da solicitação
- ✅ **Aprovar**: Aprovar solicitação pendente com confirmação
- ✅ **Reprovar**: Reprovar solicitação com justificativa obrigatória (mínimo 10 caracteres)

**Controle de Permissões**:

- Botões "Aprovar" e "Reprovar" só aparecem para:
  - Usuários do grupo **Superintendência**
  - Solicitações com `status=pendente`
- Alinhado com **PA-06** (Política de Aprovação Manual)

**Validações**:

- Justificativa obrigatória para reprovar (mínimo 10, máximo 500 caracteres)
- Confirmação antes de aprovar
- Feedback visual de sucesso/erro
- Recarga automática da lista após ações

## 🔗 Endpoints Consumidos

### Disponibilidade (Formadores)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/availability-blocks/?owner=me` | Lista bloqueios do usuário atual |
| POST | `/api/availability-blocks/` | Cria novo bloqueio |
| DELETE | `/api/availability-blocks/{id}/` | Remove bloqueio (apenas pendente) |

**Nota**: Endpoints de checagem de disponibilidade (`/api/availability/check/` e `/api/availability/check-many/`) são ferramentas consultivas restritas a perfis Controle/Superintendência (não usadas em tempo real na UX).

### Solicitações (Superintendência)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/solicitacoes/` | Lista solicitações com filtros (status, page, search) |
| GET | `/api/solicitacoes/{id}/` | Busca detalhes de uma solicitação específica |
| PATCH | `/api/solicitacoes/{id}/approve/` | Aprova solicitação pendente |
| PATCH | `/api/solicitacoes/{id}/reject/` | Reprova solicitação (requer justificativa) |

### Autenticação

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/me/` | Informações do usuário atual |

## 🎨 Componentes Principais

### `<BlockForm />`

Formulário de criação de bloqueio com:
- DatePicker para início/fim
- Select para tipo (T/P)
- TextArea para motivo (opcional)
- Validação de datas (início < fim)

### `<MyBlocksTable />`

Tabela de bloqueios com:
- Colunas: Início, Fim, Tipo, Status, Motivo, Ações
- Filtros por Tipo e Status
- Ordenação por data
- Botão "Excluir" (apenas para pendentes)
- Estados de vazio e loading

### `<Disponibilidade />`

Página orquestradora que:
- Carrega lista de bloqueios ao montar
- Gerencia estados de loading
- Exibe mensagens de sucesso/erro
- Recarrega lista após criar/excluir

## 🐛 Troubleshooting

### Erro: "VITE_API_URL não definido"

Verifique se o arquivo `.env` existe e contém:

```env
VITE_API_URL=http://localhost:8002/api
```

### Erro: "Unauthorized" ou "CSRF token missing"

1. Faça login no Django Admin: http://localhost:8002/admin
2. Verifique se o cookie `csrftoken` está sendo enviado
3. Confirme que `credentials: 'include'` está habilitado no fetch

### Erro: "Network Error" ou "CORS"

1. Verifique se o backend está rodando: `docker-compose ps`
2. Confirme a URL da API no `.env`
3. Backend deve ter CORS configurado para `http://localhost:5173`

## 📝 Próximos Passos (TODO)

- [x] Implementar roteamento com React Router
- [x] Adicionar página de solicitações de eventos (Superintendência)
- [ ] Adicionar página de criação de solicitações (Coordenadores)
- [ ] Criar página de mapa mensal de disponibilidade
- [ ] Implementar testes (Vitest + React Testing Library)
- [ ] Adicionar modo escuro
- [ ] Implementar refresh token JWT (se migrar de sessão)

## 📄 Licença

Aprender Sistema (AS v2) - Uso interno

## 📞 Suporte

Em caso de dúvidas ou problemas, consulte:
- **Documentação Backend**: `v2/backend/README.md`
- **RUNBOOK**: `v2/docs/RUNBOOK_E2E_GCAL_SYNC.md`
