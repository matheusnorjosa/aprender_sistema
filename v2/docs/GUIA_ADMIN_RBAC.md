# Guia do Administrador: Sistema RBAC (Setor + Função)

Este guia explica como gerenciar permissões de usuários no Aprender Sistema v2.

**Revisto em 2026-07-24** contra `apps/core/constants.py`, `apps/core/rbac/policies.py`,
`apps/core/views/admin.py` e as telas do frontend. Correções principais desta revisão:
as listas de Setor (9 → **13**) e Função (4 → **5**), o terceiro caminho de aprovação SUPER
(na época, Assistente Administrativo do Controle; desde o PR 11 o Controle aprova pelo vínculo, não pelo
grupo) e o fato de que **editar grupos virou superuser-only**.

SSOT das listas: `SETOR_GROUPS`/`FUNCAO_GROUPS` (`v2/backend/apps/core/constants.py`).

> 🔴 **Desde o PR 12 (17/10/2026, o corte), grupo não dá poder.** O acesso vem só do lugar onde a pessoa
> trabalha: a **lotação** (gerência + papel, no formulário de Usuários). Os grupos de Setor e de Função viram
> **etiquetas** na tabela e no Perfil. Pôr alguém no grupo "DAT", "Controle" ou "Diretoria" (pela tela de
> Grupos, pelo `/admin/` ou por planilha) **não libera nada**. Para dar o acesso do DAT ou do Controle, lote a
> pessoa como **Equipe administrativa** (ou Gerente) na gerência DAT ou CONTROLE. A volta de emergência
> (`RBAC_FONTE=uniao`) e a correção de uma pessoa só estão no [DEPLOY_CHECKLIST.md §9](./DEPLOY_CHECKLIST.md).

---

## Conceito Básico

O que a pessoa pode fazer vem da **lotação**: o vínculo vigente com uma gerência e o **papel** nela
(Formador, Coordenador, Apoio, Gerente ou Equipe administrativa).

1. **Gerência com perfil** (DAT, CONTROLE e, quando existir, DIRETORIA): quem é **Equipe** ou **Gerente** nela
   recebe o pacote do setor (ex.: o DAT administra os cadastros, aprova e opera a Pré-agenda).
2. **Papel em qualquer gerência ativa**: Coordenador, Gerente e Apoio criam e editam eventos da própria
   gerência; o Apoio também publica no Google. Formador e Equipe, nada além do pacote.
3. **Gerente na Superintendência**: aprova as solicitações SUPER da Superintendência.

Os grupos de Setor e de Função abaixo continuam existindo como etiqueta (e para o escopo de algumas listas,
até o PR 13), mas não dão capacidade, tela nem aprovação.

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
| **Formador** | Etiqueta. O papel Formador na lotação gerencia os próprios bloqueios; a Grade Mensal exige papel Gerente, Coordenador ou Apoio na gerência, ou a capacidade `view_all_availability` (`TELAS_DE_ESCOPO`, `apps/core/rbac/policies.py`) |
| **Coordenador** | Cria solicitações de eventos para sua equipe |
| **Apoio de Coordenação** | Auxilia coordenação, visualiza solicitações |
| **Gerente** | Etiqueta. O papel Gerente na lotação cria e edita eventos da gerência; na Superintendência, aprova |
| **Assistente Administrativo** | Etiqueta. Não aprova (PR 11): quem trabalha no Controle aprova pela lotação |

---

## Quem Pode Aprovar Solicitações SUPER?

