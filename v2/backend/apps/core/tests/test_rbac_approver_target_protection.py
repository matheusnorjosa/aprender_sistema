"""
M07-01/M07-02 (#1616/#1617) — Proteção ator×alvo de contas APROVADORAS.

Contexto (v2/docs/audits/ACHADOS_REAIS.md, achados M07-01/M07-02):
Um admin não-superuser com `manage_admin_registries` (DAT) conseguia tomar uma
conta APROVADORA (Gerente da Superintendência ou Assistente Administrativo do
Controle) pelo `UsuarioAdminViewSet` — reset de senha, troca de e-mail,
desativação e hard delete/anonimização — em uma requisição. Tomar a conta de um
aprovador viabiliza auto-aprovação de solicitações (login-como-aprovador),
violando CP-02 (PA-01..07).

P0-0 (2026-07-17) já fechou o vetor para alvo SUPERUSER (404-invisível). Este
módulo estende a invariante para o alvo APROVADOR não-superuser, que P0-0 não
cobria (a queryset só exclui `is_superuser=True`).

Invariante de segurança (o que estes testes asseguram):
- Um não-superuser NÃO muta (senha/e-mail/is_active/delete/anonimizar) uma conta
  aprovadora → **403** (existe, mas é intocável; distinto do 404-Tier-0).
- Aprovador continua VISÍVEL/legível ao DAT (não é Tier-0): `retrieve`/`list` OK.
- Superuser-ator mantém bypass total.
- Contas comuns (não-aprovador, não-superuser) seguem administráveis pelo DAT.
- `can_admin_mutate_target` é o SSOT ator×alvo (semeia o épico #1656).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportIndexIssue=false, reportOptionalSubscript=false, reportCallIssue=false

from __future__ import annotations

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.core.models import Usuario
from apps.core.rbac import can_admin_mutate_target
from apps.core.tests.factories import GroupFactory, UsuarioFactory

APPROVER_PASSWORD = "AprovOldPass!123"
COMMON_PASSWORD = "CommonOld!123"
DETAIL = "/api/usuarios-admin/{}/"
ANONIMIZAR = "/api/usuarios-admin/{}/anonimizar/"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def usuario_dat(db):
    """DAT: tem manage_admin_registries (seed). Não é aprovador nem superuser."""
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
class TestApproverTargetProtectionAPI:
    """DAT (não-superuser) não toma conta aprovadora pelo UsuarioAdminViewSet."""

    def test_dat_reset_approver_password_forbidden_and_unchanged(self, api_client, usuario_dat, aprovador):
        api_client.force_authenticate(user=usuario_dat)
        resp = api_client.patch(DETAIL.format(aprovador.id), {"password": "Hacked!newpass9"}, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        aprovador.refresh_from_db()
        assert aprovador.check_password(APPROVER_PASSWORD)
        assert not aprovador.check_password("Hacked!newpass9")

    def test_dat_deactivate_approver_forbidden_and_still_active(self, api_client, usuario_dat, aprovador):
        api_client.force_authenticate(user=usuario_dat)
        resp = api_client.patch(DETAIL.format(aprovador.id), {"is_active": False}, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        aprovador.refresh_from_db()
        assert aprovador.is_active is True

    def test_dat_change_approver_email_forbidden_and_unchanged(self, api_client, usuario_dat, aprovador):
        original = aprovador.email
        api_client.force_authenticate(user=usuario_dat)
        resp = api_client.patch(DETAIL.format(aprovador.id), {"email": "hacked@example.com"}, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        aprovador.refresh_from_db()
        assert aprovador.email == original
        assert aprovador.email != "hacked@example.com"

    def test_dat_delete_approver_forbidden_and_still_exists(self, api_client, usuario_dat, aprovador):
        api_client.force_authenticate(user=usuario_dat)
        resp = api_client.delete(DETAIL.format(aprovador.id))
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert Usuario.objects.filter(pk=aprovador.id).exists()

    def test_dat_anonimizar_approver_forbidden_and_pii_intact(self, api_client, usuario_dat, aprovador):
        aprovador.first_name = "Nome Real"
        aprovador.save(update_fields=["first_name"])
        api_client.force_authenticate(user=usuario_dat)
        resp = api_client.post(ANONIMIZAR.format(aprovador.id), {}, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        aprovador.refresh_from_db()
        assert aprovador.first_name == "Nome Real"

    def test_dat_can_retrieve_approver(self, api_client, usuario_dat, aprovador):
        """Aprovador NÃO é Tier-0: leitura é permitida (não vira 404 como superuser)."""
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

    def test_non_superuser_cannot_mutate_gerente_super_approver(self, usuario_dat, aprovador):
        assert can_admin_mutate_target(usuario_dat, aprovador) is False

    def test_non_superuser_cannot_mutate_asst_admin_controle_approver(self, usuario_dat):
        target = UsuarioFactory(username="asst_controle", cpf="90000000032")
        target.groups.add(GroupFactory(name="Controle"), GroupFactory(name="Assistente Administrativo"))
        assert can_admin_mutate_target(usuario_dat, target) is False

    def test_non_superuser_can_mutate_common_target(self, usuario_dat, common_user):
        assert can_admin_mutate_target(usuario_dat, common_user) is True

    def test_actor_can_mutate_self(self, aprovador):
        """Mutar a própria conta nunca é escalonamento (self-service)."""
        assert can_admin_mutate_target(aprovador, aprovador) is True
