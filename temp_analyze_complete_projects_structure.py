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
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')
django.setup()

print("=== ANÁLISE COMPLETA DA ESTRUTURA DE PROJETOS ===")

# URLs das planilhas
PLANILHAS_GOOGLE = {
    "Disponibilidade_2025": "1fsCeGUzsNCv0SCiE6mcIvcCHsMbqNeyzANwdU_148Vw",
    "Controle_2025": "1P6YG3sIAEpiAPIQL9bKBaIznNl3V9VLan9CpVnrEOgA", 
    "Acompanhamento_Agenda_2025": "16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU",
    "Usuarios": "1Zj_I7sqYAJ9uaYbVoBfskl0LqxGM3SAFzwm4Zpph1RI"
}

def conectar_google_sheets():
    """Conecta ao Google Sheets"""
    try:
        gc = gspread.oauth(
            credentials_filename='google_oauth_token.json',
            authorized_user_filename='google_oauth_token.json'
        )
        print("✅ Conectado ao Google Sheets")
        return gc
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        return None

def analisar_projetos_por_aba(gc):
    """Analisa os projetos específicos dentro de cada aba"""
    print("\n🔍 ANÁLISE DETALHADA: PROJETOS POR ABA")
    
    try:
        planilha_agenda = gc.open_by_key(PLANILHAS_GOOGLE["Acompanhamento_Agenda_2025"])
        
        # Estrutura correta dos projetos
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
                    "Cataventos"
                ]
            },
            "ACerta": {
                "aba": "ACerta",
                "projetos": [
                    "Acerta Matemática",
                    "Acerta Língua Portuguesa", 
                    "Escrever Comunicar e Ser",
                    "Superativar",
                    "Acerta - Esquenta SAEB"
                ]
            },
            "Brincando": {
                "aba": "Brincando",
                "projetos": [
                    "Brincando e Aprendendo"
                ]
            },
            "Vidas": {
                "aba": "Vidas",
                "projetos": [
                    "Vida & Linguagem",
                    "Vida & Matemática",
                    "Vida & Ciências",
                    "Avançando Juntos Matemática",
                    "Avançando Juntos Língua Portuguesa",
                    "Vida - ESQUENTA SAEB"
                ]
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
                    "IDEB10 - ESQUENTA SAEB"
                ]
            }
        }
        
        # Analisar cada aba
        for categoria, info in projetos_estrutura.items():
            print(f"\n📊 {categoria.upper()}:")
            print(f"   Aba: {info['aba']}")
            print(f"   Projetos: {len(info['projetos'])}")
            
            try:
                aba = planilha_agenda.worksheet(info['aba'])
                dados = aba.get_all_values()
                
                if not dados:
                    print(f"   ❌ Dados não encontrados na aba {info['aba']}")
                    continue
                
                cabecalhos = dados[0]
                print(f"   📋 Total de registros: {len(dados) - 1}")
                
                # Analisar projetos encontrados na aba
                projetos_encontrados = set()
                coordenadores_por_projeto = defaultdict(set)
                formadores_por_projeto = defaultdict(set)
                
                for linha in dados[1:]:
                    if len(linha) >= len(cabecalhos):
                        projeto_linha = ""
                        coordenador_linha = ""
                        formadores_linha = []
                        
                        for i, cabecalho in enumerate(cabecalhos):
                            valor = linha[i].strip() if i < len(linha) else ''
                            if valor:
                                if 'projeto' in cabecalho.lower():
                                    projeto_linha = valor
                                    projetos_encontrados.add(valor)
                                elif 'coordenador' in cabecalho.lower():
                                    coordenador_linha = valor
                                elif 'formador' in cabecalho.lower():
                                    formadores_linha.append(valor)
                        
                        # Agrupar por projeto
                        if projeto_linha:
                            if coordenador_linha:
                                coordenadores_por_projeto[projeto_linha].add(coordenador_linha)
                            for formador in formadores_linha:
                                if formador:
                                    formadores_por_projeto[projeto_linha].add(formador)
                
                print(f"   📚 Projetos encontrados na aba: {len(projetos_encontrados)}")
                for projeto in sorted(projetos_encontrados):
                    print(f"      - {projeto}")
                
                # Mostrar coordenadores e formadores por projeto
                for projeto in sorted(projetos_encontrados):
                    coord_count = len(coordenadores_por_projeto[projeto])
                    form_count = len(formadores_por_projeto[projeto])
                    print(f"\n   📋 {projeto}:")
                    print(f"      👨‍💼 Coordenadores: {coord_count}")
                    for coord in sorted(coordenadores_por_projeto[projeto]):
                        print(f"         - {coord}")
                    print(f"      👨‍🏫 Formadores: {form_count}")
                    for form in sorted(list(formadores_por_projeto[projeto])[:5]):  # Primeiros 5
                        print(f"         - {form}")
                    if form_count > 5:
                        print(f"         ... e mais {form_count - 5} formadores")
                
            except Exception as e:
                print(f"   ❌ Erro ao analisar aba {info['aba']}: {e}")
                continue
        
        return projetos_estrutura
        
    except Exception as e:
        print(f"❌ Erro ao analisar projetos: {e}")
        return {}

