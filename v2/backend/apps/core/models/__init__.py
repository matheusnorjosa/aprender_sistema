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
    ├── organizacao.py       # Municipio, Gerencia, EquipeGerencia, ProjetoGeral, Projeto, TipoEvento, Produto
    ├── solicitacao.py       # Solicitacao, Participation
    ├── agenda.py            # AvailabilityBlock
    ├── compra.py            # Compra
    ├── workflow.py          # Deslocamento, AcaoControle, AcaoDAT
    ├── config.py            # Config
    ├── auditoria.py         # AuditLog
    ├── integracao.py        # GoogleOAuthCredential
    ├── dat_registro.py      # DATRegistro
    ├── dat_coordenador.py   # DATCoordenador, DATArea
    ├── dat_acao.py          # DATAcao
    ├── dat_compra.py        # DATCompra
    ├── dat_cadastro.py      # DATCadastro
    ├── dat_formacao.py      # DATFormacao
    ├── plano_formacoes.py   # PlanoFormacoes
    ├── formacao.py          # Formacao
    ├── acompanhamento.py    # Acompanhamento
    └── prova.py             # Prova

Type-checked with Pyright (strict mode).
"""

from __future__ import annotations

from apps.core.models.agenda import AvailabilityBlock
from apps.core.models.auditoria import AuditLog
from apps.core.models.compra import Compra
from apps.core.models.config import Config
from apps.core.models.dat_acao import DATAcao
from apps.core.models.dat_cadastro import DATCadastro
from apps.core.models.dat_compra import DATCompra
from apps.core.models.dat_coordenador import DATArea, DATCoordenador
from apps.core.models.dat_formacao import DATFormacao
from apps.core.models.dat_registro import DATRegistro
from apps.core.models.plano_formacoes import PlanoFormacoes
from apps.core.models.formacao import Formacao
from apps.core.models.acompanhamento import Acompanhamento
from apps.core.models.prova import Prova
from apps.core.models.integracao import GoogleOAuthCredential
from apps.core.models.organizacao import (
    EquipeGerencia,
    Gerencia,
    Municipio,
    Produto,
    Projeto,
    ProjetoGeral,
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
    "ProjetoGeral",
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
    # DAT Registros
    "DATRegistro",
    # DAT Module
    "DATArea",
    "DATCoordenador",
    "DATAcao",
    "DATCompra",
    "DATCadastro",
    "DATFormacao",
    # Plano Formacoes (novo modelo estruturado)
    "PlanoFormacoes",
    "Formacao",
    "Acompanhamento",
    "Prova",
    # Config
    "Config",
    # Auditoria
    "AuditLog",
    # Integracao
    "GoogleOAuthCredential",
]
