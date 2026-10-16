"""
S5 da lista de liberação (auditoria de segurança 14/10, C6, C10 e C11): o CPF sai das telas,
da busca e dos logs.

Desde 29/09 o login (`username`) de toda conta é o CPF. Então:
- C6: a busca de pessoas não pode casar o login nem o e-mail por pedaço (oráculo de CPF);
  só quem administra cadastros acha por CPF ou e-mail, e só com o valor exato.
- C10: as respostas de `/api/solicitacoes*` e `/api/gcal/*` (JSON e CSV) não levam o login;
  a busca textual dessas listas também não casa o login.
- C11: os logs estruturados não levam o login nos `extra`, e o filtro de PII limpa também os
  valores dos `extra` e o traceback.

Todos os CPFs aqui são sintéticos.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportPrivateUsage=false

from __future__ import annotations

import io
import itertools
import json
import logging
import re
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.test import RequestFactory
from django.utils import timezone
from rest_framework.test import APIClient

import pytest
from pythonjsonlogger.jsonlogger import JsonFormatter

from apps.core.logging_filters import PIIRedactionFilter
from apps.core.models import AuditLog, Solicitacao
from apps.core.tests.factories import (
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db

_ONZE_DIGITOS = re.compile(r"\d{11}")
_CPF_SEQ = itertools.count(90000000001)


def _cpf() -> str:
    return str(next(_CPF_SEQ))


def _conta(*, nome: str = "", sobrenome: str = "", groups=None):
    """Conta como em produção: o login é o CPF."""
    cpf = _cpf()
    return UsuarioFactory(
        username=cpf,
        cpf=cpf,
        email=f"pessoa{cpf}@example.invalid",
        first_name=nome,
        last_name=sobrenome,
        groups=groups or [],
    )


def _client(user) -> APIClient:
    c = APIClient()
    c.force_authenticate(user)
    return c


def _ids(resp) -> set[int]:
    assert resp.status_code == 200, resp.content
    return {item["id"] for item in resp.json()}


# =============================================================================
# C6: /api/lookup/usuarios/ não é oráculo de CPF
# =============================================================================


@pytest.fixture
def alvo():
    return _conta(nome="Maria", sobrenome="Alvo", groups=["Formador"])


def test_coordenador_busca_so_com_digitos_do_cpf_nao_acha_ninguem(alvo):
    coord = _conta(nome="Coord", groups=["Coordenador"])
    resp = _client(coord).get("/api/lookup/usuarios/", {"q": alvo.username[:6]})
    assert _ids(resp) == set()


def test_coordenador_busca_o_cpf_inteiro_nao_acha_ninguem(alvo):
    coord = _conta(nome="Coord", groups=["Coordenador"])
    resp = _client(coord).get("/api/lookup/usuarios/", {"q": alvo.username})
    assert _ids(resp) == set()


def test_coordenador_busca_por_pedaco_do_email_nao_acha_ninguem(alvo):
    coord = _conta(nome="Coord", groups=["Coordenador"])
    resp = _client(coord).get("/api/lookup/usuarios/", {"q": f"pessoa{alvo.cpf}"})
    assert _ids(resp) == set()


def test_coordenador_continua_achando_por_nome(alvo):
    coord = _conta(nome="Coord", groups=["Coordenador"])
    resp = _client(coord).get("/api/lookup/usuarios/", {"q": "Maria"})
    assert alvo.id in _ids(resp)


@pytest.mark.parametrize("grafia", ["cru", "formatado"])
def test_quem_administra_cadastros_acha_pelo_cpf_exato(alvo, grafia):
    dat = _conta(nome="Dat", groups=["DAT"])
    c = alvo.username
    q = c if grafia == "cru" else f"{c[:3]}.{c[3:6]}.{c[6:9]}-{c[9:]}"
    assert alvo.id in _ids(_client(dat).get("/api/lookup/usuarios/", {"q": q}))


def test_quem_administra_cadastros_nao_acha_por_pedaco_do_cpf(alvo):
    dat = _conta(nome="Dat", groups=["DAT"])
    assert _ids(_client(dat).get("/api/lookup/usuarios/", {"q": alvo.username[:6]})) == set()


def test_quem_administra_cadastros_acha_pelo_email_exato_e_nao_por_pedaco(alvo):
    dat = _conta(nome="Dat", groups=["DAT"])
    assert alvo.id in _ids(_client(dat).get("/api/lookup/usuarios/", {"q": alvo.email.upper()}))
    assert _ids(_client(dat).get("/api/lookup/usuarios/", {"q": f"pessoa{alvo.cpf}"})) == set()


def test_rotulo_de_conta_sem_nome_nao_e_o_cpf():
    sem_nome = _conta(groups=["Formador"])
    coord = _conta(nome="Coord", groups=["Coordenador"])
    resp = _client(coord).get("/api/lookup/usuarios/", {"role": "Formador"})
    assert resp.status_code == 200
    rotulos = {item["id"]: item["label"] for item in resp.json()}
    assert rotulos[sem_nome.id] == f"Usuario #{sem_nome.id}"
    assert not _ONZE_DIGITOS.search(resp.content.decode())


# =============================================================================
# C10: respostas de /api/solicitacoes* e /api/gcal/* sem CPF; busca sem o login
# =============================================================================


@pytest.fixture
def cenario():
    controle = _conta(nome="Operadora", groups=["Controle", "Assistente Administrativo"])
    criador_sem_nome = _conta(groups=["Coordenador"])
    coordenador = _conta(nome="Joana", sobrenome="Coordenadora", groups=["Coordenador"])
    agora = timezone.now()
    comum = {"status": "aprovado", "gcal_status": Solicitacao.GCalStatus.PUBLISHED, "gcal_payload_hash": "hash"}
    com_coord = SolicitacaoFactory(
        usuario=criador_sem_nome,
        coordenador=coordenador,
        inicio=agora + timedelta(days=2),
        fim=agora + timedelta(days=2, hours=2),
        external_event_id="evtcomcoord",
        **comum,
    )
    sem_coord = SolicitacaoFactory(
        usuario=criador_sem_nome,
        coordenador=None,
        inicio=agora + timedelta(days=3),
        fim=agora + timedelta(days=3, hours=2),
        external_event_id="evtsemcoord",
        **comum,
    )
    # Linha da timeline do detalhe feita por quem não tem nome.
    AuditLog.objects.create(
        usuario=criador_sem_nome,
        action="PUBLISH_GCAL_REQUESTED",
        model_name="Solicitacao",
        details={"solicitacao_id": sem_coord.id},
    )
    return {
        "controle": controle,
        "criador": criador_sem_nome,
        "coordenador": coordenador,
        "com_coord": com_coord,
        "sem_coord": sem_coord,
    }


def _rotas(c) -> list[str]:
    sem = c["sem_coord"].id
    return [
        "/api/solicitacoes/",
        f"/api/solicitacoes/{sem}/",
        f"/api/solicitacoes/{c['com_coord'].id}/",
        "/api/gcal/list/",
        "/api/gcal/dashboard/events/",
        f"/api/gcal/dashboard/events/{sem}/detail/",
        "/api/gcal/dashboard/events/export/?export_format=csv",
        "/api/gcal/dashboard/events/export/?export_format=json",
    ]


def test_respostas_de_solicitacoes_e_gcal_nao_levam_cpf(cenario):
    cliente = _client(cenario["controle"])
    cpfs = {cenario["criador"].username, cenario["coordenador"].username}
    for rota in _rotas(cenario):
        resp = cliente.get(rota)
        assert resp.status_code == 200, (rota, resp.status_code)
        corpo = resp.content.decode("utf-8-sig")
        assert not any(cpf in corpo for cpf in cpfs), rota
        assert not _ONZE_DIGITOS.search(corpo), rota


def test_nome_continua_saindo_no_lugar_do_login(cenario):
    cliente = _client(cenario["controle"])
    detalhe = cliente.get(f"/api/solicitacoes/{cenario['com_coord'].id}/").json()
    assert "usuario_username" not in detalhe and "coordenador_username" not in detalhe
    assert detalhe["coordenador_nome"] == "Joana Coordenadora"

    gcal = cliente.get(f"/api/gcal/dashboard/events/{cenario['com_coord'].id}/detail/").json()
    assert "usuario_username" not in gcal and "coordenador_username" not in gcal
    assert gcal["coordenador_nome"] == "Joana Coordenadora"
    assert gcal["usuario_nome"] == f"Usuario #{cenario['criador'].id}"

    csv = cliente.get("/api/gcal/dashboard/events/export/?export_format=csv").content.decode("utf-8-sig")
    assert "Joana Coordenadora" in csv


@pytest.mark.parametrize(
    "rota, param",
    [
        ("/api/solicitacoes/", "search"),
        ("/api/solicitacoes/", "q"),
        ("/api/gcal/list/", "q"),
    ],
)
def test_busca_das_listas_nao_casa_o_login(cenario, rota, param):
    cliente = _client(cenario["controle"])
    pedaco = cenario["criador"].username[:7]
    resp = cliente.get(rota, {param: pedaco})
    assert resp.status_code == 200
    corpo = resp.json()
    linhas = corpo["results"] if isinstance(corpo, dict) else corpo
    assert linhas == []


# =============================================================================
# C11: logs sem CPF (extras e traceback), com o JsonFormatter de produção
# =============================================================================


def _logger_de_producao() -> tuple[logging.Logger, io.StringIO]:
    cfg = settings.LOGGING["formatters"]["json"]
    formatter = JsonFormatter(cfg["format"], reserved_attrs=cfg["reserved_attrs"], timestamp=cfg["timestamp"])
    saida = io.StringIO()
    handler = logging.StreamHandler(saida)
    handler.setFormatter(formatter)
    handler.addFilter(PIIRedactionFilter())
    logger = logging.getLogger("test.s5.cpf")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)
    return logger, saida


def test_filtro_redige_cpf_nos_extras():
    logger, saida = _logger_de_producao()
    cpf = _cpf()
    logger.info("evento", extra={"username": cpf, "contexto": {"login": cpf, "lista": [cpf]}, "user_id": 7})
    linha = saida.getvalue()
    assert not _ONZE_DIGITOS.search(linha), linha
    assert json.loads(linha)["user_id"] == 7


def test_filtro_redige_cpf_no_traceback():
    logger, saida = _logger_de_producao()
    cpf = _cpf()
    try:
        raise ValueError(f"conta {cpf} não encontrada")
    except ValueError:
        logger.exception("falhou")
    linha = saida.getvalue()
    assert "ValueError" in linha
    assert not _ONZE_DIGITOS.search(linha), linha


def test_criar_solicitacao_loga_user_id_sem_username(caplog):
    user = UsuarioFactory(superuser=True)  # isento da regra da compra: o foco é o log
    coordenador = _conta(nome="Joana", groups=["Coordenador"])
    inicio = timezone.now() + timedelta(days=30)
    payload = {
        "municipio": MunicipioFactory().id,
        "projeto": ProjetoFactory(fluxo="NAO_SUPER").id,
        "tipo_evento": TipoEventoFactory().id,
        "inicio": inicio.isoformat(),
        "fim": (inicio + timedelta(hours=1)).isoformat(),
        "coordenador": coordenador.id,
        "coordenador_acompanha": False,
    }
    with caplog.at_level(logging.INFO, logger="apps.core.views_solicitacao"):
        resp = _client(user).post("/api/solicitacoes/", payload, format="json")
    assert resp.status_code == 201, resp.content
    registros = [r for r in caplog.records if r.getMessage() == "solicitacao_initial_status_decided"]
    assert registros
    for r in registros:
        assert not hasattr(r, "username")
        assert r.user_id == user.id


@pytest.mark.parametrize("acao", ["publish", "resync", "cancel"])
def test_pedidos_ao_gcal_logam_user_id_sem_username(caplog, acao):
    from apps.core.services import solicitacao_publish as svc

    user = _conta(nome="Operadora", groups=["Controle"])
    s = SolicitacaoFactory(status="aprovado", external_event_id="evt1", gcal_status=Solicitacao.GCalStatus.PUBLISHED)
    request = RequestFactory().post("/")
    tarefa = MagicMock(id="tarefa-1")
    with (
        patch.object(svc, "_check_google_oauth", return_value=None),
        patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay", return_value=tarefa),
        patch("apps.core.tasks.task_cancel_solicitacao_from_gcal.delay", return_value=tarefa),
        caplog.at_level(logging.INFO, logger=svc.logger.name),
    ):
        if acao == "publish":
            svc.publish_to_gcal(s, user, request, dry_run=True)
        elif acao == "resync":
            svc.resync_to_gcal(s, user, request)
        else:
            svc.cancel_from_gcal(s, user, request)
    registros = [r for r in caplog.records if r.getMessage() == f"{acao}_gcal_requested"]
    assert registros, [r.getMessage() for r in caplog.records]
    for r in registros:
        assert not hasattr(r, "username")
        assert r.user_id == user.id


def test_login_com_cpf_digitado_errado_nao_vai_para_a_auditoria():
    """Família (AuditLog de login): CPF com um dígito a menos ou a mais ainda é o CPF de alguém."""
    from apps.core.views_auth import _username_para_auditoria

    assert _username_para_auditoria("9000000000") == "<cpf>"  # 10 dígitos
    assert _username_para_auditoria("900.000.000-012") == "<cpf>"  # 12 dígitos
    assert _username_para_auditoria("admin") == "admin"


def test_auditoria_redige_cpf_digitado_errado_em_linha_antiga():
    from apps.core.serializers.auditoria import _redact_details

    assert _redact_details({"username": "900.000.000-0"})["username"] == "<cpf>"
    assert _redact_details({"username": "admin"})["username"] == "admin"
