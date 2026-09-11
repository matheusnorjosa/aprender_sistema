# Guia do Administrador: Sistema RBAC (Setor + Função)

Este guia explica como gerenciar permissões de usuários no Aprender Sistema v2.

**Revisto em 2026-07-24** contra `apps/core/constants.py`, `apps/core/rbac/policies.py`,
`apps/core/views/admin.py` e as telas do frontend. Correções principais desta revisão:
as listas de Setor (9 → **13**) e Função (4 → **5**), o terceiro caminho de aprovação SUPER
(Assistente Administrativo do Controle) e o fato de que **editar grupos virou superuser-only**.

SSOT das listas: `SETOR_GROUPS`/`FUNCAO_GROUPS` (`v2/backend/apps/core/constants.py`).

---

## Conceito Básico

O sistema usa **duas dimensões** para controlar permissões:

1. **SETOR** - Onde o usuário trabalha
2. **FUNÇÃO** - O que o usuário pode fazer

Cada usuário pode ter **um ou mais setores** e **uma ou mais funções**.

---

## Grupos de SETOR

São **13** (`SETOR_GROUPS`, `apps/core/constants.py`). A lista abaixo estava com 9 até 2026-07-24 e ainda
incluía um grupo **"Gerência"** que não existe.

| Setor | Descrição | Fluxo |
|-------|-----------|-------|
| **Superintendência** | Setor estratégico | SUPER (requer aprovação) |
| **Vidas** | Gerência 2 - Projetos Vida | NAO_SUPER |
| **Fluir** | Gerência 3 - Projeto Fluir | NAO_SUPER |
| **ACerta** | Gerência 4 - Projetos ACerta | NAO_SUPER |
| **Brincando** | Gerência 5 - Brincando e Aprendendo | NAO_SUPER |
| **Sou da Paz** | Gerência 6 - Projeto Sou da Paz | NAO_SUPER |
| **DAT** | Departamento de Apoio Técnico | - |
| **Controle** | Setor de Controle (operações) | - |
| **Diretoria** | Acesso a dashboards | - |
| **Comercial** | Operação de ações/notificações | - |
| **Relacionamento** | Operação de ações/notificações | - |
| **Logística Viagens** | Operação de ações/notificações | - |
| **Logística Galpão** | Operação de ações/notificações | - |

> ❌ **Não existe grupo "Gerência".** "Gerente" é uma **Função**; as gerências de projeto são os
> setores nomeados acima (Vidas, Fluir, ACerta, …).

---

## Grupos de FUNÇÃO

São **5** (`FUNCAO_GROUPS`, `apps/core/constants.py`).

