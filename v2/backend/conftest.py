"""
conftest.py — Test fixtures for Aprender Sistema v2.

Provides a per-test user that auto-injects into Solicitacao instances
missing usuario_id. Uses pre_save signal scoped to test lifetime
(connected on setup, disconnected on teardown).

Refactored from #847: signal now properly disconnects after each test.
"""

from uuid import uuid4

from django.contrib.auth.models import Group
from django.db.models.signals import pre_save

import pytest


@pytest.fixture(autouse=True, scope="function")
def default_test_user(db):
    """
    Create unique test user and auto-inject into Solicitacao.

    - Connected via pre_save signal (scoped to this test only)
    - Disconnected in teardown (no leaking between tests)
    - Unique CPF/username via uuid4 (xdist-safe)

    Available as explicit fixture: `def test_x(default_test_user):`
    """
    from apps.core.models import Solicitacao, Usuario

    uid = uuid4().hex
    user = Usuario.objects.create(
        username=f"test_{uid}",
        email=f"test_{uid}@example.com",
        first_name="Test",
        last_name="User",
        cpf=str(uuid4().int % 10**11).zfill(11),
        is_active=True,
    )

    coordenador_group, _ = Group.objects.get_or_create(name="Coordenador")
    user.groups.add(coordenador_group)

    # Scoped signal: inject user into Solicitacao missing usuario_id
    def _auto_inject_user(sender, instance, **kwargs):
        if isinstance(instance, Solicitacao) and not instance.usuario_id:
            instance.usuario = user

    pre_save.connect(_auto_inject_user, sender=Solicitacao)

    yield user

    # Teardown: disconnect signal to prevent leaking
    pre_save.disconnect(_auto_inject_user, sender=Solicitacao)
