# Hook: graphify-sync -- keep the knowledge graph fresh after code changes.
# Event: Stop. Best-effort, NEVER blocks (always exit 0). AST-only (no API cost).
# Runs `graphify update .` only when the git working tree has changed .py/.ts/.tsx
# files AND a graph already exists. graphify e opcional (CLAUDE.md D2); este hook
# so mantem o grafo menos velho quando ja existe -- best-effort. Para desligar,
# remova a entrada Stop em settings.json.

# Drain the Stop payload from stdin so the pipe doesn't break (content unused).
$null = [Console]::In.ReadToEnd()

if (-not (Test-Path "graphify-out/graph.json")) { exit 0 }

$changed = $null
try { $changed = git status --porcelain 2>$null } catch { exit 0 }
if (-not $changed) { exit 0 }

# Only fire when a tracked code file changed (skip .md/.json/.txt churn).
$codeChanged = $changed | Where-Object { $_ -match '\.(py|tsx?)($|\s|")' }
if (-not $codeChanged) { exit 0 }

try {
    if (Get-Command graphify -ErrorAction SilentlyContinue) {
        & graphify update . 2>$null | Out-Null
    }
} catch { }

exit 0
