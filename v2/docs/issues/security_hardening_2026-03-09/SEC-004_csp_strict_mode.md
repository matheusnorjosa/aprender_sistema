## Contexto
A CSP atual permite diretivas fracas (`unsafe-inline`/`unsafe-eval`) que reduzem defesa contra XSS e script injection.

## Objetivo
Adotar CSP estrita com nonce/hash, eliminando fontes inseguras em producao.

## Plano de implementacao
1. Revisar `v2/backend/apps/core/middleware_security.py` para politica CSP estrita.
2. Remover `unsafe-eval` e `unsafe-inline` de `script-src` em producao.
3. Adaptar frontend para evitar scripts inline e handlers inline.
4. Operar inicialmente em `Content-Security-Policy-Report-Only` por janela controlada.
5. Tratar violacoes legitimas e promover para modo enforcing.
6. Integrar coleta de violacoes CSP (endpoint/log/SIEM).

## Resultado esperado dos testes
- Fluxos E2E criticos funcionam sem regressao funcional.
- Tentativas de execucao inline/eval sao bloqueadas no navegador.
- Relatorio de violacoes cai para baseline aceitavel antes do enforcing.

## Criterios de aceite
- CSP enforcing ativa em producao sem `unsafe-inline`/`unsafe-eval` para scripts.
- Plano de excecoes documentado e minimizado.
- Testes de seguranca no browser validados (console + E2E).

## Referencias
- OWASP Content Security Policy Cheat Sheet
