"""
PR 16 hardening RBAC (2026-05-04): Admin UI superuser-only para atribuição
Group × Capability. Atualizado no #1672: a auditoria não usa mais o buffer
global `_PENDING_GROUP_CAP_DELTAS` — o Admin `save_related` captura before/after
e delega ao serviço transacional `apps.core.services.audit`, que emite o
AuditLog em `transaction.on_commit`. Por isso os POSTs que verificam AuditLog
rodam dentro de `django_capture_on_commit_callbacks(execute=True)`.

Desde a D4 do ADR-020 (PR A da arquitetura de permissões, 14/10/2026) o Admin
só mostra: a matriz Group × Capability muda só por PR (migration de dados).
O `save_related` e o AuditLog do Admin saíram junto com a edição.

Cobre:
- Guarda de acesso: superuser passa, staff puro nega, anonymous redireciona.
- Guardas de mutação: add/change/delete bloqueados; codename readonly.
- POST de `groups` no change view → 403, nada gravado nem auditado.
- Escrita direta na M2M (o que a migration faz) invalida o cache funcional.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportMissingTypeStubs=false, reportUnusedFunction=false, reportIndexIssue=false

from __future__ import annotations

import itertools

from django.contrib.auth.models import Group
from django.core.cache import cache
from django.test import Client

import pytest

from apps.core.models import AuditLog, PermissaoFuncional, Usuario
from apps.core.services.functional_permissions_seed import seed_functional_permissions
from apps.core.services.rbac_permissions import get_user_functional_permissions
from apps.core.tests.factories import GroupFactory, UsuarioFactory

pytestmark = pytest.mark.django_db


_CPF_COUNTER = itertools.count(73000000000)
ADMIN_LIST_URL = "/admin/core/permissaofuncional/"


def _make_user(*, is_superuser: bool = False, is_staff: bool = False, label: str = "u") -> Usuario:
    cpf = str(next(_CPF_COUNTER)).zfill(11)
    return UsuarioFactory(
        username=f"{label}_{cpf}",
        email=f"{label}_{cpf}@test.com",
        password="testpass",
        cpf=cpf,
        is_superuser=is_superuser,
        is_staff=is_staff or is_superuser,
    )


@pytest.fixture
def superuser() -> Usuario:
    return _make_user(is_superuser=True, label="su")


@pytest.fixture
def staff_user() -> Usuario:
    return _make_user(is_staff=True, label="staff")


@pytest.fixture
def capability() -> PermissaoFuncional:
    """Garante que `view_compras_dashboard` exista (do seed). Sem grupos."""
    seed_functional_permissions(assign_default_groups=False)
    AuditLog.objects.filter(action="GROUP_CAPABILITY_CHANGED").delete()
    return PermissaoFuncional.objects.get(codename="view_compras_dashboard")


@pytest.fixture
def group_diretoria(db) -> Group:
    return GroupFactory(name="Diretoria")


@pytest.fixture
def group_dat(db) -> Group:
    return GroupFactory(name="DAT")


# ============================================================================
# Acesso ao Admin (superuser-only via SuperuserOnlyAdminSite)
# ============================================================================


class TestAdminAccess:
    def test_superuser_lista_capabilities(self, superuser):
        c = Client()
        c.force_login(superuser)
        r = c.get(ADMIN_LIST_URL)
        assert r.status_code == 200

    def test_staff_puro_nao_acessa(self, staff_user):
        c = Client()
        c.force_login(staff_user)
        r = c.get(ADMIN_LIST_URL)
        # SuperuserOnlyAdminSite redireciona não-superuser para login.
        assert r.status_code in {302, 403}
        if r.status_code == 302:
            assert "/admin/login" in r["Location"]

    def test_anonymous_redireciona_para_login(self):
        c = Client()
        r = c.get(ADMIN_LIST_URL)
        assert r.status_code == 302
        assert "/admin/login" in r["Location"]


# ============================================================================
# Guardas estritos (add/delete bloqueados, codename readonly)
# ============================================================================


class TestAdminGuards:
    def test_add_capability_bloqueado(self, superuser):
        c = Client()
        c.force_login(superuser)
        # Botão de Adicionar não deve aparecer; POST direto retorna 403.
        r = c.get("/admin/core/permissaofuncional/add/")
        assert r.status_code == 403

    def test_delete_capability_bloqueado(self, superuser, capability):
        c = Client()
        c.force_login(superuser)
        r = c.post(
            f"/admin/core/permissaofuncional/{capability.pk}/delete/",
            {"post": "yes"},
        )
        assert r.status_code == 403

    def test_codename_e_readonly_no_change_view(self, superuser, capability):
        c = Client()
        c.force_login(superuser)
        r = c.get(f"/admin/core/permissaofuncional/{capability.pk}/change/")
        assert r.status_code == 200
        # Em readonly_fields, o campo não vira <input name="codename">,
        # vira um <div class="readonly">. Asserção robusta:
        body = r.content.decode("utf-8", errors="replace")
        assert 'name="codename"' not in body, "codename não deve ser editável (deve estar em readonly_fields)"


# ============================================================================
# Edição de groups via Admin: bloqueada desde a D4 do ADR-020 (matriz muda só por PR)
# ============================================================================


class TestAdminSemEdicaoDeGrupos:
    def _post_groups(self, client: Client, capability: PermissaoFuncional, group_ids: list[int]):
        return client.post(
            f"/admin/core/permissaofuncional/{capability.pk}/change/",
            data={"groups": [str(g) for g in group_ids], "_save": "Salvar"},
        )

    def test_superuser_nao_adiciona_grupo(self, superuser, capability, group_dat):
        c = Client()
        c.force_login(superuser)
        r = self._post_groups(c, capability, [group_dat.pk])
        assert r.status_code == 403
        assert not capability.groups.exists()

    def test_superuser_nao_remove_grupo(self, superuser, capability, group_dat):
        capability.groups.add(group_dat)
        c = Client()
        c.force_login(superuser)
        r = self._post_groups(c, capability, [])
        assert r.status_code == 403
        assert list(capability.groups.values_list("name", flat=True)) == ["DAT"]

    def test_tentativa_nao_emite_auditlog(self, superuser, capability, group_dat, django_capture_on_commit_callbacks):
        c = Client()
        c.force_login(superuser)
        with django_capture_on_commit_callbacks(execute=True):
            self._post_groups(c, capability, [group_dat.pk])
        assert not AuditLog.objects.filter(action="GROUP_CAPABILITY_CHANGED").exists()


# ============================================================================
# Cache bust automático (a escrita na M2M agora vem da migration do PR)
# ============================================================================


class TestCacheInvalidation:
    @pytest.mark.usefixtures("modo_uniao")  # grupo com capacidade: só vale no modo soma (PR 12)
    def test_usuario_do_grupo_recebe_capability_apos_escrita_na_m2m(self, capability, group_dat):
        # User pertence a DAT mas DAT ainda não tem `view_compras_dashboard`.
        member = _make_user(label="dat_member")
        member.groups.add(group_dat)
        cache.clear()
        assert "view_compras_dashboard" not in get_user_functional_permissions(member)

        # Mesma escrita que uma migration de dados faz (D4): o signal invalida o cache.
        capability.groups.add(group_dat)

        assert "view_compras_dashboard" in get_user_functional_permissions(member)
