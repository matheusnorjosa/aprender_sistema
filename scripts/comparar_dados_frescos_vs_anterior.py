#!/usr/bin/env python3
"""
Script para comparar dados frescos extraídos com a análise anterior
"""

import json
import os
from datetime import datetime
from collections import defaultdict

class ComparadorDados:
    def __init__(self):
        self.dados_frescos = {}
        self.dados_anteriores = {}
        self.comparacao = {
            'timestamp': datetime.now().isoformat(),
            'resumo': {},
            'detalhes': {},
            'discrepancias': [],
            'recomendacoes': []
        }
    
    def carregar_dados_frescos(self):
        """Carrega os dados frescos extraídos"""
        arquivo_frescos = 'dados_frescos_completos_20250919_223942.json'
        
        if not os.path.exists(arquivo_frescos):
            print(f"❌ Arquivo de dados frescos não encontrado: {arquivo_frescos}")
            return False
        
        with open(arquivo_frescos, 'r', encoding='utf-8') as f:
            self.dados_frescos = json.load(f)
        
        print(f"✅ Dados frescos carregados: {len(self.dados_frescos)} abas")
        return True
    
    def carregar_dados_anteriores(self):
        """Carrega os dados da análise anterior"""
        # Procurar arquivos de dados anteriores
        arquivos_anteriores = [
            'fonte_unica_dados/dados_finais_limpos.json',
            'dados_unificados/dados_unificados_finais.json',
            'dados_planilhas_originais/super_colunas_e_t_tratados.json'
        ]
        
        for arquivo in arquivos_anteriores:
            if os.path.exists(arquivo):
                with open(arquivo, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                    self.dados_anteriores[arquivo] = dados
                    print(f"✅ Dados anteriores carregados: {arquivo}")
        
        return len(self.dados_anteriores) > 0
    
    def comparar_abas_agenda(self):
        """Compara as abas da planilha de agenda"""
        print(f"\n📊 COMPARANDO ABAS DA AGENDA 2025")
        print("=" * 50)
        
        abas_agenda = ['super', 'acerta', 'outros', 'brincando', 'vidas']
        
        for aba in abas_agenda:
            chave_frescos = f'agenda_2025_{aba}'
            
            if chave_frescos in self.dados_frescos:
                dados_frescos = self.dados_frescos[chave_frescos]
                total_frescos = len(dados_frescos)
                
                print(f"\n📋 Aba: {aba.upper()}")
                print(f"  🔄 Dados frescos: {total_frescos} registros")
                
                # Analisar estrutura dos dados frescos
                if dados_frescos:
                    headers_frescos = list(dados_frescos[0].keys())
                    print(f"  📝 Colunas frescas: {len(headers_frescos)}")
                    
                    # Verificar colunas importantes
                    colunas_importantes = ['Aprovação', 'Municípios', 'projeto', 'Coordenador', 'Formador 1']
                    for coluna in colunas_importantes:
                        if coluna in headers_frescos:
                            valores_unicos = set()
                            for registro in dados_frescos[:100]:  # Amostra
                                if registro.get(coluna):
                                    valores_unicos.add(registro[coluna])
                            print(f"    ✅ {coluna}: {len(valores_unicos)} valores únicos (amostra)")
                        else:
                            print(f"    ❌ {coluna}: Não encontrada")
                
                # Comparar com dados anteriores se disponível
                self.comparar_com_anteriores(aba, dados_frescos)
    
    def comparar_com_anteriores(self, aba, dados_frescos):
        """Compara dados frescos com dados anteriores"""
        # Procurar dados correspondentes nos arquivos anteriores
        for arquivo_anterior, dados_anterior in self.dados_anteriores.items():
            if isinstance(dados_anterior, dict):
                # Procurar por chaves relacionadas à aba
                chaves_relacionadas = [k for k in dados_anterior.keys() if aba.lower() in k.lower()]
                
                if chaves_relacionadas:
                    for chave in chaves_relacionadas:
                        dados_anteriores_aba = dados_anterior[chave]
                        if isinstance(dados_anteriores_aba, list):
                            total_anteriores = len(dados_anteriores_aba)
                            total_frescos = len(dados_frescos)
                            
                            diferenca = total_frescos - total_anteriores
                            percentual = (diferenca / total_anteriores * 100) if total_anteriores > 0 else 0
                            
                            print(f"  📈 Comparação com {arquivo_anterior}:")
                            print(f"    🔄 Anteriores: {total_anteriores} registros")
                            print(f"    🆕 Frescos: {total_frescos} registros")
                            print(f"    📊 Diferença: {diferenca:+d} ({percentual:+.1f}%)")
                            
                            if abs(percentual) > 10:
                                self.comparacao['discrepancias'].append({
                                    'aba': aba,
                                    'arquivo_anterior': arquivo_anterior,
                                    'diferenca_percentual': percentual,
                                    'total_anteriores': total_anteriores,
                                    'total_frescos': total_frescos
                                })
    
    def analisar_qualidade_dados_frescos(self):
        """Analisa a qualidade dos dados frescos"""
        print(f"\n🔍 ANÁLISE DE QUALIDADE DOS DADOS FRESCOS")
        print("=" * 50)
        
        for chave, dados in self.dados_frescos.items():
            if not dados:
                continue
                
            print(f"\n📋 {chave}: {len(dados)} registros")
            
            # Analisar completude dos dados
            headers = list(dados[0].keys())
            campos_obrigatorios = ['Municípios', 'projeto', 'Coordenador']
            
            for campo in campos_obrigatorios:
                if campo in headers:
                    preenchidos = sum(1 for registro in dados if registro.get(campo, '').strip())
                    percentual = (preenchidos / len(dados) * 100) if dados else 0
                    print(f"  📊 {campo}: {preenchidos}/{len(dados)} ({percentual:.1f}%) preenchidos")
            
            # Analisar dados da coluna Aprovação (se existir)
            if 'Aprovação' in headers:
                aprovacoes = defaultdict(int)
                for registro in dados:
                    aprovacao = registro.get('Aprovação', '').strip().upper()
                    if aprovacao:
                        aprovacoes[aprovacao] += 1
                
                print(f"  ✅ Status de aprovação:")
                for status, count in aprovacoes.items():
                    percentual = (count / len(dados) * 100) if dados else 0
                    print(f"    {status}: {count} ({percentual:.1f}%)")
    
    def gerar_recomendacoes(self):
        """Gera recomendações baseadas na comparação"""
        print(f"\n💡 RECOMENDAÇÕES")
        print("=" * 50)
        
        # Analisar discrepâncias
        if self.comparacao['discrepancias']:
            print("⚠️ DISCREPÂNCIAS ENCONTRADAS:")
            for disc in self.comparacao['discrepancias']:
                print(f"  📊 {disc['aba']}: {disc['diferenca_percentual']:+.1f}% de diferença")
                if abs(disc['diferenca_percentual']) > 20:
                    self.comparacao['recomendacoes'].append(
                        f"Investigar grande diferença na aba {disc['aba']} ({disc['diferenca_percentual']:+.1f}%)"
                    )
        
        # Recomendações gerais
        total_frescos = sum(len(dados) for dados in self.dados_frescos.values())
        self.comparacao['recomendacoes'].extend([
            f"Total de {total_frescos} registros frescos extraídos com sucesso",
            "Dados frescos são mais atuais que os dados anteriores",
            "Considerar usar dados frescos como fonte principal",
            "Implementar extração automática regular dos dados"
        ])
        
        for i, rec in enumerate(self.comparacao['recomendacoes'], 1):
            print(f"  {i}. {rec}")
    
    def salvar_comparacao(self):
        """Salva o relatório de comparação"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        arquivo_comparacao = f"comparacao_dados_frescos_vs_anterior_{timestamp}.json"
        
        with open(arquivo_comparacao, 'w', encoding='utf-8') as f:
            json.dump(self.comparacao, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Relatório de comparação salvo: {arquivo_comparacao}")
        return arquivo_comparacao
    
    def executar_comparacao_completa(self):
        """Executa a comparação completa"""
        print("🔍 INICIANDO COMPARAÇÃO: DADOS FRESCOS vs ANÁLISE ANTERIOR")
        print("=" * 70)
        
        # Carregar dados
        if not self.carregar_dados_frescos():
            return False
        
        if not self.carregar_dados_anteriores():
            print("⚠️ Nenhum dado anterior encontrado para comparação")
        
        # Executar comparações
        self.comparar_abas_agenda()
        self.analisar_qualidade_dados_frescos()
        self.gerar_recomendacoes()
        
        # Salvar relatório
        arquivo_comparacao = self.salvar_comparacao()
        
        print("\n" + "=" * 70)
        print("✅ COMPARAÇÃO CONCLUÍDA COM SUCESSO!")
        print(f"📄 Relatório salvo: {arquivo_comparacao}")
        
        return True

if __name__ == "__main__":
    comparador = ComparadorDados()
    sucesso = comparador.executar_comparacao_completa()
    
    if sucesso:
        print("\n🎉 Análise comparativa concluída!")
        print("📋 Dados frescos extraídos e comparados com sucesso")
    else:
        print("\n❌ Falha na comparação dos dados")