| Função | O que pode fazer |
|--------|------------------|
| **Formador** | Visualiza grade mensal, gerencia bloqueios pessoais |
| **Coordenador** | Cria solicitações de eventos para sua equipe |
| **Apoio de Coordenação** | Auxilia coordenação, visualiza solicitações |
| **Gerente** | Aprova/reprova solicitações (quando no Setor Superintendência), acessa dashboards |
| **Assistente Administrativo** | Combinada com o Setor **Controle**, aprova solicitações (composite, PR 3 / #1308) |

---

## Quem Pode Aprovar Solicitações SUPER?

São **três** caminhos (`_user_has_solicitation_approvals` em `apps/core/rbac/policies.py`, espelhado por
`can_approve_super` em `apps/core/views_basic.py`). A versão anterior deste guia listava só os dois primeiros.

✅ Ser **superusuário** (`_user_has_solicitation_approvals`)

**OU** ter **ambos** (`_user_has_solicitation_approvals`):
- Função **Gerente** + Setor **Superintendência**

**OU** ter **ambos** (`_user_has_solicitation_approvals`, via `user_is_assistente_administrativo_controle`):
- Função **Assistente Administrativo** + Setor **Controle**

### Exemplos

| Usuário | Setor | Função | Pode Aprovar? |
|---------|-------|--------|---------------|
| Maria | Superintendência | Gerente | ✅ **Sim** |
| Beatriz | Controle | Assistente Administrativo | ✅ **Sim** (composite #1308) |
| João | DAT | Gerente | ❌ Não (não é Superintendência) |
| Pedro | Superintendência | Formador | ❌ Não (não é Gerente) |
| Ana | Superintendência | Coordenador | ❌ Não (não é Gerente) |
| Carlos | Vidas | Gerente | ❌ Não (não é Superintendência) |
| Rita | Controle | Coordenador | ❌ Não (Controle puro não aprova) |
| Admin | - | - (superuser) | ✅ **Sim** |

---

## Como Gerenciar Usuários

### Acessar a Interface

1. Faça login
2. No menu lateral, abra **DAT** → **Administração** (`/dat/admin`)
   — `v2/frontend/src/components/AppSidebar.tsx`
3. A tela de usuários fica em `/dat/admin/usuarios`
   (`v2/frontend/src/components/AppRoutes.tsx`); não há item de menu direto para ela

*(Corrigido em 2026-07-24: não existe item "Admin DAT" no menu lateral.)*

### Atribuir Grupos a um Usuário — 🔒 **somente superusuário**

> 🔴 **Mudou com o hardening Tier-0 (P0-1).** Editar Setor/Função de um usuário **não é mais
> operação de "administrador"**: é restrita ao superusuário.
>
> - **Frontend**: os selects `setor_ids` e `funcao_ids` são renderizados com
>   `disabled={!currentIsSuperuser}` (`v2/frontend/src/pages/AdminDAT/UsuariosPage.tsx`), e o
>   payload de salvamento **não envia `group_ids`** para não-superuser.
> - **Backend**: a action `assign_groups` é `permission_classes=[SuperuserOnly]`
>   (`apps/core/views/admin.py`).
>
> Em produção há **1 superusuário ativo**. Consequência operacional: se essa conta ficar
> indisponível, **ninguém** consegue atribuir Setor/Função. Isso é um bus factor conhecido —
> ver [audits/ACHADOS_REAIS.md](./audits/ACHADOS_REAIS.md), premissa F3.

Passos (como superusuário):

1. Na lista de usuários, clique no botão **Editar** (ícone de lápis)
2. No modal, você verá:
   - **Setor (onde trabalha)**: selecione um ou mais setores
   - **Função (o que pode fazer)**: selecione uma ou mais funções
3. Clique em **Salvar**

Se os campos aparecerem **desabilitados**, é porque sua conta não é superusuário — não é bug.

### Visualização na Tabela

- **Setor**: Tags em cor **roxa**
- **Função**: Tags em cor **azul** (Gerente aparece em **dourado**)

---

## Cenários Comuns

### Novo Formador da Superintendência
- Setor: Superintendência
- Função: Formador

### Novo Coordenador do projeto Vidas
- Setor: Vidas
- Função: Coordenador

### Gerente que pode aprovar SUPER
- Setor: Superintendência
- Função: Gerente

### Usuário do DAT que gerencia eventos
- Setor: DAT
- Função: Coordenador ou Gerente (dependendo das responsabilidades)

### Usuário que trabalha em múltiplos setores
- Setores: Vidas, Fluir (múltiplos)
- Função: Coordenador

---

## Verificar Permissões de um Usuário

### Via Interface
Na tabela de usuários, observe as tags de Setor e Função.

### Via API
```bash
# Logar como o usuário e acessar:
GET /api/me/

# Resposta inclui:
{
  "setores": ["Superintendência"],
  "funcoes": ["Gerente"],
  "can_approve_super": true
}

# Para autorização atual de Aprovações, prefira:
GET /api/me/policies/
# Resposta: lista de keys públicas; `access_solicitation_approvals` indica
# que o usuário pode aprovar (PR 3 #1308 — composite Setor × Função).
```

> **⚠️ Legado:** `can_approve_super` permanece em `/api/me/` por compat externa.
> Não é fonte de decisão no frontend desde PR 10 (#1315). Use a policy
> `access_solicitation_approvals` via `/api/me/policies/`.

---

## Fluxo de Aprovação

```
┌─────────────────────────────────────────────────────────────┐
│                    FLUXO SUPER                              │
├─────────────────────────────────────────────────────────────┤
│ 1. Coordenador cria solicitação                             │
│ 2. Status = "pendente"                                      │
│ 3. Gerente da Superintendência aprova/reprova               │
│ 4. Se aprovado → vai para pré-agenda                        │
│ 5. Controle cria evento no Google Calendar                  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   FLUXO NAO_SUPER                           │
├─────────────────────────────────────────────────────────────┤
│ 1. Coordenador cria solicitação                             │
│ 2. Status = "aprovado" (automático)                         │
│ 3. Vai direto para pré-agenda                               │
│ 4. Controle cria evento no Google Calendar                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Dúvidas Frequentes

### Por que um Gerente não consegue aprovar?
Verifique se ele está no setor **Superintendência**. Gerente em outro setor não aprova.
O outro caminho é Assistente Administrativo **do Controle**.

### Por que os campos de Setor/Função aparecem desabilitados para mim?
Porque desde o hardening Tier-0 essa edição é **somente superusuário**
(`assign_groups`, `apps/core/views/admin.py`; UI em `UsuariosPage.tsx`). Não é bug.

### Posso dar múltiplas funções a um usuário?
Sim. Por exemplo, alguém pode ser Coordenador e Gerente ao mesmo tempo.

### Como remover um grupo de um usuário?
Na edição do usuário (como superusuário), desmarque o grupo desejado e salve.

⚠️ **O import de usuários NÃO remove grupos — só adiciona.** A concessão de grupos por
`POST /api/usuarios/import/` (coluna `grupos`) **passou a exigir superusuário** — era drift
(issue [#1610](https://github.com/matheusnorjosa/aprender_sistema/issues/1610)), **corrigido**
em `ccbe1e05`: `_actor_pode_atribuir_grupos` (`usuarios_import.py`) faz um ator não-superusuário
ter os grupos ignorados (`grupos_ignorados`), e o importer dedicado impõe allowlist (`run` de
`ExportContractImporter`, `export_contract_importer.py`). Resta o residual
de escopo ator × alvo abrangente, endereçado pelo épico
[#1656](https://github.com/matheusnorjosa/aprender_sistema/issues/1656) —
ver [imports/usuarios.md](./imports/usuarios.md).

### Os grupos são case-sensitive?
Sim para a atribuição via admin. Use exatamente: "Superintendência", "Gerente", etc.
*(O import de usuários resolve com `name__iexact`, ou seja, ignora caixa — mais uma razão
para não usá-lo como via de administração.)*

---

## Referências Técnicas

- **SSOT das listas**: `SETOR_GROUPS` e `FUNCAO_GROUPS` (`apps/core/constants.py`).
  `apps/core/views_basic.py` apenas as importa; em runtime a classificação prefere o model
  `GroupClassificacao` (em `CurrentUserView.get`, `views_basic.py`), com as constantes como fallback.
- **Policies de aprovação**: `_user_has_solicitation_approvals` (`apps/core/rbac/policies.py`)
- **Gate de edição de grupos**: `assign_groups` (`apps/core/views/admin.py`, `SuperuserOnly`)
- **Testes**: `apps/core/tests/test_rbac_permissions.py` (21 testes)
- **Frontend**: `v2/frontend/src/pages/AdminDAT/UsuariosPage.tsx`
- **Convenção RBAC**: [RBAC_NAMING.md](./RBAC_NAMING.md)
- **Matriz de autorização**: [rbac_authorization_matrix.md](./rbac_authorization_matrix.md)
  *(gerada e verificada por guard de drift no CI — não editar à mão)*

*(Removida em 2026-07-24 a referência a `.claude/PLANO_RBAC_SETOR_FUNCAO.md`, que não existe.)*

---

## Telas administrativas existentes (não cobertas por este guia)

Rotas em `v2/frontend/src/components/AppRoutes.tsx`:
`/dat/admin/usuarios`, `/grupos`, `/setores`, `/funcoes`, `/gerencias`, `/produtos`, `/configuracoes`.

A administração de **Grupo × Capability** não fica no frontend: é o Django Admin
(`/admin/core/permissaofuncional/`, `PermissaoFuncionalAdmin` em `apps/core/admin.py`), **superuser-only** desde o #1567.
