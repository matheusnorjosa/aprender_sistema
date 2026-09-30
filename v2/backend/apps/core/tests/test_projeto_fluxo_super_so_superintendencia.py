"""
Regra do dono (30/09) — trava no cadastro de projeto: fluxo SUPER só em projeto da gerência
Superintendência (`Gerencia.nome == "SUPERINTENDENCIA"`, g1).

Vale para todo caminho que grava `fluxo` (ou move o projeto de gerência): API (`ProjetoSerializer`,
400 com a mensagem no `detail`, que a tela mostra), admin Django (`ProjetoAdminForm`), import do
export-contract (não cria SUPER: a planilha não traz gerência) e o seed do catálogo canônico (SUPER
nasce em g1). Um PATCH que não grava fluxo nem gerência não é barrado por dado antigo.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

import json

from rest_framework.test import APIClient

import pytest

from apps.core.models import Gerencia, Projeto, ProjetoGeral
from apps.core.tests.factories import ProjetoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

_MSG = "Fluxo SUPER só é permitido em projeto da gerência Superintendência."


@pytest.fixture
def g1() -> Gerencia:
    gerencia, _ = Gerencia.objects.get_or_create(nome="SUPERINTENDENCIA", defaults={"nome_setor": "Super"})
    return gerencia


@pytest.fixture
def outra() -> Gerencia:
    return Gerencia.objects.create(nome="GERENCIA TRAVA VIDAS", nome_setor="Vidas")


@pytest.fixture
def dat() -> APIClient:
    client = APIClient()
    client.force_authenticate(user=UsuarioFactory(groups=["DAT"]))
    return client


# =============================================================================
# API (/api/projetos/)
# =============================================================================


@pytest.mark.parametrize("onde", ["outra", "sem_gerencia"])
def test_api_nao_cria_super_fora_de_g1(dat, outra, onde):
    payload = {"nome": "Trava SUPER nova", "fluxo": "SUPER", "ativo": True}
    if onde == "outra":
        payload["gerencia"] = outra.id

    resp = dat.post("/api/projetos/", payload, format="json")

    assert resp.status_code == 400, resp.content
    assert resp.json()["detail"] == _MSG  # a tela (ProjetosPage) mostra o `detail`
    assert not Projeto.objects.filter(nome="Trava SUPER nova").exists()


def test_api_cria_super_em_g1(dat, g1):
    resp = dat.post("/api/projetos/", {"nome": "Trava SUPER g1", "fluxo": "SUPER", "gerencia": g1.id}, format="json")

    assert resp.status_code == 201, resp.content


def test_api_cria_nao_super_em_qualquer_gerencia(dat, outra):
    resp = dat.post("/api/projetos/", {"nome": "Trava NAO", "fluxo": "NAO_SUPER", "gerencia": outra.id}, format="json")

    assert resp.status_code == 201, resp.content


def test_api_nao_marca_super_em_projeto_de_outra_gerencia(dat, outra):
    projeto = ProjetoFactory(fluxo="NAO_SUPER", gerencia=outra)

    resp = dat.patch(f"/api/projetos/{projeto.id}/", {"fluxo": "SUPER"}, format="json")

    assert resp.status_code == 400, resp.content
    assert resp.json()["detail"] == _MSG
    projeto.refresh_from_db()
    assert projeto.fluxo == "NAO_SUPER"


def test_api_nao_tira_projeto_super_de_g1(dat, g1, outra):
    projeto = ProjetoFactory(fluxo="SUPER", gerencia=g1)

    resp = dat.patch(f"/api/projetos/{projeto.id}/", {"gerencia": outra.id}, format="json")

    assert resp.status_code == 400, resp.content
    projeto.refresh_from_db()
    assert projeto.gerencia_id == g1.id


def test_api_salvar_super_de_g1_pela_tela_continua_ok(dat, g1):
    """A ProjetosPage não manda `gerencia`: salvar um SUPER de g1 usa a gerência atual."""
    projeto = ProjetoFactory(fluxo="SUPER", gerencia=g1)

    resp = dat.patch(
        f"/api/projetos/{projeto.id}/", {"nome": "Renomeado", "fluxo": "SUPER", "ativo": True}, format="json"
    )

    assert resp.status_code == 200, resp.content


def test_api_patch_sem_fluxo_nem_gerencia_nao_barra_dado_antigo(dat):
    projeto = ProjetoFactory(fluxo="SUPER", gerencia=None)

    resp = dat.patch(f"/api/projetos/{projeto.id}/", {"ativo": False}, format="json")

    assert resp.status_code == 200, resp.content


# =============================================================================
# Admin Django
# =============================================================================


def _admin_form(fluxo: str, gerencia: Gerencia | None):
    from apps.core.admin import ProjetoAdminForm

    return ProjetoAdminForm(
        data={
            "nome": f"Admin trava {fluxo}",
            "codigo": "",
            "fluxo": fluxo,
            "ativo": True,
            "is_test": False,
            "descricao": "",
            "gerencia": gerencia.id if gerencia else "",
        }
    )


def test_admin_nao_salva_super_fora_de_g1(outra):
    form = _admin_form("SUPER", outra)

    assert not form.is_valid()
    assert form.errors["fluxo"] == [_MSG]


def test_admin_salva_super_em_g1(g1):
    form = _admin_form("SUPER", g1)

    assert form.is_valid(), form.errors


# =============================================================================
# Import do export-contract (a planilha de projeto não traz gerência)
# =============================================================================


def _export(tmp_path, csv: str) -> str:
    """Diretório de export mínimo (manifest + projeto.csv), como nos testes do importer."""
    manifest = {
        "generated_at": "2026-09-30",
        "snapshot_date": "2026-09-30",
        "entities": {"projeto": {"file_csv": "projeto.csv", "rows": csv.strip().count("\n")}},
    }
    (tmp_path / "projeto.csv").write_text(csv, encoding="utf-8")
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return str(tmp_path)


def test_import_classifica_super_novo_como_rejeitado(tmp_path):
    from apps.core.services.export_contract_importer import ExportContractImporter

    ProjetoGeral.objects.create(nome="PG TRAVA")
    csv = "projeto,projeto_geral,fluxo\nProjeto Trava Super,PG TRAVA,SUPER\nProjeto Trava Nao,PG TRAVA,NAO_SUPER\n"

    r = ExportContractImporter(path=_export(tmp_path, csv)).run()["por_entidade"]["projeto"]

    assert r["would_create"] == 1
    assert r["would_reject"] == 1
    assert r["reject_reasons"]["fluxo_super_sem_superintendencia"] == 1


def test_import_nao_cria_super(tmp_path):
    from apps.core.services.export_contract_importer import ExportContractImporter

    ProjetoGeral.objects.create(nome="PG TRAVA")
    csv = "projeto,projeto_geral,fluxo\nProjeto Trava Super,PG TRAVA,SUPER\nProjeto Trava Nao,PG TRAVA,NAO_SUPER\n"

    r = ExportContractImporter(path=_export(tmp_path, csv), apply=True, allow=("projeto",)).run()

    assert r["applied"]["projeto"] == 1
    assert not Projeto.objects.filter(nome="Projeto Trava Super").exists()
    assert Projeto.objects.filter(nome="Projeto Trava Nao").exists()


# =============================================================================
# Seed do catálogo canônico (SUPER = projeto da Superintendência)
# =============================================================================


def test_seed_cria_super_em_g1(g1):
    from apps.core.management.commands.seed_projetos_canonicos import seed_projetos_canonicos

    seed_projetos_canonicos([("Proj Trava Seed", "SUPER")])

    assert Projeto.objects.get(nome="Proj Trava Seed").gerencia_id == g1.id


def test_seed_sem_g1_rejeita_super():
    from apps.core.management.commands.seed_projetos_canonicos import seed_projetos_canonicos

    stats = seed_projetos_canonicos([("Proj Trava Seed", "SUPER"), ("Proj Trava Seed Nao", "NAO_SUPER")])

    assert stats["created"] == 1
    assert stats["rejected"] == 1
    assert not Projeto.objects.filter(nome="Proj Trava Seed").exists()
