# Guia do Administrador: Sistema RBAC (Setor + Função)

Este guia explica como gerenciar permissões de usuários no Aprender Sistema v2.

---

## Conceito Básico

O sistema usa **duas dimensões** para controlar permissões:

1. **SETOR** - Onde o usuário trabalha
2. **FUNÇÃO** - O que o usuário pode fazer

Cada usuário pode ter **um ou mais setores** e **uma ou mais funções**.

---

## Grupos de SETOR

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
| **Gerência** | Gerência genérica | - |

---

## Grupos de FUNÇÃO

| Função | O que pode fazer |
|--------|------------------|
| **Formador** | Visualiza grade mensal, gerencia bloqueios pessoais |
| **Coordenador** | Cria solicitações de eventos para sua equipe |
| **Apoio de Coordenação** | Auxilia coordenação, visualiza solicitações |
| **Gerente** | Aprova/reprova solicitações, acessa dashboards e relatórios |

---

## Quem Pode Aprovar Solicitações SUPER?

Para aprovar solicitações do fluxo SUPER, o usuário precisa:

✅ Ser **superusuário** (is_superuser = true)

**OU**

✅ Ter **ambos**:
- Função: **Gerente**
- Setor: **Superintendência**

### Exemplos

| Usuário | Setor | Função | Pode Aprovar? |
|---------|-------|--------|---------------|
| Maria | Superintendência | Gerente | ✅ **Sim** |
| João | DAT | Gerente | ❌ Não (não é Superintendência) |
| Pedro | Superintendência | Formador | ❌ Não (não é Gerente) |
| Ana | Superintendência | Coordenador | ❌ Não (não é Gerente) |
| Carlos | Vidas | Gerente | ❌ Não (não é Superintendência) |
| Admin | - | - (superuser) | ✅ **Sim** |

---

## Como Gerenciar Usuários

### Acessar a Interface

1. Faça login como administrador
2. Acesse **Admin DAT** no menu lateral
3. Clique em **Usuários**

### Atribuir Grupos a um Usuário

1. Na lista de usuários, clique no botão **Editar** (ícone de lápis)
2. No modal que abrir, você verá:
   - **Setor (onde trabalha)**: Selecione um ou mais setores
   - **Função (o que pode fazer)**: Selecione uma ou mais funções
3. Clique em **Salvar**

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
```

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
Verifique se ele está no setor **Superintendência**. Apenas Gerentes da Superintendência podem aprovar fluxo SUPER.

### Posso dar múltiplas funções a um usuário?
Sim. Por exemplo, alguém pode ser Coordenador e Gerente ao mesmo tempo.

### Como remover um grupo de um usuário?
Na edição do usuário, desmarque o grupo desejado e salve.

### Os grupos são case-sensitive?
Sim. Use exatamente: "Superintendência", "Gerente", etc.

---

## Referências Técnicas

- **Código Backend**: `apps/core/views_basic.py` (SETOR_GROUPS, FUNCAO_GROUPS)
- **Testes**: `apps/core/tests/test_rbac_permissions.py` (20 testes)
- **Frontend**: `src/pages/AdminDAT/UsuariosPage.jsx`
- **Documentação Técnica**: `.claude/PLANO_RBAC_SETOR_FUNCAO.md`
