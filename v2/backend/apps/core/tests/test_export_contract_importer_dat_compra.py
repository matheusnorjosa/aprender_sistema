"""
Tests do classify + apply da fatia `dat_compra` do export-contract, e do guard de
ambiguidade de `projeto_geral` (CONTRATO-v4 §2).

Segurança: apply exige allowlist + actor; create-only; idempotente; fixtures sintéticos.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from apps.core.models import DATCompra, DATRegistro, ProjetoGeral
from apps.core.services.export_contract_importer import ExportContractImporter
from apps.core.tests.factories import MunicipioFactory, ProjetoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

COMPRA_HEADER = (
    "municipio,uf,projeto,produto_codigo,descricao_produto,tipo,conta_para_codigos,quantidade,ano_uso,data_compra"
)
# Contrato v12 renomeou `ano_uso` -> `ano_uso_colecao` (ano de USO da coleção != ano_compra).
COMPRA_HEADER_V12 = COMPRA_HEADER.replace("ano_uso", "ano_uso_colecao")
PG_HEADER = (
    "nome,nome_norm,usa_avaliar,tipo_calculo_codigos,divisor_aluno,multiplicador_professor,precisa_config,visto_na_dat"
)


def _write_export(tmp_path, files: dict[str, str]) -> str:
    d = tmp_path / "export"
    d.mkdir()
    manifest: dict[str, Any] = {"generated_at": "2026-08-20", "entities": {}}
    for name, content in files.items():
        (d / f"{name}.csv").write_text(content, encoding="utf-8")
        manifest["entities"][name] = {"file_csv": f"{name}.csv", "rows": max(content.strip().count("\n"), 0)}
    (d / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return str(d)


def _actor():
    return UsuarioFactory(username="u_compra", password="x", cpf="11144477735")


def _compra_row(municipio="Cidade X", projeto="Proj X", tipo="Professor", conta="true", qtde=41, ano=2026):
    return f"{municipio},CE,{projeto},99,{tipo} kit,{tipo},{conta},{qtde},{ano},2026-06-08"


def test_classify_dat_compra_skip_create_reject(tmp_path):
    actor = _actor()
    mun = MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    proj = ProjetoFactory(nome="Proj X", fluxo="NAO_SUPER")
    # pré-existente (skip): mesma NK do 1º row
    DATCompra.objects.create(
        municipio=mun,
        projeto=proj,
        descricao_produto="Professor kit",
        tipo="Professor",
        quantidade=41,
        ano_uso=2026,
        data_compra=date(2026, 6, 8),  # parte da NK: precisa casar a data do row p/ skip
        created_by=actor,
    )
    rows = "\n".join(
        [
            _compra_row(qtde=41),  # skip (existe)
            _compra_row(qtde=99),  # create (nova NK)
            _compra_row(projeto="Projeto Inexistente"),  # reject (FK não resolve)
        ]
    )
    r = ExportContractImporter(path=_write_export(tmp_path, {"dat_compra": f"{COMPRA_HEADER}\n{rows}\n"})).run()
    t = r["por_entidade"]["dat_compra"]
    assert t["would_skip_same"] == 1
    assert t["would_create"] == 1
    assert t["would_reject"] == 1


def test_apply_dat_compra_creates_and_recomputes(tmp_path):
    actor = _actor()
    mun = MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    pg = ProjetoGeral.objects.create(
        nome="PG X", usa_avaliar=False, tipo_calculo_codigos="por_professor", multiplicador_professor=Decimal("1.1")
    )
    proj = ProjetoFactory(nome="Proj X", fluxo="NAO_SUPER", projeto_geral=pg)
    reg = DATRegistro.objects.create(municipio=mun, projeto_geral=pg, projeto=proj, professor_qtde=52, created_by=actor)
    assert reg.nr_codigos == 0
    rows = "\n".join([_compra_row(qtde=41), _compra_row(qtde=11)])  # 41+11 professor
    r = ExportContractImporter(
        path=_write_export(tmp_path, {"dat_compra": f"{COMPRA_HEADER}\n{rows}\n"}),
        apply=True,
        allow=("dat_compra",),
        actor=actor,
    ).run()
    assert r["applied"]["dat_compra"] == 2
    reg.refresh_from_db()
    assert reg.nr_codigos == 59  # ceil(41×1.1)+ceil(11×1.1) = 46+13, NÃO ceil(52×1.1)=58


def test_apply_dat_compra_reads_ano_uso_colecao_v12(tmp_path):
    """Regressão de drift: o contrato v12 renomeou a coluna `ano_uso` -> `ano_uso_colecao`.
    Se o importer lesse só o nome antigo, `ano_uso` viria None e TODA compra seria descartada
    como 'ano_uso ausente' (applied=0, silencioso). Aqui o header só tem o nome NOVO."""
    actor = _actor()
    MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    ProjetoFactory(nome="Proj X", fluxo="NAO_SUPER")
    row = "Cidade X,CE,Proj X,99,Professor kit,Professor,true,41,2026,2026-06-08"
    r = ExportContractImporter(
        path=_write_export(tmp_path, {"dat_compra": f"{COMPRA_HEADER_V12}\n{row}\n"}),
        apply=True,
        allow=("dat_compra",),
        actor=actor,
    ).run()
    assert r["applied"]["dat_compra"] == 1
    assert DATCompra.objects.get().ano_uso == 2026


def test_apply_dat_compra_stores_nao_classificado_as_null(tmp_path):
    """fix2: compra com ano_uso_colecao VAZIO (NÃO_CLASSIFICADO) é GRAVADA com ano_uso=NULL
    (pendente de ano), não descartada. Decisão A do dono: 'guarda como pendente até alguém
    preencher o ano'. Antes, a guarda `nk[5] is None` a descartava silenciosamente."""
    actor = _actor()
    MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    ProjetoFactory(nome="Proj X", fluxo="NAO_SUPER")
    row = "Cidade X,CE,Proj X,99,Professor kit,Professor,true,41,,2026-06-08"  # ano_uso_colecao vazio
    r = ExportContractImporter(
        path=_write_export(tmp_path, {"dat_compra": f"{COMPRA_HEADER_V12}\n{row}\n"}),
        apply=True,
        allow=("dat_compra",),
        actor=actor,
    ).run()
    assert r["applied"]["dat_compra"] == 1
    assert DATCompra.objects.get().ano_uso is None


