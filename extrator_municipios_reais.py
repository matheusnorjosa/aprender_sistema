#!/usr/bin/env python
"""
Extrator de municípios reais das planilhas para o sistema Django
"""

import json
import gspread
import pandas as pd
import re
from google.oauth2.credentials import Credentials
import os
import sys
import django

# Configurar Django
sys.path.append("/app")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
django.setup()

from core.models import Municipio
from django.db import transaction


class ExtratorMunicipiosReais:
    """Extrai e importa os 76 municípios reais das planilhas"""

    def __init__(self):
        self.municipios_importados = 0
        self.erros = []

    def conectar_planilhas(self):
        """Conecta às planilhas Google Sheets"""
        try:
            with open("google_oauth_token.json", "r") as f:
                token_data = json.load(f)

            creds = Credentials.from_authorized_user_info(token_data)
            self.gc = gspread.authorize(creds)
            print("✅ Conectado às planilhas Google Sheets")
            return True
        except Exception as e:
            print(f"❌ Erro na conexão: {e}")
            return False

    def normalizar_municipio_uf(self, municipio_uf_str):
        """Normaliza string município-UF"""
        if not municipio_uf_str:
            return None, None

        municipio_uf = str(municipio_uf_str).strip()

        # Padrões comuns: "Município - UF", "Município-UF", "Município/UF"
        for separador in [" - ", "-", "/"]:
            if separador in municipio_uf:
                partes = municipio_uf.split(separador)
                if len(partes) >= 2:
                    municipio = partes[0].strip().title()
                    uf = partes[-1].strip().upper()

                    # Validar UF (2 letras)
                    if len(uf) == 2 and uf.isalpha():
                        return municipio, uf

        # Se não tem separador, assumir que é só município
        municipio = municipio_uf.strip().title()
        return municipio, None

    def extrair_municipios_da_planilha_controle(self):
        """Extrai municípios da planilha de controle"""

        print("📋 Extraindo municípios da Planilha de Controle...")

        sheet_controle = self.gc.open_by_key(
            "1P6YG3sIAEpiAPIQL9bKBaIznNl3V9VLan9CpVnrEOgA"
        )

        municipios_encontrados = set()

        # Aba CADASTROS
        try:
            print("   📋 Analisando aba CADASTROS...")
            aba_cadastros = sheet_controle.worksheet("☑️ CADASTROS")
            dados_cadastros = aba_cadastros.get_all_records()
            df_cadastros = pd.DataFrame(dados_cadastros)

            print(f"   📊 Total de registros na aba CADASTROS: {len(df_cadastros)}")

            # Extrair municípios únicos
            if "Município - UF" in df_cadastros.columns:
                municipios_cadastros = df_cadastros[
                    df_cadastros["Município - UF"].notna()
                    & (df_cadastros["Município - UF"] != "")
                ]

                for municipio_uf in municipios_cadastros["Município - UF"].unique():
                    municipio, uf = self.normalizar_municipio_uf(municipio_uf)
                    if municipio:
                        municipios_encontrados.add((municipio, uf, "CADASTROS"))

                print(
                    f"   🏛️ Municípios únicos em CADASTROS: {len(municipios_encontrados)}"
                )

        except Exception as e:
            self.erros.append(f"Erro na aba CADASTROS: {e}")
            print(f"   ❌ Erro na aba CADASTROS: {e}")

        # Aba COMPRAS
        try:
            print("   📋 Analisando aba COMPRAS...")
            aba_compras = sheet_controle.worksheet("🟥 COMPRAS")
            dados_compras = aba_compras.get_all_records()
            df_compras = pd.DataFrame(dados_compras)

            print(f"   📊 Total de registros na aba COMPRAS: {len(df_compras)}")

            # Extrair municípios únicos
            municipios_compras_antes = len(municipios_encontrados)

            if "Município" in df_compras.columns:
                municipios_compras = df_compras[
                    df_compras["Município"].notna() & (df_compras["Município"] != "")
                ]

                for _, row in municipios_compras.iterrows():
                    municipio = str(row["Município"]).strip().title()
                    uf = (
                        str(row.get("UF", "")).strip().upper()
                        if row.get("UF")
                        else None
                    )

                    if municipio and municipio.lower() not in ["nan", "none"]:
                        # Validar UF se existir
                        if uf and (len(uf) != 2 or not uf.isalpha()):
                            uf = None

                        municipios_encontrados.add((municipio, uf, "COMPRAS"))

                print(
                    f"   🏛️ Novos municípios em COMPRAS: {len(municipios_encontrados) - municipios_compras_antes}"
                )

        except Exception as e:
            self.erros.append(f"Erro na aba COMPRAS: {e}")
            print(f"   ❌ Erro na aba COMPRAS: {e}")

        # Aba FILTRO_PROD
        try:
            print("   📋 Analisando aba FILTRO_PROD...")
            aba_filtro = sheet_controle.worksheet("ℹ️ FILTRO_PROD.")
            dados_filtro = aba_filtro.get_all_records()
            df_filtro = pd.DataFrame(dados_filtro)

            print(f"   📊 Total de registros na aba FILTRO_PROD: {len(df_filtro)}")

            municipios_filtro_antes = len(municipios_encontrados)

            if "Município - UF" in df_filtro.columns:
                municipios_filtro = df_filtro[
                    df_filtro["Município - UF"].notna()
                    & (df_filtro["Município - UF"] != "")
                ]

                for municipio_uf in municipios_filtro["Município - UF"].unique():
                    municipio, uf = self.normalizar_municipio_uf(municipio_uf)
                    if municipio:
                        # Adicionar informação de região se disponível
                        regiao = None
                        matching_rows = df_filtro[
                            df_filtro["Município - UF"] == municipio_uf
                        ]
                        if (
                            not matching_rows.empty
                            and "Região" in matching_rows.columns
                        ):
                            regiao = str(matching_rows.iloc[0]["Região"]).strip()

                        municipios_encontrados.add(
                            (
                                municipio,
                                uf,
                                f"FILTRO_PROD ({regiao})" if regiao else "FILTRO_PROD",
                            )
                        )

                print(
                    f"   🏛️ Novos municípios em FILTRO_PROD: {len(municipios_encontrados) - municipios_filtro_antes}"
                )

        except Exception as e:
            self.erros.append(f"Erro na aba FILTRO_PROD: {e}")
            print(f"   ❌ Erro na aba FILTRO_PROD: {e}")

        print(
            f"📊 Total de municípios únicos encontrados: {len(municipios_encontrados)}"
        )

        return list(municipios_encontrados)

    def extrair_municipios_da_agenda(self):
        """Extrai municípios da planilha de Acompanhamento de Agenda"""

        print("📋 Extraindo municípios da Acompanhamento de Agenda...")

        try:
            sheet_agenda = self.gc.open_by_key(
                "16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU"
            )

            municipios_agenda = set()

            # Listar todas as abas da planilha
            worksheets = sheet_agenda.worksheets()
            print(f"   📊 Encontradas {len(worksheets)} abas na planilha de agenda")

            for worksheet in worksheets:
                try:
                    print(f"   📋 Analisando aba: {worksheet.title}")
                    dados = worksheet.get_all_records()

                    if not dados:
                        continue

                    df = pd.DataFrame(dados)

                    # Procurar colunas que podem conter municípios
                    colunas_municipio = [
                        col
                        for col in df.columns
                        if any(
                            termo in col.lower()
                            for termo in ["município", "municipio", "cidade", "local"]
                        )
                    ]

                    for coluna in colunas_municipio:
                        municipios_coluna = df[df[coluna].notna() & (df[coluna] != "")]

                        for municipio_str in municipios_coluna[coluna].unique():
                            municipio, uf = self.normalizar_municipio_uf(municipio_str)
                            if municipio and municipio.lower() not in [
                                "nan",
                                "none",
                                "município",
                            ]:
                                municipios_agenda.add(
                                    (municipio, uf, f"AGENDA-{worksheet.title}")
                                )

                    print(
                        f"      🏛️ Municípios encontrados na aba {worksheet.title}: {len([m for m in municipios_agenda if f'AGENDA-{worksheet.title}' in m[2]])}"
                    )

                except Exception as e:
                    self.erros.append(f"Erro na aba {worksheet.title} da agenda: {e}")
                    print(f"      ❌ Erro na aba {worksheet.title}: {e}")

            print(f"📊 Total de municípios únicos na agenda: {len(municipios_agenda)}")
            return list(municipios_agenda)

        except Exception as e:
            self.erros.append(f"Erro geral na planilha de agenda: {e}")
            print(f"❌ Erro geral na planilha de agenda: {e}")
            return []

    def consolidar_municipios(self, municipios_controle, municipios_agenda):
        """Consolida municípios de todas as fontes"""

        print("🔄 Consolidando municípios de todas as fontes...")

        # Combinar todas as fontes
        todos_municipios = municipios_controle + municipios_agenda

        # Agrupar por município (nome normalizado)
        municipios_consolidados = {}

        for municipio, uf, fonte in todos_municipios:
            # Criar chave normalizada
            chave = municipio.lower().strip()

            if chave not in municipios_consolidados:
                municipios_consolidados[chave] = {
                    "nome": municipio,
                    "uf": uf,
                    "fontes": [fonte],
                    "uf_mais_comum": uf,
                }
            else:
                # Adicionar fonte
                if fonte not in municipios_consolidados[chave]["fontes"]:
                    municipios_consolidados[chave]["fontes"].append(fonte)

                # Se não tínhamos UF antes e agora temos, usar
                if not municipios_consolidados[chave]["uf"] and uf:
                    municipios_consolidados[chave]["uf"] = uf
                    municipios_consolidados[chave]["uf_mais_comum"] = uf

        # Converter para lista ordenada
        municipios_finais = []
        for dados in municipios_consolidados.values():
            municipio_data = {
                "nome": dados["nome"],
                "uf": dados["uf_mais_comum"],
                "fontes": dados["fontes"],
                "total_fontes": len(dados["fontes"]),
            }
            municipios_finais.append(municipio_data)

        # Ordenar por frequência (mais fontes primeiro) e depois alfabeticamente
        municipios_finais.sort(key=lambda x: (-x["total_fontes"], x["nome"]))

        print(f"📊 Total de municípios consolidados: {len(municipios_finais)}")

        return municipios_finais

    def importar_municipios(self, municipios_data):
        """Importa municípios para o Django"""

        print("💾 Importando municípios para o banco de dados...")

        for municipio_data in municipios_data:
            try:
                with transaction.atomic():
                    # Verificar se já existe
                    nome = municipio_data["nome"]
                    uf = municipio_data["uf"]

                    # Buscar por nome exato primeiro
                    if Municipio.objects.filter(nome=nome).exists():
                        print(f"   ⚠️ Município '{nome}' já existe, pulando...")
                        continue

                    # Criar município
                    municipio = Municipio.objects.create(
                        nome=nome,
                        uf=uf or "CE",  # Default para CE se não tiver UF
                        ativo=True,
                    )

                    self.municipios_importados += 1

                    if self.municipios_importados % 10 == 0:
                        print(
                            f"   ✅ {self.municipios_importados} municípios importados..."
                        )

            except Exception as e:
                self.erros.append(
                    f"Erro importando município '{municipio_data['nome']}': {e}"
                )
                print(f"   ❌ Erro: {municipio_data['nome']} - {e}")

        print(f"✅ Total de municípios importados: {self.municipios_importados}")

    def gerar_relatorio(self, municipios_data):
        """Gera relatório da importação"""

        relatorio = {
            "timestamp": "2025-09-23",
            "municipios_importados": self.municipios_importados,
            "total_erros": len(self.erros),
            "erros": self.erros,
            "estatisticas": {
                "total_municipios_sistema": Municipio.objects.count(),
                "municipios_por_uf": {},
                "top_10_municipios": municipios_data[:10],
                "distribuicao_por_fontes": {},
            },
        }

        # Estatísticas por UF
        for municipio in municipios_data:
            uf = municipio["uf"] or "SEM_UF"
            if uf not in relatorio["estatisticas"]["municipios_por_uf"]:
                relatorio["estatisticas"]["municipios_por_uf"][uf] = 0
            relatorio["estatisticas"]["municipios_por_uf"][uf] += 1

        # Estatísticas por número de fontes
        for municipio in municipios_data:
            total_fontes = municipio["total_fontes"]
            if total_fontes not in relatorio["estatisticas"]["distribuicao_por_fontes"]:
                relatorio["estatisticas"]["distribuicao_por_fontes"][total_fontes] = 0
            relatorio["estatisticas"]["distribuicao_por_fontes"][total_fontes] += 1

        with open(
            "/app/relatorio_importacao_municipios_reais.json", "w", encoding="utf-8"
        ) as f:
            json.dump(relatorio, f, indent=2, ensure_ascii=False)

        print("📄 Relatório salvo: relatorio_importacao_municipios_reais.json")
        return relatorio


