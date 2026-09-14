"""
bloqueios_import: o bloqueio importado ganha `created_by` (o ator) + AuditLog (#1643).

O import criava `AvailabilityBlock` por nome **sem atribuição nem auditoria** — não
dava para saber quem gerou o bloqueio (que afeta RD-02/RD-03). Este fix threada o
ator (a view passa `request.user`; o task Celery passa `job.user`) e registra
`created_by` + um AuditLog `DELEGATE_BLOCK_CREATE` (origem=import), espelhando o
`perform_create` da API. NÃO muda QUAIS linhas entram (validação de alvo
is_active/Formador fica como decisão de produto — pode ser mais estrita que a
prática operacional).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false, reportArgumentType=false, reportCallIssue=false

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from apps.core.models import AuditLog, AvailabilityBlock
from apps.core.services.bloqueios_import import import_bloqueios_from_file
from apps.core.tests.factories import UsuarioFactory


@pytest.fixture
def ator(db):
    return UsuarioFactory(username="dat_ator", cpf="99999999999", groups=["DAT"])


@pytest.fixture
def alvo(db):
    return UsuarioFactory(
        username="alvo_bloq",
        cpf="88888888888",
        first_name="Alvo",
        last_name="Bloqueado",
    )


@pytest.fixture
def csv_alvo(alvo):
    content = (
        "usuario,inicio,fim,tipo,motivo\n"
        f"{alvo.first_name} {alvo.last_name},2026-04-01 08:00,2026-04-01 12:00,P,Teste\n"
    )
    temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    temp.write(content)
    temp.close()
    yield temp.name
    Path(temp.name).unlink(missing_ok=True)


@pytest.mark.django_db
class TestBloqueiosImportActor:
    """#1643 — bloqueio importado atribuido ao ator + auditado."""

    def test_created_by_e_o_ator(self, csv_alvo, ator, alvo):
        import_bloqueios_from_file(path=csv_alvo, dry_run=False, actor=ator)

        bloco = AvailabilityBlock.objects.get(usuario=alvo)
        assert bloco.created_by_id == ator.id

    def test_auditlog_registrado(self, csv_alvo, ator, alvo):
        import_bloqueios_from_file(path=csv_alvo, dry_run=False, actor=ator)

        assert AuditLog.objects.filter(
            action=AuditLog.Action.DELEGATE_BLOCK_CREATE,
            usuario=ator,
        ).exists()

    def test_sem_ator_nao_quebra(self, csv_alvo, alvo):
        # Retrocompat: chamadas legadas sem ator seguem criando (created_by nulo).
        import_bloqueios_from_file(path=csv_alvo, dry_run=False)
        assert AvailabilityBlock.objects.filter(usuario=alvo).exists()
