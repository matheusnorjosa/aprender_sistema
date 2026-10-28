"""
Testes: o projeto é obrigatório na escrita da solicitação (revisão do #2149).

Sem projeto o evento nascia pendente e pulava a regra da compra e o escopo de gerência do projeto
(`projeto_fora_da_gerencia` isenta `None`, contando com o serializer). O FK continua `null=True`
por causa do dado legado e dos importadores (gravam pelo ORM); a API é que passa a exigir:

- POST sem a chave `projeto` ou com `projeto: null` → 400 no campo `projeto`, nada criado;
- PATCH/PUT com `projeto: null` → 400 no campo `projeto`, nada muda;
- PATCH que não toca no projeto segue passando, inclusive em evento legado sem projeto.

O lote (`/api/solicitacoes/lote/`) usa o mesmo serializer por evento: ver `test_solicitacao_lote.py`.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false

from __future__ import annotations

from datetime import datetime
from datetime import timezone as dt_timezone

from rest_framework.test import APIClient

import pytest

from apps.core.models import Solicitacao
from apps.core.tests.conftest import get_field_errors
from apps.core.tests.factories import (
    GerenciaFactory,
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
    com_papel,
    liberar_par,
)

pytestmark = pytest.mark.django_db

URL = "/api/solicitacoes/"
MENSAGEM = "Informe o projeto do evento."
INICIO = datetime(2027, 4, 12, 12, 0, tzinfo=dt_timezone.utc)
FIM = datetime(2027, 4, 12, 15, 0, tzinfo=dt_timezone.utc)


@pytest.fixture
def gerencia():
    return GerenciaFactory(pergunta_avaliar_formador=False)


@pytest.fixture
def coordenador(gerencia):
    user = UsuarioFactory(username="coord_projeto_obrig")
    com_papel(user, "COORDENADOR", gerencia)
    return user


@pytest.fixture
def municipio():
    return MunicipioFactory(nome="Cidade Projeto Obrigatorio", uf="CE")


@pytest.fixture
def tipo_evento():
    return TipoEventoFactory(nome="Formação Projeto Obrigatório")


@pytest.fixture
def projeto(gerencia, municipio):
    projeto = ProjetoFactory(nome="Projeto Obrigatorio", gerencia=gerencia)
    liberar_par(municipio, projeto)
    return projeto


def _client(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _payload(municipio, tipo_evento, **extra):
    payload = {
        "municipio": municipio.pk,
        "tipo_evento": tipo_evento.pk,
        "coordenador_acompanha": False,
        "inicio": INICIO.isoformat(),
        "fim": FIM.isoformat(),
    }
    payload.update(extra)
    return payload


def _assert_erro_no_projeto(response):
    assert response.status_code == 400, response.data
    erros = get_field_errors(response)
    assert erros["projeto"] == [MENSAGEM]


class TestCriacao:
    def test_sem_a_chave_projeto_da_400_e_nada_e_criado(self, coordenador, municipio, tipo_evento):
        antes = Solicitacao.objects.count()

        response = _client(coordenador).post(URL, _payload(municipio, tipo_evento), format="json")

        _assert_erro_no_projeto(response)
        assert Solicitacao.objects.count() == antes

    def test_projeto_null_da_400_e_nada_e_criado(self, coordenador, municipio, tipo_evento):
        antes = Solicitacao.objects.count()

        response = _client(coordenador).post(URL, _payload(municipio, tipo_evento, projeto=None), format="json")

        _assert_erro_no_projeto(response)
        assert Solicitacao.objects.count() == antes

    def test_com_projeto_cria(self, coordenador, municipio, tipo_evento, projeto):
        response = _client(coordenador).post(URL, _payload(municipio, tipo_evento, projeto=projeto.pk), format="json")

        assert response.status_code == 201, response.data
        assert Solicitacao.objects.get(pk=response.data["id"]).projeto_id == projeto.pk


class TestEdicao:
    @pytest.fixture
    def evento(self, coordenador, municipio, tipo_evento, projeto):
        return SolicitacaoFactory(
            usuario=coordenador,
            coordenador=coordenador,
            municipio=municipio,
            projeto=projeto,
            tipo_evento=tipo_evento,
            inicio=INICIO,
            fim=FIM,
            status="aprovado",
        )

    def test_patch_projeto_null_da_400_e_nada_muda(self, coordenador, evento, projeto):
        response = _client(coordenador).patch(f"{URL}{evento.pk}/", {"projeto": None}, format="json")

        _assert_erro_no_projeto(response)
        evento.refresh_from_db()
        assert evento.projeto_id == projeto.pk
        assert evento.status == "aprovado"

    def test_put_projeto_null_da_400(self, coordenador, evento, municipio, tipo_evento, projeto):
        response = _client(coordenador).put(
            f"{URL}{evento.pk}/", _payload(municipio, tipo_evento, projeto=None), format="json"
        )

        _assert_erro_no_projeto(response)
        evento.refresh_from_db()
        assert evento.projeto_id == projeto.pk

    def test_patch_que_nao_toca_no_projeto_passa(self, coordenador, evento, projeto):
        response = _client(coordenador).patch(f"{URL}{evento.pk}/", {"observacoes": "nova"}, format="json")

        assert response.status_code == 200, response.data
        evento.refresh_from_db()
        assert evento.observacoes == "nova"
        assert evento.projeto_id == projeto.pk

    def test_evento_legado_sem_projeto_edita_sem_informar_projeto(self, coordenador, municipio, tipo_evento):
        """Linha antiga sem projeto (gravada pelo ORM): editar a observação não exige escolher projeto."""
        legado = SolicitacaoFactory(
            usuario=coordenador,
            coordenador=coordenador,
            municipio=municipio,
            projeto=None,
            tipo_evento=tipo_evento,
            inicio=INICIO,
            fim=FIM,
            status="aprovado",
        )

        response = _client(coordenador).patch(f"{URL}{legado.pk}/", {"observacoes": "ajuste"}, format="json")

        assert response.status_code == 200, response.data
        legado.refresh_from_db()
        assert legado.observacoes == "ajuste"
        assert legado.projeto_id is None
