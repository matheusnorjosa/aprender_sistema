# 🔐 RBAC Completo - Grupos, Permissões e Controle de Acesso - AS v2

**Data**: 2025-12-05
**Versão**: v3.0
**Status**: ✅ Atualizado com estrutura RBAC Setor + Função (PRs #239, #240)

---

## 📊 Estatísticas Atuais (01/12/2025)

**Total de usuários cadastrados**: 128

| Grupo | Usuários | % Total | Status |
|-------|----------|---------|--------|
| **Formador** | 90 | 70.3% | ✅ Ativo |
| **Coordenador** | 37 | 28.9% | ✅ Ativo |
| **Controle** | 2 | 1.6% | ✅ Ativo |
| **DAT** | 1 | 0.8% | ✅ Ativo |
| **Superintendência** | 1 | 0.8% | ✅ Ativo |
| **Gerência** | 0 | 0.0% | ⚠️ Grupo existe mas sem usuários |
| **Apoio de Coordenação** | 0 | 0.0% | ✨ **NOVO** - Pronto para atribuição |
| **Superuser** (flag) | 1 | 0.8% | ✅ Ativo |

---

## 🏷️ 1. GRUPOS DO SISTEMA (Django Groups) - RBAC Setor + Função

> **NOVA ESTRUTURA (PRs #239, #240)**: O sistema agora usa dois tipos de grupos:
> - **Grupos de SETOR**: Onde o usuário trabalha (gerência/departamento)
> - **Grupos de FUNÇÃO**: O que o usuário pode fazer (papel/cargo)

### Grupos de SETOR (onde trabalha)

| # | Grupo | Gerência | Fluxo | Descrição |
|---|-------|----------|-------|-----------|
| 1 | **Superintendência** | SUPERINTENDENCIA | SUPER | Setor estratégico - aprovação de solicitações SUPER |
| 2 | **Vidas** | GERENCIA 2 | NAO_SUPER | Projetos Vida e Ciências/Linguagem/Matemática |
| 3 | **Fluir** | GERENCIA 3 | NAO_SUPER | Projeto Fluir das Emoções |
| 4 | **ACerta** | GERENCIA 4 | NAO_SUPER | Projetos ACerta Matemática/Português |
| 5 | **Brincando** | GERENCIA 5 | NAO_SUPER | Projeto Brincando e Aprendendo |
| 6 | **Sou da Paz** | GERENCIA 6 | NAO_SUPER | Projeto Sou da Paz |
| 7 | **DAT** | - | - | Departamento de Apoio Técnico |
| 8 | **Controle** | - | - | Setor de Controle (operações) |
| 9 | **Gerência** | - | - | Gerência genérica |

### Grupos de FUNÇÃO (o que pode fazer)

| # | Grupo | Descrição | Permissões Principais |
|---|-------|-----------|----------------------|
| 1 | **Gerente** | Pode aprovar (se Superintendência) | Aprovar/reprovar, dashboards |
| 2 | **Coordenador** | Cria solicitações de eventos | Criar solicitações |
| 3 | **Apoio de Coordenação** | Auxilia coordenadores | Criar solicitações + view usuarios |
| 4 | **Formador** | Executa eventos, bloqueia agenda | Gerenciar bloqueios |

### Regra de Aprovação SUPER

> **Atualização hardening RBAC (2026-04-29 — PR 3 #1308 e PR 10 #1315):**
> a regra original `can_approve_super = is_superuser OR (Gerente + Superintendência)` foi
> substituída pela policy composite `access_solicitation_approvals`. O campo
> `can_approve_super` permanece em `/api/me/` apenas como **legacy compat**;
> não é fonte de decisão no frontend nem nos gates dos endpoints de aprovação.

Policy oficial:

```python
# Pode aprovar solicitações SUPER se:
access_solicitation_approvals = is_superuser OR (
    ("Gerente" IN funcoes AND "Superintendência" IN setores)  # Gerente da Sup
    OR
    ("Assistente Administrativo" IN funcoes AND "Controle" IN setores)  # Asst Admin Controle
)
```

**Exemplos**:
| Usuário | Setor | Função | Pode aprovar SUPER? |
|---------|-------|--------|---------------------|
| Maria | Superintendência | Gerente | ✅ Sim (Gerente da Superintendência) |
| Carla | Controle | Assistente Administrativo | ✅ Sim (composite Asst Admin Controle, PR 3 #1308) |
| João | Superintendência | Formador | ❌ Não (sem Função Gerente) |
| Pedro | Vidas | Gerente | ❌ Não (Gerente pedagógico, setor diferente) |
| Ana | Controle | — | ❌ Não (Controle puro, sem Função Asst Admin) |
| Bruno | DAT | — | ❌ Não (DAT não aprova após PR 3) |

**Nota**: Um usuário pode pertencer a **múltiplos grupos** de ambos os tipos. A policy
exige composite (AND) entre Setor e Função — pertencer a um sem o outro nega.

---

## 🔑 2. FLAGS ESPECIAIS DE USUÁRIO

Além dos grupos, o Django possui flags especiais no modelo `Usuario` (AbstractUser):

| Flag | Tipo | Descrição | Usuários | Onde é setado |
|------|------|-----------|----------|---------------|
| **is_superuser** | Boolean | Administrador do sistema (bypass de todas as permissões) | 1 | Django Admin / createsuperuser |
| **is_staff** | Boolean | Pode acessar Django Admin (/admin/) | 1 | Django Admin |
| **is_superintendencia** | Calculado | `is_superuser OR 'Superintendência' in groups` | 2 | Endpoint `/api/auth/me/` (views_auth.py:135) |

**⚠️ Importante**: `is_superintendencia` **não é campo do banco**, é computed no backend e retornado via API.

---

## 💼 3. CARGOS (Campo `cargo` no modelo Usuario)

Cargos são **descritivos** (campo de texto livre), **não controlam acesso**.

| Cargo | Descrição | Relação com Grupo |
|-------|-----------|-------------------|
| **Administrador do Sistema** | Admin técnico | Geralmente `is_superuser` |
| **Superintendência** | Nível estratégico | Grupo Superintendência |
| **Gerente** | Nível gerencial | Grupo Gerência |
| **Coordenador** | Coordena projetos | Grupo Coordenador |
| **Formador** | Executa eventos | Grupo Formador |
| **Operacional** | Suporte operacional | Grupo Controle ou DAT |

**⚠️ Importante**: Cargo é apenas informativo. Permissões são controladas por **grupos**, não por cargo.

---

## 🎯 4. PERFIS/PAPÉIS (Frontend - App.jsx)

No frontend, a lógica de permissões usa a estrutura **Setor + Função**:

```javascript
// App.jsx - Nova estrutura RBAC (PR #239)

// Extrair setores e funções da API
const setores = user?.setores || [];
const funcoes = user?.funcoes || [];

// Permissões baseadas em FUNÇÃO
const isGerente = user?.is_superuser || funcoes.includes('Gerente');
const isCoordenador = funcoes.includes('Coordenador') || funcoes.includes('Apoio de Coordenação');

// Permissões baseadas em SETOR
const inDAT = setores.includes('DAT');
const inControle = setores.includes('Controle');
const inGerencia = setores.includes('Gerência');

// Permissões compostas (Setor + Função)
// [legacy] canApproveSuper continua em usePermissions por contrato externo,
// mas o frontend NÃO o consulta para gating de Aprovações (PR 10 #1315).
// Fonte de verdade: policy `access_solicitation_approvals` via getMyPolicies().
const canApproveSuper = user?.can_approve_super || false;  // legacy compat
const canCoordenador = user?.is_superuser || isCoordenador || inDAT;
const canControle = user?.is_superuser || inControle;
const canDAT = user?.is_superuser || inDAT;
const isAdmin = user?.is_superuser;
const isManager = isGerente && (inGerencia || isAdmin);
```

**Endpoint `/api/me/` retorna**:

```json
{
  "id": 1,
  "username": "maria",
  "setores": ["Superintendência"],
  "funcoes": ["Gerente"],
  "can_approve_super": true,
  "is_superintendencia": true,
  "is_superuser": false
}
```

> **⚠️ Legado:** `can_approve_super` continua no payload por **compatibilidade de contrato**
> com clientes externos, mas o frontend deixou de consultá-lo em PR 10 (#1315). A fonte oficial
> de autorização para Aprovações é `GET /api/me/policies/` retornando
> `access_solicitation_approvals`. Para novas integrações, prefira `policies` direto.

---

## 🛡️ 5. PERMISSÕES POR GRUPO (Django - seed_rbac.py)

### 🔴 Superintendência (Aprovação)

**Permissões Django**:
- `view_solicitacao`, `change_solicitacao` (aprovar/reprovar)
- `view_usuario`, `view_municipio`, `view_projeto` (referências)

**Total**: 5 permissões

**Acesso a páginas**:
- `/aprovacoes` ✅ (exclusivo)
- `/dashboards`, `/dashboards/equipe`, `/mapa-brasil`, `/dashboard/gcal` ✅
- `/controle/etl-reports` ✅

---

### 🟡 Gerência (Dashboards)

**Permissões Django**:
- `view_solicitacao` (apenas leitura)

**Total**: 1 permissão

**Acesso a páginas**:
- `/dashboards`, `/dashboards/equipe`, `/mapa-brasil` ✅
- `/aprovacoes` ✅ (herda de isManager)

**⚠️ Status**: Grupo criado mas **sem usuários** (0).

---

### 🟢 Controle (Operações)

**Permissões Django**:
- `view_municipio`, `view_projeto`, `view_compra`, `add_compra`
- `add/change/delete/view_availabilityblock` (bloqueios)

**Total**: 8 permissões

**Acesso a páginas**:
- `/pre-agenda` ✅ (exclusivo - publicar eventos)
- `/dashboard/gcal` ✅ (monitorar publicações)
- `/dashboards/equipe` ✅
- `/controle`, `/dat`, `/deslocamentos` ✅
- `/controle/etl-reports` ✅

---

### 🔵 DAT (Administração de Dados)

**Permissões Django**:
- `add/change/delete/view_usuario` (CRUD completo)
- `add/change/delete/view_municipio` (CRUD completo)
- `view/add_solicitacao` (criar + visualizar)

**Total**: 10 permissões

**Acesso a páginas**:
- `/admin-dat/*` ✅ (exclusivo - 6 páginas)
- `/solicitacoes/minhas`, `/solicitacoes/nova` ✅
- `/deslocamentos` ✅

---

### 🟣 Coordenador (Solicitações)

**Permissões Django**:
- `add/view_solicitacao` (criar + visualizar)
- `view_municipio`, `view_projeto` (referências)

**Total**: 4 permissões

**Acesso a páginas**:
- `/solicitacoes/minhas`, `/solicitacoes/nova` ✅
- `/deslocamentos` ✅

---

### 🟣 Apoio de Coordenação (Auxiliar Coordenador) ✨ NOVO

**Permissões Django**:
- `add/view_solicitacao` (criar + visualizar - **mesmas do Coordenador**)
- `view_municipio`, `view_projeto` (referências)
- `view_usuario` (**adicional** - para auxiliar coordenador na gestão de formadores)

**Total**: 5 permissões

**Acesso a páginas**:
- `/solicitacoes/minhas`, `/solicitacoes/nova` ✅ (via `canCoordenador`)
- `/deslocamentos` ✅

**Diferença do Coordenador**: Acesso a lista de usuários (`view_usuario`) para auxiliar na gestão.

**Status**: Grupo criado em 2025-12-01, pronto para atribuição (0 usuários).

---

### ⚪ Formador (Bloqueios)

**Permissões Django**:
- `add/change/delete/view_availabilityblock` (gerenciar bloqueios)
- `view_solicitacao` (ver eventos)

**Total**: 5 permissões

**Acesso a páginas**:
- `/disponibilidade`, `/bloqueios`, `/home` ✅

---

## 📋 6. PÁGINAS ACESSÍVEIS POR PERFIL

### 🔴 Superuser (is_superuser)

**Total**: 22 páginas (TODAS)

**Rotas**:
- `/home`, `/disponibilidade`, `/bloqueios`
- `/dashboards`, `/dashboards/equipe`, `/dashboard/gcal`, `/mapa-brasil`
- `/solicitacoes/minhas`, `/solicitacoes/nova`
- `/aprovacoes`, `/pre-agenda`
- `/deslocamentos`, `/controle`, `/dat`, `/controle/etl-reports`
- `/admin-dat/*` (6 páginas)

**HomePage Cards**: 6 ativos + 2 desabilitados

---

### 🟠 Superintendência

**Total**: 11 páginas

**Rotas**:
- `/home`, `/disponibilidade`, `/bloqueios`
- `/dashboards`, `/dashboards/equipe`, `/dashboard/gcal`, `/mapa-brasil`
- `/aprovacoes` ✅
- `/controle/etl-reports`
- `/controle`, `/dat`

**HomePage Cards**: 2 ativos + 1 desabilitado

---

### 🟡 Gerência

**Total**: 11 páginas

**Rotas**:
- `/home`, `/disponibilidade`, `/bloqueios`
- `/dashboards`, `/dashboards/equipe`, `/mapa-brasil` ✅
- `/aprovacoes` (via isManager)
- `/controle/etl-reports`
- `/controle`, `/dat`

**HomePage Cards**: 3 ativos + 2 desabilitados

**⚠️ Status**: 0 usuários atribuídos ao grupo

---

### 🟢 Controle

**Total**: 11 páginas

**Rotas**:
- `/home`, `/disponibilidade`, `/bloqueios`
- `/dashboards/equipe`, `/dashboard/gcal` ✅
- `/aprovacoes`, `/pre-agenda` ✅
- `/deslocamentos`, `/controle`, `/dat`
- `/controle/etl-reports`

**HomePage Cards**: 2 ativos + 1 desabilitado

---

### 🔵 DAT

**Total**: 14 páginas

**Rotas**:
- `/home`, `/disponibilidade`, `/bloqueios`
- `/solicitacoes/minhas`, `/solicitacoes/nova`
- `/deslocamentos`, `/controle`, `/dat`
- `/admin-dat/*` (6 páginas) ✅

**HomePage Cards**: 3 ativos

---

### 🟣 Coordenador

**Total**: 7 páginas

**Rotas**:
- `/home`, `/disponibilidade`, `/bloqueios`
- `/solicitacoes/minhas`, `/solicitacoes/nova` ✅
- `/deslocamentos`
- `/controle`, `/dat`

**HomePage Cards**: 3 ativos

---

### 🟣 Apoio de Coordenação ✨ NOVO

**Total**: 7 páginas (mesmas do Coordenador)

**Rotas**:
- `/home`, `/disponibilidade`, `/bloqueios`
- `/solicitacoes/minhas`, `/solicitacoes/nova` ✅ (via `canCoordenador`)
- `/deslocamentos`
- `/controle`, `/dat`

**HomePage Cards**: 3 ativos (mesmos do Coordenador)

**Status**: Grupo criado em 2025-12-01, 0 usuários atribuídos.

---

### ⚪ Formador

**Total**: 5 páginas

**Rotas**:
- `/home`, `/disponibilidade`, `/bloqueios` ✅
- `/controle`, `/dat` ⚠️

**HomePage Cards**: 1 ativo

---

## 🏠 7. HOMEPAGE - CARDS POR PERFIL

### Estrutura HomePage (4 seções)

#### 1️⃣ Acesso Administrativo (`isAdmin`)
- **Gerenciamento de Usuários** → `/admin-dat/usuarios` (apenas se `canDAT`)
- **Configurações do Sistema** → desabilitado
- **Análises** → `/dashboards`

#### 2️⃣ Acesso Gerencial (`isManager`)
- **Solicitações de Aprovação** → `/aprovacoes` (badge: pendências)
- **Desempenho da Equipe** → desabilitado

#### 3️⃣ Acesso Geral (todos)
- **Meu Painel** → `/disponibilidade`
- **Enviar Solicitação** → `/solicitacoes/nova` (apenas `isCoordenador`)
- **Minhas Solicitações** → `/solicitacoes/minhas` (apenas `isCoordenador`)

#### 4️⃣ Resumo Rápido (KPIs)
- **Eventos Futuros** (todos)
- **Minhas Solicitações** (`isCoordenador`)
- **Aprovações Pendentes** (`isManager`)

---

## ⚠️ 8. VULNERABILIDADES IDENTIFICADAS

### 🚨 Rotas SEM proteção RBAC

| Rota | Proteção Atual | Problema | Correção Necessária |
|------|----------------|----------|---------------------|
| `/controle` | ❌ Nenhuma | Qualquer usuário autenticado pode acessar | `canControle ? <Page /> : <Forbidden />` |
| `/dat` | ❌ Nenhuma | Qualquer usuário autenticado pode acessar | `canDAT ? <Page /> : <Forbidden />` |

**Impacto**: Formadores e Coordenadores podem acessar páginas operacionais sem permissão.

---

## 🔄 9. MÚLTIPLOS GRUPOS

### Herança de Permissões

Quando um usuário tem **múltiplos grupos**, as permissões são **cumulativas** (união de todas).

**Exemplos práticos**:

| Combinação | Efeito | Caso de Uso |
|------------|--------|-------------|
| **DAT + Coordenador** | Pode criar solicitações + administrar dados | Usuário que gerencia dados e também coordena projetos |
| **Controle + Superintendência** | Operações + Aprovações | Usuário de confiança com poderes amplos |
| **Gerência + Superintendência** | Dashboards + Aprovações | Gerente que também aprova |
| **Formador + Coordenador** | Executa + Coordena | Formador que também coordena projetos |

---

## 🏢 10. SETORES/DEPARTAMENTOS

O AS v2 **não tem modelo de Setor/Departamento** explícito. A organização é feita por:

1. **Grupos** (papéis funcionais)
2. **Projetos** (modelo `Projeto` - agrupa solicitações)
3. **Municípios** (modelo `Municipio` - agrupa por localização)

**Consulte**: `docs/MAPEAMENTO_COMPLETO_SETORES_GERENCIAS.md` para estrutura organizacional da empresa.

---

## 📊 11. HIERARQUIA DE ACESSO

```
is_superuser (1 usuário)
    └── Acesso total (bypass de todas as regras)

Superintendência (1 usuário)
    ├── Aprovar/reprovar solicitações
    ├── Dashboards estratégicos
    └── Relatórios ETL

Gerência (0 usuários) ⚠️
    ├── Dashboards estratégicos
    ├── Mapa do Brasil
    └── Aprovações (via isManager)

Controle (2 usuários)
    ├── Publicar eventos (Pré-agenda)
    ├── Dashboard GCal
    ├── Importar dados (ETL)
    └── Operações (Controle, DAT)

DAT (1 usuário)
    ├── Administrar usuários
    ├── Administrar municípios
    ├── Criar solicitações
    └── Admin DAT

Coordenador (37 usuários)
    ├── Criar solicitações
    ├── Ver minhas solicitações
    └── Gerenciar deslocamentos

Formador (90 usuários)
    ├── Bloquear agenda
    ├── Ver disponibilidade
    └── Ver eventos
```

---

## 🔧 12. COMO ATRIBUIR/VERIFICAR GRUPOS

### Via Django Admin

```
1. Acessar http://localhost:8002/admin/core/usuario/
2. Editar usuário
3. Seção "Permissions" → "Groups" → Selecionar grupos
4. Salvar
```

### Via Django Shell

```python
from django.contrib.auth.models import Group
from apps.core.models import Usuario

user = Usuario.objects.get(username='joao.silva')
grupo = Group.objects.get(name='Coordenador')
user.groups.add(grupo)
```

### Via Management Command

```bash
# Criar grupos (idempotente)
python manage.py seed_rbac --verbose

# Atribuir grupos faltantes baseado em padrões
python manage.py backfill_user_groups --apply
```

---

## 🛡️ 13. TRIPLA CAMADA DE SEGURANÇA

### Camada 1: Menu (UI)
- **Arquivo**: `App.jsx`
- **Função**: Oculta itens do menu que o usuário não pode acessar
- **Método**: Condicionais React baseadas nas flags de permissão

### Camada 2: Rotas (Frontend)
- **Arquivo**: `App.jsx`
- **Função**: Bloqueia acesso direto via URL
- **Método**: `element={canX ? <Page /> : <Forbidden />}`
- **Resultado**: 403 Forbidden se tentar acessar sem permissão

### Camada 3: Backend API (Django)
- **Arquivo**: `views.py`, `permissions.py`
- **Função**: Validação final no servidor
- **Método**: Django Rest Framework `permission_classes`
- **Resultado**: 401/403 se não autorizado

---

## ❓ 14. FAQ

### 1. Qual a diferença entre grupo e cargo?
- **Grupo**: Controla permissões e acesso (RBAC) ✅
- **Cargo**: Campo descritivo, não afeta acesso ❌

### 2. Um usuário pode ter múltiplos grupos?
Sim! E as permissões são **cumulativas** (união de todas as permissões).

### 3. O que é is_superintendencia?
Flag calculada no backend: `is_superuser OR 'Superintendência' in groups`
Não é campo do banco, é retornada pelo endpoint `/api/auth/me/`

### 4. Por que Gerência tem 0 usuários?
Grupo foi criado para uso futuro (seed_rbac.py), mas ainda não foi atribuído a ninguém.

### 5. Como criar um novo grupo?
1. Adicionar em `apps/core/management/commands/seed_rbac.py` (lista GROUPS)
2. Definir permissões em PERMS_BY_GROUP
3. Rodar `python manage.py seed_rbac`

### 6. Por que /controle e /dat não têm proteção?
⚠️ **Vulnerabilidade identificada**. Precisa ser corrigido adicionando RBAC nas rotas (App.jsx).

### 7. Como ver os grupos de um usuário?
```python
user = Usuario.objects.get(username='joao.silva')
print(list(user.groups.values_list('name', flat=True)))
```

### 8. O que acontece se um usuário tentar acessar via URL direta?
- Se rota **COM proteção**: Vê tela 403 Forbidden
- Se rota **SEM proteção** (/controle, /dat): **Consegue acessar** ⚠️

### 9. Como atribuir gerentes ao grupo Gerência?
```bash
# Via management command (quando criado)
python manage.py seed_gerentes --apply

# Ou via shell
from django.contrib.auth.models import Group
from apps.core.models import Usuario

grupo_gerencia = Group.objects.get(name='Gerência')
gerente = Usuario.objects.get(username='fulano')
gerente.groups.add(grupo_gerencia)
```

### 10. Diferença entre is_superuser e Superintendência?
- **is_superuser**: Flag Django, bypass total de permissões, acesso ao Django Admin
- **Superintendência**: Grupo funcional, aprova solicitações SUPER, não tem acesso ao Django Admin

---

## 📝 15. RESUMO COMPARATIVO

| Aspecto | Valor |
|---------|-------|
| **Total de usuários** | 128 |
| **Total de grupos** | 6 |
| **Grupo mais populoso** | Formador (90 usuários, 70.3%) |
| **Grupo vazio** | Gerência (0 usuários) |
| **Páginas totais** | 22 |
| **Páginas protegidas** | 15 |
| **Páginas públicas** | 3 (home, disponibilidade, bloqueios) |
| **Páginas vulneráveis** | 2 (/controle, /dat) ⚠️ |
| **Permissões Django** | 33 (total em PERMS_BY_GROUP) |
| **Flags especiais** | 3 (is_superuser, is_staff, is_superintendencia) |

---

## 🔗 DOCUMENTAÇÃO RELACIONADA

- **Páginas e Fluxos**: `.agents/outbox/PERMISSOES-POR-PERFIL.md`
- **Estrutura Organizacional**: `docs/MAPEAMENTO_COMPLETO_SETORES_GERENCIAS.md`
- **Arquitetura Geral**: `docs/PROJETO_ORIGEM.md`
- **Código RBAC**: `apps/core/management/commands/seed_rbac.py`

---

**Última Atualização**: 2025-12-01 15:10 BRT
**Revisão**: v2.0
**Dados**: Consulta em tempo real ao banco PostgreSQL (128 usuários)
**Status**: ✅ **ATUALIZADO E COMPLETO**
