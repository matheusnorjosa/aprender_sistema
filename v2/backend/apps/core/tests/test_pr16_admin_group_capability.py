"""
PR 16 hardening RBAC (2026-05-04, último do programa): Admin UI
superuser-only para atribuição Group × Capability.

Cobre:
- Guarda de acesso: superuser passa, staff puro nega, anonymous redireciona.
- Guardas de mutação: add/delete bloqueados; codename readonly.
- Edição da relação `groups` persiste e invalida cache funcional.
- AuditLog `GROUP_CAPABILITY_CHANGED` consolidado por operação,
  com actor_user_id, capability_codename, added_groups, removed_groups,
  groups_after.
- Decisão D17: chamadas em série (add → remove) geram entries distintos
  com o delta correto.
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


@pytest.fixture(autouse=True)
def _reset_rbac_audit_buffer():
    """
    O seed `seed_functional_permissions(assign_default_groups=False)`
    dispara `m2m_changed.pre_clear` em todas as 16 capabilities, populando
    `_PENDING_GROUP_CAP_DELTAS`. Sem reset entre testes, o `save_related`
    do Admin flushaaria deltas vindos do seed — falsos positivos.
    """
    from apps.core.signals import _PENDING_GROUP_CAP_DELTAS

    _PENDING_GROUP_CAP_DELTAS.clear()
    yield
    _PENDING_GROUP_CAP_DELTAS.clear()


@pytest.fixture
def capability() -> PermissaoFuncional:
    """Garante que `view_compras_dashboard` exista (do seed). Sem grupos."""
    seed_functional_permissions(assign_default_groups=False)
    # Limpa o buffer poluído pelo seed antes do test rodar.
    from apps.core.signals import _PENDING_GROUP_CAP_DELTAS

    _PENDING_GROUP_CAP_DELTAS.clear()
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
# Edição de groups via Admin (com cache bust + AuditLog)
# ============================================================================


class TestAdminGroupEditing:
    def _change_url(self, capability: PermissaoFuncional) -> str:
        return f"/admin/core/permissaofuncional/{capability.pk}/change/"

    def _post_groups(
        self,
        client: Client,
        capability: PermissaoFuncional,
        group_ids: list[int],
    ):
        # Django Admin form submission para um ModelAdmin com filter_horizontal:
        # `groups` aceita lista; campos readonly não precisam estar no payload
        # mas precisamos de _continue/_save para POST válido.
        return client.post(
            self._change_url(capability),
            data={
                "groups": [str(g) for g in group_ids],
                "_save": "Salvar",
            },
        )

    def test_superuser_adiciona_grupo(self, superuser, capability, group_dat):
        c = Client()
        c.force_login(superuser)
        r = self._post_groups(c, capability, [group_dat.pk])
        assert r.status_code == 302  # redirect after save
        capability.refresh_from_db()
        assert list(capability.groups.values_list("name", flat=True)) == ["DAT"]

    def test_superuser_remove_grupo(self, superuser, capability, group_dat):
        capability.groups.add(group_dat)
        # Limpa AuditLog gerado pelo signal m2m_changed direto (fora de Admin)
        AuditLog.objects.filter(action="GROUP_CAPABILITY_CHANGED").delete()
        from apps.core.signals import _PENDING_GROUP_CAP_DELTAS

        _PENDING_GROUP_CAP_DELTAS.clear()

        c = Client()
        c.force_login(superuser)
        r = self._post_groups(c, capability, [])  # remove tudo
        assert r.status_code == 302
        capability.refresh_from_db()
        assert capability.groups.count() == 0

    def test_alteracao_persiste(self, superuser, capability, group_dat, group_diretoria):
        c = Client()
        c.force_login(superuser)
        self._post_groups(c, capability, [group_dat.pk, group_diretoria.pk])
        capability.refresh_from_db()
        assert set(capability.groups.values_list("name", flat=True)) == {"DAT", "Diretoria"}


# ============================================================================
# Cache bust automático
# ============================================================================


class TestCacheInvalidation:
    def test_usuario_do_grupo_recebe_capability_apos_admin_edit(self, superuser, capability, group_dat):
        # User pertence a DAT mas DAT ainda não tem `view_compras_dashboard`.
        member = _make_user(label="dat_member")
        member.groups.add(group_dat)
        cache.clear()
        assert "view_compras_dashboard" not in get_user_functional_permissions(member)

        # Superuser atribui capability ao grupo via Admin.
        c = Client()
        c.force_login(superuser)
        c.post(
            f"/admin/core/permissaofuncional/{capability.pk}/change/",
            data={"groups": [str(group_dat.pk)], "_save": "Salvar"},
        )

        # Cache deve ter sido invalidado pelo signal — próxima chamada
        # vê a capability sem precisar restart.
        assert "view_compras_dashboard" in get_user_functional_permissions(member)


# ============================================================================
# AuditLog consolidado (GROUP_CAPABILITY_CHANGED)
# ============================================================================


class TestAuditLog:
    def test_auditlog_criado_com_actor_e_deltas(self, superuser, capability, group_dat):
        AuditLog.objects.filter(action="GROUP_CAPABILITY_CHANGED").delete()
        from apps.core.signals import _PENDING_GROUP_CAP_DELTAS

        _PENDING_GROUP_CAP_DELTAS.clear()
        c = Client()
        c.force_login(superuser)
        c.post(
            f"/admin/core/permissaofuncional/{capability.pk}/change/",
            data={"groups": [str(group_dat.pk)], "_save": "Salvar"},
        )
        log = AuditLog.objects.filter(action="GROUP_CAPABILITY_CHANGED").latest("created_at")
        assert log.usuario_id == superuser.id
        assert log.model_name == "PermissaoFuncional"
        d = log.details
        assert d["actor_user_id"] == superuser.id
        assert d["capability_codename"] == capability.codename
        assert d["added_groups"] == ["DAT"]
        assert d["removed_groups"] == []
        assert d["groups_after"] == ["DAT"]

    def test_remocao_explicita_lista_grupos_removidos(self, superuser, capability, group_dat, group_diretoria):
        capability.groups.add(group_dat, group_diretoria)
        AuditLog.objects.filter(action="GROUP_CAPABILITY_CHANGED").delete()
        from apps.core.signals import _PENDING_GROUP_CAP_DELTAS

        _PENDING_GROUP_CAP_DELTAS.clear()

        c = Client()
        c.force_login(superuser)
        c.post(
            f"/admin/core/permissaofuncional/{capability.pk}/change/",
            data={"groups": [], "_save": "Salvar"},
        )
        log = AuditLog.objects.filter(action="GROUP_CAPABILITY_CHANGED").latest("created_at")
        d = log.details
        assert d["added_groups"] == []
        # D17: remoção total → lista explícita, não "ALL".
        assert sorted(d["removed_groups"]) == ["DAT", "Diretoria"]
        assert d["groups_after"] == []

    def test_uma_operacao_admin_gera_um_auditlog_por_capability(
        self, superuser, capability, group_dat, group_diretoria
    ):
        capability.groups.add(group_dat)
        AuditLog.objects.filter(action="GROUP_CAPABILITY_CHANGED").delete()
        from apps.core.signals import _PENDING_GROUP_CAP_DELTAS

        _PENDING_GROUP_CAP_DELTAS.clear()

        c = Client()
        c.force_login(superuser)
        # Em uma única operação Admin: remove DAT + adiciona Diretoria.
        c.post(
            f"/admin/core/permissaofuncional/{capability.pk}/change/",
            data={"groups": [str(group_diretoria.pk)], "_save": "Salvar"},
        )
        # Apenas UM AuditLog para essa capability nesta operação.
        logs = AuditLog.objects.filter(
            action="GROUP_CAPABILITY_CHANGED",
            details__capability_codename=capability.codename,
        )
        assert logs.count() == 1
        log = logs.first()
        assert log is not None
        d = log.details
        assert d["added_groups"] == ["Diretoria"]
        assert d["removed_groups"] == ["DAT"]
        assert d["groups_after"] == ["Diretoria"]

    def test_save_sem_mudanca_em_groups_nao_emite_auditlog(self, superuser, capability, group_dat):
        capability.groups.add(group_dat)
        AuditLog.objects.filter(action="GROUP_CAPABILITY_CHANGED").delete()
        from apps.core.signals import _PENDING_GROUP_CAP_DELTAS

        _PENDING_GROUP_CAP_DELTAS.clear()

        c = Client()
        c.force_login(superuser)
        # Re-salva com o mesmo set → sem delta.
        c.post(
            f"/admin/core/permissaofuncional/{capability.pk}/change/",
            data={"groups": [str(group_dat.pk)], "_save": "Salvar"},
        )
        assert not AuditLog.objects.filter(action="GROUP_CAPABILITY_CHANGED").exists()
