#!/usr/bin/env python3
"""
Script de validação do sistema neural do Sistema APRENDER
Verifica se todos os componentes estão funcionando corretamente.
"""

import os
import sys
import json
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Adicionar diretório atual ao path
sys.path.insert(0, str(Path(__file__).parent))


def check_documentation_files() -> Tuple[bool, List[str]]:
    """Verifica se arquivos de documentação essenciais existem."""
    docs_dir = Path(__file__).parent.parent
    essential_docs = [
        "ARQUITETURA_REFERENCIA.md",
        "PADROES_CODIGO_PYTHON.md",
        "GUIA_SEGURANCA.md",
        "CLAUDE_CONTEXT_PACKAGE.md",
    ]

    issues = []
    for doc in essential_docs:
        doc_path = docs_dir / doc
        if not doc_path.exists():
            issues.append(f"❌ Documento não encontrado: {doc}")
        else:
            # Verificar se o arquivo não está vazio
            try:
                content = doc_path.read_text(encoding="utf-8")
                if len(content.strip()) < 100:
                    issues.append(
                        f"⚠️ Documento muito pequeno: {doc} ({len(content)} chars)"
                    )
            except Exception as e:
                issues.append(f"❌ Erro ao ler {doc}: {e}")

    return len(issues) == 0, issues


def check_mcp_server() -> Tuple[bool, List[str]]:
    """Verifica se o servidor MCP pode ser carregado."""
    issues = []

    try:
        # Tentar importar o módulo do servidor MCP
        from mcp_server_aprender import (
            server,
            _read_documentation_file,
            handle_list_tools,
            handle_call_tool,
        )

        # Verificar se o servidor tem as ferramentas esperadas
        tools = asyncio.run(handle_list_tools())
        expected_tools = [
            "get_architecture_patterns",
            "get_python_patterns",
            "get_security_guidelines",
            "get_business_rules",
            "validate_code_pattern",
            "check_security_vulnerabilities",
            "get_system_context",
            "get_project_structure",
        ]

        tool_names = [tool["name"] for tool in tools]
        for expected_tool in expected_tools:
            if expected_tool not in tool_names:
                issues.append(f"❌ Ferramenta MCP não encontrada: {expected_tool}")

        # Testar uma ferramenta simples
        try:
            result = asyncio.run(handle_call_tool("get_project_structure", {}))
            if not result or result[0]["type"] != "text":
                issues.append(
                    "❌ Ferramenta get_project_structure não retornou resultado válido"
                )
        except Exception as e:
            issues.append(f"❌ Erro ao testar ferramenta MCP: {e}")

    except ImportError as e:
        issues.append(f"❌ Não é possível importar servidor MCP: {e}")
        issues.append(
            "   Instale as dependências: pip install -r neural_system/requirements_mcp.txt"
        )
    except Exception as e:
        issues.append(f"❌ Erro no servidor MCP: {e}")

    return len(issues) == 0, issues


def _is_running_in_docker() -> bool:
    """Detecta se está rodando dentro de um container Docker."""
    # Primeiro, verificar pistas mais diretas
    if os.path.exists("/.dockerenv"):
        return True

    if os.environ.get("DOCKER_CONTAINER") == "true":
        return True

    if os.environ.get("PYTHONPATH") == "/app":
        return True

    # Verificar cgroup como fallback
    try:
        with open("/proc/1/cgroup", "r") as f:
            content = f.read()
            return "docker" in content or "containerd" in content
    except (FileNotFoundError, PermissionError):
        return False


def check_cursor_configuration() -> Tuple[bool, List[str]]:
    """Verifica configuração do Cursor."""
    issues = []

    cursor_dir = Path(__file__).parent.parent / ".cursor"

    # Detectar ambiente e escolher configuração apropriada
    if _is_running_in_docker():
        mcp_settings = cursor_dir / "mcp_settings_docker.json"
        env_name = "Docker"
    else:
        mcp_settings = cursor_dir / "mcp_settings.json"
        env_name = "Local"

    if not cursor_dir.exists():
        issues.append("❌ Diretório .cursor não encontrado")
        return False, issues

    if not mcp_settings.exists():
        issues.append(
            f"❌ Arquivo {mcp_settings.name} não encontrado para ambiente {env_name}"
        )
        return False, issues

    try:
        with open(mcp_settings, "r") as f:
            settings = json.load(f)

        if "mcpServers" not in settings:
            issues.append(
                f"❌ Configuração mcpServers não encontrada em {mcp_settings.name}"
            )
        elif "aprender-context" not in settings["mcpServers"]:
            issues.append("❌ Servidor aprender-context não configurado")
        else:
            server_config = settings["mcpServers"]["aprender-context"]

            # Verificar configuração baseada no ambiente
            if _is_running_in_docker():
                # Em Docker, verificar se usa docker-compose
                if server_config.get("command") != "docker-compose":
                    issues.append(
                        "⚠️ Configuração Docker deve usar 'docker-compose' como comando"
                    )
            else:
                # Local, verificar se o arquivo MCP existe
                if "args" in server_config:
                    mcp_server_path = Path(server_config["args"][0])
                    if not mcp_server_path.exists():
                        issues.append(
                            f"❌ Servidor MCP não encontrado no caminho: {mcp_server_path}"
                        )

    except json.JSONDecodeError as e:
        issues.append(f"❌ JSON inválido em {mcp_settings.name}: {e}")
    except Exception as e:
        issues.append(f"❌ Erro ao verificar configuração Cursor: {e}")

    return len(issues) == 0, issues


