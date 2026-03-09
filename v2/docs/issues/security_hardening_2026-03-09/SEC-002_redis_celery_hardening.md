## Contexto
Foi detectada inconsistencia entre configuracoes de Redis para cache/sessoes e Celery broker/results. Isso cria risco de conexao sem autenticacao em partes do stack e dificulta hardening uniforme.

## Objetivo
Padronizar autenticacao e criptografia do Redis em todo o ecossistema (Django, Celery broker e backend de resultados).

## Plano de implementacao
1. Consolidar uso de `REDIS_URL` autenticada no backend (`v2/backend/config/settings.py`).
2. Garantir senha obrigatoria para cache, sessao, broker e results (sem fallback anonimo).
3. Habilitar TLS (`rediss://`) quando ambiente suportar e configurar certificados.
4. Restringir bind/rede do Redis para subnet interna e manter `protected-mode` ativo.
5. Opcional recomendado: ACL por funcao (usuario dedicado para cache, broker e results).
6. Ajustar `v2/infra/.env.production` e `v2/infra/redis/redis.conf` para baseline seguro.

## Resultado esperado dos testes
- Aplicacao e workers sobem usando Redis autenticado.
- Tentativa sem senha falha com erro de autorizacao (`NOAUTH` equivalente).
- Publicacao e consumo de tasks Celery funcionam com URL autenticada.
- Em ambiente TLS, handshake e operacoes passam sem downgrade para conexao insegura.

## Criterios de aceite
- Nenhum caminho de conexao Redis sem senha em producao.
- Testes automatizados de conectividade/autenticacao adicionados ao CI.
- Evidencia de configuracao unificada backend + worker + infra.

## Referencias
- Redis Security
- Celery Redis broker/backends
