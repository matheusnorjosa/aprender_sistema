"""
Tests for DAT Module (5 páginas React).

Testa models, serializers e ViewSets para:
- DATArea
- DATCoordenador
- DATAcao
- DATCompra
- DATCadastro

Ref: .claude/plans/linear-scribbling-boole.md
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.models import (
    DATAcao,
    DATArea,
    DATCadastro,
    DATCompra,
    DATCoordenador,
    ProjetoGeral,
)
from apps.core.tests.factories import (
    GroupFactory,
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
    com_pacote_da_diretoria,
    com_pacote_do_dat,
)

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
        cls.user = UsuarioFactory(username=f"testuser_{uid}", password="test123", cpf=f"111{uid}11")  # 11 chars

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


class DATAcaoModelTests(TestCase):
    """Tests for DATAcao model."""

    @classmethod
    def setUpTestData(cls):
        import uuid

        uid = uuid.uuid4().hex[:5]
        cls.user = UsuarioFactory(username=f"testuser_acao_{uid}", password="test123", cpf=f"222{uid}222")  # 11 chars
        cls.municipio = MunicipioFactory(nome=f"Fortaleza_{uid}", uf="CE")
        cls.projeto = ProjetoFactory(nome=f"Projeto Teste_{uid}", codigo=f"PT{uid[:4]}", fluxo="NAO_SUPER")
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
        cls.user = UsuarioFactory(username=f"testuser_compra_{uid}", password="test123", cpf=f"333{uid}333")  # 11 chars
        cls.municipio = MunicipioFactory(nome=f"Fortaleza_compra_{uid}", uf="CE")
        cls.projeto = ProjetoFactory(nome=f"Projeto Teste_compra_{uid}", codigo=f"PC{uid[:4]}", fluxo="NAO_SUPER")

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
        cls.user = UsuarioFactory(
            username=f"testuser_cadastro_{uid}", password="test123", cpf=f"444{uid}444"  # 11 chars
        )
        cls.municipio = MunicipioFactory(nome=f"Fortaleza_cadastro_{uid}", uf="CE")
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


class DATModuleAPITestCase(APITestCase):
    """Base test case with common setup for DAT Module API tests."""

    @classmethod
    def setUpTestData(cls):
        import uuid

        # Create groups
        cls.dat_group = GroupFactory(name="DAT")
        cls.diretoria_group = GroupFactory(name="Diretoria")
        cls.super_group = GroupFactory(name="Superintendência")
        cls.gerente_group = GroupFactory(name="Gerente")

        # Create users with unique CPFs (exactly 11 chars)
        uid = uuid.uuid4().hex[:5]
        cls.dat_user = UsuarioFactory(username=f"dat_user_{uid}", password="test123", cpf=f"666{uid}666")  # 11 chars
        cls.dat_user.groups.add(cls.dat_group)
        com_pacote_do_dat(cls.dat_user)

        uid2 = uuid.uuid4().hex[:5]
        cls.super_user = UsuarioFactory(
            username=f"super_user_{uid2}", password="test123", cpf=f"777{uid2}777"  # 11 chars
        )
        cls.super_user.groups.add(cls.super_group, cls.gerente_group)
        # PR 10: o grupo Superintendência não tem capacidade (0126); o poder vem do pacote do DAT.
        com_pacote_do_dat(cls.super_user)

        uid3 = uuid.uuid4().hex[:5]
        cls.regular_user = UsuarioFactory(
            username=f"regular_user_{uid3}", password="test123", cpf=f"888{uid3}888"  # 11 chars
        )

        uid4 = uuid.uuid4().hex[:5]
        cls.diretoria_user = UsuarioFactory(
            username=f"diretoria_user_{uid4}", password="test123", cpf=f"889{uid4}889"  # 11 chars
        )
        cls.diretoria_user.groups.add(cls.diretoria_group)
        com_pacote_da_diretoria(cls.diretoria_user)

        # Create base data with unique names
        uid = uuid.uuid4().hex[:8]
        cls.municipio = MunicipioFactory(nome=f"Fortaleza_api_{uid}", uf="CE")
        cls.municipio2 = MunicipioFactory(nome=f"Caucaia_api_{uid}", uf="CE")
        cls.projeto = ProjetoFactory(nome=f"Projeto Teste_api_{uid}", codigo=f"PA{uid[:4]}", fluxo="NAO_SUPER")
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
        """Sem o pacote do DAT, não exclui coordenador (PR 10: o DAT exclui pelo vínculo)."""
        self.client.force_authenticate(user=self.regular_user)
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
        self.assertIn("total_acoes", response.data)


class DATAcaoAPITests(DATModuleAPITestCase):
    """Tests for DATAcao API endpoints."""

    def test_list_acoes_dat_user(self):
        """DAT user should list acoes."""
        self.client.force_authenticate(user=self.dat_user)
        url = reverse("core:dat-acao-ciclo-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_acoes_devolve_observacao_da_carta(self):
        """Lote D (D2): a coluna Observações da Gestão de Ações lê `observacao_carta` da lista."""
        self.client.force_authenticate(user=self.dat_user)
        acao = DATAcao.objects.create(
            municipio=self.municipio,
            projeto=self.projeto,
            observacao_carta="Carta entregue na secretaria",
            created_by=self.dat_user,
        )
        url = reverse("core:dat-acao-ciclo-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        linha = next(item for item in response.data["results"] if item["id"] == acao.id)
        self.assertEqual(linha["observacao_carta"], "Carta entregue na secretaria")

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
            mun = MunicipioFactory(nome=f"StatsCity_{uid}_{prio}", uf="CE")
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

    def test_stats_aggregations_not_fragmented_by_listing_ordering(self):
        """Regression: same bug as DATAcao stats (PR #1361).

        DATCompra base queryset is ordered by ("-ano_uso", "municipio__nome").
        Without `.order_by()` before `.values_list().annotate(Count())`, Django
        injects those columns into GROUP BY and fragments the counts.
        """
        import uuid

        self.client.force_authenticate(user=self.dat_user)

        uid = uuid.uuid4().hex[:6]
        # 6 compras, same status_uso, varied municipio + ano_uso → would
        # fragment without the fix (GROUP BY status, ano_uso, municipio_nome).
        for i in range(6):
            mun = MunicipioFactory(nome=f"ComprasCity_{uid}_{i}", uf="CE")
            DATCompra.objects.create(
                municipio=mun,
                projeto=self.projeto,
                descricao_produto=f"Item {i}",
                quantidade=10,
                ano_uso=2020 + i,  # varied
                status_uso="disponivel",
                created_by=self.dat_user,
            )

        url = reverse("core:dat-compra-material-stats")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        total = response.data["total"]
        self.assertEqual(total, 6)

        # por_status deve somar 6 (todos disponivel) — não fragmentado
        sum_status = sum(response.data["por_status"].values())
        self.assertEqual(
            sum_status,
            total,
            f"por_status should sum to total ({total}); got {sum_status}. "
            f"Regression of ORDER BY → GROUP BY fragmentation. por_status={response.data['por_status']!r}",
        )

        # por_ano top 5 deve ter contagens corretas
        sum_ano = sum(p["count"] for p in response.data["por_ano"])
        # 5 últimos anos: cada ano teve 1 compra → sum = 5 (de 6 total)
        self.assertEqual(sum_ano, 5)

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

    def _dat_compra(self, municipio, projeto, **extra):
        dados = {"descricao_produto": "Kit", "quantidade": 10, "ano_uso": 2026, "created_by": self.dat_user}
        dados.update(extra)
        return DATCompra.objects.create(municipio=municipio, projeto=projeto, **dados)

    def _evento(self, municipio, projeto, status_evento="pendente"):
        inicio = timezone.now() + timedelta(days=2)
        return SolicitacaoFactory(
            usuario=self.dat_user,
            municipio=municipio,
            projeto=projeto,
            tipo_evento=TipoEventoFactory(),
            inicio=inicio,
            fim=inicio + timedelta(hours=2),
            status=status_evento,
        )

    def _pendencias(self, **params):
        self.client.force_authenticate(user=self.dat_user)
        response = self.client.get(reverse("core:dat-compra-material-pendencias"), params, secure=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.data

    def test_pendencias_action_returns_only_pairs_without_active_event(self):
        """Pendências: pares da DATCompra válida sem solicitação pendente/aprovada."""
        self._dat_compra(self.municipio, self.projeto, data_compra=date(2026, 3, 1))
        self._dat_compra(self.municipio2, self.projeto, quantidade=20, data_compra=date(2026, 3, 2))
        self._evento(self.municipio, self.projeto)

        data = self._pendencias()

        self.assertEqual(data["total_com_compra"], 2)
        self.assertEqual(data["total_com_evento"], 1)
        self.assertEqual(data["total_pendentes"], 1)
        self.assertEqual(len(data["pendentes"]), 1)
        self.assertEqual(data["pendentes"][0]["municipio"], self.municipio2.nome)
        self.assertEqual(data["pendentes"][0]["projeto"], self.projeto.nome)
        self.assertEqual(data["pendentes"][0]["total_itens"], 20)
        self.assertEqual(data["pendentes"][0]["ultima_compra"], date(2026, 3, 2))

    def test_pendencias_ignoram_a_compra_que_nao_libera(self):
        """DATCompra inativa ou com quantidade 0 não conta."""
        self._dat_compra(self.municipio2, self.projeto, ativo=False)
        self._dat_compra(self.municipio2, self.projeto, quantidade=0, ano_uso=2027)

        data = self._pendencias()

        self.assertEqual(data["total_com_compra"], 0)
        self.assertEqual(data["pendentes"], [])

    def test_pendencias_evento_de_outro_projeto_da_colecao_atende_a_compra(self):
        """Regra da compra: a compra libera a coleção inteira, então o evento da coleção a atende."""
        colecao = ProjetoGeral.objects.create(nome="Colecao Ficticia Pendencias")
        livro_1 = ProjetoFactory(nome="Ficticio Pendencias 1", projeto_geral=colecao)
        livro_2 = ProjetoFactory(nome="Ficticio Pendencias 2", projeto_geral=colecao)
        solto = ProjetoFactory(nome="Ficticio Pendencias Solto")
        self._dat_compra(self.municipio, livro_1)
        self._dat_compra(self.municipio2, solto)
        self._evento(self.municipio, livro_2, status_evento="aprovado")
        self._evento(self.municipio2, ProjetoFactory(nome="Ficticio Outro Solto"))  # sem coleção: não casa

        data = self._pendencias()

        self.assertEqual(data["total_com_compra"], 2)
        self.assertEqual(data["total_com_evento"], 1)
        self.assertEqual([p["projeto"] for p in data["pendentes"]], [solto.nome])

    def test_pendencias_evento_do_projeto_de_nome_geral_da_gerencia_atende_a_compra(self):
        """O projeto de nome geral é liberado pela compra de qualquer projeto da gerência."""
        from apps.core.models import Gerencia

        gerencia = Gerencia.objects.create(nome="G-PEND", nome_setor="Setor Pend", pergunta_avaliar_formador=False)
        comprado = ProjetoFactory(nome="Ficticio Pend Comprado", gerencia=gerencia)
        nome_geral = ProjetoFactory(nome="Ficticio Pend Geral", gerencia=gerencia, eh_nome_geral=True)
        self._dat_compra(self.municipio, comprado)
        self._evento(self.municipio, nome_geral)

        data = self._pendencias()

        self.assertEqual(data["total_com_evento"], 1)
        self.assertEqual(data["pendentes"], [])

    def test_pendencias_compra_sem_colecao_segue_pendente_com_evento_de_colecao_do_combo(self):
        """Projeto sem coleção não cai no ramo do combo: o NULL do JOIN não pode sumir com a pendência."""
        novo_lendo, _ = ProjetoGeral.objects.get_or_create(nome="NOVO LENDO")
        sem_colecao = ProjetoFactory(nome="Ficticio Pend Sem Colecao")
        self._dat_compra(self.municipio, sem_colecao)
        self._evento(self.municipio, ProjetoFactory(nome="Ficticio Pend Livro NL", projeto_geral=novo_lendo))

        data = self._pendencias()

        self.assertEqual(data["total_com_compra"], 1)
        self.assertEqual(data["total_pendentes"], 1)
        self.assertEqual(data["total_com_compra"], data["total_com_evento"] + data["total_pendentes"])
        self.assertEqual([p["projeto"] for p in data["pendentes"]], [sem_colecao.nome])

    def test_pendencias_compra_do_combo_e_atendida_por_evento_de_colecao_do_combo(self):
        """A compra do combo 'NL E AMMA PORT E MAT' libera o NOVO LENDO: o evento do livro a atende."""
        combo, _ = ProjetoGeral.objects.get_or_create(nome="NL E AMMA PORT E MAT")
        novo_lendo, _ = ProjetoGeral.objects.get_or_create(nome="NOVO LENDO")
        self._dat_compra(self.municipio, ProjetoFactory(nome="Ficticio Pend Combo", projeto_geral=combo))
        self._evento(self.municipio, ProjetoFactory(nome="Ficticio Pend Livro NL 2", projeto_geral=novo_lendo))

        data = self._pendencias()

        self.assertEqual(data["total_com_compra"], 1)
        self.assertEqual(data["total_com_evento"], 1)
        self.assertEqual(data["pendentes"], [])

    def test_pendencias_seguem_os_filtros_do_painel(self):
        """Ano de uso e tipo de compra filtram as pendências como filtram os KPIs."""
        self._dat_compra(self.municipio, self.projeto, ano_uso=2026, tipo_compra="primeira")
        self._dat_compra(self.municipio2, self.projeto, ano_uso=2027, tipo_compra="adicional_1")

        self.assertEqual([p["municipio"] for p in self._pendencias(ano_uso=2026)["pendentes"]], [self.municipio.nome])
        self.assertEqual(
            [p["municipio"] for p in self._pendencias(tipo_compra="adicional_1")["pendentes"]], [self.municipio2.nome]
        )
        self.assertEqual(self._pendencias(uf="SP")["total_com_compra"], 0)

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
        self.assertIn("detail", response.data)

    def test_etapa_action_recusa_status_e_data_invalidos(self):
        """B#44: status fora de DATCadastro.StatusEtapa ou data que não é data → 400 com mensagem."""
        self.client.force_authenticate(user=self.dat_user)
        cadastro = DATCadastro.objects.create(
            municipio=self.municipio, projeto_geral=self.projeto_geral, plataforma="FORMAR", created_by=self.dat_user
        )
        url = reverse("core:dat-cadastro-etapa", args=[cadastro.id])

        resp_status = self.client.post(url, {"etapa": "chaves", "status": "qualquer coisa"})
        resp_data = self.client.post(url, {"etapa": "chaves", "status": "concluido", "data": "15/01/2025"})

        self.assertEqual(resp_status.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Status inválido", resp_status.data["detail"])
        self.assertEqual(resp_data.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Data inválida", resp_data.data["detail"])
        cadastro.refresh_from_db()
        self.assertEqual(cadastro.status_chaves, "pendente")
        self.assertIsNone(cadastro.data_chaves)

    def test_filtro_status_etapa(self):
        """P#35: status_etapa filtra (concluído = todas as etapas da plataforma; pendente = nenhuma; resto)."""
        import uuid

        self.client.force_authenticate(user=self.dat_user)
        uid = uuid.uuid4().hex[:6]
        formar = ["status_criacao_curso", "status_chaves", "status_instrucoes", "status_envio"]
        avaliar = ["status_recebidos", "status_validados", "status_importados"]

        def cadastro(nome, plataforma, campos, valor):
            return DATCadastro.objects.create(
                municipio=MunicipioFactory(nome=f"{nome}_{uid}", uf="CE"),
                projeto_geral=self.projeto_geral,
                plataforma=plataforma,
                created_by=self.dat_user,
                **dict.fromkeys(campos, valor),
            )

        f_concluido = cadastro("FConcluido", "FORMAR", formar, "concluido")
        f_pendente = cadastro("FPendente", "FORMAR", formar, "pendente")
        f_andamento = cadastro("FAndamento", "FORMAR", formar[:1], "concluido")
        a_concluido = cadastro("AConcluido", "AVALIAR", avaliar, "concluido")
        a_pendente = cadastro("APendente", "AVALIAR", avaliar, "pendente")

        def ids(valor):
            response = self.client.get(reverse("core:dat-cadastro-list"), {"status_etapa": valor, "page_size": 50})
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            return {item["id"] for item in response.data["results"]}

        self.assertEqual(ids("concluido"), {f_concluido.id, a_concluido.id})
        self.assertEqual(ids("pendente"), {f_pendente.id, a_pendente.id})
        self.assertEqual(ids("em_andamento"), {f_andamento.id})

    def test_stats_aggregations_not_fragmented_by_listing_ordering(self):
        """Regression: same bug as DATAcao stats (PR #1361).

        DATCadastro base queryset is ordered by ("plataforma", "municipio__nome").
        Without `.order_by()` before `.values_list().annotate(Count())`, Django
        injects those columns into GROUP BY → por_plataforma fragmented.
        """
        import uuid

        self.client.force_authenticate(user=self.dat_user)

        uid = uuid.uuid4().hex[:6]
        # 6 cadastros plataforma=FORMAR, varied municipio → should yield
        # por_plataforma == {"FORMAR": 6} (not 6 distinct buckets).
        # DATCadastro has unique_together(municipio, projeto_geral, plataforma).
        for i in range(6):
            mun = MunicipioFactory(nome=f"CadastroCity_{uid}_{i}", uf="CE")
            DATCadastro.objects.create(
                municipio=mun,
                projeto_geral=self.projeto_geral,
                plataforma="FORMAR",
                created_by=self.dat_user,
            )

        url = reverse("core:dat-cadastro-stats")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        total = response.data["total"]
        self.assertEqual(total, 6)

        sum_plataforma = sum(response.data["por_plataforma"].values())
        self.assertEqual(
            sum_plataforma,
            total,
            f"por_plataforma should sum to total ({total}); got {sum_plataforma}. "
            f"Regression of ORDER BY → GROUP BY. por_plataforma={response.data['por_plataforma']!r}",
        )


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

    def test_dat_user_cannot_delete(self):
        """Sem o pacote do DAT, não exclui registros (PR 10: o DAT exclui pelo vínculo)."""
        self.client.force_authenticate(user=self.regular_user)

        acao = DATAcao.objects.create(
            municipio=self.municipio2,  # Use different municipio to avoid constraint
            projeto=self.projeto,
            created_by=self.dat_user,
        )

        response = self.client.delete(reverse("core:dat-acao-ciclo-detail", args=[acao.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
