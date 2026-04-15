# Plano: Gerências e Produtos — Seed + CRUD Admin

**Data:** 2026-04-14
**Branch:** `feat/admin-gerencias-produtos`
**Issues relacionadas:** Dropdown vazio na Grade Mensal, CRUD admin

## Contexto

A tabela `core_gerencia` está vazia em produção. O dropdown de "Gerência" na Grade Mensal chama `GET /api/gerencias/` e retorna `[]`. O backend (ViewSets, Serializers, URLs) já está pronto — falta seed de dados e UI de CRUD no admin.

## Mapeamento de dados confirmado

| Gerência | Setor (nome_setor) | Projetos |
|---|---|---|
| GERENCIA 2 | Vidas | VIDA E CIÊNCIAS, LINGUAGEM, MATEMÁTICA, AVANÇANDO JUNTOS MAT/PORT |
| GERENCIA 3 | Fluir | FLUIR DAS EMOÇÕES |
| GERENCIA 4 | ACerta | ACERTA PORT/MAT, ECS, SUPERATIVAR, LEIO ESCREVO E CALCULO |
| GERENCIA 5 | Brincando | BRINCANDO E APRENDENDO |
| GERENCIA 6 | Sou da Paz | SOU DA PAZ |
| GERENCIA INDIVIDUAL | Individual | A COR DA GENTE, ED FINANCEIRA, GESTÃO ESCOLAR, MY COMPANION, TRÂNSITO LEGAL, UNI DUNI TÊ |
| SUPERINTENDENCIA | Super | CIRANDAR, LENDO E ESCREVENDO, NOVO LENDO, TEMA, LER OUVIR E CONTAR, AMMA, CATAVENTO, MIUDEZAS |

## Tarefas

### Tarefa 1 — Seed de Gerências em `apps/core` (backend)

**O que fazer:**
- Copiar `dev_tools/management/commands/seed_gerencias.py` → `core/management/commands/seed_gerencias.py`
- Idempotente com `get_or_create`
- Funciona em produção (core não depende de `INCLUDE_DEV_TOOLS`)

**Arquivos:**
- `v2/backend/apps/core/management/commands/seed_gerencias.py` (novo)

**Teste:**
```bash
docker exec aprender_dev-web-1 python manage.py seed_gerencias
# Verificar: GET /api/gerencias/ retorna 7 registros
```

---

### Tarefa 2 — Seed de Produtos em `apps/core` (backend)

**O que fazer:**
- Criar `core/management/commands/seed_produtos.py`
- Ler dados da planilha Produtos.xlsx (hardcoded no command como lista Python, não CSV runtime)
- Para cada produto: `get_or_create` por código/nome
- Vincular ao Projeto via FK (buscar por nome)
- Idempotente

**Dados:** ~400 produtos da planilha com colunas: id, Descrição, Nome, Projeto, Tipo, Gerência

**Arquivos:**
- `v2/backend/apps/core/management/commands/seed_produtos.py` (novo)

**Teste:**
```bash
docker exec aprender_dev-web-1 python manage.py seed_produtos --dry-run
docker exec aprender_dev-web-1 python manage.py seed_produtos
```

---

### Tarefa 3 — CRUD de Gerências no frontend

**O que fazer:**
- Criar `GerenciasPage.tsx` seguindo o padrão do `ProjetosPage.tsx`
- Tabela com colunas: ID, Nome, Nome Setor, Gerente, Projetos (count), Ativo, Ações
- Modal de criação/edição com campos: nome, nome_setor, gerente (dropdown de usuários), descricao, ativo
- API functions em `adminDAT.ts`: `listGerencias`, `createGerencia`, `updateGerencia`, `deleteGerencia`

**Arquivos:**
- `v2/frontend/src/pages/AdminDAT/GerenciasPage.tsx` (novo)
- `v2/frontend/src/api/adminDAT.ts` (adicionar CRUD de gerências)

**Teste:**
- Criar gerência via UI → verificar em `GET /api/gerencias/`
- Editar nome_setor → verificar que dropdown da Grade Mensal reflete
- Deletar gerência sem projetos → sucesso
- Deletar gerência com projetos → erro PROTECT

---

