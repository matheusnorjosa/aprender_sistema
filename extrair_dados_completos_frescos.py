#!/usr/bin/env python3
"""
Script para extrair dados completos e frescos das planilhas Google Sheets
"""

import json
import os
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


class ExtratorCompletoFresco:
    def __init__(self):
        self.service = None
        self.dados_extraidos = {}
        self.relatorio = {
            "timestamp": datetime.now().isoformat(),
            "planilhas_acessadas": [],
            "abas_processadas": [],
            "erros": [],
            "estatisticas": {},
        }

    def configurar_autenticacao(self):
        """Configura autenticação usando o token original"""
        try:
            token_file = "dados/extraidos/google_oauth_token.json"

            if not os.path.exists(token_file):
                print("❌ Arquivo de token não encontrado")
                return False

            with open(token_file, "r") as f:
                token_data = json.load(f)

            creds = Credentials(
                token=token_data.get("token"),
                refresh_token=token_data.get("refresh_token"),
                token_uri=token_data.get("token_uri"),
                client_id=token_data.get("client_id"),
                client_secret=token_data.get("client_secret"),
                scopes=token_data.get("scopes", []),
            )

            self.service = build("sheets", "v4", credentials=creds)
            print("✅ Autenticação configurada com sucesso!")
            return True

        except Exception as e:
            print(f"❌ Erro na autenticação: {e}")
            return False

    def extrair_planilha_agenda_2025(self):
        """Extrai dados da planilha 'Acompanhamento de Agenda | 2025'"""
        planilha_id = "16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU"

        abas_para_extrair = {
            "Super": {"aprovacao_externa": True},
            "ACerta": {"aprovacao_externa": False},
            "Outros": {"aprovacao_externa": False},
            "Brincando": {"aprovacao_externa": False},
            "Vidas": {"aprovacao_externa": False},
        }

        print(f"\n📊 Extraindo planilha: Acompanhamento de Agenda | 2025")
        self.relatorio["planilhas_acessadas"].append(
            {
                "nome": "Acompanhamento de Agenda | 2025",
                "id": planilha_id,
                "abas": list(abas_para_extrair.keys()),
            }
        )

        for aba_nome, config in abas_para_extrair.items():
            try:
                print(f"  📋 Processando aba: {aba_nome}")

                # Obter dados da aba
                range_name = f"{aba_nome}!A:Z"
                result = (
                    self.service.spreadsheets()
                    .values()
                    .get(spreadsheetId=planilha_id, range=range_name)
                    .execute()
                )

                values = result.get("values", [])
                if not values:
                    print(f"    ⚠️ Aba {aba_nome} vazia")
                    continue

                # Processar dados
                dados_aba = self.processar_dados_aba(values, aba_nome, config)
                self.dados_extraidos[f"agenda_2025_{aba_nome.lower()}"] = dados_aba

                print(f"    ✅ {aba_nome}: {len(dados_aba)} registros extraídos")
                self.relatorio["abas_processadas"].append(
                    {
                        "planilha": "Acompanhamento de Agenda | 2025",
                        "aba": aba_nome,
                        "registros": len(dados_aba),
                    }
                )

            except Exception as e:
                erro = f"Erro ao extrair aba {aba_nome}: {str(e)}"
                print(f"    ❌ {erro}")
                self.relatorio["erros"].append(erro)

    def extrair_planilha_disponibilidade_2025(self):
        """Extrai dados da planilha 'Disponibilidade | 2025'"""
        planilha_id = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"

        abas_para_extrair = {"EVENTOS": {}, "MENSAL": {}}

        print(f"\n📊 Extraindo planilha: Disponibilidade | 2025")
        self.relatorio["planilhas_acessadas"].append(
            {
                "nome": "Disponibilidade | 2025",
                "id": planilha_id,
                "abas": list(abas_para_extrair.keys()),
            }
        )

        for aba_nome, config in abas_para_extrair.items():
            try:
                print(f"  📋 Processando aba: {aba_nome}")

                # Obter dados da aba
                range_name = f"{aba_nome}!A:Z"
                result = (
                    self.service.spreadsheets()
                    .values()
                    .get(spreadsheetId=planilha_id, range=range_name)
                    .execute()
                )

                values = result.get("values", [])
                if not values:
                    print(f"    ⚠️ Aba {aba_nome} vazia")
                    continue

                # Processar dados
                dados_aba = self.processar_dados_aba(values, aba_nome, config)
                self.dados_extraidos[f"disponibilidade_2025_{aba_nome.lower()}"] = (
                    dados_aba
                )

                print(f"    ✅ {aba_nome}: {len(dados_aba)} registros extraídos")
                self.relatorio["abas_processadas"].append(
                    {
                        "planilha": "Disponibilidade | 2025",
                        "aba": aba_nome,
                        "registros": len(dados_aba),
                    }
                )

            except Exception as e:
                erro = f"Erro ao extrair aba {aba_nome}: {str(e)}"
                print(f"    ❌ {erro}")
                self.relatorio["erros"].append(erro)

    def extrair_planilha_usuarios(self):
        """Extrai dados da planilha 'Usuários'"""
        planilha_id = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"

        abas_para_extrair = {"Usuários": {}}

        print(f"\n📊 Extraindo planilha: Usuários")
        self.relatorio["planilhas_acessadas"].append(
            {
                "nome": "Usuários",
                "id": planilha_id,
                "abas": list(abas_para_extrair.keys()),
            }
        )

        for aba_nome, config in abas_para_extrair.items():
            try:
                print(f"  📋 Processando aba: {aba_nome}")

                # Obter dados da aba
                range_name = f"{aba_nome}!A:Z"
                result = (
                    self.service.spreadsheets()
                    .values()
                    .get(spreadsheetId=planilha_id, range=range_name)
                    .execute()
                )

                values = result.get("values", [])
                if not values:
                    print(f"    ⚠️ Aba {aba_nome} vazia")
                    continue

                # Processar dados
                dados_aba = self.processar_dados_aba(values, aba_nome, config)
                self.dados_extraidos[f"usuarios_{aba_nome.lower()}"] = dados_aba

                print(f"    ✅ {aba_nome}: {len(dados_aba)} registros extraídos")
                self.relatorio["abas_processadas"].append(
                    {
                        "planilha": "Usuários",
                        "aba": aba_nome,
                        "registros": len(dados_aba),
                    }
                )

            except Exception as e:
                erro = f"Erro ao extrair aba {aba_nome}: {str(e)}"
                print(f"    ❌ {erro}")
                self.relatorio["erros"].append(erro)

    def processar_dados_aba(self, values, aba_nome, config):
        """Processa os dados brutos de uma aba"""
        if not values:
            return []

        # Primeira linha são os cabeçalhos
        headers = values[0]
        dados = []

        for i, row in enumerate(values[1:], 1):
            # Garantir que a linha tenha o mesmo número de colunas que os headers
            while len(row) < len(headers):
                row.append("")

            # Criar dicionário com os dados
            registro = {
                "linha": i,
                "aba": aba_nome,
                "config": config,
                "timestamp_extracao": datetime.now().isoformat(),
            }

            for j, header in enumerate(headers):
                if j < len(row):
                    registro[header] = row[j]
                else:
                    registro[header] = ""

            dados.append(registro)

        return dados

    def gerar_relatorio_estatisticas(self):
        """Gera estatísticas dos dados extraídos"""
        print(f"\n📈 Gerando estatísticas...")

        total_registros = 0
        for chave, dados in self.dados_extraidos.items():
            count = len(dados)
            total_registros += count
            self.relatorio["estatisticas"][chave] = {
                "total_registros": count,
                "primeira_linha": dados[0] if dados else None,
                "ultima_linha": dados[-1] if dados else None,
            }
            print(f"  📊 {chave}: {count} registros")

        self.relatorio["estatisticas"]["total_geral"] = total_registros
        print(f"  🎯 Total geral: {total_registros} registros")

    def salvar_dados(self):
        """Salva os dados extraídos em arquivos JSON"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Salvar dados completos
        arquivo_dados = f"dados_frescos_completos_{timestamp}.json"
        with open(arquivo_dados, "w", encoding="utf-8") as f:
            json.dump(self.dados_extraidos, f, ensure_ascii=False, indent=2)

        # Salvar relatório
        arquivo_relatorio = f"relatorio_extracao_completa_{timestamp}.json"
        with open(arquivo_relatorio, "w", encoding="utf-8") as f:
            json.dump(self.relatorio, f, ensure_ascii=False, indent=2)

        print(f"\n💾 Dados salvos:")
        print(f"  📄 {arquivo_dados}")
        print(f"  📄 {arquivo_relatorio}")

        return arquivo_dados, arquivo_relatorio

    def executar_extracao_completa(self):
        """Executa a extração completa de todas as planilhas"""
        print("🚀 INICIANDO EXTRAÇÃO COMPLETA E FRESCA DAS PLANILHAS GOOGLE SHEETS")
        print("=" * 70)

        # Configurar autenticação
        if not self.configurar_autenticacao():
            print("❌ Falha na autenticação. Abortando extração.")
            return False

        # Extrair dados de todas as planilhas
        self.extrair_planilha_agenda_2025()
        self.extrair_planilha_disponibilidade_2025()
        self.extrair_planilha_usuarios()

        # Gerar estatísticas
        self.gerar_relatorio_estatisticas()

        # Salvar dados
        arquivo_dados, arquivo_relatorio = self.salvar_dados()

        print("\n" + "=" * 70)
        print("✅ EXTRAÇÃO COMPLETA E FRESCA CONCLUÍDA COM SUCESSO!")
        print(
            f"📊 Total de registros extraídos: {self.relatorio['estatisticas']['total_geral']}"
        )
        print(f"❌ Erros encontrados: {len(self.relatorio['erros'])}")

        return True


if __name__ == "__main__":
    extrator = ExtratorCompletoFresco()
    sucesso = extrator.executar_extracao_completa()

    if sucesso:
        print("\n🎉 Dados frescos extraídos com sucesso!")
        print("📋 Próximo passo: Comparar com análise anterior")
    else:
        print("\n❌ Falha na extração dos dados frescos")
