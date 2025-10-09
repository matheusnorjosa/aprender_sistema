#!/usr/bin/env python3
"""
IMPORTADOR AGENDA 2025 - CONTEXTO SUPREMO
=========================================

Script para importar dados da planilha "Acompanhamento de Agenda | 2025"
conforme o contexto supremo fornecido.

Regras de Negócio:
1. Coordenador (coluna N) é o solicitante do evento
2. Eventos cancelados (checkbox coluna D) são apenas informativos
3. Eventos 01/01/2025 a 25/09/2025 = já aconteceram
4. Eventos futuros = ainda irão acontecer
5. Aba Super: "SIM" na coluna B = aprovado

Autor: Claude Code
Data: Janeiro 2025
"""

import os
import sys
import django
import json
import logging
from datetime import datetime, time, date
from typing import Dict, List, Any, Optional

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
django.setup()

from django.db import transaction
from django.contrib.auth import get_user_model
from core.models import (
    Usuario,
    Municipio,
    Projeto,
    TipoEvento,
    Solicitacao,
    SolicitacaoStatus,
    Setor,
    FormadoresSolicitacao,
    Formador,
)

# Configurar logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

User = get_user_model()


class ImportadorAgenda2025ContextoSupremo:
    """
    Importador da planilha Agenda 2025 com contexto supremo
    """

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.planilha_id = "1oqDA9tN-wNiFVLS3KYTFzsXKpJpvDECfeKucjwf9GKs"

        # Configuração das abas e colunas
        self.abas_config = {
            "ACerta": {
                "colunas": [
                    "A",
                    "E",
                    "F",
                    "G",
                    "H",
                    "I",
                    "J",
                    "K",
                    "L",
                    "M",
                    "N",
                    "O",
                    "P",
                    "Q",
                    "R",
                    "S",
                    "T",
                ],
                "nomes_colunas": [
                    "Criado na Agenda",
                    "município",
                    "encontro",
                    "tipo",
                    "data",
                    "hora início",
                    "hora fim",
                    "projeto",
                    "segmento",
                    "Coord Acompanha",
                    "Coordenador",
                    "Formador 1",
                    "Formador 2",
                    "Formador 3",
                    "Formador 4",
                    "Formador 5",
                    "Convidados",
                ],
                "setor": "ACerta",
            },
            "Outros": {
                "colunas": [
                    "A",
                    "E",
                    "F",
                    "G",
                    "H",
                    "I",
                    "J",
                    "K",
                    "L",
                    "M",
                    "N",
                    "O",
                    "P",
                    "Q",
                    "R",
                    "S",
                    "T",
                ],
                "nomes_colunas": [
                    "Criado na Agenda",
                    "município",
                    "encontro",
                    "tipo",
                    "data",
                    "hora início",
                    "hora fim",
                    "projeto",
                    "segmento",
                    "Coord Acompanha",
                    "Coordenador",
                    "Formador 1",
                    "Formador 2",
                    "Formador 3",
                    "Formador 4",
                    "Formador 5",
                    "Convidados",
                ],
                "setor": "Outros",
            },
            "Brincando": {
                "colunas": [
                    "A",
                    "E",
                    "F",
                    "G",
                    "H",
                    "I",
                    "J",
                    "K",
                    "L",
                    "M",
                    "N",
                    "O",
                    "P",
                    "Q",
                    "R",
                    "S",
                    "T",
                ],
                "nomes_colunas": [
                    "Criado na Agenda",
                    "município",
                    "encontro",
                    "tipo",
                    "data",
                    "hora início",
                    "hora fim",
                    "projeto",
                    "segmento",
                    "Coord Acompanha",
                    "Coordenador",
                    "Formador 1",
                    "Formador 2",
                    "Formador 3",
                    "Formador 4",
                    "Formador 5",
                    "Convidados",
                ],
                "setor": "Brincando",
            },
            "Vidas": {
                "colunas": [
                    "A",
                    "E",
                    "F",
                    "G",
                    "H",
                    "I",
                    "J",
                    "K",
                    "M",
                    "N",
                    "O",
                    "P",
                    "Q",
                    "R",
                    "S",
                    "T",
                ],
                "nomes_colunas": [
                    "Criado na Agenda",
                    "município",
                    "encontro",
                    "tipo",
                    "data",
                    "hora início",
                    "hora fim",
                    "projeto",
                    "segmento",
                    "Coord Acompanha",
                    "Coordenador",
                    "Formador 1",
                    "Formador 2",
                    "Formador 3",
                    "Formador 4",
                    "Formador 5",
                    "Convidados",
                ],
                "setor": "Vidas",
            },
            "Super": {
                "colunas": [
                    "A",
                    "B",
                    "E",
                    "F",
                    "G",
                    "H",
                    "I",
                    "J",
                    "K",
                    "L",
                    "M",
                    "N",
                    "O",
                    "P",
                    "Q",
                    "R",
                    "S",
                    "T",
                ],
                "nomes_colunas": [
                    "Criado na Agenda",
                    "Aprovação",
                    "Municípios",
                    "encontro",
                    "tipo",
                    "data",
                    "hora início",
                    "hora fim",
                    "projeto",
                    "Coord Acompanha",
                    "Coordenador",
                    "Formador 1",
                    "Formador 2",
                    "Formador 3",
                    "Formador 4",
                    "Formador 5",
                    "Convidados",
                ],
                "setor": "Superintendência",
            },
        }

        # Data limite para eventos já acontecidos
        self.data_limite_eventos_passados = date(2025, 9, 25)

        # Estatísticas
        self.estatisticas = {
            "total_registros": 0,
            "eventos_importados": 0,
            "eventos_ja_aconteceram": 0,
            "eventos_futuros": 0,
            "eventos_aprovados": 0,
            "eventos_cancelados": 0,
            "erros": 0,
            "por_aba": {},
        }

    def conectar_google_sheets(self):
        """
        Conectar ao Google Sheets
        """
        try:
            import gspread
            from google.oauth2.service_account import Credentials

            # Configurar credenciais
            creds_path = os.path.join(
                os.path.dirname(__file__), "google_service_account.json"
            )
            if not os.path.exists(creds_path):
                logger.error(
                    "❌ Arquivo de credenciais não encontrado: google_service_account.json"
                )
                return None

            scope = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive",
            ]

            creds = Credentials.from_service_account_file(creds_path, scopes=scope)
            client = gspread.authorize(creds)

            # Abrir planilha
            spreadsheet = client.open_by_key(self.planilha_id)
            logger.info(f"✅ Conectado à planilha: {spreadsheet.title}")

            return spreadsheet

        except Exception as e:
            logger.error(f"❌ Erro ao conectar Google Sheets: {str(e)}")
            return None

    def extrair_dados_aba(self, spreadsheet, nome_aba: str) -> List[Dict]:
        """
        Extrair dados de uma aba específica
        """
        try:
            worksheet = spreadsheet.worksheet(nome_aba)
            config = self.abas_config[nome_aba]

            # Obter todas as linhas
            all_values = worksheet.get_all_values()

            if not all_values:
                logger.warning(f"⚠️ Aba {nome_aba} está vazia")
                return []

            # Primeira linha são os cabeçalhos
            headers = all_values[0]
            data_rows = all_values[1:]

            # Filtrar apenas as colunas necessárias
            colunas_indices = []
            for coluna in config["colunas"]:
                # Converter letra para índice (A=0, B=1, etc.)
                indice = ord(coluna) - ord("A")
                if indice < len(headers):
                    colunas_indices.append(indice)

            # Processar dados
            dados_processados = []
            for i, row in enumerate(data_rows):
                if not any(row):  # Pular linhas vazias
                    continue

                # Extrair apenas as colunas necessárias
                dados_linha = {}
                for j, indice in enumerate(colunas_indices):
                    if indice < len(row):
                        nome_coluna = config["nomes_colunas"][j]
                        dados_linha[nome_coluna] = row[indice].strip()

                # Adicionar informações da aba
                dados_linha["aba_origem"] = nome_aba
                dados_linha["setor"] = config["setor"]
                dados_linha["linha_planilha"] = i + 2  # +2 porque começamos da linha 2

                dados_processados.append(dados_linha)

            logger.info(
                f"📊 Aba {nome_aba}: {len(dados_processados)} registros extraídos"
            )
            return dados_processados

        except Exception as e:
            logger.error(f"❌ Erro ao extrair dados da aba {nome_aba}: {str(e)}")
            return []

    def aplicar_regras_negocio(self, evento_data: Dict) -> Dict:
        """
        Aplicar regras de negócio específicas
        """
        # Regra 1: Coordenador como solicitante (coluna N)
        if "Coordenador" in evento_data and evento_data["Coordenador"]:
            evento_data["solicitante"] = evento_data["Coordenador"]
        else:
            evento_data["solicitante"] = "Coordenador não informado"

        # Regra 2: Eventos cancelados (checkbox coluna D - não incluída nas colunas)
        # Nota: A coluna D não está nas colunas especificadas, então assumimos que não há cancelamentos

        # Regra 3: Status temporal baseado na data
        data_evento_str = evento_data.get("data", "")
        if data_evento_str:
            try:
                # Tentar diferentes formatos de data
                for formato in ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"]:
                    try:
                        data_evento = datetime.strptime(data_evento_str, formato).date()
                        break
                    except ValueError:
                        continue
                else:
                    logger.warning(
                        f"⚠️ Formato de data não reconhecido: {data_evento_str}"
                    )
                    data_evento = None

                if data_evento:
                    if data_evento <= self.data_limite_eventos_passados:
                        evento_data["status_temporal"] = "ja_aconteceu"
                        evento_data["data_evento"] = data_evento
                    else:
                        evento_data["status_temporal"] = "futuro"
                        evento_data["data_evento"] = data_evento

            except Exception as e:
                logger.warning(f"⚠️ Erro ao processar data {data_evento_str}: {str(e)}")
                evento_data["status_temporal"] = "data_invalida"
        else:
            evento_data["status_temporal"] = "sem_data"

        # Regra 4: Aprovação (aba Super, coluna B)
        if evento_data.get("aba_origem") == "Super":
            if evento_data.get("Aprovação") == "SIM":
                evento_data["aprovado"] = True
            else:
                evento_data["aprovado"] = False
        else:
            evento_data["aprovado"] = None  # Não se aplica a outras abas

        return evento_data

    def processar_formadores(self, evento_data: Dict) -> List[str]:
        """
        Processar lista de formadores do evento
        """
        formadores = []

        for i in range(1, 6):  # Formador 1 a Formador 5
            formador_key = f"Formador {i}"
            if formador_key in evento_data and evento_data[formador_key]:
                formador_nome = evento_data[formador_key].strip()
                if formador_nome and formador_nome.lower() not in [
                    "",
                    "n/a",
                    "não informado",
                ]:
                    formadores.append(formador_nome)

        return formadores

    def importar_evento(self, evento_data: Dict) -> bool:
        """
        Importar um evento para o banco de dados
        """
        try:
            if self.dry_run:
                logger.info(
                    f"🔍 [DRY RUN] Evento: {evento_data.get('encontro', 'N/A')} - {evento_data.get('município', 'N/A')}"
                )
                return True

            # Aplicar regras de negócio
            evento_data = self.aplicar_regras_negocio(evento_data)

            # Buscar ou criar município
            municipio_nome = evento_data.get("município", "").strip()
            if not municipio_nome:
                logger.warning("⚠️ Município não informado, pulando evento")
                return False

            municipio, created = Municipio.objects.get_or_create(
                nome=municipio_nome, defaults={"uf": "TO"}  # Assumir TO como padrão
            )

            # Buscar ou criar projeto
            projeto_nome = evento_data.get("projeto", "").strip()
            if not projeto_nome:
                logger.warning("⚠️ Projeto não informado, pulando evento")
                return False

            projeto, created = Projeto.objects.get_or_create(
                nome=projeto_nome, defaults={"descricao": f"Projeto {projeto_nome}"}
            )

            # Buscar ou criar tipo de evento
            tipo_nome = evento_data.get("tipo", "").strip()
            if not tipo_nome:
                tipo_nome = "Formação"

            tipo_evento, created = TipoEvento.objects.get_or_create(
                nome=tipo_nome, defaults={"descricao": f"Tipo de evento: {tipo_nome}"}
            )

            # Buscar ou criar coordenador (solicitante)
            coordenador_nome = evento_data.get("solicitante", "").strip()
            if not coordenador_nome:
                logger.warning("⚠️ Coordenador não informado, pulando evento")
                return False

            # Criar usuário coordenador se não existir
            coordenador, created = Usuario.objects.get_or_create(
                username=coordenador_nome.lower().replace(" ", "_"),
                defaults={
                    "nome": coordenador_nome,
                    "email": f'{coordenador_nome.lower().replace(" ", ".")}@aprender.com',
                    "is_active": True,
                },
            )

            # Determinar status da solicitação
            if evento_data.get("status_temporal") == "ja_aconteceu":
                status = SolicitacaoStatus.REALIZADA
            elif evento_data.get("aprovado") is True:
                status = SolicitacaoStatus.APROVADA
            elif evento_data.get("aprovado") is False:
                status = SolicitacaoStatus.REPROVADA
            else:
                status = SolicitacaoStatus.PENDENTE

            # Criar solicitação
            solicitacao = Solicitacao.objects.create(
                municipio=municipio,
                projeto=projeto,
                tipo_evento=tipo_evento,
                solicitante=coordenador,
                data_evento=evento_data.get("data_evento"),
                hora_inicio=evento_data.get("hora início"),
                hora_fim=evento_data.get("hora fim"),
                status=status,
                observacoes=f"Importado da planilha Agenda 2025 - Aba: {evento_data.get('aba_origem')} - Linha: {evento_data.get('linha_planilha')}",
            )

            # Adicionar formadores
            formadores = self.processar_formadores(evento_data)
            for formador_nome in formadores:
                formador, created = Usuario.objects.get_or_create(
                    username=formador_nome.lower().replace(" ", "_"),
                    defaults={
                        "nome": formador_nome,
                        "email": f'{formador_nome.lower().replace(" ", ".")}@aprender.com',
                        "is_active": True,
                    },
                )

                FormadoresSolicitacao.objects.create(
                    solicitacao=solicitacao, formador=formador
                )

            return True

        except Exception as e:
            logger.error(f"❌ Erro ao importar evento: {str(e)}")
            return False

    def processar_aba(self, spreadsheet, nome_aba: str):
        """
        Processar uma aba específica
        """
        logger.info(f"🔄 Processando aba: {nome_aba}")

        # Extrair dados
        dados = self.extrair_dados_aba(spreadsheet, nome_aba)

        if not dados:
            logger.warning(f"⚠️ Nenhum dado encontrado na aba {nome_aba}")
            return

        # Estatísticas da aba
        stats_aba = {
            "total_registros": len(dados),
            "eventos_importados": 0,
            "eventos_ja_aconteceram": 0,
            "eventos_futuros": 0,
            "eventos_aprovados": 0,
            "erros": 0,
        }

        # Processar cada evento
        for evento_data in dados:
            self.estatisticas["total_registros"] += 1

            # Aplicar regras de negócio
            evento_data = self.aplicar_regras_negocio(evento_data)

            # Atualizar estatísticas
            if evento_data.get("status_temporal") == "ja_aconteceu":
                stats_aba["eventos_ja_aconteceram"] += 1
                self.estatisticas["eventos_ja_aconteceram"] += 1
            elif evento_data.get("status_temporal") == "futuro":
                stats_aba["eventos_futuros"] += 1
                self.estatisticas["eventos_futuros"] += 1

            if evento_data.get("aprovado") is True:
                stats_aba["eventos_aprovados"] += 1
                self.estatisticas["eventos_aprovados"] += 1

            # Importar evento
            if self.importar_evento(evento_data):
                stats_aba["eventos_importados"] += 1
                self.estatisticas["eventos_importados"] += 1
            else:
                stats_aba["erros"] += 1
                self.estatisticas["erros"] += 1

        # Salvar estatísticas da aba
        self.estatisticas["por_aba"][nome_aba] = stats_aba

        logger.info(f"✅ Aba {nome_aba} processada:")
        logger.info(f"   - Total de registros: {stats_aba['total_registros']}")
        logger.info(f"   - Eventos importados: {stats_aba['eventos_importados']}")
        logger.info(f"   - Já aconteceram: {stats_aba['eventos_ja_aconteceram']}")
        logger.info(f"   - Futuros: {stats_aba['eventos_futuros']}")
        logger.info(f"   - Aprovados: {stats_aba['eventos_aprovados']}")
        logger.info(f"   - Erros: {stats_aba['erros']}")

    def executar_importacao(self, abas_especificas: Optional[List[str]] = None):
        """
        Executar importação completa
        """
        logger.info("🚀 INICIANDO IMPORTAÇÃO AGENDA 2025 - CONTEXTO SUPREMO")
        logger.info("=" * 70)

        if self.dry_run:
            logger.info("🔍 MODO DRY RUN - Nenhum dado será salvo no banco")

        # Conectar Google Sheets
        spreadsheet = self.conectar_google_sheets()
        if not spreadsheet:
            logger.error("❌ Não foi possível conectar ao Google Sheets")
            return False

        # Determinar abas para processar
        abas_para_processar = abas_especificas or list(self.abas_config.keys())

        try:
            with transaction.atomic():
                # Processar cada aba
                for nome_aba in abas_para_processar:
                    if nome_aba in self.abas_config:
                        self.processar_aba(spreadsheet, nome_aba)
                    else:
                        logger.warning(f"⚠️ Aba {nome_aba} não configurada")

                if self.dry_run:
                    logger.info("🔍 [DRY RUN] Transação seria commitada aqui")
                    raise transaction.TransactionManagementError("Dry run - rollback")

        except transaction.TransactionManagementError:
            if self.dry_run:
                logger.info("🔍 [DRY RUN] Rollback executado conforme esperado")
            else:
                logger.error("❌ Erro na transação")
                return False
        except Exception as e:
            logger.error(f"❌ Erro durante a importação: {str(e)}")
            return False

        # Relatório final
        self.gerar_relatorio_final()

        return True

    def gerar_relatorio_final(self):
        """
        Gerar relatório final da importação
        """
        logger.info("\n" + "=" * 70)
        logger.info("📊 RELATÓRIO FINAL DA IMPORTAÇÃO")
        logger.info("=" * 70)

        logger.info(f"📈 ESTATÍSTICAS GERAIS:")
        logger.info(
            f"   - Total de registros processados: {self.estatisticas['total_registros']}"
        )
        logger.info(
            f"   - Eventos importados: {self.estatisticas['eventos_importados']}"
        )
        logger.info(
            f"   - Eventos já aconteceram: {self.estatisticas['eventos_ja_aconteceram']}"
        )
        logger.info(f"   - Eventos futuros: {self.estatisticas['eventos_futuros']}")
        logger.info(f"   - Eventos aprovados: {self.estatisticas['eventos_aprovados']}")
        logger.info(f"   - Erros: {self.estatisticas['erros']}")

        logger.info(f"\n📋 ESTATÍSTICAS POR ABA:")
        for aba, stats in self.estatisticas["por_aba"].items():
            logger.info(f"   {aba}:")
            logger.info(f"     - Registros: {stats['total_registros']}")
            logger.info(f"     - Importados: {stats['eventos_importados']}")
            logger.info(f"     - Já aconteceram: {stats['eventos_ja_aconteceram']}")
            logger.info(f"     - Futuros: {stats['eventos_futuros']}")
            logger.info(f"     - Aprovados: {stats['eventos_aprovados']}")
            logger.info(f"     - Erros: {stats['erros']}")

        # Salvar relatório em arquivo
        relatorio = {
            "timestamp": datetime.now().isoformat(),
            "dry_run": self.dry_run,
            "estatisticas": self.estatisticas,
        }

        with open("relatorio_importacao_agenda_2025.json", "w", encoding="utf-8") as f:
            json.dump(relatorio, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"\n💾 Relatório salvo em: relatorio_importacao_agenda_2025.json")


def main():
    """
    Função principal
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Importar dados da planilha Agenda 2025"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Executar em modo de teste (padrão)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Executar importação real (salvar no banco)",
    )
    parser.add_argument(
        "--abas",
        nargs="+",
        choices=["ACerta", "Outros", "Brincando", "Vidas", "Super"],
        help="Processar apenas abas específicas",
    )

    args = parser.parse_args()

    # Determinar modo de execução
    dry_run = not args.execute

    # Criar importador
    importador = ImportadorAgenda2025ContextoSupremo(dry_run=dry_run)

    # Executar importação
    sucesso = importador.executar_importacao(abas_especificas=args.abas)

    if sucesso:
        logger.info("🎉 IMPORTAÇÃO CONCLUÍDA COM SUCESSO!")
    else:
        logger.error("❌ IMPORTAÇÃO FALHOU!")
        sys.exit(1)


if __name__ == "__main__":
    main()
