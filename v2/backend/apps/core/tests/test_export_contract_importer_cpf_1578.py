"""
Testes de contrato do CPF no importer export-contract — #1578.

Defeito: o importer só checava ``len(cpf) == 11``. Consequências:
1. dry-run classificava CPF estruturalmente inválido (DV errado) ou placeholder
   (00000000000) como ``would_create`` — o dry-run MENTIA sobre o que o apply faria.
2. apply escrevia usuário com CPF bogus, e três causas de skip distintas
   ("sem NK", "já existe", "CPF inválido") caíam no mesmo ``continue`` mudo.

Este módulo prova (RED→GREEN #1578):
- dry-run rejeita CPF inválido/placeholder (não conta como create);
- placeholder é tratado como AUSENTE (item 4), não como "inválido";
- as causas de reject aparecem distinguíveis em ``reject_reasons``;
- apply NÃO escreve CPF inválido/placeholder;
- nada de PII (CPF/email/nome) no relatório.

CPFs sintéticos (DV calculado) — não são PII de pessoas reais.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false

from __future__ import annotations

import json
from typing import Any

from django.contrib.auth.models import Group

import pytest

from apps.core.models import Usuario
from apps.core.services.export_contract_importer import ExportContractImporter
from apps.core.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db

VALID_CPF_A = "11144477735"  # DV mod-11 confere
VALID_CPF_B = "22255588846"  # DV mod-11 confere
INVALID_CHECKSUM_CPF = "12345678900"  # 11 díg, não-placeholder, DV errado
PLACEHOLDER_CPF = "00000000000"  # dígito repetido → tratado como ausente


def _write_export(tmp_path, files: dict[str, str]) -> str:
    d = tmp_path / "export"
    d.mkdir()
    manifest: dict[str, Any] = {"generated_at": "2026-06-02", "snapshot_date": "2026-05-19", "entities": {}}
    for name, content in files.items():
        (d / f"{name}.csv").write_text(content, encoding="utf-8")
        manifest["entities"][name] = {"file_csv": f"{name}.csv", "rows": max(content.strip().count("\n"), 0)}
    (d / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return str(d)


def _seed_funcao_groups() -> None:
    for g in ("Coordenador", "Formador", "Gerente", "Apoio de Coordenação"):
        Group.objects.get_or_create(name=g)


# ───────── dry-run: validação estrutural ─────────
def test_dryrun_rejects_checksum_invalid_cpf_not_create(tmp_path):
    csv = f"nome_completo,cpf,email\nFulano,{INVALID_CHECKSUM_CPF},\n"
    r = ExportContractImporter(path=_write_export(tmp_path, {"usuario": csv})).run()["por_entidade"]["usuario"]
    assert r["would_create"] == 0  # NÃO cria CPF com DV errado
    assert r["would_reject"] == 1
    assert r["reject_reasons"]["cpf_invalido"] == 1


def test_dryrun_placeholder_cpf_treated_as_absent(tmp_path):
    csv = f"nome_completo,cpf,email\nFulano,{PLACEHOLDER_CPF},\n"
    r = ExportContractImporter(path=_write_export(tmp_path, {"usuario": csv})).run()["por_entidade"]["usuario"]
    assert r["would_create"] == 0
    # Placeholder é AUSENTE (sem NK, pois sem email), NÃO "cpf_invalido".
    assert r["reject_reasons"]["sem_nk"] == 1
    assert r["reject_reasons"]["cpf_invalido"] == 0


def test_dryrun_separates_three_skip_causes(tmp_path):
    UsuarioFactory(username="u1578_exist", password="x", cpf=VALID_CPF_A, email="exist1578@ex.com")
    csv = (
        "nome_completo,cpf,email\n"
        f"Existe,{VALID_CPF_A},exist1578@ex.com\n"  # já existe → would_skip_same
        f"Novo,{VALID_CPF_B},novo1578@ex.com\n"  # válido novo → would_create
        "SemId,,\n"  # sem CPF e sem email → sem_nk
        f"Ruim,{INVALID_CHECKSUM_CPF},\n"  # CPF inválido (DV) → cpf_invalido
        "SoEmail,,soemail1578@ex.com\n"  # tem email, sem CPF válido → sem_cpf
    )
    r = ExportContractImporter(path=_write_export(tmp_path, {"usuario": csv})).run()["por_entidade"]["usuario"]
    assert r["would_skip_same"] == 1  # "já existe"
    assert r["would_create"] == 1
    assert r["reject_reasons"] == {"sem_nk": 1, "cpf_invalido": 1, "sem_cpf": 1}
    assert r["would_reject"] == 3


def test_dryrun_valid_new_cpf_is_create(tmp_path):
    csv = f"nome_completo,cpf,email\nNovo,{VALID_CPF_A},novo.valido@ex.com\n"
    r = ExportContractImporter(path=_write_export(tmp_path, {"usuario": csv})).run()["por_entidade"]["usuario"]
    assert r["would_create"] == 1
    assert r["would_reject"] == 0


def test_dryrun_reject_reasons_have_no_pii(tmp_path):
    csv = f"nome_completo,cpf,email\nSecreto,{INVALID_CHECKSUM_CPF},secreto1578@ex.com\n"
    report = ExportContractImporter(path=_write_export(tmp_path, {"usuario": csv})).run()
    blob = json.dumps(report)
    assert INVALID_CHECKSUM_CPF not in blob  # CPF não vaza
    assert "secreto1578@ex.com" not in blob  # email não vaza
    assert "Secreto" not in blob  # nome não vaza


# ───────── apply: nunca escreve CPF inválido/placeholder ─────────
def test_apply_skips_checksum_invalid_cpf(tmp_path):
    csv = f"nome_completo,cpf,email,cargo\nRuim,{INVALID_CHECKSUM_CPF},,\n"
    _seed_funcao_groups()
    r = ExportContractImporter(path=_write_export(tmp_path, {"usuario": csv}), apply=True, allow=("usuario",)).run()
    assert r["applied"]["usuario"] == 0
    assert not Usuario.objects.filter(cpf=INVALID_CHECKSUM_CPF).exists()


def test_apply_skips_placeholder_creates_only_valid(tmp_path):
    # Dois placeholders + um válido: só o válido é criado; nenhum usuário bogus.
    csv = (
        "nome_completo,cpf,email,cargo\n"
        f"Dummy1,{PLACEHOLDER_CPF},,\n"
        "Dummy2,11111111111,,\n"
        f"Bom,{VALID_CPF_A},,\n"
    )
    _seed_funcao_groups()
    r = ExportContractImporter(path=_write_export(tmp_path, {"usuario": csv}), apply=True, allow=("usuario",)).run()
    assert r["applied"]["usuario"] == 1  # só o válido
    assert not Usuario.objects.filter(cpf=PLACEHOLDER_CPF).exists()
    assert not Usuario.objects.filter(cpf="11111111111").exists()
    assert Usuario.objects.filter(cpf=VALID_CPF_A).exists()


def test_apply_valid_cpf_is_created(tmp_path):
    csv = f"nome_completo,cpf,email,cargo\nBom,{VALID_CPF_B},,\n"
    _seed_funcao_groups()
    r = ExportContractImporter(path=_write_export(tmp_path, {"usuario": csv}), apply=True, allow=("usuario",)).run()
    assert r["applied"]["usuario"] == 1
    assert Usuario.objects.get(cpf=VALID_CPF_B).username == VALID_CPF_B
