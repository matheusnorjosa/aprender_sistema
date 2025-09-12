#!/usr/bin/env python3
"""
Script para executar linting automático no projeto.
"""
import subprocess
import sys
from pathlib import Path


def run_command(command, description):
    """Executa um comando e retorna True se bem-sucedido."""
    print(f"\n🔍 {description}...")
    try:
        result = subprocess.run(
            command, shell=True, check=True, capture_output=True, text=True
        )
        print(f"✅ {description} concluído com sucesso")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} falhou:")
        print(e.stdout)
        print(e.stderr)
        return False


def main():
    """Executa todas as verificações de linting."""
    project_root = Path(__file__).parent

    print("🚀 Iniciando verificações de código...")

    commands = [
        ("isort . --check-only --diff", "Verificando ordenação de imports"),
        ("black . --check --diff", "Verificando formatação do código"),
        ("flake8 .", "Verificando estilo de código (flake8)"),
    ]

    all_passed = True

    for command, description in commands:
        if not run_command(command, description):
            all_passed = False

    if all_passed:
        print("\n🎉 Todas as verificações passaram!")
        return 0
    else:
        print("\n❌ Algumas verificações falharam. Execute os comandos para corrigir:")
        print("  isort .")
        print("  black .")
        return 1


if __name__ == "__main__":
    sys.exit(main())
