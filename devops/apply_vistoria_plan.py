#!/usr/bin/env python
"""
Script para aplicar o plano de vistoria.
Executa as operações de migração de arquivos de forma segura.
"""
import json
import pathlib
import shutil
import subprocess
import sys
from datetime import datetime


def load_plan(plan_file: pathlib.Path) -> dict:
    """Carrega o plano de migração."""
    if not plan_file.exists():
        print(f"❌ Plano não encontrado: {plan_file}")
        sys.exit(1)

    return json.loads(plan_file.read_text(encoding="utf-8"))


def execute_git_commands(commands: list) -> bool:
    """Executa comandos git de forma segura."""
    print("🔧 Executando comandos Git...")

    for cmd in commands:
        print(f"  → {cmd}")
        try:
            result = subprocess.run(
                cmd, shell=True, check=True, capture_output=True, text=True
            )
            print(f"    ✓ Sucesso")
        except subprocess.CalledProcessError as e:
            print(f"    ❌ Erro: {e.stderr}")
            return False

    return True


def execute_file_operations(operations: list) -> bool:
    """Executa operações de arquivo de forma segura."""
    print("📁 Executando operações de arquivo...")

    for op in operations:
        op_type = op["type"]
        source = pathlib.Path(op["source"])
        reason = op["reason"]

        print(f"  → {op_type}: {source} ({reason})")

        try:
            if op_type == "mkdir":
                source.mkdir(parents=True, exist_ok=True)
                print(f"    ✓ Pasta criada")

            elif op_type == "move":
                dest = pathlib.Path(op["destination"])
                dest.parent.mkdir(parents=True, exist_ok=True)

                if source.exists():
                    shutil.move(str(source), str(dest))
                    print(f"    ✓ Movido para {dest}")
                else:
                    print(f"    ⚠ Arquivo não existe: {source}")

            elif op_type == "remove":
                if source.exists():
                    source.unlink()
                    print(f"    ✓ Removido")
                else:
                    print(f"    ⚠ Arquivo não existe: {source}")

        except Exception as e:
            print(f"    ❌ Erro: {e}")
            return False

    return True


def create_migration_manifest(plan: dict, results_file: pathlib.Path) -> dict:
    """Cria manifest de migração."""
    manifest = {
        "migration_timestamp": datetime.now().isoformat(),
        "plan_file": str(results_file),
        "operations_executed": len(plan["file_operations"]),
        "git_commands_executed": len(plan["git_commands"]),
        "files_moved": [],
        "files_removed": [],
        "folders_created": [],
    }

    for op in plan["file_operations"]:
        if op["type"] == "move":
            manifest["files_moved"].append(
                {"from": op["source"], "to": op["destination"], "reason": op["reason"]}
            )
        elif op["type"] == "remove":
            manifest["files_removed"].append(
                {"file": op["source"], "reason": op["reason"]}
            )
        elif op["type"] == "mkdir":
            manifest["folders_created"].append(op["path"])

    return manifest


def main():
    """Aplica o plano de vistoria."""
    print("🚀 APLICANDO PLANO DE VISTORIA")
    print("=" * 60)

    # Detectar docs root
    try:
        from django.conf import settings

        docs_root = pathlib.Path(settings.DOCS_ROOT)
    except ImportError:
        docs_root = pathlib.Path("docs")

    plan_file = docs_root / "PLANO_MIGRACAO_VISTORIA.json"
    results_file = docs_root / "RELATORIO_VISTORIA_DRYRUN.json"

    if not plan_file.exists():
        print(f"❌ Plano não encontrado: {plan_file}")
        print("Execute primeiro: python devops/vistoria_projeto.py")
        sys.exit(1)

    # Carregar plano
    plan = load_plan(plan_file)

    print(f"📋 Plano carregado:")
    print(f"   - Operações de arquivo: {len(plan['file_operations'])}")
    print(f"   - Comandos Git: {len(plan['git_commands'])}")

    # Confirmar execução
    response = input("\n⚠️  Continuar com a aplicação? (y/N): ")
    if response.lower() != "y":
        print("❌ Operação cancelada")
        sys.exit(0)

    # Executar operações
    success = True

    # 1. Operações de arquivo
    if plan["file_operations"]:
        success &= execute_file_operations(plan["file_operations"])

    # 2. Comandos Git
    if plan["git_commands"]:
        success &= execute_git_commands(plan["git_commands"])

    if not success:
        print("\n❌ Algumas operações falharam!")
        sys.exit(1)

    # Criar manifest de migração
    manifest = create_migration_manifest(plan, results_file)
    manifest_file = docs_root / "MIGRATION_MANIFEST.json"
    manifest_file.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Gerar relatório final
    report_md = f"""# ✅ RELATÓRIO DE VISTORIA APLICADA

**Data:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Status:** ✅ CONCLUÍDO COM SUCESSO

## 📊 RESUMO DA MIGRAÇÃO

- **Operações executadas:** {manifest['operations_executed']}
- **Comandos Git executados:** {manifest['git_commands_executed']}
- **Arquivos movidos:** {len(manifest['files_moved'])}
- **Arquivos removidos:** {len(manifest['files_removed'])}
- **Pastas criadas:** {len(manifest['folders_created'])}

## 📁 ARQUIVOS MOVIDOS

"""

    for move in manifest["files_moved"]:
        report_md += f"- `{move['from']}` → `{move['to']}` ({move['reason']})\n"

    report_md += f"""
## 🗑️ ARQUIVOS REMOVIDOS

"""

    for remove in manifest["files_removed"]:
        report_md += f"- `{remove['file']}` ({remove['reason']})\n"

    report_md += f"""
## 📂 PASTAS CRIADAS

"""

    for folder in manifest["folders_created"]:
        report_md += f"- `{folder}`\n"

    report_md += f"""
## 📋 ARQUIVOS GERADOS

- `docs/MIGRATION_MANIFEST.json` - Manifest da migração
- `docs/RELATORIO_VISTORIA_APLICADA.md` - Este relatório

## ✅ PRÓXIMOS PASSOS

1. Verificar que todos os relatórios saem em docs/
2. Executar auditoria full para validar
3. Commit das mudanças: `git add . && git commit -m "chore(docs): centraliza saída em DOCS_ROOT e migra artefatos"`
4. Tag opcional: `git tag v2025.10.08-organizacao`
"""

    report_file = docs_root / "RELATORIO_VISTORIA_APLICADA.md"
    report_file.write_text(report_md, encoding="utf-8")

    print(f"\n✅ Vistoria aplicada com sucesso!")
    print(f"📊 Operações: {manifest['operations_executed']}")
    print(f"📁 Movidos: {len(manifest['files_moved'])}")
    print(f"🗑️  Removidos: {len(manifest['files_removed'])}")
    print(f"\n📋 Relatórios salvos em: {docs_root}")
    print(f"   - RELATORIO_VISTORIA_APLICADA.md")
    print(f"   - MIGRATION_MANIFEST.json")


if __name__ == "__main__":
    main()
