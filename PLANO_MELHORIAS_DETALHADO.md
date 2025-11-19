# Plano de Melhorias Detalhado - Aprender Sistema v2
**Data:** 2025-01-19
**Baseado em:** Análise completa do sistema (models, endpoints, planilhas, regras de negócio)

---

## Sumário Executivo

Este plano detalha a implementação de 2 funcionalidades atualmente desabilitadas na HomePage:
1. **Configurações do Sistema** - UI para ajustar parâmetros críticos (disponibilidade, GCal, sessões)
2. **Desempenho da Equipe** - Métricas de negócio e KPIs para gestão

Além disso, identifica **3 gaps funcionais críticos** descobertos na análise.

---

## 📊 Análise Atual do Sistema

### O que já temos implementado

#### Backend (Django)
- ✅ Model `Config` (v2/backend/apps/core/models.py:573-624) com cache Redis (5 min TTL)
- ✅ 15 configurações via env vars em `settings.py`
- ✅ Observabilidade completa (MP1: Prometheus, MP2: Logs JSON, MP3: Sentry APM)
- ✅ Models completos: `Solicitacao`, `Participation`, `AvailabilityBlock`, `Deslocamento`, `AuditLog`

#### Frontend (React)
- ✅ Páginas principais: Grade Mensal, Pré-agenda, Aprovações, Solicitações
- ✅ RBAC implementado por perfil
- ✅ HomePage com cards por nível de acesso

#### Gaps Identificados
- ❌ **UI para Configurações** - Model existe mas sem interface (só Django Admin)
- ❌ **Métricas de Negócio** - Só temos métricas técnicas (Prometheus), faltam KPIs de negócio
- ❌ **UI para Deslocamentos** - Model existe, ETL implementado, mas sem CRUD na UI

---

## 🎯 Plano de Implementação (4 Fases)

### ✅ Fase 1: UI para Configurações do Sistema
**Esforço estimado:** 8-12h
**Prioridade:** 🔴 Alta (base para outras features)
**Issue:** #XXX

#### Motivação
- Time atualmente usa Django Admin para ajustar parâmetros críticos (buffer, limite diário)
- Mudanças exigem conhecimento técnico e acesso de superuser
- Parâmetros afetam regras de negócio (RD-04, RD-05) e devem ser ajustáveis por Superintendência/DAT

#### Escopo

**Backend:**
- [ ] Endpoint `GET /api/config/` - Leitura de configurações
  - Retorna JSON com categorias: `availability`, `gcal_sync`, `session_settings`, `features`
  - Permissão: `IsDAT | IsSuperintendencia`
  - Cache: 5 min (já implementado no model)

- [ ] Endpoint `PUT /api/config/` - Edição de configurações
  - Validação de tipos (int, bool, enum)
  - Validação de ranges (ex: `TRAVEL_BUFFER_MINUTES >= 0`)
  - AuditLog automático via signal
  - Invalidação de cache após save

- [ ] Serializer `ConfigSerializer` (apps/core/serializers.py)
  - Campos aninhados por categoria
  - Validação customizada por campo

**Frontend:**
- [ ] Página `/admin/configuracoes` (apps/AdminDAT/ConfiguracoesPage.jsx)
  - Permissão: DAT + Superintendência (RBAC)
  - Layout: Tabs por categoria + botão "Salvar"

- [ ] Tab "Disponibilidade" (RD-04, RD-05)
  - `TRAVEL_BUFFER_MINUTES` (InputNumber, min: 0, default: 120)
  - `AVAILABILITY_DAILY_LIMIT_HOURS` (InputNumber, min: 1, max: 12, default: 8)
  - `ALLOW_ADJACENT_EVENTS` (Switch, default: true)
  - `BLOCK_AUTO_APPROVE` (Switch, default: true)

- [ ] Tab "Google Calendar" (RF05/RF06)
  - `BATCH_SIZE` (InputNumber, min: 50, max: 500, default: 200)
  - `LOCK_TTL_SECONDS` (InputNumber, min: 60, max: 600, default: 300)
  - `AUTO_RETRY_ON_ERROR` (Switch, default: true)
  - `MAX_RETRIES` (InputNumber, min: 1, max: 5, default: 3)
  - `SEND_UPDATES` (Select: "none", "all", "externalOnly")

- [ ] Tab "Sessões e UX"
  - `SESSION_COOKIE_AGE` (InputNumber, segundos, default: 1800)
  - `SESSION_WARNING_THRESHOLD` (InputNumber, segundos, default: 300)
  - `AUTOCOMPLETE_DEBOUNCE_MS` (InputNumber, ms, default: 300)

