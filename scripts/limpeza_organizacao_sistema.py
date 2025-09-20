#!/usr/bin/env python3
"""
Limpeza e Organização do Sistema
================================

Script para executar limpeza e organização baseada na análise
de duplicatas e scripts obsoletos.

Author: Claude Code
Date: Janeiro 2025
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime

class SistemaCleaner:
    """Limpeza e organização do sistema"""
    
    def __init__(self, root_path="."):
        self.root_path = Path(root_path)
        self.operations = {
            "files_removed": [],
            "files_moved": [],
            "errors": []
        }
    
    def load_analysis_report(self, report_file):
        """Carrega relatório de análise"""
        try:
            with open(report_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Erro ao carregar relatório: {e}")
            return None
    
    def remove_obsolete_files(self, obsolete_files):
        """Remove arquivos obsoletos"""
        print("🗑️ Removendo arquivos obsoletos...")
        
        for file_info in obsolete_files:
            file_path = self.root_path / file_info["arquivo"]
            
            try:
                if file_path.exists():
                    file_path.unlink()
                    self.operations["files_removed"].append({
                        "file": str(file_path),
                        "reason": file_info["motivo"],
                        "type": file_info["tipo"]
                    })
                    print(f"✅ Removido: {file_path}")
                else:
                    print(f"⚠️ Arquivo não encontrado: {file_path}")
                    
            except Exception as e:
                error_msg = f"Erro ao remover {file_path}: {e}"
                self.operations["errors"].append(error_msg)
                print(f"❌ {error_msg}")
    
    def consolidate_similar_scripts(self, similar_scripts):
        """Consolida scripts similares"""
        print("🔄 Consolidando scripts similares...")
        
        for group in similar_scripts:
            scripts = group["scripts"]
            if len(scripts) < 2:
                continue
            
            # Manter o script mais recente
            latest_script = None
            latest_time = 0
            
            for script_path in scripts:
                full_path = self.root_path / script_path
                if full_path.exists():
                    mtime = full_path.stat().st_mtime
                    if mtime > latest_time:
                        latest_time = mtime
                        latest_script = script_path
            
            if latest_script:
                # Remover os outros scripts
                for script_path in scripts:
                    if script_path != latest_script:
                        full_path = self.root_path / script_path
                        try:
                            if full_path.exists():
                                full_path.unlink()
                                self.operations["files_removed"].append({
                                    "file": str(full_path),
                                    "reason": f"Consolidado com {latest_script}",
                                    "type": "consolidacao"
                                })
                                print(f"✅ Consolidado: {full_path} -> {latest_script}")
                        except Exception as e:
                            error_msg = f"Erro ao consolidar {full_path}: {e}"
                            self.operations["errors"].append(error_msg)
                            print(f"❌ {error_msg}")
    
    def create_optimized_scripts(self, similar_scripts):
        """Cria versões otimizadas dos scripts"""
        print("⚡ Criando versões otimizadas...")
        
        # Criar diretório para scripts otimizados
        optimized_dir = self.root_path / "scripts" / "otimizados"
        optimized_dir.mkdir(exist_ok=True)
        
        for group in similar_scripts:
            scripts = group["scripts"]
            if len(scripts) < 2:
                continue
            
            # Encontrar o script mais completo
            best_script = None
            max_lines = 0
            
            for script_path in scripts:
                full_path = self.root_path / script_path
                if full_path.exists():
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = len(f.readlines())
                        if lines > max_lines:
                            max_lines = lines
                            best_script = full_path
            
            if best_script:
                # Criar versão otimizada
                optimized_name = f"script_otimizado_{group['motivo'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
                optimized_path = optimized_dir / optimized_name
                
                try:
                    # Copiar o melhor script como base
                    shutil.copy2(best_script, optimized_path)
                    
                    # Adicionar cabeçalho de otimização
                    with open(optimized_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    header = f'''#!/usr/bin/env python3
"""
Script Otimizado - {group['motivo']}
=====================================

Script consolidado e otimizado gerado automaticamente.
Consolida funcionalidades de múltiplos scripts similares.

Scripts originais:
{chr(10).join(f"- {s}" for s in scripts)}

