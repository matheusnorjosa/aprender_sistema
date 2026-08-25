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

# Caminho de codigo citado em prosa de instrucao. Exige extensao e uma barra,
# para nao casar palavra solta. `tsx` antes de `ts`: a alternancia do `re` e
# ordenada, e `ts|tsx` truncaria `Componente.tsx` em `Componente.ts` — que nao
# existe, e o achado nasceria falso. (Aconteceu na medicao que calibrou isto.)
CITACAO = re.compile(
    r"(?<![\w/.-])((?:v2/)?(?:backend/|frontend/|infra/)?"
    r"(?:apps|src|scripts|config)/[\w./-]+\.(?:tsx|ts|py|sh|yml|yaml))"
)

# Um caminho citado pode estar escrito relativo a raiz ou a um subprojeto.
PREFIXOS = ("", "v2/", "v2/backend/", "v2/frontend/", "v2/infra/")

ALLOWLIST = "citacoes-apagadas-allowlist.txt"

# Nao varrer: binario, cache, dependencia e worktree (copias).
DIR_IGNORADOS = {"__pycache__", "node_modules", ".venv", "venv", "worktrees", ".git", "_archive"}
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


def _git(args: list[str]) -> str | None:
    """stdout do git, ou None se o git nao estiver disponivel/utilizavel."""
    import subprocess

    try:
        r = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 else None


def _apagados() -> set[str] | None:
    """Caminhos que este repositorio ja teve e apagou.

    ESTE E O DISCRIMINADOR. Varrer "caminho citado que nao existe" produz 12
    achados no repositorio, dos quais so 2 sao drift — 17% de precisao, e um
    gate assim e desligado na primeira semana. O resto e texto-exemplo generico
    (`src/auth/session.py`, `src/path/to.test.tsx`) que o git nunca viu.

    Filtrar por palavra-chave nao serve: um texto que NEGA a mentira contem as
    mesmas palavras. Perguntar ao git elimina os exemplos genericos e leva a
    precisao de 17% para 83% (10 de 12 exigem acao).

    O QUE ELE NAO RESOLVE, medido no repo real: `src/api.ts` foi de fato apagado
    (#1045, remocao do axios), e a skill que o cita esta CERTA — a frase e "There
    is no `src/api.ts` anymore". Declaracao historica correta sobre um arquivo
    realmente apagado e indistinguivel, por historico, de instrucao que ficou
    para tras. Esses 2 casos vao para o allowlist, que existe para isso.

    Uma chamada so, sobre todo o historico. Sem git, devolve None e o detector
    se cala — nao ha como distinguir drift de exemplo, e acusar tudo seria pior
    que nao acusar nada.
    """
    out = _git(["log", "--all", "--diff-filter=D", "--name-only", "--format="])
    if out is None:
        return None
    return {x.strip() for x in out.split("\n") if x.strip()}


def _candidatos(cit: str) -> list[str]:
    return [pref + cit for pref in PREFIXOS]


def _quem_apagou(cit: str) -> str:
    for cand in _candidatos(cit):
        out = _git(["log", "--all", "--format=%h %s", "-1", "--diff-filter=D", "--", cand])
        if out and out.strip():
            return out.strip().split("\n")[0]
    return ""


def _le_allowlist(alvos: list[pathlib.Path]) -> set[str]:
    """Arquivos perdoados enquanto a limpeza de conteudo nao acontece.

    «Limpar primeiro, trancar depois com allowlist» e o padrao que este
    repositorio prova que funciona (`check-no-legacy-js`). Sem isto o gate nasce
    vermelho por divida preexistente e e desligado antes de pegar o primeiro
    caso novo — que e o que ele existe para pegar.
    """
    perdoados: set[str] = set()
    vistos: set[pathlib.Path] = set()
    for alvo in alvos:
        base = alvo if alvo.is_dir() else alvo.parent
        f = base / ALLOWLIST
        if f in vistos or not f.is_file():
            continue
        vistos.add(f)
        try:
            for linha in f.read_text(encoding="utf-8").splitlines():
                linha = linha.strip()
                if linha and not linha.startswith("#"):
                    perdoados.add(linha.replace("\\", "/"))
        except OSError:
            continue
    return perdoados


