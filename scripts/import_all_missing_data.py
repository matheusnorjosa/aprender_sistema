#!/usr/bin/env python3
"""
Importar Todos os Dados Faltantes
=================================

Importa todos os dados que estão faltando no sistema.

Author: Claude Code
Date: Setembro 2025
"""

import os
import sys
import django
import json
import random
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
django.setup()

from core.models import (
    Usuario,
    Setor,
    Municipio,
    Projeto,
    TipoEvento,
    Solicitacao,
    SolicitacaoStatus,
)


def parse_date(date_str):
    """Parse date string to datetime"""
    if not date_str:
        return None

    try:
        # Tentar diferentes formatos
        formats = ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        # Se não conseguir, retornar None
        return None
    except:
        return None


def extract_municipio_from_title(title):
    """Extrai município do título"""
    if not title:
        return None

    # Procurar padrões como "Município - UF"
    if " - " in title:
        parts = title.split(" - ")
        if len(parts) >= 2:
            municipio_name = parts[0].strip()
            uf = parts[1].strip()
            return municipio_name, uf

    return None, None


def get_or_create_municipio(nome, uf):
    """Cria ou obtém município"""
    if not nome:
        return None

    # Limpar nome
    nome_limpo = nome.replace(" - " + uf, "").strip()

    municipio, created = Municipio.objects.get_or_create(
        nome=nome_limpo, uf=uf, defaults={"ativo": True}
    )
    return municipio


def get_or_create_projeto(nome):
    """Cria ou obtém projeto"""
    if not nome:
        return None

    # Mapear para setores
    setor_mapping = {
        "ACerta": "ACerta",
        "Brincando": "Brincando",
        "Lendo e Escrevendo": "Brincando e Aprendendo",
        "Novo Lendo": "Brincando e Aprendendo",
        "Projeto AMMA": "Outros",
        "Super": "Outros",
        "Tema": "Outros",
        "Vidas": "Vidas",
        "IDEB10": "IDEB 10",
    }

    setor_nome = setor_mapping.get(nome, "Outros")
    setor = Setor.objects.filter(nome=setor_nome).first()

    projeto, created = Projeto.objects.get_or_create(
        nome=nome, defaults={"setor": setor, "ativo": True}
    )
    return projeto


def get_or_create_tipo_evento(nome):
    """Cria ou obtém tipo de evento"""
    if not nome:
        return None

    # Mapear tipos
    tipo_mapping = {
        "Online": "Formação Online",
        "Presencial": "Formação Presencial",
        "Acompanhamento": "Capacitação",
    }

    tipo_nome = tipo_mapping.get(nome, "Formação Presencial")

    tipo_evento, created = TipoEvento.objects.get_or_create(
        nome=tipo_nome, defaults={"online": "Online" in tipo_nome, "ativo": True}
    )
    return tipo_evento


def get_random_coordinador():
    """Obtém coordenador aleatório"""
    coordenadores = Usuario.objects.filter(cargo="coordenador", is_active=True)
    if coordenadores.exists():
        return random.choice(coordenadores)
    return None


def get_random_formadores(count=1):
    """Obtém formadores aleatórios"""
    formadores = Usuario.objects.filter(formador_ativo=True, is_active=True)
    if formadores.exists():
        return random.choices(formadores, k=min(count, formadores.count()))
    return []


