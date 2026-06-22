"""
Tests para Capability Policy Layer (Epic 4.1, Issue #1232).

Cobertura:
- Matrix integrity (orphans, empty entries, type)
- Naming convention (canonical verbs, class ↔ key mapping, no _policy suffix)
- Capabilities reais (existem na seed; não há roles na matriz)
- Smoke por Policy (anonymous bloqueia, superuser passa, user com cap correto passa)
- Edge cases (unknown policy, composition OR, fail-secure)

Padrão: TDD-first — testes escritos antes da implementação.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false, reportPrivateUsage=false

from __future__ import annotations

import re
from typing import Iterable

from django.contrib.auth.models import AnonymousUser
from rest_framework import permissions as drf_permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.test import APIRequestFactory

import pytest

from apps.core.models import PermissaoFuncional
from apps.core.rbac import policies as policies_module
from apps.core.rbac.policies import ACCESS_POLICIES, _PolicyPermission
from apps.core.tests.factories import GroupFactory, UsuarioFactory

pytestmark = pytest.mark.django_db


# ============================================================================
# Helpers
# ============================================================================

# Snake_case canonical verb prefixes (decisão #4 do stakeholder, 2026-04-26).
CANONICAL_VERB_PREFIX = re.compile(r"^(access|use|import|manage|view)_[a-z][a-z0-9_]*$")

# Roles do projeto — NÃO devem aparecer na matriz (decisão #6 — só capabilities).
ROLE_NAMES = frozenset(
    {
        "DAT",
        "Controle",
        "Diretoria",
        "Superintendência",
        "Gerente",
        "Coordenador",
        "Apoio de Coordenação",
        "Formador",
    }
)


def _all_policy_classes() -> list[type[_PolicyPermission]]:
    """Subclasses concretas de _PolicyPermission (com `policy` não-vazio)."""
    return [cls for cls in _PolicyPermission.__subclasses__() if cls.policy]


def _camelize(snake: str) -> str:
    """access_audit_logs → AccessAuditLogs."""
    return "".join(part.capitalize() for part in snake.split("_"))


_USER_COUNTER = {"i": 0}


def _next_cpf() -> str:
    """CPF único determinístico por test session (evita colisão de hash não-determinístico)."""
    _USER_COUNTER["i"] += 1
    return f"99988{_USER_COUNTER['i']:06d}"


def _make_user(username: str, *codenames: str):
    """Cria User autenticado e atribui capabilities via PermissaoFuncional groups."""
    user = UsuarioFactory(
        username=username,
        email=f"{username}@example.com",
        password="testpass123",
        cpf=_next_cpf(),
    )
    if codenames:
        # Atribui capabilities via grupo dedicado (consistent com pattern atual)
        group = GroupFactory(name=f"test-group-{username}")
        user.groups.add(group)
        for code in codenames:
            perm = PermissaoFuncional.objects.filter(codename=code).first()
            assert perm is not None, f"PermissaoFuncional '{code}' não está no seed"
            perm.groups.add(group)
    return user


def _request_for(user) -> object:
    """Build a DRF Request com user setado (mesmo pattern de outras suites)."""
    factory = APIRequestFactory()
    http_req = factory.get("/api/test/")
    http_req.user = user
    return http_req


# ============================================================================
# A. Matrix integrity (sem DB)
# ============================================================================


@pytest.mark.django_db(transaction=False)
class TestMatrixIntegrity:
    def test_every_policy_class_has_matrix_entry(self):
        """Toda subclass de _PolicyPermission referencia uma key existente."""
        for cls in _all_policy_classes():
            assert cls.policy in ACCESS_POLICIES, (
                f"{cls.__name__}.policy={cls.policy!r} não existe em ACCESS_POLICIES — "
                f"adicione a key na matriz ou remova a class"
            )

    def test_every_matrix_key_has_policy_class(self):
        """Sem keys órfãs: toda key da matriz tem uma classe Can*."""
        keys_with_classes = {cls.policy for cls in _all_policy_classes()}
        orphans = set(ACCESS_POLICIES.keys()) - keys_with_classes
        assert not orphans, f"Keys órfãs em ACCESS_POLICIES (sem classe Can*): {sorted(orphans)}"

    def test_no_matrix_entry_is_empty(self):
        """frozenset() vazio nunca dá acesso → sintoma de bug.

        Exceção: keys em `COMPOSITE_POLICY_KEYS` carregam frozenset() vazio
        como sentinela porque sua semântica é composite Setor × Função (não
        cabe em OR de capabilities). A lógica vive em helpers dedicados
        despachados por `user_has_policy`.
        """
        from apps.core.rbac.policies import COMPOSITE_POLICY_KEYS

        empty = [k for k, caps in ACCESS_POLICIES.items() if not caps and k not in COMPOSITE_POLICY_KEYS]
        assert not empty, f"Policies com capabilities vazias (não-composite): {empty}"

    def test_matrix_values_are_frozensets(self):
        """Defensivo: impede dict drift para set/list que quebrariam imutabilidade."""
        for k, v in ACCESS_POLICIES.items():
            assert isinstance(v, frozenset), f"ACCESS_POLICIES[{k!r}] deve ser frozenset, é {type(v).__name__}"


# ============================================================================
# B. Naming convention (sem DB)
# ============================================================================


@pytest.mark.django_db(transaction=False)
class TestNamingConvention:
    @pytest.mark.parametrize("policy_key", list(ACCESS_POLICIES.keys()))
    def test_policy_keys_use_canonical_verbs(self, policy_key: str):
        """Cada key começa com verbo do vocabulário canônico (access/use/import/manage/view)."""
        assert CANONICAL_VERB_PREFIX.match(policy_key), (
            f"Key {policy_key!r} não segue convenção <verb>_<resource> snake_case "
            f"(verbos: access|use|import|manage|view)"
        )

    @pytest.mark.parametrize("policy_cls", _all_policy_classes(), ids=lambda c: c.__name__)
    def test_class_names_match_policy_keys(self, policy_cls: type[_PolicyPermission]):
        """`access_audit_logs` → `CanAccessAuditLogs`. 1 nome, 3 derivações mecânicas."""
        expected = "Can" + _camelize(policy_cls.policy)
        assert (
            policy_cls.__name__ == expected
        ), f"Class {policy_cls.__name__} deveria ser {expected} (derivado de policy={policy_cls.policy!r})"

    @pytest.mark.parametrize("policy_key", list(ACCESS_POLICIES.keys()))
    def test_no_policy_suffix_in_keys(self, policy_key: str):
        """Decisão stakeholder: keys públicas não usam sufixo `_policy` (linguagem de produto)."""
        assert not policy_key.endswith("_policy"), f"Key {policy_key!r} usa sufixo `_policy` proibido — remover"


# ============================================================================
# C. Capabilities reais (com DB)
# ============================================================================


class TestCapabilitiesAreSeeded:
    """Valida que cada capability na matriz existe na seed do PermissaoFuncional."""

    @pytest.fixture(autouse=True)
    def _run_seed(self, db):
        from django.core.management import call_command

        call_command("seed_rbac")

    def test_all_policy_capabilities_exist_in_seed(self):
        """Detecta typo / rename de capability no seed."""
        all_caps: set[str] = set()
        for caps in ACCESS_POLICIES.values():
            all_caps.update(caps)
        existing = set(PermissaoFuncional.objects.filter(codename__in=all_caps).values_list("codename", flat=True))
        missing = all_caps - existing
        assert not missing, f"Capabilities referenciadas em ACCESS_POLICIES NÃO existem no seed: {sorted(missing)}"

    def test_no_role_names_in_matrix(self):
        """ACCESS_POLICIES guarda apenas capabilities — nunca nome de role/grupo."""
        leaked: list[tuple[str, str]] = []
        for policy_key, caps in ACCESS_POLICIES.items():
            for cap in caps:
                if cap in ROLE_NAMES:
                    leaked.append((policy_key, cap))
        assert not leaked, (
            f"Roles vazaram para a matriz (anti-pattern): {leaked}. " f"ACCESS_POLICIES guarda APENAS capabilities."
        )


# ============================================================================
# D. Smoke por policy (com DB, parametrize)
# ============================================================================


def _policy_classes_with_caps() -> Iterable[tuple[type[_PolicyPermission], frozenset[str]]]:
    """Yield (class, capabilities) — usado em parametrize com expand."""
    for cls in _all_policy_classes():
        yield cls, ACCESS_POLICIES[cls.policy]


def _policy_id(item):
    cls, _ = item
    return cls.__name__


@pytest.fixture
def seeded_db(db):
    from django.core.management import call_command

    call_command("seed_rbac")


class TestPolicySmoke:
    @pytest.mark.parametrize("policy_cls", _all_policy_classes(), ids=lambda c: c.__name__)
    def test_blocks_anonymous(self, policy_cls):
        """Anonymous → False (nem chega a consultar caps)."""
        req = _request_for(AnonymousUser())
        assert policy_cls().has_permission(req, view=object()) is False

    @pytest.mark.parametrize("policy_cls", _all_policy_classes(), ids=lambda c: c.__name__)
    def test_allows_superuser(self, policy_cls, seeded_db):
        """Superuser bypass (mesma semântica de HasPerm)."""
        super_user = UsuarioFactory(superuser=True)
        req = _request_for(super_user)
        assert policy_cls().has_permission(req, view=object()) is True

    @pytest.mark.parametrize("policy_cls", _all_policy_classes(), ids=lambda c: c.__name__)
    def test_blocks_user_with_no_caps(self, policy_cls, seeded_db):
        """User autenticado sem capability nenhuma → False."""
        user = _make_user("noperms_user")
        req = _request_for(user)
        assert policy_cls().has_permission(req, view=object()) is False

    @pytest.mark.parametrize(
        "policy_with_caps",
        list(_policy_classes_with_caps()),
        ids=_policy_id,
    )
    def test_allows_user_with_any_required_cap(self, policy_with_caps, seeded_db):
        """Para cada cap em ACCESS_POLICIES[policy], user com SÓ essa cap → True (OR semantics)."""
        policy_cls, caps = policy_with_caps
        for idx, cap in enumerate(sorted(caps)):
            user = _make_user(f"perm_user_{policy_cls.__name__}_{idx}", cap)
            req = _request_for(user)
            assert (
                policy_cls().has_permission(req, view=object()) is True
            ), f"{policy_cls.__name__} deveria liberar user com cap={cap!r}"


# ============================================================================
# E. Edge cases
# ============================================================================


class TestEdgeCases:
    def test_unknown_policy_key_returns_false(self, db):
        """Subclasse com policy inválida → fail-secure (returns False)."""
        from django.core.management import call_command

        call_command("seed_rbac")

        class _NonExistentPolicy(_PolicyPermission):
            policy = "nonexistent_policy_xyz"

        user = _make_user("test_unknown")
        req = _request_for(user)
        assert _NonExistentPolicy().has_permission(req, view=object()) is False

    def test_empty_policy_attribute_returns_false(self, db):
        """`policy = ""` (default da base class) → False (sem keys = sem caps)."""

        class _EmptyPolicy(_PolicyPermission):
            pass  # herda policy = ""

        user = _make_user("test_empty")
        req = _request_for(user)
        assert _EmptyPolicy().has_permission(req, view=object()) is False

    def test_policies_can_be_composed_with_or(self, db, seeded_db):
        """Composition CanA() | CanB() funciona via DRF OR (monkey-patch ativo)."""
        # Pega 2 classes diferentes da matriz para compor
        classes = _all_policy_classes()
        assert len(classes) >= 2, "Matriz precisa ter ≥2 policies pra testar composition"
        cls_a, cls_b = classes[0], classes[1]

        # User com cap só de cls_a → composition deve passar
        first_cap_a = sorted(ACCESS_POLICIES[cls_a.policy])[0]
        user = _make_user("compose_user_a", first_cap_a)
        req = _request_for(user)
        composed = cls_a() | cls_b()
        assert composed.has_permission(req, view=object()) is True

    def test_module_imports_permissions_to_load_or_patch(self):
        """policies.py deve garantir que monkey-patch DRF OR/AND/NOT está ativo."""
        # Se permissions.py não foi importado em algum momento, OR.__call__ retorna nova OR
        # ao invés de self. Validamos que self é retornado (patch ativo).
        from apps.core.rbac.permissions import HasPerm

        instance_a = HasPerm("manage_admin_registries")
        instance_b = HasPerm("operate_preagenda")
        composed = instance_a | instance_b
        # Após o monkey-patch, composed() retorna composed (não nova instance)
        assert composed() is composed

    def test_all_policy_classes_are_exported_via_module(self):
        """Todas as classes Can* (definidas em policies.py) estão acessíveis via módulo."""
        for cls in _all_policy_classes():
            # Ignora subclasses inner de tests (definidas em outros testes deste arquivo)
            if cls.__module__ != "apps.core.rbac.policies":
                continue
            assert hasattr(
                policies_module, cls.__name__
            ), f"{cls.__name__} não está exportada via apps.core.rbac.policies"


# ============================================================================
# F. Integration light: combinar com IsAuthenticated
# ============================================================================


class TestIntegration:
    def test_works_alongside_isauthenticated(self, db, seeded_db):
        """Padrão idiomático em views: [IsAuthenticated, CanXxx]."""
        classes = _all_policy_classes()
        cls = classes[0]
        first_cap = sorted(ACCESS_POLICIES[cls.policy])[0]
        user = _make_user("auth_combine_user", first_cap)
        req = _request_for(user)
        assert IsAuthenticated().has_permission(req, view=object()) is True
        assert cls().has_permission(req, view=object()) is True

    def test_drf_or_composition_with_isauthenticated_short_circuit(self, db, seeded_db):
        """`IsAuthenticated() & CanXxx()` exige ambos."""
        classes = _all_policy_classes()
        cls = classes[0]
        first_cap = sorted(ACCESS_POLICIES[cls.policy])[0]
        user = _make_user("auth_and_user", first_cap)
        req = _request_for(user)
        composed = drf_permissions.AND(IsAuthenticated(), cls())
        assert composed.has_permission(req, view=object()) is True
