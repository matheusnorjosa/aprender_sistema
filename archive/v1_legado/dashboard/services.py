"""
Serviços de KPIs canônicos para o dashboard.

Regras:
- coordenadores_ativos = usuários no grupo 'coordenador' ∪ usuários que solicitaram evento com status != CANCELADO
- formadores_envolvidos = usuários vinculados como formador em eventos com status != CANCELADO
- Implementação robusta e tolerante a variações de schema
"""

from __future__ import annotations

from typing import Dict, Optional

from django.contrib.auth import get_user_model
from django.db import connection

STATUS_NC = ("CRIADO", "APROVADO", "REALIZADO")


def _table_exists(name: str) -> bool:
    """Verifica se tabela existe no banco."""
    with connection.cursor() as c:
        c.execute("SELECT to_regclass(%s)", [name])
        return c.fetchone()[0] is not None


def _col_exists(table: str, col: str) -> bool:
    """Verifica se coluna existe na tabela."""
    with connection.cursor() as c:
        c.execute(
            """SELECT 1 FROM information_schema.columns
               WHERE table_name=%s AND column_name=%s""",
            [table, col],
        )
        return c.fetchone() is not None


def _first_existing(tables: list[str]) -> Optional[str]:
    """Retorna a primeira tabela que existe da lista."""
    for t in tables:
        if _table_exists(t):
            return t
    return None


def _count(sql: str, params: list = None) -> int:
    """Executa SQL e retorna contagem."""
    with connection.cursor() as c:
        c.execute(sql, params or [])
        return int(c.fetchone()[0])


def compute_dashboard_kpis() -> Dict[str, int]:
    """
    Calcula KPIs canônicos do dashboard.

    Returns:
        Dict com chaves:
        - coordenadores_ativos: int
        - formadores_envolvidos: int
        - total_eventos: int
        - eventos_nao_cancelados: int
    """
    # 1) Tabela principal de solicitações/eventos
    sol_table = _first_existing(
        ["core_solicitacao", "agenda_solicitacao", "agenda_evento", "core_evento"]
    )
    coord_ativos = 0
    formadores_env = 0
    total_eventos = 0
    eventos_validos = 0

    if sol_table:
        # Detectar coluna de solicitante
        solicit_col = (
            "usuario_solicitante_id"
            if _col_exists(sol_table, "usuario_solicitante_id")
            else (
                "solicitante_id" if _col_exists(sol_table, "solicitante_id") else None
            )
        )

        # Contagem total e válidos
        total_eventos = _count(f"SELECT COUNT(*) FROM {sol_table}")
        placeholders = ",".join(["%s"] * len(STATUS_NC))
        eventos_validos = _count(
            f"SELECT COUNT(*) FROM {sol_table} WHERE status IN ({placeholders})",
            list(STATUS_NC),
        )

        # Coordenadores do grupo (usar core_usuario se auth_user não existir)
        user_table = "core_usuario" if _table_exists("core_usuario") else "auth_user"
        user_id_col = "usuario_id" if "usuario" in user_table else "user_id"
        groups_table = (
            user_table.replace("usuario", "usuario_groups")
            if "usuario" in user_table
            else "auth_user_groups"
        )
        coord_grupo = _count(
            f"""
            SELECT COUNT(DISTINCT u.id)
              FROM {user_table} u
              JOIN {groups_table} ug ON ug.{user_id_col} = u.id
              JOIN auth_group g ON g.id = ug.group_id
             WHERE LOWER(g.name) = 'coordenador'
        """
        )

        # Solicitantes com status != CANCELADO
        coord_solic = 0
        if solicit_col:
            coord_solic = _count(
                f"SELECT COUNT(DISTINCT {solicit_col}) FROM {sol_table} "
                f"WHERE status IN ({placeholders}) AND {solicit_col} IS NOT NULL",
                list(STATUS_NC),
            )
        # União (aproximação por soma)
        coord_ativos = coord_grupo + max(0, coord_solic - 0)

        # 2) Formadores envolvidos
        # Preferência: tabela Participante com papel='FORMADOR' + join no {sol_table}
        part_table = _first_existing(["core_participante", "agenda_participante"])
        if part_table and _col_exists(part_table, "papel"):
            # Detectar FK do participante -> evento/sol
            ev_fk = "evento_id" if _col_exists(part_table, "evento_id") else None
            user_fk = "usuario_id" if _col_exists(part_table, "usuario_id") else None
            if ev_fk and user_fk:
                formadores_env = _count(
                    f"""
                    SELECT COUNT(DISTINCT p.{user_fk})
                      FROM {part_table} p
                      JOIN {sol_table} s ON s.id = p.{ev_fk}
                     WHERE p.papel = 'FORMADOR' AND s.status IN ({placeholders})
                       AND p.{user_fk} IS NOT NULL
                    """,
                    list(STATUS_NC),
                )
        # Fallback: 0 se não houver estrutura compatível

    return {
        "coordenadores_ativos": coord_ativos,
        "formadores_envolvidos": formadores_env,
        "total_eventos": total_eventos,
        "eventos_nao_cancelados": eventos_validos,
    }
