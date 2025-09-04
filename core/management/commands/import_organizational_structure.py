"""
Comando para importar estrutura organizacional completa das planilhas Excel.
Processa setores, usuários, projetos e estabelece vinculações corretas.
"""

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

import pandas as pd

from core.models import Projeto, Setor, Usuario


class Command(BaseCommand):
    help = "Importa estrutura organizacional das planilhas Excel"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Apenas simula a importação sem salvar no banco",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Sobrescreve dados existentes",
        )

    def handle(self, *args, **options):
        self.dry_run = options["dry_run"]
        self.force = options["force"]

        if self.dry_run:
            self.stdout.write(self.style.WARNING("=== MODO DRY-RUN ==="))

        try:
            with transaction.atomic():
                # 1. Criar setores organizacionais
                self.create_setores()

                # 2. Processar planilha de produtos
                self.process_produtos()

                # 3. Processar planilha de superintendência
                self.process_superintendencia()

                # 4. Processar planilhas dos demais setores
                self.process_setores_planilhas()

                if self.dry_run:
                    raise Exception("DRY RUN - Rollback para não salvar")

                self.stdout.write(
                    self.style.SUCCESS("\n✓ Importação concluída com sucesso!")
                )

        except Exception as e:
            if "DRY RUN" in str(e):
                self.stdout.write(
                    self.style.WARNING("\n✓ DRY RUN concluído - nenhum dado foi salvo")
                )
            else:
                self.stdout.write(self.style.ERROR(f"\n✗ Erro na importação: {e}"))
                raise

    def create_setores(self):
        """Cria os setores organizacionais base"""
        self.stdout.write("\n=== CRIANDO SETORES ===")

        setores_base = [
            {
                "nome": "Superintendência",
                "sigla": "SUPER",
                "vinculado_superintendencia": True,
            },
            {
                "nome": "Vidas",
                "sigla": "VIDAS",
                "vinculado_superintendencia": False,
            },
            {
                "nome": "ACerta",
                "sigla": "ACERTA",
                "vinculado_superintendencia": False,
            },
            {
                "nome": "Brincando e Aprendendo",
                "sigla": "BRINC",
                "vinculado_superintendencia": False,
            },
            {
                "nome": "Fluir das Emoções",
                "sigla": "FLUIR",
                "vinculado_superintendencia": False,
            },
            {
                "nome": "IDEB 10",
                "sigla": "IDEB",
                "vinculado_superintendencia": False,
            },
            {
                "nome": "Ler, Ouvir e Contar",
                "sigla": "LOC",
                "vinculado_superintendencia": False,
            },
            {
                "nome": "AMMA",
                "sigla": "AMMA",
                "vinculado_superintendencia": False,
            },
        ]

        for setor_data in setores_base:
            setor, created = Setor.objects.get_or_create(
                nome=setor_data["nome"],
                defaults={
                    "sigla": setor_data["sigla"],
                    "vinculado_superintendencia": setor_data[
                        "vinculado_superintendencia"
                    ],
                },
            )

            if created:
                self.stdout.write(f"✓ Setor criado: {setor.nome}")
            else:
                self.stdout.write(f"• Setor já existe: {setor.nome}")

    def process_produtos(self):
        """Processa planilha produtos.xlsx para criar projetos"""
        self.stdout.write("\n=== PROCESSANDO PRODUTOS ===")

        try:
            df = pd.read_excel("produtos.xlsx")
            self.stdout.write(f"Planilha produtos.xlsx: {len(df)} registros")

            # Log das colunas para debug
            self.stdout.write(f"Colunas encontradas: {list(df.columns)}")

            # Processar produtos e criar projetos
            projetos_criados = 0
            for idx, row in df.iterrows():
                try:
                    # Extrair dados básicos
                    codigo = str(row.get("id", "")).strip()
                    nome = str(row.get("Nome", "")).strip()
                    projeto_nome = str(row.get("Projeto", "")).strip()
                    tipo = str(row.get("Tipo", "")).strip()

                    if not projeto_nome or projeto_nome == "nan":
                        continue

                    # Determinar setor baseado no nome do projeto
                    setor = self.determine_setor_by_project_name(projeto_nome)

                    if setor:
                        projeto, created = Projeto.objects.get_or_create(
                            nome=projeto_nome,
                            defaults={
                                "setor": setor,
                                "descricao": nome,
                                "codigo_produto": codigo,
                                "tipo_produto": tipo,
                                "ativo": True,
                            },
                        )

                        if created:
                            projetos_criados += 1
                            self.stdout.write(
                                f"✓ Projeto criado: {projeto.nome} → {setor.nome}"
                            )

                except Exception as e:
                    self.stdout.write(f"Erro na linha {idx}: {e}")
                    continue

            self.stdout.write(f"Total projetos criados: {projetos_criados}")

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR("Arquivo produtos.xlsx não encontrado"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro ao processar produtos: {e}"))

    def determine_setor_by_project_name(self, project_name):
        """Determina o setor baseado no nome do projeto"""
        project_lower = project_name.lower()

        # Mapeamento de palavras-chave para setores
        mappings = {
            "superintendencia": [
                "novo lendo",
                "lendo e escrevendo",
                "tema",
                "amma",
                "uni duni",
                "cataventos",
                "miudezas",
            ],
            "vidas": ["vida", "vidas"],
            "acerta": ["acerta"],
            "brincando": ["brincando"],
            "fluir": ["fluir"],
            "ideb": ["ideb"],
            "ler": ["ler", "ouvir", "contar"],
        }

        for setor_key, keywords in mappings.items():
            if any(keyword in project_lower for keyword in keywords):
                try:
                    if setor_key == "superintendencia":
                        return Setor.objects.get(nome="Superintendência")
                    elif setor_key == "vidas":
                        return Setor.objects.get(nome="Vidas")
                    elif setor_key == "acerta":
                        return Setor.objects.get(nome="ACerta")
                    elif setor_key == "brincando":
                        return Setor.objects.get(nome="Brincando e Aprendendo")
                    elif setor_key == "fluir":
                        return Setor.objects.get(nome="Fluir das Emoções")
                    elif setor_key == "ideb":
                        return Setor.objects.get(nome="IDEB 10")
                    elif setor_key == "ler":
                        return Setor.objects.get(nome="Ler, Ouvir e Contar")
                except Setor.DoesNotExist:
                    pass

        # Default para superintendência se não conseguir mapear
        try:
            return Setor.objects.get(nome="Superintendência")
        except Setor.DoesNotExist:
            return None

    def process_superintendencia(self):
        """Processa planilha superintendencia.xlsx"""
        self.stdout.write("\n=== PROCESSANDO SUPERINTENDÊNCIA ===")

        try:
            df = pd.read_excel("superintendencia.xlsx")
            self.stdout.write(f"Planilha superintendencia.xlsx: {len(df)} registros")
            self.stdout.write(f"Colunas: {list(df.columns)}")

            # Processar cada linha da superintendência
            for idx, row in df.iterrows():
                self.stdout.write(f"Linha {idx}: {dict(row)}")

        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR("Arquivo superintendencia.xlsx não encontrado")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Erro ao processar superintendência: {e}")
            )

    def process_setores_planilhas(self):
        """Processa planilhas dos demais setores"""
        self.stdout.write("\n=== PROCESSANDO SETORES ===")

        planilhas_setores = [
            ("ACerta.xlsx", "ACerta"),
            ("Vidas.xlsx", "Vidas"),
            ("Fluir das Emoções.xlsx", "Fluir das Emoções"),
            ("IDEB10.xlsx", "IDEB 10"),
            ("amma.xlsx", "AMMA"),
            ("ler, ouvir e contar.xlsx", "Ler, Ouvir e Contar"),
            ("Brincando e Aprendendo.xlsx", "Brincando e Aprendendo"),
        ]

        for arquivo, setor_nome in planilhas_setores:
            try:
                df = pd.read_excel(arquivo)
                self.stdout.write(f"\nPlanilha {arquivo}: {len(df)} registros")
                self.stdout.write(f"Colunas: {list(df.columns)}")

                # Processar algumas linhas como exemplo
                for idx, row in df.head(3).iterrows():
                    self.stdout.write(f"  Linha {idx}: {dict(row)}")

            except FileNotFoundError:
                self.stdout.write(f"⚠ Arquivo {arquivo} não encontrado")
            except Exception as e:
                self.stdout.write(f"Erro em {arquivo}: {e}")
