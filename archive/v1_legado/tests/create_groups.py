#!/usr/bin/env python
"""
Script para criar grupos e permissões Django manualmente
Execute: python create_groups.py
"""

import os
import sys

import django

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
django.setup()

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from core.models import Aprovacao, DisponibilidadeFormadores, LogAuditoria, Solicitacao


def create_groups_and_permissions():
    """
    Cria os grupos (papéis) e associa as permissões adequadas
    """
    print("=== CRIANDO GRUPOS E PERMISSÕES ===\n")

    # Obter ContentTypes
    solicitacao_ct = ContentType.objects.get_for_model(Solicitacao)
    aprovacao_ct = ContentType.objects.get_for_model(Aprovacao)
    log_ct = ContentType.objects.get_for_model(LogAuditoria)
    disponibilidade_ct = ContentType.objects.get_for_model(DisponibilidadeFormadores)

    # Criar permissões customizadas se não existirem
    sync_calendar_perm, created = Permission.objects.get_or_create(
        codename="sync_calendar",
        name="Can sync with Google Calendar",
        content_type=solicitacao_ct,
    )
    if created:
        print("✅ Permissão 'sync_calendar' criada")

    view_relatorios_perm, created = Permission.objects.get_or_create(
        codename="view_relatorios",
        name="Can view consolidated reports",
        content_type=log_ct,
    )
    if created:
        print("✅ Permissão 'view_relatorios' criada")

    print()

    # Definir grupos e suas permissões
    groups_permissions = {
        "superintendencia": [
            # Solicitações
            "view_solicitacao",
            "change_solicitacao",
            # Aprovações
            "view_aprovacao",
            "add_aprovacao",
            # Auditoria
            "view_logauditoria",
        ],
        "coordenador": [
            # Solicitações (limitado às próprias na view)
            "add_solicitacao",
            "view_solicitacao",
        ],
        "formador": [
            # Disponibilidade (limitado às próprias na view)
            "add_disponibilidadeformadores",
            "change_disponibilidadeformadores",
            # Solicitações (apenas eventos em que participa)
            "view_solicitacao",
        ],
        "controle": [
            # Visualização para monitoramento
            "view_solicitacao",
            "view_aprovacao",
            # Sincronização do calendário (permissão customizada)
            "sync_calendar",
        ],
        "diretoria": [
            # Relatórios executivos (permissão customizada)
            "view_relatorios",
            # Visualização estratégica
            "view_solicitacao",
            "view_disponibilidadeformadores",
        ],
        "admin": [
            # Admin já tem is_superuser, mas incluímos algumas para consistência
            "view_solicitacao",
            "add_solicitacao",
            "change_solicitacao",
            "delete_solicitacao",
            "sync_calendar",
            "view_relatorios",
        ],
    }

    # Criar grupos e associar permissões
    for group_name, permission_codenames in groups_permissions.items():
        group, created = Group.objects.get_or_create(name=group_name)

        if created:
            print(f"✅ Grupo '{group_name}' criado")
        else:
            print(f"📝 Grupo '{group_name}' já existe, atualizando permissões")

        # Limpar permissões existentes
        group.permissions.clear()

        # Adicionar permissões
        permissions_added = 0
        for perm_codename in permission_codenames:
            if perm_codename in ["sync_calendar", "view_relatorios"]:
                # Permissões customizadas
                if perm_codename == "sync_calendar":
                    group.permissions.add(sync_calendar_perm)
                    permissions_added += 1
                elif perm_codename == "view_relatorios":
                    group.permissions.add(view_relatorios_perm)
                    permissions_added += 1
            else:
                # Permissões padrão do Django
                try:
                    permission = Permission.objects.get(codename=perm_codename)
                    group.permissions.add(permission)
                    permissions_added += 1
                except Permission.DoesNotExist:
                    print(f"   ⚠️  Permissão '{perm_codename}' não encontrada")
                except Exception as e:
                    print(f"   ❌ Erro ao processar permissão '{perm_codename}': {e}")

        print(f"   → {permissions_added} permissões associadas ao grupo '{group_name}'")

    print("\n=== SINCRONIZANDO USUÁRIOS EXISTENTES ===\n")

    # Sincronizar usuários existentes
    from core.models import Usuario

    papel_to_group = {
        "admin": "admin",
        "superintendencia": "superintendencia",
        "coordenador": "coordenador",
        "formador": "formador",
        "controle": "controle",
        "diretoria": "diretoria",
    }

    users_synced = 0

    for user in Usuario.objects.all():
        if user.papel and user.papel in papel_to_group:
            group_name = papel_to_group[user.papel]
            try:
                group = Group.objects.get(name=group_name)
                # Limpar grupos de papel existentes
                for existing_group in Group.objects.filter(
                    name__in=papel_to_group.values()
                ):
                    user.groups.remove(existing_group)
                # Adicionar ao grupo correto
                user.groups.add(group)
                users_synced += 1
                print(f"✅ Usuário '{user.username}' → grupo '{group_name}'")
            except Group.DoesNotExist:
                print(
                    f"❌ Grupo '{group_name}' não encontrado para usuário '{user.username}'"
                )
        else:
            print(
                f"⚠️  Usuário '{user.username}' sem papel definido ou papel inválido: '{user.papel}'"
            )

    print(f"\n=== RESUMO ===")
    print(f"✅ {len(groups_permissions)} grupos criados/atualizados")
    print(f"✅ 2 permissões customizadas criadas")
    print(f"✅ {users_synced} usuários sincronizados")

    # Verificação final
    print(f"\n=== VERIFICAÇÃO FINAL ===")
    for group_name in groups_permissions.keys():
        group = Group.objects.get(name=group_name)
        user_count = group.user_set.count()
        perm_count = group.permissions.count()
        print(
            f"📊 Grupo '{group_name}': {user_count} usuários, {perm_count} permissões"
        )


if __name__ == "__main__":
    try:
        create_groups_and_permissions()
        print("\n🎉 Script executado com sucesso!")
    except Exception as e:
        print(f"\n❌ Erro durante execução: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
