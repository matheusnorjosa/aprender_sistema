# core/management/commands/corrigir_status_solicitacoes.py
"""
Comando para corrigir os status das solicitações importadas baseado nos dados extraídos.

Este script:
1. Carrega os dados tratados das planilhas
2. Aplica o status correto conforme a lógica por aba:
   - Aba Super: Coluna B ("SIM" = APROVADO, "NÃO" = PENDENTE)
   - Outras abas: Todas APROVADO
3. Atualiza as 2.257 solicitações com o status correto

Resultado esperado: 2.113 APROVADO + 144 PENDENTE
"""

import json
import logging
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from core.models import Solicitacao, SolicitacaoStatus

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Corrige status das solicitações baseado nos dados extraídos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula a correção sem fazer alterações no banco',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Mostra informações detalhadas',
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.verbose = options['verbose']

        self.stdout.write("🔧 CORREÇÃO DE STATUS DAS SOLICITAÇÕES")
        self.stdout.write("=" * 60)

        if self.dry_run:
            self.stdout.write(self.style.WARNING("MODO SIMULAÇÃO - Nenhuma alteração será feita"))

        try:
            # 1. Carregar dados tratados das planilhas
            dados_tratados = self._carregar_dados_tratados()

            # 2. Corrigir status das solicitações
            self._corrigir_status_solicitacoes(dados_tratados)

        except Exception as e:
            raise CommandError(f'Erro durante correção: {e}')

    def _carregar_dados_tratados(self):
        """Carrega dados tratados das planilhas"""
        self.stdout.write("📋 Carregando dados tratados...")

        arquivo_dados = 'dados/extraidos/dados_completos_tratados_20250919_153743.json'

        try:
            with open(arquivo_dados, 'r', encoding='utf-8') as f:
                dados = json.load(f)
        except FileNotFoundError:
            raise CommandError(f"Arquivo não encontrado: {arquivo_dados}")

        eventos = dados.get('eventos_agenda', [])
        stats = dados.get('estatisticas', {})

        self.stdout.write(f"✅ {len(eventos)} eventos carregados")
        self.stdout.write(f"📊 Status esperado nos dados:")
        self.stdout.write(f"   Aprovados: {stats.get('por_status', {}).get('APROVADO', 0)}")
        self.stdout.write(f"   Pendentes: {stats.get('por_status', {}).get('PENDENTE', 0)}")

        return dados

    def _corrigir_status_solicitacoes(self, dados_tratados):
        """Corrige status das solicitações baseado nos dados tratados"""
        self.stdout.write("\n🔧 Iniciando correção de status...")

        eventos = dados_tratados.get('eventos_agenda', [])

        # Contar status atual das solicitações
        total_solicitacoes = Solicitacao.objects.count()
        self.stdout.write(f"📊 {total_solicitacoes} solicitações no sistema")

        if not self.dry_run:
            with transaction.atomic():
                corrigidas_aprovado = 0
                corrigidas_pendente = 0
                nao_encontradas = 0

                def normalizar_texto(texto):
                    """Normaliza texto para matching"""
                    if not texto:
                        return ''
                    return texto.strip().upper().replace(' - ', ' ').replace('-', ' ')

                # Processar cada evento dos dados tratados
                for i, evento in enumerate(eventos, 1):

                    if self.verbose and i % 500 == 0:
                        self.stdout.write(f"📊 Processando evento {i}/{len(eventos)}")

                    # Extrair dados do evento
                    municipio_evento = normalizar_texto(evento.get('municipio', ''))
                    projeto_evento = normalizar_texto(evento.get('projeto', ''))
                    data_evento = evento.get('data', '')
                    status_calculado = evento.get('status_calculado', 'APROVADO')

                    # Converter data para formato do sistema
                    try:
                        if '/' in data_evento:
                            data_obj = datetime.strptime(data_evento, '%d/%m/%Y').date()
                        else:
                            data_obj = datetime.strptime(data_evento, '%Y-%m-%d').date()
                        data_str = data_obj.strftime('%Y-%m-%d')
                    except (ValueError, AttributeError):
                        continue

                    # Buscar solicitação correspondente no sistema (otimizado)
                    try:
                        # Buscar por data primeiro (mais específico)
                        solicitacoes_data = Solicitacao.objects.select_related("municipio", "projeto", "tipo_evento", "solicitante").prefetch_related("formadores").filter(data_inicio__date=data_obj)

                        solicitacao_encontrada = None
                        for solicitacao in solicitacoes_data:
                            municipio_sol = normalizar_texto(solicitacao.municipio.nome)
                            projeto_sol = normalizar_texto(solicitacao.projeto.nome)

                            # Match exato
                            if (municipio_evento == municipio_sol and projeto_evento == projeto_sol):
                                solicitacao_encontrada = solicitacao
                                break

                        # Match flexível por palavra-chave do município
                        if not solicitacao_encontrada:
                            municipio_palavras = municipio_evento.split()
                            if municipio_palavras:
                                palavra_principal = municipio_palavras[0]
                                for solicitacao in solicitacoes_data:
                                    municipio_sol = normalizar_texto(solicitacao.municipio.nome)
                                    if palavra_principal in municipio_sol:
                                        solicitacao_encontrada = solicitacao
                                        break
                    except Exception:
                        continue

                    if solicitacao_encontrada:
                        # Aplicar status correto
                        if status_calculado == 'APROVADO':
                            novo_status = SolicitacaoStatus.APROVADO
                            corrigidas_aprovado += 1
                        else:
                            novo_status = SolicitacaoStatus.PENDENTE
                            corrigidas_pendente += 1

                        # Atualizar apenas se diferente
                        if solicitacao_encontrada.status != novo_status:
                            solicitacao_encontrada.status = novo_status
                            solicitacao_encontrada.save()

                            if self.verbose and (corrigidas_aprovado + corrigidas_pendente) <= 10:
                                self.stdout.write(f"  ✅ {solicitacao_encontrada.municipio.nome} → {novo_status}")
                    else:
                        nao_encontradas += 1
                        if self.verbose and nao_encontradas <= 5:
                            self.stdout.write(f"  ❌ Não encontrado: {municipio_evento} - {data_evento}")

                # Resultado final
                self.stdout.write(f"\n✅ Status corrigidos:")
                self.stdout.write(f"   → APROVADO: {corrigidas_aprovado} solicitações")
                self.stdout.write(f"   → PENDENTE: {corrigidas_pendente} solicitações")
                self.stdout.write(f"⚠️  Não encontradas: {nao_encontradas}")

                # Verificar distribuição final
                aprovados_final = Solicitacao.objects.select_related("municipio", "projeto", "tipo_evento", "solicitante").prefetch_related("formadores").filter(status=SolicitacaoStatus.APROVADO).count()
                pendentes_final = Solicitacao.objects.select_related("municipio", "projeto", "tipo_evento", "solicitante").prefetch_related("formadores").filter(status=SolicitacaoStatus.PENDENTE).count()

                self.stdout.write(f"\n📊 DISTRIBUIÇÃO FINAL:")
                self.stdout.write(f"   APROVADO: {aprovados_final}")
                self.stdout.write(f"   PENDENTE: {pendentes_final}")
                self.stdout.write(f"   TOTAL: {aprovados_final + pendentes_final}")

        else:
            # Modo simulação
            self.stdout.write("🔍 SIMULAÇÃO DA CORREÇÃO:")

            status_counts = {}
            for evento in eventos:
                status = evento.get('status_calculado', 'APROVADO')
                status_counts[status] = status_counts.get(status, 0) + 1

            self.stdout.write(f"  → APROVADO: {status_counts.get('APROVADO', 0)} solicitações")
            self.stdout.write(f"  → PENDENTE: {status_counts.get('PENDENTE', 0)} solicitações")

    def _log_resultado(self, aprovados, pendentes):
        """Log dos resultados para auditoria"""
        resultado = {
            'timestamp': timezone.now().isoformat(),
            'status_aprovado': aprovados,
            'status_pendente': pendentes,
            'total_corrigido': aprovados + pendentes,
            'dry_run': self.dry_run
        }

        arquivo_log = f"logs/correcao_status_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        try:
            with open(arquivo_log, 'w', encoding='utf-8') as f:
                json.dump(resultado, f, indent=2, ensure_ascii=False)

            self.stdout.write(f"📝 Log salvo em: {arquivo_log}")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Não foi possível salvar log: {e}"))