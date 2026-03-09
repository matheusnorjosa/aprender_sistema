## Contexto
Endpoints de docs/schema/metrics/probes podem ampliar superficie de reconhecimento quando expostos sem controle adequado.

## Objetivo
Reduzir superficie publica e proteger endpoints administrativos/observabilidade com autenticacao e segmentacao de rede.

## Plano de implementacao
1. Classificar endpoints publicos essenciais vs administrativos.
2. Restringir `schema/docs/redoc/metrics` com autenticacao forte e autorizacao por papel.
3. Em producao, aplicar allowlist de rede para endpoints de observabilidade.
4. Configurar `drf-spectacular` (`SERVE_PERMISSIONS`) restritivo em prod.
5. Manter `liveness/readiness` minimos para orquestracao, sem metadados sensiveis.
6. Aplicar rate limit nos endpoints administrativos expostos.

## Resultado esperado dos testes
- Usuario anonimo recebe `401/403` em docs/schema/metrics.
- Usuario autenticado sem perfil admin continua sem acesso (`403`).
- Orquestrador interno consegue probes de saude sem quebrar deploy.

## Criterios de aceite
- Inventario de endpoints administrativos publicado e aprovado.
- Testes de permissao por perfil e por origem de rede no CI.
- Nenhum endpoint de observabilidade sensivel aberto publicamente.

## Referencias
- OWASP REST Security Cheat Sheet
- drf-spectacular settings (`SERVE_PERMISSIONS`)
