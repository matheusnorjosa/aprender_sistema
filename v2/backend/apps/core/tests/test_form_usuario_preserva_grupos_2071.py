"""
#2071: salvar o formulário de Usuários não pode tirar o que o formulário não mostra.

O formulário (UsuariosPage) só edita as FUNÇÕES e UMA gerência (a primeira vigente). Ele envia
`group_ids` = funções e `gerencia_id` = a gerência exibida. Antes, o backend fazia
`groups.set(group_ids)` e `sync_user_lotacao` encerrava todo vínculo fora do alvo. Medido em prod
(29/09, só leitura), um "salvar sem mudar nada" tiraria o grupo Controle da Fabiana, o DAT de 6
pessoas, grupos de permissão de 2, e vínculos de 2 pessoas (uma com duas gerências).

Regras:
- `group_ids` substitui só os grupos de FUNÇÃO (estáticos + classificados como função); os demais
  grupos (setor, permissão funcional) ficam.
- Trocar a gerência troca o grupo de setor derivado dela (sem acúmulo de privilégio).
- Salvar sem mudar gerência nem funções não mexe em vínculo.
- Mudar a lotação mexe só na gerência exibida e na gerência alvo; vínculos em outras gerências ficam.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportIndexIssue=false

from __future__ import annotations

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.core.models import EquipeGerencia, Gerencia, GroupClassificacao
from apps.core.tests.factories import GroupFactory, UsuarioFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def root(db):
    return UsuarioFactory(username="root_2071", cpf="92071000009", superuser=True)


def _grupos(user):
    user.refresh_from_db()
    return set(user.groups.values_list("name", flat=True))


def _salvar(api_client, root, alvo, payload):
    api_client.force_authenticate(root)
    resp = api_client.patch(f"/api/usuarios-admin/{alvo.id}/", payload, format="json")
    assert resp.status_code == status.HTTP_200_OK, resp.data


@pytest.mark.django_db
class TestGruposQueOFormularioNaoMostra:
    def test_editar_pessoa_do_controle_nao_tira_o_grupo_controle(self, api_client, root):
        asst = GroupFactory(name="Assistente Administrativo")
        alvo = UsuarioFactory(username="controle_2071", cpf="92071000001")
        alvo.groups.add(GroupFactory(name="Controle"), asst)

        # payload do form: funções hidratadas + gerência vazia (o Controle não tem gerência)
        _salvar(api_client, root, alvo, {"first_name": "Novo", "group_ids": [asst.id], "gerencia_id": None})

        assert _grupos(alvo) == {"Controle", "Assistente Administrativo"}

    def test_editar_pessoa_do_dat_sem_vinculo_mantem_o_grupo_dat(self, api_client, root):
        alvo = UsuarioFactory(username="dat_2071", cpf="92071000002")
        alvo.groups.add(GroupFactory(name="DAT"))

        _salvar(api_client, root, alvo, {"telefone": "85911112222", "group_ids": [], "gerencia_id": None})

        assert _grupos(alvo) == {"DAT"}

    def test_grupo_de_permissao_fica(self, api_client, root):
        formador = GroupFactory(name="Formador")
        alvo = UsuarioFactory(username="prog_2071", cpf="92071000003")
        alvo.groups.add(GroupFactory(name="Programador"), formador)

        _salvar(api_client, root, alvo, {"group_ids": [formador.id], "gerencia_id": None})

        assert _grupos(alvo) == {"Programador", "Formador"}

    def test_funcoes_sao_substituidas(self, api_client, root):
        formador, coord, gerente = (GroupFactory(name=n) for n in ("Formador", "Coordenador", "Gerente"))
        alvo = UsuarioFactory(username="func_2071", cpf="92071000004")
        alvo.groups.add(formador, coord)

        _salvar(api_client, root, alvo, {"group_ids": [gerente.id], "gerencia_id": None})

        assert _grupos(alvo) == {"Gerente"}

    def test_funcao_classificada_na_tela_de_grupos_tambem_e_substituida(self, api_client, root):
        formador = GroupFactory(name="Formador")
        dinamica = GroupFactory(name="Funcao Dinamica 2071")
        GroupClassificacao.objects.create(group=dinamica, tipo=GroupClassificacao.Tipo.FUNCAO)
        alvo = UsuarioFactory(username="dinamica_2071", cpf="92071000005")
        alvo.groups.add(dinamica)

        _salvar(api_client, root, alvo, {"group_ids": [formador.id], "gerencia_id": None})

        assert _grupos(alvo) == {"Formador"}

    def test_trocar_a_gerencia_troca_o_grupo_de_setor(self, api_client, root):
        formador, grupo_fluir = GroupFactory(name="Formador"), GroupFactory(name="Fluir")
        GroupFactory(name="Vidas")
        fluir = Gerencia.objects.create(nome="G FLUIR 2071", nome_setor="Fluir", setor_canonico="Fluir", ativo=True)
        vidas = Gerencia.objects.create(nome="G VIDAS 2071", nome_setor="Vidas", setor_canonico="Vidas", ativo=True)
        alvo = UsuarioFactory(username="troca_2071", cpf="92071000006")
        alvo.groups.add(formador, grupo_fluir)
        EquipeGerencia.objects.create(gerencia=fluir, usuario=alvo, papel="FORMADOR", ativo=True)

        _salvar(api_client, root, alvo, {"group_ids": [formador.id], "gerencia_id": vidas.id})

        assert _grupos(alvo) == {"Formador", "Vidas"}

    def test_trocar_a_gerencia_mantem_o_setor_ainda_justificado_por_outro_vinculo(self, api_client, root):
        formador, grupo_vidas = GroupFactory(name="Formador"), GroupFactory(name="Vidas")
        GroupFactory(name="Fluir")
        vidas_a = Gerencia.objects.create(
            nome="G VIDAS A 2071", nome_setor="Vidas A", setor_canonico="Vidas", ativo=True
        )
        vidas_b = Gerencia.objects.create(
            nome="G VIDAS B 2071", nome_setor="Vidas B", setor_canonico="Vidas", ativo=True
        )
        fluir = Gerencia.objects.create(nome="G FLUIR B 2071", nome_setor="Fluir", setor_canonico="Fluir", ativo=True)
        alvo = UsuarioFactory(username="dois_vidas_2071", cpf="92071000010")
        alvo.groups.add(formador, grupo_vidas)
        EquipeGerencia.objects.create(gerencia=vidas_a, usuario=alvo, papel="FORMADOR", ativo=True)
        EquipeGerencia.objects.create(gerencia=vidas_b, usuario=alvo, papel="FORMADOR", ativo=True)

        _salvar(api_client, root, alvo, {"group_ids": [formador.id], "gerencia_id": fluir.id})

        assert _grupos(alvo) == {"Formador", "Vidas", "Fluir"}


@pytest.mark.django_db
class TestVinculosQueOFormularioNaoMostra:
    def test_salvar_sem_mudar_lotacao_nao_mexe_em_vinculo(self, api_client, root):
        """Grupo Formador com vínculo COORDENADOR: salvar o telefone não converte o papel."""
        formador = GroupFactory(name="Formador")
        g = Gerencia.objects.create(nome="G SUPER 2071", nome_setor="Super", setor_canonico="", ativo=True)
        alvo = UsuarioFactory(username="lara_2071", cpf="92071000007")
        alvo.groups.add(formador)
        EquipeGerencia.objects.create(gerencia=g, usuario=alvo, papel="COORDENADOR", ativo=True)

        _salvar(api_client, root, alvo, {"telefone": "85933334444", "group_ids": [formador.id], "gerencia_id": g.id})

        ativos = set(EquipeGerencia.objects.filter(usuario=alvo, ativo=True).values_list("papel", flat=True))
        assert ativos == {"COORDENADOR"}

    def test_mudar_funcao_nao_encerra_vinculo_em_outra_gerencia(self, api_client, root):
        """Duas gerências: o form mostra a primeira; o vínculo da segunda fica."""
        coord, formador, gerente = (GroupFactory(name=n) for n in ("Coordenador", "Formador", "Gerente"))
        exibida = Gerencia.objects.create(nome="G LER 2071", nome_setor="Ler", setor_canonico="", ativo=True)
        outra = Gerencia.objects.create(nome="G BRINCANDO 2071", nome_setor="Brincando", setor_canonico="", ativo=True)
        alvo = UsuarioFactory(username="lourene_2071", cpf="92071000008")
        alvo.groups.add(coord, formador)
        EquipeGerencia.objects.create(gerencia=exibida, usuario=alvo, papel="COORDENADOR", ativo=True)
        EquipeGerencia.objects.create(gerencia=outra, usuario=alvo, papel="FORMADOR", ativo=True)

        _salvar(
            api_client,
            root,
            alvo,
            {"group_ids": [coord.id, formador.id, gerente.id], "gerencia_id": exibida.id},
        )

        assert EquipeGerencia.objects.filter(usuario=alvo, gerencia=outra, papel="FORMADOR", ativo=True).exists()
        assert EquipeGerencia.objects.filter(usuario=alvo, gerencia=exibida, papel="GERENTE", ativo=True).exists()
