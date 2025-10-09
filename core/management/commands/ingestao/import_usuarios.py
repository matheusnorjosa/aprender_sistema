"""
Comando Canônico: Importação de Usuários
========================================

Comando oficial para importação de usuários do Google Sheets.
Implementa regras de negócio específicas e validações.

Author: Claude Code
Date: Janeiro 2025
"""

import csv
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from backend.config.sheets_config import sheets_config
from core.models import LogAuditoria, Setor, Usuario

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Importa usuários do Google Sheets (comando canônico)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--from",
            type=str,
            choices=["sheets", "csv"],
            default="sheets",
            help="Fonte dos dados: sheets (Google Sheets) ou csv (arquivo local)",
        )
        parser.add_argument(
            "--csv-file", type=str, help="Caminho para arquivo CSV (quando --from=csv)"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Execução de teste sem salvar no banco",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Limpar usuários existentes antes da importação",
        )
        parser.add_argument(
            "--verbose", action="store_true", help="Mostrar informações detalhadas"
        )

    def handle(self, *args, **options):
        self.dry_run = options["dry_run"]
        self.verbose = options["verbose"]
        self.clear = options["clear"]
        self.source = options["from"]
        self.csv_file = options["csv_file"]

        if self.verbose:
            logging.basicConfig(level=logging.DEBUG)

        self.stdout.write(
            self.style.SUCCESS("🚀 Iniciando importação canônica de usuários...")
        )

        try:
            if self.source == "sheets":
                self._import_from_sheets()
            elif self.source == "csv":
                if not self.csv_file:
                    raise CommandError("--csv-file é obrigatório quando --from=csv")
                self._import_from_csv(self.csv_file)

            self.stdout.write(
                self.style.SUCCESS("✅ Importação de usuários concluída com sucesso!")
            )

        except Exception as e:
            logger.error(f"Erro na importação de usuários: {e}")
            raise CommandError(f"Erro na importação: {e}")

    def _import_from_sheets(self):
        """Importa usuários do Google Sheets"""
        try:
            from core.services.google_sheets_service import google_sheets_service

            spreadsheet_id = sheets_config.get_spreadsheet_id("usuarios")
            abas = sheets_config.get_abas("usuarios")

            self.stdout.write(f"📊 Importando da planilha: {spreadsheet_id}")

            for aba_name, sheet_name in abas.items():
                self.stdout.write(f"📋 Processando aba: {sheet_name}")

                # Obter dados da aba
                data = google_sheets_service.get_worksheet_data(
                    spreadsheet_id, sheet_name
                )

                if not data:
                    self.stdout.write(
                        self.style.WARNING(
                            f"⚠️  Aba '{sheet_name}' vazia ou inacessível"
                        )
                    )
                    continue

                self._process_users_data(data, f"sheets:{sheet_name}")

        except ImportError:
            raise CommandError(
                "Serviço Google Sheets não disponível. "
                "Use --from=csv com arquivo local."
            )

    def _import_from_csv(self, csv_file: str):
        """Importa usuários de arquivo CSV"""
        try:
            with open(csv_file, "r", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                data = list(reader)

            self.stdout.write(f"📄 Importando de arquivo: {csv_file}")
            self._process_users_data(data, f"csv:{csv_file}")

        except FileNotFoundError:
            raise CommandError(f"Arquivo não encontrado: {csv_file}")
        except Exception as e:
            raise CommandError(f"Erro ao ler arquivo CSV: {e}")

    def _process_users_data(self, data: List[Dict], source: str):
        """Processa dados de usuários"""
        if self.clear and not self.dry_run:
            self.stdout.write("🧹 Limpando usuários existentes...")
            Usuario.objects.all().delete()

        created_count = 0
        updated_count = 0
        error_count = 0

        for row_num, row in enumerate(data, 1):
            try:
                result = self._create_or_update_user(row, source, row_num)
                if result == "created":
                    created_count += 1
                elif result == "updated":
                    updated_count += 1

            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f"❌ Erro na linha {row_num}: {e}"))
                if self.verbose:
                    logger.error(f"Erro linha {row_num}: {e}")

        # Log de auditoria
        if not self.dry_run:
            LogAuditoria.objects.create(
                usuario=None,  # Sistema
                acao="RF01",  # Importação de usuários
                detalhes=f"Importação canônica: {created_count} criados, {updated_count} atualizados, {error_count} erros",
                origem=source,
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"📊 Resultado: {created_count} criados, {updated_count} atualizados, {error_count} erros"
            )
        )

    def _create_or_update_user(self, row: Dict, source: str, row_num: int) -> str:
        """Cria ou atualiza um usuário"""
        # Mapeamento de campos (ajustar conforme estrutura da planilha)
        cpf = row.get("CPF", "").strip()
        nome = row.get("Nome", "").strip()
        email = row.get("Email", "").strip()
        setor_nome = row.get("Setor", "").strip()
        papel = row.get("Papel", "").strip()

        if not cpf or not nome:
            raise ValueError("CPF e Nome são obrigatórios")

        # Gerar hash único para idempotência
        external_hash = hashlib.sha256(
            f"{source}|{cpf}|{nome}|{email}".encode()
        ).hexdigest()

        # Buscar ou criar setor
        setor = None
        if setor_nome:
            setor, _ = Setor.objects.get_or_create(
                nome=setor_nome, defaults={"descricao": f"Setor {setor_nome}"}
            )

        # Buscar usuário existente
        try:
            usuario = Usuario.objects.get(username=cpf)
            action = "updated"
        except Usuario.DoesNotExist:
            usuario = Usuario(username=cpf)
            action = "created"

        # Atualizar dados
        usuario.first_name = nome.split()[0] if nome else ""
        usuario.last_name = " ".join(nome.split()[1:]) if len(nome.split()) > 1 else ""
        usuario.email = email
        usuario.setor = setor
        usuario.is_active = True

        # Salvar apenas se não for dry-run
        if not self.dry_run:
            usuario.save()

            # Log detalhado
            if self.verbose:
                self.stdout.write(f"✅ {action.title()}: {nome} ({cpf})")

        return action
