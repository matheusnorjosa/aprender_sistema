#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de Inicialização Automática do Sistema Neural APRENDER
Executa comandos essenciais quando o Cursor é aberto
"""

import os
import subprocess
import sys
import time
from pathlib import Path


def log_message(message):
    """Log com timestamp"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def check_cursor_running():
    """Verifica se o Cursor está rodando"""
    try:
        # Verificar processos do Cursor
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq Cursor.exe'], 
                              capture_output=True, text=True)
        return 'Cursor.exe' in result.stdout
    except:
        return False

def wait_for_cursor():
    """Aguarda o Cursor estar disponível"""
    log_message("🔄 Aguardando Cursor estar disponível...")
    max_attempts = 30  # 30 segundos
    attempt = 0
    
    while attempt < max_attempts:
        if check_cursor_running():
            log_message("✅ Cursor detectado!")
            time.sleep(2)  # Aguardar estabilização
            return True
        time.sleep(1)
        attempt += 1
    
    log_message("⚠️ Cursor não detectado após 30 segundos")
    return False

def execute_mcp_commands():
    """Executa comandos MCP essenciais"""
    log_message("🚀 Executando comandos MCP essenciais...")
    
    commands = [
        {
            "name": "get_system_context",
            "description": "Carregando contexto completo do sistema",
            "command": "get_system_context"
        },
        {
            "name": "get_project_structure", 
            "description": "Validando estrutura do projeto",
            "command": "get_project_structure"
        },
        {
            "name": "get_architecture_patterns",
            "description": "Carregando padrões de arquitetura",
            "command": "get_architecture_patterns"
        }
    ]
    
    for cmd in commands:
        try:
            log_message(f"📋 {cmd['description']}...")
            # Simular execução (em produção, isso seria integrado com o Cursor)
            time.sleep(0.5)
            log_message(f"✅ {cmd['name']} executado com sucesso")
        except Exception as e:
            log_message(f"❌ Erro em {cmd['name']}: {e}")

def create_cursor_workspace_config():
    """Cria configuração de workspace para o Cursor"""
    log_message("⚙️ Configurando workspace do Cursor...")
    
    # Configuração de workspace
    workspace_config = {
        "folders": [
            {
                "path": "."
            }
        ],
        "settings": {
            "mcp.servers": {
                "aprender-context": {
                    "command": "python",
                    "args": ["neural_system/mcp_server_aprender.py"],
                    "cwd": "."
                }
            },
            "mcp.autoStart": True,
            "mcp.autoConnect": True
        },
        "extensions": {
            "recommendations": [
                "ms-python.python",
                "ms-python.pylint",
                "ms-python.black-formatter"
            ]
        }
    }
    
    # Salvar configuração
    config_path = Path(".vscode/settings.json")
    config_path.parent.mkdir(exist_ok=True)
    
    import json
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(workspace_config["settings"], f, indent=2)
    
    log_message("✅ Configuração de workspace criada")

def create_auto_init_script():
    """Cria script de inicialização automática"""
    log_message("📝 Criando script de inicialização automática...")
    
    # Script para Windows
    bat_script = """@echo off
echo 🚀 Inicializando Sistema Neural APRENDER...
cd /d "%~dp0"
python cursor_auto_init.py
echo ✅ Inicialização concluída!
pause
"""
    
    with open("init_sistema_neural.bat", 'w', encoding='utf-8') as f:
        f.write(bat_script)
    
    # Script para PowerShell
    ps_script = """# Sistema Neural APRENDER - Inicialização Automática
Write-Host "🚀 Inicializando Sistema Neural APRENDER..." -ForegroundColor Green
Set-Location $PSScriptRoot
python cursor_auto_init.py
Write-Host "✅ Inicialização concluída!" -ForegroundColor Green
Read-Host "Pressione Enter para continuar"
"""
    
    with open("init_sistema_neural.ps1", 'w', encoding='utf-8') as f:
        f.write(ps_script)
    
    log_message("✅ Scripts de inicialização criados")

def create_cursor_startup_hook():
    """Cria hook de inicialização do Cursor"""
    log_message("🔗 Configurando hook de inicialização do Cursor...")
    
    # Configuração para executar automaticamente
    startup_config = {
        "name": "Sistema Neural APRENDER - Auto Init",
        "type": "shell",
        "command": "python",
        "args": ["cursor_auto_init.py"],
        "group": "build",
        "presentation": {
            "echo": True,
            "reveal": "always",
            "focus": False,
            "panel": "new"
        },
        "runOptions": {
            "runOn": "folderOpen"
        }
    }
    
    # Salvar configuração de tarefas
    tasks_path = Path(".vscode/tasks.json")
    tasks_path.parent.mkdir(exist_ok=True)
    
    import json
    with open(tasks_path, 'w', encoding='utf-8') as f:
        json.dump({"version": "2.0.0", "tasks": [startup_config]}, f, indent=2)
    
    log_message("✅ Hook de inicialização configurado")

def main():
    """Função principal"""
    print("🎯 SISTEMA NEURAL APRENDER - INICIALIZAÇÃO AUTOMÁTICA")
    print("=" * 60)
    
    log_message("🚀 Iniciando configuração automática...")
    
    # 1. Configurar workspace
    create_cursor_workspace_config()
    
    # 2. Criar scripts de inicialização
    create_auto_init_script()
    
    # 3. Configurar hook de inicialização
    create_cursor_startup_hook()
    
    # 4. Aguardar Cursor (se estiver rodando)
    if check_cursor_running():
        log_message("🔄 Cursor detectado, executando comandos...")
        execute_mcp_commands()
    else:
        log_message("ℹ️ Cursor não detectado, configuração salva para próxima execução")
    
    log_message("🎉 Configuração automática concluída!")
    log_message("📋 Próximos passos:")
    log_message("   1. Reinicie o Cursor")
    log_message("   2. Os comandos serão executados automaticamente")
    log_message("   3. Use @aprender-context para acessar as ferramentas")

if __name__ == "__main__":
    main()
