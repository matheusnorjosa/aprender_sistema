# Hook: Injetar lembrete de ferramentas no contexto do Claude
# Roda no inicio de cada prompt do usuario via UserPromptSubmit

$reminder = @"
<system-reminder>
Antes de tarefa nao-trivial: usar skill/command/agent adequado (ver CLAUDE.md).
</system-reminder>
"@

Write-Output $reminder
