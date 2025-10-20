"""
Utilitários para ingestão de dados com idempotência.
Garante que dados já processados não sejam reimportados.
"""

import hashlib
import json
from typing import Any, Mapping


def sha1_of_row(row: Mapping[str, Any]) -> str:
    """
    Gera SHA1 canônico de um dicionário (idempotência).

    Args:
        row: Dicionário com dados da linha a ser processada

    Returns:
        Hash SHA1 hexadecimal (40 caracteres) do conteúdo canônico

    Examples:
        >>> sha1_of_row({"nome": "João", "email": "joao@example.com"})
        'a1b2c3d4e5f6...'
    """
    blob = json.dumps(
        row, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha1(blob).hexdigest()
