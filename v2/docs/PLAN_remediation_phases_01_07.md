# Plano de Remediação — Fases 01 a 07

**Data**: 2026-02-05
**Baseado em**: Análise de código Codex (phases 01-07)
**Status**: Aguardando execução

---

## Sumário Executivo

| Severidade | Quantidade | Esforço Total |
|------------|------------|---------------|
| 🔴 Crítico | 6 | ~3-4 dias |
| 🟠 Alto | 8 | ~4-5 dias |
| 🟡 Médio | 14 | ~5-6 dias |
| 🟢 Baixo | 12 | ~2-3 dias |
| **Total** | **40** | **~14-18 dias** |

---

## 🔴 CRÍTICOS (Segurança/Integridade) — Sprint 1

### C-01: Criação de solicitação não valida conflitos (RD-01)
- **Fase**: 02
- **Arquivo**: `views_solicitacao.py`, `availability_service.py`
- **Problema**: Backend não chama `check_conflicts` na criação, permitindo eventos conflitantes
- **Impacto**: Viola RD-01 (não-sobreposição)
- **Esforço**: M (4-8h)
- **Issue**: #558

### C-02: Aprovação aceita transições fora de "pendente"
- **Fase**: 02
- **Arquivo**: `solicitacao_approval.py`
- **Problema**: `approve_solicitacao` não bloqueia status reprovado; `reject_solicitacao` não bloqueia aprovado
- **Impacto**: Estados inválidos possíveis
- **Esforço**: S (2-4h)
- **Issue**: #559

### C-03: Usuários podem editar/excluir bloqueios de terceiros
- **Fase**: 03
- **Arquivo**: `views_availability.py`
- **Problema**: Queryset permite listar/editar blocos de outros usuários da mesma gerência
- **Impacto**: IDOR - acesso indevido a dados sensíveis
- **Esforço**: M (4-8h)
- **Issue**: #560

### C-04: `assign_groups` ignora whitelist e auto-modificação
- **Fase**: 05
- **Arquivo**: `views/admin.py`
- **Problema**: Endpoint não usa validação do serializer, permite escalação de privilégios
- **Impacto**: Risco de segurança RBAC
- **Esforço**: S (2-4h)
- **Issue**: #561

### C-05: Backups via Celery quebrados no Docker
- **Fase**: 07
- **Arquivos**: `tasks_backup.py`, `docker-compose.yml`, `backup_db.sh`
- **Problema**: Script não disponível no worker; paths e host incorretos
- **Impacto**: **Sem backup automático em produção**
- **Esforço**: L (8-16h)
- **Issue**: #562

### C-06: Health check de backup sempre degrada
- **Fase**: 07
- **Arquivo**: `views_health.py`
- **Problema**: Busca `backup_full_*.sql.gz` mas script gera `aprender_db_*.sql.gz`
- **Impacto**: Falsos alertas de backup degradado
- **Esforço**: S (1-2h)
- **Issue**: #563

---

## 🟠 ALTOS (RBAC/Permissões) — Sprint 2

### A-01: Dashboard overview exposto com IsAuthenticated
- **Fase**: 01
- **Arquivo**: `views_dashboard.py`
- **Problema**: `/api/dashboard/overview/` permite qualquer autenticado ver métricas agregadas
- **Impacto**: Exposição de dados sensíveis
- **Esforço**: S (2-4h)
- **Issue**: #564

### A-02: RBAC desalinhado UI vs Backend (dashboards)
- **Fase**: 01, 06
- **Arquivos**: `App.tsx`, `views/metrics/*.py`
- **Problema**: Frontend permite DAT/Diretoria, backend exige Controle/Gerência
- **Impacto**: 403 inesperados ou acesso indevido
- **Esforço**: M (4-8h)
- **Issue**: #565

### A-03: Grupo "Diretoria" não é criado via seed/migration
- **Fase**: 01, 05
- **Arquivos**: `seed_rbac.py`, migrations
- **Problema**: UI referencia grupo inexistente
- **Impacto**: Funcionalidade quebrada para Diretoria
- **Esforço**: S (1-2h)
- **Issue**: #566

### A-04: Grade mensal expõe dados SUPER sem filtro
- **Fase**: 03
- **Arquivo**: `views_availability_monthly.py`
- **Problema**: Sem `gerencia_id`, retorna dados de toda organização
- **Impacto**: Exposição ampla de dados
- **Esforço**: M (4-8h)
- **Issue**: #567

### A-05: Endpoints GCal muito abertos
- **Fase**: 04
- **Arquivo**: `views_gcal/gcal.py`
- **Problema**: `/api/gcal/calendars/` e `/api/gcal/health/` permitem qualquer autenticado
- **Impacto**: Info sensível do GCal exposta
- **Esforço**: S (2-4h)
- **Issue**: #568

