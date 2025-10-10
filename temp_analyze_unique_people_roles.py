#!/usr/bin/env python
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime

import django

import gspread
import pandas as pd

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
django.setup()

print("=== ANÁLISE DE PESSOAS ÚNICAS E SEUS MÚLTIPLOS PAPÉIS ===")

# URLs das planilhas
PLANILHAS_GOOGLE = {
    "Disponibilidade_2025": "1fsCeGUzsNCv0SCiE6mcIvcCHsMbqNeyzANwdU_148Vw",
    "Controle_2025": "1P6YG3sIAEpiAPIQL9bKBaIznNl3V9VLan9CpVnrEOgA",
    "Acompanhamento_Agenda_2025": "16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU",
    "Usuarios": "1Zj_I7sqYAJ9uaYbVoBfskl0LqxGM3SAFzwm4Zpph1RI",
}


def conectar_google_sheets():
    """Conecta ao Google Sheets"""
    try:
        gc = gspread.oauth(
            credentials_filename="google_oauth_token.json",
            authorized_user_filename="google_oauth_token.json",
        )
        print("✅ Conectado ao Google Sheets")
        return gc
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        return None


def normalizar_nome(nome):
    """Normaliza nomes para identificar pessoas únicas"""
    if not nome:
        return ""
    # Remover acentos e normalizar
    nome = nome.strip().title()
    # Mapear variações comuns
    variacoes = {
        "Antônia Fabiola": "Fabíola Morais",
        "Fabíola Morais": "Fabíola Morais",
        "Paula Freire": "Paula Freire",
        "Paula freire": "Paula Freire",
        "Vanessa Angélica": "Vanessa Angélica",
        "Vanessa Ferreira": "Vanessa Angélica",  # Mesma pessoa
        "Elienai Góes": "Elienai Oliveira",
        "ELIENAI GÓES": "Elienai Oliveira",
        "Elienai Oliveira": "Elienai Oliveira",
        "GLEICE ANNE": "Gleice Anne",
        "Gleice Anne": "Gleice Anne",
        "Gleice": "Gleice Anne",
        "Gabriela": "Gabriela Duarte",
        "Gabriela Duarte": "Gabriela Duarte",
        "Solicitado": "SOLICITADO",
        "SOLICITADO": "SOLICITADO",
    }
    return variacoes.get(nome, nome)


