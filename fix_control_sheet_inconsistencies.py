#!/usr/bin/env python3
"""
Corrigir Inconsistências da Planilha de Controle
===============================================

Corrige as inconsistências entre a planilha de controle e a plataforma.

Author: Claude Code
Date: Setembro 2025
"""

import os
import sys
import json
import django
from pathlib import Path
from django.db import transaction

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
django.setup()

from core.models import Usuario, Setor, Municipio, Projeto, TipoEvento, Solicitacao


def load_control_sheet_data():
    """Carrega os dados da planilha de controle"""
    control_files = list(Path(".").glob("planilha_controle_2025_*.json"))
    if not control_files:
        return None

    with open(control_files[0], "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("dados", [])


def normalize_name(name):
    """Normaliza nome para comparação"""
    if not name:
        return ""

    # Converter para minúsculo e remover acentos básicos
    name = name.lower().strip()

    # Mapear acentos
    replacements = {
        "á": "a",
        "à": "a",
        "ã": "a",
        "â": "a",
        "é": "e",
        "è": "e",
        "ê": "e",
        "í": "i",
        "ì": "i",
        "î": "i",
        "ó": "o",
        "ò": "o",
        "õ": "o",
        "ô": "o",
        "ú": "u",
        "ù": "u",
        "û": "u",
        "ç": "c",
    }

    for old, new in replacements.items():
        name = name.replace(old, new)

    return name


def find_matching_municipio(municipio_planilha):
    """Encontra município correspondente na plataforma"""
    municipio_normalized = normalize_name(municipio_planilha)

    for municipio in Municipio.objects.all():
        municipio_plataforma = f"{municipio.nome} - {municipio.uf}"
        if normalize_name(municipio_plataforma) == municipio_normalized:
            return municipio

    return None


def find_matching_projeto(projeto_planilha):
    """Encontra projeto correspondente na plataforma"""
    projeto_normalized = normalize_name(projeto_planilha)

    # Mapear projetos específicos para genéricos
    projeto_mapping = {
        "acerta brasil matematica": "acerta",
        "acerta brasil portugues": "acerta",
        "acerta matemática": "acerta",
        "acerta português": "acerta",
        "novo lendo": "novo lendo",
        "projeto amma": "projeto amma",
        "brincando e aprendendo": "brincando e aprendendo",
        "tema": "tema",
        "vidas": "vidas",
        "ideb10": "ideb10",
        "ideb 10": "ideb10",
    }

    # Tentar mapeamento direto
    if projeto_normalized in projeto_mapping:
        projeto_nome = projeto_mapping[projeto_normalized]
        try:
            return Projeto.objects.get(nome__iexact=projeto_nome)
        except Projeto.DoesNotExist:
            pass

    # Tentar busca por similaridade
    for projeto in Projeto.objects.all():
        if normalize_name(projeto.nome) == projeto_normalized:
            return projeto

    return None


def find_matching_coordenador(coordenador_planilha):
    """Encontra coordenador correspondente na plataforma"""
    coordenador_normalized = normalize_name(coordenador_planilha)

    for usuario in Usuario.objects.filter(cargo="coordenador", is_active=True):
        nome_completo = f"{usuario.first_name} {usuario.last_name}".strip()
        if normalize_name(nome_completo) == coordenador_normalized:
            return usuario

    return None


def create_missing_municipios(control_data):
    """Cria municípios faltantes"""
    print("🏙️ CRIANDO MUNICÍPIOS FALTANTES")
    print("=" * 50)

    municipios_planilha = set()
    for item in control_data:
        municipio = item.get("municipio", "").strip()
        if municipio:
            municipios_planilha.add(municipio)

    created_count = 0
    for municipio_planilha in municipios_planilha:
        if not find_matching_municipio(municipio_planilha):
            # Extrair nome e UF
            if " - " in municipio_planilha:
                nome, uf = municipio_planilha.split(" - ", 1)
                nome = nome.strip()
                uf = uf.strip()
            else:
                nome = municipio_planilha
                uf = "CE"  # Default

            try:
                municipio, created = Municipio.objects.get_or_create(
                    nome=nome, uf=uf, defaults={"ativo": True}
                )
                if created:
                    created_count += 1
                    print(f"   ✅ Criado: {nome} - {uf}")
            except Exception as e:
                print(f"   ❌ Erro ao criar {nome} - {uf}: {e}")

    print(f"📊 Municípios criados: {created_count}")
    return created_count


def create_missing_projetos(control_data):
    """Cria projetos faltantes"""
    print("\n📋 CRIANDO PROJETOS FALTANTES")
    print("=" * 50)

    projetos_planilha = set()
    for item in control_data:
        projeto = item.get("projeto", "").strip()
        if projeto:
            projetos_planilha.add(projeto)

    created_count = 0
    for projeto_planilha in projetos_planilha:
        if not find_matching_projeto(projeto_planilha):
            # Determinar setor baseado no nome do projeto
            setor_nome = "Outros"  # Default
            if "acerta" in normalize_name(projeto_planilha):
                setor_nome = "ACerta"
            elif "brincando" in normalize_name(projeto_planilha):
                setor_nome = "Brincando"
            elif "vidas" in normalize_name(projeto_planilha):
                setor_nome = "Vidas"
            elif "ideb" in normalize_name(projeto_planilha):
                setor_nome = "IDEB 10"

            setor = Setor.objects.filter(nome=setor_nome).first()

            try:
                projeto, created = Projeto.objects.get_or_create(
                    nome=projeto_planilha, defaults={"setor": setor, "ativo": True}
                )
                if created:
                    created_count += 1
                    print(f"   ✅ Criado: {projeto_planilha} (setor: {setor_nome})")
            except Exception as e:
                print(f"   ❌ Erro ao criar {projeto_planilha}: {e}")

    print(f"📊 Projetos criados: {created_count}")
    return created_count


def create_missing_coordenadores(control_data):
    """Cria coordenadores faltantes"""
    print("\n👨‍💼 CRIANDO COORDENADORES FALTANTES")
    print("=" * 50)

    coordenadores_planilha = set()
    for item in control_data:
        coordenador = item.get("coordenador", "").strip()
        if coordenador:
            coordenadores_planilha.add(coordenador)

    created_count = 0
    for coordenador_planilha in coordenadores_planilha:
        if not find_matching_coordenador(coordenador_planilha):
            # Separar nome e sobrenome
            partes = coordenador_planilha.split()
            if len(partes) >= 2:
                first_name = partes[0]
                last_name = " ".join(partes[1:])
            else:
                first_name = coordenador_planilha
                last_name = ""

            try:
                usuario, created = Usuario.objects.get_or_create(
                    first_name=first_name,
                    last_name=last_name,
                    defaults={
                        "cargo": "coordenador",
                        "is_active": True,
                        "formador_ativo": False,
                    },
                )
                if created:
                    created_count += 1
                    print(f"   ✅ Criado: {first_name} {last_name}")
            except Exception as e:
                print(f"   ❌ Erro ao criar {coordenador_planilha}: {e}")

    print(f"📊 Coordenadores criados: {created_count}")
    return created_count


def create_relationships(control_data):
    """Cria relacionamentos município-projeto-coordenador"""
    print("\n🔗 CRIANDO RELACIONAMENTOS")
    print("=" * 50)

    created_count = 0
    error_count = 0

    for item in control_data:
        municipio_planilha = item.get("municipio", "").strip()
        projeto_planilha = item.get("projeto", "").strip()
        coordenador_planilha = item.get("coordenador", "").strip()

        if not (municipio_planilha and projeto_planilha and coordenador_planilha):
            continue

        # Encontrar objetos correspondentes
        municipio = find_matching_municipio(municipio_planilha)
        projeto = find_matching_projeto(projeto_planilha)
        coordenador = find_matching_coordenador(coordenador_planilha)

        if not (municipio and projeto and coordenador):
            error_count += 1
            continue

        # Criar solicitação de exemplo para estabelecer o relacionamento
        try:
            from django.utils import timezone
            from datetime import timedelta

            solicitacao, created = Solicitacao.objects.get_or_create(
                titulo_evento=f"Relacionamento {municipio.nome} - {projeto.nome}",
                data_inicio=timezone.now() + timedelta(days=30),
                defaults={
                    "projeto": projeto,
                    "municipio": municipio,
                    "tipo_evento": TipoEvento.objects.first(),
                    "usuario_solicitante": coordenador,
                    "data_fim": timezone.now() + timedelta(days=30, hours=4),
                    "status": "aprovado",
                    "observacoes": f"Relacionamento criado da planilha de controle: {coordenador_planilha}",
                    "data_solicitacao": timezone.now(),
                    "coordenador_acompanha": True,
                },
            )

            if created:
                created_count += 1
                if created_count % 50 == 0:
                    print(f"   📊 Criados: {created_count} relacionamentos...")

        except Exception as e:
            error_count += 1
            if error_count <= 5:  # Mostrar apenas os primeiros 5 erros
                print(f"   ❌ Erro: {e}")

    print(f"📊 Relacionamentos criados: {created_count}")
    print(f"❌ Erros: {error_count}")
    return created_count


def main():
    """Função principal"""
    print("🔧 CORRIGINDO INCONSISTÊNCIAS DA PLANILHA DE CONTROLE")
    print("=" * 80)

    # Carregar dados da planilha
    control_data = load_control_sheet_data()
    if not control_data:
        print("❌ Não foi possível carregar os dados da planilha")
        return False

    print(f"📊 Dados carregados: {len(control_data)} registros")

    with transaction.atomic():
        # Criar entidades faltantes
        municipios_criados = create_missing_municipios(control_data)
        projetos_criados = create_missing_projetos(control_data)
        coordenadores_criados = create_missing_coordenadores(control_data)
        relacionamentos_criados = create_relationships(control_data)

    print("\n📊 RESUMO DA CORREÇÃO")
    print("=" * 50)
    print(f"✅ Municípios criados: {municipios_criados}")
    print(f"✅ Projetos criados: {projetos_criados}")
    print(f"✅ Coordenadores criados: {coordenadores_criados}")
    print(f"✅ Relacionamentos criados: {relacionamentos_criados}")

    total_criados = (
        municipios_criados
        + projetos_criados
        + coordenadores_criados
        + relacionamentos_criados
    )
    print(f"\n🎯 Total de entidades criadas: {total_criados}")

    print("=" * 80)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
