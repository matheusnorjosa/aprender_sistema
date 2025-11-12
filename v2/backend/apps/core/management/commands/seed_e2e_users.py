"""
Management command: seed_e2e_users

Cria usuários e dados mínimos para testes E2E (Playwright).
Comando idempotente: roda várias vezes sem duplicar dados.

Uso:
    # Docker (recomendado)
    docker compose exec -T web python manage.py seed_e2e_users

    # Local
    python manage.py seed_e2e_users

Dados criados:
    - 4 usuários (coord, super, controle, formador) + grupos
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false
    - 1 município (Salvador, BA)
    - 1 projeto (TESTE E2E, fluxo SUPER)
    - Logs de criação

Fase 2 - Testes E2E (Playwright) - Plano DAT/GCal 2025-10-29
"""
from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import Municipio, Projeto

User = get_user_model()


class Command(BaseCommand):
    help = "Cria usuários e dados mínimos para testes E2E (Playwright)"

    def handle(self, *args: Any, **options: Any) -> None:
        self.stdout.write("=" * 80)
        self.stdout.write("SEED E2E USERS — Testes Playwright")
        self.stdout.write("=" * 80)

        with transaction.atomic():
            # 1. Criar grupos
            self.stdout.write("\n1. Criando grupos necessários...")
            grupos = {}
            for nome_grupo in ["Coordenador", "Superintendência", "Controle"]:
                grupo, created = Group.objects.get_or_create(name=nome_grupo)
                grupos[nome_grupo] = grupo
                status = "✅ Criado" if created else "⏭️  Já existe"
                self.stdout.write(f"   {status}: {nome_grupo}")

            # 2. Criar usuários
            self.stdout.write("\n2. Criando usuários de teste...")
            usuarios = self._create_users(grupos)

            # 3. Criar município
            self.stdout.write("\n3. Criando município de teste...")
            municipio = self._create_municipio()

            # 4. Criar projeto
            self.stdout.write("\n4. Criando projeto de teste...")
            projeto = self._create_projeto(municipio)

            # 5. Resumo
            self.stdout.write("\n" + "=" * 80)
            self.stdout.write("✅ SEED E2E concluído com sucesso!")
            self.stdout.write("\n📋 Resumo:")
            self.stdout.write(f"   Usuários criados: {len(usuarios)}")
            self.stdout.write(f"   Município: {municipio.nome} ({municipio.uf})")
            self.stdout.write(f"   Projeto: {projeto.nome} (fluxo: {projeto.fluxo})")
            self.stdout.write("\n🔑 Credenciais (todas com senha: testpass123):")
            for usuario in usuarios:
                grupos_str = ", ".join([g.name for g in usuario.groups.all()])
                flags = []
                if usuario.is_superuser:
                    flags.append("is_superuser")
                flags_str = f" [{', '.join(flags)}]" if flags else ""
                self.stdout.write(f"   - {usuario.username} (grupos: {grupos_str}){flags_str}")
            self.stdout.write("=" * 80)

    def _create_users(self, grupos: dict[str, Group]) -> list[Any]:
        """Cria 4 usuários para testes E2E."""
        users_data = [
            {
                "username": "coord_e2e@test.com",
                "email": "coord_e2e@test.com",
                "first_name": "Coordenador",
                "last_name": "E2E",
                "cpf": "00000000001",  # Placeholder CPF
                "password": "testpass123",
                "groups": [grupos["Coordenador"]],
                "is_superuser": False,
            },
            {
                "username": "super_e2e@test.com",
                "email": "super_e2e@test.com",
                "first_name": "Superintendência",
                "last_name": "E2E",
                "cpf": "00000000002",
                "password": "testpass123",
                "groups": [grupos["Superintendência"]],
                "is_superuser": False,
            },
            {
                "username": "controle_e2e@test.com",
                "email": "controle_e2e@test.com",
                "first_name": "Controle",
                "last_name": "E2E",
                "cpf": "00000000003",
                "password": "testpass123",
                "groups": [grupos["Controle"]],
                "is_superuser": False,
            },
            {
                "username": "formador_e2e@test.com",
                "email": "formador_e2e@test.com",
                "first_name": "Formador",
                "last_name": "E2E",
                "cpf": "00000000004",
                "password": "testpass123",
                "groups": [],  # Formador não precisa de grupo específico
                "is_superuser": False,
            },
        ]

        usuarios_criados = []
        for user_data in users_data:
            user, created = User.objects.get_or_create(
                username=user_data["username"],
                defaults={
                    "email": user_data["email"],
                    "first_name": user_data["first_name"],
                    "last_name": user_data["last_name"],
                    "cpf": user_data["cpf"],
                    "is_superuser": user_data["is_superuser"],
                },
            )

            if created:
                user.set_password(user_data["password"])
                user.save()
                status = "✅ Criado"
            else:
                status = "⏭️  Já existe"

            # Adicionar grupos (sem duplicar)
            for grupo in user_data["groups"]:
                user.groups.add(grupo)

            self.stdout.write(f"   {status}: {user.username}")
            usuarios_criados.append(user)

        return usuarios_criados

    def _create_municipio(self) -> Municipio:
        """Cria município para testes E2E."""
        municipio, created = Municipio.objects.get_or_create(
            ibge_code="2927408",  # Salvador
            defaults={
                "nome": "Salvador",
                "uf": "BA",
                "ativo": True,
            },
        )

        status = "✅ Criado" if created else "⏭️  Já existe"
        self.stdout.write(f"   {status}: {municipio.nome} ({municipio.uf})")
        return municipio

    def _create_projeto(self, municipio: Municipio) -> Projeto:
        """Cria projeto para testes E2E."""
        projeto, created = Projeto.objects.get_or_create(
            codigo="E2E",
            defaults={
                "nome": "TESTE E2E",
                "fluxo": "SUPER",  # Exige aprovação manual (Superintendência)
                "ativo": True,
            },
        )

        status = "✅ Criado" if created else "⏭️  Já existe"
        self.stdout.write(f"   {status}: {projeto.nome} (fluxo: {projeto.fluxo})")
        return projeto