### Tarefa 4 — CRUD de Produtos no frontend

**O que fazer:**
- Criar `ProdutosPage.tsx` seguindo o padrão do `ProjetosPage.tsx`
- Tabela com colunas: ID, Código, Nome, Descrição, Projeto, Tipo, Ativo, Ações
- Modal de criação/edição com campos: codigo, nome, descricao, projeto (dropdown), tipo (dropdown Aluno/Professor), ativo
- API functions em `adminDAT.ts`: `listProdutos`, `createProduto`, `updateProduto`, `deleteProduto`

**Arquivos:**
- `v2/frontend/src/pages/AdminDAT/ProdutosPage.tsx` (novo)
- `v2/frontend/src/api/adminDAT.ts` (adicionar CRUD de produtos)

**Teste:**
- Criar produto vinculado a projeto → verificar na listagem
- Editar produto → atualiza
- Verificar que Compras mostra os novos produtos no dropdown

---

### Tarefa 5 — Integrar páginas no Admin DAT

**O que fazer:**
- Adicionar cards "Gerências" e "Produtos" na `AdminDATHomePage.tsx`
- Adicionar rotas em `AppRoutes.tsx` (lazy-loaded, `canDAT` permission)
- Adicionar itens no sidebar em `AppSidebar.tsx`

**Arquivos:**
- `v2/frontend/src/pages/AdminDAT/AdminDATHomePage.tsx` (adicionar 2 cards)
- `v2/frontend/src/components/AppRoutes.tsx` (adicionar 2 rotas)
- `v2/frontend/src/components/AppSidebar.tsx` (adicionar 2 menu items)

**Teste:**
- Navegar para `/dat/admin` → ver cards de Gerências e Produtos
- Clicar no card → abre página de CRUD
- Sidebar mostra os novos itens no submenu DAT

---

### Tarefa 6 — Limpar setor "Gerência" do RBAC

**O que fazer:**
- Remover `"Gerência"` do `SETOR_GROUPS` em `constants.py`
- Verificar se algum usuário em produção está nesse grupo antes de remover
- Manter o grupo Django existente (não deletar) — apenas remover da whitelist

**Arquivos:**
- `v2/backend/apps/core/constants.py` (remover 1 linha)

**Risco:** Se algum usuário está no grupo "Gerência", perde o setor. Verificar no Portainer antes.

**Teste:**
```bash
docker exec aprender_dev-web-1 python manage.py shell -c "
from django.contrib.auth.models import Group
g = Group.objects.filter(name='Gerência').first()
print(f'Usuarios no grupo Gerência: {g.user_set.count() if g else 0}')
"
```

---

## Ordem de execução

1. **Tarefa 1** (seed gerências) → merge → rodar em prod → dropdown funciona
2. **Tarefa 6** (limpar RBAC) → pode ir junto com tarefa 1
3. **Tarefa 3** (CRUD gerências frontend) → PR separado
4. **Tarefa 4** (CRUD produtos frontend) → PR separado ou junto com 3
5. **Tarefa 5** (integração admin) → junto com 3 e 4
6. **Tarefa 2** (seed produtos) → após CRUD estar pronto para validar

## Riscos

| Risco | Probabilidade | Mitigação |
|-------|--------------|-----------|
| Seed cria IDs diferentes em prod vs dev | Baixa | `get_or_create` por `nome`, não por ID |
| Grupo "Gerência" tem usuários | Média | Verificar no banco antes de remover |
| Produto sem Projeto correspondente no banco | Alta | Seed de produtos precisa do seed de projetos rodando antes |
| Frontend type `is_super` não vem do serializer | Baixa | Não é usado no CRUD, ignorar por agora |

## Backend pronto (sem mudanças necessárias)

- ✅ `GerenciaViewSet` — `views/admin.py` (linhas 240-272)
- ✅ `ProdutoViewSet` — `views/admin.py` (linhas 207-238)
- ✅ `GerenciaSerializer` — `serializers/organizacao.py` (linhas 116-143)
- ✅ `ProdutoSerializer` — `serializers/organizacao.py` (linhas 155-176)
- ✅ Rotas `/api/gerencias/` e `/api/produtos/` — `urls.py` (linha 123)
