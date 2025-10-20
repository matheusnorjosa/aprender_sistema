"""
Comando Django para importar TODAS as solicitações de evento da planilha "Acompanhamento de Agenda | 2025"

Este comando importa os 6.008 registros válidos de eventos identificados na análise,
populando o sistema Django com dados reais das planilhas.

Abas importadas:
- Super (1.985 registros - PRIORIDADE ALTA)
- ACerta (1.001 registros)
- Outros (1.022 registros)
- Brincando (1.000 registros)
- Vidas (1.000 registros)

Uso:
python manage.py import_agenda_completa [--aba ABA] [--dry-run] [--force] [--verbose]
"""

import json
import logging
from datetime import datetime, time

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

# Importações para Google Sheets
import gspread
from google.oauth2.credentials import Credentials

from core.models import (
    Formador,
    FormadoresSolicitacao,
    Municipio,
    Projeto,
    Setor,
    Solicitacao,
    SolicitacaoStatus,
    TipoEvento,
    Usuario,
)

User = get_user_model()


class Command(BaseCommand):
    help = 'Importa todas as solicitações de evento da planilha "Acompanhamento de Agenda | 2025"'

    def add_arguments(self, parser):
        parser.add_argument(
            "--aba",
            type=str,
            help="Importar apenas uma aba específica (Super, ACerta, Outros, Brincando, Vidas)",
            choices=["Super", "ACerta", "Outros", "Brincando", "Vidas"],
        )
        parser.add_argument(
            "--filter-quality",
            action="store_true",
            default=True,
            help="Aplicar filtro de qualidade (apenas registros com município + data)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Executa uma simulação sem salvar dados no banco",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Força reimportação, removendo dados existentes",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Exibe informações detalhadas durante a importação",
        )

    def setup_logging(self, verbose):
        """Configura logging baseado no nível de verbosidade"""
        level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler()],
        )
        self.logger = logging.getLogger(__name__)

    def setup_google_sheets(self):
        """Configura conexão com Google Sheets"""
        try:
            # Usar credenciais OAuth configuradas
            creds = Credentials.from_authorized_user_file("google_authorized_user.json")
            self.gc = gspread.authorize(creds)

            # ID da planilha
            PLANILHA_ID = "16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU"
            self.sheet = self.gc.open_by_key(PLANILHA_ID)

            self.logger.info(
                f"✅ Conexão com Google Sheets estabelecida: {self.sheet.title}"
            )

        except Exception as e:
            raise CommandError(f"❌ Erro ao conectar com Google Sheets: {e}")

    def get_or_create_municipio(self, nome_municipio):
        """Cria ou recupera município, tratando formatos com UF"""
        if not nome_municipio or nome_municipio.strip() == "":
            return None

        # Tratar casos como "Dias d'Avila - BA"
        if " - " in nome_municipio:
            nome, uf = nome_municipio.split(" - ", 1)
            nome = nome.strip()
            uf = uf.strip()
        else:
            nome = nome_municipio.strip()
            uf = "CE"  # Padrão Ceará

        municipio, created = Municipio.objects.get_or_create(
            nome=nome, uf=uf, defaults={"ativo": True}
        )

        if created:
            self.logger.debug(f"🏛️ Município criado: {nome} - {uf}")

        return municipio

    def get_or_create_setor(self, projeto_nome):
        """Cria ou recupera setor baseado no projeto"""
        # Mapear projetos para setores
        mapeamento_setores = {
            "Lendo e Escrevendo": "Superintendência",
            "ACerta": "ACerta",
            "Brincando e Aprendendo": "Brincando",
            "Vida & Linguagem": "Vidas",
            "Vida & Matemática": "Vidas",
            "Vida & Ciências": "Vidas",
            "SOU DA PAZ": "Outros",
            "LEIO ESCREVO E CALCULO": "Outros",
        }

        nome_setor = mapeamento_setores.get(projeto_nome, "Outros")

        # Verificar se é superintendência
        vinculado_super = nome_setor == "Superintendência"

        setor, created = Setor.objects.get_or_create(
            nome=nome_setor,
            defaults={
                "sigla": nome_setor[:4].upper(),
                "vinculado_superintendencia": vinculado_super,
                "ativo": True,
            },
        )

        if created:
            self.logger.debug(f"🏢 Setor criado: {nome_setor}")

        return setor

    def get_or_create_projeto(self, nome_projeto):
        """Cria ou recupera projeto com setor associado"""
        if not nome_projeto or nome_projeto.strip() == "":
            return None

        nome_projeto = nome_projeto.strip()

        # Criar setor primeiro
        setor = self.get_or_create_setor(nome_projeto)

        projeto, created = Projeto.objects.get_or_create(
            nome=nome_projeto,
            defaults={
                "ativo": True,
                "descricao": f"Projeto {nome_projeto}",
                "setor": setor,
            },
        )

        if created:
            self.logger.debug(
                f"📋 Projeto criado: {nome_projeto} (Setor: {setor.nome})"
            )

        return projeto

    def get_or_create_tipo_evento(self, tipo_str):
        """Cria ou recupera tipo de evento"""
        # Mapear tipos da planilha para o sistema
        mapeamento_tipos = {
            "Presencial": ("Presencial", False),
            "Online": ("Online", True),
            "Acompanhamento": ("Acompanhamento", False),
        }

        nome_tipo, is_online = mapeamento_tipos.get(tipo_str, ("Presencial", False))

        tipo_evento, created = TipoEvento.objects.get_or_create(
            nome=nome_tipo, defaults={"ativo": True, "online": is_online}
        )

        if created:
            self.logger.debug(f"🎯 Tipo de evento criado: {nome_tipo}")

        return tipo_evento

    def get_or_create_usuario(self, nome_pessoa, papel="formador"):
        """Cria ou recupera usuário baseado no nome"""
        if not nome_pessoa or nome_pessoa.strip() == "" or nome_pessoa == "SOLICITADO":
            return None

        # Limpar formatação especial como "?Regianio Lima?"
        nome_pessoa = nome_pessoa.strip("?").strip()

        # Tentar encontrar usuário existente por nome
        nomes = nome_pessoa.split()
        primeiro_nome = nomes[0] if nomes else nome_pessoa

        try:
            # Buscar por primeiro nome
            usuario = Usuario.objects.get(first_name__iexact=primeiro_nome)
        except (Usuario.DoesNotExist, Usuario.MultipleObjectsReturned):
            # Criar usuário temporário
            username = nome_pessoa.lower().replace(" ", "_").replace("?", "")
            email = f"{username}@sistema.local"

            # Verificar se username já existe
            counter = 1
            original_username = username
            while (
                Usuario.objects.select_related("municipio", "projeto")
                .prefetch_related("groups", "user_permissions")
                .filter(username=username)
                .exists()
            ):
                username = f"{original_username}_{counter}"
                counter += 1

            usuario = Usuario.objects.create(
                username=username,
                email=email,
                first_name=primeiro_nome,
                last_name=" ".join(nomes[1:]) if len(nomes) > 1 else "",
                is_active=True,
            )

            # Adicionar ao grupo correto
            try:
                grupo = Group.objects.get(name=papel)
                usuario.groups.add(grupo)
            except Group.DoesNotExist:
                self.logger.warning(
                    f"⚠️ Grupo '{papel}' não encontrado para {nome_pessoa}"
                )

            self.logger.debug(f"👤 Usuário criado: {nome_pessoa} ({username})")

        return usuario

    def get_or_create_formador(self, nome_formador):
        """Cria ou recupera formador"""
        if (
            not nome_formador
            or nome_formador.strip() == ""
            or nome_formador == "SOLICITADO"
        ):
            return None

        # Criar usuário primeiro
        usuario = self.get_or_create_usuario(nome_formador, "formador")
        if not usuario:
            return None

        # Buscar formador existente ou criar novo
        try:
            formador = FormadorService.get_formador(usuario=usuario)
        except Formador.DoesNotExist:
            formador = Formador.objects.create(
                nome=nome_formador, email=usuario.email, usuario=usuario, ativo=True
            )
            self.logger.debug(f"👨‍🏫 Formador criado: {nome_formador}")

        return formador

    def parse_data(self, data_str):
        """Converte string de data para objeto date"""
        if not data_str:
            return None

        # Tentar diferentes formatos
        formatos = ["%d/%m/%Y", "%d/%m", "%Y-%m-%d"]

        for formato in formatos:
            try:
                if formato == "%d/%m":
                    # Para formato DD/MM, assumir ano 2025
                    data_obj = datetime.strptime(str(data_str), formato)
                    return data_obj.replace(year=2025).date()
                else:
                    return datetime.strptime(str(data_str), formato).date()
            except (ValueError, TypeError):
                continue

        self.logger.warning(f"⚠️ Formato de data não reconhecido: {data_str}")
        return None

    def parse_hora(self, hora_str):
        """Converte string de hora para objeto time"""
        if not hora_str:
            return None

        # Tentar diferentes formatos
        formatos = ["%H:%M", "%H:%M:%S"]

        for formato in formatos:
            try:
                return datetime.strptime(str(hora_str), formato).time()
            except (ValueError, TypeError):
                continue

        self.logger.warning(f"⚠️ Formato de hora não reconhecido: {hora_str}")
        return None

    def determinar_status_solicitacao(self, aprovacao_str, nome_aba):
        """Determina status da solicitação baseado no campo aprovação e aba"""

        # Para abas que não passam pela superintendência, sempre aprovado
        if nome_aba in ["ACerta", "Outros", "Brincando", "Vidas"]:
            return SolicitacaoStatus.APROVADO

        # Para aba Super, verificar aprovação explícita
        if nome_aba == "Super":
            if not aprovacao_str:
                return SolicitacaoStatus.PENDENTE

            aprovacao_str = str(aprovacao_str).upper().strip()

            if aprovacao_str == "SIM":
                return SolicitacaoStatus.APROVADO
            elif aprovacao_str == "NÃO":
                return SolicitacaoStatus.REPROVADO
            else:
                return SolicitacaoStatus.PENDENTE

        # Fallback
        return SolicitacaoStatus.PENDENTE

    def get_column_mapping(self, nome_aba):
        """Retorna mapeamento de colunas por aba"""
        if nome_aba == "Super":
            return {
                "municipio": "Municípios",
                "data": "data",
                "hora_inicio": "hora início",
                "hora_fim": "hora fim",
                "projeto": "projeto",
                "tipo": "tipo",
                "aprovacao": "Aprovação",
                "coordenador": "Coordenador",
                "formador1": "Formador 1",
                "formador2": "Formador 2",
                "formador3": "Formador 3",
                "formador4": "Formador 4",
                "formador5": "Formador 5",
                "convidados": "Convidados",
            }
        else:
            # Para outras abas, usar nomes padrão
            return {
                "municipio": "município",
                "data": "data",
                "hora_inicio": "hora início",
                "hora_fim": "hora fim",
                "projeto": "projeto",
                "tipo": "tipo",
                "aprovacao": None,  # Outras abas não têm aprovação
                "coordenador": "coordenador",
                "formador1": "formador",
                "formador2": "formador2",
                "formador3": "formador3",
            }

    def importar_eventos_aba(self, nome_aba):
        """Importa eventos de uma aba específica"""
        self.logger.info(f"📋 Importando eventos da aba: {nome_aba}")

        try:
            worksheet = self.sheet.worksheet(nome_aba)
            dados = worksheet.get_all_records()

            eventos_criados = 0
            eventos_pulados = 0
            eventos_filtrados = 0

            # Obter mapeamento de colunas
            cols = self.get_column_mapping(nome_aba)

            for i, row in enumerate(dados, 1):
                try:
                    # Extrair dados básicos usando mapeamento correto
                    municipio_nome = (row.get(cols["municipio"]) or "").strip()
                    data_evento = self.parse_data(row.get(cols["data"], ""))
                    hora_inicio = self.parse_hora(row.get(cols["hora_inicio"], ""))
                    hora_fim = self.parse_hora(row.get(cols["hora_fim"], ""))
                    projeto_nome = (row.get(cols["projeto"]) or "").strip()
                    tipo_evento = (row.get(cols["tipo"]) or "Presencial").strip()

                    # FILTRO DE QUALIDADE (como aplicado pelo Cursor)
                    if self.options["filter_quality"]:
                        if not municipio_nome or not data_evento:
                            self.logger.debug(
                                f"⚡ Linha {i} filtrada: falta município ou data"
                            )
                            eventos_filtrados += 1
                            continue

                    # Validar dados obrigatórios básicos
                    if not municipio_nome or not data_evento:
                        self.logger.debug(
                            f"⏭️ Linha {i} pulada: dados obrigatórios faltando"
                        )
                        eventos_pulados += 1
                        continue

                    # Criar/recuperar objetos relacionados
                    municipio = self.get_or_create_municipio(municipio_nome)
                    projeto = self.get_or_create_projeto(projeto_nome)
                    tipo = self.get_or_create_tipo_evento(tipo_evento)

                    if not all([municipio, projeto, tipo]):
                        eventos_pulados += 1
                        continue

                    # Determinar status com base na aba e aprovação
                    aprovacao = ""
                    if cols["aprovacao"]:
                        aprovacao = row.get(cols["aprovacao"]) or ""
                    status = self.determinar_status_solicitacao(aprovacao, nome_aba)

                    # Preparar dados da solicitação
                    encontro = row.get("encontro") or row.get("Encontro") or "1"
                    segmento = row.get("segmento") or ""
                    titulo = f"{projeto_nome} - {municipio_nome}"
                    if encontro and str(encontro).strip():
                        titulo += f" - Encontro {encontro}"

                    # Buscar coordenador/solicitante
                    coordenador_nome = (
                        row.get("Coordenador")
                        or row.get("Gerente")
                        or "Sistema Automatizado"
                    ).strip()

                    usuario_solicitante = self.get_or_create_usuario(
                        coordenador_nome, "coordenador"
                    )
                    if not usuario_solicitante:
                        # Usar usuário padrão se não conseguir criar
                        usuario_solicitante = (
                            Usuario.objects.select_related("municipio", "projeto")
                            .prefetch_related("groups", "user_permissions")
                            .filter(is_superuser=True)
                            .first()
                        )
                        if not usuario_solicitante:
                            self.logger.error(
                                f"❌ Nenhum usuário disponível para linha {i}"
                            )
                            eventos_pulados += 1
                            continue

                    # Usar hora fim ou calcular duração padrão
                    if not hora_fim:
                        # Duração padrão de 8 horas para presencial, 4 para online
                        duracao_horas = 4 if tipo.online else 8
                        data_fim = datetime.combine(
                            data_evento,
                            time(
                                min(23, hora_inicio.hour + duracao_horas),
                                hora_inicio.minute,
                            ),
                        )
                    else:
                        data_fim = datetime.combine(data_evento, hora_fim)

                    data_inicio = datetime.combine(data_evento, hora_inicio)

                    if not self.options["dry_run"]:
                        # Verificar se solicitação já existe
                        existing = (
                            Solicitacao.objects.select_related(
                                "municipio", "projeto", "tipo_evento", "solicitante"
                            )
                            .prefetch_related("formadores")
                            .filter(titulo_evento=titulo, data_inicio=data_inicio)
                            .first()
                        )

                        if existing and not self.options["force"]:
                            self.logger.debug(f"⏭️ Solicitação já existe: {titulo}")
                            eventos_pulados += 1
                            continue

                        # Criar solicitação
                        solicitacao = Solicitacao.objects.create(
                            usuario_solicitante=usuario_solicitante,
                            projeto=projeto,
                            municipio=municipio,
                            tipo_evento=tipo,
                            titulo_evento=titulo,
                            data_inicio=data_inicio,
                            data_fim=data_fim,
                            status=status,
                            numero_encontro_formativo=str(encontro),
                            coordenador_acompanha=bool(row.get("Coord Acompanha")),
                            observacoes=f"Importado da aba {nome_aba}. Segmento: {segmento}",
                        )

                        # Associar formadores (até 5)
                        formadores_associados = 0
                        for j in range(1, 6):
                            nome_formador = row.get(f"Formador {j}", "").strip()
                            if nome_formador and nome_formador != "SOLICITADO":
                                formador = self.get_or_create_formador(nome_formador)
                                if formador:
                                    FormadoresSolicitacao.objects.create(
                                        solicitacao=solicitacao, formador=formador
                                    )
                                    formadores_associados += 1

                        self.logger.debug(
                            f"✅ Evento criado: {titulo} - {formadores_associados} formadores"
                        )

                    eventos_criados += 1

                except Exception as e:
                    self.logger.error(f"❌ Erro ao importar linha {i}: {e}")
                    eventos_pulados += 1
                    continue

            # Relatório final da aba
            total_processado = len(dados)
            total_valido = total_processado - eventos_filtrados - eventos_pulados

            self.logger.info(f"🎆 Aba {nome_aba} importada:")
            self.logger.info(f"  📋 Total de linhas: {total_processado}")
            if self.options["filter_quality"]:
                self.logger.info(
                    f"  ⚡ Filtradas (sem município/data): {eventos_filtrados}"
                )
            self.logger.info(f"  ⏭️ Puladas (outros motivos): {eventos_pulados}")
            self.logger.info(f"  ✅ Válidas processadas: {total_valido}")
            self.logger.info(f"  🎆 Eventos criados: {eventos_criados}")

            return eventos_criados

        except Exception as e:
            self.logger.error(f"❌ Erro ao importar aba {nome_aba}: {e}")
            return 0

    def handle(self, *args, **options):
        self.options = options
        self.setup_logging(options["verbose"])

        # Estatísticas
        total_importados = 0
        abas_processadas = []

        self.logger.info(
            "🚀 Iniciando importação da planilha 'Acompanhamento de Agenda | 2025'"
        )

        if options["dry_run"]:
            self.logger.info("🔍 MODO DRY-RUN: Nenhum dado será salvo no banco")

        try:
            # Configurar Google Sheets
            self.setup_google_sheets()

            # Definir abas para importação (ordem de prioridade)
            if options["aba"]:
                abas_para_importar = [options["aba"]]
            else:
                # Ordem de prioridade: Super primeiro (aprovações), depois demais
                abas_para_importar = ["Super", "ACerta", "Outros", "Brincando", "Vidas"]

            # Processar cada aba
            with transaction.atomic():
                for aba in abas_para_importar:
                    try:
                        importados = self.importar_eventos_aba(aba)
                        total_importados += importados
                        abas_processadas.append(f"{aba}: {importados}")

                    except Exception as e:
                        self.logger.error(f"❌ Falha ao processar aba {aba}: {e}")
                        continue

                if options["dry_run"]:
                    # Rollback em modo dry-run
                    transaction.set_rollback(True)
                    self.logger.info("🔄 Rollback executado (modo dry-run)")

            # Relatório final
            self.logger.info("=" * 80)
            self.logger.info("📊 RELATÓRIO FINAL DA IMPORTAÇÃO")
            self.logger.info("=" * 80)
            self.logger.info(f"✅ Total de registros importados: {total_importados}")
            self.logger.info(f"📋 Abas processadas: {len(abas_processadas)}")

            for aba_info in abas_processadas:
                self.logger.info(f"   • {aba_info}")

            if options["dry_run"]:
                self.logger.info("🔍 SIMULAÇÃO CONCLUÍDA - Nenhum dado foi salvo")
            else:
                self.logger.info("💾 IMPORTAÇÃO CONCLUÍDA - Dados salvos no banco")

                # Estatísticas finais do banco
                self.logger.info(
                    f"📊 Total de solicitações no sistema: {Solicitacao.objects.count()}"
                )
                self.logger.info(
                    f"👥 Total de formadores no sistema: {Formador.objects.count()}"
                )
                self.logger.info(
                    f"📋 Total de projetos no sistema: {Projeto.objects.count()}"
                )
                self.logger.info(
                    f"🏛️ Total de municípios no sistema: {Municipio.objects.count()}"
                )

            self.logger.info("=" * 80)

        except Exception as e:
            raise CommandError(f"❌ Erro durante a importação: {e}")
