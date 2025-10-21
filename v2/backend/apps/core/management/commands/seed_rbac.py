"""
Seed RBAC — Criar grupos e permissões mínimas (idempotente).

Grupos criados:
- Superintendência
- Coordenador
- Formador
- Controle
- DAT
- Gerência

Permissões atribuídas por grupo para modelo Solicitacao.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from apps.core.models import Solicitacao

GROUPS = [
    "Superintendência",
    "Coordenador",
    "Formador",
    "Controle",
    "DAT",
    "Gerência",
]

PERMS_BY_GROUP = {
    "Controle": [("view", Solicitacao), ("change", Solicitacao)],
    "Superintendência": [("view", Solicitacao), ("change", Solicitacao)],
    "Coordenador": [("view", Solicitacao), ("add", Solicitacao)],
    "Formador": [("view", Solicitacao)],
    "DAT": [("view", Solicitacao)],
    "Gerência": [("view", Solicitacao)],
}


def perm_codename(action: str, model) -> str:
    """Gera codename de permissão: <action>_<model_name>."""
    return f"{action}_{model._meta.model_name}"


class Command(BaseCommand):
    """Command para criar/atualizar grupos e permissões (idempotente)."""

    help = "Cria/atualiza grupos e permissões mínimas (idempotente)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Exibir detalhes da operação",
        )

    def handle(self, *args, **opts):
        verbose = opts.get("verbose", False)

        # Criar grupos
        for name in GROUPS:
            group, created = Group.objects.get_or_create(name=name)
            if verbose and created:
                self.stdout.write(f"  ✅ Grupo criado: {name}")
            elif verbose:
                self.stdout.write(f"  ✓  Grupo existente: {name}")

        # Atribuir permissões
        for group_name, items in PERMS_BY_GROUP.items():
            g = Group.objects.get(name=group_name)
            for action, model in items:
                ct = ContentType.objects.get_for_model(model)
                code = perm_codename(action, model)
                try:
                    p = Permission.objects.get(content_type=ct, codename=code)
                    g.permissions.add(p)
                    if verbose:
                        self.stdout.write(
                            f"  ✅ Permissão atribuída: {group_name} → {code}"
                        )
                except Permission.DoesNotExist:
                    # Silencioso: permissão não existe (pode ser normal)
                    if verbose:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  ⚠️  Permissão não encontrada: {code}"
                            )
                        )

        self.stdout.write(self.style.SUCCESS("RBAC seeds aplicados (idempotente)."))
