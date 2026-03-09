# Backlog Completo de Qualidade e Escalabilidade

Data: 2026-03-06
Base: analise do codigo implementado em `v2/`.
Objetivo: resolver de forma completa os gaps de arquitetura, performance e escalabilidade com priorizacao executavel.

## 1. Regras de Execucao do Backlog

- Todas as issues abaixo devem ter DoD (Definition of Done) com codigo, testes, monitoracao e documentacao.
- Nenhuma issue fecha sem evidencias de teste automatizado ou justificativa formal de risco.
- Mudancas de alto impacto devem sair atras de feature flag quando aplicavel.
- Sempre priorizar solucao simples e operacionalmente segura antes de desenho complexo.

## 2. Plano Geral por Fase

| Fase | Objetivo | Issues | Resultado esperado |
|---|---|---|---|
| Fase 1 | Corretude e throughput no core backend | ASQ-001, ASQ-002, ASQ-003, ASQ-006, ASQ-008 | Fluxos criticos estaveis e sem gargalos obvios |
| Fase 2 | Retirar cargas pesadas da thread web | ASQ-005, ASQ-007, ASQ-004 | Latencia menor e maior capacidade sob carga |
| Fase 3 | Sustentabilidade frontend | ASQ-009, ASQ-010, ASQ-011 | Menor risco de regressao e maior velocidade de manutencao |
| Fase 4 | Observabilidade e guard rails | ASQ-012, ASQ-015 | Visibilidade operacional e prevencao de regressao |
| Fase 5 | Alta disponibilidade e consistencia | ASQ-013, ASQ-014 | Escala horizontal real com politica de consistencia controlada |

## 3. Matriz de Cobertura de Gaps

| Gap do relatorio | Issue(s) que resolvem |
|---|---|
| Drift de arquitetura em Solicitacoes | ASQ-001 |
| Regra de autoaprovacao no model | ASQ-002 |
| N+1 em lote de aprovacao | ASQ-003 |
| ETL/import sincrono | ASQ-005 |
| Grade mensal com loops caros | ASQ-004 |
| Circuit breaker nao integrado | ASQ-006 |
| Invalidacao de cache ampla | ASQ-007 |
| Metricas/relatorios com query ineficiente | ASQ-008 |
| Frontend monolitico | ASQ-010 |
| Tipagem frouxa com `any` | ASQ-011 |
| Dois clients HTTP | ASQ-009 |
| Observabilidade worker/beat incompleta | ASQ-012 |
| SPOF e sem LB efetivo | ASQ-013 |
| Replicacao sem estrategia de consistencia | ASQ-014 |
| Falta de guard rails de performance em CI | ASQ-015 |

---

## ASQ-001 - Canonicalizar SolicitacaoViewSet e eliminar drift arquitetural

- Prioridade: P0
- Fase: 1
- Esforco: 3 a 5 dias uteis
- Dono principal: Backend

### Problema
Coexistem implementacoes paralelas de `SolicitacaoViewSet` com regras diferentes, aumentando risco de regressao e inconsistencia.

### Evidencias
- `v2/backend/apps/core/views_solicitacao.py`
- `v2/backend/apps/core/views/solicitacao.py`
- `v2/backend/apps/core/urls.py` (roteamento atual)

### Plano de resolucao
1. Definir implementacao canonica unica para `SolicitacaoViewSet`.
2. Consolidar regras de permissao e filtros em um unico modulo.
3. Desativar imports legados e remover caminhos mortos.
4. Atualizar testes para apontar somente para a rota canonica.
5. Atualizar documentacao de API e arquitetura.

### Testes obrigatorios
- Unit: permissao por action (`create`, `approve`, `reject`, `update`).
- Integration: filtros `mine`, `status`, `flow`, `date_from/date_to`.
- Regression: snapshot de contrato JSON das rotas de Solicitacao.

### Criterios de aceitacao
- Existe apenas um `SolicitacaoViewSet` ativo no roteamento.
- Suite de testes de solicitacoes sem regressao.
- Nenhum import legado residual referenciado em runtime.

### Trade-offs
- Curto prazo: risco de quebrar chamadas internas nao mapeadas.
- Mitigacao: fase de compatibilidade com alias temporario + logs.

### Dependencias
- Nenhuma.

