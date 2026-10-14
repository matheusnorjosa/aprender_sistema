"""
Município sem UF no export-contract: AMIGOS DO BEM (decisão do dono, export v37 de 14/10/2026).

Os eventos, planos, formações e acompanhamentos de AMIGOS DO BEM sem unidade chegam com município
"AMIGOS DO BEM" e UF vazia; o `municipio.csv` traz essa linha sem UF. O caminho inteiro precisa casar
por (nome, ''): o apply de `municipio` cria o município sem UF, e os resolvers de solicitacao,
plano_formacao, formacao e acompanhamento o acham por (nome, ''). Não pode cair em "AMIGOS DO BEM
(MAURITI)"/CE (onde ficam as compras e o DAT) nem num homônimo com UF.

Fixtures sintéticos, sem dado pessoal.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false

from __future__ import annotations

import json
from typing import Any

import pytest

from apps.core.models import Acompanhamento, Formacao, Municipio, PlanoFormacoes, Solicitacao
from apps.core.services.export_contract_importer import ExportContractImporter
from apps.core.tests.factories import MunicipioFactory, ProjetoFactory, TipoEventoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

_CPF = "11144477735"
_ENTIDADES = ("solicitacao", "plano_formacao", "formacao", "acompanhamento")

MUNICIPIO_CSV = (
    "nome,nome_norm,uf,ibge_code,ativo\n"
    "AMIGOS DO BEM,AMIGOS DO BEM,,,true\n"
    "AMIGOS DO BEM (MAURITI),AMIGOS DO BEM (MAURITI),CE,,true\n"
)
SOLICITACAO_CSV = (
    "evento_id,municipio,uf,projeto,tipo_evento,data,hora_inicio,hora_fim,segmento,solicitante_cpf\n"
    f"EV-ADB-1,AMIGOS DO BEM,,Proj ADB,Formacao,2026-11-10,09:00,12:00,3º ano,{_CPF}\n"
)
PLANO_CSV = f"municipio,uf,projeto,ano,coordenador_cpf\nAMIGOS DO BEM,,Proj ADB,2026,{_CPF}\n"
FORMACAO_CSV = (
    "municipio,uf,projeto,ano,numero_formacao,data_formacao,carga_horaria,modalidade\n"
    "AMIGOS DO BEM,,Proj ADB,2026,1,2026-07-24,4,presencial\n"
)
ACOMP_CSV = "municipio,uf,projeto,ano,tipo,data_acompanhamento\nAMIGOS DO BEM,,Proj ADB,2026,primeiro,2026-08-10\n"


def _write_export(tmp_path, files: dict[str, str]) -> str:
    d = tmp_path / "export"
    d.mkdir()
    manifest: dict[str, Any] = {"generated_at": "2026-10-14", "entities": {}}
    for name, content in files.items():
        (d / f"{name}.csv").write_text(content, encoding="utf-8")
        manifest["entities"][name] = {"file_csv": f"{name}.csv", "rows": max(content.strip().count("\n"), 0)}
    (d / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return str(d)


def _pacote(tmp_path, *, com_municipio: bool = True) -> str:
    files = {
        "solicitacao": SOLICITACAO_CSV,
        "plano_formacao": PLANO_CSV,
        "formacao": FORMACAO_CSV,
        "acompanhamento": ACOMP_CSV,
    }
    if com_municipio:
        files["municipio"] = MUNICIPIO_CSV
    return _write_export(tmp_path, files)


@pytest.fixture
def base():
    """Masters + os dois vizinhos que NÃO podem casar: o de Mauriti/CE e um homônimo com UF."""
    actor = UsuarioFactory(username="u_adb", cpf=_CPF, email="adb@example.invalid")
    TipoEventoFactory(nome="Formacao")
    ProjetoFactory(nome="Proj ADB", fluxo="NAO_SUPER")
    mauriti = MunicipioFactory(nome="AMIGOS DO BEM (MAURITI)", uf="CE", ativo=True)
    homonimo = MunicipioFactory(nome="AMIGOS DO BEM", uf="PE", ativo=True)
    return {"actor": actor, "vizinhos": {mauriti.id, homonimo.id}}


def _apply(path: str, actor, *allow: str) -> dict[str, Any]:
    return ExportContractImporter(path=path, apply=True, allow=allow, actor=actor).run()


def test_apply_de_municipio_cria_amigos_do_bem_sem_uf(tmp_path, base):
    path = _pacote(tmp_path)
    seco = ExportContractImporter(path=path).run()["por_entidade"]["municipio"]
    assert (seco["would_create"], seco["would_skip_same"], seco["would_reject"]) == (1, 1, 0)

    r = _apply(path, base["actor"], "municipio")

    assert r["applied"]["municipio"] == 1
    assert Municipio.objects.filter(nome="AMIGOS DO BEM", uf="").count() == 1
    assert Municipio.objects.filter(nome__startswith="AMIGOS DO BEM").count() == 3


def test_entidades_casam_o_municipio_sem_uf_no_dry_run(tmp_path, base):
    sem_uf = MunicipioFactory(nome="AMIGOS DO BEM", uf="", ativo=True)
    path = _pacote(tmp_path)
    _apply(path, base["actor"], "plano_formacao")  # as filhas precisam do plano pai no banco
    assert PlanoFormacoes.objects.get().municipio_id == sem_uf.id

    pe = ExportContractImporter(path=path).run()["por_entidade"]

    assert (pe["solicitacao"]["would_create"], pe["solicitacao"]["would_reject"]) == (1, 0)
    assert (pe["plano_formacao"]["would_skip_same"], pe["plano_formacao"]["would_reject"]) == (1, 0)
    assert (pe["formacao"]["would_create"], pe["formacao"]["would_reject"]) == (1, 0)
    assert (pe["acompanhamento"]["would_create"], pe["acompanhamento"]["would_reject"]) == (1, 0)


def test_carga_inteira_grava_tudo_no_municipio_sem_uf(tmp_path, base):
    path = _pacote(tmp_path)

    r = _apply(path, base["actor"], "municipio", *_ENTIDADES)

    assert [r["applied"][e] for e in ("municipio", *_ENTIDADES)] == [1, 1, 1, 1, 1]
    sem_uf = Municipio.objects.get(nome="AMIGOS DO BEM", uf="")
    plano = PlanoFormacoes.objects.get()
    assert Solicitacao.objects.get().municipio_id == sem_uf.id
    assert plano.municipio_id == sem_uf.id
    assert Formacao.objects.get().plano_id == plano.id
    assert Acompanhamento.objects.get().plano_id == plano.id


def test_sem_o_municipio_sem_uf_nada_cai_nos_vizinhos(tmp_path, base):
    """Banco sem o AMIGOS DO BEM sem UF: as linhas são recusadas e nenhuma vai para Mauriti/CE nem
    para o homônimo com UF."""
    path = _pacote(tmp_path, com_municipio=False)

    pe = ExportContractImporter(path=path).run()["por_entidade"]
    assert all(pe[e]["would_reject"] == 1 for e in _ENTIDADES)

    r = _apply(path, base["actor"], *_ENTIDADES)

    assert all(r["applied"][e] == 0 for e in _ENTIDADES)
    assert not Solicitacao.objects.filter(municipio_id__in=base["vizinhos"]).exists()
    assert not PlanoFormacoes.objects.filter(municipio_id__in=base["vizinhos"]).exists()
