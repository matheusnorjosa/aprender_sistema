## Contexto
Com `CORS_ALLOW_CREDENTIALS=True`, listas amplas de origem em producao aumentam risco de confianca excessiva e erros de configuracao.

## Objetivo
Minimizar CORS/CSRF em producao com allowlist explicita e controles anti-drift.

## Plano de implementacao
1. Separar claramente configuracoes de dev/staging/prod em `settings.py` e envs.
2. Em producao, permitir apenas origens explicitamente aprovadas (sem wildcard).
3. Bloquear startup/CI quando houver combinacao insegura (credentials + wildcard).
4. Revisar politica CSRF para dominios confiaveis estritamente necessarios.
5. Adicionar verificacao periodica de drift (CI lint de seguranca de configuracao).

## Resultado esperado dos testes
- Origem autorizada recebe headers CORS corretos.
- Origem nao autorizada nao recebe `Access-Control-Allow-Origin`.
- Preflight de origem invalida e bloqueado.
- Testes CSRF confirmam rejeicao para origem/token invalidos.

## Criterios de aceite
- Nenhuma origem generica em producao.
- Regras de CORS/CSRF cobertas por testes automatizados.
- Gate de CI impede regressao de configuracao insegura.

## Referencias
- MDN CORS credentials guidance
- OWASP REST Security Cheat Sheet