### A-06: ImportCompras sem validação de upload
- **Fase**: 05
- **Arquivo**: `views_controle_imports.py`
- **Problema**: Não valida tamanho/MIME como outros endpoints
- **Impacto**: Risco de DoS por upload grande
- **Esforço**: S (2-4h)
- **Issue**: #569

### A-07: `/metrics` não exposto no Nginx
- **Fase**: 07
- **Arquivo**: `nginx/sites-available/aprender`
- **Problema**: Endpoint cai no SPA, Prometheus não consegue scrape
- **Impacto**: Observabilidade quebrada em produção
- **Esforço**: S (1-2h)
- **Issue**: #570

### A-08: Celery Beat pode não rodar backups em produção
- **Fase**: 07
- **Arquivo**: systemd config, celery
- **Problema**: DatabaseScheduler ignora `beat_schedule` do código
- **Impacto**: Backups não executam
- **Esforço**: M (4-8h)
- **Issue**: #571

---

## 🟡 MÉDIOS (Funcionalidade) — Sprint 3

### M-01: Cancelamento OAuth usa service account
- **Fase**: 04
- **Arquivo**: `solicitacao_publish.py`
- **Problema**: Não usa OAuth do operador para cancelar
- **Impacto**: Status pode ficar preso
- **Esforço**: M (4-8h)
- **Issue**: #572

### M-02: Hash drift em eventos online (falsos positivos)
- **Fase**: 04
- **Arquivo**: `gcal/payload.py`, `gcal/sync.py`
- **Problema**: `conferenceData` com requestId aleatório causa drift falso
- **Impacto**: Alertas incorretos de eventos desatualizados
- **Esforço**: M (4-8h)
- **Issue**: #573

### M-03: CadastrosPage envia campos não suportados
- **Fase**: 05
- **Arquivo**: `CadastrosPage.tsx`, `dat_cadastro.py`
- **Problema**: Frontend envia campos que serializer rejeita
- **Impacto**: HTTP 400 em create/update
- **Esforço**: S (2-4h)
- **Issue**: #574

### M-04: ETL Reports RBAC desalinhado
- **Fase**: 05
- **Arquivo**: `App.tsx`, `dat_ingest/views.py`
- **Problema**: UI usa `canDAT`, backend exige Controle/Super
- **Impacto**: DAT recebe 403
- **Esforço**: S (2-4h)
- **Issue**: #575

### M-05: Downloads ETL sem endpoint backend
- **Fase**: 05
- **Arquivo**: `etl.ts`, `dat_ingest/urls.py`
- **Problema**: Frontend espera `/out_etl/<arquivo>`, não existe
- **Impacto**: Download 404
- **Esforço**: M (4-8h)
- **Issue**: #576

### M-06: Filtros de data no mapa não funcionam
- **Fase**: 06
- **Arquivo**: `map_metrics.py`
- **Problema**: Backend ignora `data_inicio/data_fim`
- **Impacto**: UX enganosa
- **Esforço**: M (4-8h)
- **Issue**: #577

### M-07: metrics_map truncado em 50
- **Fase**: 06
- **Arquivo**: `map_metrics.py`
- **Problema**: Limite default trunca dados, UI agrega incorretamente
- **Impacto**: Contagens por UF erradas
- **Esforço**: S (2-4h)
- **Issue**: #578

### M-08: Contagem coordenadores por nome (colisão)
- **Fase**: 06
- **Arquivo**: `map_metrics.py`
- **Problema**: Usa nome do município como chave, não ID
- **Impacto**: Dados incorretos para municípios homônimos
- **Esforço**: S (2-4h)
- **Issue**: #579

### M-09: RequestIDMiddleware reaproveita ID entre requisições
- **Fase**: 07
- **Arquivo**: `middleware.py`
- **Problema**: Thread-local não é limpo, IDs reutilizados
- **Impacto**: Correlação de logs inválida
- **Esforço**: S (2-4h)
- **Issue**: #580

### M-10: RPO/RTO inconsistentes entre docs
- **Fase**: 07
- **Arquivos**: `DISASTER_RECOVERY.md`, `GUIDE_DR.md`, `BACKUP_OPERATIONS.md`
- **Problema**: Valores divergentes (5 min vs 24h, 30 min vs 1h)
- **Impacto**: Confusão operacional
- **Esforço**: S (2-4h)
- **Issue**: #581

### M-11: Scripts DR divergem da implementação
- **Fase**: 07
- **Arquivo**: `DISASTER_RECOVERY.md`, `infra/scripts/`
- **Problema**: Docs mostram `docker compose exec`, scripts usam VM local
- **Impacto**: Runbook incorreto
- **Esforço**: M (4-8h)
- **Issue**: #582

### M-12: test_dr.sh usa DB name diferente
- **Fase**: 07
- **Arquivo**: `test_dr.sh`
- **Problema**: Usa `aprender_sistema`, settings usa `aprender_db`
- **Impacto**: Teste DR falha
- **Esforço**: S (1-2h)
- **Issue**: #583

