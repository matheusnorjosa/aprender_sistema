"""CON-09: o Nº da formação é obrigatório no evento de formação (plano aprovado pelo dono em 23/11/2026, entrega A).

- Evento de formação = tipo Presencial, Online ou Workshop, pelo nome sem acento e sem maiúscula
  (`services/evento_de_formacao`, a definição única).
- O número (`Solicitacao.encontro`): só algarismos, de 1 a 999; aceita "3º", "3°", "03" e espaço nas pontas e
  guarda "3". Tipo que não é de formação segue com o campo livre.
- Bloqueia ao criar (avulso e lote), ao editar evento que ainda não terminou e para Publicar, Reenviar e
  Reaplicar (`motivo_nao_publicavel`). Editar evento que já terminou não é barrado. Aprovar não muda.
- O lookup de tipos manda a marca `de_formacao`; o detalhe do evento manda `tipo_evento_de_formacao`.

Fixtures sintéticos, sem dado pessoal.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportCallIssue=false, reportIndexIssue=false

from __future__ import annotations

from datetime import timedelta
from typing import cast
from unittest.mock import patch

from django.core.management import call_command
from django.test import RequestFactory, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.exceptions import ValidationAPIError
from apps.core.models import Solicitacao
from apps.core.services.evento_de_formacao import (
    MSG_NUMERO_DA_FORMACAO,
    eh_tipo_de_formacao,
    numero_da_formacao,
)
from apps.core.services.gcal.sync import CriacaoRecusada, upsert_one
from apps.core.services.gcal_fake_client import FakeCalendarClient
from apps.core.services.solicitacao_approval import approve_solicitacao
from apps.core.services.solicitacao_publish import motivo_nao_publicavel, publish_to_gcal, resync_to_gcal
from apps.core.tests.conftest import get_field_errors
from apps.core.tests.factories import (
    GerenciaFactory,
    GroupFactory,
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
    com_pacote_do_controle,
    com_papel,
    liberar_par,
)

pytestmark = pytest.mark.django_db

URL = "/api/solicitacoes/"
URL_LOTE = "/api/solicitacoes/lote/"
SEM_NUMERO = "sem_numero_da_formacao"


# ---------- a definição única ----------
@pytest.mark.parametrize(
    ("nome", "esperado"),
    [
        ("Presencial", True),
        ("presencial", True),
        ("ONLINE", True),
        ("Workshop", True),
        ("Wórkshop", True),
        (" Online ", True),
        ("Formação", False),
        ("Acompanhamento", False),
        ("Seminário", False),
        ("Aulão", False),
        ("Presencial Extra", False),
        ("", False),
        (None, False),
    ],
)
def test_eh_tipo_de_formacao(nome, esperado):
    assert eh_tipo_de_formacao(nome) is esperado


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("3", "3"),
        ("3º", "3"),
        ("3°", "3"),
        ("03", "3"),
        (" 4 ", "4"),
        ("10º", "10"),
        ("999", "999"),
        ("1", "1"),
        (None, None),
        ("", None),
        ("   ", None),
        ("0", None),
        ("00", None),
        ("1000", None),
        ("Encontro 1", None),
        ("4º EF", None),
        ("3ª", None),
        ("3 º", None),
        ("-1", None),
        ("1.5", None),
        ("²", None),
        ("１", None),  # algarismo de largura cheia: o título do Google não pode levar
        ("٣", None),  # algarismo arábico-índico
    ],
)
def test_numero_da_formacao(valor, esperado):
    assert numero_da_formacao(valor) == esperado


# ---------- criar e editar pela API ----------
@pytest.fixture
def gerencia():
    return GerenciaFactory(pergunta_avaliar_formador=False)


@pytest.fixture
def coordenador(gerencia):
    user = UsuarioFactory(username="coord_numero_formacao")
    com_papel(user, "COORDENADOR", gerencia)
    return user


@pytest.fixture
def municipio():
    return MunicipioFactory(nome="Cidade Numero Formacao", uf="CE")


@pytest.fixture
def projeto(gerencia, municipio):
    projeto = ProjetoFactory(nome="Projeto Numero Formacao", gerencia=gerencia)
    liberar_par(municipio, projeto)
    return projeto


@pytest.fixture
def presencial():
    return TipoEventoFactory(nome="Presencial")


@pytest.fixture
def online():
    return TipoEventoFactory(nome="Online")


@pytest.fixture
def workshop():
    return TipoEventoFactory(nome="Workshop")


@pytest.fixture
def reuniao():
    return TipoEventoFactory(nome="Reunião")


def _client(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _payload(projeto, municipio, tipo, *, dias: int = 30, **extra):
    inicio = timezone.now() + timedelta(days=dias)
    payload = {
        "projeto": projeto.pk,
        "municipio": municipio.pk,
        "tipo_evento": tipo.pk,
        "coordenador_acompanha": False,
        "inicio": inicio.isoformat(),
        "fim": (inicio + timedelta(hours=2)).isoformat(),
    }
    payload.update(extra)
    return payload


def _erro_no_numero(response) -> None:
    assert response.status_code == 400, response.data
    assert get_field_errors(response)["encontro"] == [MSG_NUMERO_DA_FORMACAO]


class TestCriacao:
    @pytest.mark.parametrize("encontro", [None, "", "Encontro 1", "0"])
    def test_tipo_de_formacao_sem_numero_valido_da_400(self, coordenador, projeto, municipio, workshop, encontro):
        antes = Solicitacao.objects.count()
        response = _client(coordenador).post(
            URL, _payload(projeto, municipio, workshop, encontro=encontro), format="json"
        )
        _erro_no_numero(response)
        assert Solicitacao.objects.count() == antes

    def test_sem_a_chave_encontro_da_400(self, coordenador, projeto, municipio, presencial):
        _erro_no_numero(_client(coordenador).post(URL, _payload(projeto, municipio, presencial), format="json"))

    def test_numero_com_ordinal_e_guardado_so_com_algarismos(self, coordenador, projeto, municipio, presencial):
        response = _client(coordenador).post(
            URL, _payload(projeto, municipio, presencial, encontro=" 03º "), format="json"
        )
        assert response.status_code == 201, response.data
        assert Solicitacao.objects.get(pk=response.data["id"]).encontro == "3"

    def test_tipo_que_nao_e_de_formacao_segue_livre(self, coordenador, projeto, municipio, reuniao):
        response = _client(coordenador).post(
            URL, _payload(projeto, municipio, reuniao, encontro="Encontro 1"), format="json"
        )
        assert response.status_code == 201, response.data
        assert Solicitacao.objects.get(pk=response.data["id"]).encontro == "Encontro 1"
        sem = _client(coordenador).post(URL, _payload(projeto, municipio, reuniao, dias=31), format="json")
        assert sem.status_code == 201, sem.data


class TestLote:
    def test_item_de_formacao_sem_numero_recusa_o_lote(self, coordenador, projeto, municipio, online, reuniao):
        antes = Solicitacao.objects.count()
        response = _client(coordenador).post(
            URL_LOTE,
            {
                "eventos": [
                    _payload(projeto, municipio, reuniao),
                    _payload(projeto, municipio, online, dias=31, encontro=""),
                ]
            },
            format="json",
        )
        assert response.status_code == 400, response.data
        itens = {i["indice"]: i for i in response.data["errors"]["itens"]}
        assert list(itens) == [1]
        assert itens[1]["errors"]["encontro"] == [MSG_NUMERO_DA_FORMACAO]
        assert Solicitacao.objects.count() == antes

    def test_lote_guarda_o_numero_so_com_algarismos(self, coordenador, projeto, municipio, online, presencial):
        response = _client(coordenador).post(
            URL_LOTE,
            {
                "eventos": [
                    _payload(projeto, municipio, online, encontro="3°"),
                    _payload(projeto, municipio, presencial, dias=31, encontro="12"),
                ]
            },
            format="json",
        )
        assert response.status_code == 201, response.data
        ids = [e["id"] for e in response.data["eventos"]]
        assert [Solicitacao.objects.get(pk=i).encontro for i in ids] == ["3", "12"]


class TestEdicao:
    def _evento(self, coordenador, projeto, municipio, tipo, *, dias: int, **kw) -> Solicitacao:
        inicio = timezone.now() + timedelta(days=dias)
        return SolicitacaoFactory(
            usuario=coordenador,
            coordenador=coordenador,
            municipio=municipio,
            projeto=projeto,
            tipo_evento=tipo,
            inicio=inicio,
            fim=inicio + timedelta(hours=2),
            status="aprovado",
            **kw,
        )

    def test_evento_futuro_de_formacao_sem_numero_nao_salva(self, coordenador, projeto, municipio, presencial):
        s = self._evento(coordenador, projeto, municipio, presencial, dias=10, encontro=None)
        _erro_no_numero(_client(coordenador).patch(f"{URL}{s.pk}/", {"observacoes": "nova"}, format="json"))
        s.refresh_from_db()
        assert s.observacoes != "nova"

    def test_evento_futuro_recebe_o_numero_e_salva(self, coordenador, projeto, municipio, presencial):
        s = self._evento(coordenador, projeto, municipio, presencial, dias=10, encontro=None)
        response = _client(coordenador).patch(f"{URL}{s.pk}/", {"encontro": "4º"}, format="json")
        assert response.status_code == 200, response.data
        s.refresh_from_db()
        assert s.encontro == "4"

    def test_trocar_para_tipo_de_formacao_exige_o_numero(self, coordenador, projeto, municipio, reuniao, online):
        s = self._evento(coordenador, projeto, municipio, reuniao, dias=10, encontro=None)
        _erro_no_numero(_client(coordenador).patch(f"{URL}{s.pk}/", {"tipo_evento": online.pk}, format="json"))
        s.refresh_from_db()
        assert s.tipo_evento_id == reuniao.pk

    def test_evento_que_ja_terminou_edita_sem_numero(self, coordenador, projeto, municipio, presencial):
        s = self._evento(coordenador, projeto, municipio, presencial, dias=-10, encontro=None)
        response = _client(coordenador).patch(f"{URL}{s.pk}/", {"observacoes": "ajuste"}, format="json")
        assert response.status_code == 200, response.data
        s.refresh_from_db()
        assert s.observacoes == "ajuste"

    def test_tipo_que_nao_e_de_formacao_edita_sem_numero(self, coordenador, projeto, municipio, reuniao):
        s = self._evento(coordenador, projeto, municipio, reuniao, dias=10, encontro="Encontro 1")
        response = _client(coordenador).patch(f"{URL}{s.pk}/", {"observacoes": "ajuste"}, format="json")
        assert response.status_code == 200, response.data
        s.refresh_from_db()
        assert s.encontro == "Encontro 1"

    def test_detalhe_manda_a_marca_do_tipo(self, coordenador, projeto, municipio, presencial, reuniao):
        de_formacao = self._evento(coordenador, projeto, municipio, presencial, dias=10, encontro="2")
        outro = self._evento(coordenador, projeto, municipio, reuniao, dias=11)
        client = _client(coordenador)
        assert client.get(f"{URL}{de_formacao.pk}/").data["tipo_evento_de_formacao"] is True
        assert client.get(f"{URL}{outro.pk}/").data["tipo_evento_de_formacao"] is False

    def test_lista_manda_se_falta_o_numero(self, coordenador, projeto, municipio, presencial, reuniao):
        """A Pré-agenda desabilita o Publicar com o motivo (espelho do `motivo_nao_publicavel`), sem repetir na
        tela a conferência do formato: quem diz se falta o número é o servidor."""
        sem = self._evento(coordenador, projeto, municipio, presencial, dias=10, encontro=None)
        invalido = self._evento(coordenador, projeto, municipio, presencial, dias=11, encontro="Encontro 1")
        com = self._evento(coordenador, projeto, municipio, presencial, dias=12, encontro="03")
        outro = self._evento(coordenador, projeto, municipio, reuniao, dias=13, encontro=None)
        response = _client(coordenador).get(URL, {"page_size": 50})
        assert response.status_code == 200, response.data
        falta = {linha["id"]: linha["falta_numero_da_formacao"] for linha in response.json()["results"]}
        assert falta == {sem.pk: True, invalido.pk: True, com.pk: False, outro.pk: False}


# ---------- lookup ----------
def test_lookup_de_tipos_manda_a_marca(presencial, online, workshop, reuniao):
    TipoEventoFactory(nome="Formação")
    client = _client(UsuarioFactory(username="lookup_tipos_con09"))
    response = client.get("/api/lookup/tipos-evento/")
    assert response.status_code == 200
    itens = cast(list[dict[str, object]], response.data)
    assert {i["label"]: i["de_formacao"] for i in itens} == {
        "Formação": False,
        "Online": True,
        "Presencial": True,
        "Reunião": False,
        "Workshop": True,
    }


# ---------- Publicar, Reenviar e Reaplicar (motivo_nao_publicavel) ----------
def _futuro(tipo, **kw) -> Solicitacao:
    inicio = timezone.now() + timedelta(days=3)
    return SolicitacaoFactory(status="aprovado", tipo_evento=tipo, inicio=inicio, fim=inicio + timedelta(hours=2), **kw)


def _passado(tipo, **kw) -> Solicitacao:
    inicio = timezone.now() - timedelta(days=10)
    return SolicitacaoFactory(status="aprovado", tipo_evento=tipo, inicio=inicio, fim=inicio + timedelta(hours=2), **kw)


def test_motivo_nao_publicavel_pede_o_numero(presencial, reuniao):
    assert motivo_nao_publicavel(_futuro(presencial, encontro=None)) == SEM_NUMERO
    assert motivo_nao_publicavel(_futuro(presencial, encontro="Encontro 1")) == SEM_NUMERO
    assert motivo_nao_publicavel(_futuro(presencial, encontro="4")) is None
    assert motivo_nao_publicavel(_futuro(presencial, encontro="4º")) is None
    assert motivo_nao_publicavel(_futuro(reuniao, encontro=None)) is None
    # Reenviar e Reaplicar: o que já está no Google também.
    assert (
        motivo_nao_publicavel(_futuro(presencial, encontro=None, gcal_status="PUBLISHED"), reenvio=True) == SEM_NUMERO
    )
    assert motivo_nao_publicavel(_futuro(presencial, encontro="4", gcal_status="PUBLISHED"), reenvio=True) is None
    # Os motivos de antes vêm primeiro.
    assert motivo_nao_publicavel(_passado(presencial, encontro=None)) == "evento_passado"
    assert motivo_nao_publicavel(_futuro(presencial, encontro=None, gcal_status="PUBLISHED")) == "ja_publicado"
    assert motivo_nao_publicavel(_futuro(presencial, encontro=None), reenvio=True) == "nao_publicado"


@override_settings(GCAL_CLIENT="google", GCAL_AUTH_MODE="service_account")
def test_publish_e_resync_recusam_sem_numero(presencial):
    for chamar, kw in (
        (publish_to_gcal, {}),
        (resync_to_gcal, {"gcal_status": "PUBLISHED"}),
    ):
        s = _futuro(presencial, encontro=None, **kw)
        with patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay") as task:
            task.return_value.id = "t1"
            with pytest.raises(ValidationAPIError) as exc:
                chamar(s, UsuarioFactory(), RequestFactory().post("/x/"))
        assert exc.value.code == SEM_NUMERO
        assert task.call_count == 0
        s.refresh_from_db()
        assert s.gcal_status == kw.get("gcal_status", "NONE"), "recusa não marca PENDING"


@pytest.fixture
def controle_client():
    user = UsuarioFactory(username="controle_con09", email="controle_con09@example.invalid", cpf="11144477735")
    user.groups.add(GroupFactory(name="Controle"))
    com_pacote_do_controle(user)
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@override_settings(GCAL_CLIENT="google", GCAL_AUTH_MODE="service_account")
def test_lote_de_publicacao_recusa_sem_numero(controle_client, presencial):
    sem = _futuro(presencial, encontro=None)
    com = _futuro(presencial, encontro="4")
    with patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay") as task:
        resp = controle_client.post("/api/gcal/publish-batch/", {"solicitacao_ids": [sem.id, com.id]}, format="json")
    assert resp.status_code == 202
    assert resp.data["queued"] == 1
    assert {e["id"]: e["code"] for e in resp.data["errors"]} == {sem.id: SEM_NUMERO}
    assert task.call_count == 1


@override_settings(GCAL_CLIENT="google", GCAL_AUTH_MODE="service_account")
@pytest.mark.parametrize("url", ["/api/gcal/dashboard/batch/reapply/", "/api/gcal/dashboard/batch/resync/"])
def test_reapply_e_resync_em_lote_recusam_sem_numero(controle_client, presencial, url):
    sem = _futuro(presencial, encontro=None, gcal_status="PUBLISHED")
    com = _futuro(presencial, encontro="4", gcal_status="PUBLISHED")
    with patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay") as task:
        resp = controle_client.post(url, {"ids": [sem.id, com.id]}, format="json")
    assert resp.status_code == 202
    assert resp.data["queued"] == 1
    assert {e["id"]: e["code"] for e in resp.data["errors"]} == {sem.id: SEM_NUMERO}
    assert [c.args[0] for c in task.call_args_list] == [com.id]
    sem.refresh_from_db()
    assert sem.gcal_status == "PUBLISHED", "a recusa não marca PENDING"


def test_aprovar_nao_pede_o_numero(presencial):
    """Aprovar não muda (plano, entrega A): a regra do número fica no criar, no editar e no Google."""
    s = _futuro(presencial, encontro=None)
    s.status = "pendente"
    s.save(update_fields=["status"])
    aprovador = UsuarioFactory(username="aprovador_con09", superuser=True)
    approve_solicitacao(s, aprovador, RequestFactory().post("/x/"))
    s.refresh_from_db()
    assert s.status == "aprovado"


# ---------- preagenda_to_gcal e auto-apply: a guarda do CREATE ----------
def test_guarda_do_create_recusa_formacao_sem_numero(presencial, reuniao):
    """O `upsert_one` não cria evento de formação sem o número (o `preagenda_to_gcal` e o auto-apply chegam
    nele sem passar pelo `motivo_nao_publicavel`)."""
    sem = _futuro(presencial, encontro=None)
    with pytest.raises(CriacaoRecusada) as exc:
        upsert_one(client=FakeCalendarClient(), calendar_id="cal", s=sem)
    assert exc.value.code == SEM_NUMERO
    assert upsert_one(client=FakeCalendarClient(), calendar_id="cal", s=_futuro(presencial, encontro="4")).action == (
        "CREATE"
    )
    assert upsert_one(client=FakeCalendarClient(), calendar_id="cal", s=_futuro(reuniao, encontro=None)).action == (
        "CREATE"
    )


def test_preagenda_to_gcal_pula_formacao_sem_numero(presencial):
    sem = _futuro(presencial, encontro=None)
    com = _futuro(presencial, encontro="4")
    inserts: list[str] = []
    original = FakeCalendarClient.insert

    def _conta(self, calendar_id, event_id, payload):
        inserts.append(event_id)
        return original(self, calendar_id, event_id, payload)

    with patch.object(FakeCalendarClient, "insert", _conta):
        call_command("preagenda_to_gcal", "--client", "fake", "--calendar-id", "cal", "--ids", f"{sem.id},{com.id}")
    assert inserts == [f"asv2{com.id}"]
