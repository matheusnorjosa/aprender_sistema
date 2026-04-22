# Epic 2 — `HasPerm(codename)` parametrizado + deprecation

**Parent plan:** [master-plan.md](./master-plan.md)
**Dependências:** Epic 1 (labels usados em mensagens de erro)
**Bloqueia:** Epic 3 (que usa `HasPerm` como substituto de hardcoded checks)
**Issues:** 1
**PR size total:** ~350 linhas
**Tempo estimado:** 3h + 24h soak

---

## Por que este epic existe

A DRF oficial nunca define `Is<Role>`; só `IsAuthenticated` e `IsAdminUser` (estados, não identidades). Ter 15 classes para 14 codenames é "permission class explosion" (anti-pattern OWASP). O idioma canônico é `HasPerm("codename")` inline + composition via `| & ~`.

Este epic **introduz** o novo padrão mas **não remove** nada — as 15 classes antigas ficam vivas, anotadas com `@typing.deprecated` (PEP 702). Sweep total é o Epic 5. Este é o ponto de inflexão: a partir daqui, PRs novas usam `HasPerm`.

## Escopo

### Dentro do escopo
- Nova classe `HasPerm(codename)` em `apps/core/permissions.py`
- Integração com serviço existente `get_user_functional_permissions`
- Suporte a composition (`HasPerm("A") | HasPerm("B")`) via DRF 3.9+ operators
- `@typing.deprecated` (PEP 702) em cada uma das 15 classes legacy
- `warnings.warn(DeprecationWarning, stacklevel=2)` no `__init__` de cada classe legacy
- Documento oficial da convenção: `v2/docs/RBAC_NAMING.md`
- Testes: 8+ cobrindo HasPerm, composition, deprecation warnings

### Fora do escopo
- Sweep das views existentes (Epic 5)
- Eliminar hardcoded group checks (Epic 3)
- Renomear codenames (Epic 4)
- Configurar CI para falhar em DeprecationWarning — adiado para Epic 5.3

## Issues

- [ ] **Issue 2.1** — Introduzir HasPerm + deprecation das 15 classes + documentação (single PR)

## Acceptance criteria

- [ ] Classe `HasPerm` em `apps/core/permissions.py`, parametrizável por codename
- [ ] `HasPerm` suporta composition DRF (`|`, `&`, `~`)
- [ ] `HasPerm` respeita `is_superuser` bypass (compatível com classes legacy)
- [ ] 15 classes legacy anotadas com `@typing.deprecated` (mensagem aponta para `HasPerm("codename")` equivalente)
- [ ] 15 classes legacy emitem `DeprecationWarning` no `__init__`
- [ ] Arquivo `v2/docs/RBAC_NAMING.md` publicado com convenção completa
- [ ] Testes `test_permissions_hasperm.py` (8 testes mínimos): grant/deny, superuser, anon, composition OR, composition AND, deprecation warning, integração com functional service
- [ ] Baseline parity test (capturado em E1) continua verde
- [ ] Zero mudança de comportamento em endpoints existentes
- [ ] Verificação manual staging: hit em `/api/reports/status-counts/` com role Controle → mesmo HTTP status de antes

## Design da classe

```python
# apps/core/permissions.py (topo do arquivo, antes das existentes)

from __future__ import annotations
import warnings
import typing
from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView


class HasPerm(permissions.BasePermission):
    """
    Capability-oriented parametric permission class.

    Checks a single functional permission codename via the functional
    permissions service. Preferred over subclassing for new endpoints.

    Composition:
        HasPerm("a") | HasPerm("b")  # OR
        HasPerm("a") & HasPerm("b")  # AND
        ~HasPerm("a")                # NOT (rare)

    Usage:
        class MyView(APIView):
            permission_classes = [
                IsAuthenticated,
                HasPerm("core.approve_solicitation"),
            ]

    Note on app_label:
        The "core." prefix is optional — the functional permission system
        uses bare codenames. We accept both forms for familiarity with
        Django's native has_perm() format.
    """

    def __init__(self, codename: str, *, message: str | None = None) -> None:
        # Strip "core." prefix if provided (functional service uses bare codename)
        self.codename = codename.split(".", 1)[-1] if "." in codename else codename
        if message:
            self.message = message

    def __call__(self) -> "HasPerm":
        """DRF calls the permission with () after resolution; we're already an instance."""
        return self

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "is_superuser", False):
            return True
        from apps.core.services.rbac_permissions import get_user_functional_permissions
        return self.codename in get_user_functional_permissions(user)

    def __repr__(self) -> str:
        return f"HasPerm({self.codename!r})"
```

## Deprecation pattern (PEP 702)

```python
# Exemplo para IsDAT
import typing
import warnings

@typing.deprecated(
    "IsDAT is deprecated; use HasPerm('pode_operar_dat_exclusivo') instead. "
    "See v2/docs/RBAC_NAMING.md."
)
class IsDAT(
    funcperm_factory(
        "IsDAT",
        "pode_operar_dat_exclusivo",
        "Apenas usuários do grupo DAT podem realizar esta ação.",
    )
):
    def __init__(self) -> None:
        super().__init__()
        warnings.warn(
            "IsDAT is deprecated; use HasPerm('pode_operar_dat_exclusivo'). "
            "This class will be removed in Epic 5 of the RBAC refactor.",
            DeprecationWarning,
            stacklevel=2,
        )
```

## RBAC_NAMING.md outline (artefato a criar)

```markdown
# RBAC Naming Convention

## Codenames
- Format: `verb_noun` snake_case (English)
- Allowed verbs: create, read, update, delete, approve, publish, import, export, assign, reconcile, view
- Forbidden: admin_, manage_, operate_, configure_, change_, modify_, edit_, list_, set_, write_
- Never: role name, setor name, group name

## Labels (pt-BR, admin UI)
- Format: Verbo infinitivo + substantivo plural
- Examples: "Aprovar solicitações", "Importar planilhas e dados"

## Permission classes
- Prefer: HasPerm("codename") inline
- Exception: object-level checks (IsSolicitationOwner)
- Forbidden: Is<Role>, Is<Setor>, Is<Group>

## Authorization checks
- Canonical: user.has_perm("codename") or HasPerm("codename")
- Forbidden: user.groups.filter(name="X")

## Adding a new permission
1. Add to FUNCTIONAL_PERMISSIONS_SEED
2. Run migration to seed
3. Use HasPerm("codename") in views
4. Add test

## Examples of good/bad
(...)
```

## Fontes autoritativas

- [DRF — Permissions composition](https://www.django-rest-framework.org/api-guide/permissions/#composed-permissions)
- [PEP 702 — Marking deprecations using the type system](https://peps.python.org/pep-0702/)
- [Python warnings — DeprecationWarning semantics](https://docs.python.org/3/library/warnings.html)
- [OWASP — Permission class explosion antipattern](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
