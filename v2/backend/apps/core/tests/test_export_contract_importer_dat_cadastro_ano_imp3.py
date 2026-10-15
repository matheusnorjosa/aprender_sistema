"""
IMP-3 do importador export-contract: `dat_cadastro` com o ano da planilha e `produto` sem ruído.

Decisão do dono (14/10): o cadastro DAT sem ano passa ao ano da planilha QUANDO a planilha trouxer um
ano só para aquele cadastro; com dois anos, não mexe e reporta (`sem_ano_ambiguo`). A adoção preenche só
o campo `ano`: etapas e demais campos ficam como estão (never-overwrite). O ano vem da coluna `ano` do
CSV; sem ela (ou inválida), das datas de etapa como antes. Inválida e sem data → `ano_invalido` (rejeita).

Produto: o classify decide só pela existência do código (`_norm_codigo` dos dois lados), sem comparar
nome. O apply segue sem gravar produto.

Fixtures sintéticos, sem dado pessoal.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false

from __future__ import annotations

import json
from datetime import date
from typing import Any

from django.db import connection
from django.test.utils import CaptureQueriesContext

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


@pytest.mark.parametrize(
    "ano",
    ["", "abc", "0", "-1", "1", "26", "1.000", "20262", "40000"],
    ids=["vazio", "invalido", "zero", "negativo", "um", "dois_digitos", "mil", "digito_a_mais", "acima_smallint"],
)
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

    with CaptureQueriesContext(connection) as ctx:
        r = _apply(path, base["actor"])

    assert r["applied"]["dat_cadastro"] == 0
    assert r["applied"]["dat_cadastro__ano_preenchido"] == 1
    assert DATCadastro.objects.count() == 1
    cad.refresh_from_db()
    assert cad.ano == 2026
    # a adoção grava SÓ o ano: uma edição concorrente das etapas não é apagada por um save() completo
    updates = [q["sql"] for q in ctx.captured_queries if q["sql"].startswith('UPDATE "core_dat_cadastro"')]
    assert len(updates) == 1
    set_clause = updates[0].split(" SET ", 1)[1].split(" WHERE ", 1)[0]
    assert sorted(c.split(" = ")[0] for c in set_clause.split(", ")) == ['"ano"', '"updated_at"']
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


@pytest.mark.parametrize(
    "ano",
    ["26", "40000", "abc", "1999", "2101", "inf", "1e999"],
    ids=["dois_digitos", "acima_smallint", "texto", "abaixo_do_piso", "acima_do_teto", "infinito", "notacao_enorme"],
)
def test_ano_fora_da_faixa_sem_data_rejeita_e_nao_mexe(tmp_path, base, ano):
    # Ano digitado errado não é ano ausente: sem data de etapa, a linha é rejeitada (`ano_invalido`).
    # Antes: '26' adotava ano=26 sem volta; '40000' passava no dry-run e quebrava o apply (smallint).
    _sem_ano(base)
    path = _write_export(tmp_path, _cad_csv(f"Cidade Cad,CE,PG Cad,FORMAR,pendente,,{ano}"))

    seco = _seco(path)
    assert (seco["would_skip_same"], seco["would_update"], seco["would_create"], seco["would_reject"]) == (0, 0, 0, 1)
    assert seco["reject_reasons"]["ano_invalido"] == 1

    r = _apply(path, base["actor"])

    assert r["applied"]["dat_cadastro"] == 0
    assert "dat_cadastro__ano_preenchido" not in r["applied"]
    assert list(DATCadastro.objects.values_list("ano", flat=True)) == [None]


@pytest.mark.parametrize("ano", [2000, 2100], ids=["piso", "teto"])
def test_bordas_da_faixa_adotam(tmp_path, base, ano):
    _sem_ano(base)
    path = _write_export(tmp_path, _cad_csv(f"Cidade Cad,CE,PG Cad,FORMAR,pendente,,{ano}"))

    _apply(path, base["actor"])

    assert list(DATCadastro.objects.values_list("ano", flat=True)) == [ano]


def test_ano_fora_da_faixa_sem_data_nao_cria_cadastro_sem_ano(tmp_path, base):
    path = _write_export(tmp_path, _cad_csv("Cidade Cad,CE,PG Cad,FORMAR,pendente,,26"))

    assert _seco(path)["reject_reasons"]["ano_invalido"] == 1
    r = _apply(path, base["actor"])

    assert r["applied"]["dat_cadastro"] == 0
    assert not DATCadastro.objects.exists()


@pytest.mark.parametrize("ordem", [("2026", "26"), ("26", "2026")], ids=["valido_antes", "invalido_antes"])
def test_ano_invalido_ao_lado_de_ano_valido_nao_adota_nem_duplica(tmp_path, base, ordem):
    # A linha de ano ilegível pode ser outro ano: o cadastro sem ano fica ambíguo (decide uma pessoa).
    # Antes: ela contava como "linha sem ano" e a de 2026 criava um cadastro novo ao lado do sem ano.
    cad = _sem_ano(base)
    path = _write_export(tmp_path, _cad_csv(*(f"Cidade Cad,CE,PG Cad,FORMAR,pendente,,{ano}" for ano in ordem)))

    seco = _seco(path)
    assert (seco["would_update"], seco["would_create"], seco["would_skip_same"], seco["would_reject"]) == (0, 0, 0, 2)
    assert (seco["reject_reasons"]["ano_invalido"], seco["reject_reasons"]["sem_ano_ambiguo"]) == (1, 1)

    r = _apply(path, base["actor"])

    assert r["applied"]["dat_cadastro"] == 0
    assert "dat_cadastro__ano_preenchido" not in r["applied"]
    assert DATCadastro.objects.count() == 1
    cad.refresh_from_db()
    assert cad.ano is None


def test_adocao_preenche_so_o_sem_ano_da_tripla_certa(tmp_path, base):
    # O get da adoção filtra pelos três campos da tripla: outro município, outra plataforma e outro projeto
    # geral com cadastro sem ano não podem ser pegos (nem estourar MultipleObjectsReturned).
    alvo = _sem_ano(base, "FORMAR")
    _sem_ano(base, "AVALIAR")
    outro_mun = MunicipioFactory(nome="Cidade Vizinha", uf="CE", ativo=True)
    outro_pg = ProjetoGeral.objects.create(nome="PG Outro", usa_avaliar=True)
    for mun, pg in ((outro_mun, base["pg"]), (base["mun"], outro_pg)):
        DATCadastro.objects.create(
            municipio=mun, projeto_geral=pg, plataforma="FORMAR", ano=None, created_by=base["actor"]
        )
    path = _write_export(tmp_path, _cad_csv("Cidade Cad,CE,PG Cad,FORMAR,pendente,,2026"))

    assert _seco(path)["would_update"] == 1
    r = _apply(path, base["actor"])

    assert r["applied"]["dat_cadastro__ano_preenchido"] == 1
    assert DATCadastro.objects.count() == 4
    assert list(DATCadastro.objects.exclude(ano=None).values_list("pk", "ano")) == [(alvo.pk, 2026)]


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


def test_classify_produto_normaliza_o_codigo_do_lado_do_arquivo(tmp_path):
    # Zero à esquerda na planilha casa com o catálogo sem zero; código só de zeros casa consigo mesmo.
    proj = ProjetoFactory(nome="Proj Prod Imp3 Arq", fluxo="NAO_SUPER")
    Produto.objects.create(codigo="402002", nome="Sem Zero", projeto=proj)
    Produto.objects.create(codigo="000", nome="Zeros", projeto=proj)
    csv = "codigo,nome\n0402002,Com Zero\n000,Zeros\n00,Zeros Curto\n"

    r = ExportContractImporter(path=_write_export(tmp_path, {"produto": csv})).run()["por_entidade"]["produto"]

    assert (r["would_skip_same"], r["would_create"], r["would_reject"]) == (3, 0, 0)
