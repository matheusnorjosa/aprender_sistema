"""
Command para migrar dados de disponibilidade das planilhas para Django
Migra: Bloqueios, Eventos, Deslocamentos
"""

import json
import os
from datetime import date, datetime

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.dateparse import parse_date, parse_datetime

from core.models import (
    Aprovacao,
    Deslocamento,
    DisponibilidadeFormadores,
    Formador,
    LogAuditoria,
    Municipio,
    Projeto,
    Solicitacao,
    SolicitacaoStatus,
    TipoEvento,
    Usuario,
)


class Command(BaseCommand):
    help = "Migra dados de disponibilidade das planilhas extraídas"

    def add_arguments(self, parser):
        parser.add_argument(
            "--source-file",
            type=str,
            default="extracted_disponibilidade.json",
            help="Arquivo JSON com dados extraídos da planilha de disponibilidade",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Executa sem fazer alterações no banco",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("=== MIGRAÇÃO DE DISPONIBILIDADE ==="))

        source_file = options["source_file"]
        dry_run = options["dry_run"]

        if not os.path.exists(source_file):
            self.stdout.write(
                self.style.ERROR(f"Arquivo não encontrado: {source_file}")
            )
            return

        # Carregar dados
        with open(source_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.stdout.write(f"Arquivo carregado: {source_file}")
        self.stdout.write(f'Planilha: {data.get("planilha_nome", "N/A")}')
        self.stdout.write(f'Total abas: {data.get("total_abas", 0)}')

        # Estatísticas
        stats = {
            "bloqueios_criados": 0,
            "eventos_criados": 0,
            "deslocamentos_criados": 0,
            "erros": 0,
        }

        try:
            with transaction.atomic():
                # Migrar cada aba
                worksheets = data.get("worksheets", {})

                # 1. Migrar Bloqueios
                if "Bloqueios" in worksheets:
                    self.stdout.write("\\nMigrando Bloqueios...")
                    stats["bloqueios_criados"] = self.migrate_bloqueios(
                        worksheets["Bloqueios"], dry_run
                    )

                # 2. Migrar Eventos
                if "Eventos" in worksheets:
                    self.stdout.write("\\nMigrando Eventos...")
                    stats["eventos_criados"] = self.migrate_eventos(
                        worksheets["Eventos"], dry_run
                    )

                # 3. Migrar Deslocamentos
                if "DESLOCAMENTO" in worksheets:
                    self.stdout.write("\\nMigrando Deslocamentos...")
                    stats["deslocamentos_criados"] = self.migrate_deslocamentos(
                        worksheets["DESLOCAMENTO"], dry_run
                    )

                if dry_run:
                    raise transaction.TransactionManagementError("Dry run - rollback")

        except transaction.TransactionManagementError:
            if not dry_run:
                raise
            self.stdout.write(
                self.style.WARNING("DRY RUN - Nenhuma alteração foi feita")
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro durante migração: {str(e)}"))
            stats["erros"] += 1

        # Exibir estatísticas
        self.stdout.write(self.style.SUCCESS("\\n=== ESTATÍSTICAS ==="))
        self.stdout.write(f'Bloqueios criados: {stats["bloqueios_criados"]}')
        self.stdout.write(f'Eventos criados: {stats["eventos_criados"]}')
        self.stdout.write(f'Deslocamentos criados: {stats["deslocamentos_criados"]}')
        self.stdout.write(f'Erros encontrados: {stats["erros"]}')

        if dry_run:
            self.stdout.write(
                self.style.WARNING("MODO DRY RUN - Execute sem --dry-run para aplicar")
            )

    def migrate_bloqueios(self, worksheet_data, dry_run=False):
        """Migra dados de bloqueios para DisponibilidadeFormador"""
        records = worksheet_data.get("records", [])
        headers = worksheet_data.get("headers", [])

        self.stdout.write(f"Headers encontrados: {headers}")
        self.stdout.write(f"Total registros: {len(records)}")

        count = 0
        for record in records:
            try:
                if not record or not any(record.values()):
                    continue  # Pular registros vazios

                # Mapear campos
                usuario_nome = record.get("Usuário", "").strip()
                data_inicio = self.parse_date_field(record.get("Inicio", ""))
                data_fim = self.parse_date_field(record.get("Fim", ""))
                tipo_bloqueio = record.get("Tipo", "").strip()

                if not usuario_nome or not data_inicio or not data_fim:
                    continue

                # Buscar formador (não usuário direto)
                try:
                    # Primeiro buscar usuário
                    usuario = Usuario.objects.get(
                        first_name__icontains=(
                            usuario_nome.split()[0] if usuario_nome else ""
                        )
                    )
                    # Depois buscar formador vinculado
                    try:
                        formador = Formador.objects.get(usuario=usuario)
                    except Formador.DoesNotExist:
                        self.stdout.write(
                            f"Formador não encontrado para usuário: {usuario_nome}"
                        )
                        continue

                except Usuario.DoesNotExist:
                    self.stdout.write(f"Usuário não encontrado: {usuario_nome}")
                    continue
                except Usuario.MultipleObjectsReturned:
                    # Tentar busca mais específica
                    usuario = Usuario.objects.filter(
                        first_name__iexact=(
                            usuario_nome.split()[0] if usuario_nome else ""
                        )
                    ).first()
                    if not usuario:
                        continue
                    try:
                        formador = Formador.objects.get(usuario=usuario)
                    except Formador.DoesNotExist:
                        continue

                # Converter horas para TimeField
                from datetime import time

                hora_inicio = (
                    time(0, 0) if "total" in tipo_bloqueio.lower() else time(8, 0)
                )
                hora_fim = (
                    time(23, 59) if "total" in tipo_bloqueio.lower() else time(18, 0)
                )

                # Criar bloqueio
                if not dry_run:
                    bloqueio, created = DisponibilidadeFormadores.objects.get_or_create(
                        formador=formador,
                        data_bloqueio=data_inicio,
                        hora_inicio=hora_inicio,
                        hora_fim=hora_fim,
                        defaults={
                            "tipo_bloqueio": tipo_bloqueio,
                            "motivo": f"Migrado de planilha - Tipo: {tipo_bloqueio}",
                        },
                    )
                    if created:
                        count += 1
                else:
                    count += 1  # Para dry run

            except Exception as e:
                self.stdout.write(f"Erro ao processar bloqueio: {str(e)}")
                continue

        return count

    def migrate_eventos(self, worksheet_data, dry_run=False):
        """Migra dados de eventos para Solicitacao"""
        records = worksheet_data.get("records", [])
        headers = worksheet_data.get("headers", [])

        self.stdout.write(f"Headers: {headers}")
        self.stdout.write(f"Total registros: {len(records)}")

        count = 0
        for record in records:
            try:
                if not record or not any(record.values()):
                    continue

                # Mapear campos
                titulo = record.get("titulo", "").strip()
                municipio_nome = record.get("municipio", "").strip()
                data_evento = self.parse_date_field(record.get("data", ""))
                horario_inicio = record.get("inicio", "08:00")
                horario_fim = record.get("fim", "18:00")
                projeto_nome = record.get("projeto", "").strip()
                tipo_evento_nome = record.get("tipo", "").strip()

                if not titulo or not data_evento:
                    continue

                # Buscar/criar municipio
                municipio, _ = Municipio.objects.get_or_create(
                    nome=municipio_nome,
                    defaults={"uf": "CE"},  # Assumir Ceará como padrão
                )

                # Buscar/criar projeto
                projeto, _ = Projeto.objects.get_or_create(
                    nome=projeto_nome or "Projeto Migrado",
                    defaults={"descricao": "Migrado de planilha"},
                )

                # Buscar/criar tipo de evento
                tipo_evento, _ = TipoEvento.objects.get_or_create(
                    nome=tipo_evento_nome or "Evento Migrado",
                    defaults={"duracao_padrao": 8, "permite_online": True},
                )

                # Criar solicitação de evento
                if not dry_run:
                    solicitacao, created = Solicitacao.objects.get_or_create(
                        titulo=titulo,
                        data_evento=data_evento,
                        defaults={
                            "municipio": municipio,
                            "projeto": projeto,
                            "tipo_evento": tipo_evento,
                            "horario_inicio": horario_inicio,
                            "horario_fim": horario_fim,
                            "observacoes": "Migrado de planilha de disponibilidade",
                            "status": SolicitacaoStatus.APROVADO,  # Assumir aprovado
                            "usuario_solicitante": Usuario.objects.filter(
                                groups__name="admin"
                            ).first(),
                        },
                    )
                    if created:
                        count += 1
                else:
                    count += 1

            except Exception as e:
                self.stdout.write(f"Erro ao processar evento: {str(e)}")
                continue

        return count

    def migrate_deslocamentos(self, worksheet_data, dry_run=False):
        """Migra dados de deslocamentos"""
        records = worksheet_data.get("records", [])
        headers = worksheet_data.get("headers", [])

        self.stdout.write(f"Headers: {headers}")
        self.stdout.write(f"Total registros: {len(records)}")

        count = 0
        for record in records:
            try:
                if not record or not any(record.values()):
                    continue

                # Mapear campos básicos de deslocamento
                formador_nome = record.get("formador", "").strip()
                origem = record.get("origem", "").strip()
                destino = record.get("destino", "").strip()
                data_deslocamento = self.parse_date_field(record.get("data", ""))

                if not formador_nome or not data_deslocamento:
                    continue

                # Buscar formador
                try:
                    usuario = Usuario.objects.get(
                        first_name__icontains=formador_nome.split()[0]
                    )
                except Usuario.DoesNotExist:
                    continue

                # Buscar/criar municípios
                municipio_origem, _ = Municipio.objects.get_or_create(
                    nome=origem, defaults={"uf": "CE"}
                )
                municipio_destino, _ = Municipio.objects.get_or_create(
                    nome=destino, defaults={"uf": "CE"}
                )

                # Criar deslocamento
                if not dry_run:
                    deslocamento, created = Deslocamento.objects.get_or_create(
                        usuario_id=usuario.id,
                        data=data_deslocamento,
                        municipio_origem=municipio_origem,
                        municipio_destino=municipio_destino,
                        defaults={
                            "observacoes": "Migrado de planilha de disponibilidade"
                        },
                    )
                    if created:
                        count += 1
                else:
                    count += 1

            except Exception as e:
                self.stdout.write(f"Erro ao processar deslocamento: {str(e)}")
                continue

        return count

    def parse_date_field(self, date_str):
        """Parse date string in various formats"""
        if not date_str:
            return None

        # Tentar diferentes formatos
        formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y/%m/%d",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(str(date_str).strip(), fmt).date()
            except (ValueError, AttributeError):
                continue

        # Tentar parse automático do Django
        try:
            return parse_date(str(date_str).strip())
        except:
            return None

    def log_migration(self, action, details):
        """Log migration action"""
        LogAuditoria.objects.create(
            usuario=None,  # Sistema
            acao=action,
            modelo="Disponibilidade",
            detalhes=details,
        )
