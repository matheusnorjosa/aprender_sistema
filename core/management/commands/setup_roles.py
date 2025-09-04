# aprender_sistema/core/management/commands/setup_roles.py
from django.contrib.auth.models import ContentType, Group, Permission
from django.core.management.base import BaseCommand

from core import models

ROLES = [
    "Coordenador",
    "Superintendência",
    "Controle",
    "Diretoria",
    "Admin do Sistema",
    "Formador",
]


class Command(BaseCommand):
    help = "Cria grupos/papéis padrão e associa permissões básicas."

    def handle(self, *args, **options):
        groups = {name: Group.objects.get_or_create(name=name)[0] for name in ROLES}

        perms_by_group = {
            "Coordenador": [
                (models.Solicitacao, ["add", "view"]),
            ],
            "Superintendência": [
                (models.Solicitacao, ["view", "change"]),
                (models.Aprovacao, ["add", "view"]),
            ],
            "Controle": [
                (models.Solicitacao, ["view"]),
                (models.EventoGoogleCalendar, ["add", "view", "change"]),
            ],
            "Diretoria": [
                (models.Solicitacao, ["view"]),
            ],
            "Admin do Sistema": [
                (models.Projeto, ["add", "view", "change", "delete"]),
                (models.Municipio, ["add", "view", "change", "delete"]),
                (models.TipoEvento, ["add", "view", "change", "delete"]),
                (models.Formador, ["add", "view", "change", "delete"]),
                (models.Solicitacao, ["add", "view", "change", "delete"]),
                (models.Aprovacao, ["add", "view", "change", "delete"]),
                (models.EventoGoogleCalendar, ["add", "view", "change", "delete"]),
                (models.DisponibilidadeFormadores, ["add", "view", "change", "delete"]),
                (models.LogAuditoria, ["add", "view", "change", "delete"]),
            ],
            "Formador": [
                (models.Solicitacao, ["view"]),
            ],
        }

        def grant(model, actions, group):
            ct = ContentType.objects.get_for_model(model)
            for act in actions:
                codename = f"{act}_{model._meta.model_name}"
                try:
                    perm = Permission.objects.get(content_type=ct, codename=codename)
                    group.permissions.add(perm)
                except Permission.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f"Permissão não achada: {codename}")
                    )

        for gname, items in perms_by_group.items():
            g = groups[gname]
            for model, actions in items:
                grant(model, actions, g)

        self.stdout.write(
            self.style.SUCCESS("Grupos/perfis criados e permissões básicas atribuídas.")
        )
