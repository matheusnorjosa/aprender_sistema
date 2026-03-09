# Plano Definitivo - API Canonica, Deprecacao de /api/v1 e Documentacao Oficial (2026-03-09)

## 1) Objetivo

Resolver de forma definitiva a ambiguidade entre `/api/` e `/api/v1/`, corrigir a confiabilidade de Swagger/ReDoc, e estabelecer um processo seguro para descontinuar o alias legado sem quebra para integracoes existentes.

## 2) Decisao Arquitetural

- **Canonico oficial**: `/api/*`
- **Alias temporario**: `/api/v1/*` (somente compatibilidade)
- **Politica**: nenhum codigo novo, teste novo, doc nova ou integracao nova pode usar `/api/v1/*`.

Justificativa tecnica:
- frontend first-party, Makefile, healthchecks e testes principais ja usam `/api/*`;
- manter dois prefixos sem governanca aumenta risco de drift e regressao;
- reduzir para um canonico melhora manutencao, onboarding e confiabilidade do contrato.

## 3) Estado Atual Resumido

- Backend expoe os dois prefixos (`/api/` e `/api/v1/`) com paridade.
- Ainda existem referencias remanescentes a `/api/v1/` em:
  - `frontend/public/sw.js`;
  - testes de compatibilidade;
  - comentarios/exemplos pontuais.
- Swagger/ReDoc ja tem endpoint (`/api/docs/`, `/api/redoc/`), mas houve relato de tela em branco no navegador, exigindo hardening com validacao de assets, CSP e teste de renderizacao real.

## 4) Plano de Execucao (6 frentes)

## Frente 1 - Governanca canonica no backend e docs

### Como sera resolvido

1. Formalizar a decisao em documento oficial (ADR curta + referencia API).
2. Padronizar exemplos e snippets para `/api/*`.
3. Manter `/api/v1/*` explicitamente marcado como alias temporario.
4. Criar regra de contribuicao: PR com novo endpoint deve incluir somente caminho canonico.

### Resultados esperados dos testes

- `rg "/api/v1"` fora de testes de compatibilidade e arquivos arquivados retorna 0 ocorrencias.
- Testes de API existentes continuam verdes com `/api/*`.
- Documentacao principal lista `/api/*` como contrato oficial sem ambiguidade.

---

## Frente 2 - Telemetria + deprecacao controlada de `/api/v1/*`

### Como sera resolvido

1. Adicionar middleware para detectar requests em `/api/v1/*`.
2. Emitir metrica Prometheus por endpoint legado (contador por path/method/status).
3. Incluir headers de deprecacao na resposta do alias:
   - `Deprecation: true`
   - `Sunset: <data RFC1123>`
   - `Link: <doc de migracao>; rel="deprecation"`
4. Registrar logs estruturados para consumo em dashboard.

### Resultados esperados dos testes

- Request para `/api/v1/...` retorna headers de deprecacao/sunset.
- Request para `/api/...` nao retorna esses headers.
- Metricas de uso legado aparecem em `/metrics` e sobem quando hitamos `/api/v1/...`.
- Testes unitarios de middleware + integracao HTTP aprovados.

---

## Frente 3 - Frontend: remover dependencia de alias legado

### Como sera resolvido

1. Atualizar `frontend/public/sw.js` para cachear somente rotas `/api/*`.
2. Revisar cliente HTTP e interceptors para garantir base unica.
3. Adicionar invalidador de cache/service worker quando versao muda.
4. Validar que paginas criticas continuam funcionais offline/online.

### Resultados esperados dos testes

- Build frontend passa sem referencia funcional a `/api/v1/*`.
- Teste E2E de login + carregamento de options/me/config funcionando via `/api/*`.
- Atualizacao de SW invalida cache antigo e evita retorno stale de rotas legadas.

---

## Frente 4 - Swagger/ReDoc: corrigir tela em branco e blindar regressao

### Como sera resolvido

1. Validar entrega de assets (sidecar/local static) para docs.
2. Revisar CSP para docs (`/api/docs`, `/api/redoc`) com allowlist minima e correta.
3. Garantir schema carregando por caminho canonico.
4. Criar teste de smoke real de renderizacao (Playwright ou teste browser headless no CI).
5. Registrar runbook de troubleshooting para browser cache/service worker/CSP.

### Resultados esperados dos testes