- [ ] Tab "Feature Flags"
  - `ENABLE_MULTI_CALENDAR` (Switch, default: false) - OAuth multi-calendar (GAP-5)
  - `ENABLE_BATCH_ACTIONS` (Switch, default: false) - Ações em lote
  - `ENABLE_ADVANCED_FILTERS` (Switch, default: false) - Filtros avançados

**Testes:**
- [ ] `test_config_get_endpoint` - Leitura com permissão correta
- [ ] `test_config_put_endpoint` - Edição com validação
- [ ] `test_config_rbac` - Apenas DAT/Superintendência tem acesso
- [ ] `test_config_validation` - Ranges e tipos corretos
- [ ] `test_config_audit_log` - AuditLog criado ao salvar

#### Entregáveis
- ✅ Superintendência/DAT ajustam RD-04 (buffer) e RD-05 (limite) sem restart
- ✅ Histórico de mudanças via AuditLog
- ✅ UI intuitiva (ISO 9241-110)

---

### ✅ Fase 2: UI para Deslocamentos (CRUD Completo) — CONCLUÍDA
**Esforço estimado:** 16-20h
**Prioridade:** 🔴 Alta (gap funcional crítico)
**Issue:** #188
**PR:** #193
**Data conclusão:** 2025-01-19

#### Motivação
- **Gap funcional**: Planilha original tem CRUD manual de deslocamentos, sistema só tem ETL
- Coordenadores atualmente preenchem deslocamentos na planilha e importam via ETL
- Fluxo deve ser 100% dentro do sistema

#### Escopo

**Backend:**
- [x] Endpoint `GET /api/deslocamentos/` - Lista com filtros
  - Query params: `usuario_id`, `data_inicio`, `data_fim`, `origem`, `destino`
  - Ordenação: `-start_date`
  - Permissão: `IsControleOrDAT`
  - Paginação: 50 itens/página

- [x] Endpoint `POST /api/deslocamentos/` - Criação
  - Validação: `start_date < end_date`
  - Validação: `origem != destino`
  - AuditLog automático com IP e user agent
  - Serializer: `DeslocamentoSerializer`

- [x] Endpoint `PUT /api/deslocamentos/{id}/` - Edição
  - Tracking de campos alterados (prev/new values)
  - AuditLog com details estruturado

- [x] Endpoint `DELETE /api/deslocamentos/{id}/` - Deleção
  - AuditLog com snapshot dos dados deletados

**Frontend:**
- [x] Página `/deslocamentos` (DeslocamentosPage.jsx, 527 linhas)
  - Permissão: Controle + Coordenador + DAT (RBAC)
  - Layout: Tabela Ant Design com filtros e modal

- [x] Tabela com filtros avançados
  - Colunas: Formador, Origem, Destino, Data Início, Data Fim, Observação, Ações
  - Filtros: Usuario (Select search), Data Range (RangePicker), Origem/Destino (Input)
  - Ações: Editar (modal), Deletar (Popconfirm)
  - Paginação: 50/página
  - Observação: Truncada com tooltip

- [x] Modal CRUD (Create/Edit)
  - Campos: Formador (select searchable), Origem (input), Destino (input), Datas (DatePicker), Observação (TextArea)
  - Validação: fim > início, origem != destino, max lengths
  - Submit: POST ou PUT conforme modalMode

**Testes:**
- [x] `test_deslocamento_list` - 7 cenários de filtros (usuario, datas, origem, destino)
- [x] `test_deslocamento_create` - Criação + validação AuditLog
- [x] `test_deslocamento_update` - Edição + tracking de changed_fields
- [x] `test_deslocamento_delete` - Deleção + AuditLog snapshot
- [x] `test_deslocamento_validation` - 2 casos de erro (datas, origem==destino)
- [x] `test_deslocamento_rbac` - 3 cenários de permissão (200/403)
- ✅ **6/6 testes passando**

#### Entregáveis
- ✅ Coordenadores criam deslocamentos direto no sistema
- ✅ CRUD completo via `/deslocamentos` (lista, criar, editar, deletar)
- ✅ Filtros avançados (usuario, datas, origem, destino)
- ✅ AuditLog completo (CREATE/UPDATE/DELETE)
- ✅ RBAC implementado (IsControleOrDAT)
- ✅ Frontend com UX conforme ISO 9241-110
- ✅ CI verde (build/lint + tests)