---

## ASQ-002 - Formalizar regra de aprovacao e remover efeito colateral no model

- Prioridade: P0
- Fase: 1
- Esforco: 2 a 4 dias uteis
- Dono principal: Backend + Produto

### Problema
A regra de autoaprovacao `NAO_SUPER` esta no `save()` do model, misturando persistencia e negocio.

### Evidencias
- `v2/backend/apps/core/models/solicitacao.py` (`save` com `projeto.fluxo == "NAO_SUPER"`)

### Plano de resolucao
1. Definir politica oficial de aprovacao com Produto/Negocio.
2. Mover decisao de status inicial para service layer de criacao.
3. Manter model sem regra implicita de workflow.
4. Adicionar auditoria explicita de decisao de status inicial.
5. Criar migration de dados somente se necessario para consistencia historica.

### Testes obrigatorios
- Unit: status inicial por tipo de fluxo (`SUPER`, `NAO_SUPER`).
- Integration: criacao via API com cenarios validos e invalidos.
- Audit: verificacao de log/audit trail da decisao.

### Criterios de aceitacao
- Sem regra de workflow no `save()` do model.
- Status inicial decidido em camada de servico testada.
- Regra alinhada ao documento de negocio vigente.

### Trade-offs
- Retirar logica do model aumenta verbosidade da camada de servico.
- Ganha-se previsibilidade e testabilidade.

### Dependencias
- ASQ-001.

---

## ASQ-003 - Otimizar lote de aprovacao/reprovacao e remover N+1

- Prioridade: P1
- Fase: 1
- Esforco: 2 a 3 dias uteis
- Dono principal: Backend

### Problema
Consulta por ID dentro de loop em batch gera N+1 para itens invalidos/reprocessados.

### Evidencias
- `v2/backend/apps/core/services/solicitacao_approval.py` (trechos com `filter(id=sol_id).first()` no loop)

### Plano de resolucao
1. Substituir consultas por loop por `in_bulk`/mapa em memoria.
2. Processar sucesso/erro por lote sem query individual.
3. Manter lock/atomicidade para itens validos.
4. Instrumentar metricas de tempo por tamanho do lote.

### Testes obrigatorios
- Unit: lote com IDs validos, invalidos e duplicados.
- Performance: benchmark com 100, 500 e 1000 IDs.
- Concurrency: chamadas paralelas no mesmo conjunto de IDs.

### Criterios de aceitacao
- Reducao visivel de query count em lote.
- Tempo de resposta sublinear frente a baseline anterior.
- Sem regressao funcional de mensagens de erro por item.

### Trade-offs
- Mais uso de memoria em lotes muito grandes.
- Mitigacao: chunking de lote configuravel.

### Dependencias
- ASQ-001.

---

## ASQ-004 - Reengenharia simples do motor de grade mensal

- Prioridade: P0
- Fase: 2
- Esforco: 5 a 8 dias uteis
- Dono principal: Backend

### Problema
Motor atual usa multiplos loops Python por evento/bloqueio/dia e tende a degradar com volume.

### Evidencias
- `v2/backend/apps/core/services/monthly_grid_service.py`

### Plano de resolucao
1. Criar baseline de custo atual (tempo e query count).
2. Reduzir loops redundantes com pre-indexacao por dia e usuario.
3. Mover agregacoes possiveis para banco (annotate/grouping).
4. Introduzir cache de resultado por chave de escopo com versao.
5. Manter contrato de resposta atual para evitar quebra de frontend.

### Testes obrigatorios
- Unit: regras de CH, ranking e composicao de cards por dia.
- Integration: comparacao de resposta antiga vs nova em dataset fixture.
- Performance: p95 com cenarios de alta carga sintetica.

### Criterios de aceitacao
- p95 da API mensal reduzido em pelo menos 40% no baseline definido.
- Query count previsivel por faixa de volume.
- Sem divergencia funcional nas regras de negocio validadas.

### Trade-offs
- Codigo mais sofisticado para ganhar performance.
- Mitigacao: comentarios tecnicos curtos e testes de contrato.

### Dependencias
- ASQ-007 (cache versionado melhora resultado final).

---

## ASQ-005 - Migrar imports/ETL para pipeline assincrono com status

