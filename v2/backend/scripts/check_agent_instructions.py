#!/usr/bin/env python
"""
Gate da camada de instrucao de agente — D3.

A auditoria de 2026-08-24 encontrou 155 arquivos de instrucao de agente
(.claude/, .agents/, AGENTS.md, CLAUDE.md) FORA do git: sem revisao, sem diff,
sem historico. E onde drift desvia um agente em vez de confundir uma pessoa.

A decisao D3 (v2/docs/plans/PLAN_doc_drift_2026-08-25.md) passou a versiona-los.
Isso cria um risco novo, porque o repositorio e PUBLICO (ADR-009): caminho da
maquina de quem escreveu, e credencial embutida, entrando por descuido.

Este script existe para que a sanitizacao feita uma vez nao se perca. Sem ele,
o primeiro `settings.json` colado de volta reintroduz o problema em silencio.

Uso:
    python scripts/check_agent_instructions.py <diretorio-ou-arquivo> [...]
    python scripts/check_agent_instructions.py --tracked-only <caminho> [...]

`--tracked-only` restringe a varredura ao que o git rastreia. E o modo do CI:
sem ele, o gate acusa arquivo deliberadamente fora do git (settings.local.json
guarda exatamente os caminhos de maquina que este script proibe no versionado),
e gate que reclama do que nao esta no repo e desligado na primeira semana.

Exit 0 = limpo. Exit 1 = achados (com arquivo:linha). Exit 2 = erro de uso.

Testes: apps/core/tests/test_check_agent_instructions.py
"""

from __future__ import annotations

import pathlib
import re
import sys

# --- o que se procura -------------------------------------------------------

# Caminho absoluto que carrega o nome de usuario de quem escreveu.
# Aceita $CLAUDE_PROJECT_DIR e $HOME — sao a correcao prescrita, nao violacao.
CAMINHO_MAQUINA = re.compile(r"""(?ix)
    (?: [A-Z]:[\\/]{1,2} Users [\\/]{1,2} (?!\<) [A-Za-z0-9._-]+   # C:\Users\nome
      | /home/   (?!\<) [A-Za-z0-9._-]+                            # /home/nome
      | /Users/  (?!\<) [A-Za-z0-9._-]+                            # /Users/nome
    )
    """)

# Credencial embutida em URL de conexao. Placeholder <...> e aceito.
CREDENCIAL_URL = re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://(?!\<)[^\s:/@]+:(?!\<)[^\s:/@]+@")

# Tokens de provedores conhecidos.
TOKENS = [
    ("GitHub PAT classico", re.compile(r"\bghp_[A-Za-z0-9]{30,}")),
    ("GitHub PAT fine-grained", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}")),
    ("OpenAI/Anthropic-like", re.compile(r"\bsk-[A-Za-z0-9]{24,}")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}")),
    ("Slack", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("Chave privada", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]

# Nao varrer: binario, cache, dependencia e worktree (copias).
DIR_IGNORADOS = {"__pycache__", "node_modules", ".venv", "venv", "worktrees", ".git"}
EXT_IGNORADAS = {
    ".pyc",
    ".pyo",
    ".so",
    ".dll",
    ".exe",
    ".bin",
    ".zip",
    ".gz",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".pdf",
    ".woff",
    ".woff2",
    ".ttf",
    ".mp3",
}


def _deve_varrer(p: pathlib.Path) -> bool:
    if p.suffix.lower() in EXT_IGNORADAS:
        return False
    return not any(parte in DIR_IGNORADOS for parte in p.parts)


def _arquivos(alvo: pathlib.Path):
    if alvo.is_file():
        if _deve_varrer(alvo):
            yield alvo
        return
    for p in sorted(alvo.rglob("*")):
        if p.is_file() and _deve_varrer(p):
            yield p


def _analisa(p: pathlib.Path) -> list[tuple[int, str, str]]:
    """Devolve [(linha, tipo, trecho)]."""
    try:
        texto = p.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []  # binario ou ilegivel: fora de escopo

    achados: list[tuple[int, str, str]] = []
    for n, linha in enumerate(texto.splitlines(), 1):
        if m := CAMINHO_MAQUINA.search(linha):
            achados.append((n, "caminho de maquina", m.group(0)))
        if m := CREDENCIAL_URL.search(linha):
            # nao ecoar a senha
            achados.append((n, "credencial em URL", m.group(0).split("://")[0] + "://<redigido>@"))
        for nome, rx in TOKENS:
            if rx.search(linha):
                achados.append((n, f"token ({nome})", "<redigido>"))
    return achados


def _rastreados(alvos: list[pathlib.Path]) -> set[pathlib.Path] | None:
    """Conjunto de arquivos que o git rastreia. None se git nao estiver disponivel."""
    import subprocess

    try:
        r = subprocess.run(
            ["git", "ls-files", "-z", "--", *[str(a) for a in alvos]],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return {pathlib.Path(x).resolve() for x in r.stdout.split("\0") if x}


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if a != "--tracked-only"]
    so_rastreados = "--tracked-only" in argv[1:]

    if not args:
        print(__doc__)
        return 2

    alvos: list[pathlib.Path] = []
    for a in args:
        p = pathlib.Path(a)
        if not p.exists():
            print(f"ERRO: caminho nao encontrado: {p}", file=sys.stderr)
            return 2
        alvos.append(p)

    permitidos: set[pathlib.Path] | None = None
    if so_rastreados:
        permitidos = _rastreados(alvos)
        if permitidos is None:
            print("ERRO: --tracked-only exige git disponivel e um repositorio.", file=sys.stderr)
            return 2

    total = 0
    varridos = 0
    for alvo in alvos:
        raiz = alvo if alvo.is_dir() else alvo.parent
        for p in _arquivos(alvo):
            if permitidos is not None and p.resolve() not in permitidos:
                continue
            varridos += 1
            for linha, tipo, trecho in _analisa(p):
                try:
                    rel = p.relative_to(raiz)
                except ValueError:
                    rel = p
                print(f"{rel}:{linha}: {tipo}: {trecho}")
                total += 1

    if total:
        print()
        print(f"FALHOU: {total} achado(s) em {varridos} arquivo(s) varrido(s).")
        print("Caminho de maquina -> use $CLAUDE_PROJECT_DIR ou $HOME.")
        print("Credencial -> use placeholder <usuario>:<senha> e ponha o valor real")
        print("em .claude/settings.local.json, que continua fora do git.")
        return 1

    print(f"OK {varridos} arquivo(s) varrido(s), nenhum caminho de maquina nem credencial.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
