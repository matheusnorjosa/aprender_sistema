---
name: aprender-domain
description: Complete business rules reference for Aprender Sistema v2. Use when implementing features, validating requirements, or testing compliance with RF (Functional Requirements), RD (Availability Rules), PA (Approval Policy), and CP (Immutable Clauses). Essential for understanding domain logic.
---

# Aprender Sistema v2 — Business Domain

## 🎯 Project Context

**Objective**: Replace 82,389 Excel formulas with a modern web system for event management and instructor availability.

**Before**: Manual spreadsheets with IMPORTRANGE, formulas, inconsistencies
**After**: Single Source of Truth in PostgreSQL with automated conflict checking

### Key Metrics
- ✅ 122 users migrated
- ✅ 1,250+ events imported
- ✅ 56+ tests passing
- ✅ MVP in staging (ready for production)

---

## 🔒 CP (Cláusulas Pétreas) — IMMUTABLE

### CP-01: REQUIRE_DOCKER=1 (v2 ONLY)
**Rule**: v2 MUST run ONLY in Docker. No exceptions.

**Validation** (config/settings.py):
```python
REQUIRE_DOCKER = os.getenv("REQUIRE_DOCKER", "0") == "1"
if REQUIRE_DOCKER and not os.path.exists("/.dockerenv"):
    print("❌ ERROR: v2 must run only in Docker", file=sys.stderr)
    sys.exit(1)
```

**Commands**:
```bash
cd v2 && make up  # OK
python manage.py runserver  # ❌ FORBIDDEN for v2
```

