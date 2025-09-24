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

print("=== ANÁLISE PROFUNDA DO CONTEXTO ORGANIZACIONAL ===")

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

def analisar_usuarios_e_hierarquia(gc):
    """Analisa a planilha de usuários para entender hierarquia"""
    print("\n🔍 ANALISANDO USUÁRIOS E HIERARQUIA")
    
    try:
        planilha = gc.open_by_key(PLANILHAS_GOOGLE["Usuarios"])
        aba_ativos = planilha.worksheet("Ativos")
        dados = aba_ativos.get_all_values()
        
        if not dados:
            return {}
        
        cabecalhos = dados[0]
        usuarios = []
        
        for linha in dados[1:]:
            if len(linha) >= len(cabecalhos):
                usuario = {}
                for i, cabecalho in enumerate(cabecalhos):
                    usuario[cabecalho] = linha[i] if i < len(linha) else ''
                usuarios.append(usuario)
        
        print(f"📊 {len(usuarios)} usuários ativos analisados")
        
        # Análise de cargos
        cargos = Counter()
        gerencias = Counter()
        projetos_por_usuario = defaultdict(list)
        
        for usuario in usuarios:
            cargo = usuario.get('Cargo', '').strip()
            gerencia = usuario.get('Gerência', '').strip()
            
            if cargo:
                cargos[cargo] += 1
            
            if gerencia:
                gerencias[gerencia] += 1
                projetos_por_usuario[usuario.get('Nome Completo', '')].append(gerencia)
        
        print(f"\n📋 CARGOS IDENTIFICADOS:")
        for cargo, count in cargos.most_common():
            print(f"   - {cargo}: {count} pessoas")
        
        print(f"\n🏢 GERÊNCIAS/PROJETOS:")
        for gerencia, count in gerencias.most_common():
            print(f"   - {gerencia}: {count} pessoas")
        
        return {
            'usuarios': usuarios,
            'cargos': dict(cargos),
            'gerencias': dict(gerencias),
            'projetos_por_usuario': dict(projetos_por_usuario)
        }
        
    except Exception as e:
        print(f"❌ Erro ao analisar usuários: {e}")
        return {}

