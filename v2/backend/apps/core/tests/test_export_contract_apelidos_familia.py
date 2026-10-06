"""
Apelidos de FAMÍLIA (ProjetoGeral) no import do export-contract — decisão do dono de 06/10/2026.

Catavento, Superativar, ACerta e Fluir das Emoções viram uma coleção cada, com nome curto. A planilha
continua mandando os nomes antigos ("PROJETO CATAVENTO 2", "SUPERATIVAR - LINGUAGENS", "ACERTA
MATEMÁTICA", "FLUIR DAS EMOÇÕES - 1"...). O importador resolve família pelo NOME: sem apelido, a carga
recriaria a família antiga (create-only por nome) e o dat_registro/dat_cadastro entrariam nela como
novos, com os códigos em dobro. Estes testes provam que o nome antigo cai na coleção nova e que nada é
recriado; e que o nome que existe continua vencendo o apelido (antes da junção o import não muda).

NÃO importa dados reais.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false

from __future__ import annotations

import json
from typing import Any

import pytest

from apps.core.models import DATCadastro, DATRegistro, Projeto, ProjetoGeral
from apps.core.services.export_contract_importer import ExportContractImporter
from apps.core.services.export_contract_projeto_resolver import (
    _PROJETO_GERAL_ALIASES,
    _norm,
    projeto_geral_index,
)
from apps.core.tests.factories import MunicipioFactory, ProjetoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

CAD_HEADER = (
    "municipio,municipio_norm,uf,projeto_geral,projeto_geral_norm,plataforma,"
    "etapa1_status,etapa1_data,etapa2_status,etapa2_data,etapa3_status,etapa3_data,"
    "etapa4_status,etapa4_data,variantes_qtd"
)
REG_HEADER = "municipio,uf,projeto_geral,projeto,aluno_qtde,professor_qtde"


def _write_export(tmp_path, files: dict[str, str]) -> str:
    d = tmp_path / "export"
    d.mkdir()
    manifest: dict[str, Any] = {"generated_at": "2026-10-06", "snapshot_date": "2026-10-05", "entities": {}}
    for name, content in files.items():
        (d / f"{name}.csv").write_text(content, encoding="utf-8")
        manifest["entities"][name] = {"file_csv": f"{name}.csv", "rows": max(content.strip().count("\n"), 0)}
    (d / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return str(d)


@pytest.fixture(autouse=True)
def _familias_ja_juntadas():
    """As migrações semeiam as famílias com os nomes antigos; aqui o banco fica como depois dos scripts
    de junção (as famílias antigas não existem). Cada teste cria a coleção nova de que precisa."""
    nomes = set(_PROJETO_GERAL_ALIASES) | {_norm(v) for v in _PROJETO_GERAL_ALIASES.values()}
    ids = [pk for pk, n in ProjetoGeral.objects.values_list("id", "nome") if _norm(n) in nomes]
    ProjetoGeral.objects.filter(id__in=ids).delete()


def _familias(*nomes: str) -> int:
    """Quantas famílias com estes nomes (normalizados) existem."""
    alvo = {_norm(n) for n in nomes}
    return sum(1 for n in ProjetoGeral.objects.values_list("nome", flat=True) if _norm(n) in alvo)


def _actor():
    return UsuarioFactory(username="u_apelido_familia", password="x", cpf="11144477735")


# ───────── a tabela ─────────
def test_tabela_de_apelidos_cobre_os_nomes_que_somem():
    esperado = {
        "PROJETO CATAVENTO 2": "Catavento",
        "PROJETO CATAVENTO 3": "Catavento",
        "SUPERATIVAR - LINGUAGENS": "Superativar",
        "SUPERATIVAR - MATEMATICA": "Superativar",
        "ACERTA MATEMATICA": "ACerta",
        "ACERTA PORTUGUES": "ACerta",
        "FLUIR DAS EMOCOES - 1": "Fluir das Emoções",
        "FLUIR DAS EMOCOES - 2": "Fluir das Emoções",
        "FLUIR DAS EMOCOES - 3": "Fluir das Emoções",
    }
    assert _PROJETO_GERAL_ALIASES == esperado
    # chave normalizada; alvo = nome EXATO da coleção unificada; um nome antigo vai para UMA coleção só
    assert all(_norm(k) == k for k in _PROJETO_GERAL_ALIASES)
    assert not {_norm(v) for v in _PROJETO_GERAL_ALIASES.values()} & set(_PROJETO_GERAL_ALIASES)


# ───────── o índice ─────────
def test_indice_manda_o_nome_antigo_para_a_colecao_nova():
    cat = ProjetoGeral.objects.create(nome="Catavento")
    idx = projeto_geral_index()
    assert idx["CATAVENTO"] == cat.id
    assert idx["PROJETO CATAVENTO 2"] == cat.id
    assert idx["PROJETO CATAVENTO 3"] == cat.id


def test_nome_que_existe_vence_o_apelido():
    # Antes da junção: a família antiga existe e continua resolvendo para ela mesma.
    cat = ProjetoGeral.objects.create(nome="Catavento")
    antiga = ProjetoGeral.objects.create(nome="PROJETO CATAVENTO 3")
    idx = projeto_geral_index()
    assert idx["PROJETO CATAVENTO 3"] == antiga.id
    assert idx["PROJETO CATAVENTO 2"] == cat.id


def test_fluir_antes_da_juncao_nao_vai_para_a_familia_antiga():
    # A família antiga do Fluir Antigo tem a mesma chave normalizada da coleção nova. Antes da junção (nome
    # antigo 'FLUIR DAS EMOÇÕES', regra nao_aplicavel) o apelido NÃO vale: Fluir 1/2/3 não caem nela.
    antiga = ProjetoGeral.objects.create(nome="FLUIR DAS EMOÇÕES", tipo_calculo_codigos="nao_aplicavel")
    idx = projeto_geral_index()
    assert idx["FLUIR DAS EMOCOES"] == antiga.id
    assert "FLUIR DAS EMOCOES - 1" not in idx
    # o script unificar_fluir.py renomeia para o nome exato da coleção: aí o apelido vale
    ProjetoGeral.objects.filter(pk=antiga.pk).update(nome="Fluir das Emoções", tipo_calculo_codigos="por_professor")
    assert projeto_geral_index()["FLUIR DAS EMOCOES - 1"] == antiga.id


def test_apelido_sem_alvo_nao_entra():
    idx = projeto_geral_index()
    assert "SUPERATIVAR - LINGUAGENS" not in idx


# ───────── projeto_geral: classify e apply não recriam ─────────
def test_carga_de_projeto_geral_nao_recria_familia_antiga(tmp_path):
    ProjetoGeral.objects.create(nome="Superativar", usa_avaliar=True)
    csv = (
        "nome,usa_avaliar,tipo_calculo_codigos,divisor_aluno,multiplicador_professor\n"
        "SUPERATIVAR - LINGUAGENS,true,professor_x_multiplicador,,1.1\n"
        "SUPERATIVAR - MATEMÁTICA,true,professor_x_multiplicador,,1.1\n"
    )
    path = _write_export(tmp_path, {"projeto_geral": csv})
    seco = ExportContractImporter(path=path).run()
    assert seco["por_entidade"]["projeto_geral"]["would_create"] == 0
    assert seco["por_entidade"]["projeto_geral"]["would_skip_same"] == 2
    r = ExportContractImporter(path=path, apply=True, allow=("projeto_geral",)).run()
    assert r["applied"]["projeto_geral"] == 0
    assert _familias("Superativar", "SUPERATIVAR - LINGUAGENS", "SUPERATIVAR - MATEMÁTICA") == 1


def test_carga_de_projeto_geral_casa_o_nome_sem_acento_e_caixa():
    pg = ProjetoGeral.objects.create(nome="Fluir das Emoções")
    assert projeto_geral_index()["FLUIR DAS EMOCOES"] == pg.id


def test_carga_de_projeto_geral_sem_acento_nao_cria_homonimo(tmp_path):
    ProjetoGeral.objects.create(nome="Fluir das Emoções")
    antes = ProjetoGeral.objects.count()
    csv = "nome,usa_avaliar\nFLUIR DAS EMOCOES,false\n"
    path = _write_export(tmp_path, {"projeto_geral": csv})
    r = ExportContractImporter(path=path, apply=True, allow=("projeto_geral",)).run()
    assert r["applied"]["projeto_geral"] == 0
    assert ProjetoGeral.objects.count() == antes


# ───────── dat_registro / dat_cadastro ─────────
def test_dat_registro_com_familia_antiga_cai_na_colecao_e_nao_duplica(tmp_path):
    actor = _actor()
    m1 = MunicipioFactory(nome="Cidade Um", uf="CE", ativo=True)
    MunicipioFactory(nome="Cidade Dois", uf="CE", ativo=True)
    acerta = ProjetoGeral.objects.create(nome="ACerta", usa_avaliar=True)
    mat = ProjetoFactory(nome="ACerta Matemática", projeto_geral=acerta)
    ProjetoFactory(nome="ACerta Português", projeto_geral=acerta)
    DATRegistro.objects.create(
        municipio=m1, projeto_geral=acerta, projeto=mat, ano=2026, aluno_qtde=10, professor_qtde=2, created_by=actor
    )
    csv = (
        f"{REG_HEADER}\n"
        "Cidade Um,CE,ACERTA MATEMATICA,ACERTA MATEMATICA,10,2\n"  # existe: pula
        "Cidade Dois,CE,ACERTA PORTUGUES,ACERTA PORTUGUES,20,3\n"  # novo: entra na coleção ACerta
    )
    path = _write_export(tmp_path, {"dat_registro": csv})
    seco = ExportContractImporter(path=path).run()["por_entidade"]["dat_registro"]
    assert (seco["would_create"], seco["would_skip_same"], seco["would_reject"]) == (1, 1, 0)
    r = ExportContractImporter(path=path, apply=True, allow=("dat_registro",), actor=actor).run()
    assert r["applied"]["dat_registro"] == 1
    assert DATRegistro.objects.count() == 2
    assert set(DATRegistro.objects.values_list("projeto_geral_id", flat=True)) == {acerta.id}
    assert _familias("ACerta", "ACERTA MATEMÁTICA", "ACERTA PORTUGUÊS") == 1


def test_dat_cadastro_com_familia_antiga_cai_na_colecao(tmp_path):
    actor = _actor()
    MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    cat = ProjetoGeral.objects.create(nome="Catavento")
    csv = (
        f"{CAD_HEADER}\n"
        "Cidade X,CIDADE X,CE,PROJETO CATAVENTO 2,PROJETO CATAVENTO 2,FORMAR,concluido,2026-03-01,,,,,,,1\n"
        "Cidade X,CIDADE X,CE,PROJETO CATAVENTO 3,PROJETO CATAVENTO 3,FORMAR,concluido,2026-03-01,,,,,,,1\n"
    )
    path = _write_export(tmp_path, {"dat_cadastro": csv})
    r = ExportContractImporter(path=path, apply=True, allow=("dat_cadastro",), actor=actor).run()
    assert r["applied"]["dat_cadastro"] == 1  # a 2ª linha repetida da planilha é a mesma chave: pula
    assert DATCadastro.objects.get().projeto_geral_id == cat.id


# ───────── projeto novo declarando família antiga ─────────
def test_serie_nova_com_familia_antiga_nasce_na_colecao(tmp_path):
    sup = ProjetoGeral.objects.create(nome="Superativar")
    csv = "projeto,projeto_geral,fluxo\nSUPERATIVAR - MATEMÁTICA 6,SUPERATIVAR - MATEMÁTICA,NAO_SUPER\n"
    path = _write_export(tmp_path, {"projeto": csv})
    r = ExportContractImporter(path=path, apply=True, allow=("projeto",)).run()
    assert r["applied"]["projeto"] == 1
    p = Projeto.objects.get(nome="SUPERATIVAR - MATEMÁTICA 6")
    assert p.projeto_geral_id == sup.id
    assert p.eh_serie is True


# ───────── linhas que colapsam na mesma chave: classify conta como o apply ─────────
def test_dat_cadastro_linhas_que_colapsam_contam_uma_vez_e_divergencia_aparece(tmp_path):
    actor = _actor()
    MunicipioFactory(nome="Cidade Y", uf="PR", ativo=True)
    ProjetoGeral.objects.create(nome="Fluir das Emoções", tipo_calculo_codigos="por_professor")
    csv = (
        f"{CAD_HEADER}\n"
        "Cidade Y,CIDADE Y,PR,FLUIR DAS EMOÇÕES - 1,X,FORMAR,concluido,2026-03-01,concluido,2026-03-05,,,,,1\n"
        "Cidade Y,CIDADE Y,PR,FLUIR DAS EMOÇÕES - 2,X,FORMAR,concluido,2026-03-01,concluido,2026-03-09,,,,,1\n"
        "Cidade Y,CIDADE Y,PR,FLUIR DAS EMOÇÕES - 3,X,FORMAR,concluido,2026-03-01,concluido,2026-03-05,,,,,1\n"
    )
    path = _write_export(tmp_path, {"dat_cadastro": csv})
    seco = ExportContractImporter(path=path).run()["por_entidade"]["dat_cadastro"]
    assert seco["would_create"] == 1
    assert seco["reject_reasons"]["repetida_no_arquivo"] == 2
    assert seco["repetidas_divergentes"] == ["CIDADE Y/PR | Fluir das Emoções | FORMAR | 2026"]
    r = ExportContractImporter(path=path, apply=True, allow=("dat_cadastro",), actor=actor).run()
    assert r["applied"]["dat_cadastro"] == seco["would_create"] == 1


def test_dat_registro_linha_repetida_conta_uma_vez(tmp_path):
    actor = _actor()
    MunicipioFactory(nome="Cidade Z", uf="CE", ativo=True)
    acerta = ProjetoGeral.objects.create(nome="ACerta", usa_avaliar=True)
    ProjetoFactory(nome="ACerta Português", projeto_geral=acerta)
    csv = (
        f"{REG_HEADER}\n"
        "Cidade Z,CE,ACERTA PORTUGUES,ACERTA PORTUGUES,20,3\n"
        "Cidade Z,CE,ACERTA PORTUGUES,ACERTA PORTUGUES,25,3\n"
    )
    path = _write_export(tmp_path, {"dat_registro": csv})
    seco = ExportContractImporter(path=path).run()["por_entidade"]["dat_registro"]
    assert seco["would_create"] == 1
    assert seco["reject_reasons"]["repetida_no_arquivo"] == 1
    assert seco["repetidas_divergentes"] == ["CIDADE Z/CE | ACerta | ACerta Português"]
    r = ExportContractImporter(path=path, apply=True, allow=("dat_registro",), actor=actor).run()
    assert r["applied"]["dat_registro"] == seco["would_create"] == 1


def test_projeto_mesma_variante_repetida_conta_uma_vez(tmp_path):
    ProjetoGeral.objects.create(nome="Superativar")
    csv = (
        "projeto,projeto_geral,fluxo\n"
        "SUPERATIVAR - MATEMÁTICA 7,SUPERATIVAR - MATEMÁTICA,NAO_SUPER\n"
        "Superativar Matemática 7,SUPERATIVAR - MATEMÁTICA,NAO_SUPER\n"
    )
    path = _write_export(tmp_path, {"projeto": csv})
    seco = ExportContractImporter(path=path).run()["por_entidade"]["projeto"]
    assert seco["would_create"] == 1
    assert seco["reject_reasons"]["repetido_no_arquivo"] == 1
    r = ExportContractImporter(path=path, apply=True, allow=("projeto",)).run()
    assert r["applied"]["projeto"] == seco["would_create"] == 1
