#!/usr/bin/env python
"""
Analisador completo das planilhas - Mapeia TODAS as relações organizacionais
"""

import json
import gspread
from google.oauth2.credentials import Credentials
from collections import defaultdict, Counter
import re


class AnalisadorCompletoOrganizacional:
    """Analisa completamente a estrutura organizacional das planilhas"""

    def __init__(self):
        self.estrutura_organizacional = {}
        self.vinculos_projeto_pessoa = {}
        self.produtos_colecoes = {}
        self.areas_operacionais = {}
        self.fluxos_aprovacao = {}

    def conectar(self):
        """Conecta às planilhas usando token OAuth2"""
        with open("google_oauth_token.json", "r") as f:
            token_data = json.load(f)

        creds = Credentials.from_authorized_user_info(token_data)
        self.gc = gspread.authorize(creds)
        print("✅ Conectado às planilhas Google Sheets")

    def analisar_hierarquia_organizacional(self):
        """Analisa hierarquia: Superintendência → Gerentes → Coordenadores → Formadores"""

        print("\n📊 ANALISANDO HIERARQUIA ORGANIZACIONAL...")

        # Acessar planilha de usuários
        sheet_usuarios = self.gc.open_by_key(
            "1Zj_I7sqYAJ9uaYbVoBfskl0LqxGM3SAFzwm4Zpph1RI"
        )
        aba_ativos = sheet_usuarios.worksheet("Ativos")

        # Obter todos os dados da aba Ativos
        print("   📋 Lendo usuários ativos...")
        usuarios_dados = aba_ativos.get_all_records()

        # Mapear por cargo
        por_cargo = defaultdict(list)
        por_gerencia = defaultdict(list)

        for usuario in usuarios_dados:
            if usuario.get("Nome"):  # Ignora linhas vazias
                cargo = str(usuario.get("Cargo", "")).strip()
                gerencia = str(usuario.get("Gerência", "")).strip()

                info_usuario = {
                    "nome": str(usuario.get("Nome", "")).strip(),
                    "nome_completo": str(usuario.get("Nome Completo", "")).strip(),
                    "cpf": str(usuario.get("CPF", "")).strip(),
                    "email": str(usuario.get("Email", "")).strip(),
                    "telefone": str(usuario.get("Telefone", "")).strip(),
                    "cargo": cargo,
                    "gerencia": gerencia,
                }

                if cargo:
                    por_cargo[cargo].append(info_usuario)
                if gerencia:
                    por_gerencia[gerencia].append(info_usuario)

        self.estrutura_organizacional["por_cargo"] = dict(por_cargo)
        self.estrutura_organizacional["por_gerencia"] = dict(por_gerencia)

        print(f"   👥 Total de usuários ativos: {len(usuarios_dados)}")
        print(f"   🏢 Cargos identificados: {list(por_cargo.keys())}")
        print(f"   🏛️ Gerências identificadas: {list(por_gerencia.keys())}")

        # Analisar coordenadores específicos
        sheet_controle = self.gc.open_by_key(
            "1P6YG3sIAEpiAPIQL9bKBaIznNl3V9VLan9CpVnrEOgA"
        )
        aba_coord = sheet_controle.worksheet("🟥 COORD")

        print("   📋 Lendo coordenadores específicos...")
        coord_dados = aba_coord.get_all_records()

        coordenadores_especificos = []
        for coord in coord_dados:
            if coord.get("Coordenador"):
                coordenadores_especificos.append(
                    {
                        "coordenador": coord.get("Coordenador", "").strip(),
                        "detalhes": coord,
                    }
                )

        self.estrutura_organizacional["coordenadores_especificos"] = (
            coordenadores_especificos
        )
        print(f"   👨‍💼 Coordenadores específicos: {len(coordenadores_especificos)}")

        return True

    def analisar_projetos_e_vinculos(self):
        """Analisa todos os projetos e seus vínculos com pessoas"""

        print("\n📚 ANALISANDO PROJETOS E VÍNCULOS...")

        sheet_controle = self.gc.open_by_key(
            "1P6YG3sIAEpiAPIQL9bKBaIznNl3V9VLan9CpVnrEOgA"
        )

        # Analisar aba AÇÕES (projetos e coordenadores)
        print("   📋 Analisando ações e projetos...")
        aba_acoes = sheet_controle.worksheet("🟥 AÇÕES")
        acoes_dados = aba_acoes.get_all_records()

        projetos_coordenadores = defaultdict(set)

        for acao in acoes_dados:
            projeto = acao.get("Projeto", "").strip()
            coordenador = acao.get("Coordenador", "").strip()

            if projeto and coordenador:
                projetos_coordenadores[projeto].add(coordenador)

        # Converter sets para listas para JSON
        self.vinculos_projeto_pessoa["projetos_coordenadores"] = {
            k: list(v) for k, v in projetos_coordenadores.items()
        }

        print(f"   📊 Projetos com coordenadores: {len(projetos_coordenadores)}")

        # Analisar aba CADASTROS (projetos por município)
        print("   📋 Analisando cadastros por município...")
        aba_cadastros = sheet_controle.worksheet("☑️ CADASTROS")
        cadastros_dados = aba_cadastros.get_all_records()

        projetos_municipios = defaultdict(set)
        municipios_projetos = defaultdict(set)

        for cadastro in cadastros_dados:
            municipio = cadastro.get("Município - UF", "").strip()
            projeto = cadastro.get("Projeto", "").strip()

            if municipio and projeto:
                projetos_municipios[projeto].add(municipio)
                municipios_projetos[municipio].add(projeto)

        self.vinculos_projeto_pessoa["projetos_municipios"] = {
            k: list(v) for k, v in projetos_municipios.items()
        }
        self.vinculos_projeto_pessoa["municipios_projetos"] = {
            k: list(v) for k, v in municipios_projetos.items()
        }

        print(f"   🏛️ Projetos em municípios: {len(projetos_municipios)}")
        print(f"   🗺️ Municípios com projetos: {len(municipios_projetos)}")

        return True

    def analisar_produtos_colecoes(self):
        """Analisa produtos e coleções por projeto"""

        print("\n📦 ANALISANDO PRODUTOS E COLEÇÕES...")

        sheet_controle = self.gc.open_by_key(
            "1P6YG3sIAEpiAPIQL9bKBaIznNl3V9VLan9CpVnrEOgA"
        )

        # Analisar aba COMPRAS
        print("   📋 Analisando compras e produtos...")
        aba_compras = sheet_controle.worksheet("🟥 COMPRAS")
        compras_dados = aba_compras.get_all_records()

        produtos_por_municipio = defaultdict(lambda: defaultdict(int))
        produtos_globais = Counter()

        for compra in compras_dados:
            produto = compra.get("Produto", "").strip()
            municipio = compra.get("Município", "").strip()
            uf = compra.get("UF", "").strip()
            quantidade = compra.get("Quant.", 0)

            try:
                quantidade = int(quantidade) if quantidade else 0
            except:
                quantidade = 0

            if produto:
                produtos_globais[produto] += quantidade

                if municipio:
                    municipio_uf = f"{municipio} - {uf}" if uf else municipio
                    produtos_por_municipio[municipio_uf][produto] += quantidade

        self.produtos_colecoes["produtos_globais"] = dict(produtos_globais)
        self.produtos_colecoes["produtos_por_municipio"] = {
            k: dict(v) for k, v in produtos_por_municipio.items()
        }

        print(f"   📦 Produtos únicos: {len(produtos_globais)}")
        print(f"   🗺️ Municípios com compras: {len(produtos_por_municipio)}")

        # Analisar aba FILTRO_PROD para entender coleções
        print("   📋 Analisando filtros e coleções...")
        aba_filtro = sheet_controle.worksheet("ℹ️ FILTRO_PROD.")
        filtro_dados = aba_filtro.get_all_records()

        # Extrair informações de coleções/regiões
        colecoes_info = {}
        for item in filtro_dados:
            municipio = item.get("Município - UF", "").strip()
            regiao = item.get("Região", "").strip()

            if municipio and regiao:
                colecoes_info[municipio] = {"regiao": regiao, "item": item}

        self.produtos_colecoes["colecoes_info"] = colecoes_info

        return True

    def analisar_areas_operacionais(self):
        """Identifica áreas operacionais: DAT, Controle, etc."""

        print("\n⚙️ ANALISANDO ÁREAS OPERACIONAIS...")

        # Analisar cargos para identificar áreas operacionais
        cargos_operacionais = {}

        for cargo, pessoas in self.estrutura_organizacional.get(
            "por_cargo", {}
        ).items():
            cargo_lower = cargo.lower()

            if any(
                termo in cargo_lower for termo in ["dat", "dados", "analytics", "bi"]
            ):
                cargos_operacionais["DAT"] = pessoas
            elif any(
                termo in cargo_lower for termo in ["controle", "control", "auditoria"]
            ):
                cargos_operacionais["Controle"] = pessoas
            elif any(termo in cargo_lower for termo in ["super", "superintend"]):
                cargos_operacionais["Superintendência"] = pessoas
            elif any(termo in cargo_lower for termo in ["gerente", "gerência"]):
                cargos_operacionais["Gerência"] = pessoas
            elif any(termo in cargo_lower for termo in ["coordenador", "coord"]):
                cargos_operacionais["Coordenação"] = pessoas
            elif any(termo in cargo_lower for termo in ["formador", "forma"]):
                cargos_operacionais["Formação"] = pessoas

        self.areas_operacionais = cargos_operacionais

        print(
            f"   🏢 Áreas operacionais identificadas: {list(cargos_operacionais.keys())}"
        )

        return True

    def analisar_fluxos_aprovacao(self):
        """Analisa fluxos de aprovação baseado na estrutura organizacional"""

        print("\n🔄 ANALISANDO FLUXOS DE APROVAÇÃO...")

        # Identificar hierarquia de aprovação
        hierarquia = {
            "nivel_1_superintendencia": self.areas_operacionais.get(
                "Superintendência", []
            ),
            "nivel_2_gerencia": self.areas_operacionais.get("Gerência", []),
            "nivel_3_coordenacao": self.areas_operacionais.get("Coordenação", []),
            "nivel_4_formacao": self.areas_operacionais.get("Formação", []),
        }

        # Analisar quem aprova o quê baseado nos projetos
        aprovacoes_por_projeto = {}

        for projeto, coordenadores in self.vinculos_projeto_pessoa.get(
            "projetos_coordenadores", {}
        ).items():
            # Coordenadores aprovam ações do projeto
            aprovacoes_por_projeto[projeto] = {
                "coordenadores_responsaveis": coordenadores,
                "processo": "Coordenador → Gerência → Superintendência",
            }

        self.fluxos_aprovacao = {
            "hierarquia_aprovacao": hierarquia,
            "aprovacoes_por_projeto": aprovacoes_por_projeto,
        }

        print(f"   📊 Projetos com fluxo de aprovação: {len(aprovacoes_por_projeto)}")

        return True

    def gerar_relatorio_completo(self):
        """Gera relatório completo da análise organizacional"""

        print("\n📄 GERANDO RELATÓRIO COMPLETO...")

        relatorio = {
            "timestamp": "2025-09-23",
            "resumo_executivo": {
                "total_usuarios_ativos": len(
                    [
                        pessoa
                        for pessoas in self.estrutura_organizacional.get(
                            "por_cargo", {}
                        ).values()
                        for pessoa in pessoas
                    ]
                ),
                "total_cargos": len(self.estrutura_organizacional.get("por_cargo", {})),
                "total_gerencias": len(
                    self.estrutura_organizacional.get("por_gerencia", {})
                ),
                "total_projetos": len(
                    self.vinculos_projeto_pessoa.get("projetos_coordenadores", {})
                ),
                "total_municipios": len(
                    self.vinculos_projeto_pessoa.get("municipios_projetos", {})
                ),
                "total_produtos": len(
                    self.produtos_colecoes.get("produtos_globais", {})
                ),
                "areas_operacionais": list(self.areas_operacionais.keys()),
            },
            "estrutura_organizacional": self.estrutura_organizacional,
            "vinculos_projeto_pessoa": self.vinculos_projeto_pessoa,
            "produtos_colecoes": self.produtos_colecoes,
            "areas_operacionais": self.areas_operacionais,
            "fluxos_aprovacao": self.fluxos_aprovacao,
        }

        # Salvar relatório
        with open("analise_organizacional_completa.json", "w", encoding="utf-8") as f:
            json.dump(relatorio, f, indent=2, ensure_ascii=False)

        print("✅ Relatório salvo: analise_organizacional_completa.json")

        # Imprimir resumo
        print("\n" + "=" * 60)
        print("📊 RESUMO DA ANÁLISE ORGANIZACIONAL")
        print("=" * 60)

        resumo = relatorio["resumo_executivo"]
        print(f"👥 Usuários ativos: {resumo['total_usuarios_ativos']}")
        print(f"🏢 Cargos: {resumo['total_cargos']}")
        print(f"🏛️ Gerências: {resumo['total_gerencias']}")
        print(f"📚 Projetos: {resumo['total_projetos']}")
        print(f"🗺️ Municípios: {resumo['total_municipios']}")
        print(f"📦 Produtos: {resumo['total_produtos']}")
        print(f"⚙️ Áreas operacionais: {', '.join(resumo['areas_operacionais'])}")

        return relatorio


def main():
    """Executa análise completa"""

    print("🔍 INICIANDO ANÁLISE ORGANIZACIONAL COMPLETA")
    print("=" * 60)

    analisador = AnalisadorCompletoOrganizacional()

    try:
        # Conectar
        analisador.conectar()

        # Executar análises
        analisador.analisar_hierarquia_organizacional()
        analisador.analisar_projetos_e_vinculos()
        analisador.analisar_produtos_colecoes()
        analisador.analisar_areas_operacionais()
        analisador.analisar_fluxos_aprovacao()

        # Gerar relatório
        relatorio = analisador.gerar_relatorio_completo()

        print("\n🎉 ANÁLISE ORGANIZACIONAL CONCLUÍDA COM SUCESSO!")
        return True

    except Exception as e:
        print(f"❌ ERRO na análise: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    main()