def analisar_projetos_e_colecoes(gc):
    """Analisa projetos e coleções nas planilhas"""
    print("\n🔍 ANALISANDO PROJETOS E COLEÇÕES")
    
    projetos_identificados = set()
    colecoes_identificadas = set()
    produtos_identificados = set()
    
    try:
        # Analisar planilha de Controle
        planilha_controle = gc.open_by_key(PLANILHAS_GOOGLE["Controle_2025"])
        
        # Aba CONFIG - configurações gerais
        try:
            aba_config = planilha_controle.worksheet("⚙️ CONFIG")
            dados_config = aba_config.get_all_values()
            
            if dados_config:
                cabecalhos = dados_config[0]
                for linha in dados_config[1:]:
                    if len(linha) >= len(cabecalhos):
                        for i, cabecalho in enumerate(cabecalhos):
                            if 'projeto' in cabecalho.lower() and linha[i]:
                                projetos_identificados.add(linha[i].strip())
                            elif 'coleção' in cabecalho.lower() and linha[i]:
                                colecoes_identificadas.add(linha[i].strip())
        except:
            pass
        
        # Aba COMPRAS - produtos
        try:
            aba_compras = planilha_controle.worksheet("🟥 COMPRAS")
            dados_compras = aba_compras.get_all_values()
            
            if dados_compras:
                cabecalhos = dados_compras[0]
                for linha in dados_compras[1:]:
                    if len(linha) >= len(cabecalhos):
                        for i, cabecalho in enumerate(cabecalhos):
                            if 'produto' in cabecalho.lower() and linha[i]:
                                produtos_identificados.add(linha[i].strip())
        except:
            pass
        
        # Analisar planilha de Acompanhamento
        planilha_agenda = gc.open_by_key(PLANILHAS_GOOGLE["Acompanhamento_Agenda_2025"])
        
        # Analisar abas de projetos
        abas_projetos = ['Super', 'ACerta', 'Brincando', 'Vidas', 'Outros']
        
        for aba_nome in abas_projetos:
            try:
                aba = planilha_agenda.worksheet(aba_nome)
                dados = aba.get_all_values()
                
                if dados:
                    cabecalhos = dados[0]
                    for linha in dados[1:]:
                        if len(linha) >= len(cabecalhos):
                            for i, cabecalho in enumerate(cabecalhos):
                                if 'projeto' in cabecalho.lower() and linha[i]:
                                    projetos_identificados.add(linha[i].strip())
                                elif 'segmento' in cabecalho.lower() and linha[i]:
                                    colecoes_identificadas.add(linha[i].strip())
            except:
                pass
        
        print(f"📊 PROJETOS IDENTIFICADOS ({len(projetos_identificados)}):")
        for projeto in sorted(projetos_identificados):
            print(f"   - {projeto}")
        
        print(f"\n📚 COLEÇÕES IDENTIFICADAS ({len(colecoes_identificadas)}):")
        for colecao in sorted(colecoes_identificadas):
            print(f"   - {colecao}")
        
        print(f"\n🛍️ PRODUTOS IDENTIFICADOS ({len(produtos_identificados)}):")
        for produto in sorted(list(produtos_identificados)[:20]):  # Mostrar primeiros 20
            print(f"   - {produto}")
        if len(produtos_identificados) > 20:
            print(f"   ... e mais {len(produtos_identificados) - 20} produtos")
        
        return {
            'projetos': list(projetos_identificados),
            'colecoes': list(colecoes_identificadas),
            'produtos': list(produtos_identificados)
        }
        
    except Exception as e:
        print(f"❌ Erro ao analisar projetos: {e}")
        return {}

def analisar_vinculacoes_superintendencia(gc):
    """Analisa quais projetos são vinculados à superintendência"""
    print("\n🔍 ANALISANDO VINCULAÇÕES À SUPERINTENDÊNCIA")
    
    try:
        # Analisar planilha de usuários
        planilha_usuarios = gc.open_by_key(PLANILHAS_GOOGLE["Usuarios"])
        aba_ativos = planilha_usuarios.worksheet("Ativos")
        dados = aba_ativos.get_all_values()
        
        if not dados:
            return {}
        
        cabecalhos = dados[0]
        usuarios_superintendencia = []
        outros_usuarios = []
        
        for linha in dados[1:]:
            if len(linha) >= len(cabecalhos):
                usuario = {}
                for i, cabecalho in enumerate(cabecalhos):
                    usuario[cabecalho] = linha[i] if i < len(linha) else ''
                
                gerencia = usuario.get('Gerência', '').strip().lower()
                if 'superintendência' in gerencia or 'superintendencia' in gerencia:
                    usuarios_superintendencia.append(usuario)
                else:
                    outros_usuarios.append(usuario)
        
        print(f"🏢 USUÁRIOS DA SUPERINTENDÊNCIA: {len(usuarios_superintendencia)}")
        for usuario in usuarios_superintendencia:
            print(f"   - {usuario.get('Nome Completo', '')} ({usuario.get('Cargo', '')}) - {usuario.get('Gerência', '')}")
        
        print(f"\n🏢 OUTROS USUÁRIOS: {len(outros_usuarios)}")
        gerencias_outros = Counter()
        for usuario in outros_usuarios:
            gerencia = usuario.get('Gerência', '').strip()
            if gerencia:
                gerencias_outros[gerencia] += 1
        
        for gerencia, count in gerencias_outros.most_common():
            print(f"   - {gerencia}: {count} pessoas")
        
        return {
            'superintendencia': usuarios_superintendencia,
            'outros': outros_usuarios,
            'gerencias_outros': dict(gerencias_outros)
        }
        
    except Exception as e:
        print(f"❌ Erro ao analisar superintendência: {e}")
        return {}