- Prioridade: P0
- Fase: 2
- Esforco: 6 a 10 dias uteis
- Dono principal: Backend + Frontend

### Problema
Uploads com pandas rodam no request thread, podendo bloquear web workers.

### Evidencias
- `v2/backend/apps/core/views_imports.py`
- `v2/backend/apps/core/views_import_produtos.py`
- `v2/backend/apps/core/services/produtos_import.py`

### Plano de resolucao
1. Criar modelo de `ImportJob` com estado (`queued`, `running`, `done`, `failed`).
2. Endpoint de upload apenas grava arquivo e enfileira task.
3. Worker Celery processa arquivo em chunks com idempotencia por hash.
4. Endpoint de status e detalhes de erro por linha.
5. Ajustar frontend para polling de status e exibicao de resultado.

### Testes obrigatorios
- Unit: parser e validacoes por tipo de arquivo.
- Integration: fluxo upload -> queue -> processamento -> resultado.
- Resilience: retry de falha transiente sem duplicar registros.
- Security: validacao de tamanho/extensao/mimetype do upload.

### Criterios de aceitacao
- Nenhum processamento pesado de import no request thread.
- Usuario consegue acompanhar status fim a fim.
- Reprocessamento do mesmo arquivo nao duplica dados (idempotencia).

### Trade-offs
- Fluxo deixa de ser imediatista e passa a eventual.
- Mitigacao: UX clara de progresso e notificacao de fim.

### Dependencias
- Infra Celery estavel.

---

## ASQ-006 - Integrar circuit breaker no fluxo real de Google Calendar

- Prioridade: P1
- Fase: 1
- Esforco: 2 a 4 dias uteis
- Dono principal: Backend

### Problema
Circuit breaker existe mas nao esta acoplado ao caminho principal de sync.

### Evidencias
- `v2/backend/apps/core/services/gcal/utils.py` (`_retry_with_circuit_breaker` sem uso externo)

### Plano de resolucao
1. Encapsular chamadas GCal com wrapper padrao de retry + breaker.
2. Parametrizar `max_retries`, backoff e janela do breaker por env var.
3. Expor metricas de estado do breaker e taxa de erro.
4. Evitar retry em erros nao transientes.

### Testes obrigatorios
- Unit: transicao CLOSED -> OPEN -> HALF_OPEN -> CLOSED.
- Integration: simular 429/503 e validar throttling de chamadas.
- Observability: assert de metricas e logs estruturados.

### Criterios de aceitacao
- 100% das chamadas GCal criticas passam pelo wrapper padrao.
- Em indisponibilidade externa, sistema evita tempestade de retries.
- Dashboard de operacao mostra estado do breaker.

### Trade-offs
- Pode aumentar falha rapida durante janela OPEN.
- Beneficio: protege infraestrutura e evita cascata.

### Dependencias
- Nenhuma.

---

## ASQ-007 - Granularizar invalidacao de cache availability (cache-aside)

- Prioridade: P1
- Fase: 2
- Esforco: 3 a 5 dias uteis
- Dono principal: Backend

### Problema
Invalidacao global `availability_check:*` derruba hit ratio e pode causar stampede.

### Evidencias
- `v2/backend/apps/core/utils/cache_utils.py`
- `v2/backend/apps/core/signals.py`

### Plano de resolucao
1. Introduzir chave versionada por escopo (usuario/projeto/mes).
2. Invalidar somente escopo afetado em signals.
3. Aplicar jitter no TTL para evitar expiracao simultanea.
4. Substituir uso de `keys` por estrategia incremental segura quando necessario.

### Testes obrigatorios
- Unit: composicao de chave e versao.
- Integration: mudanca em solicitacao invalida somente chaves relevantes.
- Load: validar melhoria de cache hit ratio em workload repetitivo.

### Criterios de aceitacao
- Invalidacao global removida do caminho principal.
- Hit ratio aumenta no minimo 20% no endpoint de availability.
- Sem retorno stale apos alteracoes criticas dentro do SLA definido.

### Trade-offs
- Estrategia de chave mais complexa do que wildcard simples.
- Beneficio: cache mais eficiente e previsivel.

### Dependencias
- Nenhuma.

---

## ASQ-008 - Otimizar metricas e relatorios com agregacao SQL

