# aprender_sistema/core/management/commands/import_municipios.py
"""
Comando para importar municípios das planilhas Google Sheets
Suporte para CSV, Excel e Google Sheets via django-import-export

SEMANA 2 - DIA 1: Importação de municípios das planilhas
"""
import csv
import json
import uuid

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from core.models import LogAuditoria, Municipio
from core.tasks import migrate_usuarios_task

User = get_user_model()


class Command(BaseCommand):
    help = "Importa municípios de arquivos CSV, Excel ou JSON extraídos das planilhas"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            help="Arquivo para importação (CSV, Excel ou JSON)",
            default="municipios.csv",
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
            help="Limpar municípios existentes antes da importação (CUIDADO!)",
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

    def handle(self, *args, **options):
        """Execução principal do comando"""
        self.stdout.write("=== IMPORTAÇÃO DE MUNICÍPIOS DAS PLANILHAS ===")

        arquivo = options["file"]
        formato = options["format"]
        dry_run = options["dry_run"]
        clear_existing = options["clear"]
        encoding = options["encoding"]
        username = options["user"]

        # Obter usuário para auditoria
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = None
            self.stdout.write(
                self.style.WARNING(
                    f'Usuário "{username}" não encontrado. Auditoria será registrada sem usuário.'
                )
            )

        self.stdout.write(f"Arquivo: {arquivo}")
        self.stdout.write(f"Formato: {formato}")
        self.stdout.write(f'Modo: {"DRY-RUN" if dry_run else "EXECUÇÃO REAL"}')

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "MODO DRY-RUN: Nenhuma alteração será salva no banco"
                )
            )

        try:
            # Limpar municípios existentes se solicitado
            if clear_existing and not dry_run:
                self.clear_municipios(user)

            # Importar dados
            if formato == "csv":
                municipios_data = self.load_from_csv(arquivo, encoding)
            elif formato == "json":
                municipios_data = self.load_from_json(arquivo)
            elif formato == "excel":
                municipios_data = self.load_from_excel(arquivo)
            else:
                raise CommandError(f"Formato não suportado: {formato}")

            # Processar dados
            resultado = self.process_municipios(municipios_data, dry_run, user)

            # Exibir resultado
            self.display_result(resultado)

            # Log de auditoria
            if not dry_run:
                self.log_import_audit(user, resultado, arquivo, formato)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro durante importação: {e}"))
            if user:
                LogAuditoria.objects.create(
                    usuario=user,
                    acao="IMPORT_MUNICIPIOS_ERROR",
                    detalhes=f"Erro na importação de municípios: {str(e)} - Arquivo: {arquivo}",
                )
            raise CommandError(f"Falha na importação: {e}")

    def clear_municipios(self, user):
        """Limpar municípios existentes"""
        count = Municipio.objects.count()

        if count == 0:
            self.stdout.write("Nenhum município para limpar")
            return

        self.stdout.write(f"Removendo {count} municípios existentes...")

        with transaction.atomic():
            Municipio.objects.all().delete()

            if user:
                LogAuditoria.objects.create(
                    usuario=user,
                    acao="CLEAR_MUNICIPIOS",
                    detalhes=f"Removidos {count} municípios antes da importação",
                )

        self.stdout.write(self.style.SUCCESS(f"{count} municípios removidos"))

    def load_from_csv(self, arquivo, encoding):
        """Carregar dados de arquivo CSV"""
        self.stdout.write(f"Carregando dados do CSV: {arquivo}")

        municipios = []

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
                        k.strip().lower(): v.strip() for k, v in row.items()
                    }

                    # Mapear colunas possíveis
                    nome = self.extract_field(
                        normalized_row,
                        ["nome", "municipio", "cidade", "nome_municipio"],
                    )
                    uf = self.extract_field(
                        normalized_row, ["uf", "estado", "sigla", "sigla_estado"]
                    )
                    ativo_str = self.extract_field(
                        normalized_row, ["ativo", "status", "ativo_inativo"], "True"
                    )

                    if not nome:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Linha {row_num}: Nome do município não encontrado. Pulando."
                            )
                        )
                        continue

                    # Normalizar UF
                    uf = uf.upper()[:2] if uf else ""

                    # Processar campo ativo
                    ativo = self.parse_boolean(ativo_str)

                    municipios.append(
                        {
                            "nome": nome.title(),  # Capitalizar
                            "uf": uf,
                            "ativo": ativo,
                            "linha": row_num,
                        }
                    )

        except FileNotFoundError:
            raise CommandError(f"Arquivo não encontrado: {arquivo}")
        except Exception as e:
            raise CommandError(f"Erro ao ler CSV: {e}")

        self.stdout.write(f"Carregados {len(municipios)} registros do CSV")
        return municipios

    def load_from_json(self, arquivo):
        """Carregar dados de arquivo JSON"""
        self.stdout.write(f"Carregando dados do JSON: {arquivo}")

        try:
            with open(arquivo, "r", encoding="utf-8") as jsonfile:
                data = json.load(jsonfile)

                if isinstance(data, list):
                    municipios_data = data
                elif isinstance(data, dict) and "municipios" in data:
                    municipios_data = data["municipios"]
                else:
                    raise CommandError(
                        "Formato JSON inválido. Esperado lista ou {municipios: [...]}"
                    )

                municipios = []

                for item in municipios_data:
                    municipios.append(
                        {
                            "nome": item.get("nome", "").title(),
                            "uf": item.get("uf", "").upper()[:2],
                            "ativo": self.parse_boolean(item.get("ativo", True)),
                        }
                    )

        except FileNotFoundError:
            raise CommandError(f"Arquivo não encontrado: {arquivo}")
        except json.JSONDecodeError as e:
            raise CommandError(f"Erro ao decodificar JSON: {e}")
        except Exception as e:
            raise CommandError(f"Erro ao ler JSON: {e}")

        self.stdout.write(f"Carregados {len(municipios)} registros do JSON")
        return municipios

    def load_from_excel(self, arquivo):
        """Carregar dados de arquivo Excel usando django-import-export"""
        try:
            import openpyxl
        except ImportError:
            raise CommandError(
                "openpyxl não está instalado. Execute: pip install openpyxl"
            )

        self.stdout.write(f"Carregando dados do Excel: {arquivo}")

        municipios = []

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

                nome = self.extract_field(row_data, ["nome", "municipio", "cidade"])
                uf = self.extract_field(row_data, ["uf", "estado", "sigla"])
                ativo_str = self.extract_field(row_data, ["ativo", "status"], "True")

                if not nome:
                    continue

                municipios.append(
                    {
                        "nome": str(nome).title(),
                        "uf": str(uf).upper()[:2] if uf else "",
                        "ativo": self.parse_boolean(ativo_str),
                        "linha": row_num,
                    }
                )

        except FileNotFoundError:
            raise CommandError(f"Arquivo não encontrado: {arquivo}")
        except Exception as e:
            raise CommandError(f"Erro ao ler Excel: {e}")

        self.stdout.write(f"Carregados {len(municipios)} registros do Excel")
        return municipios

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

    def process_municipios(self, municipios_data, dry_run, user):
        """Processar e salvar dados dos municípios"""
        self.stdout.write("Processando dados dos municípios...")

        resultado = {
            "total": len(municipios_data),
            "criados": 0,
            "atualizados": 0,
            "duplicados": 0,
            "erros": 0,
            "detalhes_erros": [],
        }

        for municipio_data in municipios_data:
            try:
                nome = municipio_data["nome"]
                uf = municipio_data["uf"]
                ativo = municipio_data["ativo"]

                # Validações
                if not nome:
                    resultado["erros"] += 1
                    resultado["detalhes_erros"].append("Nome do município vazio")
                    continue

                if len(nome) > 255:
                    resultado["erros"] += 1
                    resultado["detalhes_erros"].append(
                        f"Nome muito longo: {nome[:50]}..."
                    )
                    continue

                if uf and len(uf) > 2:
                    resultado["erros"] += 1
                    resultado["detalhes_erros"].append(f"UF inválida: {uf}")
                    continue

                if not dry_run:
                    # Tentar criar ou atualizar
                    municipio, created = Municipio.objects.get_or_create(
                        nome=nome, uf=uf, defaults={"ativo": ativo}
                    )

                    if created:
                        resultado["criados"] += 1
                        self.stdout.write(f"  [+] Criado: {nome} ({uf})")
                    else:
                        # Atualizar se necessário
                        if municipio.ativo != ativo:
                            municipio.ativo = ativo
                            municipio.save()
                            resultado["atualizados"] += 1
                            self.stdout.write(f"  [~] Atualizado: {nome} ({uf})")
                        else:
                            resultado["duplicados"] += 1
                            self.stdout.write(f"  [=] Ja existe: {nome} ({uf})")
                else:
                    # Simular criação (dry-run)
                    exists = Municipio.objects.filter(nome=nome, uf=uf).exists()
                    if exists:
                        resultado["duplicados"] += 1
                        self.stdout.write(f"  [=] [DRY] Ja existe: {nome} ({uf})")
                    else:
                        resultado["criados"] += 1
                        self.stdout.write(f"  [+] [DRY] Seria criado: {nome} ({uf})")

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
        self.stdout.write("=== RESULTADO DA IMPORTAÇÃO ===")
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
            self.stdout.write(self.style.SUCCESS("Importação concluída com sucesso!"))
        elif sucesso > 0:
            self.stdout.write(
                self.style.WARNING("Importação concluída com alguns erros")
            )
        else:
            self.stdout.write(self.style.ERROR("Nenhum registro foi importado"))

    def log_import_audit(self, user, resultado, arquivo, formato):
        """Registrar log de auditoria da importação"""
        if user:
            LogAuditoria.objects.create(
                usuario=user,
                acao="IMPORT_MUNICIPIOS",
                detalhes=f'Importação de municípios concluída - Arquivo: {arquivo} - Formato: {formato} - Criados: {resultado["criados"]} - Atualizados: {resultado["atualizados"]} - Erros: {resultado["erros"]}',
            )
