"""
S3 (auditoria de segurança 14/10, achado C4): o `setor_canonico` da gerência não concede poder.

Antes, `setor_canonico` aceitava texto livre e `setor_group_for` derivava o grupo de mesmo nome na
lotação pela tela de Usuários. `PATCH {"setor_canonico": "DAT"}` numa gerência e, depois, lotar
alguém nela dava o grupo DAT (cadastros, compras, importação) sem aparecer no formulário.

Regras:
- `setor_group_for` nunca deriva grupo que tenha capacidade funcional (lido do banco: grupo com
  `PermissaoFuncional` ligada). O poder do DAT vem do pacote do perfil da gerência (ADR-020).
- `validate_setor_canonico`: o valor atual sempre passa (salvar sem mexer = 200). Valor NOVO é
  recusado (400) se for nome de grupo com capacidade ou se não for um setor conhecido
  (`SETORES_PRODUTO` ∪ `setor_canonico` já gravado em alguma gerência ∪ vazio).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

from django.contrib.auth.models import Group
from django.core.cache import cache
from rest_framework.test import APIClient

import pytest

from apps.core.models import Gerencia
from apps.core.services.equipe_gerencia import setor_group_for
from apps.core.tests.factories import GroupFactory, UsuarioFactory

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _limpa_cache(db):
    cache.clear()
    yield
    cache.clear()


def _root_client() -> APIClient:
    client = APIClient()
    client.force_authenticate(UsuarioFactory(superuser=True))
    return client


def _grupos_com_capacidade() -> set[str]:
    return set(Group.objects.filter(permissoes_funcionais__isnull=False).values_list("name", flat=True))


def _gerencia(nome: str, setor: str) -> Gerencia:
    return Gerencia.objects.create(nome=nome, nome_setor=nome, setor_canonico=setor, ativo=True)


class TestSetorGroupFor:
    def test_o_seed_tem_grupos_com_capacidade(self):
        # Sentinela: sem isso os testes abaixo passariam no vazio. A Superintendência perdeu as
        # capacidades no PR 10 (0126), mas segue recusada por compor o par aprovador legado.
        assert {"DAT", "Controle", "Diretoria"} <= _grupos_com_capacidade()

    def test_nenhum_grupo_com_capacidade_e_derivado(self):
        for i, nome in enumerate(sorted(_grupos_com_capacidade())):
            assert setor_group_for(_gerencia(f"G CAP {i}", nome)) is None, nome

    def test_gerencia_dat_nao_deriva_o_grupo_dat(self):
        assert setor_group_for(_gerencia("GERENCIA DAT S3", "DAT")) is None

    def test_grupo_de_setor_sem_capacidade_continua_derivado(self):
        vidas = GroupFactory(name="Vidas")
        assert not vidas.permissoes_funcionais.exists()
        assert setor_group_for(_gerencia("G VIDAS S3", "Vidas")) == vidas


class TestLotacaoPelaTela:
    def test_lotar_na_gerencia_dat_nao_da_o_grupo_dat(self):
        formador = GroupFactory(name="Formador")
        g19 = _gerencia("GERENCIA DAT S3 TELA", "DAT")
        alvo = UsuarioFactory(username="lotado_dat_s3", cpf="93000000001")

        resp = _root_client().patch(
            f"/api/usuarios-admin/{alvo.id}/", {"group_ids": [formador.id], "gerencia_id": g19.id}, format="json"
        )

        assert resp.status_code == 200, resp.data
        assert set(alvo.groups.values_list("name", flat=True)) == {"Formador"}

    def test_lotar_em_gerencia_vidas_continua_dando_o_grupo_vidas(self):
        formador = GroupFactory(name="Formador")
        GroupFactory(name="Vidas")
        vidas = _gerencia("G VIDAS S3 TELA", "Vidas")
        alvo = UsuarioFactory(username="lotado_vidas_s3", cpf="93000000002")

        resp = _root_client().patch(
            f"/api/usuarios-admin/{alvo.id}/", {"group_ids": [formador.id], "gerencia_id": vidas.id}, format="json"
        )

        assert resp.status_code == 200, resp.data
        assert set(alvo.groups.values_list("name", flat=True)) == {"Formador", "Vidas"}

    def test_sair_da_gerencia_dat_tira_o_grupo_dat_como_antes(self):
        # Revisão do S3: o filtro de capacidade vale só para o grupo que ENTRA. Quem já tem o grupo DAT
        # (lotação antiga na gerência de setor "DAT") e é transferido continua perdendo o DAT, como na main.
        formador = GroupFactory(name="Formador")
        GroupFactory(name="Vidas")
        g19 = _gerencia("GERENCIA DAT S3 SAIDA", "DAT")
        vidas = _gerencia("G VIDAS S3 SAIDA", "Vidas")
        alvo = UsuarioFactory(username="saida_dat_s3", cpf="93000000003")
        client = _root_client()
        resp = client.patch(
            f"/api/usuarios-admin/{alvo.id}/", {"group_ids": [formador.id], "gerencia_id": g19.id}, format="json"
        )
        assert resp.status_code == 200, resp.data
        alvo.groups.add(Group.objects.get(name="DAT"))

        resp = client.patch(
            f"/api/usuarios-admin/{alvo.id}/", {"group_ids": [formador.id], "gerencia_id": vidas.id}, format="json"
        )

        assert resp.status_code == 200, resp.data
        assert set(alvo.groups.values_list("name", flat=True)) == {"Formador", "Vidas"}


class TestValidateSetorCanonico:
    @pytest.mark.parametrize("setor", ["DAT", "Controle", "Diretoria", "Superintendência"])
    def test_patch_para_grupo_com_capacidade_devolve_400(self, setor):
        ger = _gerencia("G FLUIR S3", "Fluir")

        resp = _root_client().patch(f"/api/gerencias/{ger.id}/", {"setor_canonico": setor}, format="json")

        assert resp.status_code == 400, resp.content
        assert "setor_canonico" in resp.data["errors"]
        ger.refresh_from_db()
        assert ger.setor_canonico == "Fluir"

    def test_criar_gerencia_com_setor_dat_devolve_400(self):
        resp = _root_client().post(
            "/api/gerencias/", {"nome": "NOVA S3", "nome_setor": "Nova", "setor_canonico": "DAT"}, format="json"
        )

        assert resp.status_code == 400, resp.content
        assert "setor_canonico" in resp.data["errors"]

    def test_patch_para_setor_desconhecido_devolve_400(self):
        ger = _gerencia("G FLUIR S3 B", "Fluir")

        resp = _root_client().patch(f"/api/gerencias/{ger.id}/", {"setor_canonico": "Qualquer Coisa"}, format="json")

        assert resp.status_code == 400, resp.content

    @pytest.mark.parametrize("atual", ["DAT", "SOU DA PAZ", "Superativar", "Superintendência", ""])
    def test_salvar_sem_mudar_o_setor_continua_200(self, atual):
        # Valores de produção de hoje (fora de SETORES_PRODUTO ou nome de grupo com poder) não travam
        # o salvar da gerência: a tela reenvia o valor atual.
        ger = _gerencia(f"G ATUAL S3 {len(atual)}", atual)

        resp = _root_client().patch(
            f"/api/gerencias/{ger.id}/", {"setor_canonico": atual, "descricao": "nova"}, format="json"
        )

        assert resp.status_code == 200, resp.content
        ger.refresh_from_db()
        assert ger.setor_canonico == atual
        assert ger.descricao == "nova"

    @pytest.mark.parametrize("novo", ["Vidas", "Brincando e Aprendendo", "TRÂNSITO LEGAL", ""])
    def test_setor_conhecido_e_aceito(self, novo):
        # SETORES_PRODUTO, valor já em uso em outra gerência ou vazio.
        _gerencia("G TRANSITO S3", "TRÂNSITO LEGAL")
        ger = _gerencia("G FLUIR S3 C", "Fluir")

        resp = _root_client().patch(f"/api/gerencias/{ger.id}/", {"setor_canonico": novo}, format="json")

        assert resp.status_code == 200, resp.content
        ger.refresh_from_db()
        assert ger.setor_canonico == novo

    def test_valor_em_uso_que_e_grupo_com_capacidade_nao_vale_para_outra_gerencia(self):
        _gerencia("GERENCIA DAT S3 USO", "DAT")
        ger = _gerencia("G FLUIR S3 D", "Fluir")

        resp = _root_client().patch(f"/api/gerencias/{ger.id}/", {"setor_canonico": "DAT"}, format="json")

        assert resp.status_code == 400, resp.content
