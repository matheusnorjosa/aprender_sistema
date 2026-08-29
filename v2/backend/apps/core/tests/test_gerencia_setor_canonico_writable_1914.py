"""#1914 (BE) — `setor_canonico` gravavel no GerenciaSerializer (entrada-direta/conferencia).

`Gerencia.setor_canonico` (vocabulario setor-de-produto do de-para v15, RELAY 28) so entrava
por IMPORT e GATEIA navegacao (`usePermissions.ts`). Fora do write-serializer, nao havia como
conferir/corrigir pela UI — se o import errasse, o usuario perdia telas sem conserto. Este teste
fixa o contrato backend: `setor_canonico` presente e NAO read-only no GerenciaSerializer, para a
tela de conferencia poder ler e gravar. (A tela em si e frontend / Onda H.)
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false

from __future__ import annotations

from apps.core.serializers.organizacao import GerenciaSerializer


def test_setor_canonico_is_writable_in_gerencia_serializer() -> None:
    fields = GerenciaSerializer.Meta.fields
    read_only = getattr(GerenciaSerializer.Meta, "read_only_fields", [])
    assert "setor_canonico" in fields, "'setor_canonico' ausente de GerenciaSerializer.Meta.fields"
    assert "setor_canonico" not in read_only, "'setor_canonico' esta em read_only_fields"
