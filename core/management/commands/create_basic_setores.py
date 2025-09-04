"""
Comando simples para criar setores organizacionais básicos.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Projeto, Setor


class Command(BaseCommand):
    help = "Cria setores organizacionais básicos"

    def handle(self, *args, **options):
        try:
            with transaction.atomic():
                self.stdout.write("=== CRIANDO SETORES ORGANIZACIONAIS ===")

                # Setores principais baseados na sua explicação
                setores_data = [
                    {
                        "nome": "Superintendência",
                        "sigla": "SUPER",
                        "vinculado_superintendencia": True,
                        "descricao": "Setor principal - projetos requerem aprovação",
                    },
                    {
                        "nome": "Vidas",
                        "sigla": "VIDAS",
                        "vinculado_superintendencia": False,
                        "descricao": "Setor Vidas - Vida e Matemática, Vida e Ciências, Vida e Linguagem",
                    },
                    {
                        "nome": "ACerta",
                        "sigla": "ACERTA",
                        "vinculado_superintendencia": False,
                        "descricao": "Setor ACerta - ACerta Matemática e ACerta Língua Portuguesa",
                    },
                    {
                        "nome": "Brincando e Aprendendo",
                        "sigla": "BRINC",
                        "vinculado_superintendencia": False,
                        "descricao": "Setor Brincando e Aprendendo",
                    },
                    {
                        "nome": "Fluir das Emoções",
                        "sigla": "FLUIR",
                        "vinculado_superintendencia": False,
                        "descricao": "Setor Fluir das Emoções",
                    },
                    {
                        "nome": "IDEB 10",
                        "sigla": "IDEB",
                        "vinculado_superintendencia": False,
                        "descricao": "Setor IDEB 10",
                    },
                    {
                        "nome": "Ler, Ouvir e Contar",
                        "sigla": "LOC",
                        "vinculado_superintendencia": False,
                        "descricao": "Setor Ler, Ouvir e Contar",
                    },
                ]

                created_count = 0
                existing_count = 0

                for setor_info in setores_data:
                    setor, created = Setor.objects.get_or_create(
                        nome=setor_info["nome"],
                        defaults={
                            "sigla": setor_info["sigla"],
                            "vinculado_superintendencia": setor_info[
                                "vinculado_superintendencia"
                            ],
                            "ativo": True,
                        },
                    )

                    if created:
                        created_count += 1
                        status = (
                            "SUPER" if setor.vinculado_superintendencia else "DIRETO"
                        )
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"✓ Criado: {setor.nome} ({setor.sigla}) - {status}"
                            )
                        )
                    else:
                        existing_count += 1
                        self.stdout.write(f"• Já existe: {setor.nome}")

                self.stdout.write("")
                self.stdout.write(f"Resumo:")
                self.stdout.write(f"- Setores criados: {created_count}")
                self.stdout.write(f"- Setores existentes: {existing_count}")
                self.stdout.write(f"- Total: {Setor.objects.count()}")

                # Listar setores por categoria
                self.stdout.write("")
                self.stdout.write("Setores por categoria:")

                super_setores = Setor.objects.filter(vinculado_superintendencia=True)
                self.stdout.write(f"SUPERINTENDÊNCIA ({len(super_setores)}):")
                for setor in super_setores:
                    self.stdout.write(f"  - {setor.nome} ({setor.sigla})")

                direct_setores = Setor.objects.filter(vinculado_superintendencia=False)
                self.stdout.write(f"DIRETOS ({len(direct_setores)}):")
                for setor in direct_setores:
                    self.stdout.write(f"  - {setor.nome} ({setor.sigla})")

                # Atualizar projetos existentes para usar setor Superintendência por padrão
                self.update_existing_projects()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro ao criar setores: {e}"))
            raise

    def update_existing_projects(self):
        """Atualiza projetos existentes para ter setor padrão"""
        self.stdout.write("")
        self.stdout.write("=== ATUALIZANDO PROJETOS EXISTENTES ===")

        # Buscar setor superintendência para usar como padrão
        try:
            setor_super = Setor.objects.get(nome="Superintendência")

            # Projetos sem setor definido
            projetos_sem_setor = Projeto.objects.filter(setor__isnull=True)

            if projetos_sem_setor.exists():
                count = projetos_sem_setor.update(setor=setor_super)
                self.stdout.write(
                    f"✓ {count} projetos vinculados ao setor Superintendência (padrão)"
                )

                # Listar alguns projetos atualizados
                for projeto in projetos_sem_setor[:5]:
                    self.stdout.write(f"  - {projeto.nome}")

                if projetos_sem_setor.count() > 5:
                    self.stdout.write(
                        f"  ... e mais {projetos_sem_setor.count() - 5} projetos"
                    )
            else:
                self.stdout.write("• Todos os projetos já têm setor definido")

        except Setor.DoesNotExist:
            self.stdout.write(self.style.ERROR("Setor Superintendência não encontrado"))
