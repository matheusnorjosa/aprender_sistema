"""
#1643 (lote D do grupo B) — alvo do bloqueio e trilha na carga `availability_block` do export-contract.

Decisão do dono (07/11/2026): a partir do corte de 31/07/2026 (`_FORMADOR_CUTOFF`, pela data local do
`inicio`), o bloqueio da planilha entra para quem está ativo e tem papel vigente em gerência ativa que usa
a tela Bloqueios (Gerente, Coordenador, Apoio ou Formador). Fica de fora quem está inativo
(`alvo_inativo`) ou sem papel nenhum desses vigente (`alvo_sem_papel`), com o motivo no relatório.
Antes do corte, qualquer alvo (decisão de 14/09). Cada bloqueio criado grava o AuditLog
`DELEGATE_BLOCK_CREATE` da rota delegada, com origem `import_export_contract`.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false, reportPrivateUsage=false

from __future__ import annotations

from datetime import datetime, timedelta

from django.utils import timezone

import pytest

from apps.core.models import AuditLog, AvailabilityBlock, EquipeGerencia, Gerencia
from apps.core.services.export_contract_importer import ExportContractImporter
from apps.core.tests.factories import UsuarioFactory
from apps.core.tests.test_export_contract_importer_apply_availability_1896 import (
    _CPF,
    AVAIL_HEADER,
    _actor,
    _row,
    _write_export,
)

pytestmark = pytest.mark.django_db

_POS = {"inicio": "2026-11-20T08:00:00", "fim": "2026-11-20T12:00:00"}
_PRE = {"inicio": "2026-03-01T08:00:00", "fim": "2026-03-01T12:00:00"}
_ALLOW = ("availability_block",)


def _gerencia(ativo=True):
    return Gerencia.objects.create(nome="GERENCIA ALVO", nome_setor="Vidas", ativo=ativo)


def _com_papel(usuario, papel="FORMADOR", **kw):
    gerencia = kw.pop("gerencia", None) or _gerencia()
    return EquipeGerencia.objects.create(gerencia=gerencia, usuario=usuario, papel=papel, **kw)


def _csv(*rows):
    return f"{AVAIL_HEADER}\n" + "\n".join(rows) + "\n"


def _dry(path):
    return ExportContractImporter(path=path).run()["por_entidade"]["availability_block"]


def _apply(path, actor, allow=_ALLOW):
    return ExportContractImporter(path=path, apply=True, allow=allow, actor=actor).run()["applied"]


def _audits():
    return AuditLog.objects.filter(action=AuditLog.Action.DELEGATE_BLOCK_CREATE)


def test_pos_corte_alvo_inativo_nao_cria(tmp_path):
    actor = _actor()
    pessoa = UsuarioFactory(cpf=_CPF, is_active=False)
    _com_papel(pessoa)
    path = _write_export(tmp_path, {"availability_block": _csv(_row(**_POS))})

    dry = _dry(path)
    assert dry["would_reject"] == 1
    assert dry["reject_reasons"]["alvo_inativo"] == 1

    assert _apply(path, actor)["availability_block"] == 0
    assert AvailabilityBlock.objects.count() == 0


@pytest.mark.parametrize(
    "caso", ["sem_vinculo", "so_grupo_formador", "so_equipe", "vinculo_encerrado", "gerencia_inativa"]
)
def test_pos_corte_alvo_sem_papel_nao_cria(tmp_path, caso):
    """O critério é o PAPEL vigente em gerência ativa (não o grupo, não o papel EQUIPE, não o vínculo vencido)."""
    actor = _actor()
    pessoa = UsuarioFactory(cpf=_CPF)
    ontem = timezone.localdate() - timedelta(days=1)
    if caso == "so_grupo_formador":
        from django.contrib.auth.models import Group

        pessoa.groups.add(Group.objects.get_or_create(name="Formador")[0])
    elif caso == "so_equipe":
        _com_papel(pessoa, papel=EquipeGerencia.PAPEL_EQUIPE)
    elif caso == "vinculo_encerrado":
        _com_papel(pessoa, valid_from=ontem - timedelta(days=30), valid_to=ontem)
    elif caso == "gerencia_inativa":
        _com_papel(pessoa, gerencia=_gerencia(ativo=False))
    path = _write_export(tmp_path, {"availability_block": _csv(_row(**_POS))})

    dry = _dry(path)
    assert dry["would_reject"] == 1
    assert dry["reject_reasons"]["alvo_sem_papel"] == 1

    assert _apply(path, actor)["availability_block"] == 0
    assert AvailabilityBlock.objects.count() == 0


@pytest.mark.parametrize("papel", ["COORDENADOR", "APOIO", "GERENTE"])
def test_pos_corte_papel_de_atuacao_sem_formador_cria(tmp_path, papel):
    """Decisão do dono (07/11): coordenadora ou apoio que não é formadora também entra."""
    actor = _actor()
    pessoa = UsuarioFactory(cpf=_CPF)
    _com_papel(pessoa, papel=papel)
    path = _write_export(tmp_path, {"availability_block": _csv(_row(**_POS))})

    assert _dry(path)["would_create"] == 1
    assert _apply(path, actor)["availability_block"] == 1
    assert AvailabilityBlock.objects.get().usuario_id == pessoa.pk


def test_pos_corte_alvo_ativo_cria_com_auditlog(tmp_path):
    actor = _actor()
    pessoa = UsuarioFactory(cpf=_CPF)
    _com_papel(pessoa)
    path = _write_export(tmp_path, {"availability_block": _csv(_row(**_POS))})

    assert _apply(path, actor)["availability_block"] == 1
    block = AvailabilityBlock.objects.get()
    assert block.created_by_id == actor.pk
    log = _audits().get()
    assert log.usuario_id == actor.pk
    assert log.model_name == "AvailabilityBlock"
    details = dict(log.details)
    # Mesmo instante do bloqueio; o fuso do texto não importa.
    assert datetime.fromisoformat(details.pop("inicio")) == block.inicio
    assert datetime.fromisoformat(details.pop("fim")) == block.fim
    assert details == {
        "delegate_user_id": actor.pk,
        "target_formador_id": pessoa.pk,
        "block_id": block.pk,
        "origem": "import_export_contract",
    }


def test_rodar_de_novo_nao_duplica_auditlog(tmp_path):
    actor = _actor()
    _com_papel(UsuarioFactory(cpf=_CPF))
    path = _write_export(tmp_path, {"availability_block": _csv(_row(**_POS))})

    _apply(path, actor)
    assert _apply(path, actor)["availability_block"] == 0
    assert AvailabilityBlock.objects.count() == 1
    assert _audits().count() == 1


def test_dry_run_espelha_apply(tmp_path):
    actor = _actor()
    _com_papel(UsuarioFactory(cpf=_CPF))  # ativo com papel, pós-corte → cria
    UsuarioFactory(cpf="52998224725", is_active=False)  # inativo pós-corte → alvo_inativo
    UsuarioFactory(cpf="39053344705", is_active=False)  # inativo pré-corte → cria (14/09)
    csv = _csv(_row(**_POS), _row(cpf="52998224725", **_POS), _row(cpf="39053344705", **_PRE))
    path = _write_export(tmp_path, {"availability_block": csv})

    dry = _dry(path)
    assert (dry["would_create"], dry["would_reject"]) == (2, 1)
    assert dry["reject_reasons"]["alvo_inativo"] == 1

    assert _apply(path, actor)["availability_block"] == 2
    assert _audits().count() == 2


def test_usuario_criado_na_mesma_execucao_recebe_bloqueio(tmp_path):
    """usuario e equipe_gerencia vêm antes no ENTITY_ORDER: o índice de alvo é montado no apply, não no classify."""
    actor = _actor()
    Gerencia.objects.create(nome="GERENCIA 2", nome_setor="Vidas")
    path = _write_export(
        tmp_path,
        {
            "usuario": f"nome_completo,cpf,email,cargo\nFulana Nova,{_CPF},,Formadores\n",
            "equipe_gerencia": f"gerencia,usuario_cpf,papel,setor_canonico\nVidas,{_CPF},FORMADOR,\n",
            "availability_block": _csv(_row(**_POS)),
        },
    )

    applied = _apply(path, actor, allow=("usuario", "equipe_gerencia", "availability_block"))
    assert applied["availability_block"] == 1
    assert AvailabilityBlock.objects.get().usuario.cpf == _CPF
    assert _audits().count() == 1


@pytest.mark.parametrize(("papel", "cria"), [("FORMADOR", True), ("COORDENADOR", True), ("EQUIPE", False)])
def test_conta_existente_vinculo_na_mesma_execucao_dry_run_espelha_apply(tmp_path, papel, cria):
    """Conta já existe e o vínculo entra pela equipe_gerencia do mesmo pacote: o dry-run prevê o vínculo
    (como o apply, que monta o índice depois de gravá-lo) e não recusa por `alvo_sem_papel`."""
    actor = _actor()
    UsuarioFactory(cpf=_CPF)
    Gerencia.objects.create(nome="GERENCIA 2", nome_setor="Vidas")
    path = _write_export(
        tmp_path,
        {
            "equipe_gerencia": f"gerencia,usuario_cpf,papel,setor_canonico\nVidas,{_CPF},{papel},\n",
            "availability_block": _csv(_row(**_POS)),
        },
    )

    dry = _dry(path)
    assert (dry["would_create"], dry["would_reject"]) == ((1, 0) if cria else (0, 1))
    assert dry["reject_reasons"]["alvo_sem_papel"] == (0 if cria else 1)

    applied = _apply(path, actor, allow=("equipe_gerencia", "availability_block"))
    assert applied["availability_block"] == (1 if cria else 0)


def test_pre_corte_inativo_sem_papel_cria(tmp_path):
    """Guarda da decisão de 14/09: antes do corte vale qualquer alvo (dado histórico), com AuditLog."""
    actor = _actor()
    UsuarioFactory(cpf=_CPF, is_active=False)
    path = _write_export(tmp_path, {"availability_block": _csv(_row(**_PRE))})

    assert _dry(path)["would_create"] == 1
    assert _apply(path, actor)["availability_block"] == 1
    assert _audits().count() == 1
