"""
Self-verification do detector de citacao apagada (camada de instrucao).

A LACUNA QUE ISTO FECHA. A decisao D3 (2026-08-25) versionou `.claude/` e
`.agents/` porque o enforcement da CP-07 mora la. Mas versionar nao e vigiar:
`check_agent_instructions.py` so olhava caminho de maquina e credencial — se o
conteudo e VERDADE, ninguem checava. `check_doc_impact.py` nem enxerga a arvore
(`RAIZES_DOC = ["v2/docs", "docs", "specs"]`).

Consequencia medida em 2026-08-25: `apps/core/models.py` foi apagado em
`4ae989fe` (#213, 2025-12-02) e TRES arquivos de instrucao ainda mandavam o
agente procurar a regra PA-01 la dentro — nove meses depois. `apps/core/views.py`
idem, apagado em `733e3933`. Ninguem tropecou porque nao havia em que tropecar.

O PROBLEMA DE PRECISAO, E A SAIDA. Varrer "caminho citado que nao existe" produz
12 achados dos quais 2 sao drift — 17% de precisao, gate revertido na primeira
semana. O grosso e texto-exemplo generico (`src/auth/session.py`,
`src/path/to.test.tsx`) que este repositorio nunca teve.

Filtro por palavra-chave nao resolve, porque um texto que NEGA a mentira contem
as mesmas palavras. O discriminador e o git: **este repositorio ja teve este
caminho?** Se `git log --diff-filter=D` o conhece, alguem apagou e a instrucao
ficou para tras. Se o git nunca o viu, e exemplo. Isso leva a precisao de 17%
para 83% — 10 dos 12 achados exigem acao.

O QUE O DISCRIMINADOR NAO RESOLVE, e por que o allowlist nao e concessao. Medido
no repo real, contrariando a hipotese inicial: `src/api.ts` FOI apagado (#1045,
remocao do axios), e a skill que o cita esta CERTA — a frase e "There is no
`src/api.ts` anymore". Declaracao historica correta sobre arquivo realmente
apagado e, por historico, indistinguivel de instrucao que ficou para tras. Sao os
2 achados restantes, e a saida deles e o allowlist, com motivo escrito.

CALIBRAGEM. Preciso e raro -> BLOQUEIA, mesma regra dos detectores anteriores.
Como o repo ja nasce com divida, o gate entra com allowlist datada: «limpar
primeiro, trancar depois com allowlist» e o padrao que o proprio repositorio
prova que funciona (`check-no-legacy-js`).

Verifica que:
1. Baseline limpo passa.
2. Citacao a caminho que o git APAGOU bloqueia, e nomeia o commit que apagou.
3. Citacao a caminho que o git NUNCA viu (exemplo generico) nao bloqueia.
4. Negacao sobre caminho que o git nunca viu tambem nao bloqueia.
5. Declaracao historica CORRETA sobre caminho realmente apagado ainda bloqueia —
   o falso positivo conhecido, fixado como teste, com o allowlist como saida.
6. Citacao a caminho vivo nao bloqueia.
7. Allowlist suprime o arquivo listado, e so ele.
8. Sem git disponivel, o detector se cala em vez de acusar tudo.
9. `_archive/` e `worktrees/` ficam fora.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingTypeStubs=false

from __future__ import annotations

import pathlib
import subprocess
import sys

from apps.core.tests.repo_git import commita, cria_repo, escreve, git

BACKEND_ROOT = pathlib.Path(__file__).resolve().parents[3]
SCRIPT = BACKEND_ROOT / "scripts" / "check_agent_instructions.py"


def _run(raiz: pathlib.Path, *alvos: str, extra: list[str] | None = None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *(alvos or (".claude",)), *(extra or [])],
        cwd=raiz,
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
    )


def _repo_base(tmp_path: pathlib.Path) -> pathlib.Path:
    """Repo com um arquivo vivo, um apagado, e a instrucao ainda em branco."""
    raiz = cria_repo(tmp_path)
    escreve(raiz, "apps/core/models.py", "# monolito\n")
    escreve(raiz, "apps/core/services/pagamento.py", "# vivo\n")
    commita(raiz, "chore: base")

    (raiz / "apps/core/models.py").unlink()
    escreve(raiz, "apps/core/models/__init__.py", "# pacote\n")
    commita(raiz, "refactor(models): modulariza models.py em pacote")
    return raiz


def test_script_existe():
    assert SCRIPT.exists(), f"check_agent_instructions.py nao encontrado em {SCRIPT}"


def test_baseline_limpo_passa(tmp_path):
    """Sem isto o gate nasce vermelho e alguem o desliga."""
    raiz = _repo_base(tmp_path)
    escreve(raiz, ".claude/skills/x/SKILL.md", "Regra vive em apps/core/services/pagamento.py.\n")
    commita(raiz, "docs: skill")

    r = _run(raiz)
    assert r.returncode == 0, f"baseline limpo reprovou:\n{r.stdout}\n{r.stderr}"


def test_citacao_a_caminho_apagado_bloqueia(tmp_path):
    raiz = _repo_base(tmp_path)
    escreve(
        raiz,
        ".claude/commands/approve-flow.md",
        "Check `apps/core/models.py` para a regra PA-01.\n",
    )
    commita(raiz, "docs: command")

    r = _run(raiz)
    assert r.returncode != 0, f"citacao a arquivo apagado passou:\n{r.stdout}"
    assert "apps/core/models.py" in r.stdout
    assert "approve-flow.md" in r.stdout


def test_saida_nomeia_o_commit_que_apagou(tmp_path):
    """Sem o commit, quem le nao sabe para onde a coisa foi."""
    raiz = _repo_base(tmp_path)
    escreve(raiz, ".claude/commands/x.md", "Ver `apps/core/models.py`.\n")
    commita(raiz, "docs: x")

    sha = git(raiz, "log", "--format=%h", "-1", "--diff-filter=D", "--", "apps/core/models.py")
    r = _run(raiz)
    assert sha and sha in r.stdout, f"a saida deveria citar {sha}:\n{r.stdout}"


def test_caminho_que_o_git_nunca_viu_nao_bloqueia(tmp_path):
    """O caso que decide a precisao: `src/api.ts` e exemplo, nao drift.

    Sem este discriminador o gate acusa 12 e acerta 2 — e e revertido.
    """
    raiz = _repo_base(tmp_path)
    escreve(
        raiz,
        ".claude/skills/deprecation/SKILL.md",
        "Exemplo generico: mova o cliente de `src/api.ts` para o wrapper.\n"
        "Outro: `src/auth/session.py` vira `{stem}_{entity}`.\n",
    )
    commita(raiz, "docs: skill com exemplo")

    r = _run(raiz)
    assert r.returncode == 0, f"texto-exemplo virou achado:\n{r.stdout}"


def test_negacao_sobre_caminho_nunca_visto_nao_bloqueia(tmp_path):
    """Um texto que NEGA contem as mesmas palavras — filtro textual marcaria.

    Aqui o caminho negado nunca existiu neste repositorio, entao o
    discriminador o descarta. O caso IRMAO — negacao sobre caminho que
    realmente foi apagado — NAO e resolvido, e esta fixado logo abaixo em
    `test_declaracao_historica_correta_precisa_de_allowlist`.
    """
    raiz = _repo_base(tmp_path)
    escreve(
        raiz,
        ".claude/skills/y/SKILL.md",
        "Verify: zero axios imports. There is no `src/http/client.ts` wrapper anymore.\n",
    )
    commita(raiz, "docs: y")

    r = _run(raiz)
    assert r.returncode == 0, f"negacao sobre caminho inexistente virou achado:\n{r.stdout}"


def test_declaracao_historica_correta_precisa_de_allowlist(tmp_path):
    """O limite conhecido do discriminador, registrado como teste.

    Caso real: `src/api.ts` foi mesmo apagado (#1045, remocao do axios), e a
    skill que o cita esta CERTA — diz "There is no `src/api.ts` anymore". Uma
    declaracao historica correta sobre arquivo realmente apagado e, por
    historico, indistinguivel de instrucao que ficou para tras.

    Este teste nao finge que o gate acerta: fixa que ele ERRA aqui, e que a
    saida prevista e o allowlist. Se algum dia surgir um discriminador melhor,
    este teste e o que vai reprovar e cobrar a atualizacao.
    """
    raiz = _repo_base(tmp_path)
    escreve(
        raiz,
        ".claude/skills/dep/SKILL.md",
        "Verify: zero axios. There is no `apps/core/models.py` anymore.\n",
    )
    commita(raiz, "docs: declaracao historica correta")

    r = _run(raiz)
    assert r.returncode != 0, "documenta o falso positivo conhecido — se passou, o gate melhorou"

    escreve(
        raiz,
        ".claude/citacoes-apagadas-allowlist.txt",
        "# declaracao historica correta, nao instrucao desatualizada\n.claude/skills/dep/SKILL.md\n",
    )
    commita(raiz, "chore: allowlist")
    r2 = _run(raiz)
    assert r2.returncode == 0, f"o allowlist deveria ser a saida para este caso:\n{r2.stdout}"


def test_caminho_vivo_nao_bloqueia(tmp_path):
    raiz = _repo_base(tmp_path)
    escreve(raiz, ".claude/skills/z/SKILL.md", "Ver `apps/core/services/pagamento.py:23`.\n")
    commita(raiz, "docs: z")

    r = _run(raiz)
    assert r.returncode == 0, f"caminho vivo virou achado:\n{r.stdout}"


def test_allowlist_suprime_so_o_arquivo_listado(tmp_path):
    """«Limpar primeiro, trancar depois com allowlist» — padrao do check-no-legacy-js."""
    raiz = _repo_base(tmp_path)
    escreve(raiz, ".claude/commands/sujo.md", "Ver `apps/core/models.py`.\n")
    escreve(raiz, ".claude/commands/outro.md", "Tambem ver `apps/core/models.py`.\n")
    escreve(
        raiz,
        ".claude/citacoes-apagadas-allowlist.txt",
        "# Lote C, sessao paralela de 2026-08-25\n.claude/commands/sujo.md\n",
    )
    commita(raiz, "docs: dois sujos, um perdoado")

    r = _run(raiz)
    assert r.returncode != 0, "o arquivo fora do allowlist deveria bloquear"
    assert "outro.md" in r.stdout
    assert "sujo.md" not in r.stdout, "o allowlist nao suprimiu o arquivo listado"


def test_o_allowlist_nao_se_acusa(tmp_path):
    """O allowlist explica CADA entrada, e explicar exige nomear o caminho.

    Sem esta excecao o gate reprova na propria configuracao — e a saida seria
    escrever um allowlist sem motivo, que e exatamente a erosao que ele evita.
    """
    raiz = _repo_base(tmp_path)
    escreve(raiz, ".claude/skills/x/SKILL.md", "Nada de errado aqui.\n")
    escreve(
        raiz,
        ".claude/citacoes-apagadas-allowlist.txt",
        "# `apps/core/models.py` foi apagado em 4ae989fe; a mencao abaixo e historica.\n" ".claude/commands/velho.md\n",
    )
    commita(raiz, "chore: allowlist com motivo")

    r = _run(raiz)
    assert r.returncode == 0, f"o allowlist se acusou:\n{r.stdout}"


def test_sem_git_o_detector_se_cala(tmp_path):
    """Sem historico nao da para distinguir drift de exemplo: calar > acusar tudo.

    Mesma disciplina do doc_drift_report em repo raso — nao produzir medida que
    nao da para sustentar.
    """
    raiz = tmp_path / "sem_git"
    (raiz / ".claude/commands").mkdir(parents=True)
    (raiz / ".claude/commands/x.md").write_text("Ver `apps/core/models.py`.\n", encoding="utf-8")

    r = _run(raiz)
    assert r.returncode == 0, f"sem git o detector deveria se calar:\n{r.stdout}\n{r.stderr}"


def test_archive_e_worktrees_ficam_fora(tmp_path):
    """Historico nao se corrige (ADR-017 item 5); worktree e copia de trabalho."""
    raiz = _repo_base(tmp_path)
    escreve(raiz, ".claude/_archive/velho.md", "Ver `apps/core/models.py`.\n")
    escreve(raiz, ".claude/worktrees/wt/x.md", "Ver `apps/core/models.py`.\n")
    commita(raiz, "docs: historico")

    r = _run(raiz)
    assert r.returncode == 0, f"_archive/worktrees viraram achado:\n{r.stdout}"
