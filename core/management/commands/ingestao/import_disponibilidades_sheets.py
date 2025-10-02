"""
Comando Canônico: Importação de Disponibilidades
================================================

Comando oficial para importação de disponibilidades dos formadores
do Google Sheets. Implementa regras de negócio específicas.

Author: Claude Code
Date: Janeiro 2025
"""

import csv
import hashlib
import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from backend.config.sheets_config import sheets_config
from core.models import (
    DisponibilidadeFormadores,
    LogAuditoria,
    MarcadorPlanilha,
    Usuario,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Importa disponibilidades dos formadores do Google Sheets (comando canônico)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--from',
            type=str,
            choices=['sheets', 'csv'],
            default='sheets',
            help='Fonte dos dados: sheets (Google Sheets) ou csv (arquivo local)'
        )
        parser.add_argument(
            '--csv-file',
            type=str,
            help='Caminho para arquivo CSV (quando --from=csv)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Execução de teste sem salvar no banco'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Limpar disponibilidades existentes antes da importação'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Mostrar informações detalhadas'
        )
        parser.add_argument(
            '--periodo',
            type=str,
            help='Período específico (YYYY-MM) para importar'
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.verbose = options['verbose']
        self.clear = options['clear']
        self.source = options['from']
        self.csv_file = options['csv_file']
        self.periodo = options['periodo']

        if self.verbose:
            logging.basicConfig(level=logging.DEBUG)

        self.stdout.write(
            self.style.SUCCESS('🚀 Iniciando importação canônica de disponibilidades...')
        )

        try:
            if self.source == 'sheets':
                self._import_from_sheets()
            elif self.source == 'csv':
                if not self.csv_file:
                    raise CommandError("--csv-file é obrigatório quando --from=csv")
                self._import_from_csv(self.csv_file)

            self.stdout.write(
                self.style.SUCCESS('✅ Importação de disponibilidades concluída com sucesso!')
            )

        except Exception as e:
            logger.error(f"Erro na importação de disponibilidades: {e}")
            raise CommandError(f"Erro na importação: {e}")

    def _import_from_sheets(self):
        """Importa disponibilidades do Google Sheets"""
        try:
            from core.services.google_sheets_service import google_sheets_service

            spreadsheet_id = sheets_config.get_spreadsheet_id('disponibilidade')
            abas = sheets_config.get_abas('disponibilidade')

            self.stdout.write(f"📊 Importando da planilha: {spreadsheet_id}")

            for aba_name, sheet_name in abas.items():
                self.stdout.write(f"📋 Processando aba: {sheet_name}")

                # Obter dados da aba
                data = google_sheets_service.get_worksheet_data(
                    spreadsheet_id, sheet_name
                )

                if not data:
                    self.stdout.write(
                        self.style.WARNING(f"⚠️  Aba '{sheet_name}' vazia ou inacessível")
                    )
                    continue

                self._process_availability_data(data, aba_name, f"sheets:{sheet_name}")

        except ImportError:
            raise CommandError(
                "Serviço Google Sheets não disponível. "
                "Use --from=csv com arquivo local."
            )

    def _import_from_csv(self, csv_file: str):
        """Importa disponibilidades de arquivo CSV"""
        try:
            with open(csv_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                data = list(reader)

            self.stdout.write(f"📄 Importando de arquivo: {csv_file}")
            self._process_availability_data(data, 'CSV', f"csv:{csv_file}")

        except FileNotFoundError:
            raise CommandError(f"Arquivo não encontrado: {csv_file}")
        except Exception as e:
            raise CommandError(f"Erro ao ler arquivo CSV: {e}")

    def _process_availability_data(self, data: List[Dict], aba_name: str, source: str):
        """Processa dados de disponibilidade"""
        if self.clear and not self.dry_run:
            self.stdout.write("🧹 Limpando disponibilidades existentes...")
            DisponibilidadeFormadores.objects.all().delete()

        created_count = 0
        updated_count = 0
        error_count = 0

        for row_num, row in enumerate(data, 1):
            try:
                result = self._create_or_update_availability(row, aba_name, source, row_num)
                if result == 'created':
                    created_count += 1
                elif result == 'updated':
                    updated_count += 1

            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f"❌ Erro na linha {row_num}: {e}")
                )
                if self.verbose:
                    logger.error(f"Erro linha {row_num}: {e}")

        # Log de auditoria
        if not self.dry_run:
            LogAuditoria.objects.create(
                usuario=None,  # Sistema
                acao='RF03',  # Importação de disponibilidades
                detalhes=f"Importação canônica: {created_count} criadas, {updated_count} atualizadas, {error_count} erros",
                origem=source
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"📊 Resultado: {created_count} criadas, {updated_count} atualizadas, {error_count} erros"
            )
        )

    def _create_or_update_availability(self, row: Dict, aba_name: str, source: str, row_num: int) -> str:
        """Cria ou atualiza uma disponibilidade"""
        # Extrair dados da linha (ajustar conforme estrutura da planilha)
        formador_nome = row.get('Formador', '').strip()
        data_str = row.get('Data', '').strip()
        periodo_inicio = row.get('Período Início', '').strip()
        periodo_fim = row.get('Período Fim', '').strip()
        disponivel = row.get('Disponível', '').strip().upper()
        observacoes = row.get('Observações', '').strip()

        if not formador_nome or not data_str:
            raise ValueError("Formador e Data são obrigatórios")

        # Buscar formador
        formador = self._get_formador(formador_nome)
        if not formador:
            raise ValueError(f"Formador não encontrado: {formador_nome}")

        # Processar data
        try:
            data_disponibilidade = datetime.strptime(data_str, '%d/%m/%Y').date()
        except:
            try:
                data_disponibilidade = datetime.strptime(data_str, '%Y-%m-%d').date()
            except:
                raise ValueError(f"Formato de data inválido: {data_str}")

        # Filtrar por período se especificado
        if self.periodo:
            periodo_date = datetime.strptime(self.periodo, '%Y-%m').date()
            if data_disponibilidade.year != periodo_date.year or data_disponibilidade.month != periodo_date.month:
                return 'skipped'

        # Processar horários
        hora_inicio, hora_fim = self._process_horarios(periodo_inicio, periodo_fim)

        # Determinar disponibilidade
        is_disponivel = disponivel in ['SIM', 'TRUE', '1', 'DISPONÍVEL']

        # Gerar hash único para idempotência
        external_hash = hashlib.sha256(
            f"{formador.id}|{data_disponibilidade}|{hora_inicio}|{hora_fim}".encode()
        ).hexdigest()

        # Verificar se já existe
        try:
            marcador = MarcadorPlanilha.objects.get(external_hash=external_hash)
            disponibilidade = marcador.disponibilidade
            action = 'updated'
        except MarcadorPlanilha.DoesNotExist:
            disponibilidade = None
            action = 'created'

        # Criar ou atualizar disponibilidade
        if not disponibilidade:
            disponibilidade = DisponibilidadeFormadores()

        disponibilidade.formador = formador
        disponibilidade.data = data_disponibilidade
        disponibilidade.hora_inicio = hora_inicio
        disponibilidade.hora_fim = hora_fim
        disponibilidade.disponivel = is_disponivel
        disponibilidade.observacoes = observacoes
        disponibilidade.origem = source

        # Salvar apenas se não for dry-run
        if not self.dry_run:
            with transaction.atomic():
                disponibilidade.save()

                # Criar marcador de planilha
                MarcadorPlanilha.objects.get_or_create(
                    external_hash=external_hash,
                    defaults={
                        'disponibilidade': disponibilidade,
                        'gid': str(row_num),
                        'linha': row_num,
                        'origem_aba': aba_name,
                        'origem': source
                    }
                )

        if self.verbose:
            status = "Disponível" if is_disponivel else "Indisponível"
            self.stdout.write(f"✅ {action.title()}: {formador_nome} - {data_str} ({status})")

        return action

    def _get_formador(self, nome: str) -> Optional[Usuario]:
        """Busca formador pelo nome"""
        if not nome:
            return None

        # Buscar por primeiro nome
        primeiro_nome = nome.split()[0]
        try:
            return Usuario.objects.get(first_name__icontains=primeiro_nome)
        except Usuario.DoesNotExist:
            return None

    def _process_horarios(self, periodo_inicio: str, periodo_fim: str) -> Tuple[str, str]:
        """Processa horários de início e fim"""
        # Horários padrão se não especificados
        hora_inicio = "08:00"
        hora_fim = "17:00"

        if periodo_inicio:
            try:
                # Tentar diferentes formatos
                if ':' in periodo_inicio:
                    hora_inicio = periodo_inicio
                else:
                    # Assumir formato HHMM
                    hora_inicio = f"{periodo_inicio[:2]}:{periodo_inicio[2:]}"
            except:
                pass

        if periodo_fim:
            try:
                # Tentar diferentes formatos
                if ':' in periodo_fim:
                    hora_fim = periodo_fim
                else:
                    # Assumir formato HHMM
                    hora_fim = f"{periodo_fim[:2]}:{periodo_fim[2:]}"
            except:
                pass

        return hora_inicio, hora_fim
