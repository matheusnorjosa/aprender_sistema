"""
Self-verification do check de numeracao de ADR (F.1, pela raiz).

O PROBLEMA NAO E A COLISAO QUE EXISTE — E A PROXIMA. Ha dois `ADR-012` em arvores
diferentes, e isso ja esta documentado em
`docs/architecture/project-decisions/README.md:30` como "pendente de renumeracao".
Renumerar agora e churn em duas arvores por ganho cosmetico.

O que uma nota em README nao faz e impedir reincidencia — e o proprio plano
registra que o **ADR-019 recriou a colisao 21 dias depois de a primeira ser
documentada**. Medido em 2026-08-26: `docs/architecture/project-decisions/` vai
ate **ADR-018**, e `v2/docs/adr/` ja tem **ADR-019**. O proximo ADR escrito na
primeira arvore colide. Nao e divida do passado: e uma armadilha armada para o
proximo commit.

DUAS ARVORES, UM ESPACO DE NUMERACAO. Nao existe registro central de numero. As
duas pastas se comportam como se fossem independentes, e nao sao — quem escreve
`ADR-019` cita "ADR-019" em prosa, e o leitor resolve para a arvore errada. O
dano ja aconteceu com o 012: `docs/guides/etl.md:5` cita "ADR-012" querendo dizer
o de SHA1 (v2), e dentro do mkdocs isso resolve para o de guardrails.

CALIBRAGEM: BLOQUEIA. E preciso (parse de nome de arquivo, zero heuristica),
raro (uma colisao hoje) e conserta-se DENTRO do PR — escolhe-se outro numero. A
colisao existente entra no allowlist, com motivo, seguindo o mesmo contrato do
`citacoes-apagadas-allowlist.txt`: limpar primeiro, trancar depois.

Verifica que:
1. Baseline sem colisao passa.
2. Mesmo numero nas DUAS arvores bloqueia, e a saida nomeia os dois arquivos.
3. Mesmo numero DUPLICADO na mesma arvore bloqueia.
4. Numero so numa arvore nao bloqueia.
5. Allowlist suprime o numero listado, e so ele.
6. Allowlist exige motivo — entrada nua nao vale.
7. Arvore inexistente nao derruba o check.
8. Nome que nao casa o padrao ADR-NNN e ignorado, nao vira colisao.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingTypeStubs=false

from __future__ import annotations

import pathlib
import subprocess
import sys

BACKEND_ROOT = pathlib.Path(__file__).resolve().parents[3]
SCRIPT = BACKEND_ROOT / "scripts" / "check_adr_numbers.py"

A = "docs/architecture/project-decisions"
B = "v2/docs/adr"


def _monta(raiz: pathlib.Path, arquivos: list[str], allowlist: str | None = None) -> None:
    for rel in arquivos:
        p = raiz / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("# ADR\n", encoding="utf-8")
    if allowlist is not None:
        p = raiz / "docs" / "architecture" / "project-decisions" / "adr-numeros-allowlist.txt"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(allowlist, encoding="utf-8")


def _run(raiz: pathlib.Path):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(raiz)],
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
    )


def test_script_existe():
    assert SCRIPT.exists(), f"check_adr_numbers.py nao encontrado em {SCRIPT}"


def test_sem_colisao_passa(tmp_path):
    """Sem isto o gate nasce vermelho e alguem o desliga."""
    _monta(tmp_path, [f"{A}/ADR-001-um.md", f"{A}/ADR-002-dois.md", f"{B}/ADR-019-tres.md"])
    r = _run(tmp_path)
    assert r.returncode == 0, f"baseline limpo reprovou:\n{r.stdout}\n{r.stderr}"


def test_mesmo_numero_nas_duas_arvores_bloqueia(tmp_path):
    _monta(tmp_path, [f"{A}/ADR-012-guardrails.md", f"{B}/ADR-012-sha1.md"])
    r = _run(tmp_path)
    assert r.returncode != 0, f"colisao entre arvores passou:\n{r.stdout}"
    assert "012" in r.stdout
    assert (
        "guardrails" in r.stdout and "sha1" in r.stdout
    ), f"a saida deve nomear OS DOIS arquivos, senao nao da para escolher qual renumerar:\n{r.stdout}"


def test_numero_duplicado_na_mesma_arvore_bloqueia(tmp_path):
    _monta(tmp_path, [f"{A}/ADR-007-a.md", f"{A}/ADR-007-b.md"])
    r = _run(tmp_path)
    assert r.returncode != 0, f"duplicata na mesma arvore passou:\n{r.stdout}"
    assert "007" in r.stdout


def test_numero_em_uma_arvore_so_nao_bloqueia(tmp_path):
    _monta(tmp_path, [f"{A}/ADR-018-x.md", f"{B}/ADR-019-y.md"])
    r = _run(tmp_path)
    assert r.returncode == 0, f"numeros distintos reprovaram:\n{r.stdout}"


def test_allowlist_suprime_so_o_numero_listado(tmp_path):
    """«Limpar primeiro, trancar depois» — mesmo contrato do gate de citacao."""
    _monta(
        tmp_path,
        [f"{A}/ADR-012-a.md", f"{B}/ADR-012-b.md", f"{A}/ADR-013-c.md", f"{B}/ADR-013-d.md"],
        allowlist="012 — colisao historica, documentada no README, renumeracao pendente\n",
    )
    r = _run(tmp_path)
    assert r.returncode != 0, "o numero fora do allowlist deveria bloquear"
    assert "013" in r.stdout
    assert "ADR-012" not in r.stdout, f"o allowlist nao suprimiu o 012:\n{r.stdout}"


def test_allowlist_exige_motivo(tmp_path):
    """Entrada sem motivo e o comeco da erosao — o gate volta a nao valer nada."""
    _monta(
        tmp_path,
        [f"{A}/ADR-012-a.md", f"{B}/ADR-012-b.md"],
        allowlist="012\n",
    )
    r = _run(tmp_path)
    assert r.returncode != 0, "entrada de allowlist sem motivo foi aceita"
    assert "motivo" in r.stdout.lower() or "justific" in r.stdout.lower()


def test_arvore_inexistente_nao_derruba(tmp_path):
    _monta(tmp_path, [f"{A}/ADR-001-x.md"])
    r = _run(tmp_path)
    assert r.returncode == 0, f"ausencia da segunda arvore derrubou o check:\n{r.stderr}"


def test_nome_fora_do_padrao_e_ignorado(tmp_path):
    """README.md e template.md vivem na mesma pasta e nao sao ADR."""
    _monta(tmp_path, [f"{A}/README.md", f"{A}/template.md", f"{A}/ADR-001-x.md"])
    r = _run(tmp_path)
    assert r.returncode == 0, f"arquivo fora do padrao virou colisao:\n{r.stdout}"


def test_saida_ensina_o_proximo_numero_livre(tmp_path):
    """Sem isto, quem for consertar escolhe outro numero colidido."""
    _monta(tmp_path, [f"{A}/ADR-001-a.md", f"{B}/ADR-001-b.md", f"{B}/ADR-019-c.md"])
    r = _run(tmp_path)
    assert r.returncode != 0
    assert "020" in r.stdout, f"a saida deveria sugerir o proximo numero livre:\n{r.stdout}"
