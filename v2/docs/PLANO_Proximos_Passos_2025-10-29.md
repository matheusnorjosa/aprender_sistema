# Plano de Próximos Passos — 2025-10-29

## Escopo

Projeto v2-only, Docker-first. Documentação consolidada em `v2/docs`.

---

## Imediato (1–3 dias)

### ETL Observability
- Registrar execuções em `AuditLog` e expor `GET /api/etl/reports/latest` (read-only)
- Testes focados + documentação

### Execução CPF (produção)
- DRY-RUN com planilhas reais → revisar conflitos → APPLY controlado
- Registros em `out_etl/`

### Docs GCal
- `GCAL_GUIDE.md` consolidando SA/envs/apply_blocked/dry_run, Meet/meet_link, sendUpdates

---

## Curto Prazo (4–7 dias)

### Rollout de constantes
- Estender uso de `apps/dat_ingest/constants.py` para comandos `import_*`
- Sem mudar semântica

### OpenAPI (drf-spectacular)
- Publicar `/api/schema/` e `/api/docs/`
- Incluir exemplos e erros (403/409)

---

## Performance (1–2 semanas)

### Benchmark estendido
- Datasets maiores: 10k/50k/100k usuários
- Profiling: cProfile/py-spy
- `PERFORMANCE_GUIDE.md` com hotspots e recomendações

### Otimizações seguras
- LRU cache `normalize_text`
- Índices/estruturas para lookups
- Deduplicação por linha eficiente

---

## Observabilidade e Qualidade

### Endpoint de últimos relatórios
- Endpoint `latest` para relatórios ETL
- Opcional: página administrativa simples

### Testes adicionais
- Empates no Top 20
- Cenários de CPF (duplicado/divergente)
- GCal retry/backoff (429/5xx)

---

## Backlog (2–3 semanas)

### UI Controle/DAT
- Listas + criação manual

### Dashboard DAT
- Agregações + export CSV

---

## Critérios de Aceite

| Item | Critério |
|------|----------|
| **Observability** | AuditLog por execução + endpoint latest com testes |
| **Docs GCal** | Guia completo e exemplos funcionais |
| **Constantes** | Sem magic numbers remanescentes; testes verdes |
| **Performance** | Baseline publicado e plano de otimização aprovado |

---

## Notas de Implementação

### ETL Observability
- Criar modelo `ETLExecution` com campos: comando, timestamp, status, duration_ms, summary
- Endpoint: `GET /api/etl/reports/latest?command=audit_agenda_users&limit=10`
- Testes: validar persistência, formato JSON, filtros

### Constantes
- Verificar comandos pendentes: `import_acompanhamento`, `import_deslocamento`, `import_acoes_controle`
- Aplicar mesmo padrão de PR #54 (constants.py + testes + docs)

### Performance
- Baseline atual (PR #55):
  - 100 users: 0.46ms (normalize), 1.24ms (matching), 0.49ms (aggregation)
  - 1000 users: 4.43ms (normalize), 1.26ms (matching), 3.33ms (aggregation)
- Meta para 10k users: <50ms total, <1MB memória

---

## Referências

- **PR #54**: Constantes ETL (https://github.com/matheusnorjosa/aprender_sistema/pull/54)
- **PR #55**: Benchmark ETL (https://github.com/matheusnorjosa/aprender_sistema/pull/55)
- **Issue #55**: Follow-up de performance
- **GUIDE_GCAL.md**: Documentação atual de Google Calendar
- **ENV_VARS_ETL.md**: Variáveis de ambiente ETL

---

**Última atualização**: 2025-10-29
**Status**: Plano aprovado, aguardando implementação