- `GET /api/docs/` e `GET /api/redoc/` retornam 200 com assets carregados.
- Smoke E2E confirma elemento visivel de Swagger/ReDoc (nao apenas status HTTP).
- Console do browser sem erro de CSP ou asset bloqueado para essas paginas.

---

## Frente 5 - Guard rails em CI para evitar reintroducao

### Como sera resolvido

1. Criar check CI que falha se houver nova referencia a `/api/v1/` fora de allowlist.
2. Adicionar suite de contrato:
   - paridade temporaria `/api/` vs `/api/v1/` (enquanto alias existir);
   - headers de deprecacao no alias.
3. Incluir job de smoke docs (`/api/docs` e `/api/redoc`) em PRs backend.

### Resultados esperados dos testes

- PR com novo uso indevido de `/api/v1/*` falha automaticamente.
- CI valida docs, contrato e headers deprecados em toda alteracao relevante.
- Tempo de feedback permanece aceitavel (jobs novos com runtime controlado).

---

## Frente 6 - Corte do alias e limpeza final

### Como sera resolvido

1. Definir janela de observacao (ex.: 30 dias) com criterio objetivo:
   - uso de `/api/v1/*` abaixo do limite acordado por periodo.
2. Comunicar freeze e data final de corte.
3. Remover alias de `config/urls.py`.
4. Remover testes de compatibilidade legado, mantendo testes do contrato canonico.
5. Atualizar documentacao final e release notes.

### Resultados esperados dos testes

- `GET /api/v1/...` passa a responder 404/410 conforme estrategia definida.
- `GET /api/...` segue funcional sem alteracao de payload.
- Suite backend/frontend verde apos remocao.
- Observabilidade sem alerta de erro anormal pos-corte.

## 5) Ordem recomendada de PRs

1. PR1: Frente 1 (governanca e docs canonicas)
2. PR2: Frente 2 (telemetria + headers deprecacao)
3. PR3: Frente 3 (frontend + service worker)
4. PR4: Frente 4 (swagger/redoc hardening + smoke)
5. PR5: Frente 5 (guard rails CI)
6. PR6: Frente 6 (remocao alias, apos janela)

## 6) Riscos e mitigacoes

- Risco: integracao externa ainda depende de `/api/v1/*`.
  - Mitigacao: telemetria + janela de deprecacao + comunicacao.
- Risco: CI ficar mais lento.
  - Mitigacao: smoke enxuto, paralelizacao e cache de dependencias.
- Risco: falso positivo de CSP/docs em navegadores com cache antigo.
  - Mitigacao: versao de assets, instrucoes de hard refresh e teste em navegador limpo.

## 7) Definition of Done (programa completo)

- `/api/*` documentado e aplicado como unico canonico.
- `/api/v1/*` monitorado, deprecado e removido com janela segura.
- Swagger/ReDoc estavel e coberto por teste de renderizacao.
- CI bloqueando regressao de contrato e de padrao de rotas.
- Runbook e release notes atualizados.

## 8) Referencias tecnicas (fontes confiaveis)

- Django REST Framework - Versioning:
  - https://www.django-rest-framework.org/api-guide/versioning/
  - https://www.django-rest-framework.org/api-guide/versioning/#urlpathversioning
- drf-spectacular (OpenAPI em Django/DRF):
  - https://drf-spectacular.readthedocs.io/
- Prometheus - Instrumentation/Naming best practices:
  - https://prometheus.io/docs/practices/instrumentation/
  - https://prometheus.io/docs/practices/naming/
- Service Worker (MDN):
  - https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API/Using_Service_Workers
  - https://developer.mozilla.org/en-US/docs/Web/API/ServiceWorkerRegistration/update
- Sunset header (RFC 8594):
  - https://datatracker.ietf.org/doc/rfc8594/

## 9) Issues abertas para execucao

- API-001: https://github.com/matheusnorjosa/aprender_sistema/issues/792
- API-002: https://github.com/matheusnorjosa/aprender_sistema/issues/793
- API-003: https://github.com/matheusnorjosa/aprender_sistema/issues/794
- API-004: https://github.com/matheusnorjosa/aprender_sistema/issues/795
- API-005: https://github.com/matheusnorjosa/aprender_sistema/issues/796
- API-006: https://github.com/matheusnorjosa/aprender_sistema/issues/797
