# Key Models (Domain)

## Usuario (Custom AbstractUser)

**SSOT**: Substitui a planilha "Usuários"
**Fields**: cpf (UK), telefone, cargo, groups (Django RBAC)
**Groups (RBAC SSOT)**:
- **13 Setores** (`apps.core.constants.SETOR_GROUPS`): Superintendência, Vidas, Fluir, ACerta, Brincando, Sou da Paz, DAT, Controle, Diretoria, Comercial, Relacionamento, Logística Viagens, Logística Galpão
- **5 Funções** (`apps.core.constants.FUNCAO_GROUPS`): Formador, Coordenador, Apoio de Coordenação, Gerente, Assistente Administrativo
- Idioma canônico de permissão: `permission_classes = [HasPerm("codename")]` (ver `v2/docs/RBAC_NAMING.md`)

## Municipio

**SSOT**: Lista de municípios atendidos
**Fields**: nome (UK), uf, ibge_code (UK), ativo

## Projeto

**SSOT**: Projetos organizacionais (ACerta, Brincando, etc.)
**Fields**: nome (UK), codigo (UK), **fluxo (SUPER/NAO_SUPER)**, descricao
- **SUPER Flow**: Requires manual Superintendência approval
- **NAO_SUPER Flow**: Auto-approved on creation

## Solicitacao (Core of System)

**SSOT**: Pré-agenda, substitui a planilha "Acompanhamento"
**File**: `apps/core/models/solicitacao.py`

**Key Fields**:
- `status`: pendente | aprovado | reprovado
- `inicio/fim`: DateTimeField timezone-aware (America/Fortaleza)
- `local`: CharField (max 300, endereço ou local específico do evento)
- `is_online`: Boolean (RF06 - determines if Meet link is generated)
- `external_event_id`: Google Calendar ID (idempotence)
- `meet_link`: TextField (auto-generated if `is_online=True`)
- `gcal_status`: NONE | PENDING | PUBLISHED | ERROR
- `gcal_payload_hash`: SHA256 for update idempotence
- `external_hash`: SHA1 for import idempotence
- `coordenador`: FK → Usuario (coordenador responsável)
- `coordenador_acompanha`: Boolean (se coordenador participa)

## AvailabilityBlock

**SSOT**: Bloqueios de agenda do formador
**Fields**: usuario, start_date, end_date, start_time, end_time, tipo (P/T), status

## AuditLog

**SSOT**: Rastreabilidade completa (PA-05)
**Fields**: usuario, action, model_name, details (JSON)