#### Arquivos Criados/Modificados
**Backend (4 arquivos):**
- `v2/backend/apps/core/serializers.py` - DeslocamentoSerializer (50 linhas)
- `v2/backend/apps/core/views_deslocamento.py` - DeslocamentoViewSet (266 linhas)
- `v2/backend/apps/core/urls.py` - Registro do router
- `v2/backend/apps/core/tests/test_deslocamento_api.py` - 6 testes (381 linhas)

**Frontend (2 arquivos):**
- `v2/frontend/src/pages/Deslocamentos/DeslocamentosPage.jsx` - Página completa (527 linhas)
- `v2/frontend/src/App.jsx` - Menu item + rota RBAC

---

### ✅ Fase 3: Endpoints de Desempenho da Equipe
**Esforço estimado:** 8-12h
**Prioridade:** 🟡 Média (métricas de negócio)
**Issue:** #189
**Status:** ✅ **COMPLETA** (2025-11-19)
**PR:** #XXX

#### Motivação
- Sistema tem métricas técnicas (Prometheus: requests, latência, cache) mas **falta métricas de negócio**
- Gestão precisa de KPIs: eventos criados/dia, taxa de aprovação, tempo médio de aprovação, ranking de formadores
- Endpoints validam cálculos antes de construir dashboard React

#### Escopo

**Backend:**
- [x] Endpoint `GET /api/metrics/team/productivity/`
  - Query params: `days` (default: 7)
  - Retorna:
    ```json
    {
      "period": "7d",
      "events_created": 120,
      "events_approved": 95,
      "events_rejected": 10,
      "approval_rate": 79.17,
      "avg_approval_time_hours": 18.5,
      "gcal_published": 85,
      "gcal_error_rate": 5.26
    }
    ```
  - Cálculos:
    - `approval_rate = aprovados / total * 100`
    - `avg_approval_time_hours = avg(updated_at - created_at).total_seconds() / 3600`
    - `gcal_error_rate = erros / aprovados * 100`
  - Permissão: `IsControle | IsGerencia`

- [x] Endpoint `GET /api/metrics/team/formadores/`
  - Query params: `days` (default: 30)
  - Retorna:
    ```json
    {
      "period": "30d",
      "formadores": [
        {
          "id": 1,
          "nome": "João Silva",
          "eventos": 45,
          "horas_trabalhadas": 180.0,
          "municipios_atendidos": 12
        },
        ...
      ]
    }
    ```
  - Cálculos:
    - Aggregar `Participation` por `usuario`
    - `horas_trabalhadas = sum(fim - inicio).total_seconds() / 3600`
    - `municipios_atendidos = count(distinct municipio_id)`
  - Ordenação: `-eventos` (top 10)
  - Permissão: `IsControle | IsGerencia`

- [x] Endpoint `GET /api/metrics/team/quality/`
  - Query params: `days` (default: 30)
  - Retorna:
    ```json
    {
      "period": "30d",
      "rejection_rate": 8.3,
      "conflict_rate": 5.2,
      "rework_rate": 12.1,
      "avg_approval_time_hours": 18.5,
      "avg_publish_time_minutes": 3.2
    }
    ```
  - Cálculos:
    - `rejection_rate = reprovados / total * 100`
    - `conflict_rate = solicitações com conflitos detectados / total * 100`
    - `rework_rate = solicitações editadas após criação / total * 100`
    - `avg_publish_time_minutes = avg(gcal_last_sync_at - updated_at).total_seconds() / 60`
  - Permissão: `IsControle | IsGerencia`

**Testes:**
- [x] `test_metrics_productivity` - Cálculos corretos
- [x] `test_metrics_formadores` - Ranking top 10
- [x] `test_metrics_quality` - KPIs de qualidade
- [x] `test_metrics_rbac` - Permissões corretas

#### Entregáveis
- ✅ Métricas de negócio expostas via REST
- ✅ Grafana pode consumir endpoints (dashboard opcional)
- ✅ Base para dashboard React (Fase 4)

#### Resultado da Implementação
**Data de conclusão:** 2025-11-19
**Arquivos criados/modificados:**
- `v2/backend/apps/core/permissions.py` (+41 linhas): `IsControle`, `IsGerencia`
- `v2/backend/apps/core/views_metrics.py` (+415 linhas): 3 endpoints de métricas
- `v2/backend/apps/core/urls.py` (+4 linhas): Rotas `/api/metrics/team/*`
- `v2/backend/apps/core/tests/test_metrics_api.py` (+774 linhas): 13 testes completos

