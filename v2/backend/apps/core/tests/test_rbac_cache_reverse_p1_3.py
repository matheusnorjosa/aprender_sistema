"""
P1-3: invalidação de cache na mudança REVERSA de membership.

`sync_members` usa `group.user_set.set(...)` (relação reversa: instance=Group,
pk_set=user_ids). O handler de `m2m_changed` assumia sempre instance=User
(`instance.id` = user_id) e ignorava `pk_set` → invalidava a chave errada e
deixava a autorização revogada em cache até CACHE_TTL_SECONDS (300s).

Estes testes provam que remover/limpar membros pela relação reversa invalida o
cache de permissões funcionais dos USUÁRIOS afetados.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false

from __future__ import annotations

from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.core.models import PermissaoFuncional
from apps.core.services.rbac_permissions import get_user_functional_permissions
from apps.core.tests.factories import GroupFactory, UsuarioFactory

LOCMEM = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "rbac-p1-3"}}


@override_settings(CACHES=LOCMEM)
class TestReverseMembershipCacheInvalidation(TestCase):
    def setUp(self):
        cache.clear()
        self.user = UsuarioFactory(username="cache_user_p13", cpf="70000000001")
        self.group = GroupFactory(name="GrupoCacheP13")
        self.perm = PermissaoFuncional.objects.create(
            codename="p13.test_cap", label="P13", description="", category="operacao", is_system=False
        )
        self.perm.groups.add(self.group)

    def _prime(self):
        """Adiciona o usuário ao grupo (reverse) e prime o cache com a cap."""
        self.group.user_set.add(self.user)
        self.assertIn("p13.test_cap", get_user_functional_permissions(self.user))

    def test_reverse_remove_invalidates_user_cache(self):
        self._prime()
        self.group.user_set.remove(self.user)  # revogação via reverse
        self.assertNotIn("p13.test_cap", get_user_functional_permissions(self.user))

    def test_reverse_set_invalidates_removed_user_cache(self):
        # sync_members usa group.user_set.set(...).
        self._prime()
        self.group.user_set.set([])
        self.assertNotIn("p13.test_cap", get_user_functional_permissions(self.user))

    def test_reverse_clear_invalidates_members(self):
        self._prime()
        self.group.user_set.clear()  # pk_set=None → snapshot no pre_clear
        self.assertNotIn("p13.test_cap", get_user_functional_permissions(self.user))

    def test_forward_change_still_invalidates(self):
        # Regressão: forward (user.groups.*) continua invalidando.
        self.user.groups.add(self.group)
        self.assertIn("p13.test_cap", get_user_functional_permissions(self.user))
        self.user.groups.remove(self.group)
        self.assertNotIn("p13.test_cap", get_user_functional_permissions(self.user))
