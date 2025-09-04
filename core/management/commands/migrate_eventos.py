"""
Command para migrar eventos da planilha DISPONIBILIDADE para Django
"""

import json
from datetime import datetime
from typing import Any, Dict, List

from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from core.management.commands.migration.base_migration import BaseMigrationCommand
from core.models import Formador, Municipio, Projeto, Solicitacao, TipoEvento


class Command(BaseMigrationCommand):
    """
    Migra eventos da planilha DISPONIBILIDADE para o modelo Django

    Uso:
        python manage.py migrate_eventos --source=extracted_disponibilidade.json
        python manage.py migrate_eventos --source=extracted_disponibilidade.json --worksheet=Eventos --dry-run
        python manage.py migrate_eventos --source=extracted_disponibilidade.json --batch-size=100
    """

    help = "Migra eventos da planilha DISPONIBILIDADE para Django"

    def add_arguments(self, parser):
        super().add_arguments(parser)

        parser.add_argument(
            "--skip-validation",
            action="store_true",
            help="Pula validações de conflito (apenas para migração inicial)",
        )

        parser.add_argument(
            "--default-project",
            type=str,
            default="GERAL",
            help="Projeto padrão para eventos sem projeto especificado",
        )

    def migrate_data(self, source_file: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migra dados de eventos da planilha DISPONIBILIDADE

        Args:
            source_file: Arquivo JSON da planilha extraída
            options: Opções do command

        Returns:
            Dict com resultado da migração
        """
        self.logger.info(f"Iniciando migração de eventos de {source_file}")

        # Carregar dados
        data = self.load_json_data(source_file)
        if not data or "worksheets" not in data:
            raise CommandError(f"Dados inválidos em {source_file}")

        # Focar na aba EVENTOS
        eventos_data = data["worksheets"].get("Eventos", {})
        if not eventos_data or "data" not in eventos_data:
            self.logger.warning("Aba 'Eventos' não encontrada ou vazia")
            return self.stats

        eventos = eventos_data["data"]
        headers = eventos_data.get("headers", [])

        self.logger.info(f"Encontrados {len(eventos)} eventos para migrar")
        self.stats["total_records"] = len(eventos)

        # Processar eventos
        for i, evento_row in enumerate(eventos, 1):
            try:
                if self.verbose:
                    self.logger.info(f"Processando evento {i}/{len(eventos)}")

                evento_data = self.parse_evento_row(evento_row, headers, options)

                if evento_data:
                    if not self.dry_run:
                        self.create_or_update_evento(evento_data, options)

                    self.stats["processed"] += 1

                else:
                    self.stats["skipped"] += 1
                    if self.verbose:
                        self.logger.info(f"Evento {i} pulado (dados insuficientes)")

            except Exception as e:
                self.stats["errors"] += 1
                self.logger.error(f"Erro processando evento {i}: {e}")
                if self.verbose:
                    self.logger.exception(e)

        return self.stats

    def parse_evento_row(
        self, row: List, headers: List, options: Dict
    ) -> Dict[str, Any]:
        """
        Converte linha da planilha em dados estruturados do evento

        Args:
            row: Linha de dados da planilha
            headers: Cabeçalhos da planilha
            options: Opções do command

        Returns:
            Dict com dados do evento ou None se inválido
        """
        if len(row) < 6:
            return None

        try:
            # Mapear campos baseado na estrutura identificada na análise
            # ['SIM', 'SIM', 'Amigos do Bem', '1', 'Presencial', '10/03/2025', ...]

            controle = row[0] if len(row) > 0 else ""
            aprovacao = row[1] if len(row) > 1 else ""
            municipio_nome = row[2] if len(row) > 2 else ""
            encontro = row[3] if len(row) > 3 else ""
            modalidade = row[4] if len(row) > 4 else "Presencial"
            data_str = row[5] if len(row) > 5 else ""

            # Validações básicas
            if not municipio_nome or not data_str:
                return None

            # Processar data
            data_evento = self.parse_date_string(data_str)
            if not data_evento:
                return None

            # Determinar status baseado na aprovação
            if aprovacao == "SIM":
                status = "APROVADO"
            elif aprovacao == "FALSE" or aprovacao == "NÃO":
                status = "REPROVADO"
            else:
                status = "PENDENTE"

            return {
                "municipio_nome": municipio_nome,
                "data_inicio": data_evento,
                "data_fim": data_evento.replace(hour=17),  # Padrão 8h-17h
                "modalidade": modalidade,
                "titulo": f"Evento {encontro} - {municipio_nome}",
                "status": status,
                "encontro": encontro,
                "controle": controle,
                "projeto_nome": options.get("default_project", "GERAL"),
            }

        except Exception as e:
            self.logger.error(f"Erro parseando linha do evento: {e}")
            return None

    def parse_date_string(self, date_str: str):
        """
        Converte string de data para datetime

        Args:
            date_str: String da data (formato DD/MM/YYYY ou similar)

        Returns:
            datetime object ou None se inválido
        """
        if not date_str or not isinstance(date_str, str):
            return None

        # Tentar diferentes formatos
        formats = ["%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%m/%d/%Y"]

        for fmt in formats:
            try:
                date_obj = datetime.strptime(date_str, fmt)
                # Assumir horário padrão 8:00
                return timezone.make_aware(
                    date_obj.replace(hour=8, minute=0, second=0),
                    timezone.get_current_timezone(),
                )
            except ValueError:
                continue

        self.logger.warning(f"Formato de data não reconhecido: {date_str}")
        return None

    def create_or_update_evento(self, evento_data: Dict[str, Any], options: Dict):
        """
        Cria ou atualiza evento no Django

        Args:
            evento_data: Dados do evento
            options: Opções do command
        """
        try:
            # Buscar ou criar município
            municipio, created = Municipio.objects.get_or_create(
                nome=evento_data["municipio_nome"], defaults={"ativo": True}
            )

            # Buscar ou criar projeto
            projeto, created = Projeto.objects.get_or_create(
                nome=evento_data["projeto_nome"], defaults={"ativo": True}
            )

            # Buscar ou criar tipo de evento
            tipo_evento, created = TipoEvento.objects.get_or_create(
                nome=evento_data["modalidade"], defaults={"ativo": True}
            )

            # Criar solicitação
            solicitacao_data = {
                "titulo": evento_data["titulo"],
                "data_inicio": evento_data["data_inicio"],
                "data_fim": evento_data["data_fim"],
                "municipio": municipio,
                "projeto": projeto,
                "tipo_evento": tipo_evento,
                "modalidade": evento_data["modalidade"],
                "status": evento_data["status"],
                "observacoes": f"Migrado da planilha - Encontro: {evento_data['encontro']}, Controle: {evento_data['controle']}",
            }

            # Verificar se já existe
            existing = Solicitacao.objects.filter(
                titulo=evento_data["titulo"],
                data_inicio=evento_data["data_inicio"],
                municipio=municipio,
            ).first()

            if existing:
                # Atualizar
                for key, value in solicitacao_data.items():
                    setattr(existing, key, value)
                existing.save()
                self.stats["updated"] += 1
                if self.verbose:
                    self.logger.info(f"Evento atualizado: {evento_data['titulo']}")
            else:
                # Criar novo
                solicitacao = Solicitacao.objects.create(**solicitacao_data)
                self.stats["created"] += 1
                if self.verbose:
                    self.logger.info(f"Evento criado: {evento_data['titulo']}")

        except Exception as e:
            self.stats["errors"] += 1
            self.logger.error(
                f"Erro criando evento {evento_data.get('titulo', 'desconhecido')}: {e}"
            )
            raise
