"""
conftest.py — Test fixtures for Aprender Sistema v2.

Provides a per-test default user with Coordenador group.
Available as explicit fixture: `def test_x(default_test_user):`

History:
- PR #1062: Added signal auto-inject (scoped per test)
- PR #1063: Removed signal — all Solicitacao.objects.create now pass
  usuario= explicitly. Signal was no longer needed.
"""

from uuid import uuid4

from django.contrib.auth.models import Group

import pytest


@pytest.fixture(autouse=True, scope="function")
def default_test_user(db):
    """
    Create unique test user for each test function.

    - Unique CPF/username via uuid4 (xdist-safe)
    - Added to Coordenador group
    - autouse=True ensures DB is available for all tests

    Available as explicit fixture: `def test_x(default_test_user):`
    """
    from apps.core.models import Usuario

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

    yield user
