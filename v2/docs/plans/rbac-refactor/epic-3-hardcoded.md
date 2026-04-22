# Epic 3 — Eliminar hardcoded group checks

**Parent plan:** [master-plan.md](./master-plan.md)
**Dependências:** Epic 2 (usa `HasPerm` e helper `user_has_any_perm`)
**Bloqueia:** Epic 4 (que precisa do caminho único via `has_perm` limpo)
**Issues:** 2
**PR size total:** ~700 linhas (split em 2 PRs)
**Tempo estimado:** 4h total + 24h soak após E3.2

---

## Por que este epic existe

~15 locais fazem `user.groups.filter(name="DAT").exists()` direto — isso é **bypass do sistema RBAC**: invisível ao `has_perm()`, invisível ao admin UI de permissões, quebra silenciosamente quando um Django Group é renomeado.

Django docs oficial sempre recomendam `user.has_perm("app.codename")`. Este epic migra cada check hardcoded para o caminho canônico, criando novas permissões funcionais onde necessário.

## Escopo

### Dentro do escopo
- Módulo `apps/core/rbac_helpers.py` com `user_has_any_perm(user, *codenames)`
- Módulo `apps/core/constants/rbac.py` com constantes `COORDENADOR_ROLE_GROUPS`, `FORMADOR_ROLE_GROUPS` (para filtros de queryset legítimos que NÃO são autorização)
- Nova permissão `pode_ver_todas_disponibilidades` + seed
- Migração de 8 call sites de autorização para `user_has_any_perm`
- Migração de 4 call sites de data scope filter para constantes
- Refactor de 3 helpers (`_is_dat_or_super`, `_has_any_group`, `_is_privileged_user`) para usar `has_perm`

### Fora do escopo
- Renomear codenames (Epic 4)
- Remover classes legacy (Epic 5)
- Lint rule que bane `groups.filter(name=...)` (Epic 6)

## Issues

- [ ] **Issue 3.1** — Infraestrutura: helpers, constants, nova permissão + seed
- [ ] **Issue 3.2** — Substituir 15 call sites (split por domínio: availability+solicitacao, notifications, options)

## Acceptance criteria

### Para 3.1
- [ ] `apps/core/rbac_helpers.py` criado com `user_has_any_perm` (8 testes)
- [ ] `apps/core/constants/rbac.py` criado com constantes de role groups (para data scope)
- [ ] Permissão `pode_ver_todas_disponibilidades` adicionada ao seed
- [ ] Migration 0075 aplica seed nova em staging
- [ ] Groups `Superintendência`, `Controle`, `Gerência`, `Diretoria` recebem a nova permissão automaticamente

### Para 3.2
- [ ] `permissions.py:186` (`IsGerenteSuperintendencia`) — mantém (composite rule documentado)
- [ ] `permissions.py:241` (`HasSectorAccess`) — usa `user_has_any_perm(user, "pode_ver_todas_disponibilidades")` em vez de filter name="Controle"
- [ ] `views/acoes_notificacao.py:37` — `_is_dat_or_super` usa `user_has_any_perm(user, "pode_operar_dat_exclusivo")`
- [ ] `views/acoes_notificacao.py:43` — `_has_any_group` refatorado para aceitar codenames, não group names
- [ ] `views/availability.py:50` — `_is_privileged_user` usa `user_has_any_perm(user, "pode_ver_todas_disponibilidades")`
- [ ] `views_availability_monthly.py:176` — mesma migração
- [ ] `views_solicitacao.py:198` — mesma migração
- [ ] `views/options.py:111, 139` — mantém `groups__name__in=...` mas referencia constantes em `constants/rbac.py`
- [ ] `services/notificacoes_acoes_service.py:134,141` — refatorado para aceitar codenames OU usar constantes (caso data scope)
- [ ] Baseline parity test continua verde
- [ ] Teste novo `test_rbac_layer3_parity.py` valida que `_is_privileged_user` com user só-Controle retorna `True` (preserva comportamento)

## Mapeamento detalhado: check → substituto

