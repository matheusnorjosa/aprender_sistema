"""
Repositorio git de verdade para testar os gates de documentacao.

Nao e arquivo de teste: e helper compartilhado, no mesmo espirito de
`factories.py`. Existe porque os gates de doc (`doc_drift_report.py`,
`check_doc_impact.py`) tem o proprio `git log`/`git show` como objeto sob teste —
simular isso com mock testaria o mock.
"""

from __future__ import annotations

import os
import pathlib
import subprocess


def git(raiz: pathlib.Path, *args: str) -> str:
    r = subprocess.run(
        ["git", *args],
        cwd=raiz,
        capture_output=True,
        text=True,
        check=True,
        encoding="utf-8",
    )
    return r.stdout.strip()


def cria_repo(tmp_path: pathlib.Path, nome: str = "repo") -> pathlib.Path:
    raiz = tmp_path / nome
    raiz.mkdir()
    git(raiz, "init", "-q", "-b", "main")
    git(raiz, "config", "user.email", "teste@exemplo.invalid")
    git(raiz, "config", "user.name", "Teste")
    git(raiz, "config", "commit.gpgsign", "false")
    return raiz


def escreve(raiz: pathlib.Path, rel: str, conteudo: str) -> None:
    p = raiz / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(conteudo, encoding="utf-8")


def _env_data(quando: str | None) -> dict[str, str]:
    env = dict(os.environ)
    if quando:
        env["GIT_AUTHOR_DATE"] = quando
        env["GIT_COMMITTER_DATE"] = quando
    return env


def commita(raiz: pathlib.Path, mensagem: str, quando: str | None = None) -> str:
    """Commit com data fixa. `quando` em ISO com fuso: '2026-08-01T10:00:00-03:00'."""
    git(raiz, "add", "-A")
    subprocess.run(
        ["git", "commit", "-q", "-m", mensagem],
        cwd=raiz,
        check=True,
        capture_output=True,
        env=_env_data(quando),
    )
    return git(raiz, "rev-parse", "HEAD")


def spec(
    sha: str | None,
    fontes: list[str],
    status: str = "canonical",
    corpo: str = "Conteudo.",
) -> str:
    linhas = ["---", f"status: {status}", "last_verified: 2026-08-01"]
    if sha:
        linhas.append(f"verified_at_commit: {sha}")
    if fontes:
        linhas.append("sources_of_truth:")
        linhas += [f"  - {f}" for f in fontes]
    linhas += ["---", "", "# Spec", "", corpo, ""]
    return "\n".join(linhas)