### CP-02: PA-01 to PA-07 (Manual Approval Policy)
See [PA section](#pa-approval-policy) below.

### CP-03: RD-01 to RD-08 (Availability Rules)
See [RD section](#rd-availability-rules) below.

### CP-04: Sub-Agent Workflow
**Order**: Understand → Plan → Implement → Test → Infra → ETL → UI/UX
**Never skip steps.**

### CP-05: Commit, Branch, and PR Standards
- **Commits**: `<type>(<scope>): <message>` (feat, fix, chore, docs, test, refactor)
- **Branches**: `<type>/<nome>` (ex: `feat/v2-gcal-integration`)
- **PRs**: Base `main`, require 1+ approval, CI green, **squash and merge**

---

## 📋 RD (Regras de Disponibilidade) — Availability Rules

### RD-01: Non-Overlapping
**Rule**: An instructor cannot have two events that overlap partially or totally.

**Edge Case**: If `end == start` → **NOT a conflict** (adjacent OK)
**Conflict**: Any overlap ≥ 1 minute

**Implementation**: `apps/core/services/availability_service.py:check_conflicts()`

**Test**: `test_availability_service.py::test_conflict_overlap_total`

### RD-02: Total Block (T)
**Rule**: A block marked as **T (total)** prevents ANY events in the defined interval.

**Code**: `X`
**Title**: "Bloqueio total"
**Detail**: "Formador [nome] tem bloqueio total em [data] [início]-[fim]"

**Test**: `test_availability_service.py::test_block_total_T_prevents_any_event`

### RD-03: Partial Block (P)
**Rule**: A block marked as **P (partial)** prevents events WITHIN the blocked subinterval.

**Code**: `P`
**Title**: "Bloqueio parcial"
**Allowed**: Events outside the subinterval

**Test**: `test_availability_service.py::test_block_partial_P_prevents_inside_allows_outside`

### RD-04: Travel Buffer (D)
**Rule**: Between **different municipalities**, require a **minimum travel time** (configurable, ex: 60-120 min).

**Same Municipality**: Buffer can be zero.

**Code**: `D`
**Title**: "Deslocamento necessário"
**Detail**: "Tempo mínimo de [X] min entre [cidade1] e [cidade2]"

**Test**: `test_availability_service.py::test_travel_buffer_between_cities_required`

### RD-05: Daily Capacity (M)
**Rule**: An instructor cannot have more than **N hours of events per day** (configurable).

**Code**: `M`
**Title**: "Mais de um evento / Capacidade excedida"

**Test**: `test_availability_service.py::test_daily_capacity_M_exceeded`

### RD-06: Timezone
**Rule**: Comparisons must be **timezone-aware**, using `America/Fortaleza`.

**Storage**: UTC in database
**Comparison**: Local timezone (America/Fortaleza)

**Test**: `test_availability_service.py::test_timezone_aware_fortaleza_localtime`

### RD-07: Priority of Checks
**Order**:
1. Blocks (T, P)
2. Conflicts (overlapping approved events)
3. Travel buffer (D)
4. Daily limit (M)

### RD-08: Conflict Messages
**Structure**: Must list:
- **Instructor(s)** in conflict
- **Date** and **interval** (HH:MM dd/mm)
- **Conflict type** (E, M, D, P, T, X)

**Example**:
```json
{
  "code": "T",
  "title": "Bloqueio total",
  "detail": "Maria Silva - 15/01/2025 09:00-12:00",
  "ref_id": 123
}
```

**Test**: `test_availability_service.py::test_conflict_messages_include_codes_and_intervals`

---

## ✅ PA (Política de Aprovação) — Approval Policy

### PA-01: No Auto-Approval (SUPER Projects)
**Rule**: A `Solicitacao` with `projeto.fluxo == 'SUPER'` **NEVER** changes to "Approved" automatically, even if no conflicts.

**Implementation**: `apps/core/models.py:Solicitacao.save()` (lines 431-448)

**Test**: `test_approval_policy_PA.py::test_never_auto_approves_on_clean_or_save`

### PA-02: Required Profile
**Rule**: Only users with **Superintendência** profile (or delegated Admin) can approve/reject.

**Permission Class**: `IsSuperintendencia` (apps/core/permissions.py)

**Test**: `test_approval_policy_PA.py::test_only_superintendencia_can_approve_or_reject`

### PA-03: Post-Approval Triggers
**Rule**: External integrations (RF05/RF06 - Google Calendar) only execute **AFTER** manual approval is complete.

**Validation**: Task `task_publish_solicitacao_to_gcal` is NOT called during Solicitacao.save()

**Test**: `test_approval_policy_PA.py::test_calendar_integration_not_called_before_approval`

### PA-04: Initial State
**Rule**: All SUPER project solicitations start with `status = 'pendente'`.

**NAO_SUPER Projects**: Auto-approved on creation (exception to PA-01, see PR18)

### PA-05: Audit
**Rule**: Record user, date/time, and justification (when applicable) in `Aprovacao` and `AuditLog`.

**Actions Logged**:
- `APPROVE` (approve endpoint)
- `REJECT` (reject endpoint)
- `PREVIEW_GCAL` (preview endpoint)
- `PUBLISH_GCAL_REQUESTED` (publish endpoint)
- `PUBLISH_GCAL` (celery task execution)

**Fields**: usuario, action, model_name, details (JSON: solicitation_id, prev_status, new_status, ip_address, user_agent)

**Test**: `test_approval_policy_PA.py::test_approval_flow_records_audit_log`

### PA-06: UI/UX
**Rule**: In requester/coordinator screens, display status and guidance; hide action buttons for profiles without permission (ISO 9241-110: explicit control).

**Implementation**: `ApprovalsPage.jsx` (lines 66-68, 89-109, 211)
- Loads `getMe()` to check permissions
- Verifies `is_superuser || is_superintendencia || groups.includes('Superintendência')`
- Buttons only render if `record.status === 'pendente' && canApprove`

### PA-07: Mandatory Tests
**Rule**: All 5 tests must pass:
1. `test_never_auto_approves_on_clean_or_save`
2. `test_only_superintendencia_can_approve_or_reject`
3. `test_calendar_integration_not_called_before_approval`
4. `test_approval_flow_records_audit_log`
5. `test_non_privileged_user_gets_403_on_approval_endpoint`

**Run**: `pytest apps/core/tests/test_approval_policy_PA.py -v`
**Expected**: 5/5 passing ✅

---

## 📝 RF (Requisitos Funcionais) — Functional Requirements

### RF01: Data Import (100% Complete)
**ETLs**:
- ✅ Users (122 migrated)
- ✅ Acompanhamento (events + participants, hash v2, quality gates)
- ✅ Compras (CSV/XLSX upload via API)
- ✅ Deslocamento (idempotent import)
- ✅ Ações Controle (reports in `out_etl/`)
- ✅ Cadastros DAT (API + management commands)

**Idempotence**: `external_hash` SHA1/SHA256 prevents duplicates

**Commands**:
```bash
# Dry-run
docker compose exec web python manage.py etl_upsert_acompanhamento

# Apply
docker compose exec web python manage.py etl_upsert_acompanhamento --apply
```

### RF02: Event Solicitation (100% Complete)
**UI**: Multi-step wizard (Ant Design) with 3 steps
1. Project, Municipality, Event Type
2. Date, Times (DatePicker + TimePicker)
3. Participants (multiple Select), Observation, **"Online Event" checkbox**

**Flow**:
- Coordinator → Creates solicitation
- System → Checks conflicts (RF03)
- If NAO_SUPER → Auto-approved (PR18)
- If SUPER → Pending → Awaits approval (PA-01 to PA-07)

### RF03: Conflict Verification (PR16 - 100% Complete)
**Status**: 17 tests passing ✅

**Service**: `availability_service.py:check_conflicts()`
**Returns**: `AvailabilityResult` with list of `ConflictDetail`

**Rules**: RD-01 to RD-08 (see above)

**API Endpoints**:
- `GET /api/availability/check/` - Individual
- `POST /api/availability/check-many/` - Batch

**Frontend**: `NewSolicitacaoPage.jsx` with visual feedback by type:
- ❌ Red (X, T): Blocking
- ⚠️ Orange (P, D): Attention
- ℹ️ Gold (M): Warning

### RF04: Approval Flow (PR17 - 100% Complete)
**Status**: 5 tests PA-01 to PA-07 passing ✅

**Policy**: See PA section above

**Endpoints**:
- `POST /api/solicitacoes/{id}/approve/` → AuditLog "APPROVE"
- `POST /api/solicitacoes/{id}/reject/` → AuditLog "REJECT"

**Frontend**: `ApprovalsPage.jsx` lists pending, Approve/Reject buttons (Superintendência only)

### RF05: Google Calendar Integration (PR32, PR33, PR41, PR42 - 100% Complete)
**Status**: All tests passing ✅

**Architecture**:
- **Factory Pattern**: `calendar_client_factory.py` (fake vs google)
- **Fake Client**: In-memory, safe, no side effects
- **Google Client**: Real API via Service Account
- **Idempotence**: `eventId=asv2-{id}` + `gcal_payload_hash` (SHA256)
- **Retry/Backoff**: 3 attempts (1s, 2s, 4s) for 429/5xx

**Workflow**:
1. **Preview** (`/preview-gcal/`): Generates full payload, returns JSON, **DOES NOT** persist
2. **Publish** (`/publish/`): Enqueues Celery task, returns 202 Accepted, respects `apply_blocked`

**Variables**:
```bash
GCAL_CLIENT=fake|google
GCAL_CALENDAR_ID=primary
GOOGLE_SERVICE_ACCOUNT_FILE=/secrets/sa.json
GCAL_SEND_UPDATES=none
```

### RF06: Google Meet Link Generation (PR41, PR42 - 100% Complete)
**Status**: Persistence tests passing ✅

**Field**: `meet_link` (TextField, read-only in serializer)

**Generation**:
- Payload includes `conferenceData` with unique `requestId`
- Google Calendar creates event + generates Meet link automatically
- Backend extracts `hangoutLink` from response
- **Persists ONLY in real APPLY** (not in preview, not in dry_run, not in 409)

**Modality (`is_online`)**:
- **`is_online=false` (default)**: In-person event, **no conferenceData**, no Meet link
- **`is_online=true`**: Online event, **with conferenceData**, generates Meet link

**UI**: `MeetLink.jsx` reusable component (used in 3 pages)
- Buttons: "Join meeting" + "Copy link"
- Returns `null` if `href` does not exist

### RF07: Audit (100% Complete)
**Model**: `AuditLog` (usuario, action, model_name, details JSON, created_at)

**Actions Logged**: APPROVE, REJECT, PREVIEW_GCAL, PUBLISH_GCAL_REQUESTED, PUBLISH_GCAL, RESYNC_GCAL_REQUESTED, CANCEL_GCAL_REQUESTED, CANCEL_GCAL

**Details Fields**: solicitation_id, prev_status, new_status, justificativa, ip_address, user_agent

### RF08: Monthly Map Interface (PR11 - 100% Complete)
**Page**: `/disponibilidade`

**Features**:
- **2 Separate Grids**: "Formadores" and "Coordenadores"
- **Shared Filters**: Year, Month, Sector, Search (q)
- **Virtualization**: Virtualized rows (performance with 100+ people)
- **Codes per Cell**:
  - **E**: 1 event
  - **2**: 2+ events
  - **P**: Partial block
  - **T**: Total block
  - **X**: Event + block
  - **D**: Travel
  - **D1**: Event + travel
- **Details on Click**: Modal with list of events/blocks/travels
- **Export CSV**: Button for each grid
- **Cache**: Redis 5 min, dense ranking by monthly workload

**API**:
```bash
GET /api/availability/monthly/?year=2025&month=1&role=FORMADOR&sector=SUL&q=maria
```

---

## 📊 Key Models (Domain)

### Usuario (Custom AbstractUser)
**SSOT**: Replaces "Usuários.xlsx" spreadsheet
**Fields**: cpf (UK), telefone, cargo, groups (Django RBAC)
**Groups**: Superintendência, Controle, Coordenador, Formador, DAT, Gerência

### Municipio
**SSOT**: List of served municipalities
**Fields**: nome (UK), uf, ibge_code (UK), ativo

### Projeto
**SSOT**: Organizational projects (ACerta, Brincando, etc.)
**Fields**: nome (UK), codigo (UK), **fluxo (SUPER/NAO_SUPER)**, descricao
- **SUPER Flow**: Requires manual Superintendência approval
- **NAO_SUPER Flow**: Auto-approved on creation (PR18)

### Solicitacao (Core of System)
**SSOT**: Pre-agenda, replaces "Acompanhamento" spreadsheet
**Key Fields**:
- `status`: pendente | aprovado | reprovado
- `inicio/fim`: DateTimeField timezone-aware (America/Fortaleza)
- `is_online`: Boolean (RF06 - determines if Meet link is generated)
- `external_event_id`: Google Calendar ID (idempotence)
- `meet_link`: TextField (auto-generated if `is_online=True`)
- `gcal_status`: NONE | PENDING | PUBLISHED | ERROR
- `gcal_payload_hash`: SHA256 for update idempotence
- `external_hash`: SHA1 for ETL import idempotence

### AvailabilityBlock
**SSOT**: Instructor schedule blocks
**Fields**: usuario, start_date, end_date, start_time, end_time, tipo (P/T), status

### AuditLog
**SSOT**: Complete traceability (PA-05)
**Fields**: usuario, action, model_name, details (JSON)

---

## 🔍 When to Use This Skill

| Scenario | Use aprender-domain |
|----------|---------------------|
| Implementing RF01-RF08 | Check requirements here |
| Validating RD-01 to RD-08 | Verify rules and tests |
| Testing PA-01 to PA-07 | Run mandatory tests |
| Understanding CP-01 to CP-06 | Review immutable clauses |
| Checking PR history | See Status Atual section |
| Designing new features | Ensure compliance with RD/PA/CP |

---

## 📚 Related Skills

- **`django-patterns`**: For implementation patterns (models, views, serializers)
- **`etl-guidelines`**: For ETL development (idempotence, quality gates)
- **`planning`**: For architecture decisions

---

## 🚀 Quick Reference Commands

```bash
# Test RF03 (RD-01 to RD-08)
pytest apps/core/tests/test_availability_service.py -v
# Expected: 17/17 passing

# Test PA-01 to PA-07
pytest apps/core/tests/test_approval_policy_PA.py -v
# Expected: 5/5 passing

# Test Google Calendar
pytest apps/core/tests/test_gcal*.py -v
# Expected: All passing

# ETL Acompanhamento (dry-run)
docker compose exec web python manage.py etl_upsert_acompanhamento

# ETL Acompanhamento (apply)
docker compose exec web python manage.py etl_upsert_acompanhamento --apply
```

---

**Last Updated**: 04/11/2025
**Version**: 1.0 (Consolidated: AS v2 Requirements + Premium Config)
