"""#1643 — resolve_user_by_name: escada determinística com uniqueness (fim do match único errado).

Antes, as Tentativas 2/3 usavam `icontains` + `.first()` SEM checar unicidade: quando o nome
era substring de 2+ usuários, devolvia UM em silêncio (o alvo errado). Agora cada degrau exige
candidato ÚNICO (reusa `_pick_unique` do #1613); ambíguo → None (vai pra fila), nunca chute.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false

from __future__ import annotations

import pytest

from apps.core.services.resolvers import resolve_user_by_name
from apps.core.tests.factories import UsuarioFactory


@pytest.mark.django_db
class TestResolveUserByName1643:
    def test_ambiguous_substring_returns_none(self):
        """Dois 'Maria Souza X', nenhum exatamente 'Maria Souza' → ambíguo → None (não chuta)."""
        UsuarioFactory(first_name="Maria", last_name="Souza Lima")
        UsuarioFactory(first_name="Maria", last_name="Souza Santos")
        # Antes: icontains(maria)+icontains(souza).first() devolvia UM (chute errado).
        assert resolve_user_by_name("Maria Souza") is None

    def test_exact_full_name_wins_over_substring_superset(self):
        """Match de nome COMPLETO exato ganha do superset por substring, mesmo com ruído de pk menor."""
        UsuarioFactory(first_name="Maria", last_name="Souza Lima")  # ruído, criado 1º (pk menor)
        alvo = UsuarioFactory(first_name="Maria", last_name="Souza")
        # Antes: caía na Tentativa 2 e .first() podia devolver o ruído (pk menor).
        assert resolve_user_by_name("Maria Souza") == alvo

    def test_unique_token_subset_resolves(self):
        """Nome com nome-do-meio omitido resolve pro único candidato que contém todos os tokens."""
        alvo = UsuarioFactory(first_name="Joao Pedro", last_name="Alencar")
        UsuarioFactory(first_name="Carlos", last_name="Mendes")  # não colide
        assert resolve_user_by_name("Joao Alencar") == alvo

    def test_empty_returns_none(self):
        assert resolve_user_by_name("") is None
