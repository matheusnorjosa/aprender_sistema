"""
AS v2 — DAT Module Serializers

§10 Epic #459: Refactored to delegate to modular serializers.

This module re-exports all serializers from serializers/dat_module/ for backward compatibility.
Original serializers extracted to:
- serializers/dat_module/dat_area.py (DATAreaSerializer, DATAreaOptionSerializer)
- serializers/dat_module/dat_coordenador.py (DATCoordenadorSerializer, etc.)
- serializers/dat_module/dat_acao.py (DATAcaoSerializer, DATAcaoListSerializer)
- serializers/dat_module/dat_compra.py (DATCompraSerializer, DATCompraListSerializer)
- serializers/dat_module/dat_cadastro.py (DATCadastroSerializer, DATCadastroListSerializer)
- serializers/dat_module/dat_formacao.py (DATFormacaoSerializer, etc.)
"""

# §10 Epic #459: Re-export from modular serializers for backward compatibility
from apps.core.serializers.dat_module import (
    DATAcaoListSerializer,
    DATAcaoSerializer,
    DATAreaOptionSerializer,
    DATAreaSerializer,
    DATCadastroListSerializer,
    DATCadastroSerializer,
    DATCompraListSerializer,
    DATCompraSerializer,
    DATCoordenadorListSerializer,
    DATCoordenadorOptionSerializer,
    DATCoordenadorSerializer,
    DATFormacaoCalendarioSerializer,
    DATFormacaoListSerializer,
    DATFormacaoSerializer,
)

__all__ = [
    "DATAreaSerializer",
    "DATAreaOptionSerializer",
    "DATCoordenadorSerializer",
    "DATCoordenadorOptionSerializer",
    "DATCoordenadorListSerializer",
    "DATAcaoSerializer",
    "DATAcaoListSerializer",
    "DATCompraSerializer",
    "DATCompraListSerializer",
    "DATCadastroSerializer",
    "DATCadastroListSerializer",
    "DATFormacaoSerializer",
    "DATFormacaoListSerializer",
    "DATFormacaoCalendarioSerializer",
]
