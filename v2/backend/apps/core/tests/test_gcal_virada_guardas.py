"""Guardas do Google Agenda para a virada (plano do importador da virada, 16/10/2026, §4 e §5).

- #1899: evento com Event ID adotado (diferente do `asv2{id}`) é atualizado PELO ID GRAVADO, e o GET que
  falha (exceção ou 404) num id adotado levanta erro em vez de cair no CREATE do `asv2{id}` (duplicata).
- Guarda única do CREATE no `upsert_one`: não cria evento que já terminou nem evento marcado
  `publicado_fora_do_sistema`. UPDATE de evento já publicado segue igual. O `preagenda_to_gcal` conta
  como SKIP e segue.
- `motivo_nao_publicavel`: Publicar (individual e lote) recusa passado, já publicado e fora do sistema;
  Reapply e Resync recusam também o evento que nunca foi publicado (`NONE`). ERROR pode tentar de novo.

Fixtures sintéticos, sem dado pessoal.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportArgumentType=false

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from django.core.management import call_command
from django.db import connection
from django.test import RequestFactory, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.exceptions import ValidationAPIError
from apps.core.models import Solicitacao
from apps.core.services.gcal.payload import build_event_payload
from apps.core.services.gcal.sync import CriacaoRecusada, apply_one_solicitacao, upsert_one
from apps.core.services.gcal.utils import _payload_hash
from apps.core.services.gcal_fake_client import FakeCalendarClient
from apps.core.services.solicitacao_publish import motivo_nao_publicavel, publish_to_gcal
from apps.core.tests.factories import GroupFactory, SolicitacaoFactory, UsuarioFactory, com_pacote_do_controle

pytestmark = pytest.mark.django_db

_PASSTHROUGH = "apps.core.services.gcal.sync._retry_with_circuit_breaker"
_ADOTADO = "0a1b2c3d4e5f6g7h8i9j0k1l2m"  # 26 caracteres base32hex, como os do v38


def _passthrough(fn, **kwargs):
    return fn()


class _Cliente:
    """Cliente mínimo que registra as chamadas. `store` = eventos que existem no Google."""

    def __init__(
        self, store: set[str] | None = None, get_exc: Exception | None = None, horas: dict[str, object] | None = None
    ) -> None:
        self.store = set(store or ())
        self.get_exc = get_exc
        self.horas = horas  # `start`/`end` que o GET devolve (o Google sempre devolve)
        self.inserts: list[str] = []
        self.updates: list[str] = []

    def get(self, calendar_id, event_id):  # noqa: ARG002
        if self.get_exc is not None:
            raise self.get_exc
        return {"id": event_id, **(self.horas or {})} if event_id in self.store else None

    def insert(self, calendar_id, event_id, payload):  # noqa: ARG002
        self.inserts.append(event_id)
        self.store.add(event_id)
        return {"id": event_id}

    def update(self, calendar_id, event_id, payload):  # noqa: ARG002
        self.updates.append(event_id)
        return {"id": event_id}

    def delete(self, calendar_id, event_id):  # noqa: ARG002
        self.store.discard(event_id)


def _futuro(**kw) -> Solicitacao:
    inicio = timezone.now() + timedelta(days=3)
    return SolicitacaoFactory(status="aprovado", inicio=inicio, fim=inicio + timedelta(hours=2), **kw)


def _passado(**kw) -> Solicitacao:
    inicio = timezone.now() - timedelta(days=10)
    return SolicitacaoFactory(status="aprovado", inicio=inicio, fim=inicio + timedelta(hours=2), **kw)


def _upsert(client, s, **kw):
    with patch(_PASSTHROUGH, side_effect=_passthrough):
        return upsert_one(client=client, calendar_id="cal", s=s, **kw)


# ---------- #1899: UPDATE pelo id gravado ----------
def test_update_vai_para_o_event_id_adotado():
    s = _futuro(external_event_id=_ADOTADO, gcal_status="PUBLISHED")
    payload = build_event_payload(s, enable_meet=False)
    client = _Cliente(store={_ADOTADO}, horas={"start": payload["start"], "end": payload["end"]})
    out = _upsert(client, s, payload=payload)
    assert out.action == "UPDATE"
    assert client.updates == [_ADOTADO], "o UPDATE tem de mirar o id gravado, não o asv2{id}"
    assert client.inserts == []
    s.refresh_from_db()
    assert s.external_event_id == _ADOTADO


def test_adotado_com_hash_igual_pula():
    s = _futuro(external_event_id=_ADOTADO, gcal_status="PUBLISHED")
    payload = build_event_payload(s, enable_meet=False)
    s.gcal_payload_hash = _payload_hash(payload)
    s.save(update_fields=["gcal_payload_hash"])
    client = _Cliente(store={_ADOTADO}, horas={"start": payload["start"], "end": payload["end"]})
    out = _upsert(client, s, payload=payload)
    assert out.action == "SKIP"
    assert client.updates == [] and client.inserts == []


def _adotado_as_14h_com_hash() -> tuple[Solicitacao, dict]:
    """Adotado das 14h às 16h (Fortaleza) daqui a 3 dias, com o hash do sistema gravado como na adoção."""
    inicio = timezone.localtime(timezone.now() + timedelta(days=3)).replace(hour=14, minute=0, second=0, microsecond=0)
    s = SolicitacaoFactory(
        status="aprovado",
        inicio=inicio,
        fim=inicio + timedelta(hours=2),
        external_event_id=_ADOTADO,
        gcal_status="PUBLISHED",
    )
    payload = build_event_payload(s, enable_meet=False)
    s.gcal_payload_hash = _payload_hash(payload)
    s.save(update_fields=["gcal_payload_hash"])
    return s, payload


def _no_google(s: Solicitacao, dias: int, hora: int) -> dict:
    """`start`/`end` como o GET devolve, `dias` depois do dia do sistema, das `hora` às `hora`+2 (-03:00)."""
    dia = timezone.localtime(s.inicio).date() + timedelta(days=dias)
    return {
        "start": {"dateTime": f"{dia.isoformat()}T{hora:02d}:00:00-03:00"},
        "end": {"dateTime": f"{dia.isoformat()}T{hora + 2:02d}:00:00-03:00"},
    }


def test_adotado_com_hash_igual_e_outra_hora_no_google_atualiza():
    """O hash do id adotado é o do sistema, não o do Google: hora diferente lá vai no UPDATE (dono, 20/10)."""
    s, payload = _adotado_as_14h_com_hash()
    client = _Cliente(store={_ADOTADO}, horas=_no_google(s, dias=0, hora=8))
    out = _upsert(client, s, payload=payload)
    assert out.action == "UPDATE"
    assert client.updates == [_ADOTADO] and client.inserts == []


def test_adotado_com_hash_igual_e_outro_dia_no_google_nao_atualiza():
    """Dia diferente = o id adotado é de outro encontro (relay 65): o PATCH mudaria o dia desse evento."""
    s, payload = _adotado_as_14h_com_hash()
    client = _Cliente(store={_ADOTADO}, horas=_no_google(s, dias=1, hora=14))
    with pytest.raises(ValueError, match="outro dia"):
        _upsert(client, s, payload=payload)
    assert client.updates == [] and client.inserts == []


def test_adotado_em_outro_dia_segue_travado_na_nova_tentativa_e_sem_hash():
    """O ERROR apaga o hash, e o Resync/Publicar também chegam sem ele: a trava não pode depender do hash."""
    s, _ = _adotado_as_14h_com_hash()
    client = _Cliente(store={_ADOTADO}, horas=_no_google(s, dias=1, hora=14))
    with patch(_PASSTHROUGH, side_effect=_passthrough):
        for _tentativa in range(2):
            with pytest.raises(ValueError, match="outro dia"):
                apply_one_solicitacao(s, apply_blocked=True, client=client)
            s.refresh_from_db()
            assert s.gcal_status == "ERROR" and s.gcal_payload_hash is None
    assert client.updates == [] and client.inserts == []


def test_get_com_excecao_num_adotado_nao_cria():
    s = _futuro(external_event_id=_ADOTADO, gcal_status="PUBLISHED")
    client = _Cliente(get_exc=RuntimeError("503 Service Unavailable"))
    with pytest.raises(Exception):
        _upsert(client, s)
    assert client.inserts == [], "GET que falha num id adotado nunca cria o asv2{id}"


def test_adotado_que_nao_existe_no_google_nao_cria():
    s = _futuro(external_event_id=_ADOTADO, gcal_status="PUBLISHED")
    client = _Cliente(store=set())
    with pytest.raises(Exception):
        _upsert(client, s)
    assert client.inserts == []


class _ClienteAdotadoCancelado(_Cliente):
    """O id adotado foi apagado no Google: o GET devolve o evento com `status=cancelled` (soft-delete)."""

    def get(self, calendar_id, event_id):  # noqa: ARG002
        return {"id": event_id, "status": "cancelled"} if event_id in self.store else None


def test_adotado_cancelado_no_google_nao_ressuscita():
    """Relay 65, ação 2: o UPDATE leva `status: confirmed` e traria de volta o evento apagado no Google."""
    s = _futuro(external_event_id=_ADOTADO, gcal_status="PUBLISHED")
    client = _ClienteAdotadoCancelado(store={_ADOTADO})
    with patch(_PASSTHROUGH, side_effect=_passthrough), pytest.raises(ValueError, match="cancelado no Google"):
        apply_one_solicitacao(s, apply_blocked=True, client=client)
    assert client.updates == [] and client.inserts == []
    s.refresh_from_db()
    assert s.external_event_id == _ADOTADO
    assert s.gcal_status == "ERROR"
    assert "cancelado no Google" in (s.gcal_last_error or ""), "o motivo fica no erro do evento"


def test_id_deterministico_gravado_segue_o_caminho_de_antes():
    s = _futuro(gcal_status="PUBLISHED")
    s.external_event_id = f"asv2{s.id}"
    s.save(update_fields=["external_event_id"])
    client = _Cliente(store={f"asv2{s.id}"})
    assert _upsert(client, s).action == "UPDATE"
    assert client.updates == [f"asv2{s.id}"]


# ---------- guarda do CREATE ----------
def test_create_recusa_evento_passado():
    s = _passado()
    client = _Cliente()
    with pytest.raises(CriacaoRecusada) as exc:
        _upsert(client, s)
    assert exc.value.code == "evento_passado"
    assert client.inserts == []


def test_create_recusa_publicado_fora_do_sistema():
    s = _futuro(publicado_fora_do_sistema=True)
    client = _Cliente()
    with pytest.raises(CriacaoRecusada) as exc:
        _upsert(client, s)
    assert exc.value.code == "publicado_fora_do_sistema"
    assert client.inserts == []


def test_create_de_evento_futuro_segue():
    s = _futuro()
    client = _Cliente()
    assert _upsert(client, s).action == "CREATE"
    assert client.inserts == [f"asv2{s.id}"]


def test_update_de_evento_passado_ja_publicado_segue():
    s = _passado(gcal_status="PUBLISHED")
    s.external_event_id = f"asv2{s.id}"
    s.save(update_fields=["external_event_id"])
    client = _Cliente(store={f"asv2{s.id}"})
    assert _upsert(client, s).action == "UPDATE"
    assert client.inserts == []


class _ClienteSoftDelete(_Cliente):
    """O DELETE do Google é soft-delete: o GET pelo `asv2{id}` acha o evento cancelado."""

    def get(self, calendar_id, event_id):  # noqa: ARG002
        return {"id": event_id, "status": "cancelled"} if event_id in self.store else None


@pytest.mark.parametrize(
    "fazer,code",
    [
        (lambda: _passado(last_sync_action="DELETE"), "evento_passado"),
        (lambda: _futuro(publicado_fora_do_sistema=True), "publicado_fora_do_sistema"),
    ],
)
def test_adopt_de_asv2_cancelado_tambem_passa_pela_guarda(fazer, code):
    """Evento tirado do Google ("Remover do Google" zera o id e o status e deixa aprovado): o GET acha o
    `asv2{id}` cancelado e o sync cairia no ADOPT, que o traz de volta (status confirmed) sem guarda."""
    s = fazer()
    client = _ClienteSoftDelete(store={f"asv2{s.id}"})
    with pytest.raises(CriacaoRecusada) as exc:
        _upsert(client, s)
    assert exc.value.code == code
    assert client.updates == [] and client.inserts == []


def test_preagenda_to_gcal_pula_passado_aprovado_e_segue():
    passado = _passado()
    futuro = _futuro()
    inserts: list[str] = []
    original = FakeCalendarClient.insert

    def _conta(self, calendar_id, event_id, payload):
        inserts.append(event_id)
        return original(self, calendar_id, event_id, payload)

    with patch.object(FakeCalendarClient, "insert", _conta):
        call_command("preagenda_to_gcal", "--client", "fake", "--calendar-id", "cal", "--json")
    assert f"asv2{passado.id}" not in inserts
    assert f"asv2{futuro.id}" in inserts


# ---------- motivo_nao_publicavel ----------
def test_motivo_nao_publicavel():
    assert motivo_nao_publicavel(_futuro()) is None
    assert motivo_nao_publicavel(_passado()) == "evento_passado"
    assert motivo_nao_publicavel(_futuro(gcal_status="PUBLISHED")) == "ja_publicado"
    assert motivo_nao_publicavel(_futuro(gcal_status="PENDING")) == "ja_publicado"
    assert motivo_nao_publicavel(_futuro(gcal_status="ERROR")) is None
    assert motivo_nao_publicavel(_futuro(publicado_fora_do_sistema=True)) == "publicado_fora_do_sistema"
    # Reenvio (Reapply/Resync): só o que já foi ao Google.
    assert motivo_nao_publicavel(_futuro(), reenvio=True) == "nao_publicado"
    assert motivo_nao_publicavel(_futuro(gcal_status="PUBLISHED"), reenvio=True) is None
    assert motivo_nao_publicavel(_futuro(gcal_status="ERROR"), reenvio=True) is None
    assert motivo_nao_publicavel(_passado(gcal_status="PUBLISHED"), reenvio=True) == "evento_passado"


@override_settings(GCAL_CLIENT="google", GCAL_AUTH_MODE="service_account")
@pytest.mark.parametrize(
    ("kw", "code"),
    [
        ({"quando": "passado"}, "evento_passado"),
        ({"gcal_status": "PUBLISHED"}, "ja_publicado"),
        ({"publicado_fora_do_sistema": True}, "publicado_fora_do_sistema"),
    ],
)
def test_publish_to_gcal_recusa(kw, code):
    quando = kw.pop("quando", "futuro")
    s = _passado(**kw) if quando == "passado" else _futuro(**kw)
    with patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay") as task:
        task.return_value.id = "t1"
        with pytest.raises(ValidationAPIError) as exc:
            publish_to_gcal(s, UsuarioFactory(), RequestFactory().post("/x/"))
    assert exc.value.code == code
    assert task.call_count == 0
    s.refresh_from_db()
    assert s.gcal_status == kw.get("gcal_status", "NONE"), "recusa não marca PENDING"


@override_settings(GCAL_CLIENT="google", GCAL_AUTH_MODE="service_account")
def test_publish_to_gcal_aceita_error():
    s = _futuro(gcal_status="ERROR")
    with patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay") as task:
        task.return_value.id = "t1"
        publish_to_gcal(s, UsuarioFactory(), RequestFactory().post("/x/"))
    assert task.call_count == 1


# ---------- lotes ----------
@pytest.fixture
def controle_client():
    user = UsuarioFactory(username="controle_virada", email="controle_virada@example.invalid", cpf="11144477735")
    user.groups.add(GroupFactory(name="Controle"))
    com_pacote_do_controle(user)
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@override_settings(GCAL_CLIENT="google", GCAL_AUTH_MODE="service_account")
@pytest.mark.parametrize(
    "url",
    ["/api/gcal/dashboard/batch/reapply/", "/api/gcal/dashboard/batch/resync/"],
)
def test_reapply_e_resync_recusam_nao_publicado_e_passado(controle_client, url):
    nunca = _futuro()
    passado = _passado(gcal_status="PUBLISHED")
    ok = _futuro(gcal_status="PUBLISHED")
    with patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay") as task:
        resp = controle_client.post(url, {"ids": [nunca.id, passado.id, ok.id]}, format="json")
    assert resp.status_code == 202
    assert resp.data["queued"] == 1
    assert {e["id"]: e["code"] for e in resp.data["errors"]} == {
        nunca.id: "nao_publicado",
        passado.id: "evento_passado",
    }
    assert [c.args[0] for c in task.call_args_list] == [ok.id]
    nunca.refresh_from_db()
    assert nunca.gcal_status == "NONE", "o resync recusado não marca PENDING"


@override_settings(GCAL_CLIENT="google", GCAL_AUTH_MODE="service_account")
def test_lote_de_publicacao_recusa_passado_publicado_e_fora_do_sistema(controle_client):
    passado = _passado()
    publicado = _futuro(gcal_status="PUBLISHED")
    fora = _futuro(publicado_fora_do_sistema=True)
    ok = _futuro()
    with patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay") as task:
        resp = controle_client.post(
            "/api/gcal/publish-batch/",
            {"solicitacao_ids": [passado.id, publicado.id, fora.id, ok.id]},
            format="json",
        )
    assert resp.status_code == 202
    assert resp.data["queued"] == 1
    assert {e["id"]: e["code"] for e in resp.data["errors"]} == {
        passado.id: "evento_passado",
        publicado.id: "ja_publicado",
        fora.id: "publicado_fora_do_sistema",
    }
    assert task.call_count == 1


def test_insert_sem_a_coluna_nasce_false_pelo_default_do_banco():
    """Deploy: a migration roda antes da troca do container; o código antigo não conhece a coluna.

    O INSERT dele (sem `publicado_fora_do_sistema`) precisa passar pelo DEFAULT do banco (`db_default`),
    senão falha com NOT NULL ao criar Solicitação durante o deploy.
    """
    base = SolicitacaoFactory()
    with connection.cursor() as cursor:
        colunas = [
            c.name
            for c in connection.introspection.get_table_description(cursor, Solicitacao._meta.db_table)
            if c.name not in {"id", "publicado_fora_do_sistema"}
        ]
        lista = ", ".join(connection.ops.quote_name(c) for c in colunas)
        tabela = connection.ops.quote_name(Solicitacao._meta.db_table)
        cursor.execute(
            f"INSERT INTO {tabela} ({lista}) SELECT {lista} FROM {tabela} WHERE id = %s RETURNING id",  # noqa: S608  # nosec B608 (nomes da introspecção; valor parametrizado)
            [base.pk],
        )
        linha = cursor.fetchone()
    assert linha is not None
    assert Solicitacao.objects.get(pk=linha[0]).publicado_fora_do_sistema is False
