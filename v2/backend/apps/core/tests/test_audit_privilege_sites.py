"""
Integração dos pontos de mutação de privilégio com o serviço de auditoria (#1672).

Prova que cada endpoint/serviço REALMENTE emite a trilha — não só o helper.
Como a auditoria é emitida em `transaction.on_commit`, cada chamada mutante roda
dentro de `django_capture_on_commit_callbacks(execute=True)`.

Cobre os caminhos que ANTES perdiam o registro por não passar pelo Django Admin:
- Group × Capability via REST (GroupSerializer create/update) — o bug do issue.
- `assign_groups` (membership).
- Reset de senha de outro usuário (admin).
- Exclusão de usuário e de grupo.
- Import de usuários (apply audita; dry-run não).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalMemberAccess=false

from __future__ import annotations

import itertools
from unittest import mock

from django.contrib.auth.models import Group
from django.core.cache import cache
from django.test import RequestFactory
from rest_framework.test import APIClient

import pytest

from apps.core.admin import UsuarioAdmin, admin_site
from apps.core.models import AuditLog, PermissaoFuncional, Usuario
from apps.core.services.functional_permissions_seed import seed_functional_permissions
from apps.core.services.usuarios_import import import_usuarios_from_file
from apps.core.tests.factories import GroupFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

_CPF = itertools.count(75000000000)


def _mk(label: str, **kwargs) -> Usuario:
    cpf = str(next(_CPF)).zfill(11)
    return UsuarioFactory(username=f"{label}_{cpf}", email=f"{label}_{cpf}@t.com", cpf=cpf, **kwargs)


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def superuser() -> Usuario:
    return _mk("su", is_superuser=True, is_staff=True)


@pytest.fixture
def common_user() -> Usuario:
    return _mk("common")


@pytest.fixture
def caps() -> list[PermissaoFuncional]:
    seed_functional_permissions(assign_default_groups=False)
    return list(PermissaoFuncional.objects.order_by("codename")[:2])


# ============================================================================
# Group × Capability via REST (o path do bug — antes só o Admin persistia)
# ============================================================================


class TestGroupCapabilityViaREST:
    def test_create_group_com_caps_audita(self, api_client, superuser, caps, django_capture_on_commit_callbacks):
        AuditLog.objects.filter(action="GROUP_CAPABILITY_CHANGED").delete()
        api_client.force_authenticate(user=superuser)
        with django_capture_on_commit_callbacks(execute=True):
            resp = api_client.post(
                "/api/grupos/",
                {"name": "GrupoAudit", "permissao_funcional_ids": [caps[0].id]},
                format="json",
            )
        assert resp.status_code == 201, resp.content
        logs = AuditLog.objects.filter(action="GROUP_CAPABILITY_CHANGED")
        assert logs.count() == 1
        d = logs.first().details
        assert d["via"] == "group_serializer"
        assert d["capability_id"] == caps[0].id
        assert d["added_groups"] == ["GrupoAudit"]
        assert d["removed_groups"] == []

    def test_update_group_caps_audita_uma_por_cap(
        self, api_client, superuser, caps, django_capture_on_commit_callbacks
    ):
        group = GroupFactory(name="GrupoUpd")
        api_client.force_authenticate(user=superuser)
        AuditLog.objects.filter(action="GROUP_CAPABILITY_CHANGED").delete()
        with django_capture_on_commit_callbacks(execute=True):
            resp = api_client.patch(
                f"/api/grupos/{group.id}/",
                {"permissao_funcional_ids": [caps[0].id, caps[1].id]},
                format="json",
            )
        assert resp.status_code == 200, resp.content
        assert AuditLog.objects.filter(action="GROUP_CAPABILITY_CHANGED").count() == 2


# ============================================================================
# assign_groups (membership)
# ============================================================================


class TestAssignGroups:
    def test_assign_groups_audita(self, api_client, superuser, common_user, caps, django_capture_on_commit_callbacks):
        group = GroupFactory(name="GrupoAtrib")
        # Vincular capability torna o grupo "atribuível" (whitelist dinâmica).
        group.permissoes_funcionais.add(caps[0])
        cache.clear()
        api_client.force_authenticate(user=superuser)
        AuditLog.objects.filter(action="ASSIGN_GROUPS").delete()
        with django_capture_on_commit_callbacks(execute=True):
            resp = api_client.post(
                f"/api/usuarios-admin/{common_user.id}/assign_groups/",
                {"group_ids": [group.id]},
                format="json",
            )
        assert resp.status_code == 200, resp.content
        log = AuditLog.objects.filter(action="ASSIGN_GROUPS").latest("created_at")
        assert log.usuario_id == superuser.id
        assert log.details["target_user_id"] == common_user.id
        assert log.details["added_groups"] == ["GrupoAtrib"]


# ============================================================================
# Reset de senha (admin -> outro usuário)
# ============================================================================


class TestResetPassword:
    def test_patch_senha_de_outro_audita(self, api_client, superuser, common_user, django_capture_on_commit_callbacks):
        api_client.force_authenticate(user=superuser)
        AuditLog.objects.filter(action="RESET_PASSWORD").delete()
        with django_capture_on_commit_callbacks(execute=True):
            resp = api_client.patch(
                f"/api/usuarios-admin/{common_user.id}/",
                {"password": "NovaSenhaForte123"},  # gitleaks:allow (literal de teste, nao e segredo)
                format="json",
            )
        assert resp.status_code == 200, resp.content
        log = AuditLog.objects.filter(action="RESET_PASSWORD").latest("created_at")
        assert log.usuario_id == superuser.id
        assert log.details["target_user_id"] == common_user.id
        assert log.details["contexto"] == "update"
        # Contrato de segurança: a senha nunca aparece na trilha.
        assert "NovaSenhaForte123" not in str(log.details)


# ============================================================================
# Exclusão de usuário e de grupo
# ============================================================================


class TestDeletions:
    def test_delete_usuario_audita(self, api_client, superuser, common_user, django_capture_on_commit_callbacks):
        uid = common_user.id
        api_client.force_authenticate(user=superuser)
        AuditLog.objects.filter(action="USER_DELETE").delete()
        with django_capture_on_commit_callbacks(execute=True):
            resp = api_client.delete(f"/api/usuarios-admin/{uid}/")
        assert resp.status_code == 204, resp.content
        assert not Usuario.objects.filter(id=uid).exists()
        log = AuditLog.objects.filter(action="USER_DELETE").latest("created_at")
        assert log.usuario_id == superuser.id
        assert log.details["target_user_id"] == uid

    def test_delete_grupo_audita_com_capabilities(
        self, api_client, superuser, caps, django_capture_on_commit_callbacks
    ):
        group = GroupFactory(name="GrupoDel")
        group.permissoes_funcionais.add(caps[0])
        gid = group.id
        api_client.force_authenticate(user=superuser)
        AuditLog.objects.filter(action="DELETE", model_name="Group").delete()
        with django_capture_on_commit_callbacks(execute=True):
            resp = api_client.delete(f"/api/grupos/{gid}/")
        assert resp.status_code == 204, resp.content
        log = AuditLog.objects.filter(action="DELETE", model_name="Group").latest("created_at")
        assert log.details["group_id"] == gid
        assert caps[0].codename in log.details["capabilities"]

    def test_delete_usuario_falho_nao_deixa_trilha_fantasma(
        self, superuser, common_user, django_capture_on_commit_callbacks
    ):
        # Regressão #1672 (achado adversarial P1): audit + delete no mesmo atomic.
        # Se o delete falha (ex.: ProtectedError), o on_commit é descartado no
        # rollback -> NENHUM USER_DELETE gravado (sem trilha de exclusão fantasma).
        uid = common_user.id
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user=superuser)
        AuditLog.objects.filter(action="USER_DELETE").delete()
        with mock.patch.object(Usuario, "delete", side_effect=RuntimeError("PROTECT")):
            with django_capture_on_commit_callbacks(execute=True):
                resp = client.delete(f"/api/usuarios-admin/{uid}/")
        assert resp.status_code == 500
        assert Usuario.objects.filter(id=uid).exists()  # não removido
        assert not AuditLog.objects.filter(action="USER_DELETE").exists()  # sem fantasma

    def test_delete_grupo_falho_nao_deixa_trilha_fantasma(self, superuser, caps, django_capture_on_commit_callbacks):
        group = GroupFactory(name="GrupoProt")
        group.permissoes_funcionais.add(caps[0])
        gid = group.id
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user=superuser)
        AuditLog.objects.filter(action="DELETE", model_name="Group").delete()
        with mock.patch.object(Group, "delete", side_effect=RuntimeError("PROTECT")):
            with django_capture_on_commit_callbacks(execute=True):
                resp = client.delete(f"/api/grupos/{gid}/")
        assert resp.status_code == 500
        assert Group.objects.filter(id=gid).exists()
        assert not AuditLog.objects.filter(action="DELETE", model_name="Group").exists()


# ============================================================================
# M07-03 (#1618): usuarios-admin REST audita create/update/activate/deactivate
# (o path REST antes so auditava senha e grupos; o flip de flags e a criacao
#  ficavam sem trilha — assimetria com o Django Admin, que ja auditava)
# ============================================================================


class TestUsuarioCadastralViaREST:
    def test_deactivate_audita_privilege(self, api_client, superuser, common_user, django_capture_on_commit_callbacks):
        api_client.force_authenticate(user=superuser)
        AuditLog.objects.filter(action="USER_PRIVILEGE_CHANGED").delete()
        with django_capture_on_commit_callbacks(execute=True):
            resp = api_client.patch(f"/api/usuarios-admin/{common_user.id}/", {"is_active": False}, format="json")
        assert resp.status_code == 200, resp.content
        log = AuditLog.objects.filter(action="USER_PRIVILEGE_CHANGED").latest("created_at")
        assert log.details["changes"]["is_active"] == {"before": True, "after": False}
        assert log.details["via"] == "rest_api"
        assert log.details["target_user_id"] == common_user.id

    def test_promote_superuser_audita_privilege(
        self, api_client, superuser, common_user, django_capture_on_commit_callbacks
    ):
        api_client.force_authenticate(user=superuser)
        AuditLog.objects.filter(action="USER_PRIVILEGE_CHANGED").delete()
        with django_capture_on_commit_callbacks(execute=True):
            resp = api_client.patch(f"/api/usuarios-admin/{common_user.id}/", {"is_superuser": True}, format="json")
        assert resp.status_code == 200, resp.content
        log = AuditLog.objects.filter(action="USER_PRIVILEGE_CHANGED").latest("created_at")
        assert log.details["changes"]["is_superuser"] == {"before": False, "after": True}
        assert log.details["via"] == "rest_api"

    def test_create_usuario_audita(self, api_client, superuser, django_capture_on_commit_callbacks):
        api_client.force_authenticate(user=superuser)
        AuditLog.objects.filter(action="CREATE", model_name="Usuario").delete()
        with django_capture_on_commit_callbacks(execute=True):
            resp = api_client.post(
                "/api/usuarios-admin/",
                {
                    "username": "novo_m0703",
                    "cpf": "11144477735",
                    "password": "SenhaForte123",  # gitleaks:allow (literal de teste, nao e segredo)
                    "email": "novo_m0703@t.com",
                    "first_name": "Novo",
                    "last_name": "User",
                },
                format="json",
            )
        assert resp.status_code == 201, resp.content
        log = AuditLog.objects.filter(action="CREATE", model_name="Usuario").latest("created_at")
        assert log.details["target_username"] == "novo_m0703"
        assert "target_user_id" in log.details

    def test_update_cadastral_audita_sem_pii(
        self, api_client, superuser, common_user, django_capture_on_commit_callbacks
    ):
        api_client.force_authenticate(user=superuser)
        AuditLog.objects.filter(action="UPDATE", model_name="Usuario").delete()
        with django_capture_on_commit_callbacks(execute=True):
            resp = api_client.patch(
                f"/api/usuarios-admin/{common_user.id}/", {"email": "novo_email@t.com"}, format="json"
            )
        assert resp.status_code == 200, resp.content
        log = AuditLog.objects.filter(action="UPDATE", model_name="Usuario").latest("created_at")
        assert "email" in log.details["campos"]
        # contrato PII: o VALOR do campo nunca entra nos details, so o NOME do campo
        assert "novo_email@t.com" not in str(log.details)


# ============================================================================
# Import de usuários (apply audita; dry-run não)
# ============================================================================


class TestImportAudit:
    def _csv(self, tmp_path, name: str) -> str:
        p = tmp_path / name
        p.write_text("cpf,nome\n11144477735,Fulano De Tal\n", encoding="utf-8")
        return str(p)

    def test_apply_audita_user_import(self, tmp_path, superuser, django_capture_on_commit_callbacks):
        path = self._csv(tmp_path, "u.csv")
        AuditLog.objects.filter(action="USER_IMPORT").delete()
        with django_capture_on_commit_callbacks(execute=True):
            result = import_usuarios_from_file(path=path, dry_run=False, actor=superuser)
        assert result["dry_run"] is False
        log = AuditLog.objects.filter(action="USER_IMPORT").latest("created_at")
        assert log.usuario_id == superuser.id
        assert log.details["created"] >= 1
        assert log.details["file"].endswith("u.csv")

    def test_dry_run_nao_audita(self, tmp_path, superuser, django_capture_on_commit_callbacks):
        path = self._csv(tmp_path, "u2.csv")
        AuditLog.objects.filter(action="USER_IMPORT").delete()
        with django_capture_on_commit_callbacks(execute=True):
            import_usuarios_from_file(path=path, dry_run=True, actor=superuser)
        assert not AuditLog.objects.filter(action="USER_IMPORT").exists()


# ============================================================================
# Django admin UsuarioAdmin (achado adversarial P1: mudar grupos/flags de
# privilégio pelo admin web não deixava trilha)
# ============================================================================


class TestUsuarioAdminAudit:
    def _admin(self) -> UsuarioAdmin:
        return UsuarioAdmin(Usuario, admin_site)

    def _request(self, actor: Usuario):
        req = RequestFactory().post("/admin/core/usuario/")
        req.user = actor
        return req

    def test_save_model_audita_concessao_de_superuser(self, superuser, common_user, django_capture_on_commit_callbacks):
        AuditLog.objects.filter(action="USER_PRIVILEGE_CHANGED").delete()
        admin_obj = self._admin()
        req = self._request(superuser)
        common_user.is_superuser = True  # concessão de superuser via admin
        with django_capture_on_commit_callbacks(execute=True):
            admin_obj.save_model(req, common_user, form=None, change=True)
        log = AuditLog.objects.filter(action="USER_PRIVILEGE_CHANGED").latest("created_at")
        assert log.usuario_id == superuser.id
        assert log.details["target_user_id"] == common_user.id
        assert log.details["changes"]["is_superuser"] == {"before": False, "after": True}
        assert log.details["via"] == "django_admin"

    def test_save_model_sem_flip_de_flag_nao_audita(self, superuser, common_user, django_capture_on_commit_callbacks):
        AuditLog.objects.filter(action="USER_PRIVILEGE_CHANGED").delete()
        admin_obj = self._admin()
        req = self._request(superuser)
        # Re-salva sem mudar flag -> sem trilha.
        with django_capture_on_commit_callbacks(execute=True):
            admin_obj.save_model(req, common_user, form=None, change=True)
        assert not AuditLog.objects.filter(action="USER_PRIVILEGE_CHANGED").exists()

    def test_save_related_audita_grupos(self, superuser, common_user, django_capture_on_commit_callbacks):
        group = GroupFactory(name="DAT")
        AuditLog.objects.filter(action="ASSIGN_GROUPS").delete()
        admin_obj = self._admin()
        req = self._request(superuser)

        class _FakeForm:
            instance = common_user

            def save_m2m(self):
                common_user.groups.set([group])

        with django_capture_on_commit_callbacks(execute=True):
            admin_obj.save_related(req, _FakeForm(), [], change=True)
        log = AuditLog.objects.filter(action="ASSIGN_GROUPS").latest("created_at")
        assert log.usuario_id == superuser.id
        assert log.details["target_user_id"] == common_user.id
        assert log.details["added_groups"] == ["DAT"]
