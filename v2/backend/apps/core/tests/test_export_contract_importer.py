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
from typing import Any

import pytest

from apps.core.models import (
    DATAcao,
    DATArea,
    DATCoordenador,
    Gerencia,
    Municipio,
    PlanoFormacoes,
    Produto,
    Projeto,
    ProjetoGeral,
    TipoEvento,
    Usuario,
)
from apps.core.services.export_contract_importer import (
    ExportContractImporter,
    diff_and_classify,
)

pytestmark = pytest.mark.django_db


def _write_export(tmp_path, files: dict[str, str]):
    """Cria um diretório de export mínimo com manifest + CSVs."""
    d = tmp_path / "export"
    d.mkdir()
    manifest: dict[str, Any] = {"generated_at": "2026-06-02", "snapshot_date": "2026-05-19", "entities": {}}
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
    # Nomes sintéticos (PG TESTE *) para não colidir com ProjetoGeral seedado por migração.
    ProjetoGeral.objects.create(nome="PG TESTE SKIP", usa_avaliar=True)
    ProjetoGeral.objects.create(nome="PG TESTE UPD", usa_avaliar=True)
    # SKIP igual -> skip; UPD usa_avaliar diverge -> would_update; PG TESTE NOVO -> create
    csv = "nome,usa_avaliar\nPG TESTE SKIP,True\nPG TESTE UPD,False\nPG TESTE NOVO,False\n"
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


# ───────── entidades-mestre adicionais (PR feat/export-contract-master-importers) ─────────
def test_classify_produto(tmp_path):
    proj = Projeto.objects.create(nome="Proj Prod Teste", fluxo="NAO_SUPER")
    Produto.objects.create(codigo="PT-1", nome="Produto Existente", projeto=proj)
    Produto.objects.create(codigo="PT-2", nome="Produto Upd", projeto=proj)
    # PT-1 nome igual -> skip; PT-2 nome diverge -> update; PT-NOVO -> create; vazio -> reject
    csv = "codigo,nome\nPT-1,Produto Existente\nPT-2,Nome Mudou\nPT-NOVO,Novo\n,Sem Codigo\n"
    r = ExportContractImporter(path=_write_export(tmp_path, {"produto": csv})).run()["por_entidade"]["produto"]
    assert r["would_skip_same"] == 1
    assert r["would_update"] == 1
    assert r["would_create"] == 1
    assert r["would_reject"] == 1


def test_classify_usuario(tmp_path):
    Usuario.objects.create_user(username="u_imp_exist", password="x", cpf="11122233344", email="u.exist@ex.com")
    # existente por cpf -> skip; novo -> create; sem cpf/email -> reject
    csv = "nome_completo,cpf,email\nFulano,11122233344,u.exist@ex.com\nBeltrano,55566677788,novo@ex.com\nSem Id,,\n"
    r = ExportContractImporter(path=_write_export(tmp_path, {"usuario": csv})).run()["por_entidade"]["usuario"]
    assert r["would_skip_same"] == 1
    assert r["would_create"] == 1
    assert r["would_reject"] == 1


def test_usuario_no_pii_in_report(tmp_path):
    csv = "nome_completo,cpf,email\nFulano Secreto,12398712399,fulano.secreto@ex.com\n"
    report = ExportContractImporter(path=_write_export(tmp_path, {"usuario": csv})).run()
    blob = json.dumps(report)
    assert "12398712399" not in blob  # CPF não vaza
    assert "fulano.secreto@ex.com" not in blob  # email não vaza
    assert "Fulano Secreto" not in blob  # nome não vaza


def test_classify_tipo_evento(tmp_path):
    TipoEvento.objects.create(nome="Formacao TE", cor="#111111")
    TipoEvento.objects.create(nome="Visita TE", cor="#222222")
    # Formacao igual -> skip; Visita cor diverge -> update; Novo -> create
    csv = "nome,cor\nFormacao TE,#111111\nVisita TE,#999999\nEvento Novo TE,#333333\n"
    r = ExportContractImporter(path=_write_export(tmp_path, {"tipo_evento": csv})).run()["por_entidade"]["tipo_evento"]
    assert r["would_skip_same"] == 1
    assert r["would_update"] == 1
    assert r["would_create"] == 1


def test_classify_gerencia_matches_by_setor(tmp_path):
    # Export `nome` é o setor → casa DB.nome_setor (não DB.nome canônico).
    Gerencia.objects.create(nome="GERENCIA TESTE", nome_setor="Setor Existente")
    csv = "nome,nome_setor\nSetor Existente,Setor Existente\nSetor Novo,Setor Novo\n-,-\n"
    r = ExportContractImporter(path=_write_export(tmp_path, {"gerencia": csv})).run()["por_entidade"]["gerencia"]
    assert r["would_skip_same"] == 1  # casou por nome_setor
    assert r["would_create"] == 1  # setor novo (create exige nome canônico — caveat)
    assert r["would_reject"] == 1  # linha "-"


