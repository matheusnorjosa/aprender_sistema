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
def ensure_rbac_seed(db):
    """
    Garante o seed de RBAC (grupos + PermissaoFuncional + ligacoes group x capability)
    presente em CADA teste, mesmo sob pytest-xdist. #1402.

    Por que: os testes `@pytest.mark.django_db(transaction=True)` usam semantica
    TransactionTestCase e fazem TRUNCATE/flush do DB no teardown, apagando o seed de
    RBAC (vindo das migrations RunPython e do fixture de sessao). O runner nativo do
    Django reordena TransactionTestCase para o FIM, entao serial nunca perde o seed no
    meio. Mas pytest-xdist NAO reordena: sob `-n auto`, um teste-truncate roda no meio
    do worker e TODOS os testes seguintes naquele worker perdem o seed -> a resolucao de
    capability (`PermissaoFuncional.objects.filter(groups__user__id=...)`) retorna vazio
    -> 403 PERMISSION_DENIED em cascata (centenas de falhas, nao-deterministicas).

    Guarda de 1 query: no-op quando o seed ja existe (caso comum -> sem overhead). So
    re-semeia (idempotente) quando o vinculo group x capability sumiu (pos-truncate).

    `ensure_base_groups()` restaura tambem os 18 grupos base (setor + funcao) que o
    truncate apaga. Necessario sob `pytest --no-migrations`, onde os grupos vem do
    fixture de sessao (nao das migrations RunPython). #1404.
    """
    from apps.core.models import PermissaoFuncional
    from apps.core.services.functional_permissions_seed import (
        ensure_base_groups,
        seed_functional_permissions,
    )

    if not PermissaoFuncional.objects.filter(groups__isnull=False).exists():
        ensure_base_groups()
        seed_functional_permissions(assign_default_groups=True)
        # O groups.set do seed dispara m2m_changed e popula o buffer de auditoria de
        # capability; essas mudancas sao infraestrutura de teste (nao operacoes
        # auditaveis) -> limpar para nao contaminar contagens de AuditLog.
        from apps.core.signals import _PENDING_GROUP_CAP_DELTAS

        _PENDING_GROUP_CAP_DELTAS.clear()


@pytest.fixture(autouse=True, scope="function")
def default_test_user(db, ensure_rbac_seed):
    """
    Create unique test user for each test function.

    - Unique CPF/username via uuid4 (xdist-safe)
    - Added to Coordenador group
    - autouse=True ensures DB is available for all tests
    - depends on ensure_rbac_seed so o grupo/seed RBAC exista antes do groups.add

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
