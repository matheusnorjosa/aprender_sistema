#!/usr/bin/env python3
"""
ESTRATÉGIA COMPLETA DE ANÁLISE DAS PLANILHAS GOOGLE SHEETS
Senior Data Analyst Approach - Extração, Tratamento e Comparação
"""

import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd


class GoogleSheetsDataAnalyst:
    """
    Classe para análise completa das planilhas Google Sheets
    Abordagem de Senior Data Analyst
    """

    def __init__(self):
        self.credenciais_path = "google_service_account.json"
        self.dados_extraidos = {}
        self.estatisticas_extracao = {}
        self.planilhas_config = {
            "Acompanhamento de Agenda | 2025": {
                "abas": {
                    "ACerta": {"gid": "1430609894"},
                    "Outros": {"gid": "1430609894"},
                    "Super": {"gid": "0"},
                    "Brincando": {"gid": "1430609894"},
                    "Vidas": {"gid": "1430609894"},
                }
            },
            "Disponibilidade | 2025": {
                "abas": {
                    "MENSAL": {"gid": "1510755488"},
                    "EVENTOS": {"gid": "1430609894"},
                }
            },
            "Usuários": {"abas": {"Usuários": {"gid": "0"}}},
        }

    def verificar_credenciais(self):
        """Verificar se as credenciais estão disponíveis"""

        print("🔐 VERIFICANDO CREDENCIAIS GOOGLE SHEETS")
        print("=" * 60)

        if not os.path.exists(self.credenciais_path):
            print(f"❌ Arquivo de credenciais não encontrado: {self.credenciais_path}")
            return False

        try:
            with open(self.credenciais_path, "r") as f:
                credenciais = json.load(f)

            campos_obrigatorios = [
                "type",
                "project_id",
                "private_key_id",
                "private_key",
                "client_email",
                "client_id",
            ]
            campos_faltando = [
                campo for campo in campos_obrigatorios if campo not in credenciais
            ]

            if campos_faltando:
                print(f"❌ Campos obrigatórios faltando: {campos_faltando}")
                return False

            print("✅ Credenciais válidas encontradas")
            print(f"   • Tipo: {credenciais['type']}")
            print(f"   • Projeto: {credenciais['project_id']}")
            print(f"   • Email: {credenciais['client_email']}")

            return True

        except Exception as e:
            print(f"❌ Erro ao verificar credenciais: {e}")
            return False

    def configurar_google_sheets_api(self):
        """Configurar API do Google Sheets"""

        print("\n🔧 CONFIGURANDO GOOGLE SHEETS API")
        print("=" * 60)

        try:
            import gspread
            from google.oauth2.service_account import Credentials

            # Definir escopos
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets.readonly",
                "https://www.googleapis.com/auth/drive.readonly",
            ]

            # Carregar credenciais
            credenciais = Credentials.from_service_account_file(
                self.credenciais_path, scopes=scopes
            )

            # Inicializar cliente
            self.gc = gspread.authorize(credenciais)

            print("✅ Google Sheets API configurada com sucesso")
            return True

        except ImportError:
            print("❌ Bibliotecas necessárias não instaladas")
            print("   Execute: pip install gspread google-auth")
            return False
        except Exception as e:
            print(f"❌ Erro ao configurar API: {e}")
            return False

    def listar_planilhas_disponiveis(self):
        """Listar planilhas disponíveis na conta"""

        print("\n📋 LISTANDO PLANILHAS DISPONÍVEIS")
        print("=" * 60)

        try:
            planilhas = self.gc.list_spreadsheet_files()

            print(f"📊 Total de planilhas encontradas: {len(planilhas)}")

            planilhas_relevantes = []
            for planilha in planilhas:
                nome = planilha["name"]
                if any(
                    palavra in nome
                    for palavra in [
                        "2025",
                        "Acompanhamento",
                        "Disponibilidade",
                        "Usuários",
                    ]
                ):
                    planilhas_relevantes.append(planilha)
                    print(f"   ✅ {nome} (ID: {planilha['id']})")

            return planilhas_relevantes

        except Exception as e:
            print(f"❌ Erro ao listar planilhas: {e}")
            return []

    def acessar_planilha_por_id(self, planilha_id: str, nome_planilha: str):
        """Acessar planilha específica por ID"""

        print(f"\n📂 ACESSANDO PLANILHA: {nome_planilha}")
        print("=" * 60)

        try:
            planilha = self.gc.open_by_key(planilha_id)
            print(f"✅ Planilha acessada: {planilha.title}")

            # Listar abas
            abas = planilha.worksheets()
            print(f"📊 Abas disponíveis: {len(abas)}")

            for aba in abas:
                print(f"   • {aba.title} (ID: {aba.id})")

            return planilha

        except Exception as e:
            print(f"❌ Erro ao acessar planilha {nome_planilha}: {e}")
            return None

    def extrair_dados_aba(self, planilha, nome_aba: str, gid: str):
        """Extrair dados de uma aba específica"""

        print(f"\n📊 EXTRAINDO DADOS DA ABA: {nome_aba}")
        print("=" * 60)

        try:
            # Acessar aba por GID
            if gid == "0":
                aba = planilha.sheet1  # Primeira aba
            else:
                aba = planilha.get_worksheet_by_id(int(gid))

            if not aba:
                print(f"❌ Aba {nome_aba} não encontrada")
                return None

            print(f"✅ Aba acessada: {aba.title}")
            print(f"   • Dimensões: {aba.row_count} linhas x {aba.col_count} colunas")

            # Obter todos os dados
            dados_brutos = aba.get_all_records()
            print(f"   • Registros encontrados: {len(dados_brutos)}")

            if not dados_brutos:
                print("⚠️ Nenhum dado encontrado na aba")
                return None

            # Analisar estrutura
            primeiro_registro = dados_brutos[0]
            print(f"   • Campos disponíveis: {list(primeiro_registro.keys())}")

            return dados_brutos

        except Exception as e:
            print(f"❌ Erro ao extrair dados da aba {nome_aba}: {e}")
            return None

    def analisar_estrutura_dados(self, dados: List[Dict], nome_aba: str):
        """Analisar estrutura dos dados extraídos"""

        print(f"\n🔍 ANÁLISE DA ESTRUTURA - ABA: {nome_aba}")
        print("=" * 60)

        if not dados:
            print("❌ Nenhum dado para analisar")
            return {}

        analise = {
            "total_registros": len(dados),
            "campos_disponiveis": list(dados[0].keys()) if dados else [],
            "campos_preenchidos": {},
            "valores_unicos": {},
            "problemas_identificados": [],
        }

        # Analisar preenchimento de campos
        for campo in analise["campos_disponiveis"]:
            valores_nao_vazios = [
                registro.get(campo, "") for registro in dados if registro.get(campo, "")
            ]
            analise["campos_preenchidos"][campo] = len(valores_nao_vazios)

            # Valores únicos
            valores_unicos = set(valores_nao_vazios)
            analise["valores_unicos"][campo] = len(valores_unicos)

        # Identificar problemas
        for campo, preenchidos in analise["campos_preenchidos"].items():
            percentual = (preenchidos / analise["total_registros"]) * 100
            if percentual < 50:
                analise["problemas_identificados"].append(
                    f"Campo '{campo}' com apenas {percentual:.1f}% preenchido"
                )

        # Relatório
        print(f"📊 Total de registros: {analise['total_registros']}")
        print(f"📊 Campos disponíveis: {len(analise['campos_disponiveis'])}")

        print(f"\n📋 Preenchimento de campos:")
        for campo, preenchidos in analise["campos_preenchidos"].items():
            percentual = (preenchidos / analise["total_registros"]) * 100
            print(
                f"   • {campo}: {preenchidos}/{analise['total_registros']} ({percentual:.1f}%)"
            )

        if analise["problemas_identificados"]:
            print(f"\n⚠️ Problemas identificados:")
            for problema in analise["problemas_identificados"]:
                print(f"   • {problema}")

        return analise

    def tratar_dados_extraidos(self, dados: List[Dict], nome_aba: str):
        """Tratar e padronizar dados extraídos"""

        print(f"\n🧹 TRATANDO DADOS - ABA: {nome_aba}")
        print("=" * 60)

        dados_tratados = []
        estatisticas_tratamento = {
            "registros_processados": 0,
            "registros_validos": 0,
            "registros_removidos": 0,
            "correcoes_aplicadas": defaultdict(int),
        }

        for i, registro in enumerate(dados):
            try:
                registro_tratado = self._tratar_registro_individual(
                    registro, nome_aba, i + 1
                )

                if registro_tratado:
                    dados_tratados.append(registro_tratado)
                    estatisticas_tratamento["registros_validos"] += 1
                else:
                    estatisticas_tratamento["registros_removidos"] += 1

                estatisticas_tratamento["registros_processados"] += 1

            except Exception as e:
                print(f"   ⚠️ Erro no registro {i+1}: {e}")
                estatisticas_tratamento["registros_removidos"] += 1

        print(f"✅ Tratamento concluído:")
        print(
            f"   • Registros processados: {estatisticas_tratamento['registros_processados']}"
        )
        print(f"   • Registros válidos: {estatisticas_tratamento['registros_validos']}")
        print(
            f"   • Registros removidos: {estatisticas_tratamento['registros_removidos']}"
        )

        return dados_tratados, estatisticas_tratamento

    def _tratar_registro_individual(
        self, registro: Dict, nome_aba: str, linha: int
    ) -> Optional[Dict]:
        """Tratar registro individual"""

        # Mapear campos baseado na estrutura esperada
        campos_mapeados = self._mapear_campos_registro(registro, nome_aba)

        if not campos_mapeados:
            return None

        # Criar registro tratado
        registro_tratado = {
            "id_extracao": f"{nome_aba}_{linha}",
            "aba_origem": nome_aba,
            "linha_original": linha,
            "municipio": self._tratar_municipio(campos_mapeados.get("municipio")),
            "projeto": self._tratar_projeto(campos_mapeados.get("projeto")),
            "evento": self._tratar_evento(campos_mapeados),
            "formadores": self._tratar_formadores(campos_mapeados.get("formadores")),
            "dados_extras": {
                "observacoes": campos_mapeados.get("observacoes"),
                "status": campos_mapeados.get(
                    "status", "Aprovado" if nome_aba != "Super" else "Pendente"
                ),
                "dados_originais": registro,
            },
        }

        # Validar se registro é válido
        if (
            registro_tratado["municipio"]["nome"]
            and registro_tratado["projeto"]["nome"]
            and registro_tratado["evento"]["tipo"]
            and registro_tratado["formadores"]
        ):
            return registro_tratado

        return None

    def _mapear_campos_registro(self, registro: Dict, nome_aba: str) -> Dict:
        """Mapear campos do registro baseado na aba"""

        # Mapeamento de campos por aba
        mapeamentos = {
            "Super": {
                "municipio": ["municipio", "Município", "MUNICIPIO"],
                "projeto": ["projeto", "Projeto", "PROJETO"],
                "tipo_evento": ["tipo_evento", "Tipo Evento", "TIPO_EVENTO"],
                "formadores": ["formadores", "Formadores", "FORMADORES"],
                "data": ["data_evento", "Data Evento", "DATA_EVENTO"],
                "observacoes": ["observacoes", "Observações", "OBSERVACOES"],
            },
            "ACerta": {
                "municipio": ["municipio", "Município", "MUNICIPIO"],
                "projeto": ["projeto", "Projeto", "PROJETO"],
                "tipo_evento": ["tipo_evento", "Tipo Evento", "TIPO_EVENTO"],
                "formadores": ["formadores", "Formadores", "FORMADORES"],
                "data": ["data_evento", "Data Evento", "DATA_EVENTO"],
                "observacoes": ["observacoes", "Observações", "OBSERVACOES"],
            },
            "Brincando": {
                "municipio": ["municipio", "Município", "MUNICIPIO"],
                "projeto": ["projeto", "Projeto", "PROJETO"],
                "tipo_evento": ["tipo_evento", "Tipo Evento", "TIPO_EVENTO"],
                "formadores": ["formadores", "Formadores", "FORMADORES"],
                "data": ["data_evento", "Data Evento", "DATA_EVENTO"],
                "observacoes": ["observacoes", "Observações", "OBSERVACOES"],
            },
            "Outros": {
                "municipio": ["municipio", "Município", "MUNICIPIO"],
                "projeto": ["projeto", "Projeto", "PROJETO"],
                "tipo_evento": ["tipo_evento", "Tipo Evento", "TIPO_EVENTO"],
                "formadores": ["formadores", "Formadores", "FORMADORES"],
                "data": ["data_evento", "Data Evento", "DATA_EVENTO"],
                "observacoes": ["observacoes", "Observações", "OBSERVACOES"],
            },
            "Vidas": {
                "municipio": ["municipio", "Município", "MUNICIPIO"],
                "projeto": ["projeto", "Projeto", "PROJETO"],
                "tipo_evento": ["tipo_evento", "Tipo Evento", "TIPO_EVENTO"],
                "formadores": ["formadores", "Formadores", "FORMADORES"],
                "data": ["data_evento", "Data Evento", "DATA_EVENTO"],
                "observacoes": ["observacoes", "Observações", "OBSERVACOES"],
            },
        }

        mapeamento = mapeamentos.get(nome_aba, {})
        campos_mapeados = {}

        for campo, possibilidades in mapeamento.items():
            for possibilidade in possibilidades:
                if possibilidade in registro:
                    campos_mapeados[campo] = registro[possibilidade]
                    break

        return campos_mapeados

    def _tratar_municipio(self, municipio_raw) -> Dict:
        """Tratar dados de município"""

        if not municipio_raw:
            return {"nome": None, "uf": None, "nome_completo": None}

        municipio = str(municipio_raw).strip()

        # Extrair UF se estiver no formato "Município - UF"
        if " - " in municipio:
            partes = municipio.split(" - ")
            if len(partes) == 2:
                municipio_nome = partes[0].strip()
                uf = partes[1].strip()
                return {
                    "nome": municipio_nome,
                    "uf": uf,
                    "nome_completo": f"{municipio_nome} - {uf}",
                }

        # Tentar extrair UF de outros formatos
        uf_patterns = [
            r"/([A-Z]{2})$",  # /UF no final
            r"-([A-Z]{2})$",  # -UF no final
            r"\(([A-Z]{2})\)$",  # (UF) no final
        ]

        for pattern in uf_patterns:
            match = re.search(pattern, municipio)
            if match:
                uf = match.group(1)
                municipio_nome = re.sub(pattern, "", municipio).strip()
                return {
                    "nome": municipio_nome,
                    "uf": uf,
                    "nome_completo": f"{municipio_nome} - {uf}",
                }

        # Se não conseguir extrair UF, retornar apenas o nome
        return {"nome": municipio, "uf": None, "nome_completo": municipio}

    def _tratar_projeto(self, projeto_raw) -> Dict:
        """Tratar dados de projeto"""

        if not projeto_raw:
            return {"nome": None, "categoria": None}

        projeto = str(projeto_raw).strip()

        # Remover sufixos comuns
        sufixos_remover = ["(SS)", "(Super)", "(Superintendência)", "(SUPER)"]
        for sufixo in sufixos_remover:
            if projeto.endswith(sufixo):
                projeto = projeto[: -len(sufixo)].strip()

        return {"nome": projeto, "categoria": "Educacional"}

    def _tratar_evento(self, campos_mapeados: Dict) -> Dict:
        """Tratar dados de evento"""

        tipo_evento_raw = campos_mapeados.get("tipo_evento")
        data_raw = campos_mapeados.get("data")

        # Tratar tipo de evento
        modalidade = None
        tipo = None

        if tipo_evento_raw:
            tipo_evento = str(tipo_evento_raw).strip()
            if " - " in tipo_evento:
                partes = tipo_evento.split(" - ")
                if len(partes) == 2:
                    modalidade = partes[0].strip()
                    tipo = partes[1].strip()
            else:
                tipo = tipo_evento

        return {
            "modalidade": modalidade,
            "tipo": tipo,
            "data": data_raw,
            "titulo": f"{campos_mapeados.get('projeto', 'Evento')} - {campos_mapeados.get('municipio', 'Local')}",
        }

    def _tratar_formadores(self, formadores_raw) -> List[str]:
        """Tratar dados de formadores"""

        if not formadores_raw:
            return []

        if isinstance(formadores_raw, list):
            formadores = formadores_raw
        else:
            # Se for string, tentar separar por vírgula ou ponto e vírgula
            formadores = re.split(r"[,;]", str(formadores_raw))

        # Limpar e filtrar formadores
        formadores_limpos = []
        for formador in formadores:
            formador_limpo = formador.strip()
            if formador_limpo and len(formador_limpo) > 2:  # Filtrar nomes muito curtos
                formadores_limpos.append(formador_limpo)

        return formadores_limpos

    def executar_extracao_completa(self):
        """Executar extração completa de todas as planilhas"""

        print("🚀 INICIANDO EXTRAÇÃO COMPLETA DAS PLANILHAS")
        print("=" * 80)
        print(f"⏰ Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

        # 1. Verificar credenciais
        if not self.verificar_credenciais():
            return False

        # 2. Configurar API
        if not self.configurar_google_sheets_api():
            return False

        # 3. Listar planilhas
        planilhas_disponiveis = self.listar_planilhas_disponiveis()
        if not planilhas_disponiveis:
            print("❌ Nenhuma planilha relevante encontrada")
            return False

        # 4. Extrair dados de cada planilha
        for planilha_info in planilhas_disponiveis:
            planilha_id = planilha_info["id"]
            nome_planilha = planilha_info["name"]

            planilha = self.acessar_planilha_por_id(planilha_id, nome_planilha)
            if not planilha:
                continue

            # Extrair dados das abas configuradas
            if nome_planilha in self.planilhas_config:
                config_abas = self.planilhas_config[nome_planilha]["abas"]

                for nome_aba, config in config_abas.items():
                    gid = config["gid"]

                    # Extrair dados da aba
                    dados_brutos = self.extrair_dados_aba(planilha, nome_aba, gid)
                    if not dados_brutos:
                        continue

                    # Analisar estrutura
                    analise = self.analisar_estrutura_dados(dados_brutos, nome_aba)

                    # Tratar dados
                    dados_tratados, estatisticas = self.tratar_dados_extraidos(
                        dados_brutos, nome_aba
                    )

                    # Armazenar resultados
                    self.dados_extraidos[nome_aba] = {
                        "dados_brutos": dados_brutos,
                        "dados_tratados": dados_tratados,
                        "analise": analise,
                        "estatisticas_tratamento": estatisticas,
                    }

        return True

    def gerar_relatorio_extracao(self):
        """Gerar relatório da extração"""

        print("\n📋 RELATÓRIO DE EXTRAÇÃO")
        print("=" * 80)

        total_registros = 0
        total_abas = len(self.dados_extraidos)

        print(f"📊 Total de abas processadas: {total_abas}")

        for nome_aba, dados in self.dados_extraidos.items():
            registros_brutos = len(dados["dados_brutos"])
            registros_tratados = len(dados["dados_tratados"])
            total_registros += registros_tratados

            print(f"\n📊 {nome_aba}:")
            print(f"   • Registros brutos: {registros_brutos}")
            print(f"   • Registros tratados: {registros_tratados}")
            print(
                f"   • Taxa de sucesso: {(registros_tratados/registros_brutos)*100:.1f}%"
            )

        print(f"\n📊 Total de registros extraídos: {total_registros}")

        return {
            "total_abas": total_abas,
            "total_registros": total_registros,
            "dados_por_aba": {
                nome: len(dados["dados_tratados"])
                for nome, dados in self.dados_extraidos.items()
            },
        }

    def salvar_dados_extraidos(self):
        """Salvar dados extraídos"""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        diretorio = f"dados_extracao_sheets_{timestamp}"

        os.makedirs(diretorio, exist_ok=True)

        # Salvar dados tratados
        dados_consolidados = []
        for nome_aba, dados in self.dados_extraidos.items():
            dados_consolidados.extend(dados["dados_tratados"])

        arquivo_principal = f"{diretorio}/dados_extraidos_sheets_{timestamp}.json"
        with open(arquivo_principal, "w", encoding="utf-8") as f:
            json.dump(dados_consolidados, f, ensure_ascii=False, indent=2)

        # Salvar relatório
        relatorio = self.gerar_relatorio_extracao()
        arquivo_relatorio = f"{diretorio}/relatorio_extracao_{timestamp}.json"
        with open(arquivo_relatorio, "w", encoding="utf-8") as f:
            json.dump(relatorio, f, ensure_ascii=False, indent=2)

        print(f"\n💾 DADOS SALVOS:")
        print(f"   • Dados extraídos: {arquivo_principal}")
        print(f"   • Relatório: {arquivo_relatorio}")

        return arquivo_principal, arquivo_relatorio


def main():
    """Função principal"""

    print("🚀 ESTRATÉGIA COMPLETA DE ANÁLISE DAS PLANILHAS GOOGLE SHEETS")
    print("=" * 80)
    print("👨‍💼 Abordagem de Senior Data Analyst")
    print("=" * 80)

    # Inicializar analista
    analista = GoogleSheetsDataAnalyst()

    # Executar extração completa
    sucesso = analista.executar_extracao_completa()

    if sucesso:
        # Gerar relatório
        relatorio = analista.gerar_relatorio_extracao()

        # Salvar dados
        arquivo_dados, arquivo_relatorio = analista.salvar_dados_extraidos()

        print(f"\n🎉 EXTRAÇÃO CONCLUÍDA COM SUCESSO!")
        print(f"   ✅ {relatorio['total_abas']} abas processadas")
        print(f"   ✅ {relatorio['total_registros']} registros extraídos")
        print(f"   ✅ Dados tratados e organizados")
        print(f"   ✅ Pronto para comparação")

        return analista
    else:
        print(f"\n❌ EXTRAÇÃO FALHOU!")
        return None


if __name__ == "__main__":
    analista = main()
