"""Extrai os tempos de deslocamento do PDF da Coordenação Pedagógica para a Integra.

Lê "Relatorio_Tempo_Deslocamento - TODOS MUNICÓPIOS..pdf" (Fortaleza → 92 municípios,
nov/2026) e reescreve o trecho gerado de src/pages/Integra/dados/deslocamento.ts:
municípios, regras do cálculo (páginas 2 e 3), faixas e observações (seção 4).
Só lê o PDF; não toca em banco nem em rede.

Os nomes de coordenador do PDF NÃO saem daqui: a linha deles é descartada, e antes de
gravar o roteiro confere que nenhum deles foi parar no .ts (se foi, para sem gravar e
sem mostrar o nome).

Uso (num venv com pdfplumber, fora do repositório):
    python scripts/integra_extrair_deslocamento.py "<PDF>"
    python scripts/integra_extrair_deslocamento.py "<PDF>" --saida <arquivo .ts>

O .ts precisa ter os marcadores INICIO e FIM abaixo; o que fica fora deles (tipos e
helpers) é escrito à mão e preservado.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber

INICIO = (
    "// <<< INÍCIO DO TRECHO GERADO por scripts/integra_extrair_deslocamento.py:"
    " não editar à mão >>>"
)
FIM = "// <<< FIM DO TRECHO GERADO >>>"

SAIDA_PADRAO = (
    Path(__file__).resolve().parent.parent / "src/pages/Integra/dados/deslocamento.ts"
)

# A marca d'água ("APRENDER EDITORA" na vertical) usa corpo 33 a 46; o texto, até 15.
CORPO_MAXIMO_DO_TEXTO = 20
# A borda de cada coluna fica 5 pt à esquerda da palavra do cabeçalho.
RECUO_DA_COLUNA = 5
TOLERANCIA_DA_LINHA = 2.5

HORA = re.compile(r"^(\d+)h(\d{2})$")
TITULO_UF = re.compile(r"^(.+) \(([A-Z]{2})\) · (\d+) municípios?$")
RODAPE = re.compile(
    r"^Tempo de deslocamento dos coordenadores pedagógicos · .* Página \d+$"
)
CABECALHO_DA_PAGINA = (
    "Aprender Editora",
    "Coordenação Pedagógica · Superintendência de Coordenação",
)
FAIXAS = {
    "Próximo": "proximo",
    "Médio": "medio",
    "Longo": "longo",
    "Muito longo": "muito_longo",
}
TAG_SUSPENSA = "ações suspensas"


def sem_marca_dagua(pagina):
    return pagina.filter(
        lambda o: o.get("object_type") != "char"
        or o.get("size", 0) < CORPO_MAXIMO_DO_TEXTO
    )


def linhas_da_pagina(pagina) -> list[list[dict]]:
    """Palavras agrupadas em linhas (mesma altura), da esquerda para a direita."""
    linhas: list[list[dict]] = []
    for palavra in sorted(pagina.extract_words(), key=lambda w: (w["top"], w["x0"])):
        if linhas and abs(linhas[-1][0]["top"] - palavra["top"]) <= TOLERANCIA_DA_LINHA:
            linhas[-1].append(palavra)
        else:
            linhas.append([palavra])
    return [sorted(linha, key=lambda w: w["x0"]) for linha in linhas]


def texto(linha: list[dict]) -> str:
    return " ".join(w["text"] for w in linha)


def por_coluna(linha: list[dict], bordas: list[float]) -> list[str]:
    celulas: list[list[str]] = [[] for _ in bordas]
    for palavra in linha:
        indice = (
            max(i for i, borda in enumerate(bordas) if palavra["x0"] >= borda)
            if palavra["x0"] >= bordas[0]
            else 0
        )
        celulas[indice].append(palavra["text"])
    return [" ".join(c) for c in celulas]


def juntar(partes: list[str]) -> str:
    """Junta as linhas da célula; "Belo Horizonte/" + "Confins" fica sem espaço."""
    resultado = ""
    for parte in (p.strip() for p in partes if p.strip()):
        resultado = (
            parte
            if not resultado
            else resultado + ("" if resultado.endswith("/") else " ") + parte
        )
    return resultado


def horas(texto_hora: str) -> float:
    achado = HORA.match(texto_hora)
    if not achado:
        raise ValueError(f"hora fora do formato: {texto_hora!r}")
    return int(achado[1]) + int(achado[2]) / 60


@dataclass
class Linha:
    nome: str
    uf: str
    estado: str
    modal: list[str]
    rota: list[str]
    ida: str
    ida_volta: str
    alternativa: list[str]
    faixa: list[str] = field(default_factory=list)
    suspensas: bool = False


def extrair_municipios(
    pdf, proibidos: set[str]
) -> tuple[list[Linha], dict[str, tuple[str, int]]]:
    """Tabela da seção 2.

    `proibidos` recebe as linhas de coordenador, só para a conferência final.
    """
    municipios: list[Linha] = []
    estados: dict[str, tuple[str, int]] = {}
    uf_atual = estado_atual = None
    fim = False
    for pagina in pdf.pages:
        if fim:
            break
        linhas = linhas_da_pagina(sem_marca_dagua(pagina))
        cabecalho = next(
            (
                i
                for i, linha in enumerate(linhas)
                if texto(linha).startswith("Município e coordenador(es)")
            ),
            None,
        )
        if cabecalho is None:
            continue
        palavras = linhas[cabecalho]
        inicio_das = {
            "Município": palavras[0]["x0"],
            "Rota": next(w["x0"] for w in palavras if w["text"] == "Rota"),
            "Ida": [w["x0"] for w in palavras if w["text"] == "Ida"],
            "Alternativa": next(
                w["x0"] for w in palavras if w["text"] == "Alternativa"
            ),
        }
        modal = next(
            w["x0"]
            for vizinha in linhas[cabecalho - 1 : cabecalho + 2]
            for w in vizinha
            if w["text"] == "Modal"
        )
        bordas = [
            inicio_das["Município"] - RECUO_DA_COLUNA,
            modal - RECUO_DA_COLUNA,
            inicio_das["Rota"] - RECUO_DA_COLUNA,
            inicio_das["Ida"][0] - RECUO_DA_COLUNA,
            inicio_das["Ida"][1] - RECUO_DA_COLUNA,
            inicio_das["Alternativa"] - RECUO_DA_COLUNA,
        ]
        atual: Linha | None = None
        for linha in linhas[cabecalho + 1 :]:
            corrido = texto(linha)
            if corrido == "recomendado":
                continue
            if RODAPE.match(corrido):
                break
            if corrido.startswith("Os municípios incluídos") or corrido.startswith(
                "3. Tempo de deslocamento"
            ):
                fim = True
                break
            titulo = TITULO_UF.match(corrido)
            if titulo:
                estado_atual, uf_atual = titulo[1], titulo[2]
                estados[uf_atual] = (estado_atual, int(titulo[3]))
                atual = None
                continue
            col = por_coluna(linha, bordas)
            if HORA.match(col[3]):
                nome = col[0]
                suspensas = nome.endswith(TAG_SUSPENSA)
                if suspensas:
                    nome = nome[: -len(TAG_SUSPENSA)].strip()
                atual = Linha(
                    nome=nome,
                    uf=uf_atual,
                    estado=estado_atual,
                    modal=[col[1]],
                    rota=[col[2]],
                    ida=col[3],
                    ida_volta=col[4],
                    alternativa=[col[5]],
                    suspensas=suspensas,
                )
                municipios.append(atual)
                continue
            if atual is None:
                raise ValueError(
                    f"linha fora de um município na página {pagina.page_number}"
                )
            if col[0]:
                proibidos.update(p.strip() for p in col[0].split(",") if p.strip())
            atual.modal.append(col[1])
            atual.rota.append(col[2])
            atual.faixa.append(col[4])
            atual.alternativa.append(col[5])
    return municipios, estados


def extrair_regras(pdf) -> list[dict[str, str]]:
    """Tabela "1. Como o tempo foi calculado" (páginas 2 e 3)."""
    regras: list[dict[str, list[str]]] = []
    for pagina in pdf.pages[1:3]:
        linhas = linhas_da_pagina(sem_marca_dagua(pagina))
        cabecalho = next(
            i
            for i, linha in enumerate(linhas)
            if texto(linha) == "Componente Tempo adotado Critério"
        )
        bordas = [
            w["x0"] - RECUO_DA_COLUNA
            for w in linhas[cabecalho]
            if w["text"] in ("Componente", "Tempo", "Critério")
        ]
        for linha in linhas[cabecalho + 1 :]:
            corrido = texto(linha)
            if RODAPE.match(corrido) or corrido.startswith("2. Tempo de deslocamento"):
                break
            componente, tempo, criterio = por_coluna(linha, bordas)
            if tempo:
                regras.append(
                    {
                        "componente": [componente],
                        "tempo": [tempo],
                        "criterio": [criterio],
                    }
                )
            else:
                regras[-1]["componente"].append(componente)
                regras[-1]["criterio"].append(criterio)
    return [
        {chave: juntar(valor) for chave, valor in regra.items()} for regra in regras
    ]


def texto_corrido(pdf) -> list[str]:
    """Linhas de texto de todas as páginas, sem marca d'água, cabeçalho nem rodapé."""
    saida: list[str] = []
    for pagina in pdf.pages:
        for linha in (sem_marca_dagua(pagina).extract_text() or "").splitlines():
            if linha in CABECALHO_DA_PAGINA or RODAPE.match(linha):
                continue
            saida.append(linha)
    return saida


