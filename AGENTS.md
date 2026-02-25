# AGENTS Guide

Guia enxuto para execução com Codex neste repositório.

## Fonte Local de Operação

Use a estrutura local em `.codex/` como referência principal:

1. Workflow: `.codex/docs/WORKFLOW.md`
2. Regras de domínio: `.codex/docs/DOMAIN_RULES.md`
3. Gates de CI e preflight: `.codex/docs/CI_GATES.md`
4. Operações Docker: `.codex/docs/DOCKER_OPERATIONS.md`
5. Skills operacionais: `.codex/skills/`
6. Templates: `.codex/templates/`
7. MCP local: `.codex/mcp/`

## Regras Essenciais

1. Rodar backend em Docker (`REQUIRE_DOCKER=1`).
2. Seguir fluxo: plano -> issue -> PR por issue -> checks verdes -> merge.
3. Não fazer push direto na `main`.
4. Não declarar sucesso sem evidência de execução (verification gate).

## Planejamento e Execução

1. Registrar planos locais em `.codex/docs/plans/`.
2. Usar templates para padronizar issue/PR.
3. Priorizar correção por causa raiz (debug sistemático).

