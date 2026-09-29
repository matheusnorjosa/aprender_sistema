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
from typing import Any

from django.core.management import call_command

import pytest

from apps.core.models import AuditLog
from apps.core.tests.factories import SolicitacaoFactory, UsuarioFactory


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


def _check_segregacao() -> dict[str, Any]:
    out = StringIO()
    call_command("compliance_audit", "--days=30", "--format=json", stdout=out)
    report = json.loads(out.getvalue())
    return next(c for c in report["checks"] if c["rule"] == "PA-02 (segregação)")


@pytest.mark.django_db
def test_segregacao_conta_decisao_propria_e_ignora_autoaprovacao_de_superuser():
    """PR B1 (M11-17): decidir a própria viola PA-02 (segregação), não PA-01; APPROVE e
    REJECT contam; a autoaprovação de superuser (`details.autoaprovacao`) é break-glass."""
    aprovada = SolicitacaoFactory(status="aprovado")
    reprovada = SolicitacaoFactory(status="reprovado")
    break_glass = SolicitacaoFactory(status="aprovado")
    anterior_ao_b1 = SolicitacaoFactory(status="aprovado")
    alheia = SolicitacaoFactory(status="aprovado")
    for sol, ator, action, extra in (
        (aprovada, aprovada.usuario, "APPROVE", {"autoridade": "gerente_superintendencia"}),
        (reprovada, reprovada.usuario, "REJECT", {"autoridade": "gerente_superintendencia"}),
        (break_glass, break_glass.usuario, "APPROVE", {"autoridade": "superuser", "autoaprovacao": True}),
        # Antes do B1 a regra não existia e o log não tem `autoridade`: não conta.
        (anterior_ao_b1, anterior_ao_b1.usuario, "APPROVE", {}),
        # Decisão legítima: outra pessoa decidiu.
        (alheia, UsuarioFactory(), "APPROVE", {"autoridade": "gerente_superintendencia"}),
    ):
        AuditLog.objects.create(
            usuario=ator,
            action=action,
            model_name="Solicitacao",
            details={"solicitacao_id": sol.id, **extra},
        )

    check = _check_segregacao()

    assert check["violations"] == 2
    assert check["status"] == "FAIL"
