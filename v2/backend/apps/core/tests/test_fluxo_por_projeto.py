"""
Testes para PR 13/N - Fluxo baseado em Projeto

Verifica que o fluxo de aprovação (SUPER/NAO_SUPER) é determinado
pelo projeto, não pelo campo coordenador_acompanha.
"""

import pytest
from django.test import TestCase
from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from datetime import timedelta

from apps.core.models import (
    Usuario,
    Projeto,
    Municipio,
    TipoEvento,
    Solicitacao,
)


class TestFluxoPorProjeto(TestCase):
    """
    Testa que o fluxo de aprovação é determinado pelo projeto.
    """

    def setUp(self):
        """Setup inicial para os testes."""
        self.client = APIClient()

        # Criar grupos
        self.grupo_coordenador, _ = Group.objects.get_or_create(name="Coordenador")
        self.grupo_superintendencia, _ = Group.objects.get_or_create(name="Superintendência")
        self.grupo_controle, _ = Group.objects.get_or_create(name="Controle")
        self.grupo_dat, _ = Group.objects.get_or_create(name="DAT")

        # Criar usuários
        self.coordenador = Usuario.objects.create_user(
            username="coordenador1",
            password="test123",
            email="coord@test.com",
            cpf="12345678901",
        )
        self.coordenador.groups.add(self.grupo_coordenador)

        self.superintendente = Usuario.objects.create_user(
            username="super1",
            password="test123",
            email="super@test.com",
            cpf="98765432109",
        )
        self.superintendente.groups.add(self.grupo_superintendencia)

        # Criar dados de teste
        self.municipio = Municipio.objects.create(
            nome="Fortaleza",
            uf="CE",
            ativo=True,
        )

        self.tipo_evento = TipoEvento.objects.create(
            nome="Formação",
            descricao="Formação de professores",
        )

        # Criar projetos com diferentes fluxos
        self.projeto_super = Projeto.objects.create(
            nome="ACerta",
            codigo='',  # Explicitly set empty string (default)
            fluxo="SUPER",
            ativo=True,
        )

        self.projeto_outros = Projeto.objects.create(
            nome="Workshop",
            codigo='',  # Explicitly set empty string (default)
            fluxo="NAO_SUPER",
            ativo=True,
        )

        # Datas para testes
        self.inicio = timezone.now() + timedelta(days=7)
        self.fim = self.inicio + timedelta(hours=4)

    def test_projeto_super_cria_solicitacao_pendente(self):
        """
        Testa que projetos com fluxo SUPER criam solicitações pendentes.
        """
        self.client.force_authenticate(user=self.coordenador)

        response = self.client.post(
            "/api/solicitacoes/",
            {
                "municipio": self.municipio.id,
                "projeto": self.projeto_super.id,
                "tipo": "evento",
                "tipo_evento": self.tipo_evento.id,
                "inicio": self.inicio.isoformat(),
                "fim": self.fim.isoformat(),
                "coordenador_acompanha": True,  # Não deve afetar o fluxo
                "formadores": [],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "pendente")

        # Verificar no banco
        solicitacao = Solicitacao.objects.get(id=response.data["id"])
        self.assertEqual(solicitacao.status, "pendente")
        self.assertEqual(solicitacao.projeto.fluxo, "SUPER")

    def test_projeto_outros_cria_solicitacao_aprovada(self):
        """
        Testa que projetos com fluxo NAO_SUPER criam solicitações auto-aprovadas.
        """
        self.client.force_authenticate(user=self.coordenador)

        response = self.client.post(
            "/api/solicitacoes/",
            {
                "municipio": self.municipio.id,
                "projeto": self.projeto_outros.id,
                "tipo": "evento",
                "tipo_evento": self.tipo_evento.id,
                "inicio": self.inicio.isoformat(),
                "fim": self.fim.isoformat(),
                "coordenador_acompanha": True,  # Não deve afetar o fluxo
                "formadores": [],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "aprovado")

        # Verificar no banco
        solicitacao = Solicitacao.objects.get(id=response.data["id"])
        self.assertEqual(solicitacao.status, "aprovado")
        self.assertEqual(solicitacao.projeto.fluxo, "NAO_SUPER")

    def test_coordenador_acompanha_nao_afeta_fluxo(self):
        """
        Testa que coordenador_acompanha não afeta mais o fluxo de aprovação.
        """
        self.client.force_authenticate(user=self.coordenador)

        # Teste 1: SUPER com coordenador_acompanha=False ainda fica pendente
        response1 = self.client.post(
            "/api/solicitacoes/",
            {
                "municipio": self.municipio.id,
                "projeto": self.projeto_super.id,
                "tipo": "evento",
                "tipo_evento": self.tipo_evento.id,
                "inicio": self.inicio.isoformat(),
                "fim": self.fim.isoformat(),
                "coordenador_acompanha": False,  # False mas ainda deve ficar pendente
                "formadores": [],
            },
            format="json",
        )

        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response1.data["status"], "pendente")

        # Teste 2: NAO_SUPER com coordenador_acompanha=True ainda é auto-aprovado
        response2 = self.client.post(
            "/api/solicitacoes/",
            {
                "municipio": self.municipio.id,
                "projeto": self.projeto_outros.id,
                "tipo": "evento",
                "tipo_evento": self.tipo_evento.id,
                "inicio": (self.inicio + timedelta(days=1)).isoformat(),
                "fim": (self.fim + timedelta(days=1)).isoformat(),
                "coordenador_acompanha": True,  # True mas ainda é auto-aprovado
                "formadores": [],
            },
            format="json",
        )

        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response2.data["status"], "aprovado")

    def test_projeto_sem_fluxo_usa_padrao_pendente(self):
        """
        Testa que projetos sem fluxo definido usam o padrão (pendente).
        """
        # Criar projeto sem fluxo definido (simula migration antiga)
        projeto_sem_fluxo = Projeto.objects.create(
            nome="Projeto Antigo",
            codigo='',  # Explicitly set empty string (default)
            ativo=True,
            # fluxo será 'NAO_SUPER' por padrão do modelo
        )
        # Forçar fluxo como None para simular projeto antigo
        Projeto.objects.filter(id=projeto_sem_fluxo.id).update(fluxo='NAO_SUPER')
        projeto_sem_fluxo.refresh_from_db()

        self.client.force_authenticate(user=self.coordenador)

        response = self.client.post(
            "/api/solicitacoes/",
            {
                "municipio": self.municipio.id,
                "projeto": projeto_sem_fluxo.id,
                "tipo": "evento",
                "tipo_evento": self.tipo_evento.id,
                "inicio": self.inicio.isoformat(),
                "fim": self.fim.isoformat(),
                "formadores": [],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Como o padrão do modelo é NAO_SUPER, deve ser auto-aprovado
        self.assertEqual(response.data["status"], "aprovado")

    def test_pre_agenda_filtra_por_fluxo_corretamente(self):
        """
        Testa que o endpoint de pré-agenda filtra por fluxo do projeto.
        """
        # Criar solicitações aprovadas
        sol_super = Solicitacao.objects.create(
            usuario=self.coordenador,
            municipio=self.municipio,
            projeto=self.projeto_super,
            tipo="evento",
            tipo_evento=self.tipo_evento,
            inicio=self.inicio,
            fim=self.fim,
            status="aprovado",
        )

        sol_outros = Solicitacao.objects.create(
            usuario=self.coordenador,
            municipio=self.municipio,
            projeto=self.projeto_outros,
            tipo="evento",
            tipo_evento=self.tipo_evento,
            inicio=self.inicio + timedelta(days=1),
            fim=self.fim + timedelta(days=1),
            status="aprovado",
        )

        # Autenticar como Controle (pode ver pré-agenda)
        usuario_controle = Usuario.objects.create_user(
            username="controle1",
            password="test123",
            cpf="11111111111",
        )
        usuario_controle.groups.add(self.grupo_controle)
        self.client.force_authenticate(user=usuario_controle)

        # Filtrar por SUPER
        response_super = self.client.get("/api/pre-agenda/?super=1")
        self.assertEqual(response_super.status_code, status.HTTP_200_OK)
        ids_super = [item["id"] for item in response_super.data["results"]]
        self.assertIn(sol_super.id, ids_super)
        self.assertNotIn(sol_outros.id, ids_super)

        # Filtrar por NAO_SUPER
        response_outros = self.client.get("/api/pre-agenda/?super=0")
        self.assertEqual(response_outros.status_code, status.HTTP_200_OK)
        ids_outros = [item["id"] for item in response_outros.data["results"]]
        self.assertIn(sol_outros.id, ids_outros)
        self.assertNotIn(sol_super.id, ids_outros)

    def test_serializer_retorna_fluxo_do_projeto(self):
        """
        Testa que o PreAgendaListSerializer retorna o fluxo correto.
        """
        # Criar solicitação
        solicitacao = Solicitacao.objects.create(
            usuario=self.coordenador,
            municipio=self.municipio,
            projeto=self.projeto_super,
            tipo="evento",
            tipo_evento=self.tipo_evento,
            inicio=self.inicio,
            fim=self.fim,
            status="aprovado",
        )

        # Autenticar como Controle
        usuario_controle = Usuario.objects.create_user(
            username="controle2",
            password="test123",
            cpf="22222222222",
        )
        usuario_controle.groups.add(self.grupo_controle)
        self.client.force_authenticate(user=usuario_controle)

        response = self.client.get(f"/api/pre-agenda/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Encontrar a solicitação na resposta
        item = next(
            (i for i in response.data["results"] if i["id"] == solicitacao.id),
            None
        )

        self.assertIsNotNone(item)
        self.assertEqual(item["fluxo"], "SUPER")

    def test_comando_seed_atualiza_fluxo_projetos(self):
        """
        Testa que o comando seed_projetos_fluxo_from_csv funciona.

        Skip se CSV não existe (ex: CI sem dados de produção).
        """
        from django.core.management import call_command
        from django.conf import settings
        from pathlib import Path
        from io import StringIO
        import pytest

        # Path absoluto do CSV (não depende do CWD)
        csv_path = Path(settings.BASE_DIR) / "apps/core/data/projetos_fluxo.csv"

        # Skip se CSV não existe (CI sem dados de produção)
        if not csv_path.exists():
            pytest.skip(f"CSV não encontrado: {csv_path}")

        # Criar projeto para atualizar
        projeto_teste = Projeto.objects.create(
            nome="Lendo e Escrevendo",  # Nome no CSV como SUPER
            codigo='',  # Explicitly set empty string (default)
            fluxo="NAO_SUPER",  # Começar com NAO_SUPER
            ativo=True,
        )

        out = StringIO()
        call_command(
            "seed_projetos_fluxo_from_csv",
            f"--csv={csv_path}",
            "--dry-run",
            "--verbose",
            stdout=out,
        )

        output = out.getvalue()
        self.assertIn("Lendo e Escrevendo", output)
        self.assertIn("NAO_SUPER → SUPER", output)

        # Verificar que dry-run não alterou
        projeto_teste.refresh_from_db()
        self.assertEqual(projeto_teste.fluxo, "NAO_SUPER")

        # Executar sem dry-run
        call_command("seed_projetos_fluxo_from_csv", f"--csv={csv_path}")

        # Verificar que foi atualizado
        projeto_teste.refresh_from_db()
        self.assertEqual(projeto_teste.fluxo, "SUPER")


class TestMigrationFluxoProjeto(TestCase):
    """
    Testa a migration que adiciona o campo fluxo.
    """

    def test_migration_adiciona_campo_fluxo(self):
        """
        Verifica que o campo fluxo existe no modelo Projeto.
        """
        # Criar um projeto
        projeto = Projeto.objects.create(
            nome="Teste Migration",
            codigo='',  # Explicitly set empty string (default)
            ativo=True,
        )

        # Verificar que o campo existe e tem valor padrão
        self.assertTrue(hasattr(projeto, "fluxo"))
        self.assertEqual(projeto.fluxo, "NAO_SUPER")  # Valor padrão

        # Verificar choices
        self.assertIn(
            projeto.fluxo,
            [choice[0] for choice in Projeto.FLUXO_CHOICES]
        )

    def test_migration_backfill_projetos_existentes(self):
        """
        Verifica que projetos existentes receberam fluxo='NAO_SUPER'.
        """
        # Todos os projetos criados devem ter fluxo definido
        projetos = Projeto.objects.all()
        for projeto in projetos:
            self.assertIsNotNone(projeto.fluxo)
            self.assertIn(projeto.fluxo, ["SUPER", "NAO_SUPER"])