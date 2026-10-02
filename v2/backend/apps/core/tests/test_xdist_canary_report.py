"""
Self-verification do relatorio do canary do backend (`v2/scripts/xdist_canary_report.py`).

O PROBLEMA. O canary roda `pytest apps` inteiro num banco MIGRADO (o gate do PR roda
`--no-migrations`). De 02/07 a 28/09 ele ficou vermelho em 16 runs seguidos e ninguem
viu: as celulas terminam verdes de proposito e o alerta ia como comentario na #677,
fechada desde 23/04. O workflow agora abre/comenta/fecha uma issue propria, e QUEM
DECIDE e este script — por isso a decisao tem teste.

NAO PODER MEDIR NAO E APROVAR. So um run COMPLETO E LIMPO fecha a issue:
`refs/heads/main`, sem `extra_pytest_args`, todas as celulas da matriz com artefato e
metadata, zero falhas. Qualquer outra coisa e "nao mediu": o job fica vermelho e nada
fecha. Run nao oficial (outro ref ou suite filtrada) nunca toca na issue da main: so o summary.

CONTAGEM DUPLA. O id do junit (`apps.core.tests.mod.Classe::teste`) e o do log
(`apps/core/tests/mod.py::Classe::teste`) nunca coincidiam: cada falha aparecia duas
vezes, a segunda com a assinatura falsa `failed-from-log-without-junit-entry` (14 onde
havia 7).

Verifica que:
1. Run completo e limpo da main fecha.
2. Falha em run oficial abre ou comenta, e cada teste conta uma vez so.
3. Artefato ausente (0 ou 3 de 4 celulas) e "nao mediu", nunca "limpo".
4. Celula sem metadata e "nao mediu".
5. Ref de branch: resultado so no summary (limpo fica verde; falha fica vermelho), sem tocar na issue.
6. `extra_pytest_args`: idem; celula faltando continua "nao mediu".
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingTypeStubs=false

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

from apps.core.tests.ambiente_repo import exige_raiz_do_repo


def _script() -> pathlib.Path:
    """O relatorio mora em `<raiz>/v2/scripts/`, fora do que o container de dev monta."""
    return exige_raiz_do_repo() / "v2" / "scripts" / "xdist_canary_report.py"


MAIN = "refs/heads/main"
CELULAS = (("2", "loadscope"), ("2", "loadfile"), ("auto", "loadscope"), ("auto", "loadfile"))

JUNIT_LIMPO = """<?xml version="1.0" encoding="utf-8"?>
<testsuites><testsuite name="pytest" tests="2" failures="0" errors="0">
<testcase classname="apps.core.tests.test_a" name="test_ok" time="0.1"/>
<testcase classname="apps.core.tests.test_b.TestX" name="test_ok[p-1]" time="0.1"/>
</testsuite></testsuites>
"""

JUNIT_FALHA = """<?xml version="1.0" encoding="utf-8"?>
<testsuites><testsuite name="pytest" tests="2" failures="2" errors="0">
<testcase classname="apps.core.tests.test_a" name="test_quebra" time="0.1">
<failure message="django.db.utils.IntegrityError: duplicate key value">trace</failure>
</testcase>
<testcase classname="apps.core.tests.test_b.TestX" name="test_param[a/b-1]" time="0.1">
<failure message="AssertionError: assert 1 == 2">trace</failure>
</testcase>
</testsuite></testsuites>
"""

LOG_FALHA = """\
FAILED apps/core/tests/test_a.py::test_quebra - django.db.utils.IntegrityError: duplicate key value
FAILED apps/core/tests/test_b.py::TestX::test_param[a/b-1] - AssertionError: assert 1 == 2
2 failed, 10 passed in 3.00s
"""


def _celula(
    base: pathlib.Path, workers: str, dist: str, *, junit: str, log: str = "", exit_code: int = 0, metadata=True
):
    d = base / f"xdist-canary-{workers}w-{dist}"
    d.mkdir(parents=True)
    (d / "xdist-canary-junit.xml").write_text(junit, encoding="utf-8")
    (d / "xdist-canary-pytest.log").write_text(log, encoding="utf-8")
    if metadata:
        meta = {"workers": workers, "dist": dist, "exit_code": exit_code, "duration_seconds": 10}
        (d / "xdist-canary-metadata.json").write_text(json.dumps(meta), encoding="utf-8")


def _matriz_limpa(base: pathlib.Path):
    for w, dist in CELULAS:
        _celula(base, w, dist, junit=JUNIT_LIMPO)


def _run(tmp_path: pathlib.Path, artefatos: pathlib.Path, *, ref=MAIN, extra="", celulas=4):
    saida_json = tmp_path / "report.json"
    saida_md = tmp_path / "report.md"
    r = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--artifacts-dir",
            str(artefatos),
            "--output-json",
            str(saida_json),
            "--output-md",
            str(saida_md),
            f"--ref={ref}",
            # Forma com "=": o valor comeca com "-" (ex.: "-k teste") e o workflow passa assim.
            f"--extra-pytest-args={extra}",
            f"--expected-cells={celulas}",
        ],
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
    )
    assert r.returncode == 0, f"o relatorio deve sair 0 (quem decide o vermelho e o workflow):\n{r.stdout}\n{r.stderr}"
    return json.loads(saida_json.read_text(encoding="utf-8")), saida_md.read_text(encoding="utf-8")


def test_script_existe():
    script = _script()
    assert script.exists(), f"xdist_canary_report.py nao encontrado em {script}"


def test_limpo_completo_na_main_fecha(tmp_path):
    art = tmp_path / "art"
    _matriz_limpa(art)
    payload, md = _run(tmp_path, art)
    assert payload["runs_total"] == 4
    assert payload["runs_with_failures"] == 0
    assert payload["alerta"]["estado"] == "limpo"
    assert payload["alerta"]["acao"] == "fechar"
    assert payload["alerta"]["motivos"] == []
    assert "limpo" in md


def test_falha_oficial_abre_ou_comenta_e_conta_cada_teste_uma_vez(tmp_path):
    art = tmp_path / "art"
    for w, dist in CELULAS:
        _celula(art, w, dist, junit=JUNIT_FALHA, log=LOG_FALHA, exit_code=1)
    payload, _ = _run(tmp_path, art)
    assert payload["alerta"]["estado"] == "falha"
    assert payload["alerta"]["acao"] == "abrir_ou_comentar"
    assert payload["runs_with_failures"] == 4
    testes = {item["test_id"]: item["count"] for item in payload["recurrent_failed_tests"]}
    # 2 testes distintos, cada um em 4 celulas — nao 4 ids (junit + log) com contagem dobrada.
    assert testes == {
        "apps.core.tests.test_a::test_quebra": 4,
        "apps.core.tests.test_b.TestX::test_param[a/b-1]": 4,
    }, testes
    for linha in payload["matrix_results"]:
        assert linha["failed_tests_count"] == 2, linha
        assert "failed-from-log-without-junit-entry" not in linha["failure_signatures"], linha


def test_falha_so_no_log_sem_junit_ainda_conta(tmp_path):
    """Sem junit (worker morreu antes de escrever), o log continua sendo a fonte."""
    art = tmp_path / "art"
    for w, dist in CELULAS:
        _celula(art, w, dist, junit=JUNIT_LIMPO)
    d = art / "xdist-canary-2w-loadscope"
    (d / "xdist-canary-junit.xml").unlink()
    (d / "xdist-canary-pytest.log").write_text(LOG_FALHA, encoding="utf-8")
    (d / "xdist-canary-metadata.json").write_text(
        json.dumps({"workers": "2", "dist": "loadscope", "exit_code": 1, "duration_seconds": 5}), encoding="utf-8"
    )
    payload, _ = _run(tmp_path, art)
    assert payload["alerta"]["estado"] == "falha"
    linha = next(x for x in payload["matrix_results"] if x["artifact_name"] == "xdist-canary-2w-loadscope")
    assert linha["failed_tests_count"] == 2, linha


def test_artefatos_ausentes_nao_mediu(tmp_path):
    payload, _ = _run(tmp_path, tmp_path / "nao-existe")
    assert payload["runs_total"] == 0
    assert payload["alerta"]["estado"] == "nao_mediu"
    assert payload["alerta"]["acao"] == "abrir_ou_comentar"
    assert any("0 de 4" in m for m in payload["alerta"]["motivos"]), payload["alerta"]


def test_celula_faltando_nao_mediu(tmp_path):
    """Matriz cancelada ou celula que morreu antes do upload: 3 de 4 nao e run limpo."""
    art = tmp_path / "art"
    for w, dist in CELULAS[:3]:
        _celula(art, w, dist, junit=JUNIT_LIMPO)
    payload, _ = _run(tmp_path, art)
    assert payload["runs_with_failures"] == 0
    assert payload["alerta"]["estado"] == "nao_mediu"
    assert payload["alerta"]["acao"] != "fechar"
    assert any("3 de 4" in m for m in payload["alerta"]["motivos"]), payload["alerta"]


def test_celula_sem_metadata_nao_mediu(tmp_path):
    """Sem metadata o exit_code e desconhecido — antes virava 0 e contava como passou."""
    art = tmp_path / "art"
    for w, dist in CELULAS[:3]:
        _celula(art, w, dist, junit=JUNIT_LIMPO)
    _celula(art, *CELULAS[3], junit=JUNIT_LIMPO, metadata=False)
    payload, _ = _run(tmp_path, art)
    assert payload["alerta"]["estado"] == "nao_mediu"
    assert payload["alerta"]["acao"] != "fechar"
    assert any("xdist-canary-autow-loadfile" in m for m in payload["alerta"]["motivos"]), payload["alerta"]


def test_ref_de_branch_limpo_nao_toca_na_issue(tmp_path):
    """Run nao oficial limpo: verde e so o summary (nao comenta 'nao mediu' na issue da main)."""
    art = tmp_path / "art"
    _matriz_limpa(art)
    payload, _ = _run(tmp_path, art, ref="refs/heads/perf/experimento")
    assert payload["alerta"]["estado"] == "limpo"
    assert payload["alerta"]["acao"] == "so_resumo"
    assert any("refs/heads/perf/experimento" in m for m in payload["alerta"]["motivos"]), payload["alerta"]


def test_falha_em_branch_nao_toca_na_issue_da_main(tmp_path):
    art = tmp_path / "art"
    for w, dist in CELULAS:
        _celula(art, w, dist, junit=JUNIT_FALHA, log=LOG_FALHA, exit_code=1)
    payload, _ = _run(tmp_path, art, ref="refs/heads/perf/experimento")
    assert payload["alerta"]["estado"] == "falha"
    assert payload["alerta"]["acao"] == "so_resumo"


def test_extra_pytest_args_nao_fecha_nem_comenta(tmp_path):
    """Quem roda `-k um_teste` para conferir o conserto nao pode fechar o alerta dos outros,
    nem poluir a issue: o resultado fica so no summary do run."""
    art = tmp_path / "art"
    _matriz_limpa(art)
    payload, _ = _run(tmp_path, art, extra="-k test_versioning")
    assert payload["alerta"]["estado"] == "limpo"
    assert payload["alerta"]["acao"] == "so_resumo"
    assert any("-k test_versioning" in m for m in payload["alerta"]["motivos"]), payload["alerta"]


def test_nao_oficial_sem_artefato_continua_nao_mediu(tmp_path):
    """Nao oficial nao vira desculpa: celula faltando ainda e 'nao mediu' (job vermelho), so nao toca na issue."""
    art = tmp_path / "art"
    art.mkdir()
    payload, _ = _run(tmp_path, art, extra="-k test_versioning")
    assert payload["alerta"]["estado"] == "nao_mediu"
    assert payload["alerta"]["acao"] == "so_resumo"
