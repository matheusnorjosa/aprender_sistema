"""
Testes para command seed_rbac (idempotência).

Valida que os grupos e permissões são criados corretamente
e que executar múltiplas vezes não causa efeitos colaterais.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false

from __future__ import annotations
import pytest
from django.core.management import call_command
from django.contrib.auth.models import Group


pytestmark = pytest.mark.django_db


def test_seed_rbac_creates_groups():
    """
    Testa que seed_rbac cria todos os grupos esperados.
    """
    call_command("seed_rbac")

    expected_groups = [
        "Superintendência",
        "Coordenador",
        "Formador",
        "Controle",
        "DAT",
        "Gerência",
    ]

    for group_name in expected_groups:
        assert Group.objects.filter(name=group_name).exists(), \
            f"Grupo {group_name} não foi criado"


def test_seed_rbac_idempotent():
    """
    Testa que seed_rbac é idempotente.

    Executar múltiplas vezes não deve alterar as permissões
    nem criar grupos duplicados.
    """
    # Primeira execução
    call_command("seed_rbac")
    g = Group.objects.get(name="Controle")
    perms1 = set(g.permissions.values_list("codename", flat=True))

    # Segunda execução (idempotente)
    call_command("seed_rbac")
    g2 = Group.objects.get(name="Controle")
    perms2 = set(g2.permissions.values_list("codename", flat=True))

    assert perms1 == perms2, "Permissões mudaram após segunda execução"

    # Verificar que não há grupos duplicados
    assert Group.objects.filter(name="Controle").count() == 1


def test_seed_rbac_assigns_permissions():
    """
    Testa que seed_rbac atribui permissões aos grupos.

    Verifica que pelo menos algumas permissões foram atribuídas.
    """
    call_command("seed_rbac")

    # Verificar que Superintendência tem permissões
    super_group = Group.objects.get(name="Superintendência")
    assert super_group.permissions.count() > 0, \
        "Superintendência deveria ter permissões"

    # Verificar que Coordenador tem permissões
    coord_group = Group.objects.get(name="Coordenador")
    assert coord_group.permissions.count() > 0, \
        "Coordenador deveria ter permissões"
