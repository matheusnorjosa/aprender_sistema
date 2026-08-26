# Hook: graphify-reminder -- PreToolUse (Bash). Sugere o grafo como ferramenta
# SOB DEMANDA (CLAUDE.md D2): nunca obriga a le-lo, nunca falha fechado.
# REGRA CRITICA: SEMPRE emitir JSON valido em stdout + exit 0. Um stdout vazio
# e lido como "invalid JSON" pelo Cursor -> a tool e BLOQUEADA. Por isso o ramo
# else devolve '{}' em vez de nada.

$inputJson = [Console]::In.ReadToEnd()
$commandText = ""

try {
    $payload = $inputJson | ConvertFrom-Json
    if ($payload.tool_input -and $payload.tool_input.command) {
        $commandText = [string]$payload.tool_input.command
    } elseif ($payload.command) {
        $commandText = [string]$payload.command
    }
} catch {
    $commandText = ""
}

$isSearchCommand = $commandText -match "(^|\s)(grep|rg|ripgrep|find|fd|ack|ag)(\s|$)"

if ($isSearchCommand -and (Test-Path "graphify-out/graph.json")) {
    # Sugestao OPCIONAL -- o grafo pode estar velho; a verdade de arquitetura sao
    # as specs vivas em v2/docs/specs/. Nunca obriga a ler.
    '{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"graphify: existe um grafo em graphify-out/ (opcional, pode estar desatualizado). Use se quiser explorar; a fonte de verdade de arquitetura sao as specs vivas em v2/docs/specs/."}}'
} else {
    # Nada a sugerir -- mas SEMPRE JSON valido em stdout (nunca vazio).
    '{}'
}

exit 0
