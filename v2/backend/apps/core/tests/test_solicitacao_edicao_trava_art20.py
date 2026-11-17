"""
DEF-30 (ART-20) — a edição pela tela espera a publicação no Google terminar.

A edição (PUT/PATCH) lia o evento sem trava, validava "não editar o que está publicado ou pendente"
sobre essa leitura e gravava a linha inteira (`ModelSerializer.update` → `save()`). A task do Google
(publicação ou nova tentativa) trava a linha com `select_for_update` e grava só os campos dela. Na
corrida, a edição lia ERROR, esperava a task no UPDATE e, quando a task gravava PUBLISHED com o id do
evento, regravava ERROR sem id por cima: o Google ficava com o conteúdo de antes e a linha sumia do
"publicado" (apagar depois deixaria o evento órfão no Google).

Contrato: `update`/`partial_update` leem a linha com `select_for_update(of=("self",))` dentro de
`transaction.atomic()`; a regra do serializer roda sobre a linha já travada e relida. Ver, aprovar e
recusar não travam (aprovar e recusar são PATCH chamados fora de transação: travar ali dá erro).

(i) estrutural; (ii) corrida real com duas threads e banco de verdade, sem sleep fixo: a espera pela
trava é observada em `pg_stat_activity`, e a espera tem teto (`lock_timeout`) que devolve 400, não 500;
(iii) aprovar, recusar e editar seguem 200 com transação real.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

from django.db import connection
from django.utils import timezone
from rest_framework.request import Request
from rest_framework.test import APIClient, APIRequestFactory

import pytest

from apps.core.models import Solicitacao
from apps.core.tests.factories import (
    GroupFactory,
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)
from apps.core.views_solicitacao import SolicitacaoViewSet


def _usuario(prefixo: str, **extra):
    uid = uuid4().hex[:8]
    return UsuarioFactory(
        username=f"{prefixo}_{uid}",
        cpf=str(uuid4().int % 10**11).zfill(11),
        email=f"{prefixo}_{uid}@test.com",
        **extra,
    )


def _solicitacao(usuario, *, status: str, fluxo: str, gcal_status: str = Solicitacao.GCalStatus.NONE):
    inicio = timezone.now() + timedelta(days=5)
    uid = uuid4().hex[:6]
    sol = SolicitacaoFactory(
        usuario=usuario,
        municipio=MunicipioFactory(nome=f"Mun_{uid}", uf="CE", ativo=True),
        projeto=ProjetoFactory(nome=f"Proj_{uid}", codigo=f"A{uid[:5]}", fluxo=fluxo, ativo=True),
        tipo_evento=TipoEventoFactory(nome=f"Evt_{uid}"),
        inicio=inicio,
        fim=inicio + timedelta(hours=2),
        status=status,
        observacoes="original",
    )
    Solicitacao.objects.filter(pk=sol.pk).update(status=status, gcal_status=gcal_status)
    sol.refresh_from_db()
    return sol


# =============================================================================
# (i) Estrutural: só editar trava
# =============================================================================


@pytest.mark.django_db
class TestSoEditarTrava:
    def _queryset(self, action: str, metodo: str):
        view = SolicitacaoViewSet()
        view.action = action
        request = Request(getattr(APIRequestFactory(), metodo)("/"))
        request.user = _usuario("trava_su", superuser=True)
        view.request = request
        return view.get_queryset()

    @pytest.mark.parametrize("action,metodo", [("partial_update", "patch"), ("update", "put")])
    def test_editar_trava_a_linha(self, action, metodo):
        qs = self._queryset(action, metodo)
        assert qs.query.select_for_update is True, f"{action} deve ler a linha com select_for_update"
        # `of=self`: o select_related de FK opcional vira OUTER JOIN, e FOR UPDATE no lado nulo dá erro.
        assert qs.query.select_for_update_of == ("self",)

    @pytest.mark.parametrize(
        "action,metodo",
        [("retrieve", "get"), ("list", "get"), ("approve", "patch"), ("reject", "patch"), ("destroy", "delete")],
    )
    def test_ver_aprovar_recusar_e_apagar_nao_travam(self, action, metodo):
        qs = self._queryset(action, metodo)
        assert qs.query.select_for_update is False, f"{action} não deve travar a linha"


# =============================================================================
# (ii) Corrida real: a publicação está falando com o Google e a edição chega
# =============================================================================


class _GoogleQueTravaNoInsert:
    """Cliente falso do Google: o insert avisa que chegou (`travou`) e só responde após `liberar`."""

    def __init__(self):
        self.travou = threading.Event()
        self.liberar = threading.Event()

    def get(self, calendar_id, event_id):  # noqa: ARG002
        return None

    def insert(self, calendar_id, event_id, payload):  # noqa: ARG002
        self.travou.set()
        if not self.liberar.wait(timeout=30):
            raise TimeoutError("o teste não liberou o insert")
        return {"id": event_id}

    def update(self, calendar_id, event_id, payload):  # noqa: ARG002
        return {"id": event_id}

    def delete(self, calendar_id, event_id):  # noqa: ARG002
        return None


def _esperar_alguem_esperando_trava(timeout: float = 15.0) -> None:
    """Polling em `pg_stat_activity` até outra conexão deste banco estar parada esperando uma trava."""
    limite = time.monotonic() + timeout
    with connection.cursor() as cursor:
        while time.monotonic() < limite:
            cursor.execute("""
                SELECT count(*) FROM pg_stat_activity
                WHERE datname = current_database() AND wait_event_type = 'Lock' AND pid <> pg_backend_pid()
                """)
            if cursor.fetchone()[0]:
                return
            time.sleep(0.02)
    pytest.fail("a edição não chegou a esperar a trava da publicação")


@pytest.mark.django_db(transaction=True)
def test_edicao_durante_publicacao_espera_e_nao_desfaz_o_publicado(monkeypatch, settings):
    """A edição que chega enquanto a task fala com o Google espera a trava, relê PUBLISHED e recebe 400.

    A linha começa em ERROR, o estado em que a tela deixa editar e a nova tentativa (`queue_gcal_sync_retry`)
    publica; a publicação e a nova tentativa travam e gravam igual (`apply_one_solicitacao`). Antes do
    conserto: PATCH 200 e a linha voltava a ERROR sem o id do evento.
    """
    from apps.core.services import gcal_client_factory
    from apps.core.services.gcal import sync as sync_mod
    from apps.core.tasks import task_publish_solicitacao_to_gcal

    settings.GCAL_AUTH_MODE = "service_account"
    settings.GCAL_CLIENT = "fake"
    google = _GoogleQueTravaNoInsert()
    monkeypatch.setattr(gcal_client_factory, "get_gcal_client_and_calendar_id", lambda: (google, "primary"))
    monkeypatch.setattr(sync_mod, "_retry_with_circuit_breaker", lambda f, **_: f())

    dono = _usuario("art20_dono")
    dono.groups.add(GroupFactory(name="Coordenador"))
    sol = _solicitacao(dono, status="aprovado", fluxo="NAO_SUPER", gcal_status=Solicitacao.GCalStatus.ERROR)

    def publicar():
        try:
            return task_publish_solicitacao_to_gcal(sol.id)
        finally:
            connection.close()

    def editar():
        try:
            client = APIClient()
            client.force_authenticate(dono)
            return client.patch(f"/api/solicitacoes/{sol.id}/", {"observacoes": "novo"}, format="json")
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futuro_publicar = executor.submit(publicar)
        futuro_editar = None
        try:
            assert google.travou.wait(timeout=15), "a publicação não chegou ao insert do Google"
            futuro_editar = executor.submit(editar)
            _esperar_alguem_esperando_trava()
        finally:
            google.liberar.set()
        resultado = futuro_publicar.result(timeout=30)
        assert futuro_editar is not None
        resposta = futuro_editar.result(timeout=30)

    assert resultado["action"] == "CREATE", resultado
    assert resposta.status_code == 400, f"esperado 400, obteve {resposta.status_code}: {resposta.data}"
    sol.refresh_from_db()
    assert sol.gcal_status == Solicitacao.GCalStatus.PUBLISHED
    assert sol.external_event_id == resultado["external_event_id"]
    assert sol.external_event_id
    assert sol.observacoes == "original"


class _GoogleQueFalhaNoInsert(_GoogleQueTravaNoInsert):
    """Como o de cima, mas o insert, depois de liberado, falha como um 500 do Google."""

    def insert(self, calendar_id, event_id, payload):
        super().insert(calendar_id, event_id, payload)
        raise RuntimeError("HttpError 500: backendError")


@pytest.mark.django_db(transaction=True)
def test_edicao_durante_publicacao_que_falha_recebe_400_e_a_linha_fica_em_erro(monkeypatch, settings):
    """A publicação normal (linha em PENDING, como `publish_to_gcal` deixa) falha enquanto a edição espera.

    O ERROR que o `apply_one_solicitacao` marca dentro da trava é desfeito pelo rollback da task; a edição
    pega a trava, relê PENDING e recebe o 400 do PENDING. O ERROR só é gravado depois, por
    `_mark_gcal_error`, fora da trava (ART-22). A edição não muda a linha; a próxima, já sobre ERROR, segue.
    """
    from apps.core.services import gcal_client_factory
    from apps.core.services.gcal import sync as sync_mod
    from apps.core.tasks import task_publish_solicitacao_to_gcal

    settings.GCAL_AUTH_MODE = "service_account"
    settings.GCAL_CLIENT = "fake"
    google = _GoogleQueFalhaNoInsert()
    monkeypatch.setattr(gcal_client_factory, "get_gcal_client_and_calendar_id", lambda: (google, "primary"))
    monkeypatch.setattr(sync_mod, "_retry_with_circuit_breaker", lambda f, **_: f())

    dono = _usuario("art20_falha")
    dono.groups.add(GroupFactory(name="Coordenador"))
    sol = _solicitacao(dono, status="aprovado", fluxo="NAO_SUPER", gcal_status=Solicitacao.GCalStatus.PENDING)

    def publicar():
        try:
            return task_publish_solicitacao_to_gcal(sol.id)
        finally:
            connection.close()

    def editar():
        try:
            client = APIClient()
            client.force_authenticate(dono)
            return client.patch(f"/api/solicitacoes/{sol.id}/", {"observacoes": "novo"}, format="json")
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futuro_publicar = executor.submit(publicar)
        futuro_editar = None
        try:
            assert google.travou.wait(timeout=15), "a publicação não chegou ao insert do Google"
            futuro_editar = executor.submit(editar)
            _esperar_alguem_esperando_trava()
        finally:
            google.liberar.set()
        resultado = futuro_publicar.result(timeout=30)
        assert futuro_editar is not None
        resposta = futuro_editar.result(timeout=30)

    assert resultado["action"] == "ERROR", resultado
    assert resposta.status_code == 400, f"esperado 400, obteve {resposta.status_code}: {resposta.data}"
    assert "Aguarde a conclusão" in str(resposta.data)
    sol.refresh_from_db()
    assert sol.gcal_status == Solicitacao.GCalStatus.ERROR
    assert not sol.external_event_id
    assert sol.observacoes == "original"

    client = APIClient()
    client.force_authenticate(dono)
    segunda = client.patch(f"/api/solicitacoes/{sol.id}/", {"observacoes": "novo"}, format="json")
    assert segunda.status_code == 200, segunda.data
    sol.refresh_from_db()
    assert sol.observacoes == "novo"


@pytest.mark.django_db(transaction=True)
def test_edicao_que_espera_demais_recebe_400_e_nao_500(monkeypatch):
    """A espera pela trava tem teto (`lock_timeout`) abaixo do `statement_timeout` de produção (30 s).

    Com o Google lento, a task segura a trava por mais de 30 s; sem teto, o SELECT FOR UPDATE da edição era
    cancelado pelo statement_timeout (500 genérico) e prendia a thread do gunicorn. Com o teto, a edição
    desiste e recebe 400 "tente de novo", sem mudar a linha. O teto é encurtado aqui para o teste ser rápido.
    """
    from django.db import transaction

    monkeypatch.setattr(SolicitacaoViewSet, "_EDICAO_LOCK_TIMEOUT", "200ms", raising=False)
    dono = _usuario("art20_teto")
    dono.groups.add(GroupFactory(name="Coordenador"))
    sol = _solicitacao(dono, status="aprovado", fluxo="NAO_SUPER", gcal_status=Solicitacao.GCalStatus.ERROR)
    travou, liberar = threading.Event(), threading.Event()

    def task_presa_no_google():
        try:
            with transaction.atomic():
                Solicitacao.objects.select_for_update().get(pk=sol.pk)
                travou.set()
                liberar.wait(timeout=5)
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=1) as executor:
        futuro = executor.submit(task_presa_no_google)
        try:
            assert travou.wait(timeout=15), "a task não chegou a travar a linha"
            client = APIClient()
            client.force_authenticate(dono)
            resposta = client.patch(f"/api/solicitacoes/{sol.id}/", {"observacoes": "novo"}, format="json")
        finally:
            liberar.set()
        futuro.result(timeout=30)

    assert resposta.status_code == 400, f"esperado 400, obteve {resposta.status_code}: {resposta.data}"
    assert "Tente de novo" in str(resposta.data)
    # Quem segura a linha pode ser a task do Google ou a aprovação (o lote trava as linhas até o commit):
    # a mensagem não afirma que é o Google.
    assert "sincronizado com o Google" not in str(resposta.data)
    sol.refresh_from_db()
    assert sol.observacoes == "original"


@pytest.mark.django_db(transaction=True)
def test_teto_vale_so_para_a_trava_da_linha_e_nao_para_a_dos_participantes(monkeypatch):
    """O teto cobre só a leitura da linha; a trava dos participantes (`lock_participants`) espera como antes.

    Uma aprovação em lote segura a trava de uma formadora até o commit. A edição de outro evento, nunca
    publicado, com essa formadora pega a linha na hora e espera a trava dela. Com o teto valendo para a
    transação inteira, passava dos 10 s e recebia 400 "sincronizado com o Google", motivo falso.
    """
    from django.db import transaction

    from apps.core.models import Participation
    from apps.core.services.solicitacao_availability import lock_participants

    monkeypatch.setattr(SolicitacaoViewSet, "_EDICAO_LOCK_TIMEOUT", "200ms", raising=False)
    dono = _usuario("art20_lote")
    dono.groups.add(GroupFactory(name="Coordenador"))
    formadora = _usuario("art20_formadora")
    sol = _solicitacao(dono, status="aprovado", fluxo="NAO_SUPER")
    Participation.objects.create(solicitacao=sol, usuario=formadora, role="FORMADOR")
    travou, liberar = threading.Event(), threading.Event()

    def lote_segurando_a_formadora():
        try:
            with transaction.atomic():
                lock_participants([formadora.id])
                travou.set()
                liberar.wait(timeout=15)
        finally:
            connection.close()

    def editar():
        try:
            client = APIClient()
            client.force_authenticate(dono)
            return client.patch(f"/api/solicitacoes/{sol.id}/", {"observacoes": "novo"}, format="json")
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futuro_lote = executor.submit(lote_segurando_a_formadora)
        try:
            assert travou.wait(timeout=15), "o lote não chegou a travar a formadora"
            futuro_editar = executor.submit(editar)
            _esperar_alguem_esperando_trava()
            time.sleep(0.6)  # passa do teto de 200 ms com a edição parada na trava da formadora
        finally:
            liberar.set()
        futuro_lote.result(timeout=30)
        resposta = futuro_editar.result(timeout=30)

    assert resposta.status_code == 200, f"esperado 200, obteve {resposta.status_code}: {resposta.data}"
    sol.refresh_from_db()
    assert sol.observacoes == "novo"


# =============================================================================
# (iii) Com transação real: aprovar, recusar e editar seguem funcionando
# =============================================================================


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("acao,status_final", [("approve", "aprovado"), ("reject", "reprovado")])
def test_aprovar_e_recusar_seguem_200_com_transacao_real(acao, status_final):
    sol = _solicitacao(_usuario("art20_autor"), status="pendente", fluxo="SUPER")
    client = APIClient()
    client.force_authenticate(_usuario("art20_aprova", superuser=True))

    resposta = client.patch(f"/api/solicitacoes/{sol.id}/{acao}/", {"justificativa": "conferido"}, format="json")

    assert resposta.status_code == 200, resposta.data
    sol.refresh_from_db()
    assert sol.status == status_final


@pytest.mark.django_db(transaction=True)
def test_editar_segue_200_com_transacao_real():
    dono = _usuario("art20_edita")
    dono.groups.add(GroupFactory(name="Coordenador"))
    sol = _solicitacao(dono, status="aprovado", fluxo="NAO_SUPER")
    client = APIClient()
    client.force_authenticate(dono)

    resposta = client.patch(f"/api/solicitacoes/{sol.id}/", {"observacoes": "editado"}, format="json")

    assert resposta.status_code == 200, resposta.data
    sol.refresh_from_db()
    assert sol.observacoes == "editado"
