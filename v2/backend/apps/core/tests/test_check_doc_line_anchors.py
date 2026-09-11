"""
Self-verification do check de ancoras de linha em specs (use simbolo, nao linha).

O PROBLEMA E DE CLASSE, NAO DE ARQUIVO. O doc-drift-auditor achou ancoras
`arquivo.py:NNN` obsoletas no imports.spec.md: o importer cresceu ~500->1900
linhas e nenhuma ancora foi re-derivada, entao quem clica cai em codigo nao
relacionado. Medido em 2026-09-11: 52 linhas de ancora-com-linha em 17 specs,
contra ~575 referencias a nivel de arquivo/simbolo (~92%). A ancora-com-linha e
a minoria de ~8% que drifta a cada movimento de codigo.

CALIBRAGEM: BLOQUEIA. Preciso (regex de `arquivo.ext:NNN`), com a divida
existente varrida ANTES de trancar (limpar primeiro, trancar depois), e
conserta-se DENTRO do PR — troca-se a ancora pelo nome do simbolo, que e estavel
a movimento de linha. A excecao deliberada entra no allowlist COM MOTIVO, mesmo
contrato do `adr-numeros-allowlist.txt`.

Verifica que:
1. O script existe.
2. Corpus so com referencia a simbolo/arquivo (sem linha) passa.
3. Ancora inline `arquivo.py:NNN` em backtick bloqueia e nomeia o arquivo:linha.
4. Ancora em range `arquivo.py:NNN-MMM` bloqueia.
5. Ancora em parenteses `(arquivo.py:NNN)` na prosa bloqueia.
6. Simbolo/arquivo sem numero de linha (`x.py`, `PROTECTED_FIELDS`) passa.
7. Link markdown a arquivo `[x](../x.py)` passa (nao tem `:NNN`).
8. Ancora dentro de bloco de codigo cercado (```) e ignorada.
9. Ancora no frontmatter e ignorada (sources_of_truth e caminho puro).
10. Allowlist suprime so a ancora listada, e so ela.
11. Allowlist exige motivo — entrada nua nao vale.
12. Spec fora de escopo (status historical/superseded) e ignorada.
13. A saida ensina a correcao (usar o nome do simbolo).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingTypeStubs=false

from __future__ import annotations

import pathlib
import subprocess
import sys

BACKEND_ROOT = pathlib.Path(__file__).resolve().parents[3]
SCRIPT = BACKEND_ROOT / "scripts" / "check_doc_line_anchors.py"

SPECS = "v2/docs/specs/backend"
ALLOWLIST = "v2/docs/.doc-line-anchors-allowlist.txt"


def _spec(raiz: pathlib.Path, rel: str, corpo: str, status: str = "canonical") -> None:
    """Escreve uma spec com frontmatter minimo valido + corpo."""
    p = raiz / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    fm = f"---\ntitle: T\nstatus: {status}\nlast_verified: 2026-09-11\nsources_of_truth:\n  - v2/backend/apps/core/x.py\n---\n\n"
    p.write_text(fm + corpo, encoding="utf-8")


def _allowlist(raiz: pathlib.Path, conteudo: str) -> None:
    p = raiz / ALLOWLIST
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(conteudo, encoding="utf-8")


def _run(raiz: pathlib.Path):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(raiz)],
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
    )


def test_script_existe():
    assert SCRIPT.exists(), f"check_doc_line_anchors.py nao encontrado em {SCRIPT}"


def test_corpus_limpo_passa(tmp_path):
    """Sem isto o gate nasce vermelho e alguem o desliga."""
    _spec(
        tmp_path,
        f"{SPECS}/limpa.spec.md",
        "O `ExportContractImporter` define `PROTECTED_FIELDS` e usa "
        "[resolvers](../../../backend/apps/core/services/resolvers.py).\n",
    )
    r = _run(tmp_path)
    assert r.returncode == 0, f"corpus limpo reprovou:\n{r.stdout}\n{r.stderr}"


def test_ancora_inline_bloqueia(tmp_path):
    _spec(tmp_path, f"{SPECS}/suja.spec.md", "O `PROTECTED_FIELDS` fica em `export_contract_importer.py:50`.\n")
    r = _run(tmp_path)
    assert r.returncode == 1, f"ancora de linha passou:\n{r.stdout}"
    assert "export_contract_importer.py:50" in r.stdout
    assert "suja.spec.md" in r.stdout


def test_ancora_em_range_bloqueia(tmp_path):
    _spec(tmp_path, f"{SPECS}/range.spec.md", "Ver `dat_compra.py:145-153` (auto-status).\n")
    r = _run(tmp_path)
    assert r.returncode == 1, f"ancora em range passou:\n{r.stdout}"
    assert "dat_compra.py:145-153" in r.stdout


def test_ancora_em_parenteses_bloqueia(tmp_path):
    _spec(tmp_path, f"{SPECS}/paren.spec.md", "O guard superuser (usuarios_import.py:288) recusa a linha.\n")
    r = _run(tmp_path)
    assert r.returncode == 1, f"ancora em parenteses passou:\n{r.stdout}"
    assert "usuarios_import.py:288" in r.stdout


def test_ancora_encadeada_por_virgula_bloqueia(tmp_path):
    """`x.py:9-10,219-225,353-358` — a docstring cita varios ranges no mesmo arquivo."""
    _spec(tmp_path, f"{SPECS}/chain.spec.md", "Docstrings citam `views/dat_module.py:9-10,219-225,353-358`.\n")
    r = _run(tmp_path)
    assert r.returncode == 1, f"cadeia por virgula passou:\n{r.stdout}"
    assert "views/dat_module.py:9-10,219-225,353-358" in r.stdout, f"a cadeia inteira deve ser reportada:\n{r.stdout}"


def test_bare_e_porta_ficam_fora_do_gate(tmp_path):
    """CALIBRAGEM: bare `:305` e porta `:9443` sao sintaticamente identicas -> nenhuma
    e hard-banida. Porta e conteudo legitimo; reprova-la desligaria o gate. A bare
    e varrida uma vez e regressao dela e caso do doc-drift-auditor."""
    _spec(
        tmp_path,
        f"{SPECS}/bare.spec.md",
        "A checagem vive em `availability_service.py` (`:305`); Portainer em `127.0.0.1:9443` (`:9443`).\n",
    )
    r = _run(tmp_path)
    assert r.returncode == 0, f"bare/porta viraram bloqueio (falso-positivo de calibragem):\n{r.stdout}"


def test_ancora_yml_bloqueia(tmp_path):
    _spec(tmp_path, f"{SPECS}/infra.spec.md", "O beat roda em `docker-compose.prod.yml:44`.\n")
    r = _run(tmp_path)
    assert r.returncode == 1, f"ancora .yml passou:\n{r.stdout}"
    assert "docker-compose.prod.yml:44" in r.stdout


def test_ancora_sh_bloqueia(tmp_path):
    _spec(tmp_path, f"{SPECS}/sh.spec.md", "O dump esta em `backup_db.sh:31`.\n")
    r = _run(tmp_path)
    assert r.returncode == 1, f"ancora .sh passou:\n{r.stdout}"
    assert "backup_db.sh:31" in r.stdout


def test_horario_em_backtick_nao_e_ancora(tmp_path):
    """`09:00` tem digito antes do `:` — nao e ancora de linha (evita falso-positivo)."""
    _spec(tmp_path, f"{SPECS}/hora.spec.md", "O evento vai das `09:00` as `12:00` (RD-06).\n")
    r = _run(tmp_path)
    assert r.returncode == 0, f"horario em backtick virou ancora:\n{r.stdout}"


def test_simbolo_sem_linha_passa(tmp_path):
    _spec(tmp_path, f"{SPECS}/simbolo.spec.md", "O `_assign_groups` em `usuarios_import.py` aplica o gate.\n")
    r = _run(tmp_path)
    assert r.returncode == 0, f"referencia a simbolo sem linha reprovou:\n{r.stdout}"


def test_link_markdown_passa(tmp_path):
    _spec(
        tmp_path,
        f"{SPECS}/link.spec.md",
        "Ver [importer](../../../backend/apps/core/services/export_contract_importer.py).\n",
    )
    r = _run(tmp_path)
    assert r.returncode == 0, f"link markdown a arquivo reprovou:\n{r.stdout}"


def test_bloco_cercado_ignorado(tmp_path):
    _spec(
        tmp_path,
        f"{SPECS}/fence.spec.md",
        "Exemplo de saida:\n\n```\ntraceback em foo.py:42 aqui\n```\n\nFim.\n",
    )
    r = _run(tmp_path)
    assert r.returncode == 0, f"ancora dentro de bloco cercado bloqueou:\n{r.stdout}"


def test_frontmatter_ignorado(tmp_path):
    """sources_of_truth e caminho puro; nao deve ser lido como ancora mesmo com :NNN improvavel."""
    p = tmp_path / SPECS / "fm.spec.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "---\ntitle: T\nstatus: canonical\nlast_verified: 2026-09-11\n"
        "sources_of_truth:\n  - v2/backend/apps/core/x.py\n---\n\nCorpo limpo, so `x.py`.\n",
        encoding="utf-8",
    )
    r = _run(tmp_path)
    assert r.returncode == 0, f"frontmatter derrubou o check:\n{r.stdout}"


def test_allowlist_suprime_so_a_listada(tmp_path):
    """«Limpar primeiro, trancar depois» — mesmo contrato do gate de ADR."""
    _spec(
        tmp_path,
        f"{SPECS}/rbac.spec.md",
        "Auditoria: `admin.py:371-384` (perdoada) e `views.py:99` (nao perdoada).\n",
    )
    _allowlist(
        tmp_path,
        f"{SPECS}/rbac.spec.md admin.py:371-384 — range de auditoria de seguranca, deliberado\n",
    )
    r = _run(tmp_path)
    assert r.returncode == 1, "a ancora fora do allowlist deveria bloquear"
    assert "views.py:99" in r.stdout
    assert "admin.py:371-384" not in r.stdout, f"o allowlist nao suprimiu a ancora listada:\n{r.stdout}"


def test_allowlist_exige_motivo(tmp_path):
    """Entrada sem motivo e o comeco da erosao — o gate volta a nao valer nada."""
    _spec(tmp_path, f"{SPECS}/rbac.spec.md", "Auditoria: `admin.py:371-384`.\n")
    _allowlist(tmp_path, f"{SPECS}/rbac.spec.md admin.py:371-384\n")
    r = _run(tmp_path)
    assert r.returncode == 1, "entrada de allowlist sem motivo foi aceita"
    assert "motivo" in r.stdout.lower() or "justific" in r.stdout.lower()


def test_spec_fora_de_escopo_ignorada(tmp_path):
    """Historico nao se corrige (ADR-017 item 5) — apontar ancora nele e ruido."""
    _spec(
        tmp_path,
        f"{SPECS}/velha.spec.md",
        "Ver `export_contract_importer.py:50`.\n",
        status="superseded",
    )
    r = _run(tmp_path)
    assert r.returncode == 0, f"spec fora de escopo virou bloqueio:\n{r.stdout}"


def test_saida_ensina_a_correcao(tmp_path):
    """Sem isto, quem for consertar nao sabe que a correcao e nomear o simbolo."""
    _spec(tmp_path, f"{SPECS}/ensina.spec.md", "Ver `export_contract_importer.py:50`.\n")
    r = _run(tmp_path)
    assert r.returncode == 1
    assert "simbolo" in r.stdout.lower() or "símbolo" in r.stdout.lower()
