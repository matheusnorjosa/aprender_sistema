# RBAC Refactor — Master Plan

**Status:** Planejado (execução pendente)
**Owner:** @matheusnorjosa
**Data de criação:** 2026-04-22
**Escopo:** 6 epics, ~14 issues, ~14 PRs (500-700 linhas cada)
**Timeline estimada:** ~3 semanas em execução linear com soak de 24h em staging entre cada PR

---

## 1. TL;DR

Refatorar o sistema RBAC do Aprender Sistema v2 para **desacoplar capability (o que se pode fazer) de identidade (quem faz hoje)**. O acoplamento atual produz 3 tipos de acidente técnico:

1. Labels como "Operação DAT" na UI admin — se o setor DAT mudar, a label vira mentira
2. Classes DRF como `IsDAT`, `IsControleOrDAT` em 85+ arquivos — rename organizacional quebra imports
3. ~15 checks `user.groups.filter(name="DAT")` espalhados — bypass do sistema de permissão, invisível ao `has_perm()`

O plano executa 6 epics em sequência estrita, cada um dependente do anterior, cada epic fragmentado em 1-3 issues (PR máximo 700 linhas).

---

## 2. Fundamentos (pesquisa externa validada)

Cada decisão de design abaixo tem fonte autoritativa — não é opinião isolada.

