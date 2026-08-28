"""
M17 (list-serializer-como-fonte-de-detalhe) — DATCompra (#1636/M15-09) e DATCoordenador (#1654/M18-05).

O modal de edição é semeado a partir da LINHA da lista. Se a List serializer omite um campo que o
form edita, o round-trip quebra: `data_admissao` é zerada a cada edição (handleSave coage null) e os
FK ids da compra vazam entre registros (o form retém o valor anterior). O fix é expor na List os
campos que o modal precisa. Este teste fixa o contrato.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false

from __future__ import annotations

from apps.core.serializers.dat_module.dat_compra import DATCompraListSerializer
from apps.core.serializers.dat_module.dat_coordenador import DATCoordenadorListSerializer


def test_dat_coordenador_list_exposes_data_admissao() -> None:
    # #1654/M18-05: sem data_admissao na List, o modal (semeado da linha) manda null → ZERA a admissão.
    assert "data_admissao" in DATCoordenadorListSerializer.Meta.fields


def test_dat_compra_list_exposes_fk_ids() -> None:
    # #1636/M15-09: sem os FK ids na List, editar A depois B retém os FKs de A → contaminação.
    fields = DATCompraListSerializer.Meta.fields
    for f in ("municipio", "projeto", "produto"):
        assert f in fields, f
