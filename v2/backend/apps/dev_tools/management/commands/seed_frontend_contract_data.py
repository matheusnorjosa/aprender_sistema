"""
Management command: seed_frontend_contract_data

Seed deterministico para testes de contrato funcional frontend-backend
(matriz critica usada no checklist Playwright).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from django.contrib.auth.models import Group
from django.core.management import BaseCommand, call_command

from apps.core.models import Compra, DATCompra, Municipio, PermissaoFuncional, Projeto, Solicitacao, Usuario


class Command(BaseCommand):
    help = "Cria dados deterministicos para a matriz funcional critica do frontend"

    def handle(self, *args: Any, **options: Any) -> None:
        self.stdout.write("=" * 80)
        self.stdout.write("SEED FRONTEND CONTRACT DATA")
        self.stdout.write("=" * 80)

        # Reusa seed de usuarios/projeto base de E2E.
        call_command("seed_e2e_users")

        dat_group, _ = Group.objects.get_or_create(name="DAT")
        dashboard_perm = PermissaoFuncional.objects.filter(codename="pode_acessar_dashboard_compras").first()
        if dashboard_perm is not None:
            dashboard_perm.groups.add(dat_group)

        dat_user, created = Usuario.objects.update_or_create(
            username="dat_matrix@test.com",
            defaults={
                "email": "dat_matrix@test.com",
                "first_name": "DAT",
                "last_name": "Matrix",
                "cpf": "00000000005",
                "is_superuser": False,
            },
        )
        if created or not dat_user.check_password("testpass123"):
            dat_user.set_password("testpass123")
            dat_user.save(update_fields=["password"])
        dat_user.groups.set([dat_group])

        projeto, _ = Projeto.objects.get_or_create(
            codigo="E2E",
            defaults={"nome": "TESTE E2E", "fluxo": "SUPER", "ativo": True},
        )

        municipio, _ = Municipio.objects.get_or_create(
            nome="Matrizopolis",
            uf="BA",
            defaults={"ativo": True},
        )
        if not municipio.ativo:
            municipio.ativo = True
            municipio.save(update_fields=["ativo"])

        # Garante que esse par municipio+projeto fique pendente no dashboard
        # (sem solicitacao ativa).
        Solicitacao.objects.filter(
            municipio=municipio,
            projeto=projeto,
            status__in=["pendente", "aprovado"],
        ).delete()

        Compra.objects.update_or_create(
            external_hash="9" * 64,
            defaults={
                "codigo": "MATRIX-PEND-001",
                "projeto": projeto,
                "municipio": municipio,
                "quantidade": 15,
                "data": date(2026, 3, 3),
                "uso": "Matriz funcional frontend",
            },
        )

        DATCompra.objects.update_or_create(
            municipio=municipio,
            projeto=projeto,
            descricao_produto="KIT MATRIX CONTRACT",
            ano_uso=2026,
            defaults={
                "quantidade": 77,
                "quantidade_utilizada": 0,
                "valor_unitario": Decimal("19.90"),
                "created_by": dat_user,
                "updated_by": dat_user,
                "ativo": True,
            },
        )

        self.stdout.write(self.style.SUCCESS("✅ Seed funcional da matriz concluido"))
        self.stdout.write("Usuarios:")
        self.stdout.write("  - controle_e2e@test.com / testpass123 (Controle)")
        self.stdout.write("  - dat_matrix@test.com / testpass123 (DAT)")
        self.stdout.write("Dados-chave:")
        self.stdout.write("  - core_compra codigo=MATRIX-PEND-001 municipio=Matrizopolis projeto=TESTE E2E")
        self.stdout.write("  - core_dat_compra descricao=KIT MATRIX CONTRACT municipio=Matrizopolis projeto=TESTE E2E")
