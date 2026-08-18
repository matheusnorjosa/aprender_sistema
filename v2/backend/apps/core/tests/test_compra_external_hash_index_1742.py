"""
#1742 PR-B: `external_hash` tinha TRES indices — `db_index=True` no campo,
`models.Index(fields=["external_hash"])` no Meta e a `UniqueConstraint`. O indice
unico da constraint ja cobre os lookups de idempotencia do import; os outros dois
eram redundantes (3 btrees na mesma coluna). A migracao 0084 remove os dois extras.

RED no codigo antigo: `pg_indexes` traria 3+ linhas para `external_hash` (o assert
por igualdade exata falharia). GREEN: apenas o indice unico da constraint.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false

from __future__ import annotations

from django.db import connection

import pytest


@pytest.mark.django_db
def test_external_hash_tem_apenas_o_indice_unico():
    with connection.cursor() as cur:
        cur.execute(
            "SELECT indexname FROM pg_indexes "
            "WHERE tablename = 'core_compra' AND indexdef LIKE '%%external_hash%%' "
            "ORDER BY indexname"
        )
        indices = [row[0] for row in cur.fetchall()]

    assert indices == [
        "core_compra_external_hash_unique"
    ], f"esperado apenas o indice unico em external_hash; achou: {indices}"
