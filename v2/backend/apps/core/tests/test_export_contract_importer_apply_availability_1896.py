"""
Tests do APPLY (create-only) da fatia `availability_block` do export-contract.

Contrato (sheets.banco / RELAY 31): bloco de disponibilidade de um formador. `usuario` resolvido
por CPF → Usuario (FK PROTECT NOT NULL → sem match = reject, não cria bloco órfão). `inicio`/`fim`
são datetimes LOCAIS (America/Fortaleza) → armazenados em UTC (RD-06). `tipo` ∈ {T, P}
(CheckConstraint no BD) → fora disso reject. `motivo` sem origem na planilha → vazio. NK
existence-based (usuario, inicio, fim, tipo). Exige actor (created_by).

Segurança: apply exige allowlist + actor; create-only; idempotente. Fixtures sintéticos.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from django.utils import timezone

import pytest

from apps.core.models import AvailabilityBlock
from apps.core.services.export_contract_importer import ExportContractImporter
from apps.core.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db

_TZ = ZoneInfo("America/Fortaleza")
AVAIL_HEADER = (
    "usuario,usuario_norm,usuario_cpf,inicio,fim,inicio_data,fim_data,"
    "futuro,dia_unico,janela_presumida,tipo,tipo_raw,motivo,timezone"
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


def _actor():
    return UsuarioFactory(username="u_apply_avail", password="x", cpf="11144477735")


def _row(cpf=_CPF, usuario="Fulana", inicio="2026-02-28T00:00:00", fim="2026-03-02T23:59:59", tipo="T", motivo=""):
    # ordem: usuario,usuario_norm,usuario_cpf,inicio,fim,inicio_data,fim_data,futuro,dia_unico,
    #        janela_presumida,tipo,tipo_raw,motivo,timezone
    return (
        f"{usuario},{usuario.upper()},{cpf},{inicio},{fim},{inicio[:10]},{fim[:10]},"
        f"false,false,false,{tipo},Total,{motivo},America/Fortaleza"
    )


def test_apply_availability_creates_block(tmp_path):
    actor = _actor()
    pessoa = UsuarioFactory(cpf=_CPF)
    path = _write_export(tmp_path, {"availability_block": f"{AVAIL_HEADER}\n{_row()}\n"})
    r = ExportContractImporter(path=path, apply=True, allow=("availability_block",), actor=actor).run()
    assert r["applied"]["availability_block"] == 1
    b = AvailabilityBlock.objects.get()
    assert b.usuario_id == pessoa.id
    assert b.tipo == "T"
    assert b.inicio == timezone.make_aware(datetime(2026, 2, 28, 0, 0, 0), _TZ)  # local → UTC
    assert b.fim == timezone.make_aware(datetime(2026, 3, 2, 23, 59, 59), _TZ)
    assert b.motivo == ""  # sem origem na planilha
    assert b.status == "aprovado"  # save() auto-aprova


def test_apply_availability_resolves_usuario_by_cpf(tmp_path):
    """Nome divergente na linha; a PESSOA casa por CPF (não pelo nome)."""
    actor = _actor()
    pessoa = UsuarioFactory(cpf=_CPF)
    path = _write_export(tmp_path, {"availability_block": f"{AVAIL_HEADER}\n{_row(usuario='Outro Nome')}\n"})
    ExportContractImporter(path=path, apply=True, allow=("availability_block",), actor=actor).run()
    assert AvailabilityBlock.objects.get().usuario_id == pessoa.id


def test_apply_availability_rejects_unresolved_cpf(tmp_path):
    """CPF sem Usuario correspondente → não cria (usuario é PROTECT NOT NULL)."""
    actor = _actor()
    UsuarioFactory(cpf="33366699957")  # outra pessoa
    path = _write_export(tmp_path, {"availability_block": f"{AVAIL_HEADER}\n{_row(cpf=_CPF)}\n"})
    r = ExportContractImporter(path=path, apply=True, allow=("availability_block",), actor=actor).run()
    assert r["applied"]["availability_block"] == 0
    assert AvailabilityBlock.objects.count() == 0


def test_apply_availability_rejects_invalid_tipo(tmp_path):
    """tipo fora de {T, P} (CheckConstraint no BD) → reject, sem estourar IntegrityError."""
    actor = _actor()
    UsuarioFactory(cpf=_CPF)
    path = _write_export(tmp_path, {"availability_block": f"{AVAIL_HEADER}\n{_row(tipo='')}\n"})
    r = ExportContractImporter(path=path, apply=True, allow=("availability_block",), actor=actor).run()
    assert r["applied"]["availability_block"] == 0
    assert AvailabilityBlock.objects.count() == 0


def test_apply_availability_tipo_parcial(tmp_path):
    actor = _actor()
    UsuarioFactory(cpf=_CPF)
    path = _write_export(tmp_path, {"availability_block": f"{AVAIL_HEADER}\n{_row(tipo='P')}\n"})
    ExportContractImporter(path=path, apply=True, allow=("availability_block",), actor=actor).run()
    assert AvailabilityBlock.objects.get().tipo == "P"


def test_apply_availability_idempotent(tmp_path):
    actor = _actor()
    UsuarioFactory(cpf=_CPF)
    path = _write_export(tmp_path, {"availability_block": f"{AVAIL_HEADER}\n{_row()}\n"})
    ExportContractImporter(path=path, apply=True, allow=("availability_block",), actor=actor).run()
    r2 = ExportContractImporter(path=path, apply=True, allow=("availability_block",), actor=actor).run()
    assert r2["applied"]["availability_block"] == 0  # (usuario, inicio, fim, tipo) já existe
    assert AvailabilityBlock.objects.count() == 1


def test_apply_availability_requires_actor(tmp_path):
    UsuarioFactory(cpf=_CPF)
    path = _write_export(tmp_path, {"availability_block": f"{AVAIL_HEADER}\n{_row()}\n"})
    with pytest.raises(ValueError):
        ExportContractImporter(path=path, apply=True, allow=("availability_block",), actor=None).run()


def test_apply_availability_blocked_without_allowlist(tmp_path):
    actor = _actor()
    UsuarioFactory(cpf=_CPF)
    path = _write_export(tmp_path, {"availability_block": f"{AVAIL_HEADER}\n{_row()}\n"})
    r = ExportContractImporter(path=path, apply=True, allow=(), actor=actor).run()
    assert r["apply_blocked"] is True
    assert AvailabilityBlock.objects.count() == 0


def test_classify_availability_create_and_reject(tmp_path):
    UsuarioFactory(cpf=_CPF)
    csv = (
        f"{AVAIL_HEADER}\n"
        f"{_row()}\n"  # resolve → create
        f"{_row(cpf='00000000000')}\n"  # CPF inválido/sem match → reject
    )
    r = ExportContractImporter(path=_write_export(tmp_path, {"availability_block": csv})).run()["por_entidade"][
        "availability_block"
    ]
    assert r["would_create"] == 1
    assert r["would_reject"] == 1
