#!/usr/bin/env python3
"""
Importação de Usuários Corrigida
===============================

Importa usuários de forma mais simples, evitando o erro de FOR UPDATE.

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

from core.models import Usuario


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


def import_users_fixed():
    """Importa usuários de forma corrigida"""
    print("👥 IMPORTANDO USUÁRIOS CORRIGIDO")
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
    error_count = 0

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

                # Usar get_or_create em vez de update_or_create
                if cpf_limpo:
                    # Tentar encontrar por CPF primeiro
                    try:
                        usuario = Usuario.objects.get(cpf=cpf_limpo)
                        # Atualizar campos
                        usuario.first_name = (
                            nome_normalizado.split()[0] if nome_normalizado else ""
                        )
                        usuario.last_name = (
                            " ".join(nome_normalizado.split()[1:])
                            if len(nome_normalizado.split()) > 1
                            else ""
                        )
                        usuario.email = email or ""
                        usuario.telefone = telefone or ""
                        usuario.cargo = cargo or ""
                        usuario.is_active = is_active
                        usuario.formador_ativo = formador_ativo
                        usuario.username = cpf_limpo
                        usuario.save()
                        updated_count += 1
                        print(f"   ✅ Usuário atualizado: {nome_normalizado}")
                    except Usuario.DoesNotExist:
                        # Criar novo usuário
                        usuario = Usuario.objects.create(
                            cpf=cpf_limpo,
                            first_name=(
                                nome_normalizado.split()[0] if nome_normalizado else ""
                            ),
                            last_name=(
                                " ".join(nome_normalizado.split()[1:])
                                if len(nome_normalizado.split()) > 1
                                else ""
                            ),
                            email=email or "",
                            telefone=telefone or "",
                            cargo=cargo or "",
                            is_active=is_active,
                            formador_ativo=formador_ativo,
                            username=cpf_limpo,
                        )
                        imported_count += 1
                        print(f"   ✅ Usuário criado: {nome_normalizado}")
                else:
                    # Se não tem CPF, usar nome como username
                    username = re.sub(r"\W+", "", nome_normalizado.lower())
                    try:
                        usuario = Usuario.objects.get(username=username)
                        # Atualizar campos
                        usuario.first_name = (
                            nome_normalizado.split()[0] if nome_normalizado else ""
                        )
                        usuario.last_name = (
                            " ".join(nome_normalizado.split()[1:])
                            if len(nome_normalizado.split()) > 1
                            else ""
                        )
                        usuario.email = email or ""
                        usuario.telefone = telefone or ""
                        usuario.cargo = cargo or ""
                        usuario.is_active = is_active
                        usuario.formador_ativo = formador_ativo
                        usuario.save()
                        updated_count += 1
                        print(f"   ✅ Usuário atualizado: {nome_normalizado}")
                    except Usuario.DoesNotExist:
                        # Criar novo usuário
                        usuario = Usuario.objects.create(
                            username=username,
                            first_name=(
                                nome_normalizado.split()[0] if nome_normalizado else ""
                            ),
                            last_name=(
                                " ".join(nome_normalizado.split()[1:])
                                if len(nome_normalizado.split()) > 1
                                else ""
                            ),
                            email=email or "",
                            telefone=telefone or "",
                            cargo=cargo or "",
                            is_active=is_active,
                            formador_ativo=formador_ativo,
                        )
                        imported_count += 1
                        print(f"   ✅ Usuário criado: {nome_normalizado}")

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
                error_count += 1
                print(
                    f"   ❌ Erro ao processar usuário {record.get('Nome', 'N/A')}: {e}"
                )

    print(f"📊 Usuários importados: {imported_count}")
    print(f"📊 Usuários atualizados: {updated_count}")
    print(f"❌ Erros: {error_count}")


def main():
    """Função principal"""
    print("📥 IMPORTAÇÃO DE USUÁRIOS CORRIGIDA")
    print("=" * 80)

    try:
        import_users_fixed()

        print("\n" + "=" * 80)
        print("✅ IMPORTAÇÃO DE USUÁRIOS CONCLUÍDA!")
        print("=" * 80)

        return True

    except Exception as e:
        print(f"\n❌ Erro durante importação: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
