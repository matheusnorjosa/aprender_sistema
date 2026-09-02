"""
Tests do APPLY (create-only) das filhas de PlanoFormacoes no export-contract:
`formacao`, `acompanhamento`, `prova`.

Contrato (travado com o pipeline sheets.banco): cada filha herda o plano pai — resolvido por
(municipio, projeto[, ano]); o CSV da filha NÃO traz `ano` (deriva-se da data quando há múltiplos
planos do par). NK: Formacao (plano, numero_formacao); Acompanhamento (plano, tipo);
Prova (plano, numero_prova). Sem plano pai / FK não-resolvida / numero fora de faixa / tipo fora do
domínio → would_reject. Sem `created_by` no model → apply NÃO exige actor.

Segurança: apply exige allowlist; create-only; idempotente. Fixtures sintéticos.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from apps.core.models import Acompanhamento, Formacao, PlanoFormacoes, Prova
from apps.core.services.export_contract_importer import ExportContractImporter
from apps.core.tests.factories import MunicipioFactory, ProjetoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

FORMACAO_HEADER = (
    "municipio,municipio_norm,uf,projeto,projeto_norm,numero_formacao,data_formacao,carga_horaria,modalidade"
)
ACOMP_HEADER = "municipio,municipio_norm,uf,projeto,projeto_norm,tipo,data_acompanhamento"
PROVA_HEADER = "municipio,municipio_norm,uf,projeto,projeto_norm,numero_prova,data_prova,marcado,marca_raw"


def _write_export(tmp_path, files: dict[str, str]) -> str:
    d = tmp_path / "export"
    d.mkdir()
    manifest: dict[str, Any] = {"generated_at": "2026-08-24", "snapshot_date": "2026-08-24", "entities": {}}
    for name, content in files.items():
        (d / f"{name}.csv").write_text(content, encoding="utf-8")
        manifest["entities"][name] = {"file_csv": f"{name}.csv", "rows": max(content.strip().count("\n"), 0)}
    (d / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return str(d)


def _plano(ano: int = 2026):
    """Cria (municipio, projeto, plano) e devolve o plano pai."""
    actor = UsuarioFactory(cpf="11144477735")
    mun = MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    proj = ProjetoFactory(nome="Proj X", fluxo="NAO_SUPER")
    return PlanoFormacoes.objects.create(municipio=mun, projeto=proj, ano=ano, created_by=actor)


# ─────────────────────────── formacao ───────────────────────────


def test_apply_formacao_creates_child_of_plano(tmp_path):
    plano = _plano()
    row = "Cidade X,CIDADE X,CE,Proj X,Proj X,1,2026-07-24,4,presencial"
    path = _write_export(tmp_path, {"formacao": f"{FORMACAO_HEADER}\n{row}\n"})
    r = ExportContractImporter(path=path, apply=True, allow=("formacao",)).run()
    assert r["applied"]["formacao"] == 1
    f = Formacao.objects.get()
    assert f.plano_id == plano.id
    assert f.numero_formacao == 1
    assert f.data_formacao == date(2026, 7, 24)
    assert f.carga_horaria == Decimal("4")
    assert f.modalidade == "presencial"


def test_apply_formacao_idempotent(tmp_path):
    _plano()
    row = "Cidade X,CIDADE X,CE,Proj X,Proj X,1,2026-07-24,4,online"
    path = _write_export(tmp_path, {"formacao": f"{FORMACAO_HEADER}\n{row}\n"})
    ExportContractImporter(path=path, apply=True, allow=("formacao",)).run()
    r2 = ExportContractImporter(path=path, apply=True, allow=("formacao",)).run()
    assert r2["applied"]["formacao"] == 0  # (plano, numero) já existe
    assert Formacao.objects.count() == 1


def test_apply_formacao_rejects_without_parent_plano(tmp_path):
    """Sem plano pai (municipio/projeto sem PlanoFormacoes) → não cria (create-only da filha)."""
    MunicipioFactory(nome="Cidade Y", uf="CE", ativo=True)
    ProjetoFactory(nome="Proj Y", fluxo="NAO_SUPER")
    row = "Cidade Y,CIDADE Y,CE,Proj Y,Proj Y,1,2026-07-24,4,presencial"
    path = _write_export(tmp_path, {"formacao": f"{FORMACAO_HEADER}\n{row}\n"})
    r = ExportContractImporter(path=path, apply=True, allow=("formacao",)).run()
    assert r["applied"]["formacao"] == 0
    assert Formacao.objects.count() == 0


def test_apply_formacao_rejects_numero_out_of_range(tmp_path):
    """numero_formacao fora de 1..15 (CheckConstraint) → skip, sem estourar IntegrityError na transação."""
    _plano()
    row = "Cidade X,CIDADE X,CE,Proj X,Proj X,99,2026-07-24,4,presencial"
    path = _write_export(tmp_path, {"formacao": f"{FORMACAO_HEADER}\n{row}\n"})
    r = ExportContractImporter(path=path, apply=True, allow=("formacao",)).run()
    assert r["applied"]["formacao"] == 0
    assert Formacao.objects.count() == 0


def test_apply_formacao_data_vazia_ok(tmp_path):
    """data_formacao vazia é válida (nullable) — o plano ainda resolve pelo par único."""
    plano = _plano()
    row = "Cidade X,CIDADE X,CE,Proj X,Proj X,2,,8,presencial"
    path = _write_export(tmp_path, {"formacao": f"{FORMACAO_HEADER}\n{row}\n"})
    r = ExportContractImporter(path=path, apply=True, allow=("formacao",)).run()
    assert r["applied"]["formacao"] == 1
    f = Formacao.objects.get()
    assert f.plano_id == plano.id
    assert f.data_formacao is None


def test_apply_formacao_blocked_without_allowlist(tmp_path):
    _plano()
    row = "Cidade X,CIDADE X,CE,Proj X,Proj X,1,2026-07-24,4,presencial"
    path = _write_export(tmp_path, {"formacao": f"{FORMACAO_HEADER}\n{row}\n"})
    r = ExportContractImporter(path=path, apply=True, allow=()).run()
    assert r["apply_blocked"] is True
    assert Formacao.objects.count() == 0


def test_classify_formacao_create_vs_skip(tmp_path):
    plano = _plano()
    Formacao.objects.create(plano=plano, numero_formacao=1)
    csv = (
        f"{FORMACAO_HEADER}\n"
        "Cidade X,CIDADE X,CE,Proj X,Proj X,1,2026-07-24,4,presencial\n"  # existe → skip
        "Cidade X,CIDADE X,CE,Proj X,Proj X,2,2026-08-04,4,online\n"  # novo → create
    )
    r = ExportContractImporter(path=_write_export(tmp_path, {"formacao": csv})).run()["por_entidade"]["formacao"]
    assert r["would_skip_same"] == 1
    assert r["would_create"] == 1
    assert r["would_reject"] == 0


# ─────────────────────────── acompanhamento ───────────────────────────


def test_apply_acompanhamento_creates_child_of_plano(tmp_path):
    plano = _plano()
    row = "Cidade X,CIDADE X,CE,Proj X,Proj X,primeiro,2026-05-27"
    path = _write_export(tmp_path, {"acompanhamento": f"{ACOMP_HEADER}\n{row}\n"})
    r = ExportContractImporter(path=path, apply=True, allow=("acompanhamento",)).run()
    assert r["applied"]["acompanhamento"] == 1
    a = Acompanhamento.objects.get()
    assert a.plano_id == plano.id
    assert a.tipo == "primeiro"
    assert a.data_acompanhamento == date(2026, 5, 27)
    assert a.realizado is False  # sem sinal de realizado no contrato → default


def test_apply_acompanhamento_idempotent(tmp_path):
    _plano()
    row = "Cidade X,CIDADE X,CE,Proj X,Proj X,segundo,2026-05-27"
    path = _write_export(tmp_path, {"acompanhamento": f"{ACOMP_HEADER}\n{row}\n"})
    ExportContractImporter(path=path, apply=True, allow=("acompanhamento",)).run()
    r2 = ExportContractImporter(path=path, apply=True, allow=("acompanhamento",)).run()
    assert r2["applied"]["acompanhamento"] == 0  # (plano, tipo) já existe
    assert Acompanhamento.objects.count() == 1


def test_apply_acompanhamento_rejects_invalid_tipo(tmp_path):
    """tipo fora de {primeiro, segundo} (choices, sem CheckConstraint no BD) → não cria dado inválido."""
    _plano()
    row = "Cidade X,CIDADE X,CE,Proj X,Proj X,terceiro,2026-05-27"
    path = _write_export(tmp_path, {"acompanhamento": f"{ACOMP_HEADER}\n{row}\n"})
    r = ExportContractImporter(path=path, apply=True, allow=("acompanhamento",)).run()
    assert r["applied"]["acompanhamento"] == 0
    assert Acompanhamento.objects.count() == 0


def test_apply_acompanhamento_rejects_without_parent_plano(tmp_path):
    MunicipioFactory(nome="Cidade Y", uf="CE", ativo=True)
    ProjetoFactory(nome="Proj Y", fluxo="NAO_SUPER")
    row = "Cidade Y,CIDADE Y,CE,Proj Y,Proj Y,primeiro,2026-05-27"
    path = _write_export(tmp_path, {"acompanhamento": f"{ACOMP_HEADER}\n{row}\n"})
    r = ExportContractImporter(path=path, apply=True, allow=("acompanhamento",)).run()
    assert r["applied"]["acompanhamento"] == 0
    assert Acompanhamento.objects.count() == 0


def test_classify_acompanhamento_create_and_reject(tmp_path):
    _plano()
    csv = (
        f"{ACOMP_HEADER}\n"
        "Cidade X,CIDADE X,CE,Proj X,Proj X,primeiro,2026-05-27\n"  # create
        "Cidade X,CIDADE X,CE,Proj X,Proj X,terceiro,2026-05-27\n"  # tipo inválido → reject
    )
    r = ExportContractImporter(path=_write_export(tmp_path, {"acompanhamento": csv})).run()["por_entidade"][
        "acompanhamento"
    ]
    assert r["would_create"] == 1
    assert r["would_reject"] == 1


# ─────────────────────────── prova ───────────────────────────


def test_apply_prova_creates_child_of_plano(tmp_path):
    plano = _plano()
    row = "Cidade X,CIDADE X,CE,Proj X,Proj X,1,,true,x"  # data_prova vazia (comum), marcado→realizada
    path = _write_export(tmp_path, {"prova": f"{PROVA_HEADER}\n{row}\n"})
    r = ExportContractImporter(path=path, apply=True, allow=("prova",)).run()
    assert r["applied"]["prova"] == 1
    p = Prova.objects.get()
    assert p.plano_id == plano.id
    assert p.numero_prova == 1
    assert p.data_prova is None
    assert p.realizada is True  # marcado=true → realizada


def test_apply_prova_idempotent(tmp_path):
    _plano()
    row = "Cidade X,CIDADE X,CE,Proj X,Proj X,2,2026-06-01,true,x"
    path = _write_export(tmp_path, {"prova": f"{PROVA_HEADER}\n{row}\n"})
    ExportContractImporter(path=path, apply=True, allow=("prova",)).run()
    r2 = ExportContractImporter(path=path, apply=True, allow=("prova",)).run()
    assert r2["applied"]["prova"] == 0  # (plano, numero_prova) já existe
    assert Prova.objects.count() == 1


def test_apply_prova_rejects_numero_out_of_range(tmp_path):
    """numero_prova fora de 1..3 (CheckConstraint) → skip, sem estourar IntegrityError."""
    _plano()
    row = "Cidade X,CIDADE X,CE,Proj X,Proj X,7,,true,x"
    path = _write_export(tmp_path, {"prova": f"{PROVA_HEADER}\n{row}\n"})
    r = ExportContractImporter(path=path, apply=True, allow=("prova",)).run()
    assert r["applied"]["prova"] == 0
    assert Prova.objects.count() == 0


def test_apply_prova_not_marcado_realizada_false(tmp_path):
    _plano()
    row = "Cidade X,CIDADE X,CE,Proj X,Proj X,3,,false,"
    path = _write_export(tmp_path, {"prova": f"{PROVA_HEADER}\n{row}\n"})
    ExportContractImporter(path=path, apply=True, allow=("prova",)).run()
    assert Prova.objects.get().realizada is False