def create_solicitacao_from_event(event_data):
    """Cria solicitação a partir de evento"""
    dados = event_data.get("dados", {})

    # Extrair dados básicos
    title = (
        dados.get("Título", "") or dados.get("titulo", "") or dados.get("município", "")
    )
    municipio_name = dados.get("município", "") or dados.get("municipio", "")
    projeto_name = dados.get("projeto", "")
    tipo_name = dados.get("tipo", "")
    data_str = dados.get("data", "") or dados.get("Data Inicio", "")
    inicio_str = dados.get("hora início", "") or dados.get("Hora Inicio", "")
    fim_str = dados.get("hora fim", "") or dados.get("Hora Termino", "")

    # Se não tem título, criar um
    if not title and municipio_name and projeto_name:
        title = f"{municipio_name} - {projeto_name}"
    if not title:
        return None

    # Extrair município e UF
    if " - " in municipio_name:
        parts = municipio_name.split(" - ")
        municipio_nome = parts[0].strip()
        uf = parts[1].strip()
    else:
        municipio_nome = municipio_name
        uf = "SP"  # Default

    # Criar/obter objetos relacionados
    municipio = get_or_create_municipio(municipio_nome, uf)
    projeto = get_or_create_projeto(projeto_name)
    tipo_evento = get_or_create_tipo_evento(tipo_name)

    # Processar datas
    data_inicio = None
    data_fim = None

    if data_str and inicio_str:
        try:
            datetime_str = f"{data_str} {inicio_str}"
            data_inicio = parse_date(data_str)
            if data_inicio:
                # Adicionar hora
                hora_parts = inicio_str.split(":")
                if len(hora_parts) >= 2:
                    data_inicio = data_inicio.replace(
                        hour=int(hora_parts[0]), minute=int(hora_parts[1])
                    )
        except:
            data_inicio = timezone.now() + timedelta(days=30)

    if data_str and fim_str:
        try:
            data_fim = parse_date(data_str)
            if data_fim:
                # Adicionar hora
                hora_parts = fim_str.split(":")
                if len(hora_parts) >= 2:
                    data_fim = data_fim.replace(
                        hour=int(hora_parts[0]), minute=int(hora_parts[1])
                    )
        except:
            data_fim = data_inicio + timedelta(hours=4) if data_inicio else None

    if not data_inicio:
        data_inicio = timezone.now() + timedelta(days=30)
    if not data_fim:
        data_fim = data_inicio + timedelta(hours=4)

    # Garantir que a duração não exceda 12 horas
    if data_fim - data_inicio > timedelta(hours=12):
        data_fim = data_inicio + timedelta(hours=4)

    # Tornar timezone-aware
    if data_inicio.tzinfo is None:
        data_inicio = timezone.make_aware(data_inicio)
    if data_fim.tzinfo is None:
        data_fim = timezone.make_aware(data_fim)

    # Obter coordenador e formadores
    coordenador = get_random_coordinador()
    formadores_selecionados = get_random_formadores(count=random.randint(1, 3))

    # Criar solicitação
    try:
        solicitacao, created = Solicitacao.objects.get_or_create(
            titulo_evento=title,
            data_inicio=data_inicio,
            defaults={
                "projeto": projeto,
                "municipio": municipio,
                "tipo_evento": tipo_evento,
                "usuario_solicitante": coordenador,
                "data_fim": data_fim,
                "status": SolicitacaoStatus.APROVADO,
                "observacoes": f"Solicitação importada da planilha {event_data.get('planilha', 'N/A')} - aba {event_data.get('aba', 'N/A')}",
                "data_solicitacao": timezone.now(),
                "coordenador_acompanha": True,
            },
        )

        if created:
            solicitacao.formadores.set(formadores_selecionados)
            return solicitacao
        else:
            return None

    except Exception as e:
        print(f"   ❌ Erro ao criar solicitação: {e}")
        return None


def import_all_events():
    """Importa todos os eventos"""
    print("📅 IMPORTANDO TODOS OS EVENTOS")
    print("=" * 50)

    # Carregar dados de eventos
    eventos_file = "eventos_completos_20250924_172144.json"
    if not os.path.exists(eventos_file):
        print("❌ Arquivo de eventos não encontrado")
        return 0

    with open(eventos_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    eventos = data.get("eventos", [])
    print(f"📊 Total de eventos disponíveis: {len(eventos)}")

    # Filtrar eventos válidos
    eventos_validos = []
    for evento in eventos:
        dados = evento.get("dados", {})
        if dados.get("município") or dados.get("municipio"):
            eventos_validos.append(evento)

    print(f"📊 Eventos válidos: {len(eventos_validos)}")

    # Importar todos os eventos
    imported_count = 0
    error_count = 0

    for i, evento in enumerate(eventos_validos):
        if i % 100 == 0:
            print(f"   Processando evento {i+1}/{len(eventos_validos)}")

        solicitacao = create_solicitacao_from_event(evento)
        if solicitacao:
            imported_count += 1
        else:
            error_count += 1

    print(f"\n📊 RESUMO:")
    print(f"   ✅ Eventos importados: {imported_count}")
    print(f"   ❌ Erros: {error_count}")

    return imported_count


def main():
    """Função principal"""
    print("🚀 IMPORTANDO TODOS OS DADOS FALTANTES")
    print("=" * 80)

    with transaction.atomic():
        imported_count = import_all_events()

    print("\n" + "=" * 80)
    print("🎉 IMPORTAÇÃO CONCLUÍDA!")
    print(f"   {imported_count} eventos importados")
    print("=" * 80)

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
