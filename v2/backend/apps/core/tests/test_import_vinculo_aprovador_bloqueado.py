"""
PR B1 — anti-escalada nos importers de EquipeGerencia.

Com o PR B1, um vínculo GERENTE vigente na SUPERINTENDENCIA dá poder de aprovar
solicitações. Sem esta guarda, a DAT (que importa vínculos) importaria o próprio CPF
como GERENTE de "Super" e ganharia o poder de aprovar — reabrindo o M03-01 por outro
caminho. Os dois importers recusam CRIAR ou REATIVAR esse vínculo e registram a
pendência `vinculo_aprovador_bloqueado`; DESATIVAR continua permitido. Conceder o
poder fica só no formulário de usuário (superuser, auditado).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false, reportCallIssue=false

from __future__ import annotations

import json
from typing import Any

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import EquipeGerencia, Gerencia, Usuario
from apps.core.services.equipe_gerencia_import import import_equipe_gerencia_from_file
from apps.core.services.export_contract_importer import ExportContractImporter
from apps.core.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def g1() -> Gerencia:
    """Catálogo semeado: `nome_setor="Super"` (seed_gerencias); a planilha escreve "Super"."""
    gerencia, _ = Gerencia.objects.get_or_create(nome="SUPERINTENDENCIA", defaults={"nome_setor": "Super"})
    return gerencia


@pytest.fixture
def alvo() -> Usuario:
    return UsuarioFactory(cpf="10000005673")


def _csv(tmp_path, papel: str, cpf: str, ativo: str = "true") -> str:
    fp = tmp_path / "equipe.csv"
    fp.write_text(f"setor,papel,usuario_cpf,ativo\nSuper,{papel},{cpf},{ativo}\n", encoding="utf-8")
    return str(fp)


# =============================================================================
# Upload de equipe (services/equipe_gerencia_import.py)
# =============================================================================


def test_dat_importando_gerente_em_super_recebe_403_e_nao_grava(tmp_path, g1):
    dat = UsuarioFactory(groups=["DAT"])
    content = f"setor,papel,usuario_cpf\nSuper,GERENTE,{dat.cpf}\n".encode()
    client = APIClient()
    client.force_authenticate(user=dat)

    resp = client.post(
        "/api/equipe-gerencia/import/?dry_run=false",
        {"file": SimpleUploadedFile("equipe.csv", content, content_type="text/csv")},
        format="multipart",
    )

    # Import pela tela é só do superusuário (02/10/2026): o DAT nem chega ao service.
    assert resp.status_code == 403, resp.content
    assert not EquipeGerencia.objects.filter(usuario=dat).exists()


def test_superusuario_importando_gerente_em_super_nao_grava_e_gera_pendencia(tmp_path, g1, alvo):
    content = f"setor,papel,usuario_cpf\nSuper,GERENTE,{alvo.cpf}\n".encode()
    client = APIClient()
    client.force_authenticate(user=UsuarioFactory(superuser=True))

    resp = client.post(
        "/api/equipe-gerencia/import/?dry_run=false",
        {"file": SimpleUploadedFile("equipe.csv", content, content_type="text/csv")},
        format="multipart",
    )

    assert resp.status_code == 200, resp.content
    assert not EquipeGerencia.objects.filter(usuario=alvo).exists()
    body = resp.json()
    assert body["stats"]["created"] == 0
    assert len(body["pendencias"]["vinculo_aprovador_bloqueado"]) == 1


def test_reativar_gerente_em_super_e_bloqueado(tmp_path, g1, alvo):
    hoje = timezone.localdate()
    EquipeGerencia.objects.create(
        gerencia=g1, usuario=alvo, papel="GERENTE", ativo=False, valid_from=hoje, valid_to=hoje
    )

    result = import_equipe_gerencia_from_file(path=_csv(tmp_path, "GERENTE", alvo.cpf, "true"), dry_run=False)

    vinculo = EquipeGerencia.objects.get(gerencia=g1, usuario=alvo, papel="GERENTE")
    assert vinculo.ativo is False
    assert result["stats"]["updated"] == 0
    assert result["stats"]["skipped"]["vinculo_aprovador_bloqueado"] == 1
    assert result["pendencias"]["vinculo_aprovador_bloqueado"][0]["linha"] == 1


def test_desativar_gerente_em_super_continua_permitido(tmp_path, g1, alvo):
    EquipeGerencia.objects.create(gerencia=g1, usuario=alvo, papel="GERENTE", ativo=True)

    result = import_equipe_gerencia_from_file(path=_csv(tmp_path, "GERENTE", alvo.cpf, "false"), dry_run=False)

    vinculo = EquipeGerencia.objects.get(gerencia=g1, usuario=alvo, papel="GERENTE")
    assert vinculo.ativo is False
    assert result["stats"]["updated"] == 1
    assert result["pendencias"]["vinculo_aprovador_bloqueado"] == []


def test_outros_papeis_em_super_seguem_importando(tmp_path, g1, alvo):
    result = import_equipe_gerencia_from_file(path=_csv(tmp_path, "COORDENADOR", alvo.cpf), dry_run=False)

    assert result["stats"]["created"] == 1
    assert EquipeGerencia.objects.filter(gerencia=g1, usuario=alvo, papel="COORDENADOR").exists()


# =============================================================================
# export-contract (services/export_contract_importer.py)
# =============================================================================


def _export(tmp_path, csv: str) -> str:
    d = tmp_path / "export"
    d.mkdir()
    (d / "equipe_gerencia.csv").write_text(csv, encoding="utf-8")
    manifest: dict[str, Any] = {"entities": {"equipe_gerencia": {"file_csv": "equipe_gerencia.csv"}}}
    (d / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return str(d)


def test_export_contract_recusa_gerente_em_super(tmp_path, g1, alvo):
    path = _export(tmp_path, f"gerencia,usuario_cpf,papel\nSuper,{alvo.cpf},GERENTE\n")

    report = ExportContractImporter(path=path, apply=True, allow=("equipe_gerencia",)).run()

    pe = report["por_entidade"]["equipe_gerencia"]
    assert pe["would_create"] == 0
    assert pe["would_reject"] == 1
    assert pe["reject_reasons"]["vinculo_aprovador_bloqueado"] == 1
    assert report["applied"]["equipe_gerencia"] == 0
    assert not EquipeGerencia.objects.filter(usuario=alvo).exists()


def test_export_contract_segue_criando_outros_papeis_em_super(tmp_path, g1, alvo):
    path = _export(tmp_path, f"gerencia,usuario_cpf,papel\nSuper,{alvo.cpf},COORDENADOR\n")

    report = ExportContractImporter(path=path, apply=True, allow=("equipe_gerencia",)).run()

    assert report["applied"]["equipe_gerencia"] == 1
    assert EquipeGerencia.objects.filter(gerencia=g1, usuario=alvo, papel="COORDENADOR").exists()