def test_classify_dat_coordenador(tmp_path):
    creator = Usuario.objects.create_user(username="u_dc_creator", password="x", cpf="99900011122")
    area = DATArea.objects.create(nome="Area Coord Teste")
    DATCoordenador.objects.create(nome="Coord Existente", email="coord.exist@ex.com", area=area, created_by=creator)
    # existente por email -> skip; novo -> create; vazio -> reject
    csv = "usuario,area\ncoord.exist@ex.com,Area Coord Teste\nNovo Coord,Area Coord Teste\n,Area Coord Teste\n"
    r = ExportContractImporter(path=_write_export(tmp_path, {"dat_coordenador": csv})).run()["por_entidade"][
        "dat_coordenador"
    ]
    assert r["would_skip_same"] == 1
    assert r["would_create"] == 1
    assert r["would_reject"] == 1


def test_dat_coordenador_no_pii(tmp_path):
    csv = "usuario,area\ncoord.secreto@ex.com,Area X\n"
    report = ExportContractImporter(path=_write_export(tmp_path, {"dat_coordenador": csv})).run()
    assert "coord.secreto@ex.com" not in json.dumps(report)


# ───────── entidades operacionais — espinhaço municipio+projeto (Slice 1, classify dry-run) ─────────
def test_classify_dat_acao_skip_create_reject(tmp_path):
    # NK = (municipio_id, projeto_id). Existência decide skip vs create; FK não-resolvido → reject.
    creator = Usuario.objects.create_user(username="u_da_creator", password="x", cpf="33344455566")
    mun_a = Municipio.objects.create(nome="Cidade Acao Um", uf="CE", ativo=True)
    Municipio.objects.create(nome="Cidade Acao Dois", uf="CE", ativo=True)
    proj = Projeto.objects.create(nome="Proj Acao Teste", fluxo="NAO_SUPER")
    DATAcao.objects.create(municipio=mun_a, projeto=proj, created_by=creator)
    # linha 1: (Um, Proj) existe → skip; linha 2: (Dois, Proj) resolve mas sem DATAcao → create;
    # linha 3: municipio inexistente → reject (FK não-resolvido).
    csv = (
        "municipio,uf,projeto,coordenador\n"
        "Cidade Acao Um,CE,Proj Acao Teste,Coord Um\n"
        "Cidade Acao Dois,CE,Proj Acao Teste,Coord Dois\n"
        "Cidade Fantasma XYZ,CE,Proj Acao Teste,Coord Tres\n"
    )
    r = ExportContractImporter(path=_write_export(tmp_path, {"dat_acao": csv})).run()["por_entidade"]["dat_acao"]
    assert r["would_skip_same"] == 1
    assert r["would_create"] == 1
    assert r["would_reject"] == 1
    assert r["would_update"] == 0


def test_classify_plano_formacao_skip_create_reject(tmp_path):
    creator = Usuario.objects.create_user(username="u_pf_creator", password="x", cpf="77788899900")
    mun_a = Municipio.objects.create(nome="Cidade Plano Um", uf="CE", ativo=True)
    Municipio.objects.create(nome="Cidade Plano Dois", uf="CE", ativo=True)
    proj = Projeto.objects.create(nome="Proj Plano Teste", fluxo="NAO_SUPER")
    PlanoFormacoes.objects.create(municipio=mun_a, projeto=proj, created_by=creator)
    csv = (
        "municipio,uf,projeto,coordenador\n"
        "Cidade Plano Um,CE,Proj Plano Teste,Coord Um\n"
        "Cidade Plano Dois,CE,Proj Plano Teste,Coord Dois\n"
        "Cidade Fantasma ZZZ,CE,Proj Plano Teste,Coord Tres\n"
    )
    r = ExportContractImporter(path=_write_export(tmp_path, {"plano_formacao": csv})).run()["por_entidade"][
        "plano_formacao"
    ]
    assert r["would_skip_same"] == 1
    assert r["would_create"] == 1
    assert r["would_reject"] == 1
    assert r["would_update"] == 0


def test_dat_acao_no_coordenador_pii(tmp_path):
    # coordenador é pessoa (DATCoordenador) → nunca deve vazar no relatório.
    Municipio.objects.create(nome="Cidade PII", uf="CE", ativo=True)
    Projeto.objects.create(nome="Proj PII Teste", fluxo="NAO_SUPER")
    csv = "municipio,uf,projeto,coordenador\nCidade PII,CE,Proj PII Teste,CoordSecretoXYZ\n"
    report = ExportContractImporter(path=_write_export(tmp_path, {"dat_acao": csv})).run()
    assert "CoordSecretoXYZ" not in json.dumps(report)


def test_demo_dez_entidades_implementadas(tmp_path):
    files = {
        "dat_area": "nome,descricao\nA,d\n",
        "municipio": "nome,uf,ativo\nC,CE,True\n",
        "projeto_geral": "nome,usa_avaliar\nPG,True\n",
        "produto": "codigo,nome\nC1,N\n",
        "usuario": "nome_completo,cpf,email\nF,11111111111,f@ex.com\n",
        "tipo_evento": "nome,cor\nT,#000000\n",
        "gerencia": "nome,nome_setor\nSetor,Setor\n",
        "dat_coordenador": "usuario,area\ncoord@ex.com,Area\n",
        "dat_acao": "municipio,uf,projeto\nC,CE,P\n",
        "plano_formacao": "municipio,uf,projeto\nC,CE,P\n",
    }
    r = ExportContractImporter(path=_write_export(tmp_path, files)).run()["por_entidade"]
    for ent in files:
        assert "status" not in r[ent], f"{ent} deveria estar implementada"
        assert "export_rows" in r[ent]
