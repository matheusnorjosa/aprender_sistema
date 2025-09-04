"""
Command para migrar usuários das planilhas para Django
"""

import re
from typing import Any, Dict, Optional

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from core.management.commands.migration.base_migration import BaseMigrationCommand
from core.models import Usuario


class Command(BaseMigrationCommand):
    """
    Migra usuários das planilhas extraídas para o modelo Django

    Uso:
        python manage.py migrate_usuarios --source=extracted_usuarios.json
        python manage.py migrate_usuarios --source=extracted_usuarios.json --worksheet=Ativos --dry-run
        python manage.py migrate_usuarios --source=extracted_usuarios.json --validate-only
    """

    help = "Migra usuários das planilhas Google Sheets para Django"

    def add_arguments(self, parser):
        super().add_arguments(parser)

        parser.add_argument(
            "--create-django-users",
            action="store_true",
            help="Cria também usuários Django (auth.User) para login",
        )

        parser.add_argument(
            "--update-existing",
            action="store_true",
            help="Atualiza usuários existentes baseado no CPF",
        )

    def migrate_data(self, source_file: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migra dados de usuários

        Args:
            source_file: Arquivo JSON fonte
            options: Opções do command

        Returns:
            Dict com resultado da migração
        """
        worksheet_name = options.get(
            "worksheet", "Ativos"
        )  # Default para usuários ativos
        create_django_users = options.get("create_django_users", False)
        update_existing = options.get("update_existing", False)

        self.stdout.write(f"Migrando usuários da aba '{worksheet_name}'...")

        # Carregar dados
        records = self.load_records_as_dicts(source_file, worksheet_name)

        if not records:
            self.stdout.write(self.style.WARNING("Nenhum registro encontrado"))
            return {"status": "no_records"}

        # Processar em lotes
        batch_size = options.get("batch_size", 100)
        usuarios_to_create = []
        usuarios_to_update = []

        for i, record in enumerate(records):
            self.stats["processed"] += 1

            try:
                # Transformar registro
                usuario_data = self.transform_record(record)

                if not usuario_data:
                    self.stats["skipped"] += 1
                    continue

                # Verificar se já existe (por CPF)
                cpf = usuario_data.get("cpf")
                if cpf and update_existing:
                    try:
                        existing_user = Usuario.objects.get(cpf=cpf)
                        # Atualizar dados do usuário existente
                        for field, value in usuario_data.items():
                            setattr(existing_user, field, value)
                        usuarios_to_update.append(existing_user)
                        continue
                    except Usuario.DoesNotExist:
                        pass

                # Criar novo usuário
                usuario = Usuario(**usuario_data)

                # Validar antes de adicionar ao lote
                try:
                    usuario.full_clean()
                    usuarios_to_create.append(usuario)
                except ValidationError as e:
                    self.log_error(f"Usuário inválido: {e}", record)

            except Exception as e:
                self.log_error(f"Erro ao processar registro: {e}", record)

            # Atualizar progresso
            if i % 50 == 0:
                self.update_progress(i + 1, len(records))

        # Executar criação em massa
        create_result = {"created": 0, "errors": 0}
        if usuarios_to_create:
            create_result = self.bulk_create_objects(
                Usuario, usuarios_to_create, batch_size
            )
            self.log_success(f"Criados {create_result['created']} usuários")

        # Executar atualizações em massa
        update_result = {"updated": 0, "errors": 0}
        if usuarios_to_update and not self.dry_run:
            from core.management.commands.utils.bulk_operations import bulk_ops

            update_result = bulk_ops.bulk_update_safe(
                usuarios_to_update,
                fields=["first_name", "last_name", "email", "cpf", "telefone"],
                batch_size=batch_size,
            )
            self.stats["updated"] += update_result["updated"]
            self.log_success(f"Atualizados {update_result['updated']} usuários")

        # Vincular usuários criados aos Groups baseado na aba
        groups_assigned = 0
        if usuarios_to_create and not self.dry_run:
            groups_assigned = self.assign_users_to_groups(
                usuarios_to_create, worksheet_name
            )

        # Return string para evitar erro de output
        return f"Migração concluída: {create_result['created']} criados, {update_result['updated']} atualizados, {groups_assigned} grupos atribuídos"

    def transform_record(self, record: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        Transforma registro da planilha em dados do modelo Usuario (AbstractUser)

        Args:
            record: Dict com dados do registro

        Returns:
            Dict com dados do usuário ou None se deve ser pulado
        """
        # Verificar se registro tem dados mínimos
        nome = record.get("Nome", "").strip()
        nome_completo = record.get("Nome Completo", "").strip()
        cpf = record.get("CPF", "").strip()
        email = record.get("Email", "").strip().lower()

        if not nome or not cpf or not email:
            self.log_error("Registro sem nome, CPF ou email", record)
            return None

        # Validar e limpar CPF
        cpf_clean = self.clean_cpf(cpf)
        if not cpf_clean or not self.validate_cpf(cpf_clean):
            self.log_error(f"CPF inválido: {cpf}", record)
            return None

        # Validar email
        if not self.validate_email(email):
            self.log_error(f"Email inválido: {email}", record)
            return None

        # Dividir nome completo em first_name e last_name
        if nome_completo:
            partes_nome = nome_completo.split()
            first_name = partes_nome[0] if partes_nome else nome
            last_name = " ".join(partes_nome[1:]) if len(partes_nome) > 1 else ""
        else:
            first_name = nome
            last_name = ""

        # Construir dados do usuário para AbstractUser
        usuario_data = {
            # Campos AbstractUser
            "username": email,  # Email como username
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "is_active": True,
            # Campos customizados
            "cpf": cpf_clean,
            "telefone": self.clean_phone(record.get("Telefone", "")),
            # municipio será vinculado depois se necessário
        }

        # Senha padrão (pode ser alterada depois)
        usuario_data["password"] = "pbkdf2_sha256$600000$temp$temp"  # Senha temporária

        return usuario_data

    def clean_cpf(self, cpf: str) -> str:
        """Remove formatação do CPF"""
        return re.sub(r"[^\d]", "", cpf)

    def validate_cpf(self, cpf: str) -> bool:
        """Validação básica de CPF"""
        if len(cpf) != 11:
            return False

        # Verificar se todos os dígitos são iguais
        if cpf == cpf[0] * 11:
            return False

        # Algoritmo de validação do CPF
        def calc_digit(cpf_part: str, weights: list) -> str:
            total = sum(int(digit) * weight for digit, weight in zip(cpf_part, weights))
            remainder = total % 11
            return "0" if remainder < 2 else str(11 - remainder)

        # Verificar primeiro dígito verificador
        first_digit = calc_digit(cpf[:9], list(range(10, 1, -1)))
        if cpf[9] != first_digit:
            return False

        # Verificar segundo dígito verificador
        second_digit = calc_digit(cpf[:10], list(range(11, 1, -1)))
        if cpf[10] != second_digit:
            return False

        return True

    def validate_email(self, email: str) -> bool:
        """Validação básica de email"""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    def clean_phone(self, phone: str) -> str:
        """Limpa e padroniza telefone"""
        # Remove tudo exceto números
        clean = re.sub(r"[^\d]", "", phone)

        # Adicionar DDD padrão se necessário (85 - Fortaleza)
        if len(clean) == 8:
            clean = "85" + clean
        elif len(clean) == 9:
            clean = "85" + clean

        return clean

    def determine_perfil(self, record: Dict[str, str]) -> str:
        """Determina perfil do usuário baseado nos dados"""
        # Verificar se tem campo específico de perfil
        perfil = record.get("Perfil", "").strip().lower()

        if "superintend" in perfil or "super" in perfil:
            return "superintendencia"
        elif "coordenad" in perfil:
            return "coordenador"
        elif "formador" in perfil:
            return "formador"

        # Default baseado em outros campos ou contexto
        return "coordenador"  # Padrão mais restritivo

    def assign_users_to_groups(self, usuarios: list, worksheet_name: str) -> int:
        """
        Vincula usuários aos Groups Django baseado na aba de origem

        Args:
            usuarios: Lista de objetos Usuario criados
            worksheet_name: Nome da aba (Ativos, Inativos, Pendentes)

        Returns:
            Número de usuários vinculados a grupos
        """
        from django.contrib.auth.models import Group

        # Mapeamento aba -> grupo
        aba_to_group = {
            "Ativos": "coordenador",  # Usuários ativos = coordenadores
            "Inativos": "coordenador",  # Inativos também coordenadores
            "Pendentes": "coordenador",  # Pendentes = coordenadores (quando ativados)
        }

        group_name = aba_to_group.get(worksheet_name, "coordenador")
        assigned_count = 0

        try:
            # Obter o grupo
            group = Group.objects.get(name=group_name)

            # Buscar usuários criados no banco (bulk_create não retorna objetos com IDs)
            emails = [
                u.get("email")
                for u in usuarios
                if isinstance(u, dict) and u.get("email")
            ]

            if emails:
                created_users = Usuario.objects.filter(email__in=emails)

                for user in created_users:
                    user.groups.add(group)
                    assigned_count += 1
                    self.log_success(
                        f"Usuário {user.email} vinculado ao grupo '{group_name}'"
                    )

        except Group.DoesNotExist:
            self.log_error(
                f"Grupo '{group_name}' não encontrado. Execute setup_groups primeiro."
            )
        except Exception as e:
            self.log_error(f"Erro ao vincular usuários ao grupo: {e}")

        return assigned_count

    def validate_data(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validação específica para usuários

        Args:
            options: Opções do command

        Returns:
            Dict com resultado da validação
        """
        # Import necessário
        from core.management.commands.utils.json_loader import json_loader

        # Validação básica do arquivo
        result = super().validate_data(options)

        source_file = options.get("source")

        # Validações específicas para usuários
        try:
            data = json_loader.load_extracted_data(source_file)
            worksheets = data.get("worksheets", {})

            self.stdout.write("\n=== VALIDAÇÃO DE USUÁRIOS ===")

            total_users = 0
            for ws_name, ws_data in worksheets.items():
                user_count = ws_data.get("total_rows", 0) - 1  # -1 para header
                total_users += user_count
                self.stdout.write(f"Aba '{ws_name}': {user_count} usuários")

            self.stdout.write(f"Total de usuários: {total_users}")

            # Verificar estrutura das abas principais
            required_worksheets = ["Ativos", "Inativos", "Pendentes"]
            missing_worksheets = [
                ws for ws in required_worksheets if ws not in worksheets
            ]

            if missing_worksheets:
                self.stdout.write(
                    self.style.WARNING(f"Abas ausentes: {missing_worksheets}")
                )

            result["usuarios_validation"] = {
                "total_users": total_users,
                "worksheets": list(worksheets.keys()),
                "missing_worksheets": missing_worksheets,
            }

            # Converter para string para evitar erro de output
            self.stdout.write(
                f"\nValidação concluída: {total_users} usuários encontrados"
            )

        except Exception as e:
            self.log_error(f"Erro na validação específica: {e}")

        return "Validação de usuários concluída"  # Retornar string ao invés de dict
