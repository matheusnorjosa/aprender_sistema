"""
AS v2 — Core Models (Modular)

Re-exporta todos os models para manter retrocompatibilidade:
    from apps.core.models import Usuario, Solicitacao, ...

Imports diretos tambem funcionam:
    from apps.core.models.usuario import Usuario

Estrutura:
    models/
    ├── __init__.py          # Este arquivo (re-exports)
    ├── usuario.py           # Usuario
    ├── organizacao.py       # Municipio, Gerencia, EquipeGerencia, Projeto, TipoEvento, Produto
    ├── solicitacao.py       # Solicitacao, Participation
    ├── agenda.py            # AvailabilityBlock
    ├── compra.py            # Compra
    ├── workflow.py          # Deslocamento, AcaoControle, AcaoDAT
    ├── config.py            # Config
    ├── auditoria.py         # AuditLog
    └── integracao.py        # GoogleOAuthCredential

Type-checked with Pyright (strict mode).
"""
from apps.core.models.agenda import AvailabilityBlock
from apps.core.models.auditoria import AuditLog
from apps.core.models.compra import Compra
from apps.core.models.config import Config
from apps.core.models.integracao import GoogleOAuthCredential
from apps.core.models.organizacao import (
    EquipeGerencia,
    Gerencia,
    Municipio,
    Produto,
    Projeto,
    TipoEvento,
)
from apps.core.models.solicitacao import Participation, Solicitacao
from apps.core.models.usuario import Usuario
from apps.core.models.workflow import AcaoControle, AcaoDAT, Deslocamento

__all__ = [
    # Usuario
    "Usuario",
    # Organizacao
    "Municipio",
    "Gerencia",
    "EquipeGerencia",
    "Projeto",
    "TipoEvento",
    "Produto",
    # Solicitacao
    "Solicitacao",
    "Participation",
    # Agenda
    "AvailabilityBlock",
    # Compra
    "Compra",
    # Workflow
    "Deslocamento",
    "AcaoControle",
    "AcaoDAT",
    # Config
    "Config",
    # Auditoria
    "AuditLog",
    # Integracao
    "GoogleOAuthCredential",
]
