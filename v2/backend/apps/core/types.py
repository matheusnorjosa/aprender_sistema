"""
Type Aliases Centralizados — Aprender Sistema v2

Arquivo centralizado com todos os type aliases do projeto usando TypeAlias (Python 3.10+).

Organização:
1. IDs e Identificadores
2. Status e Estados
3. Códigos de Conflito (RD-01 a RD-08)
4. Google Calendar
5. JSON e Estruturas
6. Handlers e Callbacks

Uso:
    from apps.core.types import UserId, Status, ConflictCode
"""

from __future__ import annotations

from typing import Any, Callable, Literal, TypeAlias

# ==============================================================================
# 1. IDs e Identificadores
# ==============================================================================

UserId: TypeAlias = int
"""ID de usuário (Usuario.id)."""

SolicitacaoId: TypeAlias = int
"""ID de solicitação (Solicitacao.id)."""

ProjetoId: TypeAlias = int
"""ID de projeto (Projeto.id)."""

MunicipioId: TypeAlias = int
"""ID de município (Municipio.id)."""

TipoEventoId: TypeAlias = int
"""ID de tipo de evento (TipoEvento.id)."""

AvailabilityBlockId: TypeAlias = int
"""ID de bloqueio (AvailabilityBlock.id)."""

DeslocamentoId: TypeAlias = int
"""ID de deslocamento (Deslocamento.id)."""

ParticipationId: TypeAlias = int
"""ID de participação (Participation.id)."""

# ==============================================================================
# 2. Status e Estados
# ==============================================================================

Status: TypeAlias = Literal["pendente", "aprovado", "reprovado"]
"""Status de solicitação (Solicitacao.status)."""

Fluxo: TypeAlias = Literal["SUPER", "NAO_SUPER"]
"""Fluxo de aprovação (Projeto.fluxo).

- SUPER: Requer aprovação manual da Superintendência (PA-01 a PA-07)
- NAO_SUPER: Auto-aprovado na criação (PR18)
"""

GCalStatus: TypeAlias = Literal["NONE", "PENDING", "PUBLISHED", "ERROR"]
"""Status de sincronização Google Calendar (Solicitacao.gcal_status)."""

BlockType: TypeAlias = Literal["P", "T"]
"""Tipo de bloqueio de disponibilidade (AvailabilityBlock.tipo).

- P: Parcial (RD-03)
- T: Total (RD-02)
"""

ApprovalStatus: TypeAlias = Literal["pendente", "aprovado", "reprovado"]
"""Status de aprovação (Aprovacao.status)."""

# ==============================================================================
# 3. Códigos de Conflito (RD-01 a RD-08)
# ==============================================================================

ConflictCode: TypeAlias = Literal["X", "T", "P", "D", "M", "E"]
"""Código de conflito de disponibilidade (RD-08).

Códigos:
- X: Conflito geral (overlap)
- T: Bloqueio total (RD-02)
- P: Bloqueio parcial (RD-03)
- D: Deslocamento necessário (RD-04)
- M: Mais de um evento / Capacidade excedida (RD-05)
- E: Evento existente (informativo)
"""

# ==============================================================================
# 4. Google Calendar
# ==============================================================================

EventId: TypeAlias = str
"""ID de evento no Google Calendar (ex: 'asv2-123')."""

CalendarId: TypeAlias = str
"""ID de calendário Google (ex: 'primary' ou 'user@group.calendar.google.com')."""

MeetLink: TypeAlias = str
"""URL do Google Meet (ex: 'https://meet.google.com/abc-defg-hij')."""

GCalClientType: TypeAlias = Literal["fake", "google"]
"""Tipo de cliente Google Calendar (settings.GCAL_CLIENT).

- fake: Cliente in-memory para testes (sem side effects)
- google: Cliente real via Google Calendar API
"""

SendUpdates: TypeAlias = Literal["none", "all", "externalOnly"]
"""Política de envio de notificações Google Calendar (settings.GCAL_SEND_UPDATES).

- none: Não envia emails
- all: Envia para todos os participantes
- externalOnly: Envia apenas para participantes externos ao domínio
"""

# ==============================================================================
# 5. JSON e Estruturas
# ==============================================================================

JsonDict: TypeAlias = dict[str, Any]
"""Dicionário JSON genérico."""

JsonList: TypeAlias = list[JsonDict]
"""Lista de dicionários JSON."""

PayloadHash: TypeAlias = str
"""Hash SHA1 hex (40 chars) de payload GCal para drift detection."""

ExternalHash: TypeAlias = str
"""Hash SHA256 hex (64 chars) para idempotência de ETL e imports."""

# ==============================================================================
# 6. Handlers e Callbacks
# ==============================================================================

ErrorHandler: TypeAlias = Callable[[Exception], None]
"""Callback para tratamento de erros."""

# Generic callbacks (Python 3.11+ compatible)
from typing import TypeVar  # noqa: E402

T = TypeVar("T")

SuccessCallback: TypeAlias = Callable[[Any], None]
"""Callback genérico para sucesso."""

ValidationFunction: TypeAlias = Callable[[Any], bool]
"""Função de validação genérica (retorna True se válido)."""

# ==============================================================================
# 7. Timezone
# ==============================================================================

TimezoneName: TypeAlias = Literal["America/Fortaleza"]
"""Timezone do projeto (RD-06).

IMPORTANTE: Sempre usar timezone-aware datetimes.
- Storage: UTC no banco
- Comparison: America/Fortaleza
"""

# ==============================================================================
# 8. RBAC (Grupos e Permissões)
# ==============================================================================

GroupName: TypeAlias = Literal[
    # Setores (SETOR_GROUPS)
    "Superintendência",
    "Vidas",
    "Fluir",
    "ACerta",
    "Brincando",
    "Sou da Paz",
    "DAT",
    "Controle",
    "Diretoria",
    "Comercial",
    "Relacionamento",
    "Logística Viagens",
    "Logística Galpão",
    # Funções (FUNCAO_GROUPS)
    "Formador",
    "Coordenador",
    "Apoio de Coordenação",
    "Gerente",
    # Legacy — grupo Django ativo, não é mais setor
    "Gerência",
]
"""Grupos de permissão Django (Usuario.groups). Ref: constants.py"""

ActionType: TypeAlias = Literal[
    "APPROVE",
    "REJECT",
    "PREVIEW_GCAL",
    "PUBLISH_GCAL_REQUESTED",
    "PUBLISH_GCAL",
    "RESYNC_GCAL_REQUESTED",
    "CANCEL_GCAL_REQUESTED",
    "CANCEL_GCAL",
]
"""Tipos de ação para auditoria (AuditLog.action)."""

# ==============================================================================
# 9. ETL e Import
# ==============================================================================

ETLMode: TypeAlias = Literal["dry-run", "apply"]
"""Modo de execução de ETL.

- dry-run: Simulação, não persiste no banco
- apply: Execução real, persiste no banco
"""

ImportSource: TypeAlias = Literal["xlsx", "csv", "api"]
"""Fonte de importação de dados."""

# ==============================================================================
# Fim do arquivo
# ==============================================================================
