"""
Comando para processar dados de todas as planilhas dos setores e
associar usuários aos setores e cargos corretos.
"""

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

import pandas as pd

from core.models import Setor, Usuario


class Command(BaseCommand):
    help = "Processa dados de todas as planilhas dos setores"

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
                # Processar todas as planilhas dos setores
                self.process_all_sectors()

                if self.dry_run:
                    raise Exception("DRY RUN - Rollback para não salvar")

                self.stdout.write(
                    self.style.SUCCESS(
                        "\n✓ Processamento de todos os setores concluído!"
                    )
                )

        except Exception as e:
            if "DRY RUN" in str(e):
                self.stdout.write(
                    self.style.WARNING("\n✓ DRY RUN concluído - nenhum dado foi salvo")
                )
            else:
                self.stdout.write(self.style.ERROR(f"\n✗ Erro no processamento: {e}"))
                raise

    def process_all_sectors(self):
        """Processa todas as planilhas dos setores"""

        # Mapeamento planilha → setor
        sector_mappings = {
            "ACerta.xlsx": "ACerta",
            "Vidas.xlsx": "Vidas",
            "Fluir das Emoções.xlsx": "Fluir das Emoções",
            "IDEB10.xlsx": "IDEB 10",
            "Brincando e Aprendendo.xlsx": "Brincando e Aprendendo",
            "ler, ouvir e contar.xlsx": "Ler, Ouvir e Contar",
            "amma.xlsx": "AMMA",  # Criar setor se não existir
        }

        # Mapeamento cargos planilha → sistema
        cargo_map = {
            "Gerente": "gerente",
            "Coordenadores": "coordenador",
            "Formadores": "formador",
        }

        # Estatísticas globais
        global_stats = {
            "setores_processados": 0,
            "usuarios_criados": 0,
            "usuarios_atualizados": 0,
            "usuarios_vinculados_setor": 0,
            "usuarios_vinculados_grupo": 0,
            "erros": 0,
        }

        # Processar cada planilha
        for planilha_file, setor_nome in sector_mappings.items():
            try:
                self.stdout.write(
                    f"\n=== PROCESSANDO {planilha_file} → SETOR {setor_nome} ==="
                )

                # Verificar se arquivo existe
                try:
                    df = pd.read_excel(planilha_file)
                except FileNotFoundError:
                    self.stdout.write(
                        f"⚠ Arquivo {planilha_file} não encontrado - pulando"
                    )
                    continue

                # Buscar ou criar setor
                setor, setor_created = Setor.objects.get_or_create(
                    nome=setor_nome,
                    defaults={
                        "sigla": setor_nome.replace(" ", "").upper()[:10],
                        "vinculado_superintendencia": False,  # Setores não-superintendência
                        "ativo": True,
                    },
                )

                if setor_created:
                    self.stdout.write(f"✓ Setor criado: {setor_nome}")

                self.stdout.write(f"Planilha carregada: {len(df)} registros")

                # Processar usuários desta planilha
                stats = self.process_sector_users(df, setor, cargo_map)

                # Atualizar estatísticas globais
                global_stats["setores_processados"] += 1
                for key in [
                    "usuarios_criados",
                    "usuarios_atualizados",
                    "usuarios_vinculados_setor",
                    "usuarios_vinculados_grupo",
                    "erros",
                ]:
                    global_stats[key] += stats[key]

                # Mostrar resumo do setor
                self.stdout.write(
                    f'Setor {setor_nome}: {stats["usuarios_criados"]} criados, {stats["usuarios_atualizados"]} atualizados'
                )

            except Exception as e:
                global_stats["erros"] += 1
                self.stdout.write(f"✗ Erro processando {planilha_file}: {e}")
                continue

        # Mostrar estatísticas finais globais
        self.stdout.write("\n=== ESTATÍSTICAS GLOBAIS ===")
        self.stdout.write(f'Setores processados: {global_stats["setores_processados"]}')
        self.stdout.write(f'Usuários criados: {global_stats["usuarios_criados"]}')
        self.stdout.write(
            f'Usuários atualizados: {global_stats["usuarios_atualizados"]}'
        )
        self.stdout.write(
            f'Usuários vinculados a setores: {global_stats["usuarios_vinculados_setor"]}'
        )
        self.stdout.write(
            f'Usuários vinculados a grupos: {global_stats["usuarios_vinculados_grupo"]}'
        )
        self.stdout.write(f'Erros: {global_stats["erros"]}')

        # Mostrar resumo final por setor
        self.show_final_summary()

    def process_sector_users(self, df, setor, cargo_map):
        """Processa usuários de uma planilha/setor específico"""
        stats = {
            "usuarios_criados": 0,
            "usuarios_atualizados": 0,
            "usuarios_vinculados_setor": 0,
            "usuarios_vinculados_grupo": 0,
            "erros": 0,
        }

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
                        "username": email.split("@")[0],
                        "first_name": nome,
                        "last_name": nome_completo.replace(nome, "").strip(),
                        "cpf": cpf,
                        "setor": setor,
                        "cargo": cargo_sistema,
                        "is_active": True,
                    },
                )

                if created:
                    stats["usuarios_criados"] += 1
                    self.stdout.write(f"✓ Criado: {nome} ({email}) - {cargo_planilha}")
                else:
                    # Atualizar dados se usuário já existia
                    updated = False

                    if usuario.setor != setor:
                        usuario.setor = setor
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

        return stats

    def show_final_summary(self):
        """Mostra resumo final de todos os setores"""
        self.stdout.write("\n=== RESUMO FINAL POR SETOR ===")

        for setor in Setor.objects.all().order_by("nome"):
            usuarios = Usuario.objects.filter(setor=setor)
            status = (
                "REQUER APROVAÇÃO"
                if setor.vinculado_superintendencia
                else "APROVAÇÃO DIRETA"
            )

            self.stdout.write(f"\n{setor.nome} ({setor.sigla}) - {status}:")
            self.stdout.write(f"  Total usuários: {usuarios.count()}")

            # Por cargo
            for cargo_db, cargo_display in Usuario.CARGO_CHOICES:
                count = usuarios.filter(cargo=cargo_db).count()
                if count > 0:
                    self.stdout.write(f"  - {cargo_display}: {count}")

        # Estatísticas gerais
        total_usuarios = Usuario.objects.exclude(setor__isnull=True).count()
        usuarios_super = Usuario.objects.filter(
            setor__vinculado_superintendencia=True
        ).count()
        usuarios_direto = Usuario.objects.filter(
            setor__vinculado_superintendencia=False
        ).count()

        self.stdout.write(f"\n=== ESTATÍSTICAS GERAIS ===")
        self.stdout.write(f"Total usuários com setor: {total_usuarios}")
        self.stdout.write(f"Usuários superintendência: {usuarios_super}")
        self.stdout.write(f"Usuários aprovação direta: {usuarios_direto}")
