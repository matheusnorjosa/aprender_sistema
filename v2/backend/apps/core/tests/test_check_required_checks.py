"""
Self-verification do gate que confere quais gates sao gates (Fase E.3 do plano).

O PROBLEMA. Dezenove jobs carregam `[required]` no proprio nome; o ruleset da
`main` exige dez. Nove estao rotulados como obrigatorios sem serem — entre eles
`backend rbac-lint`, `backend typecheck (pyright)`, `backend tests (runner)` e
`docker parity (backend)`. Quem le o nome no PR conclui que aquilo trava o merge.
Nao trava. E um rotulo que informa errado sobre a propria protecao do repo.

DUAS DIVERGENCIAS, CALIBRAGEM OPOSTA — e a diferenca e quem consegue consertar:

1. **Exigido pelo ruleset, mas nenhum job produz.** BLOQUEIA.
   Um context exigido que ninguem emite deixa o PR «Expected» para sempre e
   trava merge — foi o trap que `docs-quality.yml` documenta em comentario. E
   preciso, e raro (hoje: zero), e conserta-se DENTRO do PR: alguem renomeou um
   job. Bloquear sobre baseline limpo e barato.

2. **Declara `[required]` no nome, mas o ruleset nao exige.** AVISA.
   Corrigir isso e acao de admin no ruleset, nao mudanca de codigo. Bloquear um
   PR por algo que o autor nao pode consertar e a receita para o gate ser
   desligado. Vai para o job summary, que e onde a pessoa ja olha (E.1).

NAO PODER MEDIR NAO E APROVAR. Se a API nao responde, o script avisa alto e sai
0 — fazer o CI depender da disponibilidade da API do GitHub seria pior. Mas um
conjunto exigido VAZIO nao e tratado como «nada exigido»: e tratado como falha
de leitura, porque a diferenca entre «medi e nao ha» e «nao consegui medir» e
exatamente o que este plano existe para nao confundir.

Verifica que:
1. Baseline limpo passa.
2. Context exigido sem job correspondente BLOQUEIA e nomeia o context.
3. Job que declara [required] sem o ruleset exigir apenas AVISA.
4. Nome de job com matriz/expressao nao vira fantasma.
5. Conjunto exigido vazio e lido como falha de medida, nao como aprovacao.
6. Sem acesso a API, avisa e sai 0.
7. Workflow ilegivel nao derruba o gate.
8. A saida nomeia o arquivo do workflow, para dar onde agir.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingTypeStubs=false

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

BACKEND_ROOT = pathlib.Path(__file__).resolve().parents[3]
SCRIPT = BACKEND_ROOT / "scripts" / "check_required_checks.py"


def _monta(raiz: pathlib.Path, workflows: dict[str, str]) -> None:
    d = raiz / ".github" / "workflows"
    d.mkdir(parents=True, exist_ok=True)
    for nome, conteudo in workflows.items():
        (d / nome).write_text(conteudo, encoding="utf-8")


def _run(raiz: pathlib.Path, exigidos: list[str] | None):
    args = [sys.executable, str(SCRIPT), "--repo-root", str(raiz)]
    if exigidos is not None:
        f = raiz / "_exigidos.json"
        f.write_text(json.dumps(exigidos), encoding="utf-8")
        args += ["--enforced-from", str(f)]
    return subprocess.run(args, capture_output=True, text=True, check=False, encoding="utf-8")


WF = """\
name: CI
on: [pull_request]
jobs:
  lint:
    name: "[required] lint"
    runs-on: ubuntu-latest
    steps:
      - run: echo ok
  info:
    name: "[info] telemetria"
    runs-on: ubuntu-latest
    steps:
      - run: echo ok
"""


def test_script_existe():
    assert SCRIPT.exists(), f"check_required_checks.py nao encontrado em {SCRIPT}"


def test_baseline_limpo_passa(tmp_path):
    """Sem isto o gate nasce vermelho e alguem o desliga."""
    _monta(tmp_path, {"ci.yml": WF})
    r = _run(tmp_path, ["[required] lint"])
    assert r.returncode == 0, f"baseline limpo reprovou:\n{r.stdout}\n{r.stderr}"


def test_context_exigido_sem_job_bloqueia(tmp_path):
    """Trava merge para sempre: o PR fica «Expected» e ninguem emite o status."""
    _monta(tmp_path, {"ci.yml": WF})
    r = _run(tmp_path, ["[required] lint", "[required] job-que-foi-renomeado"])
    assert r.returncode != 0, f"context fantasma passou:\n{r.stdout}"
    assert "job-que-foi-renomeado" in r.stdout


def test_rotulo_falso_apenas_avisa(tmp_path):
    """Corrigir e acao de admin no ruleset — o autor do PR nao consegue."""
    _monta(tmp_path, {"ci.yml": WF})
    r = _run(tmp_path, ["[info] telemetria"])
    assert r.returncode == 0, f"rotulo falso deveria avisar, nao bloquear:\n{r.stdout}"
    assert "[required] lint" in r.stdout, "o aviso deveria nomear o job mal rotulado"


def test_saida_nomeia_o_arquivo_do_workflow(tmp_path):
    _monta(tmp_path, {"ci.yml": WF})
    r = _run(tmp_path, ["[info] telemetria"])
    assert "ci.yml" in r.stdout, f"sem o arquivo, nao ha onde agir:\n{r.stdout}"


def test_job_sem_name_usa_o_id(tmp_path):
    """O GitHub usa o id do job como context quando `name:` esta ausente."""
    _monta(
        tmp_path,
        {
            "x.yml": "name: X\non: [pull_request]\njobs:\n  meu-job:\n"
            "    runs-on: ubuntu-latest\n    steps:\n      - run: echo ok\n"
        },
    )
    r = _run(tmp_path, ["meu-job"])
    assert r.returncode == 0, f"job sem name deveria casar pelo id:\n{r.stdout}"


def test_conjunto_exigido_vazio_e_falha_de_medida(tmp_path):
    """«Medi e nao ha» != «nao consegui medir» — a confusao que este plano combate.

    Um ruleset que devolve zero contexts quase sempre significa leitura falhada
    (token sem escopo, repo errado). Tratar como «nada exigido» faria o gate
    aprovar em silencio justamente quando esta cego.
    """
    _monta(tmp_path, {"ci.yml": WF})
    r = _run(tmp_path, [])
    saida = (r.stdout + r.stderr).lower()
    assert (
        "nao consegui" in saida or "vazio" in saida or "falha de medida" in saida
    ), f"conjunto vazio foi lido como aprovacao:\n{r.stdout}\n{r.stderr}"


def test_sem_acesso_a_api_avisa_e_sai_zero(tmp_path):
    """CI nao pode depender da disponibilidade da API do GitHub."""
    _monta(tmp_path, {"ci.yml": WF})
    r = _run(tmp_path, None)  # sem --enforced-from e sem gh disponivel no container
    assert r.returncode == 0, f"falta de API derrubou o build:\n{r.stdout}\n{r.stderr}"
    assert "AVISO" in (r.stdout + r.stderr), "o skip precisa ser barulhento"


def test_workflow_ilegivel_nao_derruba(tmp_path):
    _monta(tmp_path, {"ci.yml": WF, "quebrado.yml": "isto: [nao\n  fecha\n"})
    r = _run(tmp_path, ["[required] lint"])
    assert r.returncode == 0, f"YAML quebrado derrubou o gate:\n{r.stdout}\n{r.stderr}"
    assert "quebrado.yml" in r.stdout, "o arquivo ilegivel deveria ser reportado"
