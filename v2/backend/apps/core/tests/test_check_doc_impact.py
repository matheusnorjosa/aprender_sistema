"""
Self-verification do gate que mantem a documentacao viva (Fase C do plano).

Problema medido na auditoria de 2026-08-24: **92,9% dos commits `fix(...)` nao
tocam um unico `.md`** (8 de 112 desde junho). O arbitro de defeitos ficou 64
commits sem atualizacao, 26 deles fixes. A regra ja estava escrita, em negrito,
dentro do proprio arbitro — o modo de falha nao e ignorancia, e ausencia de gate.

Este gate tem DOIS detectores, com calibragem diferente porque a precisao deles e
diferente:

1. **Issue resolvida -> doc que a cita.** Preciso e raro. BLOQUEIA.
   Um commit que diz `Closes #1610` resolve algo; se a doc viva descreve #1610
   como defeito aberto, ela passou a mentir naquele instante.

2. **Codigo alterado -> spec que o declara.** Amplo. AVISA.
   Toda spec declara `sources_of_truth` com os arquivos que descreve. Se o PR
   toca um deles, aquela spec ficou suspeita por construcao. Medido: dispara em
   60% dos commits, media de 2,6 specs. Bloquear nisso trava o repo.

Por que nao ancorar so na issue: `Closes #N` aparece em apenas **27,7%** dos
commits de fix, e as citacoes `Mxx-yy` cairam a zero quando a frente de trabalho
virou frontend. Gate ancorado so ai fica verde por vacuidade.

Verifica que:
1. Baseline limpo passa (sem isso o gate nasce vermelho e e desligado).
2. Issue resolvida cujo doc a cita como aberta BLOQUEIA.
3. Doc alterado no mesmo PR satisfaz o gate.
4. Waiver no corpo do PR satisfaz, e exige justificativa.
5. Codigo que uma spec declara gera AVISO, nunca bloqueio.
6. Referencia a issue sem verbo de resolucao gera aviso, nao bloqueio.
7. `_archive/` e ignorado (historico nao se corrige).
8. A saida nomeia o doc e diz por que ele foi apontado.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingTypeStubs=false

from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

BACKEND_ROOT = pathlib.Path(__file__).resolve().parents[3]
SCRIPT = BACKEND_ROOT / "scripts" / "check_doc_impact.py"


def _monta(base: pathlib.Path, arquivos: dict[str, str]) -> None:
    for rel, conteudo in arquivos.items():
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(conteudo, encoding="utf-8")


def _run(
    raiz: pathlib.Path,
    alterados: list[str],
    commits: str = "",
    corpo_pr: str = "",
) -> subprocess.CompletedProcess[str]:
    (raiz / "_alterados.txt").write_text("\n".join(alterados), encoding="utf-8")
    (raiz / "_commits.txt").write_text(commits, encoding="utf-8")
    (raiz / "_corpo.txt").write_text(corpo_pr, encoding="utf-8")
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo-root", str(raiz),
            "--changed-files-from", str(raiz / "_alterados.txt"),
            "--commit-messages-from", str(raiz / "_commits.txt"),
            "--pr-body-file", str(raiz / "_corpo.txt"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


SPEC = """---
status: canonical
last_verified: 2026-08-01
sources_of_truth:
  - v2/backend/apps/core/services/pagamento.py
  - v2/backend/apps/core/models/pagamento.py
---

# Pagamento

