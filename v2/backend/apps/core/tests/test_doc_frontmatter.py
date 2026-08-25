"""
Self-verification do leitor de frontmatter compartilhado pelos gates de doc.

Este modulo e o SSOT de "o que esta spec declara como fonte da verdade". Ele
existe porque dois parsers que respondem diferente sobre o mesmo arquivo sao o
proprio gerador de drift que os gates combatem.

O CASO QUE MOTIVOU O ARQUIVO: a regex `^([A-Za-z_]+):\\s*(.*)$` de
`scripts/check_doc_frontmatter.py` casa `sources_of_truth:` com valor vazio e
descarta os itens `  - caminho`. Quem confiasse nela leria toda spec como se nao
declarasse fonte nenhuma — e toda spec ficaria verde por falta de dado.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingTypeStubs=false

from __future__ import annotations

import pathlib
import sys

import pytest

SCRIPTS = pathlib.Path(__file__).resolve().parents[3] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from doc_frontmatter import fora_de_escopo, frontmatter, status  # noqa: E402

SPEC = """---
status: canonical
last_verified: 2026-08-01
verified_at_commit: 5801e17d
sources_of_truth:
  - v2/backend/apps/core/services/pagamento.py
  - v2/backend/apps/core/models/pagamento.py
---

# Pagamento
"""


def test_le_escalares_e_lista():
    campos, fontes = frontmatter(SPEC)
    assert campos["status"] == "canonical"
    assert campos["last_verified"] == "2026-08-01"
    assert campos["verified_at_commit"] == "5801e17d"
    assert fontes == [
        "v2/backend/apps/core/services/pagamento.py",
        "v2/backend/apps/core/models/pagamento.py",
    ]


def test_sources_of_truth_nao_vira_escalar_vazio():
    """O defeito exato do parser antigo: a chave casava com valor vazio."""
    campos, _ = frontmatter(SPEC)
    assert "sources_of_truth" not in campos, "a chave da lista nao pode aparecer como campo escalar vazio"


def test_sem_frontmatter_devolve_vazio():
    campos, fontes = frontmatter("# Doc solto\n\nsem frontmatter\n")
    assert campos == {} and fontes == []


def test_lista_termina_na_proxima_chave():
    texto = """---
sources_of_truth:
  - a.py
  - b.py
status: canonical
---
"""
    campos, fontes = frontmatter(texto)
    assert fontes == ["a.py", "b.py"]
    assert campos["status"] == "canonical"


def test_forma_inline_da_lista():
    texto = "---\nstatus: canonical\nsources_of_truth: [a.py, b.py]\n---\n"
    _, fontes = frontmatter(texto)
    assert fontes == ["a.py", "b.py"]


def test_lista_vazia_e_lista_vazia_nao_ausencia():
    texto = "---\nstatus: canonical\nsources_of_truth:\n---\n"
    campos, fontes = frontmatter(texto)
    assert fontes == []
    assert campos.get("status") == "canonical"


def test_aspas_e_crases_sao_removidas():
    texto = '---\nsources_of_truth:\n  - "a.py"\n  - `b.py`\n---\n'
    _, fontes = frontmatter(texto)
    assert fontes == ["a.py", "b.py"]


def test_corpo_do_doc_nao_e_lido_como_frontmatter():
    texto = "---\nstatus: canonical\n---\n\nstatus: mentira\nsources_of_truth:\n  - x.py\n"
    campos, fontes = frontmatter(texto)
    assert campos["status"] == "canonical"
    assert fontes == [], "o corpo do doc vazou para o frontmatter"


@pytest.mark.parametrize(
    "valor,esperado",
    [("canonical", False), ("historical", True), ("STALE", True), ("draft", False), ("", False)],
)
def test_fora_de_escopo(valor, esperado):
    texto = f"---\nstatus: {valor}\n---\n" if valor else "---\nlast_verified: x\n---\n"
    assert fora_de_escopo(texto) is esperado


def test_status_normaliza_caixa():
    assert status("---\nstatus: Canonical\n---\n") == "canonical"


def test_specs_reais_do_repo_sao_lidas():
    """Guarda contra regressao que so aparece nos arquivos de verdade."""
    raiz = pathlib.Path(__file__).resolve().parents[5]
    specs = sorted((raiz / "v2" / "docs" / "specs").rglob("*.spec.md"))
    assert specs, "nenhuma spec encontrada — o caminho mudou?"

    com_fontes = 0
    for p in specs:
        campos, fontes = frontmatter(p.read_text(encoding="utf-8"))
        assert campos, f"{p.name}: frontmatter nao foi lido"
        assert "sources_of_truth" not in campos, f"{p.name}: lista lida como escalar"
        if fontes:
            com_fontes += 1

    assert com_fontes >= 20, (
        f"so {com_fontes} specs com sources_of_truth; a auditoria mediu 22 — "
        "queda assim costuma ser parser quebrado, nao spec apagada"
    )
