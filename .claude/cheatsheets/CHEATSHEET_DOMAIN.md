# Domain Cheatsheet — Aprender Sistema v2

Quick reference for business rules. Full details: `.claude/skills/aprender-domain/SKILL.md`

---

## CP — Cláusulas Pétreas (IMUTÁVEIS)

| CP | Regra | Validação |
|----|-------|-----------|
| **CP-01** | v2 só roda em Docker | `cd v2 && make up` |
| **CP-02** | Política de Aprovação PA-01~07 | Ver PA abaixo |
| **CP-03** | Regras Disponibilidade RD-01~08 | Ver RD abaixo |
| **CP-04** | Workflow: Entender→Planejar→Implementar→Testar→Infra→ETL→UI | Nunca pular |
| **CP-05** | Conventional commits | `<type>(<scope>): <msg>` |
| **CP-06** | Nunca tocar v1 | Branch `fix/v1-*` + PR `main-v1` |
| **CP-07** | Nunca push direto na main | Sempre via PR |
| **CP-08** | INCLUDE_DEV_TOOLS | `true` dev/staging, `false` prod |

---

## RD — Regras de Disponibilidade

| RD | Código | Regra | Mensagem |
|----|--------|-------|----------|
| **RD-01** | `E` | Não-sobreposição (fim==início OK) | "Conflito com evento existente" |
| **RD-02** | `T` | Bloqueio total impede tudo | "Bloqueio total em [data] [hora]" |
| **RD-03** | `P` | Bloqueio parcial impede subintervalo | "Bloqueio parcial em [hora]" |
| **RD-04** | `D` | Buffer deslocamento entre municípios | "Deslocamento necessário [X] min" |
| **RD-05** | `M` | Capacidade diária por formador | "Mais de um evento / Capacidade" |
| **RD-06** | — | Timezone America/Fortaleza, UTC storage | — |
| **RD-07** | — | Prioridade: T/P → E → D → M | — |
| **RD-08** | — | Mensagens: formador, data, intervalo, tipo | JSON com code/title/detail |

### Códigos do Mapa Mensal
| Código | Significado |
|--------|-------------|
| `E` | 1 evento |
| `2` | 2+ eventos |
| `P` | Bloqueio parcial |
| `T` | Bloqueio total |
| `X` | Evento + bloqueio |
| `D` | Deslocamento |
| `D1` | Evento + deslocamento |

---

## PA — Política de Aprovação

| PA | Regra | Implementação |
|----|-------|---------------|
| **PA-01** | Sem auto-aprovação SUPER | `Solicitacao.save()` lines 431-448 |
| **PA-02** | Só Superintendência/DAT/superuser aprova | `IsSuperintendencia` permission |
| **PA-03** | GCal só após aprovação | Task não chamada em save() |
| **PA-04** | Estado inicial: pendente (SUPER), aprovado (NAO_SUPER) | — |
| **PA-05** | Registrar em Aprovacao + AuditLog | Campos: usuario, action, details |
| **PA-06** | Esconder botões sem permissão | `ApprovalsPage.jsx` lines 66-68 |
| **PA-07** | 5 testes obrigatórios | `test_approval_policy_PA.py` |

### Testes PA Obrigatórios
```bash
pytest apps/core/tests/test_approval_policy_PA.py -v
# 1. test_never_auto_approves_on_clean_or_save
# 2. test_only_superintendencia_can_approve_or_reject
# 3. test_calendar_integration_not_called_before_approval
# 4. test_approval_flow_records_audit_log
# 5. test_non_privileged_user_gets_403_on_approval_endpoint
```

---

## RF — Requisitos Funcionais

| RF | Descrição | Status | Endpoint/Service |
|----|-----------|--------|------------------|
| **RF01** | Import ETL | ✅ | `etl_upsert_*` commands |
| **RF02** | Solicitar evento | ✅ | `POST /api/solicitacoes/` |
| **RF03** | Verificar conflitos | ✅ | `GET /api/availability/check/` |
| **RF04** | Aprovar/Reprovar | ✅ | `POST /api/solicitacoes/{id}/approve/` |
| **RF05** | Google Calendar | ✅ | `POST /api/solicitacoes/{id}/publish/` |
| **RF06** | Google Meet | ✅ | Campo `meet_link` (is_online=true) |
| **RF07** | Auditoria | ✅ | Model `AuditLog` |
| **RF08** | Mapa Mensal | ✅ | `GET /api/availability/monthly/` |

---

## Fluxos de Projeto

```
SUPER (Superintendência, ACerta, etc.):
  Criar → pendente → [Aprovar] → aprovado → GCal
                   → [Reprovar] → reprovado

NAO_SUPER (Controle interno):
  Criar → aprovado (auto) → GCal
```

---

## Models Principais

| Model | Chave Única | Propósito |
|-------|-------------|-----------|
| `Usuario` | cpf | Usuários do sistema |
| `Municipio` | nome, ibge_code | Municípios atendidos |
| `Projeto` | nome, codigo | Projetos (fluxo SUPER/NAO_SUPER) |
| `Solicitacao` | — | Pré-agenda de eventos |
| `AvailabilityBlock` | — | Bloqueios de agenda |
| `AuditLog` | — | Rastreabilidade |
| `PlanoFormacoes` | municipio+projeto | Plano anual |
| `Formacao` | plano+numero_formacao | Formação individual |
| `DATAcao` | municipio+projeto | Workflow 4 etapas |
| `DATCadastro` | municipio+projeto_geral+plataforma | FORMAR/AVALIAR |

---

## Quick Commands

```bash
# Testes RD
pytest apps/core/tests/test_availability_service.py -v

# Testes PA
pytest apps/core/tests/test_approval_policy_PA.py -v

# Testes GCal
pytest apps/core/tests/test_gcal*.py -v

# ETL dry-run
docker compose exec web python manage.py etl_upsert_acompanhamento

# ETL apply
docker compose exec web python manage.py etl_upsert_acompanhamento --apply

# Type check
cd v2/backend && pyright apps/core
```