- Prioridade: P1
- Fase: 1
- Esforco: 4 a 6 dias uteis
- Dono principal: Backend

### Problema
Alguns endpoints fazem loops com contagens repetidas e queries por item.

### Evidencias
- `v2/backend/apps/core/views_reports.py`
- `v2/backend/apps/core/views/metrics/formador_metrics.py`
- `v2/backend/apps/core/views/metrics/dashboard_metrics.py`

### Plano de resolucao
1. Reescrever `weekly_approved` com agregacao por semana em query unica.
2. Eliminar lookup por usuario dentro de loop (`select_related`/join).
3. Trocar materializacao desnecessaria de listas por `count()` no banco.
4. Revisar semantica temporal (`created_at` vs data de evento) e padronizar.

### Testes obrigatorios
- Unit: consistencia das agregacoes por periodo.
- Integration: contratos JSON e filtros por data.
- Performance: comparativo de latencia e query count antes/depois.

### Criterios de aceitacao
- Queda de query count e latencia nos endpoints alvo.
- Sem divergencia de valor agregado validado por fixtures.
- Semantica temporal documentada e coberta por testes.

### Trade-offs
- Queries SQL mais elaboradas sao menos triviais para leitura.
- Mitigacao: encapsular em funcoes de repositorio com testes.

### Dependencias
- Nenhuma.

---

## ASQ-009 - Unificar cliente HTTP frontend

- Prioridade: P1
- Fase: 3
- Esforco: 3 a 5 dias uteis
- Dono principal: Frontend

### Problema
Convivencia de `fetchAPI` e `axios` gera inconsistencias de erro/retry/CSRF.

### Evidencias
- `v2/frontend/src/api/config.ts`
- `v2/frontend/src/api.ts`
- `v2/frontend/src/api/*.ts` (uso misto)

### Plano de resolucao
1. Definir client oficial unico (recomendado: manter um wrapper padronizado).
2. Migrar modulos por dominio com adaptador de compatibilidade temporario.
3. Padronizar contrato de erro e mensagens para UI.
4. Remover client legado apos cobertura completa.

### Testes obrigatorios
- Unit: tratamento de 401/403/429/500 e CSRF refresh.
- Integration (frontend): chamadas principais por dominio (Solicitacoes, DAT, GCal).
- E2E: fluxo de login + chamadas autenticadas.

### Criterios de aceitacao
- 100% das chamadas passam pelo mesmo client.
- Tratamento de erro uniforme entre paginas.
- Sem regressao de autenticacao e CSRF.

### Trade-offs
- Mudanca ampla de imports no frontend.
- Mitigacao: migracao por lotes e feature branch curta.

### Dependencias
- Nenhuma.

---

## ASQ-010 - Refatorar paginas frontend monoliticas em feature slices

- Prioridade: P1
- Fase: 3
- Esforco: 8 a 12 dias uteis
- Dono principal: Frontend

### Problema
Paginas muito extensas dificultam manutencao e introduzem acoplamento alto.

### Evidencias
- `v2/frontend/src/App.tsx`
- `v2/frontend/src/pages/MapaBrasil/MapaBrasilPage.tsx`
- `v2/frontend/src/pages/Dashboards/GCalDashboardPage.tsx`

### Plano de resolucao
1. Extrair hooks de dados e estado por responsabilidade.
2. Extrair componentes puros para blocos de UI grandes.
3. Isolar regras de RBAC e navegacao em camada dedicada.
4. Criar limite de tamanho por arquivo para novas PRs (guard rail de manutencao).

### Testes obrigatorios
- Unit: hooks extraidos (estado, filtros, memoizacao).
- Component: render e interacoes dos novos blocos.
- E2E: fluxos principais das paginas refatoradas.

### Criterios de aceitacao
- Reducao de tamanho e complexidade ciclomatica nas paginas alvo.
- Cobertura automatizada mantida ou maior.
- Sem regressao visual/funcional relevante.

### Trade-offs
- Refatoracao estrutural pode gerar conflitos de merge.
- Mitigacao: fatiar por pagina e mergear incrementalmente.

### Dependencias
- ASQ-009 recomendado antes.

---

## ASQ-011 - Endurecer tipagem TypeScript (eliminar `any` em caminhos criticos)

