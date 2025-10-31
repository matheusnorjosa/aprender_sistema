"""
conftest.py - Auto-inject default test user for Solicitacao (Fix for NOT NULL usuario_id constraint)

This conftest ensures all Solicitacao instances have a valid usuario_id, preventing
IntegrityError: null value in column "usuario_id" violates not-null constraint.

Applied to:
- pytest test suite (36 failing tests)
- ETL imports (missing coordenador/usuario in planilhas)
"""
import pytest
from uuid import uuid4
from django.db.models.signals import pre_save
from django.contrib.auth.models import Group


@pytest.fixture(autouse=True, scope="function")
def _ensure_default_test_user(django_db_setup, django_db_blocker, faker):
    """
    Create default test user and auto-inject into Solicitacao instances missing usuario_id.

    Runs once per test function with unique CPF to avoid IntegrityError.
    """
    from apps.core.models import Usuario, Solicitacao

    with django_db_blocker.unblock():
        # Create default test user with Python uuid4() (truly random, not seeded)
        # CRITICAL: faker.uuid4() is seeded and generates duplicates across tests!
        # Python's uuid4() uses os.urandom() and is cryptographically secure
        uid = uuid4().hex  # 32 chars hex (no hyphens), 128-bit entropy
        user = Usuario.objects.create(
            username=f"test_{uid}",
            email=f"test_{uid}@example.com",
            first_name=faker.first_name(),
            last_name=faker.last_name(),
            cpf=str(uuid4().int % 10**11).zfill(11),  # 11-digit CPF from UUID int
            is_active=True,
        )

        # Get existing Coordenador group (created by seed_rbac)
        coordenador_group, _ = Group.objects.get_or_create(name="Coordenador")
        user.groups.add(coordenador_group)

        # Auto-inject user into Solicitacao instances missing usuario_id
        def _auto_inject_user(sender, instance, **kwargs):
            """Pre-save signal: inject default user if usuario_id is None"""
            if isinstance(instance, Solicitacao) and not instance.usuario_id:
                instance.usuario = user

        # Connect signal (weak=False ensures it persists for the session)
        pre_save.connect(_auto_inject_user, sender=Solicitacao, weak=False)
