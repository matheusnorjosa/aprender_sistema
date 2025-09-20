# Sistema Neural APRENDER - Inicialização Automática
# PowerShell Script

param(
    [switch]$AutoStart,
    [switch]$Verbose
)

# Configurar cores e output
$Host.UI.RawUI.WindowTitle = "Sistema Neural APRENDER - Inicialização Automática"

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

function Test-Environment {
    Write-ColorOutput "🔍 Verificando ambiente..." "Yellow"
    
    # Verificar se estamos no diretório correto
    if (-not (Test-Path "neural_system\mcp_server_aprender.py")) {
        Write-ColorOutput "❌ Diretório incorreto! Execute este script na raiz do projeto." "Red"
        return $false
    }
    
    # Verificar ambiente virtual
    if (-not (Test-Path "venv\Scripts\python.exe")) {
        Write-ColorOutput "❌ Ambiente virtual não encontrado!" "Red"
        Write-ColorOutput "💡 Execute: python -m venv venv" "Cyan"
        return $false
    }
    
    Write-ColorOutput "✅ Ambiente virtual encontrado!" "Green"
    return $true
}

function Test-Dependencies {
    Write-ColorOutput "📦 Verificando dependências..." "Yellow"
    
    try {
        & "venv\Scripts\python.exe" -c "import mcp, pandas, ijson, orjson, mistletoe; print('✅ Dependências OK')"
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✅ Dependências verificadas!" "Green"
            return $true
        }
    }
    catch {
        Write-ColorOutput "⚠️ Dependências não encontradas!" "Red"
        Write-ColorOutput "💡 Execute: venv\Scripts\pip.exe install -r requirements.txt" "Cyan"
        return $false
    }
}

function Start-AutoInit {
    Write-ColorOutput "🚀 Executando inicialização automática..." "Yellow"
    
    try {
        & "venv\Scripts\python.exe" "cursor_auto_init.py"
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✅ Inicialização concluída!" "Green"
            return $true
        }
    }
    catch {
        Write-ColorOutput "❌ Erro na inicialização: $($_.Exception.Message)" "Red"
        return $false
    }
}

function Show-NextSteps {
    Write-ColorOutput "`n📋 Próximos passos:" "Cyan"
    Write-ColorOutput "   1. Abra o Cursor" "White"
    Write-ColorOutput "   2. Os comandos MCP serão executados automaticamente" "White"
    Write-ColorOutput "   3. Use @aprender-context para acessar as ferramentas" "White"
    Write-ColorOutput "`n🎯 Sistema Neural APRENDER pronto para uso!" "Green"
}

# Função principal
function Main {
    Write-ColorOutput "`n========================================" "Cyan"
    Write-ColorOutput "   SISTEMA NEURAL APRENDER" "Cyan"
    Write-ColorOutput "   Inicialização Automática" "Cyan"
    Write-ColorOutput "========================================`n" "Cyan"
    
    # Verificar ambiente
    if (-not (Test-Environment)) {
        Read-Host "Pressione Enter para sair"
        exit 1
    }
    
    # Verificar dependências
    if (-not (Test-Dependencies)) {
        Read-Host "Pressione Enter para sair"
        exit 1
    }
    
    # Executar inicialização
    if (-not (Start-AutoInit)) {
        Read-Host "Pressione Enter para sair"
        exit 1
    }
    
    # Mostrar próximos passos
    Show-NextSteps
    
    if (-not $AutoStart) {
        Read-Host "`nPressione Enter para continuar"
    }
}

# Executar função principal
Main
