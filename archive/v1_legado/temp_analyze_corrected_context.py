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

print("=== ANÁLISE CORRIGIDA DO CONTEXTO ORGANIZACIONAL ===")

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


def analisar_vinculacao_superintendencia_corrigida(gc):
    """Analisa CORRETAMENTE a vinculação à superintendência"""
    print("\n🔍 ANÁLISE CORRIGIDA: VINCULAÇÃO À SUPERINTENDÊNCIA")

    try:
        # Analisar planilha de usuários
        planilha_usuarios = gc.open_by_key(PLANILHAS_GOOGLE["Usuarios"])
        aba_ativos = planilha_usuarios.worksheet("Ativos")
        dados = aba_ativos.get_all_values()

        if not dados:
            return {}

        cabecalhos = dados[0]
        usuarios_superintendencia = []
        usuarios_outros_projetos = []

        for linha in dados[1:]:
            if len(linha) >= len(cabecalhos):
                usuario = {}
                for i, cabecalho in enumerate(cabecalhos):
                    usuario[cabecalho] = linha[i] if i < len(linha) else ""

                gerencia = usuario.get("Gerência", "").strip()

                # CORREÇÃO: Apenas usuários da "Superintendência" estão vinculados
                if gerencia == "Superintendência":
                    usuarios_superintendencia.append(usuario)
                else:
                    usuarios_outros_projetos.append(usuario)

        print(
            f"🏢 USUÁRIOS VINCULADOS À SUPERINTENDÊNCIA: {len(usuarios_superintendencia)}"
        )
        print("   (Apenas usuários com Gerência = 'Superintendência')")
        for usuario in usuarios_superintendencia:
            print(
                f"   - {usuario.get('Nome Completo', '')} ({usuario.get('Cargo', '')})"
            )

        print(
            f"\n🏢 USUÁRIOS DE OUTROS PROJETOS (ESTRUTURA PRÓPRIA): {len(usuarios_outros_projetos)}"
        )
        gerencias_outros = Counter()
        for usuario in usuarios_outros_projetos:
            gerencia = usuario.get("Gerência", "").strip()
            if gerencia:
                gerencias_outros[gerencia] += 1

        for gerencia, count in gerencias_outros.most_common():
            print(f"   - {gerencia}: {count} pessoas")

        return {
            "superintendencia": usuarios_superintendencia,
            "outros_projetos": usuarios_outros_projetos,
            "gerencias_outros": dict(gerencias_outros),
        }

    except Exception as e:
        print(f"❌ Erro ao analisar superintendência: {e}")
        return {}


def analisar_brincando_detalhadamente(gc):
    """Analisa DETALHADAMENTE o projeto Brincando"""
    print("\n🔍 ANÁLISE DETALHADA: PROJETO BRINCANDO")

    try:
        planilha_agenda = gc.open_by_key(PLANILHAS_GOOGLE["Acompanhamento_Agenda_2025"])
        aba_brincando = planilha_agenda.worksheet("Brincando")
        dados = aba_brincando.get_all_values()

        if not dados:
            print("❌ Dados não encontrados na aba Brincando")
            return {}

        cabecalhos = dados[0]
        print(f"📊 Total de registros: {len(dados) - 1}")
        print(f"📋 Cabeçalhos: {cabecalhos}")

        # Analisar coordenadores
        coordenadores_brincando = set()
        formadores_brincando = set()
        gerentes_brincando = set()

        for linha in dados[1:]:
            if len(linha) >= len(cabecalhos):
                for i, cabecalho in enumerate(cabecalhos):
                    valor = linha[i].strip() if i < len(linha) else ""
                    if valor:
                        if "coordenador" in cabecalho.lower():
                            coordenadores_brincando.add(valor)
                        elif "formador" in cabecalho.lower():
                            formadores_brincando.add(valor)
                        elif "gerente" in cabecalho.lower():
                            gerentes_brincando.add(valor)

        print(f"\n👨‍💼 COORDENADORES BRINCANDO: {len(coordenadores_brincando)}")
        for coord in sorted(coordenadores_brincando):
            print(f"   - {coord}")

        print(f"\n👨‍🏫 FORMADORES BRINCANDO: {len(formadores_brincando)}")
        for form in sorted(formadores_brincando):
            print(f"   - {form}")

        print(f"\n👔 GERENTES BRINCANDO: {len(gerentes_brincando)}")
        for ger in sorted(gerentes_brincando):
            print(f"   - {ger}")

        # Verificar se há dados na planilha de usuários para Brincando
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
                print(
                    f"   - {usuario.get('Nome Completo', '')} ({usuario.get('Cargo', '')}) - {usuario.get('Gerência', '')}"
                )

        return {
            "coordenadores": list(coordenadores_brincando),
            "formadores": list(formadores_brincando),
            "gerentes": list(gerentes_brincando),
            "usuarios_planilha": usuarios_brincando,
        }

    except Exception as e:
        print(f"❌ Erro ao analisar Brincando: {e}")
        return {}


