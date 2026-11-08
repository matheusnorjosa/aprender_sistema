"""
Lote E2 (decisões do dono de 07/11/2026): a carga cadastra só os produtos reais do `produto.csv`.

Produto real = linha com `codigo_erp` vazio e `fonte=Produtos` (o id curto da planilha) cujo código, por
`_norm_codigo`, ainda não está no banco. Linha com `codigo_erp` é ruído do ERP (fragmento ou kit duplicado de
um id curto) e nunca vira produto. Pacote sem as colunas `codigo_erp`/`fonte` é recusado inteiro: um export
antigo criaria os 585 ruídos do v40. O dry-run lista os produtos que nasceriam (`would_create_codigos`) para
o dono aprovar a lista, não o número.

Fixtures sintéticos, sem dado pessoal.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false

from __future__ import annotations

import json
from io import StringIO
from typing import Any

from django.core.management import call_command
from django.core.management.base import CommandError

import pytest

from apps.core.models import Produto, ProjetoGeral
from apps.core.services.export_contract_importer import ExportContractImporter
from apps.core.tests.factories import ProjetoFactory

pytestmark = pytest.mark.django_db

PRODUTO_HEADER = "codigo,nome,descricao,projeto,tipo,fonte,natureza,codigo_erp,id_curto_par"
COMPRA_HEADER = (
    "municipio,uf,projeto,produto_codigo,descricao_produto,tipo,conta_para_codigos,quantidade,ano_uso,data_compra"
)


def _write_export(tmp_path, files: dict[str, str]) -> str:
    d = tmp_path / "export"
    d.mkdir()
    manifest: dict[str, Any] = {"generated_at": "2026-11-07", "entities": {}}
    for name, content in files.items():
        (d / f"{name}.csv").write_text(content, encoding="utf-8")
        manifest["entities"][name] = {"file_csv": f"{name}.csv", "rows": max(content.strip().count("\n"), 0)}
    (d / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return str(d)


def _colecao():
    """Coleção A com o projeto que leva o nome da coleção (como o `projeto` do produto.csv)."""
    pg = ProjetoGeral.objects.create(nome="Col A", usa_avaliar=False)
    return ProjetoFactory(nome="Col A", fluxo="NAO_SUPER", projeto_geral=pg)


def _produtos(*linhas: str) -> str:
    return PRODUTO_HEADER + "\n" + "\n".join(linhas) + "\n"


def _seco(path: str) -> dict[str, Any]:
    return ExportContractImporter(path=path).run()["por_entidade"]["produto"]


def _aplica(path: str) -> dict[str, Any]:
    return ExportContractImporter(path=path, apply=True, allow=("produto",)).run()


# Formato do v40: fragmento ERP, kit ERP com par, kit ERP sem par, id curto já no banco e id curto novo.
_V40 = (
    "ME02084,Col A 1,livro do aluno,Col A,Aluno,produtos_erp,fragmento,ME02084,",
    "0101005,Col A 1,kit erp,Col A,Aluno,produtos_erp,kit,0101005,5",
    "0109009,Col A 9,kit erp sem par,Col A,Aluno,produtos_erp,kit,0109009,",
    "5,Col A 1,kit,Col A,Aluno,Produtos,kit,,",
    "6,Col A 2,kit do aluno,Col A,Aluno,Produtos,kit,,",
)


def test_classify_cria_so_o_id_curto_novo_e_pula_o_ruido_do_erp(tmp_path):
    proj = _colecao()
    Produto.objects.create(codigo="5", nome="Nome Antigo", projeto=proj)
    path = _write_export(tmp_path, {"produto": _produtos(*_V40)})

    t = _seco(path)

    assert (t["would_create"], t["would_skip_same"], t["would_reject"], t["would_update"]) == (1, 4, 0, 0)
    assert t["skip_reasons"] == {
        "ja_existe": 1,
        "erp_kit_com_par": 1,
        "erp_kit_sem_par": 1,
        "erp_fragmento": 1,
        "erp_outro": 0,
    }
    assert sum(t["skip_reasons"].values()) == t["would_skip_same"]
    assert t["would_create_codigos"] == [
        {"codigo": "6", "nome": "Col A 2", "projeto": "Col A", "compras_no_pacote": 0, "gemeo_de": []}
    ]
    assert "nota" not in t  # produto passa a gravar


def test_pacote_sem_a_coluna_codigo_erp_e_recusado_inteiro(tmp_path):
    _colecao()
    path = _write_export(tmp_path, {"produto": "codigo,nome,projeto\n6,Col A 2,Col A\n0101005,Col A 1,Col A\n"})

    t = _seco(path)

    assert (t["would_create"], t["would_reject"]) == (0, 2)
    assert t["reject_reasons"]["contrato_sem_codigo_erp"] == 2
    assert _aplica(path)["applied"]["produto"] == 0
    assert not Produto.objects.exists()


def test_apply_cria_so_o_produto_real_e_nunca_atualiza_o_existente(tmp_path):
    proj = _colecao()
    Produto.objects.create(codigo="5", nome="Nome Antigo", projeto=proj)
    linhas = (*_V40, "7,Sem Projeto 1,kit,Projeto Que Nao Existe,Aluno,Produtos,kit,,")
    path = _write_export(tmp_path, {"produto": _produtos(*linhas)})

    t = _seco(path)
    assert (t["would_create"], t["would_reject"]) == (1, 1)
    assert t["reject_reasons"]["projeto_nao_resolvido"] == 1

    assert _aplica(path)["applied"]["produto"] == t["would_create"]
    novo = Produto.objects.get(codigo="6")
    assert (novo.nome, novo.descricao, novo.projeto_id, novo.ativo) == ("Col A 2", "kit do aluno", proj.pk, True)
    assert Produto.objects.get(codigo="5").nome == "Nome Antigo"
    assert sorted(Produto.objects.values_list("codigo", flat=True)) == ["5", "6"]

    assert _aplica(path)["applied"]["produto"] == 0  # 2ª execução não cria nada


def test_motivos_de_recusa_somam_o_would_reject(tmp_path):
    proj = _colecao()
    Produto.objects.create(codigo="0101005", nome="Kit ERP já cadastrado", projeto=proj)
    path = _write_export(
        tmp_path,
        {
            "produto": _produtos(
                ",Sem Codigo,kit,Col A,Aluno,Produtos,kit,,",
                "8,Col A 8,kit,Col A,Aluno,produtos_erp,kit,,",  # id curto com fonte do ERP: sinais divergem
                "0101005,Col A 1,kit erp,Col A,Aluno,produtos_erp,kit,0101005,5",  # ERP já no banco
                "0103003,Col A 3,brinde,Col A,Aluno,produtos_erp,brinde,0103003,",  # natureza desconhecida
                "6,Col A 2,kit,Col A,Aluno,Produtos,kit,,",
                "006,Col A 2,kit,Col A,Aluno,Produtos,kit,,",  # o mesmo id curto novo de novo
            )
        },
    )

    t = _seco(path)

    assert (t["would_create"], t["would_skip_same"], t["would_reject"]) == (1, 2, 3)
    assert t["reject_reasons"] == {
        "contrato_sem_codigo_erp": 0,
        "fonte_inconsistente": 1,
        "codigo_vazio": 1,
        "projeto_nao_resolvido": 0,
        "codigo_repetido_no_arquivo": 1,
    }
    assert sum(t["reject_reasons"].values()) == t["would_reject"]
    assert t["skip_reasons"]["erp_outro"] == 1
    assert t["erp_ja_no_banco"] == 1


def test_lista_dos_novos_traz_gemeo_projeto_sem_colecao_e_compras_do_pacote(tmp_path):
    _colecao()
    ProjetoFactory(nome="Avulso", fluxo="NAO_SUPER")  # projeto sem coleção
    path = _write_export(
        tmp_path,
        {
            "produto": _produtos(
                "6,Col A 2,kit,Col A,Aluno,Produtos,kit,,",
                "79,Col A 2,kit,Col A,Aluno,Produtos,kit,,",  # mesmo projeto, nome e tipo do 6
                "80,Col A 2,kit,Col A,Professor,Produtos,kit,,",  # outro tipo: não é gêmeo
                "0102006,Col A 2,kit erp,Col A,Aluno,produtos_erp,kit,0102006,6",
                "90,Avulso 1,kit,Avulso,Aluno,Produtos,kit,,",
            ),
            "dat_compra": COMPRA_HEADER
            + "\nCidade X,CE,Col A 2,6,kit,Aluno,true,10,2026,2026-06-08"
            + "\nCidade X,CE,Col A 2,102006,kit,Aluno,true,11,2026,2026-06-08\n",
        },
    )

    t = _seco(path)

    por_codigo = {c["codigo"]: c for c in t["would_create_codigos"]}
    assert sorted(por_codigo) == ["6", "79", "80", "90"]
    assert por_codigo["6"]["gemeo_de"] == ["79"]
    assert por_codigo["79"]["gemeo_de"] == ["6"]
    assert por_codigo["80"]["gemeo_de"] == []
    assert por_codigo["6"]["compras_no_pacote"] == 2  # uma pelo id curto e uma pelo par do ERP
    assert por_codigo["90"]["projeto"] == "Avulso"
    assert t["gemeo_no_catalogo"] == 2
    assert t["produto_projeto_sem_colecao"] == 1


def test_veto_de_um_item_e_a_copia_do_pacote_sem_a_linha(tmp_path):
    """O apply cria toda a lista; o item vetado sai tirando a linha do produto.csv de uma cópia (spec)."""
    _colecao()
    gemeo = "79,Col A 2,kit,Col A,Aluno,Produtos,kit,,"
    linhas = (
        "6,Col A 2,kit,Col A,Aluno,Produtos,kit,,",
        gemeo,
        "0102079,Col A 2,kit erp,Col A,Aluno,produtos_erp,kit,0102079,79",  # par do vetado
    )
    (tmp_path / "original").mkdir()
    (tmp_path / "copia").mkdir()
    original = _write_export(tmp_path / "original", {"produto": _produtos(*linhas)})
    copia = _write_export(tmp_path / "copia", {"produto": _produtos(*(x for x in linhas if x != gemeo))})

    antes, depois = _seco(original), _seco(copia)

    assert [c["codigo"] for c in antes["would_create_codigos"]] == ["6", "79"]
    assert [c["codigo"] for c in depois["would_create_codigos"]] == ["6"]
    assert depois["would_create"] == antes["would_create"] - 1  # o portão cai só pelos vetados
    assert (depois["would_skip_same"], depois["would_reject"]) == (antes["would_skip_same"], 0)
    assert depois["skip_reasons"] == antes["skip_reasons"]  # o par do vetado segue erp_kit_com_par

    assert _aplica(copia)["applied"]["produto"] == 1
    assert list(Produto.objects.values_list("codigo", flat=True)) == ["6"]


# ───────── comando: produto roda sozinho (F7) ─────────
def _vazio(tmp_path) -> str:
    return _write_export(tmp_path, {})


@pytest.mark.parametrize("outra", ["dat_compra", "projeto"])
def test_produto_com_outra_entidade_e_command_error(tmp_path, outra):
    with pytest.raises(CommandError, match="produto"):
        call_command(
            "import_export_contract",
            "--path",
            _vazio(tmp_path),
            "--apply",
            "--allow-entity",
            "produto",
            "--allow-entity",
            outra,
        )


def test_comando_imprime_a_lista_dos_produtos_novos(tmp_path):
    proj = _colecao()
    Produto.objects.create(codigo="5", nome="Nome Antigo", projeto=proj)
    out = StringIO()
    call_command("import_export_contract", "--path", _write_export(tmp_path, {"produto": _produtos(*_V40)}), stdout=out)
    texto = out.getvalue()
    assert "would_create_codigos" in texto
    assert "Col A 2" in texto
    assert "erp_fragmento" in texto
