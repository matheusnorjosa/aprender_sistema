"""
RBAC data-scope constants.

Estes grupos são usados para **data scope** (filtrar querysets por função
do usuário), NÃO para autorização. Autorização passa sempre por
`user.has_perm()` / `HasPerm(codename)` / `user_has_any_perm`.

Ver v2/docs/RBAC_NAMING.md §4 e master-plan §4.
"""

# Coordenadores (para dropdown /api/options/coordenadores/)
COORDENADOR_ROLE_GROUPS: tuple[str, ...] = ("Coordenador", "Apoio de Coordenação")

# Formadores (para dropdown /api/options/formadores/)
FORMADOR_ROLE_GROUPS: tuple[str, ...] = ("Formador",)
