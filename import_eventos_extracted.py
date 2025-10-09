#!/usr/bin/env python
"""
IMPORTADOR DE EVENTOS - Dados já extraídos do Google Sheets

Este script importa os eventos/solicitações usando os dados já extraídos
do arquivo mapeamento_completo_google_sheets_20250923_220315.json

Importará aproximadamente 6.000+ registros de eventos.
"""

import os
import sys
import json
import django
from datetime import datetime, time

# Configuração do Django
sys.path.append(".")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
django.setup()

from django.db import transaction
from django.contrib.auth import get_user_model
from core.models import (
    Municipio,
    Projeto,
    TipoEvento,
    Solicitacao,
    SolicitacaoStatus,
    Setor,
)

User = get_user_model()


def normalizar_data(data_str, hora_str="08:00"):
    """Converter data DD/MM/YYYY + hora HH:MM para datetime"""
    if not data_str or data_str.strip() == "":
        return None

    try:
        # Remover espaços e processar data
        data_str = data_str.strip()
        if "/" in data_str:
            dia, mes, ano = data_str.split("/")
            dia, mes, ano = int(dia), int(mes), int(ano)
        else:
            return None

        # Processar hora
        if hora_str and ":" in hora_str:
            hora, minuto = hora_str.split(":")[:2]
            hora, minuto = int(hora), int(minuto)
        else:
            hora, minuto = 8, 0

        return datetime(ano, mes, dia, hora, minuto)
    except Exception as e:
        print(f"❌ Erro ao processar data '{data_str}' + hora '{hora_str}': {e}")
        return None


def obter_ou_criar_municipio(nome):
    """Obter ou criar município"""
    if not nome or nome.strip() == "":
        return None

    nome = nome.strip()

    # Buscar por nome exato
    municipio = Municipio.objects.filter(nome__iexact=nome).first()
    if municipio:
        return municipio

    # Criar novo município (assumir CE como padrão)
    municipio = Municipio.objects.create(
        nome=nome, uf="CE", ativo=True  # Padrão baseado nos dados existentes
    )
    print(f"✅ Município criado: {nome}/CE")
    return municipio


def obter_ou_criar_projeto(nome):
    """Obter ou criar projeto"""
    if not nome or nome.strip() == "":
        nome = "Outros"

    nome = nome.strip()

    # Buscar por nome exato
    projeto = Projeto.objects.filter(nome__iexact=nome).first()
    if projeto:
        return projeto

    # Criar novo projeto
    projeto = Projeto.objects.create(nome=nome, ativo=True)
    print(f"✅ Projeto criado: {nome}")
    return projeto


def obter_ou_criar_tipo_evento(nome):
    """Obter ou criar tipo de evento"""
    if not nome or nome.strip() == "":
        nome = "Formação"

    nome = nome.strip()

    # Mapear abreviações comuns
    mapeamento = {
        "LP": "Língua Portuguesa",
        "MAT": "Matemática",
        "FORM": "Formação",
        "Presencial": "Presencial",
        "Online": "Online",
    }
    nome = mapeamento.get(nome, nome)

    tipo = TipoEvento.objects.filter(nome__iexact=nome).first()
    if tipo:
        return tipo

    tipo = TipoEvento.objects.create(
        nome=nome, online=(nome.lower() == "online"), ativo=True
    )
    print(f"✅ Tipo evento criado: {nome}")
    return tipo


def buscar_formador(nome):
    """Buscar formador por nome"""
    if not nome or nome.strip() == "":
        return None

    nome = nome.strip()

    # Buscar por nome completo ou parcial
    user = User.objects.filter(
        first_name__icontains=nome.split()[0], formador_ativo=True
    ).first()

    return user


