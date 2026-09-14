"""
resolve_user_by_email: rejeita email duplicado em vez de `.first()`.

`Usuario` usa o `email` do AbstractUser (não-único) — duas contas podem
compartilhar o mesmo e-mail. O fallback `.first()` ligava import/validação à
pessoa ERRADA em silêncio. Mesma disciplina anti-ambiguidade de `resolve_projeto`
(#1613) e `resolve_municipio` (#2003): 2+ candidatos → `None` + WARNING (o
chamador trata como pendência).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false

from __future__ import annotations

import pytest

from apps.core.services.resolvers import resolve_user_by_email
from apps.core.tests.factories import UsuarioFactory


@pytest.mark.django_db
class TestResolveUserByEmailAmbiguity:
    """#1658 — email duplicado não pode ser resolvido no chute."""

    def test_email_duplicado_rejeita(self):
        UsuarioFactory(username="dup_a", cpf="11111111111", email="dup@example.com")
        UsuarioFactory(username="dup_b", cpf="22222222222", email="dup@example.com")

        assert resolve_user_by_email("dup@example.com") is None

    def test_email_unico_resolve(self):
        u = UsuarioFactory(username="uniq", cpf="33333333333", email="uniq@example.com")

        assert resolve_user_by_email("uniq@example.com") == u

    def test_email_inexistente_none(self):
        assert resolve_user_by_email("nao_existe@example.com") is None
