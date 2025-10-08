"""
Teste de conectividade com Anthropic API.

Script simples para verificar se a API key do Anthropic está configurada
corretamente e se conseguimos fazer chamadas básicas à API.
"""

from __future__ import annotations

import os
import sys


def main():
    """Envia mensagem ping para Claude e valida resposta."""
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        print("FALHA: defina ANTHROPIC_API_KEY no ambiente", file=sys.stderr)
        sys.exit(2)

    try:
        from anthropic import Anthropic

        cli = Anthropic(api_key=key)
        msg = cli.messages.create(
            model="claude-3-5-sonnet-latest",
            max_tokens=16,
            messages=[{"role": "user", "content": "ping"}],
        )

        print(f"✓ OK: {msg.model}")
        print(f"  Input tokens: {msg.usage.input_tokens}")
        print(f"  Output tokens: {msg.usage.output_tokens}")
        print(f"  Response: {msg.content[0].text if msg.content else '(empty)'}")

    except Exception as e:
        print(f"✗ ERRO: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
