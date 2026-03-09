# Relatorio Tecnico de Arquitetura e Escalabilidade

Data: 2026-03-06
Escopo analisado: codigo implementado em `v2/backend`, `v2/frontend`, `v2/infra`.
Objetivo: avaliar fundamentos, arquitetura de codigo, escalabilidade, trade-offs e consistencia.

## 1. Resumo Executivo

O sistema ja possui uma base tecnica madura para operacao em producao: Django/DRF com Postgres e Redis, Celery para processamento assincrono, controle de seguranca no middleware, healthchecks, throttling e pipelines de CI.

Os riscos principais estao em 3 eixos:
1. Drift arquitetural e de regras de negocio em partes criticas (Solicitacoes).
2. Gargalos de performance por processamento sincrono e loops Python em caminhos de alto volume.
3. Divida de manutenibilidade no frontend (arquivos muito grandes, tipagem frouxa e clients HTTP duplicados).

A recomendacao e executar um plano em fases com foco primeiro em corretude e throughput, depois em reducao de latencia e finalmente em alta disponibilidade com replicacao controlada.

## 2. Pontos Fortes Confirmados no Codigo

### 2.1 Fundamentos e eficiencia computacional
- Uso de `transaction.atomic` e `select_for_update` em fluxos de aprovacao concorrentes em `apps/core/services/solicitacao_approval.py`.
- Modelagem de banco com `indexes` e `constraints` no dominio de solicitacoes em `apps/core/models/solicitacao.py`.
- Throttling por escopo para endpoints pesados em `config/settings.py`.

### 2.2 Arquitetura de codigo
- Presenca de camada de servicos em fluxos criticos (aprovacao/publicacao GCal).
- Uso de factory para cliente Google Calendar em `apps/core/services/gcal_client_factory.py`.
- Injeccao de comportamento fake/real para GCal ja prevista no desenho.

### 2.3 Design de sistema e escalabilidade
- Processamento assincrono com Celery em `apps/core/tasks.py` para operacoes de Google Calendar.
- Cache Redis para disponibilidade e sessoes.
- Health endpoints com verificacao de DB, Redis e estado de circuit breaker em `config/urls.py`.

### 2.4 Qualidade operacional
- CI com gates de qualidade e cobertura.
- Logging com `request_id` e padrao estruturado.

## 3. Gaps Criticos e Riscos

### GAP-01 (Critico): Drift de arquitetura no modulo de Solicitacoes
- Evidencia: coexistencia de `views_solicitacao.py` e `views/solicitacao.py`, com import ativo em `apps/core/urls.py` apontando para `views_solicitacao.py`.
- Risco: mudancas parciais gerando comportamentos divergentes e regressao silenciosa.

### GAP-02 (Critico): Regra de autoaprovacao implementada no model
- Evidencia: autoaprovacao de projetos `NAO_SUPER` no `save()` em `apps/core/models/solicitacao.py`.
- Risco: regra de negocio embutida em camada de persistencia, mais dificil de testar e auditar por fluxo.

### GAP-03 (Alto): Ineficiencia em lotes de aprovacao/reprovacao
- Evidencia: consultas por ID dentro de loop (`filter(id=sol_id).first()`) em lote.
- Risco: N+1 sob carga e aumento de latencia linear com tamanho do lote.

### GAP-04 (Critico): Imports/ETL pesados ainda sincronos
- Evidencia: upload + parse pandas + persistencia no request thread em `views_imports.py`, `views_import_produtos.py`, `services/produtos_import.py`.
- Risco: timeout, queda de throughput e bloqueio de workers web.

### GAP-05 (Alto): Motor de grade mensal com loops Python intensivos
- Evidencia: loops por eventos, bloqueios e dias em `services/monthly_grid_service.py`.
- Risco: custo alto em cenarios com muitos usuarios/eventos.

### GAP-06 (Alto): Circuit breaker GCal nao acoplado ao fluxo principal
- Evidencia: `_retry_with_circuit_breaker` definido em `services/gcal/utils.py`, sem uso no fluxo principal.
- Risco: rajadas de retry em indisponibilidade externa.

### GAP-07 (Alto): Invalidador de cache amplo
- Evidencia: invalidacao por padrao `availability_check:*` em `utils/cache_utils.py`.
- Risco: baixa taxa de hit e risco de cache stampede.

### GAP-08 (Alto): Endpoints de metricas/relatorios com queries repetidas
- Evidencia: contagens por semana em loop e acessos por ID em loop em views de metricas/relatorios.
- Risco: latencia crescente com volume historico.

### GAP-09 (Alto): Frontend com baixa coesao em telas criticas
- Evidencia: `App.tsx` (869 linhas), `MapaBrasilPage.tsx` (975), `GCalDashboardPage.tsx` (803).
- Risco: custo alto de evolucao e regressao funcional.

