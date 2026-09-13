"""
resolve_municipio: rejeita ambiguidade em vez de escolher `.first()` (#2003).

Município homônimo entre UFs (ex.: "Bonito" em MS/PA/PE/BA) informado SEM UF
no texto não pode ser resolvido no chute — deve devolver `None` para o chamador
tratar como pendência, exatamente como os resolvers irmãos já fazem via
`_pick_unique` (M02-09/#1613). O `.first()` gravava o município ERRADO em
silêncio (dado persistido, indetectável depois) — o furo central do #2003.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false

from __future__ import annotations

import pytest

from apps.core.models import Municipio
from apps.core.services.resolvers import resolve_municipio


@pytest.mark.django_db
class TestResolveMunicipioAmbiguity:
    """#2003 — resolve_municipio deve rejeitar ambiguidade, não chutar."""

    def test_homonimo_sem_uf_rejeita(self):
        """Dois municípios homônimos em UFs distintas, sem UF no texto → None."""
        Municipio.objects.create(nome="Bonito", uf="MS")
        Municipio.objects.create(nome="Bonito", uf="PA")

        assert resolve_municipio("Bonito") is None

    def test_uf_no_texto_desempata(self):
        """Com a UF no texto, o homônimo é resolvido para o município certo."""
        ms = Municipio.objects.create(nome="Bonito", uf="MS")
        Municipio.objects.create(nome="Bonito", uf="PA")

        assert resolve_municipio("Bonito - MS") == ms
        assert resolve_municipio("Bonito/PA").uf == "PA"

    def test_nome_unico_resolve(self):
        """Nome sem homônimo continua resolvendo normalmente."""
        fortaleza = Municipio.objects.create(nome="Fortaleza", uf="CE")

        assert resolve_municipio("Fortaleza") == fortaleza

    def test_inexistente_devolve_none(self):
        """Nome sem correspondência continua devolvendo None."""
        Municipio.objects.create(nome="Fortaleza", uf="CE")

        assert resolve_municipio("Cidade Que Nao Existe") is None