def main():
    """Executa extração e importação de municípios reais"""

    print("🏛️ EXTRAÇÃO E IMPORTAÇÃO DE MUNICÍPIOS REAIS")
    print("=" * 60)

    extrator = ExtratorMunicipiosReais()

    try:
        # Conectar
        if not extrator.conectar_planilhas():
            return False

        # Extrair de diferentes fontes
        municipios_controle = extrator.extrair_municipios_da_planilha_controle()
        municipios_agenda = extrator.extrair_municipios_da_agenda()

        # Consolidar
        municipios_consolidados = extrator.consolidar_municipios(
            municipios_controle, municipios_agenda
        )

        if not municipios_consolidados:
            print("❌ Nenhum município válido encontrado")
            return False

        # Importar
        extrator.importar_municipios(municipios_consolidados)

        # Gerar relatório
        relatorio = extrator.gerar_relatorio(municipios_consolidados)

        print("\n📊 RESUMO DA IMPORTAÇÃO:")
        print(f"   ✅ Municípios importados: {relatorio['municipios_importados']}")
        print(f"   ❌ Erros: {relatorio['total_erros']}")
        print(
            f"   🏛️ Total no sistema: {relatorio['estatisticas']['total_municipios_sistema']}"
        )

        print(f"\n📊 DISTRIBUIÇÃO POR UF:")
        for uf, count in relatorio["estatisticas"]["municipios_por_uf"].items():
            print(f"   - {uf}: {count}")

        print(f"\n📊 TOP 5 MUNICÍPIOS MAIS FREQUENTES:")
        for i, municipio in enumerate(
            relatorio["estatisticas"]["top_10_municipios"][:5]
        ):
            print(
                f"   {i+1}. {municipio['nome']} ({municipio['uf']}) - {municipio['total_fontes']} fontes"
            )

        if relatorio["total_erros"] > 0:
            print(f"\n⚠️ Primeiros 3 erros:")
            for erro in relatorio["erros"][:3]:
                print(f"   - {erro}")

        print("\n🎉 IMPORTAÇÃO DE MUNICÍPIOS REAIS CONCLUÍDA!")
        return True

    except Exception as e:
        print(f"❌ ERRO na extração: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    main()
