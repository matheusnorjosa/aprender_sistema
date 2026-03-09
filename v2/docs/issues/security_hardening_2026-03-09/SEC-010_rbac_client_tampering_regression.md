## Contexto
Foi reportado risco de escalacao vertical por manipulacao de `_auth`/`localStorage` no navegador. Mesmo quando o PoC nao reproduz no estado atual, a protecao precisa ser permanente para evitar regressao.

## Objetivo
Garantir de forma definitiva que autorizacao seja exclusivamente server-side e imune a tampering client-side.

## Plano de implementacao
1. Auditar endpoints administrativos para confirmar validacao RBAC no backend (sem confiar em estado de UI/localStorage).
2. Garantir que claims de privilegio venham de JWT assinado e validado, com checagem de permissao por endpoint.
3. Revisar fluxos onde frontend usa `perfil/perfilId` apenas para UX (nunca para autorizacao efetiva).
4. Criar suite Playwright de seguranca com tampering no console (`localStorage`, fake perfil ADMIN, token invalido).
5. Adicionar esses testes como gate obrigatorio no CI.
6. Documentar regra arquitetural: toda decisao de acesso deve ser server-side.

## Resultado esperado dos testes
- Alterar `_auth.perfil` para `ADMIN` no browser nao libera operacoes administrativas reais.
- Requisicoes a endpoints admin sem permissao retornam `403` de forma consistente.
- Token adulterado/invalido e rejeitado (`401/403`).
- Testes de regressao bloqueiam merge em caso de reintroducao da falha.

## Criterios de aceite
- Matriz RBAC por endpoint validada e testada.
- Suite E2E de tampering ativa e obrigatoria no CI.
- Evidencia objetiva de que manipulacao client-side nao altera autorizacao backend.

## Referencias
- OWASP Authorization Cheat Sheet
- OWASP Top 10 A01:2021 Broken Access Control
