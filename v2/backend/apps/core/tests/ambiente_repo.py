"""
Ponto unico que decide o que fazer quando falta a raiz do repositorio ou o git.

Nao e arquivo de teste: e helper compartilhado, no mesmo espirito de `repo_git.py`.

O PROBLEMA. Os testes dos scripts de documentacao/git precisam de duas coisas que o
container de desenvolvimento nao tem: o binario `git` e a raiz do repositorio (o
container monta so `v2/backend` em `/app`; `scripts/`, `v2/scripts/` e `v2/docs/`
ficam de fora). La eles falhavam por ambiente, e vermelho que nao e defeito ensina a
ignorar vermelho.

A REGRA. Fora da CI, quem depende do que falta e PULADO com motivo. Na CI
(`CI` ou `GITHUB_ACTIONS` definidos) o mesmo caso FALHA: o checkout do Actions tem
raiz e git, entao a ausencia la e defeito do job, e pular esconderia o teste.
"""

from __future__ import annotations

import os
import pathlib
import shutil
from typing import NoReturn

import pytest

MOTIVO = "precisa da raiz do repositório e do git (roda na CI)"
FALHA_NA_CI = "na CI estes testes têm de rodar; a raiz do repositório ou o git não foram encontrados"

# <raiz>/v2/backend/apps/core/tests/ambiente_repo.py
_NIVEIS_ATE_A_RAIZ = 5


def raiz_do_repo(arquivo: pathlib.Path | None = None) -> pathlib.Path | None:
    """Raiz do repositorio, ou None quando so `v2/backend` esta montado.

    Nao indexa `parents[5]` direto: em `/app/apps/core/tests/` esse indice nao
    existe e estourava `IndexError` na coleta.
    """
    pais = (arquivo or pathlib.Path(__file__)).resolve().parents
    if len(pais) <= _NIVEIS_ATE_A_RAIZ:
        return None
    raiz = pais[_NIVEIS_ATE_A_RAIZ]
    if (raiz / "scripts").is_dir() and (raiz / "v2" / "docs").is_dir():
        return raiz
    return None


def _na_ci() -> bool:
    return bool(os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"))


def _falta(o_que: str) -> NoReturn:
    if _na_ci():
        pytest.fail(f"{FALHA_NA_CI} (faltou: {o_que})", pytrace=False)
    pytest.skip(MOTIVO)


def exige_raiz_do_repo() -> pathlib.Path:
    """Devolve a raiz; sem ela, pula o teste (ou falha, na CI)."""
    raiz = raiz_do_repo()
    if raiz is None:
        _falta("raiz do repositório")
    return raiz


def exige_git() -> None:
    """Sem o binario `git` no PATH, pula o teste (ou falha, na CI)."""
    if shutil.which("git") is None:
        _falta("git")