| Princípio | Fonte |
|---|---|
| "Permission = ação sobre recurso; Role = agregador de permissões (conjuntos distintos)" | [NIST RBAC](https://csrc.nist.gov/projects/role-based-access-control) |
| "Permission codenames seguem `verb_noun` snake_case" | [Django 5.2 auth customizing](https://docs.djangoproject.com/en/5.2/topics/auth/customizing/) |
| "Proibir verbos `admin_`, `manage_`, `operate_`, `configure_` (escopo indefinido)" | [GitLab permissions conventions](https://docs.gitlab.com/development/permissions/conventions/) |
| "DRF não define `Is<Role>` — apenas estados (`IsAuthenticated`, `IsAdminUser`)" | [DRF permissions guide](https://www.django-rest-framework.org/api-guide/permissions/) |
| "Classe parametrizada `HasPerm(codename)` + composição `\|&~` > 1 classe por codename" | DRF + OWASP (anti-padrão: "permission class explosion") |
| "Labels em UI devem usar verbo infinitivo, não gerúndio nem substantivo" | Nielsen Norman, Microsoft Writing Style Guide |
| "Autoridades granulares > papéis coarse" | [Spring Security — hasAuthority vs hasRole](https://www.baeldung.com/spring-security-granted-authority-vs-role) |
| "Renomear classes via PEP 702 `@typing.deprecated` + `warnings.warn`" | [PEP 702](https://peps.python.org/pep-0702/) |
| "Data migration para renomear labels, codenames idempotente via `update_or_create`" | Django 5.2 data migrations |
| "Lint guards previnem regressão após refactor" | Casbin, OWASP Access Control Cheat Sheet |

---

## 3. Princípios de nomenclatura adotados

### 3.1 Codenames (identificador interno, snake_case, inglês)

- **Forma**: `<verb>_<noun>[_<qualifier>]`
- **Verbos canônicos** (em ordem de preferência): `create`, `read`, `update`, `delete`, `approve`, `publish`, `import`, `export`, `assign`, `reconcile`, `view`
- **Proibidos**: `admin_`, `manage_`, `operate_`, `configure_`, `change_`, `modify_`, `edit_`, `list_`, `set_`, `write_` (todos banidos pela convenção GitLab — escopo ambíguo ou bundle CRUD)
- **Nunca**: nome de setor, nome de função, nome de role, nome de group

Exemplos válidos: `approve_solicitation`, `publish_gcal_event`, `import_spreadsheet`, `view_compras_dashboard`

### 3.2 Labels (texto user-visible em português)

- **Forma**: `<Verbo infinitivo> <substantivo plural>`
- **Exemplos**: "Aprovar solicitações", "Importar planilhas", "Visualizar métricas geográficas"
- **Evitar**: gerúndio ("Aprovação de..."), substantivo nominal ("Aprovações"), adjetivos de identidade ("DAT", "Controle")

### 3.3 Classes DRF (PascalCase, inglês)

- **Padrão preferido**: usar `HasPerm("codename")` inline no `permission_classes`; sem classe dedicada
- **Exceção**: classes com lógica de `has_object_permission` complexa → nomear como condição (`IsSolicitationOwner`, `IsWithinEditWindow`)
- **Proibido**: `Is<Role>`, `Is<Setor>`, `Is<Grupo>`

### 3.4 Categorias (identificador interno)

Valores permitidos (após migração):
- `solicitacao` — fluxo de aprovação de eventos
- `importacao` — carga em massa de dados
- `cadastros_administrativos` — gestão de entidades (municípios, produtos, etc.)
- `dashboard` — leitura de painéis analíticos
- `operacao` — rotinas operacionais diárias
- `supervisao` — supervisão gerencial

---

## 4. Arquitetura alvo (antes → depois)

### Antes (estado atual)

```python
# permissions.py — 15 classes dedicadas
class IsDAT(funcperm_factory(...)): pass
class IsControleOrDAT(funcperm_factory(...)): pass
# ... 13 mais

# views/reports.py
from .permissions import IsControleOrDAT
@permission_classes([IsControleOrDAT])
def reports_status_counts(...): ...

# views/availability.py — bypass do sistema RBAC
def _is_privileged_user(self):
    return user.groups.filter(
        name__in=["Superintendência", "Controle"]
    ).exists()
```

### Depois (após 6 epics)

```python
# permissions.py — 1 classe parametrizada
class HasPerm(permissions.BasePermission):
    def __init__(self, codename): self.codename = codename
    def has_permission(self, request, view):
        return request.user.has_perm(self.codename)

# views/reports.py
@permission_classes([
    IsAuthenticated,
    HasPerm("core.operate_preagenda")
])
def reports_status_counts(...): ...

# views/availability.py — usa o sistema RBAC
from apps.core.rbac import has_any
def _is_privileged_user(self):
    return has_any(self.request.user, "core.view_all_availability")
```

E no banco: codenames `approve_solicitation`, `import_spreadsheet`, `manage_admin_registries` em inglês; labels "Aprovar solicitações", "Importar planilhas e dados", "Administrar cadastros" em português.

---

## 5. Breakdown em 6 epics

| # | Epic | Issues | GitHub | PR size |
|---|---|---|---|---|
| E1 | Labels + descriptions + categorias capability-oriented | 1 | #1174 | ~200 LoC |
| E2 | `HasPerm(codename)` parametrizado + deprecation das 15 classes | 1 | #1175 | ~350 LoC |
| E3 | Eliminar 15 `groups.filter(name=...)` hardcoded | 2 | #1176 | ~700 LoC |
| E4 | Codename rename para verb_noun inglês | 3 | #1177 | ~900 LoC |
| E5 | Sweep completo: remover 15 classes `Is<Role>` via codemod | 3 | #1178 | ~1000 LoC |
| E6 | Módulo `apps/core/rbac/` + lint guard custom | 1 | #1179 | ~400 LoC |

Issues linkadas a cada epic:

| Epic | Issues no GitHub |
|---|---|
| E1 (#1174) | #1180 |
| E2 (#1175) | #1181 |
| E3 (#1176) | #1182, #1183 |
| E4 (#1177) | #1190 (4.1), #1191 (4.2), #1185 (4.3) |
| E5 (#1178) | #1186 (5.1), #1187 (5.2), #1188 (5.3) |
| E6 (#1179) | #1189 |

Planos detalhados por epic (este diretório):
- [Epic 1 — Labels capability-oriented](./epic-1-labels.md)
- [Epic 2 — HasPerm + deprecation](./epic-2-hasperm.md)
- [Epic 3 — Eliminar hardcoded group checks](./epic-3-hardcoded.md)
- [Epic 4 — Codename rename para verb_noun](./epic-4-codenames.md)
- [Epic 5 — Class sweep via codemod](./epic-5-class-sweep.md)
- [Epic 6 — RBAC module + lint guard](./epic-6-rbac-module.md)

---

## 6. Rollout strategy

### 6.1 Ordenação rígida

```
E1 (labels)
  └─> soak 24h staging
      └─> E2 (HasPerm + deprecation)
          └─> soak 24h staging
              └─> E3.1 (helpers + seed infra)
                  └─> E3.2 (replace call sites)
                      └─> soak 24h
                          └─> E4.1 (seed new codenames + dual-write)
                              └─> E4.2 (migrate internal usages)
                                  └─> soak 1 semana (API consumers)
                                      └─> E4.3 (remove old codenames)
                                          └─> E5.1 (codemod script + dry-run)
                                              └─> E5.2 (run codemod on views)
                                                  └─> E5.3 (delete legacy classes)
                                                      └─> E6 (rbac module + lint)
```

Cada "soak" é:
- Deploy em staging via Portainer (CP-01)
- 24h mínimo observando logs (erros 403/500, audit logs)
- Validação smoke: abrir UI admin, criar grupo de teste, ver labels
- Só então merge da próxima PR

**Exceção**: E4.2 → E4.3 exige **1 semana de soak** para permitir que qualquer consumidor externo da API (Zapier, N8N, scripts admin) ajuste suas chamadas `has_perm("old")` → `has_perm("new")` durante o dual-write.

### 6.2 Por que rígida

Cada epic depende das abstrações introduzidas pelo anterior:
- E2 usa os labels de E1 em mensagens de erro
- E3 usa `HasPerm` introduzido em E2
- E4 facilita E5 (codenames já padronizados antes do sweep)
- E6 cimenta o que E1-E5 construíram

Paralelizar é convite a merge conflict e regressão.

---

## 7. Testing strategy

### 7.1 Baseline (captura antes de E1)

Antes do primeiro merge, criar teste de paridade que captura o estado atual:

```python
# v2/backend/apps/core/tests/test_rbac_baseline_parity.py
@pytest.mark.django_db
class TestRBACBaselineParity:
    """
    Capture current 403/200 matrix for every setor-coupled endpoint.
    Re-run after EACH epic to confirm no behavior change.
    """
    ROLE_MATRIX = [
        ("superuser", {"is_superuser": True}),
        ("controle", {"groups": ["Controle"]}),
        ("dat", {"groups": ["DAT"]}),
        ("superintendencia", {"groups": ["Superintendência"]}),
        ("gerencia", {"groups": ["Gerência"]}),
        ("formador", {"groups": ["Formador"]}),
        ("coordenador", {"groups": ["Coordenador"]}),
        ("apoio", {"groups": ["Apoio de Coordenação"]}),
        ("none", {}),
    ]

    ENDPOINTS = [
        ("GET", "/api/solicitacoes/"),
        ("GET", "/api/availability/monthly/"),
        ("GET", "/api/controle/compras/"),
        ("POST", "/api/disponibilidade/import-bloqueios/"),
        ("GET", "/api/pre-agenda/"),
        ("GET", "/api/reports/status-counts/"),
        ("GET", "/api/options/formadores/"),
        # ... ~15 endpoints críticos
    ]

    def test_parity_matrix(self):
        """Run this test AFTER EACH epic. Must stay green."""
        for role, attrs in self.ROLE_MATRIX:
            user = self._build_user(role, attrs)
            for method, path in self.ENDPOINTS:
                response = getattr(self.client, method.lower())(path)
                assert response.status_code == EXPECTED[role][path]
```

Capturar `EXPECTED` numa snapshot test antes de E1 (rodar uma vez, salvar JSON). Depois cada epic re-roda e compara.

### 7.2 Testes novos por epic

| Epic | Novos testes | Arquivo |
|---|---|---|
| E1 | Labels não contêm nome de setor; categorias válidas | `test_rbac_seed.py` (add) |
| E2 | `HasPerm` parametrizado funcional; composition (`\|&`); deprecation warning | `test_permissions_hasperm.py` (novo) |
| E3 | Capability `view_all_availability` equivalente ao check hardcoded | `test_rbac_layer3_parity.py` (novo) |
| E4 | Dual-codename period: `has_perm(old)` e `has_perm(new)` ambos grant | `test_codename_dual_write.py` (novo) |
| E5 | Codemod preserva comportamento; paridade com baseline | (reusa baseline) |
| E6 | Lint rule bloqueia `groups.filter(name=...)` em views/services | `test_rbac_lint.py` (novo) |

### 7.3 Coverage gate

85% mantido em todas as PRs (convenção do projeto, não baixar).

---

## 8. Risks register

| # | Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|---|
| R1 | Label muda em tela traduzida hardcoded | Baixa | Médio | Grep final antes do merge E1; frontend é codename-driven (memória confirma) |
| R2 | `HasPerm` não integra com `get_user_functional_permissions` | Baixa | Alto | Teste dedicado em E2.1 |
| R3 | Codemod de E5 gera código quebrado em edge cases | Média | Alto | E5.1 = dry-run obrigatório em sub-módulo; review manual antes de expandir |
| R4 | Consumidor externo da API usa `pode_operar_dat` via `has_perm()` remoto | Alta se existir | Alto | E4 dual-write de 1 semana + anúncio em changelog |
| R5 | Lint rule custom (E6) dá falso-positivo em fixtures/tests | Baixa | Baixo | Whitelist `tests/`, `migrations/`, `fixtures/` |
| R6 | Migration falha em produção por dados inconsistentes | Baixa | Alto | Migration usa `update_or_create`; reverse documented; testado em staging antes |
| R7 | Portainer inacessível durante deploy (vimos em #1162) | Média | Baixo | Re-run; imagem já está no registry |
| R8 | Deprecation warning do E2 explode logs em produção | Média | Médio | Warnings só no primeiro load (Python ignora duplicatas por default); configurar `-W default::DeprecationWarning` |

---

## 9. Deferred items (com justificativa arquitetural)

Não são cost/benefit — são decisões de design deliberadas:

### 9.1 Renomear Django Group names (DAT, Controle, Vidas, etc.)

**Deferido permanentemente.**

Após os 6 epics, nenhum código referencia "DAT" ou "Controle" como string — aparecem só no banco como `Group.name`. Groups são **mecanismo de agregação de permissões** e **rótulo humano**. "DAT" e "Controle" são departamentos reais da organização. Renomear para algo abstrato (`AdminRegistriesManagers`) não resolve nada — só acopla nome do grupo ao bundle atual, que é exatamente o acoplamento eliminado.

Se a organização reestruturar (DAT absorver Controle), é `Group.objects.filter(name="DAT").update(name=...)` — 1 linha de migration, zero código.

### 9.2 `EquipeGerencia.papel` choices

**Deferido para refactor separado.**

`papel` (GERENTE/COORDENADOR/APOIO/FORMADOR) é **modelo estrutural** (relação usuário↔gerência), não RBAC. Refactor legítimo existe — deduplicação entre `papel` e Django Group com mesmo nome — mas é problema de normalização de dados, ortogonal ao RBAC.

Ticket a criar ao final: `refactor(data): unify EquipeGerencia.papel with role Group membership`.

### 9.3 Decomposição em CRUD completo (create_X / read_X / update_X / delete_X)

**Deferido até surgir demanda.**

GitLab recomenda decomposição CRUD **quando o negócio atribui subsets diferentes**. No AS v2, ninguém hoje tem "só read_registry sem update_registry". Decompor agora produz 30+ permissões que aparecem sempre juntas (ruído puro). YAGNI: decompõe quando surgir o primeiro papel que precisa só de um subset (ex: auditor read-only).

---

## 10. Success criteria

Ao final dos 6 epics, verificar cada um:

- [ ] **S1.** `grep -r "IsDAT\|IsControle\|IsSuperintendencia" v2/backend/apps/core/views*/` retorna zero resultados
- [ ] **S2.** `grep -rE 'groups.filter\(name\s*=' v2/backend/apps/core/views*/ v2/backend/apps/core/services/` retorna zero resultados (fora de `constants/rbac.py` e `tests/`)
- [ ] **S3.** Nenhum codename começa com `pode_` (todos em inglês `verb_noun`)
- [ ] **S4.** Nenhum label de `PermissaoFuncional` contém string "DAT", "Controle", "Superintendência", "Gerência", "Coordenador" ou "Formador"
- [ ] **S5.** Nenhuma categoria de `PermissaoFuncional` contém nome de setor
- [ ] **S6.** Baseline parity test (`test_rbac_baseline_parity.py`) passa com os mesmos status HTTP capturados antes de E1
- [ ] **S7.** Coverage ≥85% em `apps.core.permissions`, `apps.core.rbac.*`, `apps.core.services.rbac_*`
- [ ] **S8.** Lint custom rule (introduzida em E6) passa limpo em toda a codebase
- [ ] **S9.** Documento `v2/docs/RBAC_NAMING.md` publicado como convenção oficial para PRs futuras
- [ ] **S10.** UI admin (`AdminDAT → Grupos`) exibe labels capability-oriented (verificação manual em staging)

---

## 11. Appendix — Research citations

Links para as fontes usadas nas decisões de design:

- [Django 5.2 — Customizing authentication](https://docs.djangoproject.com/en/5.2/topics/auth/customizing/)
- [Django 5.2 — Using the Django authentication system](https://docs.djangoproject.com/en/5.2/topics/auth/default/)
- [DRF — Permissions API guide](https://www.django-rest-framework.org/api-guide/permissions/)
- [NIST — Role Based Access Control project](https://csrc.nist.gov/projects/role-based-access-control)
- [OWASP — Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
- [Casbin — RBAC model](https://casbin.apache.org/docs/rbac)
- [GitLab — Permissions conventions](https://docs.gitlab.com/development/permissions/conventions/)
- [Spring Security — hasAuthority vs hasRole](https://www.baeldung.com/spring-security-granted-authority-vs-role)
- [GitHub changelog — Fine-grained permissions for custom repository roles (2025)](https://github.blog/changelog/2025-06-26-github-actions-fine-grain-permissions-are-now-generally-available-for-custom-repository-roles/)
- [PEP 702 — Marking deprecations using the type system](https://peps.python.org/pep-0702/)
- [Python 3 — `warnings` module](https://docs.python.org/3/library/warnings.html)

---

## 12. Changelog deste plano

- **2026-04-22** — v1.0 — Plano inicial criado por @matheusnorjosa após audit completo da codebase + pesquisa em fontes autoritativas.
