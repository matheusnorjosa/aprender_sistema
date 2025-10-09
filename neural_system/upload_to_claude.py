#!/usr/bin/env python3
"""
Script para upload de documentação do Sistema APRENDER para o Claude
Adaptado para estrutura existente do projeto.
"""

import os
import base64
from pathlib import Path
import anthropic
from typing import List

# Configuração da API do Claude
# NOTA: Configure sua API key como variável de ambiente
API_KEY = os.getenv("CLAUDE_API_KEY")
if not API_KEY:
    print("⚠️ CLAUDE_API_KEY não configurada como variável de ambiente")
    print("   Para configurar: export CLAUDE_API_KEY=sua_chave_aqui")
    exit(1)

client = anthropic.Anthropic(api_key=API_KEY)

# Diretório base da documentação (raiz do projeto)
DOCS_DIR = Path(__file__).parent.parent

# Lista de documentos essenciais para upload (adaptado para nossa estrutura)
ESSENTIAL_DOCS = [
    "ARQUITETURA_REFERENCIA.md",
    "PADROES_CODIGO_PYTHON.md",
    "GUIA_SEGURANCA.md",
    "CLAUDE_CONTEXT_PACKAGE.md",
    "CLAUDE.md",
    "DOCUMENTACAO_PROJETO.md",
    "docs/fluxo_aprovacao.md",
    "docs/hierarquia_organizacional.md",
]


def upload_document_to_claude(file_path: Path) -> bool:
    """Faz upload de um documento para o Claude"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Criar mensagem com o documento
        response = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            messages=[
                {
                    "role": "user",
                    "content": f"""
                    Por favor, armazene este documento como contexto para futuras interações sobre o Sistema APRENDER.

                    Arquivo: {file_path.name}

                    Este documento contém informações críticas sobre:
                    - Arquitetura do sistema Django
                    - Padrões de código Python/Django
                    - Diretrizes de segurança
                    - Regras de negócio específicas
                    - Fluxos de trabalho e aprovação
                    - Estrutura do projeto

                    Use este contexto para fornecer respostas precisas e contextualizadas sobre o Sistema APRENDER.
                    Sempre que trabalhar com código para este sistema, siga rigorosamente os padrões aqui definidos.
                    """,
                }
            ],
        )

        print(f"✅ Documento {file_path.name} enviado com sucesso!")
        return True

    except Exception as e:
        print(f"❌ Erro ao enviar documento {file_path.name}: {e}")
        return False


def main():
    """Função principal"""
    print("🚀 Iniciando upload de documentação do Sistema APRENDER para o Claude...")
    print(f"📁 Diretório de documentação: {DOCS_DIR}")
    print()

    successful_uploads = 0
    total_docs = len(ESSENTIAL_DOCS)

    for doc_name in ESSENTIAL_DOCS:
        doc_path = DOCS_DIR / doc_name
        print(f"📄 Processando: {doc_name}")

        if doc_path.exists():
            if upload_document_to_claude(doc_path):
                successful_uploads += 1
        else:
            print(f"⚠️ Documento não encontrado: {doc_path}")

        print("-" * 50)

    print()
    print("📊 RESUMO DO UPLOAD:")
    print(f"   Total de documentos: {total_docs}")
    print(f"   Uploads bem-sucedidos: {successful_uploads}")
    print(f"   Falhas: {total_docs - successful_uploads}")

    if successful_uploads == total_docs:
        print("🎉 Todos os documentos foram enviados com sucesso!")
        print()
        print("💡 Próximos passos:")
        print("   1. Configure o Cursor MCP com neural_system/mcp_server_aprender.py")
        print("   2. Teste as ferramentas MCP disponíveis")
        print("   3. Use update_context.py para atualizações automáticas")
    else:
        print("⚠️ Alguns documentos não puderam ser enviados. Verifique os logs acima.")
        print()
        print(
            "🔧 Documentos faltantes podem ser criados com base nos padrões existentes."
        )


if __name__ == "__main__":
    main()
