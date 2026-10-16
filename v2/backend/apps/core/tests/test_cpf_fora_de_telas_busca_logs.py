"""
S5 da lista de liberação (auditoria de segurança 14/10, C6, C10 e C11): o CPF sai das telas,
da busca e dos logs.

Desde 29/09 o login (`username`) de toda conta é o CPF. Então:
- C6: a busca de pessoas não pode casar o login nem o e-mail por pedaço (oráculo de CPF);
  só quem administra cadastros acha por CPF ou e-mail, e só com o valor exato. Termo sem dígito
  casa também o e-mail (acha "Conceição" por "conceicao"; sem dígito não há CPF a testar).
- C10: as respostas de `/api/solicitacoes*` e `/api/gcal/*` (JSON e CSV) não levam o login;
  a busca textual dessas listas também não casa o login.
- C11: os logs estruturados não levam o login nos `extra`, e o filtro de PII limpa também os
  valores dos `extra` e o traceback.
- O mesmo atalho "nome ou login" fora dessas rotas: bloqueios, deslocamentos, Plano de
  Formações, métricas de formadores e do mapa, e a Grade Mensal (nome, e-mail de reserva e `q`).

Todos os CPFs aqui são sintéticos.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportPrivateUsage=false

from __future__ import annotations

import io
import itertools
import json
import logging
import pathlib
import re
import runpy
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.test import RequestFactory, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

import pytest
from pythonjsonlogger.jsonlogger import JsonFormatter

from apps.core.logging_filters import PIIRedactionFilter
from apps.core.models import AuditLog, AvailabilityBlock, Deslocamento, Participation, PlanoFormacoes, Solicitacao
from apps.core.services.monthly_grid_service import build_monthly_grid
from apps.core.tests.ambiente_repo import exige_raiz_do_repo
from apps.core.tests.factories import (
    GerenciaFactory,
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
    com_papel,
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


def _conceicao(**extra):
    """Nome acentuado com e-mail sem acento e com dígito: quem digita sem acento acha pelo e-mail."""
    u = _conta(nome="Conceição", sobrenome="Lima", **extra)
    u.email = "conceicao.lima7@example.invalid"
    u.save(update_fields=["email"])
    return u


def test_busca_sem_acento_e_sem_digito_acha_o_nome_acentuado_pelo_email():
    alvo = _conceicao(groups=["Formador"])
    coord = _conta(nome="Coord", groups=["Coordenador"])
    assert alvo.id in _ids(_client(coord).get("/api/lookup/usuarios/", {"q": "conceicao"}))


@pytest.mark.parametrize("q", ["lima7", "conceicao.lima7"])
def test_busca_com_digito_nao_casa_o_email(q):
    _conceicao(groups=["Formador"])
    coord = _conta(nome="Coord", groups=["Coordenador"])
    assert _ids(_client(coord).get("/api/lookup/usuarios/", {"q": q})) == set()


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
    avaliado_sem_nome = _conta(groups=["Formador"])
    agora = timezone.now()
    comum = {"status": "aprovado", "gcal_status": Solicitacao.GCalStatus.PUBLISHED, "gcal_payload_hash": "hash"}
    com_coord = SolicitacaoFactory(
        usuario=criador_sem_nome,
        coordenador=coordenador,
        formador_avaliado=avaliado_sem_nome,
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
    # Conta importada sem e-mail na planilha: o e-mail de reserva é `<cpf>@placeholder.local`.
    sem_email = _conta(nome="Rita", groups=["Formador"])
    sem_email.email = f"{sem_email.cpf}@placeholder.local"
    sem_email.save(update_fields=["email"])
    Participation.objects.create(solicitacao=com_coord, usuario=sem_email, role=Participation.Role.FORMADOR)
    # Convidados sem conta: um com o e-mail de reserva e outro com e-mail que leva o CPF.
    Participation.objects.create(
        solicitacao=sem_coord, guest_email=f"{_cpf()}@placeholder.local", role=Participation.Role.FORMADOR
    )
    Participation.objects.create(
        solicitacao=com_coord, guest_email=f"{_cpf()}@example.invalid", role=Participation.Role.FORMADOR
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
        "avaliado": avaliado_sem_nome,
        "sem_email": sem_email,
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
    cpfs = {cenario[k].username for k in ("criador", "coordenador", "avaliado", "sem_email")}
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
    assert detalhe["formador_avaliado_nome"] == f"Usuario #{cenario['avaliado'].id}"

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


# O access log do gunicorn e do nginx não passa pelo PIIRedactionFilter: a linha do pedido
# não pode levar a query string (?q=<cpf> na busca de quem administra cadastros) nem o referer.


def _gunicorn_conf(qual: str) -> pathlib.Path:
    if qual == "backend":  # o que o container de desenvolvimento usa (/app/infra)
        return pathlib.Path(__file__).resolve().parents[3] / "infra" / "gunicorn.conf.py"
    return exige_raiz_do_repo() / "v2" / "infra" / "gunicorn.conf.py"  # o da imagem de produção


@pytest.mark.parametrize("qual", ["backend", "imagem"])
def test_access_log_do_gunicorn_nao_grava_a_query_nem_o_referer(qual):
    from gunicorn.config import Config
    from gunicorn.glogging import Logger

    formato = runpy.run_path(str(_gunicorn_conf(qual)))["access_log_format"]
    cpf = _cpf()
    environ = {
        "REQUEST_METHOD": "GET",
        "RAW_URI": f"/api/lookup/usuarios/?q={cpf}",
        "PATH_INFO": "/api/lookup/usuarios/",
        "QUERY_STRING": f"q={cpf}",
        "SERVER_PROTOCOL": "HTTP/1.1",
        "HTTP_REFERER": f"https://sistema.example.invalid/usuarios?busca={cpf}",
        "HTTP_USER_AGENT": "pytest",
        "REMOTE_ADDR": "10.0.0.1",
    }
    resp = SimpleNamespace(status="200 OK", sent=10, headers=[])
    atoms = Logger(Config()).atoms(resp, SimpleNamespace(headers=[]), environ, timedelta(milliseconds=5))
    linha = formato % atoms
    assert "/api/lookup/usuarios/" in linha
    assert not _ONZE_DIGITOS.search(linha), linha


def test_access_log_do_nginx_nao_grava_a_query_nem_o_referer():
    conf = (exige_raiz_do_repo() / "v2" / "frontend" / "nginx.conf").read_text(encoding="utf-8")
    m = re.search(r"^\s*access_log\s+\S+\s+(\w+)\s*;", conf, re.MULTILINE)
    assert m, "o server não declara access_log com formato próprio (o padrão grava $request)"
    fmt = re.search(rf"log_format\s+{m.group(1)}\s+(?P<corpo>[^;]*);", conf)
    assert fmt, f"log_format {m.group(1)} não declarado"
    variaveis = set(re.findall(r"\$(\w+)", fmt.group("corpo")))
    # `$uri` vira /index.html nas rotas da SPA (try_files): o caminho sai do pedido original.
    assert "caminho_sem_query" in variaveis
    assert not variaveis & {"uri", "request", "request_uri", "args", "query_string", "http_referer"}, variaveis
    mapa = re.search(
        r"map\s+\$request_uri\s+\$caminho_sem_query\s*\{\s*\"~(?P<regex>[^\"]+)\"\s+\$(?P<grupo>\w+);", conf
    )
    assert mapa, "o caminho sem a query não sai de um map sobre $request_uri"
    cpf = _cpf()
    casou = re.match(mapa.group("regex").replace("(?<", "(?P<"), f"/usuarios?busca={cpf}")
    assert casou and casou.group(mapa.group("grupo")) == "/usuarios"


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


# =============================================================================
# Família: nome de exibição, erro do GCal e descrição do evento sem o login
# =============================================================================


def _linha_de_erro_antiga(s, operador) -> None:
    """Linha gravada antes do conserto: a mensagem da exceção levava o login do operador."""
    AuditLog.objects.create(
        usuario=operador,
        action=AuditLog.Action.PUBLISH_GCAL_ERROR,
        model_name="Solicitacao",
        details={
            "solicitacao_id": s.id,
            "operation": "publish",
            "error": f"Google OAuth credential not found for user '{operador.username}' (id={operador.id}).",
        },
    )


@pytest.mark.parametrize("origem", ["task", "linha_antiga"])
@override_settings(GCAL_AUTH_MODE="oauth")
def test_erro_de_credencial_google_nao_leva_cpf_a_timeline_nem_a_auditoria(cenario, origem):
    from apps.core.tasks import task_publish_solicitacao_to_gcal

    operador = cenario["controle"]  # sem GoogleOAuthCredential
    s = cenario["sem_coord"]
    if origem == "task":
        task_publish_solicitacao_to_gcal(s.id, operator_user_id=operador.id)
    else:
        _linha_de_erro_antiga(s, operador)
    linha = AuditLog.objects.get(action=AuditLog.Action.PUBLISH_GCAL_ERROR, details__solicitacao_id=s.id)
    if origem == "task":  # na origem: a mensagem da exceção já não leva o login
        assert operador.username not in linha.details["error"], linha.details

    cliente = _client(operador)
    for rota in (
        f"/api/gcal/dashboard/events/{s.id}/detail/",
        f"/api/audit-logs/?action={AuditLog.Action.PUBLISH_GCAL_ERROR}",
    ):
        resp = cliente.get(rota)
        assert resp.status_code == 200, (rota, resp.status_code)
        corpo = resp.content.decode()
        assert "credential not found" in corpo, rota
        assert not _ONZE_DIGITOS.search(corpo), (rota, corpo)


def test_conflito_de_agenda_nao_leva_cpf_de_formador_sem_nome():
    from apps.core.models import AvailabilityBlock
    from apps.core.tests.factories import liberar_par

    municipio = MunicipioFactory()
    projeto = ProjetoFactory(fluxo="SUPER")
    liberar_par(municipio, projeto)
    formador = _conta(groups=["Formador"])
    inicio = timezone.now() + timedelta(days=30)
    s = SolicitacaoFactory(
        usuario=_conta(nome="Coord", groups=["Coordenador"]),
        municipio=municipio,
        projeto=projeto,
        inicio=inicio,
        fim=inicio + timedelta(hours=2),
        status="pendente",
    )
    Participation.objects.create(solicitacao=s, usuario=formador, role=Participation.Role.FORMADOR)
    AvailabilityBlock.objects.create(
        usuario=formador,
        inicio=inicio + timedelta(minutes=30),
        fim=inicio + timedelta(hours=1),
        tipo="T",
        status="aprovado",
        motivo="Bloqueio",
    )

    resp = _client(UsuarioFactory(superuser=True)).patch(f"/api/solicitacoes/{s.id}/approve/", {}, format="json")

    assert resp.status_code == 400, resp.content
    assert resp.data["code"] == "availability_conflict"
    assert resp.data["errors"]["blocked_participants"][0]["usuario_nome"] == f"Usuario #{formador.id}"
    assert not _ONZE_DIGITOS.search(resp.content.decode()), resp.content


def test_conflito_de_agenda_nao_leva_cpf_no_email_de_convidado_sem_conta():
    """`skipped_guests` lista os convidados sem conta; o e-mail de reserva ou com CPF não sai."""
    from apps.core.tests.factories import liberar_par

    municipio = MunicipioFactory()
    projeto = ProjetoFactory(fluxo="SUPER")
    liberar_par(municipio, projeto)
    formador = _conta(nome="Formadora", groups=["Formador"])
    inicio = timezone.now() + timedelta(days=30)
    s = SolicitacaoFactory(
        usuario=_conta(nome="Coord", groups=["Coordenador"]),
        municipio=municipio,
        projeto=projeto,
        inicio=inicio,
        fim=inicio + timedelta(hours=2),
        status="pendente",
    )
    Participation.objects.create(solicitacao=s, usuario=formador, role=Participation.Role.FORMADOR)
    for email in (f"{_cpf()}@placeholder.local", f"{_cpf()}@example.invalid", "externo@fora.com"):
        Participation.objects.create(solicitacao=s, guest_email=email, role=Participation.Role.FORMADOR)
    AvailabilityBlock.objects.create(
        usuario=formador,
        inicio=inicio + timedelta(minutes=30),
        fim=inicio + timedelta(hours=1),
        tipo="T",
        status="aprovado",
        motivo="Bloqueio",
    )

    resp = _client(UsuarioFactory(superuser=True)).patch(f"/api/solicitacoes/{s.id}/approve/", {}, format="json")

    assert resp.status_code == 400, resp.content
    assert resp.data["code"] == "availability_conflict"
    convidados = resp.data["errors"]["skipped_guests"]
    assert len(convidados) == 3  # todo convidado sem conta continua reportado (PA-05)
    assert "externo@fora.com" in convidados  # o e-mail seguro continua aparecendo
    assert not _ONZE_DIGITOS.search(resp.content.decode()), resp.content


def test_meus_eventos_nao_levam_cpf_de_co_participante_sem_nome():
    eu = _conta(nome="Ana", sobrenome="Formadora", groups=["Formador"])
    colega_sem_nome = _conta(groups=["Formador"])
    s = SolicitacaoFactory(status="aprovado", inicio=timezone.now() + timedelta(days=5))
    for u in (eu, colega_sem_nome):
        Participation.objects.create(solicitacao=s, usuario=u, role=Participation.Role.FORMADOR)

    resp = _client(eu).get("/api/me/events/")

    assert resp.status_code == 200, resp.content
    corpo = resp.content.decode()
    assert f"Usuario #{colega_sem_nome.id}" in corpo
    assert not _ONZE_DIGITOS.search(corpo), corpo


def test_meus_eventos_nao_levam_cpf_de_convidado_sem_conta():
    eu = _conta(nome="Ana", sobrenome="Formadora", groups=["Formador"])
    s = SolicitacaoFactory(status="aprovado", inicio=timezone.now() + timedelta(days=5))
    Participation.objects.create(solicitacao=s, usuario=eu, role=Participation.Role.FORMADOR)
    for email in (f"{_cpf()}@placeholder.local", f"{_cpf()}@example.invalid"):
        Participation.objects.create(solicitacao=s, guest_email=email, role=Participation.Role.FORMADOR)

    resp = _client(eu).get("/api/me/events/")

    assert resp.status_code == 200, resp.content
    corpo = resp.content.decode()
    assert "Ana Formadora" in corpo
    assert not _ONZE_DIGITOS.search(corpo), corpo


def test_descricao_do_evento_no_google_nao_leva_cpf_de_quem_nao_tem_nome():
    from apps.core.services.gcal.payload import build_event_payload

    coordenador = _conta(groups=["Coordenador"])
    formador = _conta(groups=["Formador"])
    s = SolicitacaoFactory(status="aprovado", coordenador=coordenador)
    s.formadores.add(formador)

    descricao = build_event_payload(s)["description"]

    assert f"Coordenador(a): Usuario #{coordenador.id}" in descricao
    assert f"Formador(es): Usuario #{formador.id}" in descricao
    assert not _ONZE_DIGITOS.search(descricao), descricao


def test_convite_do_google_nao_leva_email_de_reserva_com_cpf():
    """O e-mail `<cpf>@placeholder.local` não é caixa de verdade e mostraria o CPF aos convidados."""
    from apps.core.services.gcal.payload import build_attendees_for_solicitacao

    sem_email = _conta(groups=["Formador"])
    sem_email.email = f"{sem_email.cpf}@placeholder.local"
    sem_email.save(update_fields=["email"])
    com_email = _conta(groups=["Formador"])
    s = SolicitacaoFactory(status="aprovado")
    for u in (sem_email, com_email):
        Participation.objects.create(solicitacao=s, usuario=u, role=Participation.Role.FORMADOR)

    assert build_attendees_for_solicitacao(s) == [{"email": com_email.email}]


# =============================================================================
# Mesmo atalho "nome ou login" fora de /api/solicitacoes* e /api/gcal/*: bloqueios,
# deslocamentos, Plano de Formações, métricas e Grade Mensal
# =============================================================================


@pytest.fixture
def gerencia_com_sem_nome():
    """Coordenador e uma conta sem nome (e com e-mail de reserva) na mesma gerência."""
    g = GerenciaFactory()
    coord = _conta(nome="Coord")
    com_papel(coord, "COORDENADOR", g)
    sem_nome = _conta()
    sem_nome.email = f"{sem_nome.cpf}@placeholder.local"
    sem_nome.save(update_fields=["email"])
    com_papel(sem_nome, "FORMADOR", g)
    return g, coord, sem_nome


def _sem_cpf(resp, rotulo: str) -> None:
    assert resp.status_code == 200, (rotulo, resp.status_code, resp.content[:300])
    corpo = resp.content.decode()
    assert not _ONZE_DIGITOS.search(corpo), rotulo


def test_bloqueios_e_deslocamentos_da_gerencia_nao_levam_cpf(gerencia_com_sem_nome):
    _, coord, sem_nome = gerencia_com_sem_nome
    agora = timezone.now()
    AvailabilityBlock.objects.create(
        usuario=sem_nome, inicio=agora + timedelta(days=1), fim=agora + timedelta(days=1, hours=2), tipo="T"
    )
    Deslocamento.objects.create(
        usuario=sem_nome,
        origem="Fortaleza",
        destino="Sobral",
        start_date=timezone.localdate(),
        end_date=timezone.localdate() + timedelta(days=1),
    )
    cliente = _client(coord)
    for rota in ("/api/availability-blocks/", "/api/deslocamentos/"):
        resp = cliente.get(rota)
        _sem_cpf(resp, rota)
        corpo = resp.json()
        linhas = corpo["results"] if isinstance(corpo, dict) else corpo
        assert [linha["usuario_nome"] for linha in linhas] == [f"Usuario #{sem_nome.id}"], rota


def test_plano_de_formacoes_nao_leva_cpf_de_coordenador_sem_nome():
    controle = _conta(nome="Operadora", groups=["Controle", "Assistente Administrativo"])
    sem_nome = _conta(groups=["Coordenador"])
    plano = PlanoFormacoes.objects.create(municipio=MunicipioFactory(), projeto=ProjetoFactory(), created_by=controle)
    plano.coordenadores.add(sem_nome)
    resp = _client(controle).get("/api/dat/plano-formacoes/")
    _sem_cpf(resp, "plano-formacoes")
    assert f"Usuario #{sem_nome.id}" in resp.content.decode()


def test_metricas_de_formadores_e_coordenadores_nao_levam_cpf_de_quem_nao_tem_nome():
    # Quem vê não administra contas: Controle (ranking de formadores) e Diretoria (mapa).
    controle = _conta(nome="Operadora", groups=["Controle", "Assistente Administrativo"])
    diretoria = _conta(nome="Diretora", groups=["Diretoria"])
    formador, coordenador = _conta(groups=["Formador"]), _conta(groups=["Coordenador"])
    inicio = timezone.now() - timedelta(days=1)
    s = SolicitacaoFactory(status="aprovado", inicio=inicio, fim=inicio + timedelta(hours=2))
    Participation.objects.create(solicitacao=s, usuario=formador, role=Participation.Role.FORMADOR)
    Participation.objects.create(solicitacao=s, usuario=coordenador, role=Participation.Role.COORDENADOR)
    for quem, rota in (
        (controle, "/api/metrics/team/formadores/"),
        (diretoria, f"/api/metrics/map/coordinators/?uf={s.municipio.uf}"),
    ):
        resp = _client(quem).get(rota)
        _sem_cpf(resp, rota)
        assert "Usuario #" in resp.content.decode(), rota


def test_painel_geral_nao_leva_cpf_de_coordenador_sem_nome():
    # Diretoria vê o painel geral e não administra contas.
    diretoria = _conta(nome="Diretora", groups=["Diretoria"])
    sem_nome = _conta(groups=["Coordenador"])
    inicio = timezone.now() - timedelta(days=2)
    SolicitacaoFactory(status="aprovado", usuario=sem_nome, inicio=inicio, fim=inicio + timedelta(hours=2))
    resp = _client(diretoria).get("/api/dashboard/overview/")
    _sem_cpf(resp, "dashboard/overview")
    assert resp.json()["top_coordenadores"] == [{"nome": f"Usuario #{sem_nome.id}", "eventos": 1}]


def _membro_super_sem_nome():
    """Conta sem nome, com e-mail de reserva, numa formação SUPER (caminho sem gerência da Grade)."""
    sem_nome = _conta()
    sem_nome.email = f"{sem_nome.cpf}@placeholder.local"
    sem_nome.save(update_fields=["email"])
    s = SolicitacaoFactory(status="aprovado", projeto=ProjetoFactory(super=True))
    Participation.objects.create(solicitacao=s, usuario=sem_nome, role=Participation.Role.FORMADOR)
    return sem_nome


@pytest.mark.parametrize("com_gerencia", [True, False])
def test_grade_mensal_nao_leva_cpf_no_nome_nem_no_email(gerencia_com_sem_nome, com_gerencia):
    g, _, sem_nome = gerencia_com_sem_nome
    if not com_gerencia:
        sem_nome = _membro_super_sem_nome()
    hoje = timezone.localdate()
    grade = build_monthly_grid(
        year=hoje.year, month=hoje.month, role="FORMADOR", gerencia_id=g.id if com_gerencia else None
    )
    pessoa = next(p for p in grade["people"] if p["id"] == sem_nome.id)
    assert pessoa["name"] == f"Usuario #{sem_nome.id}"
    assert pessoa["email"] is None
    assert not _ONZE_DIGITOS.search(json.dumps(grade["people"]))


@pytest.mark.parametrize("com_gerencia", [True, False])
def test_grade_mensal_busca_so_com_digitos_do_cpf_nao_acha_ninguem(gerencia_com_sem_nome, com_gerencia):
    g, _, sem_nome = gerencia_com_sem_nome
    if not com_gerencia:
        sem_nome = _membro_super_sem_nome()
    hoje = timezone.localdate()
    grade = build_monthly_grid(
        year=hoje.year,
        month=hoje.month,
        role="FORMADOR",
        gerencia_id=g.id if com_gerencia else None,
        q=sem_nome.cpf[2:7],
    )
    assert grade["people"] == []


@pytest.mark.parametrize("com_gerencia", [True, False])
def test_grade_mensal_busca_sem_acento_acha_nome_acentuado_e_com_digito_nao_casa_email(com_gerencia):
    g = GerenciaFactory()
    alvo = _conceicao()
    if com_gerencia:
        com_papel(alvo, "FORMADOR", g)
    else:
        s = SolicitacaoFactory(status="aprovado", projeto=ProjetoFactory(super=True))
        Participation.objects.create(solicitacao=s, usuario=alvo, role=Participation.Role.FORMADOR)
    hoje = timezone.localdate()

    def _grade(q: str) -> set[int]:
        grade = build_monthly_grid(
            year=hoje.year, month=hoje.month, role="FORMADOR", gerencia_id=g.id if com_gerencia else None, q=q
        )
        return {p["id"] for p in grade["people"]}

    assert alvo.id in _grade("conceicao")
    assert _grade("lima7") == set()
    assert _grade("conceicao.lima7") == set()
