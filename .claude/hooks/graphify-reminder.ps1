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
    '{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"graphify: Knowledge graph exists. Read graphify-out/GRAPH_REPORT.md for god nodes and community structure before searching raw files."}}'
}
