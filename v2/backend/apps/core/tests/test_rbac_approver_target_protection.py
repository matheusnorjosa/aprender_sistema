"""
M07-01/M07-02 (#1616/#1617) e S4 do PR 10 — proteção ator×alvo no `UsuarioAdminViewSet`.

Histórico: o M07 (2026-07) protegeu a conta APROVADORA do DAT (tomar a conta viabilizava a
auto-aprovação). A decisão do dono de 14/10 (C8) estenderia a proteção às contas fortes. A decisão
de 16/10 (PR 10) **substituiu** as duas: o DAT é o administrador operacional da plataforma e altera
**todas** as contas, inclusive outro DAT, Apoio, Controle e as aprovadoras. **Só a conta de
superusuário fica protegida** (P0-0: invisível, 404). O que segura a segregação agora:

- toda alteração de conta fica no AuditLog, e a senha redefinida obriga a troca no próximo acesso
  (`deve_trocar_senha`), então a dona da conta percebe;
- quem alterou a conta do autor não decide as solicitações dele por 30 dias (PA-02, D2).

Invariantes destes testes:
- o DAT muta (senha/e-mail/is_active/delete/anonimizar) a conta aprovadora → 200/204;
- a senha redefinida pelo DAT grava `RESET_PASSWORD` e liga `deve_trocar_senha`;
- alvo superusuário segue intocável para não-superusuário (404 na view, False no helper);
- superusuário-ator mantém bypass total; `can_admin_mutate_target` é o SSOT ator×alvo.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportIndexIssue=false, reportOptionalSubscript=false, reportCallIssue=false

from __future__ import annotations

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog, Usuario
from apps.core.rbac import can_admin_mutate_target
from apps.core.tests.factories import GroupFactory, UsuarioFactory, com_pacote_do_controle

APPROVER_PASSWORD = "AprovOldPass!123"
COMMON_PASSWORD = "CommonOld!123"
DETAIL = "/api/usuarios-admin/{}/"
ANONIMIZAR = "/api/usuarios-admin/{}/anonimizar/"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def usuario_dat(db):
    """DAT pelo grupo: tem manage_admin_registries (seed). Não é aprovador nem superuser."""
    user = UsuarioFactory(username="dat_m07", cpf="90000000021")
    user.groups.add(GroupFactory(name="DAT"))
    return user


@pytest.fixture
def aprovador(db):
    """Alvo aprovador: Gerente da Superintendência (composite Setor × Função).

    Autoridade de aprovação (CP-02) sem ser superuser — o alvo exato do M07.
    """
    user = UsuarioFactory(
        username="gerente_super_m07",
        cpf="10000007706",
        password=APPROVER_PASSWORD,
    )
    user.groups.add(GroupFactory(name="Gerente"), GroupFactory(name="Superintendência"))
    return user


@pytest.fixture
def common_user(db):
    """Conta comum (não-aprovador) — administrável pelo DAT."""
    return UsuarioFactory(username="comum_m07", cpf="10000008427", password=COMMON_PASSWORD)


@pytest.mark.django_db
class TestDatAdministraContaAprovadora:
    """S4 do PR 10: o DAT (não-superuser) administra a conta aprovadora pelo UsuarioAdminViewSet."""

    def test_dat_reset_approver_password_audita_e_obriga_troca(self, api_client, usuario_dat, aprovador):
        api_client.force_authenticate(user=usuario_dat)
        resp = api_client.patch(DETAIL.format(aprovador.id), {"password": "Rotated!newpass9"}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        aprovador.refresh_from_db()
        assert aprovador.check_password("Rotated!newpass9")
        assert aprovador.deve_trocar_senha is True
        assert AuditLog.objects.filter(
            usuario=usuario_dat, action=AuditLog.Action.RESET_PASSWORD, details__target_user_id=aprovador.id
        ).exists()

    def test_dat_deactivate_approver(self, api_client, usuario_dat, aprovador):
        api_client.force_authenticate(user=usuario_dat)
        resp = api_client.patch(DETAIL.format(aprovador.id), {"is_active": False}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        aprovador.refresh_from_db()
        assert aprovador.is_active is False

    def test_dat_change_approver_email(self, api_client, usuario_dat, aprovador):
        api_client.force_authenticate(user=usuario_dat)
        resp = api_client.patch(DETAIL.format(aprovador.id), {"email": "novo@example.com"}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        aprovador.refresh_from_db()
        assert aprovador.email == "novo@example.com"

    def test_dat_delete_approver(self, api_client, usuario_dat, aprovador):
        api_client.force_authenticate(user=usuario_dat)
        resp = api_client.delete(DETAIL.format(aprovador.id))
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not Usuario.objects.filter(pk=aprovador.id).exists()

    def test_dat_anonimizar_approver(self, api_client, usuario_dat, aprovador):
        aprovador.first_name = "Nome Real"
        aprovador.save(update_fields=["first_name"])
        api_client.force_authenticate(user=usuario_dat)
        resp = api_client.post(ANONIMIZAR.format(aprovador.id), {}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        aprovador.refresh_from_db()
        assert aprovador.first_name != "Nome Real"

    def test_dat_can_retrieve_approver(self, api_client, usuario_dat, aprovador):
        api_client.force_authenticate(user=usuario_dat)
        resp = api_client.get(DETAIL.format(aprovador.id))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["id"] == aprovador.id

    def test_dat_list_includes_approver(self, api_client, usuario_dat, aprovador, common_user):
        api_client.force_authenticate(user=usuario_dat)
        resp = api_client.get("/api/usuarios-admin/")
        assert resp.status_code == status.HTTP_200_OK
        ids = {item["id"] for item in resp.data["results"]}
        assert aprovador.id in ids
        assert common_user.id in ids

    def test_dat_nao_alcanca_conta_de_superusuario(self, api_client, usuario_dat):
        alvo = UsuarioFactory(username="su_alvo_pr10", cpf="90000000033", superuser=True)
        api_client.force_authenticate(user=usuario_dat)
        resp = api_client.patch(DETAIL.format(alvo.id), {"password": "Hacked!newpass9"}, format="json")
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        alvo.refresh_from_db()
        assert not alvo.check_password("Hacked!newpass9")


@pytest.mark.django_db
class TestApproverBypassAndRegression:
    def test_superuser_actor_can_reset_approver_password(self, api_client, aprovador):
        actor = UsuarioFactory(username="root_m07", cpf="90000000029", superuser=True)
        api_client.force_authenticate(user=actor)
        resp = api_client.patch(DETAIL.format(aprovador.id), {"password": "RotatedByRoot!789"}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        aprovador.refresh_from_db()
        assert aprovador.check_password("RotatedByRoot!789")

    def test_dat_can_still_reset_common_user_password(self, api_client, usuario_dat, common_user):
        api_client.force_authenticate(user=usuario_dat)
        resp = api_client.patch(DETAIL.format(common_user.id), {"password": "NewCommon!456"}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        common_user.refresh_from_db()
        assert common_user.check_password("NewCommon!456")

    def test_dat_can_still_delete_common_user(self, api_client, usuario_dat, common_user):
        api_client.force_authenticate(user=usuario_dat)
        resp = api_client.delete(DETAIL.format(common_user.id))
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not Usuario.objects.filter(pk=common_user.id).exists()


@pytest.mark.django_db
class TestCanAdminMutateTargetHelper:
    """Unit do SSOT ator×alvo — semeia o épico #1656."""

    def test_superuser_actor_can_mutate_anyone(self, aprovador):
        actor = UsuarioFactory(username="root_unit", cpf="90000000030", superuser=True)
        assert can_admin_mutate_target(actor, aprovador) is True

    def test_non_superuser_cannot_mutate_superuser_target(self, usuario_dat):
        target = UsuarioFactory(username="su_target", cpf="90000000031", superuser=True)
        assert can_admin_mutate_target(usuario_dat, target) is False

    def test_non_superuser_can_mutate_gerente_super_approver(self, usuario_dat, aprovador):
        assert can_admin_mutate_target(usuario_dat, aprovador) is True

    def test_non_superuser_can_mutate_asst_admin_controle_approver(self, usuario_dat):
        target = UsuarioFactory(username="asst_controle", cpf="90000000032")
        target.groups.add(GroupFactory(name="Controle"), GroupFactory(name="Assistente Administrativo"))
        com_pacote_do_controle(target)  # PR 11: aprova pelo vínculo no Controle
        assert can_admin_mutate_target(usuario_dat, target) is True

    def test_non_superuser_can_mutate_common_target(self, usuario_dat, common_user):
        assert can_admin_mutate_target(usuario_dat, common_user) is True

    def test_actor_can_mutate_self(self, aprovador):
        """Mutar a própria conta nunca é escalonamento (self-service)."""
        assert can_admin_mutate_target(aprovador, aprovador) is True
