"""
Tests do APPLY (create-only) das fatias dat_cadastro + dat_registro do
export-contract (Onda 2). Consome o formato v3 (status já em enum, datas ISO,
NK única, turma_formar_id populado).

Segurança: apply exige allowlist + actor (--as-user); create-only; idempotente.
NÃO importa dados reais — fixtures sintéticos.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false

from __future__ import annotations

import json
from datetime import date
from typing import Any

import pytest

from apps.core.models import DATCadastro, DATRegistro, ProjetoGeral
from apps.core.services.export_contract_importer import ExportContractImporter
from apps.core.tests.factories import MunicipioFactory, ProjetoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

CAD_HEADER = (
    "municipio,municipio_norm,uf,projeto_geral,projeto_geral_norm,plataforma,"
    "etapa1_status,etapa1_data,etapa2_status,etapa2_data,etapa3_status,etapa3_data,"
    "etapa4_status,etapa4_data,variantes_qtd"
)
REG_HEADER = (
    "municipio,municipio_norm,uf,projeto_geral,projeto_geral_norm,projeto,projeto_norm,"
    "aluno_qtde,professor_qtde,nr_codigos_planilha,reuniao_dat,turma_formar_id,turma_formar_status,"
    "chaves_inscricao_status,chaves_inscricao_data,instrucoes_status,instrucoes_data,"
    "envio_codigos_status,envio_codigos_data,obs_formar,"
    "alunos_recebidos_status,alunos_recebidos_datas,alunos_validados_status,alunos_validados_datas,"
    "alunos_importados_status,alunos_importados_datas,obs_avaliar,usa_avaliar_planilha,ano_inferido"
)


def _write_export(tmp_path, files: dict[str, str]) -> str:
    d = tmp_path / "export"
    d.mkdir()
    manifest: dict[str, Any] = {"generated_at": "2026-08-19", "snapshot_date": "2026-05-19", "entities": {}}
    for name, content in files.items():
        (d / f"{name}.csv").write_text(content, encoding="utf-8")
        manifest["entities"][name] = {"file_csv": f"{name}.csv", "rows": max(content.strip().count("\n"), 0)}
    (d / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return str(d)


def _actor():
    return UsuarioFactory(username="u_apply_dat", password="x", cpf="11144477735")


# ───────── dat_cadastro ─────────
def test_apply_dat_cadastro_formar_creates_and_maps(tmp_path):
    actor = _actor()
    MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    ProjetoGeral.objects.create(nome="PG X", usa_avaliar=True)
    csv = (
        f"{CAD_HEADER}\n"
        "Cidade X,CIDADE X,CE,PG X,PG X,FORMAR,concluido,2026-03-01,pendente,,na,,concluido,2026-04-05,3\n"
    )
    path = _write_export(tmp_path, {"dat_cadastro": csv})
    r = ExportContractImporter(path=path, apply=True, allow=("dat_cadastro",), actor=actor).run()
    assert r["applied"]["dat_cadastro"] == 1
    dc = DATCadastro.objects.get()
    assert dc.plataforma == "FORMAR"
    assert dc.status_criacao_curso == "concluido"
    assert dc.data_criacao_curso == date(2026, 3, 1)
    assert dc.status_chaves == "pendente"
    assert dc.status_instrucoes == "na"
    assert dc.status_envio == "concluido"
    assert dc.data_envio == date(2026, 4, 5)
    assert dc.created_by_id == actor.id

    # idempotência: 2ª run (mesmo path) não recria
    r2 = ExportContractImporter(path=path, apply=True, allow=("dat_cadastro",), actor=actor).run()
    assert r2["applied"]["dat_cadastro"] == 0
    assert DATCadastro.objects.count() == 1


def test_apply_dat_cadastro_avaliar_maps_three_etapas(tmp_path):
    actor = _actor()
    MunicipioFactory(nome="Cidade Y", uf="CE", ativo=True)
    ProjetoGeral.objects.create(nome="PG Y", usa_avaliar=True)
    csv = (
        f"{CAD_HEADER}\n" "Cidade Y,CIDADE Y,CE,PG Y,PG Y,AVALIAR,concluido,2026-05-01,pendente,,nao_aplicavel,,na,,2\n"
    )
    r = ExportContractImporter(
        path=_write_export(tmp_path, {"dat_cadastro": csv}), apply=True, allow=("dat_cadastro",), actor=actor
    ).run()
    assert r["applied"]["dat_cadastro"] == 1
    dc = DATCadastro.objects.get()
    assert dc.plataforma == "AVALIAR"
    assert dc.status_recebidos == "concluido"
    assert dc.data_recebidos == date(2026, 5, 1)
    assert dc.status_validados == "pendente"
    assert dc.status_importados == "nao_aplicavel"


def test_apply_blocked_without_allowlist(tmp_path):
    actor = _actor()
    MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    ProjetoGeral.objects.create(nome="PG X", usa_avaliar=False)
    csv = f"{CAD_HEADER}\nCidade X,CIDADE X,CE,PG X,PG X,FORMAR,concluido,2026-03-01,pendente,,pendente,,pendente,,1\n"
    r = ExportContractImporter(
        path=_write_export(tmp_path, {"dat_cadastro": csv}), apply=True, allow=(), actor=actor
    ).run()
    assert r["apply_blocked"] is True
    assert DATCadastro.objects.count() == 0


def test_apply_dat_cadastro_requires_actor(tmp_path):
    MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    ProjetoGeral.objects.create(nome="PG X", usa_avaliar=False)
    csv = f"{CAD_HEADER}\nCidade X,CIDADE X,CE,PG X,PG X,FORMAR,pendente,,pendente,,pendente,,pendente,,1\n"
    with pytest.raises(ValueError):
        ExportContractImporter(
            path=_write_export(tmp_path, {"dat_cadastro": csv}), apply=True, allow=("dat_cadastro",), actor=None
        ).run()


# ───────── dat_registro ─────────
def test_apply_dat_registro_creates_derives_and_stores_planilha(tmp_path):
    actor = _actor()
    MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    # por_professor (default) × 1.1 → ceil(10*1.1)=11; usa_avaliar espelhado do PG.
    ProjetoGeral.objects.create(nome="PG X", usa_avaliar=True)
    ProjetoFactory(nome="Proj X", fluxo="NAO_SUPER")
    row = (
        "Cidade X,CIDADE X,CE,PG X,PG X,Proj X,Proj X,20,10,22,2026-02-01,2598,criada,"
        "concluido,2026-03-01,pendente,,pendente,,obs f,"
        'concluido,["2026-03-27"],nao_aplicavel,[],nao_aplicavel,[],,true,false'
    )
    csv = f"{REG_HEADER}\n{row}\n"
    r = ExportContractImporter(
        path=_write_export(tmp_path, {"dat_registro": csv}), apply=True, allow=("dat_registro",), actor=actor
    ).run()
    assert r["applied"]["dat_registro"] == 1
    dr = DATRegistro.objects.get()
    assert dr.aluno_qtde == 20
    assert dr.professor_qtde == 10
    assert dr.nr_codigos_planilha == 22
    assert dr.reuniao_dat == date(2026, 2, 1)
    assert dr.turma_formar_id == 2598
    assert dr.turma_formar_status == "criada"
    assert dr.chaves_inscricao_status == "concluido"
    assert dr.chaves_inscricao_data == date(2026, 3, 1)
    assert dr.alunos_recebidos_status == "concluido"
    assert dr.alunos_recebidos_datas == ["2026-03-27"]
    assert dr.created_by_id == actor.id
    # save() derivou:
    assert dr.usa_avaliar is True
    assert dr.nr_codigos == 0  # sem compras importadas → 0 (cálculo per-compra em test_dat_codigos)


def test_apply_dat_registro_creates_professor_only(tmp_path):
    actor = _actor()
    MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    ProjetoGeral.objects.create(nome="PG X", usa_avaliar=False)
    ProjetoFactory(nome="Proj X", fluxo="NAO_SUPER")
    # aluno_qtde vazio é LEGÍTIMO (registro professor-only) → cria (aluno_qtde nullable)
    row = "Cidade X,CIDADE X,CE,PG X,PG X,Proj X,Proj X,,,,,,pendente,pendente,,pendente,,pendente,,,nao_aplicavel,[],nao_aplicavel,[],nao_aplicavel,[],,,false"
    csv = f"{REG_HEADER}\n{row}\n"
    r = ExportContractImporter(
        path=_write_export(tmp_path, {"dat_registro": csv}), apply=True, allow=("dat_registro",), actor=actor
    ).run()
    assert r["applied"]["dat_registro"] == 1
    assert DATRegistro.objects.get().aluno_qtde is None


def test_apply_dat_registro_skips_unresolved_projeto_geral(tmp_path):
    actor = _actor()
    MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    ProjetoFactory(nome="Proj X", fluxo="NAO_SUPER")
    # PG inexistente → FK não-resolvida → não cria
    row = "Cidade X,CIDADE X,CE,PG Inexistente,PG Inexistente,Proj X,Proj X,20,10,22,,,pendente,pendente,,pendente,,pendente,,,nao_aplicavel,[],nao_aplicavel,[],nao_aplicavel,[],,,false"
    csv = f"{REG_HEADER}\n{row}\n"
    r = ExportContractImporter(
        path=_write_export(tmp_path, {"dat_registro": csv}), apply=True, allow=("dat_registro",), actor=actor
    ).run()
    assert r["applied"]["dat_registro"] == 0
    assert DATRegistro.objects.count() == 0
