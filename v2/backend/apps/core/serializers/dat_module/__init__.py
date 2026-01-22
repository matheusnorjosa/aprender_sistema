"""
DAT Module Serializers - §10 Epic #459

Re-exports all DAT serializers for backward compatibility.
Original monolithic file split into domain-specific modules.
"""

from apps.core.serializers.dat_module.dat_acao import (
    DATAcaoListSerializer,
    DATAcaoSerializer,
)
from apps.core.serializers.dat_module.dat_area import (
    DATAreaOptionSerializer,
    DATAreaSerializer,
)
from apps.core.serializers.dat_module.dat_cadastro import (
    DATCadastroListSerializer,
    DATCadastroSerializer,
)
from apps.core.serializers.dat_module.dat_compra import (
    DATCompraListSerializer,
    DATCompraSerializer,
)
from apps.core.serializers.dat_module.dat_coordenador import (
    DATCoordenadorListSerializer,
    DATCoordenadorOptionSerializer,
    DATCoordenadorSerializer,
)
from apps.core.serializers.dat_module.dat_formacao import (
    DATFormacaoCalendarioSerializer,
    DATFormacaoListSerializer,
    DATFormacaoSerializer,
)

__all__ = [
    # DATArea
    "DATAreaSerializer",
    "DATAreaOptionSerializer",
    # DATCoordenador
    "DATCoordenadorSerializer",
    "DATCoordenadorOptionSerializer",
    "DATCoordenadorListSerializer",
    # DATAcao
    "DATAcaoSerializer",
    "DATAcaoListSerializer",
    # DATCompra
    "DATCompraSerializer",
    "DATCompraListSerializer",
    # DATCadastro
    "DATCadastroSerializer",
    "DATCadastroListSerializer",
    # DATFormacao
    "DATFormacaoSerializer",
    "DATFormacaoListSerializer",
    "DATFormacaoCalendarioSerializer",
]
