#!/usr/bin/env python3
"""
Importação Simplificada de Dados
================================

Importa dados das planilhas de forma simplificada.

Author: Claude Code
Date: Setembro 2025
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

from django.contrib.auth.models import Group
from django.db import transaction
from django.utils import timezone

from core.models import (
    Municipio,
    Projeto,
    Setor,
    Solicitacao,
    SolicitacaoStatus,
    TipoEvento,
    Usuario,
)


def normalize_cpf(cpf):
    """Normaliza CPF"""
    if not cpf:
        return None
    cpf_limpo = re.sub(r"\D", "", str(cpf))
    if len(cpf_limpo) == 11:
        return cpf_limpo
    return None


def normalize_name(name):
    """Normaliza nome"""
    if not name:
        return None
    return " ".join(word.capitalize() for word in str(name).strip().split())


def get_or_create_setor(nome, sigla=None):
    """Obtém ou cria setor"""
    if not nome:
        return None

    nome_normalizado = normalize_name(nome)
    if not nome_normalizado:
        return None

    setor, created = Setor.objects.get_or_create(
        nome=nome_normalizado,
        defaults={
            "sigla": sigla or nome_normalizado[:3].upper(),
            "ativo": True,
            "vinculado_superintendencia": False,
        },
    )

    if created:
        print(f"   ✅ Setor criado: {nome_normalizado}")

    return setor


def get_or_create_municipio(nome, uf="CE"):
    """Obtém ou cria município"""
    if not nome:
        return None

    # Limpar nome
    nome_limpo = str(nome).strip()
    if " - " in nome_limpo:
        nome_limpo = nome_limpo.split(" - ")[0].strip()

    nome_normalizado = normalize_name(nome_limpo)
    if not nome_normalizado:
        return None

    municipio, created = Municipio.objects.get_or_create(
        nome=nome_normalizado, uf=uf, defaults={"ativo": True}
    )

    if created:
        print(f"   ✅ Município criado: {nome_normalizado} - {uf}")

    return municipio


def get_or_create_projeto(nome, setor=None):
    """Obtém ou cria projeto"""
    if not nome:
        return None

    nome_normalizado = normalize_name(nome)
    if not nome_normalizado:
        return None

    # Mapear projetos específicos para genéricos
    project_mapping = {
        "ACERTA MATEMÁTICA": "ACerta",
        "ACERTA PORTUGUÊS": "ACerta",
        "NOVO LENDO": "Lendo e Escrevendo",
        "VIDA E MATEMÁTICA": "Vida & Matemática",
        "VIDA E LINGUAGEM": "Vida & Linguagem",
        "BRINCANDO E APRENDENDO": "Brincando e Aprendendo",
        "LENDO E ESCREVENDO": "Lendo e Escrevendo",
        "PROJETO AMMA": "Projeto AMMA",
        "VIDA E CIÊNCIAS": "Vida & Ciências",
    }

    nome_final = project_mapping.get(nome_normalizado, nome_normalizado)

    projeto, created = Projeto.objects.get_or_create(
        nome=nome_final,
        defaults={"setor": setor or get_or_create_setor("Outros"), "ativo": True},
    )

    if created:
        print(f"   ✅ Projeto criado: {nome_final}")

    return projeto


def get_or_create_tipo_evento(nome):
    """Obtém ou cria tipo de evento"""
    if not nome:
        return None

    nome_normalizado = normalize_name(nome)
    if not nome_normalizado:
        return None

    # Mapear tipos específicos
    tipo_mapping = {
        "Presencial": "Formação Presencial",
        "Online": "Formação Online",
        "Acompanhamento": "Acompanhamento",
        "Deslocamento": "Deslocamento",
        "Retorno": "Retorno",
    }

    nome_final = tipo_mapping.get(nome_normalizado, nome_normalizado)

    tipo_evento, created = TipoEvento.objects.get_or_create(
        nome=nome_final, defaults={"ativo": True, "online": "Online" in nome_final}
    )

    if created:
        print(f"   ✅ Tipo de evento criado: {nome_final}")

    return tipo_evento


def import_usuarios_simple():
    """Importa usuários de forma simplificada"""
    print("👥 IMPORTANDO USUÁRIOS SIMPLIFICADO")
    print("=" * 50)

    # Encontrar arquivo de usuários mais recente
    usuarios_files = [
        f
        for f in os.listdir(".")
        if f.startswith("usuarios_planilha_") and f.endswith(".json")
    ]
    if not usuarios_files:
        print("❌ Arquivo de usuários não encontrado")
        return

    latest_file = max(usuarios_files)
    print(f"📋 Carregando: {latest_file}")

    with open(latest_file, "r", encoding="utf-8") as f:
        usuarios_data = json.load(f)

    imported_count = 0
    updated_count = 0

    for ws in usuarios_data.get("worksheets", []):
        ws_title = ws.get("title", "")
        records = ws.get("records", [])

        print(f"📊 Processando {ws_title}: {len(records)} registros")

        for record in records:
            try:
                # Extrair dados
                nome_completo = record.get("Nome Completo", "") or record.get(
                    "Nome", ""
                )
                cpf = record.get("CPF", "")
                email = record.get("Email", "")
                telefone = record.get("Telefone", "")
                cargo = record.get("Cargo", "")

                if not nome_completo:
                    continue

                # Normalizar dados
                cpf_limpo = normalize_cpf(cpf)
                nome_normalizado = normalize_name(nome_completo)

                # Determinar se é ativo
                is_active = "Ativos" in ws_title
                formador_ativo = cargo and "formador" in cargo.lower()

                # Criar ou atualizar usuário
                if cpf_limpo:
                    usuario, created = Usuario.objects.update_or_create(
                        cpf=cpf_limpo,
                        defaults={
                            "first_name": (
                                nome_normalizado.split()[0] if nome_normalizado else ""
                            ),
                            "last_name": (
                                " ".join(nome_normalizado.split()[1:])
                                if len(nome_normalizado.split()) > 1
                                else ""
                            ),
                            "email": email or "",
                            "telefone": telefone or "",
                            "cargo": cargo or "",
                            "is_active": is_active,
                            "formador_ativo": formador_ativo,
                            "username": cpf_limpo,
                        },
                    )
                else:
                    # Se não tem CPF, usar nome como username
                    username = re.sub(r"\W+", "", nome_normalizado.lower())
                    usuario, created = Usuario.objects.update_or_create(
                        username=username,
                        defaults={
                            "first_name": (
                                nome_normalizado.split()[0] if nome_normalizado else ""
                            ),
                            "last_name": (
                                " ".join(nome_normalizado.split()[1:])
                                if len(nome_normalizado.split()) > 1
                                else ""
                            ),
                            "email": email or "",
                            "telefone": telefone or "",
                            "cargo": cargo or "",
                            "is_active": is_active,
                            "formador_ativo": formador_ativo,
                        },
                    )

                if created:
                    imported_count += 1
                    print(f"   ✅ Usuário criado: {nome_normalizado}")
                else:
                    updated_count += 1

                # Adicionar a grupos
                if cargo:
                    if "formador" in cargo.lower():
                        grupo, _ = Group.objects.get_or_create(name="formador")
                        usuario.groups.add(grupo)
                    elif "coordenador" in cargo.lower():
                        grupo, _ = Group.objects.get_or_create(name="coordenador")
                        usuario.groups.add(grupo)
                    elif "gerente" in cargo.lower():
                        grupo, _ = Group.objects.get_or_create(name="gerente")
                        usuario.groups.add(grupo)

            except Exception as e:
                print(
                    f"   ❌ Erro ao processar usuário {record.get('Nome', 'N/A')}: {e}"
                )

    print(f"📊 Usuários importados: {imported_count}")
    print(f"📊 Usuários atualizados: {updated_count}")


def import_coordenadores_simple():
    """Importa coordenadores de forma simplificada"""
    print("\n👨‍💼 IMPORTANDO COORDENADORES SIMPLIFICADO")
    print("=" * 50)

    # Encontrar arquivo de controle mais recente
    controle_files = [
        f
        for f in os.listdir(".")
        if f.startswith("controle_planilha_") and f.endswith(".json")
    ]
    if not controle_files:
        print("❌ Arquivo de controle não encontrado")
        return

    latest_file = max(controle_files)
    print(f"📋 Carregando: {latest_file}")

    with open(latest_file, "r", encoding="utf-8") as f:
        controle_data = json.load(f)

    coordenadores_importados = set()

    for ws in controle_data.get("worksheets", []):
        ws_title = ws.get("title", "")
        records = ws.get("records", [])

        if "AÇÕES" not in ws_title:
            continue

        print(f"📊 Processando {ws_title}: {len(records)} registros")

        for record in records:
            try:
                coordenador_nome = record.get("Coordenador", "")

                if not coordenador_nome or coordenador_nome in coordenadores_importados:
                    continue

                coordenadores_importados.add(coordenador_nome)

                # Normalizar nome
                nome_normalizado = normalize_name(coordenador_nome)
                if not nome_normalizado:
                    continue

                # Tentar encontrar por nome
                usuario = Usuario.objects.filter(
                    first_name__icontains=nome_normalizado.split()[0],
                    last_name__icontains=(
                        " ".join(nome_normalizado.split()[1:])
                        if len(nome_normalizado.split()) > 1
                        else ""
                    ),
                ).first()

                if usuario:
                    # Atualizar cargo se necessário
                    if usuario.cargo != "coordenador":
                        usuario.cargo = "coordenador"
                        usuario.save()

                    # Adicionar ao grupo
                    grupo, _ = Group.objects.get_or_create(name="coordenador")
                    usuario.groups.add(grupo)

                    print(f"   ✅ Coordenador atualizado: {nome_normalizado}")
                else:
                    # Criar novo coordenador
                    username = re.sub(r"\W+", "", nome_normalizado.lower())
                    usuario, created = Usuario.objects.get_or_create(
                        username=username,
                        defaults={
                            "first_name": (
                                nome_normalizado.split()[0] if nome_normalizado else ""
                            ),
                            "last_name": (
                                " ".join(nome_normalizado.split()[1:])
                                if len(nome_normalizado.split()) > 1
                                else ""
                            ),
                            "cargo": "coordenador",
                            "is_active": True,
                            "formador_ativo": False,
                        },
                    )

                    if created:
                        print(f"   ✅ Coordenador criado: {nome_normalizado}")

                    # Adicionar ao grupo
                    grupo, _ = Group.objects.get_or_create(name="coordenador")
                    usuario.groups.add(grupo)

            except Exception as e:
                print(f"   ❌ Erro ao processar coordenador: {e}")

    print(f"📊 Coordenadores processados: {len(coordenadores_importados)}")


def main():
    """Função principal"""
    print("📥 IMPORTAÇÃO SIMPLIFICADA DE DADOS")
    print("=" * 80)

    try:
        # Importar usuários
        import_usuarios_simple()

        # Importar coordenadores
        import_coordenadores_simple()

        print("\n" + "=" * 80)
        print("✅ IMPORTAÇÃO SIMPLIFICADA CONCLUÍDA!")
        print("=" * 80)

        return True

    except Exception as e:
        print(f"\n❌ Erro durante importação: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
