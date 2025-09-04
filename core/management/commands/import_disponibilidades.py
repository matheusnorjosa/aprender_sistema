# aprender_sistema/core/management/commands/import_disponibilidades.py
"""
Comando para importar disponibilidades dos formadores das planilhas Google Sheets
Suporte para CSV, Excel e Google Sheets via django-import-export

SEMANA 2 - DIA 4: Importação de disponibilidades dos formadores
"""
import csv
import json
import uuid
from datetime import date, datetime, time

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_time

from core.models import DisponibilidadeFormadores, Formador, LogAuditoria

User = get_user_model()


class Command(BaseCommand):
    help = "Importa disponibilidades dos formadores de arquivos CSV, Excel ou JSON extraidos das planilhas"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            help="Arquivo para importacao (CSV, Excel ou JSON)",
            default="disponibilidades.csv",
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
            help="Limpar disponibilidades existentes antes da importacao (CUIDADO!)",
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
            help="Atualizar disponibilidades existentes com novos dados",
        )

        parser.add_argument(
            "--formador",
            type=str,
            help="Filtrar importacao para um formador especifico (nome ou email)",
        )

        parser.add_argument(
            "--date-format",
            type=str,
            help="Formato de data esperado no arquivo (padrao: autodetect)",
            choices=["dd/mm/yyyy", "yyyy-mm-dd", "mm/dd/yyyy", "dd-mm-yyyy"],
        )

    def handle(self, *args, **options):
        """Execucao principal do comando"""
        self.stdout.write("=== IMPORTACAO DE DISPONIBILIDADES DOS FORMADORES ===")

        arquivo = options["file"]
        formato = options["format"]
        dry_run = options["dry_run"]
        clear_existing = options["clear"]
        encoding = options["encoding"]
        username = options["user"]
        update_existing = options["update_existing"]
        formador_filter = options["formador"]
        date_format = options["date_format"]

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
        if formador_filter:
            self.stdout.write(f"Filtro formador: {formador_filter}")
        if date_format:
            self.stdout.write(f"Formato data: {date_format}")

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "MODO DRY-RUN: Nenhuma alteracao sera salva no banco"
                )
            )

        try:
            # Limpar disponibilidades existentes se solicitado
            if clear_existing and not dry_run:
                self.clear_disponibilidades(user, formador_filter)

            # Importar dados
            if formato == "csv":
                disponibilidades_data = self.load_from_csv(
                    arquivo, encoding, date_format
                )
            elif formato == "json":
                disponibilidades_data = self.load_from_json(arquivo, date_format)
            elif formato == "excel":
                disponibilidades_data = self.load_from_excel(arquivo, date_format)
            else:
                raise CommandError(f"Formato nao suportado: {formato}")

            # Aplicar filtro de formador se especificado
            if formador_filter:
                disponibilidades_data = self.filter_by_formador(
                    disponibilidades_data, formador_filter
                )

            # Processar dados
            resultado = self.process_disponibilidades(
                disponibilidades_data, dry_run, user, update_existing
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
                    acao="IMPORT_DISPONIBILIDADES_ERROR",
                    detalhes=f"Erro na importacao de disponibilidades: {str(e)} - Arquivo: {arquivo}",
                )
            raise CommandError(f"Falha na importacao: {e}")

    def clear_disponibilidades(self, user, formador_filter=None):
        """Limpar disponibilidades existentes"""
        if formador_filter:
            # Filtrar por formador específico
            formador = self.get_formador_by_name_or_email(formador_filter)
            if not formador:
                raise CommandError(f'Formador "{formador_filter}" nao encontrado')

            queryset = DisponibilidadeFormadores.objects.filter(formador=formador)
            self.stdout.write(f"Filtrando limpeza para o formador: {formador.nome}")
        else:
            queryset = DisponibilidadeFormadores.objects.all()

        count = queryset.count()

        if count == 0:
            self.stdout.write("Nenhuma disponibilidade para limpar")
            return

        self.stdout.write(f"Removendo {count} disponibilidades existentes...")

        with transaction.atomic():
            queryset.delete()

            if user:
                LogAuditoria.objects.create(
                    usuario=user,
                    acao="CLEAR_DISPONIBILIDADES",
                    detalhes=f'Removidas {count} disponibilidades antes da importacao{f" (formador: {formador_filter})" if formador_filter else ""}',
                )

        self.stdout.write(self.style.SUCCESS(f"{count} disponibilidades removidas"))

    def load_from_csv(self, arquivo, encoding, date_format):
        """Carregar dados de arquivo CSV"""
        self.stdout.write(f"Carregando dados do CSV: {arquivo}")

        disponibilidades = []

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

                    try:
                        disp_data = self.parse_row_data(
                            normalized_row, date_format, row_num
                        )
                        if disp_data:
                            disp_data["linha"] = row_num
                            disponibilidades.append(disp_data)
                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Linha {row_num}: Erro ao processar - {e}"
                            )
                        )
                        continue

        except FileNotFoundError:
            raise CommandError(f"Arquivo nao encontrado: {arquivo}")
        except Exception as e:
            raise CommandError(f"Erro ao ler CSV: {e}")

        self.stdout.write(f"Carregados {len(disponibilidades)} registros do CSV")
        return disponibilidades

    def load_from_json(self, arquivo, date_format):
        """Carregar dados de arquivo JSON"""
        self.stdout.write(f"Carregando dados do JSON: {arquivo}")

        try:
            with open(arquivo, "r", encoding="utf-8") as jsonfile:
                data = json.load(jsonfile)

                if isinstance(data, list):
                    disponibilidades_data = data
                elif isinstance(data, dict) and "disponibilidades" in data:
                    disponibilidades_data = data["disponibilidades"]
                elif isinstance(data, dict) and "bloqueios" in data:
                    disponibilidades_data = data["bloqueios"]
                else:
                    raise CommandError(
                        "Formato JSON invalido. Esperado lista ou {disponibilidades: [...]} ou {bloqueios: [...]}"
                    )

                disponibilidades = []

                for item in disponibilidades_data:
                    try:
                        disp_data = self.parse_json_data(item, date_format)
                        if disp_data:
                            disponibilidades.append(disp_data)
                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(f"Item JSON: Erro ao processar - {e}")
                        )
                        continue

        except FileNotFoundError:
            raise CommandError(f"Arquivo nao encontrado: {arquivo}")
        except json.JSONDecodeError as e:
            raise CommandError(f"Erro ao decodificar JSON: {e}")
        except Exception as e:
            raise CommandError(f"Erro ao ler JSON: {e}")

        self.stdout.write(f"Carregados {len(disponibilidades)} registros do JSON")
        return disponibilidades

    def load_from_excel(self, arquivo, date_format):
        """Carregar dados de arquivo Excel usando django-import-export"""
        try:
            import openpyxl
        except ImportError:
            raise CommandError(
                "openpyxl nao esta instalado. Execute: pip install openpyxl"
            )

        self.stdout.write(f"Carregando dados do Excel: {arquivo}")

        disponibilidades = []

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

                try:
                    disp_data = self.parse_row_data(row_data, date_format, row_num)
                    if disp_data:
                        disp_data["linha"] = row_num
                        disponibilidades.append(disp_data)
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f"Linha {row_num}: Erro ao processar - {e}")
                    )
                    continue

        except FileNotFoundError:
            raise CommandError(f"Arquivo nao encontrado: {arquivo}")
        except Exception as e:
            raise CommandError(f"Erro ao ler Excel: {e}")

        self.stdout.write(f"Carregados {len(disponibilidades)} registros do Excel")
        return disponibilidades

    def parse_row_data(self, row_data, date_format, row_num):
        """Parse de dados de linha (CSV/Excel)"""
        # Extrair campos
        formador_nome = self.extract_field(
            row_data, ["formador", "nome_formador", "nome", "instrutor"]
        )
        formador_email = self.extract_field(
            row_data, ["email", "email_formador", "formador_email"]
        )
        data_str = self.extract_field(row_data, ["data", "data_bloqueio", "date"])
        hora_inicio_str = self.extract_field(
            row_data, ["hora_inicio", "inicio", "start", "de"]
        )
        hora_fim_str = self.extract_field(row_data, ["hora_fim", "fim", "end", "ate"])
        tipo_bloqueio = self.extract_field(
            row_data, ["tipo", "tipo_bloqueio", "categoria", "motivo_categoria"]
        )
        motivo = self.extract_field(
            row_data, ["motivo", "observacao", "descricao", "detalhes"]
        )

        if not (formador_nome or formador_email):
            self.stdout.write(
                self.style.WARNING(
                    f"Linha {row_num}: Formador nao identificado. Pulando."
                )
            )
            return None

        if not data_str:
            self.stdout.write(
                self.style.WARNING(f"Linha {row_num}: Data nao encontrada. Pulando.")
            )
            return None

        # Parse de data
        data_bloqueio = self.parse_date_field(data_str, date_format)
        if not data_bloqueio:
            raise ValueError(f"Data invalida: {data_str}")

        # Parse de horários
        hora_inicio = (
            self.parse_time_field(hora_inicio_str) if hora_inicio_str else time(9, 0)
        )
        hora_fim = self.parse_time_field(hora_fim_str) if hora_fim_str else time(17, 0)

        if hora_fim <= hora_inicio:
            raise ValueError(
                f"Hora fim ({hora_fim}) deve ser posterior a hora inicio ({hora_inicio})"
            )

        return {
            "formador_nome": formador_nome,
            "formador_email": formador_email,
            "data_bloqueio": data_bloqueio,
            "hora_inicio": hora_inicio,
            "hora_fim": hora_fim,
            "tipo_bloqueio": tipo_bloqueio or "Bloqueio",
            "motivo": motivo or "",
        }

    def parse_json_data(self, item, date_format):
        """Parse de dados JSON"""
        # Extrair campos JSON
        formador_nome = (
            item.get("formador") or item.get("nome_formador") or item.get("nome")
        )
        formador_email = item.get("email") or item.get("formador_email")
        data_str = item.get("data") or item.get("data_bloqueio")
        hora_inicio_str = item.get("hora_inicio") or item.get("inicio") or "09:00"
        hora_fim_str = item.get("hora_fim") or item.get("fim") or "17:00"
        tipo_bloqueio = item.get("tipo") or item.get("tipo_bloqueio") or "Bloqueio"
        motivo = item.get("motivo") or item.get("observacao") or ""

        if not (formador_nome or formador_email):
            self.stdout.write(
                self.style.WARNING(f"Item JSON: Formador nao identificado. Pulando.")
            )
            return None

        if not data_str:
            self.stdout.write(
                self.style.WARNING(f"Item JSON: Data nao encontrada. Pulando.")
            )
            return None

        # Parse de data
        data_bloqueio = self.parse_date_field(data_str, date_format)
        if not data_bloqueio:
            raise ValueError(f"Data invalida: {data_str}")

        # Parse de horários
        hora_inicio = self.parse_time_field(hora_inicio_str)
        hora_fim = self.parse_time_field(hora_fim_str)

        if hora_fim <= hora_inicio:
            raise ValueError(
                f"Hora fim ({hora_fim}) deve ser posterior a hora inicio ({hora_inicio})"
            )

        return {
            "formador_nome": formador_nome,
            "formador_email": formador_email,
            "data_bloqueio": data_bloqueio,
            "hora_inicio": hora_inicio,
            "hora_fim": hora_fim,
            "tipo_bloqueio": tipo_bloqueio,
            "motivo": motivo,
        }

    def extract_field(self, row_data, field_names, default=""):
        """Extrair campo de um dicionario usando multiplos nomes possiveis"""
        for field_name in field_names:
            if field_name in row_data and row_data[field_name]:
                value = row_data[field_name]
                return str(value).strip() if value else default
        return default

    def parse_date_field(self, date_str, date_format=None):
        """Parse de campo de data com multiplos formatos"""
        if not date_str:
            return None

        date_str = str(date_str).strip()

        # Formatos para tentar
        formats_to_try = []

        if date_format == "dd/mm/yyyy":
            formats_to_try.extend(["%d/%m/%Y", "%d/%m/%y"])
        elif date_format == "yyyy-mm-dd":
            formats_to_try.extend(["%Y-%m-%d"])
        elif date_format == "mm/dd/yyyy":
            formats_to_try.extend(["%m/%d/%Y", "%m/%d/%y"])
        elif date_format == "dd-mm-yyyy":
            formats_to_try.extend(["%d-%m-%Y", "%d-%m-%y"])
        else:
            # Autodetect - tentar formatos comuns
            formats_to_try.extend(
                [
                    "%Y-%m-%d",  # ISO format
                    "%d/%m/%Y",  # BR format
                    "%d/%m/%y",  # BR format short year
                    "%m/%d/%Y",  # US format
                    "%m/%d/%y",  # US format short year
                    "%d-%m-%Y",  # BR format with dash
                    "%d-%m-%y",  # BR format with dash short year
                ]
            )

        # Tentar cada formato
        for fmt in formats_to_try:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        # Tentar parse do Django como último recurso
        try:
            return parse_date(date_str)
        except:
            pass

        return None

    def parse_time_field(self, time_str):
        """Parse de campo de horário"""
        if not time_str:
            return None

        time_str = str(time_str).strip()

        # Formatos para tentar
        time_formats = [
            "%H:%M:%S",  # 14:30:00
            "%H:%M",  # 14:30
            "%H.%M",  # 14.30
            "%H,%M",  # 14,30
            "%Hh%M",  # 14h30
            "%Hh",  # 14h
        ]

        # Tentar cada formato
        for fmt in time_formats:
            try:
                return datetime.strptime(time_str, fmt).time()
            except ValueError:
                continue

        # Tentar parse do Django
        try:
            return parse_time(time_str)
        except:
            pass

        # Se nada funcionar, tentar extrair apenas números
        import re

        numbers = re.findall(r"\d+", time_str)
        if len(numbers) >= 1:
            hour = int(numbers[0])
            minute = int(numbers[1]) if len(numbers) >= 2 else 0
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return time(hour, minute)

        return None

    def get_formador_by_name_or_email(self, identifier):
        """Buscar formador por nome ou email"""
        try:
            # Tentar por email primeiro
            return Formador.objects.get(email__iexact=identifier.strip())
        except Formador.DoesNotExist:
            try:
                # Tentar por nome
                return Formador.objects.get(nome__icontains=identifier.strip())
            except Formador.DoesNotExist:
                return None

    def filter_by_formador(self, disponibilidades_data, formador_filter):
        """Filtrar dados por formador específico"""
        formador = self.get_formador_by_name_or_email(formador_filter)
        if not formador:
            raise CommandError(
                f'Formador "{formador_filter}" nao encontrado para filtro'
            )

        filtered_data = []
        for disp_data in disponibilidades_data:
            if (
                disp_data["formador_nome"]
                and formador.nome.lower() in disp_data["formador_nome"].lower()
            ) or (
                disp_data["formador_email"]
                and formador.email.lower() == disp_data["formador_email"].lower()
            ):
                filtered_data.append(disp_data)

        self.stdout.write(
            f"Filtradas {len(filtered_data)} disponibilidades para {formador.nome}"
        )
        return filtered_data

    def process_disponibilidades(
        self, disponibilidades_data, dry_run, user, update_existing
    ):
        """Processar e salvar dados das disponibilidades"""
        self.stdout.write("Processando dados das disponibilidades...")

        resultado = {
            "total": len(disponibilidades_data),
            "criados": 0,
            "atualizados": 0,
            "duplicados": 0,
            "erros": 0,
            "detalhes_erros": [],
        }

        for disp_data in disponibilidades_data:
            try:
                # Buscar formador
                formador = None
                if disp_data["formador_email"]:
                    formador = self.get_formador_by_name_or_email(
                        disp_data["formador_email"]
                    )
                if not formador and disp_data["formador_nome"]:
                    formador = self.get_formador_by_name_or_email(
                        disp_data["formador_nome"]
                    )

                if not formador:
                    resultado["erros"] += 1
                    resultado["detalhes_erros"].append(
                        f'Formador nao encontrado: {disp_data["formador_nome"]} / {disp_data["formador_email"]}'
                    )
                    continue

                # Dados da disponibilidade
                data_bloqueio = disp_data["data_bloqueio"]
                hora_inicio = disp_data["hora_inicio"]
                hora_fim = disp_data["hora_fim"]
                tipo_bloqueio = disp_data["tipo_bloqueio"]
                motivo = disp_data["motivo"]

                # Validações adicionais
                if len(tipo_bloqueio) > 50:
                    tipo_bloqueio = tipo_bloqueio[:50]

                if not dry_run:
                    # Tentar criar ou atualizar
                    disponibilidade, created = (
                        DisponibilidadeFormadores.objects.get_or_create(
                            formador=formador,
                            data_bloqueio=data_bloqueio,
                            hora_inicio=hora_inicio,
                            hora_fim=hora_fim,
                            defaults={"tipo_bloqueio": tipo_bloqueio, "motivo": motivo},
                        )
                    )

                    if created:
                        resultado["criados"] += 1
                        self.stdout.write(
                            f"  [+] Criado: {formador.nome} - {data_bloqueio} {hora_inicio}-{hora_fim} [{tipo_bloqueio}]"
                        )
                    else:
                        # Atualizar se necessario e permitido
                        if update_existing:
                            updated = False
                            if disponibilidade.tipo_bloqueio != tipo_bloqueio:
                                disponibilidade.tipo_bloqueio = tipo_bloqueio
                                updated = True
                            if disponibilidade.motivo != motivo:
                                disponibilidade.motivo = motivo
                                updated = True

                            if updated:
                                disponibilidade.save()
                                resultado["atualizados"] += 1
                                self.stdout.write(
                                    f"  [~] Atualizado: {formador.nome} - {data_bloqueio} {hora_inicio}-{hora_fim}"
                                )
                            else:
                                resultado["duplicados"] += 1
                                self.stdout.write(
                                    f"  [=] Ja existe (sem alteracoes): {formador.nome} - {data_bloqueio}"
                                )
                        else:
                            resultado["duplicados"] += 1
                            self.stdout.write(
                                f"  [=] Ja existe: {formador.nome} - {data_bloqueio} {hora_inicio}-{hora_fim}"
                            )
                else:
                    # Simular criacao (dry-run)
                    exists = DisponibilidadeFormadores.objects.filter(
                        formador=formador,
                        data_bloqueio=data_bloqueio,
                        hora_inicio=hora_inicio,
                        hora_fim=hora_fim,
                    ).exists()

                    if exists:
                        if update_existing:
                            resultado["atualizados"] += 1
                            self.stdout.write(
                                f"  [~] [DRY] Seria atualizado: {formador.nome} - {data_bloqueio}"
                            )
                        else:
                            resultado["duplicados"] += 1
                            self.stdout.write(
                                f"  [=] [DRY] Ja existe: {formador.nome} - {data_bloqueio}"
                            )
                    else:
                        resultado["criados"] += 1
                        self.stdout.write(
                            f"  [+] [DRY] Seria criado: {formador.nome} - {data_bloqueio} {hora_inicio}-{hora_fim} [{tipo_bloqueio}]"
                        )

            except Exception as e:
                resultado["erros"] += 1
                formador_info = disp_data.get("formador_nome", "Desconhecido")
                resultado["detalhes_erros"].append(
                    f"Erro ao processar {formador_info}: {str(e)}"
                )
                self.stdout.write(
                    self.style.ERROR(f"  [X] Erro: {formador_info} - {e}")
                )

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
                acao="IMPORT_DISPONIBILIDADES",
                detalhes=f'Importacao de disponibilidades concluida - Arquivo: {arquivo} - Formato: {formato} - Criados: {resultado["criados"]} - Atualizados: {resultado["atualizados"]} - Erros: {resultado["erros"]}',
            )
