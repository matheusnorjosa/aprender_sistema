"""Exercita o command `compliance_audit` end-to-end.

Este era o teste AUSENTE que deixou o AUDIT-01 apodrecer: a subquery
`values_list("details__solicitacao_id")` retorna jsonb e o `id__in=<jsonb>` compara
com o `id` (bigint) -> `ProgrammingError: operator does not exist: bigint = jsonb`.
O comando crashava em qualquer execução real com dados no período. Aqui garantimos que
ele roda de ponta a ponta (inclusive AUDIT-01 e o GCAL-01 que vinha depois do crash).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportMissingParameterType=false, reportUnknownParameterType=false

from __future__ import annotations

import json
from io import StringIO

from django.core.management import call_command

import pytest

from apps.core.models import AuditLog
from apps.core.tests.factories import SolicitacaoFactory


@pytest.mark.django_db
def test_compliance_audit_roda_sem_crashar_e_emite_json():
    sol = SolicitacaoFactory(status="aprovado")
    # Um log de CREATE com o id no details exercita o ramo do AUDIT-01 (id no set).
    AuditLog.objects.create(
        usuario=sol.usuario,
        action="CREATE",
        model_name="Solicitacao",
        details={"solicitacao_id": sol.id},
    )

    out = StringIO()
    call_command("compliance_audit", "--days=30", "--format=json", stdout=out)

    report = json.loads(out.getvalue())
    rules = {c["rule"] for c in report["checks"]}
    # AUDIT-01 (crashava) e GCAL-01 (vinha depois do crash) precisam constar.
    assert "AUDIT-01" in rules
    assert "GCAL-01" in rules
    assert report["summary"]["total_checks"] == len(report["checks"])
    # A solicitacao tem trilha de CREATE -> nao entra na contagem "sem audit".
    audit01 = next(c for c in report["checks"] if c["rule"] == "AUDIT-01")
    assert audit01["violations"] == 0
