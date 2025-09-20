# core/management/commands/validar_dados_finais.py
"""
Comando para validação final da integridade dos dados importados.

Este script:
1. Valida a integridade dos dados importados
2. Compara com os dados originais das planilhas
3. Gera relatório completo de qualidade
4. Identifica problemas restantes
"""

import json
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from core.models import (
    Solicitacao, Usuario, Municipio, Projeto, TipoEvento,
    FormadoresSolicitacao, SolicitacaoStatus
)


class Command(BaseCommand):
    help = 'Validação final da integridade dos dados importados'

    def add_arguments(self, parser):
        parser.add_argument(
            '--salvar-relatorio',
            action='store_true',
            help='Salva relatório em arquivo JSON',
        )

    def handle(self, *args, **options):
        self.salvar_relatorio = options['salvar_relatorio']

        self.stdout.write("🔍 VALIDAÇÃO FINAL DA INTEGRIDADE DOS DADOS")
        self.stdout.write("=" * 60)

        resultado_validacao = self._executar_validacao_completa()

        if self.salvar_relatorio:
            self._salvar_relatorio(resultado_validacao)

    def _executar_validacao_completa(self):
        """Executa validação completa do sistema"""

        resultado = {
            'timestamp': datetime.now().isoformat(),
            'solicitacoes': {},
            'usuarios': {},
            'estrutura': {},
            'formadores': {},
            'qualidade': {},
            'comparacao_planilhas': {},
            'problemas': [],
            'recomendacoes': []
        }

        # 1. Validar solicitações
        self._validar_solicitacoes(resultado)

        # 2. Validar usuários e coordenadores
        self._validar_usuarios(resultado)

        # 3. Validar estrutura auxiliar
        self._validar_estrutura(resultado)

        # 4. Validar associações de formadores
        self._validar_formadores(resultado)

        # 5. Comparar com dados originais
        self._comparar_com_planilhas(resultado)

        # 6. Calcular métricas de qualidade
        self._calcular_qualidade(resultado)

        # 7. Identificar problemas e recomendações
        self._identificar_problemas(resultado)

        # 8. Exibir relatório
        self._exibir_relatorio(resultado)

        return resultado

    def _validar_solicitacoes(self, resultado):
        """Valida dados das solicitações"""

        total = Solicitacao.objects.count()
        aprovadas = Solicitacao.objects.filter(status=SolicitacaoStatus.APROVADO).count()
        pendentes = Solicitacao.objects.filter(status=SolicitacaoStatus.PENDENTE).count()

        # Solicitações com admin
        com_admin = Solicitacao.objects.filter(usuario_solicitante__username='admin').count()

        # Por projeto
        por_projeto = dict(
            Solicitacao.objects
            .values('projeto__nome')
            .annotate(count=Count('id'))
            .order_by('-count')
            .values_list('projeto__nome', 'count')[:10]
        )

        # Por coordenador (excluindo admin)
        coordenadores_query = (
            Solicitacao.objects
            .exclude(usuario_solicitante__username='admin')
            .values('usuario_solicitante__first_name', 'usuario_solicitante__last_name')
            .annotate(count=Count('id'))
            .order_by('-count')[:5]
        )

        coordenadores_formatados = {}
        for item in coordenadores_query:
            nome = f"{item['usuario_solicitante__first_name']} {item['usuario_solicitante__last_name']}".strip()
            coordenadores_formatados[nome] = item['count']

        resultado['solicitacoes'] = {
            'total': total,
            'aprovadas': aprovadas,
            'pendentes': pendentes,
            'com_admin': com_admin,
            'por_projeto': por_projeto,
            'por_coordenador': coordenadores_formatados,
            'percentual_aprovadas': round((aprovadas / total) * 100, 1) if total > 0 else 0,
            'percentual_pendentes': round((pendentes / total) * 100, 1) if total > 0 else 0
        }

    def _validar_usuarios(self, resultado):
        """Valida usuários e coordenadores"""

        total_usuarios = Usuario.objects.count()
        coordenadores = Usuario.objects.filter(cargo='coordenador', is_active=True).count()
        formadores_ativos = Usuario.objects.filter(formador_ativo=True, is_active=True).count()

        # Usuários com eventos
        usuarios_com_eventos = Usuario.objects.filter(
            solicitacoes_criadas__isnull=False
        ).distinct().count()

        resultado['usuarios'] = {
            'total': total_usuarios,
            'coordenadores': coordenadores,
            'formadores_ativos': formadores_ativos,
            'usuarios_com_eventos': usuarios_com_eventos
        }

    def _validar_estrutura(self, resultado):
        """Valida estrutura auxiliar (municípios, projetos, tipos)"""

        municipios = Municipio.objects.count()
        projetos = Projeto.objects.count()
        tipos_evento = TipoEvento.objects.count()

        # Municípios com eventos
        municipios_com_eventos = Municipio.objects.filter(
            solicitacao__isnull=False
        ).distinct().count()

        # Projetos com eventos
        projetos_com_eventos = Projeto.objects.filter(
            solicitacao__isnull=False
        ).distinct().count()

        resultado['estrutura'] = {
            'municipios': municipios,
            'projetos': projetos,
            'tipos_evento': tipos_evento,
            'municipios_com_eventos': municipios_com_eventos,
            'projetos_com_eventos': projetos_com_eventos
        }

    def _validar_formadores(self, resultado):
        """Valida associações de formadores"""

        total_associacoes = FormadoresSolicitacao.objects.count()
        solicitacoes_com_formador = Solicitacao.objects.filter(
            formadoressolicitacao__isnull=False
        ).distinct().count()

        total_solicitacoes = Solicitacao.objects.count()
        percentual_com_formador = round(
            (solicitacoes_com_formador / total_solicitacoes) * 100, 1
        ) if total_solicitacoes > 0 else 0

        # Formadores mais ativos
        formadores_query = (
            FormadoresSolicitacao.objects
            .values('usuario__first_name', 'usuario__last_name')
            .annotate(count=Count('id'))
            .order_by('-count')[:5]
        )

        formadores_formatados = {}
        for item in formadores_query:
            nome = f"{item['usuario__first_name']} {item['usuario__last_name']}".strip()
            formadores_formatados[nome] = item['count']

        resultado['formadores'] = {
            'total_associacoes': total_associacoes,
            'solicitacoes_com_formador': solicitacoes_com_formador,
            'percentual_com_formador': percentual_com_formador,
            'formadores_ativos': formadores_formatados
        }

    def _comparar_com_planilhas(self, resultado):
        """Compara com dados originais das planilhas"""

        try:
            with open('dados/extraidos/dados_completos_tratados_20250919_153743.json', 'r', encoding='utf-8') as f:
                dados_planilhas = json.load(f)

            stats_planilhas = dados_planilhas.get('estatisticas', {})

            total_planilhas = stats_planilhas.get('total_eventos', 0)
            aprovados_planilhas = stats_planilhas.get('por_status', {}).get('APROVADO', 0)
            pendentes_planilhas = stats_planilhas.get('por_status', {}).get('PENDENTE', 0)

            total_sistema = resultado['solicitacoes']['total']

            resultado['comparacao_planilhas'] = {
                'total_planilhas': total_planilhas,
                'total_sistema': total_sistema,
                'taxa_importacao': round((total_sistema / total_planilhas) * 100, 1) if total_planilhas > 0 else 0,
                'aprovados_planilhas': aprovados_planilhas,
                'aprovados_sistema': resultado['solicitacoes']['aprovadas'],
                'pendentes_planilhas': pendentes_planilhas,
                'pendentes_sistema': resultado['solicitacoes']['pendentes'],
                'eventos_perdidos': total_planilhas - total_sistema
            }

        except FileNotFoundError:
            resultado['comparacao_planilhas'] = {
                'erro': 'Arquivo de dados das planilhas não encontrado'
            }

    def _calcular_qualidade(self, resultado):
        """Calcula métricas de qualidade dos dados"""

        sol = resultado['solicitacoes']
        usr = resultado['usuarios']
        form = resultado['formadores']
        comp = resultado.get('comparacao_planilhas', {})

        # Score de qualidade (0-100)
        score_importacao = comp.get('taxa_importacao', 0)
        score_coordenadores = 100 - ((sol['com_admin'] / sol['total']) * 100) if sol['total'] > 0 else 0
        score_formadores = form['percentual_com_formador']
        score_estrutura = 100 if resultado['estrutura']['projetos_com_eventos'] > 0 else 0

        score_total = round((score_importacao + score_coordenadores + score_formadores + score_estrutura) / 4, 1)

        resultado['qualidade'] = {
            'score_total': score_total,
            'score_importacao': round(score_importacao, 1),
            'score_coordenadores': round(score_coordenadores, 1),
            'score_formadores': round(score_formadores, 1),
            'score_estrutura': round(score_estrutura, 1)
        }

    def _identificar_problemas(self, resultado):
        """Identifica problemas e gera recomendações"""

        problemas = []
        recomendacoes = []

        # Problemas identificados
        if resultado['solicitacoes']['com_admin'] > 0:
            problemas.append(f"{resultado['solicitacoes']['com_admin']} eventos ainda com usuário admin")

        taxa_importacao = resultado.get('comparacao_planilhas', {}).get('taxa_importacao', 0)
        if taxa_importacao < 100:
            eventos_perdidos = resultado.get('comparacao_planilhas', {}).get('eventos_perdidos', 0)
            problemas.append(f"{eventos_perdidos} eventos das planilhas não foram importados")

        if resultado['formadores']['percentual_com_formador'] < 80:
            problemas.append(f"Apenas {resultado['formadores']['percentual_com_formador']}% dos eventos têm formador associado")

        # Recomendações
        if resultado['solicitacoes']['com_admin'] > 0:
            recomendacoes.append("Executar novamente o comando de correção de coordenadores")

        if resultado['formadores']['percentual_com_formador'] < 90:
            recomendacoes.append("Melhorar associação de formadores às solicitações")

        if taxa_importacao < 99:
            recomendacoes.append("Investigar eventos não importados das planilhas")

        resultado['problemas'] = problemas
        resultado['recomendacoes'] = recomendacoes

    def _exibir_relatorio(self, resultado):
        """Exibe relatório completo"""

        sol = resultado['solicitacoes']
        usr = resultado['usuarios']
        est = resultado['estrutura']
        form = resultado['formadores']
        qual = resultado['qualidade']
        comp = resultado.get('comparacao_planilhas', {})

        self.stdout.write("\n📊 RELATÓRIO DE INTEGRIDADE DOS DADOS")
        self.stdout.write("=" * 60)

        # Solicitações
        self.stdout.write(f"\n📋 SOLICITAÇÕES:")
        self.stdout.write(f"   Total: {sol['total']}")
        self.stdout.write(f"   Aprovadas: {sol['aprovadas']} ({sol['percentual_aprovadas']}%)")
        self.stdout.write(f"   Pendentes: {sol['pendentes']} ({sol['percentual_pendentes']}%)")
        self.stdout.write(f"   Com admin: {sol['com_admin']}")

        # Top projetos
        self.stdout.write(f"\n🎯 TOP 5 PROJETOS:")
        for projeto, count in list(sol['por_projeto'].items())[:5]:
            self.stdout.write(f"   {projeto}: {count} eventos")

        # Top coordenadores
        self.stdout.write(f"\n👥 TOP 5 COORDENADORES:")
        for coord, count in list(sol['por_coordenador'].items())[:5]:
            self.stdout.write(f"   {coord}: {count} eventos")

        # Estrutura
        self.stdout.write(f"\n🏗️ ESTRUTURA:")
        self.stdout.write(f"   Usuários: {usr['total']} ({usr['coordenadores']} coordenadores)")
        self.stdout.write(f"   Municípios: {est['municipios']} ({est['municipios_com_eventos']} com eventos)")
        self.stdout.write(f"   Projetos: {est['projetos']} ({est['projetos_com_eventos']} com eventos)")

        # Formadores
        self.stdout.write(f"\n👨‍🏫 FORMADORES:")
        self.stdout.write(f"   Associações: {form['total_associacoes']}")
        self.stdout.write(f"   Eventos com formador: {form['solicitacoes_com_formador']} ({form['percentual_com_formador']}%)")

        # Comparação
        if 'erro' not in comp:
            self.stdout.write(f"\n📊 COMPARAÇÃO COM PLANILHAS:")
            self.stdout.write(f"   Planilhas: {comp['total_planilhas']} eventos")
            self.stdout.write(f"   Importados: {comp['total_sistema']} eventos")
            self.stdout.write(f"   Taxa de importação: {comp['taxa_importacao']}%")
            if comp['eventos_perdidos'] > 0:
                self.stdout.write(f"   Eventos perdidos: {comp['eventos_perdidos']}")

        # Qualidade
        self.stdout.write(f"\n🏆 SCORE DE QUALIDADE: {qual['score_total']}/100")
        self.stdout.write(f"   Importação: {qual['score_importacao']}/100")
        self.stdout.write(f"   Coordenadores: {qual['score_coordenadores']}/100")
        self.stdout.write(f"   Formadores: {qual['score_formadores']}/100")
        self.stdout.write(f"   Estrutura: {qual['score_estrutura']}/100")

        # Problemas
        if resultado['problemas']:
            self.stdout.write(f"\n⚠️ PROBLEMAS IDENTIFICADOS:")
            for problema in resultado['problemas']:
                self.stdout.write(f"   • {problema}")

        # Recomendações
        if resultado['recomendacoes']:
            self.stdout.write(f"\n💡 RECOMENDAÇÕES:")
            for recomendacao in resultado['recomendacoes']:
                self.stdout.write(f"   • {recomendacao}")

        # Status final
        if qual['score_total'] >= 90:
            self.stdout.write(f"\n✅ SISTEMA COM EXCELENTE QUALIDADE DE DADOS!")
        elif qual['score_total'] >= 75:
            self.stdout.write(f"\n👍 SISTEMA COM BOA QUALIDADE DE DADOS")
        else:
            self.stdout.write(f"\n⚠️ SISTEMA NECESSITA MELHORIAS NA QUALIDADE DOS DADOS")

    def _salvar_relatorio(self, resultado):
        """Salva relatório em arquivo"""

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        arquivo = f'dados/relatorios/validacao_final_{timestamp}.json'

        try:
            with open(arquivo, 'w', encoding='utf-8') as f:
                json.dump(resultado, f, indent=2, ensure_ascii=False, default=str)

            self.stdout.write(f"\n💾 Relatório salvo: {arquivo}")
        except Exception as e:
            self.stdout.write(f"\n❌ Erro ao salvar relatório: {e}")