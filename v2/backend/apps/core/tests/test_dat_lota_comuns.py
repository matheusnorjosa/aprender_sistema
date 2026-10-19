"""
O DAT lota nas gerências comuns (decisão do dono de 17/10/2026).

Quem tem a policy `manage_lotacao_comum` (= `manage_admin_registries`, hoje só o pacote ADMIN_OPERACIONAL)
lota, pela tela de Usuários, nas gerências comuns: FORMADOR, COORDENADOR, APOIO, GERENTE (menos na
aprovadora) e EQUIPE. Lotar no DAT, no Controle, na Diretoria ou como GERENTE da Superintendência continua
só com o superusuário (`lotacao_reservada`).

O DAT recebe 400 (não é ignorado em silêncio) quando: a gerência ou o papel é reservado; o alvo tem vínculo
reservado vigente (protege também o encerramento); é a própria conta; mexe em grupo que não é de função
(`PAPEL_POR_FUNCAO`). Salvar sem mudar a lotação continua passando (#2071). Importadores e
`assign_groups` continuam só do superusuário.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportIndexIssue=false

from __future__ import annotations

from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory

import pytest

from apps.core.models import AuditLog, EquipeGerencia, Gerencia, Usuario
from apps.core.rbac.policies import resolve_public_policies
from apps.core.serializers.usuario import UsuarioAdminSerializer
from apps.core.services.equipe_gerencia_import import gerencia_reservada, lotacao_reservada
from apps.core.tests.factories import (
    GerenciaFactory,
    GroupFactory,
    UsuarioFactory,
    com_pacote_do_controle,
    com_pacote_do_dat,
    com_papel,
)

pytestmark = pytest.mark.django_db

FUNCAO_DO_PAPEL = {"FORMADOR": "Formador", "COORDENADOR": "Coordenador", "APOIO": "Apoio de Coordenação"}


@pytest.fixture(autouse=True)
def _limpa_cache(db):
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def root(db):
    return UsuarioFactory(superuser=True)


@pytest.fixture
def dat(db):
    user = UsuarioFactory()
    com_pacote_do_dat(user)
    return user


@pytest.fixture
def comum(db):
    return GerenciaFactory(nome="GERENCIA VIDAS LOTA", nome_setor="Vidas", setor_canonico="Vidas")


@pytest.fixture
def g1(db):
    gerencia, _ = Gerencia.objects.get_or_create(
        nome="SUPERINTENDENCIA", defaults={"nome_setor": "Super", "setor_canonico": "Superintendência"}
    )
    return gerencia


def _gerencia_dat():
    return com_pacote_do_dat(UsuarioFactory()).gerencia


def _gerencia_controle():
    return com_pacote_do_controle(UsuarioFactory()).gerencia


def _gerencia_diretoria():
    # Nome em `PERFIL_PERMITIDO`: reservada mesmo com o perfil ainda PADRAO.
    return Gerencia.objects.get_or_create(nome="DIRETORIA", defaults={"nome_setor": "Diretoria"})[0]


RESERVADAS = {"DAT": _gerencia_dat, "CONTROLE": _gerencia_controle, "DIRETORIA": _gerencia_diretoria}


def _grupo(nome):
    return GroupFactory(name=nome)


def _patch(ator, alvo, payload):
    client = APIClient()
    client.force_authenticate(ator)
    return client.patch(f"/api/usuarios-admin/{alvo.id}/", payload, format="json")


def _vigentes(user):
    return {(v.gerencia_id, v.papel) for v in EquipeGerencia.vigentes_em().filter(usuario=user)}


def _erros(resp):
    return resp.data.get("errors", resp.data)


class TestPredicado:
    @pytest.mark.parametrize("papel", ["FORMADOR", "COORDENADOR", "APOIO", "GERENTE", "EQUIPE"])
    def test_gerencia_comum_nao_e_reservada(self, comum, papel):
        assert not lotacao_reservada(comum, papel)
        assert not gerencia_reservada(comum)

    @pytest.mark.parametrize("nome", sorted(RESERVADAS))
    @pytest.mark.parametrize("papel", ["FORMADOR", "COORDENADOR", "APOIO", "GERENTE", "EQUIPE"])
    def test_dat_controle_e_diretoria_sao_reservadas_em_qualquer_papel(self, nome, papel):
        gerencia = RESERVADAS[nome]()
        assert gerencia_reservada(gerencia)
        assert lotacao_reservada(gerencia, papel)

    def test_superintendencia_reserva_so_o_gerente(self, g1):
        assert not gerencia_reservada(g1)
        assert lotacao_reservada(g1, "GERENTE")
        assert not lotacao_reservada(g1, "COORDENADOR")
        assert not lotacao_reservada(g1, "EQUIPE")

    def test_perfil_aprovacao_nao_reserva(self):
        gerencia = GerenciaFactory(perfil=Gerencia.Perfil.APROVACAO)
        assert not lotacao_reservada(gerencia, "EQUIPE")


class TestDatLotaNasComuns:
    @pytest.mark.parametrize("papel", sorted(FUNCAO_DO_PAPEL))
    def test_lota_por_funcao_grava_o_vinculo_e_audita(self, dat, comum, papel):
        funcao = _grupo(FUNCAO_DO_PAPEL[papel])
        alvo = UsuarioFactory()
        resp = _patch(dat, alvo, {"group_ids": [funcao.id], "gerencia_id": comum.id})
        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert _vigentes(alvo) == {(comum.id, papel)}
        assert funcao in alvo.groups.all()
        log = AuditLog.objects.get(action=AuditLog.Action.UPDATE, model_name="EquipeGerencia")
        assert log.usuario_id == dat.id
        assert log.details["target_user_id"] == alvo.id
        assert log.details["lotacao_depois"] == [[comum.id, papel]]

    def test_lota_gerente_em_gerencia_comum(self, dat, comum):
        alvo = UsuarioFactory()
        resp = _patch(dat, alvo, {"group_ids": [_grupo("Gerente").id], "gerencia_id": comum.id})
        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert _vigentes(alvo) == {(comum.id, "GERENTE")}

    def test_lota_equipe_administrativa_em_gerencia_comum(self, dat, comum):
        alvo = UsuarioFactory()
        resp = _patch(dat, alvo, {"group_ids": [], "gerencia_id": comum.id, "equipe_administrativa": True})
        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert _vigentes(alvo) == {(comum.id, "EQUIPE")}
        assert AuditLog.objects.filter(action=AuditLog.Action.UPDATE, model_name="EquipeGerencia").exists()

    def test_coordenador_na_superintendencia_passa(self, dat, g1):
        alvo = UsuarioFactory()
        resp = _patch(dat, alvo, {"group_ids": [_grupo("Coordenador").id], "gerencia_id": g1.id})
        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert _vigentes(alvo) == {(g1.id, "COORDENADOR")}

    def test_troca_de_gerencia_comum(self, dat, comum):
        outra = GerenciaFactory()
        alvo = UsuarioFactory()
        com_papel(alvo, "FORMADOR", outra)
        formador = _grupo("Formador")
        resp = _patch(dat, alvo, {"group_ids": [formador.id], "gerencia_id": comum.id})
        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert _vigentes(alvo) == {(comum.id, "FORMADOR")}

    def test_cria_conta_ja_lotada(self, dat, comum):
        client = APIClient()
        client.force_authenticate(dat)
        resp = client.post(
            "/api/usuarios-admin/",
            {
                "username": "nova_lotada_dat",
                "email": "nova_lotada_dat@example.invalid",
                "cpf": "93017000001",
                "password": "SecurePass123!",
                "group_ids": [_grupo("Formador").id],
                "gerencia_id": comum.id,
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert _vigentes(Usuario.objects.get(username="nova_lotada_dat")) == {(comum.id, "FORMADOR")}

    def test_mantem_grupo_de_funcao_sem_papel_que_o_alvo_ja_tem(self, dat, comum):
        asst = _grupo("Assistente Administrativo")
        alvo = UsuarioFactory()
        alvo.groups.add(asst)
        formador = _grupo("Formador")
        resp = _patch(dat, alvo, {"group_ids": [asst.id, formador.id], "gerencia_id": comum.id})
        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert set(alvo.groups.values_list("name", flat=True)) >= {"Assistente Administrativo", "Formador"}


class TestDatRecebe400:
    @pytest.mark.parametrize("nome", sorted(RESERVADAS))
    @pytest.mark.parametrize("papel", ["FORMADOR", "GERENTE", "EQUIPE"])
    def test_gerencia_reservada_em_qualquer_papel(self, dat, nome, papel):
        gerencia = RESERVADAS[nome]()
        alvo = UsuarioFactory()
        payload = (
            {"group_ids": [], "gerencia_id": gerencia.id, "equipe_administrativa": True}
            if papel == "EQUIPE"
            else {"group_ids": [_grupo("Gerente" if papel == "GERENTE" else "Formador").id], "gerencia_id": gerencia.id}
        )
        resp = _patch(dat, alvo, payload)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "gerencia_id" in _erros(resp)
        assert _vigentes(alvo) == set()
        assert not alvo.groups.exists()

    def test_gerente_na_superintendencia(self, dat, g1):
        alvo = UsuarioFactory()
        resp = _patch(dat, alvo, {"group_ids": [_grupo("Gerente").id], "gerencia_id": g1.id})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "gerencia_id" in _erros(resp)
        assert _vigentes(alvo) == set()

    def test_dar_a_funcao_gerente_a_quem_ja_esta_na_superintendencia(self, dat, g1):
        alvo = UsuarioFactory()
        com_papel(alvo, "COORDENADOR", g1)
        coordenador = _grupo("Coordenador")
        resp = _patch(dat, alvo, {"group_ids": [coordenador.id, _grupo("Gerente").id], "gerencia_id": g1.id})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert _vigentes(alvo) == {(g1.id, "COORDENADOR")}

    def test_funcao_gerente_sem_gerencia_para_quem_esta_na_superintendencia(self, dat, g1):
        # Sem `gerencia_id` o vínculo não muda agora, mas o próximo salvar do form (que reenvia a g1)
        # gravaria o GERENTE na aprovadora: a regra olha a gerência exibida.
        alvo = UsuarioFactory()
        com_papel(alvo, "COORDENADOR", g1)
        coordenador = _grupo("Coordenador")
        resp = _patch(dat, alvo, {"group_ids": [coordenador.id, _grupo("Gerente").id]})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert set(alvo.groups.values_list("name", flat=True)) == {"Coordenador"}

    @pytest.mark.parametrize("onde", ["DAT", "CONTROLE", "GERENTE_G1"])
    def test_alvo_com_vinculo_reservado_nao_e_transferido(self, dat, comum, g1, onde):
        alvo = UsuarioFactory()
        if onde == "DAT":
            com_pacote_do_dat(alvo)
        elif onde == "CONTROLE":
            com_pacote_do_controle(alvo)
        else:
            com_papel(alvo, "GERENTE", g1)
        antes = _vigentes(alvo)
        resp = _patch(dat, alvo, {"group_ids": [_grupo("Formador").id], "gerencia_id": comum.id})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "gerencia_id" in _erros(resp)
        assert _vigentes(alvo) == antes

    def test_tirar_a_funcao_da_gerente_da_superintendencia(self, dat, g1):
        alvo = UsuarioFactory()
        com_papel(alvo, "GERENTE", g1)
        resp = _patch(dat, alvo, {"group_ids": [], "gerencia_id": g1.id})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert _vigentes(alvo) == {(g1.id, "GERENTE")}
        assert alvo.groups.filter(pk=_grupo("Gerente").pk).exists()

    def test_desmarcar_a_equipe_do_dat(self, dat):
        alvo = UsuarioFactory()
        vinculo = com_pacote_do_dat(alvo)
        resp = _patch(dat, alvo, {"gerencia_id": vinculo.gerencia_id, "equipe_administrativa": False})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert _vigentes(alvo) == {(vinculo.gerencia_id, "EQUIPE")}

    def test_propria_conta(self, dat, comum):
        resp = _patch(dat, dat, {"gerencia_id": comum.id, "equipe_administrativa": True})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "própria" in str(_erros(resp)["gerencia_id"])

    @pytest.mark.parametrize("nome", ["Superintendência", "DAT", "Assistente Administrativo"])
    def test_grupo_que_nao_e_de_funcao_com_papel(self, dat, comum, nome):
        alvo = UsuarioFactory()
        resp = _patch(dat, alvo, {"group_ids": [_grupo(nome).id], "gerencia_id": comum.id})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "group_ids" in _erros(resp)
        assert not alvo.groups.exists()
        assert _vigentes(alvo) == set()

    def test_tirar_grupo_de_funcao_sem_papel(self, dat, comum):
        alvo = UsuarioFactory()
        alvo.groups.add(_grupo("Assistente Administrativo"))
        resp = _patch(dat, alvo, {"group_ids": [_grupo("Formador").id], "gerencia_id": comum.id})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "group_ids" in _erros(resp)


class TestSalvarSemMudar:
    def test_conta_protegida_salva_o_cadastro(self, dat, g1):
        alvo = UsuarioFactory()
        com_papel(alvo, "GERENTE", g1)
        gerente = _grupo("Gerente")
        resp = _patch(dat, alvo, {"telefone": "85900000000", "group_ids": [gerente.id], "gerencia_id": g1.id})
        assert resp.status_code == status.HTTP_200_OK, resp.data
        alvo.refresh_from_db()
        assert alvo.telefone == "85900000000"
        assert _vigentes(alvo) == {(g1.id, "GERENTE")}

    def test_equipe_do_dat_salva_o_cadastro(self, dat):
        alvo = UsuarioFactory()
        vinculo = com_pacote_do_dat(alvo)
        resp = _patch(
            dat,
            alvo,
            {"cargo": "Suporte", "group_ids": [], "gerencia_id": vinculo.gerencia_id, "equipe_administrativa": True},
        )
        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert _vigentes(alvo) == {(vinculo.gerencia_id, "EQUIPE")}

    def test_lotacao_igual_nao_audita(self, dat, comum):
        alvo = UsuarioFactory()
        com_papel(alvo, "FORMADOR", comum)
        resp = _patch(dat, alvo, {"group_ids": [_grupo("Formador").id], "gerencia_id": comum.id})
        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert not AuditLog.objects.filter(model_name="EquipeGerencia").exists()


class TestQuemNaoGanha:
    @pytest.mark.parametrize("nome", sorted(RESERVADAS))
    def test_superusuario_segue_lotando_em_tudo(self, root, nome):
        gerencia = RESERVADAS[nome]()
        alvo = UsuarioFactory()
        resp = _patch(root, alvo, {"group_ids": [], "gerencia_id": gerencia.id, "equipe_administrativa": True})
        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert _vigentes(alvo) == {(gerencia.id, "EQUIPE")}

    def test_superusuario_lota_gerente_na_superintendencia(self, root, g1):
        alvo = UsuarioFactory()
        resp = _patch(root, alvo, {"group_ids": [_grupo("Gerente").id], "gerencia_id": g1.id})
        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert _vigentes(alvo) == {(g1.id, "GERENTE")}

    def test_controle_continua_403(self, comum):
        controle = UsuarioFactory()
        com_pacote_do_controle(controle)
        resp = _patch(controle, UsuarioFactory(), {"group_ids": [], "gerencia_id": comum.id})
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_sem_a_policy_a_lotacao_segue_ignorada(self, comum):
        # Reuso do serializer fora da view: ator sem `manage_lotacao_comum` não lota e não recebe 400.
        ator = UsuarioFactory()
        alvo = UsuarioFactory()
        request = APIRequestFactory().patch(f"/api/usuarios-admin/{alvo.id}/")
        request.user = ator
        data = {"group_ids": [_grupo("Formador").id], "gerencia_id": comum.id}
        serializer = UsuarioAdminSerializer(instance=alvo, data=data, partial=True, context={"request": request})
        assert serializer.is_valid(), serializer.errors
        serializer.save()
        assert _vigentes(alvo) == set()
        assert not alvo.groups.exists()


class TestPolicyPublica:
    def _policies(self, user):
        client = APIClient()
        client.force_authenticate(user)
        resp = client.get("/api/me/policies/")
        assert resp.status_code == status.HTTP_200_OK
        return resp.json()

    def test_dat_tem(self, dat):
        assert "manage_lotacao_comum" in self._policies(dat)

    def test_superusuario_tem(self, root):
        assert "manage_lotacao_comum" in self._policies(root)

    @pytest.mark.parametrize("papel", ["EQUIPE", "GERENTE"])
    def test_controle_nao_tem(self, papel):
        controle = UsuarioFactory()
        com_pacote_do_controle(controle, papel)
        assert "manage_lotacao_comum" not in self._policies(controle)

    def test_segue_manage_admin_registries(self, dat):
        sem = UsuarioFactory()
        com_papel(sem, "GERENTE")
        for user in (dat, sem):
            policies = resolve_public_policies(user)
            assert ("manage_lotacao_comum" in policies) == ("manage_admin_registries" in policies)


class TestCamposDeLeitura:
    def test_gerencia_diz_se_e_reservada(self, dat, comum, g1):
        reservada = _gerencia_dat()
        client = APIClient()
        client.force_authenticate(dat)
        resp = client.get("/api/gerencias/", {"page_size": 100})
        assert resp.status_code == status.HTTP_200_OK
        por_id = {g["id"]: g["lotacao_reservada"] for g in resp.json()["results"]}
        assert por_id[reservada.id] is True
        assert por_id[comum.id] is False
        assert por_id[g1.id] is False

    def test_usuario_diz_se_a_lotacao_e_reservada(self, dat, comum, g1):
        protegida = UsuarioFactory()
        com_papel(protegida, "GERENTE", g1)
        livre = UsuarioFactory()
        com_papel(livre, "GERENTE", comum)
        client = APIClient()
        client.force_authenticate(dat)
        assert client.get(f"/api/usuarios-admin/{protegida.id}/").json()["lotacao_reservada"] is True
        assert client.get(f"/api/usuarios-admin/{livre.id}/").json()["lotacao_reservada"] is False
