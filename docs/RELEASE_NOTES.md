# Release Notes - Aprender Sistema v2

## Autenticação

### Login por CPF (PR #51)

**Backend: `CPFOrUsernameBackend`**
- Aceita **username** ou **CPF** no mesmo campo de login
- Remove pontuação automaticamente (dots, hyphens, spaces) via regex `r'[.\-\s]'`
- Se input tem 11 dígitos após limpeza → busca por CPF
- Caso contrário → busca por username
- Validação de senha e status do usuário (`user_can_authenticate`)
- Implementação reversível, sem migrations
- Arquivo: `v2/backend/apps/core/auth_backends.py`
- Configuração: `AUTHENTICATION_BACKENDS` em `config/settings.py` (linhas 95-101)

**Frontend: Placeholder/Label Atualizado**
- Label: "CPF ou usuário"
- Placeholder: "CPF (com ou sem máscara) ou usuário"
- Arquivo: `v2/frontend/src/pages/Auth/LoginPage.jsx`

**Pré-requisito**
- Campo `Usuario.cpf` deve estar populado com 11 dígitos (sem pontuação)

**Segurança**
- Mensagens genéricas: "Credenciais inválidas." (não vaza existência de CPF/username)
- Rate-limit configurado via DRF throttling (`anon`, `user` scopes)

**Testes Validados**
- ✅ Autenticação por username (`cpf_test`)
- ✅ Autenticação por CPF com máscara (`987.654.321-09`)
- ✅ Autenticação por CPF sem máscara (`98765432109`)
- ✅ Mensagem genérica para credenciais inválidas

---

## Estabilização de ETL/Tests

### Batches 1-5: 96 → 0 Fails

**Progresso de Estabilização**
- **Início**: 96 testes falhando
- **Final**: 0 fails, 618 passing (100% estabilizado)

**PRs e Commits**
- **PR #46** (fechado): Batch 1 - Infraestrutura de testes
- **PR #47**: Batch 2 - Loaders/Commands (73→40 issues, -45%)
- **PR #48**: Batch 3 - Fixtures e permissões
- **PR #49**: Batch 4 - Idempotência e hash
- **PR #50**: Batch 5 - Quality gates e regras de negócio (23/23 testes passando)

**Correções Principais**

**Batch 1** - Infraestrutura
- ETL_OUTPUT_DIR com tmpdir
- Fixtures de dependências (Municipio, Projeto, TipoEvento)

**Batch 2** - Loaders/Commands
- Fixtures FK (Usuario → groups)
- tearDown e setup corrigidos

**Batch 3** - Fixtures e Permissões
- Permissions asserts alignment
- Fixtures scope review

**Batch 4** - Idempotência e Hash
- `external_hash` duplicado corrigido (4 campos → 11 campos completos)
- Testes de idempotência com `apply=True` para persistir dados
- Backfill de grupos (65 Formadores + 10 Coordenadores)

