"""
Dev Tools App — AS v2

Ferramentas de desenvolvimento: seeds, backfills, fixtures.
Excluido de producao via INCLUDE_DEV_TOOLS=false.

Commands disponiveis:
- seed_* : Dados iniciais (usuarios, projetos, RBAC)
- backfill_* : Migracoes de dados
- fix_* : Correcoes unicas
- cleanup_* : Limpeza de dados E2E
"""

from __future__ import annotations

default_app_config = "apps.dev_tools.apps.DevToolsConfig"
