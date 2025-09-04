"""
Comando para organizar projetos existentes nos setores corretos e criar projetos reais.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Projeto, Setor


class Command(BaseCommand):
    help = "Organiza projetos por setor e cria projetos reais"

    def handle(self, *args, **options):
        try:
            with transaction.atomic():
                self.stdout.write("=== ORGANIZANDO PROJETOS POR SETOR ===")

                # Mover projetos existentes para setores apropriados
                self.reorganize_existing_projects()

                # Criar projetos reais baseados nas planilhas
                self.create_real_projects()

                # Mostrar resumo final
                self.show_final_summary()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro: {e}"))
            raise

    def reorganize_existing_projects(self):
        """Move projetos existentes para setores apropriados baseado no nome"""
        self.stdout.write("\n=== REORGANIZANDO PROJETOS EXISTENTES ===")

        # Mapeamento de projetos para setores baseado em palavras-chave
        project_mappings = {
            "vidas": "Vidas",
            "acerta": "ACerta",
            "vida": "Vidas",
            "brincando": "Brincando e Aprendendo",
            "fluir": "Fluir das Emoções",
            "ideb": "IDEB 10",
        }

        moved_count = 0

        for projeto in Projeto.objects.all():
            projeto_lower = projeto.nome.lower()

            # Tentar mapear baseado no nome
            for keyword, setor_name in project_mappings.items():
                if keyword in projeto_lower:
                    try:
                        setor = Setor.objects.get(nome=setor_name)
                        if projeto.setor != setor:
                            old_setor = (
                                projeto.setor.nome if projeto.setor else "SEM SETOR"
                            )
                            projeto.setor = setor
                            projeto.save()
                            moved_count += 1
                            self.stdout.write(
                                f"✓ {projeto.nome}: {old_setor} → {setor.nome}"
                            )
                        break
                    except Setor.DoesNotExist:
                        continue

        self.stdout.write(f"Total projetos reorganizados: {moved_count}")

    def create_real_projects(self):
        """Cria projetos reais baseados na estrutura organizacional informada"""
        self.stdout.write("\n=== CRIANDO PROJETOS REAIS ===")

        # Projetos reais baseados na sua explicação
        real_projects = [
            # Projetos vinculados à superintendência
            {
                "nome": "Novo Lendo",
                "setor": "Superintendência",
                "descricao": "Projeto de alfabetização - vinculado à superintendência",
                "ativo": True,
            },
            {
                "nome": "Lendo e Escrevendo",
                "setor": "Superintendência",
                "descricao": "Projeto de letramento - vinculado à superintendência",
                "ativo": True,
            },
            {
                "nome": "TEMA",
                "setor": "Superintendência",
                "descricao": "Projeto TEMA - vinculado à superintendência",
                "ativo": True,
            },
            {
                "nome": "AMMA",
                "setor": "Superintendência",
                "descricao": "Projeto AMMA - vinculado à superintendência",
                "ativo": True,
            },
            {
                "nome": "UNI DUNI TÊ",
                "setor": "Superintendência",
                "descricao": "Projeto UNI DUNI TÊ - vinculado à superintendência",
                "ativo": True,
            },
            {
                "nome": "CATAVENTOS",
                "setor": "Superintendência",
                "descricao": "Projeto CATAVENTOS - vinculado à superintendência",
                "ativo": True,
            },
            {
                "nome": "MIUDEZAS",
                "setor": "Superintendência",
                "descricao": "Projeto MIUDEZAS - vinculado à superintendência",
                "ativo": True,
            },
            # Projetos dos demais setores
            {
                "nome": "Vida e Matemática",
                "setor": "Vidas",
                "descricao": "Projeto de matemática do setor Vidas",
                "ativo": True,
            },
            {
                "nome": "Vida e Ciências",
                "setor": "Vidas",
                "descricao": "Projeto de ciências do setor Vidas",
                "ativo": True,
            },
            {
                "nome": "Vida e Linguagem",
                "setor": "Vidas",
                "descricao": "Projeto de linguagem do setor Vidas",
                "ativo": True,
            },
            {
                "nome": "ACerta Matemática",
                "setor": "ACerta",
                "descricao": "Projeto de matemática ACerta",
                "ativo": True,
            },
            {
                "nome": "ACerta Língua Portuguesa",
                "setor": "ACerta",
                "descricao": "Projeto de língua portuguesa ACerta (Coord: Beatriz Castelo, Form: Polly)",
                "ativo": True,
            },
            {
                "nome": "Fluir",
                "setor": "Fluir das Emoções",
                "descricao": "Projeto principal do setor Fluir das Emoções",
                "ativo": True,
            },
            {
                "nome": "IDEB 10",
                "setor": "IDEB 10",
                "descricao": "Projeto principal do setor IDEB 10",
                "ativo": True,
            },
            {
                "nome": "Avançando Juntos",
                "setor": "Ler, Ouvir e Contar",
                "descricao": "Projeto Avançando Juntos do setor LOC",
                "ativo": True,
            },
            {
                "nome": "A Cor da Gente",
                "setor": "Ler, Ouvir e Contar",
                "descricao": "Projeto A Cor da Gente",
                "ativo": True,
            },
            {
                "nome": "Sou da Paz",
                "setor": "Ler, Ouvir e Contar",
                "descricao": "Projeto Sou da Paz",
                "ativo": True,
            },
            {
                "nome": "Educação Financeira",
                "setor": "Ler, Ouvir e Contar",
                "descricao": "Projeto Educação Financeira",
                "ativo": True,
            },
            {
                "nome": "Ler, Ouvir e Contar",
                "setor": "Ler, Ouvir e Contar",
                "descricao": "Projeto principal do setor LOC",
                "ativo": True,
            },
            {
                "nome": "Brincando e Aprendendo",
                "setor": "Brincando e Aprendendo",
                "descricao": "Projeto principal do setor Brincando e Aprendendo",
                "ativo": True,
            },
        ]

        created_count = 0
        existing_count = 0

        for project_data in real_projects:
            try:
                setor = Setor.objects.get(nome=project_data["setor"])

                projeto, created = Projeto.objects.get_or_create(
                    nome=project_data["nome"],
                    defaults={
                        "setor": setor,
                        "descricao": project_data["descricao"],
                        "ativo": project_data["ativo"],
                    },
                )

                if created:
                    created_count += 1
                    status = "SUPER" if setor.vinculado_superintendencia else "DIRETO"
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ Criado: {projeto.nome} → {setor.nome} ({status})"
                        )
                    )
                else:
                    existing_count += 1
                    # Atualizar setor se necessário
                    if projeto.setor != setor:
                        projeto.setor = setor
                        projeto.save()
                        self.stdout.write(
                            self.style.WARNING(
                                f"⚠ Atualizado: {projeto.nome} → {setor.nome}"
                            )
                        )
                    else:
                        self.stdout.write(f"• Já existe: {projeto.nome}")

            except Setor.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'✗ Setor não encontrado: {project_data["setor"]}')
                )
                continue

        self.stdout.write(f"\nResumo projetos reais:")
        self.stdout.write(f"- Criados: {created_count}")
        self.stdout.write(f"- Já existiam: {existing_count}")

    def show_final_summary(self):
        """Mostra resumo final da organização"""
        self.stdout.write("\n=== RESUMO FINAL ===")

        for setor in Setor.objects.all().order_by("nome"):
            projetos = Projeto.objects.filter(setor=setor)
            status = (
                "REQUER APROVAÇÃO"
                if setor.vinculado_superintendencia
                else "APROVAÇÃO DIRETA"
            )

            self.stdout.write(f"\n{setor.nome} ({setor.sigla}) - {status}:")
            self.stdout.write(f"  Total projetos: {projetos.count()}")

            for projeto in projetos.order_by("nome")[:5]:  # Mostrar até 5
                self.stdout.write(f"  - {projeto.nome}")

            if projetos.count() > 5:
                self.stdout.write(f"  ... e mais {projetos.count() - 5} projetos")

        # Estatísticas gerais
        total_projetos = Projeto.objects.count()
        projetos_super = Projeto.objects.filter(
            setor__vinculado_superintendencia=True
        ).count()
        projetos_direto = Projeto.objects.filter(
            setor__vinculado_superintendencia=False
        ).count()

        self.stdout.write(f"\n=== ESTATÍSTICAS GERAIS ===")
        self.stdout.write(f"Total de projetos: {total_projetos}")
        self.stdout.write(
            f"Projetos que requerem aprovação superintendência: {projetos_super}"
        )
        self.stdout.write(f"Projetos com aprovação direta: {projetos_direto}")

        # Calcular percentuais
        if total_projetos > 0:
            pct_super = (projetos_super / total_projetos) * 100
            pct_direto = (projetos_direto / total_projetos) * 100
            self.stdout.write(
                f"Distribuição: {pct_super:.1f}% superintendência, {pct_direto:.1f}% direto"
            )
