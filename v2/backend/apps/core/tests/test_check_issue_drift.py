"""
Self-verification do reconciliador de issue (Fase A.1 do PLAN_doc_drift_2026-08-25).

O QUE OS GATES ANTERIORES NAO ALCANCAM. As Fases B–F impedem drift NOVO: sao
todas por PR. Nenhuma limpa o que ja estava la quando foram construidas — e a
Fase A, que era exatamente isso, nunca foi executada.

CASO VERIFICADO PONTA A PONTA em 2026-08-26: a issue **#1611 esta CLOSED**, e
`v2/docs/specs/backend/backup-dr.spec.md:40` diz "Restore (leitura) — quebrado",
`:109` diz "(M26-01, P0, issue #1611)", e `INDEX_SDD.md:81` repete "restore
quebrado, #1611 P0". Quem abre a spec CANONICA de DR hoje conclui que o restore
de producao nao funciona. O gate da Fase C bloquearia isso — mas o fix mergeou
antes dele existir, e gate por PR nao alcanca o passado.

O NUMERO, MEDIDO COM CUIDADO. 146 issues fechadas sao citadas em doc viva, em 305
lugares. **Nao sao 146 mentiras**: "corrigido em #1611" e referencia historica
correta, e contar palavra-chave aqui e a armadilha de sempre — um texto que
descreve a correcao cita a mesma issue. Filtrando para citacao com marcador de
ABERTO (`P0`, `quebrado`, `pendente`, `⛔`) e SEM marcador de corrigido: **59**,
sendo 27 nas specs canonicas.

POR QUE RATCHET, E NAO BLOQUEIO NEM AVISO. Bloquear com 59 pendentes reprova todo
PR no dia 1. Avisar e o que fez o limiar de 180 dias virar decoracao — aviso sem
acao associada e ruido. O ratchet sobre piso medido e o terceiro caminho, e e
padrao provado neste repositorio (cobertura vitest, subida 3x em 4 dias): a
contagem por raiz nao pode CRESCER. A reducao e trabalho de conteudo, de outra
frente; o mecanismo garante que ela nunca ande para tras.

A HEURISTICA E ASSUMIDA, NAO DISFARCADA. "Marcador de aberto na mesma linha" nao
prova que o doc mente — prova que merece triagem. A saida chama isso de suspeita,
e o numero que o ratchet trava e o de suspeitas, nao o de mentiras confirmadas.

Verifica que:
1. Baseline limpo passa.
2. Contagem que CRESCE reprova, e a saida diz onde.
3. Contagem que CAI passa (e sugere apertar o piso).
4. Issue ABERTA descrita como aberta nao e achado.
5. Issue fechada descrita como CORRIGIDA nao e achado.
6. Issue fechada descrita como P0/quebrada E achado.
7. `_archive/` e `status: historical` ficam fora.
8. Sem acesso a API, avisa e sai 0 — nunca aprova por nao ter medido.
9. Piso ausente e tratado como falha de configuracao, nao como zero.
10. A saida nomeia arquivo:linha e o numero da issue.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingTypeStubs=false

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

BACKEND_ROOT = pathlib.Path(__file__).resolve().parents[3]
SCRIPT = BACKEND_ROOT / "scripts" / "check_issue_drift.py"


def _monta(raiz: pathlib.Path, arquivos: dict[str, str]) -> None:
    for rel, conteudo in arquivos.items():
        p = raiz / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(conteudo, encoding="utf-8")


def _run(
    raiz: pathlib.Path,
    fechadas: list[int] | None,
    piso: dict[str, int] | None = None,
    sem_gh: bool = False,
):
    """`sem_gh` remove o `gh` do PATH em vez de torcer para ele nao existir.

    O teste do caminho sem-API passou no CI por acaso: se o runner tivesse `gh`
    autenticado — e tem — ele consultaria as issues de verdade e o teste viraria
    flake. Um teste que depende do ambiente nao testa o que diz testar.
    """
    args = [sys.executable, str(SCRIPT), "--repo-root", str(raiz)]
    if fechadas is not None:
        f = raiz / "_fechadas.json"
        f.write_text(json.dumps(fechadas), encoding="utf-8")
        args += ["--closed-from", str(f)]
    if piso is not None:
        f = raiz / "_piso.json"
        f.write_text(json.dumps(piso), encoding="utf-8")
        args += ["--baseline", str(f)]
    env = dict(os.environ)
    if sem_gh:
        env["PATH"] = str(raiz)  # diretorio sem `gh` dentro
    return subprocess.run(args, capture_output=True, text=True, check=False, encoding="utf-8", env=env)


SPEC_ABERTA = """---
status: canonical
last_verified: 2026-08-01
---

# Backup