**Testes:** 13/13 passando (100% cobertura)
- 3 testes de produtividade (cálculos, empty dataset, custom days)
- 3 testes de ranking de formadores (ranking, top 10, exclusão de convidados)
- 2 testes de qualidade (KPIs, empty dataset)
- 5 testes de RBAC (Controle/Gerência allowed, Formador/Coordenador forbidden, anonymous forbidden)

**Total de código:** 1,234 linhas adicionadas

---

### ✅ Fase 4: Dashboard React - Desempenho da Equipe (Opcional)
**Esforço estimado:** 8-10h
**Prioridade:** 🟢 Baixa (opcional, Grafana já pode consumir)
**Issue:** #XXX

#### Motivação
- Endpoints da Fase 3 estão prontos, mas gestão pode preferir UI integrada ao sistema
- Dashboard React oferece UX melhor para não-técnicos vs Grafana
- Export CSV facilitado

#### Escopo

**Frontend:**
- [ ] Página `/dashboards/equipe` (pages/Dashboards/EquipeDashboardPage.jsx)
  - Permissão: Controle + Gerência (RBAC)
  - Layout: Cards + Gráficos

- [ ] Seção "Produtividade" (GET /api/metrics/team/productivity/)
  - Cards `Statistic`: Eventos Criados, Taxa Aprovação, Tempo Médio Aprovação, Taxa Erro GCal
  - TimeSeries (ultimos 30 dias): Eventos criados/aprovados/reprovados
  - Range picker: 7d, 15d, 30d, custom

- [ ] Seção "Ranking de Formadores" (GET /api/metrics/team/formadores/)
  - Bar Chart horizontal: Top 10 formadores por eventos
  - Tabela: Nome, Eventos, Horas, Municípios
  - Export CSV

- [ ] Seção "Qualidade do Processo" (GET /api/metrics/team/quality/)
  - Cards `Statistic` com thresholds:
    - Taxa Rejeição (meta: < 10%) - verde/vermelho
    - Conflitos (meta: < 5%) - verde/vermelho
    - Re-trabalho (meta: < 15%) - verde/vermelho
  - Gauge: Tempo aprovação (meta: < 24h)

**Testes (opcional):**
- [ ] `test_dashboard_equipe_render` - Componentes renderizam
- [ ] `test_dashboard_equipe_rbac` - Permissões corretas

#### Entregáveis
- ✅ Dashboard visual integrado ao sistema
- ✅ Export CSV de métricas
- ✅ Thresholds visuais (verde/vermelho)

---

## 📅 Cronograma Sugerido

| Fase | Esforço | Quando | Status | Issue | PR |
|------|---------|--------|--------|-------|-----|
| 1. Configurações | 8-12h | Semana 1 | ⏳ Planejado | #XXX | - |
| 2. UI Deslocamentos | 16-20h | Semana 2-3 | ⏳ Planejado | #XXX | - |
| 3. Endpoints Métricas | 8-12h | Semana 4 | ⏳ Planejado | #XXX | - |
| 4. Dashboard React | 8-10h | (opcional) | 🟢 Opcional | #XXX | - |

**Total estimado:** 32-44h (sem dashboard React) ou 40-54h (completo)

---

## 🔍 Gaps Funcionais Descobertos (Análise Planilhas)

### 1. UI para Deslocamentos 🔴 ALTA PRIORIDADE
**Status:** ⏳ Planejado (Fase 2)
**Problema:** Planilha tem CRUD manual, sistema só tem ETL
**Impacto:** Coordenadores ainda dependem da planilha
**Solução:** CRUD completo + calendário visual

### 2. Relacionamento Coordenador ↔ Município 🟡 MÉDIA PRIORIDADE
**Status:** 🔴 Não implementado
**Problema:** Planilha tem vínculo explícito, sistema não modela
**Impacto:** Sem rastreamento de quais coordenadores atendem quais municípios
**Solução proposta:**
```python
# v2/backend/apps/core/models.py
class CoordMunicipioAssignment(models.Model):
    coordenador = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    municipio = models.ForeignKey(Municipio, on_delete=models.CASCADE)
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('coordenador', 'municipio')
```

### 3. Relatórios Avançados 🟡 MÉDIA PRIORIDADE
**Status:** 🟡 Parcialmente implementado
**Problema:** Faltam relatórios detalhados (eventos por formador/coordenador, conflitos, deslocamentos)
**Solução proposta:**
- Endpoint `GET /api/reports/events-by-formador/`
- Endpoint `GET /api/reports/events-by-coordenador/`
- Endpoint `GET /api/reports/conflicts-detected/`
- Endpoint `GET /api/reports/travel-summary/`
- Export CSV em todos

