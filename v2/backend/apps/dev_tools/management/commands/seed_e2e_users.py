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
    - 1 município (Salvador, BA)
    - 1 projeto (TESTE E2E, fluxo SUPER)
    - Logs de criação

Fase 2 - Testes E2E (Playwright) - Plano DAT/GCal 2025-10-29
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportGeneralTypeIssues=false
from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import IntegrityError, transaction

from apps.core.constants import FUNCAO_GROUPS, SETOR_GROUPS
from apps.core.models import Compra, EquipeGerencia, Gerencia, Municipio, Projeto, TipoEvento

User = get_user_model()


class Command(BaseCommand):
    help = "Cria usuários e dados mínimos para testes E2E (Playwright)"

    def handle(self, *args: Any, **options: Any) -> None:
        self.stdout.write("=" * 80)
        self.stdout.write("SEED E2E USERS — Testes Playwright")
        self.stdout.write("=" * 80)

        # 1. Criar grupos (união de SETOR_GROUPS + FUNCAO_GROUPS — SSOT em apps.core.constants)
        self.stdout.write("\n1. Criando grupos necessários...")
        grupos: dict[str, Group] = {}
        todos_grupos = list({*SETOR_GROUPS, *FUNCAO_GROUPS})
        for nome_grupo in todos_grupos:
            grupo, created = Group.objects.get_or_create(name=nome_grupo)
            grupos[nome_grupo] = grupo
            status = "✅ Criado" if created else "⏭️  Já existe"
            self.stdout.write(f"   {status}: {nome_grupo}")

        # 1b. Vincular permissions funcionais aos grupos (testes E2E exigem
        # que Coordenador tenha `pode_criar_solicitacao_coord_dat`, etc.).
        # Em prod o seed_rbac roda com assign_default_groups=False — aqui
        # forçamos True porque o ambiente E2E precisa do vínculo padrão.
        from apps.core.services.functional_permissions_seed import seed_functional_permissions

        fp_stats = seed_functional_permissions(assign_default_groups=True, verbose=False)
        self.stdout.write(f"   ✅ Permissions funcionais vinculadas (updated={fp_stats['permissions_updated']})")

        # 2. Criar usuários
        self.stdout.write("\n2. Criando usuários de teste...")
        usuarios = self._create_users(grupos)

        # 3. Criar municípios (Salvador + Fortaleza para testes de deslocamento RD-04)
        self.stdout.write("\n3. Criando municípios de teste...")
        municipio_salvador = self._upsert_municipio(nome="Salvador", uf="BA", ibge_code="2927408")
        municipio_fortaleza = self._upsert_municipio(nome="Fortaleza", uf="CE", ibge_code="2304400")
        municipio = municipio_salvador  # compat com resumo abaixo

        # 4. Criar projetos (SUPER e NAO_SUPER para cobrir ambos os fluxos em E2E)
        self.stdout.write("\n4. Criando projetos de teste...")
        projeto_super = self._upsert_projeto(
            codigo="E2E",
            nome="TESTE E2E",
            fluxo="SUPER",
            gerencia_setor=None,
        )
        projeto_nao_super = self._upsert_projeto(
            codigo="E2E_NS",
            nome="TESTE E2E NAO_SUPER",
            fluxo="NAO_SUPER",
            gerencia_setor="Vidas",
        )

        # 4-pre. TipoEvento (pré-requisito: solicitação obrigatoriamente aponta para
        # um tipo_evento). Em banco virgem do CI, nenhum tipo existe por default.
        self.stdout.write("\n4-pre. Criando tipo de evento E2E...")
        tipo_evento, tipo_created = TipoEvento.objects.update_or_create(
            nome="Formação E2E",
            defaults={"descricao": "Tipo padrão para testes E2E", "cor": "#1890ff"},
        )
        status_te = "✅ Criado" if tipo_created else "⏭️  Já existe"
        self.stdout.write(f"   {status_te}: {tipo_evento.nome}")

        # 4a. EquipeGerencia (vínculos usuário ↔ gerência com papel).
        # Necessário para HasSectorAccess — grade mensal e filtros de setor
        # exigem que o usuário esteja em EquipeGerencia da gerência consultada.
        # Também usado para resolver gerência do usuário em outras views.
        self.stdout.write("\n4a. Criando vínculos EquipeGerencia...")
        vinculos = [
            # (username, nome_setor, papel)
            ("coord_vidas@test.com", "Vidas", "COORDENADOR"),
            ("coord_fluir@test.com", "Fluir", "COORDENADOR"),
            ("coord_acerta@test.com", "ACerta", "COORDENADOR"),
            ("gerente_vidas@test.com", "Vidas", "GERENTE"),
            ("formador_vidas@test.com", "Vidas", "FORMADOR"),
            ("formador_fluir@test.com", "Fluir", "FORMADOR"),
        ]
        by_username = {u.username: u for u in usuarios}
        for username, nome_setor, papel in vinculos:
            user_obj = by_username.get(username)
            if not user_obj:
                self.stdout.write(f"   ⚠️  Usuário {username} não encontrado — vínculo pulado")
                continue
            gerencia = Gerencia.objects.filter(nome_setor=nome_setor, ativo=True).first()
            if not gerencia:
                self.stdout.write(f"   ⚠️  Gerência '{nome_setor}' ausente — vínculo pulado")
                continue
            self._upsert_equipe_gerencia(usuario=user_obj, gerencia=gerencia, papel=papel)

        # 4b. Compras (pré-requisito para criação de solicitação: o serializer
        # exige que exista Compra para o par (municipio, projeto)).
        self.stdout.write("\n4b. Criando compras pré-requisitas...")
        pares_compra = [
            (municipio_salvador, projeto_super, "COMP-E2E-SALV-SUPER"),
            (municipio_salvador, projeto_nao_super, "COMP-E2E-SALV-NS"),
            (municipio_fortaleza, projeto_super, "COMP-E2E-FORT-SUPER"),
            (municipio_fortaleza, projeto_nao_super, "COMP-E2E-FORT-NS"),
        ]
        for muni, proj, codigo in pares_compra:
            self._upsert_compra(codigo=codigo, municipio=muni, projeto=proj)

        # 5. Resumo
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("✅ SEED E2E concluído com sucesso!")
        self.stdout.write("\n📋 Resumo:")
        self.stdout.write(f"   Usuários criados: {len(usuarios)}")
        self.stdout.write(
            f"   Municípios: {municipio_salvador.nome} ({municipio_salvador.uf}), {municipio_fortaleza.nome} ({municipio_fortaleza.uf})"
        )
        self.stdout.write(f"   Projeto SUPER: {projeto_super.nome} (fluxo: {projeto_super.fluxo})")
        self.stdout.write(f"   Projeto NAO_SUPER: {projeto_nao_super.nome} (fluxo: {projeto_nao_super.fluxo})")
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
        """Cria usuários para testes E2E cobrindo combinações setor × função.

        Usuários criados:

        Legacy (back-compat com specs existentes):
        - coord_e2e, super_e2e, controle_e2e, formador_e2e

        Por combinação setor × função (jornadas J01-J19 do plano QA 2026-04-22):
        - coord_vidas, coord_fluir, coord_acerta (Coordenador + setor)
        - gerente_vidas (Gerente + setor — jornada J14, issue #1165)
        - super_geral (Gerente + Superintendência — PA-02 quorum composto)
        - formador_vidas, formador_fluir (Formador + setor — jornadas J06, J11, J13)
        """
        users_data = [
            # === Legacy — manter compat com specs atuais ===
            {
                "username": "coord_e2e@test.com",
                "email": "coord_e2e@test.com",
                "first_name": "Coordenador",
                "last_name": "E2E",
                "cpf": "99900000001",
                "password": "testpass123",
                "groups": [grupos["Coordenador"]],
                "is_superuser": False,
            },
            {
                "username": "super_e2e@test.com",
                "email": "super_e2e@test.com",
                "first_name": "Superintendência",
                "last_name": "E2E",
                "cpf": "99900000002",
                "password": "testpass123",
                "groups": [grupos["Superintendência"], grupos["Gerente"]],
                "is_superuser": False,
            },
            {
                "username": "controle_e2e@test.com",
                "email": "controle_e2e@test.com",
                "first_name": "Controle",
                "last_name": "E2E",
                "cpf": "99900000003",
                "password": "testpass123",
                "groups": [grupos["Controle"]],
                "is_superuser": False,
            },
            {
                "username": "formador_e2e@test.com",
                "email": "formador_e2e@test.com",
                "first_name": "Formador",
                "last_name": "E2E",
                "cpf": "99900000004",
                "password": "testpass123",
                "groups": [grupos["Formador"]],
                "is_superuser": False,
            },
            # === Coordenadores por setor ===
            {
                "username": "coord_vidas@test.com",
                "email": "coord_vidas@test.com",
                "first_name": "Ana",
                "last_name": "Vidas",
                "cpf": "99900000010",
                "password": "testpass123",
                "groups": [grupos["Coordenador"], grupos["Vidas"]],
                "is_superuser": False,
            },
            {
                "username": "coord_fluir@test.com",
                "email": "coord_fluir@test.com",
                "first_name": "Carlos",
                "last_name": "Fluir",
                "cpf": "99900000011",
                "password": "testpass123",
                "groups": [grupos["Coordenador"], grupos["Fluir"]],
                "is_superuser": False,
            },
            {
                "username": "coord_acerta@test.com",
                "email": "coord_acerta@test.com",
                "first_name": "Diana",
                "last_name": "ACerta",
                "cpf": "99900000012",
                "password": "testpass123",
                "groups": [grupos["Coordenador"], grupos["ACerta"]],
                "is_superuser": False,
            },
            # === Gerente por setor (jornada J14 — issue #1165) ===
            {
                "username": "gerente_vidas@test.com",
                "email": "gerente_vidas@test.com",
                "first_name": "Joao",
                "last_name": "GerenteVidas",
                "cpf": "99900000020",
                "password": "testpass123",
                "groups": [grupos["Gerente"], grupos["Vidas"]],
                "is_superuser": False,
            },
            # === DAT puro (jornada J18 — regra PO: DAT acesso total no frontend) ===
            {
                "username": "dat_e2e@test.com",
                "email": "dat_e2e@test.com",
                "first_name": "Daniel",
                "last_name": "DATPuro",
                "cpf": "99900000040",
                "password": "testpass123",
                "groups": [grupos["DAT"]],
                "is_superuser": False,
            },
            # === Gerente + Superintendência (PA-02 quorum composto) ===
            {
                "username": "super_geral@test.com",
                "email": "super_geral@test.com",
                "first_name": "Maria",
                "last_name": "SuperGeral",
                "cpf": "99900000021",
                "password": "testpass123",
                "groups": [grupos["Gerente"], grupos["Superintendência"]],
                "is_superuser": False,
            },
            # === Formadores por setor (jornadas J06, J11, J13) ===
            {
                "username": "formador_vidas@test.com",
                "email": "formador_vidas@test.com",
                "first_name": "Rafael",
                "last_name": "FormadorVidas",
                "cpf": "99900000030",
                "password": "testpass123",
                "groups": [grupos["Formador"], grupos["Vidas"]],
                "is_superuser": False,
            },
            {
                "username": "formador_fluir@test.com",
                "email": "formador_fluir@test.com",
                "first_name": "Luiza",
                "last_name": "FormadorFluir",
                "cpf": "99900000031",
                "password": "testpass123",
                "groups": [grupos["Formador"], grupos["Fluir"]],
                "is_superuser": False,
            },
        ]

        usuarios_criados = []
        for user_data in users_data:
            user, created = User.objects.update_or_create(
                username=user_data["username"],
                defaults={
                    "email": user_data["email"],
                    "first_name": user_data["first_name"],
                    "last_name": user_data["last_name"],
                    "cpf": user_data["cpf"],
                    "is_superuser": user_data["is_superuser"],
                },
            )

            if created or not user.check_password(user_data["password"]):
                user.set_password(user_data["password"])
                user.save(update_fields=["password"])

            status = "✅ Criado" if created else "⏭️  Já existe"

            # Garante estado determinístico dos grupos em reexecução.
            user.groups.set(user_data["groups"])

            self.stdout.write(f"   {status}: {user.username}")
            usuarios_criados.append(user)

        return usuarios_criados

    def _upsert_municipio(self, *, nome: str, uf: str, ibge_code: str) -> Municipio:
        """Upsert idempotente de município para testes E2E.

        Prioriza chave natural (nome+uf) para evitar violar unique constraint
        quando o município já existe sem ibge_code.
        """
        target_nome = nome
        target_uf = uf
        target_ibge_code = ibge_code

        # Prioriza chave natural (nome+uf) para evitar violar unique constraint
        # quando o município já existe sem ibge_code.
        municipio = Municipio.objects.filter(nome=target_nome, uf=target_uf).first()
        if municipio:
            updated_fields = []

            if not municipio.ativo:
                municipio.ativo = True
                updated_fields.append("ativo")

            if not municipio.ibge_code:
                ibge_conflict = Municipio.objects.filter(ibge_code=target_ibge_code).exclude(pk=municipio.pk).exists()
                if ibge_conflict:
                    self.stdout.write(
                        "   ⚠️  Salvador (BA) já existe, mas ibge_code 2927408 está em outro registro. "
                        "Mantendo município atual sem atualizar ibge_code."
                    )
                else:
                    municipio.ibge_code = target_ibge_code
                    updated_fields.append("ibge_code")

            if updated_fields:
                with transaction.atomic():
                    municipio.save(update_fields=updated_fields)

            self.stdout.write(f"   ⏭️  Já existe: {municipio.nome} ({municipio.uf})")
            return municipio

        # Fallback por IBGE (registro já criado em rodada anterior).
        municipio = Municipio.objects.filter(ibge_code=target_ibge_code).first()
        if municipio:
            updated_fields = []

            if not municipio.ativo:
                municipio.ativo = True
                updated_fields.append("ativo")
            if municipio.nome != target_nome:
                municipio.nome = target_nome
                updated_fields.append("nome")
            if municipio.uf != target_uf:
                municipio.uf = target_uf
                updated_fields.append("uf")

            if updated_fields:
                try:
                    with transaction.atomic():
                        municipio.save(update_fields=updated_fields)
                except IntegrityError:
                    municipio = Municipio.objects.get(nome=target_nome, uf=target_uf)

            self.stdout.write(f"   ⏭️  Já existe: {municipio.nome} ({municipio.uf})")
            return municipio

        municipio = Municipio.objects.create(
            nome=target_nome,
            uf=target_uf,
            ibge_code=target_ibge_code,
            ativo=True,
        )
        self.stdout.write(f"   ✅ Criado: {municipio.nome} ({municipio.uf})")
        return municipio

    def _upsert_equipe_gerencia(
        self,
        *,
        usuario: Any,
        gerencia: Gerencia,
        papel: str,
    ) -> EquipeGerencia:
        """Upsert idempotente de EquipeGerencia.

        Unique constraint: (gerencia, usuario, papel) — é possível o mesmo
        usuário ter múltiplos papéis na mesma gerência (raro, mas suportado).
        Aqui cada (usuario, gerencia, papel) vira um registro independente.
        """
        obj, created = EquipeGerencia.objects.update_or_create(
            gerencia=gerencia,
            usuario=usuario,
            papel=papel,
            defaults={"ativo": True},
        )
        status = "✅ Criado" if created else "⏭️  Já existe"
        self.stdout.write(f"   {status}: {usuario.username} → {gerencia.nome_setor} ({papel})")
        return obj

    def _upsert_compra(
        self,
        *,
        codigo: str,
        municipio: Municipio,
        projeto: Projeto,
    ) -> Compra:
        """Upsert idempotente de Compra para testes E2E.

        Serializer de Solicitacao exige que exista Compra para o par
        (municipio, projeto). Este helper garante a pré-condição em dev.
        """
        import hashlib

        external_hash = hashlib.sha256(f"e2e-{codigo}-{municipio.id}-{projeto.id}".encode()).hexdigest()
        compra, created = Compra.objects.update_or_create(
            external_hash=external_hash,
            defaults={
                "codigo": codigo,
                "municipio": municipio,
                "projeto": projeto,
                "quantidade": 1,
                "data": "2026-01-01",
                "uso": "E2E test fixture",
            },
        )
        status = "✅ Criada" if created else "⏭️  Já existe"
        self.stdout.write(f"   {status}: {codigo} ({municipio.nome} × {projeto.codigo})")
        return compra

    def _upsert_projeto(
        self,
        *,
        codigo: str,
        nome: str,
        fluxo: str,
        gerencia_setor: str | None = None,
    ) -> Projeto:
        """Upsert idempotente de projeto para testes E2E.

        Quando `gerencia_setor` é passado, vincula o projeto à primeira
        `Gerencia` com `nome_setor` correspondente. Se a gerência não existir
        (seed dev local incompleto), o projeto é criado sem vínculo.
        """
        gerencia = None
        if gerencia_setor:
            from django.core.management import call_command

            from apps.core.models import Gerencia

            gerencia = Gerencia.objects.filter(nome_setor=gerencia_setor, ativo=True).first()
            if not gerencia:
                # Fallback idempotente: roda seed_gerencias para garantir que a
                # gerência exista. Evita exigir ordem manual dos seeds em dev.
                self.stdout.write(
                    f"   ⚠️  Gerência '{gerencia_setor}' ausente — rodando seed_gerencias automaticamente..."
                )
                call_command("seed_gerencias", verbosity=0)
                gerencia = Gerencia.objects.filter(nome_setor=gerencia_setor, ativo=True).first()

        projeto = Projeto.objects.filter(codigo=codigo).first()
        if not projeto:
            projeto = Projeto.objects.filter(nome=nome).first()

        if projeto:
            updated_fields: list[str] = []
            original_codigo = projeto.codigo

            if projeto.nome != nome:
                projeto.nome = nome
                updated_fields.append("nome")
            if projeto.fluxo != fluxo:
                projeto.fluxo = fluxo
                updated_fields.append("fluxo")
            if not projeto.ativo:
                projeto.ativo = True
                updated_fields.append("ativo")
            if projeto.codigo != codigo:
                projeto.codigo = codigo
                updated_fields.append("codigo")
            if gerencia and projeto.gerencia_id != gerencia.id:
                projeto.gerencia = gerencia
                updated_fields.append("gerencia")

            if updated_fields:
                try:
                    with transaction.atomic():
                        projeto.save(update_fields=updated_fields)
                except IntegrityError:
                    if "codigo" not in updated_fields:
                        raise
                    projeto.codigo = original_codigo
                    retry_fields = [field for field in updated_fields if field != "codigo"]
                    if retry_fields:
                        with transaction.atomic():
                            projeto.save(update_fields=retry_fields)
                    self.stdout.write(
                        f"   ⚠️  Código {codigo} já está em uso por outro projeto. "
                        "Mantendo o código atual do projeto existente."
                    )

            self.stdout.write(f"   ⏭️  Já existe: {projeto.nome} (fluxo: {projeto.fluxo})")
            return projeto

        try:
            with transaction.atomic():
                projeto = Projeto.objects.create(
                    codigo=codigo,
                    nome=nome,
                    fluxo=fluxo,
                    gerencia=gerencia,
                    ativo=True,
                )
        except IntegrityError:
            projeto = Projeto.objects.filter(nome=nome).first() or Projeto.objects.get(codigo=codigo)
            projeto.fluxo = fluxo
            projeto.ativo = True
            if gerencia and projeto.gerencia_id != gerencia.id:
                projeto.gerencia = gerencia
            with transaction.atomic():
                projeto.save(update_fields=["fluxo", "ativo", "gerencia"])
            self.stdout.write(f"   ⏭️  Já existe: {projeto.nome} (fluxo: {projeto.fluxo})")
            return projeto

        self.stdout.write(f"   ✅ Criado: {projeto.nome} (fluxo: {projeto.fluxo})")
        return projeto
