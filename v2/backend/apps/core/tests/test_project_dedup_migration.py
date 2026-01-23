"""
Testes para data migration 0036_consolidate_duplicate_projetos.py.

Valida:
- Migration consolida todos os 3 pares duplicados
- Todas as FK references são atualizadas corretamente
- Projetos duplicados são deletados
- Projetos canônicos permanecem com dados corretos
- Safe handling quando duplicados não existem

Issue: #150
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

import importlib
from datetime import datetime
from zoneinfo import ZoneInfo

from django.apps import apps
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

import pytest

from apps.core.models import Municipio, Projeto, Solicitacao, TipoEvento, Usuario

# Import migration function dynamically (module name starts with number)
migration_module = importlib.import_module("apps.core.migrations.0036_consolidate_duplicate_projetos")
consolidate_projetos = migration_module.consolidate_projetos


@pytest.mark.django_db(transaction=True)
class TestProjectDedupMigration:
    """Testes para migration 0036_consolidate_duplicate_projetos."""

    @pytest.fixture
    def migration_executor(self):
        """Retorna executor de migrations para testes."""
        return MigrationExecutor(connection)

    @pytest.fixture
    def setup_duplicate_projects(self, db):
        """
        Cria dados de teste com projetos duplicados e relacionamentos.

        Estrutura:
        - 3 pares de projetos duplicados (canônico + duplicado)
        - Solicitações apontando para duplicados
        - Municipio e Usuario para Solicitacao
        """
        # Limpar projetos existentes (de testes anteriores)
        Projeto.objects.all().delete()

        # Criar dados auxiliares
        municipio = Municipio.objects.create(
            nome="Município Teste",
            uf="CE",
            ativo=True,
        )

        usuario = Usuario.objects.create(
            username="user_test",
            cpf="12345678901",
            email="test@aprender.local",
        )

        tipo_evento = TipoEvento.objects.create(
            nome="Evento Teste",
        )

        # Par 1: LEIO ESCREVO E CALCULO (duplicado) vs LEIO, ESCREVO E CALCULO (canônico)
        leio_canonical = Projeto.objects.create(
            nome="LEIO, ESCREVO E CALCULO",
            fluxo="NAO_SUPER",
            ativo=True,
        )
        leio_duplicate = Projeto.objects.create(
            nome="LEIO ESCREVO E CALCULO",
            fluxo="NAO_SUPER",
            ativo=True,
        )

        # Timestamps para solicitações
        tz = ZoneInfo("America/Fortaleza")
        inicio = datetime(2025, 1, 15, 14, 0, tzinfo=tz)
        fim = datetime(2025, 1, 15, 17, 0, tzinfo=tz)

        # Criar solicitações apontando para duplicado
        sol_leio_1 = Solicitacao.objects.create(
            usuario=usuario,
            projeto=leio_duplicate,  # FK para duplicado
            municipio=municipio,
            tipo_evento=tipo_evento,
            status="pendente",
            inicio=inicio,
            fim=fim,
        )
        sol_leio_2 = Solicitacao.objects.create(
            usuario=usuario,
            projeto=leio_duplicate,  # FK para duplicado
            municipio=municipio,
            tipo_evento=tipo_evento,
            status="aprovado",
            inicio=inicio,
            fim=fim,
        )

        # Par 2: Gestão Escolar (duplicado) vs GESTÃO ESCOLAR (canônico)
        gestao_canonical = Projeto.objects.create(
            nome="GESTÃO ESCOLAR",
            fluxo="NAO_SUPER",
            ativo=True,
        )
        gestao_duplicate = Projeto.objects.create(
            nome="Gestão Escolar",
            fluxo="NAO_SUPER",
            ativo=True,
        )

        sol_gestao = Solicitacao.objects.create(
            usuario=usuario,
            projeto=gestao_duplicate,  # FK para duplicado
            municipio=municipio,
            tipo_evento=tipo_evento,
            status="pendente",
            inicio=inicio,
            fim=fim,
        )

        # Par 3: LER OUVIR E CONTAR (duplicado) vs LER, OUVIR E CONTAR (canônico)
        ler_canonical = Projeto.objects.create(
            nome="LER, OUVIR E CONTAR",
            fluxo="NAO_SUPER",
            ativo=True,
        )
        ler_duplicate = Projeto.objects.create(
            nome="LER OUVIR E CONTAR",
            fluxo="NAO_SUPER",
            ativo=True,
        )

        sol_ler = Solicitacao.objects.create(
            usuario=usuario,
            projeto=ler_duplicate,  # FK para duplicado
            municipio=municipio,
            tipo_evento=tipo_evento,
            status="pendente",
            inicio=inicio,
            fim=fim,
        )

        return {
            "municipio": municipio,
            "usuario": usuario,
            "tipo_evento": tipo_evento,
            # Pares canônico/duplicado
            "leio_canonical": leio_canonical,
            "leio_duplicate": leio_duplicate,
            "gestao_canonical": gestao_canonical,
            "gestao_duplicate": gestao_duplicate,
            "ler_canonical": ler_canonical,
            "ler_duplicate": ler_duplicate,
            # Solicitações
            "sol_leio_1": sol_leio_1,
            "sol_leio_2": sol_leio_2,
            "sol_gestao": sol_gestao,
            "sol_ler": sol_ler,
        }

    def test_migration_consolidates_leio_pair(self, setup_duplicate_projects):
        """
        Migration deve consolidar par 'LEIO ESCREVO E CALCULO' → 'LEIO, ESCREVO E CALCULO'.
        """
        data = setup_duplicate_projects

        # Executar migration manualmente (simular comportamento)
        consolidate_projetos(apps, None)

        # Verificar que duplicado foi deletado
        assert not Projeto.objects.filter(nome="LEIO ESCREVO E CALCULO").exists()

        # Verificar que canônico existe
        canonical = Projeto.objects.get(nome="LEIO, ESCREVO E CALCULO")
        assert canonical.fluxo == "NAO_SUPER"
        assert canonical.ativo is True

        # Verificar que todas as FKs foram atualizadas
        sol_leio_1 = Solicitacao.objects.get(id=data["sol_leio_1"].id)
        sol_leio_2 = Solicitacao.objects.get(id=data["sol_leio_2"].id)

        assert sol_leio_1.projeto.nome == "LEIO, ESCREVO E CALCULO"
        assert sol_leio_2.projeto.nome == "LEIO, ESCREVO E CALCULO"

    def test_migration_consolidates_gestao_pair(self, setup_duplicate_projects):
        """
        Migration deve consolidar par 'Gestão Escolar' → 'GESTÃO ESCOLAR'.
        """
        data = setup_duplicate_projects

        # Executar migration
        consolidate_projetos(apps, None)

        # Verificar que duplicado foi deletado
        assert not Projeto.objects.filter(nome="Gestão Escolar").exists()

        # Verificar que canônico existe
        canonical = Projeto.objects.get(nome="GESTÃO ESCOLAR")
        assert canonical.fluxo == "NAO_SUPER"

        # Verificar FK atualizada
        sol_gestao = Solicitacao.objects.get(id=data["sol_gestao"].id)
        assert sol_gestao.projeto.nome == "GESTÃO ESCOLAR"

    def test_migration_consolidates_ler_pair(self, setup_duplicate_projects):
        """
        Migration deve consolidar par 'LER OUVIR E CONTAR' → 'LER, OUVIR E CONTAR'.
        """
        data = setup_duplicate_projects

        # Executar migration
        consolidate_projetos(apps, None)

        # Verificar que duplicado foi deletado
        assert not Projeto.objects.filter(nome="LER OUVIR E CONTAR").exists()

        # Verificar que canônico existe
        canonical = Projeto.objects.get(nome="LER, OUVIR E CONTAR")
        assert canonical.fluxo == "NAO_SUPER"

        # Verificar FK atualizada
        sol_ler = Solicitacao.objects.get(id=data["sol_ler"].id)
        assert sol_ler.projeto.nome == "LER, OUVIR E CONTAR"

    def test_migration_updates_all_solicitacao_fks(self, setup_duplicate_projects):
        """
        Migration deve atualizar TODAS as Solicitacoes apontando para duplicados.
        """
        data = setup_duplicate_projects

        # Antes da migration: contar solicitações por projeto duplicado
        leio_dup_count_before = Solicitacao.objects.filter(projeto__nome="LEIO ESCREVO E CALCULO").count()
        assert leio_dup_count_before == 2  # sol_leio_1 + sol_leio_2

        # Executar migration
        consolidate_projetos(apps, None)

        # Após migration: todas devem apontar para canônico
        leio_dup_count_after = Solicitacao.objects.filter(projeto__nome="LEIO ESCREVO E CALCULO").count()
        assert leio_dup_count_after == 0  # Nenhuma solicitação aponta para duplicado

        leio_canonical_count = Solicitacao.objects.filter(projeto__nome="LEIO, ESCREVO E CALCULO").count()
        assert leio_canonical_count == 2  # Ambas migraram para canônico

    def test_migration_deletes_all_duplicates(self, setup_duplicate_projects):
        """
        Migration deve deletar TODOS os 3 projetos duplicados.
        """
        data = setup_duplicate_projects

        # Antes: 6 projetos (3 canônicos + 3 duplicados)
        assert Projeto.objects.count() == 6

        # Executar migration
        consolidate_projetos(apps, None)

        # Após: 3 projetos (apenas canônicos)
        assert Projeto.objects.count() == 3

        # Verificar que apenas canônicos existem
        canonical_names = [
            "LEIO, ESCREVO E CALCULO",
            "GESTÃO ESCOLAR",
            "LER, OUVIR E CONTAR",
        ]
        for name in canonical_names:
            assert Projeto.objects.filter(nome=name).exists()

        # Verificar que duplicados não existem
        duplicate_names = [
            "LEIO ESCREVO E CALCULO",
            "Gestão Escolar",
            "LER OUVIR E CONTAR",
        ]
        for name in duplicate_names:
            assert not Projeto.objects.filter(nome=name).exists()

    def test_migration_preserves_canonical_if_exists(self):
        """
        Migration deve preservar projeto canônico se já existir.
        """
        # Criar apenas projeto canônico (sem duplicado)
        canonical = Projeto.objects.create(
            nome="LEIO, ESCREVO E CALCULO",
            fluxo="NAO_SUPER",
            ativo=True,
        )
        canonical_id = canonical.id

        # Executar migration (não há duplicado para mesclar)
        consolidate_projetos(apps, None)

        # Verificar que canônico ainda existe com mesmo ID
        canonical_after = Projeto.objects.get(nome="LEIO, ESCREVO E CALCULO")
        assert canonical_after.id == canonical_id
        assert canonical_after.fluxo == "NAO_SUPER"

    def test_migration_handles_missing_duplicate_gracefully(self):
        """
        Migration deve continuar mesmo se duplicado não existir.
        """
        # Criar apenas canônico (sem duplicado)
        Projeto.objects.create(
            nome="GESTÃO ESCOLAR",
            fluxo="NAO_SUPER",
            ativo=True,
        )

        # Executar migration (não deve crashar)

        # Não deve lançar exceção
        try:
            consolidate_projetos(apps, None)
        except Exception as e:
            pytest.fail(f"Migration deve lidar com duplicado ausente sem crash: {e}")

        # Verificar que canônico ainda existe
        assert Projeto.objects.filter(nome="GESTÃO ESCOLAR").exists()

    def test_migration_creates_canonical_if_missing(self):
        """
        Migration deve criar projeto canônico se não existir.
        """
        # Criar apenas duplicado (sem canônico)
        Projeto.objects.create(
            nome="LEIO ESCREVO E CALCULO",
            fluxo="NAO_SUPER",
            ativo=True,
        )

        # Executar migration
        consolidate_projetos(apps, None)

        # Verificar que canônico foi criado
        assert Projeto.objects.filter(nome="LEIO, ESCREVO E CALCULO").exists()

        # Verificar que duplicado foi deletado
        assert not Projeto.objects.filter(nome="LEIO ESCREVO E CALCULO").exists()

    def test_migration_is_idempotent(self, setup_duplicate_projects):
        """
        Migration deve ser idempotente (rodar 2x não quebra).
        """
        data = setup_duplicate_projects

        # Executar migration primeira vez
        consolidate_projetos(apps, None)

        # Contar projetos após primeira execução
        count_after_first = Projeto.objects.count()
        canonical_names = list(Projeto.objects.values_list("nome", flat=True))

        # Executar migration segunda vez (não deve quebrar)
        consolidate_projetos(apps, None)

        # Contar projetos após segunda execução
        count_after_second = Projeto.objects.count()
        canonical_names_second = list(Projeto.objects.values_list("nome", flat=True))

        # Deve ser idêntico
        assert count_after_first == count_after_second
        assert sorted(canonical_names) == sorted(canonical_names_second)


@pytest.mark.django_db
class TestMigrationEdgeCases:
    """Testes para casos extremos da migration."""

    def test_migration_handles_empty_database(self):
        """
        Migration deve rodar sem erros em banco vazio (não cria canônicos sem duplicados).
        """
        # Garantir que não há projetos
        Projeto.objects.all().delete()

        # Executar migration (não deve crashar)
        try:
            consolidate_projetos(apps, None)
        except Exception as e:
            pytest.fail(f"Migration deve lidar com banco vazio sem crash: {e}")

        # Verificar que NENHUM canônico foi criado (não havia duplicados)
        assert not Projeto.objects.filter(nome="LEIO, ESCREVO E CALCULO").exists()
        assert not Projeto.objects.filter(nome="GESTÃO ESCOLAR").exists()
        assert not Projeto.objects.filter(nome="LER, OUVIR E CONTAR").exists()
        assert Projeto.objects.count() == 0

    def test_migration_preserves_other_projects(self):
        """
        Migration não deve afetar projetos que não são duplicados.
        """
        # Criar projeto não relacionado
        other_project = Projeto.objects.create(
            nome="OUTRO PROJETO",
            fluxo="SUPER",
            ativo=True,
        )
        other_id = other_project.id

        # Executar migration
        consolidate_projetos(apps, None)

        # Verificar que projeto não-relacionado permanece intacto
        other_after = Projeto.objects.get(id=other_id)
        assert other_after.nome == "OUTRO PROJETO"
        assert other_after.fluxo == "SUPER"
        assert other_after.ativo is True
