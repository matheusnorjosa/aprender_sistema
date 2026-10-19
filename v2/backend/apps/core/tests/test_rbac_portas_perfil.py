"""
PR A da arquitetura de permissões (ADR-020): portas fechadas antes de o perfil dar poder.

`Gerencia.perfil` nasce PADRAO e nada o lê ainda. Antes do PR B ligar a união
(grupos ∪ pacote do perfil), três portas ficam fechadas:
- a API de gerências não grava `perfil` (fica fora do serializer) nem renomeia gerência com
  perfil, porque a auditoria reconhece a gerência pelo `nome`;
- os dois importadores de equipe recusam criar ou reativar o vínculo que daria o pacote:
  EQUIPE ou GERENTE numa gerência cujo pacote não é vazio (pendência
  `vinculo_com_pacote_bloqueado`). FORMADOR, COORDENADOR e APOIO não recebem pacote (D3) e
  seguem importando; gerência APROVACAO tem pacote vazio e não trava ninguém;
- desativar continua permitido.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false, reportCallIssue=false

from __future__ import annotations

import itertools
import json
from typing import Any

from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import EquipeGerencia, Gerencia, Usuario
from apps.core.services.equipe_gerencia_import import import_equipe_gerencia_from_file
from apps.core.services.export_contract_importer import ExportContractImporter
from apps.core.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db

_SEQ = itertools.count(1)


def _gerencia(perfil: str = "PADRAO", **kwargs: Any) -> Gerencia:
    n = next(_SEQ)
    kwargs.setdefault("nome", f"GERENCIA PORTA {n}")
    kwargs.setdefault("nome_setor", f"Setor Porta {n}")
    return Gerencia.objects.create(perfil=perfil, **kwargs)


def _cliente(usuario: Usuario) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=usuario)
    return client


@pytest.fixture
def alvo() -> Usuario:
    return UsuarioFactory()


def _csv(tmp_path, gerencia: Gerencia, papel: str, usuario: Usuario, ativo: str = "true") -> str:
    fp = tmp_path / "equipe.csv"
    linha = f"{gerencia.nome_setor},{papel},{usuario.cpf},{ativo}"
    if papel == "APOIO":
        supervisor = UsuarioFactory()
        fp.write_text(
            f"setor,papel,usuario_cpf,ativo,coordenador_supervisor\n{linha},{supervisor.cpf}\n", encoding="utf-8"
        )
    else:
        fp.write_text(f"setor,papel,usuario_cpf,ativo\n{linha}\n", encoding="utf-8")
    return str(fp)


# =============================================================================
# Gerencia.perfil e a API de gerências
# =============================================================================


def test_gerencia_nasce_padrao():
    g = Gerencia.objects.create(nome="GERENCIA NASCE", nome_setor="Nasce")
    g.refresh_from_db()
    assert g.perfil == Gerencia.Perfil.PADRAO == "PADRAO"


def test_api_gerencias_ignora_perfil_no_post_e_patch():
    dat = _cliente(UsuarioFactory(groups=["DAT"]))

    criada = dat.post(
        "/api/gerencias/",
        {"nome": "GERENCIA NOVA PORTA", "nome_setor": "Nova Porta", "perfil": "ADMIN_OPERACIONAL"},
        format="json",
    )
    assert criada.status_code == 201, criada.content
    assert "perfil" not in criada.json()
    g = Gerencia.objects.get(id=criada.json()["id"])
    assert g.perfil == Gerencia.Perfil.PADRAO

    editada = dat.patch(f"/api/gerencias/{g.id}/", {"perfil": "CONTROLE", "descricao": "x"}, format="json")
    assert editada.status_code == 200, editada.content
    assert "perfil" not in editada.json()
    g.refresh_from_db()
    assert g.perfil == Gerencia.Perfil.PADRAO
    assert g.descricao == "x"


def test_nome_de_gerencia_com_perfil_nao_muda_pela_api():
    g = _gerencia(perfil=Gerencia.Perfil.CONTROLE, nome="CONTROLE PORTA")
    root = _cliente(UsuarioFactory(superuser=True))

    resp = root.patch(f"/api/gerencias/{g.id}/", {"nome": "OUTRO NOME"}, format="json")

    assert resp.status_code == 400, resp.content
    assert "nome" in resp.content.decode()
    g.refresh_from_db()
    assert g.nome == "CONTROLE PORTA"


@pytest.mark.parametrize("nome", ["GERENCIA DAT", "CONTROLE", "DIRETORIA"])
def test_nome_de_perfil_permitido_nao_sai_da_gerencia_mesmo_com_perfil_padrao(nome):
    """A auditoria acha a gerência pelo `nome` e a 0120 deixa todas em PADRAO: o nome é a trava."""
    g, _ = Gerencia.objects.update_or_create(nome=nome, defaults={"nome_setor": f"Setor {nome}"})
    assert g.perfil == Gerencia.Perfil.PADRAO
    # Superusuário: a escrita em gerências pede `manage_admin_registries` (19/10), e o vínculo do pacote
    # do DAT poria a `GERENCIA DAT` em ADMIN_OPERACIONAL, tirando o caso "perfil PADRAO".
    root = _cliente(UsuarioFactory(superuser=True))

    resp = root.patch(f"/api/gerencias/{g.id}/", {"nome": f"{nome} ANTIGA"}, format="json")

    assert resp.status_code == 400, resp.content
    assert "nome" in resp.json()["errors"]
    g.refresh_from_db()
    assert g.nome == nome


@pytest.mark.parametrize("nome", ["GERENCIA DAT", "CONTROLE", "DIRETORIA"])
def test_nome_de_perfil_permitido_nao_vai_para_outra_gerencia(nome):
    Gerencia.objects.filter(nome=nome).delete()  # nome livre: a trava vale mesmo assim
    g = _gerencia()
    # Superusuário: a trava vale para todos, e o vínculo de quem é do Controle recriaria a gerência CONTROLE.
    root = _cliente(UsuarioFactory(superuser=True))

    editar = root.patch(f"/api/gerencias/{g.id}/", {"nome": nome}, format="json")
    criar = root.post("/api/gerencias/", {"nome": nome, "nome_setor": "Setor Porta Nova"}, format="json")

    assert editar.status_code == 400, editar.content
    assert criar.status_code == 400, criar.content
    g.refresh_from_db()
    assert g.nome != nome
    assert not Gerencia.objects.filter(nome=nome).exists()


def test_nome_de_gerencia_padrao_muda_como_hoje():
    g = _gerencia()
    dat = _cliente(UsuarioFactory(groups=["DAT"]))

    resp = dat.patch(f"/api/gerencias/{g.id}/", {"nome": "GERENCIA RENOMEADA PORTA"}, format="json")

    assert resp.status_code == 200, resp.content
    g.refresh_from_db()
    assert g.nome == "GERENCIA RENOMEADA PORTA"


# =============================================================================
# Upload de equipe (services/equipe_gerencia_import.py)
# =============================================================================


@pytest.mark.parametrize("papel", ["EQUIPE", "GERENTE"])
def test_import_equipe_recusa_criar_e_reativar_equipe_e_gerente_em_gerencia_com_pacote(tmp_path, alvo, papel):
    g = _gerencia(perfil=Gerencia.Perfil.ADMIN_OPERACIONAL)

    criar = import_equipe_gerencia_from_file(path=_csv(tmp_path, g, papel, alvo), dry_run=False)

    assert criar["stats"]["created"] == 0
    assert criar["stats"]["skipped"]["vinculo_com_pacote_bloqueado"] == 1
    assert criar["pendencias"]["vinculo_com_pacote_bloqueado"][0]["linha"] == 1
    assert not EquipeGerencia.objects.filter(usuario=alvo).exists()

    hoje = timezone.localdate()
    EquipeGerencia.objects.create(gerencia=g, usuario=alvo, papel=papel, ativo=False, valid_from=hoje, valid_to=hoje)
    reativar = import_equipe_gerencia_from_file(path=_csv(tmp_path, g, papel, alvo), dry_run=False)

    assert reativar["stats"]["updated"] == 0
    assert reativar["stats"]["skipped"]["vinculo_com_pacote_bloqueado"] == 1
    assert EquipeGerencia.objects.get(gerencia=g, usuario=alvo, papel=papel).ativo is False


@pytest.mark.parametrize("papel", ["FORMADOR", "COORDENADOR", "APOIO"])
def test_import_equipe_aceita_formador_coordenador_apoio_em_gerencia_com_pacote(tmp_path, alvo, papel):
    g = _gerencia(perfil=Gerencia.Perfil.ADMIN_OPERACIONAL)

    result = import_equipe_gerencia_from_file(path=_csv(tmp_path, g, papel, alvo), dry_run=False)

    assert result["stats"]["created"] == 1, result
    assert result["pendencias"]["vinculo_com_pacote_bloqueado"] == []
    assert EquipeGerencia.objects.filter(gerencia=g, usuario=alvo, papel=papel).exists()


@pytest.mark.parametrize("papel", ["EQUIPE", "GERENTE", "FORMADOR", "COORDENADOR"])
def test_import_equipe_aceita_qualquer_papel_em_gerencia_aprovacao(tmp_path, alvo, papel):
    """APROVACAO tem pacote vazio: a trava não dispara (o aprovador é só o GERENTE da g1, pelo nome)."""
    g = _gerencia(perfil=Gerencia.Perfil.APROVACAO)

    result = import_equipe_gerencia_from_file(path=_csv(tmp_path, g, papel, alvo), dry_run=False)

    assert result["stats"]["created"] == 1, result
    assert EquipeGerencia.objects.filter(gerencia=g, usuario=alvo, papel=papel).exists()


def test_import_equipe_desativa_vinculo_em_gerencia_com_pacote(tmp_path, alvo):
    g = _gerencia(perfil=Gerencia.Perfil.CONTROLE)
    EquipeGerencia.objects.create(gerencia=g, usuario=alvo, papel="EQUIPE", ativo=True)

    result = import_equipe_gerencia_from_file(path=_csv(tmp_path, g, "EQUIPE", alvo, "false"), dry_run=False)

    assert result["stats"]["updated"] == 1
    assert result["pendencias"]["vinculo_com_pacote_bloqueado"] == []
    assert EquipeGerencia.objects.get(gerencia=g, usuario=alvo, papel="EQUIPE").ativo is False


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


def test_export_contract_classify_e_apply_recusam_vinculo_com_pacote(tmp_path, alvo):
    g = _gerencia(perfil=Gerencia.Perfil.ADMIN_OPERACIONAL)
    formador = UsuarioFactory()
    path = _export(
        tmp_path,
        f"gerencia,usuario_cpf,papel\n{g.nome_setor},{alvo.cpf},EQUIPE\n{g.nome_setor},{formador.cpf},FORMADOR\n",
    )

    report = ExportContractImporter(path=path, apply=True, allow=("equipe_gerencia",)).run()

    pe = report["por_entidade"]["equipe_gerencia"]
    assert pe["would_reject"] == 1
    assert pe["would_create"] == 1
    assert pe["reject_reasons"]["vinculo_com_pacote_bloqueado"] == 1
    assert pe["reject_reasons"]["vinculo_aprovador_bloqueado"] == 0
    assert report["applied"]["equipe_gerencia"] == 1
    assert not EquipeGerencia.objects.filter(usuario=alvo).exists()
    assert EquipeGerencia.objects.filter(gerencia=g, usuario=formador, papel="FORMADOR").exists()
