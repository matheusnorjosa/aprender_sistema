#!/usr/bin/env python
"""
Script para remover extrações locais antigas e desnecessárias
Foco: Manter apenas arquivos essenciais e remover temporários
"""
import os
import glob
from datetime import datetime


def cleanup_old_extractions():
    """Remove extrações antigas e arquivos temporários"""
    print("🧹 REMOVENDO EXTRAÇÕES LOCAIS ANTIGAS")
    print("=" * 50)

    # Arquivos a serem removidos (padrões)
    patterns_to_remove = [
        # Análises temporárias
        "analise_*.json",
        "relatorio_*.json",
        "mapeamento_*.json",
        "estrutura_*.json",
        "backup_*.json",
        "dados_*.json",
        "usuarios_*.json",
        # Scripts temporários
        "temp_*.py",
        # Arquivos de dados antigos
        "dados_frescos_*.json",
        "dados_organizados_*.json",
        "dados_tratados_*.json",
        "dados_unificados_*.json",
        "consolidado_*.xlsx",
        "relatorio_*.xlsx",
        # Arquivos de comparação
        "comparacao_*.json",
        "comparar_*.py",
        # Arquivos de teste
        "teste_*.csv",
        "teste_*.json",
        # Arquivos de backup antigos
        "backup_*.txt",
        "backup_*.sql",
    ]

    # Arquivos essenciais a serem preservados
    essential_files = [
        "google_oauth_token.json",
        "RELATORIO_COMPLETO_ENTENDIMENTO_SISTEMA.md",
        "requirements.txt",
        "requirements-dev.txt",
        "pyproject.toml",
        "manage.py",
        "docker-compose.yml",
        "Dockerfile",
        "README.md",
    ]

    removed_count = 0
    preserved_count = 0

    for pattern in patterns_to_remove:
        files = glob.glob(pattern)
        for file_path in files:
            # Verificar se é um arquivo essencial
            if os.path.basename(file_path) in essential_files:
                print(f"   🔒 Preservando: {file_path}")
                preserved_count += 1
                continue

            try:
                # Verificar se o arquivo é recente (últimas 2 horas)
                file_time = os.path.getmtime(file_path)
                current_time = datetime.now().timestamp()
                time_diff = current_time - file_time

                if time_diff > 7200:  # 2 horas em segundos
                    os.remove(file_path)
                    print(f"   🗑️  Removido: {file_path}")
                    removed_count += 1
                else:
                    print(f"   ⏰ Recente (preservado): {file_path}")
                    preserved_count += 1

            except Exception as e:
                print(f"   ❌ Erro ao remover {file_path}: {e}")

    print(f"\n📊 RESUMO DA LIMPEZA:")
    print(f"   🗑️  Arquivos removidos: {removed_count}")
    print(f"   🔒 Arquivos preservados: {preserved_count}")

    return removed_count, preserved_count


def list_remaining_files():
    """Lista arquivos restantes"""
    print(f"\n📁 ARQUIVOS RESTANTES:")
    print("=" * 30)

    # Listar arquivos JSON restantes
    json_files = glob.glob("*.json")
    if json_files:
        print("📄 Arquivos JSON:")
        for file in sorted(json_files):
            size = os.path.getsize(file)
            print(f"   - {file} ({size} bytes)")

    # Listar arquivos Python restantes
    py_files = glob.glob("*.py")
    if py_files:
        print("\n🐍 Arquivos Python:")
        for file in sorted(py_files):
            if not file.startswith("temp_"):
                size = os.path.getsize(file)
                print(f"   - {file} ({size} bytes)")

    # Listar arquivos de dados restantes
    data_files = glob.glob("*.xlsx") + glob.glob("*.csv")
    if data_files:
        print("\n📊 Arquivos de Dados:")
        for file in sorted(data_files):
            size = os.path.getsize(file)
            print(f"   - {file} ({size} bytes)")


if __name__ == "__main__":
    print("🚀 INICIANDO LIMPEZA DE EXTRAÇÕES ANTIGAS")
    print("=" * 50)

    removed, preserved = cleanup_old_extractions()
    list_remaining_files()

    print(f"\n✅ LIMPEZA CONCLUÍDA!")
    print(f"   🗑️  {removed} arquivos removidos")
    print(f"   🔒 {preserved} arquivos preservados")
