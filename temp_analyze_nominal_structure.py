#!/usr/bin/env python
import os
import sys
import django
import gspread
import pandas as pd
from collections import defaultdict, Counter
import json
from datetime import datetime

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
django.setup()

print("=== ANÁLISE NOMINAL DETALHADA DE TODOS OS PROJETOS ===")

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
    """Normaliza nomes para evitar duplicatas por diferenças de capitalização"""
    if not nome:
        return ""
    return nome.strip().title()


def analisar_estrutura_nominal_completa(gc):
    """Analisa a estrutura nominal completa de todos os projetos"""
    print("\n🔍 ANÁLISE NOMINAL COMPLETA DE TODOS OS PROJETOS")

    try:
        planilha_agenda = gc.open_by_key(PLANILHAS_GOOGLE["Acompanhamento_Agenda_2025"])
        planilha_usuarios = gc.open_by_key(PLANILHAS_GOOGLE["Usuarios"])

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

        # Analisar cada categoria
        for categoria, info in projetos_estrutura.items():
            print(f"\n{'='*60}")
            print(f"🏢 {categoria.upper()}")
            print(f"{'='*60}")

            try:
                aba = planilha_agenda.worksheet(info["aba"])
                dados = aba.get_all_values()

                if not dados:
                    print(f"❌ Dados não encontrados na aba {info['aba']}")
                    continue

                cabecalhos = dados[0]
                print(f"📋 Total de registros: {len(dados) - 1}")

                # Analisar cada projeto individualmente
                for projeto_nome in info["projetos"]:
                    print(f"\n📚 {projeto_nome.upper()}:")

                    # Coletar dados do projeto
                    coordenadores_projeto = set()
                    formadores_projeto = set()
                    gerentes_projeto = set()
                    registros_projeto = 0

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
                                        registros_projeto += 1
                                    elif "coordenador" in cabecalho.lower():
                                        coordenador_linha = valor
                                    elif "formador" in cabecalho.lower():
                                        formadores_linha.append(valor)
                                    elif "gerente" in cabecalho.lower():
                                        gerente_linha = valor

                            # Se é o projeto correto, adicionar dados
                            if projeto_linha == projeto_nome:
                                if coordenador_linha:
                                    coordenadores_projeto.add(
                                        normalizar_nome(coordenador_linha)
                                    )
                                for formador in formadores_linha:
                                    if formador:
                                        formadores_projeto.add(
                                            normalizar_nome(formador)
                                        )
                                if gerente_linha:
                                    gerentes_projeto.add(normalizar_nome(gerente_linha))

                    # Mostrar resultados
                    print(f"   📊 Registros: {registros_projeto}")
                    print(f"   👨‍💼 Coordenadores: {len(coordenadores_projeto)}")
                    for coord in sorted(coordenadores_projeto):
                        print(f"      - {coord}")

                    print(f"   👨‍🏫 Formadores: {len(formadores_projeto)}")
                    for form in sorted(formadores_projeto):
                        print(f"      - {form}")

                    if gerentes_projeto:
                        print(f"   👔 Gerentes: {len(gerentes_projeto)}")
                        for ger in sorted(gerentes_projeto):
                            print(f"      - {ger}")

                # Analisar usuários da categoria na planilha de usuários
                print(f"\n👥 USUÁRIOS {categoria.upper()} NA PLANILHA USUÁRIOS:")
                try:
                    aba_usuarios = planilha_usuarios.worksheet("Ativos")
                    dados_usuarios = aba_usuarios.get_all_values()

                    if dados_usuarios:
                        cabecalhos_usuarios = dados_usuarios[0]
                        usuarios_categoria = []

                        for linha in dados_usuarios[1:]:
                            if len(linha) >= len(cabecalhos_usuarios):
                                usuario = {}
                                for i, cabecalho in enumerate(cabecalhos_usuarios):
                                    usuario[cabecalho] = (
                                        linha[i] if i < len(linha) else ""
                                    )

                                gerencia = usuario.get("Gerência", "").strip()

                                # Verificar se pertence à categoria
                                pertence_categoria = False
                                if (
                                    categoria == "Superintendência"
                                    and gerencia == "Superintendência"
                                ):
                                    pertence_categoria = True
                                elif (
                                    categoria == "ACerta"
                                    and "acerta" in gerencia.lower()
                                ):
                                    pertence_categoria = True
                                elif (
                                    categoria == "Brincando"
                                    and "brincando" in gerencia.lower()
                                ):
                                    pertence_categoria = True
                                elif (
                                    categoria == "Vidas" and "vidas" in gerencia.lower()
                                ):
                                    pertence_categoria = True
                                elif (
                                    categoria == "Projetos_Específicos"
                                    and gerencia
                                    not in ["Superintendência", "ACerta", "Brincando"]
                                    and "vidas" not in gerencia.lower()
                                ):
                                    pertence_categoria = True

                                if pertence_categoria:
                                    usuarios_categoria.append(usuario)

                        print(f"   📊 Total: {len(usuarios_categoria)} pessoas")

                        # Agrupar por cargo
                        por_cargo = defaultdict(list)
                        for usuario in usuarios_categoria:
                            cargo = usuario.get("Cargo", "").strip()
                            if cargo:
                                por_cargo[cargo].append(usuario)

                        for cargo, usuarios in por_cargo.items():
                            print(f"\n   👔 {cargo.upper()}: {len(usuarios)} pessoas")
                            for usuario in usuarios:
                                nome = usuario.get("Nome Completo", "").strip()
                                gerencia = usuario.get("Gerência", "").strip()
                                print(f"      - {nome} ({gerencia})")

                except Exception as e:
                    print(f"   ❌ Erro ao analisar usuários: {e}")

            except Exception as e:
                print(f"❌ Erro ao analisar categoria {categoria}: {e}")
                continue

        return projetos_estrutura

    except Exception as e:
        print(f"❌ Erro ao analisar estrutura: {e}")
        return {}


