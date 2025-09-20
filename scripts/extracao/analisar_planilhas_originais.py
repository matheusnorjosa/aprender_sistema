#!/usr/bin/env python
import json
import csv
from datetime import datetime
from collections import defaultdict, Counter

def determinar_status_aprovacao(aba, linha, super_status_data):
    """Determina o status de aprovação baseado na aba e dados de status"""
    if aba == 'super':
        # Para aba SUPER, verificar no arquivo de status
        for status_registro in super_status_data:
            if status_registro.get('linha_original') == linha:
                status = status_registro.get('status', '').upper()
                if status == 'APROVADO':
                    return 'APROVADO'
                elif status == 'PENDENTE':
                    return 'PENDENTE'
                else:
                    return 'PENDENTE'  # Default para pendente se não especificado
        return 'PENDENTE'  # Se não encontrado no arquivo de status
    else:
        # Para outras abas, sempre aprovado
        return 'APROVADO'

def analisar_planilhas_originais():
    """Analisa apenas os dados das planilhas originais (JSON) com lógica de aprovação"""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. ANÁLISE DOS DADOS DAS PLANILHAS
    print("🔍 Analisando dados das planilhas originais...")
    
    # Carregar dados das planilhas
    planilhas = {
        'super': 'dados_planilhas_originais/super_colunas_e_t_tratados.json',
        'vidas': 'dados_planilhas_originais/vidas_colunas_e_t_tratados.json',
        'brincando': 'dados_planilhas_originais/brincando_colunas_e_t_tratados.json',
        'acerta': 'dados_planilhas_originais/acerta_colunas_e_t_tratados.json',
        'outros': 'dados_planilhas_originais/outros_colunas_e_t_tratados.json'
    }
    
    # Carregar dados de status de aprovação da aba SUPER
    super_status_file = 'dados_planilhas_originais/previa_aba_super.json'
    super_status_data = []
    try:
        with open(super_status_file, 'r', encoding='utf-8') as f:
            super_status_data = json.load(f)
        print(f"✅ Status de aprovação SUPER: {len(super_status_data)} registros")
    except FileNotFoundError:
        print(f"❌ Arquivo de status não encontrado: {super_status_file}")
        super_status_data = []
    
    dados_planilhas = {}
    for nome, arquivo in planilhas.items():
        try:
            with open(arquivo, 'r', encoding='utf-8') as f:
                dados_planilhas[nome] = json.load(f)
            print(f"✅ {nome}: {len(dados_planilhas[nome])} registros")
        except FileNotFoundError:
            print(f"❌ Arquivo não encontrado: {arquivo}")
            dados_planilhas[nome] = []
    
    # 2. EXTRAIR FORMADORES ÚNICOS DAS PLANILHAS
    formadores_planilhas = set()
    coordenadores_planilhas = set()
    projetos_planilhas = set()
    municipios_planilhas = set()
    tipos_evento_planilhas = set()
    
    for aba, dados in dados_planilhas.items():
        for registro in dados:
            # Formadores
            if 'formadores' in registro:
                for formador in registro['formadores']:
                    if formador and formador.strip():
                        formadores_planilhas.add(formador.strip())
            
            # Projetos
            if 'projeto' in registro:
                projetos_planilhas.add(registro['projeto'])
            
            # Municípios
            if 'municipio' in registro:
                municipios_planilhas.add(registro['municipio'])
            
            # Tipos de evento
            if 'tipo_evento' in registro:
                tipos_evento_planilhas.add(registro['tipo_evento'])
            
            # Coordenadores (das observações)
            if 'observacoes' in registro:
                obs = registro['observacoes']
                if 'Coordenador Responsável:' in obs:
                    # Extrair nome do coordenador
                    partes = obs.split('Coordenador Responsável:')
                    if len(partes) > 1:
                        coord_part = partes[1].split('|')[0].strip()
                        if coord_part:
                            coordenadores_planilhas.add(coord_part)
    
    # 3. GERAR RELATÓRIO DE FORMADORES DAS PLANILHAS
    with open(f'planilhas_formadores_unicos_{timestamp}.csv', 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Formador', 'Total_Eventos', 'Projetos', 'Municipios', 'Tipos_Evento'])
        
        for formador in sorted(formadores_planilhas):
            eventos_count = 0
            projetos_formador = set()
            municipios_formador = set()
            tipos_formador = set()
            
            for aba, dados in dados_planilhas.items():
                for registro in dados:
                    if 'formadores' in registro and formador in registro['formadores']:
                        eventos_count += 1
                        if 'projeto' in registro:
                            projetos_formador.add(registro['projeto'])
                        if 'municipio' in registro:
                            municipios_formador.add(registro['municipio'])
                        if 'tipo_evento' in registro:
                            tipos_formador.add(registro['tipo_evento'])
            
            writer.writerow([
                formador,
                eventos_count,
                '; '.join(sorted(projetos_formador)),
                '; '.join(sorted(municipios_formador)),
                '; '.join(sorted(tipos_formador))
            ])
    
    # 4. GERAR RELATÓRIO DE COORDENADORES DAS PLANILHAS
    with open(f'planilhas_coordenadores_{timestamp}.csv', 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Coordenador', 'Total_Eventos', 'Projetos', 'Municipios', 'Acompanha_Eventos'])
        
        for coordenador in sorted(coordenadores_planilhas):
            eventos_count = 0
            projetos_coord = set()
            municipios_coord = set()
            acompanha_count = 0
            
            for aba, dados in dados_planilhas.items():
                for registro in dados:
                    if 'observacoes' in registro and coordenador in registro['observacoes']:
                        eventos_count += 1
                        if 'projeto' in registro:
                            projetos_coord.add(registro['projeto'])
                        if 'municipio' in registro:
                            municipios_coord.add(registro['municipio'])
                        if 'Coordenador Acompanha: Sim' in registro['observacoes']:
                            acompanha_count += 1
            
            writer.writerow([
                coordenador,
                eventos_count,
                '; '.join(sorted(projetos_coord)),
                '; '.join(sorted(municipios_coord)),
                acompanha_count
            ])
    
    # 5. GERAR RELATÓRIO DE PROJETOS DAS PLANILHAS
    with open(f'planilhas_projetos_{timestamp}.csv', 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Projeto', 'Total_Eventos', 'Formadores', 'Municipios', 'Tipos_Evento', 'Aba_Origem'])
        
        for projeto in sorted(projetos_planilhas):
            eventos_count = 0
            formadores_projeto = set()
            municipios_projeto = set()
            tipos_projeto = set()
            abas_projeto = set()
            
            for aba, dados in dados_planilhas.items():
                for registro in dados:
                    if 'projeto' in registro and projeto in registro['projeto']:
                        eventos_count += 1
                        abas_projeto.add(aba)
                        if 'formadores' in registro:
                            for formador in registro['formadores']:
                                if formador and formador.strip():
                                    formadores_projeto.add(formador.strip())
                        if 'municipio' in registro:
                            municipios_projeto.add(registro['municipio'])
                        if 'tipo_evento' in registro:
                            tipos_projeto.add(registro['tipo_evento'])
            
            writer.writerow([
                projeto,
                eventos_count,
                '; '.join(sorted(formadores_projeto)),
                '; '.join(sorted(municipios_projeto)),
                '; '.join(sorted(tipos_projeto)),
                '; '.join(sorted(abas_projeto))
            ])
    
    # 6. GERATÓRIO DE MUNICÍPIOS DAS PLANILHAS
    with open(f'planilhas_municipios_{timestamp}.csv', 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Municipio', 'Total_Eventos', 'Projetos', 'Formadores', 'Tipos_Evento'])
        
        for municipio in sorted(municipios_planilhas):
            eventos_count = 0
            projetos_municipio = set()
            formadores_municipio = set()
            tipos_municipio = set()
            
            for aba, dados in dados_planilhas.items():
                for registro in dados:
                    if 'municipio' in registro and municipio in registro['municipio']:
                        eventos_count += 1
                        if 'projeto' in registro:
                            projetos_municipio.add(registro['projeto'])
                        if 'formadores' in registro:
                            for formador in registro['formadores']:
                                if formador and formador.strip():
                                    formadores_municipio.add(formador.strip())
                        if 'tipo_evento' in registro:
                            tipos_municipio.add(registro['tipo_evento'])
            
            writer.writerow([
                municipio,
                eventos_count,
                '; '.join(sorted(projetos_municipio)),
                '; '.join(sorted(formadores_municipio)),
                '; '.join(sorted(tipos_municipio))
            ])
    
    # 7. RELATÓRIO CONSOLIDADO DAS PLANILHAS
    with open(f'planilhas_consolidado_{timestamp}.csv', 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Categoria', 'Total', 'Detalhes'])
        
        # Estatísticas gerais das planilhas
        total_registros = sum(len(dados) for dados in dados_planilhas.values())
        writer.writerow(['Total_Registros_Planilhas', total_registros, 'Total de registros em todas as abas'])
        
        for aba, dados in dados_planilhas.items():
            writer.writerow([f'Registros_Aba_{aba.upper()}', len(dados), f'Registros na aba {aba}'])
        
        writer.writerow(['Formadores_Unicos_Planilhas', len(formadores_planilhas), 'Formadores únicos identificados'])
        writer.writerow(['Coordenadores_Unicos_Planilhas', len(coordenadores_planilhas), 'Coordenadores únicos identificados'])
        writer.writerow(['Projetos_Unicos_Planilhas', len(projetos_planilhas), 'Projetos únicos identificados'])
        writer.writerow(['Municipios_Unicos_Planilhas', len(municipios_planilhas), 'Municípios únicos identificados'])
        writer.writerow(['Tipos_Evento_Unicos_Planilhas', len(tipos_evento_planilhas), 'Tipos de evento únicos identificados'])
        
        # Análise por aba
        for aba, dados in dados_planilhas.items():
            formadores_aba = set()
            projetos_aba = set()
            municipios_aba = set()
            
            for registro in dados:
                if 'formadores' in registro:
                    for formador in registro['formadores']:
                        if formador and formador.strip():
                            formadores_aba.add(formador.strip())
                if 'projeto' in registro:
                    projetos_aba.add(registro['projeto'])
                if 'municipio' in registro:
                    municipios_aba.add(registro['municipio'])
            
            writer.writerow([f'Formadores_Aba_{aba.upper()}', len(formadores_aba), f'Formadores únicos na aba {aba}'])
            writer.writerow([f'Projetos_Aba_{aba.upper()}', len(projetos_aba), f'Projetos únicos na aba {aba}'])
            writer.writerow([f'Municipios_Aba_{aba.upper()}', len(municipios_aba), f'Municípios únicos na aba {aba}'])
    
    # 8. ANÁLISE DETALHADA POR ABA COM STATUS DE APROVAÇÃO
    with open(f'planilhas_analise_detalhada_{timestamp}.csv', 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Aba', 'Registro', 'Data_Evento', 'Municipio', 'Projeto', 'Tipo_Evento', 'Formadores', 'Coordenador_Responsavel', 'Coordenador_Acompanha', 'Status_Aprovacao', 'Observacoes'])
        
        for aba, dados in dados_planilhas.items():
            for i, registro in enumerate(dados, 1):
                # Extrair coordenador responsável
                coord_responsavel = ''
                coord_acompanha = 'Não'
                
                if 'observacoes' in registro:
                    obs = registro['observacoes']
                    if 'Coordenador Responsável:' in obs:
                        partes = obs.split('Coordenador Responsável:')
                        if len(partes) > 1:
                            coord_responsavel = partes[1].split('|')[0].strip()
                    if 'Coordenador Acompanha: Sim' in obs:
                        coord_acompanha = 'Sim'
                
                # Determinar status de aprovação
                linha = registro.get('linha', i)
                status_aprovacao = determinar_status_aprovacao(aba, linha, super_status_data)
                
                writer.writerow([
                    aba.upper(),
                    i,
                    registro.get('data_evento', ''),
                    registro.get('municipio', ''),
                    registro.get('projeto', ''),
                    registro.get('tipo_evento', ''),
                    '; '.join(registro.get('formadores', [])),
                    coord_responsavel,
                    coord_acompanha,
                    status_aprovacao,
                    registro.get('observacoes', '')
                ])
    
    # 9. RELATÓRIO DE EVENTOS APROVADOS
    with open(f'planilhas_eventos_aprovados_{timestamp}.csv', 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Aba', 'Registro', 'Data_Evento', 'Municipio', 'Projeto', 'Tipo_Evento', 'Formadores', 'Coordenador_Responsavel', 'Status_Aprovacao'])
        
        eventos_aprovados = 0
        for aba, dados in dados_planilhas.items():
            for i, registro in enumerate(dados, 1):
                linha = registro.get('linha', i)
                status_aprovacao = determinar_status_aprovacao(aba, linha, super_status_data)
                
                if status_aprovacao == 'APROVADO':
                    eventos_aprovados += 1
                    # Extrair coordenador responsável
                    coord_responsavel = ''
                    if 'observacoes' in registro:
                        obs = registro['observacoes']
                        if 'Coordenador Responsável:' in obs:
                            partes = obs.split('Coordenador Responsável:')
                            if len(partes) > 1:
                                coord_responsavel = partes[1].split('|')[0].strip()
                    
                    writer.writerow([
                        aba.upper(),
                        i,
                        registro.get('data_evento', ''),
                        registro.get('municipio', ''),
                        registro.get('projeto', ''),
                        registro.get('tipo_evento', ''),
                        '; '.join(registro.get('formadores', [])),
                        coord_responsavel,
                        status_aprovacao
                    ])
    
    # 10. RELATÓRIO DE EVENTOS PENDENTES
    with open(f'planilhas_eventos_pendentes_{timestamp}.csv', 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Aba', 'Registro', 'Data_Evento', 'Municipio', 'Projeto', 'Tipo_Evento', 'Formadores', 'Coordenador_Responsavel', 'Status_Aprovacao'])
        
        eventos_pendentes = 0
        for aba, dados in dados_planilhas.items():
            for i, registro in enumerate(dados, 1):
                linha = registro.get('linha', i)
                status_aprovacao = determinar_status_aprovacao(aba, linha, super_status_data)
                
                if status_aprovacao == 'PENDENTE':
                    eventos_pendentes += 1
                    # Extrair coordenador responsável
                    coord_responsavel = ''
                    if 'observacoes' in registro:
                        obs = registro['observacoes']
                        if 'Coordenador Responsável:' in obs:
                            partes = obs.split('Coordenador Responsável:')
                            if len(partes) > 1:
                                coord_responsavel = partes[1].split('|')[0].strip()
                    
                    writer.writerow([
                        aba.upper(),
                        i,
                        registro.get('data_evento', ''),
                        registro.get('municipio', ''),
                        registro.get('projeto', ''),
                        registro.get('tipo_evento', ''),
                        '; '.join(registro.get('formadores', [])),
                        coord_responsavel,
                        status_aprovacao
                    ])
    
    # 11. RELATÓRIO DE ANÁLISE DE APROVAÇÃO
    with open(f'planilhas_analise_aprovacao_{timestamp}.csv', 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Categoria', 'Total', 'Detalhes'])
        
        writer.writerow(['Total_Eventos_Aprovados', eventos_aprovados, 'Eventos com status APROVADO'])
        writer.writerow(['Total_Eventos_Pendentes', eventos_pendentes, 'Eventos com status PENDENTE'])
        writer.writerow(['Total_Eventos_Geral', eventos_aprovados + eventos_pendentes, 'Total de eventos analisados'])
        
        # Análise por aba
        for aba, dados in dados_planilhas.items():
            aprovados_aba = 0
            pendentes_aba = 0
            
            for i, registro in enumerate(dados, 1):
                linha = registro.get('linha', i)
                status_aprovacao = determinar_status_aprovacao(aba, linha, super_status_data)
                
                if status_aprovacao == 'APROVADO':
                    aprovados_aba += 1
                else:
                    pendentes_aba += 1
            
            writer.writerow([f'Eventos_Aprovados_Aba_{aba.upper()}', aprovados_aba, f'Eventos aprovados na aba {aba}'])
            writer.writerow([f'Eventos_Pendentes_Aba_{aba.upper()}', pendentes_aba, f'Eventos pendentes na aba {aba}'])
    
    print(f"\n✅ Análise das planilhas concluída!")
    print(f"📁 Arquivos gerados:")
    print(f"   - planilhas_formadores_unicos_{timestamp}.csv")
    print(f"   - planilhas_coordenadores_{timestamp}.csv")
    print(f"   - planilhas_projetos_{timestamp}.csv")
    print(f"   - planilhas_municipios_{timestamp}.csv")
    print(f"   - planilhas_consolidado_{timestamp}.csv")
    print(f"   - planilhas_analise_detalhada_{timestamp}.csv")
    print(f"   - planilhas_eventos_aprovados_{timestamp}.csv")
    print(f"   - planilhas_eventos_pendentes_{timestamp}.csv")
    print(f"   - planilhas_analise_aprovacao_{timestamp}.csv")
    
    print(f"\n📊 RESUMO DOS DADOS DAS PLANILHAS:")
    print(f"   - Total de registros: {total_registros}")
    print(f"   - Formadores únicos: {len(formadores_planilhas)}")
    print(f"   - Coordenadores únicos: {len(coordenadores_planilhas)}")
    print(f"   - Projetos únicos: {len(projetos_planilhas)}")
    print(f"   - Municípios únicos: {len(municipios_planilhas)}")
    print(f"   - Tipos de evento únicos: {len(tipos_evento_planilhas)}")

if __name__ == "__main__":
    analisar_planilhas_originais()
