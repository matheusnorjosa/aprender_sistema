# aprender_sistema/core/management/commands/import_tipos_evento.py
"""
Comando para importar tipos de eventos das planilhas Google Sheets
Suporte para CSV, Excel e Google Sheets via django-import-export

SEMANA 2 - DIA 3: Importação de tipos de eventos das planilhas
"""
import csv
import json
import uuid

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from core.models import LogAuditoria, TipoEvento

User = get_user_model()


class Command(BaseCommand):
    help = "Importa tipos de eventos de arquivos CSV, Excel ou JSON extraidos das planilhas"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            help="Arquivo para importacao (CSV, Excel ou JSON)",
            default="tipos_evento.csv",
        )

        parser.add_argument(
            "--format",
            type=str,
            choices=["csv", "json", "excel"],
            help="Formato do arquivo (padrao: csv)",
            default="csv",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Execucao de teste sem salvar no banco",
        )

        parser.add_argument(
            "--clear",
            action="store_true",
            help="Limpar tipos de eventos existentes antes da importacao (CUIDADO!)",
        )

        parser.add_argument(
            "--encoding",
            type=str,
            help="Codificacao do arquivo CSV",
            default="utf-8-sig",
        )

        parser.add_argument(
            "--user",
            type=str,
            help="Username do usuario responsavel pela importacao (para auditoria)",
            default="system",
        )

        parser.add_argument(
            "--update-existing",
            action="store_true",
            help="Atualizar tipos de eventos existentes com novos dados",
        )

    def handle(self, *args, **options):
        """Execucao principal do comando"""
        self.stdout.write("=== IMPORTACAO DE TIPOS DE EVENTOS DAS PLANILHAS ===")

        arquivo = options["file"]
        formato = options["format"]
        dry_run = options["dry_run"]
        clear_existing = options["clear"]
        encoding = options["encoding"]
        username = options["user"]
        update_existing = options["update_existing"]

        # Obter usuario para auditoria
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
            # Limpar tipos de eventos existentes se solicitado
            if clear_existing and not dry_run:
                self.clear_tipos_evento(user)

            # Importar dados
            if formato == "csv":
                tipos_data = self.load_from_csv(arquivo, encoding)
            elif formato == "json":
                tipos_data = self.load_from_json(arquivo)
            elif formato == "excel":
                tipos_data = self.load_from_excel(arquivo)
            else:
                raise CommandError(f"Formato nao suportado: {formato}")

            # Processar dados
            resultado = self.process_tipos_evento(
                tipos_data, dry_run, user, update_existing
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
                    acao="IMPORT_TIPOS_EVENTO_ERROR",
                    detalhes=f"Erro na importacao de tipos de eventos: {str(e)} - Arquivo: {arquivo}",
                )
            raise CommandError(f"Falha na importacao: {e}")

    def clear_tipos_evento(self, user):
        """Limpar tipos de eventos existentes"""
        count = TipoEvento.objects.count()

        if count == 0:
            self.stdout.write("Nenhum tipo de evento para limpar")
            return

        self.stdout.write(f"Removendo {count} tipos de eventos existentes...")

        with transaction.atomic():
            TipoEvento.objects.all().delete()

            if user:
                LogAuditoria.objects.create(
                    usuario=user,
                    acao="CLEAR_TIPOS_EVENTO",
                    detalhes=f"Removidos {count} tipos de eventos antes da importacao",
                )

        self.stdout.write(self.style.SUCCESS(f"{count} tipos de eventos removidos"))

    def load_from_csv(self, arquivo, encoding):
        """Carregar dados de arquivo CSV"""
        self.stdout.write(f"Carregando dados do CSV: {arquivo}")

        tipos = []

        try:
            with open(arquivo, "r", encoding=encoding, newline="") as csvfile:
                # Detectar delimitador
                sample = csvfile.read(1024)
                csvfile.seek(0)
                delimiter = "," if "," in sample else ";"

                reader = csv.DictReader(csvfile, delimiter=delimiter)

                for row_num, row in enumerate(reader, 1):
                    # Normalizar nomes das colunas (remover espacos, minusculas)
                    normalized_row = {
                        k.strip().lower(): v.strip() if isinstance(v, str) else v
                        for k, v in row.items()
                    }

                    # Mapear colunas possiveis
                    nome = self.extract_field(
                        normalized_row,
                        ["nome", "tipo", "tipo_evento", "evento", "title"],
                    )
                    online_str = self.extract_field(
                        normalized_row,
                        ["online", "modalidade", "formato", "tipo_modalidade"],
                        "False",
                    )
                    ativo_str = self.extract_field(
                        normalized_row, ["ativo", "status", "ativo_inativo"], "True"
                    )

                    if not nome:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Linha {row_num}: Nome do tipo de evento nao encontrado. Pulando."
                            )
                        )
                        continue

                    # Processar campo online (modalidade)
                    online = self.parse_online_field(online_str)
                    ativo = self.parse_boolean(ativo_str)

                    tipos.append(
                        {
                            "nome": nome.strip(),
                            "online": online,
                            "ativo": ativo,
                            "linha": row_num,
                        }
                    )

        except FileNotFoundError:
            raise CommandError(f"Arquivo nao encontrado: {arquivo}")
        except Exception as e:
            raise CommandError(f"Erro ao ler CSV: {e}")

        self.stdout.write(f"Carregados {len(tipos)} registros do CSV")
        return tipos

    def load_from_json(self, arquivo):
        """Carregar dados de arquivo JSON"""
        self.stdout.write(f"Carregando dados do JSON: {arquivo}")

        try:
            with open(arquivo, "r", encoding="utf-8") as jsonfile:
                data = json.load(jsonfile)

                if isinstance(data, list):
                    tipos_data = data
                elif isinstance(data, dict) and "tipos_evento" in data:
                    tipos_data = data["tipos_evento"]
                elif isinstance(data, dict) and "tipos" in data:
                    tipos_data = data["tipos"]
                else:
                    raise CommandError(
                        "Formato JSON invalido. Esperado lista ou {tipos_evento: [...]} ou {tipos: [...]}"
                    )

                tipos = []

                for item in tipos_data:
                    nome = item.get("nome", "").strip()
                    online = self.parse_online_field(
                        item.get("online", item.get("modalidade", False))
                    )
                    ativo = self.parse_boolean(item.get("ativo", True))

                    tipos.append({"nome": nome, "online": online, "ativo": ativo})

        except FileNotFoundError:
            raise CommandError(f"Arquivo nao encontrado: {arquivo}")
        except json.JSONDecodeError as e:
            raise CommandError(f"Erro ao decodificar JSON: {e}")
        except Exception as e:
            raise CommandError(f"Erro ao ler JSON: {e}")

        self.stdout.write(f"Carregados {len(tipos)} registros do JSON")
        return tipos

    def load_from_excel(self, arquivo):
        """Carregar dados de arquivo Excel usando django-import-export"""
        try:
            import openpyxl
        except ImportError:
            raise CommandError(
                "openpyxl nao esta instalado. Execute: pip install openpyxl"
            )

        self.stdout.write(f"Carregando dados do Excel: {arquivo}")

        tipos = []

        try:
            workbook = openpyxl.load_workbook(arquivo, read_only=True)
            sheet = workbook.active

            # Primeira linha e cabecalho
            headers = [
                cell.value.strip().lower() if cell.value else "" for cell in sheet[1]
            ]

            for row_num, row in enumerate(sheet.iter_rows(min_row=2), 2):
                row_data = {
                    headers[i]: cell.value if cell.value else ""
                    for i, cell in enumerate(row)
                    if i < len(headers)
                }

                nome = self.extract_field(row_data, ["nome", "tipo", "tipo_evento"])
                online_str = self.extract_field(
                    row_data, ["online", "modalidade", "formato"], "False"
                )
                ativo_str = self.extract_field(row_data, ["ativo", "status"], "True")

                if not nome:
                    continue

                tipos.append(
                    {
                        "nome": str(nome).strip(),
                        "online": self.parse_online_field(online_str),
                        "ativo": self.parse_boolean(ativo_str),
                        "linha": row_num,
                    }
                )

        except FileNotFoundError:
            raise CommandError(f"Arquivo nao encontrado: {arquivo}")
        except Exception as e:
            raise CommandError(f"Erro ao ler Excel: {e}")

        self.stdout.write(f"Carregados {len(tipos)} registros do Excel")
        return tipos

    def extract_field(self, row_data, field_names, default=""):
        """Extrair campo de um dicionario usando multiplos nomes possiveis"""
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

    def parse_online_field(self, value):
        """Converter string para boolean especifico para campo online"""
        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            value_lower = value.lower().strip()
            # Valores que indicam modalidade online
            online_values = [
                "true",
                "1",
                "sim",
                "online",
                "virtual",
                "remoto",
                "ead",
                "distancia",
                "web",
                "digital",
                "internet",
            ]
            # Valores que indicam modalidade presencial
            presencial_values = [
                "false",
                "0",
                "nao",
                "presencial",
                "fisico",
                "local",
                "sala",
                "auditorio",
                "classroom",
            ]

            if value_lower in online_values:
                return True
            elif value_lower in presencial_values:
                return False

        # Default para presencial se nao conseguir determinar
        return bool(value) if value else False

    def process_tipos_evento(self, tipos_data, dry_run, user, update_existing):
        """Processar e salvar dados dos tipos de eventos"""
        self.stdout.write("Processando dados dos tipos de eventos...")

        resultado = {
            "total": len(tipos_data),
            "criados": 0,
            "atualizados": 0,
            "duplicados": 0,
            "erros": 0,
            "detalhes_erros": [],
        }

        for tipo_data in tipos_data:
            try:
                nome = tipo_data["nome"]
                online = tipo_data["online"]
                ativo = tipo_data["ativo"]

                # Validacoes
                if not nome:
                    resultado["erros"] += 1
                    resultado["detalhes_erros"].append("Nome do tipo de evento vazio")
                    continue

                if len(nome) > 255:
                    resultado["erros"] += 1
                    resultado["detalhes_erros"].append(
                        f"Nome muito longo: {nome[:50]}..."
                    )
                    continue

                if not dry_run:
                    # Tentar criar ou atualizar
                    tipo_evento, created = TipoEvento.objects.get_or_create(
                        nome=nome, defaults={"online": online, "ativo": ativo}
                    )

                    if created:
                        resultado["criados"] += 1
                        modalidade = "[ONLINE]" if online else "[PRESENCIAL]"
                        status = "[ATIVO]" if ativo else "[INATIVO]"
                        self.stdout.write(f"  [+] Criado: {nome} {modalidade} {status}")
                    else:
                        # Atualizar se necessario e permitido
                        if update_existing:
                            updated = False
                            if tipo_evento.online != online:
                                tipo_evento.online = online
                                updated = True
                            if tipo_evento.ativo != ativo:
                                tipo_evento.ativo = ativo
                                updated = True

                            if updated:
                                tipo_evento.save()
                                resultado["atualizados"] += 1
                                modalidade = "[ONLINE]" if online else "[PRESENCIAL]"
                                self.stdout.write(
                                    f"  [~] Atualizado: {nome} {modalidade}"
                                )
                            else:
                                resultado["duplicados"] += 1
                                self.stdout.write(
                                    f"  [=] Ja existe (sem alteracoes): {nome}"
                                )
                        else:
                            resultado["duplicados"] += 1
                            modalidade = (
                                "[ONLINE]" if tipo_evento.online else "[PRESENCIAL]"
                            )
                            self.stdout.write(f"  [=] Ja existe: {nome} {modalidade}")
                else:
                    # Simular criacao (dry-run)
                    exists = TipoEvento.objects.filter(nome=nome).exists()
                    if exists:
                        if update_existing:
                            resultado["atualizados"] += 1
                            self.stdout.write(f"  [~] [DRY] Seria atualizado: {nome}")
                        else:
                            resultado["duplicados"] += 1
                            self.stdout.write(f"  [=] [DRY] Ja existe: {nome}")
                    else:
                        resultado["criados"] += 1
                        modalidade = "[ONLINE]" if online else "[PRESENCIAL]"
                        status = "[ATIVO]" if ativo else "[INATIVO]"
                        self.stdout.write(
                            f"  [+] [DRY] Seria criado: {nome} {modalidade} {status}"
                        )

            except Exception as e:
                resultado["erros"] += 1
                resultado["detalhes_erros"].append(
                    f"Erro ao processar {nome}: {str(e)}"
                )
                self.stdout.write(self.style.ERROR(f"  [X] Erro: {nome} - {e}"))

        return resultado

    def display_result(self, resultado):
        """Exibir resultado da importacao"""
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
        """Registrar log de auditoria da importacao"""
        if user:
            LogAuditoria.objects.create(
                usuario=user,
                acao="IMPORT_TIPOS_EVENTO",
                detalhes=f'Importacao de tipos de eventos concluida - Arquivo: {arquivo} - Formato: {formato} - Criados: {resultado["criados"]} - Atualizados: {resultado["atualizados"]} - Erros: {resultado["erros"]}',
            )