def _citacoes_apagadas(p: pathlib.Path, apagados: set[str], raiz: pathlib.Path) -> list[tuple[int, str, str]]:
    try:
        texto = p.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []

    achados: list[tuple[int, str, str]] = []
    for n, linha in enumerate(texto.splitlines(), 1):
        for m in CITACAO.finditer(linha):
            cit = m.group(1)
            cands = _candidatos(cit)
            if any((raiz / c).exists() for c in cands):
                continue  # vivo
            if not any(c in apagados for c in cands):
                continue  # o git nunca viu: e exemplo, nao drift
            achados.append((n, "citacao a caminho apagado", cit))
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

    # Sem git nao da para separar drift de texto-exemplo; nesse caso `apagados`
    # vem None e o detector de citacao fica de fora, em vez de acusar tudo.
    apagados = _apagados()
    perdoados = _le_allowlist(alvos)
    cwd = pathlib.Path.cwd()

    total = 0
    citacoes = 0
    varridos = 0
    for alvo in alvos:
        for p in _arquivos(alvo):
            if permitidos is not None and p.resolve() not in permitidos:
                continue
            varridos += 1

            achados = list(_analisa(p))
            # `lstrip("./")` aqui seria bug: lstrip remove um CONJUNTO de
            # caracteres, entao `.claude/...` viraria `claude/...` e o allowlist
            # nunca casaria.
            rel_repo = p.as_posix().replace("\\", "/")
            if rel_repo.startswith("./"):
                rel_repo = rel_repo[2:]

            # O proprio allowlist fica fora do detector de citacao: ele explica
            # cada entrada, e explicar exige nomear o caminho apagado. Sem esta
            # excecao o gate reprova na propria configuracao — e a saida seria
            # escrever um allowlist sem motivo, que e a erosao que ele evita.
            if p.name == ALLOWLIST:
                for linha, tipo, trecho in _analisa(p):
                    print(f"{rel_repo}:{linha}: {tipo}: {trecho}")
                    total += 1
                continue
            if apagados is not None and rel_repo not in perdoados:
                novos = _citacoes_apagadas(p, apagados, cwd)
                citacoes += len(novos)
                achados += novos

            for linha, tipo, trecho in achados:
                # Relativo ao repo, nao ao alvo: `.claude/skills/x/SKILL.md` e
                # `.agents/skills/x/SKILL.md` sao espelhos e imprimiam identicos
                # como `skills/x/SKILL.md` — sem dizer em qual arvore agir.
                rel = rel_repo
                extra = ""
                if tipo.startswith("citacao"):
                    quem = _quem_apagou(trecho)
                    extra = f"  (apagado em {quem})" if quem else ""
                print(f"{rel}:{linha}: {tipo}: {trecho}{extra}")
                total += 1

    if total:
        print()
        print(f"FALHOU: {total} achado(s) em {varridos} arquivo(s) varrido(s).")
        print("Caminho de maquina -> use $CLAUDE_PROJECT_DIR ou $HOME.")
        print("Credencial -> use placeholder <usuario>:<senha> e ponha o valor real")
        print("em .claude/settings.local.json, que continua fora do git.")
        if citacoes:
            print()
            print("Citacao a caminho apagado -> aponte para onde o codigo foi. O git")
            print("sabe quem apagou (mostrado acima). Se a mencao for historica e")
            print(f"deliberada, liste o arquivo em {ALLOWLIST}, com o motivo.")
        return 1

    checou = "caminho de maquina, credencial"
    if apagados is not None:
        checou += ", citacao a caminho apagado"
    else:
        checou += " (citacao nao verificada: sem git)"
    print(f"OK {varridos} arquivo(s) varrido(s) — {checou}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
