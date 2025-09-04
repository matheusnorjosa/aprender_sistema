"""
Comando para processar dados da planilha produtos.xlsx e
atualizar projetos com códigos e tipos de produtos.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

import pandas as pd

from core.models import Projeto, Setor


class Command(BaseCommand):
    help = "Processa dados da planilha produtos.xlsx"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Apenas simula o processamento sem salvar",
        )

    def handle(self, *args, **options):
        self.dry_run = options["dry_run"]

        if self.dry_run:
            self.stdout.write(self.style.WARNING("=== MODO DRY-RUN ==="))

        try:
            with transaction.atomic():
                # Processar planilha produtos
                self.process_produtos()

                if self.dry_run:
                    raise Exception("DRY RUN - Rollback para não salvar")

                self.stdout.write(
                    self.style.SUCCESS("\n✓ Processamento concluído com sucesso!")
                )

        except Exception as e:
            if "DRY RUN" in str(e):
                self.stdout.write(
                    self.style.WARNING("\n✓ DRY RUN concluído - nenhum dado foi salvo")
                )
            else:
                self.stdout.write(self.style.ERROR(f"\n✗ Erro no processamento: {e}"))
                raise

    def process_produtos(self):
        """Processa planilha produtos.xlsx"""
        self.stdout.write("\n=== PROCESSANDO PRODUTOS ===")

        try:
            df = pd.read_excel("produtos.xlsx")
            self.stdout.write(f"Planilha carregada: {len(df)} produtos")

            # Mapeamento dos nomes da planilha para projetos do sistema
            projeto_mappings = {
                "A COR DA GENTE": "A Cor da Gente",
                "ACERTA BRASIL PORTUGUÊS": "ACerta Língua Portuguesa",
                "ACERTA BRASIL MATEMÁTICA": "ACerta Matemática",
                "AVANÇANDO JUNTOS PORTUGUÊS": "Avançando Juntos",
                "BRINCANDO E APRENDENDO": "Brincando e Aprendendo",
                "EDUCACAO FINANCEIRA LIVRO": "Educação Financeira",
                "FLUIR DAS EMOCOES": "Fluir",
                "LENDO E ESCREVENDO": "Lendo e Escrevendo",
                "LER OUVIR E CONTAR": "Ler, Ouvir e Contar",
                "NOVO LENDO": "Novo Lendo",
                "SOU DA PAZ": "Sou da Paz",
                "TEMA": "TEMA",
                "VIDA E CIENCIAS": "Vida e Ciências",
                "VIDA E LINGUAGEM": "Vida e Linguagem",
                "VIDA E MATEMATICA": "Vida e Matemática",
                # Projetos que vamos criar novos
                "CIRANDAR": "CIRANDAR",
                "ESCREVER COMUNICAR E SER": "ESCREVER COMUNICAR E SER",
                "TRANSITO LEGAL ANOS FINAIS": "TRANSITO LEGAL ANOS FINAIS",
                "TRANSITO LEGAL ANOS INICIAIS": "TRANSITO LEGAL ANOS INICIAIS",
                "TRANSITO LEGAL DECIFRA PLACAS": "TRANSITO LEGAL DECIFRA PLACAS",
                "TRANSITO LEGAL GUIA": "TRANSITO LEGAL GUIA",
                "TRANSITO LEGAL TRILHA CIRCUITO": "TRANSITO LEGAL TRILHA CIRCUITO",
            }

            # Estatísticas
            stats = {
                "projetos_atualizados": 0,
                "projetos_criados": 0,
                "produtos_processados": 0,
                "produtos_ignorados": 0,
                "erros": 0,
            }

            # Agrupar produtos por projeto
            produtos_por_projeto = {}
            for _, row in df.iterrows():
                projeto_planilha = str(row["Projeto"]).strip()

                if projeto_planilha == "Não encontrado" or pd.isna(projeto_planilha):
                    stats["produtos_ignorados"] += 1
                    continue

                if projeto_planilha not in produtos_por_projeto:
                    produtos_por_projeto[projeto_planilha] = []

                produtos_por_projeto[projeto_planilha].append(
                    {
                        "id": row["id"],
                        "produto": str(row.get("Produto", "")).strip(),
                        "nome": str(row.get("Nome", "")).strip(),
                        "tipo": str(row.get("Tipo", "")).strip(),
                    }
                )

            # Processar cada projeto
            for projeto_planilha, produtos in produtos_por_projeto.items():
                try:
                    projeto_nome = projeto_mappings.get(
                        projeto_planilha, projeto_planilha
                    )

                    # Tentar encontrar projeto existente
                    try:
                        projeto = Projeto.objects.get(nome=projeto_nome)
                        stats["projetos_atualizados"] += 1
                        action = "ATUALIZADO"
                    except Projeto.DoesNotExist:
                        # Criar projeto novo - determinar setor
                        setor = self.determine_setor_for_project(projeto_nome)
                        projeto = Projeto.objects.create(
                            nome=projeto_nome,
                            setor=setor,
                            descricao=f"Projeto criado a partir dos produtos da planilha",
                            ativo=True,
                        )
                        stats["projetos_criados"] += 1
                        action = "CRIADO"

                    # Atualizar informações do projeto com dados dos produtos
                    tipos_produtos = set()
                    codigos_produtos = []

                    for produto in produtos:
                        if produto["tipo"] and produto["tipo"] != "nan":
                            tipos_produtos.add(produto["tipo"])
                        if produto["id"]:
                            codigos_produtos.append(str(produto["id"]))
                        stats["produtos_processados"] += 1

                    # Atualizar projeto
                    if tipos_produtos:
                        projeto.tipo_produto = ", ".join(sorted(tipos_produtos))
                    if codigos_produtos:
                        # Armazenar alguns códigos como exemplo
                        exemplo_codigos = codigos_produtos[:5]
                        projeto.codigo_produto = ", ".join(exemplo_codigos)
                        if len(codigos_produtos) > 5:
                            projeto.codigo_produto += (
                                f" (e mais {len(codigos_produtos)-5})"
                            )

                    projeto.save()

                    status_setor = (
                        "SUPER"
                        if projeto.setor and projeto.setor.vinculado_superintendencia
                        else "DIRETO"
                    )
                    self.stdout.write(
                        f'{action}: {projeto.nome} ({projeto.setor.nome if projeto.setor else "SEM SETOR"} - {status_setor}) - {len(produtos)} produtos'
                    )

                except Exception as e:
                    stats["erros"] += 1
                    self.stdout.write(f"✗ Erro no projeto {projeto_planilha}: {e}")
                    continue

            # Mostrar estatísticas finais
            self.stdout.write("\n=== ESTATÍSTICAS ===")
            self.stdout.write(f'Projetos criados: {stats["projetos_criados"]}')
            self.stdout.write(f'Projetos atualizados: {stats["projetos_atualizados"]}')
            self.stdout.write(f'Produtos processados: {stats["produtos_processados"]}')
            self.stdout.write(f'Produtos ignorados: {stats["produtos_ignorados"]}')
            self.stdout.write(f'Erros: {stats["erros"]}')

            # Mostrar resumo por setor
            self.stdout.write("\n=== PROJETOS POR SETOR ===")
            for setor in Setor.objects.all().order_by("nome"):
                count = Projeto.objects.filter(setor=setor).count()
                status = (
                    "REQUER APROVAÇÃO"
                    if setor.vinculado_superintendencia
                    else "APROVAÇÃO DIRETA"
                )
                self.stdout.write(f"{setor.nome}: {count} projetos ({status})")

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR("Arquivo produtos.xlsx não encontrado"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro ao processar produtos: {e}"))
            raise

    def determine_setor_for_project(self, project_name):
        """Determina o setor baseado no nome do projeto"""
        project_lower = project_name.lower()

        # Mapeamento específico
        if any(
            keyword in project_lower
            for keyword in [
                "tema",
                "novo lendo",
                "lendo e escrevendo",
                "cirandar",
                "transito",
            ]
        ):
            return Setor.objects.get(nome="Superintendência")
        elif "vida" in project_lower:
            return Setor.objects.get(nome="Vidas")
        elif "acerta" in project_lower:
            return Setor.objects.get(nome="ACerta")
        elif "brincando" in project_lower:
            return Setor.objects.get(nome="Brincando e Aprendendo")
        elif "fluir" in project_lower:
            return Setor.objects.get(nome="Fluir das Emoções")
        elif any(
            keyword in project_lower
            for keyword in [
                "cor da gente",
                "avançando juntos",
                "educação financeira",
                "sou da paz",
                "ler ouvir",
            ]
        ):
            return Setor.objects.get(nome="Ler, Ouvir e Contar")
        else:
            # Default para superintendência
            return Setor.objects.get(nome="Superintendência")
