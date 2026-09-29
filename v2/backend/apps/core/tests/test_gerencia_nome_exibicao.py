"""
PR A — setor = gerência na tela (PLANOS_LIBERACAO_2026-09-29 §0 e §2).

O nome que a tela mostra fica num campo próprio, `Gerencia.nome_exibicao`, e a
property `rotulo = nome_exibicao or nome_setor`. O fallback NUNCA chega a `nome`
("GERENCIA 4", "INDIVIDUAL - X"): `nome` é chave técnica, `nome_setor` é o rótulo
das planilhas (import) e não é reescrito.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

import itertools

from rest_framework.test import APIClient

import pytest

from apps.core.models import EquipeGerencia, Gerencia
from apps.core.serializers import ProjetoSerializer
from apps.core.tests.factories import GroupFactory, ProjetoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

_SEQ = itertools.count(1)


def _gerencia(**kwargs) -> Gerencia:
    n = next(_SEQ)
    kwargs.setdefault("nome", f"GERENCIA NE {n}")
    kwargs.setdefault("nome_setor", f"Setor NE {n}")
    return Gerencia.objects.create(**kwargs)


def _root_client() -> APIClient:
    client = APIClient()
    client.force_authenticate(user=UsuarioFactory(superuser=True))
    return client


class TestRotulo:
    def test_rotulo_usa_nome_exibicao_quando_preenchido(self):
        g = _gerencia(nome="GERENCIA 4 NE", nome_setor="ACerta", nome_exibicao="Superativar")
        assert g.rotulo == "Superativar"

    def test_rotulo_cai_para_nome_setor_e_nunca_para_nome(self):
        g = _gerencia(nome="GERENCIA 2 NE", nome_setor="Vidas")
        assert g.nome_exibicao == ""
        assert g.rotulo == "Vidas"
        g.nome_setor = ""
        assert g.rotulo == ""  # nunca "GERENCIA 2 NE"


class TestGerenciaApi:
    def test_rotulo_e_somente_leitura_e_nome_exibicao_e_gravavel(self):
        g = _gerencia(nome_setor="ACerta")
        resp = _root_client().patch(
            f"/api/gerencias/{g.id}/", {"nome_exibicao": "Superativar", "rotulo": "Hackeado"}, format="json"
        )
        assert resp.status_code == 200, resp.data
        assert resp.data["nome_exibicao"] == "Superativar"
        assert resp.data["rotulo"] == "Superativar"
        g.refresh_from_db()
        assert g.nome_exibicao == "Superativar"
        assert g.nome_setor == "ACerta"  # nome_setor não é tocado

    def test_filtro_ativo_true_exclui_inativas(self):
        ativa = _gerencia(nome_exibicao="Ativa NE", ativo=True)
        inativa = _gerencia(nome_exibicao="Inativa NE", ativo=False)
        resp = _root_client().get("/api/gerencias/", {"ativo": "true", "page_size": 1000})
        assert resp.status_code == 200
        rows = resp.data["results"]
        ids = {r["id"] for r in rows}
        assert ativa.id in ids
        assert inativa.id not in ids
        assert next(r for r in rows if r["id"] == ativa.id)["rotulo"] == "Ativa NE"

    def test_ordena_pelo_rotulo(self):
        """A tela de Gerências ordena pelo nome de tela (paginação no servidor)."""
        _gerencia(nome="ORD A", nome_setor="Zeta Ord", nome_exibicao="Beta Ord")
        _gerencia(nome="ORD B", nome_setor="Alfa Ord")
        _gerencia(nome="ORD C", nome_setor="Aaa Ord", nome_exibicao="Gama Ord")
        resp = _root_client().get("/api/gerencias/", {"ordering": "rotulo_ordem", "search": "Ord", "page_size": 1000})
        assert resp.status_code == 200
        rows = resp.data["results"]
        assert [r["rotulo"] for r in rows] == ["Alfa Ord", "Beta Ord", "Gama Ord"]


class TestUsuarioAdminLotacao:
    def test_gerencia_inativa_no_formulario_devolve_400(self):
        inativa = _gerencia(ativo=False)
        formador = GroupFactory(name="Formador")
        resp = _root_client().post(
            "/api/usuarios-admin/",
            {
                "username": "lotado_inativa",
                "email": "lotado_inativa@example.com",
                "cpf": "93000000011",
                "password": "SecurePass123!",
                "group_ids": [formador.id],
                "gerencia_id": inativa.id,
            },
            format="json",
        )
        assert resp.status_code == 400, resp.data
        assert "gerencia_id" in resp.data["errors"]
        assert not EquipeGerencia.objects.filter(gerencia=inativa).exists()

    def test_editar_quem_esta_lotado_em_gerencia_inativa_reenviando_a_atual_passa(self):
        """O form reenvia a lotação exibida; desativar a gerência não pode travar a edição."""
        inativa = _gerencia(ativo=False)
        formador = GroupFactory(name="Formador")
        user = UsuarioFactory()
        user.groups.add(formador)
        EquipeGerencia.objects.create(usuario=user, gerencia=inativa, papel="FORMADOR")
        resp = _root_client().patch(
            f"/api/usuarios-admin/{user.id}/",
            {"first_name": "Editado", "group_ids": [formador.id], "gerencia_id": inativa.id},
            format="json",
        )
        assert resp.status_code == 200, resp.data
        user.refresh_from_db()
        assert user.first_name == "Editado"
        assert EquipeGerencia.vigentes_em().filter(usuario=user, gerencia=inativa).exists()

    def test_editar_trocando_para_outra_gerencia_inativa_devolve_400(self):
        ativa = _gerencia()
        outra_inativa = _gerencia(ativo=False)
        formador = GroupFactory(name="Formador")
        user = UsuarioFactory()
        user.groups.add(formador)
        EquipeGerencia.objects.create(usuario=user, gerencia=ativa, papel="FORMADOR")
        resp = _root_client().patch(
            f"/api/usuarios-admin/{user.id}/",
            {"group_ids": [formador.id], "gerencia_id": outra_inativa.id},
            format="json",
        )
        assert resp.status_code == 400, resp.data
        assert "gerencia_id" in resp.data["errors"]
        assert not EquipeGerencia.objects.filter(usuario=user, gerencia=outra_inativa).exists()

    def test_gerencia_atual_traz_rotulo_e_mantem_nome_setor(self):
        g = _gerencia(nome_setor="ACerta", nome_exibicao="Superativar")
        user = UsuarioFactory()
        EquipeGerencia.objects.create(usuario=user, gerencia=g, papel="COORDENADOR")
        resp = _root_client().get(f"/api/usuarios-admin/{user.id}/")
        assert resp.status_code == 200, resp.data
        atual = resp.data["gerencia_atual"]
        assert atual["rotulo"] == "Superativar"
        assert atual["nome_setor"] == "ACerta"


class TestProjetoSerializer:
    def test_gerencia_nome_e_o_rotulo(self):
        g = _gerencia(nome="GERENCIA 4 PJ", nome_setor="ACerta", nome_exibicao="Superativar")
        projeto = ProjetoFactory(gerencia=g)
        assert ProjetoSerializer(projeto).data["gerencia_nome"] == "Superativar"
