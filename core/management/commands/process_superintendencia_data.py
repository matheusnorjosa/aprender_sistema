"""
Comando para processar dados da planilha superintendencia.xlsx e
associar usuários aos setores e cargos corretos.
"""

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

import pandas as pd

from core.models import Setor, Usuario


class Command(BaseCommand):
    help = "Processa dados da planilha superintendencia.xlsx"

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
                # Processar planilha superintendência
                self.process_superintendencia()

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

    def process_superintendencia(self):
        """Processa planilha superintendencia.xlsx"""
        self.stdout.write("\n=== PROCESSANDO SUPERINTENDÊNCIA ===")

        try:
            df = pd.read_excel("superintendencia.xlsx")
            self.stdout.write(f"Planilha carregada: {len(df)} registros")

            # Buscar setor superintendência
            setor_super = Setor.objects.get(nome="Superintendência")

            # Mapear cargos da planilha para sistema
            cargo_map = {
                "Gerente": "gerente",
                "Coordenadores": "coordenador",
                "Formadores": "formador",
            }

            # Estatísticas
            stats = {
                "usuarios_criados": 0,
                "usuarios_atualizados": 0,
                "usuarios_vinculados_setor": 0,
                "usuarios_vinculados_grupo": 0,
                "erros": 0,
            }

            # Processar cada registro
            for index, row in df.iterrows():
                try:
                    nome = str(row["Nome"]).strip()
                    nome_completo = (
                        str(row["Nome Completo"]).strip()
                        if pd.notna(row["Nome Completo"])
                        else nome
                    )
                    email = str(row["Email"]).strip().lower()
                    cpf = str(int(row["CPF"])) if pd.notna(row["CPF"]) else None
                    cargo_planilha = str(row["Cargo"]).strip()

                    # Mapear cargo
                    cargo_sistema = cargo_map.get(cargo_planilha)
                    if not cargo_sistema:
                        self.stdout.write(f"⚠ Cargo não mapeado: {cargo_planilha}")
                        continue

                    # Buscar ou criar usuário por email
                    usuario, created = Usuario.objects.get_or_create(
                        email=email,
                        defaults={
                            "username": email.split("@")[
                                0
                            ],  # Usar parte do email como username
                            "first_name": nome,
                            "last_name": nome_completo.replace(nome, "").strip(),
                            "cpf": cpf,
                            "setor": setor_super,
                            "cargo": cargo_sistema,
                            "is_active": True,
                        },
                    )

                    if created:
                        stats["usuarios_criados"] += 1
                        self.stdout.write(
                            f"✓ Criado: {nome} ({email}) - {cargo_planilha}"
                        )
                    else:
                        # Atualizar dados se usuário já existia
                        updated = False

                        if usuario.setor != setor_super:
                            usuario.setor = setor_super
                            updated = True
                            stats["usuarios_vinculados_setor"] += 1

                        if usuario.cargo != cargo_sistema:
                            usuario.cargo = cargo_sistema
                            updated = True

                        if not usuario.cpf and cpf:
                            usuario.cpf = cpf
                            updated = True

                        if updated:
                            usuario.save()
                            stats["usuarios_atualizados"] += 1
                            self.stdout.write(
                                f"⚠ Atualizado: {nome} ({email}) - {cargo_planilha}"
                            )
                        else:
                            self.stdout.write(f"• Já correto: {nome} ({email})")

                    # Adicionar ao grupo Django correspondente
                    try:
                        grupo = Group.objects.get(name=cargo_sistema)
                        if not usuario.groups.filter(name=cargo_sistema).exists():
                            usuario.groups.add(grupo)
                            stats["usuarios_vinculados_grupo"] += 1
                    except Group.DoesNotExist:
                        self.stdout.write(f"⚠ Grupo não encontrado: {cargo_sistema}")

                except Exception as e:
                    stats["erros"] += 1
                    self.stdout.write(f"✗ Erro na linha {index}: {e}")
                    continue

            # Mostrar estatísticas finais
            self.stdout.write("\n=== ESTATÍSTICAS ===")
            self.stdout.write(f'Usuários criados: {stats["usuarios_criados"]}')
            self.stdout.write(f'Usuários atualizados: {stats["usuarios_atualizados"]}')
            self.stdout.write(
                f'Usuários vinculados ao setor: {stats["usuarios_vinculados_setor"]}'
            )
            self.stdout.write(
                f'Usuários vinculados a grupos: {stats["usuarios_vinculados_grupo"]}'
            )
            self.stdout.write(f'Erros: {stats["erros"]}')

            # Mostrar resumo por cargo
            self.stdout.write("\n=== RESUMO POR CARGO ===")
            usuarios_super = Usuario.objects.filter(setor=setor_super)
            for cargo_db, cargo_display in Usuario.CARGO_CHOICES:
                count = usuarios_super.filter(cargo=cargo_db).count()
                if count > 0:
                    self.stdout.write(f"{cargo_display}: {count} usuários")

        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR("Arquivo superintendencia.xlsx não encontrado")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Erro ao processar superintendência: {e}")
            )
            raise
