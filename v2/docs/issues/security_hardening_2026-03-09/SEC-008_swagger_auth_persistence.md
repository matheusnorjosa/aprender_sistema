## Contexto
`persistAuthorization` no Swagger UI pode manter credenciais no browser entre refresh/reabertura, aumentando risco em estacoes compartilhadas.

## Objetivo
Reduzir risco operacional da documentacao interativa em producao sem perder utilidade em ambiente controlado.

## Plano de implementacao
1. Desabilitar `persistAuthorization` em producao (`SPECTACULAR_SETTINGS`).
2. Exigir autenticacao para acesso a Swagger/Redoc em producao.
3. Diferenciar politica por ambiente (dev mais permissivo, prod restrito).
4. Revisar timeout de sessao para ambiente administrativo.
5. Atualizar runbook de uso seguro de documentacao interativa.

## Resultado esperado dos testes
- Recarregar Swagger em producao limpa token/autorizacao.
- Usuario nao autenticado recebe `401/403` em docs.
- Usuario autorizado continua conseguindo testar endpoints conforme permissao.

## Criterios de aceite
- Configuracao por ambiente validada por teste automatizado.
- Evidencia funcional (antes/depois) do comportamento de persistencia.
- Documentacao operacional atualizada.

## Referencias
- Swagger UI configuration (`persistAuthorization`)
- drf-spectacular settings
