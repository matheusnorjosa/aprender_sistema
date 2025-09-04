# aprender_sistema/core/management/commands/import_projetos.py
"""
Comando para importar projetos das planilhas Google Sheets
Suporte para CSV, Excel e Google Sheets via django-import-export

SEMANA 2 - DIA 2: Importação de projetos das planilhas
"""
import csv
import json
import uuid

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from core.models import LogAuditoria, Projeto

User = get_user_model()


class Command(BaseCommand):
    help = "Importa projetos de arquivos CSV, Excel ou JSON extraídos das planilhas"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            help="Arquivo para importação (CSV, Excel ou JSON)",
            default="projetos.csv",
        )

        parser.add_argument(
            "--format",
            type=str,
            choices=["csv", "json", "excel"],
            help="Formato do arquivo (padrão: csv)",
            default="csv",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Execução de teste sem salvar no banco",
        )

        parser.add_argument(
            "--clear",
            action="store_true",
            help="Limpar projetos existentes antes da importação (CUIDADO!)",
        )

        parser.add_argument(
            "--encoding",
            type=str,
            help="Codificação do arquivo CSV",
            default="utf-8-sig",
        )

        parser.add_argument(
            "--user",
            type=str,
            help="Username do usuário responsável pela importação (para auditoria)",
            default="system",
        )

        parser.add_argument(
            "--update-existing",
            action="store_true",
            help="Atualizar projetos existentes com novos dados",
        )

    def handle(self, *args, **options):
        """Execução principal do comando"""
        self.stdout.write("=== IMPORTACAO DE PROJETOS DAS PLANILHAS ===")

        arquivo = options["file"]
        formato = options["format"]
        dry_run = options["dry_run"]
        clear_existing = options["clear"]
        encoding = options["encoding"]
        username = options["user"]
        update_existing = options["update_existing"]

        # Obter usuário para auditoria
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = None
            self.stdout.write(
                self.style.WARNING(
                    f'Usuario "{username}" nao encontrado. Auditoria sera registrada sem usuario.'
                )
            )

        self.stdout.write(f"Arquivo: {arquivo}")
        self.stdout.write(f"Formato: {formato}")
        self.stdout.write(f'Modo: {"DRY-RUN" if dry_run else "EXECUCAO REAL"}')
        self.stdout.write(
            f'Atualizar existentes: {"Sim" if update_existing else "Nao"}'
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "MODO DRY-RUN: Nenhuma alteracao sera salva no banco"
                )
            )

        try:
            # Limpar projetos existentes se solicitado
            if clear_existing and not dry_run:
                self.clear_projetos(user)

            # Importar dados
            if formato == "csv":
                projetos_data = self.load_from_csv(arquivo, encoding)
            elif formato == "json":
                projetos_data = self.load_from_json(arquivo)
            elif formato == "excel":
                projetos_data = self.load_from_excel(arquivo)
            else:
                raise CommandError(f"Formato nao suportado: {formato}")

            # Processar dados
            resultado = self.process_projetos(
                projetos_data, dry_run, user, update_existing
            )

            # Exibir resultado
            self.display_result(resultado)

            # Log de auditoria
            if not dry_run:
                self.log_import_audit(user, resultado, arquivo, formato)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro durante importacao: {e}"))
            if user:
                LogAuditoria.objects.create(
                    usuario=user,
                    acao="IMPORT_PROJETOS_ERROR",
                    detalhes=f"Erro na importacao de projetos: {str(e)} - Arquivo: {arquivo}",
                )
            raise CommandError(f"Falha na importacao: {e}")

    def clear_projetos(self, user):
        """Limpar projetos existentes"""
        count = Projeto.objects.count()

        if count == 0:
            self.stdout.write("Nenhum projeto para limpar")
            return

        self.stdout.write(f"Removendo {count} projetos existentes...")

        with transaction.atomic():
            Projeto.objects.all().delete()

            if user:
                LogAuditoria.objects.create(
                    usuario=user,
                    acao="CLEAR_PROJETOS",
                    detalhes=f"Removidos {count} projetos antes da importacao",
                )

        self.stdout.write(self.style.SUCCESS(f"{count} projetos removidos"))

    def load_from_csv(self, arquivo, encoding):
        """Carregar dados de arquivo CSV"""
        self.stdout.write(f"Carregando dados do CSV: {arquivo}")

        projetos = []

        try:
            with open(arquivo, "r", encoding=encoding, newline="") as csvfile:
                # Detectar delimitador
                sample = csvfile.read(1024)
                csvfile.seek(0)
                delimiter = "," if "," in sample else ";"

                reader = csv.DictReader(csvfile, delimiter=delimiter)

                for row_num, row in enumerate(reader, 1):
                    # Normalizar nomes das colunas (remover espaços, maiúsculas)
                    normalized_row = {
                        k.strip().lower(): v.strip() if isinstance(v, str) else v
                        for k, v in row.items()
                    }

                    # Mapear colunas possíveis
                    nome = self.extract_field(
                        normalized_row, ["nome", "projeto", "nome_projeto", "title"]
                    )
                    descricao = self.extract_field(
                        normalized_row, ["descricao", "description", "desc", "detalhes"]
                    )
                    ativo_str = self.extract_field(
                        normalized_row, ["ativo", "status", "ativo_inativo"], "True"
                    )
                    vinculado_str = self.extract_field(
                        normalized_row,
                        ["vinculado_superintendencia", "vinculado", "superintendencia"],
                        "False",
                    )

                    if not nome:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Linha {row_num}: Nome do projeto nao encontrado. Pulando."
                            )
                        )
                        continue

                    # Processar campos booleanos
                    ativo = self.parse_boolean(ativo_str)
                    vinculado_superintendencia = self.parse_boolean(vinculado_str)

                    projetos.append(
                        {
                            "nome": nome.strip(),
                            "descricao": descricao.strip() if descricao else "",
                            "ativo": ativo,
                            "vinculado_superintendencia": vinculado_superintendencia,
                            "linha": row_num,
                        }
                    )

        except FileNotFoundError:
            raise CommandError(f"Arquivo nao encontrado: {arquivo}")
        except Exception as e:
            raise CommandError(f"Erro ao ler CSV: {e}")

        self.stdout.write(f"Carregados {len(projetos)} registros do CSV")
        return projetos

    def load_from_json(self, arquivo):
        """Carregar dados de arquivo JSON"""
        self.stdout.write(f"Carregando dados do JSON: {arquivo}")

        try:
            with open(arquivo, "r", encoding="utf-8") as jsonfile:
                data = json.load(jsonfile)

                if isinstance(data, list):
                    projetos_data = data
                elif isinstance(data, dict) and "projetos" in data:
                    projetos_data = data["projetos"]
                else:
                    raise CommandError(
                        "Formato JSON invalido. Esperado lista ou {projetos: [...]}"
                    )

                projetos = []

                for item in projetos_data:
                    projetos.append(
                        {
                            "nome": item.get("nome", "").strip(),
                            "descricao": item.get("descricao", "").strip(),
                            "ativo": self.parse_boolean(item.get("ativo", True)),
                            "vinculado_superintendencia": self.parse_boolean(
                                item.get("vinculado_superintendencia", False)
                            ),
                        }
                    )

        except FileNotFoundError:
            raise CommandError(f"Arquivo nao encontrado: {arquivo}")
        except json.JSONDecodeError as e:
            raise CommandError(f"Erro ao decodificar JSON: {e}")
        except Exception as e:
            raise CommandError(f"Erro ao ler JSON: {e}")

        self.stdout.write(f"Carregados {len(projetos)} registros do JSON")
        return projetos

    def load_from_excel(self, arquivo):
        """Carregar dados de arquivo Excel usando django-import-export"""
        try:
            import openpyxl
        except ImportError:
            raise CommandError(
                "openpyxl nao esta instalado. Execute: pip install openpyxl"
            )

        self.stdout.write(f"Carregando dados do Excel: {arquivo}")

        projetos = []

        try:
            workbook = openpyxl.load_workbook(arquivo, read_only=True)
            sheet = workbook.active

            # Primeira linha é cabeçalho
            headers = [
                cell.value.strip().lower() if cell.value else "" for cell in sheet[1]
            ]

            for row_num, row in enumerate(sheet.iter_rows(min_row=2), 2):
                row_data = {
                    headers[i]: cell.value if cell.value else ""
                    for i, cell in enumerate(row)
                    if i < len(headers)
                }

                nome = self.extract_field(row_data, ["nome", "projeto", "nome_projeto"])
                descricao = self.extract_field(
                    row_data, ["descricao", "description", "desc"]
                )
                ativo_str = self.extract_field(row_data, ["ativo", "status"], "True")
                vinculado_str = self.extract_field(
                    row_data, ["vinculado_superintendencia", "vinculado"], "False"
                )

                if not nome:
                    continue

                projetos.append(
                    {
                        "nome": str(nome).strip(),
                        "descricao": str(descricao).strip() if descricao else "",
                        "ativo": self.parse_boolean(ativo_str),
                        "vinculado_superintendencia": self.parse_boolean(vinculado_str),
                        "linha": row_num,
                    }
                )

        except FileNotFoundError:
            raise CommandError(f"Arquivo nao encontrado: {arquivo}")
        except Exception as e:
            raise CommandError(f"Erro ao ler Excel: {e}")

        self.stdout.write(f"Carregados {len(projetos)} registros do Excel")
        return projetos

    def extract_field(self, row_data, field_names, default=""):
        """Extrair campo de um dicionário usando múltiplos nomes possíveis"""
        for field_name in field_names:
            if field_name in row_data and row_data[field_name]:
                return str(row_data[field_name]).strip()
        return default

    def parse_boolean(self, value):
        """Converter string para boolean"""
        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            value_lower = value.lower().strip()
            return value_lower in ["true", "1", "sim", "ativo", "ativado", "on", "yes"]

        return bool(value)

    def process_projetos(self, projetos_data, dry_run, user, update_existing):
        """Processar e salvar dados dos projetos"""
        self.stdout.write("Processando dados dos projetos...")

        resultado = {
            "total": len(projetos_data),
            "criados": 0,
            "atualizados": 0,
            "duplicados": 0,
            "erros": 0,
            "detalhes_erros": [],
        }

        for projeto_data in projetos_data:
            try:
                nome = projeto_data["nome"]
                descricao = projeto_data["descricao"]
                ativo = projeto_data["ativo"]
                vinculado_superintendencia = projeto_data["vinculado_superintendencia"]

                # Validações
                if not nome:
                    resultado["erros"] += 1
                    resultado["detalhes_erros"].append("Nome do projeto vazio")
                    continue

                if len(nome) > 255:
                    resultado["erros"] += 1
                    resultado["detalhes_erros"].append(
                        f"Nome muito longo: {nome[:50]}..."
                    )
                    continue

                if not dry_run:
                    # Tentar criar ou atualizar
                    projeto, created = Projeto.objects.get_or_create(
                        nome=nome,
                        defaults={
                            "descricao": descricao,
                            "ativo": ativo,
                            "vinculado_superintendencia": vinculado_superintendencia,
                        },
                    )

                    if created:
                        resultado["criados"] += 1
                        status = "[SUPER]" if vinculado_superintendencia else "[NORMAL]"
                        self.stdout.write(f"  [+] Criado: {nome} {status}")
                    else:
                        # Atualizar se necessário e permitido
                        if update_existing:
                            updated = False
                            if projeto.descricao != descricao:
                                projeto.descricao = descricao
                                updated = True
                            if projeto.ativo != ativo:
                                projeto.ativo = ativo
                                updated = True
                            if (
                                projeto.vinculado_superintendencia
                                != vinculado_superintendencia
                            ):
                                projeto.vinculado_superintendencia = (
                                    vinculado_superintendencia
                                )
                                updated = True

                            if updated:
                                projeto.save()
                                resultado["atualizados"] += 1
                                self.stdout.write(f"  [~] Atualizado: {nome}")
                            else:
                                resultado["duplicados"] += 1
                                self.stdout.write(
                                    f"  [=] Ja existe (sem alteracoes): {nome}"
                                )
                        else:
                            resultado["duplicados"] += 1
                            self.stdout.write(f"  [=] Ja existe: {nome}")
                else:
                    # Simular criação (dry-run)
                    exists = Projeto.objects.filter(nome=nome).exists()
                    if exists:
                        if update_existing:
                            resultado["atualizados"] += 1
                            self.stdout.write(f"  [~] [DRY] Seria atualizado: {nome}")
                        else:
                            resultado["duplicados"] += 1
                            self.stdout.write(f"  [=] [DRY] Ja existe: {nome}")
                    else:
                        resultado["criados"] += 1
                        status = "[SUPER]" if vinculado_superintendencia else "[NORMAL]"
                        self.stdout.write(f"  [+] [DRY] Seria criado: {nome} {status}")

            except Exception as e:
                resultado["erros"] += 1
                resultado["detalhes_erros"].append(
                    f"Erro ao processar {nome}: {str(e)}"
                )
                self.stdout.write(self.style.ERROR(f"  [X] Erro: {nome} - {e}"))

        return resultado

    def display_result(self, resultado):
        """Exibir resultado da importação"""
        self.stdout.write("")
        self.stdout.write("=== RESULTADO DA IMPORTACAO ===")
        self.stdout.write(f'Total de registros: {resultado["total"]}')
        self.stdout.write(self.style.SUCCESS(f'Criados: {resultado["criados"]}'))
        self.stdout.write(f'Atualizados: {resultado["atualizados"]}')
        self.stdout.write(f'Duplicados (ignorados): {resultado["duplicados"]}')

        if resultado["erros"] > 0:
            self.stdout.write(self.style.ERROR(f'Erros: {resultado["erros"]}'))
            self.stdout.write("Detalhes dos erros:")
            for erro in resultado["detalhes_erros"][
                :10
            ]:  # Mostrar apenas os primeiros 10
                self.stdout.write(f"  - {erro}")
            if len(resultado["detalhes_erros"]) > 10:
                self.stdout.write(
                    f'  ... e mais {len(resultado["detalhes_erros"]) - 10} erros'
                )

        # Status final
        sucesso = resultado["criados"] + resultado["atualizados"]
        if sucesso > 0 and resultado["erros"] == 0:
            self.stdout.write(self.style.SUCCESS("Importacao concluida com sucesso!"))
        elif sucesso > 0:
            self.stdout.write(
                self.style.WARNING("Importacao concluida com alguns erros")
            )
        else:
            self.stdout.write(self.style.ERROR("Nenhum registro foi importado"))

    def log_import_audit(self, user, resultado, arquivo, formato):
        """Registrar log de auditoria da importação"""
        if user:
            LogAuditoria.objects.create(
                usuario=user,
                acao="IMPORT_PROJETOS",
                detalhes=f'Importacao de projetos concluida - Arquivo: {arquivo} - Formato: {formato} - Criados: {resultado["criados"]} - Atualizados: {resultado["atualizados"]} - Erros: {resultado["erros"]}',
            )
