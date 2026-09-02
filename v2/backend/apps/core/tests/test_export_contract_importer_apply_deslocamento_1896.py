"""
Tests do APPLY (create-only) da fatia `deslocamento` do export-contract.

Contrato (sheets.banco / RELAY 31): deslocamento de um formador entre municípios (texto livre, NÃO
FK). `usuario` por CPF → Usuario (FK PROTECT NOT NULL → sem match = reject). `origem`/`destino` são
texto (CharField 200). `start_date`/`end_date` DateField. Idempotência por `external_hash` (SHA1,
ADR-012) sobre (usuario, start, end, origem, destino, **observacao**) — a observacao ENTRA na chave,
senão ida e volta (ou pernas que só diferem na observação) colapsam. Sem `created_by` → não exige actor.

Segurança: apply exige allowlist; create-only; idempotente. Fixtures sintéticos.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false

from __future__ import annotations

import json
from datetime import date
from typing import Any

import pytest

from apps.core.models import Deslocamento
from apps.core.services.export_contract_importer import ExportContractImporter
from apps.core.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db

DESLOC_HEADER = (
    "usuario,usuario_norm,usuario_cpf,origem,origem_norm,destino,destino_norm,"
    "start_date,end_date,futuro,observacao,timezone"
)
_CPF = "22255588846"


def _write_export(tmp_path, files: dict[str, str]) -> str:
    d = tmp_path / "export"
    d.mkdir()
    manifest: dict[str, Any] = {"generated_at": "2026-08-24", "snapshot_date": "2026-08-24", "entities": {}}
    for name, content in files.items():
        (d / f"{name}.csv").write_text(content, encoding="utf-8")
        manifest["entities"][name] = {"file_csv": f"{name}.csv", "rows": max(content.strip().count("\n"), 0)}
    (d / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return str(d)


def _row(
    cpf=_CPF,
    usuario="Fulana",
    origem="Fortaleza",
    destino="ITAGI - BA",
    start="2026-02-11",
    end="2026-02-11",
    obs="Deslocamento",
):
    return f"{usuario},{usuario.upper()},{cpf},{origem},{origem.upper()},{destino},{destino.upper()},{start},{end},false,{obs},America/Fortaleza"


def test_apply_deslocamento_creates(tmp_path):
    pessoa = UsuarioFactory(cpf=_CPF)
    path = _write_export(tmp_path, {"deslocamento": f"{DESLOC_HEADER}\n{_row()}\n"})
    r = ExportContractImporter(path=path, apply=True, allow=("deslocamento",)).run()
    assert r["applied"]["deslocamento"] == 1
    d = Deslocamento.objects.get()
    assert d.usuario_id == pessoa.id
    assert d.origem == "Fortaleza"
    assert d.destino == "ITAGI - BA"
    assert d.start_date == date(2026, 2, 11)
    assert d.end_date == date(2026, 2, 11)
    assert d.observacao == "Deslocamento"
    assert d.external_hash  # hash de idempotência preenchido


def test_apply_deslocamento_resolves_usuario_by_cpf(tmp_path):
    pessoa = UsuarioFactory(cpf=_CPF)
    path = _write_export(tmp_path, {"deslocamento": f"{DESLOC_HEADER}\n{_row(usuario='Outro Nome')}\n"})
    ExportContractImporter(path=path, apply=True, allow=("deslocamento",)).run()
    assert Deslocamento.objects.get().usuario_id == pessoa.id


def test_apply_deslocamento_rejects_unresolved_cpf(tmp_path):
    """CPF sem Usuario → não cria (usuario é PROTECT NOT NULL)."""
    UsuarioFactory(cpf="33366699957")
    path = _write_export(tmp_path, {"deslocamento": f"{DESLOC_HEADER}\n{_row(cpf=_CPF)}\n"})
    r = ExportContractImporter(path=path, apply=True, allow=("deslocamento",)).run()
    assert r["applied"]["deslocamento"] == 0
    assert Deslocamento.objects.count() == 0


def test_apply_deslocamento_rejects_missing_date(tmp_path):
    UsuarioFactory(cpf=_CPF)
    path = _write_export(tmp_path, {"deslocamento": f"{DESLOC_HEADER}\n{_row(start='')}\n"})
    r = ExportContractImporter(path=path, apply=True, allow=("deslocamento",)).run()
    assert r["applied"]["deslocamento"] == 0
    assert Deslocamento.objects.count() == 0


def test_apply_deslocamento_no_actor_needed(tmp_path):
    """Deslocamento não tem created_by → apply funciona sem actor."""
    UsuarioFactory(cpf=_CPF)
    path = _write_export(tmp_path, {"deslocamento": f"{DESLOC_HEADER}\n{_row()}\n"})
    r = ExportContractImporter(path=path, apply=True, allow=("deslocamento",), actor=None).run()
    assert r["applied"]["deslocamento"] == 1


def test_apply_deslocamento_idempotent(tmp_path):
    UsuarioFactory(cpf=_CPF)
    path = _write_export(tmp_path, {"deslocamento": f"{DESLOC_HEADER}\n{_row()}\n"})
    ExportContractImporter(path=path, apply=True, allow=("deslocamento",)).run()
    r2 = ExportContractImporter(path=path, apply=True, allow=("deslocamento",)).run()
    assert r2["applied"]["deslocamento"] == 0  # external_hash já existe
    assert Deslocamento.objects.count() == 1


def test_apply_deslocamento_observacao_in_hash(tmp_path):
    """Duas linhas iguais em tudo menos a observacao → distintas (observacao entra no hash, RELAY 31)."""
    UsuarioFactory(cpf=_CPF)
    csv = f"{DESLOC_HEADER}\n" f"{_row(obs='ida')}\n" f"{_row(obs='volta')}\n"
    r = ExportContractImporter(
        path=_write_export(tmp_path, {"deslocamento": csv}), apply=True, allow=("deslocamento",)
    ).run()
    assert r["applied"]["deslocamento"] == 2  # observacao diferente → não colapsa
    assert Deslocamento.objects.count() == 2


def test_apply_deslocamento_blocked_without_allowlist(tmp_path):
    UsuarioFactory(cpf=_CPF)
    path = _write_export(tmp_path, {"deslocamento": f"{DESLOC_HEADER}\n{_row()}\n"})
    r = ExportContractImporter(path=path, apply=True, allow=()).run()
    assert r["apply_blocked"] is True
    assert Deslocamento.objects.count() == 0


def test_classify_deslocamento_create_and_reject(tmp_path):
    UsuarioFactory(cpf=_CPF)
    csv = (
        f"{DESLOC_HEADER}\n"
        f"{_row()}\n"  # resolve → create
        f"{_row(cpf='00000000000')}\n"  # CPF sem match → reject
    )
    r = ExportContractImporter(path=_write_export(tmp_path, {"deslocamento": csv})).run()["por_entidade"][
        "deslocamento"
    ]
    assert r["would_create"] == 1
    assert r["would_reject"] == 1