def analisar_vidas_detalhadamente(gc):
    """Analisa DETALHADAMENTE os projetos Vidas"""
    print("\n🔍 ANÁLISE DETALHADA: PROJETOS VIDAS")

    try:
        planilha_agenda = gc.open_by_key(PLANILHAS_GOOGLE["Acompanhamento_Agenda_2025"])
        aba_vidas = planilha_agenda.worksheet("Vidas")
        dados = aba_vidas.get_all_values()

        if not dados:
            print("❌ Dados não encontrados na aba Vidas")
            return {}

        cabecalhos = dados[0]
        print(f"📊 Total de registros: {len(dados) - 1}")
        print(f"📋 Cabeçalhos: {cabecalhos}")

        # Analisar projetos específicos
        projetos_vidas = set()
        coordenadores_vidas = set()
        formadores_vidas = set()

        for linha in dados[1:]:
            if len(linha) >= len(cabecalhos):
                for i, cabecalho in enumerate(cabecalhos):
                    valor = linha[i].strip() if i < len(linha) else ""
                    if valor:
                        if "projeto" in cabecalho.lower():
                            projetos_vidas.add(valor)
                        elif "coordenador" in cabecalho.lower():
                            coordenadores_vidas.add(valor)
                        elif "formador" in cabecalho.lower():
                            formadores_vidas.add(valor)

        print(f"\n📚 PROJETOS VIDAS IDENTIFICADOS: {len(projetos_vidas)}")
        for projeto in sorted(projetos_vidas):
            print(f"   - {projeto}")

        print(f"\n👨‍💼 COORDENADORES VIDAS: {len(coordenadores_vidas)}")
        for coord in sorted(coordenadores_vidas):
            print(f"   - {coord}")

        print(f"\n👨‍🏫 FORMADORES VIDAS: {len(formadores_vidas)}")
        for form in sorted(formadores_vidas):
            print(f"   - {form}")

        # Verificar usuários Vidas na planilha de usuários
        planilha_usuarios = gc.open_by_key(PLANILHAS_GOOGLE["Usuarios"])
        aba_ativos = planilha_usuarios.worksheet("Ativos")
        dados_usuarios = aba_ativos.get_all_values()

        if dados_usuarios:
            cabecalhos_usuarios = dados_usuarios[0]
            usuarios_vidas = []

            for linha in dados_usuarios[1:]:
                if len(linha) >= len(cabecalhos_usuarios):
                    usuario = {}
                    for i, cabecalho in enumerate(cabecalhos_usuarios):
                        usuario[cabecalho] = linha[i] if i < len(linha) else ""

                    gerencia = usuario.get("Gerência", "").strip()
                    if "vidas" in gerencia.lower():
                        usuarios_vidas.append(usuario)

            print(f"\n👥 USUÁRIOS VIDAS NA PLANILHA USUÁRIOS: {len(usuarios_vidas)}")
            for usuario in usuarios_vidas:
                print(
                    f"   - {usuario.get('Nome Completo', '')} ({usuario.get('Cargo', '')}) - {usuario.get('Gerência', '')}"
                )

        return {
            "projetos": list(projetos_vidas),
            "coordenadores": list(coordenadores_vidas),
            "formadores": list(formadores_vidas),
            "usuarios_planilha": usuarios_vidas,
        }

    except Exception as e:
        print(f"❌ Erro ao analisar Vidas: {e}")
        return {}


