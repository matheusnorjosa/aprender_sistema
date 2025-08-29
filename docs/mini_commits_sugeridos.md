# Mini-Commits Sugeridos para Migração 2025

## 🔴 CRÍTICOS - Implementar Imediatamente

### Commit 1: Segurança - Substituir tokens hardcoded
```
feat(security): replace hardcoded tokens with environment variables

- Move all API tokens to .env file
- Update getApiToken() functions to use secure storage
- Add validation for missing tokens
- Remove fallback tokens from code

Files: planilhas/utils.py, .env.example
```

### Commit 2: API - Criar endpoints seguros para integrações externas
```
feat(api): add secure API endpoints for external integrations

- Create /api/formadores/ endpoint
- Create /api/disponibilidade/ endpoint  
- Create /api/compras/ endpoint
- Add authentication middleware
- Add rate limiting

Files: planilhas/api.py, planilhas/urls.py
```

### Commit 3: Triggers - Migrar onEdit triggers críticos
```
feat(automation): migrate critical onEdit triggers from Apps Script

- Add EventoAgenda auto-creation on status change
- Add Compra validation on edit
- Add availability recalculation triggers
- Add audit logging for all changes

Files: planilhas/signals.py, planilhas/models.py
```

## 🟡 IMPORTANTES - Próximas 2 semanas

### Commit 4: Dashboard - Interface para Acompanhamento de Agenda
```
feat(dashboard): add agenda management interface

- Create agenda dashboard view
- Add event creation/edit forms
- Add calendar integration
- Add formador availability display

Files: planilhas/views.py, templates/agenda/
```

### Commit 5: Dashboard - Interface para Controle de Compras
```
feat(dashboard): add purchasing management interface

- Create compras dashboard view
- Add bulk import functionality
- Add approval workflow
- Add integration with ERP systems

Files: planilhas/views.py, templates/compras/
```

### Commit 6: Backup - Sistema automático de backup
```
feat(backup): implement automated backup system

- Add daily database backup
- Add backup restoration commands
- Add backup validation
- Add notification on backup failures

Files: planilhas/management/commands/backup.py
```

### Commit 7: Monitoring - Sistema de monitoramento
```
feat(monitoring): add comprehensive monitoring system

- Add health check endpoints
- Add error tracking and alerts
- Add performance monitoring
- Add audit log viewer

Files: planilhas/monitoring.py, planilhas/health.py
```

## 🟢 MELHORIAS - Médio prazo

### Commit 8: Cache - Sistema de cache para performance
```
feat(cache): implement caching for improved performance

- Add Redis cache for frequent queries
- Cache formador availability data
- Cache calculated totals
- Add cache invalidation on data changes

Files: planilhas/cache.py, settings.py
```

### Commit 9: Integração - Google Calendar API nativa
```
feat(integration): add native Google Calendar integration

- Replace Apps Script calendar automation
- Add OAuth2 authentication
- Add event sync functionality
- Add conflict detection

Files: planilhas/google_calendar.py
```

### Commit 10: Relatórios - Sistema de relatórios avançados
```
feat(reports): add advanced reporting system

- Generate monthly availability reports
- Generate purchasing summaries
- Add export to Excel/PDF
- Add scheduled report delivery

Files: planilhas/reports.py, templates/reports/
```

### Commit 11: Mobile - Interface mobile responsiva
```
feat(mobile): add responsive mobile interface

- Optimize dashboard for mobile
- Add touch-friendly controls
- Add offline data sync
- Add push notifications

Files: static/css/mobile.css, templates/mobile/
```

### Commit 12: Testes - Cobertura completa de testes
```
test: add comprehensive test coverage

- Add integration tests for all APIs
- Add end-to-end tests for workflows
- Add performance tests
- Achieve 95%+ test coverage

Files: planilhas/tests/
```

## 📋 ORDEM DE IMPLEMENTAÇÃO RECOMENDADA

### Sprint 1 (Semana 1-2): Fundação Segura
- Commit 1: Segurança - Tokens
- Commit 2: API - Endpoints seguros
- Commit 6: Backup - Sistema automático

### Sprint 2 (Semana 3-4): Automação Core
- Commit 3: Triggers - Migração onEdit
- Commit 7: Monitoring - Sistema monitoramento
- Commit 12: Testes - Cobertura básica

### Sprint 3 (Semana 5-6): Interface Usuário
- Commit 4: Dashboard - Agenda
- Commit 5: Dashboard - Compras
- Commit 11: Mobile - Responsivo

### Sprint 4 (Semana 7-8): Integrações Avançadas
- Commit 8: Cache - Performance
- Commit 9: Integração - Google Calendar
- Commit 10: Relatórios - Sistema avançado

## 🎯 CRITÉRIOS DE SUCESSO

### Commit Aprovado Quando:
- ✅ Todos os testes passam
- ✅ Cobertura de testes > 80%
- ✅ Documentação atualizada
- ✅ Code review aprovado
- ✅ Performance não degradada
- ✅ Logs de auditoria funcionais

### Migração Completa Quando:
- ✅ Todos os 12 commits implementados
- ✅ Apps Scripts desativados
- ✅ Planilhas em modo read-only
- ✅ 100% das funcionalidades migradas
- ✅ Usuários treinados no novo sistema
- ✅ Backup e recovery testados

## 📊 ESTIMATIVAS

| Commit | Complexidade | Tempo Est. | Dependências |
|--------|--------------|------------|--------------|
| 1-3 | Alta | 3-5 dias | Nenhuma |
| 4-5 | Média | 5-7 dias | Commits 1-3 |
| 6-7 | Média | 3-5 dias | Commits 1-2 |
| 8-12 | Baixa-Média | 2-4 dias | Commits anteriores |

**Total Estimado: 6-8 semanas** para migração completa