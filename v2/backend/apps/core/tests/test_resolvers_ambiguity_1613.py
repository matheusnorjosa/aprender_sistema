"""Testes de rejeição de ambiguidade nos resolvers (issue #1613 / achado M02-09).

Antes do fix, `resolve_projeto`/`resolve_tipo_evento` usavam `.first()` (ou o
ramo `MultipleObjectsReturned → .first()`) e escolhiam um alvo no chute quando
2+ registros casavam — gravando o alvo errado em silêncio. Agora rejeitam:
retornam ``None`` (+ WARNING com candidatos), para o chamador tratar como
pendência em vez de resolver no chute.

Nota: `Projeto.nome` e `TipoEvento.nome` são `unique` (case-sensitive no
PostgreSQL), então a ambiguidade real surge por **variante de caixa** — dois
registros distintos ("X" e "x") que um `__iexact` casa ao mesmo tempo.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false, reportAttributeAccessIssue=false

import pytest

from apps.core.models import TipoEvento
from apps.core.services.resolvers import resolve_projeto, resolve_tipo_evento
from apps.core.tests.factories import ProjetoFactory


@pytest.mark.django_db
class TestResolveProjetoAmbiguity:
    """`resolve_projeto` rejeita ambiguidade em vez de `.first()`."""

    def test_case_variant_duplicates_return_none(self) -> None:
        # Regressão M02-09/#1613: "Projeto Duplo" e "projeto duplo" são 2 linhas
        # distintas; `nome__iexact` casa as duas → não escolher no chute → None.
        ProjetoFactory(nome="Projeto Duplo")
        ProjetoFactory(nome="projeto duplo")
        assert resolve_projeto("Projeto Duplo") is None

    def test_single_match_still_resolves(self) -> None:
        p = ProjetoFactory(nome="Novo Lendo")
        assert resolve_projeto("Novo Lendo") == p

    def test_accented_name_resolves_symmetric_norm(self) -> None:
        # Normalização SIMÉTRICA (os dois lados): input sem acento casa nome acentuado.
        # É deste caminho que o import DAT (#1613) passou a se beneficiar.
        p = ProjetoFactory(nome="Educação")
        assert resolve_projeto("educacao") == p


@pytest.mark.django_db
class TestResolveTipoEventoAmbiguity:
    """`resolve_tipo_evento` rejeita ambiguidade em vez de `.first()`."""

    def test_case_variant_duplicates_return_none(self) -> None:
        # `.objects.create` direto para escapar do django_get_or_create da factory.
        TipoEvento.objects.create(nome="Reunião")
        TipoEvento.objects.create(nome="reunião")  # distinto por caixa; iexact casa os 2
        assert resolve_tipo_evento("Reunião") is None

    def test_single_match_still_resolves(self) -> None:
        t = TipoEvento.objects.create(nome="Formação DAT")
        assert resolve_tipo_evento("formação dat") == t
