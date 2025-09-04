"""
Comando para limpar dados de teste e manter apenas projetos reais.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Projeto, Solicitacao


class Command(BaseCommand):
    help = "Limpa dados de teste mantendo apenas projetos reais"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Apenas simula a limpeza sem deletar",
        )

    def handle(self, *args, **options):
        self.dry_run = options["dry_run"]

        if self.dry_run:
            self.stdout.write(self.style.WARNING("=== MODO DRY-RUN ==="))

        try:
            with transaction.atomic():
                # Identificar e remover projetos de teste
                self.clean_test_projects()

                # Limpar solicitações órfãs se necessário
                self.clean_orphaned_requests()

                if self.dry_run:
                    raise Exception("DRY RUN - Rollback para não deletar")

                self.stdout.write(
                    self.style.SUCCESS("\n✓ Limpeza concluída com sucesso!")
                )

        except Exception as e:
            if "DRY RUN" in str(e):
                self.stdout.write(
                    self.style.WARNING(
                        "\n✓ DRY RUN concluído - nenhum dado foi deletado"
                    )
                )
            else:
                self.stdout.write(self.style.ERROR(f"\n✗ Erro na limpeza: {e}"))
                raise

    def clean_test_projects(self):
        """Remove projetos de teste identificados por padrões"""
        self.stdout.write("\n=== IDENTIFICANDO PROJETOS DE TESTE ===")

        # Critérios para identificar projetos de teste
        test_patterns = [
            "Projeto ",  # Projetos que começam com "Projeto "
        ]

        # Projetos que claramente são de teste
        test_names = [
            "Projeto Alpha",
            "Projeto Beta",
            "Projeto Gamma",
            "Projeto Delta",
            "Projeto Omega",
            "Projeto Flow Test",
            "Projeto Teste E2E",
            "Projeto Novo Teste",
            "Projeto Piloto 2025",
            "Projeto Piloto Experimental",
            "Projeto Historico - Descontinuado",
        ]

        # Buscar projetos de teste
        test_projects = []

        # Por padrão de nome
        for pattern in test_patterns:
            projects = Projeto.objects.filter(nome__startswith=pattern)
            for project in projects:
                if project not in test_projects:
                    test_projects.append(project)

        # Por nome específico
        for name in test_names:
            try:
                project = Projeto.objects.get(nome=name)
                if project not in test_projects:
                    test_projects.append(project)
            except Projeto.DoesNotExist:
                continue

        # Adicional: projetos sem produtos E que não são dos setores específicos
        projetos_sem_produto = Projeto.objects.filter(
            codigo_produto__isnull=True
        ).exclude(
            nome__in=[
                # Manter esses mesmo sem produtos por serem organizacionais
                "AMMA",
                "CATAVENTOS",
                "MIUDEZAS",
                "UNI DUNI TÊ",
                "IDEB 10",
            ]
        )

        for project in projetos_sem_produto:
            # Se o nome sugere ser teste, adicionar
            if any(
                pattern in project.nome
                for pattern in ["Projeto ", "Teste", "Alpha", "Beta"]
            ):
                if project not in test_projects:
                    test_projects.append(project)

        self.stdout.write(f"Projetos de teste identificados: {len(test_projects)}")

        # Mostrar quais serão removidos
        for project in test_projects:
            setor_nome = project.setor.nome if project.setor else "SEM SETOR"
            solicitacoes = Solicitacao.objects.filter(projeto=project).count()
            self.stdout.write(
                f"• {project.nome} ({setor_nome}) - {solicitacoes} solicitações"
            )

        # Verificar impacto nas solicitações
        total_solicitacoes = sum(
            Solicitacao.objects.filter(projeto=project).count()
            for project in test_projects
        )
        self.stdout.write(f"\nTotal solicitações afetadas: {total_solicitacoes}")

        if not self.dry_run and test_projects:
            self.stdout.write("\n=== REMOVENDO PROJETOS DE TESTE ===")

            stats = {"projetos_removidos": 0, "solicitacoes_removidas": 0}

            for project in test_projects:
                # Contar e deletar solicitações primeiro
                solicitacoes = Solicitacao.objects.filter(projeto=project)
                solicitacoes_count = solicitacoes.count()

                if solicitacoes_count > 0:
                    solicitacoes.delete()

                # Agora deletar projeto
                project.delete()

                stats["projetos_removidos"] += 1
                stats["solicitacoes_removidas"] += solicitacoes_count

                self.stdout.write(
                    f"✓ Removido: {project.nome} ({solicitacoes_count} solicitações)"
                )

            self.stdout.write(f"\nEstatísticas:")
            self.stdout.write(f'- Projetos removidos: {stats["projetos_removidos"]}')
            self.stdout.write(
                f'- Solicitações removidas: {stats["solicitacoes_removidas"]}'
            )

    def clean_orphaned_requests(self):
        """Remove solicitações órfãs (sem projeto)"""
        self.stdout.write("\n=== VERIFICANDO SOLICITAÇÕES ÓRFÃS ===")

        orphaned = Solicitacao.objects.filter(projeto__isnull=True)
        count = orphaned.count()

        if count > 0:
            self.stdout.write(f"Encontradas {count} solicitações órfãs")
            if not self.dry_run:
                orphaned.delete()
                self.stdout.write(f"✓ {count} solicitações órfãs removidas")
        else:
            self.stdout.write("✓ Nenhuma solicitação órfã encontrada")

    def show_final_summary(self):
        """Mostra resumo final após limpeza"""
        self.stdout.write("\n=== RESUMO FINAL ===")

        # Projetos por setor
        from core.models import Setor

        for setor in Setor.objects.all().order_by("nome"):
            count = Projeto.objects.filter(setor=setor).count()
            if count > 0:
                status = (
                    "REQUER APROVAÇÃO"
                    if setor.vinculado_superintendencia
                    else "APROVAÇÃO DIRETA"
                )
                self.stdout.write(f"{setor.nome}: {count} projetos ({status})")

        # Totais
        total_projetos = Projeto.objects.count()
        total_solicitacoes = Solicitacao.objects.count()

        self.stdout.write(f"\nTotal final:")
        self.stdout.write(f"- Projetos: {total_projetos}")
        self.stdout.write(f"- Solicitações: {total_solicitacoes}")
