"""
Utilitários para operações em massa otimizadas
"""

import logging
from typing import Any, Dict, Iterator, List, Type

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction

logger = logging.getLogger(__name__)


class BulkOperationsManager:
    """Gerenciador de operações em massa otimizadas"""

    def __init__(self, batch_size: int = None):
        self.batch_size = batch_size or getattr(
            settings, "BULK_CREATE_BATCH_SIZE", 1000
        )
        self.stats = {"created": 0, "updated": 0, "skipped": 0, "errors": 0}

    def chunked(
        self, iterable: List[Any], chunk_size: int = None
    ) -> Iterator[List[Any]]:
        """
        Divide lista em chunks menores

        Args:
            iterable: Lista para dividir
            chunk_size: Tamanho de cada chunk

        Yields:
            Chunks da lista
        """
        chunk_size = chunk_size or self.batch_size

        for i in range(0, len(iterable), chunk_size):
            yield iterable[i : i + chunk_size]

    def bulk_create_safe(
        self,
        model_class: Type[models.Model],
        objects: List[models.Model],
        batch_size: int = None,
        ignore_conflicts: bool = False,
    ) -> Dict[str, int]:
        """
        Bulk create com tratamento de erros

        Args:
            model_class: Classe do modelo Django
            objects: Lista de objetos para criar
            batch_size: Tamanho do lote
            ignore_conflicts: Se deve ignorar conflitos

        Returns:
            Dict com estatísticas
        """
        batch_size = batch_size or self.batch_size
        created_count = 0
        error_count = 0

        for chunk in self.chunked(objects, batch_size):
            try:
                with transaction.atomic():
                    # Validar objetos antes de criar
                    valid_objects = []
                    for obj in chunk:
                        try:
                            obj.full_clean()
                            valid_objects.append(obj)
                        except ValidationError as e:
                            logger.warning(f"Objeto inválido ignorado: {e}")
                            error_count += 1

                    if valid_objects:
                        created_objects = model_class.objects.bulk_create(
                            valid_objects,
                            batch_size=batch_size,
                            ignore_conflicts=ignore_conflicts,
                        )
                        created_count += len(created_objects)
                        logger.info(
                            f"Criados {len(created_objects)} objetos {model_class.__name__}"
                        )

            except Exception as e:
                logger.error(f"Erro no bulk_create para {model_class.__name__}: {e}")
                error_count += len(chunk)

        self.stats["created"] += created_count
        self.stats["errors"] += error_count

        return {
            "created": created_count,
            "errors": error_count,
            "total_processed": len(objects),
        }

    def bulk_update_safe(
        self, objects: List[models.Model], fields: List[str], batch_size: int = None
    ) -> Dict[str, int]:
        """
        Bulk update com tratamento de erros

        Args:
            objects: Lista de objetos para atualizar
            fields: Campos a serem atualizados
            batch_size: Tamanho do lote

        Returns:
            Dict com estatísticas
        """
        from bulk_update.helper import bulk_update

        batch_size = batch_size or self.batch_size
        updated_count = 0
        error_count = 0

        for chunk in self.chunked(objects, batch_size):
            try:
                with transaction.atomic():
                    bulk_update(chunk, update_fields=fields, batch_size=batch_size)
                    updated_count += len(chunk)
                    logger.info(f"Atualizados {len(chunk)} objetos")

            except Exception as e:
                logger.error(f"Erro no bulk_update: {e}")
                error_count += len(chunk)

        self.stats["updated"] += updated_count
        self.stats["errors"] += error_count

        return {
            "updated": updated_count,
            "errors": error_count,
            "total_processed": len(objects),
        }

    def bulk_create_or_update(
        self,
        model_class: Type[models.Model],
        objects: List[models.Model],
        update_fields: List[str],
        match_field: str = "id",
        batch_size: int = None,
    ) -> Dict[str, int]:
        """
        Bulk create or update baseado em campo único

        Args:
            model_class: Classe do modelo
            objects: Lista de objetos
            update_fields: Campos para update
            match_field: Campo para matching
            batch_size: Tamanho do lote

        Returns:
            Dict com estatísticas
        """
        batch_size = batch_size or self.batch_size
        created_count = 0
        updated_count = 0
        error_count = 0

        for chunk in self.chunked(objects, batch_size):
            try:
                with transaction.atomic():
                    # Separar objetos novos vs existentes
                    match_values = [
                        getattr(obj, match_field)
                        for obj in chunk
                        if hasattr(obj, match_field)
                    ]

                    if match_values:
                        existing_objects = model_class.objects.filter(
                            **{f"{match_field}__in": match_values}
                        )
                        existing_matches = {
                            getattr(obj, match_field): obj for obj in existing_objects
                        }

                        objects_to_create = []
                        objects_to_update = []

                        for obj in chunk:
                            match_value = getattr(obj, match_field, None)
                            if match_value and match_value in existing_matches:
                                # Atualizar objeto existente
                                existing_obj = existing_matches[match_value]
                                for field in update_fields:
                                    setattr(existing_obj, field, getattr(obj, field))
                                objects_to_update.append(existing_obj)
                            else:
                                # Criar novo objeto
                                objects_to_create.append(obj)

                        # Executar operações
                        if objects_to_create:
                            result = self.bulk_create_safe(
                                model_class,
                                objects_to_create,
                                batch_size,
                                ignore_conflicts=True,
                            )
                            created_count += result["created"]

                        if objects_to_update:
                            result = self.bulk_update_safe(
                                objects_to_update, update_fields, batch_size
                            )
                            updated_count += result["updated"]
                    else:
                        # Todos são novos
                        result = self.bulk_create_safe(
                            model_class, chunk, batch_size, ignore_conflicts=True
                        )
                        created_count += result["created"]

            except Exception as e:
                logger.error(f"Erro no bulk_create_or_update: {e}")
                error_count += len(chunk)

        return {
            "created": created_count,
            "updated": updated_count,
            "errors": error_count,
            "total_processed": len(objects),
        }

    def get_stats(self) -> Dict[str, int]:
        """Retorna estatísticas acumuladas"""
        return self.stats.copy()

    def reset_stats(self):
        """Reseta estatísticas"""
        self.stats = {"created": 0, "updated": 0, "skipped": 0, "errors": 0}


# Instância global para uso nos commands
bulk_ops = BulkOperationsManager()
