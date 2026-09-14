"""
usuarios_import._assign_groups: só atribui grupos da allowlist (#1658, defesa-em-profundidade).

A concessão de grupos por import já é superuser-only (#1610/M03-01), mas não filtrava
QUAIS grupos — um nome fora do conjunto legítimo (setores+funções = ALLOWED_USER_GROUPS)
podia ser atribuído via CSV, incl. grupos admin/reservados (typo ou blast-radius de
credencial comprometida). Espelha o `export_contract_importer` (que já filtra por
ALLOWED_USER_GROUPS). Grupos fora da allowlist são recusados (e logados).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false

from __future__ import annotations

from django.contrib.auth.models import Group

import pytest

from apps.core.services.usuarios_import import _assign_groups
from apps.core.tests.factories import UsuarioFactory


@pytest.mark.django_db
class TestUsuariosImportGroupAllowlist:
    """Só grupos de setor/função (ALLOWED_USER_GROUPS) entram por import."""

    def test_grupo_fora_da_allowlist_recusado(self):
        superuser = UsuarioFactory(superuser=True)
        alvo = UsuarioFactory(username="alvo_grp", cpf="77777777777")
        formador, _ = Group.objects.get_or_create(name="Formador")  # Função — allowlist
        admin, _ = Group.objects.get_or_create(name="AdminSistema")  # fora da allowlist

        _assign_groups(alvo, [formador, admin], actor=superuser)

        nomes = set(alvo.groups.values_list("name", flat=True))
        assert "Formador" in nomes
        assert "AdminSistema" not in nomes

    def test_grupo_legitimo_atribuido(self):
        superuser = UsuarioFactory(superuser=True)
        alvo = UsuarioFactory(username="alvo_grp2", cpf="66666666666")
        coord, _ = Group.objects.get_or_create(name="Coordenador")  # Função — allowlist

        _assign_groups(alvo, [coord], actor=superuser)

        assert alvo.groups.filter(name="Coordenador").exists()
