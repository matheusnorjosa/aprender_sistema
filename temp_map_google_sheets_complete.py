#!/usr/bin/env python
import os
import sys
import django
import gspread
import pandas as pd
from collections import defaultdict
import json
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')
django.setup()

print("=== MAPEAMENTO COMPLETO DAS PLANILHAS GOOGLE SHEETS ===")

# URLs das planilhas identificadas
PLANILHAS_GOOGLE = {
    "Disponibilidade_2025": {
        "url": "1fsCeGUzsNCv0SCiE6mcIvcCHsMbqNeyzANwdU_148Vw",
        "funcao": "Agenda e disponibilidade dos formadores"
    },
    "Controle_2025": {
        "url": "1P6YG3sIAEpiAPIQL9bKBaIznNl3V9VLan9CpVnrEOgA", 
        "funcao": "Controle geral do sistema"
    },
    "Acompanhamento_Agenda_2025": {
        "url": "16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU",
        "funcao": "Acompanhamento de eventos e agenda"
    },
    "Usuarios": {
        "url": "1Zj_I7sqYAJ9uaYbVoBfskl0LqxGM3SAFzwm4Zpph1RI",
        "funcao": "Base de usuários, formadores, hierarquias"
    }
}

def conectar_google_sheets():
    """Conecta ao Google Sheets usando as credenciais OAuth"""
    try:
        # Usar credenciais OAuth
        gc = gspread.oauth(
            credentials_filename='google_oauth_token.json',
            authorized_user_filename='google_oauth_token.json'
        )
        print("✅ Conectado ao Google Sheets com sucesso!")
        return gc
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        return None

def analisar_planilha(gc, nome_planilha, url, funcao):
    """Analisa uma planilha específica e retorna estatísticas"""
    print(f"\n📊 ANALISANDO: {nome_planilha}")
    print(f"   Função: {funcao}")
    print(f"   URL: {url}")
    
    try:
        # Abrir planilha
        planilha = gc.open_by_key(url)
        print(f"   ✅ Planilha aberta: {planilha.title}")
        
        # Obter todas as abas
        abas = planilha.worksheets()
        print(f"   📋 Total de abas: {len(abas)}")
        
        dados_planilha = {
            "nome": nome_planilha,
            "url": url,
            "funcao": funcao,
            "titulo": planilha.title,
            "total_abas": len(abas),
            "abas": []
        }
        
        total_registros = 0
        total_colunas = 0
        
        for aba in abas:
            print(f"\n   📄 ABA: {aba.title}")
            
            try:
                # Obter dados da aba
                dados_aba = aba.get_all_values()
                
                if not dados_aba:
                    print(f"      ⚠️  Aba vazia")
                    continue
                
                # Estatísticas da aba
                linhas = len(dados_aba)
                colunas = len(dados_aba[0]) if dados_aba else 0
                
                print(f"      📊 Linhas: {linhas}")
                print(f"      📊 Colunas: {colunas}")
                
                # Cabeçalhos
                if dados_aba:
                    cabecalhos = dados_aba[0]
                    print(f"      📋 Cabeçalhos: {cabecalhos[:10]}...")  # Primeiros 10
                
                # Contar registros não vazios
                registros_validos = 0
                for linha in dados_aba[1:]:  # Pular cabeçalho
                    if any(celula.strip() for celula in linha):  # Se tem pelo menos uma célula não vazia
                        registros_validos += 1
                
                print(f"      📊 Registros válidos: {registros_validos}")
                
                # Detectar tipos de dados
                tipos_dados = detectar_tipos_dados(dados_aba)
                print(f"      🔍 Tipos detectados: {tipos_dados}")
                
                # Salvar dados da aba
                dados_aba_info = {
                    "nome": aba.title,
                    "linhas": linhas,
                    "colunas": colunas,
                    "registros_validos": registros_validos,
                    "cabecalhos": cabecalhos,
                    "tipos_dados": tipos_dados,
                    "amostra_dados": dados_aba[:5] if len(dados_aba) > 5 else dados_aba  # Primeiras 5 linhas
                }
                
                dados_planilha["abas"].append(dados_aba_info)
                total_registros += registros_validos
                total_colunas = max(total_colunas, colunas)
                
            except Exception as e:
                print(f"      ❌ Erro ao analisar aba {aba.title}: {e}")
                continue
        
        dados_planilha["total_registros"] = total_registros
        dados_planilha["max_colunas"] = total_colunas
        
        print(f"\n   📊 RESUMO {nome_planilha}:")
        print(f"      Total de registros: {total_registros}")
        print(f"      Máximo de colunas: {total_colunas}")
        
        return dados_planilha
        
    except Exception as e:
        print(f"   ❌ Erro ao analisar planilha {nome_planilha}: {e}")
        return None

