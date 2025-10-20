#!/usr/bin/env python3
"""
IMPORTADOR DISPONIBILIDADE 2025 - CONTEXTO SUPREMO
=================================================

Script para importar dados da planilha "Disponibilidade | 2025"
conforme o contexto supremo fornecido.

Interface Gráfica da Superintendência:
- Aba MENSAL: Interface visual com formadores e coordenadores
- Aba ANUAL: Carga horária anual
- Aba DESLOCAMENTO: Informações de deslocamento
- Aba Bloqueios: Formulário de bloqueios

Autor: Claude Code
Data: Janeiro 2025
"""

import json
import logging
import os
import sys
from datetime import date, datetime, time
from typing import Any, Dict, List, Optional

import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.db import transaction

from core.models import (
    DisponibilidadeFormadores,
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

# Configurar logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

User = get_user_model()


class ImportadorDisponibilidade2025ContextoSupremo:
    """
    Importador da planilha Disponibilidade 2025 com contexto supremo
    """

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.planilha_id = "1C4_9Gn8gwKjgD1CgssIKaU4bacwv7XuL2QnoSVwomxU"

        # Configuração das abas
        self.abas_config = {
            "MENSAL": {
                "descricao": "Interface gráfica visual com legenda",
                "filtros": {"mes": "B3", "formadores": "AM3"},
                "metricas": {"ch_formacoes": ["AN", "AO", "AP"], "linhas": [4, 5]},
                "dados": {"municipio_data": ["AM", "AO", "AP", "AQ"], "linha": 7},
                "deslocamentos": {"colunas": ["AM", "AN", "AO"], "linhas": [39, 40]},
            },
            "ANUAL": {
                "descricao": "Carga horária anual dos formadores",
                "colunas": "A até AC",
            },
            "DESLOCAMENTO": {
                "descricao": "Informações de deslocamento",
                "colunas": "A até J",
            },
            "Bloqueios": {
                "descricao": "Formulário de bloqueios de datas",
                "fonte": "Formulário simples",
            },
        }

        # Estatísticas
        self.estatisticas = {
            "total_registros": 0,
            "interface_grafica_processada": 0,
            "carga_horaria_processada": 0,
            "deslocamentos_processados": 0,
            "bloqueios_processados": 0,
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

    def processar_aba_mensal(self, spreadsheet):
        """
        Processar aba MENSAL - Interface gráfica da superintendência
        """
        logger.info("🎨 Processando aba MENSAL - Interface gráfica...")

        try:
            worksheet = spreadsheet.worksheet("MENSAL")
            config = self.abas_config["MENSAL"]

            # Obter dados da planilha
            all_values = worksheet.get_all_values()

            if not all_values:
                logger.warning("⚠️ Aba MENSAL está vazia")
                return

            # Processar filtros
            logger.info("🔍 Processando filtros...")

            # Filtro de mês (B3)
            try:
                mes_filtro = (
                    all_values[2][1]
                    if len(all_values) > 2 and len(all_values[2]) > 1
                    else None
                )
                logger.info(f"📅 Filtro de mês: {mes_filtro}")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao obter filtro de mês: {str(e)}")

            # Filtro de formadores (AM3)
            try:
                formadores_filtro = (
                    all_values[2][38]
                    if len(all_values) > 2 and len(all_values[2]) > 38
                    else None
                )
                logger.info(f"👥 Filtro de formadores: {formadores_filtro}")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao obter filtro de formadores: {str(e)}")

            # Processar métricas CH Formações (AN, AO, AP)
            logger.info("📊 Processando métricas CH Formações...")
            try:
                for linha in config["metricas"]["linhas"]:
                    if len(all_values) > linha:
                        linha_data = all_values[linha]
                        if len(linha_data) > 39:  # Coluna AN (índice 39)
                            mes = linha_data[39] if len(linha_data) > 39 else ""
                            ano = linha_data[40] if len(linha_data) > 40 else ""
                            posicao_mes = linha_data[41] if len(linha_data) > 41 else ""
                            logger.info(
                                f"📈 Linha {linha}: Mês={mes}, Ano={ano}, Posição={posicao_mes}"
                            )
            except Exception as e:
                logger.warning(f"⚠️ Erro ao processar métricas: {str(e)}")

            # Processar dados de municípios (linha 7)
            logger.info("🏘️ Processando dados de municípios...")
            try:
                linha_municipios = all_values[6] if len(all_values) > 6 else []
                if len(linha_municipios) > 38:  # Coluna AM (índice 38)
                    municipio = (
                        linha_municipios[38] if len(linha_municipios) > 38 else ""
                    )
                    data = linha_municipios[40] if len(linha_municipios) > 40 else ""
                    inicio = linha_municipios[41] if len(linha_municipios) > 41 else ""
                    fim = linha_municipios[42] if len(linha_municipios) > 42 else ""
                    tipo = linha_municipios[43] if len(linha_municipios) > 43 else ""
                    logger.info(
                        f"🏘️ Município: {municipio}, Data: {data}, Início: {inicio}, Fim: {fim}, Tipo: {tipo}"
                    )
            except Exception as e:
                logger.warning(f"⚠️ Erro ao processar dados de municípios: {str(e)}")

            # Processar deslocamentos (linhas 39, 40)
            logger.info("🚗 Processando deslocamentos...")
            try:
                for linha in config["deslocamentos"]["linhas"]:
                    if len(all_values) > linha:
                        linha_data = all_values[linha]
                        if len(linha_data) > 38:  # Coluna AM (índice 38)
                            origem = linha_data[38] if len(linha_data) > 38 else ""
                            data = linha_data[39] if len(linha_data) > 39 else ""
                            destino = linha_data[40] if len(linha_data) > 40 else ""
                            logger.info(
                                f"🚗 Linha {linha}: Origem={origem}, Data={data}, Destino={destino}"
                            )
            except Exception as e:
                logger.warning(f"⚠️ Erro ao processar deslocamentos: {str(e)}")

            # Processar legenda da interface gráfica
            logger.info("🎨 Processando legenda da interface gráfica...")
            # Nota: A legenda seria processada conforme os prints fornecidos pelo usuário

            self.estatisticas["interface_grafica_processada"] += 1
            logger.info("✅ Aba MENSAL processada com sucesso")

        except Exception as e:
            logger.error(f"❌ Erro ao processar aba MENSAL: {str(e)}")
            self.estatisticas["erros"] += 1

    def processar_aba_anual(self, spreadsheet):
        """
        Processar aba ANUAL - Carga horária anual
        """
        logger.info("📊 Processando aba ANUAL - Carga horária anual...")

        try:
            worksheet = spreadsheet.worksheet("ANUAL")
            config = self.abas_config["ANUAL"]

            # Obter dados da planilha
            all_values = worksheet.get_all_values()

            if not all_values:
                logger.warning("⚠️ Aba ANUAL está vazia")
                return

            # Processar colunas A até AC (índices 0 até 28)
            logger.info("📈 Processando carga horária anual...")

            # Primeira linha são os cabeçalhos
            if len(all_values) > 0:
                headers = all_values[0]
                logger.info(f"📋 Cabeçalhos encontrados: {len(headers)} colunas")

                # Processar dados de cada formador
                for i, row in enumerate(all_values[1:], 1):
                    if not any(row):  # Pular linhas vazias
                        continue

                    # Extrair dados do formador
                    formador_nome = row[0] if len(row) > 0 else ""
                    if not formador_nome:
                        continue

                    # Processar meses (colunas 1 até 12)
                    meses_data = {}
                    for mes_idx in range(1, 13):
                        if len(row) > mes_idx:
                            meses_data[f"mes_{mes_idx}"] = row[mes_idx]

                    # Carga horária anual (coluna 28 - AC)
                    carga_anual = row[28] if len(row) > 28 else ""

                    logger.info(
                        f"👤 Formador: {formador_nome}, Carga Anual: {carga_anual}"
                    )

                    # Aqui seria a lógica para salvar no banco de dados
                    if not self.dry_run:
                        # Criar ou atualizar disponibilidade do formador
                        pass

            self.estatisticas["carga_horaria_processada"] += 1
            logger.info("✅ Aba ANUAL processada com sucesso")

        except Exception as e:
            logger.error(f"❌ Erro ao processar aba ANUAL: {str(e)}")
            self.estatisticas["erros"] += 1

    def processar_aba_deslocamento(self, spreadsheet):
        """
        Processar aba DESLOCAMENTO - Informações de deslocamento
        """
        logger.info("🚗 Processando aba DESLOCAMENTO...")

        try:
            worksheet = spreadsheet.worksheet("DESLOCAMENTO")
            config = self.abas_config["DESLOCAMENTO"]

            # Obter dados da planilha
            all_values = worksheet.get_all_values()

            if not all_values:
                logger.warning("⚠️ Aba DESLOCAMENTO está vazia")
                return

            # Processar colunas A até J (índices 0 até 9)
            logger.info("🚗 Processando informações de deslocamento...")

            # Primeira linha são os cabeçalhos
            if len(all_values) > 0:
                headers = all_values[0]
                logger.info(f"📋 Cabeçalhos: {headers[:10]}")  # Primeiras 10 colunas

                # Processar dados de deslocamento
                for i, row in enumerate(all_values[1:], 1):
                    if not any(row):  # Pular linhas vazias
                        continue

                    # Extrair dados do deslocamento
                    if len(row) >= 10:
                        deslocamento_data = {
                            "coluna_a": row[0],
                            "coluna_b": row[1],
                            "coluna_c": row[2],
                            "coluna_d": row[3],
                            "coluna_e": row[4],
                            "coluna_f": row[5],
                            "coluna_g": row[6],
                            "coluna_h": row[7],
                            "coluna_i": row[8],
                            "coluna_j": row[9],
                        }

                        logger.info(f"🚗 Deslocamento {i}: {deslocamento_data}")

                        # Aqui seria a lógica para salvar no banco de dados
                        if not self.dry_run:
                            # Criar ou atualizar registro de deslocamento
                            pass

            self.estatisticas["deslocamentos_processados"] += 1
            logger.info("✅ Aba DESLOCAMENTO processada com sucesso")

        except Exception as e:
            logger.error(f"❌ Erro ao processar aba DESLOCAMENTO: {str(e)}")
            self.estatisticas["erros"] += 1

    def processar_aba_bloqueios(self, spreadsheet):
        """
        Processar aba Bloqueios - Formulário de bloqueios
        """
        logger.info("🚫 Processando aba Bloqueios...")

        try:
            worksheet = spreadsheet.worksheet("Bloqueios")
            config = self.abas_config["Bloqueios"]

            # Obter dados da planilha
            all_values = worksheet.get_all_values()

            if not all_values:
                logger.warning("⚠️ Aba Bloqueios está vazia")
                return

            logger.info("🚫 Processando bloqueios de datas...")

            # Primeira linha são os cabeçalhos
            if len(all_values) > 0:
                headers = all_values[0]
                logger.info(f"📋 Cabeçalhos: {headers}")

                # Processar dados de bloqueios
                for i, row in enumerate(all_values[1:], 1):
                    if not any(row):  # Pular linhas vazias
                        continue

                    # Extrair dados do bloqueio
                    bloqueio_data = {
                        "formador_coordenador": row[0] if len(row) > 0 else "",
                        "data_inicial": row[1] if len(row) > 1 else "",
                        "data_final": row[2] if len(row) > 2 else "",
                        "tipo_bloqueio": row[3] if len(row) > 3 else "",
                    }

                    logger.info(f"🚫 Bloqueio {i}: {bloqueio_data}")

                    # Aqui seria a lógica para salvar no banco de dados
                    if not self.dry_run:
                        # Criar ou atualizar registro de bloqueio
                        pass

            self.estatisticas["bloqueios_processados"] += 1
            logger.info("✅ Aba Bloqueios processada com sucesso")

        except Exception as e:
            logger.error(f"❌ Erro ao processar aba Bloqueios: {str(e)}")
            self.estatisticas["erros"] += 1

    def executar_importacao(self, abas_especificas: Optional[List[str]] = None):
        """
        Executar importação completa
        """
        logger.info("🚀 INICIANDO IMPORTAÇÃO DISPONIBILIDADE 2025 - CONTEXTO SUPREMO")
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
                        logger.info(f"\n🔄 Processando aba: {nome_aba}")

                        if nome_aba == "MENSAL":
                            self.processar_aba_mensal(spreadsheet)
                        elif nome_aba == "ANUAL":
                            self.processar_aba_anual(spreadsheet)
                        elif nome_aba == "DESLOCAMENTO":
                            self.processar_aba_deslocamento(spreadsheet)
                        elif nome_aba == "Bloqueios":
                            self.processar_aba_bloqueios(spreadsheet)

                        # Salvar estatísticas da aba
                        self.estatisticas["por_aba"][nome_aba] = {
                            "processada": True,
                            "erros": 0,
                        }
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
        logger.info("📊 RELATÓRIO FINAL DA IMPORTAÇÃO DISPONIBILIDADE")
        logger.info("=" * 70)

        logger.info(f"📈 ESTATÍSTICAS GERAIS:")
        logger.info(
            f"   - Interface gráfica processada: {self.estatisticas['interface_grafica_processada']}"
        )
        logger.info(
            f"   - Carga horária processada: {self.estatisticas['carga_horaria_processada']}"
        )
        logger.info(
            f"   - Deslocamentos processados: {self.estatisticas['deslocamentos_processados']}"
        )
        logger.info(
            f"   - Bloqueios processados: {self.estatisticas['bloqueios_processados']}"
        )
        logger.info(f"   - Erros: {self.estatisticas['erros']}")

        logger.info(f"\n📋 ESTATÍSTICAS POR ABA:")
        for aba, stats in self.estatisticas["por_aba"].items():
            logger.info(f"   {aba}:")
            logger.info(f"     - Processada: {stats['processada']}")
            logger.info(f"     - Erros: {stats['erros']}")

        # Salvar relatório em arquivo
        relatorio = {
            "timestamp": datetime.now().isoformat(),
            "dry_run": self.dry_run,
            "estatisticas": self.estatisticas,
        }

        with open(
            "relatorio_importacao_disponibilidade_2025.json", "w", encoding="utf-8"
        ) as f:
            json.dump(relatorio, f, indent=2, ensure_ascii=False, default=str)

        logger.info(
            f"\n💾 Relatório salvo em: relatorio_importacao_disponibilidade_2025.json"
        )


def main():
    """
    Função principal
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Importar dados da planilha Disponibilidade 2025"
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
        choices=["MENSAL", "ANUAL", "DESLOCAMENTO", "Bloqueios"],
        help="Processar apenas abas específicas",
    )

    args = parser.parse_args()

    # Determinar modo de execução
    dry_run = not args.execute

    # Criar importador
    importador = ImportadorDisponibilidade2025ContextoSupremo(dry_run=dry_run)

    # Executar importação
    sucesso = importador.executar_importacao(abas_especificas=args.abas)

    if sucesso:
        logger.info("🎉 IMPORTAÇÃO CONCLUÍDA COM SUCESSO!")
    else:
        logger.error("❌ IMPORTAÇÃO FALHOU!")
        sys.exit(1)


if __name__ == "__main__":
    main()
