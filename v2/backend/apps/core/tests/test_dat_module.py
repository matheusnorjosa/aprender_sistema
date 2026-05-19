"""
Tests for DAT Module (5 páginas React).

Testa models, serializers e ViewSets para:
- DATArea
- DATCoordenador
- DATAcao
- DATCompra
- DATCadastro
- DATFormacao

Ref: .claude/plans/linear-scribbling-boole.md
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.models import (
    Compra,
    DATAcao,
    DATArea,
    DATCadastro,
    DATCompra,
    DATCoordenador,
    DATFormacao,
    Municipio,
    Produto,
    Projeto,
    ProjetoGeral,
    Solicitacao,
    TipoEvento,
)

User = get_user_model()


# ============================================================
# Model Tests
# ============================================================


class DATAreaModelTests(TestCase):
    """Tests for DATArea model."""

    def test_create_area(self):
        """DATArea should be created with correct fields."""
        area = DATArea.objects.create(nome="Tecnologia", cor="blue", ordem=1)
        self.assertEqual(area.nome, "Tecnologia")
        self.assertEqual(area.cor, "blue")
        self.assertTrue(area.ativo)
        self.assertEqual(str(area), "Tecnologia")

    def test_unique_nome(self):
        """DATArea nome should be unique."""
        DATArea.objects.create(nome="DAT")
        duplicate = DATArea(nome="DAT")
        with self.assertRaises(ValidationError):
            duplicate.full_clean()


class DATCoordenadorModelTests(TestCase):
    """Tests for DATCoordenador model."""

    @classmethod
    def setUpTestData(cls):
        import uuid

        uid = uuid.uuid4().hex[:6]
        cls.user = User.objects.create_user(
            username=f"testuser_{uid}", password="test123", cpf=f"111{uid}11"  # 11 chars
        )

    def test_create_coordenador(self):
        """DATCoordenador should be created with correct fields."""
        coord = DATCoordenador.objects.create(
            nome="João Silva",
            email="joao@example.com",
            telefone="85999999999",
            area="DAT",
            cargo="Coordenador",
            created_by=self.user,
        )
        self.assertEqual(coord.nome, "João Silva")
        self.assertEqual(coord.area, "DAT")
        self.assertTrue(coord.ativo)
        self.assertEqual(str(coord), "João Silva (DAT)")

    def test_coordenador_properties(self):
        """DATCoordenador properties should return correct values."""
        coord = DATCoordenador.objects.create(nome="Maria Santos", area="Tecnologia", created_by=self.user)
        # Initially no relations
        self.assertEqual(coord.total_municipios, 0)
        self.assertEqual(coord.total_projetos, 0)
        self.assertEqual(coord.total_formacoes, 0)


class DATAcaoModelTests(TestCase):
    """Tests for DATAcao model."""

    @classmethod
    def setUpTestData(cls):
        import uuid

        uid = uuid.uuid4().hex[:5]
        cls.user = User.objects.create_user(
            username=f"testuser_acao_{uid}", password="test123", cpf=f"222{uid}222"  # 11 chars
        )
        cls.municipio = Municipio.objects.create(nome=f"Fortaleza_{uid}", uf="CE")
        cls.projeto = Projeto.objects.create(nome=f"Projeto Teste_{uid}", codigo=f"PT{uid[:4]}", fluxo="NAO_SUPER")
        cls.coordenador = DATCoordenador.objects.create(nome="Coordenador Teste", area="DAT", created_by=cls.user)

    def test_create_acao(self):
        """DATAcao should be created with correct fields."""
        acao = DATAcao.objects.create(
            municipio=self.municipio, projeto=self.projeto, coordenador=self.coordenador, created_by=self.user
        )
        self.assertEqual(acao.status_carta, "pendente")
        self.assertEqual(acao.status_contato, "pendente")
        self.assertEqual(acao.status_reuniao, "pendente")
        self.assertEqual(acao.status_entrega, "pendente")
        # Check __str__ contains both municipio and projeto
        self.assertIn(self.municipio.nome, str(acao))
        self.assertIn(self.projeto.nome, str(acao))

    def test_progresso_property(self):
        """DATAcao progresso should calculate correctly."""
        acao = DATAcao.objects.create(municipio=self.municipio, projeto=self.projeto, created_by=self.user)
        # All pending = 0%
        self.assertEqual(acao.progresso, 0)

        # 1 of 4 complete = 25%
        acao.status_carta = "concluido"
        acao.save()
        self.assertEqual(acao.progresso, 25)

        # 2 of 4 complete = 50%
        acao.status_contato = "concluido"
        acao.save()
        self.assertEqual(acao.progresso, 50)

        # All complete = 100%
        acao.status_reuniao = "concluido"
        acao.status_entrega = "concluido"
        acao.save()
        self.assertEqual(acao.progresso, 100)

    def test_etapa_atual_property(self):
        """DATAcao etapa_atual should return correct stage."""
        acao = DATAcao.objects.create(municipio=self.municipio, projeto=self.projeto, created_by=self.user)
        self.assertEqual(acao.etapa_atual, "Carta")

        acao.status_carta = "concluido"
        self.assertEqual(acao.etapa_atual, "Contato")

        acao.status_contato = "concluido"
        self.assertEqual(acao.etapa_atual, "Reunião")

        acao.status_reuniao = "concluido"
        self.assertEqual(acao.etapa_atual, "Entrega")

        acao.status_entrega = "concluido"
        self.assertEqual(acao.etapa_atual, "Concluído")

    def test_unique_municipio_projeto(self):
        """DATAcao should be unique per municipio+projeto."""
        DATAcao.objects.create(municipio=self.municipio, projeto=self.projeto, created_by=self.user)
        duplicate = DATAcao(municipio=self.municipio, projeto=self.projeto, created_by=self.user)
        with self.assertRaises(ValidationError):
            duplicate.full_clean()


class DATCompraModelTests(TestCase):
    """Tests for DATCompra model."""

    @classmethod
    def setUpTestData(cls):
        import uuid

        uid = uuid.uuid4().hex[:5]
        cls.user = User.objects.create_user(
            username=f"testuser_compra_{uid}", password="test123", cpf=f"333{uid}333"  # 11 chars
        )
        cls.municipio = Municipio.objects.create(nome=f"Fortaleza_compra_{uid}", uf="CE")
        cls.projeto = Projeto.objects.create(
            nome=f"Projeto Teste_compra_{uid}", codigo=f"PC{uid[:4]}", fluxo="NAO_SUPER"
        )

    def test_create_compra(self):
        """DATCompra should be created with correct fields."""
        compra = DATCompra.objects.create(
            municipio=self.municipio,
            projeto=self.projeto,
            descricao_produto="Kit Pedagógico",
            quantidade=100,
            valor_unitario=Decimal("50.00"),
            ano_uso=2025,
            created_by=self.user,
        )
        self.assertEqual(compra.quantidade, 100)
        self.assertEqual(compra.quantidade_utilizada, 0)
        self.assertEqual(compra.status_uso, "disponivel")

    def test_disponivel_property(self):
        """DATCompra disponivel should calculate correctly."""
        compra = DATCompra.objects.create(
            municipio=self.municipio,
            projeto=self.projeto,
            descricao_produto="Material",
            quantidade=100,
            quantidade_utilizada=30,
            ano_uso=2025,
            created_by=self.user,
        )
        self.assertEqual(compra.disponivel, 70)

    def test_valor_total_property(self):
        """DATCompra valor_total should calculate correctly."""
        compra = DATCompra.objects.create(
            municipio=self.municipio,
            projeto=self.projeto,
            descricao_produto="Material",
            quantidade=10,
            valor_unitario=Decimal("25.50"),
            ano_uso=2025,
            created_by=self.user,
        )
        self.assertEqual(compra.valor_total, Decimal("255.00"))

    def test_status_uso_auto_update(self):
        """DATCompra status_uso should auto-update based on quantities."""
        compra = DATCompra.objects.create(
            municipio=self.municipio,
            projeto=self.projeto,
            descricao_produto="Material",
            quantidade=100,
            ano_uso=2025,
            created_by=self.user,
        )
        self.assertEqual(compra.status_uso, "disponivel")

        compra.quantidade_utilizada = 50
        compra.save()
        self.assertEqual(compra.status_uso, "em_uso")

        compra.quantidade_utilizada = 100
        compra.save()
        self.assertEqual(compra.status_uso, "esgotado")


class DATCadastroModelTests(TestCase):
    """Tests for DATCadastro model."""

    @classmethod
    def setUpTestData(cls):
        import uuid

        uid = uuid.uuid4().hex[:5]
        cls.user = User.objects.create_user(
            username=f"testuser_cadastro_{uid}", password="test123", cpf=f"444{uid}444"  # 11 chars
        )
        cls.municipio = Municipio.objects.create(nome=f"Fortaleza_cadastro_{uid}", uf="CE")
        cls.projeto_geral = ProjetoGeral.objects.create(nome=f"PG Teste_cadastro_{uid}", usa_avaliar=True)

    def test_create_cadastro_formar(self):
        """DATCadastro FORMAR should be created correctly."""
        cadastro = DATCadastro.objects.create(
            municipio=self.municipio, projeto_geral=self.projeto_geral, plataforma="FORMAR", created_by=self.user
        )
        self.assertEqual(cadastro.plataforma, "FORMAR")
        self.assertEqual(cadastro.status_criacao_curso, "pendente")

    def test_create_cadastro_avaliar(self):
        """DATCadastro AVALIAR should be created correctly."""
        cadastro = DATCadastro.objects.create(
            municipio=self.municipio, projeto_geral=self.projeto_geral, plataforma="AVALIAR", created_by=self.user
        )
        self.assertEqual(cadastro.plataforma, "AVALIAR")
        self.assertEqual(cadastro.status_recebidos, "pendente")

    def test_progresso_formar(self):
        """DATCadastro progresso_formar should calculate correctly."""
        cadastro = DATCadastro.objects.create(
            municipio=self.municipio, projeto_geral=self.projeto_geral, plataforma="FORMAR", created_by=self.user
        )
        self.assertEqual(cadastro.progresso_formar, 0)

        cadastro.status_criacao_curso = "concluido"
        cadastro.status_chaves = "concluido"
        cadastro.save()
        self.assertEqual(cadastro.progresso_formar, 50)

        cadastro.status_instrucoes = "concluido"
        cadastro.status_envio = "concluido"
        cadastro.save()
        self.assertEqual(cadastro.progresso_formar, 100)

    def test_progresso_avaliar(self):
        """DATCadastro progresso_avaliar should calculate correctly."""
        cadastro = DATCadastro.objects.create(
            municipio=self.municipio, projeto_geral=self.projeto_geral, plataforma="AVALIAR", created_by=self.user
        )
        self.assertEqual(cadastro.progresso_avaliar, 0)

        cadastro.status_recebidos = "concluido"
        cadastro.save()
        self.assertEqual(cadastro.progresso_avaliar, 33)  # 1/3 = 33%

        cadastro.status_validados = "concluido"
        cadastro.status_importados = "concluido"
        cadastro.save()
        self.assertEqual(cadastro.progresso_avaliar, 100)

    def test_unique_municipio_projeto_plataforma(self):
        """DATCadastro should be unique per municipio+projeto_geral+plataforma."""
        DATCadastro.objects.create(
            municipio=self.municipio, projeto_geral=self.projeto_geral, plataforma="FORMAR", created_by=self.user
        )
        duplicate = DATCadastro(
            municipio=self.municipio, projeto_geral=self.projeto_geral, plataforma="FORMAR", created_by=self.user
        )
        with self.assertRaises(ValidationError):
            duplicate.full_clean()


class DATFormacaoModelTests(TestCase):
    """Tests for DATFormacao model."""

    @classmethod
    def setUpTestData(cls):
        import uuid

        uid = uuid.uuid4().hex[:5]
        cls.user = User.objects.create_user(
            username=f"testuser_formacao_{uid}", password="test123", cpf=f"555{uid}555"  # 11 chars
        )
        cls.municipio = Municipio.objects.create(nome=f"Fortaleza_formacao_{uid}", uf="CE")
        cls.projeto = Projeto.objects.create(
            nome=f"Projeto Teste_formacao_{uid}", codigo=f"PF{uid[:4]}", fluxo="NAO_SUPER"
        )

    def test_create_formacao(self):
        """DATFormacao should be created with correct fields."""
        formacao = DATFormacao.objects.create(
            municipio=self.municipio,
            projeto=self.projeto,
            titulo="Formação de Professores",
            data_formacao=date.today(),
            horario_inicio=time(9, 0),
            horario_fim=time(12, 0),
            modalidade="presencial",
            quantidade_prevista=50,
            created_by=self.user,
        )
        self.assertEqual(formacao.status, "agendada")
        self.assertEqual(formacao.modalidade, "presencial")

    def test_duracao_horas_property(self):
        """DATFormacao duracao_horas should calculate correctly."""
        formacao = DATFormacao.objects.create(
            municipio=self.municipio,
            projeto=self.projeto,
            titulo="Formação",
            data_formacao=date.today(),
            horario_inicio=time(9, 0),
            horario_fim=time(12, 0),
            created_by=self.user,
        )
        self.assertEqual(formacao.duracao_horas, 3.0)

    def test_taxa_presenca_property(self):
        """DATFormacao taxa_presenca should calculate correctly."""
        formacao = DATFormacao.objects.create(
            municipio=self.municipio,
            projeto=self.projeto,
            titulo="Formação",
            data_formacao=date.today(),
            horario_inicio=time(9, 0),
            horario_fim=time(12, 0),
            quantidade_prevista=100,
            quantidade_presente=75,
            created_by=self.user,
        )
        self.assertEqual(formacao.taxa_presenca, 75.0)

    def test_documentacao_completa_property(self):
        """DATFormacao documentacao_completa should check all flags."""
        formacao = DATFormacao.objects.create(
            municipio=self.municipio,
            projeto=self.projeto,
            titulo="Formação",
            data_formacao=date.today(),
            horario_inicio=time(9, 0),
            horario_fim=time(12, 0),
            created_by=self.user,
        )
        self.assertFalse(formacao.documentacao_completa)

        formacao.material_preparado = True
        formacao.lista_presenca_enviada = True
        formacao.relatorio_enviado = True
        formacao.fotos_enviadas = True
        formacao.save()
        self.assertTrue(formacao.documentacao_completa)


# ============================================================
# API Tests
# ============================================================


class DATModuleAPITestCase(APITestCase):
    """Base test case with common setup for DAT Module API tests."""

    @classmethod
    def setUpTestData(cls):
        import uuid

        # Create groups
        cls.dat_group, _ = Group.objects.get_or_create(name="DAT")
        cls.diretoria_group, _ = Group.objects.get_or_create(name="Diretoria")
        cls.super_group, _ = Group.objects.get_or_create(name="Superintendência")
        cls.gerente_group, _ = Group.objects.get_or_create(name="Gerente")

        # Create users with unique CPFs (exactly 11 chars)
        uid = uuid.uuid4().hex[:5]
        cls.dat_user = User.objects.create_user(
            username=f"dat_user_{uid}", password="test123", cpf=f"666{uid}666"  # 11 chars
        )
        cls.dat_user.groups.add(cls.dat_group)

        uid2 = uuid.uuid4().hex[:5]
        cls.super_user = User.objects.create_user(
            username=f"super_user_{uid2}", password="test123", cpf=f"777{uid2}777"  # 11 chars
        )
        cls.super_user.groups.add(cls.super_group, cls.gerente_group)

        uid3 = uuid.uuid4().hex[:5]
        cls.regular_user = User.objects.create_user(
            username=f"regular_user_{uid3}", password="test123", cpf=f"888{uid3}888"  # 11 chars
        )

        uid4 = uuid.uuid4().hex[:5]
        cls.diretoria_user = User.objects.create_user(
            username=f"diretoria_user_{uid4}", password="test123", cpf=f"889{uid4}889"  # 11 chars
        )
        cls.diretoria_user.groups.add(cls.diretoria_group)

        # Create base data with unique names
        uid = uuid.uuid4().hex[:8]
        cls.municipio = Municipio.objects.create(nome=f"Fortaleza_api_{uid}", uf="CE")
        cls.municipio2 = Municipio.objects.create(nome=f"Caucaia_api_{uid}", uf="CE")
        cls.projeto = Projeto.objects.create(nome=f"Projeto Teste_api_{uid}", codigo=f"PA{uid[:4]}", fluxo="NAO_SUPER")
        cls.projeto_geral = ProjetoGeral.objects.create(nome=f"PG Teste_api_{uid}", usa_avaliar=True)
        cls.area, _ = DATArea.objects.get_or_create(nome="DAT", defaults={"cor": "blue", "ordem": 1})
        cls.coordenador = DATCoordenador.objects.create(
            nome=f"Coordenador Teste_{uid}", email=f"coord_{uid}@test.com", area="DAT", created_by=cls.dat_user
        )


class DATAreaAPITests(DATModuleAPITestCase):
    """Tests for DATArea API endpoints."""

    def test_list_areas_authenticated(self):
        """Authenticated user should list areas."""
        self.client.force_authenticate(user=self.regular_user)
        url = reverse("core:dat-area-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_areas_unauthenticated(self):
        """Unauthenticated user should get 403 (DRF default)."""
        url = reverse("core:dat-area-list")
        response = self.client.get(url)
        # DRF returns 403 for unauthenticated requests by default
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_areas_readonly(self):
        """DATArea should be read-only."""
        self.client.force_authenticate(user=self.super_user)
        url = reverse("core:dat-area-list")
        response = self.client.post(url, {"nome": "Nova Area"})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class DATCoordenadorAPITests(DATModuleAPITestCase):
    """Tests for DATCoordenador API endpoints."""

    def test_list_coordenadores_dat_user(self):
        """DAT user should list coordenadores."""
        self.client.force_authenticate(user=self.dat_user)
        url = reverse("core:dat-coordenador-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_coordenadores_regular_user_forbidden(self):
        """Regular user should get 403."""
        self.client.force_authenticate(user=self.regular_user)
        url = reverse("core:dat-coordenador-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_coordenador_dat_user(self):
        """DAT user should create coordenador."""
        self.client.force_authenticate(user=self.dat_user)
        url = reverse("core:dat-coordenador-list")
        data = {"nome": "Novo Coordenador", "email": "novo@test.com", "area": "Tecnologia"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["nome"], "Novo Coordenador")

    def test_delete_coordenador_dat_user_forbidden(self):
        """DAT user should NOT delete coordenador (Super only)."""
        self.client.force_authenticate(user=self.dat_user)
        url = reverse("core:dat-coordenador-detail", args=[self.coordenador.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_coordenador_super_user(self):
        """Super user should delete coordenador."""
        self.client.force_authenticate(user=self.super_user)
        coord = DATCoordenador.objects.create(nome="To Delete", area="Test", created_by=self.dat_user)
        url = reverse("core:dat-coordenador-detail", args=[coord.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_alocacoes_action(self):
        """Alocacoes action should return coordenador allocations."""
        self.client.force_authenticate(user=self.dat_user)
        url = reverse("core:dat-coordenador-alocacoes", args=[self.coordenador.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("acoes", response.data)
        self.assertIn("formacoes", response.data)


class DATAcaoAPITests(DATModuleAPITestCase):
    """Tests for DATAcao API endpoints."""

    def test_list_acoes_dat_user(self):
        """DAT user should list acoes."""
        self.client.force_authenticate(user=self.dat_user)
        url = reverse("core:dat-acao-ciclo-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_acao(self):
        """DAT user should create acao."""
        self.client.force_authenticate(user=self.dat_user)
        url = reverse("core:dat-acao-ciclo-list")
        data = {"municipio": self.municipio.id, "projeto": self.projeto.id, "coordenador": self.coordenador.id}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_acao_status(self):
        """DAT user should update acao status."""
        self.client.force_authenticate(user=self.dat_user)
        acao = DATAcao.objects.create(municipio=self.municipio, projeto=self.projeto, created_by=self.dat_user)
        url = reverse("core:dat-acao-ciclo-detail", args=[acao.id])
        response = self.client.patch(url, {"status_carta": "concluido", "data_carta": "2025-01-15"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        acao.refresh_from_db()
        self.assertEqual(acao.status_carta, "concluido")

    def test_stats_action(self):
        """Stats action should return aggregated data."""
        self.client.force_authenticate(user=self.dat_user)
        # Create some acoes
        DATAcao.objects.create(municipio=self.municipio, projeto=self.projeto, created_by=self.dat_user)
        url = reverse("core:dat-acao-ciclo-stats")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("total", response.data)
        self.assertIn("por_etapa", response.data)

    def test_stats_por_etapa_aggregates_correctly_across_priorities_and_municipios(self):
        """Regression: por_etapa.<status>.values() must sum to total.

        The ViewSet's base queryset is ordered by `-prioridade, municipio__nome`.
        When `.values_list("status_carta").annotate(c=Count("id"))` is called
        on that ordered queryset, Django pulls the ORDER BY columns into the
        GROUP BY clause, producing a fragmented count
        (one bucket per (status, prioridade, municipio_nome) tuple) so the
        stats endpoint reported sum << total.

        With the fix, `stats_qs = qs.order_by()` strips the inherited ordering
        before aggregation, restoring the correct GROUP BY status_carta only.
        """
        self.client.force_authenticate(user=self.dat_user)

        # 6 acoes, same status_carta="concluido", varied prioridade + municipio
        # → without the fix, GROUP BY (status_carta, prioridade, municipio__nome)
        # would yield 6 distinct buckets of count=1 instead of {"concluido": 6}.
        # DATAcao has unique_together(municipio, projeto), so we create one
        # fresh municipio per row (different prioridade for each).
        import uuid

        uid = uuid.uuid4().hex[:6]
        for prio in range(1, 7):
            mun = Municipio.objects.create(nome=f"StatsCity_{uid}_{prio}", uf="CE")
            DATAcao.objects.create(
                municipio=mun,
                projeto=self.projeto,
                status_carta="concluido",
                status_contato="pendente",
                status_reuniao="pendente",
                status_entrega="pendente",
                prioridade=prio,
                created_by=self.dat_user,
            )

        url = reverse("core:dat-acao-ciclo-stats")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        total = response.data["total"]
        self.assertEqual(total, 6, "Sanity: 6 DATAcao created in this test")

        por_etapa = response.data["por_etapa"]
        # Critério de aceite obrigatório
        sum_carta = sum(por_etapa["carta"].values())
        self.assertEqual(
            sum_carta,
            total,
            f"por_etapa.carta groups should sum to total ({total}); got {sum_carta} "
            f"— likely regression of ORDER BY → GROUP BY fragmentation. "
            f"Raw por_etapa.carta={por_etapa['carta']!r}",
        )
        # E os 6 devem estar em UMA bucket (concluido), não fragmentados
        self.assertEqual(por_etapa["carta"].get("concluido"), 6)

        # Mesma propriedade para as outras 3 etapas
        for etapa in ("contato", "reuniao", "entrega"):
            sum_etapa = sum(por_etapa[etapa].values())
            self.assertEqual(
                sum_etapa,
                total,
                f"por_etapa.{etapa} groups should sum to total ({total}); got {sum_etapa}",
            )

        # por_projeto / por_coordenador também devem usar mesmo queryset stats
        # → soma de counts deve bater com total quando há 1 projeto único
        sum_projeto = sum(p["count"] for p in response.data["por_projeto"])
        self.assertEqual(sum_projeto, total)


class DATCompraAPITests(DATModuleAPITestCase):
    """Tests for DATCompra API endpoints."""

    def test_create_compra(self):
        """DAT user should create compra."""
        self.client.force_authenticate(user=self.dat_user)
        url = reverse("core:dat-compra-material-list")
        data = {
            "municipio": self.municipio.id,
            "projeto": self.projeto.id,
            "descricao_produto": "Kit Pedagógico",
            "quantidade": 100,
            "valor_unitario": "50.00",
            "ano_uso": 2025,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_stats_action(self):
        """Stats action should return aggregated data."""
        self.client.force_authenticate(user=self.dat_user)
        DATCompra.objects.create(
            municipio=self.municipio,
            projeto=self.projeto,
            descricao_produto="Material",
            quantidade=100,
            ano_uso=2025,
            created_by=self.dat_user,
        )
        url = reverse("core:dat-compra-material-stats")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("total", response.data)

    def test_dashboard_action_allows_diretoria_user(self):
        """Diretoria deve acessar dashboard de compras (somente leitura)."""
        self.client.force_authenticate(user=self.diretoria_user)
        url = reverse("core:dat-compra-material-dashboard")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("kpis", response.data)

    def test_dashboard_action_forbidden_for_regular_user(self):
        """Regular user should not access compras dashboard action."""
        self.client.force_authenticate(user=self.regular_user)
        url = reverse("core:dat-compra-material-dashboard")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_pendencias_action_returns_only_pairs_without_active_event(self):
        """Pendencias should list only core_compra pairs without pending/approved solicitacao."""
        self.client.force_authenticate(user=self.dat_user)

        tipo_evento = TipoEvento.objects.create(nome="Seminário DAT")

        Compra.objects.create(
            codigo="CORE-A",
            projeto=self.projeto,
            municipio=self.municipio,
            quantidade=10,
            data=date(2026, 3, 1),
            uso="Fluxo A",
            external_hash="a" * 64,
        )
        Compra.objects.create(
            codigo="CORE-B",
            projeto=self.projeto,
            municipio=self.municipio2,
            quantidade=20,
            data=date(2026, 3, 2),
            uso="Fluxo B",
            external_hash="b" * 64,
        )

        inicio = timezone.now() + timedelta(days=2)
        fim = inicio + timedelta(hours=2)
        Solicitacao.objects.create(
            usuario=self.dat_user,
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=tipo_evento,
            inicio=inicio,
            fim=fim,
            status="pendente",
        )

        url = reverse("core:dat-compra-material-pendencias")
        response = self.client.get(url, secure=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_com_compra"], 2)
        self.assertEqual(response.data["total_com_evento"], 1)
        self.assertEqual(response.data["total_pendentes"], 1)
        self.assertEqual(len(response.data["pendentes"]), 1)
        self.assertEqual(response.data["pendentes"][0]["municipio"], self.municipio2.nome)
        self.assertEqual(response.data["pendentes"][0]["projeto"], self.projeto.nome)

    def test_pendencias_action_allows_diretoria_user(self):
        """Diretoria deve acessar pendências de compras para leitura executiva."""
        self.client.force_authenticate(user=self.diretoria_user)
        url = reverse("core:dat-compra-material-pendencias")
        response = self.client.get(url, secure=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("pendentes", response.data)

    def test_pendencias_action_forbidden_for_regular_user(self):
        """Regular users should not access pendencias action."""
        self.client.force_authenticate(user=self.regular_user)
        url = reverse("core:dat-compra-material-pendencias")
        response = self.client.get(url, secure=True)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class DATCadastroAPITests(DATModuleAPITestCase):
    """Tests for DATCadastro API endpoints."""

    def test_create_cadastro(self):
        """DAT user should create cadastro."""
        self.client.force_authenticate(user=self.dat_user)
        url = reverse("core:dat-cadastro-list")
        data = {"municipio": self.municipio.id, "projeto_geral": self.projeto_geral.id, "plataforma": "FORMAR"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_etapa_action(self):
        """Etapa action should update specific stage."""
        self.client.force_authenticate(user=self.dat_user)
        cadastro = DATCadastro.objects.create(
            municipio=self.municipio, projeto_geral=self.projeto_geral, plataforma="FORMAR", created_by=self.dat_user
        )
        url = reverse("core:dat-cadastro-etapa", args=[cadastro.id])
        response = self.client.post(url, {"etapa": "chaves", "status": "concluido", "data": "2025-01-15"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cadastro.refresh_from_db()
        self.assertEqual(cadastro.status_chaves, "concluido")

    def test_etapa_action_invalid_etapa(self):
        """Etapa action should reject invalid stage."""
        self.client.force_authenticate(user=self.dat_user)
        cadastro = DATCadastro.objects.create(
            municipio=self.municipio, projeto_geral=self.projeto_geral, plataforma="FORMAR", created_by=self.dat_user
        )
        url = reverse("core:dat-cadastro-etapa", args=[cadastro.id])
        response = self.client.post(url, {"etapa": "invalid_etapa", "status": "concluido"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class DATFormacaoAPITests(DATModuleAPITestCase):
    """Tests for DATFormacao API endpoints."""

    def test_create_formacao(self):
        """DAT user should create formacao."""
        self.client.force_authenticate(user=self.dat_user)
        url = reverse("core:dat-formacao-list")
        data = {
            "municipio": self.municipio.id,
            "projeto": self.projeto.id,
            "titulo": "Formação de Professores",
            "data_formacao": "2025-02-15",
            "horario_inicio": "09:00",
            "horario_fim": "12:00",
            "modalidade": "presencial",
            "quantidade_prevista": 50,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_calendario_action(self):
        """Calendario action should return events for date range."""
        self.client.force_authenticate(user=self.dat_user)
        today = date.today()
        DATFormacao.objects.create(
            municipio=self.municipio,
            projeto=self.projeto,
            titulo="Formação",
            data_formacao=today,
            horario_inicio=time(9, 0),
            horario_fim=time(12, 0),
            created_by=self.dat_user,
        )
        url = reverse("core:dat-formacao-calendario")
        response = self.client.get(
            url,
            {
                "data_inicio": (today - timedelta(days=1)).isoformat(),
                "data_fim": (today + timedelta(days=1)).isoformat(),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_calendario_action_missing_params(self):
        """Calendario action should require date params."""
        self.client.force_authenticate(user=self.dat_user)
        url = reverse("core:dat-formacao-calendario")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_stats_action(self):
        """Stats action should return aggregated data."""
        self.client.force_authenticate(user=self.dat_user)
        DATFormacao.objects.create(
            municipio=self.municipio,
            projeto=self.projeto,
            titulo="Formação",
            data_formacao=date.today(),
            horario_inicio=time(9, 0),
            horario_fim=time(12, 0),
            quantidade_prevista=50,
            quantidade_presente=40,
            created_by=self.dat_user,
        )
        url = reverse("core:dat-formacao-stats")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("total", response.data)
        self.assertIn("participantes_previstos", response.data)
        self.assertEqual(response.data["participantes_previstos"], 50)


# ============================================================
# Permission Tests
# ============================================================


class DATModulePermissionTests(DATModuleAPITestCase):
    """Tests for DAT Module permissions."""

    def test_regular_user_cannot_access_dat_endpoints(self):
        """Regular user should get 403 on all DAT endpoints."""
        self.client.force_authenticate(user=self.regular_user)

        endpoints = [
            reverse("core:dat-coordenador-list"),
            reverse("core:dat-acao-ciclo-list"),
            reverse("core:dat-compra-material-list"),
            reverse("core:dat-cadastro-list"),
            reverse("core:dat-formacao-list"),
        ]

        for url in endpoints:
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, f"Expected 403 for {url}")

    def test_dat_user_can_access_all_endpoints(self):
        """DAT user should access all DAT endpoints."""
        self.client.force_authenticate(user=self.dat_user)

        endpoints = [
            reverse("core:dat-coordenador-list"),
            reverse("core:dat-acao-ciclo-list"),
            reverse("core:dat-compra-material-list"),
            reverse("core:dat-cadastro-list"),
            reverse("core:dat-formacao-list"),
        ]

        for url in endpoints:
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK, f"Expected 200 for {url}")

    def test_super_user_can_delete(self):
        """Super user should be able to delete records."""
        self.client.force_authenticate(user=self.super_user)

        # Create records to delete
        acao = DATAcao.objects.create(municipio=self.municipio, projeto=self.projeto, created_by=self.dat_user)
        compra = DATCompra.objects.create(
            municipio=self.municipio,
            projeto=self.projeto,
            descricao_produto="Test",
            quantidade=10,
            ano_uso=2025,
            created_by=self.dat_user,
        )
        cadastro = DATCadastro.objects.create(
            municipio=self.municipio, projeto_geral=self.projeto_geral, plataforma="FORMAR", created_by=self.dat_user
        )
        formacao = DATFormacao.objects.create(
            municipio=self.municipio,
            projeto=self.projeto,
            titulo="Test",
            data_formacao=date.today(),
            horario_inicio=time(9, 0),
            horario_fim=time(12, 0),
            created_by=self.dat_user,
        )

        # Delete all
        self.assertEqual(
            self.client.delete(reverse("core:dat-acao-ciclo-detail", args=[acao.id])).status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertEqual(
            self.client.delete(reverse("core:dat-compra-material-detail", args=[compra.id])).status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertEqual(
            self.client.delete(reverse("core:dat-cadastro-detail", args=[cadastro.id])).status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertEqual(
            self.client.delete(reverse("core:dat-formacao-detail", args=[formacao.id])).status_code,
            status.HTTP_204_NO_CONTENT,
        )

    def test_dat_user_cannot_delete(self):
        """DAT user should NOT be able to delete records."""
        self.client.force_authenticate(user=self.dat_user)

        acao = DATAcao.objects.create(
            municipio=self.municipio2,  # Use different municipio to avoid constraint
            projeto=self.projeto,
            created_by=self.dat_user,
        )

        response = self.client.delete(reverse("core:dat-acao-ciclo-detail", args=[acao.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
