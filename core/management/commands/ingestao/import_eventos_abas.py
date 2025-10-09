"""
Comando Canônico: Importação de Eventos por Abas
================================================

Comando oficial para importação de eventos das abas da planilha de agenda.
Implementa regras de negócio específicas e validações rigorosas.

Author: Claude Code
Date: Janeiro 2025
"""

import csv
import hashlib
import logging
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from backend.config.sheets_config import sheets_config
from core.models import (
    Aprovacao,
    AprovacaoHistorico,
    Formador,
    FormadoresSolicitacao,
    MarcadorPlanilha,
    Municipio,
    Participante,
    Projeto,
    Solicitacao,
    SolicitacaoStatus,
    TipoEvento,
    Usuario,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Importa eventos das abas da planilha de agenda (comando canônico)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--from",
            type=str,
            choices=["sheets", "csv"],
            default="sheets",
            help="Fonte dos dados: sheets (Google Sheets) ou csv (arquivo local)",
        )
        parser.add_argument(
            "--csv-file", type=str, help="Caminho para arquivo CSV (quando --from=csv)"
        )
        parser.add_argument(
            "--aba",
            type=str,
            choices=["ACerta", "Brincando", "Vidas", "Super", "Outros", "all"],
            default="all",
            help='Aba específica para importar (ou "all" para todas)',
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Execução de teste sem salvar no banco",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Limpar eventos existentes antes da importação",
        )
        parser.add_argument(
            "--verbose", action="store_true", help="Mostrar informações detalhadas"
        )

    def handle(self, *args, **options):
        self.dry_run = options["dry_run"]
        self.verbose = options["verbose"]
        self.clear = options["clear"]
        self.source = options["from"]
        self.csv_file = options["csv_file"]
        self.aba_target = options["aba"]

        if self.verbose:
            logging.basicConfig(level=logging.DEBUG)

        self.stdout.write(
            self.style.SUCCESS("🚀 Iniciando importação canônica de eventos...")
        )

        # Data de corte para classificação de status
        self.corte_temporal = date(2025, 9, 25)

        try:
            if self.source == "sheets":
                self._import_from_sheets()
            elif self.source == "csv":
                if not self.csv_file:
                    raise CommandError("--csv-file é obrigatório quando --from=csv")
                self._import_from_csv(self.csv_file)

            self.stdout.write(
                self.style.SUCCESS("✅ Importação de eventos concluída com sucesso!")
            )

        except Exception as e:
            logger.error(f"Erro na importação de eventos: {e}")
            raise CommandError(f"Erro na importação: {e}")

    def _import_from_sheets(self):
        """Importa eventos do Google Sheets"""
        try:
            from core.services.google_sheets_service import google_sheets_service

            spreadsheet_id = sheets_config.get_spreadsheet_id("agenda")
            abas = sheets_config.get_abas("agenda")

            self.stdout.write(f"📊 Importando da planilha: {spreadsheet_id}")

            # Filtrar abas se especificado
            if self.aba_target != "all":
                abas = {k: v for k, v in abas.items() if k == self.aba_target}

            for aba_name, sheet_name in abas.items():
                self.stdout.write(f"📋 Processando aba: {sheet_name}")

                # Obter dados da aba
                data = google_sheets_service.get_worksheet_data(
                    spreadsheet_id, sheet_name
                )

                if not data:
                    self.stdout.write(
                        self.style.WARNING(
                            f"⚠️  Aba '{sheet_name}' vazia ou inacessível"
                        )
                    )
                    continue

                self._process_events_data(data, aba_name, f"sheets:{sheet_name}")

        except ImportError:
            raise CommandError(
                "Serviço Google Sheets não disponível. "
                "Use --from=csv com arquivo local."
            )

    def _import_from_csv(self, csv_file: str):
        """Importa eventos de arquivo CSV"""
        try:
            with open(csv_file, "r", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                data = list(reader)

            self.stdout.write(f"📄 Importando de arquivo: {csv_file}")

            # Determinar aba do nome do arquivo ou parâmetro
            aba_name = self.aba_target if self.aba_target != "all" else "Unknown"
            self._process_events_data(data, aba_name, f"csv:{csv_file}")

        except FileNotFoundError:
            raise CommandError(f"Arquivo não encontrado: {csv_file}")
        except Exception as e:
            raise CommandError(f"Erro ao ler arquivo CSV: {e}")

    def _process_events_data(self, data: List[Dict], aba_name: str, source: str):
        """Processa dados de eventos"""
        if self.clear and not self.dry_run:
            self.stdout.write("🧹 Limpando eventos existentes...")
            Solicitacao.objects.all().delete()

        created_count = 0
        updated_count = 0
        error_count = 0
        canceled_count = 0

        for row_num, row in enumerate(data, 1):
            try:
                result = self._create_or_update_event(row, aba_name, source, row_num)
                if result == "created":
                    created_count += 1
                elif result == "updated":
                    updated_count += 1
                elif result == "canceled":
                    canceled_count += 1

            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f"❌ Erro na linha {row_num}: {e}"))
                if self.verbose:
                    logger.error(f"Erro linha {row_num}: {e}")

        # Log de auditoria
        if not self.dry_run:
            from core.models import LogAuditoria

            LogAuditoria.objects.create(
                usuario=None,  # Sistema
                acao="RF02",  # Importação de eventos
                detalhes=f"Importação canônica aba {aba_name}: {created_count} criados, {updated_count} atualizados, {canceled_count} cancelados, {error_count} erros",
                origem=source,
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"📊 Resultado aba {aba_name}: {created_count} criados, {updated_count} atualizados, {canceled_count} cancelados, {error_count} erros"
            )
        )

    def _create_or_update_event(
        self, row: Dict, aba_name: str, source: str, row_num: int
    ) -> str:
        """Cria ou atualiza um evento"""
        # Extrair dados da linha (ajustar conforme estrutura da planilha)
        municipio_nome = row.get("Município", "").strip()
        projeto_nome = row.get("Projeto", "").strip()
        data_str = row.get("Data", "").strip()
        hora_inicio = row.get("Hora Início", "").strip()
        hora_fim = row.get("Hora Fim", "").strip()
        coordenador_nome = row.get("Coordenador", "").strip()  # Coluna N
        coord_acompanha = row.get("Coord Acompanha", "").strip()  # Coluna M
        tipo = row.get("Tipo", "").strip()
        encontro = row.get("Encontro", "").strip()
        aprovacao = row.get("Aprovação", "").strip()

        # Verificar se evento foi cancelado
        cancelado = self._is_canceled(row, aba_name)

        # Gerar hash único para idempotência
        external_hash = hashlib.sha256(
            f"{aba_name}|{row_num}|{municipio_nome}|{data_str}|{hora_inicio}|{projeto_nome}|{coordenador_nome}".encode()
        ).hexdigest()

        # Verificar se já existe
        try:
            marcador = MarcadorPlanilha.objects.get(external_hash=external_hash)
            solicitacao = marcador.solicitacao
            action = "updated"
        except MarcadorPlanilha.DoesNotExist:
            solicitacao = None
            action = "created"

        # Buscar ou criar entidades relacionadas
        municipio = self._get_or_create_municipio(municipio_nome)
        projeto = self._get_or_create_projeto(projeto_nome, aba_name)
        tipo_evento = self._get_or_create_tipo_evento(tipo)
        coordenador = self._get_coordenador(coordenador_nome)

        if not coordenador:
            raise ValueError(f"Coordenador não encontrado: {coordenador_nome}")

        # Determinar status baseado nas regras
        status = self._determine_status(data_str, aba_name, aprovacao, cancelado)

        # Criar ou atualizar solicitação
        if not solicitacao:
            solicitacao = Solicitacao()

        solicitacao.usuario_solicitante = coordenador
        solicitacao.municipio = municipio
        solicitacao.projeto = projeto
        solicitacao.tipo_evento = tipo_evento
        solicitacao.data_inicio = f"{data_str} {hora_inicio}"
        solicitacao.data_fim = f"{data_str} {hora_fim}"
        solicitacao.numero_encontro_formativo = encontro
        solicitacao.status = status
        solicitacao.observacoes = f"Importado da aba {aba_name}"

        # Salvar apenas se não for dry-run
        if not self.dry_run:
            with transaction.atomic():
                solicitacao.save()

                # Criar marcador de planilha
                marcador, _ = MarcadorPlanilha.objects.get_or_create(
                    external_hash=external_hash,
                    defaults={
                        "solicitacao": solicitacao,
                        "gid": str(row_num),
                        "linha": row_num,
                        "origem_aba": aba_name,
                        "cancelado_flag": cancelado,
                        "origem": source,
                    },
                )

                # Criar AprovacaoHistorico se Super com Aprovação=SIM
                if (
                    status == SolicitacaoStatus.APROVADO
                    and aba_name.strip().lower() == "super"
                ):
                    AprovacaoHistorico.objects.get_or_create(
                        solicitacao=solicitacao,
                        origem="planilha",
                        defaults={
                            "usuario": None,  # Stub - importação de planilha
                            "status_anterior": SolicitacaoStatus.CRIADO,
                            "status_novo": SolicitacaoStatus.APROVADO,
                            "decisao": "APROVADO",
                            "justificativa": f"Aprovação registrada na planilha (aba {aba_name})",
                        },
                    )

                # Adicionar participantes
                self._add_participants(solicitacao, coordenador, coord_acompanha, row)

        if cancelado:
            action = "canceled"

        if self.verbose:
            self.stdout.write(
                f"✅ {action.title()}: {municipio_nome} - {projeto_nome} ({data_str})"
            )

        return action

    def _is_canceled(self, row: Dict, aba_name: str) -> bool:
        """Verifica se o evento foi cancelado"""
        if aba_name == "Outros":
            # Coluna L - segmento contém "cancelado/adiado"
            segmento = row.get("Segmento", "").lower()
            return "cancelado" in segmento or "adiado" in segmento
        else:
            # Coluna D - checkbox "Cancelar"
            cancelar = row.get("Cancelar", "").strip().upper()
            return cancelar == "TRUE" or cancelar == "1"

    def _determine_status(
        self, data_str: str, aba_name: str, aprovacao: str, cancelado: bool
    ) -> str:
        """
        Determina o status da solicitação baseado nas regras do Hotfix Dia 3:

        - data ≤ 25/09/2025: CANCELADO (se cancelado_flag) ou REALIZADO
        - data > 25/09/2025: APROVADO (Super com Aprovação=SIM) ou CRIADO
        - AGENDADO só após Google Calendar (nunca no import)
        """
        try:
            data_evento = datetime.strptime(data_str, "%d/%m/%Y").date()
        except:
            data_evento = date.today()

        # Regra temporal: passado vs futuro
        if data_evento <= self.corte_temporal:
            return (
                SolicitacaoStatus.CANCELADO
                if cancelado
                else SolicitacaoStatus.REALIZADO
            )

        # Eventos futuros
        if (
            aba_name.strip().lower() == "super"
            and (aprovacao or "").strip().upper() == "SIM"
        ):
            return SolicitacaoStatus.APROVADO

        return SolicitacaoStatus.CRIADO

    def _get_or_create_municipio(self, nome: str) -> Municipio:
        """Busca ou cria município"""
        if not nome:
            raise ValueError("Nome do município é obrigatório")

        municipio, _ = Municipio.objects.get_or_create(nome=nome, defaults={"uf": "CE"})
        return municipio

    def _get_or_create_projeto(self, nome: str, aba_name: str) -> Projeto:
        """Busca ou cria projeto"""
        if not nome:
            raise ValueError("Nome do projeto é obrigatório")

        # Determinar setor baseado na aba
        if aba_name in ["ACerta", "Brincando", "Vidas", "Super"]:
            setor_nome = aba_name
        elif "IDEB" in nome.upper():
            setor_nome = "Gestão Escolar"
        else:
            setor_nome = "Outros"

        from core.models import Setor

        setor, _ = Setor.objects.get_or_create(
            nome=setor_nome, defaults={"descricao": f"Setor {setor_nome}"}
        )

        projeto, _ = Projeto.objects.get_or_create(nome=nome, defaults={"setor": setor})
        return projeto

    def _get_or_create_tipo_evento(self, nome: str) -> TipoEvento:
        """Busca ou cria tipo de evento"""
        if not nome:
            # Tipo padrão
            nome = "Formação"

        tipo, _ = TipoEvento.objects.get_or_create(
            nome=nome, defaults={"descricao": f"Tipo de evento {nome}"}
        )
        return tipo

    def _get_coordenador(self, nome: str) -> Optional[Usuario]:
        """Busca coordenador pelo nome"""
        if not nome:
            return None

        # Buscar por primeiro nome
        primeiro_nome = nome.split()[0]
        try:
            return Usuario.objects.get(first_name__icontains=primeiro_nome)
        except Usuario.DoesNotExist:
            return None

    def _get_or_create_usuario(
        self, nome: str, origem: str = "planilha"
    ) -> Optional[Usuario]:
        """
        Busca ou cria usuário marcando origem da criação.
        HOTFIX DIA 3: Usuários criados on-the-fly são marcados com origem='planilha'.
        """
        if not nome:
            return None

        # Tentar buscar primeiro
        usuario = self._get_coordenador(nome)
        if usuario:
            return usuario

        # Se não existir, criar stub provisório
        if not self.dry_run:
            # Gerar username único baseado no nome
            partes = nome.split()
            primeiro = partes[0].lower() if partes else "usuario"
            ultimo = partes[-1].lower() if len(partes) > 1 else "planilha"
            username_base = f"{primeiro}.{ultimo}"

            # Garantir unicidade
            username = username_base
            contador = 1
            while Usuario.objects.filter(username=username).exists():
                username = f"{username_base}{contador}"
                contador += 1

            usuario = Usuario.objects.create(
                username=username,
                first_name=partes[0] if partes else nome,
                last_name=" ".join(partes[1:]) if len(partes) > 1 else "",
                email=f"{username}@provisorio.aprender.ce.gov.br",
                is_active=False,  # Marcar como inativo até reconciliação
                origem=origem,
            )

            if self.verbose:
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠️  Usuário provisório criado: {nome} ({username})"
                    )
                )

        return usuario

    def _add_participants(
        self,
        solicitacao: Solicitacao,
        coordenador: Usuario,
        coord_acompanha: str,
        row: Dict,
    ):
        """Adiciona participantes à solicitação usando modelo canônico Participante"""
        # Coordenador principal (coluna N)
        Participante.objects.get_or_create(
            solicitacao=solicitacao, usuario=coordenador, papel="COORDENADOR"
        )

        # Coordenador Acompanha (coluna M) - HOTFIX DIA 3
        if coord_acompanha:
            coord_acomp = self._get_or_create_usuario(coord_acompanha, "planilha")
            if coord_acomp:
                Participante.objects.get_or_create(
                    solicitacao=solicitacao,
                    usuario=coord_acomp,
                    papel="COORDENADOR_ACOMPANHA",
                )

        # Formadores 1-5 (colunas E, F, G, H, I)
        for i in range(1, 6):
            formador_nome = row.get(f"Formador {i}", "").strip()
            if formador_nome:
                formador = self._get_or_create_usuario(formador_nome, "planilha")
                if formador:
                    Participante.objects.get_or_create(
                        solicitacao=solicitacao, usuario=formador, papel="FORMADOR"
                    )

        # Convidados (coluna J, K, etc - se existirem)
        convidados_str = row.get("Convidados", "").strip()
        if convidados_str:
            # Separar por vírgula ou ponto-e-vírgula
            convidados = [
                c.strip() for c in convidados_str.replace(";", ",").split(",")
            ]
            for convidado_nome in convidados:
                if convidado_nome:
                    convidado = self._get_or_create_usuario(convidado_nome, "planilha")
                    if convidado:
                        Participante.objects.get_or_create(
                            solicitacao=solicitacao,
                            usuario=convidado,
                            papel="CONVIDADO",
                        )
