#!/usr/bin/env python3
"""
Script de ajuda para fluxo Git do Sistema Aprender
Facilita a criação de branches seguindo as convenções estabelecidas
"""

import argparse
import os
import subprocess
import sys
from typing import List

# Módulos disponíveis no sistema
MODULOS = {
    "core": "Sistema base (usuários, permissões, formadores, municípios)",
    "planilhas": "Importações e integração Google Sheets",
    "relatorios": "Dashboards e métricas executivas",
    "api": "Integrações externas e endpoints REST",
    "calendar": "Integração Google Calendar",
    "controle": "Auditoria, logs e monitoramento",
}

# Tipos de branch disponíveis
TIPOS_BRANCH = {
    "feature": "Nova funcionalidade",
    "fix": "Correção de bug",
    "refactor": "Refatoração de código",
    "security": "Melhoria de segurança",
    "hotfix": "Correção emergencial",
}


def executar_comando(comando: str) -> tuple:
    """Executa comando git e retorna resultado"""
    try:
        result = subprocess.run(
            comando.split(), capture_output=True, text=True, check=True
        )
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return False, e.stderr.strip()


def listar_opcoes():
    """Lista módulos e tipos disponíveis"""
    print("🏗️  SISTEMA APRENDER - Git Flow Helper")
    print("=" * 50)

    print("\n📦 MÓDULOS DISPONÍVEIS:")
    for modulo, desc in MODULOS.items():
        print(f"  {modulo:12} - {desc}")

    print("\n🔧 TIPOS DE BRANCH:")
    for tipo, desc in TIPOS_BRANCH.items():
        print(f"  {tipo:12} - {desc}")


def criar_branch(tipo: str, modulo: str, descricao: str):
    """Cria uma nova branch seguindo as convenções"""

    # Validar inputs
    if tipo not in TIPOS_BRANCH:
        print(f"❌ Tipo '{tipo}' inválido. Use: {', '.join(TIPOS_BRANCH.keys())}")
        return False

    if modulo not in MODULOS:
        print(f"❌ Módulo '{modulo}' inválido. Use: {', '.join(MODULOS.keys())}")
        return False

    # Normalizar descrição (remover espaços, caracteres especiais)
    desc_clean = descricao.lower().replace(" ", "-").replace("_", "-")
    desc_clean = "".join(c for c in desc_clean if c.isalnum() or c == "-")

    # Montar nome da branch
    nome_branch = f"{tipo}/{modulo}-{desc_clean}"

    print(f"\n🌿 Criando branch: {nome_branch}")

    # Determinar branch base
    if tipo == "hotfix":
        branch_base = "main"
    else:
        branch_base = "develop"

    # Comandos git
    comandos = [
        f"git checkout {branch_base}",
        f"git pull origin {branch_base}",
        f"git checkout -b {nome_branch}",
    ]

    for comando in comandos:
        print(f"  Executando: {comando}")
        sucesso, resultado = executar_comando(comando)

        if not sucesso:
            print(f"❌ Erro: {resultado}")
            return False

        if resultado:
            print(f"    {resultado}")

    print(f"\n✅ Branch {nome_branch} criada com sucesso!")
    print(f"📋 Base: {branch_base}")
    print(f"🎯 Módulo: {modulo} - {MODULOS[modulo]}")

    return True


def listar_branches():
    """Lista branches do projeto"""
    print("\n🌳 BRANCHES DO PROJETO:")
    sucesso, resultado = executar_comando("git branch -a")

    if sucesso:
        linhas = resultado.split("\n")
        current_branch = None

        for linha in linhas:
            linha = linha.strip()
            if linha.startswith("*"):
                current_branch = linha[2:]
                print(f"  ➤ {current_branch} (atual)")
            elif linha.startswith("remotes/origin/"):
                branch_name = linha.replace("remotes/origin/", "")
                if branch_name != "HEAD":
                    print(f"    {branch_name}")
            elif linha and not linha.startswith("remotes/"):
                print(f"    {linha}")
    else:
        print(f"❌ Erro ao listar branches: {resultado}")


def status_projeto():
    """Mostra status atual do projeto"""
    print("\n📊 STATUS DO PROJETO:")

    # Branch atual
    sucesso, branch_atual = executar_comando("git branch --show-current")
    if sucesso:
        print(f"  Branch atual: {branch_atual}")

    # Status do git
    sucesso, status = executar_comando("git status --porcelain")
    if sucesso:
        if status:
            print(f"  Arquivos modificados: {len(status.split())}")
        else:
            print("  Working tree limpo ✅")

    # Últimos commits
    sucesso, commits = executar_comando("git log --oneline -5")
    if sucesso:
        print("  Últimos commits:")
        for commit in commits.split("\n")[:3]:
            print(f"    {commit}")


def main():
    parser = argparse.ArgumentParser(
        description="Sistema Aprender - Git Flow Helper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python git-flow.py --list                           # Listar opções
  python git-flow.py --create feature planilhas "import cursos csv"  # Criar feature
  python git-flow.py --create fix core "bug permissoes"  # Criar fix
  python git-flow.py --branches                        # Listar branches
  python git-flow.py --status                          # Status do projeto
        """,
    )

    parser.add_argument(
        "--list", action="store_true", help="Listar módulos e tipos disponíveis"
    )
    parser.add_argument(
        "--create",
        nargs=3,
        metavar=("TIPO", "MÓDULO", "DESCRIÇÃO"),
        help="Criar nova branch",
    )
    parser.add_argument(
        "--branches", action="store_true", help="Listar todas as branches"
    )
    parser.add_argument(
        "--status", action="store_true", help="Mostrar status do projeto"
    )

    args = parser.parse_args()

    # Se nenhum argumento, mostrar ajuda
    if len(sys.argv) == 1:
        parser.print_help()
        return

    # Verificar se estamos em um repositório git
    if not os.path.exists(".git"):
        print("❌ Este diretório não é um repositório Git")
        return

    if args.list:
        listar_opcoes()
    elif args.create:
        tipo, modulo, descricao = args.create
        criar_branch(tipo, modulo, descricao)
    elif args.branches:
        listar_branches()
    elif args.status:
        status_projeto()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