---

## 🎯 Metas e KPIs

### Indicadores de Sucesso (Após Fase 1-3)

**Adoção:**
- [ ] 100% dos ajustes de configuração feitos via UI (não Django Admin)
- [ ] 100% dos deslocamentos criados via sistema (não planilha)
- [ ] Dashboard de métricas acessado 5+ vezes/semana

**Qualidade:**
- [ ] Taxa de rejeição < 10%
- [ ] Conflitos ao criar < 5%
- [ ] Re-trabalho < 15%
- [ ] Tempo aprovação < 24h
- [ ] Tempo publicação GCal < 5 min

**Performance:**
- [ ] Endpoints `/api/metrics/*` respondem < 500ms (P95)
- [ ] Página `/admin/configuracoes` carrega < 2s
- [ ] Página `/deslocamentos` carrega < 2s

---

## 📝 Checklist de Implementação

### Fase 1: Configurações ✅
- [ ] Backend
  - [ ] Serializer `ConfigSerializer`
  - [ ] Endpoint `GET /api/config/`
  - [ ] Endpoint `PUT /api/config/`
  - [ ] Testes unitários (5 testes)
- [ ] Frontend
  - [ ] Página `/admin/configuracoes`
  - [ ] Tab Disponibilidade
  - [ ] Tab Google Calendar
  - [ ] Tab Sessões
  - [ ] Tab Features
- [ ] Documentação
  - [ ] Atualizar CLAUDE.md
  - [ ] Atualizar README

### Fase 2: UI Deslocamentos ✅
- [ ] Backend
  - [ ] Verificar endpoints existentes
  - [ ] Implementar CRUD se necessário
  - [ ] Testes unitários (4 testes)
- [ ] Frontend
  - [ ] Página `/deslocamentos`
  - [ ] Componente `DeslocamentosTable`
  - [ ] Componente `DeslocamentoCalendar`
  - [ ] Modal `DeslocamentoModal`
  - [ ] Export CSV
- [ ] Documentação
  - [ ] Atualizar CLAUDE.md
  - [ ] Guia do usuário

### Fase 3: Endpoints Métricas ✅
- [ ] Backend
  - [ ] Endpoint `productivity`
  - [ ] Endpoint `formadores`
  - [ ] Endpoint `quality`
  - [ ] Testes unitários (4 testes)
- [ ] Documentação
  - [ ] API docs (Swagger)
  - [ ] Atualizar CLAUDE.md

### Fase 4: Dashboard React (Opcional) ✅
- [ ] Frontend
  - [ ] Página `/dashboards/equipe`
  - [ ] Seção Produtividade
  - [ ] Seção Ranking
  - [ ] Seção Qualidade
  - [ ] Export CSV
- [ ] Documentação
  - [ ] Guia do usuário

---

## 📚 Referências

### Models Django
- `Config` (v2/backend/apps/core/models.py:573-624)
- `Solicitacao` (v2/backend/apps/core/models.py:92-436)
- `Participation` (v2/backend/apps/core/models.py:443-511)
- `AvailabilityBlock` (v2/backend/apps/core/models.py:513-569)
- `Deslocamento` (v2/backend/apps/core/models.py)
- `AuditLog` (v2/backend/apps/core/models.py)

### Regras de Negócio
- RD-01 a RD-08 (Regras de Disponibilidade) - `.claude/CLAUDE.md`
- PA-01 a PA-07 (Política de Aprovação) - `.claude/CLAUDE.md`
- CP-01 a CP-06 (Cláusulas Pétreas) - `.claude/CLAUDE.md`

### Observabilidade
- MP1 (Prometheus + Grafana) - Issue #165, merged
- MP2 (Structured Logging) - Issue #166, PR #182 merged
- MP3 (Sentry APM) - Issue #167, merged

---

## 🚀 Próxima Ação

**Status atual:** ⏳ Criação de issues no GitHub

**Próximos passos:**
1. ✅ Criar arquivo PLANO_MELHORIAS_DETALHADO.md
2. ⏳ Criar Issue #1: UI para Configurações do Sistema
3. ⏳ Criar Issue #2: CRUD completo UI Deslocamentos
4. ⏳ Criar Issue #3: Endpoints de desempenho da equipe
5. ⏳ Criar Issue #4: Dashboard React /dashboards/equipe
6. ⏳ Começar implementação Fase 1

---

**Última atualização:** 2025-01-19
**Autor:** Claude Code + Usuário
**Revisão:** Pendente
