"""
Testes: o município é obrigatório na escrita da solicitação (molde do projeto, #2151).

Sem município a regra da compra (Regra 4 do serializer) não tinha o par para conferir e pulava: quem
não é isento criava ou editava evento de projeto sem compra em lugar nenhum. O FK continua
`null=True` (dado legado e importadores gravam pelo ORM); a API é que passa a exigir, de todos:

- POST sem a chave `municipio` ou com `municipio: null` → 400 no campo `municipio`, nada criado;
- item do lote sem município → erro no índice certo, nada criado;
- PATCH/PUT com `municipio: null` → 400 no campo `municipio`, nada muda;
- PATCH que não toca no município segue passando, inclusive em evento antigo sem município;
- evento antigo sem município + PATCH que troca o projeto: 400 para quem não é isento (a Regra 4
  não pula mais); o isento segue passando.
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
URL_LOTE = "/api/solicitacoes/lote/"
MENSAGEM = "Informe o município do evento."
INICIO = datetime(2027, 4, 12, 12, 0, tzinfo=dt_timezone.utc)
FIM = datetime(2027, 4, 12, 15, 0, tzinfo=dt_timezone.utc)


@pytest.fixture
def gerencia():
    return GerenciaFactory(pergunta_avaliar_formador=False)


@pytest.fixture
def coordenador(gerencia):
    user = UsuarioFactory(username="coord_municipio_obrig")
    com_papel(user, "COORDENADOR", gerencia)
    return user


@pytest.fixture
def superusuario():
    """Isento da regra da compra (superuser)."""
    return UsuarioFactory(username="super_municipio_obrig", superuser=True)


@pytest.fixture
def municipio():
    return MunicipioFactory(nome="Cidade Municipio Obrigatorio", uf="CE")


@pytest.fixture
def tipo_evento():
    return TipoEventoFactory(nome="Formação Município Obrigatório")


@pytest.fixture
def projeto(gerencia, municipio):
    projeto = ProjetoFactory(nome="Projeto Municipio Obrigatorio", gerencia=gerencia)
    liberar_par(municipio, projeto)
    return projeto


@pytest.fixture
def projeto_sem_compra(gerencia):
    """Projeto sem compra em município nenhum: o furo de verdade."""
    return ProjetoFactory(nome="Projeto Sem Compra Nenhuma", gerencia=gerencia)


def _client(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _payload(projeto, tipo_evento, **extra):
    payload = {
        "projeto": projeto.pk,
        "tipo_evento": tipo_evento.pk,
        "coordenador_acompanha": False,
        "inicio": INICIO.isoformat(),
        "fim": FIM.isoformat(),
    }
    payload.update(extra)
    return payload


def _assert_erro_no_municipio(response):
    assert response.status_code == 400, response.data
    erros = get_field_errors(response)
    assert erros["municipio"] == [MENSAGEM]


class TestCriacao:
    def test_sem_a_chave_municipio_da_400_e_nada_e_criado(self, coordenador, projeto, tipo_evento):
        antes = Solicitacao.objects.count()

        response = _client(coordenador).post(URL, _payload(projeto, tipo_evento), format="json")

        _assert_erro_no_municipio(response)
        assert Solicitacao.objects.count() == antes

    def test_municipio_null_da_400_e_nada_e_criado(self, coordenador, projeto, tipo_evento):
        antes = Solicitacao.objects.count()

        response = _client(coordenador).post(URL, _payload(projeto, tipo_evento, municipio=None), format="json")

        _assert_erro_no_municipio(response)
        assert Solicitacao.objects.count() == antes

    def test_projeto_sem_compra_em_lugar_nenhum_nao_passa_sem_municipio(
        self, coordenador, projeto_sem_compra, tipo_evento
    ):
        """O furo: sem município, o projeto sem compra nenhuma nascia evento."""
        antes = Solicitacao.objects.count()

        response = _client(coordenador).post(URL, _payload(projeto_sem_compra, tipo_evento), format="json")

        _assert_erro_no_municipio(response)
        assert Solicitacao.objects.count() == antes

    def test_isento_tambem_informa_o_municipio(self, superusuario, projeto, tipo_evento):
        antes = Solicitacao.objects.count()

        response = _client(superusuario).post(URL, _payload(projeto, tipo_evento), format="json")

        _assert_erro_no_municipio(response)
        assert Solicitacao.objects.count() == antes

    def test_com_municipio_cria(self, coordenador, municipio, projeto, tipo_evento):
        response = _client(coordenador).post(URL, _payload(projeto, tipo_evento, municipio=municipio.pk), format="json")

        assert response.status_code == 201, response.data
        assert Solicitacao.objects.get(pk=response.data["id"]).municipio_id == municipio.pk


class TestLote:
    def test_item_sem_municipio_da_erro_no_indice_e_nada_e_criado(self, coordenador, municipio, projeto, tipo_evento):
        com_municipio = _payload(projeto, tipo_evento, municipio=municipio.pk)
        sem_chave = _payload(
            projeto,
            tipo_evento,
            inicio=datetime(2027, 4, 13, 12, 0, tzinfo=dt_timezone.utc).isoformat(),
            fim=datetime(2027, 4, 13, 15, 0, tzinfo=dt_timezone.utc).isoformat(),
        )
        nulo = _payload(
            projeto,
            tipo_evento,
            municipio=None,
            inicio=datetime(2027, 4, 14, 12, 0, tzinfo=dt_timezone.utc).isoformat(),
            fim=datetime(2027, 4, 14, 15, 0, tzinfo=dt_timezone.utc).isoformat(),
        )
        antes = Solicitacao.objects.count()

        response = _client(coordenador).post(URL_LOTE, {"eventos": [com_municipio, sem_chave, nulo]}, format="json")

        assert response.status_code == 400, response.data
        assert response.data["code"] == "lote_invalido"
        itens = {i["indice"]: i for i in response.data["errors"]["itens"]}
        assert list(itens) == [1, 2]
        for indice in (1, 2):
            assert itens[indice]["code"] == "VALIDATION_ERROR"
            assert itens[indice]["errors"]["municipio"] == [MENSAGEM]
        assert Solicitacao.objects.count() == antes


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

    @pytest.fixture
    def antigo(self, coordenador, tipo_evento, projeto):
        """Linha antiga sem município, gravada pelo ORM (como o legado e os importadores)."""
        return SolicitacaoFactory(
            usuario=coordenador,
            coordenador=coordenador,
            municipio=None,
            projeto=projeto,
            tipo_evento=tipo_evento,
            inicio=INICIO,
            fim=FIM,
            status="aprovado",
        )

    def test_patch_municipio_null_da_400_e_nada_muda(self, coordenador, evento, municipio):
        response = _client(coordenador).patch(f"{URL}{evento.pk}/", {"municipio": None}, format="json")

        _assert_erro_no_municipio(response)
        evento.refresh_from_db()
        assert evento.municipio_id == municipio.pk
        assert evento.status == "aprovado"

    def test_patch_municipio_null_com_projeto_sem_compra_da_400(
        self, coordenador, evento, municipio, projeto, projeto_sem_compra
    ):
        response = _client(coordenador).patch(
            f"{URL}{evento.pk}/", {"municipio": None, "projeto": projeto_sem_compra.pk}, format="json"
        )

        _assert_erro_no_municipio(response)
        evento.refresh_from_db()
        assert evento.municipio_id == municipio.pk
        assert evento.projeto_id == projeto.pk

    def test_put_municipio_null_da_400(self, coordenador, evento, municipio, projeto, tipo_evento):
        response = _client(coordenador).put(
            f"{URL}{evento.pk}/", _payload(projeto, tipo_evento, municipio=None), format="json"
        )

        _assert_erro_no_municipio(response)
        evento.refresh_from_db()
        assert evento.municipio_id == municipio.pk

    def test_patch_que_nao_toca_no_municipio_passa(self, coordenador, evento, municipio):
        response = _client(coordenador).patch(f"{URL}{evento.pk}/", {"observacoes": "nova"}, format="json")

        assert response.status_code == 200, response.data
        evento.refresh_from_db()
        assert evento.observacoes == "nova"
        assert evento.municipio_id == municipio.pk

    def test_evento_antigo_sem_municipio_edita_sem_informar_municipio(self, coordenador, antigo):
        response = _client(coordenador).patch(f"{URL}{antigo.pk}/", {"observacoes": "ajuste"}, format="json")

        assert response.status_code == 200, response.data
        antigo.refresh_from_db()
        assert antigo.observacoes == "ajuste"
        assert antigo.municipio_id is None

    def test_evento_antigo_sem_municipio_trocar_projeto_da_400_para_nao_isento(
        self, coordenador, antigo, projeto, projeto_sem_compra
    ):
        """A Regra 4 não pula mais o município vazio: trocar o projeto exige o par completo."""
        response = _client(coordenador).patch(f"{URL}{antigo.pk}/", {"projeto": projeto_sem_compra.pk}, format="json")

        _assert_erro_no_municipio(response)
        antigo.refresh_from_db()
        assert antigo.projeto_id == projeto.pk
        assert antigo.municipio_id is None

    def test_evento_antigo_sem_municipio_trocar_projeto_passa_para_isento(
        self, superusuario, antigo, projeto_sem_compra
    ):
        response = _client(superusuario).patch(f"{URL}{antigo.pk}/", {"projeto": projeto_sem_compra.pk}, format="json")

        assert response.status_code == 200, response.data
        antigo.refresh_from_db()
        assert antigo.projeto_id == projeto_sem_compra.pk
        assert antigo.municipio_id is None