def detectar_tipos_dados(dados):
    """Detecta tipos de dados nas colunas"""
    if not dados or len(dados) < 2:
        return {}
    
    cabecalhos = dados[0]
    tipos = {}
    
    for i, cabecalho in enumerate(cabecalhos):
        if not cabecalho.strip():
            continue
            
        # Analisar coluna
        valores = [linha[i] if i < len(linha) else '' for linha in dados[1:]]
        valores_nao_vazios = [v.strip() for v in valores if v.strip()]
        
        if not valores_nao_vazios:
            tipos[cabecalho] = "vazio"
            continue
        
        # Detectar tipo
        tipo = "texto"
        
        # Verificar se são emails
        if any('@' in v for v in valores_nao_vazios[:10]):
            tipo = "email"
        # Verificar se são CPFs
        elif all(len(v.replace('.', '').replace('-', '')) == 11 and v.replace('.', '').replace('-', '').isdigit() for v in valores_nao_vazios[:5]):
            tipo = "cpf"
        # Verificar se são datas
        elif any('/' in v or '-' in v for v in valores_nao_vazios[:10]):
            tipo = "data"
        # Verificar se são números
        elif all(v.replace(',', '').replace('.', '').isdigit() for v in valores_nao_vazios[:10]):
            tipo = "numero"
        
        tipos[cabecalho] = tipo
    
    return tipos

def main():
    """Função principal de mapeamento"""
    print("🔍 Iniciando mapeamento completo das planilhas Google Sheets...")
    
    # Conectar ao Google Sheets
    gc = conectar_google_sheets()
    if not gc:
        print("❌ Não foi possível conectar ao Google Sheets")
        return
    
    # Mapear todas as planilhas
    mapeamento_completo = {
        "timestamp": datetime.now().isoformat(),
        "planilhas": {},
        "resumo_geral": {}
    }
    
    total_planilhas = 0
    total_abas = 0
    total_registros = 0
    total_usuarios_unicos = set()
    total_emails_unicos = set()
    total_cpfs_unicos = set()
    
    for nome, info in PLANILHAS_GOOGLE.items():
        dados_planilha = analisar_planilha(gc, nome, info["url"], info["funcao"])
        
        if dados_planilha:
            mapeamento_completo["planilhas"][nome] = dados_planilha
            total_planilhas += 1
            total_abas += dados_planilha["total_abas"]
            total_registros += dados_planilha["total_registros"]
            
            # Extrair dados únicos
            for aba in dados_planilha["abas"]:
                for linha in aba["amostra_dados"][1:]:  # Pular cabeçalho
                    for i, valor in enumerate(linha):
                        if i < len(aba["cabecalhos"]):
                            cabecalho = aba["cabecalhos"][i]
                            if valor.strip():
                                # Detectar emails
                                if '@' in valor:
                                    total_emails_unicos.add(valor.strip())
                                # Detectar CPFs
                                elif len(valor.replace('.', '').replace('-', '')) == 11 and valor.replace('.', '').replace('-', '').isdigit():
                                    total_cpfs_unicos.add(valor.replace('.', '').replace('-', ''))
                                # Detectar nomes (heurística simples)
                                elif any(palavra in cabecalho.lower() for palavra in ['nome', 'name', 'usuario', 'user']):
                                    total_usuarios_unicos.add(valor.strip())
    
    # Resumo geral
    mapeamento_completo["resumo_geral"] = {
        "total_planilhas_analisadas": total_planilhas,
        "total_abas": total_abas,
        "total_registros": total_registros,
        "usuarios_unicos_detectados": len(total_usuarios_unicos),
        "emails_unicos_detectados": len(total_emails_unicos),
        "cpfs_unicos_detectados": len(total_cpfs_unicos),
        "planilhas_disponiveis": list(PLANILHAS_GOOGLE.keys())
    }
    
    # Salvar mapeamento
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"mapeamento_completo_google_sheets_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(mapeamento_completo, f, indent=2, ensure_ascii=False)
    
    # Relatório final
    print(f"\n🎉 MAPEAMENTO COMPLETO FINALIZADO!")
    print(f"📊 RESUMO GERAL:")
    print(f"   Planilhas analisadas: {total_planilhas}")
    print(f"   Total de abas: {total_abas}")
    print(f"   Total de registros: {total_registros}")
    print(f"   Usuários únicos detectados: {len(total_usuarios_unicos)}")
    print(f"   Emails únicos detectados: {len(total_emails_unicos)}")
    print(f"   CPFs únicos detectados: {len(total_cpfs_unicos)}")
    print(f"📁 Arquivo salvo: {filename}")
    
    # Mostrar detalhes por planilha
    print(f"\n📋 DETALHES POR PLANILHA:")
    for nome, dados in mapeamento_completo["planilhas"].items():
        print(f"\n   📊 {nome}:")
        print(f"      Abas: {dados['total_abas']}")
        print(f"      Registros: {dados['total_registros']}")
        print(f"      Função: {dados['funcao']}")
        
        for aba in dados["abas"]:
            print(f"      📄 {aba['nome']}: {aba['registros_validos']} registros, {aba['colunas']} colunas")

if __name__ == "__main__":
    main()
