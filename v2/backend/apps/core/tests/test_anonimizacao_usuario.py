"""LGPD art. 18-VI — testes da anonimizacao de Usuario (servico + endpoint).

Cobre a via de "direito ao esquecimento" que preserva a linha (FKs PROTECT):
scrub de PII, idempotencia, funcionamento onde o hard-delete falha com
ProtectedError, auditoria do FATO sem PII, e o endpoint admin com RBAC/anti-lockout.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportCallIssue=false, reportIndexIssue=false

from __future__ import annotations

from django.db.models import ProtectedError
from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog, DATCoordenador, Usuario
from apps.core.services.anonimizacao import (
    CAMPOS_ANONIMIZADOS,
    CAMPOS_ANONIMIZADOS_COORD,
    anonimizar_usuario,
)
from apps.core.tests.factories import SolicitacaoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

ANON_URL = "/api/usuarios-admin/{pk}/anonimizar/"

_CPF_TITULAR = "11144477735"
_EMAIL_TITULAR = "maria@example.com"
_TEL_TITULAR = "85999998888"


def _titular(**kw):
    """Titular com PII conhecida (para assertar que sumiu)."""
    defaults = dict(
        cpf=_CPF_TITULAR,
        first_name="Maria",
        last_name="Silva",
        email=_EMAIL_TITULAR,
        telefone=_TEL_TITULAR,
        cargo="Coordenadora",
    )
    defaults.update(kw)
    return UsuarioFactory(**defaults)


# ------------------------------- servico -------------------------------


def test_anonimiza_scrubba_pii_e_preserva_linha(django_capture_on_commit_callbacks):
    user = _titular()
    pk = user.pk
    with django_capture_on_commit_callbacks(execute=True):
        changed = anonimizar_usuario(usuario=user, actor=None)

    assert changed is True
    assert Usuario.objects.filter(pk=pk).exists()  # linha preservada (FK PROTECT)
    user.refresh_from_db()
    assert user.cpf != _CPF_TITULAR
    assert user.username == f"anon_{pk}"
    assert user.first_name == ""
    assert user.last_name == ""
    assert user.email == ""
    assert user.telefone == ""
    assert user.cargo == ""
    assert user.is_active is False
    assert user.has_usable_password() is False


def test_anonimiza_e_idempotente(django_capture_on_commit_callbacks):
    user = _titular()
    with django_capture_on_commit_callbacks(execute=True):
        assert anonimizar_usuario(usuario=user, actor=None) is True
    user.refresh_from_db()
    # 2a chamada nao muda nada e sinaliza no-op
    assert anonimizar_usuario(usuario=user, actor=None) is False


def test_anonimiza_funciona_onde_hard_delete_falha(django_capture_on_commit_callbacks):
    """FK PROTECT (Solicitacao) barra o delete; a anonimizacao preserva a linha."""
    user = _titular()
    SolicitacaoFactory(usuario=user)  # cria referencia PROTECT ao titular

    with pytest.raises(ProtectedError):
        user.delete()

    with django_capture_on_commit_callbacks(execute=True):
        assert anonimizar_usuario(usuario=user, actor=None) is True
    user.refresh_from_db()
    assert user.is_active is False
    assert user.cpf != _CPF_TITULAR


def test_auditoria_registra_o_fato_sem_pii(django_capture_on_commit_callbacks):
    actor = UsuarioFactory(superuser=True)
    user = _titular()

    with django_capture_on_commit_callbacks(execute=True):
        anonimizar_usuario(usuario=user, actor=actor)

    log = AuditLog.objects.filter(action=AuditLog.Action.USER_ANONYMIZE).latest("created_at")
    assert log.details["target_user_id"] == user.pk
    assert log.details["actor_user_id"] == actor.pk
    assert set(log.details["campos_anonimizados"]) == set(CAMPOS_ANONIMIZADOS)
    # o details NAO pode re-introduzir PII do titular
    blob = str(log.details)
    assert _CPF_TITULAR not in blob
    assert _EMAIL_TITULAR not in blob
    assert _TEL_TITULAR not in blob


# --------------------- reach ao DATCoordenador por CPF (opção A #1837) ---------------------


def _coordenador(cpf, **kw):
    actor = kw.pop("actor", None) or UsuarioFactory()
    defaults = dict(
        nome="Amanda Arruda",
        email="coordenacao11@example.com",
        telefone="85911112222",
        foto_url="https://ex/f.jpg",
        observacoes="anotação com PII",
        area="DAT",
        cpf=cpf,
        created_by=actor,
    )
    defaults.update(kw)
    return DATCoordenador.objects.create(**defaults)


def test_anonimiza_alcanca_coordenador_por_cpf(django_capture_on_commit_callbacks):
    """O CPF é a chave de join: esquecer o titular scrubba a PII do coordenador casado."""
    user = _titular()
    coord = _coordenador(cpf=_CPF_TITULAR)

    with django_capture_on_commit_callbacks(execute=True):
        anonimizar_usuario(usuario=user, actor=None)

    coord.refresh_from_db()
    assert coord.cpf is None
    assert coord.email == ""
    assert coord.telefone == ""
    assert coord.foto_url == ""
    assert coord.observacoes == ""
    assert coord.nome != "Amanda Arruda"  # tombstone, não vazio (NOT NULL)
    assert coord.nome != ""
    assert coord.ativo is False


def test_anonimiza_nao_alcanca_coordenador_de_outro_cpf(django_capture_on_commit_callbacks):
    user = _titular()
    outro = _coordenador(cpf="22255588846")

    with django_capture_on_commit_callbacks(execute=True):
        anonimizar_usuario(usuario=user, actor=None)

    outro.refresh_from_db()
    assert outro.cpf == "22255588846"
    assert outro.nome == "Amanda Arruda"  # intocado


def test_anonimiza_cpf_nao_11_digitos_nao_scrubba_ninguem(django_capture_on_commit_callbacks):
    """Guard: cpf_original que não normaliza p/ 11 dígitos NÃO pode mass-scrubbar cpf=''/NULL."""
    user = _titular(cpf="ANON0000009")  # normaliza p/ "0000009" (7 díg)
    vazio = _coordenador(cpf="")

    with django_capture_on_commit_callbacks(execute=True):
        anonimizar_usuario(usuario=user, actor=None)

    vazio.refresh_from_db()
    assert vazio.nome == "Amanda Arruda"  # NÃO foi scrubbado


def test_auditoria_conta_coordenadores_sem_pii(django_capture_on_commit_callbacks):
    actor = UsuarioFactory(superuser=True)
    user = _titular()
    _coordenador(cpf=_CPF_TITULAR)

    with django_capture_on_commit_callbacks(execute=True):
        anonimizar_usuario(usuario=user, actor=actor)

    log = AuditLog.objects.filter(action=AuditLog.Action.USER_ANONYMIZE).latest("created_at")
    assert log.details["coordenadores_anonimizados"] == 1
    assert set(log.details["campos_anonimizados_coordenador"]) == set(CAMPOS_ANONIMIZADOS_COORD)
    blob = str(log.details)
    assert _CPF_TITULAR not in blob
    assert "coordenacao11@example.com" not in blob
    assert "Amanda Arruda" not in blob


# ------------------------------- endpoint -------------------------------


def test_endpoint_anonimiza_com_permissao():
    dat = UsuarioFactory(groups=["DAT"])
    alvo = _titular()
    client = APIClient()
    client.force_authenticate(user=dat)

    resp = client.post(ANON_URL.format(pk=alvo.pk))

    assert resp.status_code == status.HTTP_200_OK
    alvo.refresh_from_db()
    assert alvo.is_active is False
    assert alvo.cpf != _CPF_TITULAR


def test_endpoint_sem_permissao_403():
    formador = UsuarioFactory(groups=["Formador"])
    alvo = _titular()
    client = APIClient()
    client.force_authenticate(user=formador)

    resp = client.post(ANON_URL.format(pk=alvo.pk))

    assert resp.status_code == status.HTTP_403_FORBIDDEN
    alvo.refresh_from_db()
    assert alvo.is_active is True  # inalterado


def test_endpoint_superuser_alvo_404_para_nao_superuser():
    """P0-0: contas superuser sao invisiveis/inalcancaveis para nao-superusers."""
    dat = UsuarioFactory(groups=["DAT"])
    alvo_super = UsuarioFactory(superuser=True)
    client = APIClient()
    client.force_authenticate(user=dat)

    resp = client.post(ANON_URL.format(pk=alvo_super.pk))

    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_endpoint_ultimo_superuser_ativo_bloqueado():
    root = UsuarioFactory(superuser=True)
    client = APIClient()
    client.force_authenticate(user=root)

    resp = client.post(ANON_URL.format(pk=root.pk))

    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    root.refresh_from_db()
    assert root.is_active is True
