# Hook: Injetar lembrete de ferramentas no contexto do Claude
# Roda no inicio de cada prompt do usuario via UserPromptSubmit

$reminder = @"
<system-reminder>
FERRAMENTAS DISPONIVEIS - Use proativamente:

SKILLS (conhecimento especializado):
- aprender-domain: Regras RF/RD/PA/CP
- django-patterns: Padroes Django/DRF
- test-driven-development: ANTES de implementar
- create_plan/implement_plan: Planejar e executar
- continuity_ledger: Salvar estado

SLASH COMMANDS:
- /project_plan: Planejar antes de implementar
- /review, /review-enhanced: Apos implementar
- /approve-flow, /check-conflicts: Validar regras
- /project_git-pr: Commits e PRs

AGENTS:
- Explore: Buscar arquivos (usar ANTES de editar)
- Plan: Arquitetar solucao

REGRA: Verificar se existe ferramenta antes de fazer manualmente.
</system-reminder>
"@

Write-Output $reminder
