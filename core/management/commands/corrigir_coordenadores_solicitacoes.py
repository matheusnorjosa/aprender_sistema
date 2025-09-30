# core/management/commands/corrigir_coordenadores_solicitacoes.py
"""
Comando para corrigir as solicitações importadas que ficaram com usuario_solicitante = admin
ao invés dos coordenadores reais que estavam na planilha original.

Este script:
1. Carrega os dados originais da planilha
2. Cria mapeamento entre nomes da planilha e usuários do sistema
3. Atualiza as 1.915 solicitações com o coordenador correto
"""

import json
import logging
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from core.models import Usuario, Solicitacao, Municipio, Projeto, TipoEvento

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Corrige coordenadores das solicitações importadas'

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

        self.stdout.write("🔧 CORREÇÃO DE COORDENADORES DAS SOLICITAÇÕES")
        self.stdout.write("=" * 60)

        if self.dry_run:
            self.stdout.write(self.style.WARNING("MODO SIMULAÇÃO - Nenhuma alteração será feita"))

        try:
            # 1. Carregar dados da planilha original
            coordenadores_planilha = self._carregar_dados_planilha()

            # 2. Criar mapeamento planilha → usuário sistema
            mapeamento = self._criar_mapeamento_coordenadores(coordenadores_planilha)

            # 3. Corrigir solicitações
            self._corrigir_solicitacoes(mapeamento)

        except Exception as e:
            raise CommandError(f'Erro durante correção: {e}')

    def _carregar_dados_planilha(self):
        """Carrega coordenadores dos dados tratados mais recentes"""
        self.stdout.write("📋 Carregando dados tratados das planilhas...")

        arquivo_dados = 'dados/extraidos/dados_completos_tratados_20250919_153743.json'

        try:
            with open(arquivo_dados, 'r', encoding='utf-8') as f:
                dados = json.load(f)
        except FileNotFoundError:
            raise CommandError(f"Arquivo não encontrado: {arquivo_dados}")

        # Extrair eventos com coordenador dos dados tratados
        eventos_com_coordenador = []
        coordenadores_unicos = set()

        for evento in dados['eventos_agenda']:
            # Usar coordenador_extraido dos dados tratados
            coordenador = evento.get('coordenador_extraido')
            if coordenador and coordenador.strip():
                coord_limpo = coordenador.strip()
                coordenadores_unicos.add(coord_limpo)

                eventos_com_coordenador.append({
                    'coordenador': coord_limpo,
                    'municipio': evento.get('municipio', ''),
                    'data': evento.get('data', ''),
                    'projeto': evento.get('projeto', ''),
                    'aba': evento.get('aba', ''),
                    'status_calculado': evento.get('status_calculado', ''),
                    'metadata_extracao': evento.get('metadata_extracao', {}),
                    'dados_completos': evento.get('dados_completos', [])
                })

        self.stdout.write(f"✅ {len(eventos_com_coordenador)} eventos com coordenador identificado")
        self.stdout.write(f"✅ {len(coordenadores_unicos)} coordenadores únicos na planilha")

        if self.verbose:
            for coord in sorted(coordenadores_unicos):
                self.stdout.write(f"  • {coord}")

        return eventos_com_coordenador

    def _criar_mapeamento_coordenadores(self, eventos_planilha):
        """Cria mapeamento entre nomes da planilha e usuários do sistema"""
        self.stdout.write("\n🔄 Criando mapeamento coordenador planilha → usuário sistema...")

        # Extrair coordenadores únicos da planilha
        coordenadores_planilha = set()
        for evento in eventos_planilha:
            coordenadores_planilha.add(evento['coordenador'])

        # Buscar usuários coordenadores no sistema
        usuarios_coordenadores = Usuario.objects.select_related("municipio", "projeto").prefetch_related("groups", "user_permissions").filter(
            cargo='coordenador',
            is_active=True
        )

        # Criar mapeamento inteligente
        mapeamento = {}

        # Mapeamento automático baseado em nomes similares
        for coord_planilha in coordenadores_planilha:
            melhor_match = None

            # Tentar match exato primeiro
            for usuario in usuarios_coordenadores:
                nome_completo = usuario.nome_completo.lower()
                first_name = usuario.first_name.lower() if usuario.first_name else ''

                if coord_planilha.lower() in nome_completo or first_name in coord_planilha.lower():
                    melhor_match = usuario
                    break

            # Mapeamentos específicos baseados na análise dos dados tratados
            mapeamentos_especificos = {
                'Laís Aline': 'laís.aline',
                'Rafael Rabelo': 'rafael.rabelo',
                'Bruno Teles': 'coordenacao10',
                'Daniele Cristina': 'daniele.cristina',
                'Beatriz Helena': 'coordenacao40',
                'Beatriz Helena Castelo de Andrade Furtado': 'coordenacao40',
                'Ellen Damares': 'coordenacao41',
                'Aurea Lucia': 'coordenacao42',
                'Maria Nadir': 'coordenacao50',
                'Eulina Carmem Santiago de Oliveira': 'coordenacao30',
                'Valdemir Silva Santos': 'coordenacao20',
                'Ana Paula': 'coordenacao15',
                'Amanda': 'coordenacao25',
                'Elienai Oliveira': 'coordenacao35',
            }

            # Usar mapeamento específico se disponível
            if coord_planilha in mapeamentos_especificos:
                username = mapeamentos_especificos[coord_planilha]
                try:
                    usuario = Usuario.objects.get(username=username)
                    melhor_match = usuario
                except Usuario.DoesNotExist:
                    pass

            if melhor_match:
                mapeamento[coord_planilha] = melhor_match
                if self.verbose:
                    self.stdout.write(f"  ✅ {coord_planilha} → {melhor_match.nome_completo} ({melhor_match.username})")
            else:
                self.stdout.write(
                    self.style.WARNING(f"  ⚠️  {coord_planilha} → NÃO ENCONTRADO")
                )

        self.stdout.write(f"✅ {len(mapeamento)} coordenadores mapeados de {len(coordenadores_planilha)} total")

        return mapeamento

    def _corrigir_solicitacoes(self, mapeamento):
        """Corrige as solicitações com os coordenadores corretos"""
        self.stdout.write("\n🔧 Iniciando correção das solicitações...")

        # Buscar solicitações do admin (importadas incorretamente)
        admin_user = Usuario.objects.select_related("municipio", "projeto").prefetch_related("groups", "user_permissions").filter(username='admin').first()
        if not admin_user:
            raise CommandError("Usuário admin não encontrado")

        solicitacoes_admin = Solicitacao.objects.select_related("municipio", "projeto", "tipo_evento", "solicitante").prefetch_related("formadores").filter(usuario_solicitante=admin_user)
        total_solicitacoes = solicitacoes_admin.count()

        self.stdout.write(f"📊 {total_solicitacoes} solicitações para corrigir")

        if not self.dry_run:
            with transaction.atomic():
                corrigidas = 0
                nao_mapeadas = 0

                # Carregar eventos tratados para correlação
                arquivo_dados = 'dados/extraidos/dados_completos_tratados_20250919_153743.json'
                with open(arquivo_dados, 'r', encoding='utf-8') as f:
                    dados = json.load(f)

                # Criar lista de eventos da planilha para matching flexível
                eventos_planilha = []
                for evento in dados['eventos_agenda']:
                    coordenador = evento.get('coordenador_extraido')
                    if coordenador and coordenador.strip():
                        eventos_planilha.append({
                            'coordenador': coordenador.strip(),
                            'municipio': evento.get('municipio', '').strip(),
                            'data': evento.get('data', '').strip(),
                            'projeto': evento.get('projeto', '').strip(),
                            'status_calculado': evento.get('status_calculado', ''),
                            'evento': evento
                        })

                def normalizar_texto(texto):
                    """Normaliza texto para matching flexível"""
                    if not texto:
                        return ''
                    return texto.strip().upper().replace(' - ', ' ').replace('-', ' ')

                # Processar cada solicitação
                for solicitacao in solicitacoes_admin:
                    data_str = solicitacao.data_inicio.strftime('%d/%m/%Y')
                    municipio_sol = normalizar_texto(solicitacao.municipio.nome)
                    projeto_sol = normalizar_texto(solicitacao.projeto.nome)

                    evento_encontrado = None

                    # Tentativa 1: Match exato
                    for evento_planilha in eventos_planilha:
                        municipio_plan = normalizar_texto(evento_planilha['municipio'])
                        projeto_plan = normalizar_texto(evento_planilha['projeto'])
                        data_plan = evento_planilha['data']

                        if (municipio_sol == municipio_plan and
                            data_str == data_plan and
                            projeto_sol == projeto_plan):
                            evento_encontrado = evento_planilha
                            break

                    # Tentativa 2: Match por município e data (projeto flexível)
                    if not evento_encontrado:
                        for evento_planilha in eventos_planilha:
                            municipio_plan = normalizar_texto(evento_planilha['municipio'])
                            data_plan = evento_planilha['data']

                            if (municipio_sol == municipio_plan and data_str == data_plan):
                                evento_encontrado = evento_planilha
                                break

                    # Tentativa 3: Match por município usando palavras chave
                    if not evento_encontrado:
                        municipio_palavras = municipio_sol.split()
                        if municipio_palavras:
                            palavra_principal = municipio_palavras[0]  # Primeira palavra (cidade)

                            for evento_planilha in eventos_planilha:
                                municipio_plan = normalizar_texto(evento_planilha['municipio'])
                                data_plan = evento_planilha['data']

                                if (palavra_principal in municipio_plan and data_str == data_plan):
                                    evento_encontrado = evento_planilha
                                    break

                    if evento_encontrado:
                        coordenador_planilha = evento_encontrado['coordenador']

                        if coordenador_planilha in mapeamento:
                            novo_usuario = mapeamento[coordenador_planilha]
                            solicitacao.usuario_solicitante = novo_usuario
                            solicitacao.save()
                            corrigidas += 1

                            if self.verbose and corrigidas <= 10:
                                municipio_match = evento_encontrado['municipio']
                                self.stdout.write(f"  ✅ {solicitacao.municipio.nome} ({municipio_match}) → {novo_usuario.first_name} {novo_usuario.last_name}")
                        else:
                            nao_mapeadas += 1
                            if self.verbose and nao_mapeadas <= 5:
                                self.stdout.write(f"  ⚠️  Coordenador '{coordenador_planilha}' não mapeado para {solicitacao.municipio.nome}")
                    else:
                        nao_mapeadas += 1
                        if self.verbose and nao_mapeadas <= 5:
                            self.stdout.write(f"  ❌ Não encontrado: {solicitacao.municipio.nome} - {data_str} - {solicitacao.projeto.nome}")

                self.stdout.write(f"✅ {corrigidas} solicitações corrigidas")
                self.stdout.write(f"⚠️  {nao_mapeadas} solicitações não puderam ser mapeadas")

        else:
            self.stdout.write("🔍 SIMULAÇÃO - As seguintes correções seriam feitas:")
            # Mostrar algumas simulações
            count = 0
            for coord_planilha, usuario in mapeamento.items():
                if count < 5:
                    self.stdout.write(f"  • Eventos de '{coord_planilha}' → {usuario.nome_completo}")
                    count += 1

            if len(mapeamento) > 5:
                self.stdout.write(f"  ... e mais {len(mapeamento)-5} mapeamentos")

    def _log_resultado(self, total_corrigidas, total_nao_mapeadas):
        """Log dos resultados para auditoria"""
        resultado = {
            'timestamp': timezone.now().isoformat(),
            'total_corrigidas': total_corrigidas,
            'total_nao_mapeadas': total_nao_mapeadas,
            'dry_run': self.dry_run
        }

        arquivo_log = f"logs/correcao_coordenadores_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        try:
            with open(arquivo_log, 'w', encoding='utf-8') as f:
                json.dump(resultado, f, indent=2, ensure_ascii=False)

            self.stdout.write(f"📝 Log salvo em: {arquivo_log}")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Não foi possível salvar log: {e}"))