def extrair_observacoes(linhas: list[str]) -> list[str]:
    """Os itens da seção "4. Observações e limites"."""
    inicio = linhas.index("4. Observações e limites") + 1
    itens: list[str] = []
    for linha in linhas[inicio:]:
        if linha.startswith("• "):
            itens.append(linha[2:])
        elif itens:
            itens[-1] += " " + linha
    return itens


def extrair_faixas(linhas: list[str]) -> list[dict]:
    corrido = " ".join(linhas)
    achado = re.search(r"A faixa considera a ida e volta: (.+?acima de \d+h)", corrido)
    if not achado:
        raise ValueError("não achei a definição das faixas")
    faixas = []
    for rotulo, limite, numero in re.findall(
        r"(Próximo|Médio|Muito longo|Longo) (até|acima de) (\d+)h", achado[1]
    ):
        faixas.append(
            {
                "faixa": FAIXAS[rotulo],
                "rotulo": rotulo,
                "descricao": f"{limite} {numero}h de ida e volta",
                "ate_horas": int(numero) if limite == "até" else None,
            }
        )
    return faixas


def grupo_terrestre_da_gestao(
    regras: list[dict[str, str]], estados: dict[str, tuple[str, int]]
) -> tuple[set[str], set[str]]:
    """UFs e municípios que a regra "Escolha do modal" nomeia como só terrestres."""
    criterio = next(
        r["criterio"] for r in regras if r["componente"] == "Escolha do modal"
    )
    achado = re.search(r"exclusivamente terrestre \(([^)]+)\)", criterio)
    if not achado:
        raise ValueError("não achei o grupo terrestre da gestão")
    nomes = [n.strip() for n in re.split(r",| e ", achado[1]) if n.strip()]
    uf_do_estado = {estado: uf for uf, (estado, _) in estados.items()}
    ufs = {uf_do_estado[n] for n in nomes if n in uf_do_estado}
    return ufs, {n for n in nomes if n not in uf_do_estado}


