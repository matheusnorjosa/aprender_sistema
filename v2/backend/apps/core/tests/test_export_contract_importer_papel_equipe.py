"""
Papel EQUIPE ("Equipe administrativa") no import_export_contract (`equipe_gerencia` e `usuario`).

O #2094 criou o papel no vínculo `EquipeGerencia` e o form de Usuários o grava. O export-contract
precisa aceitar a mesma linha com o MESMO efeito do form: vínculo gravado e nada mais. Pelo
importador o papel EQUIPE nunca dá grupo (nem de setor, nem de função) e nunca abre escopo; o
vínculo aprovador (GERENTE na Superintendência) continua barrado como antes.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false

from __future__ import annotations

import json
from typing import Any

from django.contrib.auth.models import Group

import pytest

from apps.core.models import EquipeGerencia, Gerencia, Usuario
from apps.core.rbac.helpers import user_is_gerente_superintendencia
from apps.core.services.export_contract_importer import ExportContractImporter
from apps.core.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db

_CPF = "10000005673"


@pytest.fixture
def super_g() -> Gerencia:
    gerencia, _ = Gerencia.objects.get_or_create(nome="SUPERINTENDENCIA", defaults={"nome_setor": "Super"})
    return gerencia


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
    for g in ("Coordenador", "Formador", "Gerente", "Apoio de Coordenação", "Controle", "DAT"):
        Group.objects.get_or_create(name=g)


@pytest.mark.parametrize("rotulo", ["EQUIPE", "Equipe administrativa"])
def test_classify_conta_equipe_como_would_create(tmp_path, rotulo):
    Gerencia.objects.create(nome="GERENCIA CONTROLE", nome_setor="Controle")
    UsuarioFactory(cpf=_CPF)
    path = _export(tmp_path, {"equipe_gerencia": f"gerencia,usuario_cpf,papel\nControle,{_CPF},{rotulo}\n"})

    pe = ExportContractImporter(path=path).run()["por_entidade"]["equipe_gerencia"]

    assert pe["would_create"] == 1
    assert pe["would_reject"] == 0


def test_apply_grava_vinculo_equipe_sem_grupo_e_sem_escopo(tmp_path):
    _seed_grupos()
    g = Gerencia.objects.create(nome="GERENCIA CONTROLE", nome_setor="Controle")
    u = UsuarioFactory(cpf=_CPF)
    assert u.groups.count() == 0
    path = _export(tmp_path, {"equipe_gerencia": f"gerencia,usuario_cpf,papel\nControle,{_CPF},EQUIPE\n"})

    report = ExportContractImporter(path=path, apply=True, allow=("equipe_gerencia",)).run()

    assert report["applied"]["equipe_gerencia"] == 1
    v = EquipeGerencia.objects.get(gerencia=g, usuario=u, papel="EQUIPE")
    assert v.ativo is True and v.valid_to is None
    u.refresh_from_db()
    assert u.groups.count() == 0, "EQUIPE pelo importador não dá grupo de setor nem de função"
    assert not EquipeGerencia.vigentes_com_escopo_em().filter(usuario=u).exists(), "EQUIPE não abre escopo"


def test_apply_equipe_nao_mexe_nos_grupos_que_a_pessoa_ja_tem(tmp_path):
    _seed_grupos()
    Gerencia.objects.create(nome="GERENCIA CONTROLE", nome_setor="Controle")
    u = UsuarioFactory(cpf=_CPF, groups=["Formador"])
    antes = set(u.groups.values_list("name", flat=True))
    path = _export(tmp_path, {"equipe_gerencia": f"gerencia,usuario_cpf,papel\nControle,{_CPF},EQUIPE\n"})

    ExportContractImporter(path=path, apply=True, allow=("equipe_gerencia",)).run()

    assert set(u.groups.values_list("name", flat=True)) == antes


def test_equipe_na_superintendencia_grava_mas_nao_aprova_e_gerente_segue_barrado(tmp_path, super_g):
    u = UsuarioFactory(cpf=_CPF)
    csv = f"gerencia,usuario_cpf,papel\nSuper,{_CPF},EQUIPE\nSuper,{_CPF},GERENTE\n"
    path = _export(tmp_path, {"equipe_gerencia": csv})

    pe = ExportContractImporter(path=path).run()["por_entidade"]["equipe_gerencia"]
    assert pe["would_create"] == 1
    assert pe["reject_reasons"]["vinculo_aprovador_bloqueado"] == 1

    report = ExportContractImporter(path=path, apply=True, allow=("equipe_gerencia",)).run()

    assert report["applied"]["equipe_gerencia"] == 1
    assert set(EquipeGerencia.objects.filter(usuario=u).values_list("papel", flat=True)) == {"EQUIPE"}
    assert user_is_gerente_superintendencia(u) is False
    assert u.groups.count() == 0


def test_apply_equipe_e_idempotente(tmp_path):
    Gerencia.objects.create(nome="GERENCIA CONTROLE", nome_setor="Controle")
    UsuarioFactory(cpf=_CPF)
    path = _export(tmp_path, {"equipe_gerencia": f"gerencia,usuario_cpf,papel\nControle,{_CPF},EQUIPE\n"})

    ExportContractImporter(path=path, apply=True, allow=("equipe_gerencia",)).run()
    ExportContractImporter(path=path, apply=True, allow=("equipe_gerencia",)).run()

    assert EquipeGerencia.objects.filter(papel="EQUIPE").count() == 1


@pytest.mark.parametrize("vinculo_ja_existe", [False, True])
def test_linha_equipe_nao_reescreve_setor_canonico_da_gerencia(tmp_path, vinculo_ja_existe):
    """setor_canonico é eixo de escopo (user_setores compara com Projeto.setor): uma linha EQUIPE,
    inerte por definição, não pode reescrevê-lo, nem quando o vínculo já existe."""
    g = Gerencia.objects.create(nome="GERENCIA CONTROLE", nome_setor="Controle", setor_canonico="Controle")
    u = UsuarioFactory(cpf=_CPF)
    if vinculo_ja_existe:
        EquipeGerencia.objects.create(gerencia=g, usuario=u, papel="EQUIPE", ativo=True)
    csv = f"gerencia,usuario_cpf,papel,setor_canonico\nControle,{_CPF},EQUIPE,Vidas\n"
    path = _export(tmp_path, {"equipe_gerencia": csv})

    ExportContractImporter(path=path, apply=True, allow=("equipe_gerencia",)).run()

    g.refresh_from_db()
    assert g.setor_canonico == "Controle"
    assert EquipeGerencia.objects.filter(gerencia=g, usuario=u, papel="EQUIPE").count() == 1


def test_usuario_so_com_equipe_nasce_sem_grupo_mesmo_com_cargo(tmp_path):
    """Usuário novo cujo único papel no export é EQUIPE: nenhum grupo, e o `cargo` não entra como
    fallback (o papel do export é a fonte primária e EQUIPE não tem grupo)."""
    _seed_grupos()
    path = _export(
        tmp_path,
        {
            "usuario": "nome_completo,cpf,email,cargo\nBia,11144477735,,Coordenadores\n",
            "equipe_gerencia": "gerencia,usuario_cpf,papel\nControle,11144477735,EQUIPE\n",
        },
    )

    ExportContractImporter(path=path, apply=True, allow=("usuario",)).run()

    assert Usuario.objects.get(cpf="11144477735").groups.count() == 0


@pytest.mark.parametrize(
    "linhas",
    [
        ["Controle,11144477735,EQUIPE", "Vidas,11144477735,FORMADOR"],
        ["Vidas,11144477735,FORMADOR", "Controle,11144477735,EQUIPE"],
    ],
    ids=["equipe_antes", "formador_antes"],
)
def test_usuario_novo_com_equipe_e_funcao_nasce_com_o_grupo_da_funcao(tmp_path, linhas):
    """Pessoa em duas linhas, EQUIPE e FORMADOR: o papel de função vence EQUIPE nas duas ordens.
    Antes valia a 1ª linha, e com EQUIPE primeiro a pessoa nascia sem grupo."""
    _seed_grupos()
    path = _export(
        tmp_path,
        {
            "usuario": "nome_completo,cpf,email,cargo\nBia,11144477735,,\n",
            "equipe_gerencia": "gerencia,usuario_cpf,papel\n" + "\n".join(linhas) + "\n",
        },
    )

    ExportContractImporter(path=path, apply=True, allow=("usuario",)).run()

    assert set(Usuario.objects.get(cpf="11144477735").groups.values_list("name", flat=True)) == {"Formador"}


def test_usuario_novo_com_duas_funcoes_fica_com_a_primeira(tmp_path):
    """Entre duas funções diferentes não há regra nova: vale a 1ª linha, como antes."""
    _seed_grupos()
    path = _export(
        tmp_path,
        {
            "usuario": "nome_completo,cpf,email,cargo\nBia,11144477735,,\n",
            "equipe_gerencia": "gerencia,usuario_cpf,papel\nVidas,11144477735,COORDENADOR\nVidas,11144477735,FORMADOR\n",
        },
    )

    ExportContractImporter(path=path, apply=True, allow=("usuario",)).run()

    assert set(Usuario.objects.get(cpf="11144477735").groups.values_list("name", flat=True)) == {"Coordenador"}


def test_usuario_existente_nao_muda_de_grupo_pela_regra_da_funcao(tmp_path):
    _seed_grupos()
    u = UsuarioFactory(cpf="11144477735")
    path = _export(
        tmp_path,
        {
            "usuario": "nome_completo,cpf,email,cargo\nBia,11144477735,,\n",
            "equipe_gerencia": "gerencia,usuario_cpf,papel\nControle,11144477735,EQUIPE\nVidas,11144477735,FORMADOR\n",
        },
    )

    ExportContractImporter(path=path, apply=True, allow=("usuario",)).run()

    assert u.groups.count() == 0


@pytest.mark.parametrize("com_gerencia_no_banco", [True, False], ids=["super_existe", "super_ainda_nao_existe"])
@pytest.mark.parametrize(
    "linhas",
    [
        ["Super,11144477735,EQUIPE", "Super,11144477735,GERENTE"],
        ["Super,11144477735,GERENTE", "Super,11144477735,EQUIPE"],
    ],
    ids=["equipe_antes", "gerente_antes"],
)
def test_linha_barrada_no_vinculo_nao_da_o_grupo_da_funcao(tmp_path, linhas, com_gerencia_no_banco):
    """A linha GERENTE na Superintendência é barrada no `equipe_gerencia` (anti-escalada, PR B1). O
    papel dela não pode dar ao usuário novo o grupo Gerente: só a linha que o vínculo aceita conta, e o
    EQUIPE que sobra não dá grupo. Vale também quando a gerência ainda não existe (o apply a criaria)."""
    _seed_grupos()
    if com_gerencia_no_banco:
        Gerencia.objects.create(nome="SUPERINTENDENCIA", nome_setor="Super")
    path = _export(
        tmp_path,
        {
            "usuario": "nome_completo,cpf,email,cargo\nBia,11144477735,,\n",
            "equipe_gerencia": "gerencia,usuario_cpf,papel\n" + "\n".join(linhas) + "\n",
        },
    )

    ExportContractImporter(path=path, apply=True, allow=("usuario", "equipe_gerencia")).run()

    u = Usuario.objects.get(cpf="11144477735")
    assert u.groups.count() == 0
    assert set(EquipeGerencia.objects.filter(usuario=u).values_list("papel", flat=True)) == {"EQUIPE"}


def test_linha_de_funcao_sem_gerencia_nao_da_grupo(tmp_path):
    """Linha FORMADOR com a gerência vazia: o `equipe_gerencia` a recusa, então ela não define o papel."""
    _seed_grupos()
    path = _export(
        tmp_path,
        {
            "usuario": "nome_completo,cpf,email,cargo\nBia,11144477735,,\n",
            "equipe_gerencia": "gerencia,usuario_cpf,papel\nControle,11144477735,EQUIPE\n,11144477735,FORMADOR\n",
        },
    )

    ExportContractImporter(path=path, apply=True, allow=("usuario",)).run()

    assert Usuario.objects.get(cpf="11144477735").groups.count() == 0
