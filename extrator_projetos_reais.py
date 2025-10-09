#!/usr/bin/env python
"""
Extrator de projetos reais das planilhas para o sistema Django
"""

import json
import gspread
import pandas as pd
from google.oauth2.credentials import Credentials
import os
import sys
import django

# Configurar Django
sys.path.append("/app")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
django.setup()

from core.models import Projeto
from django.db import transaction
from collections import Counter


class ExtratorProjetosReais:
    """Extrai e importa os 87 projetos reais das planilhas"""

    def __init__(self):
        self.projetos_importados = 0
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

    def extrair_projetos_das_acoes(self):
        """Extrai projetos da aba AÇÕES"""

        print("📋 Extraindo projetos da aba AÇÕES...")

        sheet_controle = self.gc.open_by_key(
            "1P6YG3sIAEpiAPIQL9bKBaIznNl3V9VLan9CpVnrEOgA"
        )
        aba_acoes = sheet_controle.worksheet("🟥 AÇÕES")

        dados_acoes = aba_acoes.get_all_records()
        df_acoes = pd.DataFrame(dados_acoes)

        print(f"📊 Total de registros na aba AÇÕES: {len(df_acoes)}")

        # Extrair projetos únicos
        projetos_acoes = df_acoes[
            df_acoes["Projeto"].notna() & (df_acoes["Projeto"] != "")
        ]
        projetos_unicos = projetos_acoes["Projeto"].str.strip().unique()

        print(f"📚 Projetos únicos em AÇÕES: {len(projetos_unicos)}")

        return projetos_unicos.tolist()

    def extrair_projetos_dos_cadastros(self):
        """Extrai projetos da aba CADASTROS"""

        print("📋 Extraindo projetos da aba CADASTROS...")

        sheet_controle = self.gc.open_by_key(
            "1P6YG3sIAEpiAPIQL9bKBaIznNl3V9VLan9CpVnrEOgA"
        )
        aba_cadastros = sheet_controle.worksheet("☑️ CADASTROS")

        dados_cadastros = aba_cadastros.get_all_records()
        df_cadastros = pd.DataFrame(dados_cadastros)

        print(f"📊 Total de registros na aba CADASTROS: {len(df_cadastros)}")

        # Extrair projetos únicos
        projetos_cadastros = df_cadastros[
            df_cadastros["Projeto"].notna() & (df_cadastros["Projeto"] != "")
        ]
        projetos_unicos = projetos_cadastros["Projeto"].str.strip().unique()

        print(f"📚 Projetos únicos em CADASTROS: {len(projetos_unicos)}")

        return projetos_unicos.tolist()

    def consolidar_projetos(self, projetos_acoes, projetos_cadastros):
        """Consolida e classifica projetos de ambas as fontes"""

        print("🔄 Consolidando projetos de ambas as fontes...")

        # Unir e remover duplicatas
        todos_projetos = set(projetos_acoes + projetos_cadastros)

        # Contar frequência para identificar importância
        contador_acoes = Counter(projetos_acoes)
        contador_cadastros = Counter(projetos_cadastros)

        projetos_consolidados = []

        for projeto_nome in todos_projetos:
            if not projeto_nome or projeto_nome.strip() == "":
                continue

            projeto_nome = projeto_nome.strip()

            # Analisar características do projeto
            freq_acoes = contador_acoes.get(projeto_nome, 0)
            freq_cadastros = contador_cadastros.get(projeto_nome, 0)

            # Classificar por coleção baseado no nome
            colecao = self.classificar_colecao(projeto_nome)
            segmento = self.classificar_segmento(projeto_nome)

            projeto_data = {
                "nome": projeto_nome,
                "colecao": colecao,
                "segmento": segmento,
                "freq_acoes": freq_acoes,
                "freq_cadastros": freq_cadastros,
                "total_freq": freq_acoes + freq_cadastros,
                "ativo": True,
            }

            projetos_consolidados.append(projeto_data)

        # Ordenar por frequência total (mais importante primeiro)
        projetos_consolidados.sort(key=lambda x: x["total_freq"], reverse=True)

        print(f"📚 Total de projetos consolidados: {len(projetos_consolidados)}")

        return projetos_consolidados

    def classificar_colecao(self, nome_projeto):
        """Classifica coleção baseado no nome do projeto"""

        nome_lower = nome_projeto.lower()

        if any(
            termo in nome_lower for termo in ["matemática", "math", "acerta", "números"]
        ):
            return "Matemática"
        elif any(
            termo in nome_lower
            for termo in ["língua", "português", "lendo", "escrevendo", "linguagem"]
        ):
            return "Língua Portuguesa"
        elif any(termo in nome_lower for termo in ["infantil", "brincando", "criança"]):
            return "Educação Infantil"
        elif any(
            termo in nome_lower for termo in ["ciências", "ciencia", "experimento"]
        ):
            return "Ciências"
        elif any(termo in nome_lower for termo in ["vida", "vidas"]):
            return "Projeto Vida"
        else:
            return "Geral"

    def classificar_segmento(self, nome_projeto):
        """Classifica segmento baseado no nome do projeto"""

        nome_lower = nome_projeto.lower()

        if any(termo in nome_lower for termo in ["infantil", "brincando", "criança"]):
            return "Educação Infantil"
        elif any(
            termo in nome_lower for termo in ["inicial", "iniciais", "fundamental i"]
        ):
            return "Anos Iniciais"
        elif any(
            termo in nome_lower for termo in ["final", "finais", "fundamental ii"]
        ):
            return "Anos Finais"
        elif any(termo in nome_lower for termo in ["médio", "ensino médio"]):
            return "Ensino Médio"
        else:
            return "Fundamental"

    def importar_projetos(self, projetos_data):
        """Importa projetos para o Django"""

        print("💾 Importando projetos para o banco de dados...")

        for projeto_data in projetos_data:
            try:
                with transaction.atomic():
                    # Verificar se já existe
                    if Projeto.objects.filter(nome=projeto_data["nome"]).exists():
                        print(
                            f"   ⚠️ Projeto '{projeto_data['nome']}' já existe, pulando..."
                        )
                        continue

                    # Criar projeto
                    projeto = Projeto.objects.create(
                        nome=projeto_data["nome"],
                        descricao=f"Projeto extraído das planilhas - Frequência: {projeto_data['total_freq']} registros",
                        ativo=projeto_data["ativo"],
                    )

                    self.projetos_importados += 1

                    if self.projetos_importados % 10 == 0:
                        print(
                            f"   ✅ {self.projetos_importados} projetos importados..."
                        )

            except Exception as e:
                self.erros.append(
                    f"Erro importando projeto '{projeto_data['nome']}': {e}"
                )
                print(f"   ❌ Erro: {projeto_data['nome']} - {e}")

        print(f"✅ Total de projetos importados: {self.projetos_importados}")

    def gerar_relatorio(self, projetos_data):
        """Gera relatório da importação"""

        relatorio = {
            "timestamp": "2025-09-23",
            "projetos_importados": self.projetos_importados,
            "total_erros": len(self.erros),
            "erros": self.erros,
            "estatisticas": {
                "total_projetos_sistema": Projeto.objects.count(),
                "projetos_por_colecao": {},
                "projetos_por_segmento": {},
                "top_10_projetos": projetos_data[:10],
            },
        }

        # Estatísticas por coleção e segmento
        for projeto in projetos_data:
            colecao = projeto["colecao"]
            segmento = projeto["segmento"]

            if colecao not in relatorio["estatisticas"]["projetos_por_colecao"]:
                relatorio["estatisticas"]["projetos_por_colecao"][colecao] = 0
            relatorio["estatisticas"]["projetos_por_colecao"][colecao] += 1

            if segmento not in relatorio["estatisticas"]["projetos_por_segmento"]:
                relatorio["estatisticas"]["projetos_por_segmento"][segmento] = 0
            relatorio["estatisticas"]["projetos_por_segmento"][segmento] += 1

        with open(
            "/app/relatorio_importacao_projetos_reais.json", "w", encoding="utf-8"
        ) as f:
            json.dump(relatorio, f, indent=2, ensure_ascii=False)

        print("📄 Relatório salvo: relatorio_importacao_projetos_reais.json")
        return relatorio


