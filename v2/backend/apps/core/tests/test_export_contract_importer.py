"""
Tests do importer dedicado do export-contract (skeleton, dry-run/create-only).

Política de segurança:
- dry-run por padrão (apply=False não escreve);
- --apply sem allowlist NÃO escreve;
- modo create-only;
- never-overwrite de campos protegidos (Solicitacao.status, Formacao.data_formacao,
  Acompanhamento.data_acompanhamento/realizado) -> classificados como protected_diff.

Primeira fatia implementada: dat_area, municipio, projeto_geral (master, baixo risco).
NÃO importa dados reais.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false

from __future__ import annotations

import json

import pytest

from apps.core.models import DATArea, Municipio, Projeto, ProjetoGeral
from apps.core.services.export_contract_importer import (
    ExportContractImporter,
    diff_and_classify,
)

pytestmark = pytest.mark.django_db


def _write_export(tmp_path, files: dict[str, str]):
    """Cria um diretório de export mínimo com manifest + CSVs."""
    d = tmp_path / "export"
    d.mkdir()
    manifest = {"generated_at": "2026-06-02", "snapshot_date": "2026-05-19", "entities": {}}
    for name, content in files.items():
        (d / f"{name}.csv").write_text(content, encoding="utf-8")
        rows = max(content.strip().count("\n"), 0)
        manifest["entities"][name] = {"file_csv": f"{name}.csv", "rows": rows}
    (d / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return str(d)


# ───────── política de campos protegidos (unit puro) ─────────
def test_diff_create_when_no_existing():
    assert diff_and_classify(None, {"status": "aprovado"}, {"status"})[0] == "would_create"


def test_diff_skip_same():
    st, _ = diff_and_classify({"descricao": "x"}, {"descricao": "x"}, set())
    assert st == "would_skip_same"


def test_diff_protected_field_never_overwrite():
    st, fields = diff_and_classify({"status": "aprovado"}, {"status": "pendente"}, {"status"})
    assert st == "protected_diff"
    assert "status" in fields


def test_diff_update_non_protected():
    st, fields = diff_and_classify({"descricao": "a"}, {"descricao": "b"}, {"status"})
    assert st == "would_update"
    assert "descricao" in fields


# ───────── dry-run / apply safety ─────────
def test_dry_run_is_default_and_writes_nothing(tmp_path):
    path = _write_export(tmp_path, {"dat_area": "nome,descricao\nArea Nova,desc\n"})
    before = DATArea.objects.count()
    imp = ExportContractImporter(path=path)  # apply default False
    report = imp.run()
    assert imp.apply is False
    assert DATArea.objects.count() == before  # nada escrito
    assert report["por_entidade"]["dat_area"]["would_create"] == 1


def test_apply_without_allowlist_writes_nothing(tmp_path):
    path = _write_export(tmp_path, {"dat_area": "nome,descricao\nArea Nova,desc\n"})
    before = DATArea.objects.count()
    imp = ExportContractImporter(path=path, apply=True, allow=())
    report = imp.run()
    assert DATArea.objects.count() == before  # abort/no-write sem allowlist
    assert report.get("apply_blocked") is True


def test_reads_manifest(tmp_path):
    path = _write_export(tmp_path, {"dat_area": "nome,descricao\nA,d\n"})
    report = ExportContractImporter(path=path).run()
    assert "manifest" in report
    assert report["manifest"]["snapshot_date"] == "2026-05-19"


# ───────── classificação por entidade (master, baixo risco) ─────────
def test_classify_dat_area(tmp_path):
    # DATArea não tem campo comparável no export → existência decide create vs skip (sem update).
    DATArea.objects.create(nome="Area Existente")
    csv = "nome,descricao\nArea Existente,old\nArea Existente,nova desc\nArea Nova,d\n,sem nome\n"
    path = _write_export(tmp_path, {"dat_area": csv})
    r = ExportContractImporter(path=path).run()["por_entidade"]["dat_area"]
    assert r["would_skip_same"] == 2  # ambas as linhas da area existente
    assert r["would_create"] == 1  # Area Nova
    assert r["would_reject"] == 1  # linha sem nome
    assert r["would_update"] == 0


def test_classify_municipio(tmp_path):
    Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
    csv = "nome,uf,ativo\nFortaleza,CE,True\nNova Cidade,PE,True\n"
    path = _write_export(tmp_path, {"municipio": csv})
    r = ExportContractImporter(path=path).run()["por_entidade"]["municipio"]
    assert r["would_skip_same"] == 1  # Fortaleza/CE existe, ativo igual
    assert r["would_create"] == 1  # Nova Cidade/PE novo


def test_classify_projeto_geral(tmp_path):
    ProjetoGeral.objects.create(nome="VIDA E LINGUAGEM", usa_avaliar=True)
    ProjetoGeral.objects.create(nome="ACERTA MAT", usa_avaliar=True)
    # VIDA E LINGUAGEM igual -> skip; ACERTA MAT usa_avaliar diverge -> would_update; NOVO PG -> create
    csv = "nome,usa_avaliar\nVIDA E LINGUAGEM,True\nACERTA MAT,False\nNOVO PG,False\n"
    path = _write_export(tmp_path, {"projeto_geral": csv})
    r = ExportContractImporter(path=path).run()["por_entidade"]["projeto_geral"]
    assert r["would_skip_same"] == 1
    assert r["would_update"] == 1
    assert r["would_create"] == 1


# ───────── uso do resolver de Projeto ─────────
def test_uses_projeto_resolver():
    Projeto.objects.create(nome="Vida & Matemática 6", fluxo="NAO_SUPER")
    imp = ExportContractImporter(path=".")
    pid = imp.resolve_projeto("VIDA E MATEMATICA 6")
    assert pid is not None
    assert Projeto.objects.get(id=pid).nome == "Vida & Matemática 6"


# ───────── entidades não implementadas ─────────
def test_not_implemented_entities_marked(tmp_path):
    path = _write_export(tmp_path, {"solicitacao": "municipio,projeto\nX,Y\n"})
    r = ExportContractImporter(path=path).run()["por_entidade"]
    assert r["solicitacao"]["status"] == "not_implemented"


# ───────── sem PII no relatório ─────────
def test_report_has_no_pii(tmp_path):
    path = _write_export(tmp_path, {"dat_area": "nome,descricao\nA,d\n"})
    report = ExportContractImporter(path=path).run()
    blob = json.dumps(report).lower()
    for token in ("cpf", "telefone", "@"):
        assert token not in blob