def ts(valor) -> str:
    """Literal TypeScript (aspas simples)."""
    if valor is None:
        return "null"
    if isinstance(valor, bool):
        return "true" if valor else "false"
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    if isinstance(valor, (int, float)):
        return repr(valor)
    return "'" + str(valor).replace("\\", "\\\\").replace("'", "\\'") + "'"


def objeto(campos: dict, recuo: str) -> str:
    corpo = "".join(
        f"{recuo}  {chave}: {ts(valor)},\n" for chave, valor in campos.items()
    )
    return f"{recuo}{{\n{corpo}{recuo}}},\n"


def montar_trecho(
    pdf_path: Path, municipios: list[dict], regras, faixas, observacoes
) -> str:
    partes = [
        INICIO,
        "",
        "export const FONTE_DESLOCAMENTO = {",
        f"  arquivo: {ts(pdf_path.name)},",
        "  autoria: 'Coordenação Pedagógica · Superintendência de Coordenação',",
        "  referencia: 'Novembro de 2026',",
        "  ponto_de_partida: 'Fortaleza (CE)',",
        "} as const;",
        "",
        "/** A faixa considera a ida e volta (página 3 do PDF). */",
        "export const FAIXAS_DESLOCAMENTO: readonly InfoFaixaDeslocamento[] = [",
        "".join(objeto(f, "  ") for f in faixas).rstrip("\n"),
        "];",
        "",
        '/** "1. Como o tempo foi calculado" (páginas 2 e 3 do PDF). */',
        "export const REGRAS_DO_CALCULO: readonly RegraDoCalculo[] = [",
        "".join(objeto(r, "  ") for r in regras).rstrip("\n"),
        "];",
        "",
        '/** "4. Observações e limites" (páginas 12 e 13 do PDF). */',
        "export const OBSERVACOES_DESLOCAMENTO: readonly string[] = [",
        *[f"  {ts(o)}," for o in observacoes],
        "];",
        "",
        "/** Seção 2 do PDF: por estado, do menor tempo ao maior. */",
        "export const DESLOCAMENTO_MUNICIPIOS: readonly MunicipioDeslocamento[] = [",
        "".join(objeto(m, "  ") for m in municipios).rstrip("\n"),
        "];",
        "",
        FIM,
    ]
    return "\n".join(partes)


