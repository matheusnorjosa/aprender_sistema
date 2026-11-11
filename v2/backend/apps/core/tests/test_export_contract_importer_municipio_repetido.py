"""
Município repetido no cadastro não pode ser escolhido calado pelo importador (ISS-1635b, Refs #1658).

`_municipio_index` casa por (nome sem acento e sem caixa, UF em caixa alta). A UniqueConstraint(nome, uf)
compara byte a byte, então 'Acaraú'/CE e 'Acarau'/CE convivem no banco. Antes, o último registro vencia e
as linhas do pacote caíam num deles sem aviso. Agora o índice levanta ValueError com as ids, e o apply de
`municipio` usa o mesmo índice, de modo que a grafia sem acento não cria a cópia (M22-05).

Homônimo em outra UF e município sem UF (AMIGOS DO BEM, '') são chaves diferentes e seguem como antes.

Fixtures sintéticos, sem dado pessoal.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false

from __future__ import annotations

import json
from typing import Any

import pytest

from apps.core.models import Municipio, PlanoFormacoes
from apps.core.services.export_contract_importer import ExportContractImporter
from apps.core.tests.factories import MunicipioFactory, ProjetoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

MUNICIPIO_HEADER = "nome,nome_norm,uf,ibge_code,ativo"
PLANO_HEADER = "municipio,uf,projeto,ano"


def _write_export(tmp_path, files: dict[str, str]) -> str:
    d = tmp_path / "export"
    d.mkdir()
    manifest: dict[str, Any] = {"generated_at": "2026-11-10", "entities": {}}
    for name, content in files.items():
        (d / f"{name}.csv").write_text(content, encoding="utf-8")
        manifest["entities"][name] = {"file_csv": f"{name}.csv", "rows": max(content.strip().count("\n"), 0)}
    (d / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return str(d)


def _plano(tmp_path, *linhas: str) -> str:
    ProjetoFactory(nome="Proj X", fluxo="NAO_SUPER")
    corpo = "".join(f"{m},Proj X,2026\n" for m in linhas)
    return _write_export(tmp_path, {"plano_formacao": f"{PLANO_HEADER}\n{corpo}"})


@pytest.mark.parametrize(
    ("primeiro", "segundo", "linha"),
    [
        (("Acaraú", "CE"), ("Acarau", "CE"), "Acarau,CE"),  # acento
        (("Itapipoca", "CE"), ("ITAPIPOCA", "CE"), "Itapipoca,CE"),  # caixa do nome
        (("Fortaleza", "CE"), ("Fortaleza", "ce"), "Fortaleza,CE"),  # caixa da UF
    ],
    ids=["acento", "caixa-do-nome", "caixa-da-uf"],
)
def test_dry_run_para_com_municipio_repetido_e_lista_as_ids(tmp_path, primeiro, segundo, linha):
    a = MunicipioFactory(nome=primeiro[0], uf=primeiro[1])
    b = MunicipioFactory(nome=segundo[0], uf=segundo[1])
    path = _plano(tmp_path, linha)

    with pytest.raises(ValueError, match="município repetido") as exc:
        ExportContractImporter(path=path).run()

    assert f"m{a.pk}" in str(exc.value)
    assert f"m{b.pk}" in str(exc.value)


def test_apply_com_municipio_repetido_nao_grava_nada(tmp_path):
    MunicipioFactory(nome="Acaraú", uf="CE")
    MunicipioFactory(nome="Acarau", uf="CE")
    path = _plano(tmp_path, "Acaraú,CE")
    actor = UsuarioFactory(cpf="11144477735")  # sem ator, o ValueError de _require_actor mascararia o teste

    with pytest.raises(ValueError, match="município repetido"):
        ExportContractImporter(path=path, apply=True, allow=("plano_formacao",), actor=actor).run()

    assert PlanoFormacoes.objects.count() == 0


def _acarau_ce() -> int:
    return Municipio.objects.filter(uf="CE", nome__in=("Acaraú", "Acarau")).count()


def test_grafia_sem_acento_nao_recria_o_municipio(tmp_path):
    """M22-05: o dry-run já dizia would_skip_same; o apply criava 'Acarau' ao lado de 'Acaraú'."""
    MunicipioFactory(nome="Acaraú", uf="CE", ativo=True)
    path = _write_export(tmp_path, {"municipio": f"{MUNICIPIO_HEADER}\nAcarau,ACARAU,CE,,true\n"})

    seco = ExportContractImporter(path=path).run()["por_entidade"]["municipio"]
    r = ExportContractImporter(path=path, apply=True, allow=("municipio",)).run()

    assert seco["would_skip_same"] == 1
    assert r["applied"]["municipio"] == 0
    assert _acarau_ce() == 1


def test_duas_grafias_no_mesmo_csv_criam_um_municipio(tmp_path):
    csv = f"{MUNICIPIO_HEADER}\nAcaraú,ACARAU,CE,,true\nAcarau,ACARAU,CE,,true\n"
    path = _write_export(tmp_path, {"municipio": csv})

    seco = ExportContractImporter(path=path).run()["por_entidade"]["municipio"]
    r = ExportContractImporter(path=path, apply=True, allow=("municipio",)).run()
    de_novo = ExportContractImporter(path=path).run()["por_entidade"]["municipio"]

    assert (seco["would_create"], seco["would_skip_same"]) == (1, 1)
    assert r["applied"]["municipio"] == 1
    assert _acarau_ce() == 1
    assert de_novo["would_skip_same"] == 2


def test_segunda_grafia_com_ativo_diferente_conta_como_update_e_nao_e_gravada(tmp_path):
    """A 2ª grafia conta como a 1ª (setdefault): ativo diferente é would_update, que o create-only não grava."""
    csv = f"{MUNICIPIO_HEADER}\nAcaraú,ACARAU,CE,,true\nAcarau,ACARAU,CE,,false\n"
    path = _write_export(tmp_path, {"municipio": csv})

    seco = ExportContractImporter(path=path).run()["por_entidade"]["municipio"]
    ExportContractImporter(path=path, apply=True, allow=("municipio",)).run()

    assert (seco["would_create"], seco["would_update"]) == (1, 1)
    assert _acarau_ce() == 1
    assert Municipio.objects.get(uf="CE", nome="Acaraú").ativo is True


def test_homonimo_em_outra_uf_e_municipio_sem_uf_seguem_casando(tmp_path):
    """Controle positivo: chaves diferentes não são repetição, e cada linha casa a id da sua UF."""
    ce = MunicipioFactory(nome="Acaraú", uf="CE")
    pi = MunicipioFactory(nome="Acaraú", uf="PI")
    sem_uf = MunicipioFactory(nome="AMIGOS DO BEM", uf="")
    path = _plano(tmp_path, "Acaraú,CE", "Acarau,PI", "AMIGOS DO BEM,")
    actor = UsuarioFactory(cpf="11144477735")

    seco = ExportContractImporter(path=path).run()["por_entidade"]["plano_formacao"]
    r = ExportContractImporter(path=path, apply=True, allow=("plano_formacao",), actor=actor).run()

    assert (seco["would_create"], seco["would_reject"]) == (3, 0)
    assert r["applied"]["plano_formacao"] == 3
    assert set(PlanoFormacoes.objects.values_list("municipio_id", flat=True)) == {ce.pk, pi.pk, sem_uf.pk}
