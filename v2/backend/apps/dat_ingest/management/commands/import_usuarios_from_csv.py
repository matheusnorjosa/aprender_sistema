"""
Importa usuários a partir de CSV gerado por gen_top50_usuarios (PR20 Task 4).

REGRAS:
- Cria Usuario quando não existir
- Ignora existentes por email (idempotente)
- Atribui grupo conforme papel_sugerido
- is_active=True
- Nunca cria usuários sem email válido

CSV ESPERADO:
nome_display,email,papel_sugerido,gerente_sugerido,origem_mais_frequente,frequencia,papeis_observados,setores
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction

from apps.core.models import Usuario


class Command(BaseCommand):
    help = "Importa usuários a partir de CSV (PR20) - idempotente"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--file",
            type=str,
            required=True,
            help="Caminho do CSV de entrada",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Aplicar criação (sem este flag, apenas dry-run)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        file_path = Path(options["file"])
        apply = options["apply"]

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("IMPORT USUÁRIOS FROM CSV (PR20 Task 4)")
        self.stdout.write("=" * 80)
        self.stdout.write(f"Arquivo: {file_path}")
        self.stdout.write(f"Modo: {'APLICAR' if apply else 'DRY-RUN'}\n")

        if not file_path.exists():
            self.stdout.write(self.style.ERROR(f"❌ Arquivo não encontrado: {file_path}"))
            return

        # Ler CSV
        usuarios_to_import = []
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                usuarios_to_import.append(row)

        self.stdout.write(f"📊 Total de usuários no CSV: {len(usuarios_to_import)}\n")

        # Validar e processar
        stats = {
            "created": 0,
            "already_exists": 0,
            "skipped_no_email": 0,
            "errors": 0,
        }

        pendencias = []

        for user_data in usuarios_to_import:
            nome = user_data.get("nome_display", "").strip()
            email = user_data.get("email", "").strip()
            papel_sugerido = user_data.get("papel_sugerido", "").strip()

            # Validar email
            if not email or not self.is_valid_email(email):
                self.stdout.write(self.style.WARNING(f"  ⚠️  Sem email válido: {nome} (skipped)"))
                stats["skipped_no_email"] += 1
                pendencias.append(
                    {
                        "nome": nome,
                        "motivo": "email_invalido",
                        "email": email,
                    }
                )
                continue

            # Verificar se já existe
            if Usuario.objects.filter(email__iexact=email).exists():
                self.stdout.write(f"  ℹ️  Já existe: {nome} ({email})")
                stats["already_exists"] += 1
                continue

            # Criar usuário
            if apply:
                try:
                    with transaction.atomic():
                        # Gerar username único a partir do email
                        username = email.split("@")[0]
                        base_username = username
                        counter = 1
                        while Usuario.objects.filter(username=username).exists():
                            username = f"{base_username}{counter}"
                            counter += 1

                        # Criar usuário
                        usuario = Usuario.objects.create_user(
                            username=username,
                            email=email,
                            nome=nome,
                            is_active=True,
                        )

                        # Atribuir grupo
                        grupo_nome = self.map_papel_to_grupo(papel_sugerido)
                        if grupo_nome:
                            try:
                                grupo = Group.objects.get(name=grupo_nome)
                                usuario.groups.add(grupo)
                            except Group.DoesNotExist:
                                self.stdout.write(self.style.WARNING(f"    ⚠️  Grupo '{grupo_nome}' não existe"))

                        self.stdout.write(self.style.SUCCESS(f"  ✅ Criado: {nome} ({email}) | Grupo: {grupo_nome}"))
                        stats["created"] += 1

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  ❌ Erro ao criar '{nome}': {e}"))
                    stats["errors"] += 1

            else:
                # Dry-run
                grupo_nome = self.map_papel_to_grupo(papel_sugerido)
                self.stdout.write(self.style.SUCCESS(f"  ✅ [DRY-RUN] Criaria: {nome} ({email}) | Grupo: {grupo_nome}"))
                stats["created"] += 1

        # Sumário
        self.stdout.write("\n" + "-" * 80)
        self.stdout.write("📊 SUMÁRIO:")
        self.stdout.write(f"   Criados: {stats['created']}")
        self.stdout.write(f"   Já existentes: {stats['already_exists']}")
        self.stdout.write(f"   Sem email válido (skipped): {stats['skipped_no_email']}")
        self.stdout.write(f"   Erros: {stats['errors']}")
        self.stdout.write("-" * 80)

        if stats["skipped_no_email"] > 0:
            self.stdout.write(self.style.WARNING(f"\n⚠️  {stats['skipped_no_email']} usuário(s) sem email válido!"))
            self.stdout.write("   Preencha emails no CSV antes de importar.")

        if not apply:
            self.stdout.write(self.style.WARNING("\n⚠️  DRY-RUN: Use --apply para criar usuários"))

        self.stdout.write("\n✅ Import concluído!\n")

    def is_valid_email(self, email: str) -> bool:
        """Valida email com regex simples"""
        if not email:
            return False
        pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        return bool(re.match(pattern, email))

    def map_papel_to_grupo(self, papel_sugerido: str) -> str:
        """Mapeia papel_sugerido → nome do Group Django"""
        papel_norm = papel_sugerido.lower().strip()

        if "coordenador" in papel_norm:
            return "Coordenador"
        elif "formador" in papel_norm:
            return "Formador"
        elif "superintendencia" in papel_norm or "superintendência" in papel_norm:
            return "Superintendência"
        elif "controle" in papel_norm:
            return "Controle"
        elif "dat" in papel_norm:
            return "DAT"
        else:
            return "Formador"  # Default
