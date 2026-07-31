"""
Servico central de auditoria transacional — `apps.core.services.audit` (#1672).

Cobre:
- `registrar_auditoria`: adia p/ on_commit por padrao; `imediato=True` cria na hora.
- `_actor_id`: None / AnonymousUser -> None; usuario real -> id.
- `auditar_group_capability_change`: contrato de details + no-op sem delta.
- `auditar_group_capabilities_set`: emite 1 entry por capability afetada (path REST).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false

from __future__ import annotations

import itertools

from django.contrib.auth.models import AnonymousUser, Group

import pytest

from apps.core.models import AuditLog, PermissaoFuncional
from apps.core.services.audit import (
    _actor_id,
    auditar_assign_groups,
    auditar_group_capabilities_set,
    auditar_group_capability_change,
    auditar_reset_senha,
    auditar_user_delete,
    registrar_auditoria,
)
from apps.core.services.functional_permissions_seed import seed_functional_permissions
from apps.core.tests.factories import GroupFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

_CPF_COUNTER = itertools.count(74000000000)


def _make_user(label: str = "u"):
    cpf = str(next(_CPF_COUNTER)).zfill(11)
    return UsuarioFactory(username=f"{label}_{cpf}", email=f"{label}_{cpf}@t.com", cpf=cpf)


@pytest.fixture
def group_dat() -> Group:
    return GroupFactory(name="DAT")


@pytest.fixture
def capability() -> PermissaoFuncional:
    seed_functional_permissions(assign_default_groups=False)
    AuditLog.objects.filter(action="GROUP_CAPABILITY_CHANGED").delete()
    return PermissaoFuncional.objects.get(codename="view_compras_dashboard")


# ============================================================================
# registrar_auditoria — semantica on_commit
# ============================================================================


class TestRegistrarAuditoria:
    def test_adia_ate_commit(self, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=False) as callbacks:
            registrar_auditoria(actor=None, action="TEST_DEFERRED", details={"x": 1})
            # Ainda nao criou — insert adiado p/ on_commit.
            assert not AuditLog.objects.filter(action="TEST_DEFERRED").exists()
        assert len(callbacks) == 1
        # execute=False -> callback nao rodou; nada gravado.
        assert not AuditLog.objects.filter(action="TEST_DEFERRED").exists()

    def test_cria_no_commit(self, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=True):
            registrar_auditoria(actor=None, action="TEST_COMMITTED", details={"x": 1})
        assert AuditLog.objects.filter(action="TEST_COMMITTED").count() == 1

    def test_imediato_cria_na_hora(self):
        registrar_auditoria(actor=None, action="TEST_IMMEDIATE", imediato=True)
        assert AuditLog.objects.filter(action="TEST_IMMEDIATE").count() == 1

    def test_details_copiado_por_valor(self):
        d = {"a": 1}
        registrar_auditoria(actor=None, action="TEST_COPY", details=d, imediato=True)
        d["a"] = 999  # mutacao pos-chamada nao deve afetar o registro
        log = AuditLog.objects.filter(action="TEST_COPY").latest("created_at")
        assert log.details["a"] == 1


# ============================================================================
# _actor_id
# ============================================================================


class TestActorId:
    def test_none(self):
        assert _actor_id(None) is None

    def test_anonymous(self):
        assert _actor_id(AnonymousUser()) is None

    def test_usuario_real(self):
        cpf = str(next(_CPF_COUNTER)).zfill(11)
        user = UsuarioFactory(username=f"a_{cpf}", email=f"a_{cpf}@t.com", cpf=cpf)
        assert _actor_id(user) == user.id

    def test_actor_none_gera_log_sistema(self):
        registrar_auditoria(actor=None, action="TEST_SYSTEM", imediato=True)
        log = AuditLog.objects.filter(action="TEST_SYSTEM").latest("created_at")
        assert log.usuario_id is None


# ============================================================================
# auditar_group_capability_change (path Admin/perm.groups)
# ============================================================================


class TestGroupCapabilityChange:
    def test_contrato_de_details(self, capability, group_dat):
        ok = auditar_group_capability_change(
            actor=None,
            capability=capability,
            before_group_ids=[],
            after_group_ids=[group_dat.pk],
            imediato=True,
        )
        assert ok is True
        log = AuditLog.objects.filter(action="GROUP_CAPABILITY_CHANGED").latest("created_at")
        assert log.model_name == "PermissaoFuncional"
        d = log.details
        assert d["capability_codename"] == capability.codename
        assert d["capability_id"] == capability.pk
        assert d["added_groups"] == ["DAT"]
        assert d["removed_groups"] == []
        assert d["groups_after"] == ["DAT"]

    def test_remocao(self, capability, group_dat):
        ok = auditar_group_capability_change(
            actor=None,
            capability=capability,
            before_group_ids=[group_dat.pk],
            after_group_ids=[],
            imediato=True,
        )
        assert ok is True
        log = AuditLog.objects.filter(action="GROUP_CAPABILITY_CHANGED").latest("created_at")
        d = log.details
        assert d["added_groups"] == []
        assert d["removed_groups"] == ["DAT"]
        assert d["groups_after"] == []

    def test_noop_sem_delta(self, capability, group_dat):
        ok = auditar_group_capability_change(
            actor=None,
            capability=capability,
            before_group_ids=[group_dat.pk],
            after_group_ids=[group_dat.pk],
            imediato=True,
        )
        assert ok is False
        assert not AuditLog.objects.filter(action="GROUP_CAPABILITY_CHANGED").exists()


# ============================================================================
# auditar_group_capabilities_set (path REST group.permissoes_funcionais.set)
# ============================================================================


class TestGroupCapabilitiesSet:
    def test_emite_um_por_capability(self, capability, group_dat):
        seed_functional_permissions(assign_default_groups=False)
        cap_a = capability
        cap_b = PermissaoFuncional.objects.exclude(pk=cap_a.pk).first()
        assert cap_b is not None

        before = list(group_dat.permissoes_funcionais.values_list("pk", flat=True))
        group_dat.permissoes_funcionais.set([cap_a.pk, cap_b.pk])
        AuditLog.objects.filter(action="GROUP_CAPABILITY_CHANGED").delete()

        n = auditar_group_capabilities_set(
            actor=None,
            group=group_dat,
            before_cap_ids=before,
            after_cap_ids=[cap_a.pk, cap_b.pk],
            imediato=True,
        )
        assert n == 2
        logs = AuditLog.objects.filter(action="GROUP_CAPABILITY_CHANGED")
        assert logs.count() == 2
        for log in logs:
            assert log.details["added_groups"] == ["DAT"]
            assert log.details["removed_groups"] == []
            assert log.details["via"] == "group_serializer"
            assert "DAT" in log.details["groups_after"]

    def test_remocao_de_capability(self, capability, group_dat):
        group_dat.permissoes_funcionais.set([capability.pk])
        before = [capability.pk]
        group_dat.permissoes_funcionais.set([])
        AuditLog.objects.filter(action="GROUP_CAPABILITY_CHANGED").delete()

        n = auditar_group_capabilities_set(
            actor=None,
            group=group_dat,
            before_cap_ids=before,
            after_cap_ids=[],
            imediato=True,
        )
        assert n == 1
        log = AuditLog.objects.filter(action="GROUP_CAPABILITY_CHANGED").latest("created_at")
        assert log.details["removed_groups"] == ["DAT"]
        assert log.details["added_groups"] == []
        assert log.details["groups_after"] == []  # grupo removido -> cap sem esse grupo

    def test_noop_sem_delta(self, capability, group_dat):
        n = auditar_group_capabilities_set(
            actor=None,
            group=group_dat,
            before_cap_ids=[capability.pk],
            after_cap_ids=[capability.pk],
            imediato=True,
        )
        assert n == 0
        assert not AuditLog.objects.filter(action="GROUP_CAPABILITY_CHANGED").exists()


# ============================================================================
# Helpers de privilegio de usuario (ASSIGN_GROUPS / RESET_PASSWORD / USER_DELETE)
# ============================================================================


class TestUserPrivilegeHelpers:
    def test_assign_groups_emite_com_delta(self, group_dat):
        user = _make_user()
        ok = auditar_assign_groups(
            actor=None,
            target_user=user,
            before_group_ids=[],
            after_group_ids=[group_dat.pk],
            imediato=True,
        )
        assert ok is True
        log = AuditLog.objects.filter(action="ASSIGN_GROUPS").latest("created_at")
        assert log.model_name == "Usuario"
        assert log.details["target_user_id"] == user.id
        assert log.details["added_groups"] == ["DAT"]
        assert log.details["removed_groups"] == []
        assert log.details["groups_after"] == ["DAT"]

    def test_assign_groups_noop(self, group_dat):
        user = _make_user()
        ok = auditar_assign_groups(
            actor=None,
            target_user=user,
            before_group_ids=[group_dat.pk],
            after_group_ids=[group_dat.pk],
            imediato=True,
        )
        assert ok is False
        assert not AuditLog.objects.filter(action="ASSIGN_GROUPS").exists()

    def test_reset_senha_nunca_inclui_a_senha(self):
        user = _make_user()
        auditar_reset_senha(actor=None, target_user=user, contexto="update", imediato=True)
        log = AuditLog.objects.filter(action="RESET_PASSWORD").latest("created_at")
        assert log.model_name == "Usuario"
        assert log.details["target_user_id"] == user.id
        assert log.details["contexto"] == "update"
        # Contrato de seguranca: senha NUNCA aparece nos details.
        assert set(log.details.keys()) == {"actor_user_id", "target_user_id", "target_username", "contexto"}

    def test_user_delete_captura_identidade_do_alvo(self):
        user = _make_user()
        uid = user.id
        uname = user.username
        auditar_user_delete(actor=None, target_user=user, imediato=True)
        log = AuditLog.objects.filter(action="USER_DELETE").latest("created_at")
        assert log.details["target_user_id"] == uid
        assert log.details["target_username"] == uname

    def test_user_delete_auto_exclusao_zera_fk_mas_preserva_ator(self):
        # actor == target: a FK usuario_id precisa ser None (a linha some), mas
        # o ator fica registrado em details.actor_user_id.
        user = _make_user()
        auditar_user_delete(actor=user, target_user=user, imediato=True)
        log = AuditLog.objects.filter(action="USER_DELETE").latest("created_at")
        assert log.usuario_id is None
        assert log.details["actor_user_id"] == user.id
        assert log.details["target_user_id"] == user.id

    def test_user_delete_ator_distinto_mantem_fk(self):
        actor = _make_user(label="actor")
        target = _make_user(label="target")
        auditar_user_delete(actor=actor, target_user=target, imediato=True)
        log = AuditLog.objects.filter(action="USER_DELETE").latest("created_at")
        assert log.usuario_id == actor.id
        assert log.details["target_user_id"] == target.id
