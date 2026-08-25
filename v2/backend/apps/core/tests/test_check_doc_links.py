"""
Self-verification do checador de links, incluindo F.5 (caminho em crase).

O CHECADOR NAO TINHA TESTE NENHUM ate 2026-08-25, apesar de ser step `[required]`
no CI desde sempre. Este arquivo cobre o comportamento existente e o novo.

F.5 — REFERENCIA POR CAMINHO EM CRASE NAO E LINK. Escrever `` `v2/docs/X.md` ``
em vez de `[X](../X.md)` produz um texto que PARECE referencia e que nenhum
checador olha: a regex de link so casa `[texto](alvo)`. Foi assim que 11 arquivos
SEC ficaram inalcancaveis com o gate verde.

CALIBRAGEM: AVISA, nao bloqueia. Medido em 2026-08-25 — 211 referencias com forma
de caminho em doc vivo, 22 nao resolvem, e so ~11 exigem acao. Metade sao
relatorios datados (candidatos a `_archive/`) e declaracoes historicas corretas,
inclusive uma no proprio plano deste trabalho, que afirma — com razao — que
`graphify-out/wiki/index.md` nao existe. 50% de precisao esta abaixo da barra que
os outros detectores usam para bloquear, e bloquear aqui reprovaria PR alheio por
divida de outra frente.

SO CONTA O QUE TEM FORMA DE CAMINHO (contem `/`). Nome solto em crase — «ver
`ACHADOS_REAIS.md`» — e prosa nomeando um documento, nao referencia quebrada:
incluir isso levava 164 achados de 610, quase todos ruido.

Verifica que:
1. Baseline limpo passa.
2. Link markdown quebrado continua BLOQUEANDO (comportamento existente).
3. Caminho em crase que nao resolve AVISA e nao bloqueia.
4. Nome solto em crase (sem `/`) nao vira achado.
5. Caminho em crase que resolve nao vira achado.
6. `_archive/` fica fora.
7. A saida nomeia o arquivo de origem e o alvo.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingTypeStubs=false

from __future__ import annotations

import pathlib
import subprocess
import sys

RAIZ_REPO = pathlib.Path(__file__).resolve().parents[5]
SCRIPT = RAIZ_REPO / "scripts" / "check_doc_links.py"


def _monta(base: pathlib.Path, arquivos: dict[str, str]) -> None:
    for rel, conteudo in arquivos.items():
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(conteudo, encoding="utf-8")


def _run(raiz: pathlib.Path):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "docs"],
        cwd=raiz,
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
    )


def test_script_existe():
    assert SCRIPT.exists(), f"check_doc_links.py nao encontrado em {SCRIPT}"


def test_baseline_limpo_passa(tmp_path):
    _monta(tmp_path, {"docs/a.md": "# A\n\n[b](b.md)\n", "docs/b.md": "# B\n"})
    r = _run(tmp_path)
    assert r.returncode == 0, f"baseline limpo reprovou:\n{r.stdout}\n{r.stderr}"


def test_link_markdown_quebrado_bloqueia(tmp_path):
    """Comportamento que ja existia — fixado para nao regredir."""
    _monta(tmp_path, {"docs/a.md": "# A\n\n[sumiu](nao-existe.md)\n"})
    r = _run(tmp_path)
    assert r.returncode != 0, f"link quebrado passou:\n{r.stdout}"
    assert "nao-existe.md" in r.stdout


def test_caminho_em_crase_quebrado_avisa_sem_bloquear(tmp_path):
    _monta(tmp_path, {"docs/a.md": "# A\n\nVer `v2/docs/NAO_EXISTE.md` para detalhes.\n"})
    r = _run(tmp_path)
    assert r.returncode == 0, f"crase deveria avisar, nao bloquear:\n{r.stdout}"
    assert "AVISO" in r.stdout, f"o aviso precisa aparecer:\n{r.stdout}"
    assert "v2/docs/NAO_EXISTE.md" in r.stdout
    assert "docs/a.md" in r.stdout.replace("\\", "/"), "a saida deve nomear a origem"


def test_nome_solto_em_crase_nao_vira_achado(tmp_path):
    """«Ver `ACHADOS_REAIS.md`» e prosa nomeando um doc, nao referencia.

    Contar nome solto levava a 164 achados de 610 — ruido que treina a ignorar.
    """
    _monta(tmp_path, {"docs/a.md": "# A\n\nVer `ACHADOS_REAIS.md` e `rbac.spec.md`.\n"})
    r = _run(tmp_path)
    assert r.returncode == 0
    assert "ACHADOS_REAIS.md" not in r.stdout, f"nome solto virou achado:\n{r.stdout}"


def test_caminho_em_crase_que_resolve_nao_avisa(tmp_path):
    _monta(
        tmp_path,
        {"docs/a.md": "# A\n\nVer `docs/sub/b.md`.\n", "docs/sub/b.md": "# B\n"},
    )
    r = _run(tmp_path)
    assert r.returncode == 0
    assert "AVISO" not in r.stdout, f"caminho que resolve virou aviso:\n{r.stdout}"


def test_archive_fica_fora(tmp_path):
    _monta(tmp_path, {"docs/_archive/velho.md": "Ver `v2/docs/NAO_EXISTE.md`.\n"})
    r = _run(tmp_path)
    assert r.returncode == 0
    assert "NAO_EXISTE" not in r.stdout, f"_archive foi varrido:\n{r.stdout}"
