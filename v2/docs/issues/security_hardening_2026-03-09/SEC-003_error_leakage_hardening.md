## Contexto
Alguns fluxos retornam detalhes tecnicos de excecao (`str(e)`) para o cliente. Isso aumenta capacidade de recon de atacante (stack, nomes internos, detalhes de SQL/driver).

## Objetivo
Padronizar respostas de erro para clientes e manter detalhes tecnicos apenas em logs internos.

## Plano de implementacao
1. Mapear endpoints que retornam excecao bruta para resposta HTTP.
2. Implementar helper central de erro com contrato padrao (`code`, `detail` generico, `request_id`).
3. Ajustar handlers globais DRF/Django para remover traces/texto interno em producao.
4. Garantir logging estruturado server-side com correlacao por `request_id`.
5. Criar testes de contrato garantindo ausencia de payload sensivel.

## Resultado esperado dos testes
- Erros 4xx/5xx retornam mensagem generica e codigo interno consistente.
- Nenhum payload em producao contem `Traceback`, SQL bruto ou nome de classe interna.
- Logs internos preservam detalhes tecnicos para troubleshooting.

## Criterios de aceite
- Cobertura automatizada para cenarios de erro criticos.
- Revisao de seguranca confirma ausencia de leak de excecoes.
- Documentacao de contrato de erro atualizada.

## Referencias
- OWASP Error Handling Cheat Sheet
