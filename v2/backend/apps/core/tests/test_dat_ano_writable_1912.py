"""#1912 — `ano` gravavel nos write-serializers DAT (entrada-direta).

`ano` existe no model (nullable, SEM default) e entra na UniqueConstraint com
`nulls_distinct=False`. Sem `ano` no write-serializer, um create pela UI grava `ano=NULL`;
um 2o create tambem NULL colide na constraint (400). Expor `ano` (gravavel) deixa o usuario
CLASSIFICAR (o NULL e o bucket pendente por design; segue valido). Este teste fixa o
contrato: `ano` presente e NAO read-only nos write-serializers de Registro/Cadastro/Acao.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false

from __future__ import annotations

from apps.core.serializers.dat_module.dat_acao import DATAcaoSerializer
from apps.core.serializers.dat_module.dat_cadastro import DATCadastroSerializer
from apps.core.serializers.dat_registro import (
    DATRegistroCreateSerializer,
    DATRegistroUpdateSerializer,
)

# Write-serializers que semeiam o form de create/edit — precisam aceitar `ano`.
WRITE_SERIALIZERS = [
    DATRegistroCreateSerializer,
    DATRegistroUpdateSerializer,
    DATCadastroSerializer,
    DATAcaoSerializer,
]


def test_ano_is_writable_in_all_dat_write_serializers() -> None:
    for cls in WRITE_SERIALIZERS:
        fields = cls.Meta.fields
        read_only = getattr(cls.Meta, "read_only_fields", [])
        assert "ano" in fields, f"{cls.__name__}: 'ano' ausente de Meta.fields"
        assert "ano" not in read_only, f"{cls.__name__}: 'ano' em read_only_fields"
