"""
Self-verification do gate da camada de instrucao de agente (D3).

Contexto: a auditoria de 2026-08-24 encontrou 155 arquivos de instrucao de agente
fora do git — sem revisao, sem diff, sem historico. A decisao D3
(v2/docs/plans/PLAN_doc_drift_2026-08-25.md) passou a versiona-los. Isso cria um
risco novo num repositorio PUBLICO (ADR-009): caminho de maquina e credencial
entrando por descuido.

Este gate impede a reincidencia. Estes testes provam que ele MORDE — rodar o
script contra o repo prova apenas que ele executa.

Verifica que:
1. O script existe e um diretorio limpo passa (baseline limpo, exit 0).
2. Caminho absoluto de maquina reprova (Windows, Linux e macOS).
3. Credencial embutida em DSN reprova.
4. Token de provedor conhecido reprova.
5. `$CLAUDE_PROJECT_DIR` e `$HOME` sao aceitos — sao a correcao, nao a violacao.
6. Placeholder de credencial e aceito (`<usuario>:<senha>`).
7. Binario e cache sao ignorados (nao geram falso positivo).
8. A saida nomeia arquivo e linha (achado sem localizacao e inutil).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingTypeStubs=false

from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

# parents[0]=tests, [1]=core, [2]=apps, [3]=backend root (local: v2/backend, container: /app)
BACKEND_ROOT = pathlib.Path(__file__).resolve().parents[3]
SCRIPT = BACKEND_ROOT / "scripts" / "check_agent_instructions.py"


def _run(alvo: pathlib.Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(alvo)],
        capture_output=True,
        text=True,
        check=False,
    )


def _escreve(base: pathlib.Path, nome: str, conteudo: str) -> pathlib.Path:
    p = base / nome
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(conteudo, encoding="utf-8")
    return p


def test_script_existe():
    assert SCRIPT.exists(), f"check_agent_instructions.py nao encontrado em {SCRIPT}"


def test_baseline_limpo_passa(tmp_path):
    """Sem esta garantia o gate nasce vermelho e e desligado na primeira semana."""
    _escreve(tmp_path, "skills/exemplo/SKILL.md", "# Skill\n\nUse `$CLAUDE_PROJECT_DIR/scripts/x.py`.\n")
    _escreve(tmp_path, "CLAUDE.md", "# Projeto\n\nRode `make up` em `v2/`.\n")
    r = _run(tmp_path)
    assert r.returncode == 0, f"baseline limpo reprovou:\nSTDOUT: {r.stdout}\nSTDERR: {r.stderr}"


@pytest.mark.parametrize(
    "caminho",
    [
        r"C:\\Users\\alguem\\OneDrive\\Documentos\\projeto",
        "C:/Users/alguem/Documentos/projeto",
        "/home/alguem/projeto",
        "/Users/alguem/projeto",
    ],
)
def test_caminho_de_maquina_reprova(tmp_path, caminho):
    _escreve(tmp_path, "hooks/h.md", f"Rode `py -3 {caminho}/hooks/x.py`\n")
    r = _run(tmp_path)
    assert r.returncode != 0, f"caminho de maquina passou despercebido: {caminho}"


def test_credencial_em_dsn_reprova(tmp_path):
    _escreve(tmp_path, "settings.json", '{"env": {"DSN": "postgresql://aprender:aprender@localhost:5432/db"}}\n')
    r = _run(tmp_path)
    assert r.returncode != 0, "DSN com credencial passou"


@pytest.mark.parametrize(
    "token",
    [
        "ghp_" + "A" * 36,
        "github_pat_" + "B" * 22,
        "sk-" + "C" * 32,
        "xoxb-" + "1" * 24,
    ],
)
def test_token_conhecido_reprova(tmp_path, token):
    _escreve(tmp_path, "commands/c.md", f"Use o token {token} para autenticar.\n")
    r = _run(tmp_path)
    assert r.returncode != 0, f"token passou despercebido: {token[:12]}..."


@pytest.mark.parametrize("variavel", ["$CLAUDE_PROJECT_DIR", "$HOME", "${HOME}"])
def test_variavel_de_ambiente_e_aceita(tmp_path, variavel):
    """E a correcao prescrita pela D3 — reprovar aqui inverteria o incentivo."""
    _escreve(tmp_path, "settings.json", f'{{"command": "py -3 {variavel}/.claude/hooks/g.py"}}\n')
    r = _run(tmp_path)
    assert r.returncode == 0, f"{variavel} foi tratado como violacao"


def test_placeholder_de_credencial_e_aceito(tmp_path):
    _escreve(tmp_path, "settings.json", '{"DSN": "postgresql://<usuario>:<senha>@localhost:5432/<db>"}\n')
    r = _run(tmp_path)
    assert r.returncode == 0, "placeholder foi tratado como credencial real"


def test_binario_e_cache_sao_ignorados(tmp_path):
    (tmp_path / "__pycache__").mkdir(parents=True, exist_ok=True)
    (tmp_path / "__pycache__" / "x.pyc").write_bytes(b"\x00\x01C:\\Users\\alguem\\p\x00")
    _escreve(tmp_path, "ok.md", "# nada aqui\n")
    r = _run(tmp_path)
    assert r.returncode == 0, f"cache gerou falso positivo:\n{r.stdout}"


def test_saida_nomeia_arquivo_e_linha(tmp_path):
    _escreve(tmp_path, "hooks/h.md", "linha ok\nrode /home/alguem/x.py aqui\n")
    r = _run(tmp_path)
    assert r.returncode != 0
    saida = r.stdout + r.stderr
    assert "hooks/h.md" in saida.replace("\\", "/"), f"achado sem nome de arquivo:\n{saida}"
    assert ":2" in saida, f"achado sem numero de linha:\n{saida}"


def test_diretorio_inexistente_falha_explicito(tmp_path):
    r = _run(tmp_path / "nao-existe")
    assert r.returncode != 0
    assert "nao encontrado" in (r.stdout + r.stderr).lower()
