"""
IMP-1 — o import_export_contract acha a gerência da linha e nunca a cria (decisões do dono, 14/10).

- `equipe_gerencia` nunca cria gerência; a linha cuja gerência não resolve não grava vínculo.
- "Vidas L", "Vidas M", "Vidas C" e "Avançando Juntos" são a gerência Vidas.
- "Outros" não lota ninguém (`setor_sem_lotacao`).
- Gerência inexistente (`gerencia_inexistente`) ou inativa (`gerencia_inativa`) não recebe vínculo.
- `Gerencia.setor_canonico` já preenchido não é reescrito pela linha.
- Usuário novo cujas linhas de equipe não acham gerência nasce sem grupo (nem o do `cargo`).
- O classify rejeita com o motivo; `produto` e `gerencia` aparecem como "só leitura, não grava".

Fixtures sintéticas: CPFs de teste com DV válido, sem dado real.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false

from __future__ import annotations

import json
from io import StringIO
from typing import Any

from django.contrib.auth.models import Group
from django.core.management import call_command

import pytest

from apps.core.models import EquipeGerencia, Gerencia, Usuario
from apps.core.services.export_contract_importer import ExportContractImporter, _gerencia_da_linha
from apps.core.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db

_CPF = "11144477735"
_GRUPOS_DE_PODER = ("Gerente", "Coordenador", "Apoio de Coordenação")


@pytest.fixture
def vidas() -> Gerencia:
    return Gerencia.objects.create(nome="GERENCIA 2", nome_setor="Vidas")


def _export(tmp_path, files: dict[str, str]) -> str:
    d = tmp_path / "export"
    d.mkdir()
    manifest: dict[str, Any] = {"entities": {}}
    for name, content in files.items():
        (d / f"{name}.csv").write_text(content, encoding="utf-8")
        manifest["entities"][name] = {"file_csv": f"{name}.csv"}
    (d / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return str(d)


def _seed_grupos() -> None:
    for g in ("Coordenador", "Formador", "Gerente", "Apoio de Coordenação"):
        Group.objects.get_or_create(name=g)


def _equipe(*linhas: str) -> str:
    return "gerencia,usuario_cpf,papel,setor_canonico\n" + "\n".join(linhas) + "\n"


@pytest.mark.parametrize("rotulo", ["Vidas L", "Vidas M", "Vidas C", "Avançando Juntos"])
def test_rotulos_da_vidas_lotam_na_vidas_sem_criar_gerencia(tmp_path, vidas, rotulo):
    u = UsuarioFactory(cpf=_CPF)
    antes = Gerencia.objects.count()
    path = _export(tmp_path, {"equipe_gerencia": _equipe(f"{rotulo},{_CPF},FORMADOR,Vidas")})

    pe = ExportContractImporter(path=path).run()["por_entidade"]["equipe_gerencia"]
    assert (pe["would_create"], pe["would_reject"]) == (1, 0)

    report = ExportContractImporter(path=path, apply=True, allow=("equipe_gerencia",)).run()

    assert report["applied"]["equipe_gerencia"] == 1
    assert EquipeGerencia.objects.filter(gerencia=vidas, usuario=u, papel="FORMADOR").exists()
    assert Gerencia.objects.count() == antes, "a linha nunca cria gerência"


def test_rotulo_igual_ao_nome_setor_do_banco_acha_a_gerencia(tmp_path):
    """O de-para leva "Brincando" a "Brincando e Aprendendo", mas o catálogo guarda nome_setor "Brincando"
    (GERENCIA 5). A linha acha a gerência pelo rótulo cru em vez de cair em `gerencia_inexistente`."""
    g = Gerencia.objects.create(nome="GERENCIA 5", nome_setor="Brincando")
    u = UsuarioFactory(cpf=_CPF)
    antes = Gerencia.objects.count()
    path = _export(tmp_path, {"equipe_gerencia": _equipe(f"Brincando,{_CPF},FORMADOR,Brincando")})

    report = ExportContractImporter(path=path, apply=True, allow=("equipe_gerencia",)).run()

    assert report["applied"]["equipe_gerencia"] == 1
    assert EquipeGerencia.objects.filter(gerencia=g, usuario=u, papel="FORMADOR").exists()
    assert Gerencia.objects.count() == antes


@pytest.mark.parametrize(
    ("rotulo", "inativa", "motivo"),
    [
        ("Outros", False, "setor_sem_lotacao"),
        ("OUTROS", False, "setor_sem_lotacao"),
        ("Setor Que Nao Existe", False, "gerencia_inexistente"),
        ("Fechada", True, "gerencia_inativa"),
    ],
    ids=["outros", "outros_maiusculo", "inexistente", "inativa"],
)
def test_gerencia_nao_resolvida_rejeita_com_motivo_e_nao_grava(tmp_path, rotulo, inativa, motivo):
    if inativa:
        Gerencia.objects.create(nome="GERENCIA FECHADA", nome_setor="Fechada", ativo=False)
    UsuarioFactory(cpf=_CPF)
    antes = Gerencia.objects.count()
    path = _export(tmp_path, {"equipe_gerencia": _equipe(f"{rotulo},{_CPF},FORMADOR,Vidas")})

    pe = ExportContractImporter(path=path).run()["por_entidade"]["equipe_gerencia"]
    assert (pe["would_create"], pe["would_reject"]) == (0, 1)
    assert pe["reject_reasons"][motivo] == 1

    report = ExportContractImporter(path=path, apply=True, allow=("equipe_gerencia",)).run()

    assert report["applied"]["equipe_gerencia"] == 0
    assert not EquipeGerencia.objects.exists()
    assert Gerencia.objects.count() == antes, "gerência não resolvida não é criada"


def test_outros_nao_lota_mesmo_com_gerencia_outros_ativa_no_catalogo(tmp_path):
    """A guarda de "Outros" vem antes da busca no catálogo: uma gerência "Outros" ativa (sobra de carga
    antiga) não recebe o vínculo."""
    Gerencia.objects.create(nome="GERENCIA OUTROS", nome_setor="Outros", ativo=True)
    UsuarioFactory(cpf=_CPF)
    path = _export(tmp_path, {"equipe_gerencia": _equipe(f"Outros,{_CPF},COORDENADOR,Outros")})

    pe = ExportContractImporter(path=path).run()["por_entidade"]["equipe_gerencia"]
    assert (pe["would_create"], pe["would_reject"]) == (0, 1)
    assert pe["reject_reasons"]["setor_sem_lotacao"] == 1

    report = ExportContractImporter(path=path, apply=True, allow=("equipe_gerencia",)).run()

    assert report["applied"]["equipe_gerencia"] == 0
    assert not EquipeGerencia.objects.exists()


@pytest.mark.parametrize(
    ("rotulo", "esperada"),
    [
        ("Vidas L", "GERENCIA 2"),
        ("Vidas l", "GERENCIA 2"),
        ("VIDAS L", "GERENCIA 2"),
        ("vidas m", "GERENCIA 2"),
        ("VIDAS C", "GERENCIA 2"),
        ("Avançando Juntos", "GERENCIA 2"),
        ("AVANÇANDO JUNTOS", "GERENCIA 2"),
        ("Avançando juntos", "GERENCIA 2"),
        ("Avancando Juntos", "GERENCIA 2"),
        ("AVANCANDO JUNTOS", "GERENCIA 2"),
        ("Brincando", "GERENCIA BRINCANDO"),
        ("brincando", "GERENCIA BRINCANDO"),
        ("BRINCANDO", "GERENCIA BRINCANDO"),
    ],
)
def test_rotulo_em_outra_grafia_vai_para_a_gerencia_ativa(rotulo, esperada):
    """O de-para ignora maiúscula e acento: com as gerências antigas inativas ainda no catálogo (retrato
    de prod), outra grafia do rótulo não cai nelas e não vira `gerencia_inativa`."""
    for nome, nome_setor, ativo in (
        ("GERENCIA 2", "Vidas", True),
        ("GERENCIA 5", "Brincando", False),
        ("GERENCIA VIDAS L", "Vidas L", False),
        ("GERENCIA VIDAS M", "Vidas M", False),
        ("GERENCIA BRINCANDO", "Brincando e Aprendendo", True),
        ("GERENCIA AVANCANDO JUNTOS", "Avançando Juntos", False),
        ("GERENCIA VIDAS C", "Vidas C", False),
    ):
        Gerencia.objects.create(nome=nome, nome_setor=nome_setor, ativo=ativo)

    gerencia, motivo = _gerencia_da_linha(rotulo)

    assert motivo == ""
    assert gerencia is not None and gerencia.nome == esperada


def test_setor_canonico_ja_preenchido_nao_e_sobrescrito(tmp_path):
    """Avançando Juntos é a Vidas: a linha dele não pode reescrever o setor da Vidas (eixo de escopo)."""
    g = Gerencia.objects.create(nome="GERENCIA 2", nome_setor="Vidas", setor_canonico="Vidas")
    u = UsuarioFactory(cpf=_CPF)
    path = _export(tmp_path, {"equipe_gerencia": _equipe(f"Avançando Juntos,{_CPF},COORDENADOR,Outro Setor")})

    ExportContractImporter(path=path, apply=True, allow=("equipe_gerencia",)).run()

    g.refresh_from_db()
    assert g.setor_canonico == "Vidas"
    assert EquipeGerencia.objects.filter(gerencia=g, usuario=u, papel="COORDENADOR").exists()


@pytest.mark.parametrize(
    ("rotulo", "inativa"),
    [("Outros", False), ("Setor Que Nao Existe", False), ("Fechada", True)],
    ids=["outros", "inexistente", "inativa"],
)
def test_usuario_so_em_gerencia_nao_resolvida_nasce_sem_grupo(tmp_path, rotulo, inativa):
    """Linha 93 do v38: só em Outros, como COORDENADOR, e com cargo de coordenador. Sem gerência a linha
    não dá papel, e o `cargo` também não entra (o CPF está no export de equipe)."""
    _seed_grupos()
    if inativa:
        Gerencia.objects.create(nome="GERENCIA FECHADA", nome_setor="Fechada", ativo=False)
    path = _export(
        tmp_path,
        {
            "usuario": f"nome_completo,cpf,email,cargo\nPessoa Teste,{_CPF},,Coordenadores\n",
            "equipe_gerencia": _equipe(f"{rotulo},{_CPF},COORDENADOR,"),
        },
    )

    ExportContractImporter(path=path, apply=True, allow=("usuario",)).run()

    assert Usuario.objects.get(cpf=_CPF).groups.count() == 0


def test_classify_gerencia_rejeita_o_que_nao_resolve_e_nunca_cria(tmp_path, vidas):
    Gerencia.objects.create(nome="GERENCIA FECHADA", nome_setor="Fechada", ativo=False)
    csv = (
        "nome,nome_setor\n"
        "Vidas,Vidas\n"
        "Vidas L,Vidas L\n"
        "Avançando Juntos,Avançando Juntos\n"
        "Outros,Outros\n"
        "Setor Novo,Setor Novo\n"
        "Fechada,Fechada\n"
        "-,-\n"
    )
    pe = ExportContractImporter(path=_export(tmp_path, {"gerencia": csv})).run()["por_entidade"]["gerencia"]

    assert pe["would_skip_same"] == 3
    assert pe["would_create"] == 0, "o import não cria gerência"
    assert pe["would_reject"] == 4
    assert pe["reject_reasons"] == {"setor_sem_lotacao": 1, "gerencia_inexistente": 1, "gerencia_inativa": 1}


def test_produto_e_gerencia_marcados_so_leitura_no_relatorio(tmp_path):
    path = _export(
        tmp_path,
        {
            "produto": "codigo,nome\nSKU-1,Livro\n",
            "gerencia": "nome,nome_setor\nVidas,Vidas\n",
            "tipo_evento": "nome,cor\nFormação,#000000\n",
        },
    )

    pe = ExportContractImporter(path=path).run()["por_entidade"]

    assert pe["produto"]["nota"] == "só leitura, não grava"
    assert pe["gerencia"]["nota"] == "só leitura, não grava"
    assert "nota" not in pe["tipo_evento"]

    out = StringIO()
    call_command("import_export_contract", "--path", path, stdout=out)
    linhas = {ln.split("]")[0].strip(): ln for ln in out.getvalue().splitlines() if ln.strip().startswith("[")}
    assert "só leitura, não grava" in linhas["[produto"]
    assert "só leitura, não grava" in linhas["[gerencia"]
    assert "só leitura" not in linhas["[tipo_evento"]


def test_apply_de_equipe_e_usuario_nao_cria_gerencia_nem_grupo_de_poder(tmp_path, vidas):
    """Prova de poder do IMP-1: cenário com Outros, Vidas L e Avançando Juntos. Antes, Outros e Vidas L
    criavam gerência e o usuário só em Outros nascia Coordenador pelo papel da linha."""
    _seed_grupos()
    Gerencia.objects.create(nome="GERENCIA FECHADA", nome_setor="Fechada", ativo=False)
    ger_antes = set(Gerencia.objects.values_list("id", "nome", "nome_setor", "ativo"))
    so_outros, vidas_l, aj, inativa = "33366699957", "44477700083", "55588811194", "66699922203"
    usuarios = (
        "nome_completo,cpf,email,cargo\n"
        f"Pessoa Um,{so_outros},,Coordenadores\n"
        f"Pessoa Dois,{vidas_l},,Gerentes\n"
        f"Pessoa Tres,{aj},,Gerentes\n"
        f"Pessoa Quatro,{inativa},,Coordenadores\n"
    )
    equipe = _equipe(
        f"Outros,{so_outros},COORDENADOR,Superintendência",
        f"Vidas L,{vidas_l},FORMADOR,Vidas",
        f"Avançando Juntos,{aj},Equipe administrativa,Vidas",
        f"Fechada,{inativa},GERENTE,",
    )
    path = _export(tmp_path, {"usuario": usuarios, "equipe_gerencia": equipe})

    report = ExportContractImporter(path=path, apply=True, allow=("usuario", "equipe_gerencia")).run()

    assert report["applied"] == {"usuario": 4, "equipe_gerencia": 2}
    assert set(Gerencia.objects.values_list("id", "nome", "nome_setor", "ativo")) == ger_antes, "0 gerências novas"
    vidas.refresh_from_db()
    assert vidas.setor_canonico == "Vidas", "vem da linha Vidas L; a linha Outros não escreve setor"
    poder = Usuario.objects.filter(cpf__in=(so_outros, vidas_l, aj, inativa), groups__name__in=_GRUPOS_DE_PODER)
    assert not poder.exists(), "nenhum grupo de poder nasce do cenário"
    assert set(Usuario.objects.get(cpf=vidas_l).groups.values_list("name", flat=True)) == {"Formador"}
    assert set(EquipeGerencia.objects.values_list("gerencia_id", "papel")) == {
        (vidas.id, "FORMADOR"),
        (vidas.id, "EQUIPE"),
    }
