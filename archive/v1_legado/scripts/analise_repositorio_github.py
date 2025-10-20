#!/usr/bin/env python3
"""
Análise Completa do Repositório GitHub
=====================================

Script para analisar o repositório GitHub do Sistema Aprender,
identificando duplicatas, problemas de organização e oportunidades
de otimização.

Author: Claude Code
Date: Janeiro 2025
"""

import hashlib
import json
import os
import re
import subprocess
from collections import defaultdict
from datetime import datetime
from pathlib import Path


class GitHubRepositoryAnalyzer:
    """Analisador do repositório GitHub"""

    def __init__(self, root_path="."):
        self.root_path = Path(root_path)
        self.analysis = {
            "timestamp": datetime.now().isoformat(),
            "repository_info": {},
            "branches_analysis": {},
            "commits_analysis": {},
            "files_analysis": {},
            "duplicates_found": [],
            "issues_identified": [],
            "recommendations": [],
        }

    def get_git_info(self):
        """Obtém informações básicas do Git"""
        try:
            # URL do repositório
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                cwd=self.root_path,
            )
            self.analysis["repository_info"]["url"] = result.stdout.strip()

            # Branch atual
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                cwd=self.root_path,
            )
            self.analysis["repository_info"]["current_branch"] = result.stdout.strip()

            # Status do repositório
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                cwd=self.root_path,
            )
            self.analysis["repository_info"]["status"] = result.stdout.strip()

            # Último commit
            result = subprocess.run(
                ["git", "log", "-1", "--format=%H|%s|%an|%ad"],
                capture_output=True,
                text=True,
                cwd=self.root_path,
            )
            if result.stdout.strip():
                commit_info = result.stdout.strip().split("|")
                self.analysis["repository_info"]["last_commit"] = {
                    "hash": commit_info[0],
                    "message": commit_info[1],
                    "author": commit_info[2],
                    "date": commit_info[3],
                }

            return True

        except Exception as e:
            print(f"Erro ao obter informações do Git: {e}")
            return False

    def analyze_branches(self):
        """Analisa branches do repositório"""
        try:
            # Branches locais
            result = subprocess.run(
                ["git", "branch"], capture_output=True, text=True, cwd=self.root_path
            )
            local_branches = [
                line.strip().replace("* ", "")
                for line in result.stdout.split("\n")
                if line.strip()
            ]

            # Branches remotas
            result = subprocess.run(
                ["git", "branch", "-r"],
                capture_output=True,
                text=True,
                cwd=self.root_path,
            )
            remote_branches = [
                line.strip()
                for line in result.stdout.split("\n")
                if line.strip() and "origin/HEAD" not in line
            ]

            # Análise de branches
            self.analysis["branches_analysis"] = {
                "local_branches": local_branches,
                "remote_branches": remote_branches,
                "total_branches": len(local_branches) + len(remote_branches),
                "issues": [],
            }

            # Identificar problemas
            issues = []

            # Branches órfãs (locais sem remoto)
            for branch in local_branches:
                if branch != "main" and f"origin/{branch}" not in remote_branches:
                    issues.append(
                        {
                            "type": "orphan_branch",
                            "branch": branch,
                            "description": "Branch local sem correspondente remoto",
                        }
                    )

            # Branches antigas
            for branch in local_branches:
                if branch.startswith("backup_") or branch.startswith("backup/"):
                    issues.append(
                        {
                            "type": "old_backup_branch",
                            "branch": branch,
                            "description": "Branch de backup que pode ser removida",
                        }
                    )

            # Muitas branches feature
            feature_branches = [b for b in local_branches if b.startswith("feature/")]
            if len(feature_branches) > 5:
                issues.append(
                    {
                        "type": "too_many_feature_branches",
                        "count": len(feature_branches),
                        "description": "Muitas branches feature ativas",
                    }
                )

            self.analysis["branches_analysis"]["issues"] = issues

            return True

        except Exception as e:
            print(f"Erro ao analisar branches: {e}")
            return False

    def analyze_commits(self):
        """Analisa histórico de commits"""
        try:
            # Últimos 50 commits
            result = subprocess.run(
                ["git", "log", "--oneline", "-50"],
                capture_output=True,
                text=True,
                cwd=self.root_path,
            )
            commits = [
                line.strip() for line in result.stdout.split("\n") if line.strip()
            ]

            # Análise de padrões de commit
            commit_patterns = {
                "feat": 0,
                "fix": 0,
                "docs": 0,
                "chore": 0,
                "refactor": 0,
                "test": 0,
                "other": 0,
            }

            issues = []

            for commit in commits:
                if commit:
                    # Extrair tipo do commit
                    if commit.startswith("feat:"):
                        commit_patterns["feat"] += 1
                    elif commit.startswith("fix:"):
                        commit_patterns["fix"] += 1
                    elif commit.startswith("docs:"):
                        commit_patterns["docs"] += 1
                    elif commit.startswith("chore:"):
                        commit_patterns["chore"] += 1
                    elif commit.startswith("refactor:"):
                        commit_patterns["refactor"] += 1
                    elif commit.startswith("test:"):
                        commit_patterns["test"] += 1
                    else:
                        commit_patterns["other"] += 1

                        # Identificar commits não padronizados
                        if not any(
                            commit.startswith(prefix)
                            for prefix in [
                                "feat:",
                                "fix:",
                                "docs:",
                                "chore:",
                                "refactor:",
                                "test:",
                            ]
                        ):
                            issues.append(
                                {
                                    "type": "non_standard_commit",
                                    "commit": commit,
                                    "description": "Commit não segue padrão conventional commits",
                                }
                            )

            self.analysis["commits_analysis"] = {
                "total_commits_analyzed": len(commits),
                "commit_patterns": commit_patterns,
                "issues": issues,
            }

            return True

        except Exception as e:
            print(f"Erro ao analisar commits: {e}")
            return False

    def analyze_files(self):
        """Analisa arquivos do repositório"""
        try:
            # Arquivos rastreados pelo Git
            result = subprocess.run(
                ["git", "ls-files"], capture_output=True, text=True, cwd=self.root_path
            )
            tracked_files = [
                line.strip() for line in result.stdout.split("\n") if line.strip()
            ]

            # Arquivos não rastreados
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                cwd=self.root_path,
            )
            untracked_files = []
            modified_files = []

            for line in result.stdout.split("\n"):
                if line.strip():
                    if line.startswith("??"):
                        untracked_files.append(line[3:].strip())
                    elif line.startswith(" M") or line.startswith("M "):
                        modified_files.append(line[3:].strip())

            # Análise de tipos de arquivo
            file_types = defaultdict(int)
            large_files = []
            duplicate_files = []

            for file_path in tracked_files:
                full_path = self.root_path / file_path
                if full_path.exists():
                    # Tipo de arquivo
                    ext = full_path.suffix.lower()
                    file_types[ext] += 1

                    # Arquivos grandes
                    size = full_path.stat().st_size
                    if size > 1024 * 1024:  # > 1MB
                        large_files.append(
                            {
                                "file": file_path,
                                "size_mb": round(size / (1024 * 1024), 2),
                            }
                        )

            # Identificar duplicatas por hash
            file_hashes = defaultdict(list)
            for file_path in tracked_files:
                full_path = self.root_path / file_path
                if full_path.exists() and full_path.is_file():
                    try:
                        with open(full_path, "rb") as f:
                            file_hash = hashlib.md5(f.read()).hexdigest()
                            file_hashes[file_hash].append(file_path)
                    except:
                        pass

            for hash_val, files in file_hashes.items():
                if len(files) > 1:
                    duplicate_files.append(
                        {"hash": hash_val, "files": files, "count": len(files)}
                    )

            self.analysis["files_analysis"] = {
                "tracked_files": len(tracked_files),
                "untracked_files": len(untracked_files),
                "modified_files": len(modified_files),
                "file_types": dict(file_types),
                "large_files": large_files,
                "duplicate_files": duplicate_files,
                "issues": [],
            }

            # Identificar problemas
            issues = []

            # Muitos arquivos não rastreados
            if len(untracked_files) > 20:
                issues.append(
                    {
                        "type": "too_many_untracked",
                        "count": len(untracked_files),
                        "description": "Muitos arquivos não rastreados pelo Git",
                    }
                )

            # Arquivos grandes
            if large_files:
                issues.append(
                    {
                        "type": "large_files",
                        "files": large_files,
                        "description": "Arquivos grandes que podem impactar performance",
                    }
                )

            # Duplicatas
            if duplicate_files:
                issues.append(
                    {
                        "type": "duplicate_files",
                        "files": duplicate_files,
                        "description": "Arquivos duplicados encontrados",
                    }
                )

            self.analysis["files_analysis"]["issues"] = issues

            return True

        except Exception as e:
            print(f"Erro ao analisar arquivos: {e}")
            return False

    def analyze_github_config(self):
        """Analisa configurações do GitHub"""
        try:
            github_dir = self.root_path / ".github"
            config_analysis = {
                "workflows": [],
                "templates": [],
                "config_files": [],
                "issues": [],
            }

            if github_dir.exists():
                # Workflows
                workflows_dir = github_dir / "workflows"
                if workflows_dir.exists():
                    for workflow_file in workflows_dir.glob("*.yml"):
                        config_analysis["workflows"].append(
                            str(workflow_file.relative_to(self.root_path))
                        )

                # Templates
                templates_dir = github_dir / "ISSUE_TEMPLATE"
                if templates_dir.exists():
                    for template_file in templates_dir.glob("*.md"):
                        config_analysis["templates"].append(
                            str(template_file.relative_to(self.root_path))
                        )

                # Arquivos de configuração
                config_files = [
                    "dependabot.yml",
                    "CODEOWNERS",
                    "PULL_REQUEST_TEMPLATE.md",
                ]
                for config_file in config_files:
                    if (github_dir / config_file).exists():
                        config_analysis["config_files"].append(config_file)

            # Verificar se tem configurações essenciais
            issues = []
            if not config_analysis["workflows"]:
                issues.append(
                    {
                        "type": "missing_ci_cd",
                        "description": "Nenhum workflow de CI/CD configurado",
                    }
                )

            if not config_analysis["templates"]:
                issues.append(
                    {
                        "type": "missing_issue_templates",
                        "description": "Templates de issues não configurados",
                    }
                )

            if "CODEOWNERS" not in config_analysis["config_files"]:
                issues.append(
                    {
                        "type": "missing_codeowners",
                        "description": "Arquivo CODEOWNERS não configurado",
                    }
                )

            config_analysis["issues"] = issues
            self.analysis["github_config"] = config_analysis

            return True

        except Exception as e:
            print(f"Erro ao analisar configurações do GitHub: {e}")
            return False

    def generate_recommendations(self):
        """Gera recomendações baseadas na análise"""
        recommendations = []

        # Recomendações para branches
        if self.analysis["branches_analysis"]["issues"]:
            branch_issues = self.analysis["branches_analysis"]["issues"]
            if any(issue["type"] == "orphan_branch" for issue in branch_issues):
                recommendations.append(
                    {
                        "category": "branches",
                        "priority": "medium",
                        "title": "Limpar branches órfãs",
                        "description": "Remover branches locais que não têm correspondente remoto",
                        "action": "git branch -d <branch_name>",
                    }
                )

            if any(issue["type"] == "old_backup_branch" for issue in branch_issues):
                recommendations.append(
                    {
                        "category": "branches",
                        "priority": "low",
                        "title": "Remover branches de backup antigas",
                        "description": "Branches de backup podem ser removidas após confirmação",
                        "action": "git branch -D backup_*",
                    }
                )

        # Recomendações para commits
        if self.analysis["commits_analysis"]["issues"]:
            commit_issues = self.analysis["commits_analysis"]["issues"]
            if any(issue["type"] == "non_standard_commit" for issue in commit_issues):
                recommendations.append(
                    {
                        "category": "commits",
                        "priority": "medium",
                        "title": "Padronizar mensagens de commit",
                        "description": "Implementar conventional commits para melhor rastreabilidade",
                        "action": "Usar formato: type(scope): description",
                    }
                )

        # Recomendações para arquivos
        if self.analysis["files_analysis"]["issues"]:
            file_issues = self.analysis["files_analysis"]["issues"]
            if any(issue["type"] == "too_many_untracked" for issue in file_issues):
                recommendations.append(
                    {
                        "category": "files",
                        "priority": "high",
                        "title": "Organizar arquivos não rastreados",
                        "description": "Adicionar ao .gitignore ou commitar arquivos necessários",
                        "action": "Revisar e organizar arquivos untracked",
                    }
                )

            if any(issue["type"] == "duplicate_files" for issue in file_issues):
                recommendations.append(
                    {
                        "category": "files",
                        "priority": "medium",
                        "title": "Remover arquivos duplicados",
                        "description": "Consolidar arquivos duplicados para reduzir tamanho do repo",
                        "action": "Identificar e remover duplicatas",
                    }
                )

        # Recomendações para configuração GitHub
        if (
            "github_config" in self.analysis
            and self.analysis["github_config"]["issues"]
        ):
            github_issues = self.analysis["github_config"]["issues"]
            if any(issue["type"] == "missing_ci_cd" for issue in github_issues):
                recommendations.append(
                    {
                        "category": "github",
                        "priority": "high",
                        "title": "Implementar CI/CD",
                        "description": "Configurar workflows de CI/CD para automação",
                        "action": "Criar .github/workflows/ci.yml",
                    }
                )

        self.analysis["recommendations"] = recommendations

    def run_analysis(self):
        """Executa análise completa"""
        print("🔍 Iniciando análise do repositório GitHub...")
        print("=" * 60)

        # Obter informações básicas
        print("📊 Coletando informações do Git...")
        if not self.get_git_info():
            return False

        # Analisar branches
        print("🌳 Analisando branches...")
        if not self.analyze_branches():
            return False

        # Analisar commits
        print("📝 Analisando commits...")
        if not self.analyze_commits():
            return False

        # Analisar arquivos
        print("📁 Analisando arquivos...")
        if not self.analyze_files():
            return False

        # Analisar configurações GitHub
        print("⚙️ Analisando configurações GitHub...")
        if not self.analyze_github_config():
            return False

        # Gerar recomendações
        print("💡 Gerando recomendações...")
        self.generate_recommendations()

        return True

    def save_analysis(self, filename=None):
        """Salva análise em arquivo JSON"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"relatorio_analise_github_{timestamp}.json"

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.analysis, f, indent=2, ensure_ascii=False)

        print(f"📊 Análise salva em: {filename}")
        return filename

    def print_summary(self):
        """Imprime resumo da análise"""
        print("\n📊 RESUMO DA ANÁLISE DO REPOSITÓRIO:")
        print("=" * 50)

        # Informações básicas
        repo_info = self.analysis["repository_info"]
        print(f"🔗 Repositório: {repo_info.get('url', 'N/A')}")
        print(f"🌿 Branch atual: {repo_info.get('current_branch', 'N/A')}")
        print(
            f"📝 Último commit: {repo_info.get('last_commit', {}).get('message', 'N/A')}"
        )

        # Branches
        branches = self.analysis["branches_analysis"]
        print(f"\n🌳 Branches:")
        print(f"  • Total: {branches.get('total_branches', 0)}")
        print(f"  • Locais: {len(branches.get('local_branches', []))}")
        print(f"  • Remotas: {len(branches.get('remote_branches', []))}")
        print(f"  • Problemas: {len(branches.get('issues', []))}")

        # Commits
        commits = self.analysis["commits_analysis"]
        print(f"\n📝 Commits:")
        print(f"  • Analisados: {commits.get('total_commits_analyzed', 0)}")
        patterns = commits.get("commit_patterns", {})
        for pattern, count in patterns.items():
            if count > 0:
                print(f"  • {pattern}: {count}")
        print(f"  • Problemas: {len(commits.get('issues', []))}")

        # Arquivos
        files = self.analysis["files_analysis"]
        print(f"\n📁 Arquivos:")
        print(f"  • Rastreados: {files.get('tracked_files', 0)}")
        print(f"  • Não rastreados: {files.get('untracked_files', 0)}")
        print(f"  • Modificados: {files.get('modified_files', 0)}")
        print(f"  • Duplicados: {len(files.get('duplicate_files', []))}")
        print(f"  • Grandes: {len(files.get('large_files', []))}")

        # Configurações GitHub
        if "github_config" in self.analysis:
            github = self.analysis["github_config"]
            print(f"\n⚙️ Configurações GitHub:")
            print(f"  • Workflows: {len(github.get('workflows', []))}")
            print(f"  • Templates: {len(github.get('templates', []))}")
            print(f"  • Configs: {len(github.get('config_files', []))}")
            print(f"  • Problemas: {len(github.get('issues', []))}")

        # Recomendações
        recommendations = self.analysis["recommendations"]
        print(f"\n💡 Recomendações: {len(recommendations)}")
        for rec in recommendations:
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                rec["priority"], "⚪"
            )
            print(f"  {priority_emoji} {rec['title']}")


def main():
    """Função principal"""
    print("🔍 Análise do Repositório GitHub - Sistema Aprender")
    print("=" * 60)

    analyzer = GitHubRepositoryAnalyzer()

    if analyzer.run_analysis():
        # Salvar análise
        report_file = analyzer.save_analysis()

        # Mostrar resumo
        analyzer.print_summary()

        print(f"\n📄 Relatório completo salvo em: {report_file}")
        print("\n✅ Análise concluída!")
    else:
        print("\n❌ Erro durante a análise!")


if __name__ == "__main__":
    main()