def principal() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "pdf", type=Path, help="caminho do PDF de tempos de deslocamento"
    )
    parser.add_argument(
        "--saida", type=Path, default=SAIDA_PADRAO, help="arquivo .ts com os marcadores"
    )
    args = parser.parse_args()

    proibidos: set[str] = set()
    with pdfplumber.open(args.pdf) as pdf:
        linhas, estados = extrair_municipios(pdf, proibidos)
        regras = extrair_regras(pdf)
        corrido = texto_corrido(pdf)
    if "Fortaleza (CE)" not in " ".join(
        corrido[:20]
    ) or "Novembro de 2026" not in " ".join(corrido[:20]):
        raise ValueError("a página 1 não traz o ponto de partida e a data esperados")
    observacoes = extrair_observacoes(corrido)
    faixas = extrair_faixas(corrido)
    ufs_gestao, nomes_gestao = grupo_terrestre_da_gestao(regras, estados)

    for uf, (estado, esperado) in estados.items():
        achados = sum(1 for item in linhas if item.uf == uf)
        if achados != esperado:
            raise ValueError(
                f"{estado}: o título diz {esperado} municípios, a tabela tem {achados}"
            )

    municipios = []
    for item in linhas:
        modal = juntar(item.modal)
        rota = [p for p in item.rota if p.strip()]
        detalhe = rota.pop() if rota and rota[-1].startswith("Voo:") else None
        faixa = juntar(item.faixa)
        meio = "carro" if modal == "Terrestre" else "aviao"
        municipios.append(
            {
                "nome": item.nome,
                "uf": item.uf,
                "meio": meio,
                "modal": modal,
                "rota": juntar(rota),
                "detalhe_rota": detalhe,
                "ida_horas": horas(item.ida),
                "ida_texto": item.ida,
                "ida_volta_horas": horas(item.ida_volta),
                "ida_volta_texto": item.ida_volta,
                "faixa": FAIXAS[faixa],
                "alternativa": juntar(item.alternativa) or None,
                "acoes_suspensas": item.suspensas,
                "travessia_maritima": "travessia marítima" in modal,
                "terrestre_por_decisao_da_gestao": meio == "carro"
                and (item.uf in ufs_gestao or item.nome in nomes_gestao),
            }
        )

    trecho = montar_trecho(args.pdf, municipios, regras, faixas, observacoes)
    vazados = [
        n
        for n in proibidos
        if n != "coordenador não informado" and n.lower() in trecho.lower()
    ]
    if vazados or "coordenador não informado" in trecho:
        print(
            f"PARADO: {len(vazados)} nome(s) de coordenador iriam para o .ts."
            " Nada foi gravado.",
            file=sys.stderr,
        )
        return 1

    atual = args.saida.read_text(encoding="utf-8")
    if INICIO not in atual or FIM not in atual:
        print(
            f"PARADO: {args.saida} não tem os marcadores do trecho gerado.",
            file=sys.stderr,
        )
        return 1
    antes, resto = atual.split(INICIO, 1)
    _, depois = resto.split(FIM, 1)
    args.saida.write_text(antes + trecho + depois, encoding="utf-8", newline="\n")
    print(
        f"{len(municipios)} municípios, {len(regras)} regras, {len(faixas)} faixas,"
        f" {len(observacoes)} observações → {args.saida}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(principal())
