# core/management/commands/sync_roles_from_papel.py
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from core.models import Usuario
from core.signals import sync_all_users_to_groups


class Command(BaseCommand):
    help = "Sincroniza todos os usuários existentes com grupos Django baseado no campo papel"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Executa sem fazer alterações, apenas mostra o que seria feito",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Força a sincronização mesmo se os grupos não existirem",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        force = options["force"]

        self.stdout.write(
            self.style.SUCCESS("=== SINCRONIZAÇÃO DE PAPÉIS PARA GRUPOS DJANGO ===\n")
        )

        # Verificar se os grupos existem
        expected_groups = [
            "admin",
            "superintendencia",
            "coordenador",
            "formador",
            "controle",
            "diretoria",
        ]
        missing_groups = []

        for group_name in expected_groups:
            if not Group.objects.filter(name=group_name).exists():
                missing_groups.append(group_name)

        if missing_groups and not force:
            self.stdout.write(
                self.style.ERROR(
                    f'ERRO: Os seguintes grupos não existem: {", ".join(missing_groups)}'
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    "Execute a migration 0002_setup_groups_and_permissions primeiro, ou use --force para prosseguir."
                )
            )
            return

        # Análise preliminar
        users_by_papel = {}
        total_users = Usuario.objects.count()

        for user in Usuario.objects.all():
            papel = user.papel or "sem_papel"
            if papel not in users_by_papel:
                users_by_papel[papel] = []
            users_by_papel[papel].append(user.username)

        self.stdout.write(f"Total de usuários encontrados: {total_users}\n")

        for papel, usernames in users_by_papel.items():
            count = len(usernames)
            self.stdout.write(f"  {papel}: {count} usuários")
            if count <= 5:
                self.stdout.write(f'    ({", ".join(usernames)})')
            else:
                self.stdout.write(f'    (primeiros 3: {", ".join(usernames[:3])}, ...)')

        self.stdout.write("")

        if dry_run:
            self.stdout.write(
                self.style.WARNING("MODE DRY-RUN: Nenhuma alteração será feita.\n")
            )

            # Simular as alterações
            for user in Usuario.objects.all():
                if user.papel:
                    current_groups = list(user.groups.values_list("name", flat=True))
                    target_group = user.papel

                    self.stdout.write(f"Usuário: {user.username}")
                    self.stdout.write(f"  Papel atual: {user.papel}")
                    self.stdout.write(f"  Grupos atuais: {current_groups}")
                    self.stdout.write(f"  Seria adicionado ao grupo: {target_group}")
                    self.stdout.write("")

        else:
            # Executar sincronização real
            self.stdout.write("Iniciando sincronização...\n")

            users_synced, errors = sync_all_users_to_groups()

            if errors == 0:
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Sincronização concluída com sucesso!")
                )
                self.stdout.write(
                    self.style.SUCCESS(f"   {users_synced} usuários sincronizados")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"⚠️  Sincronização concluída com avisos:")
                )
                self.stdout.write(f"   {users_synced} usuários sincronizados")
                self.stdout.write(f"   {errors} erros encontrados")

        # Verificação pós-sincronização
        if not dry_run:
            self.stdout.write("\n=== VERIFICAÇÃO PÓS-SINCRONIZAÇÃO ===")

            for group_name in expected_groups:
                try:
                    group = Group.objects.get(name=group_name)
                    user_count = group.user_set.count()
                    self.stdout.write(f'Grupo "{group_name}": {user_count} usuários')

                    if user_count > 0 and user_count <= 5:
                        usernames = list(
                            group.user_set.values_list("username", flat=True)
                        )
                        self.stdout.write(f'  Usuários: {", ".join(usernames)}')

                except Group.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(f'Grupo "{group_name}" não encontrado!')
                    )

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("Comando executado com sucesso!"))