def analisar_eventos_saeb(gc):
    """Analisa eventos SAEB (não são coleções, são eventos vinculados)"""
    print("\n🔍 ANÁLISE: EVENTOS SAEB (NÃO SÃO COLEÇÕES)")
    
    try:
        planilha_agenda = gc.open_by_key(PLANILHAS_GOOGLE["Acompanhamento_Agenda_2025"])
        
        eventos_saeb = set()
        abas_analisadas = ['Super', 'ACerta', 'Brincando', 'Vidas', 'Outros']
        
        for aba_nome in abas_analisadas:
            try:
                aba = planilha_agenda.worksheet(aba_nome)
                dados = aba.get_all_values()
                
                if not dados:
                    continue
                
                cabecalhos = dados[0]
                
                for linha in dados[1:]:
                    if len(linha) >= len(cabecalhos):
                        for i, cabecalho in enumerate(cabecalhos):
                            valor = linha[i].strip() if i < len(linha) else ''
                            if valor and 'SAEB' in valor.upper():
                                eventos_saeb.add(valor)
                
            except Exception as e:
                print(f"   ❌ Erro ao analisar aba {aba_nome}: {e}")
                continue
        
        print(f"📊 EVENTOS SAEB IDENTIFICADOS: {len(eventos_saeb)}")
        for evento in sorted(eventos_saeb):
            print(f"   - {evento}")
        
        print(f"\n💡 CONTEXTO:")
        print(f"   - Eventos SAEB são eventos vinculados às coleções")
        print(f"   - NÃO são coleções propriamente ditas")
        print(f"   - São eventos específicos de preparação para avaliações")
        
        return list(eventos_saeb)
        
    except Exception as e:
        print(f"❌ Erro ao analisar eventos SAEB: {e}")
        return []

def analisar_projetos_pequenos(gc):
    """Analisa projetos pequenos (formador = coordenador)"""
    print("\n🔍 ANÁLISE: PROJETOS PEQUENOS (FORMADOR = COORDENADOR)")
    
    try:
        planilha_agenda = gc.open_by_key(PLANILHAS_GOOGLE["Acompanhamento_Agenda_2025"])
        aba_outros = planilha_agenda.worksheet("Outros")
        dados = aba_outros.get_all_values()
        
        if not dados:
            print("❌ Dados não encontrados na aba Outros")
            return {}
        
        cabecalhos = dados[0]
        projetos_pequenos = defaultdict(lambda: {
            'coordenadores': set(),
            'formadores': set(),
            'total_registros': 0
        })
        
        for linha in dados[1:]:
            if len(linha) >= len(cabecalhos):
                projeto = ""
                coordenador = ""
                formadores = []
                
                for i, cabecalho in enumerate(cabecalhos):
                    valor = linha[i].strip() if i < len(linha) else ''
                    if valor:
                        if 'projeto' in cabecalho.lower():
                            projeto = valor
                        elif 'coordenador' in cabecalho.lower():
                            coordenador = valor
                        elif 'formador' in cabecalho.lower():
                            formadores.append(valor)
                
                if projeto:
                    projetos_pequenos[projeto]['total_registros'] += 1
                    if coordenador:
                        projetos_pequenos[projeto]['coordenadores'].add(coordenador)
                    for formador in formadores:
                        if formador:
                            projetos_pequenos[projeto]['formadores'].add(formador)
        
        print(f"📊 PROJETOS PEQUENOS IDENTIFICADOS: {len(projetos_pequenos)}")
        
        for projeto, dados_projeto in projetos_pequenos.items():
            coord_count = len(dados_projeto['coordenadores'])
            form_count = len(dados_projeto['formadores'])
            registros = dados_projeto['total_registros']
            
            print(f"\n📋 {projeto}:")
            print(f"   📊 Registros: {registros}")
            print(f"   👨‍💼 Coordenadores: {coord_count}")
            for coord in sorted(dados_projeto['coordenadores']):
                print(f"      - {coord}")
            print(f"   👨‍🏫 Formadores: {form_count}")
            for form in sorted(dados_projeto['formadores']):
                print(f"      - {form}")
            
            # Verificar se formador = coordenador
            if coord_count == 1 and form_count == 1:
                coord = list(dados_projeto['coordenadores'])[0]
                form = list(dados_projeto['formadores'])[0]
                if coord == form:
                    print(f"   ✅ FORMADOR = COORDENADOR: {coord}")
        
        return dict(projetos_pequenos)
        
    except Exception as e:
        print(f"❌ Erro ao analisar projetos pequenos: {e}")
        return {}

