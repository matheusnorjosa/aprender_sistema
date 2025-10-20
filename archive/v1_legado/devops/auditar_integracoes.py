"""
Auditoria de integrações MCP + Anthropic.

Verifica disponibilidade e configuração de integrações críticas:
- Anthropic API (Claude)
- MCP Server
- Service Accounts e credenciais
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys


def main():
    """Executa auditoria completa de integrações."""
    print("🔍 AUDITORIA DE INTEGRAÇÕES")
    print("=" * 60)

    # Usar DOCS_ROOT se disponível (Django) ou detectar repo root
    try:
        from django.conf import settings

        OUT = pathlib.Path(settings.DOCS_ROOT) / "inventario_integracoes"
    except ImportError:
        # Fallback: detectar repo root via git
        import subprocess

        try:
            repo_root = subprocess.check_output(
                ["git", "rev-parse", "--show-toplevel"], text=True
            ).strip()
            OUT = pathlib.Path(repo_root) / "docs" / "inventario_integracoes"
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fallback final: usar diretório atual
            OUT = pathlib.Path("docs/inventario_integracoes")

    OUT.mkdir(parents=True, exist_ok=True)
    print(f"DOCS_ROOT={OUT.parent}")

    res = {
        "anthropic": {
            "installed": False,
            "key_configured": bool(os.getenv("ANTHROPIC_API_KEY")),
            "ping": None,
        },
        "mcp": {
            "manifest_exists": pathlib.Path("mcp/mcp.json").exists(),
            "server_exists": pathlib.Path("mcp/mcp_server.py").exists(),
            "ping": None,
        },
        "gsheets": {
            "gspread_installed": False,
            "sa_path": os.getenv(
                "GOOGLE_APPLICATION_CREDENTIALS", "/app/creds/gsheet_sa.json"
            ),
            "sa_exists": False,
        },
    }

    # 1. Verificar Anthropic
    print("\n[1/3] Anthropic...")
    try:
        import anthropic

        res["anthropic"]["installed"] = True
        res["anthropic"]["version"] = anthropic.__version__
        print(f"  ✓ anthropic instalado: {anthropic.__version__}")

        if os.getenv("ANTHROPIC_API_KEY"):
            print("  ⚙ Testando ping...")
            p = subprocess.run(
                [sys.executable, "aiops/anthropic_ping.py"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            res["anthropic"]["ping"] = p.stdout.strip() or p.stderr.strip()
            if p.returncode == 0:
                print("  ✓ Ping bem-sucedido")
            else:
                print(f"  ✗ Ping falhou: {p.stderr[:100]}")
        else:
            print("  ⚠ ANTHROPIC_API_KEY não configurada")

    except ImportError:
        print("  ✗ anthropic não instalado")
    except Exception as e:
        res["anthropic"]["ping"] = f"erro: {e}"
        print(f"  ✗ Erro: {e}")

    # 2. Verificar MCP
    print("\n[2/3] MCP...")
    if res["mcp"]["manifest_exists"]:
        print("  ✓ mcp.json existe")
    else:
        print("  ✗ mcp.json não encontrado")

    if res["mcp"]["server_exists"]:
        print("  ✓ mcp_server.py existe")
        print("  ⚙ Testando ping...")
        try:
            p = subprocess.run(
                [sys.executable, "mcp/mcp_server.py"],
                input="{}",
                capture_output=True,
                text=True,
                timeout=10,
            )
            res["mcp"]["ping"] = p.stdout[:200] or p.stderr[:200]
            if '"ok"' in p.stdout or '"tools"' in p.stdout:
                print("  ✓ Server respondeu")
            else:
                print(f"  ⚠ Resposta inesperada: {p.stdout[:100]}")
        except Exception as e:
            res["mcp"]["ping"] = f"erro: {e}"
            print(f"  ✗ Erro: {e}")
    else:
        print("  ✗ mcp_server.py não encontrado")

    # 3. Verificar Google Sheets
    print("\n[3/3] Google Sheets...")
    try:
        import gspread

        res["gsheets"]["gspread_installed"] = True
        res["gsheets"]["version"] = gspread.__version__
        print(f"  ✓ gspread instalado: {gspread.__version__}")
    except ImportError:
        print("  ✗ gspread não instalado")

    sa_path = res["gsheets"]["sa_path"]
    if os.path.exists(sa_path):
        res["gsheets"]["sa_exists"] = True
        print(f"  ✓ Service Account encontrada: {sa_path}")
    else:
        print(f"  ✗ Service Account não encontrada: {sa_path}")

    # Salvar resultado
    output_file = OUT / "AUDITORIA_MCP_ANTHROPIC.json"
    output_file.write_text(
        json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("\n" + "=" * 60)
    print(f"✓ Auditoria concluída: {output_file}")
    print("=" * 60)

    # Resumo final
    print("\n📊 RESUMO:")
    print(
        f"  Anthropic: {'✓' if res['anthropic']['installed'] else '✗'} instalado, "
        f"{'✓' if res['anthropic']['key_configured'] else '✗'} configurado"
    )
    print(
        f"  MCP: {'✓' if res['mcp']['server_exists'] else '✗'} server, "
        f"{'✓' if res['mcp']['manifest_exists'] else '✗'} manifest"
    )
    print(
        f"  Google Sheets: {'✓' if res['gsheets']['gspread_installed'] else '✗'} instalado, "
        f"{'✓' if res['gsheets']['sa_exists'] else '✗'} SA"
    )

    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