> **Restore (leitura) — quebrado.** Ver M26-01, P0, issue #1611.
"""


def test_script_existe():
    assert SCRIPT.exists(), f"check_issue_drift.py nao encontrado em {SCRIPT}"


def test_baseline_limpo_passa(tmp_path):
    _monta(tmp_path, {"v2/docs/x.md": "---\nstatus: canonical\n---\n\nTudo em ordem.\n"})
    r = _run(tmp_path, fechadas=[1611], piso={})
    assert r.returncode == 0, f"baseline limpo reprovou:\n{r.stdout}\n{r.stderr}"


def test_issue_fechada_descrita_como_p0_e_achado(tmp_path):
    _monta(tmp_path, {"v2/docs/specs/backup.spec.md": SPEC_ABERTA})
    r = _run(tmp_path, fechadas=[1611], piso={})
    assert r.returncode != 0, f"issue fechada descrita como P0 passou:\n{r.stdout}"
    assert "1611" in r.stdout
    assert "backup.spec.md" in r.stdout
    assert ":8" in r.stdout or ":7" in r.stdout, f"a saida deve dar a linha:\n{r.stdout}"


def test_issue_aberta_descrita_como_aberta_nao_e_achado(tmp_path):
    """O doc esta CERTO. Marcar isso seria pedir que a doc mentisse."""
    _monta(tmp_path, {"v2/docs/specs/backup.spec.md": SPEC_ABERTA})
    r = _run(tmp_path, fechadas=[9999], piso={})
    assert r.returncode == 0, f"issue aberta virou achado:\n{r.stdout}"


def test_issue_fechada_descrita_como_corrigida_nao_e_achado(tmp_path):
    """«corrigido em #1611» e referencia historica correta, nao drift.

    Contar palavra-chave aqui e a armadilha: o texto que descreve a CORRECAO cita
    a mesma issue que o texto que descreve o defeito.
    """
    _monta(
        tmp_path,
        {
            "v2/docs/specs/backup.spec.md": "---\nstatus: canonical\n---\n\n"
            "O restore estava quebrado; **corrigido** em #1611.\n"
        },
    )
    r = _run(tmp_path, fechadas=[1611], piso={})
    assert r.returncode == 0, f"referencia historica correta virou achado:\n{r.stdout}"


def test_ratchet_reprova_quando_cresce(tmp_path):
    _monta(tmp_path, {"v2/docs/specs/backup.spec.md": SPEC_ABERTA})
    r = _run(tmp_path, fechadas=[1611], piso={"v2/docs/specs": 0})
    assert r.returncode != 0, "crescimento acima do piso deveria reprovar"
    assert "v2/docs/specs" in r.stdout


def test_ratchet_aceita_o_piso_medido(tmp_path):
    _monta(tmp_path, {"v2/docs/specs/backup.spec.md": SPEC_ABERTA})
    r = _run(tmp_path, fechadas=[1611], piso={"v2/docs/specs": 1})
    assert r.returncode == 0, f"contagem igual ao piso deveria passar:\n{r.stdout}"


def test_ratchet_passa_e_sugere_apertar_quando_cai(tmp_path):
    _monta(tmp_path, {"v2/docs/x.md": "---\nstatus: canonical\n---\n\nlimpo\n"})
    r = _run(tmp_path, fechadas=[1611], piso={"v2/docs": 5})
    assert r.returncode == 0
    assert "apert" in r.stdout.lower(), f"queda deveria sugerir apertar o piso:\n{r.stdout}"


def test_historico_e_archive_ficam_fora(tmp_path):
    _monta(
        tmp_path,
        {
            "v2/docs/_archive/velho.md": SPEC_ABERTA,
            "v2/docs/audits/antigo.md": SPEC_ABERTA.replace("canonical", "historical"),
        },
    )
    r = _run(tmp_path, fechadas=[1611], piso={})
    assert r.returncode == 0, f"historico foi varrido:\n{r.stdout}"


def test_sem_api_avisa_e_sai_zero(tmp_path):
    """CI nao pode depender da API do GitHub — mas tambem nao pode aprovar cego."""
    _monta(tmp_path, {"v2/docs/specs/backup.spec.md": SPEC_ABERTA})
    r = _run(tmp_path, fechadas=None, piso={}, sem_gh=True)
    assert r.returncode == 0, f"falta de API derrubou o build:\n{r.stdout}\n{r.stderr}"
    saida = r.stdout + r.stderr
    assert "AVISO" in saida, "o skip precisa ser barulhento"
    assert "verificad" in saida.lower() or "medi" in saida.lower()


def test_piso_ausente_e_falha_de_configuracao(tmp_path):
    """Piso inexistente lido como zero faria o gate reprovar tudo no dia 1 —
    ou, pior, um piso vazio por engano passaria por 'nada pendente'."""
    _monta(tmp_path, {"v2/docs/specs/backup.spec.md": SPEC_ABERTA})
    r = _run(tmp_path, fechadas=[1611], piso=None)
    saida = (r.stdout + r.stderr).lower()
    assert r.returncode == 2, f"piso ausente deveria ser erro de uso:\n{r.stdout}\n{r.stderr}"
    assert "piso" in saida or "baseline" in saida
