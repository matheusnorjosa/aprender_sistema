"""
Management command: cleanup_e2e_data

Remove dados de testes E2E (Playwright) criados por seed_e2e_users.
Comando idempotente: roda várias vezes sem erros.

Uso:
    # Docker (recomendado)
    docker compose exec -T web python manage.py cleanup_e2e_data

    # Local
    python manage.py cleanup_e2e_data

Dados removidos:
    - Usuários E2E (coord_e2e, super_e2e, controle_e2e, formador_e2e)
    - Solicitações criadas por esses usuários
    - Participations relacionadas
    - Município "Salvador, BA" (ibge_code=2927408) se não houver dependências
    - Projeto "TESTE E2E" (codigo=E2E) se não houver dependências

Fase 2 - Testes E2E (Playwright) - Plano DAT/GCal 2025-10-29
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from apps.core.models import Municipio, Projeto, Solicitacao, Participation

User = get_user_model()


class Command(BaseCommand):
    help = "Remove dados de testes E2E (Playwright) criados por seed_e2e_users"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Apenas exibe o que seria deletado, sem aplicar mudanças',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)

        self.stdout.write("=" * 80)
        self.stdout.write("CLEANUP E2E DATA — Limpeza de dados de teste")
        self.stdout.write("=" * 80)

        if dry_run:
            self.stdout.write("\n⚠️  MODO DRY-RUN: Nenhuma mudança será aplicada\n")

        with transaction.atomic():
            # 1. Remover usuários E2E e dados relacionados
            self.stdout.write("\n1. Removendo usuários E2E...")
            deleted_users = self._delete_users(dry_run)

            # 2. Remover município de teste (se não houver dependências)
            self.stdout.write("\n2. Verificando município de teste...")
            deleted_municipio = self._delete_municipio(dry_run)

            # 3. Remover projeto de teste (se não houver dependências)
            self.stdout.write("\n3. Verificando projeto de teste...")
            deleted_projeto = self._delete_projeto(dry_run)

            # 4. Resumo
            self.stdout.write("\n" + "=" * 80)
            if dry_run:
                self.stdout.write("📋 RESUMO (DRY-RUN):")
            else:
                self.stdout.write("✅ CLEANUP E2E concluído com sucesso!")
                self.stdout.write("\n📋 Resumo:")

            self.stdout.write(f"   Usuários removidos: {deleted_users['count']}")
            self.stdout.write(f"   Solicitações removidas: {deleted_users['solicitacoes']}")
            self.stdout.write(f"   Participações removidas: {deleted_users['participations']}")
            self.stdout.write(f"   Município removido: {'Sim' if deleted_municipio else 'Não'}")
            self.stdout.write(f"   Projeto removido: {'Sim' if deleted_projeto else 'Não'}")

            if dry_run:
                self.stdout.write("\n⚠️  Para aplicar mudanças, rode sem --dry-run")

            self.stdout.write("=" * 80)

            # Rollback if dry-run
            if dry_run:
                transaction.set_rollback(True)

    def _delete_users(self, dry_run):
        """Remove usuários E2E e seus dados relacionados."""
        e2e_usernames = [
            "coord_e2e@test.com",
            "super_e2e@test.com",
            "controle_e2e@test.com",
            "formador_e2e@test.com",
        ]

        users = User.objects.filter(username__in=e2e_usernames)
        user_count = users.count()

        # Contar dados relacionados
        solicitacoes = Solicitacao.objects.filter(usuario__in=users)
        solicitacoes_count = solicitacoes.count()

        participations = Participation.objects.filter(usuario__in=users)
        participations_count = participations.count()

        if user_count == 0:
            self.stdout.write("   ⏭️  Nenhum usuário E2E encontrado")
            return {'count': 0, 'solicitacoes': 0, 'participations': 0}

        # Deletar dados relacionados primeiro
        if not dry_run:
            participations.delete()
            solicitacoes.delete()
            users.delete()

        for username in e2e_usernames:
            status = "🗑️  Seria removido" if dry_run else "✅ Removido"
            if User.objects.filter(username=username).exists() or not dry_run:
                self.stdout.write(f"   {status}: {username}")

        return {
            'count': user_count,
            'solicitacoes': solicitacoes_count,
            'participations': participations_count,
        }

    def _delete_municipio(self, dry_run):
        """Remove município de teste se não houver dependências."""
        try:
            municipio = Municipio.objects.get(ibge_code="2927408")  # Salvador

            # Verificar dependências
            solicitacoes_count = Solicitacao.objects.filter(municipio=municipio).count()

            if solicitacoes_count > 0:
                self.stdout.write(
                    f"   ⏭️  Mantido: Salvador, BA ({solicitacoes_count} solicitações dependem)"
                )
                return False

            status = "🗑️  Seria removido" if dry_run else "✅ Removido"
            self.stdout.write(f"   {status}: {municipio.nome} ({municipio.uf})")

            if not dry_run:
                municipio.delete()

            return True

        except Municipio.DoesNotExist:
            self.stdout.write("   ⏭️  Município não encontrado")
            return False

    def _delete_projeto(self, dry_run):
        """Remove projeto de teste se não houver dependências."""
        try:
            projeto = Projeto.objects.get(codigo="E2E")

            # Verificar dependências
            solicitacoes_count = Solicitacao.objects.filter(projeto=projeto).count()

            if solicitacoes_count > 0:
                self.stdout.write(
                    f"   ⏭️  Mantido: {projeto.nome} ({solicitacoes_count} solicitações dependem)"
                )
                return False

            status = "🗑️  Seria removido" if dry_run else "✅ Removido"
            self.stdout.write(f"   {status}: {projeto.nome} (fluxo: {projeto.fluxo})")

            if not dry_run:
                projeto.delete()

            return True

        except Projeto.DoesNotExist:
            self.stdout.write("   ⏭️  Projeto não encontrado")
            return False
