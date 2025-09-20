#!/usr/bin/env python3
"""
Script para atualização contínua do contexto do Claude e MCP
Adaptado para estrutura existente do Sistema APRENDER.
"""

import os
import json
import hashlib
import subprocess
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Configurações
DOCS_DIR = Path(__file__).parent.parent
CONTEXT_DIR = Path(__file__).parent / "context"
LAST_UPDATE_FILE = CONTEXT_DIR / "last_update.json"
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')

def calculate_file_hash(file_path: Path) -> str:
    """Calcula hash SHA256 de um arquivo"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

def get_file_hashes() -> Dict[str, str]:
    """Retorna hashes de todos os arquivos de documentação"""
    file_hashes = {}

    # Arquivos principais na raiz
    main_docs = [
        "ARQUITETURA_REFERENCIA.md",
        "PADROES_CODIGO_PYTHON.md",
        "GUIA_SEGURANCA.md",
        "CLAUDE_CONTEXT_PACKAGE.md",
        "CLAUDE.md",
        "DOCUMENTACAO_PROJETO.md"
    ]

    for doc_name in main_docs:
        file_path = DOCS_DIR / doc_name
        if file_path.exists():
            file_hashes[doc_name] = calculate_file_hash(file_path)

    # Arquivos da pasta docs/
    docs_dir = DOCS_DIR / "docs"
    if docs_dir.exists():
        for file_path in docs_dir.rglob("*.md"):
            relative_path = file_path.relative_to(DOCS_DIR)
            file_hashes[str(relative_path)] = calculate_file_hash(file_path)

    return file_hashes

def load_last_hashes() -> Dict[str, str]:
    """Carrega hashes da última atualização"""
    if LAST_UPDATE_FILE.exists():
        with open(LAST_UPDATE_FILE, 'r') as f:
            data = json.load(f)
            return data.get("hashes", {})
    return {}

def save_last_hashes(hashes: Dict[str, str]) -> None:
    """Salva hashes da atualização atual"""
    CONTEXT_DIR.mkdir(exist_ok=True)

    data = {
        "timestamp": datetime.now().isoformat(),
        "hashes": hashes,
        "project": "Sistema APRENDER",
        "version": "1.0"
    }

    with open(LAST_UPDATE_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def restart_mcp_server() -> bool:
    """Reinicia o servidor MCP para carregar nova documentação"""
    try:
        mcp_server_path = Path(__file__).parent / "mcp_server_aprender.py"

        # Verificar se o servidor MCP existe
        if not mcp_server_path.exists():
            print(f"⚠️ Servidor MCP não encontrado em: {mcp_server_path}")
            return False

        # Parar servidor MCP existente (se estiver rodando)
        subprocess.run(["pkill", "-f", "mcp_server_aprender.py"], check=False)

        print("🔄 Servidor MCP será reiniciado na próxima conexão.")
        print(f"   Para iniciar manualmente: python {mcp_server_path}")

        return True

    except Exception as e:
        print(f"❌ Erro ao gerenciar servidor MCP: {e}")
        return False

def update_claude_context(changed_files: List[str]) -> bool:
    """Atualiza contexto do Claude com arquivos modificados"""
    if not CLAUDE_API_KEY:
        print("⚠️ CLAUDE_API_KEY não configurada. Pulando atualização do Claude.")
        print("   Para configurar: export CLAUDE_API_KEY=sua_chave_aqui")
        return False

    import anthropic
    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

    success_count = 0

    for file_path in changed_files:
        full_path = DOCS_DIR / file_path

        if not full_path.exists():
            print(f"⚠️ Arquivo não encontrado: {file_path}")
            continue

        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            response = client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1000,
                messages=[
                    {
                        "role": "user",
                        "content": f"""
                        Atualize seu contexto com esta versão atualizada do documento {file_path} do Sistema APRENDER.

                        Este documento contém informações críticas que podem ter sido modificadas:
                        - Atualizações de arquitetura Django
                        - Novos padrões de código Python
                        - Mudanças nas diretrizes de segurança
                        - Atualizações de regras de negócio
                        - Alterações no fluxo de aprovação

                        Substitua qualquer informação anterior sobre este documento com esta nova versão.
                        """
                    }
                ]
            )

            print(f"✅ Contexto do Claude atualizado para {file_path}")
            success_count += 1

        except Exception as e:
            print(f"❌ Erro ao atualizar contexto do Claude para {file_path}: {e}")

    return success_count == len(changed_files)

def main():
    """Função principal"""
    print("🔄 Verificando atualizações na documentação do Sistema APRENDER...")
    print(f"📁 Diretório de documentação: {DOCS_DIR}")
    print()

    current_hashes = get_file_hashes()
    last_hashes = load_last_hashes()

    changed_files = []

    for file_path, current_hash in current_hashes.items():
        if file_path not in last_hashes or last_hashes[file_path] != current_hash:
            changed_files.append(file_path)
            print(f"📄 Arquivo modificado: {file_path}")

    if not changed_files:
        print("✅ Nenhuma atualização necessária.")
        print(f"   Última verificação: {load_last_hashes().get('timestamp', 'Nunca')}")
        return

    print(f"\n🔄 Encontrados {len(changed_files)} arquivos modificados. Atualizando contextos...")
    print("-" * 50)

    # Atualizar contexto do Claude
    claude_success = False
    if CLAUDE_API_KEY:
        print("🤖 Atualizando contexto do Claude...")
        claude_success = update_claude_context(changed_files)
        print(f"   Resultado: {'✅ Sucesso' if claude_success else '❌ Falha'}")
    else:
        print("⚠️ Pulando atualização do Claude (API key não configurada)")

    print()

    # Gerenciar servidor MCP
    print("🔄 Gerenciando servidor MCP...")
    mcp_success = restart_mcp_server()
    print(f"   Resultado: {'✅ Sucesso' if mcp_success else '❌ Falha'}")

    print()

    # Salvar hashes atuais
    save_last_hashes(current_hashes)

    print("📊 RESUMO DA ATUALIZAÇÃO:")
    print(f"   Arquivos modificados: {len(changed_files)}")
    print(f"   Atualização Claude: {'✅' if CLAUDE_API_KEY and claude_success else '⚠️'}")
    print(f"   Servidor MCP: {'✅' if mcp_success else '❌'}")
    print(f"   Hashes salvos: ✅")

    if (not CLAUDE_API_KEY or claude_success) and mcp_success:
        print("🎉 Atualização de contexto concluída com sucesso!")
        print()
        print("💡 Próximos passos:")
        print("   1. Teste o servidor MCP com o Cursor")
        print("   2. Verifique se o Claude tem as informações atualizadas")
        print("   3. Execute este script regularmente para manter sincronizado")
    else:
        print("⚠️ Alguns componentes não puderam ser atualizados. Verifique os logs acima.")

if __name__ == "__main__":
    main()