### GAP-10 (Alto): Uso excessivo de `any` e casts em modulo DAT
- Evidencia: multiplos `as any` e tipos `any` no modulo DAT e disponibilidade.
- Risco: regressao nao detectada em compile-time.

### GAP-11 (Medio): Dois clients HTTP no frontend
- Evidencia: coexistencia de `fetchAPI` e `axios` com comportamentos distintos.
- Risco: inconsistencias de tratamento de erro/retry/CSRF.

### GAP-12 (Medio): Observabilidade incompleta de worker/beat
- Evidencia: targets vazios em `infra/prometheus.yml` para `django_worker` e `django_beat`.
- Risco: falhas assincronas sem visibilidade.

### GAP-13 (Critico): Escalabilidade horizontal parcial e SPOF
- Evidencia: `docker-compose.yml` com DB e Redis single instance e sem LB dedicado na topologia base.
- Risco: indisponibilidade por ponto unico de falha.

### GAP-14 (Critico): Replicacao sem estrategia de consistencia explicita
- Evidencia: ausencia de politica formal read-after-write/read-replica por endpoint.
- Risco: leitura desatualizada apos escrita (eventual consistency sem controle).

## 4. Trade-offs Principais

### 4.1 Simplicidade vs robustez
- Solucoes simples (unificar viewsets, mover ETL para Celery, reduzir `any`) geram alto retorno rapido.
- Solucoes de HA total (replica, failover automatico, roteamento de leitura) aumentam complexidade operacional.

### 4.2 Consistencia forte vs escala de leitura
- Ler sempre do primario garante consistencia, mas limita escala.
- Ler de replicas melhora escala, mas exige controle de lag, politicas read-your-writes e aceitacao de eventual consistency.

### 4.3 Cache agressivo vs frescor
- TTL longo melhora desempenho.
- TTL curto e invalidacao granular melhoram consistencia.
- Escolha deve ser por caso de uso e SLA funcional.

## 5. Plano de Evolucao (macro)

### Fase 1 - Corretude e throughput baseline
- Canonicalizar Solicitacoes.
- Corrigir N+1 de lotes e endpoints pesados de metricas.
- Integrar circuit breaker no fluxo GCal.

### Fase 2 - Tirar processamento pesado da thread web
- Migrar imports para pipeline assincrono com job status.
- Melhorar cache e engine da grade mensal.

### Fase 3 - Manutenibilidade frontend
- Unificar API client.
- Quebrar telas monoliticas em feature slices.
- Endurecer tipagem TypeScript.

### Fase 4 - Observabilidade e guard rails
- Instrumentar worker/beat e filas.
- Adicionar testes/perf budgets em CI.

### Fase 5 - Escala horizontal e consistencia operacional
- Introduzir topologia com multiplas replicas web/worker.
- Definir e implementar estrategia de replicacao Postgres com politicas por endpoint.

## 6. Referencias Externas Oficiais Utilizadas

- Django QuerySet optimization (`select_related`, `prefetch_related`): https://docs.djangoproject.com/en/5.1/ref/models/querysets/
- Django database optimization: https://docs.djangoproject.com/en/3.0/topics/db/optimization/
- Django cache framework: https://docs.djangoproject.com/en/6.0/topics/cache/
- Django sessions (cache backend considerations): https://docs.djangoproject.com/en/5.1/topics/http/sessions/
- Celery task retries (`autoretry_for`, `retry_backoff`, `retry_jitter`): https://docs.celeryq.dev/en/v5.1.2/userguide/tasks.html
- Celery worker optimization (`worker_prefetch_multiplier`, `task_acks_late`): https://docs.celeryq.dev/en/4.4.2/userguide/optimizing.html
- PostgreSQL warm standby and synchronous replication: https://www.postgresql.org/docs/current/warm-standby.html
- PostgreSQL replication monitoring (`pg_stat_replication`): https://www.postgresql.org/docs/current/monitoring-stats.html
- Redis SCAN command (iteracao incremental, evitando KEYS em cargas grandes): https://redis.io/docs/latest/commands/scan/
- Prometheus metric naming and cardinality: https://prometheus.io/docs/practices/naming/
- Prometheus scrape configuration: https://prometheus.io/docs/prometheus/latest/configuration/configuration/
- Google Calendar API quota guide: https://developers.google.com/calendar/api/guides/quota
- Google Calendar API error handling and backoff: https://developers.google.com/workspace/calendar/api/guides/errors
- Google Calendar events insert (event id semantics): https://developers.google.com/workspace/calendar/api/v3/reference/events/insert
- Cache-aside pattern (arquitetura): https://learn.microsoft.com/en-us/azure/architecture/patterns/cache-aside

## 7. Entregaveis vinculados

- Backlog completo com issues: `v2/docs/reports/BACKLOG_QUALIDADE_SISTEMA_2026-03-06.md`
- Estimativas por fase: `v2/docs/reports/ESTIMATIVAS_PRAZOS_QUALIDADE_2026-03-06.md`
