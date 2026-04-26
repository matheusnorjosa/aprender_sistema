# RBAC Naming Convention — Aprender Sistema v2

**Status:** Canônico a partir de Epic 2 do RBAC Refactor (2026-04-23).
**Source of truth:** este documento.
**Sources autoritativos** que embasam as regras: [Django auth customizing](https://docs.djangoproject.com/en/5.2/topics/auth/customizing/), [DRF permissions](https://www.django-rest-framework.org/api-guide/permissions/), [NIST RBAC](https://csrc.nist.gov/projects/role-based-access-control), [GitLab permissions conventions](https://docs.gitlab.com/development/permissions/conventions/), [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html).

---

## Princípio central

**Permission é capacidade, não identidade.** Separar o que a pessoa pode fazer (permission) de quem ela é organizacionalmente (setor, função, grupo). Groups agregam permissions; permissions nomeiam ações sobre recursos. Essa é a forma canônica do NIST RBAC.

Manifestação prática: se a organização reestrutura (DAT vira "Operações Administrativas"), **zero linha de código** muda. Apenas `Group.name`.

---

## 1. Codenames (identificador interno)

Formato: `<verb>_<noun>[_<qualifier>]`, snake_case, inglês.

**Verbos canônicos**:
`create`, `read`, `update`, `delete`, `approve`, `publish`, `import`, `export`, `assign`, `reconcile`, `view`.

**Verbos proibidos** (escopo ambíguo / bundle CRUD):
`admin_`, `manage_`, `operate_`, `configure_`, `change_`, `modify_`, `edit_`, `list_`, `set_`, `write_`.

**Nunca no codename**:

- Nome de setor (`dat`, `controle`, `super`, `vidas`, ...)
- Nome de função (`coordenador`, `formador`, ...)
- Nome de grupo Django

### Bons exemplos de codename

```text
approve_solicitation
publish_gcal_event
import_spreadsheet
view_compras_dashboard
create_solicitation
view_all_availability
```

### Maus exemplos de codename

```text
pode_operar_dat                   # setor no nome
admin_cadastros                    # verbo proibido
change_solicitation               # ambíguo (update? aprove? cancel?)
dat_full_access                   # setor + bundle indefinido
```

### Exceções conscientes ao "no `manage_`"

Duas permissões bundle foram mantidas por decisão YAGNI (ver master-plan §9.3):

- `manage_admin_registries` — CRUD de cadastros administrativos (municípios, projetos, produtos, etc.)
- `manage_purchases_and_materials` — CRUD de compras e materiais

Decompor cada uma em `create/read/update/delete` hoje produziria 8+ codenames sempre atribuídos juntos (ruído puro). Decompõe-se quando surgir primeiro papel com subset diferente (ex: auditor read-only).

---

## 2. Labels (texto user-visible, pt-BR)

Formato: `<Verbo infinitivo> <substantivo plural>`.

**Regras**:

- Começar com verbo infinitivo: *Aprovar*, *Criar*, *Importar*, *Visualizar*, *Administrar*.
- Evitar: gerúndio ("Aprovação de...", "Criando..."), substantivação ("Aprovações"), adjetivo puro ("Owner"), nome de módulo solto ("Dashboard").
- **Nunca** nome de setor/função (mesma regra dos codenames).

### Bons exemplos de label

```text
Aprovar solicitações
Importar planilhas e dados
Visualizar dashboard de compras
Administrar cadastros
Exercer supervisão gerencial
```

### Maus exemplos de label

```text
Operacao DAT                       # setor
Dashboard de Compras               # substantivo, não começa com verbo
Owner ou privilegiado              # adjetivo
Aprovação (Superintendência)       # substantivação + setor
```

### Categorias válidas

```text
solicitacao
importacao
cadastros_administrativos
dashboard
operacao
supervisao
```

Categorias fora desse vocabulário **quebram testes de regressão** em `apps/core/tests/test_rbac_labels_capability_oriented.py`.

---

## 3. Permission classes (DRF)

**Preferir sempre**: `HasPerm("codename")` inline no `permission_classes`.

```python
from apps.core.permissions import HasPerm
from rest_framework.permissions import IsAuthenticated

class SolicitacaoApproveView(APIView):
    permission_classes = [IsAuthenticated, HasPerm("approve_solicitation")]
```

### Composition

```python
# OR: qualquer um
permission_classes = [IsAuthenticated, HasPerm("approve_solicitation") | HasPerm("manage_admin_registries")]

# AND explícito (mesma semântica de listar dois):
permission_classes = [IsAuthenticated, HasPerm("a") & HasPerm("b")]

# NOT (raro):
permission_classes = [IsAuthenticated, ~HasPerm("b")]
```

### Exceções aceitas (classes dedicadas)

Só para lógica que **não** pode ser expressa por `HasPerm(codename)`:

- **Object-level check**: `IsSolicitationOwner` / `IsOwnerOrPrivileged` (verifica `obj.usuario`).
- **Dynamic scope por query param**: `HasSectorAccess` (lê `gerencia_id` do request).
- **Composite rule fixa**: `IsGerenteSuperintendencia` (permission funcional + grupo "Gerente").

Nomear como **condição** (não como identidade): `IsSolicitationOwner`, `IsWithinEditWindow`, `HasSectorAccess`. **Nunca** `Is<Role>`, `Is<Setor>`, `Is<Group>`.

### Proibido

```python
# Não faça isto em endpoints novos (Epic 5 remove estas 12 classes):
from apps.core.permissions import IsDAT, IsControle, IsSuperintendencia
permission_classes = [IsDAT]          # ❌ DeprecationWarning
permission_classes = [IsControleOrDAT] # ❌ mesmo motivo
```

---

## 4. Checks de autorização em código

**Canônico**:

```python
# 1) Via HasPerm (DRF permission class)
permission_classes = [HasPerm("approve_solicitation")]

# 2) Via has_perm() nativo do Django (fora de views DRF)
if user.has_perm("approve_solicitation"):
    ...

# 3) Helper para múltiplas permissions (epic 3):
from apps.core.rbac_helpers import user_has_any_perm
if user_has_any_perm(user, "a", "b"):
    ...
```

**Proibido** (bypass do RBAC):

```python
# ❌ NUNCA — ignorado por has_perm(), quebra com rename de Group, Epic 6 lint rejeita
user.groups.filter(name="DAT").exists()
user.groups.filter(name__in=["Controle", "DAT"]).exists()
```

---

## 5. Adicionando uma permission nova

1. Adicionar a `FUNCTIONAL_PERMISSIONS_SEED` em `apps/core/services/functional_permissions_seed.py`:
   - `codename` seguindo §1
   - `label` seguindo §2
   - `category` no vocabulário canônico
   - `group_names` com os grupos que a receberão por default

2. Criar migration data-only (`RunPython` com `update_or_create`), seguindo `0073_rename_permission_labels.py` como template.

3. Usar em views via `HasPerm("codename")`.

4. Adicionar teste (padrão: `test_endpoint_<name>_forbidden_without_perm`).

5. Atualizar `RBAC_NAMING.md` se introduzir nova categoria.

---

## 6. Depreciação de classe legacy

Se você criar uma nova classe de permission **e** ela puder ser expressa como `HasPerm(codename)`, **não crie** — use `HasPerm` direto.

Se você for remover uma legacy do código:

- Substituir por `HasPerm("codename")` no `permission_classes`
- Deletar o import
- Remover a classe do `apps/core/permissions.py` **somente** quando não houver mais nenhum uso (Epic 5 faz isso via libcst).

---

## 7. Enforcement automático

Lint AST custom em `v2/backend/scripts/rbac_lint.py` falha PRs que:

- **V001**: `user.groups.filter(name=...)` / `exclude(name=...)` em código de produção.
  Exceção: linha com marcador `# noqa: RBAC-<tipo>-allowed` documentando a justificativa (composite, block, data-scope).
- **V002**: definem classe `class Is<Word>(...)` fora da whitelist
  `{IsGerenteSuperintendencia, IsOwnerOrPrivileged}`.

**V003 (import de Group) foi descartado** — V001 já cobre o padrão observável
na prática; V003 gerava 100+ falsos positivos (seeds, fixtures, serializers,
admin views têm imports legítimos) com zero violações reais a ganhar.

**Paths whitelisted** (o lint pula):

- `tests/`, `migrations/`, `fixtures/`
- `apps/core/rbac/` (o próprio módulo RBAC)
- `apps/dev_tools/` (seeds e admin tooling manipulam grupos por design)
- `apps/core/constants.py`, `apps/core/permissions.py`, `apps/core/rbac_helpers.py` (shims e data-scope SSOT)
- `scripts/rbac_lint.py`, `scripts/rbac_codemod.py`

**Markers `# noqa: RBAC-*-allowed` em uso**:

| Marker                      | Uso legítimo                                           |
| --------------------------- | ------------------------------------------------------ |
| `RBAC-composite-allowed`    | Classe composite (funcperm + grupo Django)             |
| `RBAC-block-allowed`        | Bloqueio explícito de um grupo por design documentado  |
| `RBAC-data-scope-allowed`   | Filtro de escopo de dados (não authz)                  |

**CI job**: `[required] backend rbac-lint` em `.github/workflows/ci.yaml` — falha o PR automaticamente.

**Self-test**: `apps/core/tests/test_rbac_lint.py` valida que o lint aceita o baseline atual e rejeita os padrões proibidos (10 testes).

Rodar localmente:

```bash
cd v2/backend
python scripts/rbac_lint.py apps/
```

---

## 8. Referência rápida

| Tipo                 | Forma canônica                            | Forma proibida                                    |
| -------------------- | ----------------------------------------- | ------------------------------------------------- |
| **Codename**         | `approve_solicitation`                    | `pode_aprovar_superintendencia`                   |
| **Label**            | "Aprovar solicitações"                    | "Aprovar/Reprovar (Superintendência)"             |
| **Category**         | `solicitacao`, `operacao`, ...            | `admin_dat`, `gerencia`                           |
| **Permission class** | `HasPerm("approve_solicitation")`         | `IsSuperintendencia`                              |
| **Authz check**      | `user.has_perm("approve_solicitation")`   | `user.groups.filter(name="Superintendência")`     |
| **Classe dedicada**  | `IsSolicitationOwner` (condição)          | `IsDAT` (identidade)                              |

---

## 9. Policy Resolution Rules (Epic 4 — Capability Policy Layer)

**Em planejamento (Issue #1231)** — adiciona 3ª camada NIST RBAC: `User → Roles → Capabilities → Policies → Views`.

### Princípios

1. **Policy key = contrato externo estável**
   Quando uma Policy é exposta via `/api/me/policies/`, a key (ex: `view_compras_dashboard`) torna-se contrato público. **Renomear key = breaking change**. Adicionar nova policy = compatível.

2. **Eligibility matrix = implementação interna mutável**
   O conjunto de capabilities que satisfaz uma Policy pode mudar sem breaking. Ex: adicionar `manage_admin_registries` ao set `view_compras_dashboard` para incluir DAT — mudança compatível, frontend não depende.

3. **Não usar sufixo `_policy` em keys públicas**
   Policy key representa **capacidade funcional** (linguagem de produto), não implementação. Exemplo:
   - ✅ `view_compras_dashboard`
   - ❌ `view_compras_dashboard_policy`
   - Class name: `CanViewComprasDashboard` (linguagem de código)

4. **Não misturar roles e capabilities na matriz**
   `ACCESS_POLICIES` guarda APENAS capabilities. Roles → capabilities é responsabilidade do seed/admin.
   - ✅ `frozenset({"manage_admin_registries", "operate_preagenda"})`
   - ❌ `frozenset({"DAT", "approve_solicitation"})`

5. **Motivo legítimo de acesso > Cargo puro**
   Decidir Policy pelo **motivo** (decidir / operar / aprovar / auditar / suportar / validar), não por cargo. Se qualquer motivo for verdadeiro, acesso é legítimo. Ex: AuditLog tem 4 motivos legítimos → 4 capabilities na composition.

### Vocabulário canônico de verbos

Limitar prefixos de Policy keys ao vocabulário:

- `access_X` — acesso de leitura ao módulo (ex: `access_audit_logs`)
- `use_X` — operação ativa (ex: `use_gcal_endpoints`)
- `import_X` — importação de dados
- `manage_X` — CRUD administrativo
- `view_X` — visualização específica (dashboards, métricas)

### Anti-pattern: hardcode de role no código

NUNCA usar `if user.is_dat: return True` espalhado em views. DAT-as-suporte SEMPRE entra via matriz/policy. Razão: hardcode bypassa toda lógica RBAC, cria acoplamento invisível, impossibilita audit pelo código (precisa olhar grep em N lugares).

```python
# ❌ ERRADO
if user.groups.filter(name="DAT").exists():
    return True

# ✅ CORRETO
ACCESS_POLICIES["access_audit_logs"] = frozenset({
    "manage_admin_registries",  # DAT entra como capability declarada
    "operate_preagenda",
    "approve_solicitation",
})
```

---

## 10. Changelog

- **2026-04-23** — v1.0 criada com Epic 2 (#1181). `HasPerm` introduzido, 12 classes factory marcadas com `warnings.warn(DeprecationWarning)` + aviso para remoção no Epic 5.
- **2026-04-26** — v1.1 adicionou §9 Policy Resolution Rules em planejamento para Epic 4 (Issue #1231). Documenta princípios de naming, vocabulário canônico, motivo legítimo de acesso, e anti-pattern de hardcode de role.
