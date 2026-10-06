"""
Papel EQUIPE ("Equipe administrativa") no vínculo `EquipeGerencia` (decisão do dono, 05/10/2026).

Diz só "trabalha neste setor": serve para a equipe de suporte do DAT, o Controle e outros setores.
Não entra em lista de formadores/coordenadores, na Grade Mensal, no tier de gestor, na aprovação,
nem gera grupo RBAC. Vale como setor da pessoa onde o sistema lê o setor pelo vínculo (`user_setores`).
O formulário de Usuários põe e tira o papel pelo campo `equipe_administrativa`; salvar sem mudar
nada mantém o vínculo (regra do #2071/#2072).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportIndexIssue=false, reportUnusedFunction=false, reportPrivateUsage=false

from __future__ import annotations

import itertools
import tempfile
from pathlib import Path

from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.core.models import EquipeGerencia, Gerencia, Usuario
from apps.core.rbac.helpers import GERENCIA_APROVADORA_NOME, user_is_gerente_superintendencia
from apps.core.services.equipe_gerencia_import import import_equipe_gerencia_from_file
from apps.core.services.monthly_grid_service import build_monthly_grid
from apps.core.services.solicitacao_scope import (
    _PAPEIS_DE_GESTAO,
    participants_out_of_setor,
    scope_usuarios_by_setor,
    user_setores,
)
from apps.core.tests.factories import GroupFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

_CPF = itertools.count(93005000001)


@pytest.fixture(autouse=True)
def _clear_rbac_cache(db):
    cache.clear()
    yield
    cache.clear()


def _pessoa(nome, *grupos):
    u = UsuarioFactory(username=f"eq_{nome}", cpf=str(next(_CPF)), first_name=nome)
    for g in grupos:
        u.groups.add(GroupFactory(name=g))
    return u


def _gerencia(nome, setor):
    return Gerencia.objects.create(nome=nome, nome_setor=setor, setor_canonico=setor, ativo=True)


def _vincula(user, gerencia, papel):
    return EquipeGerencia.objects.create(usuario=user, gerencia=gerencia, papel=papel, ativo=True)


@pytest.fixture
def vidas():
    return _gerencia("G VIDAS EQ", "Vidas")


class TestPapelValido:
    def test_equipe_esta_nas_escolhas_com_rotulo_em_portugues(self):
        assert ("EQUIPE", "Equipe administrativa") in EquipeGerencia.PAPEL_CHOICES

    def test_vinculo_equipe_passa_na_validacao_do_modelo(self, vidas):
        v = EquipeGerencia(usuario=_pessoa("valida"), gerencia=vidas, papel="EQUIPE")
        v.full_clean()
        v.save()
        assert v.get_papel_display() == "Equipe administrativa"


class TestForaDasListas:
    def test_formadores_do_setor_para_superuser_nao_traz_equipe(self, vidas):
        _vincula(_pessoa("so_equipe"), vidas, "EQUIPE")
        form = _pessoa("form", "Formador")
        _vincula(form, vidas, "FORMADOR")
        client = APIClient()
        client.force_authenticate(UsuarioFactory(username="root_eq", cpf=str(next(_CPF)), superuser=True))

        resp = client.get("/api/options/formadores-do-setor/")

        assert resp.status_code == status.HTTP_200_OK
        assert {u["id"] for u in resp.data} == {form.id}

    def test_formadores_do_setor_para_coordenador_nao_traz_equipe(self, vidas):
        _vincula(_pessoa("so_equipe2"), vidas, "EQUIPE")
        form = _pessoa("form2", "Formador")
        _vincula(form, vidas, "FORMADOR")
        coord = _pessoa("coord2", "Coordenador")
        _vincula(coord, vidas, "COORDENADOR")
        client = APIClient()
        client.force_authenticate(coord)

        resp = client.get("/api/options/formadores-do-setor/")

        assert {u["id"] for u in resp.data} == {form.id}

    def test_lookup_do_setor_nao_traz_quem_so_tem_equipe(self, vidas):
        coord = _pessoa("coord3", "Coordenador")
        _vincula(coord, vidas, "COORDENADOR")
        # Tem a função Formador, mas no setor só está como equipe administrativa.
        so_equipe = _pessoa("equipe_formadora", "Formador")
        _vincula(so_equipe, vidas, "EQUIPE")
        form = _pessoa("form3", "Formador")
        _vincula(form, vidas, "FORMADOR")

        ids = set(scope_usuarios_by_setor(Usuario.objects.all(), coord).values_list("id", flat=True))

        assert form.id in ids
        assert so_equipe.id not in ids

    def test_participante_so_com_equipe_fica_fora_do_setor(self, vidas):
        coord = _pessoa("coord4", "Coordenador")
        _vincula(coord, vidas, "COORDENADOR")
        so_equipe = _pessoa("equipe_part", "Formador")
        _vincula(so_equipe, vidas, "EQUIPE")

        assert participants_out_of_setor(coord, [so_equipe]) == [so_equipe]

    @pytest.mark.parametrize("role", ["FORMADOR", "COORDENADOR"])
    def test_grade_mensal_nao_traz_equipe(self, vidas, role):
        so_equipe = _pessoa(f"equipe_grade_{role}")
        _vincula(so_equipe, vidas, "EQUIPE")
        membro = _pessoa(f"membro_{role}")
        _vincula(membro, vidas, role)

        grid = build_monthly_grid(year=2026, month=10, role=role, gerencia_id=vidas.id)

        assert {p["id"] for p in grid["people"]} == {membro.id}


class TestSemPoder:
    def test_equipe_nao_da_tier_de_gestor(self):
        assert "EQUIPE" not in _PAPEIS_DE_GESTAO

    def test_equipe_na_gerencia_aprovadora_nao_aprova(self):
        g1 = Gerencia.objects.create(
            nome=GERENCIA_APROVADORA_NOME, nome_setor="Super", setor_canonico="Superintendência", ativo=True
        )
        pessoa = _pessoa("equipe_g1")
        _vincula(pessoa, g1, "EQUIPE")

        assert user_is_gerente_superintendencia(pessoa) is False


class TestSetorDaPessoa:
    def test_vinculo_equipe_define_o_setor_da_pessoa(self):
        dat = _gerencia("G DAT EQ", "DAT")
        pessoa = _pessoa("equipe_dat")
        _vincula(pessoa, dat, "EQUIPE")

        assert user_setores(pessoa) == {"DAT"}


# ---------------------------------------------------------------- formulário de Usuários


@pytest.fixture
def root():
    return UsuarioFactory(username="root_form_eq", cpf=str(next(_CPF)), superuser=True)


def _salvar(root, alvo, payload, esperado=status.HTTP_200_OK):
    client = APIClient()
    client.force_authenticate(root)
    resp = client.patch(f"/api/usuarios-admin/{alvo.id}/", payload, format="json")
    assert resp.status_code == esperado, resp.data
    return resp


def _ativos(user):
    return {(v.gerencia_id, v.papel) for v in EquipeGerencia.objects.filter(usuario=user, ativo=True)}


def _grupos(user):
    user.refresh_from_db()
    return set(user.groups.values_list("name", flat=True))


class TestFormularioDeUsuarios:
    def test_marcar_equipe_cria_so_o_vinculo_sem_grupo_de_funcao(self, root, vidas):
        alvo = _pessoa("form_marca")

        _salvar(root, alvo, {"group_ids": [], "gerencia_id": vidas.id, "equipe_administrativa": True})

        assert _ativos(alvo) == {(vidas.id, "EQUIPE")}
        assert _grupos(alvo) <= {"Vidas"}  # só o grupo de setor da gerência (regra que já existia)

    def test_criar_usuario_so_com_equipe(self, root, vidas):
        client = APIClient()
        client.force_authenticate(root)
        resp = client.post(
            "/api/usuarios-admin/",
            {
                "username": "novo_eq",
                "email": "novo_eq@example.invalid",
                "cpf": str(next(_CPF)),
                "password": "SenhaForte#2026",
                "group_ids": [],
                "gerencia_id": vidas.id,
                "equipe_administrativa": True,
            },
            format="json",
        )

        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert _ativos(Usuario.objects.get(username="novo_eq")) == {(vidas.id, "EQUIPE")}

    def test_leitura_mostra_o_papel(self, root, vidas):
        alvo = _pessoa("form_le")
        _vincula(alvo, vidas, "EQUIPE")
        client = APIClient()
        client.force_authenticate(root)

        resp = client.get(f"/api/usuarios-admin/{alvo.id}/")

        assert resp.data["equipe_administrativa"] is True
        assert resp.data["gerencia_atual"]["papel"] == "EQUIPE"

    @pytest.mark.parametrize(
        "extra", [{"equipe_administrativa": True}, {}], ids=["form_reenvia_marcado", "campo_ausente"]
    )
    def test_salvar_sem_mudar_mantem_o_vinculo(self, root, vidas, extra):
        alvo = _pessoa("form_mantem")
        _vincula(alvo, vidas, "EQUIPE")

        _salvar(root, alvo, {"first_name": "Outro", "group_ids": [], "gerencia_id": vidas.id, **extra})

        assert _ativos(alvo) == {(vidas.id, "EQUIPE")}

    def test_salvar_sem_mudar_com_funcao_mantem_os_dois_vinculos(self, root, vidas):
        alvo = _pessoa("form_dois", "Formador")
        formador = alvo.groups.get(name="Formador")
        _vincula(alvo, vidas, "FORMADOR")
        _vincula(alvo, vidas, "EQUIPE")

        _salvar(root, alvo, {"telefone": "85900000000", "group_ids": [formador.id], "gerencia_id": vidas.id})

        assert _ativos(alvo) == {(vidas.id, "FORMADOR"), (vidas.id, "EQUIPE")}

    def test_dar_uma_funcao_nao_apaga_a_equipe(self, root, vidas):
        alvo = _pessoa("form_ganha_funcao")
        _vincula(alvo, vidas, "EQUIPE")
        formador = GroupFactory(name="Formador")

        _salvar(root, alvo, {"group_ids": [formador.id], "gerencia_id": vidas.id, "equipe_administrativa": True})

        assert _ativos(alvo) == {(vidas.id, "FORMADOR"), (vidas.id, "EQUIPE")}

    def test_desmarcar_equipe_encerra_so_esse_vinculo(self, root, vidas):
        alvo = _pessoa("form_desmarca", "Formador")
        formador = alvo.groups.get(name="Formador")
        _vincula(alvo, vidas, "FORMADOR")
        _vincula(alvo, vidas, "EQUIPE")

        _salvar(root, alvo, {"group_ids": [formador.id], "gerencia_id": vidas.id, "equipe_administrativa": False})

        assert _ativos(alvo) == {(vidas.id, "FORMADOR")}

    def test_desmarcar_a_unica_lotacao_encerra_o_vinculo(self, root, vidas):
        alvo = _pessoa("form_desmarca_unica")
        _vincula(alvo, vidas, "EQUIPE")

        _salvar(root, alvo, {"group_ids": [], "gerencia_id": vidas.id, "equipe_administrativa": False})

        assert _ativos(alvo) == set()

    def test_trocar_a_gerencia_leva_a_equipe(self, root, vidas):
        dat = _gerencia("G DAT EQ2", "DAT")
        alvo = _pessoa("form_troca")
        _vincula(alvo, vidas, "EQUIPE")

        _salvar(root, alvo, {"group_ids": [], "gerencia_id": dat.id, "equipe_administrativa": True})

        assert _ativos(alvo) == {(dat.id, "EQUIPE")}

    def test_marcar_equipe_sem_gerencia_e_recusado(self, root):
        alvo = _pessoa("form_sem_gerencia")

        resp = _salvar(
            root,
            alvo,
            {"group_ids": [], "gerencia_id": None, "equipe_administrativa": True},
            esperado=status.HTTP_400_BAD_REQUEST,
        )

        assert "gerencia_id" in resp.data.get("errors", resp.data)
        assert _ativos(alvo) == set()


# ---------------------------------------------------------------- importador


class TestImportador:
    @pytest.mark.parametrize("papel", ["EQUIPE", "Equipe administrativa", "equipe administrativa"])
    def test_importador_aceita_equipe(self, vidas, papel):
        pessoa = UsuarioFactory(username=f"imp_{papel[:6]}", email="imp_eq@example.invalid", cpf=str(next(_CPF)))
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write(f"setor,papel,usuario_email\nVidas,{papel},{pessoa.email}\n")
        try:
            import_equipe_gerencia_from_file(path=f.name, dry_run=False)
        finally:
            Path(f.name).unlink(missing_ok=True)

        assert _ativos(pessoa) == {(vidas.id, "EQUIPE")}
