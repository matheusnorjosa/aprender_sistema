#!/bin/bash
# Post-compact reminder: re-inject critical rules after context compaction
# Triggered by PreCompact (wired in .claude/settings.json), fires before context is compacted
cat <<'REMINDER'
<system-reminder>
REGRAS CRITICAS POS-COMPACTION:
- CP-01: v2 DEVE rodar APENAS em Docker (cd v2 && make up)
- CP-02: PA-01~07 (aprovacao obrigatoria para SUPER)
- CP-03: RD-01~08 (disponibilidade com timezone America/Fortaleza)
- CP-06: Conventional commits (feat/fix/chore)
- CP-07: NUNCA push direto na main (branch + PR)
- RBAC: 13 setores, 5 funcoes, permissoes funcionais
- Pyright strict mode obrigatorio
- Usar skills/commands ANTES de implementar manualmente
</system-reminder>
REMINDER
