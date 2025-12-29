# RBAC e Permissões

Sistema de permissões baseado em grupos de Setor e Função.

## Conceito

O sistema RBAC usa duas dimensões:

- **SETOR**: Onde o usuário trabalha
- **FUNÇÃO**: O que o usuário pode fazer

## Grupos de Setor

| Grupo | Descrição |
|-------|-----------|
| Superintendência | Setor estratégico (fluxo SUPER) |
| Vidas | Gerência 2 - Projetos Vida |
| Fluir | Gerência 3 - Projeto Fluir |
| ACerta | Gerência 4 - Projetos ACerta |
| Brincando | Gerência 5 - Brincando e Aprendendo |
| Sou da Paz | Gerência 6 - Projeto Sou da Paz |
| DAT | Departamento de Apoio Técnico |
| Controle | Setor de Controle (operações) |
| Gerência | Gerência genérica |

## Grupos de Função

| Grupo | Permissões |
|-------|------------|
| Formador | Visualiza grade, gerencia bloqueios pessoais |
| Coordenador | Cria solicitações de eventos |
| Apoio de Coordenação | Auxilia coordenação, visualiza solicitações |
| Gerente | Aprova/reprova, acessa dashboards e relatórios |

## Regra de Aprovação SUPER

```python
can_approve_super = is_superuser OR (
    "Gerente" IN funcoes AND "Superintendência" IN setores
)
```

## Exemplos

| Usuário | Setor | Função | Pode Aprovar SUPER? |
|---------|-------|--------|---------------------|
| Maria | Superintendência | Gerente | ✅ Sim |
| João | DAT | Gerente | ❌ Não |
| Pedro | Superintendência | Formador | ❌ Não |

## API /api/me/

Retorna dados RBAC do usuário autenticado:

```json
{
  "id": 1,
  "username": "maria",
  "groups": ["Superintendência", "Gerente"],
  "setores": ["Superintendência"],
  "funcoes": ["Gerente"],
  "is_superuser": false,
  "is_superintendencia": true,
  "can_approve_super": true
}
```

## Arquivos Principais

- `apps/core/views_basic.py`: Definição de grupos e CurrentUserView
- `apps/core/tests/test_rbac_permissions.py`: Testes unitários
- `v2/frontend/src/pages/AdminDAT/UsuariosPage.jsx`: Interface de gestão