def analisar_brincando_corrigido(gc):
    """Analisa o projeto Brincando com correção do CRECHE"""
    print("\n🔍 ANÁLISE CORRIGIDA: PROJETO BRINCANDO")

    try:
        planilha_agenda = gc.open_by_key(PLANILHAS_GOOGLE["Acompanhamento_Agenda_2025"])
        aba_brincando = planilha_agenda.worksheet("Brincando")
        dados = aba_brincando.get_all_values()

        if not dados:
            print("❌ Dados não encontrados na aba Brincando")
            return {}

        cabecalhos = dados[0]
        print(f"📊 Total de registros: {len(dados) - 1}")

        # Analisar gerentes (CORRIGIDO)
        gerentes_brincando = set()
        formadores_brincando = set()

        for linha in dados[1:]:
            if len(linha) >= len(cabecalhos):
                for i, cabecalho in enumerate(cabecalhos):
                    valor = linha[i].strip() if i < len(linha) else ""
                    if valor:
                        if "gerente" in cabecalho.lower():
                            # CORREÇÃO: Filtrar CRECHE
                            if valor.upper() != "CRECHE":
                                gerentes_brincando.add(normalizar_nome(valor))
                        elif "formador" in cabecalho.lower():
                            formadores_brincando.add(normalizar_nome(valor))

        print(f"\n👔 GERENTES BRINCANDO (CORRIGIDO): {len(gerentes_brincando)}")
        for ger in sorted(gerentes_brincando):
            print(f"   - {ger}")

        print(f"\n👨‍🏫 FORMADORES BRINCANDO: {len(formadores_brincando)}")
        for form in sorted(formadores_brincando):
            print(f"   - {form}")

        # Verificar usuários Brincando na planilha de usuários
        planilha_usuarios = gc.open_by_key(PLANILHAS_GOOGLE["Usuarios"])
        aba_ativos = planilha_usuarios.worksheet("Ativos")
        dados_usuarios = aba_ativos.get_all_values()

        if dados_usuarios:
            cabecalhos_usuarios = dados_usuarios[0]
            usuarios_brincando = []

            for linha in dados_usuarios[1:]:
                if len(linha) >= len(cabecalhos_usuarios):
                    usuario = {}
                    for i, cabecalho in enumerate(cabecalhos_usuarios):
                        usuario[cabecalho] = linha[i] if i < len(linha) else ""

                    gerencia = usuario.get("Gerência", "").strip()
                    if "brincando" in gerencia.lower():
                        usuarios_brincando.append(usuario)

            print(
                f"\n👥 USUÁRIOS BRINCANDO NA PLANILHA USUÁRIOS: {len(usuarios_brincando)}"
            )
            for usuario in usuarios_brincando:
                nome = usuario.get("Nome Completo", "").strip()
                cargo = usuario.get("Cargo", "").strip()
                print(f"   - {nome} ({cargo})")

        return {
            "gerentes": list(gerentes_brincando),
            "formadores": list(formadores_brincando),
            "usuarios_planilha": usuarios_brincando,
        }

    except Exception as e:
        print(f"❌ Erro ao analisar Brincando: {e}")
        return {}


def main():
    """Função principal de análise nominal"""
    print("🔍 Iniciando análise nominal detalhada de todos os projetos...")

    gc = conectar_google_sheets()
    if not gc:
        return

    # Executar análises
    estrutura_completa = analisar_estrutura_nominal_completa(gc)
    brincando_corrigido = analisar_brincando_corrigido(gc)

    # Salvar análise
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"analise_nominal_completa_{timestamp}.json"

    analise_completa = {
        "timestamp": datetime.now().isoformat(),
        "estrutura_completa": estrutura_completa,
        "brincando_corrigido": brincando_corrigido,
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(analise_completa, f, indent=2, ensure_ascii=False)

    print(f"\n🎉 ANÁLISE NOMINAL COMPLETA FINALIZADA!")
    print(f"📁 Arquivo salvo: {filename}")


if __name__ == "__main__":
    main()
