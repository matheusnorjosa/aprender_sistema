"""Parse de parâmetros de request dos imports síncronos (DRF).

O parse de ``dry_run`` é FAIL-CLOSED: dry-run (preview, sem persistir) é o
padrão seguro; só um token de apply EXPLÍCITO libera a escrita. Qualquer outro
valor — omitido, vazio, com typo ou lixo — permanece em dry-run, para que um
erro de digitação nunca dispare escrita silenciosa (achado M04-05, issue #1649).

Antes deste helper, cada view fazia ``dry_run = valor in {"1", "true", ...}`` —
uma *allowlist do valor verdadeiro*, não uma validação: qualquer valor fora da
lista (``dry_run=treu``, ``dry_run=sim``, ``dry_run=`` vazio) caía em ``False``
= APPLY silencioso. Este helper inverte a lógica: só ``APPLY_TOKENS`` aplicam.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Tokens que EXPLICITAMENTE ligam o APPLY (desligam o dry-run).
APPLY_TOKENS = frozenset({"false", "0", "no", "n", "f", "off"})
# Tokens reconhecidos que mantêm o dry-run — só p/ não logar um valor legítimo.
_PREVIEW_TOKENS = frozenset({"true", "1", "t", "yes", "y", "on"})


def parse_dry_run(raw: str | None, *, default: bool = True) -> bool:
    """Resolve o modo dry-run de um valor de query-param, fail-closed.

    Args:
        raw: valor cru do parâmetro (ex.: ``request.query_params.get("dry_run")``).
            ``None`` ou string vazia caem no ``default``.
        default: modo quando o parâmetro é omitido. ``True`` (preview) é o seguro.

    Returns:
        ``True`` para dry-run (preview, não persiste); ``False`` para APPLY. Só
        retorna ``False`` para um token de apply explícito (:data:`APPLY_TOKENS`);
        qualquer valor desconhecido permanece em dry-run (fail-closed).
    """
    if raw is None:
        return default
    token = raw.strip().lower()
    if not token:
        return default
    if token in APPLY_TOKENS:
        return False
    if token not in _PREVIEW_TOKENS:
        logger.warning(
            "dry_run com valor não reconhecido (%r); tratando como dry-run "
            "(preview) por segurança — envie 'false' para aplicar.",
            token,
        )
    return True
