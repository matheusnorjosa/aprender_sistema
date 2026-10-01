"""
Tests do classify + apply da fatia `dat_compra` do export-contract, e do guard de
ambiguidade de `projeto_geral` (CONTRATO-v4 §2).

Segurança: apply exige allowlist + actor; create-only; idempotente; fixtures sintéticos.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false, reportPrivateUsage=false

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from io import StringIO
from typing import Any

from django.core.management import call_command

import pytest

from apps.core.models import DATCompra, DATRegistro, Produto, ProjetoGeral
from apps.core.services.export_contract_importer import ExportContractImporter, _parse_int
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
    reg = DATRegistro.objects.create(
        municipio=mun, projeto_geral=pg, projeto=proj, professor_qtde=52, ano=2026, created_by=actor
    )
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


def test_apply_final_pass_runs_split_por_ano(tmp_path):
    """O passo final do importer roda o split por-ano automaticamente: um DATRegistro flat
    (ano=None) com compras em 2 anos vira UM registro por ano. Sem isso, os registros ficam
    flat e `nr_codigos` conta o cohort errado (ano_uso=None) — o bug que quebrou /dat/registros
    em prod (2026-09). O split roda no MESMO bloco final que já recomputa nr_codigos."""
    actor = _actor()
    mun = MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    pg = ProjetoGeral.objects.create(
        nome="PG X", usa_avaliar=False, tipo_calculo_codigos="por_professor", multiplicador_professor=Decimal("1.1")
    )
    proj = ProjetoFactory(nome="Proj X", fluxo="NAO_SUPER", projeto_geral=pg)
    # registro flat, como o import de dat_registro cria ANTES das compras (ano só se conhece depois).
    DATRegistro.objects.create(municipio=mun, projeto_geral=pg, projeto=proj, professor_qtde=40, created_by=actor)
    rows = "\n".join([_compra_row(qtde=40, ano=2026), _compra_row(qtde=20, ano=2027)])
    ExportContractImporter(
        path=_write_export(tmp_path, {"dat_compra": f"{COMPRA_HEADER}\n{rows}\n"}),
        apply=True,
        allow=("dat_compra",),
        actor=actor,
    ).run()
    anos = sorted(DATRegistro.objects.filter(municipio=mun, projeto=proj).values_list("ano", flat=True))
    assert anos == [2026, 2027]  # fan-out por ano de uso das compras
    # e nr_codigos é POR ANO: 2026 = ceil(40×1.1)=44; 2027 = ceil(20×1.1)=22
    assert DATRegistro.objects.get(municipio=mun, projeto=proj, ano=2026).nr_codigos == 44
    assert DATRegistro.objects.get(municipio=mun, projeto=proj, ano=2027).nr_codigos == 22


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


def test_apply_dat_compra_liga_produto_por_codigo_normalizando_zero(tmp_path):
    """#1635: liga DATCompra.produto por `produto_codigo` == `produto.codigo` normalizando o
    ZERO À ESQUERDA nos DOIS lados. SKU ausente do catálogo fica sem ligação (contado, não inventado).

    RED no código antigo: `_apply_dat_compra` indexava/consultava só com `.strip().upper()`, então
    '0402002' (catálogo) × '402002' (planilha) não casavam → produto NULL.
    """
    actor = _actor()
    MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    proj = ProjetoFactory(nome="Proj X", fluxo="NAO_SUPER")
    p_zero = Produto.objects.create(codigo="0402002", nome="Produto Com Zero", projeto=proj)
    p_semzero = Produto.objects.create(codigo="507", nome="Produto Sem Zero", projeto=proj)
    rows = "\n".join(
        [
            # catálogo TEM zero, planilha SEM zero
            "Cidade X,CE,Proj X,402002,desc A,Professor,true,10,2026,2026-06-08",
            # catálogo SEM zero, planilha COM zeros
            "Cidade X,CE,Proj X,0000507,desc B,Professor,true,20,2026,2026-06-08",
            # SKU ausente do catálogo -> NULL (contado, não inventado)
            "Cidade X,CE,Proj X,999999,desc C,Professor,true,30,2026,2026-06-08",
        ]
    )
    r = ExportContractImporter(
        path=_write_export(tmp_path, {"dat_compra": f"{COMPRA_HEADER}\n{rows}\n"}),
        apply=True,
        allow=("dat_compra",),
        actor=actor,
    ).run()
    assert r["applied"]["dat_compra"] == 3
    by_desc = {c.descricao_produto: c for c in DATCompra.objects.all()}
    assert by_desc["desc A"].produto_id == p_zero.id  # 402002 -> 0402002 (RED: NULL hoje)
    assert by_desc["desc B"].produto_id == p_semzero.id  # 0000507 -> 507 (RED: NULL hoje)
    assert by_desc["desc C"].produto_id is None  # SKU ausente do catálogo


# ───────── RELAY-53, defeito C: quantidade com separador de milhar pt-BR ─────────
@pytest.mark.parametrize(
    ("bruto", "esperado"),
    [
        # Formatos medidos nos dat_compra.csv das 13 versões do export-contract (06/2026 a 09/2026):
        # inteiro puro (28.921 valores) e milhar com ponto (26: "1.000" e "4.619", em toda versão).
        ("41", 41),
        ("2026", 2026),
        ("1.000", 1000),  # TEMA 2 KIT DO ALUNO, Bom Jesus da Lapa (prod gravou 1)
        ("4.619", 4619),  # ACERTA BRASIL MATEMATICA KIT ALUNO, Contagem (prod gravou 4)
        ("12.345.678", 12345678),
        # O formato float que o parser antigo aceitava continua com o mesmo sentido.
        ("100.0", 100),
        ("", None),
        ("   ", None),
        ("abc", None),
        (None, None),
    ],
)
def test_parse_int_le_separador_de_milhar_pt_br(bruto, esperado):
    assert _parse_int(bruto) == esperado


def test_apply_dat_compra_quantidade_com_milhar_pt_br(tmp_path):
    actor = _actor()
    MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    ProjetoFactory(nome="Proj X", fluxo="NAO_SUPER")
    row = "Cidade X,CE,Proj X,115,TEMA 2 KIT DO ALUNO,Aluno,true,1.000,2026,2025-12-30"
    r = ExportContractImporter(
        path=_write_export(tmp_path, {"dat_compra": f"{COMPRA_HEADER}\n{row}\n"}),
        apply=True,
        allow=("dat_compra",),
        actor=actor,
    ).run()
    assert r["applied"]["dat_compra"] == 1
    assert DATCompra.objects.get().quantidade == 1000


# ───────── RELAY-53, defeito A: ano_uso não faz parte da identidade da compra ─────────
def _compra_catole(ano: str) -> str:
    return f"Catolé do Rocha,PB,Proj X,0602003,KIT CRIANCA,Aluno,true,150,{ano},2026-08-19"


def test_reimport_mesma_compra_com_ano_uso_diferente_nao_cria_copia(tmp_path):
    """Prod, 09 e 10/09: a 1ª carga gravou 42 compras de Catolé do Rocha com ano_uso vazio; a
    planilha passou a dizer "Usará a coleção em 2027" e a 2ª carga criou 42 cópias (6.004
    unidades contadas duas vezes), porque ano_uso fazia parte da NK. Agora a compra existente é
    reconhecida: o dry-run aponta a divergência (would_update) e o apply create-only não cria
    nem sobrescreve."""
    actor = _actor()
    MunicipioFactory(nome="Catolé do Rocha", uf="PB", ativo=True)
    ProjetoFactory(nome="Proj X", fluxo="NAO_SUPER")
    (tmp_path / "v1").mkdir()
    (tmp_path / "v2").mkdir()
    carga1 = _write_export(tmp_path / "v1", {"dat_compra": f"{COMPRA_HEADER_V12}\n{_compra_catole('')}\n"})
    carga2 = _write_export(tmp_path / "v2", {"dat_compra": f"{COMPRA_HEADER_V12}\n{_compra_catole('2027')}\n"})
    ExportContractImporter(path=carga1, apply=True, allow=("dat_compra",), actor=actor).run()

    t = ExportContractImporter(path=carga2).run()["por_entidade"]["dat_compra"]
    assert (t["would_create"], t["would_update"], t["would_skip_same"]) == (0, 1, 0)

    r = ExportContractImporter(path=carga2, apply=True, allow=("dat_compra",), actor=actor).run()
    assert r["applied"]["dat_compra"] == 0
    assert DATCompra.objects.count() == 1
    assert DATCompra.objects.get().ano_uso is None  # create-only: decisão humana na tela de compras


def test_classify_compra_existente_com_mesmo_ano_uso_e_skip(tmp_path):
    actor = _actor()
    MunicipioFactory(nome="Catolé do Rocha", uf="PB", ativo=True)
    ProjetoFactory(nome="Proj X", fluxo="NAO_SUPER")
    path = _write_export(tmp_path, {"dat_compra": f"{COMPRA_HEADER_V12}\n{_compra_catole('2027')}\n"})
    ExportContractImporter(path=path, apply=True, allow=("dat_compra",), actor=actor).run()
    t = ExportContractImporter(path=path).run()["por_entidade"]["dat_compra"]
    assert (t["would_create"], t["would_update"], t["would_skip_same"]) == (0, 0, 1)


# ───────── RELAY-53, rodada 3: o projeto faz parte da identidade da compra ─────────
def _superativar_5(tmp_path):
    """Duas compras distintas que só o projeto separa: Superativar MAT 5 e PORT 5, mesmo município,
    dia, tipo e quantidade (~50 pares assim na v32) e a mesma descrição (a planilha já troca as
    descrições Mat/Port em Atibaia e Mucambo). Devolve (path, actor)."""
    actor = _actor()
    MunicipioFactory(nome="Atibaia", uf="SP", ativo=True)
    ProjetoFactory(nome="SUPERATIVAR MATEMÁTICA 5", fluxo="NAO_SUPER")
    ProjetoFactory(nome="SUPERATIVAR LINGUAGENS 5", fluxo="NAO_SUPER")
    desc = "SUPER ATIVAR - LÍNGUA PORTUGUESA ( 5° ANO ) - KIT ALUNO"
    rows = "\n".join(
        [
            f"Atibaia,SP,SUPERATIVAR MATEMÁTICA 5,467,{desc},Aluno,true,2005,2026,2025-12-22",
            f"Atibaia,SP,SUPERATIVAR LINGUAGENS 5,469,{desc},Aluno,true,2005,2026,2025-12-22",
        ]
    )
    return _write_export(tmp_path, {"dat_compra": f"{COMPRA_HEADER_V12}\n{rows}\n"}), actor


def test_mat_5_e_port_5_na_mesma_carga_criam_2_compras(tmp_path):
    """Rodada 3 da revisão: sem o projeto na NK, a 2ª compra colapsava na 1ª em silêncio (dry-run
    dizia 2, o apply criava 1) e a falta voltava no dry-run seguinte como troca de projeto."""
    path, actor = _superativar_5(tmp_path)

    t = ExportContractImporter(path=path).run()["por_entidade"]["dat_compra"]
    assert (t["would_create"], t["would_reject"]) == (2, 0)

    r = ExportContractImporter(path=path, apply=True, allow=("dat_compra",), actor=actor).run()
    assert r["applied"]["dat_compra"] == 2
    assert sorted(DATCompra.objects.values_list("projeto__nome", flat=True)) == [
        "SUPERATIVAR LINGUAGENS 5",
        "SUPERATIVAR MATEMÁTICA 5",
    ]

    t2 = ExportContractImporter(path=path).run()["por_entidade"]["dat_compra"]
    assert (t2["would_create"], t2["would_skip_same"]) == (0, 2)


def test_projeto_renomeado_entre_versoes_aparece_como_would_create(tmp_path):
    """Decisão de 01/10: perda silenciosa é pior que cópia visível. Compra gravada sob o nome
    antigo do projeto ('TEMA') e trazida pela planilha sob o novo ('TEMA 1') é outra compra para o
    importer: o dry-run mostra would_create e o apply cria a cópia. Pré-condição do reimport
    (imports.spec.md): reconciliar o projeto no banco antes."""
    actor = _actor()
    mun = MunicipioFactory(nome="Catolé do Rocha", uf="PB", ativo=True)
    ProjetoFactory(nome="TEMA 1", fluxo="NAO_SUPER")
    DATCompra.objects.create(
        municipio=mun,
        projeto=ProjetoFactory(nome="TEMA", fluxo="NAO_SUPER"),
        descricao_produto="TEMA 1 - 3º ANO ALUNO",
        tipo="Aluno",
        quantidade=270,
        ano_uso=2026,
        data_compra=date(2026, 2, 20),
        created_by=actor,
    )
    row = "Catolé do Rocha,PB,TEMA 1,0108001,TEMA 1 - 3º ANO ALUNO,Aluno,true,270,2026,2026-02-20"
    path = _write_export(tmp_path, {"dat_compra": f"{COMPRA_HEADER_V12}\n{row}\n"})

    t = ExportContractImporter(path=path).run()["por_entidade"]["dat_compra"]
    assert (t["would_create"], t["would_update"], t["would_skip_same"]) == (1, 0, 0)

    r = ExportContractImporter(path=path, apply=True, allow=("dat_compra",), actor=actor).run()
    assert r["applied"]["dat_compra"] == t["would_create"]
    assert sorted(DATCompra.objects.values_list("projeto__nome", flat=True)) == ["TEMA", "TEMA 1"]


def test_compra_repetida_no_arquivo_dry_run_espelha_apply(tmp_path):
    """O apply grava só a 1ª linha de cada NK do arquivo. O dry-run tem de dizer o mesmo: a 2ª
    vira would_reject com motivo, e would_create é o número de compras que o apply cria."""
    actor = _actor()
    MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    ProjetoFactory(nome="Proj X", fluxo="NAO_SUPER")
    rows = "\n".join(
        [
            _compra_row(qtde=41, ano=2026),
            _compra_row(qtde=41, ano=2027),  # mesma NK (ano_uso fora da chave): o apply não grava
            _compra_row(qtde=41, ano=2026),  # linha repetida idêntica
            _compra_row(qtde=99),
        ]
    )
    path = _write_export(tmp_path, {"dat_compra": f"{COMPRA_HEADER}\n{rows}\n"})

    t = ExportContractImporter(path=path).run()["por_entidade"]["dat_compra"]
    assert (t["would_create"], t["would_reject"]) == (2, 2)
    assert t["reject_reasons"]["compra_repetida_no_arquivo"] == 2
    assert sum(t["reject_reasons"].values()) == t["would_reject"]

    r = ExportContractImporter(path=path, apply=True, allow=("dat_compra",), actor=actor).run()
    assert r["applied"]["dat_compra"] == t["would_create"]
    assert sorted(DATCompra.objects.values_list("quantidade", "ano_uso")) == [(41, 2026), (99, 2026)]


# ───────── RELAY-53, defeito D: linha rejeitada aparece com motivo ─────────
def _export_com_rejeitos(tmp_path) -> str:
    MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    ProjetoFactory(nome="Proj X", fluxo="NAO_SUPER")
    # Duas grafias que colapsam na mesma chave canônica (& <-> E) → ambíguo.
    ProjetoFactory(nome="Vida & Matemática 6", fluxo="NAO_SUPER")
    ProjetoFactory(nome="Vida E Matemática 6", fluxo="NAO_SUPER")
    rows = "\n".join(
        [
            _compra_row(),  # resolve → would_create
            _compra_row(projeto=""),  # 507/508 de Maringá: projeto vazio
            _compra_row(projeto="GESTÃO ESCOLAR 4"),  # variante fora do catálogo
            _compra_row(projeto="GESTÃO ESCOLAR 4", qtde=7),
            _compra_row(projeto="VIDA - E - MATEMATICA 6"),  # ambíguo
            _compra_row(municipio="Cidade Inexistente"),
        ]
    )
    return _write_export(tmp_path, {"dat_compra": f"{COMPRA_HEADER}\n{rows}\n"})


def test_classify_dat_compra_rejeito_tem_motivo_e_nome_do_projeto(tmp_path):
    t = ExportContractImporter(path=_export_com_rejeitos(tmp_path)).run()["por_entidade"]["dat_compra"]
    assert t["would_create"] == 1
    assert t["would_reject"] == 5
    assert t["reject_reasons"] == {
        "projeto_vazio": 1,
        "projeto_nao_resolvido": 2,
        "projeto_ambiguo": 1,
        "municipio_nao_resolvido": 1,
        "compra_repetida_no_arquivo": 0,
    }
    assert sum(t["reject_reasons"].values()) == t["would_reject"]
    assert t["projetos_nao_resolvidos"] == {"GESTÃO ESCOLAR 4": 2, "VIDA - E - MATEMATICA 6": 1}


def test_comando_texto_mostra_motivo_do_rejeito(tmp_path):
    out = StringIO()
    call_command("import_export_contract", "--path", _export_com_rejeitos(tmp_path), stdout=out)
    texto = out.getvalue()
    assert "projeto_nao_resolvido" in texto
    assert "GESTÃO ESCOLAR 4" in texto
