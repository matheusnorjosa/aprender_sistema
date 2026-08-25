"""Opção A #1837 · Wave 2 — APPLY (create-only) do dat_coordenador (fecha silent-gap) +
resolução por CPF do plano.

Master real (v14): `usuario,usuario_norm,usuario_cpf,area,area_norm` (usuario=NOME, sem email;
usuario_cpf raw). Silent-gap: dat_coordenador estava em IMPLEMENTED mas sem apply → gravava 0.

- create-only, existence-based UNION (cpf OU email OU nome) — priority-first duplicaria pessoa;
- lê `usuario_cpf` (não `cpf`); cpf inválido → cria sem cpf; linha sem nome → rejeita;
- ordem de apply = ENTITY_ORDER (não a ordem de --allow-entity) → coordenador antes de plano.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false

from __future__ import annotations

import json
from typing import Any

import pytest

from apps.core.models import DATCoordenador, PlanoFormacoes
from apps.core.services.export_contract_importer import ExportContractImporter
from apps.core.tests.factories import MunicipioFactory, ProjetoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

COORD_HEADER = "usuario,usuario_norm,usuario_cpf,area,area_norm"
PLANO_HEADER = (
    "municipio,municipio_norm,uf,projeto,projeto_norm,ano,ano_origem,sem_plano,"
    "coordenador,coordenador_cpf,coordenador_email,ch_estudo,ch_total_planilha,ch_anual_planilha"
)
_CPF_A = "22255588846"


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
    return UsuarioFactory(username="u_apply_coord", password="x", cpf="11144477735")


def _coord_export(tmp_path, rows: str) -> str:
    return _write_export(tmp_path, {"dat_coordenador": f"{COORD_HEADER}\n{rows}\n"})


def test_apply_creates_coordenador_with_cpf(tmp_path):
    actor = _actor()
    path = _coord_export(tmp_path, f"Amanda Arruda,AMANDA ARRUDA,{_CPF_A},DAT,DAT")
    r = ExportContractImporter(path=path, apply=True, allow=("dat_coordenador",), actor=actor).run()
    assert r["applied"]["dat_coordenador"] == 1
    c = DATCoordenador.objects.get(nome="Amanda Arruda")
    assert c.cpf == _CPF_A
    assert c.area == "DAT"
    assert c.created_by_id == actor.id


def test_apply_union_nk_skips_existing_by_nome(tmp_path):
    """Row DB nasceu no CRUD (sem cpf); master traz cpf. Priority-first (cpf) duplicaria; UNION casa por nome."""
    actor = _actor()
    DATCoordenador.objects.create(nome="Amanda Arruda", area="DAT", created_by=actor)
    path = _coord_export(tmp_path, f"Amanda Arruda,AMANDA ARRUDA,{_CPF_A},DAT,DAT")
    r = ExportContractImporter(path=path, apply=True, allow=("dat_coordenador",), actor=actor).run()
    assert r["applied"]["dat_coordenador"] == 0
    assert DATCoordenador.objects.filter(nome="Amanda Arruda").count() == 1  # sem duplicata


def test_apply_union_nk_skips_existing_by_cpf(tmp_path):
    actor = _actor()
    DATCoordenador.objects.create(nome="Nome Antigo", area="DAT", cpf=_CPF_A, created_by=actor)
    path = _coord_export(tmp_path, f"Nome Novo,NOME NOVO,{_CPF_A},DAT,DAT")
    r = ExportContractImporter(path=path, apply=True, allow=("dat_coordenador",), actor=actor).run()
    assert r["applied"]["dat_coordenador"] == 0
    assert DATCoordenador.objects.filter(cpf=_CPF_A).count() == 1


def test_apply_invalid_cpf_creates_without_cpf(tmp_path):
    actor = _actor()
    path = _coord_export(tmp_path, "Beltrano Silva,BELTRANO SILVA,123,DAT,DAT")
    ExportContractImporter(path=path, apply=True, allow=("dat_coordenador",), actor=actor).run()
    c = DATCoordenador.objects.get(nome="Beltrano Silva")
    assert c.cpf is None  # cpf inválido → cria sem cpf (nome ainda vale)


def test_apply_rejects_nameless_row(tmp_path):
    actor = _actor()
    path = _coord_export(tmp_path, f",,{_CPF_A},DAT,DAT")
    r = ExportContractImporter(path=path, apply=True, allow=("dat_coordenador",), actor=actor).run()
    assert r["applied"]["dat_coordenador"] == 0
    assert DATCoordenador.objects.count() == 0


def test_apply_idempotent(tmp_path):
    actor = _actor()
    path = _coord_export(tmp_path, f"Amanda Arruda,AMANDA ARRUDA,{_CPF_A},DAT,DAT")
    ExportContractImporter(path=path, apply=True, allow=("dat_coordenador",), actor=actor).run()
    r2 = ExportContractImporter(path=path, apply=True, allow=("dat_coordenador",), actor=actor).run()
    assert r2["applied"]["dat_coordenador"] == 0
    assert DATCoordenador.objects.count() == 1


def test_apply_requires_actor(tmp_path):
    path = _coord_export(tmp_path, f"Amanda Arruda,AMANDA ARRUDA,{_CPF_A},DAT,DAT")
    with pytest.raises(ValueError):
        ExportContractImporter(path=path, apply=True, allow=("dat_coordenador",), actor=None).run()


def test_classify_dat_coordenador_mirrors_apply_by_cpf(tmp_path):
    """Dry-run: coord existente por CPF (nome diferente) → skip, não create (classify espelha o apply)."""
    actor = _actor()
    DATCoordenador.objects.create(nome="Nome Db", area="DAT", cpf=_CPF_A, created_by=actor)
    path = _coord_export(tmp_path, f"Nome Csv Diferente,NOME CSV DIFERENTE,{_CPF_A},DAT,DAT")
    r = ExportContractImporter(path=path).run()["por_entidade"]["dat_coordenador"]
    assert r["would_create"] == 0
    assert r["would_skip_same"] == 1


def test_classify_no_pii_in_report(tmp_path):
    path = _coord_export(tmp_path, f"CoordSecretoZZZ,COORDSECRETOZZZ,{_CPF_A},DAT,DAT")
    report = ExportContractImporter(path=path).run()
    blob = json.dumps(report)
    assert "CoordSecretoZZZ" not in blob
    assert _CPF_A not in blob


def test_allow_order_applies_by_entity_order_not_cli_order(tmp_path):
    """O apply itera por ENTITY_ORDER, não pela ordem de --allow-entity: dat_coordenador (idx menor) é
    aplicado mesmo listado DEPOIS de plano_formacao. (Nota #1849: o coordenador do PLANO resolve contra
    Usuario, não contra este DATCoordenador — que é governança; por isso o plano fica NULL aqui.)"""
    actor = _actor()
    MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    ProjetoFactory(nome="Proj X", fluxo="NAO_SUPER")
    coord_csv = f"{COORD_HEADER}\nCoord Y,COORD Y,{_CPF_A},DAT,DAT\n"
    plano_row = f"Cidade X,CIDADE X,CE,Proj X,Proj X,2026,workbook,false,Coord Y,{_CPF_A},,0,0,0"
    path = _write_export(tmp_path, {"dat_coordenador": coord_csv, "plano_formacao": f"{PLANO_HEADER}\n{plano_row}\n"})
    r = ExportContractImporter(path=path, apply=True, allow=("plano_formacao", "dat_coordenador"), actor=actor).run()
    # dat_coordenador foi aplicado apesar de listado DEPOIS de plano → ordenação por ENTITY_ORDER.
    assert r["applied"]["dat_coordenador"] == 1
    assert DATCoordenador.objects.filter(nome="Coord Y").exists()
    # o coordenador do plano NÃO vem deste DATCoordenador (resolve contra Usuario, ausente aqui) → NULL.
    assert PlanoFormacoes.objects.get().coordenador_id is None