**Batch 5** - Quality Gates e Regras de Negócio
- **Duplicate Detection**: Hash completo (11 campos: source_sheet, municipio, encontro, tipo, data, hora_inicio, hora_fim, projeto, segmento, coord_acompanha, coordenador)
- **Unknown Users**: Contagem corrigida (incluindo coordenador do evento)
- **Indicator Filtering**: Lógica ajustada (filtrar apenas se display_name E email vazios)
- **Violations Report**: Gerado corretamente em dry-run (out_etl/*.json)
- **Super Multi-Município**: 1 evento → N solicitações (1 por município)
- **Outros sem Formador**: Coordenador duplicado como FORMADOR
- **Idempotência**: Rodar ETL 2x não duplica Solicitações/Participations

**Issues Fechadas**
- #35: ETL_OUTPUT_DIR + tmpdir
- #36: Fixtures FK e tearDown
- #37: Permissions asserts
- #38: Fixtures scope
- #39: dat_ingest refactor
- #43: Quarentena removal

**Status Final**
- ✅ 618 testes passando
- ✅ 0 fails, 0 errors
- ✅ Suite estabilizada para CI/CD
- ✅ Quarentena de `dat_ingest` removida

---

## Auditoria e Atribuição de CPF

### Comandos de Management (DRY-RUN/APPLY)

**1. audit_agenda_users** (Read-Only)
- Cross-check entre planilha de usuários e planilhas de agenda
- Identifica usuários não cadastrados que aparecem na agenda
- Detecta multi-setor (usuários em múltiplas abas)
- Gera relatórios JSON/CSV em `/app/out_etl`
- Matching por nome (heurísticas) e email
- Exclui "Convidados" no matching por nome
- Inclui emails "Convidados" no matching por email

**Uso**:
```bash
python manage.py audit_agenda_users \
  --users "/app/data/csv-import/Cópia de Usuários.xlsx" \
  --agenda "/app/data/csv-import/Cópia de Acompanhamento de Agenda _ 2025.xlsx"
```

**Saída**:
- `audit_users_crosscheck_report.json`
- `audit_users_crosscheck_enhanced.json`
- `audit_users_encontrados_por_aba.csv`

**2. assign_cpf_from_excel** (DRY-RUN → APPLY)
- Atribui CPFs aos usuários do sistema baseado em planilha Excel
- DRY-RUN (default): simula sem persistir
- APPLY (`--apply`): persiste no banco via `transaction.atomic()`
- Matching preferencial por email, fallback por nome
- Validação de CPF (11 dígitos, remove máscara)
- Detecta conflitos: duplicados, ambiguidades, divergências
- Idempotente: re-run não altera registros já atualizados

**Uso**:
```bash
# DRY-RUN (não persiste)
python manage.py assign_cpf_from_excel \
  --path "/app/data/csv-import/Cópia de Usuários.xlsx"

# APPLY (persiste)
python manage.py assign_cpf_from_excel \
  --path "/app/data/csv-import/Cópia de Usuários.xlsx" \
  --apply
```

**Saída**:
- `assign_cpf_report.json` (mode, updated, skipped, conflicts, totals)

### Admin Django — Filtro e Ação

**Filtro "CPF"**:
- **Ausente**: `cpf IS NULL` ou `cpf = ""`
- **Preenchido**: `cpf != NULL` e `cpf != ""`

**Ação "Exportar usuários sem CPF"**:
- Gera CSV via HTTP download
- Colunas: Username, Email, Nome Completo, CPF, Cargo, Ativo
- Também salva em `/app/out_etl/usuarios_sem_cpf.csv` para auditoria

### Segurança e PII

- ✅ Logs contêm apenas contagens (não mostram CPFs/nomes)
- ✅ Relatórios JSON/CSV mantidos em `/app/out_etl` (ignorados no Git)
- ✅ DRY-RUN obrigatório antes de APPLY
- ⚠️ Revisar `conflicts` antes de persistir
- ⚠️ Não compartilhar relatórios publicamente

### Testes

**test_assign_cpf_command.py** (7 testes):
- DRY-RUN: email match 1:1 → updated (não persiste)
- APPLY: persiste e re-run é idempotente
- CPF inválido/mascarado → skipped
- Email ambíguo → conflicts
- CPF duplicado na planilha → conflicts
- CPF divergente (banco != planilha) → conflicts

**test_audit_agenda_users.py** (5 testes):
- Gera JSON/CSV com chaves esperadas
- Exclui "Convidados" no matching por nome
- Inclui emails "Convidados" no matching por email
- Detecta multi-setor (usuários em múltiplas abas)
- Relatório top 20 não cadastrados por frequência

### Documentação

- **Guia completo**: `v2/docs/USERS_CPF_GUIDE.md`
  - Workflow recomendado (DRY-RUN → APPLY)
  - Estrutura das planilhas
  - Lógica de matching
  - Resolução de conflitos
  - Perguntas frequentes

### Arquivos Principais

- `v2/backend/apps/dat_ingest/management/commands/audit_agenda_users.py`
- `v2/backend/apps/dat_ingest/management/commands/assign_cpf_from_excel.py`
- `v2/backend/apps/core/admin.py` (classe `CPFFilter`, ação `export_usuarios_sem_cpf`)
- `v2/backend/apps/core/tests/test_assign_cpf_command.py`
- `v2/backend/apps/dat_ingest/tests/test_audit_agenda_users.py`

---

## Commit History

- **PR #47**: `5957b71` - fix(dat_ingest/tests): batch 2 — loaders/commands; 73→40 issues (-45%)
- **PR #48**: `388c9b4` - chore(ci): remove dat_ingest quarantine (#39 resolved)
- **PR #49**: `6e99545` - fix(dat_ingest/tests): restore suite via shims/adapters (#44)
- **PR #50**: `a61f7d8` - fix(dat_ingest): batch 5 — quality gates, rules, idempotency (23/23 passing)
- **PR #51**: `fa85b32` - feat(auth): login por CPF (sem alterar username) + placeholder 'CPF'

---

**Data**: 2025-10-29
**Responsável**: Claude Code + Matheus Norjosa