def check_test_coverage() -> Tuple[bool, List[str]]:
    """Verifica se testes existem e podem ser executados."""
    issues = []

    tests_dir = Path(__file__).parent.parent / "tests" / "neural_system"

    if not tests_dir.exists():
        issues.append("❌ Diretório de testes não encontrado")
        return False, issues

    test_files = ["test_mcp_server.py", "test_context_updates.py"]

    for test_file in test_files:
        test_path = tests_dir / test_file
        if not test_path.exists():
            issues.append(f"❌ Arquivo de teste não encontrado: {test_file}")

    # Tentar executar testes (só verificar sintaxe)
    try:
        import pytest

        # Não executar os testes realmente, só verificar se pytest está disponível
    except ImportError:
        issues.append("⚠️ pytest não instalado - recomendado para executar testes")

    return len(issues) == 0, issues


def test_mcp_functionality() -> Tuple[bool, List[str]]:
    """Testa funcionalidade básica do MCP."""
    issues = []

    try:
        from mcp_server_aprender import handle_call_tool

        # Teste 1: Validação de código Python bom
        test_code_good = '''
@login_required
def test_view(request, item_id: int) -> HttpResponse:
    """View de teste com padrões corretos."""
    logger.info(f"Acessando item {item_id}")
    return render(request, 'template.html')
'''

        result = asyncio.run(
            handle_call_tool(
                "validate_code_pattern", {"code": test_code_good, "context": "view"}
            )
        )

        if "✅" not in result[0]["text"]:
            issues.append("⚠️ Validação de código bom não retornou resultado positivo")

        # Teste 2: Validação de código com problemas
        test_code_bad = """
def bad_view(request):
    print("Debug message")
    return HttpResponse("OK")
"""

        result = asyncio.run(
            handle_call_tool(
                "validate_code_pattern", {"code": test_code_bad, "context": "view"}
            )
        )

        if "ERRO" not in result[0]["text"]:
            issues.append("⚠️ Validação de código ruim não detectou problemas")

        # Teste 3: Verificação de segurança
        test_code_unsafe = """
api_key = "hardcoded-secret"
user_input = request.GET['input']
query = "SELECT * FROM table WHERE id = %s" % user_input
"""

        result = asyncio.run(
            handle_call_tool(
                "check_security_vulnerabilities", {"code": test_code_unsafe}
            )
        )

        if "RISCO" not in result[0]["text"]:
            issues.append("⚠️ Verificação de segurança não detectou vulnerabilidades")

    except Exception as e:
        issues.append(f"❌ Erro ao testar funcionalidade MCP: {e}")

    return len(issues) == 0, issues


def check_dependencies() -> Tuple[bool, List[str]]:
    """Verifica se dependências necessárias estão instaladas."""
    issues = []

    # Verificar dependências Python
    required_packages = ["mcp", "anthropic", "requests"]

    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            issues.append(f"❌ Pacote não instalado: {package}")

    # Verificar Python version
    if sys.version_info < (3, 8):
        issues.append(
            f"❌ Python {sys.version_info.major}.{sys.version_info.minor} muito antigo. Mínimo: 3.8"
        )

    return len(issues) == 0, issues


def main():
    """Função principal de validação."""
    print("🔍 VALIDAÇÃO DO SISTEMA NEURAL - Sistema APRENDER")
    print("=" * 60)
    print()

    all_checks = [
        ("📄 Arquivos de Documentação", check_documentation_files),
        ("📦 Dependências Python", check_dependencies),
        ("🤖 Servidor MCP", check_mcp_server),
        ("⚙️ Configuração Cursor", check_cursor_configuration),
        ("🧪 Cobertura de Testes", check_test_coverage),
        ("🔧 Funcionalidade MCP", test_mcp_functionality),
    ]

    total_passed = 0
    total_checks = len(all_checks)
    all_issues = []

    for check_name, check_func in all_checks:
        print(f"🔍 {check_name}...")
        try:
            passed, issues = check_func()
            if passed:
                print(f"   ✅ Passou")
                total_passed += 1
            else:
                print(f"   ❌ Falhou ({len(issues)} problemas)")
                all_issues.extend(issues)
        except Exception as e:
            print(f"   💥 Erro durante verificação: {e}")
            all_issues.append(f"❌ Erro em {check_name}: {e}")

        print()

    # Resumo final
    print("=" * 60)
    print("📊 RESUMO DA VALIDAÇÃO")
    print("=" * 60)
    print(f"✅ Verificações Passou: {total_passed}/{total_checks}")
    print(f"❌ Verificações Falhou: {total_checks - total_passed}/{total_checks}")
    print()

    if all_issues:
        print("🔧 PROBLEMAS ENCONTRADOS:")
        for issue in all_issues:
            print(f"   {issue}")
        print()

    if total_passed == total_checks:
        print("🎉 SISTEMA NEURAL VÁLIDO!")
        print()
        print("💡 Próximos passos:")
        print("   1. Configure CLAUDE_API_KEY para upload automático")
        print("   2. Execute: python neural_system/upload_to_claude.py")
        print("   3. Configure Cursor para usar o servidor MCP")
        print("   4. Teste no Cursor: use as ferramentas MCP do Sistema APRENDER")
        return True
    else:
        print("⚠️ SISTEMA NEURAL PRECISA DE CORREÇÕES")
        print()
        print("🔧 Corrija os problemas acima e execute novamente:")
        print("   python neural_system/validate_system.py")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
