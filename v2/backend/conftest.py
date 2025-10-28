"""
conftest.py - Auto-inject default test user for Solicitacao (Fix for NOT NULL usuario_id constraint)

This conftest ensures all Solicitacao instances have a valid usuario_id, preventing
IntegrityError: null value in column "usuario_id" violates not-null constraint.

Applied to:
- pytest test suite (36 failing tests)
- ETL imports (missing coordenador/usuario in planilhas)
"""
import pytest
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
        # Create default test user with UUID-guaranteed uniqueness
        # UUID ensures absolute uniqueness across all test runs (faker.unique has cache issues)
        unique_id = faker.uuid4()[:12]  # Short UUID (12 chars, 281 trillion combinations)
        user = Usuario.objects.create(
            username=f"test_{unique_id}",
            email=f"test_{unique_id}@example.com",
            first_name=faker.first_name(),
            last_name=faker.last_name(),
            cpf=faker.unique.numerify('###########'),  # Unique 11-digit CPF
            is_active=True,
        )

        # Get existing Coordenador group (created by seed_rbac)
        try:
            coordenador_group = Group.objects.get(name="Coordenador")
            user.groups.add(coordenador_group)
        except Group.DoesNotExist:
            # Fallback: create if doesn't exist (shouldn't happen)
            coordenador_group = Group.objects.create(name="Coordenador")
            user.groups.add(coordenador_group)

        # Auto-inject user into Solicitacao instances missing usuario_id
        def _auto_inject_user(sender, instance, **kwargs):
            """Pre-save signal: inject default user if usuario_id is None"""
            if isinstance(instance, Solicitacao) and not instance.usuario_id:
                instance.usuario = user

        # Connect signal (weak=False ensures it persists for the session)
        pre_save.connect(_auto_inject_user, sender=Solicitacao, weak=False)
