#!/usr/bin/env python3
"""
Análise Completa e Detalhada do Repositório GitHub
=================================================

Script para análise detalhada de todos os arquivos do repositório GitHub,
identificando arquivos desnecessários, duplicados e propondo organização.

Author: Claude Code
Date: Janeiro 2025
"""

import hashlib
import json
import mimetypes
import os
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


class GitHubCompleteAnalyzer:
    """Analisador completo do repositório GitHub"""

    def __init__(self, root_path="."):
        self.root_path = Path(root_path)
        self.analysis = {
            "timestamp": datetime.now().isoformat(),
            "repository_info": {},
            "files_analysis": {
                "total_files": 0,
                "tracked_files": [],
                "untracked_files": [],
                "modified_files": [],
                "deleted_files": [],
                "file_categories": {},
                "file_sizes": {},
                "duplicate_files": [],
                "unnecessary_files": [],
                "temporary_files": [],
                "generated_files": [],
                "backup_files": [],
                "log_files": [],
                "cache_files": [],
                "large_files": [],
                "empty_files": [],
                "binary_files": [],
                "text_files": [],
                "code_files": [],
                "documentation_files": [],
                "config_files": [],
                "data_files": [],
                "media_files": [],
                "issues": [],
            },
            "directory_analysis": {},
            "recommendations": {
                "files_to_remove": [],
                "files_to_organize": [],
                "files_to_add_gitignore": [],
                "directories_to_clean": [],
                "structure_improvements": [],
            },
        }

    def get_git_status(self):
        """Obtém status completo do Git"""
        try:
            # Arquivos rastreados
            result = subprocess.run(
                ["git", "ls-files"], capture_output=True, text=True, cwd=self.root_path
            )
            tracked_files = [
                line.strip() for line in result.stdout.split("\n") if line.strip()
            ]

            # Status detalhado
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                cwd=self.root_path,
            )

            modified_files = []
            deleted_files = []
            untracked_files = []

            for line in result.stdout.split("\n"):
                if line.strip():
                    status = line[:2]
                    filename = line[3:].strip()

                    if status.startswith("M"):
                        modified_files.append(filename)
                    elif status.startswith("D"):
                        deleted_files.append(filename)
                    elif status.startswith("??"):
                        untracked_files.append(filename)

            self.analysis["files_analysis"]["tracked_files"] = tracked_files
            self.analysis["files_analysis"]["modified_files"] = modified_files
            self.analysis["files_analysis"]["deleted_files"] = deleted_files
            self.analysis["files_analysis"]["untracked_files"] = untracked_files

            return True

        except Exception as e:
            print(f"Erro ao obter status do Git: {e}")
            return False

    def analyze_file(self, file_path):
        """Analisa um arquivo individual"""
        try:
            full_path = self.root_path / file_path

            if not full_path.exists():
                return None

            stat = full_path.stat()

            # Informações básicas
            file_info = {
                "path": str(file_path),
                "name": full_path.name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "extension": full_path.suffix.lower(),
                "is_binary": self.is_binary_file(full_path),
                "is_empty": stat.st_size == 0,
                "mime_type": mimetypes.guess_type(str(full_path))[0] or "unknown",
            }

            # Categorização
            file_info["category"] = self.categorize_file(file_path, file_info)

            # Verificar se é desnecessário
            file_info["is_unnecessary"] = self.is_unnecessary_file(file_path, file_info)
            file_info["is_temporary"] = self.is_temporary_file(file_path, file_info)
            file_info["is_generated"] = self.is_generated_file(file_path, file_info)
            file_info["is_backup"] = self.is_backup_file(file_path, file_info)

            return file_info

        except Exception as e:
            print(f"Erro ao analisar arquivo {file_path}: {e}")
            return None

    def is_binary_file(self, file_path):
        """Verifica se o arquivo é binário"""
        try:
            with open(file_path, "rb") as f:
                chunk = f.read(1024)
                return b"\0" in chunk
        except:
            return False

    def categorize_file(self, file_path, file_info):
        """Categoriza o arquivo"""
        path_str = str(file_path).lower()
        name = file_info["name"].lower()
        ext = file_info["extension"]

        # Categorias principais
        if ext in [".py"]:
            return "code_python"
        elif ext in [".js", ".ts", ".jsx", ".tsx"]:
            return "code_javascript"
        elif ext in [".html", ".htm"]:
            return "code_html"
        elif ext in [".css", ".scss", ".sass"]:
            return "code_css"
        elif ext in [".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf"]:
            return "config"
        elif ext in [".md", ".txt", ".rst"]:
            return "documentation"
        elif ext in [".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico"]:
            return "media_image"
        elif ext in [".mp4", ".avi", ".mov", ".wmv"]:
            return "media_video"
        elif ext in [".mp3", ".wav", ".ogg"]:
            return "media_audio"
        elif ext in [".pdf", ".doc", ".docx", ".xls", ".xlsx"]:
            return "document"
        elif ext in [".log"]:
            return "log"
        elif ext in [".backup", ".bak", ".old"]:
            return "backup"
        elif ext in [".tmp", ".temp"]:
            return "temporary"
        elif ext in [".cache", ".pyc", ".pyo", "__pycache__"]:
            return "cache"
        elif ext in [".sql", ".db", ".sqlite", ".sqlite3"]:
            return "database"
        elif ext in [".zip", ".tar", ".gz", ".rar"]:
            return "archive"
        elif "test" in name or "spec" in name:
            return "test"
        elif "migration" in path_str:
            return "migration"
        elif "script" in path_str:
            return "script"
        elif "template" in path_str:
            return "template"
        else:
            return "other"

    def is_unnecessary_file(self, file_path, file_info):
        """Verifica se o arquivo é desnecessário"""
        path_str = str(file_path).lower()
        name = file_info["name"].lower()

        # Padrões de arquivos desnecessários
        unnecessary_patterns = [
            # Arquivos de desenvolvimento local
            ".env.local",
            ".env.development",
            ".env.test",
            "local_settings.py",
            "dev_settings.py",
            # Arquivos de IDE
            ".vscode/settings.json",
            ".idea/",
            "*.swp",
            "*.swo",
            # Arquivos de sistema
            ".DS_Store",
            "Thumbs.db",
            "desktop.ini",
            # Arquivos temporários
            "*.tmp",
            "*.temp",
            "*.log",
            # Arquivos de backup
            "*.backup",
            "*.bak",
            "*.old",
            # Arquivos de cache
            "__pycache__/",
            "*.pyc",
            "*.pyo",
            ".pytest_cache/",
            # Arquivos de build
            "build/",
            "dist/",
            "*.egg-info/",
            # Arquivos de node
            "node_modules/",
            "package-lock.json",
            # Arquivos de Python
            "venv/",
            ".venv/",
            "env/",
            ".env/",
            # Arquivos de dados locais
            "db.sqlite3",
            "*.db",
            "*.sqlite",
            # Arquivos de relatórios gerados
            "relatorio_*.json",
            "analise_*.json",
            "*.report",
            # Screenshots e imagens temporárias
            "screenshot_*.png",
            "test_*.png",
            "debug_*.png",
            # Arquivos de conversa e chat
            "conversa_*.txt",
            "chat_*.txt",
            "*.conversation",
            # Arquivos de deploy
            "deploy_*.txt",
            "trigger_*.txt",
            # Arquivos de extração
            "extraction_*.log",
            "extract_*.log",
        ]

        for pattern in unnecessary_patterns:
            if pattern.endswith("/"):
                if path_str.startswith(pattern[:-1]):
                    return True
            elif pattern.startswith("*"):
                if name.endswith(pattern[1:]):
                    return True
            elif pattern in path_str or pattern in name:
                return True

        return False

    def is_temporary_file(self, file_path, file_info):
        """Verifica se é arquivo temporário"""
        name = file_info["name"].lower()
        path_str = str(file_path).lower()

        temp_patterns = [
            "temp",
            "tmp",
            "temporary",
            "cache",
            "swap",
            "~",
            ".swp",
            ".swo",
            ".tmp",
            ".temp",
        ]

        return any(pattern in name or pattern in path_str for pattern in temp_patterns)

    def is_generated_file(self, file_path, file_info):
        """Verifica se é arquivo gerado automaticamente"""
        name = file_info["name"].lower()
        path_str = str(file_path).lower()

        generated_patterns = [
            "generated",
            "auto",
            "build",
            "compiled",
            "migration",
            "migrate",
            "makemigrations",
            "collectstatic",
            "staticfiles",
            "coverage",
            "htmlcov",
            "pytest_cache",
            "relatorio_",
            "analise_",
            "report_",
            "extract_",
            "import_",
            "export_",
        ]

        return any(
            pattern in name or pattern in path_str for pattern in generated_patterns
        )

    def is_backup_file(self, file_path, file_info):
        """Verifica se é arquivo de backup"""
        name = file_info["name"].lower()
        path_str = str(file_path).lower()

        backup_patterns = [
            "backup",
            "bak",
            "old",
            "copy",
            "duplicate",
            "backup_",
            ".backup",
            ".bak",
            ".old",
        ]

        return any(
            pattern in name or pattern in path_str for pattern in backup_patterns
        )

    def analyze_all_files(self):
        """Analisa todos os arquivos do repositório"""
        print("📁 Analisando todos os arquivos...")

        all_files = set()

        # Adicionar arquivos rastreados
        all_files.update(self.analysis["files_analysis"]["tracked_files"])

        # Adicionar arquivos não rastreados
        all_files.update(self.analysis["files_analysis"]["untracked_files"])

        # Adicionar arquivos modificados
        all_files.update(self.analysis["files_analysis"]["modified_files"])

        # Adicionar arquivos deletados
        all_files.update(self.analysis["files_analysis"]["deleted_files"])

        # Analisar cada arquivo
        file_analyses = []
        categories = defaultdict(list)
        sizes = defaultdict(list)

        for file_path in all_files:
            file_info = self.analyze_file(file_path)
            if file_info:
                file_analyses.append(file_info)
                categories[file_info["category"]].append(file_info)
                sizes[file_info["category"]].append(file_info["size"])

        # Organizar análises
        self.analysis["files_analysis"]["total_files"] = len(file_analyses)
        self.analysis["files_analysis"]["file_categories"] = {
            category: {
                "count": len(files),
                "total_size": sum(f["size"] for f in files),
                "files": files,
            }
            for category, files in categories.items()
        }

        # Identificar arquivos problemáticos
        self.identify_problematic_files(file_analyses)

        # Analisar diretórios
        self.analyze_directories()

        return True

    def identify_problematic_files(self, file_analyses):
        """Identifica arquivos problemáticos"""
        unnecessary = []
        temporary = []
        generated = []
        backup = []
        large = []
        empty = []
        binary = []

        for file_info in file_analyses:
            if file_info["is_unnecessary"]:
                unnecessary.append(file_info)
            if file_info["is_temporary"]:
                temporary.append(file_info)
            if file_info["is_generated"]:
                generated.append(file_info)
            if file_info["is_backup"]:
                backup.append(file_info)
            if file_info["size"] > 1024 * 1024:  # > 1MB
                large.append(file_info)
            if file_info["is_empty"]:
                empty.append(file_info)
            if file_info["is_binary"]:
                binary.append(file_info)

        self.analysis["files_analysis"]["unnecessary_files"] = unnecessary
        self.analysis["files_analysis"]["temporary_files"] = temporary
        self.analysis["files_analysis"]["generated_files"] = generated
        self.analysis["files_analysis"]["backup_files"] = backup
        self.analysis["files_analysis"]["large_files"] = large
        self.analysis["files_analysis"]["empty_files"] = empty
        self.analysis["files_analysis"]["binary_files"] = binary

    def analyze_directories(self):
        """Analisa estrutura de diretórios"""
        print("📂 Analisando estrutura de diretórios...")

        directories = defaultdict(int)
        directory_sizes = defaultdict(int)

        for root, dirs, files in os.walk(self.root_path):
            # Pular diretórios do Git
            if ".git" in root or "__pycache__" in root:
                continue

            rel_root = os.path.relpath(root, self.root_path)
            if rel_root == ".":
                rel_root = "root"

            directories[rel_root] += len(files)

            # Calcular tamanho do diretório
            total_size = 0
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    total_size += os.path.getsize(file_path)
                except:
                    pass

            directory_sizes[rel_root] = total_size

        self.analysis["directory_analysis"] = {
            "directories": dict(directories),
            "directory_sizes": dict(directory_sizes),
            "total_directories": len(directories),
            "issues": [],
        }

        # Identificar diretórios problemáticos
        issues = []
        for dir_name, file_count in directories.items():
            if file_count > 100:
                issues.append(
                    {
                        "type": "too_many_files",
                        "directory": dir_name,
                        "count": file_count,
                        "description": f"Diretório com muitos arquivos ({file_count})",
                    }
                )

            if "temp" in dir_name.lower() or "tmp" in dir_name.lower():
                issues.append(
                    {
                        "type": "temporary_directory",
                        "directory": dir_name,
                        "description": "Diretório temporário que pode ser removido",
                    }
                )

        self.analysis["directory_analysis"]["issues"] = issues

    def generate_recommendations(self):
        """Gera recomendações de organização"""
        print("💡 Gerando recomendações...")

        recommendations = {
            "files_to_remove": [],
            "files_to_organize": [],
            "files_to_add_gitignore": [],
            "directories_to_clean": [],
            "structure_improvements": [],
        }

        # Arquivos para remover
        for file_info in self.analysis["files_analysis"]["unnecessary_files"]:
            recommendations["files_to_remove"].append(
                {
                    "file": file_info["path"],
                    "reason": "Arquivo desnecessário",
                    "size_mb": round(file_info["size"] / (1024 * 1024), 2),
                    "category": file_info["category"],
                }
            )

        for file_info in self.analysis["files_analysis"]["temporary_files"]:
            recommendations["files_to_remove"].append(
                {
                    "file": file_info["path"],
                    "reason": "Arquivo temporário",
                    "size_mb": round(file_info["size"] / (1024 * 1024), 2),
                    "category": file_info["category"],
                }
            )

        for file_info in self.analysis["files_analysis"]["backup_files"]:
            recommendations["files_to_remove"].append(
                {
                    "file": file_info["path"],
                    "reason": "Arquivo de backup",
                    "size_mb": round(file_info["size"] / (1024 * 1024), 2),
                    "category": file_info["category"],
                }
            )

        # Arquivos para adicionar ao .gitignore
        for file_info in self.analysis["files_analysis"]["generated_files"]:
            if (
                file_info["path"]
                not in self.analysis["files_analysis"]["tracked_files"]
            ):
                recommendations["files_to_add_gitignore"].append(
                    {
                        "file": file_info["path"],
                        "pattern": self.get_gitignore_pattern(file_info["path"]),
                        "reason": "Arquivo gerado automaticamente",
                    }
                )

        # Diretórios para limpar
        for issue in self.analysis["directory_analysis"]["issues"]:
            if issue["type"] == "temporary_directory":
                recommendations["directories_to_clean"].append(
                    {
                        "directory": issue["directory"],
                        "reason": issue["description"],
                        "action": "remove",
                    }
                )

        # Melhorias de estrutura
        recommendations["structure_improvements"] = [
            {
                "type": "organize_scripts",
                "description": "Organizar scripts em subdiretórios por categoria",
                "action": "Criar scripts/extracao/, scripts/oauth/, scripts/teste/",
            },
            {
                "type": "organize_reports",
                "description": "Centralizar relatórios em diretório específico",
                "action": "Criar reports/ e mover todos os relatórios",
            },
            {
                "type": "organize_data",
                "description": "Organizar arquivos de dados",
                "action": "Criar data/ e mover arquivos de dados",
            },
        ]

        self.analysis["recommendations"] = recommendations

    def get_gitignore_pattern(self, file_path):
        """Gera padrão para .gitignore"""
        name = Path(file_path).name

        if name.startswith("relatorio_"):
            return "relatorio_*.json"
        elif name.startswith("analise_"):
            return "analise_*.json"
        elif name.endswith(".backup"):
            return "*.backup"
        elif name.endswith(".log"):
            return "*.log"
        elif "temp" in name.lower():
            return "*temp*"
        else:
            return name

    def run_analysis(self):
        """Executa análise completa"""
        print("🔍 Iniciando análise completa do repositório GitHub...")
        print("=" * 70)

        # Obter status do Git
        print("📊 Coletando status do Git...")
        if not self.get_git_status():
            return False

        # Analisar todos os arquivos
        print("📁 Analisando todos os arquivos...")
        if not self.analyze_all_files():
            return False

        # Gerar recomendações
        print("💡 Gerando recomendações...")
        self.generate_recommendations()

        return True

    def save_analysis(self, filename=None):
        """Salva análise em arquivo JSON"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"relatorio_analise_completa_github_{timestamp}.json"

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.analysis, f, indent=2, ensure_ascii=False)

        print(f"📊 Análise completa salva em: {filename}")
        return filename

    def print_summary(self):
        """Imprime resumo da análise"""
        print("\n📊 RESUMO DA ANÁLISE COMPLETA:")
        print("=" * 60)

        files_analysis = self.analysis["files_analysis"]

        print(f"📁 Total de arquivos analisados: {files_analysis['total_files']}")
        print(f"📝 Arquivos rastreados: {len(files_analysis['tracked_files'])}")
        print(f"❓ Arquivos não rastreados: {len(files_analysis['untracked_files'])}")
        print(f"✏️ Arquivos modificados: {len(files_analysis['modified_files'])}")
        print(f"🗑️ Arquivos deletados: {len(files_analysis['deleted_files'])}")

        print(f"\n🔍 ARQUIVOS PROBLEMÁTICOS:")
        print(f"  • Desnecessários: {len(files_analysis['unnecessary_files'])}")
        print(f"  • Temporários: {len(files_analysis['temporary_files'])}")
        print(f"  • Gerados: {len(files_analysis['generated_files'])}")
        print(f"  • Backup: {len(files_analysis['backup_files'])}")
        print(f"  • Grandes (>1MB): {len(files_analysis['large_files'])}")
        print(f"  • Vazios: {len(files_analysis['empty_files'])}")
        print(f"  • Binários: {len(files_analysis['binary_files'])}")

        print(f"\n📂 CATEGORIAS DE ARQUIVOS:")
        categories = files_analysis["file_categories"]
        for category, info in sorted(
            categories.items(), key=lambda x: x[1]["count"], reverse=True
        ):
            size_mb = round(info["total_size"] / (1024 * 1024), 2)
            print(f"  • {category}: {info['count']} arquivos ({size_mb} MB)")

        print(f"\n💡 RECOMENDAÇÕES:")
        recommendations = self.analysis["recommendations"]
        print(f"  • Arquivos para remover: {len(recommendations['files_to_remove'])}")
        print(
            f"  • Arquivos para organizar: {len(recommendations['files_to_organize'])}"
        )
        print(
            f"  • Padrões para .gitignore: {len(recommendations['files_to_add_gitignore'])}"
        )
        print(
            f"  • Diretórios para limpar: {len(recommendations['directories_to_clean'])}"
        )
        print(
            f"  • Melhorias de estrutura: {len(recommendations['structure_improvements'])}"
        )


def main():
    """Função principal"""
    print("🔍 Análise Completa do Repositório GitHub - Sistema Aprender")
    print("=" * 70)

    analyzer = GitHubCompleteAnalyzer()

    if analyzer.run_analysis():
        # Salvar análise
        report_file = analyzer.save_analysis()

        # Mostrar resumo
        analyzer.print_summary()

        print(f"\n📄 Relatório completo salvo em: {report_file}")
        print("\n✅ Análise completa concluída!")
    else:
        print("\n❌ Erro durante a análise!")


if __name__ == "__main__":
    main()
