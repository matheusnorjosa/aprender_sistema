"""ART-17 — o dossiê do titular (LGPD art. 18, II e V) traz os eventos em que ele aparece.

A participação mora em `Participation` (papéis COORDENADOR, FORMADOR, COORD_ACOMPANHA e CONVIDADO). O dossiê lia o
M2M `Solicitacao.formadores`, que a API não grava: em 13/11/2026 ele tinha 0 linhas em produção, contra cerca de 16 mil
participações de 137 pessoas, e a seção dos eventos em que a pessoa participa saía vazia para todo mundo. Entram também
os eventos em que a pessoa é a coordenadora responsável (FK `coordenador`) ou a formadora avaliada (FK
`formador_avaliado`), e a exportação deixa de dar erro 500 para quem conectou a conta Google.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportMissingParameterType=false, reportUnknownParameterType=false, reportIndexIssue=false

from __future__ import annotations

import io
import json
from datetime import timedelta
from decimal import Decimal

from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog, GoogleOAuthCredential, Participation
from apps.core.services.lgpd_export_service import build_lgpd_export_data, export_counts
from apps.core.tests.factories import ProjetoFactory, SolicitacaoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

CPF_EXEMPLO = "11144477735"  # o CPF de exemplo de test_me_export.py

CHAVES_DA_PARTICIPACAO = {
    "solicitacao_id",
    "role",
    "ch_horas",
    "observacao",
    "created_at",
    "solicitacao__status",
    "solicitacao__inicio",
    "solicitacao__fim",
    "solicitacao__municipio__nome",
    "solicitacao__projeto__nome",
    "solicitacao__projeto_2__nome",
    "solicitacao__tipo_evento__nome",
}


def _participa(sol, usuario, role, **extra):
    return Participation.objects.create(solicitacao=sol, usuario=usuario, role=role, **extra)


def _baixar(usuario):
    client = APIClient()
    client.force_authenticate(user=usuario)
    resposta = client.get("/api/me/export/")
    assert resposta.status_code == 200, resposta.status_code
    return json.loads(resposta.content)


def _credencial_google(usuario):
    return GoogleOAuthCredential.objects.create(
        user=usuario,
        google_email="operacao@example.invalid",
        access_token_encrypted=b"token-de-acesso",
        refresh_token_encrypted=b"token-de-renovacao",
        token_expiry=timezone.now() + timedelta(hours=1),
        scope="https://www.googleapis.com/auth/calendar",
        default_calendar_id="primary",
    )


def test_dossie_traz_as_participacoes_do_titular_em_todos_os_papeis():
    titular = UsuarioFactory()
    eventos = {role: SolicitacaoFactory() for role in Participation.Role.values}
    for role, sol in eventos.items():
        _participa(sol, titular, role)

    linhas = build_lgpd_export_data(titular, include_audit=False)["event_participations"]

    assert sorted((linha["solicitacao_id"], linha["role"]) for linha in linhas) == sorted(
        (sol.pk, role) for role, sol in eventos.items()
    )


def test_dossie_traz_os_dados_do_evento_e_da_participacao_e_nada_alem():
    """O conjunto de chaves da linha é fechado: a observação do evento, que pode citar outras pessoas, não entra."""
    titular = UsuarioFactory()
    sol = SolicitacaoFactory(projeto_2=ProjetoFactory(), observacoes="nota interna do evento")
    _participa(sol, titular, Participation.Role.FORMADOR, ch_horas=Decimal("4.50"), observacao="levou o material")

    data = build_lgpd_export_data(titular, include_audit=False)
    [linha] = data["event_participations"]

    assert set(linha) == CHAVES_DA_PARTICIPACAO
    assert linha["solicitacao__status"] == sol.status
    assert linha["solicitacao__inicio"] == sol.inicio.isoformat()
    assert linha["solicitacao__fim"] == sol.fim.isoformat()
    assert linha["solicitacao__municipio__nome"] == sol.municipio.nome
    assert linha["solicitacao__projeto__nome"] == sol.projeto.nome
    assert linha["solicitacao__projeto_2__nome"] == sol.projeto_2.nome
    assert linha["solicitacao__tipo_evento__nome"] == sol.tipo_evento.nome
    assert linha["ch_horas"] == 4.5
    assert linha["observacao"] == "levou o material"
    assert "nota interna do evento" not in json.dumps(data)


def test_campos_vazios_saem_como_nulos():
    titular = UsuarioFactory()
    _participa(SolicitacaoFactory(), titular, Participation.Role.CONVIDADO)

    [linha] = build_lgpd_export_data(titular, include_audit=False)["event_participations"]

    assert linha["ch_horas"] is None
    assert linha["observacao"] is None
    assert linha["solicitacao__projeto_2__nome"] is None


def test_dois_papeis_no_mesmo_evento_saem_em_duas_linhas():
    titular = UsuarioFactory()
    sol = SolicitacaoFactory()
    _participa(sol, titular, Participation.Role.FORMADOR)
    _participa(sol, titular, Participation.Role.CONVIDADO)

    linhas = build_lgpd_export_data(titular, include_audit=False)["event_participations"]

    assert sorted(linha["role"] for linha in linhas) == [Participation.Role.CONVIDADO, Participation.Role.FORMADOR]
    assert {linha["solicitacao_id"] for linha in linhas} == {sol.pk}


def test_dossie_nao_traz_participacao_de_outra_pessoa():
    titular, colega = UsuarioFactory(), UsuarioFactory()
    sol = SolicitacaoFactory()
    _participa(sol, titular, Participation.Role.COORDENADOR)
    _participa(sol, colega, Participation.Role.FORMADOR, observacao="nota sobre a colega")
    _participa(SolicitacaoFactory(), colega, Participation.Role.CONVIDADO)

    data = build_lgpd_export_data(titular, include_audit=False)

    assert [(linha["solicitacao_id"], linha["role"]) for linha in data["event_participations"]] == [
        (sol.pk, Participation.Role.COORDENADOR)
    ]
    assert "nota sobre a colega" not in json.dumps(data)


def test_evento_que_o_titular_criou_nao_traz_a_participacao_do_colega():
    titular, colega = UsuarioFactory(), UsuarioFactory()
    sol = SolicitacaoFactory(usuario=titular)
    _participa(sol, colega, Participation.Role.FORMADOR, observacao="nota sobre a colega")

    data = build_lgpd_export_data(titular, include_audit=False)

    assert [linha["id"] for linha in data["solicitations_created"]] == [sol.pk]
    assert data["event_participations"] == []
    assert "nota sobre a colega" not in json.dumps(data)


def test_dossie_traz_os_eventos_em_que_o_titular_e_o_coordenador_responsavel():
    """A FK `coordenador` sem linha em Participation (o admin do Django ainda cria esse caso) não some do dossiê."""
    titular = UsuarioFactory()
    sol = SolicitacaoFactory(coordenador=titular, coordenador_acompanha=True)

    data = build_lgpd_export_data(titular, include_audit=False)

    assert data["event_participations"] == []
    assert data["solicitations_created"] == []
    [linha] = data["events_as_responsible"]
    assert linha["id"] == sol.pk
    assert linha["coordenador_acompanha"] is True
    assert export_counts(data)["events_as_responsible"] == 1


def test_dossie_traz_os_eventos_em_que_o_titular_e_o_formador_avaliado():
    titular = UsuarioFactory()
    sol = SolicitacaoFactory(pretende_avaliar_formador=True, formador_avaliado=titular)
    _participa(sol, titular, Participation.Role.FORMADOR)

    data = build_lgpd_export_data(titular, include_audit=False)

    assert [linha["id"] for linha in data["events_as_formador_to_evaluate"]] == [sol.pk]
    assert export_counts(data)["events_as_formador_to_evaluate"] == 1


CAMPOS_DO_EVENTO_NO_DOSSIE = {
    "id",
    "status",
    "inicio",
    "fim",
    "municipio__nome",
    "projeto__nome",
    "projeto_2__nome",
    "tipo_evento__nome",
}


def test_eventos_da_fk_levam_so_os_campos_do_evento():
    """As seções da FK não levam a observação, o local nem quem criou o evento (dado de outra pessoa)."""
    titular = UsuarioFactory()
    autora = UsuarioFactory(email="autora.do.evento@exemplo.org")
    SolicitacaoFactory(
        usuario=autora,
        coordenador=titular,
        pretende_avaliar_formador=True,
        formador_avaliado=titular,
        observacoes="nota interna do evento",
        local="sala X do evento",
    )

    data = build_lgpd_export_data(titular, include_audit=False)

    [responsavel] = data["events_as_responsible"]
    assert set(responsavel) == CAMPOS_DO_EVENTO_NO_DOSSIE | {"coordenador_acompanha"}
    [avaliar] = data["events_as_formador_to_evaluate"]
    assert set(avaliar) == CAMPOS_DO_EVENTO_NO_DOSSIE
    assert data["solicitations_created"] == []
    texto = json.dumps(data, default=str)
    for fora in ("nota interna do evento", "sala X do evento", "autora.do.evento@exemplo.org"):
        assert fora not in texto


def test_evento_sem_coordenador_conta_como_responsavel_para_quem_criou():
    """Mesma regra de Meus eventos, da agenda e das horas: sem a FK, o responsável é quem criou o evento."""
    titular = UsuarioFactory()
    sol = SolicitacaoFactory(usuario=titular, coordenador=None)
    SolicitacaoFactory(usuario=titular, coordenador=UsuarioFactory())

    data = build_lgpd_export_data(titular, include_audit=False)

    assert [linha["id"] for linha in data["events_as_responsible"]] == [sol.pk]


def test_trilha_conta_as_participacoes():
    titular = UsuarioFactory()
    for _ in range(3):
        _participa(SolicitacaoFactory(), titular, Participation.Role.CONVIDADO)

    data = build_lgpd_export_data(titular, include_audit=False)

    assert export_counts(data)["event_participations"] == 3


def test_download_do_proprio_titular_traz_as_participacoes():
    titular = UsuarioFactory()
    sol = SolicitacaoFactory()
    _participa(sol, titular, Participation.Role.FORMADOR)

    body = _baixar(titular)

    assert [linha["solicitacao_id"] for linha in body["event_participations"]] == [sol.pk]
    log = AuditLog.objects.filter(usuario=titular, action=AuditLog.Action.EXPORT).latest("created_at")
    assert log.details["counts"]["event_participations"] == 1


def test_download_de_quem_conectou_o_google_sai_com_os_metadados_e_sem_tokens():
    """O self-service pede os metadados da conta Google. O serviço lia um campo que não existe (`last_used_at`) e o
    download dava erro 500 para quem conectou a conta.

    RED: AttributeError -> 500.
    """
    titular = UsuarioFactory()
    _credencial_google(titular)

    body = _baixar(titular)

    credencial = body["gcal_credentials"]
    assert set(credencial) == {"has_credential", "google_email", "created_at", "updated_at", "tokens"}
    assert credencial["google_email"] == "operacao@example.invalid"
    assert credencial["tokens"] == "(excluded for security)"
    texto = json.dumps(body)
    assert "token-de-acesso" not in texto
    assert "token-de-renovacao" not in texto


def test_comando_do_admin_exporta_conta_inativa_com_google_e_conta_as_secoes(tmp_path):
    titular = UsuarioFactory(cpf=CPF_EXEMPLO, is_active=False)
    _participa(SolicitacaoFactory(), titular, Participation.Role.COORDENADOR)
    _credencial_google(titular)
    out = tmp_path / "export.json"
    saida = io.StringIO()

    call_command("lgpd_export", cpf=CPF_EXEMPLO, output=str(out), include_gcal=True, stdout=saida)

    data = json.loads(out.read_text(encoding="utf-8"))
    assert [linha["role"] for linha in data["event_participations"]] == [Participation.Role.COORDENADOR]
    assert data["gcal_credentials"]["google_email"] == "operacao@example.invalid"
    assert "Event participations: 1" in saida.getvalue()
    log = AuditLog.objects.filter(action=AuditLog.Action.EXPORT).latest("created_at")
    assert log.details["counts"]["event_participations"] == 1