def test_apply_dat_compra_distinct_by_data_compra(tmp_path):
    """NK inclui data_compra: 2 compras iguais em tudo menos a DATA são distintas (não dedup).
    Regressão real (PACATUBA/Vida & Ciências 9): mesmo kit de professor comprado em 2 datas —
    sem a data na NK, a 2ª colidia e era descartada, causando under-count de nr_codigos."""
    actor = _actor()
    MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    ProjetoFactory(nome="Proj X", fluxo="NAO_SUPER")
    rows = "\n".join(
        [
            "Cidade X,CE,Proj X,99,Professor kit,Professor,true,5,2026,2026-05-15",
            "Cidade X,CE,Proj X,99,Professor kit,Professor,true,5,2026,2026-05-25",
        ]
    )
    r = ExportContractImporter(
        path=_write_export(tmp_path, {"dat_compra": f"{COMPRA_HEADER}\n{rows}\n"}),
        apply=True,
        allow=("dat_compra",),
        actor=actor,
    ).run()
    assert r["applied"]["dat_compra"] == 2  # sem data_compra na NK seria 1 (2ª colidiria)
    assert DATCompra.objects.filter(descricao_produto="Professor kit", quantidade=5).count() == 2


def test_apply_dat_compra_idempotent(tmp_path):
    actor = _actor()
    MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    ProjetoFactory(nome="Proj X", fluxo="NAO_SUPER")
    path = _write_export(tmp_path, {"dat_compra": f"{COMPRA_HEADER}\n{_compra_row()}\n"})
    ExportContractImporter(path=path, apply=True, allow=("dat_compra",), actor=actor).run()
    r2 = ExportContractImporter(path=path, apply=True, allow=("dat_compra",), actor=actor).run()
    assert r2["applied"]["dat_compra"] == 0
    assert DATCompra.objects.count() == 1


def test_apply_dat_compra_requires_actor(tmp_path):
    MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    ProjetoFactory(nome="Proj X", fluxo="NAO_SUPER")
    path = _write_export(tmp_path, {"dat_compra": f"{COMPRA_HEADER}\n{_compra_row()}\n"})
    with pytest.raises(ValueError):
        ExportContractImporter(path=path, apply=True, allow=("dat_compra",), actor=None).run()


def test_apply_dat_compra_blocked_without_allowlist(tmp_path):
    actor = _actor()
    MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    ProjetoFactory(nome="Proj X", fluxo="NAO_SUPER")
    path = _write_export(tmp_path, {"dat_compra": f"{COMPRA_HEADER}\n{_compra_row()}\n"})
    r = ExportContractImporter(path=path, apply=True, allow=(), actor=actor).run()
    assert r["apply_blocked"] is True
    assert DATCompra.objects.count() == 0


def test_projeto_geral_alias_ambiguo_rejeitado(tmp_path):
    """CONTRATO-v4 §2: nome-alias de regra divergente nunca é criado (would_reject)."""
    actor = _actor()
    rows = "ESCREVER COMUNICAR E SER,ESCREVER COMUNICAR E SER,false,professor_x_multiplicador,,1.1,false,false"
    path = _write_export(tmp_path, {"projeto_geral": f"{PG_HEADER}\n{rows}\n"})
    r = ExportContractImporter(path=path, apply=True, allow=("projeto_geral",), actor=actor).run()
    assert r["por_entidade"]["projeto_geral"]["would_reject"] == 1
    assert not ProjetoGeral.objects.filter(nome__icontains="ESCREVER COMUNICAR").exists()
