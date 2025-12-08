# Plano de Implementação: RBAC com Grupos de Setor + Função

**Data de Criação**: 2025-12-05
**Status**: 🟢 Fases 1-5 Completas (incluindo Testes)
**PRs relacionados**: #238 (fix RBAC), #239 (Setor + Função), #240 (Todos os Setores), #241 (Admin Interface), #242 (Testes)

---

## Contexto

O sistema atual usa grupos simples (Superintendência, DAT, Controle, etc.) sem distinção entre onde o usuário trabalha (setor) e o que ele pode fazer (função).

### Problema
- Formadores, Coordenadores, Apoios e Gerentes da Superintendência têm o mesmo grupo
- Não há como distinguir um Gerente (que pode aprovar) de um Formador (que não pode)

### Solução
Criar dois tipos de grupos:
- **Grupos de SETOR**: Onde o usuário trabalha (Superintendência, DAT, Controle, etc.)
- **Grupos de FUNÇÃO**: O que o usuário pode fazer (Formador, Coordenador, Apoio, Gerente)

---

## Fases de Implementação

### Fase 1: Criação dos Grupos (Backend) ✅
- [x] **1.1** Criar migration para os novos grupos (PR #239)
  - Grupos de SETOR iniciais: Superintendência, DAT, Controle, Gerência
  - Grupos de FUNÇÃO: Formador, Coordenador, Apoio de Coordenação, Gerente
  - Migration: `0042_rbac_setor_funcao_groups.py`
- [x] **1.2** Criar migration para TODOS os setores (PR #240)
  - Grupos de SETOR (Gerências): Vidas, Fluir, ACerta, Brincando, Sou da Paz
  - Migration: `0043_add_all_setor_groups.py`
- [x] **1.3** Criar management command para migrar usuários existentes
  - Comando: `python manage.py migrate_rbac_groups`
  - Opções: `--dry-run`, `--user <username>`, `--add-gerente <username>`
- [x] **1.4** Testar migrations em ambiente de desenvolvimento

### Fase 2: Atualizar Backend (API) ✅
- [x] **2.1** Atualizar endpoint `/api/me/` para retornar `setores` e `funcoes`
  - Retorna: `setores`, `funcoes`, `can_approve_super`
- [x] **2.2** Criar helpers de permissão (inline em user.py)
  ```python
  can_approve_super = user.is_superuser or (
      "Gerente" in funcoes and "Superintendência" in setores
  )
  ```
- [x] **2.3** Atualizar views de aprovação para usar novos helpers
- [ ] **2.4** Adicionar testes unitários para helpers (futuro)

### Fase 3: Atualizar Frontend ✅
- [x] **3.1** Atualizar lógica de permissões no `App.jsx`
  - Usa `setores`, `funcoes`, `can_approve_super` da API
- [x] **3.2** Atualizar `ApprovalsPage.jsx` com nova lógica
  - Usa `can_approve_super` para mostrar botões
- [x] **3.3** Atualizar `HomePage.jsx` para mostrar seções corretas
  - Usa `canApproveSuper` para seção de Aprovações
- [x] **3.4** Testar todas as combinações de setor + função (manual)
  - 8/8 testes passaram via API /api/me/
  - Corrigido views_basic.py para incluir setores, funcoes, can_approve_super

### Fase 4: Admin e Interface ✅
- [x] **4.1** Atualizar Admin DAT para gerenciar setores e funções
  - Tabela: colunas separadas "Setor" (purple) e "Função" (blue/gold)
  - Modal: selects separados para Setor e Função com tooltips
- [x] **4.2** Criar visualização clara dos grupos do usuário
  - Tags coloridas: Setor=purple, Função=blue, Gerente=gold
- [x] **4.3** Permitir edição de setores e funções na interface
  - Form com Divider "Grupos RBAC"
  - Nota sobre regra de aprovação SUPER

### Fase 5: Testes e Validação ✅
- [x] **5.1** Testes unitários para helpers de permissão (20 testes)
  - TestRBACConstants: 5 testes (SETOR_GROUPS, FUNCAO_GROUPS)
  - TestCanApproveSuperLogic: 9 testes (todas combinações)
  - TestApiMeEndpoint: 6 testes (estrutura resposta)
- [x] **5.2** Testes de integração para endpoints (incluídos em 5.1)
- [x] **5.3** Testes E2E para fluxo RBAC (Playwright)
  - 2 testes: login page + login flow
  - Configuração Playwright completa
- [ ] **5.4** Validar com usuários reais (manual - pendente)

### Fase 6: Documentação e Deploy
- [ ] **6.1** Atualizar CLAUDE.md com nova estrutura
- [ ] **6.2** Criar documentação para administradores
- [ ] **6.3** Migrar usuários de produção
- [ ] **6.4** Deploy em staging para validação final

---

## Estrutura de Grupos

### Grupos de SETOR (onde o usuário trabalha)
| Grupo | Gerência | Fluxo | Descrição |
|-------|----------|-------|-----------|
| Superintendência | SUPERINTENDENCIA | SUPER | Setor estratégico |
| Vidas | GERENCIA 2 | NAO_SUPER | Projetos Vida e Ciências/Linguagem/Matemática |
| Fluir | GERENCIA 3 | NAO_SUPER | Projeto Fluir das Emoções |
| ACerta | GERENCIA 4 | NAO_SUPER | Projetos ACerta Matemática/Português |
| Brincando | GERENCIA 5 | NAO_SUPER | Projeto Brincando e Aprendendo |
| Sou da Paz | GERENCIA 6 | NAO_SUPER | Projeto Sou da Paz |
| DAT | - | - | Departamento de Apoio Técnico |
| Controle | - | - | Setor de Controle (operações) |
| Gerência | - | - | Gerência genérica |

### Grupos de FUNÇÃO (o que o usuário pode fazer)
| Grupo | Permissões |
|-------|------------|
| Formador | Visualiza grade, gerencia bloqueios pessoais |
| Coordenador | Cria solicitações de eventos |
| Apoio | Auxilia coordenação, visualiza solicitações |
| Gerente | Aprova/reprova, acessa dashboards e relatórios |

---

## Matriz de Permissões

| Ação | Formador | Coordenador | Apoio | Gerente |
|------|----------|-------------|-------|---------|
| Ver grade mensal | ✅ | ✅ | ✅ | ✅ |
| Gerenciar bloqueios pessoais | ✅ | ✅ | ✅ | ✅ |
| Criar solicitações | ❌ | ✅ | ✅ | ✅ |
| Ver minhas solicitações | ❌ | ✅ | ✅ | ✅ |
| Aprovar/Reprovar (setor) | ❌ | ❌ | ❌ | ✅ |
| Ver dashboards | ❌ | ❌ | ❌ | ✅ |
| Ver relatórios | ❌ | ❌ | ❌ | ✅ |

---

## Exemplos de Usuários

| Usuário | Setor | Função | Pode Aprovar SUPER? |
|---------|-------|--------|---------------------|
| Maria | Superintendência | Gerente | ✅ Sim |
| João | DAT | Gerente | ❌ Não (só DAT) |
| Pedro | Superintendência | Formador | ❌ Não |
| Ana | Superintendência | Coordenador | ❌ Não |
| Carlos | Controle | Gerente | ❌ Não (só Controle) |

---

## Código de Referência

### Backend - Helper de Permissão
```python
# apps/core/views/user.py

SETOR_GROUPS = [
    # Gerências de projeto
    'Superintendência',  # SUPERINTENDENCIA - Fluxo SUPER
    'Vidas',             # GERENCIA 2 - Fluxo NAO_SUPER
    'Fluir',             # GERENCIA 3 - Fluxo NAO_SUPER
    'ACerta',            # GERENCIA 4 - Fluxo NAO_SUPER
    'Brincando',         # GERENCIA 5 - Fluxo NAO_SUPER
    'Sou da Paz',        # GERENCIA 6 - Fluxo NAO_SUPER
    # Setores administrativos/operacionais
    'DAT',               # Departamento de Apoio Técnico
    'Controle',          # Setor de Controle
    'Gerência',          # Gerência genérica
]
FUNCAO_GROUPS = ['Formador', 'Coordenador', 'Apoio de Coordenação', 'Gerente']

# Na CurrentUserView.get():
setores = [g for g in groups if g in SETOR_GROUPS]
funcoes = [g for g in groups if g in FUNCAO_GROUPS]
can_approve_super = is_superuser or ("Gerente" in funcoes and "Superintendência" in setores)
```

### Frontend - Lógica de Permissão
```javascript
// Extrair setores e funções
const setores = user?.setores || [];
const funcoes = user?.funcoes || [];

// Verificar permissões
const isGerente = funcoes.includes('Gerente');
const isSuper = setores.includes('Superintendência');
const canApproveSuper = isGerente && isSuper;
```

---

## Histórico de Progresso

| Data | Fase | Descrição | Status |
|------|------|-----------|--------|
| 2025-12-05 | - | Plano criado | ✅ |
| 2025-12-05 | 1 | Migration 0042 + management command | ✅ PR #239 |
| 2025-12-05 | 2 | API /api/me/ com setores/funcoes/can_approve_super | ✅ PR #239 |
| 2025-12-05 | 3 | Frontend App.jsx, ApprovalsPage, HomePage | ✅ PR #239 |
| 2025-12-05 | 1.2 | Migration 0043 + todos os setores (Vidas, Fluir, ACerta, Brincando, Sou da Paz) | ✅ PR #240 |
| 2025-12-05 | 3.4 | Testes manuais 8/8 + fix views_basic.py | ✅ |
| 2025-12-05 | 4 | Admin DAT: tabela setor/função, form separado, tags coloridas | ✅ PR #241 |
| 2025-12-08 | 5 | Testes unitários (20) + E2E Playwright (2) | ✅ PR #242 |

---

## Notas e Decisões

- Manter grupos antigos durante migração para compatibilidade
- Usar prefixo nos grupos? Ex: `SETOR_Superintendência`, `FUNCAO_Gerente`?
  - **Decisão**: Não usar prefixo, identificar por lista predefinida
- Superusers (`is_superuser=True`) continuam com acesso total

