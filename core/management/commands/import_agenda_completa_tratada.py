# core/management/commands/import_agenda_completa_tratada.py
"""
Comando para importar dados completos e tratados das planilhas
===========================================================

Importa TODOS os dados das planilhas com status corretos:
- Aba Super: Aprovados e Pendentes conforme coluna B
- Outras abas: Todas aprovadas
- Total: 2.275 eventos (100% das planilhas)
- 2.127 aprovados + 148 pendentes
"""

import json
import logging
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from core.models import (
    Usuario, Solicitacao, Municipio, Projeto, TipoEvento,
    SolicitacaoStatus, FormadoresSolicitacao, Formador
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Importa dados completos e tratados das planilhas com status corretos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--arquivo',
            type=str,
            help='Arquivo específico de dados tratados para importar',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula a importação sem fazer alterações no banco',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Mostra informações detalhadas',
        )
        parser.add_argument(
            '--limpar-antes',
            action='store_true',
            help='Remove todas as solicitações antes de importar (CUIDADO!)',
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.verbose = options['verbose']
        self.limpar_antes = options['limpar_antes']

        self.stdout.write("🚀 IMPORTAÇÃO COMPLETA DE DADOS TRATADOS")
        self.stdout.write("=" * 60)

        if self.dry_run:
            self.stdout.write(self.style.WARNING("MODO SIMULAÇÃO - Nenhuma alteração será feita"))

        if self.limpar_antes:
            self.stdout.write(self.style.WARNING("⚠️  MODO LIMPEZA ATIVADO - Dados atuais serão removidos"))

        try:
            # 1. Carregar dados tratados
            dados_tratados = self._carregar_dados_tratados(options.get('arquivo'))

            # 2. Fazer backup se necessário
            if self.limpar_antes and not self.dry_run:
                self._fazer_backup_dados_atuais()

            # 3. Processar importação
            self._processar_importacao_completa(dados_tratados)

        except Exception as e:
            raise CommandError(f'Erro durante importação: {e}')

    def _carregar_dados_tratados(self, arquivo_especifico=None):
        """Carrega dados tratados mais recentes"""

        if arquivo_especifico:
            arquivo_dados = arquivo_especifico
        else:
            # Usar arquivo mais recente
            arquivo_dados = 'dados/extraidos/dados_completos_tratados_20250919_153743.json'

        self.stdout.write(f"📁 Carregando dados de: {arquivo_dados}")

        try:
            with open(arquivo_dados, 'r', encoding='utf-8') as f:
                dados = json.load(f)

            eventos = dados.get('eventos_agenda', [])
            stats = dados.get('estatisticas', {})

            self.stdout.write(f"✅ {len(eventos)} eventos carregados")
            self.stdout.write(f"📊 Aprovados: {stats.get('por_status', {}).get('APROVADO', 0)}")
            self.stdout.write(f"📊 Pendentes: {stats.get('por_status', {}).get('PENDENTE', 0)}")

            return dados

        except FileNotFoundError:
            raise CommandError(f"Arquivo não encontrado: {arquivo_dados}")

    def _fazer_backup_dados_atuais(self):
        """Faz backup dos dados atuais antes da limpeza"""

        self.stdout.write("💾 Fazendo backup dos dados atuais...")

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Backup das solicitações atuais
        solicitacoes_atuais = list(Solicitacao.objects.all().values())

        backup_data = {
            'timestamp': timestamp,
            'total_solicitacoes': len(solicitacoes_atuais),
            'solicitacoes': solicitacoes_atuais,
            'metadata': {
                'motivo': 'Backup antes de importação completa tratada',
                'data_backup': timezone.now().isoformat()
            }
        }

        arquivo_backup = f'dados/backups/backup_antes_importacao_tratada_{timestamp}.json'

        with open(arquivo_backup, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False, default=str)

        self.stdout.write(f"✅ Backup salvo: {arquivo_backup}")

    def _processar_importacao_completa(self, dados_tratados):
        """Processa a importação completa dos dados tratados"""

        eventos = dados_tratados.get('eventos_agenda', [])

        if not self.dry_run:
            # Remover transaction.atomic() para persistir eventos importados mesmo com falhas
            # Limpar dados atuais se solicitado
            if self.limpar_antes:
                self._limpar_dados_atuais()

            # Contadores
            importados = 0
            aprovados = 0
            pendentes = 0
            erros = 0

            for i, evento in enumerate(eventos, 1):

                if self.verbose and i % 100 == 0:
                    self.stdout.write(f"📊 Processando evento {i}/{len(eventos)}")

                try:
                    solicitacao_criada = self._criar_solicitacao_tratada(evento)

                    if solicitacao_criada:
                        importados += 1

                        status = evento.get('status_calculado', 'APROVADO')
                        if status == 'APROVADO':
                            aprovados += 1
                        else:
                            pendentes += 1

                except Exception as e:
                    erros += 1
                    if self.verbose:
                        self.stdout.write(f"❌ Erro no evento {i}: {e}")

            # Resultado final
            self.stdout.write("\\n" + "=" * 60)
            self.stdout.write("📊 RESULTADO DA IMPORTAÇÃO COMPLETA")
            self.stdout.write("=" * 60)
            self.stdout.write(f"✅ {importados} eventos importados")
            self.stdout.write(f"✅ {aprovados} aprovados")
            self.stdout.write(f"⏳ {pendentes} pendentes")

            if erros > 0:
                self.stdout.write(f"❌ {erros} erros")

        else:
            # Modo simulação
            self.stdout.write("🔍 SIMULAÇÃO DA IMPORTAÇÃO:")

            eventos_por_status = {}
            eventos_por_aba = {}

            for evento in eventos:
                status = evento.get('status_calculado', 'APROVADO')
                eventos_por_status[status] = eventos_por_status.get(status, 0) + 1

                aba = evento.get('metadata_extracao', {}).get('aba_origem', 'Desconhecida')
                eventos_por_aba[aba] = eventos_por_aba.get(aba, 0) + 1

            self.stdout.write(f"📊 Por status:")
            for status, count in eventos_por_status.items():
                self.stdout.write(f"   {status}: {count} eventos")

            self.stdout.write(f"\\n📊 Por aba:")
            for aba, count in eventos_por_aba.items():
                self.stdout.write(f"   {aba}: {count} eventos")

    def _limpar_dados_atuais(self):
        """Remove dados atuais do sistema"""

        self.stdout.write("🗑️ Removendo dados atuais...")

        # Remover solicitações (cascata remove relacionamentos)
        count_solicitacoes = Solicitacao.objects.count()
        Solicitacao.objects.all().delete()

        self.stdout.write(f"✅ {count_solicitacoes} solicitações removidas")

    def _criar_solicitacao_tratada(self, evento):
        """Cria solicitação com dados tratados e status correto"""

        try:
            # Extrair dados básicos
            municipio_nome = evento.get('municipio', '').strip()
            projeto_nome = evento.get('projeto', '').strip()

            if not municipio_nome or not projeto_nome:
                return None

            # Buscar ou criar município
            municipio = self._buscar_ou_criar_municipio(municipio_nome)

            # Buscar ou criar projeto
            projeto = self._buscar_ou_criar_projeto(projeto_nome)

            # Buscar ou criar tipo evento
            tipo_evento = self._buscar_ou_criar_tipo_evento("Formação")

            # Determinar coordenador
            coordenador = self._determinar_coordenador(evento)

            # Extrair datas
            data_inicio, data_fim = self._extrair_datas(evento)

            if not data_inicio:
                return None

            # Determinar status correto
            status_calculado = evento.get('status_calculado', 'APROVADO')

            if status_calculado == 'APROVADO':
                status = SolicitacaoStatus.APROVADO
            else:
                status = SolicitacaoStatus.PENDENTE

            # Criar solicitação
            metadata_extracao = evento.get('metadata_extracao', {})
            colunas_e_s = metadata_extracao.get('colunas_e_s_extraidas', {})

            observacoes_completas = f"Evento extraído da aba {metadata_extracao.get('aba_origem', '')}\n\n{self._gerar_observacoes(colunas_e_s)}"

            # As datas já vêm com horários da função _extrair_datas
            # Apenas verificar se ambas existem
            if not data_inicio or not data_fim:
                return None

            data_fim_final = data_fim

            # Gerar título único para evitar duplicatas
            titulo_base = f"Formação - {projeto_nome}"
            titulo_evento = titulo_base

            # Verificar se já existe uma solicitação com mesmo título e data_inicio
            contador = 1
            while Solicitacao.objects.filter(titulo_evento=titulo_evento, data_inicio=data_inicio).exists():
                contador += 1
                titulo_evento = f"{titulo_base} ({contador})"

            solicitacao = Solicitacao.objects.create(
                titulo_evento=titulo_evento,
                municipio=municipio,
                projeto=projeto,
                tipo_evento=tipo_evento,
                data_inicio=data_inicio,
                data_fim=data_fim_final,
                usuario_solicitante=coordenador,
                status=status,
                observacoes=observacoes_completas.strip()
            )

            # Tentar associar formador se disponível
            self._associar_formador(solicitacao, evento)

            return solicitacao

        except Exception as e:
            if self.verbose:
                self.stdout.write(f"Erro ao criar solicitação: {e}")
            return None

    def _buscar_ou_criar_municipio(self, nome):
        """Busca ou cria município"""

        # Extrair UF se presente no nome
        if '-' in nome:
            partes = nome.split('-')
            nome_limpo = partes[0].strip()
            uf = partes[1].strip() if len(partes) > 1 else 'XX'
        else:
            nome_limpo = nome.strip()
            uf = 'XX'

        municipio, created = Municipio.objects.get_or_create(
            nome=nome_limpo,
            defaults={'uf': uf, 'ativo': True}
        )

        return municipio

    def _buscar_ou_criar_projeto(self, nome):
        """Busca ou cria projeto"""

        projeto, created = Projeto.objects.get_or_create(
            nome=nome,
            defaults={'ativo': True, 'descricao': f'Projeto {nome}'}
        )

        return projeto

    def _buscar_ou_criar_tipo_evento(self, nome):
        """Busca ou cria tipo de evento"""

        tipo_evento, created = TipoEvento.objects.get_or_create(
            nome=nome,
            defaults={'ativo': True, 'online': False}
        )

        return tipo_evento

    def _determinar_coordenador(self, evento):
        """Determina coordenador responsável"""

        # Tentar usar coordenador extraído
        coordenador_extraido = evento.get('coordenador_extraido')

        if coordenador_extraido:
            # Buscar usuário por nome similar
            coordenador = self._buscar_coordenador_por_nome(coordenador_extraido)
            if coordenador:
                return coordenador

        # Fallback: usar admin
        admin_user = Usuario.objects.filter(username='admin').first()
        return admin_user

    def _buscar_coordenador_por_nome(self, nome_coordenador):
        """Busca coordenador por nome similar"""

        # Implementar lógica similar ao comando de correção
        coordenadores = Usuario.objects.filter(cargo='coordenador', is_active=True)

        for coordenador in coordenadores:
            nome_completo = f"{coordenador.first_name} {coordenador.last_name}".strip()

            if nome_coordenador.lower() in nome_completo.lower():
                return coordenador

        return None

    def _extrair_datas(self, evento):
        """Extrai datas do evento combinando data + horários"""

        data_str = evento.get('data', '')
        if not data_str:
            return None, None

        try:
            # Converter data base
            if '/' in data_str:
                data_base = datetime.strptime(data_str, '%d/%m/%Y').date()
            else:
                data_base = datetime.strptime(data_str, '%Y-%m-%d').date()

            # Buscar horários nas colunas_e_s_extraidas
            metadata = evento.get('metadata_extracao', {})
            colunas_e_s = metadata.get('colunas_e_s_extraidas', {})

            hora_inicio_str = colunas_e_s.get('hora_inicio', '08:00:00')
            hora_fim_str = colunas_e_s.get('hora_fim', '17:00')

            # Normalizar horários
            if hora_inicio_str and ':' in hora_inicio_str:
                if len(hora_inicio_str.split(':')) == 2:
                    hora_inicio_str += ':00'
                hora_inicio = datetime.strptime(hora_inicio_str, '%H:%M:%S').time()
            else:
                hora_inicio = datetime.strptime('08:00:00', '%H:%M:%S').time()

            if hora_fim_str and ':' in hora_fim_str:
                if len(hora_fim_str.split(':')) == 2:
                    hora_fim_str += ':00'
                hora_fim = datetime.strptime(hora_fim_str, '%H:%M:%S').time()
            else:
                hora_fim = datetime.strptime('17:00:00', '%H:%M:%S').time()

            # Combinar data + hora
            data_inicio_completa = timezone.datetime.combine(data_base, hora_inicio)
            data_fim_completa = timezone.datetime.combine(data_base, hora_fim)

            # Verificar se data_fim < data_inicio (evento passa da meia-noite)
            if data_fim_completa <= data_inicio_completa:
                # Adicionar 1 dia à data_fim
                from datetime import timedelta
                data_fim_completa += timedelta(days=1)

            # Tornar timezone-aware
            data_inicio_completa = timezone.make_aware(data_inicio_completa)
            data_fim_completa = timezone.make_aware(data_fim_completa)

            return data_inicio_completa, data_fim_completa

        except (ValueError, AttributeError) as e:
            if self.verbose:
                self.stdout.write(f"Erro ao processar datas: {e}")
            return None, None

    def _gerar_observacoes(self, colunas_e_s):
        """Gera observações baseadas nas colunas E-S"""

        observacoes = []

        for campo, valor in colunas_e_s.items():
            if valor:
                observacoes.append(f"{campo}: {valor}")

        return "\\n".join(observacoes) if observacoes else ""

    def _associar_formador(self, solicitacao, evento):
        """Associa formador à solicitação se disponível"""

        metadata = evento.get('metadata_extracao', {})
        colunas = metadata.get('colunas_e_s_extraidas', {})

        nome_formador = colunas.get('formador')

        if nome_formador and nome_formador.strip():
            # Buscar usuário com formador_ativo=True por nome similar
            from django.contrib.auth import get_user_model
            User = get_user_model()

            primeiro_nome = nome_formador.split()[0]
            formador_usuario = User.objects.filter(
                formador_ativo=True,
                first_name__icontains=primeiro_nome
            ).first()

            if formador_usuario:
                FormadoresSolicitacao.objects.create(
                    solicitacao=solicitacao,
                    usuario=formador_usuario
                )