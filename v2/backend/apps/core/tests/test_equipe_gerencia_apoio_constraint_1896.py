"""#1896 — a constraint `apoio_requires_supervisor` foi afrouxada (Decisão B do dono).

O dado real (equipe_gerencia v16) tem APOIO legítimo sem `coordenador_supervisor` (Daniel Lima
Moura). A CheckConstraint bloqueava o seed inteiro por 1 linha. Passa a ser opcional: APOIO pode
existir sem supervisor; a FK `coordenador_supervisor` continua disponível quando conhecida.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false

from __future__ import annotations

import pytest

from apps.core.models.organizacao import EquipeGerencia, Gerencia
from apps.core.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db


def test_apoio_without_supervisor_is_allowed():
    """Antes do #1896 isto levantava IntegrityError (apoio_requires_supervisor)."""
    g = Gerencia.objects.create(nome="GERENCIA X", nome_setor="Vidas")
    u = UsuarioFactory(username="apoio1", cpf="11144477735")
    ev = EquipeGerencia.objects.create(gerencia=g, usuario=u, papel="APOIO", coordenador_supervisor=None)
    assert ev.pk is not None
    assert ev.coordenador_supervisor is None
