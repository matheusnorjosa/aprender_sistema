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

# === SETORES (10) — Onde o usuário trabalha ===
SETOR_GROUPS: list[str] = [
    # Gerências de projeto
    "Superintendência",  # SUPERINTENDENCIA - Fluxo SUPER
    "Vidas",  # GERENCIA 2 - Fluxo NAO_SUPER
    "Fluir",  # GERENCIA 3 - Fluxo NAO_SUPER
    "ACerta",  # GERENCIA 4 - Fluxo NAO_SUPER
    "Brincando",  # GERENCIA 5 - Fluxo NAO_SUPER
    "Sou da Paz",  # GERENCIA 6 - Fluxo NAO_SUPER
    # Setores administrativos/operacionais
    "DAT",  # Departamento de Apoio Técnico
    "Controle",  # Setor de Controle
    "Gerência",  # Gerência genérica
    "Diretoria",  # Diretoria - Acesso a dashboards
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