def analisar_aba_dat(gc):
    """Analisa a aba DAT da planilha de Acompanhamento"""
    print("\n🔍 ANÁLISE: ABA DAT (DESENVOLVIMENTO E APOIO TECNOLÓGICO)")

    try:
        planilha_controle = gc.open_by_key(PLANILHAS_GOOGLE["Controle_2025"])
        aba_dat = planilha_controle.worksheet("ℹ️ DAT")
        dados = aba_dat.get_all_values()

        if not dados:
            print("❌ Dados não encontrados na aba DAT")
            return {}

        cabecalhos = dados[0]
        print(f"📊 Total de registros: {len(dados) - 1}")
        print(f"📋 Cabeçalhos: {cabecalhos}")

        # Analisar estrutura dos dados
        municipios_dat = set()
        projetos_dat = set()
        responsaveis_dat = set()

        for linha in dados[1:]:
            if len(linha) >= len(cabecalhos):
                for i, cabecalho in enumerate(cabecalhos):
                    valor = linha[i].strip() if i < len(linha) else ""
                    if valor:
                        if "município" in cabecalho.lower():
                            municipios_dat.add(valor)
                        elif "projeto" in cabecalho.lower():
                            projetos_dat.add(valor)
                        elif (
                            "responsável" in cabecalho.lower()
                            or "feitor" in cabecalho.lower()
                        ):
                            responsaveis_dat.add(valor)

        print(f"\n🌍 MUNICÍPIOS NO DAT: {len(municipios_dat)}")
        for municipio in sorted(list(municipios_dat)[:10]):  # Primeiros 10
            print(f"   - {municipio}")
        if len(municipios_dat) > 10:
            print(f"   ... e mais {len(municipios_dat) - 10} municípios")

        print(f"\n📚 PROJETOS NO DAT: {len(projetos_dat)}")
        for projeto in sorted(projetos_dat):
            print(f"   - {projeto}")

        print(f"\n👥 RESPONSÁVEIS NO DAT: {len(responsaveis_dat)}")
        for responsavel in sorted(responsaveis_dat):
            print(f"   - {responsavel}")

        # Mostrar algumas linhas de exemplo
        print(f"\n📋 EXEMPLOS DE DADOS DAT:")
        for i, linha in enumerate(dados[1:6]):  # Primeiras 5 linhas
            if len(linha) >= len(cabecalhos):
                print(f"   Linha {i+1}: {linha[:5]}...")  # Primeiras 5 colunas

        return {
            "municipios": list(municipios_dat),
            "projetos": list(projetos_dat),
            "responsaveis": list(responsaveis_dat),
            "total_registros": len(dados) - 1,
        }

    except Exception as e:
        print(f"❌ Erro ao analisar DAT: {e}")
        return {}