def analisar_colecoes_vs_eventos(gc):
    """Analisa diferença entre coleções e eventos"""
    print("\n🔍 ANÁLISE: COLEÇÕES vs EVENTOS")
    
    try:
        planilha_agenda = gc.open_by_key(PLANILHAS_GOOGLE["Acompanhamento_Agenda_2025"])
        
        # Coleções principais (materiais didáticos)
        colecoes_principais = {
            "Superintendência": [
                "Novo Lendo", "TEMA", "Lendo e Escrevendo", 
                "Projeto AMMA", "Cirandar", "Miudezas", 
                "UNI DUNI TÊ", "Cataventos"
            ],
            "ACerta": [
                "Acerta Matemática", "Acerta Língua Portuguesa", 
                "Escrever Comunicar e Ser", "Superativar"
            ],
            "Brincando": [
                "Brincando e Aprendendo"
            ],
            "Vidas": [
                "Vida & Linguagem", "Vida & Matemática", "Vida & Ciências",
                "Avançando Juntos Matemática", "Avançando Juntos Língua Portuguesa"
            ],
            "Projetos_Específicos": [
                "A Cor da Gente", "Sou da Paz", "TRÂNSITO LEGAL", 
                "ED FINANCEIRA", "LER, OUVIR E CONTAR", 
                "LEIO, ESCREVO E CALCULO", "IDEB10"
            ]
        }
        
        # Eventos (não são coleções)
        eventos_identificados = [
            "Acerta - Esquenta SAEB",
            "Vida - ESQUENTA SAEB", 
            "IDEB10 - ESQUENTA SAEB"
        ]
        
        print(f"📚 COLEÇÕES PRINCIPAIS (MATERIAIS DIDÁTICOS):")
        total_colecoes = 0
        for categoria, colecoes in colecoes_principais.items():
            print(f"\n   🏢 {categoria}: {len(colecoes)} coleções")
            for colecao in colecoes:
                print(f"      - {colecao}")
            total_colecoes += len(colecoes)
        
        print(f"\n📊 Total de coleções: {total_colecoes}")
        
        print(f"\n🎯 EVENTOS IDENTIFICADOS (NÃO SÃO COLEÇÕES):")
        for evento in eventos_identificados:
            print(f"   - {evento}")
        
        print(f"\n💡 DIFERENÇA:")
        print(f"   📚 COLEÇÕES: Materiais didáticos, livros, kits")
        print(f"   🎯 EVENTOS: Atividades específicas, preparações, avaliações")
        print(f"   🔗 VINCULAÇÃO: Eventos são vinculados às coleções")
        
        return {
            'colecoes': colecoes_principais,
            'eventos': eventos_identificados,
            'total_colecoes': total_colecoes
        }
        
    except Exception as e:
        print(f"❌ Erro ao analisar coleções vs eventos: {e}")
        return {}

def main():
    """Função principal de análise completa"""
    print("🔍 Iniciando análise completa da estrutura de projetos...")
    
    gc = conectar_google_sheets()
    if not gc:
        return
    
    # Executar todas as análises
    projetos_estrutura = analisar_projetos_por_aba(gc)
    eventos_saeb = analisar_eventos_saeb(gc)
    projetos_pequenos = analisar_projetos_pequenos(gc)
    colecoes_vs_eventos = analisar_colecoes_vs_eventos(gc)
    
    # Consolidar análise completa (convertendo sets para lists)
    analise_completa = {
        "timestamp": datetime.now().isoformat(),
        "projetos_estrutura": projetos_estrutura,
        "eventos_saeb": eventos_saeb,
        "projetos_pequenos": {k: {**v, 'coordenadores': list(v['coordenadores']), 'formadores': list(v['formadores'])} for k, v in projetos_pequenos.items()},
        "colecoes_vs_eventos": colecoes_vs_eventos
    }
    
    # Salvar análise completa
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"analise_estrutura_projetos_completa_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(analise_completa, f, indent=2, ensure_ascii=False)
    
    print(f"\n🎉 ANÁLISE COMPLETA FINALIZADA!")
    print(f"📁 Arquivo salvo: {filename}")
    
    # Resumo final
    print(f"\n📊 RESUMO FINAL DA ESTRUTURA:")
    print(f"   📚 Total de coleções: {colecoes_vs_eventos.get('total_colecoes', 0)}")
    print(f"   🎯 Eventos SAEB: {len(eventos_saeb)}")
    print(f"   📋 Projetos pequenos: {len(projetos_pequenos)}")
    print(f"   🏢 Categorias principais: {len(projetos_estrutura)}")

if __name__ == "__main__":
    main()
