"""
Command para migrar formações históricas da planilha CONTROLE (50K+ registros)
"""

import json
from datetime import datetime
from typing import Any, Dict, Generator, List

from django.db import transaction
from django.utils import timezone

from core.management.commands.migration.base_migration import BaseMigrationCommand
from core.models import Formador, Municipio, Projeto, Solicitacao, TipoEvento
from core.tasks import migrate_formacoes_task


class Command(BaseMigrationCommand):
    """
    Migra formações históricas da planilha CONTROLE para Django
    Processa 50.499 registros em batches para otimizar performance

    Uso:
        python manage.py migrate_formacoes --source=extracted_controle.json
        python manage.py migrate_formacoes --source=extracted_controle.json --batch-size=500 --async
        python manage.py migrate_formacoes --source=extracted_controle.json --worksheet=FORMAÇÕES --dry-run
    """

    help = (
        "Migra formações históricas da planilha CONTROLE (50K+ registros) para Django"
    )

    def add_arguments(self, parser):
        super().add_arguments(parser)

        parser.add_argument(
            "--async",
            action="store_true",
            help="Processa migração de forma assíncrona usando Celery",
        )

        parser.add_argument(
            "--start-offset",
            type=int,
            default=0,
            help="Offset inicial para continuar migração interrompida",
        )

        parser.add_argument(
            "--max-records",
            type=int,
            default=None,
            help="Número máximo de registros a processar (para testes)",
        )

        parser.add_argument(
            "--skip-existing",
            action="store_true",
            help="Pula registros que já existem no banco",
        )

    def migrate_data(self, source_file: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migra dados de formações históricas da planilha CONTROLE

        Args:
            source_file: Arquivo JSON da planilha extraída
            options: Opções do command

        Returns:
            Dict com resultado da migração
        """
        self.logger.info(f"Iniciando migração de formações históricas de {source_file}")

        # Carregar dados
        data = self.load_json_data(source_file)
        if not data or "worksheets" not in data:
            raise CommandError(f"Dados inválidos em {source_file}")

        # Encontrar aba de FORMAÇÕES (pode ter emoji ou nome similar)
        formacoes_data = None
        formacoes_aba = None

        for aba_nome, aba_data in data["worksheets"].items():
            if "FORMA" in aba_nome.upper() and len(aba_data.get("data", [])) > 1000:
                formacoes_data = aba_data
                formacoes_aba = aba_nome
                break

        if not formacoes_data:
            self.logger.error("Aba de FORMAÇÕES não encontrada ou vazia")
            return self.stats

        formacoes = formacoes_data["data"]
        headers = formacoes_data.get("headers", [])

        self.logger.info(
            f"Encontradas {len(formacoes)} formações na aba '{formacoes_aba}'"
        )

        # Aplicar filtros
        start_offset = options.get("start_offset", 0)
        max_records = options.get("max_records")

        if max_records:
            end_offset = min(start_offset + max_records, len(formacoes))
        else:
            end_offset = len(formacoes)

        formacoes_slice = formacoes[start_offset:end_offset]

        self.logger.info(
            f"Processando registros {start_offset} a {end_offset} ({len(formacoes_slice)} formações)"
        )
        self.stats["total_records"] = len(formacoes_slice)

        # Escolher método de processamento
        if options.get("async"):
            return self.process_async(formacoes_slice, headers, options, start_offset)
        else:
            return self.process_sync(formacoes_slice, headers, options)

    def process_async(
        self, formacoes: List, headers: List, options: Dict, start_offset: int
    ) -> Dict[str, Any]:
        """
        Processa formações de forma assíncrona usando Celery

        Args:
            formacoes: Lista de formações a processar
            headers: Cabeçalhos da planilha
            options: Opções do command
            start_offset: Offset inicial

        Returns:
            Dict com estatísticas da operação assíncrona
        """
        batch_size = options.get("batch_size", 500)

        self.logger.info(
            f"Iniciando processamento assíncrono com batches de {batch_size}"
        )

        # Dividir em batches e enviar para Celery
        task_ids = []

        for i in range(0, len(formacoes), batch_size):
            batch = formacoes[i : i + batch_size]
            current_offset = start_offset + i

            if not self.dry_run:
                # Enviar batch para Celery
                task = migrate_formacoes_task.delay(
                    batch_size=len(batch), offset=current_offset
                )
                task_ids.append(task.id)

                self.logger.info(
                    f"Batch {current_offset}-{current_offset + len(batch)} enviado para Celery (ID: {task.id})"
                )
            else:
                self.logger.info(
                    f"[DRY RUN] Batch {current_offset}-{current_offset + len(batch)} seria enviado para Celery"
                )

        self.stats["async_tasks"] = len(task_ids)
        self.stats["task_ids"] = task_ids

        self.logger.info(
            f"Processamento assíncrono iniciado: {len(task_ids)} tasks enviadas"
        )
        self.logger.info(
            "Use 'celery -A aprender_sistema flower' para monitorar progresso"
        )

        return self.stats

    def process_sync(
        self, formacoes: List, headers: List, options: Dict
    ) -> Dict[str, Any]:
        """
        Processa formações de forma síncrona

        Args:
            formacoes: Lista de formações a processar
            headers: Cabeçalhos da planilha
            options: Opções do command

        Returns:
            Dict com estatísticas do processamento
        """
        batch_size = options.get("batch_size", 500)

        self.logger.info(
            f"Iniciando processamento síncrono com batches de {batch_size}"
        )

        # Processar em batches para otimizar performance
        for i in range(0, len(formacoes), batch_size):
            batch = formacoes[i : i + batch_size]

            self.logger.info(
                f"Processando batch {i // batch_size + 1}: registros {i+1}-{i + len(batch)}"
            )

            if not self.dry_run:
                self.process_batch(batch, headers, options)
            else:
                self.stats["processed"] += len(batch)
                self.logger.info(
                    f"[DRY RUN] Batch de {len(batch)} formações seria processado"
                )

        return self.stats

    def process_batch(self, batch: List, headers: List, options: Dict):
        """
        Processa um batch de formações

        Args:
            batch: Lista de formações do batch
            headers: Cabeçalhos da planilha
            options: Opções do command
        """
        formacoes_to_create = []

        try:
            with transaction.atomic():
                for formacao_row in batch:
                    try:
                        formacao_data = self.parse_formacao_row(
                            formacao_row, headers, options
                        )

                        if formacao_data:
                            # Verificar se já existe (se solicitado)
                            if options.get("skip_existing"):
                                exists = Solicitacao.objects.filter(
                                    titulo=formacao_data["titulo"],
                                    data_inicio=formacao_data["data_inicio"],
                                ).exists()

                                if exists:
                                    self.stats["skipped"] += 1
                                    continue

                            formacoes_to_create.append(formacao_data)
                            self.stats["processed"] += 1

                        else:
                            self.stats["skipped"] += 1

                    except Exception as e:
                        self.stats["errors"] += 1
                        self.logger.error(f"Erro processando formação: {e}")
                        if self.verbose:
                            self.logger.exception(e)

                # Criar formações em massa
                if formacoes_to_create:
                    self.bulk_create_formacoes(formacoes_to_create)
                    self.stats["created"] += len(formacoes_to_create)

        except Exception as e:
            self.logger.error(f"Erro processando batch: {e}")
            raise

    def parse_formacao_row(
        self, row: List, headers: List, options: Dict
    ) -> Dict[str, Any]:
        """
        Converte linha da planilha em dados da formação

        Args:
            row: Linha de dados da planilha
            headers: Cabeçalhos da planilha
            options: Opções do command

        Returns:
            Dict com dados da formação ou None se inválido
        """
        if len(row) < 3:
            return None

        try:
            # Headers esperados: ['Delete', 'Update', 'Title', ...]
            # Adaptar baseado na estrutura real encontrada na análise

            title = row[2] if len(row) > 2 else ""

            if not title or title in ["Title", "DELETE", "UPDATE"]:
                return None

            # Extrair dados básicos (placeholder - ajustar conforme estrutura real)
            return {
                "titulo": title,
                "data_inicio": timezone.now(),  # TODO: extrair data real dos dados
                "data_fim": timezone.now(),
                "status": "CONCLUIDO",  # Formações históricas são concluídas
                "modalidade": "Presencial",  # Padrão
                "observacoes": "Migrado da planilha CONTROLE - Formação histórica",
            }

        except Exception as e:
            self.logger.error(f"Erro parseando linha da formação: {e}")
            return None

    def bulk_create_formacoes(self, formacoes_data: List[Dict[str, Any]]):
        """
        Cria formações em massa usando bulk_create

        Args:
            formacoes_data: Lista de dados das formações
        """
        try:
            # Preparar objetos para bulk_create
            formacoes_objects = []

            for data in formacoes_data:
                # TODO: Buscar referências necessárias (município, projeto, etc.)
                # Por enquanto, criar com dados mínimos

                solicitacao = Solicitacao(
                    titulo=data["titulo"],
                    data_inicio=data["data_inicio"],
                    data_fim=data["data_fim"],
                    status=data["status"],
                    modalidade=data["modalidade"],
                    observacoes=data["observacoes"],
                )
                formacoes_objects.append(solicitacao)

            # Bulk create
            if formacoes_objects:
                Solicitacao.objects.bulk_create(
                    formacoes_objects, batch_size=500, ignore_conflicts=True
                )

        except Exception as e:
            self.logger.error(f"Erro no bulk_create: {e}")
            raise
