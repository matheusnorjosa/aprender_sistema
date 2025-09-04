#!/usr/bin/env python
"""
Análise detalhada das planilhas extraídas
"""
import json
import re
from collections import Counter, defaultdict


def analyze_usuarios():
    """Analisa dados da planilha de usuários"""
    print("=== ANÁLISE DETALHADA: USUÁRIOS ===")

    try:
        with open("extracted_usuarios.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        print(f"Planilha: {data['planilha_nome']}")
        print(f"Total de abas: {data['total_abas']}")

        for aba_nome, aba_data in data["worksheets"].items():
            print(f"\n--- ABA: {aba_nome} ---")
            print(f"Total de registros: {aba_data['total_rows'] - 1}")  # -1 para header
            print(f"Campos: {aba_data['total_cols']}")

            headers = aba_data["headers"]
            print(f"Colunas: {headers}")

            # Analisar alguns registros
            sample_data = aba_data["data"][:3]  # Primeiros 3 registros
            print("Amostra de dados:")
            for i, row in enumerate(sample_data, 1):
                print(f"  {i}: {row[:5]}...")  # Primeiros 5 campos

            # Análise de campos específicos
            if "Nome" in headers and aba_data["data"]:
                nomes = [row[0] for row in aba_data["data"] if len(row) > 0 and row[0]]
                print(f"Nomes únicos: {len(set(nomes))}")

            if "Email" in headers:
                email_col = headers.index("Email") if "Email" in headers else -1
                if email_col >= 0:
                    emails = [
                        row[email_col]
                        for row in aba_data["data"]
                        if len(row) > email_col and row[email_col]
                    ]
                    emails_validos = [e for e in emails if "@" in e]
                    print(f"Emails válidos: {len(emails_validos)}")

    except Exception as e:
        print(f"Erro na análise de usuários: {e}")


def analyze_disponibilidade():
    """Analisa dados da planilha de disponibilidade"""
    print("\n=== ANÁLISE DETALHADA: DISPONIBILIDADE 2025 ===")

    try:
        with open("extracted_disponibilidade.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        print(f"Planilha: {data['planilha_nome']}")
        print(f"Total de abas: {data['total_abas']}")

        for aba_nome, aba_data in data["worksheets"].items():
            print(f"\n--- ABA: {aba_nome} ---")
            print(f"Dimensões: {aba_data['total_rows']} x {aba_data['total_cols']}")

            headers = aba_data["headers"]
            print(f"Primeiros campos: {headers[:8]}")

            # Análise específica por aba
            if aba_nome == "Eventos":
                print("ANÁLISE DE EVENTOS:")
                if len(aba_data["data"]) > 0:
                    # Analisar estrutura dos eventos
                    eventos_sample = aba_data["data"][:5]
                    print("Amostra de eventos:")
                    for i, evento in enumerate(eventos_sample, 1):
                        print(f"  {i}: {evento[:5]}...")

                    # Contar tipos de dados
                    if "tipo" in headers:
                        tipo_col = headers.index("tipo")
                        tipos = [
                            row[tipo_col]
                            for row in aba_data["data"]
                            if len(row) > tipo_col and row[tipo_col]
                        ]
                        tipo_counter = Counter(tipos)
                        print(
                            f"Tipos de eventos: {dict(list(tipo_counter.most_common(5)))}"
                        )

            elif aba_nome == "Bloqueios":
                print("ANÁLISE DE BLOQUEIOS:")
                if len(aba_data["data"]) > 0:
                    print(f"Total de bloqueios: {len(aba_data['data'])}")

                    # Analisar tipos de bloqueio
                    if "Tipo" in headers:
                        tipo_col = headers.index("Tipo")
                        tipos = [
                            row[tipo_col]
                            for row in aba_data["data"]
                            if len(row) > tipo_col and row[tipo_col]
                        ]
                        tipo_counter = Counter(tipos)
                        print(f"Tipos de bloqueio: {dict(tipo_counter)}")

            elif aba_nome == "DESLOCAMENTO":
                print("ANÁLISE DE DESLOCAMENTOS:")
                if len(aba_data["data"]) > 0:
                    print(f"Total de deslocamentos: {len(aba_data['data'])}")

                    # Analisar origens mais comuns
                    if "Origem" in headers:
                        origem_col = headers.index("Origem")
                        origens = [
                            row[origem_col]
                            for row in aba_data["data"]
                            if len(row) > origem_col and row[origem_col]
                        ]
                        origem_counter = Counter(origens)
                        print(
                            f"Origens mais comuns: {dict(list(origem_counter.most_common(3)))}"
                        )

    except Exception as e:
        print(f"Erro na análise de disponibilidade: {e}")


def analyze_acompanhamento():
    """Analisa dados da planilha de acompanhamento"""
    print("\n=== ANÁLISE DETALHADA: ACOMPANHAMENTO 2025 ===")

    try:
        with open("extracted_acompanhamento.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        print(f"Planilha: {data['planilha_nome']}")
        print(f"Total de abas: {data['total_abas']}")

        # Focar nas abas mais importantes
        abas_importantes = [
            "Super",
            "Google Agenda",
            "Novo Google Agenda",
            "Bloqueios",
            "Configurações",
        ]

        for aba_nome, aba_data in data["worksheets"].items():
            if aba_nome in abas_importantes:
                print(f"\n--- ABA: {aba_nome} ---")
                print(f"Dimensões: {aba_data['total_rows']} x {aba_data['total_cols']}")

                headers = aba_data["headers"]
                print(f"Campos principais: {headers[:10]}")

                if aba_nome == "Google Agenda":
                    print("ANÁLISE GOOGLE AGENDA:")
                    print(f"Total de eventos: {len(aba_data['data'])}")

                    # Analisar campos de título
                    if "Title" in headers:
                        title_col = headers.index("Title")
                        titulos = [
                            row[title_col]
                            for row in aba_data["data"][:10]
                            if len(row) > title_col and row[title_col]
                        ]
                        print("Exemplos de títulos:")
                        for titulo in titulos[:5]:
                            print(f"  - {titulo}")

                elif aba_nome == "Bloqueios":
                    print("ANÁLISE BLOQUEIOS:")
                    if len(aba_data["data"]) > 0:
                        print(f"Total de bloqueios: {len(aba_data['data'])}")

                        # Analisar pessoas com mais bloqueios
                        if "Pessoa" in headers:
                            pessoa_col = headers.index("Pessoa")
                            pessoas = [
                                row[pessoa_col]
                                for row in aba_data["data"]
                                if len(row) > pessoa_col and row[pessoa_col]
                            ]
                            pessoa_counter = Counter(pessoas)
                            print(
                                f"Pessoas com mais bloqueios: {dict(list(pessoa_counter.most_common(3)))}"
                            )

                elif aba_nome == "Configurações":
                    print("ANÁLISE CONFIGURAÇÕES:")
                    print(f"Total de configurações: {len(aba_data['data'])}")

                    # Verificar se tem dados de municípios
                    if "Município" in headers:
                        municipio_col = headers.index("Município")
                        municipios = [
                            row[municipio_col]
                            for row in aba_data["data"]
                            if len(row) > municipio_col and row[municipio_col]
                        ]
                        municipios_unicos = list(set([m for m in municipios if m]))
                        print(f"Municípios encontrados: {len(municipios_unicos)}")
                        print(f"Exemplos: {municipios_unicos[:5]}")

    except Exception as e:
        print(f"Erro na análise de acompanhamento: {e}")


def identify_business_rules():
    """Identifica regras de negócio a partir dos dados"""
    print("\n=== IDENTIFICAÇÃO DE REGRAS DE NEGÓCIO ===")

    print("\n1. USUÁRIOS:")
    print("- Usuários divididos em: Ativos, Inativos, Pendentes")
    print("- Campos obrigatórios: Nome, Nome Completo, CPF, Email")
    print("- Validação de CPF necessária")
    print("- Validação de email necessária")

    print("\n2. DISPONIBILIDADE:")
    print("- Sistema de bloqueios com tipos (Total/Parcial)")
    print("- Controle de deslocamentos entre municípios")
    print("- Eventos com status e validações")
    print("- Configurações por município e formador")

    print("\n3. ACOMPANHAMENTO:")
    print("- Divisão por projetos (Super, ACerta, Vidas, Brincando, Outros)")
    print("- Integração com Google Agenda")
    print("- Sistema de aprovação (campos de controle)")
    print("- Bloqueios de agenda por pessoa")

    print("\n4. CÓDIGOS IDENTIFICADOS:")
    print("- Status de aprovação: SIM/FALSE")
    print("- Tipos de bloqueio: observados nas planilhas")
    print("- Municípios: lista extensa nas configurações")
    print("- Projetos: categorizados por abas específicas")


def generate_migration_recommendations():
    """Gera recomendações para migração"""
    print("\n=== RECOMENDAÇÕES PARA MIGRAÇÃO ===")

    print("\n1. PRIORIDADE ALTA:")
    print("- Migrar usuários (118 ativos já identificados)")
    print("- Migrar municípios (das configurações)")
    print("- Migrar tipos de evento/projeto")
    print("- Migrar bloqueios existentes")

    print("\n2. ESTRUTURAS IMPORTANTES:")
    print("- Relacionamento Usuário -> Múltiplos papéis")
    print("- Sistema de bloqueios com tipos")
    print("- Deslocamentos entre municípios")
    print("- Eventos com aprovação/status")

    print("\n3. VALIDAÇÕES NECESSÁRIAS:")
    print("- CPF único e válido")
    print("- Email único e válido")
    print("- Datas de bloqueio consistentes")
    print("- Municípios válidos para deslocamento")

    print("\n4. INTEGRAÇÃO GOOGLE:")
    print("- 2,452 eventos no Google Agenda")
    print("- 578 eventos no Novo Google Agenda")
    print("- Sincronização bidirecional necessária")


if __name__ == "__main__":
    analyze_usuarios()
    analyze_disponibilidade()
    analyze_acompanhamento()
    identify_business_rules()
    generate_migration_recommendations()

    print("\n=== ANÁLISE COMPLETA CONCLUÍDA ===")
    print("Próximo passo: Implementar estratégia de migração")
