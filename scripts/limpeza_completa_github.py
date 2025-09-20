#!/usr/bin/env python3
"""
Limpeza Completa do Repositório GitHub
=====================================

Script para executar limpeza completa baseada na análise detalhada
de todos os arquivos do repositório GitHub.

Author: Claude Code
Date: Janeiro 2025
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime

class GitHubCleaner:
    """Limpeza completa do repositório GitHub"""
    
    def __init__(self, root_path=".", analysis_file=None):
        self.root_path = Path(root_path)
        self.analysis = None
        self.operations = {
            "files_removed": [],
            "files_moved": [],
            "directories_cleaned": [],
            "gitignore_updated": [],
            "errors": []
        }
        
        if analysis_file:
            self.load_analysis(analysis_file)
    
    def load_analysis(self, analysis_file):
        """Carrega análise do arquivo JSON"""
        try:
            with open(analysis_file, 'r', encoding='utf-8') as f:
                self.analysis = json.load(f)
            print(f"✅ Análise carregada de: {analysis_file}")
            return True
        except Exception as e:
            print(f"❌ Erro ao carregar análise: {e}")
            return False
    
    def remove_unnecessary_files(self):
        """Remove arquivos desnecessários"""
        if not self.analysis:
            print("❌ Análise não carregada!")
            return False
        
        print("🗑️ Removendo arquivos desnecessários...")
        
        files_to_remove = self.analysis["recommendations"]["files_to_remove"]
        
        for file_info in files_to_remove:
            file_path = self.root_path / file_info["file"]
            
            try:
                if file_path.exists():
                    # Fazer backup antes de remover
                    backup_path = self.root_path / "backups" / "removed_files" / file_info["file"]
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file_path, backup_path)
                    
                    # Remover arquivo
                    file_path.unlink()
                    
                    self.operations["files_removed"].append({
                        "file": str(file_path),
                        "reason": file_info["reason"],
                        "size_mb": file_info["size_mb"],
                        "backup": str(backup_path)
                    })
                    
                    print(f"✅ Removido: {file_path} (backup: {backup_path})")
                else:
                    print(f"⚠️ Arquivo não encontrado: {file_path}")
                    
            except Exception as e:
                error_msg = f"Erro ao remover {file_path}: {e}"
                self.operations["errors"].append(error_msg)
                print(f"❌ {error_msg}")
        
        return True
    
    def organize_files(self):
        """Organiza arquivos em estrutura adequada"""
        print("📁 Organizando arquivos...")
        
        # Criar diretórios de organização
        organize_dirs = {
            "scripts": self.root_path / "scripts",
            "reports": self.root_path / "reports",
            "data": self.root_path / "data",
            "backups": self.root_path / "backups",
            "temp": self.root_path / "temp"
        }
        
        for dir_name, dir_path in organize_dirs.items():
            dir_path.mkdir(exist_ok=True)
            print(f"📂 Diretório criado/verificado: {dir_path}")
        
        # Organizar scripts
        scripts_patterns = [
            "analise_*.py",
            "limpeza_*.py",
            "extrair_*.py",
            "import_*.py",
            "test_*.py",
            "debug_*.py"
        ]
        
        for pattern in scripts_patterns:
            for file_path in self.root_path.glob(pattern):
                if file_path.is_file():
                    try:
                        dest_path = organize_dirs["scripts"] / file_path.name
                        if not dest_path.exists():
                            shutil.move(str(file_path), str(dest_path))
                            self.operations["files_moved"].append({
                                "from": str(file_path),
                                "to": str(dest_path),
                                "reason": "Organização de scripts"
                            })
                            print(f"📁 Movido: {file_path} -> {dest_path}")
                    except Exception as e:
                        error_msg = f"Erro ao mover {file_path}: {e}"
                        self.operations["errors"].append(error_msg)
                        print(f"❌ {error_msg}")
        
        # Organizar relatórios
        reports_patterns = [
            "RELATORIO_*.md",
            "relatorio_*.json",
            "analise_*.json",
            "ANALISE_*.md"
        ]
        
        for pattern in reports_patterns:
            for file_path in self.root_path.glob(pattern):
                if file_path.is_file():
                    try:
                        dest_path = organize_dirs["reports"] / file_path.name
                        if not dest_path.exists():
                            shutil.move(str(file_path), str(dest_path))
                            self.operations["files_moved"].append({
                                "from": str(file_path),
                                "to": str(dest_path),
                                "reason": "Organização de relatórios"
                            })
                            print(f"📁 Movido: {file_path} -> {dest_path}")
                    except Exception as e:
                        error_msg = f"Erro ao mover {file_path}: {e}"
                        self.operations["errors"].append(error_msg)
                        print(f"❌ {error_msg}")
        
        return True
    
    def update_gitignore(self):
        """Atualiza arquivo .gitignore"""
        print("📝 Atualizando .gitignore...")
        
        if not self.analysis:
            print("❌ Análise não carregada!")
            return False
        
        gitignore_path = self.root_path / ".gitignore"
        gitignore_patterns = self.analysis["recommendations"]["files_to_add_gitignore"]
        
        # Ler .gitignore atual
        current_patterns = set()
        if gitignore_path.exists():
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                current_patterns = set(line.strip() for line in f if line.strip() and not line.startswith('#'))
        
        # Adicionar novos padrões
        new_patterns = set()
        for pattern_info in gitignore_patterns:
            pattern = pattern_info["pattern"]
            if pattern not in current_patterns:
                new_patterns.add(pattern)
        
        # Escrever .gitignore atualizado
        if new_patterns:
            with open(gitignore_path, 'a', encoding='utf-8') as f:
                f.write("\n# Padrões adicionados automaticamente\n")
                for pattern in sorted(new_patterns):
                    f.write(f"{pattern}\n")
                    self.operations["gitignore_updated"].append(pattern)
                    print(f"✅ Adicionado ao .gitignore: {pattern}")
        
        return True
    
    def clean_directories(self):
        """Limpa diretórios desnecessários"""
        print("🧹 Limpando diretórios...")
        
        if not self.analysis:
            print("❌ Análise não carregada!")
            return False
        
        directories_to_clean = self.analysis["recommendations"]["directories_to_clean"]
        
        for dir_info in directories_to_clean:
            dir_path = self.root_path / dir_info["directory"]
            
            try:
                if dir_path.exists() and dir_path.is_dir():
                    # Fazer backup do diretório
                    backup_path = self.root_path / "backups" / "removed_directories" / dir_info["directory"]
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(dir_path, backup_path)
                    
                    # Remover diretório
                    shutil.rmtree(dir_path)
                    
                    self.operations["directories_cleaned"].append({
                        "directory": str(dir_path),
                        "reason": dir_info["reason"],
                        "backup": str(backup_path)
                    })
                    
                    print(f"✅ Diretório removido: {dir_path} (backup: {backup_path})")
                else:
                    print(f"⚠️ Diretório não encontrado: {dir_path}")
                    
            except Exception as e:
                error_msg = f"Erro ao remover diretório {dir_path}: {e}"
                self.operations["errors"].append(error_msg)
                print(f"❌ {error_msg}")
        
        return True
    
    def create_organized_structure(self):
        """Cria estrutura organizada"""
        print("🏗️ Criando estrutura organizada...")
        
        # Estrutura proposta
        structure = {
            "scripts": {
                "extraction": "Scripts de extração de dados",
                "oauth": "Scripts de autenticação OAuth",
                "verification": "Scripts de verificação",
                "test": "Scripts de teste",
                "optimized": "Scripts otimizados"
            },
            "reports": {
                "analysis": "Relatórios de análise",
                "migration": "Relatórios de migração",
                "cleanup": "Relatórios de limpeza"
            },
            "data": {
                "extracted": "Dados extraídos",
                "backups": "Backups de dados",
                "exports": "Exportações"
            },
            "docs": {
                "technical": "Documentação técnica",
                "user": "Documentação do usuário",
                "api": "Documentação da API"
            }
        }
        
        for main_dir, subdirs in structure.items():
            main_path = self.root_path / main_dir
            main_path.mkdir(exist_ok=True)
            
            for sub_dir, description in subdirs.items():
                sub_path = main_path / sub_dir
                sub_path.mkdir(exist_ok=True)
                
                # Criar README com descrição
                readme_path = sub_path / "README.md"
                if not readme_path.exists():
                    with open(readme_path, 'w', encoding='utf-8') as f:
                        f.write(f"# {sub_dir.title()}\n\n{description}\n")
                
                print(f"📂 Criado: {sub_path}")
        
        return True
    
    def execute_cleanup(self):
        """Executa limpeza completa"""
        print("🧹 Iniciando limpeza completa do repositório GitHub...")
        print("=" * 70)
        
        if not self.analysis:
            print("❌ Análise não carregada! Execute primeiro a análise.")
            return False
        
        # Executar operações de limpeza
        print("🗑️ Fase 1: Removendo arquivos desnecessários...")
        self.remove_unnecessary_files()
        
        print("\n📁 Fase 2: Organizando arquivos...")
        self.organize_files()
        
        print("\n📝 Fase 3: Atualizando .gitignore...")
        self.update_gitignore()
        
        print("\n🧹 Fase 4: Limpando diretórios...")
        self.clean_directories()
        
        print("\n🏗️ Fase 5: Criando estrutura organizada...")
        self.create_organized_structure()
        
        return True
    
    def generate_cleanup_report(self):
        """Gera relatório de limpeza"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"relatorio_limpeza_completa_github_{timestamp}.json"
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "operations": self.operations,
            "summary": {
                "files_removed": len(self.operations["files_removed"]),
                "files_moved": len(self.operations["files_moved"]),
                "directories_cleaned": len(self.operations["directories_cleaned"]),
                "gitignore_patterns_added": len(self.operations["gitignore_updated"]),
                "errors": len(self.operations["errors"])
            }
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"📊 Relatório de limpeza salvo em: {report_file}")
        return report_file
    
    def print_summary(self):
        """Imprime resumo da limpeza"""
        print("\n📊 RESUMO DA LIMPEZA COMPLETA:")
        print("=" * 50)
        print(f"🗑️ Arquivos removidos: {len(self.operations['files_removed'])}")
        print(f"📁 Arquivos movidos: {len(self.operations['files_moved'])}")
        print(f"🧹 Diretórios limpos: {len(self.operations['directories_cleaned'])}")
        print(f"📝 Padrões .gitignore adicionados: {len(self.operations['gitignore_updated'])}")
        print(f"❌ Erros encontrados: {len(self.operations['errors'])}")
        
        if self.operations["errors"]:
            print("\n❌ ERROS ENCONTRADOS:")
            for error in self.operations["errors"]:
                print(f"  • {error}")

def main():
    """Função principal"""
    print("🧹 Limpeza Completa do Repositório GitHub - Sistema Aprender")
    print("=" * 70)
    
    # Encontrar arquivo de análise mais recente
    analysis_files = list(Path(".").glob("relatorio_analise_completa_github_*.json"))
    if not analysis_files:
        print("❌ Nenhum arquivo de análise encontrado!")
        print("Execute primeiro: python analise_completa_github.py")
        return
    
    latest_analysis = max(analysis_files, key=lambda x: x.stat().st_mtime)
    print(f"📊 Usando análise: {latest_analysis}")
    
    # Executar limpeza
    cleaner = GitHubCleaner(analysis_file=latest_analysis)
    
    if cleaner.execute_cleanup():
        # Gerar relatório
        report_file = cleaner.generate_cleanup_report()
        
        # Mostrar resumo
        cleaner.print_summary()
        
        print(f"\n📄 Relatório completo salvo em: {report_file}")
        print("\n✅ Limpeza completa concluída!")
    else:
        print("\n❌ Erro durante a limpeza!")

if __name__ == "__main__":
    main()
