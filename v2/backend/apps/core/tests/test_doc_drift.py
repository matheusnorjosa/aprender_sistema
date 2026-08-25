"""
Self-verification do medidor de drift (Fase B do plano PLAN_doc_drift_2026-08-25).

POR QUE ANCORAR EM COMMIT, NAO EM DATA. `git log --since=<data>` usa approxidate,
que resolve contra a hora atual: a mesma pergunta responde diferente as 08h e as
20h, e `--since` inclui o proprio dia, entao a spec corrigida hoje aparece como
"em drift" no PR que a corrigiu. O repositorio ja tinha inventado a saida certa —
`ACHADOS_REAIS.md` ancora em `audit_baseline: 90f6a048`. Esta fase generaliza
isso para as specs: `verified_at_commit`, e o drift vira `git log <sha>..HEAD`.

POR QUE E RELATORIO, NAO PORTAO. 21 de 21 specs que declaram `sources_of_truth`
estao em drift, e 95% das ancoradas recebem commit novo em 7 dias. Um gate que
bloqueia sobre "existe drift" bloqueia sempre e e desligado na primeira semana.
Drift em repouso e metrica; o portao e por PR (check_doc_impact.py, Fase C).

A UNICA COISA QUE FAZ ESTE SCRIPT SAIR != 0 e nao poder medir: repositorio raso.
`docs-quality.yml` fazia checkout sem `fetch-depth`, e `git log` num repo de
profundidade 1 ve um commit e responde "sem drift" — verde por falta de dado, que
e o diagnostico deste plano se reproduzindo dentro da propria correcao. Cinto e
suspensorio: `fetch-depth: 0` no workflow E o guard aqui, porque config some em
refactor e codigo com teste, nao.

DUAS PROVENIENCIAS DE ANCORA. `verified_at_commit` no frontmatter e ancora
DECLARADA: alguem conferiu naquele commit. Na falta dela, a ancora e INFERIDA do
ultimo commit da propria spec. A inferida existe porque a alternativa era pior:
preencher `verified_at_commit` nos 22 arquivos de uma vez seria escrever
"verificado no commit X" para verificacao que nunca houve — a alegacao sem lastro
que esta auditoria existe para cacar. O relatorio sempre diz qual das duas usou.

Verifica que:
1. Spec ancorada sem commit posterior nos seus arquivos: sem drift.
2. Spec ancorada com commit posterior: drift, com a contagem certa.
3. Commit no MESMO DIA da verificacao nao acusa (o bug do --since).
4. A resposta e identica em fusos/horarios diferentes (nao ha relogio no caminho).
5. Commit que nao toca `sources_of_truth` daquela spec nao conta para ela.
6. Sem `verified_at_commit`, a ancora e inferida do ultimo commit da spec...
7. ...e a saida marca que foi inferida, nunca a apresenta como conferencia.
8. Ancora declarada vence a inferida.
9. `sources_of_truth` ausente e NAO MEDIVEL, nunca "sem drift".
10. Assunto de commit nao-ASCII nao derruba o relatorio (console cp1252).
11. Repositorio raso aborta com exit != 0, em vez de reportar verde.
12. Drift, sozinho, nunca reprova — nem com 40 commits.
13. `_archive/` e `status: historical`/`stale` ficam fora.
14. A saida em gh-summary e Markdown valido e nomeia specs e contagens.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingTypeStubs=false

from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

from apps.core.tests.repo_git import commita as _commit
from apps.core.tests.repo_git import cria_repo as _repo
from apps.core.tests.repo_git import escreve as _escreve
from apps.core.tests.repo_git import git as _git
from apps.core.tests.repo_git import spec as _spec

BACKEND_ROOT = pathlib.Path(__file__).resolve().parents[3]
SCRIPT = BACKEND_ROOT / "scripts" / "doc_drift_report.py"


def _run(raiz: pathlib.Path, *extra: str, env: dict[str, str] | None = None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(raiz), *extra],
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
        env=env,
    )


# --------------------------------------------------------------------------
# B.1 — ancora em commit
# --------------------------------------------------------------------------
def test_script_existe():
    assert SCRIPT.exists(), f"doc_drift_report.py nao encontrado em {SCRIPT}"


def test_ancora_sem_commit_posterior_nao_acusa(tmp_path):
    raiz = _repo(tmp_path)
    _escreve(raiz, "v2/backend/apps/core/services/pagamento.py", "x = 1\n")
    sha = _commit(raiz, "feat: pagamento")
    _escreve(
        raiz,
        "v2/docs/specs/backend/pagamento.spec.md",
        _spec(sha, ["v2/backend/apps/core/services/pagamento.py"]),
    )
    _commit(raiz, "docs: spec de pagamento")

    r = _run(raiz)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "0 commit" in r.stdout or "sem drift" in r.stdout.lower(), r.stdout


def test_ancora_com_commit_posterior_acusa_com_contagem(tmp_path):
    raiz = _repo(tmp_path)
    fonte = "v2/backend/apps/core/services/pagamento.py"
    _escreve(raiz, fonte, "x = 1\n")
    sha = _commit(raiz, "feat: pagamento")
    _escreve(raiz, "v2/docs/specs/backend/pagamento.spec.md", _spec(sha, [fonte]))
    _commit(raiz, "docs: spec")

    for i in range(3):
        _escreve(raiz, fonte, f"x = {i + 2}\n")
        _commit(raiz, f"fix(pagamento): mudanca {i}")

    r = _run(raiz)
    assert r.returncode == 0, "drift sozinho nunca reprova"
    assert "pagamento.spec.md" in r.stdout
    assert "3" in r.stdout, f"deveria contar 3 commits de drift:\n{r.stdout}"


def test_commit_no_mesmo_dia_nao_acusa(tmp_path):
    """O bug que motivou a fase: `--since=<hoje>` acusa a spec corrigida hoje.

    Aqui a ancora e o commit que fecha o assunto; o proprio commit da spec vem
    depois, no mesmo dia, e nao pode contar como drift dela mesma.
    """
    raiz = _repo(tmp_path)
    fonte = "v2/backend/apps/core/services/pagamento.py"
    quando = "2026-08-25T09:00:00-03:00"
    _escreve(raiz, fonte, "x = 1\n")
    sha = _commit(raiz, "fix(pagamento): corrige calculo", quando)
    _escreve(raiz, "v2/docs/specs/backend/pagamento.spec.md", _spec(sha, [fonte]))
    _commit(raiz, "docs(pagamento): atualiza spec", "2026-08-25T09:30:00-03:00")

    r = _run(raiz)
    assert r.returncode == 0, r.stdout + r.stderr
    # Sem esta linha o teste passa quando o script NAO EXISTE: a asserçao abaixo e
    # negativa e uma saida vazia a satisfaz. Provar que a spec foi medida vem antes.
    assert "pagamento.spec.md" in r.stdout, f"a spec nem foi medida:\n{r.stdout}"
    # Casar a string "EM DRIFT" nao serve: a linha de resumo diz "0 em drift".
    # A afirmaçao a verificar e a contagem, nao a presença da palavra.
    assert "0 em drift" in r.stdout, f"commit do mesmo dia acusou drift — e o defeito do --since:\n{r.stdout}"


def test_roda_igual_as_08h_e_as_20h(tmp_path):
    """Sem relogio no caminho, o resultado nao pode depender de fuso nem de hora."""
    import os

    raiz = _repo(tmp_path)
    fonte = "v2/backend/apps/core/services/pagamento.py"
    _escreve(raiz, fonte, "x = 1\n")
    sha = _commit(raiz, "feat: pagamento", "2026-08-20T23:30:00-03:00")
    _escreve(raiz, "v2/docs/specs/backend/pagamento.spec.md", _spec(sha, [fonte]))
    _commit(raiz, "docs: spec", "2026-08-20T23:40:00-03:00")
    _escreve(raiz, fonte, "x = 2\n")
    _commit(raiz, "fix: ajuste", "2026-08-21T00:10:00-03:00")

    saidas = set()
    for tz in ("UTC", "Pacific/Kiritimati", "Pacific/Midway", "America/Fortaleza"):
        env = dict(os.environ)
        env["TZ"] = tz
        r = _run(raiz, env=env)
        assert r.returncode == 0, r.stdout + r.stderr
        # Saidas vazias tambem sao todas iguais: sem isto o teste passa com o
        # script ausente, que e o oposto do que ele existe para provar.
        assert "pagamento.spec.md" in r.stdout, f"nada foi medido em TZ={tz}:\n{r.stdout}"
        saidas.add(r.stdout)

    assert len(saidas) == 1, f"a saida mudou conforme o fuso: {len(saidas)} variantes"


def test_commit_fora_das_fontes_nao_conta(tmp_path):
    raiz = _repo(tmp_path)
    fonte = "v2/backend/apps/core/services/pagamento.py"
    _escreve(raiz, fonte, "x = 1\n")
    sha = _commit(raiz, "feat: pagamento")
    _escreve(raiz, "v2/docs/specs/backend/pagamento.spec.md", _spec(sha, [fonte]))
    _commit(raiz, "docs: spec")

    _escreve(raiz, "v2/frontend/src/App.tsx", "export default 1\n")
    _commit(raiz, "feat(frontend): outra area")

    r = _run(raiz)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "pagamento.spec.md" in r.stdout, f"a spec nem foi medida:\n{r.stdout}"
    assert "0 em drift" in r.stdout, f"commit em area alheia contou para a spec:\n{r.stdout}"


def test_ancora_inferida_nunca_se_apresenta_como_verificacao(tmp_path):
    """Confundir 'nao sei' com 'esta ok' e como o gate de 180 dias virou decoracao.

    A ancora inferida mede uma coisa util, mas NAO e alegacao de que alguem
    conferiu a spec contra o codigo. A saida tem que dizer qual das duas e.
    """
    raiz = _repo(tmp_path)
    fonte = "v2/backend/apps/core/services/pagamento.py"
    _escreve(raiz, fonte, "x = 1\n")
    _escreve(raiz, "v2/docs/specs/backend/pagamento.spec.md", _spec(None, [fonte]))
    _commit(raiz, "feat: tudo")

    r = _run(raiz)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "pagamento.spec.md" in r.stdout
    assert (
        "inferida" in r.stdout.lower()
    ), f"sem ancora declarada, a saida precisa marcar a medida como inferida:\n{r.stdout}"


def test_ancora_inferida_do_ultimo_commit_da_spec(tmp_path):
    """Sem `verified_at_commit`, a ancora vem do ultimo commit da propria spec.

    Preencher os 22 arquivos a mao significaria escrever "verificado no commit X"
    para verificacao que nunca houve — a alegacao sem lastro que esta auditoria
    existe para cacar. O ultimo commit da spec e um fato do git, e responde a
    pergunta util: o codigo mudou desde que este doc foi mexido pela ultima vez?
    """
    raiz = _repo(tmp_path)
    fonte = "v2/backend/apps/core/services/pagamento.py"
    _escreve(raiz, fonte, "x = 1\n")
    _commit(raiz, "feat: pagamento")
    _escreve(raiz, "v2/docs/specs/backend/pagamento.spec.md", _spec(None, [fonte]))
    _commit(raiz, "docs: spec sem ancora explicita")
    _escreve(raiz, fonte, "x = 2\n")
    _commit(raiz, "fix(pagamento): depois da spec")

    r = _run(raiz)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "1 em drift" in r.stdout, f"a ancora inferida deveria medir 1 commit:\n{r.stdout}"
    assert (
        "inferida" in r.stdout.lower()
    ), f"a saida precisa dizer que a ancora foi inferida, nao declarada:\n{r.stdout}"


def test_ancora_explicita_tem_precedencia_sobre_inferida(tmp_path):
    raiz = _repo(tmp_path)
    fonte = "v2/backend/apps/core/services/pagamento.py"
    _escreve(raiz, fonte, "x = 1\n")
    sha = _commit(raiz, "feat: pagamento")
    _escreve(raiz, fonte, "x = 2\n")
    _commit(raiz, "fix(pagamento): antes da spec")
    # A spec e commitada DEPOIS, entao a ancora inferida veria 0 commits.
    # A explicita aponta para tras e precisa vencer: 1 commit de drift.
    _escreve(raiz, "v2/docs/specs/backend/pagamento.spec.md", _spec(sha, [fonte]))
    _commit(raiz, "docs: spec com ancora explicita")

    r = _run(raiz)
    assert "1 em drift" in r.stdout, f"a ancora explicita deveria vencer a inferida:\n{r.stdout}"
    assert "inferida" not in r.stdout.lower(), r.stdout


def test_sources_of_truth_ausente_nao_vira_verde_silencioso(tmp_path):
    """As 5 specs 'verdes' do repo eram exatamente as 5 que nao declaravam nada."""
    raiz = _repo(tmp_path)
    _escreve(raiz, "v2/docs/specs/backend/vazia.spec.md", _spec("abc1234", []))
    _commit(raiz, "docs: spec sem fontes")

    r = _run(raiz)
    saida = r.stdout.upper()
    assert (
        "NAO MEDIVEL" in saida or "SEM FONTE" in saida
    ), f"spec sem sources_of_truth precisa ser reportada, nao omitida:\n{r.stdout}"


def test_assunto_de_commit_nao_ascii_nao_quebra(tmp_path):
    """O console do Windows e cp1252 e o repo tem commit com `→`, acento e emoji.

    Caso real: `feat(dat): coordenador do plano é Usuario` e
    `Pipeline Sheets→Sistema` derrubavam o relatorio com UnicodeEncodeError na
    hora de imprimir o assunto. Um relatorio que so roda no CI nao serve para
    quem precisa dele antes de abrir o PR.
    """
    raiz = _repo(tmp_path)
    fonte = "v2/backend/apps/core/services/pagamento.py"
    _escreve(raiz, fonte, "x = 1\n")
    sha = _commit(raiz, "feat: pagamento")
    _escreve(raiz, "v2/docs/specs/backend/pagamento.spec.md", _spec(sha, [fonte]))
    _commit(raiz, "docs: spec")
    _escreve(raiz, fonte, "x = 2\n")
    _commit(raiz, "fix(pagamento): Sheets→Sistema, coordenação e çedilha")

    r = _run(raiz)
    assert r.returncode == 0, f"assunto nao-ASCII derrubou o relatorio:\n{r.stdout}\n{r.stderr}"
    assert "UnicodeEncodeError" not in r.stderr
    assert "1 em drift" in r.stdout


# --------------------------------------------------------------------------
# B.2 — repositorio raso
# --------------------------------------------------------------------------
def test_repositorio_raso_aborta(tmp_path):
    raiz = _repo(tmp_path)
    fonte = "v2/backend/apps/core/services/pagamento.py"
    _escreve(raiz, fonte, "x = 1\n")
    sha = _commit(raiz, "feat: pagamento")
    _escreve(raiz, "v2/docs/specs/backend/pagamento.spec.md", _spec(sha, [fonte]))
    _commit(raiz, "docs: spec")
    _escreve(raiz, fonte, "x = 2\n")
    _commit(raiz, "fix: ajuste")

    raso = tmp_path / "raso"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", raiz.as_uri(), str(raso)],
        check=True,
        capture_output=True,
    )
    assert _git(raso, "rev-parse", "--is-shallow-repository") == "true"

    r = _run(raso)
    assert r.returncode != 0, "repo raso mede errado e precisa abortar, nao reportar verde"
    saida = (r.stdout + r.stderr).lower()
    assert "raso" in saida or "shallow" in saida, r.stdout + r.stderr


# --------------------------------------------------------------------------
# B.3 — relatorio, nunca portao
# --------------------------------------------------------------------------
def test_drift_sozinho_nunca_reprova(tmp_path):
    raiz = _repo(tmp_path)
    fonte = "v2/backend/apps/core/services/pagamento.py"
    _escreve(raiz, fonte, "x = 1\n")
    sha = _commit(raiz, "feat: pagamento")
    _escreve(raiz, "v2/docs/specs/backend/pagamento.spec.md", _spec(sha, [fonte]))
    _commit(raiz, "docs: spec")
    for i in range(40):
        _escreve(raiz, fonte, f"x = {i + 2}\n")
        _commit(raiz, f"fix: mudanca {i}")

    r = _run(raiz)
    assert r.returncode == 0, f"40 commits de drift reprovaram; deveria so reportar:\n{r.stdout}"


def test_gh_summary_e_markdown_com_specs_e_contagens(tmp_path):
    raiz = _repo(tmp_path)
    fonte = "v2/backend/apps/core/services/pagamento.py"
    _escreve(raiz, fonte, "x = 1\n")
    sha = _commit(raiz, "feat: pagamento")
    _escreve(raiz, "v2/docs/specs/backend/pagamento.spec.md", _spec(sha, [fonte]))
    _commit(raiz, "docs: spec")
    _escreve(raiz, fonte, "x = 2\n")
    _commit(raiz, "fix: ajuste")

    destino = tmp_path / "summary.md"
    r = _run(raiz, "--format=gh-summary", "--summary-file", str(destino))
    assert r.returncode == 0, r.stdout + r.stderr
    md = destino.read_text(encoding="utf-8")
    assert md.lstrip().startswith("#"), f"gh-summary deveria abrir com titulo:\n{md[:200]}"
    assert "|" in md, "gh-summary deveria trazer tabela"
    assert "pagamento.spec.md" in md
    assert "1" in md


# --------------------------------------------------------------------------
# escopo — historico nao se corrige (ADR-017 item 5)
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "caminho,status",
    [
        ("v2/docs/_archive/antiga.spec.md", "canonical"),
        ("v2/docs/specs/backend/velha.spec.md", "historical"),
        ("v2/docs/specs/backend/parada.spec.md", "stale"),
    ],
)
def test_historico_fica_fora(tmp_path, caminho, status):
    raiz = _repo(tmp_path)
    fonte = "v2/backend/apps/core/services/pagamento.py"
    _escreve(raiz, fonte, "x = 1\n")
    sha = _commit(raiz, "feat: pagamento")
    _escreve(raiz, caminho, _spec(sha, [fonte], status=status))
    _commit(raiz, "docs: doc historico")
    _escreve(raiz, fonte, "x = 2\n")
    _commit(raiz, "fix: ajuste")

    # Uma spec normal, medivel, garante que o relatorio de fato rodou — sem ela a
    # asserçao negativa abaixo passaria com o script ausente.
    _escreve(raiz, "v2/docs/specs/backend/viva.spec.md", _spec(sha, [fonte]))
    _commit(raiz, "docs: spec viva")

    r = _run(raiz)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "viva.spec.md" in r.stdout, f"o relatorio nao rodou:\n{r.stdout}"
    nome = caminho.rsplit("/", 1)[-1]
    assert nome not in r.stdout, f"{caminho} ({status}) nao deveria ser medido:\n{r.stdout}"
