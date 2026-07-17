"""
P0-0 — Proteção Tier-0 de contas superuser (auditoria 2026-07-17).

Contexto (v2/docs/audits/2026-07-17-rbac-security-audit.md §4.1):
Uma conta com `manage_admin_registries` (DAT) conseguia redefinir a senha de um
superuser e tomar a conta em UMA requisição, além de desativar/editar/excluir/
reagrupar superusers pelo `UsuarioAdminViewSet`, e alterá-los via import por CPF.

Invariante de segurança (o que estes testes asseguram):
- Um não-superuser NUNCA lê, altera ou exclui uma conta que já é superuser.
  Objeto fora do escopo == inexistente → **404** (indistinguível de não existir).
- DAT CONTINUA administrando contas comuns (inclusive reset de senha de comum —
  decisão G2 é separada). O bypass do superuser permanece total.
- O último superuser ativo não pode ser removido por esta API (anti-lockout).
- Importação em lote por CPF nunca modifica conta superuser.
- Vale para os dois aliases de rota (path canônico e o alias v1 deprecado).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.core.models import Usuario
from apps.core.services.usuarios_import import import_usuarios_from_file
from apps.core.tests.factories import GroupFactory, UsuarioFactory

SUPERUSER_PASSWORD = "SuperOldPass!123"
COMMON_PASSWORD = "CommonOld!123"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def usuario_dat(db):
    """DAT: tem manage_admin_registries + manage_purchases_and_materials (seed)."""
    user = UsuarioFactory(username="dat_p0", cpf="90000000001")
    user.groups.add(GroupFactory(name="DAT"))
    return user


@pytest.fixture
def superuser(db):
    """Alvo Tier-0: único superuser ativo, senha conhecida, sem grupos, sem nome."""
    return UsuarioFactory(
        username="super_admin_p0",
        cpf="90000000002",
        password=SUPERUSER_PASSWORD,
        superuser=True,
    )


@pytest.fixture
def common_user(db):
    """Conta comum administrável pelo DAT."""
    return UsuarioFactory(
        username="comum_p0",
        cpf="90000000003",
        password=COMMON_PASSWORD,
    )


@pytest.mark.django_db
@pytest.mark.parametrize("ns", ["core", "core-v1"])
class TestSuperuserTargetProtectionAPI:
    """DAT (não-superuser) não alcança superusers pelo UsuarioAdminViewSet.

    Parametrizado por namespace de rota: `core` (path canônico) e `core-v1`
    (alias v1 deprecado) — ambos incluem `apps.core.urls` e apontam para o mesmo
    viewset. Via `reverse` (sem literal do alias) p/ respeitar o guard rail #796.
    """

    @staticmethod
    def _detail(ns, pk):
        return reverse(f"{ns}:usuario-admin-detail", args=[pk])

    @staticmethod
    def _list(ns):
        return reverse(f"{ns}:usuario-admin-list")

    @staticmethod
    def _assign_groups(ns, pk):
        return reverse(f"{ns}:usuario-admin-assign-groups", args=[pk])

    def test_dat_patch_superuser_password_returns_404_and_password_unchanged(
        self, api_client, usuario_dat, superuser, ns
    ):
        api_client.force_authenticate(user=usuario_dat)
        resp = api_client.patch(
            self._detail(ns, superuser.id),
            {"password": "Hacked!newpass9"},
            format="json",
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        superuser.refresh_from_db()
        assert superuser.check_password(SUPERUSER_PASSWORD)
        assert not superuser.check_password("Hacked!newpass9")

    def test_dat_patch_superuser_is_active_returns_404_and_still_active(self, api_client, usuario_dat, superuser, ns):
        api_client.force_authenticate(user=usuario_dat)
        resp = api_client.patch(
            self._detail(ns, superuser.id),
            {"is_active": False},
            format="json",
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        superuser.refresh_from_db()
        assert superuser.is_active is True

    def test_dat_patch_superuser_cadastrais_returns_404_and_unchanged(self, api_client, usuario_dat, superuser, ns):
        api_client.force_authenticate(user=usuario_dat)
        resp = api_client.patch(
            self._detail(ns, superuser.id),
            {"email": "hacked@example.com", "first_name": "Hacker"},
            format="json",
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        superuser.refresh_from_db()
        assert superuser.email != "hacked@example.com"
        assert superuser.first_name == ""

    def test_dat_patch_superuser_group_ids_returns_404_and_groups_unchanged(
        self, api_client, usuario_dat, superuser, ns
    ):
        grupo = GroupFactory(name="Formador")
        api_client.force_authenticate(user=usuario_dat)
        resp = api_client.patch(
            self._detail(ns, superuser.id),
            {"group_ids": [grupo.id]},
            format="json",
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        superuser.refresh_from_db()
        assert superuser.groups.count() == 0

    def test_dat_delete_superuser_returns_404_and_still_exists(self, api_client, usuario_dat, superuser, ns):
        api_client.force_authenticate(user=usuario_dat)
        resp = api_client.delete(self._detail(ns, superuser.id))
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert Usuario.objects.filter(pk=superuser.id).exists()

    def test_dat_assign_groups_to_superuser_returns_404_and_groups_unchanged(
        self, api_client, usuario_dat, superuser, ns
    ):
        grupo = GroupFactory(name="Formador")
        api_client.force_authenticate(user=usuario_dat)
        resp = api_client.post(
            self._assign_groups(ns, superuser.id),
            {"group_ids": [grupo.id]},
            format="json",
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        superuser.refresh_from_db()
        assert superuser.groups.count() == 0

    def test_dat_retrieve_superuser_returns_404(self, api_client, usuario_dat, superuser, ns):
        api_client.force_authenticate(user=usuario_dat)
        resp = api_client.get(self._detail(ns, superuser.id))
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_dat_list_excludes_superuser(self, api_client, usuario_dat, superuser, common_user, ns):
        api_client.force_authenticate(user=usuario_dat)
        resp = api_client.get(self._list(ns))
        assert resp.status_code == status.HTTP_200_OK
        ids = {item["id"] for item in resp.data["results"]}
        assert superuser.id not in ids
        assert common_user.id in ids

    def test_dat_filter_is_superuser_true_returns_empty(self, api_client, usuario_dat, superuser, ns):
        api_client.force_authenticate(user=usuario_dat)
        resp = api_client.get(self._list(ns) + "?is_superuser=true")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["results"] == []


@pytest.mark.django_db
class TestDatStillManagesCommonUsers:
    """Regressão: o hotfix NÃO tira do DAT a administração de contas comuns."""

    def test_dat_can_still_reset_common_user_password(self, api_client, usuario_dat, common_user):
        api_client.force_authenticate(user=usuario_dat)
        resp = api_client.patch(
            f"/api/usuarios-admin/{common_user.id}/",
            {"password": "NewCommon!456"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        common_user.refresh_from_db()
        assert common_user.check_password("NewCommon!456")

    def test_dat_can_still_retrieve_common_user(self, api_client, usuario_dat, common_user):
        api_client.force_authenticate(user=usuario_dat)
        resp = api_client.get(f"/api/usuarios-admin/{common_user.id}/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["id"] == common_user.id


@pytest.mark.django_db
class TestSuperuserActorBypassIntact:
    """Regressão: o superuser mantém controle total sobre superusers."""

    def test_superuser_actor_can_retrieve_superuser(self, api_client, superuser):
        actor = UsuarioFactory(username="super_actor", cpf="90000000009", superuser=True)
        api_client.force_authenticate(user=actor)
        resp = api_client.get(f"/api/usuarios-admin/{superuser.id}/")
        assert resp.status_code == status.HTTP_200_OK

    def test_superuser_actor_can_reset_superuser_password(self, api_client, superuser):
        actor = UsuarioFactory(username="super_actor2", cpf="90000000010", superuser=True)
        api_client.force_authenticate(user=actor)
        resp = api_client.patch(
            f"/api/usuarios-admin/{superuser.id}/",
            {"password": "RotatedByRoot!789"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        superuser.refresh_from_db()
        assert superuser.check_password("RotatedByRoot!789")

    def test_superuser_actor_cannot_delete_last_active_superuser(self, api_client, superuser):
        # `superuser` é o único superuser ativo — excluí-lo deixaria zero.
        api_client.force_authenticate(user=superuser)
        resp = api_client.delete(f"/api/usuarios-admin/{superuser.id}/")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert Usuario.objects.filter(pk=superuser.id).exists()

    def test_superuser_actor_can_delete_non_last_superuser(self, api_client, superuser):
        actor = UsuarioFactory(username="super_actor3", cpf="90000000011", superuser=True)
        api_client.force_authenticate(user=actor)
        resp = api_client.delete(f"/api/usuarios-admin/{superuser.id}/")
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not Usuario.objects.filter(pk=superuser.id).exists()


@pytest.mark.django_db
class TestSuperuserSerializerGuard:
    """Defense-in-depth no serializer (a queryset da view já dá 404 antes)."""

    def _request(self, user):
        from rest_framework.test import APIRequestFactory

        req = APIRequestFactory().patch("/")
        req.user = user
        return req

    def test_serializer_rejects_superuser_instance_for_non_superuser(self, usuario_dat, superuser):
        from apps.core.serializers.usuario import UsuarioAdminSerializer

        serializer = UsuarioAdminSerializer(
            instance=superuser,
            data={"first_name": "Hacker"},
            partial=True,
            context={"request": self._request(usuario_dat)},
        )
        assert not serializer.is_valid()

    def test_serializer_allows_superuser_instance_for_superuser(self, superuser):
        from apps.core.serializers.usuario import UsuarioAdminSerializer

        actor = UsuarioFactory(username="root_ctx", cpf="90000000012", superuser=True)
        serializer = UsuarioAdminSerializer(
            instance=superuser,
            data={"first_name": "Legit"},
            partial=True,
            context={"request": self._request(actor)},
        )
        assert serializer.is_valid(), serializer.errors


@pytest.mark.django_db
class TestSuperuserImportProtection:
    """Import por CPF nunca modifica conta superuser."""

    def test_import_by_cpf_does_not_modify_superuser(self, tmp_path, superuser):
        GroupFactory(name="Formador")
        csv_path = tmp_path / "usuarios.csv"
        csv_path.write_text(
            "cpf,nome,ativo,grupos\n" f"{superuser.cpf},Hacker Invasor,nao,Formador\n",
            encoding="utf-8",
        )

        result = import_usuarios_from_file(path=str(csv_path), dry_run=False)

        superuser.refresh_from_db()
        assert superuser.first_name == ""  # segurança: nome NÃO foi alterado
        assert superuser.groups.count() == 0
        assert superuser.is_active is True
        assert superuser.check_password(SUPERUSER_PASSWORD)
        assert result["stats"]["updated"] == 0
        assert result["stats"]["skipped"]["superuser_protected"] == 1

    def test_import_still_updates_common_user_by_cpf(self, tmp_path, common_user):
        csv_path = tmp_path / "usuarios.csv"
        csv_path.write_text(
            "cpf,nome,telefone\n" f"{common_user.cpf},Fulano Atualizado,85988887777\n",
            encoding="utf-8",
        )

        result = import_usuarios_from_file(path=str(csv_path), dry_run=False)

        common_user.refresh_from_db()
        assert common_user.telefone == "85988887777"
        assert result["stats"]["updated"] == 1
