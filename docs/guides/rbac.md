# RBAC — Controle de Acesso

> **Guia consolidado (SDD 2026-06-19).** O conteúdo legado deste guia (modelo antigo via `views_basic.py`)
> foi arquivado em `v2/docs/_archive/legacy-guides/rbac.md`. A documentação **canônica e atual** de RBAC é:

- **Convenção de nomes + idioma `HasPerm`/composition**: [`RBAC_NAMING.md`](../../v2/docs/RBAC_NAMING.md)
- **Matriz de autorização (atores × capabilities × policies)**: [`rbac_authorization_matrix.md`](../../v2/docs/rbac_authorization_matrix.md)
- **Módulo de código**: [`apps/core/rbac/README.md`](../../v2/backend/apps/core/rbac/README.md)
- **Guia do administrador (atribuir Setor/Função na UI)**: [`GUIA_ADMIN_RBAC.md`](../../v2/docs/GUIA_ADMIN_RBAC.md)

## Em uma linha

- Autorização em views usa `permission_classes = [HasPerm("codename")]` — **não** checagem direta de grupos
  (`user.groups.filter(name=...)` é banido pelo `scripts/rbac_lint.py`).
- SSOT de setores/funções: `apps.core.constants` (**13 setores, 5 funções**, inclui "Assistente Administrativo").
- SSOT de capabilities × grupos: `apps.core.rbac` + admin-driven (Group × Capability).
