#!/usr/bin/env python
"""
Comparação entre Dados das Planilhas e Sistema Atual
================================================

Compara os dados extraídos das planilhas com os dados já importados no sistema
para identificar diferenças, lacunas e oportunidades de melhoria.
"""

import json
import os
import sys
import django
from datetime import datetime

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')
django.setup()

from core.models import Solicitacao, Usuario, Municipio, Projeto


class ComparadorDadosPlanilhasSistema:
    def __init__(self):
        self.dados_planilhas = None
        self.dados_sistema = None
        self.comparacao = {
            'totais': {},
            'por_status': {},
            'por_aba': {},
            'coordenadores': {},
            'municipios': {},
            'projetos': {},
            'lacunas': [],
            'recomendacoes': []
        }

    def executar_comparacao_completa(self):
        """Executa comparação completa entre planilhas e sistema"""

        print("🔍 COMPARAÇÃO: PLANILHAS vs SISTEMA ATUAL")
        print("=" * 60)

        # 1. Carregar dados das planilhas
        self._carregar_dados_planilhas()

        # 2. Carregar dados do sistema
        self._carregar_dados_sistema()

        # 3. Comparar totais
        self._comparar_totais()

        # 4. Comparar por status
        self._comparar_status()

        # 5. Comparar coordenadores
        self._comparar_coordenadores()

        # 6. Comparar municípios
        self._comparar_municipios()

        # 7. Comparar projetos
        self._comparar_projetos()

        # 8. Identificar lacunas
        self._identificar_lacunas()

        # 9. Gerar recomendações
        self._gerar_recomendacoes()

        # 10. Exibir resultado
        self._exibir_resultado_comparacao()

        return self.comparacao

    def _carregar_dados_planilhas(self):
        """Carrega dados tratados das planilhas"""

        arquivo_planilhas = 'dados/extraidos/dados_completos_tratados_20250919_153743.json'

        print(f"📊 Carregando dados das planilhas: {arquivo_planilhas}")

        try:
            with open(arquivo_planilhas, 'r', encoding='utf-8') as f:
                self.dados_planilhas = json.load(f)

            eventos = self.dados_planilhas.get('eventos_agenda', [])
            stats = self.dados_planilhas.get('estatisticas', {})

            print(f"✅ {len(eventos)} eventos das planilhas carregados")
            print(f"   Aprovados: {stats.get('por_status', {}).get('APROVADO', 0)}")
            print(f"   Pendentes: {stats.get('por_status', {}).get('PENDENTE', 0)}")

        except FileNotFoundError:
            print(f"❌ Arquivo das planilhas não encontrado")
            self.dados_planilhas = {'eventos_agenda': [], 'estatisticas': {}}

    def _carregar_dados_sistema(self):
        """Carrega dados atuais do sistema"""

        print(f"\\n🗄️ Carregando dados do sistema atual...")

        # Solicitações do sistema
        solicitacoes = Solicitacao.objects.all()

        self.dados_sistema = {
            'total_solicitacoes': solicitacoes.count(),
            'por_status': {},
            'coordenadores': {},
            'municipios': {},
            'projetos': {}
        }

        # Contar por status
        for status in ['PENDENTE', 'APROVADO', 'REPROVADO']:
            count = solicitacoes.filter(status=status).count()
            self.dados_sistema['por_status'][status] = count

        # Coordenadores únicos (excluindo admin)
        coordenadores_solicitacoes = (
            solicitacoes
            .exclude(usuario_solicitante__username='admin')
            .values('usuario_solicitante__first_name', 'usuario_solicitante__last_name', 'usuario_solicitante__username')
            .distinct()
        )

        for coord in coordenadores_solicitacoes:
            nome = f"{coord['usuario_solicitante__first_name']} {coord['usuario_solicitante__last_name']}".strip()
            if nome:
                count = solicitacoes.filter(
                    usuario_solicitante__username=coord['usuario_solicitante__username']
                ).count()
                self.dados_sistema['coordenadores'][nome] = count

        # Municípios únicos
        municipios_solicitacoes = (
            solicitacoes
            .values('municipio__nome')
            .distinct()
        )

        for municipio in municipios_solicitacoes:
            nome = municipio['municipio__nome']
            count = solicitacoes.filter(municipio__nome=nome).count()
            self.dados_sistema['municipios'][nome] = count

        # Projetos únicos
        projetos_solicitacoes = (
            solicitacoes
            .values('projeto__nome')
            .distinct()
        )

        for projeto in projetos_solicitacoes:
            nome = projeto['projeto__nome']
            count = solicitacoes.filter(projeto__nome=nome).count()
            self.dados_sistema['projetos'][nome] = count

        print(f"✅ {self.dados_sistema['total_solicitacoes']} solicitações do sistema carregadas")

    def _comparar_totais(self):
        """Compara totais entre planilhas e sistema"""

        total_planilhas = len(self.dados_planilhas.get('eventos_agenda', []))
        total_sistema = self.dados_sistema['total_solicitacoes']

        diferenca = total_planilhas - total_sistema

        self.comparacao['totais'] = {
            'planilhas': total_planilhas,
            'sistema': total_sistema,
            'diferenca': diferenca,
            'percentual_importado': round((total_sistema / total_planilhas) * 100, 1) if total_planilhas > 0 else 0
        }

    def _comparar_status(self):
        """Compara distribuição por status"""

        # Planilhas
        stats_planilhas = self.dados_planilhas.get('estatisticas', {}).get('por_status', {})

        # Sistema
        stats_sistema = self.dados_sistema['por_status']

        self.comparacao['por_status'] = {
            'planilhas': stats_planilhas,
            'sistema': stats_sistema,
            'diferenca_aprovados': stats_planilhas.get('APROVADO', 0) - stats_sistema.get('APROVADO', 0),
            'diferenca_pendentes': stats_planilhas.get('PENDENTE', 0) - stats_sistema.get('PENDENTE', 0)
        }

    def _comparar_coordenadores(self):
        """Compara coordenadores entre planilhas e sistema"""

        # Coordenadores das planilhas
        coordenadores_planilhas = self.dados_planilhas.get('estatisticas', {}).get('coordenadores_unicos', 0)

        # Coordenadores do sistema
        coordenadores_sistema = len(self.dados_sistema['coordenadores'])

        self.comparacao['coordenadores'] = {
            'total_planilhas': coordenadores_planilhas,
            'total_sistema': coordenadores_sistema,
            'diferenca': coordenadores_planilhas - coordenadores_sistema,
            'coordenadores_sistema': self.dados_sistema['coordenadores']
        }

    def _comparar_municipios(self):
        """Compara municípios entre planilhas e sistema"""

        municipios_planilhas = self.dados_planilhas.get('estatisticas', {}).get('municipios_unicos', 0)
        municipios_sistema = len(self.dados_sistema['municipios'])

        self.comparacao['municipios'] = {
            'total_planilhas': municipios_planilhas,
            'total_sistema': municipios_sistema,
            'diferenca': municipios_planilhas - municipios_sistema,
            'municipios_sistema': self.dados_sistema['municipios']
        }

    def _comparar_projetos(self):
        """Compara projetos entre planilhas e sistema"""

        # Contar projetos únicos das planilhas
        projetos_planilhas = set()
        for evento in self.dados_planilhas.get('eventos_agenda', []):
            projeto = evento.get('projeto', '').strip()
            if projeto:
                projetos_planilhas.add(projeto)

        projetos_sistema = len(self.dados_sistema['projetos'])

        self.comparacao['projetos'] = {
            'total_planilhas': len(projetos_planilhas),
            'total_sistema': projetos_sistema,
            'diferenca': len(projetos_planilhas) - projetos_sistema,
            'projetos_planilhas': list(projetos_planilhas),
            'projetos_sistema': self.dados_sistema['projetos']
        }

    def _identificar_lacunas(self):
        """Identifica lacunas principais"""

        lacunas = []

        # Lacuna de eventos
        diferenca_total = self.comparacao['totais']['diferenca']
        if diferenca_total > 0:
            lacunas.append({
                'tipo': 'EVENTOS_FALTANTES',
                'descricao': f'{diferenca_total} eventos das planilhas não estão no sistema',
                'impacto': 'ALTO',
                'prioridade': 1
            })

        # Lacuna de coordenadores
        admin_requests = Solicitacao.objects.filter(usuario_solicitante__username='admin').count()
        if admin_requests > 0:
            lacunas.append({
                'tipo': 'COORDENADORES_NAO_MAPEADOS',
                'descricao': f'{admin_requests} solicitações ainda estão com usuário admin',
                'impacto': 'MÉDIO',
                'prioridade': 2
            })

        # Lacuna de status
        diferenca_pendentes = self.comparacao['por_status']['diferenca_pendentes']
        if diferenca_pendentes > 0:
            lacunas.append({
                'tipo': 'STATUS_PENDENTES_FALTANTES',
                'descricao': f'{diferenca_pendentes} eventos pendentes das planilhas não refletidos no sistema',
                'impacto': 'MÉDIO',
                'prioridade': 3
            })

        self.comparacao['lacunas'] = lacunas

    def _gerar_recomendacoes(self):
        """Gera recomendações baseadas na comparação"""

        recomendacoes = []

        # Recomendação principal
        diferenca_total = self.comparacao['totais']['diferenca']
        if diferenca_total > 0:
            recomendacoes.append({
                'prioridade': 'ALTA',
                'acao': 'IMPORTACAO_COMPLETA',
                'descricao': f'Executar importação completa dos dados tratados para incluir {diferenca_total} eventos faltantes',
                'comando': 'python manage.py import_agenda_completa_tratada --verbose'
            })

        # Recomendação de limpeza
        if self.dados_sistema['total_solicitacoes'] > 0:
            recomendacoes.append({
                'prioridade': 'MÉDIA',
                'acao': 'LIMPEZA_E_REIMPORTACAO',
                'descricao': 'Fazer backup e limpeza completa, depois reimportar dados tratados',
                'comando': 'python manage.py import_agenda_completa_tratada --limpar-antes --verbose'
            })

        # Recomendação de correção de coordenadores
        admin_requests = Solicitacao.objects.filter(usuario_solicitante__username='admin').count()
        if admin_requests > 0:
            recomendacoes.append({
                'prioridade': 'MÉDIA',
                'acao': 'CORRECAO_COORDENADORES',
                'descricao': f'Aplicar correção de coordenadores nos {admin_requests} eventos com admin',
                'comando': 'python manage.py corrigir_coordenadores_solicitacoes --verbose'
            })

        self.comparacao['recomendacoes'] = recomendacoes

    def _exibir_resultado_comparacao(self):
        """Exibe resultado da comparação"""

        print("\\n" + "=" * 60)
        print("📊 RESULTADO DA COMPARAÇÃO")
        print("=" * 60)

        # Totais
        totais = self.comparacao['totais']
        print(f"📋 TOTAIS:")
        print(f"   Planilhas: {totais['planilhas']} eventos")
        print(f"   Sistema:   {totais['sistema']} eventos")
        print(f"   Diferença: {totais['diferenca']} eventos")
        print(f"   Importado: {totais['percentual_importado']}%")

        # Status
        status = self.comparacao['por_status']
        print(f"\\n📊 POR STATUS:")
        print(f"   Aprovados (Planilhas): {status['planilhas'].get('APROVADO', 0)}")
        print(f"   Aprovados (Sistema):   {status['sistema'].get('APROVADO', 0)}")
        print(f"   Pendentes (Planilhas): {status['planilhas'].get('PENDENTE', 0)}")
        print(f"   Pendentes (Sistema):   {status['sistema'].get('PENDENTE', 0)}")

        # Coordenadores
        coords = self.comparacao['coordenadores']
        print(f"\\n👥 COORDENADORES:")
        print(f"   Planilhas: {coords['total_planilhas']} únicos")
        print(f"   Sistema:   {coords['total_sistema']} únicos")

        # Lacunas
        lacunas = self.comparacao['lacunas']
        if lacunas:
            print(f"\\n⚠️ LACUNAS IDENTIFICADAS:")
            for lacuna in lacunas:
                print(f"   {lacuna['prioridade']}. {lacuna['descricao']} ({lacuna['impacto']})")

        # Recomendações
        recomendacoes = self.comparacao['recomendacoes']
        if recomendacoes:
            print(f"\\n🎯 RECOMENDAÇÕES:")
            for rec in recomendacoes:
                print(f"   {rec['prioridade']}: {rec['descricao']}")
                print(f"      Comando: {rec['comando']}")

    def salvar_comparacao(self):
        """Salva resultado da comparação"""

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        arquivo_comparacao = f'dados/relatorios/comparacao_planilhas_sistema_{timestamp}.json'

        with open(arquivo_comparacao, 'w', encoding='utf-8') as f:
            json.dump(self.comparacao, f, indent=2, ensure_ascii=False, default=str)

        print(f"\\n💾 Comparação salva: {arquivo_comparacao}")
        return arquivo_comparacao


def main():
    """Função principal"""

    comparador = ComparadorDadosPlanilhasSistema()

    # Executar comparação
    resultado = comparador.executar_comparacao_completa()

    # Salvar resultado
    arquivo_salvo = comparador.salvar_comparacao()

    print(f"\\n🏁 Comparação concluída!")
    print(f"📄 Relatório: {arquivo_salvo}")


if __name__ == "__main__":
    main()