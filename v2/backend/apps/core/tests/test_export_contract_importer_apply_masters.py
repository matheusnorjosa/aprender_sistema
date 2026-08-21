"""
Tests do caminho de ESCRITA (--apply create-only) dos masters do go-live no
export-contract importer: tipo_evento, projeto, usuario (+ atribuicao de Group).

Contexto: bootstrappar um PROD VAZIO ("coordenador cria solicitacao nova"). Como a
tabela nasce vazia, create-only nao tem o que sobrescrever (a regra sagrada de "nao
importar" e sobre o DEV, que tem data-fixes manuais). Estes testes provam:
- create real quando a entidade esta no allowlist;
- idempotencia (2a run cria 0);
- create-only NAO faz update de registro existente;
- allowlist bloqueia escrita sem allow;
- would_reject (NK invalida) nao cria nem quebra a transacao;
- usuario: username=cpf, senha inutilizavel, e atribuicao de Django Group por papel.

NAO importa dados reais.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false

from __future__ import annotations

import json
from typing import Any

from django.contrib.auth.models import Group

import pytest

from apps.core.models import Projeto, ProjetoGeral, TipoEvento, Usuario
from apps.core.services.export_contract_importer import ExportContractImporter
from apps.core.tests.factories import ProjetoFactory, TipoEventoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db


def _seed_funcao_groups() -> None:
    """Pre-condicao real do apply de usuario: os grupos FUNCAO existem (seed_rbac em prod)."""
    for g in ("Coordenador", "Formador", "Gerente", "Apoio de Coordenação"):
        Group.objects.get_or_create(name=g)


def _write_export(tmp_path, files: dict[str, str]) -> str:
    """Cria um diretorio de export minimo com manifest + CSVs."""
    d = tmp_path / "export"
    d.mkdir()
    manifest: dict[str, Any] = {"generated_at": "2026-06-02", "snapshot_date": "2026-05-19", "entities": {}}
    for name, content in files.items():
        (d / f"{name}.csv").write_text(content, encoding="utf-8")
        manifest["entities"][name] = {"file_csv": f"{name}.csv", "rows": max(content.strip().count("\n"), 0)}
    (d / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return str(d)


# ══════════════════════════════ tipo_evento (PR-A) ══════════════════════════════
def test_apply_tipo_evento_creates(tmp_path):
    csv = "nome,descricao,cor\nFormacao AP,desc ap,#111111\nReuniao AP,,\n"
    path = _write_export(tmp_path, {"tipo_evento": csv})
    report = ExportContractImporter(path=path, apply=True, allow=("tipo_evento",)).run()
    assert report["applied"]["tipo_evento"] == 2
    t = TipoEvento.objects.get(nome="Formacao AP")
    assert t.descricao == "desc ap"
    assert t.cor == "#111111"


def test_apply_tipo_evento_idempotent(tmp_path):
    csv = "nome,descricao,cor\nFormacao IDEM,,\n"
    path = _write_export(tmp_path, {"tipo_evento": csv})
    ExportContractImporter(path=path, apply=True, allow=("tipo_evento",)).run()
    r2 = ExportContractImporter(path=path, apply=True, allow=("tipo_evento",)).run()
    assert r2["applied"]["tipo_evento"] == 0
    assert TipoEvento.objects.filter(nome="Formacao IDEM").count() == 1


def test_apply_tipo_evento_create_only_no_update(tmp_path):
    TipoEventoFactory(nome="Existe TE AP", cor="#aaaaaa")
    csv = "nome,descricao,cor\nExiste TE AP,mudou,#ffffff\n"
    path = _write_export(tmp_path, {"tipo_evento": csv})
    r = ExportContractImporter(path=path, apply=True, allow=("tipo_evento",)).run()
    assert r["applied"]["tipo_evento"] == 0
    assert TipoEvento.objects.get(nome="Existe TE AP").cor == "#aaaaaa"  # nao alterado


def test_apply_tipo_evento_allowlist_blocks(tmp_path):
    csv = "nome,descricao,cor\nBloqueado TE,,\n"
    path = _write_export(tmp_path, {"tipo_evento": csv})
    before = TipoEvento.objects.count()
    r = ExportContractImporter(path=path, apply=True, allow=()).run()
    assert r["apply_blocked"] is True
    assert TipoEvento.objects.count() == before


def test_apply_tipo_evento_rejects_empty_nome(tmp_path):
    csv = "nome,descricao,cor\n,sem nome,\nValido TE,,\n"
    path = _write_export(tmp_path, {"tipo_evento": csv})
    r = ExportContractImporter(path=path, apply=True, allow=("tipo_evento",)).run()
    assert r["applied"]["tipo_evento"] == 1
    assert not TipoEvento.objects.filter(descricao="sem nome").exists()


# ══════════════════════════════ projeto (Onda A) ══════════════════════════════
def test_apply_projeto_creates_with_projeto_geral(tmp_path):
    # Núcleo da Onda A: cria a variante COM projeto_geral populado (não órfã).
    pg = ProjetoGeral.objects.create(nome="ACERTA BRASIL MATEMATICA")
    csv = "projeto,projeto_geral,fluxo\nACerta Brasil Matemática 3,ACERTA BRASIL MATEMATICA,SUPER\n"
    path = _write_export(tmp_path, {"projeto": csv})
    r = ExportContractImporter(path=path, apply=True, allow=("projeto",)).run()
    assert r["applied"]["projeto"] == 1
    p = Projeto.objects.get(nome="ACerta Brasil Matemática 3")
    assert p.projeto_geral_id == pg.id  # PG populado — fecha órfã tipo CATOLÉ
    assert p.fluxo == "SUPER"


def test_apply_projeto_idempotent(tmp_path):
    ProjetoGeral.objects.create(nome="PG IDEM")
    csv = "projeto,projeto_geral,fluxo\nProjeto Idem 1,PG IDEM,NAO_SUPER\n"
    path = _write_export(tmp_path, {"projeto": csv})
    ExportContractImporter(path=path, apply=True, allow=("projeto",)).run()
    r2 = ExportContractImporter(path=path, apply=True, allow=("projeto",)).run()
    assert r2["applied"]["projeto"] == 0
    assert Projeto.objects.filter(nome="Projeto Idem 1").count() == 1


def test_apply_projeto_create_only_skips_existing_by_canon_key(tmp_path):
    # Já existe sob outra grafia (& vs E) -> create-only não duplica nem atualiza.
    ProjetoFactory(nome="Vida & Matemática 6", fluxo="NAO_SUPER")
    ProjetoGeral.objects.create(nome="VIDA E MATEMATICA")
    csv = "projeto,projeto_geral,fluxo\nVIDA E MATEMATICA 6,VIDA E MATEMATICA,SUPER\n"
    path = _write_export(tmp_path, {"projeto": csv})
    r = ExportContractImporter(path=path, apply=True, allow=("projeto",)).run()
    assert r["applied"]["projeto"] == 0
    assert Projeto.objects.filter(nome__iexact="Vida & Matemática 6").count() == 1
    assert Projeto.objects.get(nome="Vida & Matemática 6").fluxo == "NAO_SUPER"  # não alterado


def test_apply_projeto_rejects_pg_desconhecido(tmp_path):
    # PG não resolvível -> NÃO cria (nunca projeto_geral=NULL órfão).
    csv = "projeto,projeto_geral,fluxo\nProjeto Sem PG 2,PG QUE NAO EXISTE,NAO_SUPER\n"
    path = _write_export(tmp_path, {"projeto": csv})
    r = ExportContractImporter(path=path, apply=True, allow=("projeto",)).run()
    assert r["applied"]["projeto"] == 0
    assert not Projeto.objects.filter(nome="Projeto Sem PG 2").exists()


def test_apply_projeto_rejects_fluxo_ausente(tmp_path):
    # fluxo vazio -> NÃO cria (default NAO_SUPER faria SUPER auto-aprovar — PA-01).
    ProjetoGeral.objects.create(nome="PG FLUXO VAZIO")
    csv = "projeto,projeto_geral,fluxo\nProjeto Sem Fluxo 2,PG FLUXO VAZIO,\n"
    path = _write_export(tmp_path, {"projeto": csv})
    r = ExportContractImporter(path=path, apply=True, allow=("projeto",)).run()
    assert r["applied"]["projeto"] == 0
    assert not Projeto.objects.filter(nome="Projeto Sem Fluxo 2").exists()


def test_apply_projeto_allowlist_blocks(tmp_path):
    ProjetoGeral.objects.create(nome="PG BLOQ")
    csv = "projeto,projeto_geral,fluxo\nProjeto Bloq 1,PG BLOQ,NAO_SUPER\n"
    path = _write_export(tmp_path, {"projeto": csv})
    before = Projeto.objects.count()
    r = ExportContractImporter(path=path, apply=True, allow=()).run()
    assert r["apply_blocked"] is True
    assert Projeto.objects.count() == before


def test_apply_projeto_dedup_intra_csv_same_canon_key(tmp_path):
    # Duas grafias da MESMA variante canônica na mesma run -> cria 1 (não quebra unique nome).
    ProjetoGeral.objects.create(nome="PG DEDUP")
    csv = (
        "projeto,projeto_geral,fluxo\n"
        "Vida & Matemática 8,PG DEDUP,NAO_SUPER\n"
        "VIDA E MATEMATICA 8,PG DEDUP,NAO_SUPER\n"
    )
    path = _write_export(tmp_path, {"projeto": csv})
    r = ExportContractImporter(path=path, apply=True, allow=("projeto",)).run()
    assert r["applied"]["projeto"] == 1
    assert Projeto.objects.filter(projeto_geral__nome="PG DEDUP").count() == 1


# ══════════════════════════ usuario (PR-C, + atribuicao de Group) ══════════════════════════
def test_apply_usuario_creates_username_cpf_unusable_password(tmp_path):
    csv = "nome_completo,cpf,email,cargo\nMaria Silva Souza,11144477735,maria@ex.com,Coordenadores\n"
    path = _write_export(tmp_path, {"usuario": csv})
    _seed_funcao_groups()
    r = ExportContractImporter(path=path, apply=True, allow=("usuario",)).run()
    assert r["applied"]["usuario"] == 1
    u = Usuario.objects.get(cpf="11144477735")
    assert u.username == "11144477735"  # username derivado do CPF (estavel, unique)
    assert u.has_usable_password() is False  # senha inutilizavel (login via OAuth Google)
    assert u.first_name == "Maria"
    assert u.last_name == "Silva Souza"
    assert u.is_active is True


def test_apply_usuario_assigns_group_from_cargo(tmp_path):
    csv = (
        "nome_completo,cpf,email,cargo\n" "Joao Coord,11144477735,,Coordenadores\n" "Ana Form,22255588846,,Formadores\n"
    )
    path = _write_export(tmp_path, {"usuario": csv})
    _seed_funcao_groups()
    ExportContractImporter(path=path, apply=True, allow=("usuario",)).run()
    assert Usuario.objects.get(cpf="11144477735").groups.filter(name="Coordenador").exists()
    assert Usuario.objects.get(cpf="22255588846").groups.filter(name="Formador").exists()


def test_apply_usuario_equipe_gerencia_papel_takes_precedence(tmp_path):
    # cargo diz Formadores, mas equipe_gerencia diz COORDENADOR (fonte primaria) -> Coordenador
    files = {
        "usuario": "nome_completo,cpf,email,cargo\nBia,11144477735,,Formadores\n",
        "equipe_gerencia": "gerencia,usuario_cpf,usuario_email,papel\nG,11144477735,,COORDENADOR\n",
    }
    path = _write_export(tmp_path, files)
    _seed_funcao_groups()
    ExportContractImporter(path=path, apply=True, allow=("usuario",)).run()
    u = Usuario.objects.get(cpf="11144477735")
    assert u.groups.filter(name="Coordenador").exists()
    assert not u.groups.filter(name="Formador").exists()


def test_apply_usuario_no_papel_creates_without_group(tmp_path):
    # sem cargo e sem equipe_gerencia -> cria SEM grupo (NUNCA chuta Coordenador)
    csv = "nome_completo,cpf,email,cargo\nSem Papel,11144477735,,\n"
    path = _write_export(tmp_path, {"usuario": csv})
    _seed_funcao_groups()
    ExportContractImporter(path=path, apply=True, allow=("usuario",)).run()
    assert Usuario.objects.get(cpf="11144477735").groups.count() == 0


def test_apply_usuario_group_missing_creates_without_group(tmp_path):
    # Simula prod ANTES do seed_rbac: o grupo alvo nao existe. (Nos testes, uma fixture
    # autouse semeia os grupos RBAC, entao deletamos explicitamente para reproduzir o caso.)
    Group.objects.filter(name__iexact="Coordenador").delete()
    csv = "nome_completo,cpf,email,cargo\nSemGrupo,11144477735,,Coordenadores\n"
    path = _write_export(tmp_path, {"usuario": csv})
    r = ExportContractImporter(path=path, apply=True, allow=("usuario",)).run()
    assert r["applied"]["usuario"] == 1  # usuario e criado mesmo sem o grupo (nao quebra)
    assert Usuario.objects.get(cpf="11144477735").groups.count() == 0


def test_apply_usuario_idempotent(tmp_path):
    csv = "nome_completo,cpf,email,cargo\nRepetido,11144477735,,Coordenadores\n"
    path = _write_export(tmp_path, {"usuario": csv})
    _seed_funcao_groups()
    ExportContractImporter(path=path, apply=True, allow=("usuario",)).run()
    r2 = ExportContractImporter(path=path, apply=True, allow=("usuario",)).run()
    assert r2["applied"]["usuario"] == 0
    assert Usuario.objects.filter(cpf="11144477735").count() == 1


def test_apply_usuario_create_only_skips_existing(tmp_path):
    UsuarioFactory(username="u_exist_ap", password="x", cpf="11144477735", email="exist@ex.com", first_name="Antigo")
    csv = "nome_completo,cpf,email,cargo\nNome Novo,11144477735,exist@ex.com,Coordenadores\n"
    path = _write_export(tmp_path, {"usuario": csv})
    _seed_funcao_groups()
    r = ExportContractImporter(path=path, apply=True, allow=("usuario",)).run()
    assert r["applied"]["usuario"] == 0
    assert Usuario.objects.get(cpf="11144477735").first_name == "Antigo"  # nao sobrescreve


def test_apply_usuario_rejects_invalid_cpf(tmp_path):
    # cpf invalido (nao 11 dig) e sem email -> nao cria; linha valida cria
    csv = "nome_completo,cpf,email,cargo\nInvalidoXYZ,123,,\nValido,11144477735,,\n"
    path = _write_export(tmp_path, {"usuario": csv})
    _seed_funcao_groups()
    r = ExportContractImporter(path=path, apply=True, allow=("usuario",)).run()
    assert r["applied"]["usuario"] == 1
    assert Usuario.objects.filter(username="11144477735").exists()
    assert not Usuario.objects.filter(first_name="InvalidoXYZ").exists()


def test_apply_usuario_allowlist_blocks(tmp_path):
    csv = "nome_completo,cpf,email,cargo\nBloq,11144477735,,Coordenadores\n"
    path = _write_export(tmp_path, {"usuario": csv})
    before = Usuario.objects.count()
    r = ExportContractImporter(path=path, apply=True, allow=()).run()
    assert r["apply_blocked"] is True
    assert Usuario.objects.count() == before


def test_apply_usuario_no_pii_in_report(tmp_path):
    csv = "nome_completo,cpf,email,cargo\nFulano Secreto,12398712399,fulano.secreto@ex.com,Coordenadores\n"
    path = _write_export(tmp_path, {"usuario": csv})
    _seed_funcao_groups()
    report = ExportContractImporter(path=path, apply=True, allow=("usuario",)).run()
    blob = json.dumps(report)
    assert "12398712399" not in blob
    assert "fulano.secreto@ex.com" not in blob
    assert "Fulano Secreto" not in blob