def main():
    """Executa extração e importação de projetos reais"""

    print("📚 EXTRAÇÃO E IMPORTAÇÃO DE PROJETOS REAIS")
    print("=" * 60)

    extrator = ExtratorProjetosReais()

    try:
        # Conectar
        if not extrator.conectar_planilhas():
            return False

        # Extrair projetos de diferentes fontes
        projetos_acoes = extrator.extrair_projetos_das_acoes()
        projetos_cadastros = extrator.extrair_projetos_dos_cadastros()

        # Consolidar
        projetos_consolidados = extrator.consolidar_projetos(
            projetos_acoes, projetos_cadastros
        )

        if not projetos_consolidados:
            print("❌ Nenhum projeto válido encontrado")
            return False

        # Importar
        extrator.importar_projetos(projetos_consolidados)

        # Gerar relatório
        relatorio = extrator.gerar_relatorio(projetos_consolidados)

        print("\n📊 RESUMO DA IMPORTAÇÃO:")
        print(f"   ✅ Projetos importados: {relatorio['projetos_importados']}")
        print(f"   ❌ Erros: {relatorio['total_erros']}")
        print(
            f"   📚 Total no sistema: {relatorio['estatisticas']['total_projetos_sistema']}"
        )

        print(f"\n📊 DISTRIBUIÇÃO POR COLEÇÃO:")
        for colecao, count in relatorio["estatisticas"]["projetos_por_colecao"].items():
            print(f"   - {colecao}: {count}")

        print(f"\n📊 TOP 5 PROJETOS MAIS FREQUENTES:")
        for i, projeto in enumerate(relatorio["estatisticas"]["top_10_projetos"][:5]):
            print(f"   {i+1}. {projeto['nome']} (freq: {projeto['total_freq']})")

        if relatorio["total_erros"] > 0:
            print(f"\n⚠️ Primeiros 3 erros:")
            for erro in relatorio["erros"][:3]:
                print(f"   - {erro}")

        print("\n🎉 IMPORTAÇÃO DE PROJETOS REAIS CONCLUÍDA!")
        return True

    except Exception as e:
        print(f"❌ ERRO na extração: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    main()
