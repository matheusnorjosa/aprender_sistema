Param(
  [ValidateSet("check","makemigrations","showmigrations")]
  [string]$Cmd = "check"
)

# Ir para a raiz do repositório
$repoRoot = (& git rev-parse --show-toplevel).Trim()
Set-Location $repoRoot

function Is-Up {
  $out = & docker compose ps --status running web 2>$null
  if ($LASTEXITCODE -ne 0) { return $false }
  return ($out -match "web")
}

function Run-InWeb {
  param([Parameter(ValueFromRemainingArguments=$true)] [string[]]$Args)
  & docker compose exec -T web @Args
  exit $LASTEXITCODE
}

if (-not (Is-Up)) {
  Write-Host "[pre-commit] container 'web' não está 'Up'; pulando hooks Django."
  exit 0
}

switch ($Cmd) {
  "check"          { Run-InWeb python manage.py check }
  "makemigrations" { Run-InWeb python manage.py makemigrations --check --dry-run }
  "showmigrations" { Run-InWeb python manage.py showmigrations }
  default          { Write-Host "uso: precommit-django.ps1 {check|makemigrations|showmigrations}"; exit 2 }
}
