"""
Constantes RBAC centralizadas — Fonte única de verdade.

Definições:
- SETOR_GROUPS: Grupos de setor (onde o usuário trabalha)
- FUNCAO_GROUPS: Grupos de função (o que o usuário pode fazer)
- ALLOWED_USER_GROUPS: União de setores + funções (whitelist para atribuição)
- RESERVED_GROUPS: Grupos que não podem ser deletados/renomeados sem confirmação

Ref: docs/MAPEAMENTO_COMPLETO_SETORES_GERENCIAS.md
"""

from __future__ import annotations

# === SETORES (13) — Onde o usuário trabalha ===
SETOR_GROUPS: list[str] = [
    # Gerências de projeto (cada uma = 1 Gerencia no model core_gerencia)
    "Superintendência",  # SUPERINTENDENCIA - Fluxo SUPER
    "Vidas",  # GERENCIA 2 - Fluxo NAO_SUPER
    "Fluir",  # GERENCIA 3 - Fluxo NAO_SUPER
    "ACerta",  # GERENCIA 4 - Fluxo NAO_SUPER
    "Brincando",  # GERENCIA 5 - Fluxo NAO_SUPER
    "Sou da Paz",  # GERENCIA 6 - Fluxo NAO_SUPER
    # Setores administrativos/operacionais
    "DAT",  # Departamento de Apoio Técnico
    "Controle",  # Setor de Controle
    "Diretoria",  # Diretoria - Acesso a dashboards
    # Setores de operação de ações/notificações
    "Comercial",
    "Relacionamento",
    "Logística Viagens",
    "Logística Galpão",
]

# === FUNÇÕES (4) — O que o usuário pode fazer ===
FUNCAO_GROUPS: list[str] = [
    "Formador",
    "Coordenador",
    "Apoio de Coordenação",
    "Gerente",
]

# === WHITELIST — Grupos atribuíveis a usuários via admin/API ===
ALLOWED_USER_GROUPS: set[str] = set(SETOR_GROUPS) | set(FUNCAO_GROUPS)

# === RESERVADOS — Proteção contra delete/rename acidental ===
RESERVED_GROUPS: frozenset[str] = frozenset(SETOR_GROUPS) | frozenset(FUNCAO_GROUPS)


# =======================================================================
# Data scope constants (Epic 3 RBAC Refactor, 2026-04-23)
#
# Nomes de grupos Django usados em filtros de QUERYSET para data scope
# (ex: "quem é formador para o dropdown?"). NUNCA usar para autorização —
# autorização passa por user.has_perm() / HasPerm(codename) / user_has_any_perm.
#
# Centralizadas aqui para que um rename organizacional futuro seja
# one-line change (sem caçar strings literais pelo código).
#
# Ver v2/docs/RBAC_NAMING.md §4 e master-plan §4.
# =======================================================================

# Coordenadores (para dropdown /api/options/coordenadores/)
COORDENADOR_ROLE_GROUPS: tuple[str, ...] = ("Coordenador", "Apoio de Coordenação")

# Formadores (para dropdown /api/options/formadores/)
FORMADOR_ROLE_GROUPS: tuple[str, ...] = ("Formador",)
