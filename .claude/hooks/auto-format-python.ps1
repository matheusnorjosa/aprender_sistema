# Hook: auto-format Python files after Write/Edit.
# Event: PostToolUse(Write|Edit). Reads tool input from stdin (JSON) -- Claude
# Code delivers hook payloads on stdin, NOT via env vars. Runs Black + isort on
# the edited file inside the dev container.
$inputJson = [Console]::In.ReadToEnd()
$filePath = ""

try {
    $payload = $inputJson | ConvertFrom-Json
    if ($payload.tool_input -and $payload.tool_input.file_path) {
        $filePath = [string]$payload.tool_input.file_path
    }
} catch {
    $filePath = ""
}

# Only format .py files under v2/backend.
if ($filePath -match '\.py$' -and $filePath -match 'v2[\\/]backend') {
    # Container path is POSIX; strip the host prefix and normalize separators.
    $relativePath = $filePath -replace '.*v2[\\/]backend[\\/]', ''
    $relativePath = $relativePath -replace '\\', '/'
    try {
        docker exec aprender_dev-web-1 black --quiet "$relativePath" 2>$null
        docker exec aprender_dev-web-1 isort --quiet "$relativePath" 2>$null
    } catch {
        # Docker not running, skip silently
    }
}