- Prioridade: P1
- Fase: 3
- Esforco: 6 a 10 dias uteis
- Dono principal: Frontend

### Problema
Uso frequente de `any` e `as any` reduz seguranca de tipos.

### Evidencias
- `v2/frontend/src/pages/DATModule/*`
- `v2/frontend/src/pages/Disponibilidade/useMonthlyQuery.ts`

### Plano de resolucao
1. Definir contratos tipados de API por dominio.
2. Remover `any` em modulo DAT e disponibilidade mensal.
3. Subir nivel de rigor do `tsconfig` de forma progressiva.
4. Bloquear novo `any` nao justificado via lint rule.

### Testes obrigatorios
- Type tests (build com `tsc --noEmit`).
- Unit: mapeamento de payloads para types.
- Integration: render com dados reais mockados por contrato.

### Criterios de aceitacao
- Reducao minima de 80% dos `any` nos modulos alvo.
- Build falha para novo `any` sem excecao aprovada.
- Sem regressao funcional nas telas DAT/disponibilidade.

### Trade-offs
- Mais tempo inicial para modelar tipos.
- Beneficio: menos bugs de runtime e manutencao mais rapida.

### Dependencias
- ASQ-009 recomendado para consolidar contratos.

---

## ASQ-012 - Completar observabilidade de worker/beat e filas

- Prioridade: P2
- Fase: 4
- Esforco: 3 a 5 dias uteis
- Dono principal: DevOps + Backend

### Problema
Prometheus nao coleta worker/beat por targets vazios, reduzindo visibilidade operacional.

### Evidencias
- `v2/infra/prometheus.yml` (`django_worker` e `django_beat` com `targets: []`)

### Plano de resolucao
1. Expor metricas de Celery (exporter/flower metric endpoint).
2. Preencher scrape targets de worker/beat.
3. Criar painel com fila, retries, falhas e tempo de execucao.
4. Criar alertas minimos (fila travada, taxa de erro alta, retry storm).

### Testes obrigatorios
- Smoke: endpoint de metricas respondendo.
- Integration ops: Prometheus scrape validado.
- Chaos leve: desligar worker e validar alertas.

### Criterios de aceitacao
- Worker e beat monitorados em dashboard unico.
- Alertas operacionais ativos e testados.
- MTTR reduzido em incidente simulado.

### Trade-offs
- Mais telemetria pode aumentar volume de metricas.
- Mitigacao: controlar cardinalidade e retencao.

### Dependencias
- Nenhuma.

---

## ASQ-013 - Escala horizontal real para app e fila com balanceamento

- Prioridade: P0
- Fase: 5
- Esforco: 6 a 10 dias uteis
- Dono principal: DevOps + Backend

### Problema
Topologia atual base ainda tem SPOF e nao formaliza escalonamento de replicas web/worker.

### Evidencias
- `v2/infra/docker-compose.yml`
- `v2/infra/docker-compose.prod.yml`

### Plano de resolucao
1. Definir topologia alvo com LB para web e escalonamento de workers.
2. Garantir armazenamento de sessao compartilhado e stateless web nodes.
3. Configurar healthcheck/readiness por instancia.
4. Validar deploy rolling sem downtime percebido.

### Testes obrigatorios
- Load test com N replicas de web e worker.
- Failover test de instancia web.
- Soak test de 4h com carga realista.

### Criterios de aceitacao
- Escala horizontal funcional com ganho de throughput comprovado.
- Falha de uma instancia nao derruba servico.
- Deploy rolling sem interrupcao relevante.

### Trade-offs
- Aumenta custo de infraestrutura e operacao.
- Beneficio: resiliencia e capacidade de crescimento.

### Dependencias
- ASQ-012 recomendado para observabilidade.

---

## ASQ-014 - Estrategia de replicacao Postgres e consistencia eventual por endpoint

- Prioridade: P0
- Fase: 5
- Esforco: 5 a 8 dias uteis
- Dono principal: Backend + DevOps

### Problema
Replicacao sem politica explicita de consistencia pode gerar leituras desatualizadas apos escrita.

### Evidencias
- Ausencia de politica formal de roteamento leitura/escrita no codigo atual.

