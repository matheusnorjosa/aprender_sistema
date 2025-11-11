"""
Type Aliases Centralizados — Aprender Sistema v2

Arquivo centralizado com todos os type aliases do projeto usando PEP 695 (Python 3.12+).

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

from typing import Any, Callable, Literal

# ==============================================================================
# 1. IDs e Identificadores
# ==============================================================================

type UserId = int
"""ID de usuário (Usuario.id)."""

type SolicitacaoId = int
"""ID de solicitação (Solicitacao.id)."""

type ProjetoId = int
"""ID de projeto (Projeto.id)."""

type MunicipioId = int
"""ID de município (Municipio.id)."""

type TipoEventoId = int
"""ID de tipo de evento (TipoEvento.id)."""

type AvailabilityBlockId = int
"""ID de bloqueio (AvailabilityBlock.id)."""

type DeslocamentoId = int
"""ID de deslocamento (Deslocamento.id)."""

type ParticipationId = int
"""ID de participação (Participation.id)."""

# ==============================================================================
# 2. Status e Estados
# ==============================================================================

type Status = Literal["pendente", "aprovado", "reprovado"]
"""Status de solicitação (Solicitacao.status)."""

type Fluxo = Literal["SUPER", "NAO_SUPER"]
"""Fluxo de aprovação (Projeto.fluxo).

- SUPER: Requer aprovação manual da Superintendência (PA-01 a PA-07)
- NAO_SUPER: Auto-aprovado na criação (PR18)
"""

type GCalStatus = Literal["NONE", "PENDING", "PUBLISHED", "ERROR"]
"""Status de sincronização Google Calendar (Solicitacao.gcal_status)."""

type BlockType = Literal["P", "T"]
"""Tipo de bloqueio de disponibilidade (AvailabilityBlock.tipo).

- P: Parcial (RD-03)
- T: Total (RD-02)
"""

type ApprovalStatus = Literal["pendente", "aprovado", "reprovado"]
"""Status de aprovação (Aprovacao.status)."""

# ==============================================================================
# 3. Códigos de Conflito (RD-01 a RD-08)
# ==============================================================================

type ConflictCode = Literal["X", "T", "P", "D", "M", "E"]
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

type EventId = str
"""ID de evento no Google Calendar (ex: 'asv2-123')."""

type CalendarId = str
"""ID de calendário Google (ex: 'primary' ou 'user@group.calendar.google.com')."""

type MeetLink = str
"""URL do Google Meet (ex: 'https://meet.google.com/abc-defg-hij')."""

type GCalClientType = Literal["fake", "google"]
"""Tipo de cliente Google Calendar (settings.GCAL_CLIENT).

- fake: Cliente in-memory para testes (sem side effects)
- google: Cliente real via Google Calendar API
"""

type SendUpdates = Literal["none", "all", "externalOnly"]
"""Política de envio de notificações Google Calendar (settings.GCAL_SEND_UPDATES).

- none: Não envia emails
- all: Envia para todos os participantes
- externalOnly: Envia apenas para participantes externos ao domínio
"""

# ==============================================================================
# 5. JSON e Estruturas
# ==============================================================================

type JsonDict = dict[str, Any]
"""Dicionário JSON genérico."""

type JsonList = list[JsonDict]
"""Lista de dicionários JSON."""

type PayloadHash = str
"""Hash SHA256 de payload (ex: gcal_payload_hash para idempotência)."""

type ExternalHash = str
"""Hash SHA1/SHA256 para idempotência de ETL (external_hash)."""

# ==============================================================================
# 6. Handlers e Callbacks
# ==============================================================================

type ErrorHandler = Callable[[Exception], None]
"""Callback para tratamento de erros."""

type SuccessCallback[T] = Callable[[T], None]
"""Callback genérico para sucesso (PEP 695 generic)."""

type ValidationFunction[T] = Callable[[T], bool]
"""Função de validação genérica (retorna True se válido)."""

# ==============================================================================
# 7. Timezone
# ==============================================================================

type TimezoneName = Literal["America/Fortaleza"]
"""Timezone do projeto (RD-06).

IMPORTANTE: Sempre usar timezone-aware datetimes.
- Storage: UTC no banco
- Comparison: America/Fortaleza
"""

# ==============================================================================
# 8. RBAC (Grupos e Permissões)
# ==============================================================================

type GroupName = Literal[
    "Superintendência",
    "Controle",
    "Coordenador",
    "Formador",
    "DAT",
    "Gerência"
]
"""Grupos de permissão Django (Usuario.groups)."""

type ActionType = Literal[
    "APPROVE",
    "REJECT",
    "PREVIEW_GCAL",
    "PUBLISH_GCAL_REQUESTED",
    "PUBLISH_GCAL",
    "RESYNC_GCAL_REQUESTED",
    "CANCEL_GCAL_REQUESTED",
    "CANCEL_GCAL"
]
"""Tipos de ação para auditoria (AuditLog.action)."""

# ==============================================================================
# 9. ETL e Import
# ==============================================================================

type ETLMode = Literal["dry-run", "apply"]
"""Modo de execução de ETL.

- dry-run: Simulação, não persiste no banco
- apply: Execução real, persiste no banco
"""

type ImportSource = Literal["xlsx", "csv", "api"]
"""Fonte de importação de dados."""

# ==============================================================================
# Fim do arquivo
# ==============================================================================