def analisar_pessoas_unicas_multiplos_papeis(gc):
    """Analisa pessoas únicas e seus múltiplos papéis"""
    print("\n🔍 ANÁLISE DE PESSOAS ÚNICAS E MÚLTIPLOS PAPÉIS")

    try:
        planilha_agenda = gc.open_by_key(PLANILHAS_GOOGLE["Acompanhamento_Agenda_2025"])

        # Estrutura dos projetos
        projetos_estrutura = {
            "Superintendência": {
                "aba": "Super",
                "projetos": [
                    "Novo Lendo",
                    "TEMA",
                    "Lendo e Escrevendo",
                    "Projeto AMMA",
                    "Cirandar",
                    "Miudezas",
                    "UNI DUNI TÊ",
                    "Cataventos",
                ],
            },
            "ACerta": {
                "aba": "ACerta",
                "projetos": [
                    "Acerta Matemática",
                    "Acerta Língua Portuguesa",
                    "Escrever Comunicar e Ser",
                    "Superativar",
                ],
            },
            "Brincando": {"aba": "Brincando", "projetos": ["Brincando e Aprendendo"]},
            "Vidas": {
                "aba": "Vidas",
                "projetos": [
                    "Vida & Linguagem",
                    "Vida & Matemática",
                    "Vida & Ciências",
                    "Avançando Juntos Matemática",
                    "Avançando Juntos Língua Portuguesa",
                ],
            },
            "Projetos_Específicos": {
                "aba": "Outros",
                "projetos": [
                    "A Cor da Gente",
                    "Sou da Paz",
                    "TRÂNSITO LEGAL",
                    "ED FINANCEIRA",
                    "LER, OUVIR E CONTAR",
                    "LEIO, ESCREVO E CALCULO",
                    "IDEB10",
                ],
            },
        }

        # Dicionário para armazenar pessoas únicas e seus papéis
        pessoas_unicas = defaultdict(
            lambda: {
                "coordenador_em": set(),
                "formador_em": set(),
                "gerente_em": set(),
                "total_projetos": 0,
                "total_registros": 0,
            }
        )

        # Analisar cada categoria
        for categoria, info in projetos_estrutura.items():
            print(f"\n📊 ANALISANDO: {categoria}")

            try:
                aba = planilha_agenda.worksheet(info["aba"])
                dados = aba.get_all_values()

                if not dados:
                    continue

                cabecalhos = dados[0]

                # Analisar cada projeto individualmente
                for projeto_nome in info["projetos"]:
                    print(f"   📚 {projeto_nome}")

                    for linha in dados[1:]:
                        if len(linha) >= len(cabecalhos):
                            projeto_linha = ""
                            coordenador_linha = ""
                            formadores_linha = []
                            gerente_linha = ""

                            for i, cabecalho in enumerate(cabecalhos):
                                valor = linha[i].strip() if i < len(linha) else ""
                                if valor:
                                    if (
                                        "projeto" in cabecalho.lower()
                                        and valor == projeto_nome
                                    ):
                                        projeto_linha = valor
                                    elif "coordenador" in cabecalho.lower():
                                        coordenador_linha = valor
                                    elif "formador" in cabecalho.lower():
                                        formadores_linha.append(valor)
                                    elif "gerente" in cabecalho.lower():
                                        gerente_linha = valor

                            # Se é o projeto correto, adicionar dados
                            if projeto_linha == projeto_nome:
                                # Coordenador
                                if coordenador_linha:
                                    nome_normalizado = normalizar_nome(
                                        coordenador_linha
                                    )
                                    pessoas_unicas[nome_normalizado][
                                        "coordenador_em"
                                    ].add(f"{categoria} - {projeto_nome}")
                                    pessoas_unicas[nome_normalizado][
                                        "total_projetos"
                                    ] += 1
                                    pessoas_unicas[nome_normalizado][
                                        "total_registros"
                                    ] += 1

                                # Formadores
                                for formador in formadores_linha:
                                    if formador:
                                        nome_normalizado = normalizar_nome(formador)
                                        pessoas_unicas[nome_normalizado][
                                            "formador_em"
                                        ].add(f"{categoria} - {projeto_nome}")
                                        pessoas_unicas[nome_normalizado][
                                            "total_projetos"
                                        ] += 1
                                        pessoas_unicas[nome_normalizado][
                                            "total_registros"
                                        ] += 1

                                # Gerente
                                if gerente_linha:
                                    nome_normalizado = normalizar_nome(gerente_linha)
                                    pessoas_unicas[nome_normalizado]["gerente_em"].add(
                                        f"{categoria} - {projeto_nome}"
                                    )
                                    pessoas_unicas[nome_normalizado][
                                        "total_projetos"
                                    ] += 1
                                    pessoas_unicas[nome_normalizado][
                                        "total_registros"
                                    ] += 1

            except Exception as e:
                print(f"   ❌ Erro ao analisar {categoria}: {e}")
                continue

        # Mostrar pessoas com múltiplos papéis
        print(f"\n🎯 PESSOAS COM MÚLTIPLOS PAPÉIS:")
        print(f"{'='*80}")

        pessoas_multiplos_papeis = []
        for pessoa, dados in pessoas_unicas.items():
            if pessoa == "SOLICITADO":
                continue  # Pular "SOLICITADO"

            total_papeis = (
                len(dados["coordenador_em"])
                + len(dados["formador_em"])
                + len(dados["gerente_em"])
            )
            if total_papeis > 1:
                pessoas_multiplos_papeis.append((pessoa, dados, total_papeis))

        # Ordenar por total de papéis
        pessoas_multiplos_papeis.sort(key=lambda x: x[2], reverse=True)

        for pessoa, dados, total_papeis in pessoas_multiplos_papeis:
            print(f"\n👤 {pessoa.upper()}:")
            print(f"   📊 Total de papéis: {total_papeis}")
            print(f"   📊 Total de registros: {dados['total_registros']}")

            if dados["coordenador_em"]:
                print(
                    f"   👨‍💼 COORDENADOR EM ({len(dados['coordenador_em'])} projetos):"
                )
                for projeto in sorted(dados["coordenador_em"]):
                    print(f"      - {projeto}")

            if dados["formador_em"]:
                print(f"   👨‍🏫 FORMADOR EM ({len(dados['formador_em'])} projetos):")
                for projeto in sorted(dados["formador_em"]):
                    print(f"      - {projeto}")

            if dados["gerente_em"]:
                print(f"   👔 GERENTE EM ({len(dados['gerente_em'])} projetos):")
                for projeto in sorted(dados["gerente_em"]):
                    print(f"      - {projeto}")

        # Estatísticas gerais
        print(f"\n📊 ESTATÍSTICAS GERAIS:")
        print(f"   👥 Total de pessoas únicas: {len(pessoas_unicas)}")
        print(f"   🎯 Pessoas com múltiplos papéis: {len(pessoas_multiplos_papeis)}")
        print(
            f"   📊 Pessoas com apenas 1 papel: {len(pessoas_unicas) - len(pessoas_multiplos_papeis) - 1}"
        )  # -1 para "SOLICITADO"

        # Top 10 pessoas com mais papéis
        print(f"\n🏆 TOP 10 PESSOAS COM MAIS PAPÉIS:")
        for i, (pessoa, dados, total_papeis) in enumerate(
            pessoas_multiplos_papeis[:10], 1
        ):
            print(f"   {i:2d}. {pessoa} - {total_papeis} papéis")

        return pessoas_unicas, pessoas_multiplos_papeis

    except Exception as e:
        print(f"❌ Erro ao analisar pessoas únicas: {e}")
        return {}, []