def analisar_formadores_coordenadores(gc):
    """Analisa formadores, coordenadores e outros cargos"""
    print("\n🔍 ANALISANDO FORMADORES, COORDENADORES E OUTROS CARGOS")
    
    try:
        planilha_usuarios = gc.open_by_key(PLANILHAS_GOOGLE["Usuarios"])
        aba_ativos = planilha_usuarios.worksheet("Ativos")
        dados = aba_ativos.get_all_values()
        
        if not dados:
            return {}
        
        cabecalhos = dados[0]
        formadores = []
        coordenadores = []
        gerentes = []
        controle = []
        dat = []
        outros = []
        
        for linha in dados[1:]:
            if len(linha) >= len(cabecalhos):
                usuario = {}
                for i, cabecalho in enumerate(cabecalhos):
                    usuario[cabecalho] = linha[i] if i < len(linha) else ''
                
                cargo = usuario.get('Cargo', '').strip().lower()
                nome = usuario.get('Nome Completo', '').strip()
                
                if not nome:
                    continue
                
                if 'formador' in cargo:
                    formadores.append(usuario)
                elif 'coordenador' in cargo:
                    coordenadores.append(usuario)
                elif 'gerente' in cargo:
                    gerentes.append(usuario)
                elif 'controle' in cargo:
                    controle.append(usuario)
                elif 'dat' in cargo:
                    dat.append(usuario)
                else:
                    outros.append(usuario)
        
        print(f"👨‍🏫 FORMADORES: {len(formadores)}")
        for formador in formadores[:10]:  # Mostrar primeiros 10
            print(f"   - {formador.get('Nome Completo', '')} - {formador.get('Gerência', '')}")
        if len(formadores) > 10:
            print(f"   ... e mais {len(formadores) - 10} formadores")
        
        print(f"\n👨‍💼 COORDENADORES: {len(coordenadores)}")
        for coordenador in coordenadores:
            print(f"   - {coordenador.get('Nome Completo', '')} - {coordenador.get('Gerência', '')}")
        
        print(f"\n👔 GERENTES: {len(gerentes)}")
        for gerente in gerentes:
            print(f"   - {gerente.get('Nome Completo', '')} - {gerente.get('Gerência', '')}")
        
        print(f"\n🔍 CONTROLE: {len(controle)}")
        for pessoa in controle:
            print(f"   - {pessoa.get('Nome Completo', '')} - {pessoa.get('Gerência', '')}")
        
        print(f"\n📊 DAT: {len(dat)}")
        for pessoa in dat:
            print(f"   - {pessoa.get('Nome Completo', '')} - {pessoa.get('Gerência', '')}")
        
        print(f"\n❓ OUTROS CARGOS: {len(outros)}")
        for pessoa in outros:
            print(f"   - {pessoa.get('Nome Completo', '')} - {pessoa.get('Cargo', '')} - {pessoa.get('Gerência', '')}")
        
        return {
            'formadores': formadores,
            'coordenadores': coordenadores,
            'gerentes': gerentes,
            'controle': controle,
            'dat': dat,
            'outros': outros
        }
        
    except Exception as e:
        print(f"❌ Erro ao analisar cargos: {e}")
        return {}