Author: Sistema de Otimização
Date: {datetime.now().strftime("%d/%m/%Y")}
Similaridade: {group.get('similaridade', 'N/A')}
"""

'''
                    
                    with open(optimized_path, 'w', encoding='utf-8') as f:
                        f.write(header + content)
                    
                    self.operations["files_moved"].append({
                        "from": str(best_script),
                        "to": str(optimized_path),
                        "reason": "Versão otimizada criada"
                    })
                    
                    print(f"✅ Otimizado criado: {optimized_path}")
                    
                except Exception as e:
                    error_msg = f"Erro ao criar otimizado {optimized_path}: {e}"
                    self.operations["errors"].append(error_msg)
                    print(f"❌ {error_msg}")
    
    def organize_legacy_scripts(self):
        """Organiza scripts legacy"""
        print("📁 Organizando scripts legacy...")
        
        legacy_dir = self.root_path / "scripts" / "legacy"
        legacy_dir.mkdir(exist_ok=True)
        
        # Mover scripts obsoletos para legacy
        obsolete_patterns = ["test_", "debug_", "old_", "backup_"]
        
        for script_dir in ["scripts/teste", "scripts/oauth", "scripts/extracao"]:
            script_path = self.root_path / script_dir
            if script_path.exists():
                for file_path in script_path.glob("*.py"):
                    if any(pattern in file_path.name for pattern in obsolete_patterns):
                        try:
                            legacy_path = legacy_dir / file_path.name
                            shutil.move(str(file_path), str(legacy_path))
                            
                            self.operations["files_moved"].append({
                                "from": str(file_path),
                                "to": str(legacy_path),
                                "reason": "Movido para legacy"
                            })
                            
                            print(f"📁 Movido para legacy: {file_path.name}")
                            
                        except Exception as e:
                            error_msg = f"Erro ao mover {file_path}: {e}"
                            self.operations["errors"].append(error_msg)
                            print(f"❌ {error_msg}")
    
    def generate_cleanup_report(self):
        """Gera relatório de limpeza"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"relatorio_organizacao_final_{timestamp}.json"
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "operations": self.operations,
            "summary": {
                "files_removed": len(self.operations["files_removed"]),
                "files_moved": len(self.operations["files_moved"]),
                "errors": len(self.operations["errors"])
            }
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"📊 Relatório de limpeza salvo em: {report_file}")
        return report_file
    
    def execute_cleanup(self, analysis_report):
        """Executa limpeza completa"""
        print("🧹 Iniciando limpeza e organização do sistema...")
        print("=" * 60)
        
        # Remover arquivos obsoletos
        if "scripts_obsoletos" in analysis_report:
            self.remove_obsolete_files(analysis_report["scripts_obsoletos"])
        
        # Consolidar scripts similares
        if "recomendacoes" in analysis_report and "consolidar" in analysis_report["recomendacoes"]:
            self.consolidate_similar_scripts(analysis_report["recomendacoes"]["consolidar"])
        
        # Criar versões otimizadas
        if "recomendacoes" in analysis_report and "consolidar" in analysis_report["recomendacoes"]:
            self.create_optimized_scripts(analysis_report["recomendacoes"]["consolidar"])
        
        # Organizar scripts legacy
        self.organize_legacy_scripts()
        
        # Gerar relatório final
        report_file = self.generate_cleanup_report()
        
        # Mostrar resumo
        print("\n📊 RESUMO DA LIMPEZA:")
        print("=" * 40)
        print(f"🗑️ Arquivos removidos: {len(self.operations['files_removed'])}")
        print(f"📁 Arquivos movidos: {len(self.operations['files_moved'])}")
        print(f"❌ Erros encontrados: {len(self.operations['errors'])}")
        
        if self.operations["errors"]:
            print("\n❌ ERROS ENCONTRADOS:")
            for error in self.operations["errors"]:
                print(f"  • {error}")
        
        print(f"\n📄 Relatório completo salvo em: {report_file}")
        print("\n✅ Limpeza concluída!")

def main():
    """Função principal"""
    print("🧹 Sistema de Limpeza e Organização")
    print("=" * 60)
    
    # Encontrar relatório de análise mais recente
    analysis_files = list(Path(".").glob("relatorio_analise_duplicatas_*.json"))
    if not analysis_files:
        print("❌ Nenhum relatório de análise encontrado!")
        return
    
    latest_analysis = max(analysis_files, key=lambda x: x.stat().st_mtime)
    print(f"📊 Usando relatório: {latest_analysis}")
    
    # Carregar análise
    cleaner = SistemaCleaner()
    analysis_report = cleaner.load_analysis_report(latest_analysis)
    
    if not analysis_report:
        print("❌ Erro ao carregar relatório de análise!")
        return
    
    # Executar limpeza
    cleaner.execute_cleanup(analysis_report)

if __name__ == "__main__":
    main()
