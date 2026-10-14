"""
IMP-3 do importador export-contract: `dat_cadastro` com o ano da planilha e `produto` sem ruído.

Decisão do dono (14/10): o cadastro DAT sem ano passa ao ano da planilha QUANDO a planilha trouxer um
ano só para aquele cadastro; com dois anos, não mexe e reporta (`sem_ano_ambiguo`). A adoção preenche só
o campo `ano`: etapas e demais campos ficam como estão (never-overwrite). O ano vem da coluna `ano` do
CSV; sem ela (ou inválida), das datas de etapa como antes.

Produto: o classify decide só pela existência do código (`_norm_codigo` dos dois lados), sem comparar
nome. O apply segue sem gravar produto.

Fixtures sintéticos, sem dado pessoal.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false

from __future__ import annotations

import json
from datetime import date
from typing import Any

import pytest

from apps.core.models import DATCadastro, Produto, ProjetoGeral
from apps.core.services.export_contract_importer import ExportContractImporter
from apps.core.tests.factories import MunicipioFactory, ProjetoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

CAD_HEADER = "municipio,uf,projeto_geral,plataforma,etapa1_status,etapa1_data,ano"


def _write_export(tmp_path, files: dict[str, str]) -> str:
    d = tmp_path / "export"
    d.mkdir()
    manifest: dict[str, Any] = {"generated_at": "2026-10-14", "entities": {}}
    for name, content in files.items():
        (d / f"{name}.csv").write_text(content, encoding="utf-8")
        manifest["entities"][name] = {"file_csv": f"{name}.csv", "rows": max(content.strip().count("\n"), 0)}
    (d / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return str(d)


@pytest.fixture
def base():
    actor = UsuarioFactory(username="u_cad_imp3", password="x", cpf="11144477735")
    mun = MunicipioFactory(nome="Cidade Cad", uf="CE", ativo=True)
    pg = ProjetoGeral.objects.create(nome="PG Cad", usa_avaliar=True)
    return {"actor": actor, "mun": mun, "pg": pg}


def _cad_csv(*linhas: str) -> dict[str, str]:
    return {"dat_cadastro": CAD_HEADER + "\n" + "\n".join(linhas) + "\n"}


def _seco(path: str) -> dict[str, Any]:
    return ExportContractImporter(path=path).run()["por_entidade"]["dat_cadastro"]


def _apply(path: str, actor) -> dict[str, Any]:
    return ExportContractImporter(path=path, apply=True, allow=("dat_cadastro",), actor=actor).run()


def _sem_ano(base, plataforma: str = "FORMAR") -> DATCadastro:
    """Cadastro antigo sem ano, com etapa já andada (que a adoção não pode mexer)."""
    return DATCadastro.objects.create(
        municipio=base["mun"],
        projeto_geral=base["pg"],
        plataforma=plataforma,
        ano=None,
        status_criacao_curso="concluido",
        data_criacao_curso=date(2025, 11, 5),
        observacoes="obs manual",
        created_by=base["actor"],
    )


# ───────── (a) o ano vem da coluna `ano` ─────────
def test_ano_da_coluna_vence_a_data_da_etapa(tmp_path, base):
    path = _write_export(tmp_path, _cad_csv("Cidade Cad,CE,PG Cad,FORMAR,concluido,2025-12-01,2026"))

    r = _apply(path, base["actor"])

    assert r["applied"]["dat_cadastro"] == 1
    assert DATCadastro.objects.get().ano == 2026


@pytest.mark.parametrize("ano", ["", "abc"], ids=["vazio", "invalido"])
def test_coluna_ano_vazia_ou_invalida_cai_na_data_da_etapa(tmp_path, base, ano):
    path = _write_export(tmp_path, _cad_csv(f"Cidade Cad,CE,PG Cad,FORMAR,concluido,2025-12-01,{ano}"))

    _apply(path, base["actor"])

    assert DATCadastro.objects.get().ano == 2025


# ───────── (b) adoção do cadastro sem ano ─────────
def test_sem_ano_no_banco_e_um_ano_no_arquivo_adota_so_o_ano(tmp_path, base):
    cad = _sem_ano(base)
    path = _write_export(tmp_path, _cad_csv("Cidade Cad,CE,PG Cad,FORMAR,pendente,,2026"))

    seco = _seco(path)
    assert (seco["would_update"], seco["would_create"], seco["would_reject"]) == (1, 0, 0)

    r = _apply(path, base["actor"])

    assert r["applied"]["dat_cadastro"] == 0
    assert r["applied"]["dat_cadastro__ano_preenchido"] == 1
    assert DATCadastro.objects.count() == 1
    cad.refresh_from_db()
    assert cad.ano == 2026
    # never-overwrite: a etapa e a observação do cadastro não vêm da planilha
    assert (cad.status_criacao_curso, cad.data_criacao_curso, cad.observacoes) == (
        "concluido",
        date(2025, 11, 5),
        "obs manual",
    )

    # idempotente: a segunda passada já acha o ano gravado
    assert _seco(path)["would_skip_same"] == 1
    r2 = _apply(path, base["actor"])
    assert r2["applied"]["dat_cadastro"] == 0
    assert "dat_cadastro__ano_preenchido" not in r2["applied"]


def test_linha_repetida_do_mesmo_ano_adota_uma_vez(tmp_path, base):
    _sem_ano(base)
    path = _write_export(
        tmp_path,
        _cad_csv("Cidade Cad,CE,PG Cad,FORMAR,pendente,,2026", "Cidade Cad,CE,PG Cad,FORMAR,pendente,,2026"),
    )

    seco = _seco(path)
    assert (seco["would_update"], seco["reject_reasons"]["repetida_no_arquivo"]) == (1, 1)
    r = _apply(path, base["actor"])
    assert r["applied"]["dat_cadastro__ano_preenchido"] == 1
    assert list(DATCadastro.objects.values_list("ano", flat=True)) == [2026]


def test_banco_com_sem_ano_e_outro_ano_nao_adota(tmp_path, base):
    _sem_ano(base)
    DATCadastro.objects.create(
        municipio=base["mun"], projeto_geral=base["pg"], plataforma="FORMAR", ano=2025, created_by=base["actor"]
    )
    path = _write_export(tmp_path, _cad_csv("Cidade Cad,CE,PG Cad,FORMAR,pendente,,2026"))

    seco = _seco(path)
    assert (seco["would_update"], seco["would_create"]) == (0, 1)

    r = _apply(path, base["actor"])

    assert r["applied"]["dat_cadastro"] == 1
    assert "dat_cadastro__ano_preenchido" not in r["applied"]
    assert DATCadastro.objects.count() == 3
    assert set(DATCadastro.objects.values_list("ano", flat=True)) == {None, 2025, 2026}


@pytest.mark.parametrize("ordem", [("2026", "2027"), ("2027", "2026")], ids=["2026_antes", "2027_antes"])
def test_dois_anos_no_arquivo_rejeita_sem_ano_ambiguo_e_nao_mexe(tmp_path, base, ordem):
    cad = _sem_ano(base)
    path = _write_export(tmp_path, _cad_csv(*(f"Cidade Cad,CE,PG Cad,FORMAR,pendente,,{ano}" for ano in ordem)))

    seco = _seco(path)
    assert (seco["would_update"], seco["would_create"], seco["would_reject"]) == (0, 0, 2)
    assert seco["reject_reasons"]["sem_ano_ambiguo"] == 2

    r = _apply(path, base["actor"])

    assert r["applied"]["dat_cadastro"] == 0
    assert "dat_cadastro__ano_preenchido" not in r["applied"]
    assert DATCadastro.objects.count() == 1
    cad.refresh_from_db()
    assert cad.ano is None


def test_arquivo_com_linha_sem_ano_nao_adota(tmp_path, base):
    # A linha sem ano do arquivo é o próprio cadastro sem ano do banco; a de 2026 é outro cadastro.
    _sem_ano(base)
    path = _write_export(
        tmp_path,
        _cad_csv("Cidade Cad,CE,PG Cad,FORMAR,pendente,,", "Cidade Cad,CE,PG Cad,FORMAR,pendente,,2026"),
    )

    seco = _seco(path)
    assert (seco["would_skip_same"], seco["would_update"], seco["would_create"]) == (1, 0, 1)
    r = _apply(path, base["actor"])
    assert "dat_cadastro__ano_preenchido" not in r["applied"]
    assert DATCadastro.objects.count() == 2
    assert set(DATCadastro.objects.values_list("ano", flat=True)) == {None, 2026}


def test_sem_ano_de_outra_plataforma_nao_e_adotado(tmp_path, base):
    _sem_ano(base, plataforma="FORMAR")
    path = _write_export(tmp_path, _cad_csv("Cidade Cad,CE,PG Cad,AVALIAR,pendente,,2026"))

    assert _seco(path)["would_create"] == 1
    _apply(path, base["actor"])
    assert set(DATCadastro.objects.values_list("plataforma", "ano")) == {("FORMAR", None), ("AVALIAR", 2026)}


# ───────── (c) produto decide só pela existência do código ─────────
def test_classify_produto_so_pela_existencia_do_codigo_normalizado(tmp_path):
    proj = ProjetoFactory(nome="Proj Prod Imp3", fluxo="NAO_SUPER")
    Produto.objects.create(codigo="0402002", nome="Nome do Catálogo", projeto=proj)
    Produto.objects.create(codigo="PT-9", nome="Outro", projeto=proj)
    csv = "codigo,nome\n402002,Nome Diferente na Planilha\npt-9,Outro\nPT-NOVO,Novo\n,Sem Codigo\n"

    r = ExportContractImporter(path=_write_export(tmp_path, {"produto": csv})).run()["por_entidade"]["produto"]

    assert r["would_update"] == 0
    assert r["would_skip_same"] == 2
    assert r["would_create"] == 1
    assert r["would_reject"] == 1