O defeito #1610 continua **aberto**: o calculo ignora desconto.
"""


def test_script_existe():
    assert SCRIPT.exists(), f"check_doc_impact.py nao encontrado em {SCRIPT}"


def test_baseline_limpo_passa(tmp_path):
    """PR que nao toca codigo declarado nem resolve issue citada."""
    _monta(tmp_path, {"v2/docs/specs/backend/pagamento.spec.md": SPEC})
    r = _run(tmp_path, ["README.md"], commits="docs: ajusta readme")
    assert r.returncode == 0, f"baseline limpo reprovou:\n{r.stdout}\n{r.stderr}"


def test_issue_resolvida_com_doc_desatualizado_bloqueia(tmp_path):
    _monta(tmp_path, {"v2/docs/specs/backend/pagamento.spec.md": SPEC})
    r = _run(
        tmp_path,
        ["v2/backend/apps/core/services/pagamento.py"],
        commits="fix(pagamento): aplica desconto no calculo\n\nCloses #1610",
    )
    assert r.returncode != 0, f"issue resolvida nao bloqueou:\n{r.stdout}"
    assert "pagamento.spec.md" in r.stdout
    assert "1610" in r.stdout


def test_doc_alterado_no_mesmo_pr_satisfaz(tmp_path):
    _monta(tmp_path, {"v2/docs/specs/backend/pagamento.spec.md": SPEC})
    r = _run(
        tmp_path,
        [
            "v2/backend/apps/core/services/pagamento.py",
            "v2/docs/specs/backend/pagamento.spec.md",
        ],
        commits="fix(pagamento): aplica desconto\n\nCloses #1610",
    )
    assert r.returncode == 0, f"doc atualizado no PR deveria satisfazer:\n{r.stdout}"


def test_waiver_com_justificativa_satisfaz(tmp_path):
    _monta(tmp_path, {"v2/docs/specs/backend/pagamento.spec.md": SPEC})
    r = _run(
        tmp_path,
        ["v2/backend/apps/core/services/pagamento.py"],
        commits="fix(pagamento): aplica desconto\n\nCloses #1610",
        corpo_pr=(
            "doc-nao-afetada: v2/docs/specs/backend/pagamento.spec.md — "
            "o #1610 citado na spec e outro defeito, de nomenclatura"
        ),
    )
    assert r.returncode == 0, f"waiver justificado deveria satisfazer:\n{r.stdout}"


def test_waiver_sem_justificativa_nao_satisfaz(tmp_path):
    """Sem esta regra o waiver vira 'ok' e o gate morre por erosao."""
    _monta(tmp_path, {"v2/docs/specs/backend/pagamento.spec.md": SPEC})
    r = _run(
        tmp_path,
        ["v2/backend/apps/core/services/pagamento.py"],
        commits="fix(pagamento): aplica desconto\n\nCloses #1610",
        corpo_pr="doc-nao-afetada: v2/docs/specs/backend/pagamento.spec.md",
    )
    assert r.returncode != 0, "waiver sem justificativa foi aceito"


def test_codigo_declarado_so_avisa(tmp_path):
    """Dispara em 60% dos commits: bloquear trava o repo."""
    _monta(tmp_path, {"v2/docs/specs/backend/pagamento.spec.md": SPEC})
    r = _run(
        tmp_path,
        ["v2/backend/apps/core/models/pagamento.py"],
        commits="refactor(pagamento): extrai helper",
    )
    assert r.returncode == 0, f"indice reverso deveria avisar, nao bloquear:\n{r.stdout}"
    assert "pagamento.spec.md" in r.stdout, "o aviso deveria nomear a spec"


def test_issue_sem_verbo_de_resolucao_so_avisa(tmp_path):
    _monta(tmp_path, {"v2/docs/specs/backend/pagamento.spec.md": SPEC})
    r = _run(
        tmp_path,
        ["v2/backend/apps/core/services/pagamento.py"],
        commits="refactor(pagamento): prepara terreno para #1610",
    )
    assert r.returncode == 0, f"mencao sem verbo deveria so avisar:\n{r.stdout}"


@pytest.mark.parametrize("verbo", ["Closes", "Fixes", "Resolves", "closes", "fix"])
def test_verbos_de_resolucao_reconhecidos(tmp_path, verbo):
    _monta(tmp_path, {"v2/docs/specs/backend/pagamento.spec.md": SPEC})
    r = _run(
        tmp_path,
        ["v2/backend/apps/core/services/pagamento.py"],
        commits=f"fix(pagamento): x\n\n{verbo} #1610",
    )
    assert r.returncode != 0, f"verbo '{verbo}' nao foi reconhecido"


def test_archive_e_ignorado(tmp_path):
    """ADR-017 item 5: historico e imutavel e nao se corrige."""
    _monta(tmp_path, {"v2/docs/_archive/antigo.md": "O #1610 esta aberto.\n"})
    r = _run(
        tmp_path,
        ["v2/backend/apps/core/services/pagamento.py"],
        commits="fix: x\n\nCloses #1610",
    )
    assert r.returncode == 0, f"_archive nao deveria ser apontado:\n{r.stdout}"


def test_waiver_dentro_de_comentario_html_nao_conta(tmp_path):
    """A razao de existir do waiver e ser revisavel. Escondido, nao e.

    Tambem impede que o texto-exemplo do pull_request_template.md — que vive
    dentro de <!-- --> — vire waiver automatico em todo PR.
    """
    _monta(tmp_path, {"v2/docs/specs/backend/pagamento.spec.md": SPEC})
    r = _run(
        tmp_path,
        ["v2/backend/apps/core/services/pagamento.py"],
        commits="fix(pagamento): x\n\nCloses #1610",
        corpo_pr=(
            "<!-- doc-nao-afetada: v2/docs/specs/backend/pagamento.spec.md — "
            "justificativa escondida no comentario -->"
        ),
    )
    assert r.returncode != 0, "waiver dentro de comentario HTML foi aceito"


@pytest.mark.parametrize(
    "motivo",
    ["por que nao afeta", "...", "xxx", "<motivo>"],
)
def test_placeholder_nao_conta_como_justificativa(tmp_path, motivo):
    _monta(tmp_path, {"v2/docs/specs/backend/pagamento.spec.md": SPEC})
    r = _run(
        tmp_path,
        ["v2/backend/apps/core/services/pagamento.py"],
        commits="fix(pagamento): x\n\nCloses #1610",
        corpo_pr=f"doc-nao-afetada: v2/docs/specs/backend/pagamento.spec.md — {motivo}",
    )
    assert r.returncode != 0, f"placeholder '{motivo}' foi aceito como justificativa"


def test_doc_marcado_historical_nao_e_apontado(tmp_path):
    """ADR-017 item 5: historico nao se corrige — e vale fora de _archive.

    Caso real: v2/docs/audits/2026-07-17-system-module-audit.md mora em audits/,
    declara `status: historical` e abre com "Registro historico — nao e a fila de
    trabalho". A primeira versao deste gate o apontou; era falso positivo.
    """
    _monta(
        tmp_path,
        {"v2/docs/audits/antiga.md": "---\nstatus: historical\n---\nO #1610 esta aberto.\n"},
    )
    r = _run(
        tmp_path,
        ["v2/backend/apps/core/services/pagamento.py"],
        commits="fix: x\n\nCloses #1610",
    )
    assert r.returncode == 0, f"doc historical foi apontado:\n{r.stdout}"


def test_achado_citado_sem_ser_fix_nao_bloqueia(tmp_path):
    """Commits citam ID de achado como contexto, nao so ao resolver.

    Caso real: ac418a50 citava M17-09, M18-09, M19-10 e M22-06 sem resolver
    nenhum, e a primeira versao deste gate bloqueou.
    """
    _monta(
        tmp_path,
        {"v2/docs/specs/backend/x.spec.md": "---\nstatus: canonical\n---\nM17-09 segue aberto.\n"},
    )
    r = _run(
        tmp_path,
        ["v2/backend/apps/core/services/x.py"],
        commits="feat(import): coordenador por CPF\n\n- guard herdado de M17-09",
    )
    assert r.returncode == 0, f"mencao de achado em commit de feat bloqueou:\n{r.stdout}"


def test_saida_explica_o_porque(tmp_path):
    _monta(tmp_path, {"v2/docs/specs/backend/pagamento.spec.md": SPEC})
    r = _run(
        tmp_path,
        ["v2/backend/apps/core/services/pagamento.py"],
        commits="fix(pagamento): x\n\nCloses #1610",
    )
    saida = r.stdout + r.stderr
    assert "doc-nao-afetada" in saida, "a saida deve ensinar como declarar o waiver"
