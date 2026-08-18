"""Redacao central de PII (LGPD art. 46) para caminhos de PERSISTENCIA.

O `PIIRedactionFilter` (logging_filters.py) protege o pipeline de LOGS. Este modulo
cobre o que o filtro de log nao alcanca: valores que vao para o banco (ex.: o JSONField
`AuditLog.details`). Um helper por tipo de dado sensivel, reusavel na escrita e na leitura.
"""

from __future__ import annotations

import re
from typing import Any

# CPF nas DUAS formas: 11 digitos crus OU formatado 000.000.000-00. As ancoras `\b`
# garantem que so o TOKEN inteiro casa — um username como `user_<hex>` (digitos cercados
# de word-chars) NAO tem fronteira de palavra no meio e por isso nunca e alterado.
_CPF_RE = re.compile(r"\b(?:\d{3}\.\d{3}\.\d{3}-\d{2}|\d{11})\b")

# Convencao alinhada ao PIIRedactionFilter dos logs (logging_filters.py).
_CPF_PLACEHOLDER = "<cpf>"


def redact_cpf(value: Any) -> Any:
    """Troca qualquer CPF (cru ou formatado) por `<cpf>`; no-op se nao houver CPF.

    Defensivo para JSONField heterogeneo: valores nao-string voltam intactos.
    """
    if not isinstance(value, str):
        return value
    return _CPF_RE.sub(_CPF_PLACEHOLDER, value)
