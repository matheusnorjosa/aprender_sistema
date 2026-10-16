"""
Campos de serializer reaproveitados entre endpoints.

Type-checked with Pyright (strict mode).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportUntypedBaseClass=false

from __future__ import annotations

from typing import Any

from rest_framework import serializers


class ListaComTeto(serializers.ListField):  # type: ignore[misc]
    """`ListField` que recusa pelo tamanho ANTES de validar os itens.

    O `ListField(max_length=)` do DRF valida todos os itens e só depois aplica o teto, juntando
    um erro por item inválido: uma lista de centenas de milhares de itens prendia o worker por
    segundos e devolvia megabytes de erro (revisão do F2, scan de segurança de 16/10/2026).
    Aqui a lista acima do teto dá um erro só, sem tocar nos itens.
    """

    def to_internal_value(self, data: Any) -> Any:
        if self.max_length is not None and isinstance(data, list | tuple) and len(data) > self.max_length:
            self.fail("max_length", max_length=self.max_length)
        return super().to_internal_value(data)
