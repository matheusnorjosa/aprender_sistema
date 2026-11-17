"""
Leitor de frontmatter das specs SDD — SSOT unico para os gates de documentacao.

POR QUE EXISTE. `check_doc_impact.py` e `doc_drift_report.py` precisam da MESMA
resposta para "o que esta spec declara como fonte da verdade". Dois parsers que
respondem diferente sobre o mesmo arquivo e literalmente o gerador de drift que
estes gates existem para combater — e a regra do repo e explicita: 1 SSOT por
topico, linkar em vez de duplicar.

COMO LE. O bloco entre os dois `---` vai para o PyYAML com o `BaseLoader`, que
devolve todo valor como TEXTO: data fica "2026-08-01" e commit so de digitos nao
vira numero octal. Cabecalho que nao e YAML valido levanta `ValueError` em vez de
ser lido como "nao declara fonte" (o verde por falta de dado). Ate o FER-64 havia
tres leitores feitos a mao, um deles perdia a lista `sources_of_truth`.

Testes: apps/core/tests/test_doc_frontmatter.py
"""

from __future__ import annotations

import re

import yaml

# Status que declaram o doc como registro, nao como contrato vigente. Historico
# nao se corrige (ADR-017 item 5), entao apontar drift neles e ruido garantido.
STATUS_FORA = {"historical", "stale", "superseded", "deprecated"}

# Bloco do cabecalho: `---` na 1a linha ate a proxima linha que seja so `---`.
_BLOCO = re.compile(r"\A---[ \t]*\r?\n(.*?)^---[ \t]*\r?$", re.S | re.M)
_ABRE = re.compile(r"\A---[ \t]*\r?\n")


class _LeitorTexto(yaml.BaseLoader):
    """`BaseLoader` (todo valor como texto) que recusa chave repetida.

    O YAML aceita chave repetida e fica com a ultima, calado: uma segunda
    `sources_of_truth:` apagaria a primeira lista da medicao.
    """

    def construct_mapping(self, node, deep=False):  # type: ignore[no-untyped-def]
        vistas: set[str] = set()
        for chave_no, _ in node.value:
            chave = self.construct_object(chave_no, deep=deep)
            if isinstance(chave, str):
                if chave in vistas:
                    raise yaml.constructor.ConstructorError(None, None, f"chave repetida: {chave}", chave_no.start_mark)
                vistas.add(chave)
        return super().construct_mapping(node, deep=deep)


def _erro(origem: str, motivo: str) -> ValueError:
    return ValueError(f"{origem}: frontmatter {motivo}" if origem else f"frontmatter {motivo}")


def frontmatter(texto: str, origem: str = "") -> tuple[dict[str, str], list[str]]:
    """Devolve (campos escalares, itens de `sources_of_truth`).

    Sem frontmatter, devolve ({}, []) — o chamador distingue "nao e doc SDD" de
    "e doc SDD que nao declara fonte", que sao coisas diferentes. Cabecalho que nao
    se le levanta `ValueError`; `origem` (o caminho do doc) entra na mensagem.
    """
    m = _BLOCO.match(texto)
    if not m:
        if _ABRE.match(texto):
            raise _erro(origem, "aberto com --- e sem o --- de fechamento")
        return {}, []
    try:
        dados = yaml.load(m.group(1), Loader=_LeitorTexto)
    except yaml.YAMLError as e:
        raise _erro(origem, f"nao e YAML valido: {e}") from e
    if dados is None:
        return {}, []
    if not isinstance(dados, dict):
        raise _erro(origem, f"nao e um mapa chave: valor (veio {type(dados).__name__})")

    campos = {str(k): v.strip() for k, v in dados.items() if isinstance(v, str) and k != "sources_of_truth"}
    bruto = dados.get("sources_of_truth", "")
    if isinstance(bruto, str):
        fontes = [bruto.strip()] if bruto.strip() else []
    elif isinstance(bruto, list):
        fontes = [str(x).strip() for x in bruto if str(x).strip()]
    else:
        raise _erro(origem, "com sources_of_truth que nao e lista de caminhos")
    return campos, fontes


def status(texto: str, origem: str = "") -> str:
    """`status` do frontmatter, em minusculas. Vazio se nao houver."""
    campos, _ = frontmatter(texto, origem)
    return campos.get("status", "").strip().lower()


def fora_de_escopo(texto: str, origem: str = "") -> bool:
    """True quando o doc e registro historico e nao contrato vigente."""
    return status(texto, origem) in STATUS_FORA