### Plano de resolucao
1. Classificar endpoints em consistencia forte vs eventual.
2. Implementar roteador de leitura com regra read-your-writes (janela temporal no primario).
3. Monitorar lag da replica e fallback para primario acima de limiar.
4. Documentar limites de consistencia por endpoint para produto/suporte.
5. Revisar `synchronous_commit` conforme SLA (nao forcar onde nao precisa).

### Testes obrigatorios
- Integration: fluxo escreve e le imediatamente (forte) sem staleness.
- Integration: endpoints eventuais aceitam pequena defasagem sem quebrar UX.
- Fault test: replica com lag alto aciona fallback.

### Criterios de aceitacao
- Politica de consistencia formal e implementada.
- Sem bugs read-after-write em fluxos criticos.
- Dashboards mostram lag e taxa de fallback.

### Trade-offs
- Mais leitura no primario em janelas criticas.
- Menor risco funcional em fluxos sensiveis.

### Dependencias
- ASQ-013.

---

## ASQ-015 - Guard rails de performance e regressao em CI/CD

- Prioridade: P1
- Fase: 4
- Esforco: 4 a 6 dias uteis
- Dono principal: Backend + Frontend + QA

### Problema
Sem gates fortes de performance nos endpoints/paginas mais sensiveis, regressao pode voltar.

### Evidencias
- CI atual cobre testes funcionais, mas sem budget de latencia/query count para todos os hotspots identificados.

### Plano de resolucao
1. Definir SLO tecnico por endpoint critico (p95, query count maximo).
2. Adicionar testes de regressao de query count no backend.
3. Adicionar smoke de performance frontend para telas chave.
4. Bloquear merge quando budget critico for violado.
5. Criar runbook de resposta a regressao.

### Testes obrigatorios
- Backend perf regression test.
- Frontend lighthouse/smoke com limite minimo acordado.
- Pipeline CI com falha automatica por regressao critica.

### Criterios de aceitacao
- Budgets definidos, publicados e aplicados no CI.
- Regressao critica passa a falhar PR automaticamente.
- Time de suporte/engenharia com runbook validado.

### Trade-offs
- Aumenta tempo de CI.
- Evita degradacao silenciosa em producao.

### Dependencias
- ASQ-004, ASQ-008, ASQ-010, ASQ-011 (para baseline final).

---

## 4. Referencias Externas Oficiais (base para as solucoes)

- Django QuerySet API: https://docs.djangoproject.com/en/5.1/ref/models/querysets/
- Django DB optimization: https://docs.djangoproject.com/en/3.0/topics/db/optimization/
- Django cache framework: https://docs.djangoproject.com/en/6.0/topics/cache/
- Celery tasks and retries: https://docs.celeryq.dev/en/v5.1.2/userguide/tasks.html
- Celery worker optimization: https://docs.celeryq.dev/en/4.4.2/userguide/optimizing.html
- PostgreSQL warm standby and replication: https://www.postgresql.org/docs/current/warm-standby.html
- PostgreSQL monitoring stats (`pg_stat_replication`): https://www.postgresql.org/docs/current/monitoring-stats.html
- Redis SCAN command: https://redis.io/docs/latest/commands/scan/
- Prometheus naming practices: https://prometheus.io/docs/practices/naming/
- Prometheus scrape config: https://prometheus.io/docs/prometheus/latest/configuration/configuration/
- Google Calendar quota guide: https://developers.google.com/calendar/api/guides/quota
- Google Calendar error handling: https://developers.google.com/workspace/calendar/api/guides/errors
- Google Calendar events insert: https://developers.google.com/workspace/calendar/api/v3/reference/events/insert
- Cache-aside pattern: https://learn.microsoft.com/en-us/azure/architecture/patterns/cache-aside

## 5. Ordem Recomendada de Execucao

1. ASQ-001
2. ASQ-002
3. ASQ-003
4. ASQ-006
5. ASQ-008
6. ASQ-005
7. ASQ-007
8. ASQ-004
9. ASQ-009
10. ASQ-010
11. ASQ-011
12. ASQ-012
13. ASQ-015
14. ASQ-013
15. ASQ-014

## 6. Entregavel Complementar

- Cronograma detalhado por fase e issue: `v2/docs/reports/ESTIMATIVAS_PRAZOS_QUALIDADE_2026-03-06.md`
