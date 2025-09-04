"""
Script simples para criar grupos via Django shell
Copie e cole este código no Django shell: python manage.py shell
"""

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from core.models import (
    Aprovacao,
    DisponibilidadeFormadores,
    LogAuditoria,
    Solicitacao,
    Usuario,
)

# Criar permissões customizadas
solicitacao_ct = ContentType.objects.get_for_model(Solicitacao)
log_ct = ContentType.objects.get_for_model(LogAuditoria)

sync_calendar_perm, created = Permission.objects.get_or_create(
    codename="sync_calendar",
    name="Can sync with Google Calendar",
    content_type=solicitacao_ct,
)
print(f"Permissão sync_calendar: {'criada' if created else 'já existe'}")

view_relatorios_perm, created = Permission.objects.get_or_create(
    codename="view_relatorios",
    name="Can view consolidated reports",
    content_type=log_ct,
)
print(f"Permissão view_relatorios: {'criada' if created else 'já existe'}")

# Criar grupos
groups_data = {
    "superintendencia": [
        "view_solicitacao",
        "change_solicitacao",
        "view_aprovacao",
        "add_aprovacao",
        "view_logauditoria",
    ],
    "coordenador": ["add_solicitacao", "view_solicitacao"],
    "formador": [
        "add_disponibilidadeformadores",
        "change_disponibilidadeformadores",
        "view_solicitacao",
    ],
    "controle": ["view_solicitacao", "view_aprovacao", "sync_calendar"],
    "diretoria": [
        "view_relatorios",
        "view_solicitacao",
        "view_disponibilidadeformadores",
    ],
    "admin": [
        "view_solicitacao",
        "add_solicitacao",
        "change_solicitacao",
        "sync_calendar",
        "view_relatorios",
    ],
}

for group_name, permission_codes in groups_data.items():
    group, created = Group.objects.get_or_create(name=group_name)
    print(f"Grupo {group_name}: {'criado' if created else 'já existe'}")

    group.permissions.clear()

    for perm_code in permission_codes:
        if perm_code == "sync_calendar":
            group.permissions.add(sync_calendar_perm)
        elif perm_code == "view_relatorios":
            group.permissions.add(view_relatorios_perm)
        else:
            try:
                perm = Permission.objects.get(codename=perm_code)
                group.permissions.add(perm)
            except Permission.DoesNotExist:
                print(f"  AVISO: Permissão {perm_code} não encontrada")

    print(f"  → {group.permissions.count()} permissões adicionadas")

# Sincronizar usuários existentes
papel_to_group = {
    "admin": "admin",
    "superintendencia": "superintendencia",
    "coordenador": "coordenador",
    "formador": "formador",
    "controle": "controle",
    "diretoria": "diretoria",
}

print("\nSincronizando usuários:")
for user in Usuario.objects.all():
    if user.papel and user.papel in papel_to_group:
        group_name = papel_to_group[user.papel]
        group = Group.objects.get(name=group_name)

        # Remove de outros grupos de papel
        for other_group in Group.objects.filter(name__in=papel_to_group.values()):
            user.groups.remove(other_group)

        # Adiciona ao grupo correto
        user.groups.add(group)
        print(f"  {user.username} → {group_name}")

print("\nConcluído! Verifique o admin em http://localhost:8000/admin/auth/group/")
