# MCP toolsets package

from .core_toolset import CoreModelToolset
from .solicitacao_toolset import SolicitacaoToolset

# Create alias for FormadorToolset (reference to CoreModelToolset)
FormadorToolset = CoreModelToolset

__all__ = [
    "CoreModelToolset",
    "SolicitacaoToolset",
    "FormadorToolset",
]