def analisar_estrutura_projetos(gc):
    """Analisa a estrutura detalhada dos projetos"""
    print("\n🔍 ANALISANDO ESTRUTURA DETALHADA DOS PROJETOS")
    
    try:
        planilha_agenda = gc.open_by_key(PLANILHAS_GOOGLE["Acompanhamento_Agenda_2025"])
        
        projetos_estrutura = {}
        
        # Analisar cada aba de projeto
        abas_projetos = ['Super', 'ACerta', 'Brincando', 'Vidas', 'Outros']
        
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
                
                # Analisar coordenadores e formadores
                coordenadores_projeto = set()
                formadores_projeto = set()
                municipios_projeto = set()
                
                for linha in dados[1:]:
                    if len(linha) >= len(cabecalhos):
                        for i, cabecalho in enumerate(cabecalhos):
                            valor = linha[i].strip() if i < len(linha) else ''
                            if valor:
                                if 'coordenador' in cabecalho.lower():
                                    coordenadores_projeto.add(valor)
                                elif 'formador' in cabecalho.lower():
                                    formadores_projeto.add(valor)
                                elif 'município' in cabecalho.lower() or 'municipio' in cabecalho.lower():
                                    municipios_projeto.add(valor)
                
                print(f"   Coordenadores: {len(coordenadores_projeto)}")
                for coord in sorted(coordenadores_projeto):
                    print(f"      - {coord}")
                
                print(f"   Formadores: {len(formadores_projeto)}")
                for form in sorted(list(formadores_projeto)[:10]):  # Primeiros 10
                    print(f"      - {form}")
                if len(formadores_projeto) > 10:
                    print(f"      ... e mais {len(formadores_projeto) - 10} formadores")
                
                print(f"   Municípios: {len(municipios_projeto)}")
                
                projetos_estrutura[aba_nome] = {
                    'coordenadores': list(coordenadores_projeto),
                    'formadores': list(formadores_projeto),
                    'municipios': list(municipios_projeto),
                    'total_registros': len(dados) - 1
                }
                
            except Exception as e:
                print(f"   ❌ Erro ao analisar {aba_nome}: {e}")
                continue
        
        return projetos_estrutura
        
    except Exception as e:
        print(f"❌ Erro ao analisar estrutura: {e}")
        return {}

def main():
    """Função principal de análise"""
    print("🔍 Iniciando análise profunda do contexto organizacional...")
    
    gc = conectar_google_sheets()
    if not gc:
        return
    
    # Executar todas as análises
    usuarios_hierarquia = analisar_usuarios_e_hierarquia(gc)
    projetos_colecoes = analisar_projetos_e_colecoes(gc)
    superintendencia = analisar_vinculacoes_superintendencia(gc)
    cargos = analisar_formadores_coordenadores(gc)
    estrutura_projetos = analisar_estrutura_projetos(gc)
    
    # Consolidar análise
    analise_completa = {
        "timestamp": datetime.now().isoformat(),
        "usuarios_hierarquia": usuarios_hierarquia,
        "projetos_colecoes": projetos_colecoes,
        "superintendencia": superintendencia,
        "cargos": cargos,
        "estrutura_projetos": estrutura_projetos
    }
    
    # Salvar análise
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"analise_contexto_organizacional_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(analise_completa, f, indent=2, ensure_ascii=False)
    
    print(f"\n🎉 ANÁLISE COMPLETA FINALIZADA!")
    print(f"📁 Arquivo salvo: {filename}")
    
    # Resumo final
    print(f"\n📊 RESUMO FINAL DO CONTEXTO ORGANIZACIONAL:")
    print(f"   👥 Total de usuários ativos: {len(usuarios_hierarquia.get('usuarios', []))}")
    print(f"   🏢 Projetos identificados: {len(projetos_colecoes.get('projetos', []))}")
    print(f"   📚 Coleções identificadas: {len(projetos_colecoes.get('colecoes', []))}")
    print(f"   🛍️ Produtos identificados: {len(projetos_colecoes.get('produtos', []))}")
    print(f"   👨‍🏫 Formadores: {len(cargos.get('formadores', []))}")
    print(f"   👨‍💼 Coordenadores: {len(cargos.get('coordenadores', []))}")
    print(f"   👔 Gerentes: {len(cargos.get('gerentes', []))}")
    print(f"   🔍 Controle: {len(cargos.get('controle', []))}")
    print(f"   📊 DAT: {len(cargos.get('dat', []))}")

if __name__ == "__main__":
    main()
