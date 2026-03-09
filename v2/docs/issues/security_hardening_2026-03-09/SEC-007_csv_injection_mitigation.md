## Contexto
Exportacoes CSV podem incluir valores iniciando com caracteres interpretados como formula (`=`, `+`, `-`, `@`, TAB/CR/LF), permitindo CSV Injection em planilhas.

## Objetivo
Sanitizar de forma centralizada todos os valores exportados para prevenir execucao de formulas em clientes de planilha.

## Plano de implementacao
1. Criar helper central `sanitize_for_csv_spreadsheet(value)` no backend.
2. Aplicar sanitizacao em todos os endpoints/servicos de exportacao CSV.
3. Cobrir tambem fluxos onde frontend monta CSV localmente (se existir).
4. Padronizar estrategia (prefixo seguro e escape consistente) com documentacao tecnica.
5. Adicionar testes unitarios com payloads maliciosos e caracteres de controle.
6. Validar abertura manual em Excel/LibreOffice/Google Sheets.

## Resultado esperado dos testes
- Payload malicioso nao e executado como formula apos export/import.
- Todos os caracteres de risco sao neutralizados conforme regra central.
- Regressao automatizada protege futuros novos exports.

## Criterios de aceite
- 100% dos pontos de exportacao identificados usam helper central.
- Suite de testes cobre casos positivos e maliciosos.
- Validacao manual em ao menos dois clientes de planilha anexada.

## Referencias
- OWASP CSV Injection
