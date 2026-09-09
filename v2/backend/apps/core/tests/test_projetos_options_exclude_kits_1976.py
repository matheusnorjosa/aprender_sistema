"""
#1976: /api/options/projetos/ deve poder filtrar por NÍVEL (família vs variante-por-série).

O catálogo tem dois níveis (relay sheets.banco): família (`A COR DA GENTE`) — para onde
evento e plano apontam — e variante-por-série (`A COR DA GENTE 1..9`) — para onde DAT/compra
apontam. O dropdown de solicitação já mostra só famílias (ProjetoLookup exclui numerados);
o de plano de formação usava este endpoint sem filtro e mostrava os dois níveis misturados
(a "duplicação" percebida). Este endpoint ganha `?exclude_kits=true` (mesma heurística do
ProjetoLookup: exclui nomes terminados em número), default false (não afeta Compras).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from rest_framework.test import APIClient

import pytest

from apps.core.tests.factories import ProjetoFactory, UsuarioFactory


@pytest.fixture
def regular_user(db):
    return UsuarioFactory(username="regular_user_1976", email="user1976@example.com", password="testpass123")


@pytest.fixture
def projetos_dois_niveis(db):
    """Família (sem número) + variantes por série (terminadas em número)."""
    familia = ProjetoFactory(nome="A COR DA GENTE", fluxo="NAO_SUPER", ativo=True, is_test=False)
    var1 = ProjetoFactory(nome="A COR DA GENTE 1", fluxo="NAO_SUPER", ativo=True, is_test=False)
    var2 = ProjetoFactory(nome="A COR DA GENTE 2", fluxo="NAO_SUPER", ativo=True, is_test=False)
    return {"familia": familia, "variantes": [var1, var2]}


@pytest.mark.django_db
class TestProjetosOptionsExcludeKits:
    """#1976: filtro de nível no /api/options/projetos/."""

    def test_exclude_kits_true_hides_numbered_variants(self, regular_user, projetos_dois_niveis):
        """Com ?exclude_kits=true, só famílias (nomes sem número final) voltam."""
        client = APIClient()
        client.force_authenticate(user=regular_user)

        response = client.get("/api/options/projetos/?exclude_kits=true")

        assert response.status_code == 200
        nomes = [p["nome"] for p in response.json()]
        assert "A COR DA GENTE" in nomes
        assert "A COR DA GENTE 1" not in nomes
        assert "A COR DA GENTE 2" not in nomes

    def test_default_includes_variants(self, regular_user, projetos_dois_niveis):
        """Sem o param (default), família E variantes voltam (comportamento atual — Compras)."""
        client = APIClient()
        client.force_authenticate(user=regular_user)

        response = client.get("/api/options/projetos/")

        assert response.status_code == 200
        nomes = [p["nome"] for p in response.json()]
        assert "A COR DA GENTE" in nomes
        assert "A COR DA GENTE 1" in nomes
        assert "A COR DA GENTE 2" in nomes

    def test_exclude_kits_false_explicit_includes_variants(self, regular_user, projetos_dois_niveis):
        """?exclude_kits=false explícito = mesmo que default."""
        client = APIClient()
        client.force_authenticate(user=regular_user)

        response = client.get("/api/options/projetos/?exclude_kits=false")

        assert response.status_code == 200
        nomes = [p["nome"] for p in response.json()]
        assert "A COR DA GENTE 1" in nomes