def analisar_estrutura_projetos_corrigida(gc):
    """Analisa a estrutura dos projetos com as correções"""
    print("\n🔍 ANÁLISE CORRIGIDA: ESTRUTURA DOS PROJETOS")

    try:
        planilha_agenda = gc.open_by_key(PLANILHAS_GOOGLE["Acompanhamento_Agenda_2025"])

        projetos_estrutura = {}

        # Analisar cada aba de projeto
        abas_projetos = ["Super", "ACerta", "Brincando", "Vidas", "Outros"]

        for aba_nome in abas_projetos:
            try:
                aba = planilha_agenda.worksheet(aba_nome)
                dados = aba.get_all_values()

                if not dados:
                    continue

                cabecalhos = dados[0]
                print(f"\n📊 PROJETO: {aba_nome}")
                print(f"   Registros: {len(dados) - 1}")
                print(f"   Colunas: {len(cabecalhos)}")

                # Analisar coordenadores, formadores e gerentes
                coordenadores_projeto = set()
                formadores_projeto = set()
                gerentes_projeto = set()
                municipios_projeto = set()

                for linha in dados[1:]:
                    if len(linha) >= len(cabecalhos):
                        for i, cabecalho in enumerate(cabecalhos):
                            valor = linha[i].strip() if i < len(linha) else ""
                            if valor:
                                if "coordenador" in cabecalho.lower():
                                    coordenadores_projeto.add(valor)
                                elif "formador" in cabecalho.lower():
                                    formadores_projeto.add(valor)
                                elif "gerente" in cabecalho.lower():
                                    gerentes_projeto.add(valor)
                                elif (
                                    "município" in cabecalho.lower()
                                    or "municipio" in cabecalho.lower()
                                ):
                                    municipios_projeto.add(valor)

                print(f"   👨‍💼 Coordenadores: {len(coordenadores_projeto)}")
                for coord in sorted(coordenadores_projeto):
                    print(f"      - {coord}")

                print(f"   👨‍🏫 Formadores: {len(formadores_projeto)}")
                for form in sorted(list(formadores_projeto)[:10]):  # Primeiros 10
                    print(f"      - {form}")
                if len(formadores_projeto) > 10:
                    print(f"      ... e mais {len(formadores_projeto) - 10} formadores")

                print(f"   👔 Gerentes: {len(gerentes_projeto)}")
                for ger in sorted(gerentes_projeto):
                    print(f"      - {ger}")

                print(f"   🌍 Municípios: {len(municipios_projeto)}")

                projetos_estrutura[aba_nome] = {
                    "coordenadores": list(coordenadores_projeto),
                    "formadores": list(formadores_projeto),
                    "gerentes": list(gerentes_projeto),
                    "municipios": list(municipios_projeto),
                    "total_registros": len(dados) - 1,
                }

            except Exception as e:
                print(f"   ❌ Erro ao analisar {aba_nome}: {e}")
                continue

        return projetos_estrutura

    except Exception as e:
        print(f"❌ Erro ao analisar estrutura: {e}")
        return {}


def main():
    """Função principal de análise corrigida"""
    print("🔍 Iniciando análise corrigida do contexto organizacional...")

    gc = conectar_google_sheets()
    if not gc:
        return

    # Executar todas as análises corrigidas
    superintendencia_corrigida = analisar_vinculacao_superintendencia_corrigida(gc)
    brincando_detalhado = analisar_brincando_detalhadamente(gc)
    vidas_detalhado = analisar_vidas_detalhadamente(gc)
    dat_analise = analisar_aba_dat(gc)
    estrutura_corrigida = analisar_estrutura_projetos_corrigida(gc)

    # Consolidar análise corrigida
    analise_corrigida = {
        "timestamp": datetime.now().isoformat(),
        "superintendencia_corrigida": superintendencia_corrigida,
        "brincando_detalhado": brincando_detalhado,
        "vidas_detalhado": vidas_detalhado,
        "dat_analise": dat_analise,
        "estrutura_corrigida": estrutura_corrigida,
    }

    # Salvar análise corrigida
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"analise_contexto_corrigida_{timestamp}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(analise_corrigida, f, indent=2, ensure_ascii=False)

    print(f"\n🎉 ANÁLISE CORRIGIDA FINALIZADA!")
    print(f"📁 Arquivo salvo: {filename}")

    # Resumo final corrigido
    print(f"\n📊 RESUMO FINAL CORRIGIDO:")
    print(
        f"   🏢 Usuários vinculados à Superintendência: {len(superintendencia_corrigida.get('superintendencia', []))}"
    )
    print(
        f"   🏢 Usuários de outros projetos (estrutura própria): {len(superintendencia_corrigida.get('outros_projetos', []))}"
    )
    print(
        f"   🎮 Coordenadores Brincando: {len(brincando_detalhado.get('coordenadores', []))}"
    )
    print(
        f"   🌱 Projetos Vidas identificados: {len(vidas_detalhado.get('projetos', []))}"
    )
    print(f"   💻 Registros DAT: {dat_analise.get('total_registros', 0)}")


if __name__ == "__main__":
    main()
