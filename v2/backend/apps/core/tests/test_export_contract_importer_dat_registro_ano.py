"""
`dat_registro` do export-contract com o ANO na chave (export v37, 14/10/2026).

A planilha manda a mesma (município, família, projeto) em 2026 e em 2027, cada linha com a sua
quantidade. Sem o ano na chave, a linha de 2027 virava `repetida_no_arquivo` e os alunos e professores
de 2027 ficavam de fora. O modelo já tem o ano na unicidade; aqui o classify, a detecção de repetida e
o apply passam a usar o ano do arquivo, e o split por ano das compras não move nem duplica o registro
cujo ano veio da planilha.

Linha sem ano (CSV antigo, fixtures) segue a regra antiga: qualquer registro da tripla conta como
existente. Fixtures sintéticos, sem dado pessoal.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

import pytest

from apps.core.models import DATRegistro, ProjetoGeral
from apps.core.services.export_contract_importer import ExportContractImporter
from apps.core.tests.factories import MunicipioFactory, ProjetoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

REG_HEADER = "municipio,uf,projeto_geral,projeto,aluno_qtde,professor_qtde,ano"
COMPRA_HEADER = "municipio,uf,projeto,descricao_produto,tipo,quantidade,data_compra,conta_para_codigos,ano_uso_colecao"


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
    actor = UsuarioFactory(username="u_dat_ano", password="x", cpf="11144477735")
    mun = MunicipioFactory(nome="Cidade Ano", uf="CE", ativo=True)
    pg = ProjetoGeral.objects.create(
        nome="PG Ano", tipo_calculo_codigos="por_professor", multiplicador_professor=Decimal("1.1")
    )
    proj = ProjetoFactory(nome="Proj Ano", fluxo="NAO_SUPER", projeto_geral=pg)
    return {"actor": actor, "mun": mun, "pg": pg, "proj": proj}


def _quantidades() -> dict[int | None, tuple[int | None, int | None]]:
    return {r.ano: (r.aluno_qtde, r.professor_qtde) for r in DATRegistro.objects.all()}


def _seco(path: str) -> dict[str, Any]:
    return ExportContractImporter(path=path).run()["por_entidade"]["dat_registro"]


def _apply(path: str, actor, *allow: str) -> dict[str, Any]:
    return ExportContractImporter(path=path, apply=True, allow=allow or ("dat_registro",), actor=actor).run()


@pytest.mark.parametrize(
    "linhas",
    [
        ["Cidade Ano,CE,PG Ano,Proj Ano,100,10,2026", "Cidade Ano,CE,PG Ano,Proj Ano,300,30,2027"],
        ["Cidade Ano,CE,PG Ano,Proj Ano,300,30,2027", "Cidade Ano,CE,PG Ano,Proj Ano,100,10,2026"],
    ],
    ids=["2026_antes", "2027_antes"],
)
def test_mesma_tripla_em_dois_anos_vira_dois_registros(tmp_path, base, linhas):
    path = _write_export(tmp_path, {"dat_registro": REG_HEADER + "\n" + "\n".join(linhas) + "\n"})

    seco = _seco(path)
    assert seco["would_create"] == 2
    assert seco["reject_reasons"]["repetida_no_arquivo"] == 0

    r = _apply(path, base["actor"])

    assert r["applied"]["dat_registro"] == seco["would_create"] == 2
    assert _quantidades() == {2026: (100, 10), 2027: (300, 30)}


def test_repetida_no_mesmo_ano_continua_repetida(tmp_path, base):
    csv = (
        f"{REG_HEADER}\n"
        "Cidade Ano,CE,PG Ano,Proj Ano,100,10,2026\n"
        "Cidade Ano,CE,PG Ano,Proj Ano,120,10,2026\n"
        "Cidade Ano,CE,PG Ano,Proj Ano,300,30,2027\n"
    )
    path = _write_export(tmp_path, {"dat_registro": csv})

    seco = _seco(path)
    assert seco["would_create"] == 2
    assert seco["reject_reasons"]["repetida_no_arquivo"] == 1
    assert seco["repetidas_divergentes"] == ["CIDADE ANO/CE | PG Ano | Proj Ano | 2026"]

    r = _apply(path, base["actor"])

    assert r["applied"]["dat_registro"] == 2
    assert _quantidades() == {2026: (100, 10), 2027: (300, 30)}  # fica a 1ª linha de 2026


def test_ano_existente_pula_e_ano_novo_entra(tmp_path, base):
    DATRegistro.objects.create(
        municipio=base["mun"],
        projeto_geral=base["pg"],
        projeto=base["proj"],
        ano=2026,
        aluno_qtde=100,
        professor_qtde=10,
        created_by=base["actor"],
    )
    csv = f"{REG_HEADER}\nCidade Ano,CE,PG Ano,Proj Ano,100,10,2026\nCidade Ano,CE,PG Ano,Proj Ano,300,30,2027\n"
    path = _write_export(tmp_path, {"dat_registro": csv})

    seco = _seco(path)
    assert (seco["would_create"], seco["would_skip_same"]) == (1, 1)

    assert _apply(path, base["actor"])["applied"]["dat_registro"] == 1
    assert _quantidades() == {2026: (100, 10), 2027: (300, 30)}


@pytest.mark.parametrize(
    "linhas",
    [
        ["Cidade Ano,CE,PG Ano,Proj Ano,100,10,2026", "Cidade Ano,CE,PG Ano,Proj Ano,300,30,2027"],
        ["Cidade Ano,CE,PG Ano,Proj Ano,300,30,2027", "Cidade Ano,CE,PG Ano,Proj Ano,100,10,2026"],
    ],
    ids=["2026_antes", "2027_antes"],
)
def test_registro_sem_ano_de_carga_antiga_recebe_o_ano_e_nao_duplica(tmp_path, base, linhas):
    """A carga antiga gravou a tripla sem ano (flat). A linha com ano e as mesmas quantidades é esse
    registro: o ano vazio é preenchido (só o ano, nada mais) e não nasce um segundo registro com as
    mesmas quantidades. A ordem das linhas no arquivo não muda o resultado."""
    flat = DATRegistro.objects.create(
        municipio=base["mun"],
        projeto_geral=base["pg"],
        projeto=base["proj"],
        ano=None,
        aluno_qtde=100,
        professor_qtde=10,
        created_by=base["actor"],
    )
    path = _write_export(tmp_path, {"dat_registro": REG_HEADER + "\n" + "\n".join(linhas) + "\n"})

    seco = _seco(path)
    assert (seco["would_create"], seco["would_update"], seco["sem_ano_divergente"]) == (1, 1, 0)

    r = _apply(path, base["actor"])

    assert r["applied"]["dat_registro"] == 1
    assert r["applied"]["dat_registro__ano_preenchido"] == 1
    flat.refresh_from_db()
    assert flat.ano == 2026
    assert _quantidades() == {2026: (100, 10), 2027: (300, 30)}


def test_registro_sem_ano_com_quantidade_de_nenhuma_linha_fica_como_esta(tmp_path, base):
    """O flat antigo não bate com a quantidade de nenhuma linha: não se sabe de que ano ele é. Nenhuma
    linha o assume (a quantidade dela não se perde), ele fica sem ano e o dry-run o conta em
    `sem_ano_divergente` para uma pessoa decidir."""
    DATRegistro.objects.create(
        municipio=base["mun"],
        projeto_geral=base["pg"],
        projeto=base["proj"],
        ano=None,
        aluno_qtde=100,
        professor_qtde=10,
        created_by=base["actor"],
    )
    csv = f"{REG_HEADER}\nCidade Ano,CE,PG Ano,Proj Ano,300,30,2027\nCidade Ano,CE,PG Ano,Proj Ano,80,8,2026\n"
    path = _write_export(tmp_path, {"dat_registro": csv})

    seco = _seco(path)
    assert (seco["would_create"], seco["would_update"], seco["sem_ano_divergente"]) == (2, 0, 1)

    r = _apply(path, base["actor"])

    assert r["applied"]["dat_registro"] == 2
    assert "dat_registro__ano_preenchido" not in r["applied"]
    assert _quantidades() == {None: (100, 10), 2026: (80, 8), 2027: (300, 30)}


def test_registro_sem_ano_criado_na_mesma_carga_nao_recebe_ano(tmp_path, base):
    """Só o flat que já estava no banco pode receber o ano. O que a linha sem ano do próprio arquivo
    acabou de criar não é carga antiga: a linha com ano ao lado vira registro dela."""
    csv = f"{REG_HEADER}\nCidade Ano,CE,PG Ano,Proj Ano,50,5,\nCidade Ano,CE,PG Ano,Proj Ano,300,30,2027\n"
    path = _write_export(tmp_path, {"dat_registro": csv})

    seco = _seco(path)
    assert (seco["would_create"], seco["would_update"]) == (2, 0)

    r = _apply(path, base["actor"])

    assert r["applied"]["dat_registro"] == 2
    assert _quantidades() == {None: (50, 5), 2027: (300, 30)}


def test_split_das_compras_nao_desfaz_o_ano_da_planilha(tmp_path, base):
    """Só a linha de 2027 na planilha, compras de 2026 e 2027: o registro de 2027 fica em 2027 com as
    quantidades dele (antes o split o movia para 2026, o ano primário) e o de 2026 nasce vazio."""
    reg = "Cidade Ano,CE,PG Ano,Proj Ano,300,30,2027\n"
    compras = (
        f"{COMPRA_HEADER}\n"
        "Cidade Ano,CE,Proj Ano,Kit prof,Professor,20,2026-03-01,true,2026\n"
        "Cidade Ano,CE,Proj Ano,Kit prof,Professor,100,2026-03-02,true,2027\n"
    )
    path = _write_export(tmp_path, {"dat_registro": f"{REG_HEADER}\n{reg}", "dat_compra": compras})

    _apply(path, base["actor"], "dat_registro", "dat_compra")

    regs = {r.ano: r for r in DATRegistro.objects.all()}
    assert set(regs) == {2026, 2027}
    assert (regs[2027].aluno_qtde, regs[2027].professor_qtde) == (300, 30)
    assert (regs[2026].aluno_qtde, regs[2026].professor_qtde) == (None, None)
    assert regs[2027].nr_codigos == 110  # ceil(100 × 1,1): só as compras de 2027
    assert regs[2026].nr_codigos == 22


def test_carga_repetida_e_idempotente_com_split(tmp_path, base):
    reg = "Cidade Ano,CE,PG Ano,Proj Ano,100,10,2026\nCidade Ano,CE,PG Ano,Proj Ano,300,30,2027\n"
    compras = (
        f"{COMPRA_HEADER}\n"
        "Cidade Ano,CE,Proj Ano,Kit prof,Professor,20,2026-03-01,true,2026\n"
        "Cidade Ano,CE,Proj Ano,Kit prof,Professor,100,2026-03-02,true,2027\n"
    )
    path = _write_export(tmp_path, {"dat_registro": f"{REG_HEADER}\n{reg}", "dat_compra": compras})

    _apply(path, base["actor"], "dat_registro", "dat_compra")
    r2 = _apply(path, base["actor"], "dat_registro", "dat_compra")

    assert r2["applied"]["dat_registro"] == 0
    assert _quantidades() == {2026: (100, 10), 2027: (300, 30)}


def test_ano_ja_criado_vazio_pelo_split_aparece_no_dry_run(tmp_path, base):
    """O registro de 2027 que o split criou sem quantidade existe: o create-only não o preenche, e o
    dry-run conta a linha em `existe_sem_quantidade` para a quantidade da planilha não sumir calada."""
    DATRegistro.objects.create(
        municipio=base["mun"], projeto_geral=base["pg"], projeto=base["proj"], ano=2027, created_by=base["actor"]
    )
    path = _write_export(tmp_path, {"dat_registro": f"{REG_HEADER}\nCidade Ano,CE,PG Ano,Proj Ano,300,30,2027\n"})

    seco = _seco(path)

    assert (seco["would_skip_same"], seco["existe_sem_quantidade"]) == (1, 1)
    assert _apply(path, base["actor"])["applied"]["dat_registro"] == 0
    assert _quantidades() == {2027: (None, None)}


@pytest.mark.parametrize(
    ("no_banco", "linhas", "pulados"),
    [
        ({2027: (100, 10)}, ["2026,100,10", "2027,300,30"], 1),
        ({2026: (300, 30)}, ["2026,100,10", "2027,300,30"], 1),
        ({2026: (100, 10)}, ["2027,100,10"], 0),
        ({2027: (100, 10)}, ["2026,100,10"], 0),
    ],
    ids=["linha_2026_no_registro_2027", "linha_2027_no_registro_2026", "so_2027_no_2026", "so_2026_no_2027"],
)
def test_registro_com_a_quantidade_de_outro_ano_nao_ganha_copia(tmp_path, base, no_banco, linhas, pulados):
    """O split antigo dava ao flat o ano das compras (2026 se houvesse, senão o maior), não o da linha de
    onde vinham as quantidades. Registro com ano que guarda a quantidade da linha de OUTRO ano, e não a do
    próprio ano: criar o ano da linha copiaria a quantidade para os dois anos. A tripla não ganha registro,
    a linha é rejeitada em `quantidade_em_outro_ano` e o banco fica como está, para uma pessoa decidir."""
    for ano, (aluno, prof) in no_banco.items():
        DATRegistro.objects.create(
            municipio=base["mun"],
            projeto_geral=base["pg"],
            projeto=base["proj"],
            ano=ano,
            aluno_qtde=aluno,
            professor_qtde=prof,
            created_by=base["actor"],
        )
    csv = REG_HEADER + "\n"
    for linha in linhas:
        ano, aluno, prof = linha.split(",")
        csv += f"Cidade Ano,CE,PG Ano,Proj Ano,{aluno},{prof},{ano}\n"
    path = _write_export(tmp_path, {"dat_registro": csv})

    seco = _seco(path)
    assert (seco["would_create"], seco["would_skip_same"], seco["would_reject"]) == (0, pulados, 1)
    assert seco["reject_reasons"]["quantidade_em_outro_ano"] == 1

    r = _apply(path, base["actor"])

    assert r["applied"]["dat_registro"] == 0
    assert _quantidades() == no_banco


def test_registro_com_a_quantidade_do_proprio_ano_deixa_o_outro_ano_entrar(tmp_path, base):
    """Controle: os dois anos com a mesma quantidade na planilha. O registro de 2026 bate com a linha de
    2026, então não foi movido de ano; a linha de 2027 entra."""
    DATRegistro.objects.create(
        municipio=base["mun"],
        projeto_geral=base["pg"],
        projeto=base["proj"],
        ano=2026,
        aluno_qtde=100,
        professor_qtde=10,
        created_by=base["actor"],
    )
    csv = f"{REG_HEADER}\nCidade Ano,CE,PG Ano,Proj Ano,100,10,2026\nCidade Ano,CE,PG Ano,Proj Ano,100,10,2027\n"
    path = _write_export(tmp_path, {"dat_registro": csv})

    seco = _seco(path)
    assert (seco["would_create"], seco["would_reject"]) == (1, 0)

    assert _apply(path, base["actor"])["applied"]["dat_registro"] == 1
    assert _quantidades() == {2026: (100, 10), 2027: (100, 10)}


def test_flat_divergente_continua_sem_ano_depois_do_split(tmp_path, base):
    """O flat que não bate com nenhuma linha (`sem_ano_divergente`) fica sem ano também depois do split
    do mesmo apply: o split não lhe dá o ano primário das compras ao lado do registro com ano da planilha."""
    DATRegistro.objects.create(
        municipio=base["mun"],
        projeto_geral=base["pg"],
        projeto=base["proj"],
        ano=None,
        aluno_qtde=300,
        professor_qtde=30,
        created_by=base["actor"],
    )
    compras = (
        f"{COMPRA_HEADER}\n"
        "Cidade Ano,CE,Proj Ano,Kit prof,Professor,20,2026-03-01,true,2026\n"
        "Cidade Ano,CE,Proj Ano,Kit prof,Professor,100,2026-03-02,true,2027\n"
    )
    reg = "Cidade Ano,CE,PG Ano,Proj Ano,310,30,2027\n"
    path = _write_export(tmp_path, {"dat_registro": f"{REG_HEADER}\n{reg}", "dat_compra": compras})

    assert _seco(path)["sem_ano_divergente"] == 1

    _apply(path, base["actor"], "dat_registro", "dat_compra")

    assert _quantidades() == {None: (300, 30), 2026: (None, None), 2027: (310, 30)}
