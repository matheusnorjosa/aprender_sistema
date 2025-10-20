"""
Comando para configurar dados iniciais em produção
"""

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Formador, Municipio, Projeto, TipoEvento, Usuario


class Command(BaseCommand):
    help = "Configura dados iniciais necessários em produção"

    def add_arguments(self, parser):
        parser.add_argument(
            "--with-sample-data",
            action="store_true",
            help="Inclui dados de exemplo além da configuração básica",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("=== CONFIGURAÇÃO PRODUÇÃO ==="))

        with_samples = options["with_sample_data"]

        try:
            with transaction.atomic():
                self.setup_groups()
                self.setup_basic_data()

                if with_samples:
                    self.setup_sample_data()

                self.stdout.write(self.style.SUCCESS("Configuração concluída!"))
                self.display_summary()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro na configuração: {str(e)}"))

    def setup_groups(self):
        """Cria grupos necessários"""
        self.stdout.write("Configurando grupos...")

        groups = [
            "coordenador",
            "superintendencia",
            "controle",
            "formador",
            "diretoria",
            "admin",
        ]

        for group_name in groups:
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                self.stdout.write(f"  + Grupo {group_name} criado")
            else:
                self.stdout.write(f"  ✓ Grupo {group_name} já existe")

    def setup_basic_data(self):
        """Cria dados básicos necessários"""
        self.stdout.write("Configurando dados básicos...")

        # Municípios básicos
        municipios_basicos = [
            ("Fortaleza", "CE"),
            ("São Paulo", "SP"),
            ("Rio de Janeiro", "RJ"),
            ("Belo Horizonte", "MG"),
            ("Salvador", "BA"),
        ]

        for nome, uf in municipios_basicos:
            municipio, created = Municipio.objects.get_or_create(
                nome=nome, defaults={"uf": uf}
            )
            if created:
                self.stdout.write(f"  + Município {nome}/{uf}")

        # Projetos básicos
        projetos_basicos = [
            ("Projeto Principal", "Projeto principal do sistema"),
            ("Formação Continuada", "Programa de formação continuada"),
            ("Capacitação Técnica", "Capacitação técnica especializada"),
        ]

        for nome, desc in projetos_basicos:
            projeto, created = Projeto.objects.get_or_create(
                nome=nome, defaults={"descricao": desc}
            )
            if created:
                self.stdout.write(f"  + Projeto {nome}")

        # Tipos de evento básicos
        tipos_basicos = [
            ("Formação Presencial", False),
            ("Workshop Online", True),
            ("Seminário", True),
            ("Curso Técnico", False),
        ]

        for nome, online in tipos_basicos:
            tipo, created = TipoEvento.objects.get_or_create(
                nome=nome, defaults={"online": online}
            )
            if created:
                self.stdout.write(f"  + Tipo {nome}")

    def setup_sample_data(self):
        """Cria dados de exemplo (opcional)"""
        self.stdout.write("Criando dados de exemplo...")

        # Usar comando existente
        from django.core.management import call_command

        call_command("create_sample_data", quantidade=10, verbosity=0)

        self.stdout.write("  ✓ Dados de exemplo criados")

    def display_summary(self):
        """Exibe resumo da configuração"""
        self.stdout.write("\n=== RESUMO DA CONFIGURAÇÃO ===")
        self.stdout.write(f"Grupos: {Group.objects.count()}")
        self.stdout.write(f"Usuários: {Usuario.objects.count()}")
        self.stdout.write(f"Municípios: {Municipio.objects.count()}")
        self.stdout.write(f"Projetos: {Projeto.objects.count()}")
        self.stdout.write(f"Tipos de Evento: {TipoEvento.objects.count()}")
        self.stdout.write(f"Formadores: {Formador.objects.count()}")

        self.stdout.write("\n=== PRÓXIMOS PASSOS ===")
        self.stdout.write("1. Criar usuário admin: python manage.py createsuperuser")
        self.stdout.write("2. Acessar admin: https://seu-dominio.com/admin/")
        self.stdout.write("3. Configurar usuários reais da equipe")
        self.stdout.write("4. Importar dados históricos (se disponíveis)")