### M-13: Media files locais (scaling incompleto)
- **Fase**: 07
- **Arquivo**: `settings.py`
- **Problema**: `MEDIA_ROOT` local, não S3
- **Impacto**: Uploads inconsistentes em múltiplas instâncias
- **Esforço**: L (8-16h)
- **Issue**: #584

### M-14: alerts.yml referenciado mas não existe
- **Fase**: 07
- **Arquivo**: `SLO_DEFINITIONS.md`
- **Problema**: Referencia arquivo inexistente
- **Impacto**: Sem alertas configurados
- **Esforço**: M (4-8h)
- **Issue**: #585

---

## 🟢 BAIXOS (Cleanup/Docs) — Sprint 4

### B-01: Login audit IP sem proxy headers
- **Fase**: 01
- **Arquivo**: `views_auth.py`
- **Esforço**: S (1-2h)
- **Issue**: #586

### B-02: AuditLog approve sem justificativa/user_agent
- **Fase**: 02
- **Arquivo**: `solicitacao_approval.py`
- **Esforço**: S (1-2h)
- **Issue**: #587

### B-03: check_conflicts sem buffer para municipio=None
- **Fase**: 03
- **Arquivo**: `availability_service.py`
- **Esforço**: S (2-4h)
- **Issue**: #588

### B-04: Código conflito "E" vs "X" na doc
- **Fase**: 03
- **Arquivo**: `regras-disponibilidade.md`
- **Esforço**: S (1h)
- **Issue**: #589

### B-05: Documentação GCal desatualizada
- **Fase**: 04
- **Arquivo**: `API_REFERENCE.md`, `API_EXAMPLES.md`
- **Esforço**: S (2-4h)
- **Issue**: #590

### B-06: Frontend GCal endpoints não implementados
- **Fase**: 04
- **Arquivo**: `gcal.ts`
- **Esforço**: S (1-2h)
- **Issue**: #591

### B-07: Hash SHA1 vs SHA256 na doc
- **Fase**: 04
- **Arquivo**: `types.py`, `gcal/utils.py`
- **Esforço**: S (1h)
- **Issue**: #592

### B-08: listProdutosDAT endpoint inexistente
- **Fase**: 05
- **Arquivo**: `datModule.ts`
- **Esforço**: S (1h)
- **Issue**: #593

### B-09: KPI total_formadores inflado
- **Fase**: 06
- **Arquivo**: `views_dashboard.py`
- **Esforço**: S (2-4h)
- **Issue**: #594

### B-10: Documentação métricas desatualizada
- **Fase**: 06
- **Arquivo**: `API_REFERENCE.md`, `BACKLOG_MAPA_BRASIL.md`
- **Esforço**: S (2-4h)
- **Issue**: #595

### B-11: LOGGING.md referencia logger.js (é .ts)
- **Fase**: 07
- **Arquivo**: `LOGGING.md`
- **Esforço**: S (15 min)
- **Issue**: #596

### B-12: Makefile usa porta/endpoint incorreto
- **Fase**: 07
- **Arquivo**: `infra/Makefile`
- **Esforço**: S (30 min)
- **Issue**: #597

---

## Ordem de Execução Recomendada

### Sprint 1 (Críticos) — ~3-4 dias
1. C-05: Backups via Celery (maior impacto operacional)
2. C-01: check_conflicts na criação
3. C-02: Transições de status
4. C-03: Autorização bloqueios
5. C-04: assign_groups
6. C-06: Health check backup

### Sprint 2 (Altos) — ~4-5 dias
1. A-02: RBAC dashboards (afeta muitos usuários)
2. A-07: /metrics no Nginx
3. A-08: Celery Beat produção
4. A-01: Dashboard overview
5. A-03: Grupo Diretoria
6. A-04: Grade mensal filtro
7. A-05: Endpoints GCal
8. A-06: ImportCompras validação

### Sprint 3 (Médios) — ~5-6 dias
- Priorizar por dependência e impacto no usuário

### Sprint 4 (Baixos) — ~2-3 dias
- Batch de cleanup e docs

---

## Métricas de Acompanhamento

- [ ] Issues criadas no GitHub
- [ ] PRs abertos para cada sprint
- [ ] Testes passando após cada correção
- [ ] CI verde em todos os PRs
- [ ] Docs atualizados conforme correções

---

## Notas

1. **Já corrigidos (PR #557)**:
   - Links `/admin-dat` → `/dat/admin` (era Fase 05, B-07 original)
   - Bugs de disponibilidade (#549-#556)

2. **Dependências entre itens**:
   - C-05 e C-06 devem ser feitos juntos
   - A-02 afeta múltiplas páginas, coordenar com frontend

3. **Riscos**:
   - C-05 (backups) é crítico para produção
   - Media files (M-13) requer mudança de infraestrutura