def importar_aba(dados_aba, nome_aba):
    """Importar uma aba específica"""
    print(f"\n🚀 Importando aba: {nome_aba}")
    print(f"📊 Registros válidos: {dados_aba.get('registros_validos', 0)}")

    registros = dados_aba.get("registros", [])
    cabecalhos = dados_aba.get("cabecalhos", [])

    if not registros:
        print("❌ Nenhum registro encontrado")
        return 0

    contador = 0
    erros = 0

    # Obter projeto padrão para esta aba
    projeto_padrao = obter_ou_criar_projeto(nome_aba)

    for i, registro in enumerate(registros[:100]):  # Começar com 100 para teste
        try:
            if len(registro) < 10:  # Validação básica
                continue

            # Extrair campos (baseado na análise dos cabeçalhos)
            municipio_nome = registro[4] if len(registro) > 4 else ""
            data_str = registro[6] if len(registro) > 6 else ""
            hora_inicio = registro[7] if len(registro) > 7 else "08:00"
            hora_fim = registro[8] if len(registro) > 8 else "12:00"
            projeto_nome = registro[9] if len(registro) > 9 else nome_aba
            tipo_evento_nome = registro[10] if len(registro) > 10 else "Formação"
            formador_nome = registro[12] if len(registro) > 12 else ""

            # Validações básicas
            if not municipio_nome or not data_str:
                continue

            # Processar dados
            municipio = obter_ou_criar_municipio(municipio_nome)
            if not municipio:
                continue

            data_inicio = normalizar_data(data_str, hora_inicio)
            data_fim = normalizar_data(data_str, hora_fim)

            if not data_inicio or not data_fim:
                continue

            projeto = obter_ou_criar_projeto(projeto_nome)
            tipo_evento = obter_ou_criar_tipo_evento(tipo_evento_nome)

            # Criar solicitação
            solicitacao = Solicitacao.objects.create(
                titulo_evento=f"{projeto.nome} - {municipio.nome}",
                projeto=projeto,
                municipio=municipio,
                tipo_evento=tipo_evento,
                data_inicio=data_inicio,
                data_fim=data_fim,
                numero_encontro_formativo=registro[5] if len(registro) > 5 else "1",
                coordenador_acompanha=True,
                observacoes=f"Importado da aba {nome_aba}",
                status=SolicitacaoStatus.APROVADO,  # Dados históricos já aprovados
            )

            # Tentar associar formador se encontrado
            if formador_nome:
                formador = buscar_formador(formador_nome)
                if formador:
                    solicitacao.formadores.add(formador)

            contador += 1

            if contador % 50 == 0:
                print(f"  📈 Processados: {contador}")

        except Exception as e:
            erros += 1
            print(f"❌ Erro no registro {i}: {e}")

    print(f"✅ Aba {nome_aba}: {contador} solicitações importadas, {erros} erros")
    return contador


def main():
    """Função principal"""
    print("🚀 INICIANDO IMPORTAÇÃO DE EVENTOS DOS DADOS EXTRAÍDOS")

    # Carregar dados extraídos
    arquivo_dados = "mapeamento_completo_google_sheets_20250923_220315.json"

    if not os.path.exists(arquivo_dados):
        print(f"❌ Arquivo não encontrado: {arquivo_dados}")
        return

    print(f"📂 Carregando dados de: {arquivo_dados}")

    with open(arquivo_dados, "r", encoding="utf-8") as f:
        dados = json.load(f)

    # Encontrar planilha de agenda
    planilha_agenda = None
    for nome, planilha in dados.get("planilhas", {}).items():
        if "Acompanhamento" in nome and "Agenda" in nome:
            planilha_agenda = planilha
            break

    if not planilha_agenda:
        print("❌ Planilha de agenda não encontrada")
        return

    print(f"📊 Planilha encontrada: {planilha_agenda.get('nome')}")
    print(f"📋 Total de abas: {planilha_agenda.get('total_abas', 0)}")

    # Importar abas priorizadas
    abas_importar = ["Super", "ACerta", "Outros", "Brincando", "Vidas"]
    total_importado = 0

    with transaction.atomic():
        for aba_config in planilha_agenda.get("abas", []):
            nome_aba = aba_config.get("nome")

            if nome_aba in abas_importar:
                total_importado += importar_aba(aba_config, nome_aba)

    print(f"\n🎉 IMPORTAÇÃO CONCLUÍDA!")
    print(f"📊 Total importado: {total_importado} solicitações")

    # Verificar resultado
    print(f"\n📈 ESTATÍSTICAS FINAIS:")
    print(f"👥 Usuários: {User.objects.count()}")
    print(f"🏙️ Municípios: {Municipio.objects.count()}")
    print(f"🏛️ Projetos: {Projeto.objects.count()}")
    print(f"⭐ Tipos Evento: {TipoEvento.objects.count()}")
    print(f"📋 Solicitações: {Solicitacao.objects.count()}")


if __name__ == "__main__":
    main()