| File:line | Check atual | Substituição | Tipo |
|---|---|---|---|
| `permissions.py:186` | `groups.filter(name="Gerente")` dentro de `IsGerenteSuperintendencia` | Mantém (já é composto com codename) | authz |
| `permissions.py:241` | `groups.filter(name="Controle")` — **BLOCK list** para grade mensal | `user_has_any_perm(u, "pode_ver_todas_disponibilidades")` (positive check) | authz |
| `views/acoes_notificacao.py:37` | `_is_dat_or_super`: `name="DAT"` | `user_has_any_perm(u, "pode_operar_dat_exclusivo")` | authz |
| `views/acoes_notificacao.py:43` | `_has_any_group(user, {names})` | refactor p/ aceitar codenames | authz |
| `views/availability.py:50` | `name__in=["Superintendência", "Controle"]` | `user_has_any_perm(u, "pode_ver_todas_disponibilidades")` | authz |
| `views_availability_monthly.py:176` | `name__in=["Superintendência", "Gerência", "Diretoria"]` | `user_has_any_perm(u, "pode_ver_todas_disponibilidades")` | authz |
| `views_solicitacao.py:198` | `name__in=["Superintendência", "Controle", "DAT"]` | `user_has_any_perm(u, "pode_operar_controle_dat")` + escopo | authz |
| `views/options.py:111` | `groups__name__in=["Coordenador", "Apoio de Coordenação"]` | `groups__name__in=COORDENADOR_ROLE_GROUPS` (constante) | data scope |
| `views/options.py:139` | `groups__name="Formador"` | `groups__name__in=FORMADOR_ROLE_GROUPS` (constante) | data scope |
| `services/notificacoes_acoes_service.py:134,141` | `groups__name__in=list(role_group_names)` | refactor: aceitar codenames OU role constants (dependendo do uso) | ambos |

## DECISÃO: split em 2 PRs?

**Sim**, por duas razões:
1. Infra (3.1) é pré-requisito para usar helpers em 3.2. Se juntar, review fica pesado.
2. 3.1 é seguro (só adiciona coisa); 3.2 muda comportamento potencial. Isolar risk.

## Nova permissão seed

```python
FunctionalPermissionSeed(
    codename="pode_ver_todas_disponibilidades",
    label="Visualizar todas as disponibilidades",
    description="Acesso à grade mensal completa e bloqueios de qualquer usuário",
    category="operacao",
    group_names=("Superintendência", "Controle", "Gerência", "Diretoria"),
),
```

## Helper

```python
# apps/core/rbac_helpers.py
"""
Capability-based authorization helpers.

Use these INSTEAD of user.groups.filter(name=...) in views and services.
Group-name filters for DATA SCOPE (e.g., "who is a formador?") belong in
apps.core.constants.rbac, not here.
"""
from __future__ import annotations
from django.contrib.auth.models import AbstractBaseUser, AnonymousUser

from apps.core.services.rbac_permissions import get_user_functional_permissions


def user_has_any_perm(
    user: AbstractBaseUser | AnonymousUser | None,
    *codenames: str,
) -> bool:
    """
    Returns True if user has ANY of the given functional permission codenames.

    Superusers always return True. Unauthenticated users always return False.
    """
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return True
    user_perms = get_user_functional_permissions(user)
    return any(code in user_perms for code in codenames)


def user_has_all_perms(
    user: AbstractBaseUser | AnonymousUser | None,
    *codenames: str,
) -> bool:
    """Returns True if user has ALL given codenames."""
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return True
    user_perms = get_user_functional_permissions(user)
    return all(code in user_perms for code in codenames)
```

## Constants de data scope

```python
# apps/core/constants/rbac.py
"""
Named constants for Django Group names used as DATA SCOPE filters
(NOT authorization — those go through user.has_perm() / HasPerm).

Centralized here so a future Group rename is a one-line change.
"""
from typing import Final

# Coordenadores (para dropdown /api/options/coordenadores/)
COORDENADOR_ROLE_GROUPS: Final = ("Coordenador", "Apoio de Coordenação")

# Formadores (para dropdown /api/options/formadores/)
FORMADOR_ROLE_GROUPS: Final = ("Formador",)
```

## Fontes autoritativas

- [Django — has_perm canonical pattern](https://docs.djangoproject.com/en/5.2/topics/auth/default/#permissions)
- [Django 5.2 — Permissions checking](https://docs.djangoproject.com/en/5.2/topics/auth/default/#default-permissions)
- [OWASP — Avoid group-based authorization shortcuts](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
