"""
Scan de segurança 16/10/2026 — `/api/solicitacoes/validate/`.

F2: o corpo passa por serializer (listas com teto de 200, e-mail válido, `participants` dict);
tipo errado dá 400, não 500; os e-mails são deduplicados e resolvidos numa consulta só.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from typing import Any

from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework import serializers
from rest_framework.test import APIClient

import pytest

from apps.core.tests.factories import (
    GerenciaFactory,
    MunicipioFactory,
    ProjetoFactory,
    TipoEventoFactory,
    UsuarioFactory,
    com_papel,
    liberar_par,
)

URL = "/api/solicitacoes/validate/"


@pytest.fixture
def cenario(db) -> dict[str, Any]:
    gerencia = GerenciaFactory()
    coord = UsuarioFactory(email="coord.validate@example.invalid")
    com_papel(coord, "COORDENADOR", gerencia)
    formador = UsuarioFactory(email="formador.validate@example.invalid")
    com_papel(formador, "FORMADOR", gerencia)
    municipio = MunicipioFactory()
    projeto = ProjetoFactory(gerencia=gerencia, fluxo="NAO_SUPER")
    liberar_par(municipio, projeto)
    return {
        "gerencia": gerencia,
        "coord": coord,
        "formador": formador,
        "municipio": municipio,
        "projeto": projeto,
        "tipo": TipoEventoFactory(),
    }


def _payload(c: dict[str, Any], participants: Any) -> dict[str, Any]:
    return {
        "municipio": {"id": c["municipio"].id},
        "projeto": {"id": c["projeto"].id},
        "tipo_evento": {"id": c["tipo"].id},
        "date": "2031-04-07",
        "start": "09:00",
        "end": "11:00",
        "participants": participants,
    }


def _post(user, body: Any):
    client = APIClient()
    client.force_authenticate(user)
    return client.post(URL, body, format="json")


@pytest.mark.django_db
class TestCorpoValidado:
    @pytest.mark.parametrize(
        "participants",
        [
            ["formador@example.invalid"],
            "texto",
            {"formadores": "formador@example.invalid"},
            {"formadores": [123]},
            {"formadores": [{"email": "x@example.invalid"}]},
            {"coord_acompanha": [None]},
            {"coordenador": ["coord@example.invalid"]},
            {"formadores": ["nao-e-email"]},
        ],
    )
    def test_tipo_errado_da_400_nao_500(self, cenario, participants):
        resp = _post(cenario["coord"], _payload(cenario, participants))
        assert resp.status_code == 400, resp.content

    def test_corpo_que_nao_e_objeto_da_400(self, cenario):
        resp = _post(cenario["coord"], ["municipio"])
        assert resp.status_code == 400

    def test_lista_acima_do_teto_da_400(self, cenario):
        emails = [f"p{i}@example.invalid" for i in range(201)]
        resp = _post(cenario["coord"], _payload(cenario, {"formadores": emails}))
        assert resp.status_code == 400

    @pytest.mark.parametrize("item", ["x", "a@b.cc"])
    def test_lista_gigante_e_recusada_pelo_tamanho_sem_validar_os_itens(self, cenario, item, monkeypatch):
        """Revisão do F2: o `ListField(max_length=)` do DRF valida TODOS os itens e só depois olha o
        tamanho, juntando um erro por item. 10 mil itens têm de dar um erro só, sem tocar nos itens."""
        chamadas = 0
        original = serializers.EmailField.to_internal_value

        def contar(self, data):
            nonlocal chamadas
            chamadas += 1
            return original(self, data)

        monkeypatch.setattr(serializers.EmailField, "to_internal_value", contar)

        resp = _post(cenario["coord"], _payload(cenario, {"formadores": [item] * 10_000}))

        assert resp.status_code == 400
        assert chamadas == 0
        erros = resp.json()["errors"]["participants"]["formadores"]
        assert len(erros) == 1 and "200" in erros[0], erros
        assert len(resp.content) < 1_000

    def test_lista_no_teto_passa(self, cenario):
        emails = [f"p{i}@example.invalid" for i in range(200)]
        resp = _post(cenario["coord"], _payload(cenario, {"formadores": emails}))
        assert resp.status_code == 200
        assert len(resp.json()["canonical"]["usuarios"]["formadores_not_found"]) == 200

    def test_resolve_e_deduplica(self, cenario):
        email = cenario["formador"].email
        resp = _post(
            cenario["coord"],
            _payload(
                cenario,
                {
                    "coordenador": cenario["coord"].email,
                    "formadores": [email, email.upper(), email],
                    "coord_acompanha": [],
                },
            ),
        )
        assert resp.status_code == 200, resp.content
        usuarios = resp.json()["canonical"]["usuarios"]
        assert usuarios["coordenador_id"] == cenario["coord"].id
        assert usuarios["formadores_ids"] == [cenario["formador"].id]
        assert usuarios["formadores_not_found"] == []

    def test_email_vazio_na_lista_e_ignorado(self, cenario):
        resp = _post(cenario["coord"], _payload(cenario, {"formadores": ["", cenario["formador"].email]}))
        assert resp.status_code == 200, resp.content
        assert resp.json()["canonical"]["usuarios"]["formadores_ids"] == [cenario["formador"].id]

    def test_email_ambiguo_nao_resolve(self, cenario):
        """Dois usuários com o mesmo e-mail: nenhum é escolhido no chute (#1658)."""
        outro = UsuarioFactory(email=cenario["formador"].email.upper())
        com_papel(outro, "FORMADOR", cenario["gerencia"])
        resp = _post(cenario["coord"], _payload(cenario, {"formadores": [cenario["formador"].email]}))
        usuarios = resp.json()["canonical"]["usuarios"]
        assert usuarios["formadores_ids"] == []
        assert usuarios["formadores_not_found"] == [cenario["formador"].email]

    def test_consultas_nao_crescem_com_a_lista(self, cenario):
        """Uma consulta para todos os e-mails, não uma por item."""

        def _contar(n: int) -> int:
            emails = [f"q{i}@example.invalid" for i in range(n)]
            with CaptureQueriesContext(connection) as ctx:
                resp = _post(cenario["coord"], _payload(cenario, {"formadores": emails}))
            assert resp.status_code == 200
            return len(ctx.captured_queries)

        _contar(1)  # aquece caches (capacidades) antes de comparar
        assert _contar(150) == _contar(1)


@pytest.mark.django_db
class TestGateEEscopo:
    """F6: só quem cria solicitação ou administra cadastros; resolve só pessoas ativas do escopo."""

    def test_formador_sem_capacidade_recebe_403(self, cenario):
        resp = _post(cenario["formador"], _payload(cenario, {"formadores": [cenario["coord"].email]}))
        assert resp.status_code == 403

    def test_conta_sem_papel_recebe_403(self, cenario):
        resp = _post(UsuarioFactory(), _payload(cenario, {}))
        assert resp.status_code == 403

    def test_pessoa_de_outra_gerencia_nao_resolve(self, cenario):
        de_fora = UsuarioFactory(email="de.fora@example.invalid")
        com_papel(de_fora, "FORMADOR", GerenciaFactory())
        resp = _post(cenario["coord"], _payload(cenario, {"formadores": [de_fora.email]}))
        usuarios = resp.json()["canonical"]["usuarios"]
        assert usuarios["formadores_ids"] == []
        assert usuarios["formadores_not_found"] == [de_fora.email]

    def test_conta_inativa_nao_resolve(self, cenario):
        inativo = UsuarioFactory(email="inativo@example.invalid", is_active=False)
        com_papel(inativo, "FORMADOR", cenario["gerencia"])
        resp = _post(cenario["coord"], _payload(cenario, {"formadores": [inativo.email]}))
        assert resp.json()["canonical"]["usuarios"]["formadores_ids"] == []

    @pytest.mark.parametrize("email", ["52998224725@placeholder.local", "52998224725@example.invalid"])
    def test_email_de_reserva_ou_com_cpf_nao_resolve(self, cenario, email):
        """Nem dentro do escopo: senão o endpoint confirma se um CPF tem conta."""
        pessoa = UsuarioFactory(email=email)
        com_papel(pessoa, "FORMADOR", cenario["gerencia"])
        resp = _post(cenario["coord"], _payload(cenario, {"formadores": [email]}))
        usuarios = resp.json()["canonical"]["usuarios"]
        assert usuarios["formadores_ids"] == []
        assert usuarios["formadores_not_found"] == [email]

    def test_dat_resolve_pessoa_de_qualquer_gerencia(self, cenario):
        from apps.core.tests.factories import GroupFactory

        dat = UsuarioFactory()
        dat.groups.add(GroupFactory(name="DAT"))
        de_fora = UsuarioFactory(email="outra.gerencia@example.invalid")
        com_papel(de_fora, "FORMADOR", GerenciaFactory())
        resp = _post(dat, _payload(cenario, {"formadores": [de_fora.email]}))
        assert resp.status_code == 200, resp.content
        assert resp.json()["canonical"]["usuarios"]["formadores_ids"] == [de_fora.id]
