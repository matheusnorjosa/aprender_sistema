#!/usr/bin/env python
"""
Script de vistoria refinada do projeto.
Identifica arquivos órfãos/legados e gera plano de organização.
"""
import json
import os
import pathlib
import subprocess
from datetime import datetime
from typing import Dict, List, Set


def get_repo_root():
    """Detecta raiz do repositório via git."""
    try:
        result = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], text=True
        )
        return pathlib.Path(result.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback: subir diretórios até encontrar .git
        current = pathlib.Path.cwd()
        while current != current.parent:
            if (current / ".git").exists():
                return current
            current = current.parent
        return pathlib.Path.cwd()


def get_docs_root():
    """Detecta DOCS_ROOT."""
    try:
        from django.conf import settings

        return pathlib.Path(settings.DOCS_ROOT)
    except ImportError:
        return get_repo_root() / "docs"


def classify_file(file_path: pathlib.Path, repo_root: pathlib.Path) -> Dict:
    """Classifica um arquivo baseado nas regras do contexto supremo."""
    relative_path = file_path.relative_to(repo_root)
    name = file_path.name.lower()
    parent = file_path.parent.name.lower()

    # Padrões de arquivos problemáticos
    problematic_patterns = [
        # Status AGENDADO em ingestão
        ("agendado", "status_agendado_ingestao"),
        # Scripts que escrevem fora de DOCS_ROOT
        ("docs/", "writes_outside_docs_root"),
        # Arquivos de credenciais
        ("credentials", "credentials_file"),
        ("service_account", "credentials_file"),
        ("api_key", "credentials_file"),
        # Dumps e backups
        ("dump", "backup_file"),
        ("backup", "backup_file"),
        ("*.sql", "backup_file"),
        # Arquivos temporários
        ("temp_", "temp_file"),
        ("tmp_", "temp_file"),
        ("_temp", "temp_file"),
        # Arquivos de desenvolvimento
        ("test_", "dev_file"),
        ("debug_", "dev_file"),
        ("_debug", "dev_file"),
    ]

    # Verificar padrões problemáticos
    for pattern, category in problematic_patterns:
        if pattern in name or pattern in str(relative_path):
            return {
                "action": (
                    "remove"
                    if category in ["temp_file", "dev_file"]
                    else "move_to_archive"
                ),
                "category": category,
                "reason": f"Padrão problemático: {pattern}",
            }

    # Arquivos de documentação fora de docs/
    if (
        name.endswith((".md", ".json", ".csv"))
        and "relatorio" in name
        or "auditoria" in name
        or "inventario" in name
    ):
        if not str(relative_path).startswith("docs/"):
            return {
                "action": "move_to_docs",
                "category": "documentation_outside_docs",
                "reason": "Documentação fora de docs/",
            }

    # Arquivos de dados sensíveis
    if any(sensitive in name for sensitive in ["password", "secret", "key", "token"]):
        return {
            "action": "move_to_archive",
            "category": "sensitive_data",
            "reason": "Dados sensíveis",
        }

    # Arquivos de configuração local
    if name.startswith(".") and name not in [
        ".gitignore",
        ".gitattributes",
        ".editorconfig",
    ]:
        return {
            "action": "move_to_archive",
            "category": "local_config",
            "reason": "Configuração local",
        }

    return {"action": "keep", "category": "normal", "reason": "Arquivo normal"}


def scan_project(repo_root: pathlib.Path) -> Dict:
    """Escaneia todo o projeto e classifica arquivos."""
    print(f"🔍 Escaneando projeto: {repo_root}")

    results = {
        "scan_timestamp": datetime.now().isoformat(),
        "repo_root": str(repo_root),
        "docs_root": str(get_docs_root()),
        "files": {},
        "summary": {
            "total_files": 0,
            "keep": 0,
            "move_to_docs": 0,
            "move_to_archive": 0,
            "remove": 0,
        },
    }

    # Ignorar pastas
    ignore_dirs = {
        ".git",
        "__pycache__",
        "node_modules",
        ".pytest_cache",
        "venv",
        "env",
        ".venv",
        "ENV",
        "env.bak",
        "venv.bak",
        "staticfiles",
        "media",
        "logs",
        "backups",
        "dumps",
    }

    # Ignorar extensões
    ignore_extensions = {
        ".pyc",
        ".pyo",
        ".pyd",
        ".so",
        ".dll",
        ".exe",
        ".log",
        ".tmp",
        ".temp",
        ".bak",
        ".backup",
    }

    for file_path in repo_root.rglob("*"):
        if not file_path.is_file():
            continue

        # Pular arquivos ignorados
        if any(part in ignore_dirs for part in file_path.parts):
            continue

        if file_path.suffix.lower() in ignore_extensions:
            continue

        # Pular arquivos muito grandes (>10MB)
        try:
            if file_path.stat().st_size > 10 * 1024 * 1024:
                continue
        except OSError:
            continue

        relative_path = file_path.relative_to(repo_root)
        classification = classify_file(file_path, repo_root)

        results["files"][str(relative_path)] = {
            "absolute_path": str(file_path),
            "size_bytes": file_path.stat().st_size,
            "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
            **classification,
        }

        results["summary"]["total_files"] += 1
        results["summary"][classification["action"]] += 1

    return results


def generate_migration_plan(results: Dict) -> Dict:
    """Gera plano de migração baseado nos resultados."""
    repo_root = pathlib.Path(results["repo_root"])
    docs_root = pathlib.Path(results["docs_root"])

    plan = {
        "migration_timestamp": datetime.now().isoformat(),
        "actions": [],
        "git_commands": [],
        "file_operations": [],
    }

    # Criar estrutura de pastas necessária
    plan["file_operations"].append(
        {"type": "mkdir", "path": str(docs_root), "reason": "Garantir que docs/ existe"}
    )

    plan["file_operations"].append(
        {
            "type": "mkdir",
            "path": str(repo_root / "archive"),
            "reason": "Pasta para arquivos movidos",
        }
    )

    for file_path, info in results["files"].items():
        if info["action"] == "keep":
            continue

        source = repo_root / file_path
        action = info["action"]
        category = info["category"]
        reason = info["reason"]

        if action == "move_to_docs":
            # Mover para docs/ mantendo estrutura
            dest = docs_root / file_path
            dest.parent.mkdir(parents=True, exist_ok=True)

            plan["file_operations"].append(
                {
                    "type": "move",
                    "source": str(source),
                    "destination": str(dest),
                    "reason": reason,
                }
            )

            if source.is_file() and str(source).startswith(str(repo_root)):
                plan["git_commands"].append(
                    f"git mv '{source.relative_to(repo_root)}' '{dest.relative_to(repo_root)}'"
                )

        elif action == "move_to_archive":
            # Mover para archive/
            dest = repo_root / "archive" / file_path
            dest.parent.mkdir(parents=True, exist_ok=True)

            plan["file_operations"].append(
                {
                    "type": "move",
                    "source": str(source),
                    "destination": str(dest),
                    "reason": reason,
                }
            )

            if source.is_file() and str(source).startswith(str(repo_root)):
                plan["git_commands"].append(
                    f"git mv '{source.relative_to(repo_root)}' '{dest.relative_to(repo_root)}'"
                )

        elif action == "remove":
            # Remover arquivo
            plan["file_operations"].append(
                {"type": "remove", "source": str(source), "reason": reason}
            )

            if source.is_file() and str(source).startswith(str(repo_root)):
                plan["git_commands"].append(f"git rm '{source.relative_to(repo_root)}'")

    return plan


def main():
    """Executa vistoria completa do projeto."""
    print("🔍 VISTORIA REFINADA DO PROJETO")
    print("=" * 60)

    repo_root = get_repo_root()
    docs_root = get_docs_root()

    print(f"Repo root: {repo_root}")
    print(f"Docs root: {docs_root}")

    # Escanear projeto
    results = scan_project(repo_root)

    # Gerar plano de migração
    plan = generate_migration_plan(results)

    # Salvar resultados
    docs_root.mkdir(parents=True, exist_ok=True)

    results_file = docs_root / "RELATORIO_VISTORIA_DRYRUN.json"
    results_file.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    plan_file = docs_root / "PLANO_MIGRACAO_VISTORIA.json"
    plan_file.write_text(
        json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Gerar relatório markdown
    report_md = f"""# 🔍 RELATÓRIO DE VISTORIA - DRY RUN

**Data:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Repo Root:** {repo_root}
**Docs Root:** {docs_root}

## 📊 RESUMO

- **Total de arquivos:** {results['summary']['total_files']}
- **Manter:** {results['summary']['keep']}
- **Mover para docs/:** {results['summary']['move_to_docs']}
- **Mover para archive/:** {results['summary']['move_to_archive']}
- **Remover:** {results['summary']['remove']}

## 📋 AÇÕES PLANEJADAS

### Mover para docs/ ({results['summary']['move_to_docs']} arquivos)
"""

    for file_path, info in results["files"].items():
        if info["action"] == "move_to_docs":
            report_md += f"- `{file_path}` → `docs/{file_path}` ({info['reason']})\n"

    report_md += f"""
### Mover para archive/ ({results['summary']['move_to_archive']} arquivos)
"""

    for file_path, info in results["files"].items():
        if info["action"] == "move_to_archive":
            report_md += f"- `{file_path}` → `archive/{file_path}` ({info['reason']})\n"

    report_md += f"""
### Remover ({results['summary']['remove']} arquivos)
"""

    for file_path, info in results["files"].items():
        if info["action"] == "remove":
            report_md += f"- `{file_path}` ({info['reason']})\n"

    report_md += f"""
## 🔧 COMANDOS GIT PLANEJADOS

```bash
# Criar estrutura
mkdir -p docs archive

# Comandos de migração
"""

    for cmd in plan["git_commands"]:
        report_md += f"{cmd}\n"

    report_md += """
```

## 📁 ARQUIVOS GERADOS

- `docs/RELATORIO_VISTORIA_DRYRUN.json` - Dados completos
- `docs/PLANO_MIGRACAO_VISTORIA.json` - Plano de execução

## ⚠️ PRÓXIMOS PASSOS

1. Revisar o plano de migração
2. Executar `devops/apply_vistoria_plan.py` para aplicar
3. Verificar que todos os relatórios saem em docs/
4. Executar auditoria full para validar
"""

    report_file = docs_root / "RELATORIO_VISTORIA_DRYRUN.md"
    report_file.write_text(report_md, encoding="utf-8")

    print(f"\n✅ Vistoria concluída!")
    print(f"📊 Total: {results['summary']['total_files']} arquivos")
    print(f"📁 Manter: {results['summary']['keep']}")
    print(f"📄 Mover para docs/: {results['summary']['move_to_docs']}")
    print(f"📦 Mover para archive/: {results['summary']['move_to_archive']}")
    print(f"🗑️  Remover: {results['summary']['remove']}")
    print(f"\n📋 Relatórios salvos em: {docs_root}")
    print(f"   - RELATORIO_VISTORIA_DRYRUN.md")
    print(f"   - RELATORIO_VISTORIA_DRYRUN.json")
    print(f"   - PLANO_MIGRACAO_VISTORIA.json")


if __name__ == "__main__":
    main()