A regra fica em `solicitation_approval_basis` (`apps/core/rbac/policies.py`), espelhada por
`can_approve_super` em `apps/core/views_basic.py`. Desde o PR B1 (#2070, 29/09/2026) são estes caminhos:

✅ Ser **superusuário**

**OU** estar **lotado como Gerente na gerência Superintendência** (vínculo vigente, sem depender de grupo). É assim
que as aprovadoras são cadastradas: no formulário de Usuários, gerência Superintendência + função Gerente.

**OU** estar **lotado no DAT ou no Controle como Equipe ou Gerente** (vínculo vigente na `GERENCIA DAT` ou na
gerência `CONTROLE`). O pacote do setor dá a capacidade de aprovar (PR 10 e PR 11). Só o superusuário faz essa lotação.

Desde o PR 11 (17/10/2026) **nenhum grupo aprova**: os pares Gerente + Superintendência e Assistente Administrativo +
Controle deixaram de dar o poder. A regra é `solicitation_approval_basis` (`apps/core/rbac/policies.py`).

### Exemplos

| Usuário | Setor | Função | Pode Aprovar? |
|---------|-------|--------|---------------|
| Maria | Superintendência (lotação) | Gerente | ✅ **Sim** (vínculo) |
| Beatriz | Controle (lotação Equipe) | Assistente Administrativo | ✅ **Sim** (pacote do Controle, PR 11) |
| Bruna | Controle (só o grupo, sem lotação) | Assistente Administrativo | ❌ Não (grupo não aprova, PR 11) |
| João | DAT (só o grupo, sem lotação) | Gerente | ❌ Não (grupo não dá poder, PR 12) |
| Pedro | Superintendência | Formador | ❌ Não (não é Gerente) |
| Ana | Superintendência | Coordenador | ❌ Não (não é Gerente) |
| Carlos | Vidas | Gerente | ❌ Não (não é Superintendência) |
| Rita | Controle (lotação Coordenador) | Coordenador | ❌ Não (só Equipe e Gerente recebem o pacote) |
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

### Lotar e dar Função a um Usuário — superusuário em tudo, DAT nas gerências comuns

> 🔴 **Mudou com o hardening Tier-0 (P0-1)** e de novo em **17/10/2026** (decisão do dono).
>
> - **Superusuário**: lota em qualquer gerência e papel.
> - **DAT** (policy `manage_lotacao_comum`): lota nas **gerências comuns** como Formador, Coordenador,
>   Apoio de Coordenação, Gerente (menos na Superintendência) e Equipe administrativa. A lista de
>   gerências não mostra DAT, Controle nem Diretoria. Lotar nelas, ou como Gerente na Superintendência,
>   é só do superusuário: o sistema responde com o motivo (400).
> - O DAT **não** mexe na lotação da própria conta nem de quem trabalha no DAT, no Controle ou na
>   Diretoria, ou é Gerente da Superintendência: os campos aparecem travados com o motivo. Salvar o
>   cadastro dessas pessoas (telefone, cargo, senha) continua funcionando.
> - O DAT só dá ou tira as funções Formador, Coordenador, Apoio de Coordenação e Gerente; os outros
>   grupos da pessoa ficam como estão. Toda mudança de lotação fica no AuditLog.
> - **Backend**: `UsuarioAdminSerializer` (`apps/core/serializers/usuario.py`, regra
>   `lotacao_reservada` em `apps/core/services/equipe_gerencia_import.py`); a action `assign_groups`
>   e os importadores seguem `SuperuserOnly`.
>
> Em produção há **1 superusuário ativo**. Se essa conta ficar indisponível, ninguém lota no DAT, no
> Controle, na Diretoria nem como Gerente da Superintendência. Isso é um bus factor conhecido —
> ver [audits/ACHADOS_REAIS.md](./audits/ACHADOS_REAIS.md), premissa F3.

Passos (como superusuário):

1. Na lista de usuários, clique no botão **Editar** (ícone de lápis)
2. No modal, você verá:
   - **Gerência (onde trabalha)**: selecione a gerência; o setor vem dela
   - **Função (o que pode fazer)**: selecione uma ou mais funções
3. Clique em **Salvar**

O Salvar mexe só no que você mudou no formulário (#2071):

- Grupos que o formulário não mostra (como Controle, DAT ou grupos de permissão) continuam. São etiquetas: desde
  o PR 12 não dão poder.
- Se a gerência e as funções não mudaram, a lotação não é alterada. Exceção: quem é Gerente na
  Superintendência sem ter a função Gerente (tirada na tela de Grupos) deixa de aprovar.
- Ao criar, gerência e função são obrigatórias. Na edição, a função pode ficar vazia, e a gerência só pode
  ficar vazia para quem não tem lotação (como o Controle).
- Lotar alguém na Superintendência não dá o grupo "Superintendência": quem é Gerente ali aprova pelo vínculo.
- Tirar a função Gerente de uma aprovadora encerra o vínculo e ela deixa de aprovar. Para revogar, use este
  formulário: tirar o Gerente pela tela de Grupos só vale depois do próximo Salvar aqui.
- Atenção: mudar a gerência ou a função encerra os vínculos da pessoa em outras gerências (o formulário
  mostra uma só). Desde o PR 12 a lotação é a única porta do poder: antes de salvar alguém da gerência DAT ou
  CONTROLE, confira que "Equipe administrativa" continua marcada. Para quem já está lotado em outra gerência,
  não use o formulário para dar o vínculo do DAT ou do Controle (ver [DEPLOY_CHECKLIST.md §9](./DEPLOY_CHECKLIST.md)).

Se os campos aparecerem **desabilitados**, é porque sua conta não é superusuário — não é bug.

### Visualização na Tabela

- **Setor**: Tags em cor **roxa**
- **Função**: Tags em cor **azul** (Gerente aparece em **dourado**)

---

## Cenários Comuns

### Novo Formador da Superintendência
- Gerência: Superintendência
- Função: Formador

### Novo Coordenador do projeto Vidas
- Gerência: Vidas
- Função: Coordenador

### Gerente que pode aprovar SUPER
- Gerência: Superintendência
- Função: Gerente

### Usuário do DAT que gerencia eventos
- Gerência: DAT
- Função: Coordenador ou Gerente (dependendo das responsabilidades)

### Usuário que trabalha em mais de uma gerência
O formulário mostra uma gerência só. Quem atua em mais de uma (ex.: coordena uma e é formadora em outra)
tem um vínculo em cada, vindo do import de equipe. Salvar sem mudar gerência nem funções mantém todos; mudar
a gerência ou a função encerra os das outras gerências.

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
# que o usuário pode aprovar (pela lotação; desde o PR 11 nenhum grupo aprova).
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
Verifique se ele está **lotado como Gerente na gerência Superintendência** (formulário de Usuários). Gerente
lotado em outra gerência não aprova por ser Gerente.
O outro caminho é estar **lotado como Equipe ou Gerente na gerência Controle ou DAT** (pacote do setor); grupo e função sozinhos não aprovam.

### Por que os campos de Gerência/Função aparecem desabilitados para mim?
Sem a policy `manage_lotacao_comum`, a lotação é **somente do superusuário**. Com ela (o DAT), os campos
travam na própria conta e em quem trabalha no DAT, no Controle ou na Diretoria, ou é Gerente da
Superintendência; o formulário mostra o motivo. Não é bug.

### Posso dar múltiplas funções a um usuário?
Sim. Por exemplo, alguém pode ser Coordenador e Gerente ao mesmo tempo.

### Como remover um grupo de um usuário?
Função: na edição do usuário (como superusuário), desmarque a função e salve. Grupos que o formulário não
mostra (setor, permissões): na tela de Grupos.

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

A matriz **Grupo × Capability** não se edita em tela nenhuma: muda só por PR (seed
`functional_permissions_seed.py` + migration de dados, D21 em
[rbac_authorization_matrix.md](./rbac_authorization_matrix.md), D4 do ADR-020). O Django Admin
(`/admin/core/permissaofuncional/`, `PermissaoFuncionalAdmin` em `apps/core/admin.py`) é **só leitura**
(add/change/delete desabilitados): serve para conferir, junto com `rbac_diff --auditar`.
