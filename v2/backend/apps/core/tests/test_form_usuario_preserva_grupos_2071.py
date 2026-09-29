"""
#2071: o salvar do formulário de Usuários mexe só no que o formulário mudou.

O formulário (UsuariosPage, só superuser) edita as FUNÇÕES e UMA gerência (a primeira vigente). Envia
`group_ids` = funções e `gerencia_id` = a gerência exibida (ou null, se a pessoa não tem). Antes, o
backend fazia `groups.set(group_ids)` e sempre re-sincronizava a lotação. Medido em prod (29/09, só
leitura), um "salvar sem mudar nada" tiraria o Controle da pessoa que aprova, o DAT de 6 pessoas e
grupos de permissão de 2; converteria o vínculo de 1 e encerraria o de outra com duas gerências; e
daria o grupo Superintendência (visão de todos os setores) a ~60 pessoas lotadas em g1.

Regras:
- `group_ids` substitui só os grupos de FUNÇÃO (estáticos + classificados como função); os demais
  grupos (setor, permissão funcional) ficam.
- O grupo de setor derivado da gerência só muda quando a gerência muda; a gerência aprovadora
  (SUPERINTENDENCIA) não concede grupo de setor — a autoridade vem do vínculo (B1).
- Vínculos só mudam quando a gerência ou os PAPÉIS mudam. Aí o form volta a ser a fonte da lotação:
  tirar a função Gerente de uma aprovadora encerra o vínculo e revoga a aprovação.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportIndexIssue=false, reportUnusedFunction=false

from __future__ import annotations

from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog, EquipeGerencia, Gerencia, GroupClassificacao
from apps.core.rbac.policies import solicitation_approval_basis
from apps.core.tests.factories import GroupFactory, UsuarioFactory

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _clear_rbac_cache(db):
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def root(db):
    return UsuarioFactory(username="root_2071", cpf="92071000009", superuser=True)


@pytest.fixture
def g1(db):
    """A gerência aprovadora, como em prod: setor 'Superintendência', que também é nome de grupo."""
    GroupFactory(name="Superintendência")
    gerencia, _ = Gerencia.objects.get_or_create(
        nome="SUPERINTENDENCIA", defaults={"nome_setor": "Super", "setor_canonico": "Superintendência"}
    )
    return gerencia


def _grupos(user):
    user.refresh_from_db()
    return set(user.groups.values_list("name", flat=True))


def _ativos(user):
    return {(v.gerencia_id, v.papel) for v in EquipeGerencia.objects.filter(usuario=user, ativo=True)}


def _salvar(api_client_ou_root, alvo, payload, captura=None):
    client = APIClient()
    client.force_authenticate(api_client_ou_root)
    if captura is None:
        resp = client.patch(f"/api/usuarios-admin/{alvo.id}/", payload, format="json")
    else:
        with captura(execute=True):
            resp = client.patch(f"/api/usuarios-admin/{alvo.id}/", payload, format="json")
    assert resp.status_code == status.HTTP_200_OK, resp.data


def _logs_autoridade(alvo):
    return list(
        AuditLog.objects.filter(details__target_user_id=alvo.id, details__has_key="autoridade_aprovacao")
        .order_by("id")
        .values_list("details__autoridade_aprovacao", flat=True)
    )


class TestGruposQueOFormularioNaoMostra:
    def test_editar_pessoa_do_controle_nao_tira_o_grupo_controle(self, root):
        asst = GroupFactory(name="Assistente Administrativo")
        alvo = UsuarioFactory(username="controle_2071", cpf="92071000001")
        alvo.groups.add(GroupFactory(name="Controle"), asst)

        # payload real do form: funções hidratadas + gerência null (o Controle não tem gerência)
        _salvar(root, alvo, {"first_name": "Novo", "group_ids": [asst.id], "gerencia_id": None})

        assert _grupos(alvo) == {"Controle", "Assistente Administrativo"}

    def test_editar_pessoa_do_dat_sem_vinculo_mantem_o_grupo_dat(self, root):
        alvo = UsuarioFactory(username="dat_2071", cpf="92071000002")
        alvo.groups.add(GroupFactory(name="DAT"))

        _salvar(root, alvo, {"telefone": "85911112222", "group_ids": [], "gerencia_id": None})

        assert _grupos(alvo) == {"DAT"}

    def test_grupo_de_permissao_fica(self, root):
        formador = GroupFactory(name="Formador")
        alvo = UsuarioFactory(username="prog_2071", cpf="92071000003")
        alvo.groups.add(GroupFactory(name="Programador"), formador)

        _salvar(root, alvo, {"group_ids": [formador.id], "gerencia_id": None})

        assert _grupos(alvo) == {"Programador", "Formador"}

    def test_funcoes_sao_substituidas(self, root):
        formador, coord, gerente = (GroupFactory(name=n) for n in ("Formador", "Coordenador", "Gerente"))
        alvo = UsuarioFactory(username="func_2071", cpf="92071000004")
        alvo.groups.add(formador, coord)

        _salvar(root, alvo, {"group_ids": [gerente.id], "gerencia_id": None})

        assert _grupos(alvo) == {"Gerente"}

    def test_funcao_classificada_na_tela_de_grupos_tambem_e_substituida(self, root):
        formador = GroupFactory(name="Formador")
        dinamica = GroupFactory(name="Funcao Dinamica 2071")
        GroupClassificacao.objects.create(group=dinamica, tipo=GroupClassificacao.Tipo.FUNCAO)
        alvo = UsuarioFactory(username="dinamica_2071", cpf="92071000005")
        alvo.groups.add(dinamica)

        _salvar(root, alvo, {"group_ids": [formador.id], "gerencia_id": None})

        assert _grupos(alvo) == {"Formador"}

    def test_trocar_a_gerencia_troca_o_grupo_de_setor_e_audita(self, root, django_capture_on_commit_callbacks):
        formador, grupo_fluir = GroupFactory(name="Formador"), GroupFactory(name="Fluir")
        GroupFactory(name="Vidas")
        fluir = Gerencia.objects.create(nome="G FLUIR 2071", nome_setor="Fluir", setor_canonico="Fluir", ativo=True)
        vidas = Gerencia.objects.create(nome="G VIDAS 2071", nome_setor="Vidas", setor_canonico="Vidas", ativo=True)
        alvo = UsuarioFactory(username="troca_2071", cpf="92071000006")
        alvo.groups.add(formador, grupo_fluir)
        EquipeGerencia.objects.create(gerencia=fluir, usuario=alvo, papel="FORMADOR", ativo=True)

        # sem group_ids (PATCH só com a gerência): a troca de setor também é auditada
        _salvar(root, alvo, {"gerencia_id": vidas.id}, django_capture_on_commit_callbacks)

        assert _grupos(alvo) == {"Formador", "Vidas"}
        assert AuditLog.objects.filter(action=AuditLog.Action.ASSIGN_GROUPS, details__target_user_id=alvo.id).exists()


class TestSalvarSemMudarNaoMexeNaLotacao:
    def test_membro_de_g1_nao_ganha_o_grupo_superintendencia(self, root, g1):
        formador = GroupFactory(name="Formador")
        alvo = UsuarioFactory(username="formadora_g1_2071", cpf="92071000011")
        alvo.groups.add(formador)
        EquipeGerencia.objects.create(gerencia=g1, usuario=alvo, papel="FORMADOR", ativo=True)

        _salvar(root, alvo, {"telefone": "85900001111", "group_ids": [formador.id], "gerencia_id": g1.id})

        assert _grupos(alvo) == {"Formador"}

    def test_vinculo_com_papel_diferente_da_funcao_nao_e_convertido(self, root, g1):
        """Grupo Formador com vínculo COORDENADOR: salvar o telefone não converte o papel."""
        formador = GroupFactory(name="Formador")
        alvo = UsuarioFactory(username="lara_2071", cpf="92071000007")
        alvo.groups.add(formador)
        EquipeGerencia.objects.create(gerencia=g1, usuario=alvo, papel="COORDENADOR", ativo=True)

        _salvar(root, alvo, {"telefone": "85933334444", "group_ids": [formador.id], "gerencia_id": g1.id})

        assert _ativos(alvo) == {(g1.id, "COORDENADOR")}

    def test_acrescentar_funcao_sem_papel_nao_mexe_no_vinculo(self, root, g1):
        formador, asst = GroupFactory(name="Formador"), GroupFactory(name="Assistente Administrativo")
        alvo = UsuarioFactory(username="lara_asst_2071", cpf="92071000012")
        alvo.groups.add(formador)
        EquipeGerencia.objects.create(gerencia=g1, usuario=alvo, papel="COORDENADOR", ativo=True)

        _salvar(root, alvo, {"group_ids": [formador.id, asst.id], "gerencia_id": g1.id})

        assert _ativos(alvo) == {(g1.id, "COORDENADOR")}

    def test_pessoa_com_duas_gerencias_mantem_as_duas(self, root):
        coord, formador = GroupFactory(name="Coordenador"), GroupFactory(name="Formador")
        exibida = Gerencia.objects.create(nome="G LER 2071", nome_setor="Ler", setor_canonico="", ativo=True)
        outra = Gerencia.objects.create(nome="G BRINCANDO 2071", nome_setor="Brincando", setor_canonico="", ativo=True)
        alvo = UsuarioFactory(username="lourene_2071", cpf="92071000008")
        alvo.groups.add(coord, formador)
        EquipeGerencia.objects.create(gerencia=exibida, usuario=alvo, papel="COORDENADOR", ativo=True)
        EquipeGerencia.objects.create(gerencia=outra, usuario=alvo, papel="FORMADOR", ativo=True)

        _salvar(
            root, alvo, {"telefone": "85922223333", "group_ids": [coord.id, formador.id], "gerencia_id": exibida.id}
        )

        assert _ativos(alvo) == {(exibida.id, "COORDENADOR"), (outra.id, "FORMADOR")}


class TestAprovadoraPeloFormulario:
    def test_criar_aprovadora_em_g1_da_o_vinculo_e_nao_o_grupo_superintendencia(self, root, g1):
        gerente = GroupFactory(name="Gerente")
        client = APIClient()
        client.force_authenticate(root)
        resp = client.post(
            "/api/usuarios-admin/",
            {
                "username": "92071000013",
                "cpf": "92071000013",
                "email": "aprovadora_2071@example.com",
                "password": "SecurePass123!",
                "group_ids": [gerente.id],
                "gerencia_id": g1.id,
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        alvo = EquipeGerencia.objects.get(gerencia=g1, papel="GERENTE").usuario

        assert _grupos(alvo) == {"Gerente"}
        assert solicitation_approval_basis(alvo) == "gerente_superintendencia"

    def test_tirar_a_funcao_gerente_revoga_a_aprovacao(self, root, g1, django_capture_on_commit_callbacks):
        gerente = GroupFactory(name="Gerente")
        alvo = UsuarioFactory(username="aprovadora_rev_2071", cpf="92071000014")
        alvo.groups.add(gerente)
        EquipeGerencia.objects.create(gerencia=g1, usuario=alvo, papel="GERENTE", ativo=True)
        assert solicitation_approval_basis(alvo) == "gerente_superintendencia"

        _salvar(root, alvo, {"group_ids": [], "gerencia_id": g1.id}, django_capture_on_commit_callbacks)

        cache.clear()
        assert _ativos(alvo) == set()
        assert solicitation_approval_basis(alvo) is None
        assert _logs_autoridade(alvo) == ["revogada"]

    def test_revoga_mesmo_quando_o_vinculo_de_g1_nao_e_o_exibido(self, root, g1, django_capture_on_commit_callbacks):
        gerente, formador = GroupFactory(name="Gerente"), GroupFactory(name="Formador")
        vidas = Gerencia.objects.create(nome="G VIDAS REV 2071", nome_setor="Vidas", setor_canonico="", ativo=True)
        alvo = UsuarioFactory(username="aprovadora_2g_2071", cpf="92071000015")
        alvo.groups.add(gerente, formador)
        EquipeGerencia.objects.create(gerencia=vidas, usuario=alvo, papel="FORMADOR", ativo=True)  # exibida
        EquipeGerencia.objects.create(gerencia=g1, usuario=alvo, papel="GERENTE", ativo=True)

        _salvar(root, alvo, {"group_ids": [formador.id], "gerencia_id": vidas.id}, django_capture_on_commit_callbacks)

        cache.clear()
        assert _ativos(alvo) == {(vidas.id, "FORMADOR")}
        assert solicitation_approval_basis(alvo) is None
        assert _logs_autoridade(alvo) == ["revogada"]


class TestSemAprovacaoPorGrupoPeloFormulario:
    """O composite legado (grupo de setor + função) ainda aprova até o B2. O form preserva grupos que
    não mostra, então não pode deixar essa preservação virar poder de aprovar que ninguém pediu."""

    def test_grupo_superintendencia_orfao_mais_gerente_e_recusado(self, root, django_capture_on_commit_callbacks):
        coord, gerente = GroupFactory(name="Coordenador"), GroupFactory(name="Gerente")
        alvo = UsuarioFactory(username="orfao_sup_2071", cpf="92071000016")
        alvo.groups.add(coord, GroupFactory(name="Superintendência"))

        client = APIClient()
        client.force_authenticate(root)
        with django_capture_on_commit_callbacks(execute=True):
            resp = client.patch(
                f"/api/usuarios-admin/{alvo.id}/",
                {"first_name": "Novo", "group_ids": [coord.id, gerente.id], "gerencia_id": None},
                format="json",
            )

        assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.data
        assert "Superintendência" in str(resp.data)
        assert _grupos(alvo) == {"Coordenador", "Superintendência"}
        alvo.refresh_from_db()
        assert alvo.first_name != "Novo"
        assert solicitation_approval_basis(alvo) is None
        assert _logs_autoridade(alvo) == []

    def test_sair_de_g1_com_o_grupo_superintendencia_e_recusado(self, root, g1):
        gerente = GroupFactory(name="Gerente")
        vidas = Gerencia.objects.create(nome="G VIDAS SUP 2071", nome_setor="Vidas", setor_canonico="", ativo=True)
        alvo = UsuarioFactory(username="aprov_sup_2071", cpf="92071000017")
        alvo.groups.add(gerente, GroupFactory(name="Superintendência"))
        EquipeGerencia.objects.create(gerencia=g1, usuario=alvo, papel="GERENTE", ativo=True)

        client = APIClient()
        client.force_authenticate(root)
        resp = client.patch(
            f"/api/usuarios-admin/{alvo.id}/", {"group_ids": [gerente.id], "gerencia_id": vidas.id}, format="json"
        )

        assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.data
        assert _ativos(alvo) == {(g1.id, "GERENTE")}

    @pytest.mark.parametrize("setor", ["Superintendência", "Controle"])
    def test_gerencia_com_setor_de_par_aprovador_nao_da_o_grupo(self, root, setor):
        asst, formador = GroupFactory(name="Assistente Administrativo"), GroupFactory(name="Formador")
        GroupFactory(name=setor)
        ger = Gerencia.objects.create(
            nome=f"G {setor.upper()} 2071", nome_setor=setor, setor_canonico=setor, ativo=True
        )
        alvo = UsuarioFactory(username=f"par_{len(setor)}_2071", cpf=f"920710000{len(setor) + 70}")

        _salvar(root, alvo, {"group_ids": [asst.id, formador.id], "gerencia_id": ger.id})

        assert _grupos(alvo) == {"Assistente Administrativo", "Formador"}

    def test_limpar_a_gerencia_e_tirar_gerente_revoga(self, root, g1, django_capture_on_commit_callbacks):
        gerente = GroupFactory(name="Gerente")
        alvo = UsuarioFactory(username="aprov_null_2071", cpf="92071000018")
        alvo.groups.add(gerente)
        EquipeGerencia.objects.create(gerencia=g1, usuario=alvo, papel="GERENTE", ativo=True)

        _salvar(root, alvo, {"group_ids": [], "gerencia_id": None}, django_capture_on_commit_callbacks)

        cache.clear()
        assert _ativos(alvo) == set()
        assert solicitation_approval_basis(alvo) is None
        assert _logs_autoridade(alvo) == ["revogada"]
