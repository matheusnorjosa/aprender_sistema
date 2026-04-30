"""
PR 9 hardening RBAC (2026-04-30): snapshot literal de `ACCESS_MATRIX`.

Congela a matriz canônica (10 atores × 11 recursos = 110 cells) em forma
literal. Qualquer alteração de célula (ALLOW ↔ DENY ↔ ALLOW_PAYLOAD_INVALID)
falha este test até o snapshot ser atualizado — diff = checklist obrigatório
no review.

Diferença vs `test_rbac_matrix_living.py`:
- Living matrix valida que o **comportamento real** (HTTP request) bate
  com a matriz declarada.
- Contract (este arquivo) valida que a **matriz declarada não mudou
  acidentalmente** desde a última revisão consciente.

Como atualizar quando uma célula mudar intencionalmente:
1. Atualizar `ACCESS_MATRIX` em `apps/core/rbac/matrix.py`.
2. Atualizar `EXPECTED_MATRIX` aqui com o mesmo valor.
3. Documentar a decisão em `v2/docs/rbac_authorization_matrix.md` §6.
4. Diff dos 3 lugares torna a mudança rastreável.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportMissingTypeStubs=false, reportPrivateUsage=false

from __future__ import annotations

from apps.core.rbac.matrix import ACCESS_MATRIX

# Valores literais — NÃO importar de matrix.py. O sentido do contract test
# é detectar drift: se alguém muda a matriz, o snapshot fica diferente.
ALLOW = 200
DENY = 403
ALLOW_PAYLOAD_INVALID = 400


# ============================================================================
# Snapshot literal — 10 atores × 11 recursos
# ============================================================================
#
# REGRA:
# - Adicionar/remover ator ou recurso → atualizar snapshot conscientemente.
# - Mudar ALLOW ↔ DENY ↔ ALLOW_PAYLOAD_INVALID → atualizar snapshot
#   conscientemente E documentar em rbac_authorization_matrix.md §6.
# - Alteração silenciosa → CI vermelho; PR não passa sem revisão.

EXPECTED_MATRIX: dict[str, dict[str, int]] = {
    "grade_mensal": {
        "Superuser": ALLOW,
        "DAT": ALLOW,
        "Controle": ALLOW,
        "Diretoria": DENY,
        "Gerente": ALLOW,
        "Gerente da Superintendência": ALLOW,
        "Assistente Administrativo do Controle": ALLOW,
        "Coordenador": ALLOW,
        "Apoio de Coordenação": ALLOW,
        "Formador": DENY,
    },
    "deslocamentos": {
        "Superuser": ALLOW,
        "DAT": ALLOW,
        "Controle": ALLOW,
        "Diretoria": ALLOW,
        "Gerente": ALLOW,
        "Gerente da Superintendência": ALLOW,
        "Assistente Administrativo do Controle": ALLOW,
        "Coordenador": ALLOW,
        "Apoio de Coordenação": ALLOW,
        "Formador": ALLOW,
    },
    "dashboard_compras": {
        "Superuser": ALLOW,
        "DAT": ALLOW,
        "Controle": DENY,
        "Diretoria": ALLOW,
        "Gerente": DENY,
        "Gerente da Superintendência": DENY,
        "Assistente Administrativo do Controle": DENY,
        "Coordenador": DENY,
        "Apoio de Coordenação": DENY,
        "Formador": DENY,
    },
    "metrics_team_productivity": {
        "Superuser": ALLOW,
        "DAT": ALLOW,
        "Controle": ALLOW,
        "Diretoria": ALLOW,
        "Gerente": DENY,
        "Gerente da Superintendência": DENY,
        "Assistente Administrativo do Controle": ALLOW,
        "Coordenador": DENY,
        "Apoio de Coordenação": DENY,
        "Formador": DENY,
    },
    "ciclos_acoes": {
        "Superuser": ALLOW,
        "DAT": DENY,
        "Controle": DENY,
        "Diretoria": DENY,
        "Gerente": DENY,
        "Gerente da Superintendência": DENY,
        "Assistente Administrativo do Controle": DENY,
        "Coordenador": DENY,
        "Apoio de Coordenação": DENY,
        "Formador": DENY,
    },
    "audit_logs": {
        "Superuser": ALLOW,
        "DAT": ALLOW,
        "Controle": ALLOW,
        "Diretoria": DENY,
        "Gerente": DENY,
        "Gerente da Superintendência": DENY,
        "Assistente Administrativo do Controle": ALLOW,
        "Coordenador": DENY,
        "Apoio de Coordenação": DENY,
        "Formador": DENY,
    },
    "me_events": {
        "Superuser": ALLOW,
        "DAT": ALLOW,
        "Controle": ALLOW,
        "Diretoria": ALLOW,
        "Gerente": ALLOW,
        "Gerente da Superintendência": ALLOW,
        "Assistente Administrativo do Controle": ALLOW,
        "Coordenador": ALLOW,
        "Apoio de Coordenação": ALLOW,
        "Formador": ALLOW,
    },
    "solicitacoes_list": {
        "Superuser": ALLOW,
        "DAT": ALLOW,
        "Controle": ALLOW,
        "Diretoria": ALLOW,
        "Gerente": ALLOW,
        "Gerente da Superintendência": ALLOW,
        "Assistente Administrativo do Controle": ALLOW,
        "Coordenador": ALLOW,
        "Apoio de Coordenação": ALLOW,
        "Formador": ALLOW,
    },
    "solicitacoes_batch_approve": {
        "Superuser": ALLOW_PAYLOAD_INVALID,
        "DAT": DENY,
        "Controle": DENY,
        "Diretoria": DENY,
        "Gerente": DENY,
        "Gerente da Superintendência": ALLOW_PAYLOAD_INVALID,
        "Assistente Administrativo do Controle": ALLOW_PAYLOAD_INVALID,
        "Coordenador": DENY,
        "Apoio de Coordenação": DENY,
        "Formador": DENY,
    },
    "produtos_list": {
        "Superuser": ALLOW,
        "DAT": ALLOW,
        "Controle": ALLOW,
        "Diretoria": DENY,
        "Gerente": DENY,
        "Gerente da Superintendência": DENY,
        "Assistente Administrativo do Controle": ALLOW,
        "Coordenador": DENY,
        "Apoio de Coordenação": DENY,
        "Formador": DENY,
    },
    "usuario_lookup": {
        "Superuser": ALLOW,
        "DAT": ALLOW,
        "Controle": DENY,
        "Diretoria": DENY,
        "Gerente": ALLOW,
        "Gerente da Superintendência": ALLOW,
        "Assistente Administrativo do Controle": DENY,
        "Coordenador": ALLOW,
        "Apoio de Coordenação": ALLOW,
        "Formador": DENY,
    },
}


def test_matrix_snapshot_is_unchanged():
    """
    Snapshot literal de ACCESS_MATRIX. Falha se qualquer célula divergir.

    Como reagir:
    1. Se a mudança é INTENCIONAL (decisão consciente):
       - Atualize EXPECTED_MATRIX neste arquivo.
       - Atualize v2/docs/rbac_authorization_matrix.md §6 (decisões D*).
       - Mencione no PR description o motivo da mudança.
    2. Se a mudança é ACIDENTAL:
       - Reverter alteração em apps/core/rbac/matrix.py::ACCESS_MATRIX.
    """
    assert ACCESS_MATRIX == EXPECTED_MATRIX, (
        "RBAC_MATRIX_DRIFT: ACCESS_MATRIX divergiu do snapshot literal.\n\n"
        "Se a mudança é intencional, atualize EXPECTED_MATRIX aqui e "
        "documente em rbac_authorization_matrix.md §6.\n"
        "Se foi acidental, reverter em apps/core/rbac/matrix.py."
    )


def test_matrix_resource_count_is_eleven():
    """Matriz tem 11 recursos (PR 8 #1313 expandiu de 8 → 11)."""
    assert len(ACCESS_MATRIX) == 11, (
        f"ACCESS_MATRIX tem {len(ACCESS_MATRIX)} recursos; esperado 11. "
        "Adicione recurso em RESOURCES + ACCESS_MATRIX + EXPECTED_MATRIX juntos."
    )


def test_matrix_actor_count_is_ten():
    """Matriz tem 10 atores (PR 8 #1313 expandiu de 8 → 10)."""
    for resource_name, actor_map in ACCESS_MATRIX.items():
        assert len(actor_map) == 10, (
            f"ACCESS_MATRIX['{resource_name}'] tem {len(actor_map)} atores; "
            "esperado 10. Atualize ACTORS + ACCESS_MATRIX + EXPECTED_MATRIX juntos."
        )
