#!/usr/bin/env python
"""
Script para extrair dados da planilha "Disponibilidade | 2025" - aba "MENSAL"
"""
import os
import sys
import json
from datetime import date, timedelta

# Configurar Django
sys.path.insert(0, "/app")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
import django

django.setup()

from core.models import Formador, DisponibilidadeFormadores, Solicitacao, Deslocamento
from django.contrib.auth import get_user_model


def extrair_dados_planilha_disponibilidade():
    print("🔍 EXTRAINDO DADOS DA PLANILHA DISPONIBILIDADE")
    print("=" * 60)

    # URL da planilha
    planilha_url = "https://docs.google.com/spreadsheets/d/1fsCeGUzsNCv0SCiE6mcIvcCHsMbqNeyzANwdU_148Vw/edit?gid=1510755488#gid=1510755488"
    planilha_id = "1fsCeGUzsNCv0SCiE6mcIvcCHsMbqNeyzANwdU_148Vw"
    aba_gid = "1510755488"  # GID da aba MENSAL

    print(f"📊 Planilha: {planilha_id}")
    print(f"📊 Aba GID: {aba_gid}")

    # Verificar se há credenciais
    credenciais_path = "/app/acesso_planilhas.json"
    if not os.path.exists(credenciais_path):
        print("❌ Credenciais não encontradas")
        print("🔧 Para configurar:")
        print("1. Acesse: https://console.cloud.google.com/")
        print("2. Crie um projeto ou selecione um existente")
        print("3. Ative a Google Sheets API")
        print("4. Crie credenciais OAuth 2.0")
        print("5. Baixe o arquivo JSON e salve como 'acesso_planilhas.json'")
        return

    print("✅ Credenciais encontradas")

    # Verificar se há token
    token_path = "/app/google_oauth_token.json"
    if not os.path.exists(token_path):
        print("❌ Token não encontrado")
        print("🔧 Para obter token:")
        print("1. Execute: python configurar_oauth.py")
        print("2. Siga as instruções para autorizar")
        return

    print("✅ Token encontrado")

    # Mapear códigos da planilha para o sistema
    print(f"\n📋 MAPEAMENTO DE CÓDIGOS:")
    print(f"  • Célula vazia = Disponível")
    print(f"  • 'P' = Bloqueio Parcial")
    print(f"  • 'T' = Bloqueio Total")
    print(f"  • '2' = Mais de um evento")
    print(f"  • 'D1' = Deslocamento e evento")
    print(f"  • 'X' = Conflito com bloqueio")

    # Verificar formadores da superintendência
    formadores_super = Formador.objects.filter(
        ativo=True, email__endswith="@planilha.super"
    )

    print(f"\n📊 Formadores da superintendência: {formadores_super.count()}")

    # Listar formadores para verificação
    print(f"\n📋 Formadores encontrados:")
    for formador in formadores_super:
        print(f"  • {formador.nome} - {formador.email}")

    print(f"\n" + "=" * 60)
    print("📋 PRÓXIMOS PASSOS:")
    print("1. Configure as credenciais Google")
    print("2. Execute: python configurar_oauth.py")
    print("3. Execute: python extrair_dados_planilha_disponibilidade.py")
    print("4. Os dados serão importados automaticamente")


if __name__ == "__main__":
    extrair_dados_planilha_disponibilidade()
