# Key Models (Domain)

## Usuario (Custom AbstractUser)

**SSOT**: Substitui a planilha "Usuários"
**Fields**: cpf (UK), telefone, cargo, groups (Django RBAC)
**Groups (etiquetas; o poder vem da lotação, PR 12)**: com `RBAC_FONTE="lotacao"` (padrão), dar grupo não libera acesso; capacidade, tela e aprovação vêm do superusuário e do vínculo vigente (pacote do perfil da gerência + papel). `RBAC_FONTE=uniao` é só a volta de emergência. Ver `v2/docs/specs/backend/rbac.spec.md`.
- **13 Setores** (`apps.core.constants.SETOR_GROUPS`): Superintendência, Vidas, Fluir, ACerta, Brincando, Sou da Paz, DAT, Controle, Diretoria, Comercial, Relacionamento, Logística Viagens, Logística Galpão
- **5 Funções** (`apps.core.constants.FUNCAO_GROUPS`): Formador, Coordenador, Apoio de Coordenação, Gerente, Assistente Administrativo
- Idioma canônico de permissão: `permission_classes = [HasPerm("codename")]` (ver `v2/docs/RBAC_NAMING.md`)

## Municipio

**SSOT**: Lista de municípios atendidos
**Fields**: nome (UK), uf, ibge_code (UK), ativo

## Projeto

**SSOT**: Projetos organizacionais (ACerta, Brincando, etc.)
**Fields**: nome (UK), codigo (UK), **fluxo (SUPER/NAO_SUPER)**, descricao
- **SUPER Flow**: Requires manual approval by someone with a base in `solicitation_approval_basis` (PA-02: superuser, GERENTE vigente na Superintendência, DAT ou Controle pelo pacote da gerência)
- **NAO_SUPER Flow**: Auto-approved on creation, except when the município+projeto pair has no purchase releasing it (creator not exempt): it is born `pendente` and goes through PA-02 approval (owner decision, 03/11/2026; `resolve_initial_status(sem_compra=...)` in `apps/core/services/solicitacao_create.py`, flag from the serializer's Regra 4). An edit that moves an approved NAO_SUPER event into such a pair also sends it back to `pendente`. Importers do not pass `sem_compra`.

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
- `gcal_payload_hash`: SHA1 for update idempotence (drift do payload, sem `conferenceData`)
- `external_hash`: SHA1 for import idempotence
- `coordenador`: FK → Usuario (coordenador responsável)
- `coordenador_acompanha`: Boolean (se coordenador participa)

## AvailabilityBlock

**SSOT**: Bloqueios de agenda do formador
**Fields**: usuario, created_by, inicio, fim (DateTimeField, UTC), tipo (T/P), motivo, status (pendente/aprovado/reprovado, default aprovado)

## AuditLog

**SSOT**: Rastreabilidade completa (PA-05)
**Fields**: usuario, action, model_name, details (JSON)
