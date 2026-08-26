"""
Guard rails arquiteturais para apps.core.

- apps.dat_ingest foi removido (#967, #971).
- Escritas de dominio de Solicitacao/Participation ficam no caminho canonico da
  API (Onda 2, monolito modular): um writer novo que dribla o serializer/ViewSet
  falha aqui antes do merge; a divida conhecida (import de eventos) e #1884.
"""

from __future__ import annotations

import re
from pathlib import Path

CORE = Path(__file__).resolve().parents[1]  # apps/core/


def test_dat_ingest_module_removed() -> None:
    """apps.dat_ingest should not exist (removed in #971)."""
    dat_ingest_dir = CORE / "dat_ingest"
    assert not dat_ingest_dir.exists(), f"apps.dat_ingest should be removed but found at {dat_ingest_dir}"


# --------------------------------------------------------------------------
# Onda 2 (monolito modular) -- fronteira de persistencia de dominio.
#
# Regra mecanica v1: Solicitacao e Participation so podem ser persistidos no
# CAMINHO CANONICO DA API (SolicitacaoViewSet: serializer.save + _create_participants
# / _update_formadores). Qualquer outro arquivo de app que chame
# .objects.(create|update|update_or_create|bulk_create|get_or_create) nesses dois
# models dribla o caminho canonico.
#
# get_or_create ENTRA na lista: todo create de Participation (canonico e ofensor)
# usa get_or_create; sem ele a banned-list fica desdentada (medido na Onda 2).
#
# Estado medido na main (2026-08-26): VERDE. Unico writer fora do caminho canonico
# = services/eventos_import.py (import de eventos, superficie viva ImportEventosView),
# registrado como divida conhecida #1884 (alvo do D8/Onda 4). Este teste bloqueia
# NOVOS ofensores; a divida so encolhe.
# --------------------------------------------------------------------------
_WRITE_RE = re.compile(
    r"\b(?:Solicitacao|Participation)\.objects\.(?:create|update|update_or_create|bulk_create|get_or_create)\b"
)

# Caminho canonico da API: persistir esses models aqui e legitimo.
_CANONICAL = {"views_solicitacao.py"}

# Divida conhecida (rastreada por issue, a rotear pelo service da API). So encolhe:
# quando o D8 rotear eventos_import pelo serializer/service, remover daqui.
_KNOWN_DEBT = {"services/eventos_import.py"}  # #1884

# Dirs que nao sao codigo de app -- escrita sempre permitida.
_ALLOWLIST_DIRS = ("tests", "migrations")


def _write_files() -> set[str]:
    """Arquivos de apps/core (fora de tests/migrations) que persistem os dois models."""
    hits: set[str] = set()
    for py in CORE.rglob("*.py"):
        rel = py.relative_to(CORE).as_posix()
        if rel.split("/", 1)[0] in _ALLOWLIST_DIRS:
            continue
        if _WRITE_RE.search(py.read_text(encoding="utf-8", errors="replace")):
            hits.add(rel)
    return hits


def test_domain_writes_stay_in_canonical_path() -> None:
    """Nenhum writer novo persiste Solicitacao/Participation fora do caminho da API."""
    offenders = sorted(_write_files() - _CANONICAL - _KNOWN_DEBT)
    assert not offenders, (
        "Escrita direta de Solicitacao/Participation fora do caminho canonico da API "
        f"(views_solicitacao.py) e da divida conhecida (#1884): {offenders}. "
        "Rote pelo SolicitacaoViewSet (serializer.save / _create_participants), ou "
        "registre a divida em _KNOWN_DEBT com uma issue."
    )


def test_known_debt_boundary_entries_are_live() -> None:
    """Cada entrada de _KNOWN_DEBT ainda escreve -- senao foi corrigida e deve sair da lista."""
    writers = _write_files()
    stale = sorted(rel for rel in _KNOWN_DEBT if rel not in writers)
    assert not stale, (
        f"Entradas de _KNOWN_DEBT sem escrita direta (ja roteadas pelo service?): {stale}. "
        "Remova-as da allowlist -- a divida encolheu."
    )
