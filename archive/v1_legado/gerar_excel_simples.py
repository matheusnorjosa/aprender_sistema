#!/usr/bin/env python3
"""
Script simplificado para gerar arquivos Excel dos dados tratados
"""

import json
from datetime import datetime

import pandas as pd


def carregar_dados():
    """Carrega os dados tratados"""
    print("📂 Carregando dados tratados...")

    # Carregar dados tratados
    with open(
        "dados_tratados_organizados_20250919_225631.json", "r", encoding="utf-8"
    ) as f:
        dados_tratados = json.load(f)

    print(f"✅ Dados carregados: {len(dados_tratados)} abas")
    return dados_tratados


def gerar_excel_principal(dados_tratados):
    """Gera o arquivo Excel principal"""
    print("📊 Gerando arquivo Excel principal...")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    arquivo = f"dados_tratados_excel_{timestamp}.xlsx"

    with pd.ExcelWriter(arquivo, engine="openpyxl") as writer:
        for i, (chave_aba, dados) in enumerate(dados_tratados.items()):
            if not dados:
                continue

            print(
                f"  📋 Processando aba {i+1}/{len(dados_tratados)}: {chave_aba[:30]}..."
            )

            # Converter para DataFrame
            df = pd.DataFrame(dados)

            # Limitar nome da aba
            nome_aba = chave_aba[:31] if len(chave_aba) > 31 else chave_aba

            # Escrever no Excel
            df.to_excel(writer, sheet_name=nome_aba, index=False)

    print(f"✅ Excel gerado: {arquivo}")
    return arquivo


def gerar_excel_categorias():
    """Gera arquivo Excel por categorias"""
    print("📊 Gerando arquivo Excel por categorias...")

    # Carregar dados organizados
    with open(
        "dados_organizados_por_categoria_20250919_225631.json", "r", encoding="utf-8"
    ) as f:
        dados_organizados = json.load(f)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    arquivo = f"dados_por_categoria_{timestamp}.xlsx"

    with pd.ExcelWriter(arquivo, engine="openpyxl") as writer:
        for categoria, abas in dados_organizados.items():
            if not abas:
                continue

            print(f"  📋 Processando categoria: {categoria}")

            # Combinar dados da categoria
            dados_categoria = []
            for chave_aba, dados in abas.items():
                for registro in dados:
                    registro_com_categoria = registro.copy()
                    registro_com_categoria["categoria"] = categoria
                    registro_com_categoria["aba_original"] = chave_aba
                    dados_categoria.append(registro_com_categoria)

            if dados_categoria:
                df = pd.DataFrame(dados_categoria)
                df.to_excel(writer, sheet_name=categoria, index=False)

    print(f"✅ Excel gerado: {arquivo}")
    return arquivo


def main():
    """Função principal"""
    print("🚀 GERANDO ARQUIVOS EXCEL SIMPLIFICADOS")
    print("=" * 50)

    try:
        # Carregar dados
        dados_tratados = carregar_dados()

        # Gerar arquivos Excel
        arquivo1 = gerar_excel_principal(dados_tratados)
        arquivo2 = gerar_excel_categorias()

        print("\n" + "=" * 50)
        print("✅ GERAÇÃO CONCLUÍDA!")
        print(f"📄 Arquivos gerados:")
        print(f"  📊 {arquivo1}")
        print(f"  📊 {arquivo2}")

    except Exception as e:
        print(f"❌ Erro: {e}")


if __name__ == "__main__":
    main()
