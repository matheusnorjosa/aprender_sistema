"""
Classe base para todos os commands de migração
"""

import json
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Type

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import models, transaction

from core.management.commands.utils.bulk_operations import bulk_ops
from core.management.commands.utils.json_loader import json_loader


class BaseMigrationCommand(BaseCommand, ABC):
    """
    Classe base para commands de migração com funcionalidades comuns:
    - Carregamento de dados JSON
    - Validação de dados
    - Operações em massa
    - Logging detalhado
    - Rollback automático
    - Métricas de performance
    """

    help = "Comando base para migração de dados"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = self.setup_logging()
        self.stats = {
            "total_records": 0,
            "processed": 0,
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None,
        }
        self.dry_run = False
        self.verbose = False

    def setup_logging(self) -> logging.Logger:
        """Configura logging específico para migração"""
        logger = logging.getLogger(f"migration.{self.__class__.__name__}")

        if not logger.handlers:
            # Handler para arquivo
            handler = logging.FileHandler(
                settings.BASE_DIR / "logs" / "migration.log", encoding="utf-8"
            )
            handler.setLevel(logging.INFO)

            # Format detalhado
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

            # Handler para console se em desenvolvimento
            if settings.DEBUG:
                console_handler = logging.StreamHandler()
                console_handler.setLevel(logging.INFO)
                console_handler.setFormatter(formatter)
                logger.addHandler(console_handler)

        logger.setLevel(logging.INFO)
        return logger

    def add_arguments(self, parser):
        """Argumentos comuns para todos os commands de migração"""
        parser.add_argument(
            "--source",
            type=str,
            help="Arquivo JSON fonte (ex: extracted_usuarios.json)",
        )

        parser.add_argument(
            "--worksheet", type=str, help="Nome da aba da planilha para processar"
        )

        parser.add_argument(
            "--batch-size",
            type=int,
            default=getattr(settings, "MIGRATION_BATCH_SIZE", 500),
            help="Tamanho do lote para processamento",
        )

        parser.add_argument(
            "--dry-run", action="store_true", help="Simula migração sem salvar dados"
        )

        parser.add_argument(
            "--validate-only",
            action="store_true",
            help="Apenas valida dados sem migrar",
        )

        parser.add_argument(
            "--force",
            action="store_true",
            help="Força migração mesmo com erros menores",
        )

        parser.add_argument("--verbose", action="store_true", help="Output detalhado")

    def handle(self, *args, **options):
        """Handler principal do command"""
        self.dry_run = options.get("dry_run", False)
        self.verbose = options.get("verbose", False)

        self.stats["start_time"] = datetime.now()

        try:
            # Log início
            self.logger.info(f"Iniciando {self.__class__.__name__}")
            self.logger.info(f"Opções: {options}")

            if options.get("validate_only"):
                return self.validate_data(options)

            if self.dry_run:
                self.stdout.write(
                    self.style.WARNING("MODO DRY RUN - Nenhum dado será salvo")
                )

            # Executar migração específica
            result = self.execute_migration(options)

            # Finalizar
            self.stats["end_time"] = datetime.now()
            self.print_final_stats()

            return result

        except Exception as e:
            self.logger.error(f"Erro na migração: {e}")
            raise CommandError(f"Migração falhou: {e}")

    def execute_migration(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executa a migração específica (implementado por subclasses)

        Args:
            options: Opções do command

        Returns:
            Dict com resultado da migração
        """
        source_file = options.get("source")
        if not source_file:
            raise CommandError("--source é obrigatório")

        # Validar arquivo fonte
        if not json_loader.validate_file_exists(source_file):
            raise CommandError(f"Arquivo fonte não encontrado: {source_file}")

        # Executar migração específica
        return self.migrate_data(source_file, options)

    @abstractmethod
    def migrate_data(self, source_file: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Implementa a lógica específica de migração (deve ser implementado pelas subclasses)

        Args:
            source_file: Arquivo JSON fonte
            options: Opções do command

        Returns:
            Dict com resultado da migração
        """
        pass

    def validate_data(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida dados sem migrar (pode ser sobrescrito pelas subclasses)

        Args:
            options: Opções do command

        Returns:
            Dict com resultado da validação
        """
        source_file = options.get("source")
        if not source_file:
            raise CommandError("--source é obrigatório para validação")

        self.stdout.write("Validando dados...")

        # Validação básica
        stats = json_loader.get_file_stats(source_file)

        self.stdout.write(f"Arquivo: {source_file}")
        self.stdout.write(f"Tamanho: {stats.get('size_mb', 0)} MB")
        self.stdout.write(f"Total de registros: {stats.get('total_records', 0)}")

        return {"status": "validated", "stats": stats}

    def load_records_as_dicts(
        self, source_file: str, worksheet_name: str
    ) -> List[Dict[str, str]]:
        """
        Carrega registros como dicionários

        Args:
            source_file: Arquivo JSON fonte
            worksheet_name: Nome da aba

        Returns:
            Lista de dicionários
        """
        try:
            records = json_loader.get_records_as_dicts(source_file, worksheet_name)
            self.stats["total_records"] = len(records)

            if self.verbose:
                self.stdout.write(
                    f"Carregados {len(records)} registros de {worksheet_name}"
                )

            return records

        except Exception as e:
            self.logger.error(f"Erro ao carregar registros: {e}")
            raise CommandError(f"Erro ao carregar dados: {e}")

    def transform_record(self, record: Dict[str, str]) -> Optional[models.Model]:
        """
        Transforma registro JSON em objeto Django (deve ser implementado pelas subclasses)

        Args:
            record: Dict com dados do registro

        Returns:
            Objeto do modelo Django ou None se deve ser pulado
        """
        raise NotImplementedError("Subclasses devem implementar transform_record")

    def bulk_create_objects(
        self,
        model_class: Type[models.Model],
        objects: List[models.Model],
        batch_size: int = None,
    ) -> Dict[str, int]:
        """
        Cria objetos em massa

        Args:
            model_class: Classe do modelo
            objects: Lista de objetos
            batch_size: Tamanho do lote

        Returns:
            Dict com estatísticas
        """
        if self.dry_run:
            return {
                "created": len(objects),
                "errors": 0,
                "total_processed": len(objects),
            }

        result = bulk_ops.bulk_create_safe(
            model_class, objects, batch_size, ignore_conflicts=True
        )

        self.stats["created"] += result["created"]
        self.stats["errors"] += result["errors"]

        return result

    def update_progress(self, current: int, total: int):
        """Atualiza progresso da migração"""
        percentage = (current / total) * 100 if total > 0 else 0

        if self.verbose:
            self.stdout.write(f"Progresso: {current}/{total} ({percentage:.1f}%)")

    def print_final_stats(self):
        """Imprime estatísticas finais"""
        duration = None
        if self.stats["start_time"] and self.stats["end_time"]:
            duration = self.stats["end_time"] - self.stats["start_time"]

        self.stdout.write(self.style.SUCCESS("\n=== ESTATÍSTICAS FINAIS ==="))
        self.stdout.write(f"Total de registros: {self.stats['total_records']}")
        self.stdout.write(f"Processados: {self.stats['processed']}")
        self.stdout.write(f"Criados: {self.stats['created']}")
        self.stdout.write(f"Atualizados: {self.stats['updated']}")
        self.stdout.write(f"Pulados: {self.stats['skipped']}")
        self.stdout.write(f"Erros: {self.stats['errors']}")

        if duration:
            self.stdout.write(f"Duração: {duration}")

        if self.stats["total_records"] > 0:
            success_rate = (
                (self.stats["created"] + self.stats["updated"])
                / self.stats["total_records"]
            ) * 100
            self.stdout.write(f"Taxa de sucesso: {success_rate:.1f}%")

        # Log estatísticas
        self.logger.info(f"Migração concluída: {self.stats}")

    def log_error(self, message: str, record: Dict[str, Any] = None):
        """Log de erro com contexto"""
        self.stats["errors"] += 1
        error_msg = f"ERRO: {message}"

        if record:
            # Incluir alguns campos do record para contexto
            context = {
                k: v for k, v in record.items() if k in ["Nome", "Email", "CPF", "id"]
            }
            error_msg += f" | Contexto: {context}"

        self.logger.error(error_msg)

        if self.verbose:
            self.stdout.write(self.style.ERROR(error_msg))

    def log_success(self, message: str):
        """Log de sucesso"""
        self.logger.info(message)

        if self.verbose:
            self.stdout.write(self.style.SUCCESS(message))