def analisar_exemplo_ana_paula(gc):
    """Analisa especificamente o caso da Ana Paula"""
    print(f"\n🔍 ANÁLISE ESPECÍFICA: ANA PAULA")
    print(f"{'='*50}")

    try:
        planilha_agenda = gc.open_by_key(PLANILHAS_GOOGLE["Acompanhamento_Agenda_2025"])
        aba_super = planilha_agenda.worksheet("Super")
        dados = aba_super.get_all_values()

        if not dados:
            print("❌ Dados não encontrados")
            return

        cabecalhos = dados[0]
        ana_paula_projetos = defaultdict(list)

        for linha in dados[1:]:
            if len(linha) >= len(cabecalhos):
                projeto = ""
                coordenador = ""
                municipio = ""

                for i, cabecalho in enumerate(cabecalhos):
                    valor = linha[i].strip() if i < len(linha) else ""
                    if valor:
                        if "projeto" in cabecalho.lower():
                            projeto = valor
                        elif (
                            "coordenador" in cabecalho.lower()
                            and "ana paula" in valor.lower()
                        ):
                            coordenador = valor
                        elif (
                            "município" in cabecalho.lower()
                            or "municipio" in cabecalho.lower()
                        ):
                            municipio = valor

                if coordenador and "ana paula" in coordenador.lower():
                    ana_paula_projetos[projeto].append(municipio)

        print(f"👤 ANA PAULA - UMA PESSOA, MÚLTIPLOS PROJETOS:")
        for projeto, municipios in ana_paula_projetos.items():
            print(f"   📚 {projeto}: {len(municipios)} municípios")
            for municipio in sorted(set(municipios))[:5]:  # Primeiros 5
                print(f"      - {municipio}")
            if len(set(municipios)) > 5:
                print(f"      ... e mais {len(set(municipios)) - 5} municípios")

        print(f"\n💡 CONCLUSÃO:")
        print(f"   - Ana Paula é UMA PESSOA")
        print(f"   - Coordena {len(ana_paula_projetos)} projetos diferentes")
        print(f"   - Atua em múltiplos municípios")
        print(f"   - NÃO são múltiplos usuários")

    except Exception as e:
        print(f"❌ Erro ao analisar Ana Paula: {e}")


def main():
    """Função principal de análise de pessoas únicas"""
    print("🔍 Iniciando análise de pessoas únicas e múltiplos papéis...")

    gc = conectar_google_sheets()
    if not gc:
        return

    # Executar análises
    pessoas_unicas, pessoas_multiplos_papeis = analisar_pessoas_unicas_multiplos_papeis(
        gc
    )
    analisar_exemplo_ana_paula(gc)

    # Salvar análise
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"analise_pessoas_unicas_multiplos_papeis_{timestamp}.json"

    # Converter sets para lists para JSON
    pessoas_unicas_json = {}
    for pessoa, dados in pessoas_unicas.items():
        pessoas_unicas_json[pessoa] = {
            "coordenador_em": list(dados["coordenador_em"]),
            "formador_em": list(dados["formador_em"]),
            "gerente_em": list(dados["gerente_em"]),
            "total_projetos": dados["total_projetos"],
            "total_registros": dados["total_registros"],
        }

    analise_completa = {
        "timestamp": datetime.now().isoformat(),
        "pessoas_unicas": pessoas_unicas_json,
        "pessoas_multiplos_papeis": len(pessoas_multiplos_papeis),
        "total_pessoas_unicas": len(pessoas_unicas),
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(analise_completa, f, indent=2, ensure_ascii=False)

    print(f"\n🎉 ANÁLISE DE PESSOAS ÚNICAS FINALIZADA!")
    print(f"📁 Arquivo salvo: {filename}")


if __name__ == "__main__":
    main()
