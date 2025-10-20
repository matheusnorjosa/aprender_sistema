"""
MCP Server - Stub básico para integração MCP.

Server minimalista do Model Context Protocol para testes e bootstrap.
"""

from __future__ import annotations

import json
import sys


def main():
    """Handler básico de MCP - retorna lista de ferramentas disponíveis."""
    try:
        # Ler request do stdin (formato JSON)
        req = sys.stdin.read()

        # Resposta stub com ferramentas básicas
        resp = {
            "ok": True,
            "tools": [
                {
                    "name": "health",
                    "description": "Ping MCP - verifica se o servidor está respondendo",
                    "input_schema": {"type": "object", "properties": {}},
                }
            ],
            "version": "1.0.0",
            "name": "aprender_mcp",
        }

        # Enviar resposta para stdout
        sys.stdout.write(json.dumps(resp, ensure_ascii=False, indent=2))
        sys.stdout.flush()

    except Exception as e:
        error_resp = {"ok": False, "error": str(e)}
        sys.stdout.write(json.dumps(error_resp))
        sys.stdout.flush()


if __name__ == "__main__":
    main()
