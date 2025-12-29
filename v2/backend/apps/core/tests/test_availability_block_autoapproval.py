"""
Testes para auto-aprovação de AvailabilityBlock.

Issue #246: Garantir cobertura de teste para o comportamento de auto-aprovação
do AvailabilityBlock.save() method.

Comportamento documentado:
- AvailabilityBlock SEMPRE auto-aprova quando status='pendente' (criação OU atualização)
- Diferente de Solicitacao SUPER que nunca auto-aprova (PA-01)
- Bloqueios são informações factuais do formador, não requerem aprovação gerencial
"""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.core.models import (
    AvailabilityBlock,
    Municipio,
    Projeto,
    Solicitacao,
    TipoEvento,
    Usuario,
)


class TestAvailabilityBlockAutoApproval(TestCase):
    """Testes para comportamento de auto-aprovação de AvailabilityBlock."""

    def setUp(self) -> None:
        """Create test fixtures."""
        self.formador = Usuario.objects.create_user(
            username="formador_block_test",
            email="formador_block@test.com",
            password="testpass123",
        )

    def test_availability_block_auto_approves_on_create(self) -> None:
        """Verifica que AvailabilityBlock é auto-aprovado na criação."""
        inicio = timezone.now() + timedelta(days=1)
        fim = inicio + timedelta(hours=4)

        # Criar com status explicitamente pendente
        bloco = AvailabilityBlock.objects.create(
            usuario=self.formador,
            tipo="T",
            inicio=inicio,
            fim=fim,
            status="pendente",
        )

        self.assertEqual(
            bloco.status,
            "aprovado",
            f"Deveria auto-aprovar na criação, mas status é {bloco.status}",
        )

    def test_availability_block_auto_approves_on_update(self) -> None:
        """Verifica que AvailabilityBlock auto-aprova também no update.

        O comportamento do model é: SEMPRE que status='pendente', converte para 'aprovado'.
        Isso se aplica tanto a criação quanto a atualização.

        Razão: Bloqueios são informações factuais - o formador SABE quando está
        indisponível. Não faz sentido ter bloqueio "pendente de aprovação".
        """
        inicio = timezone.now() + timedelta(days=3)
        fim = inicio + timedelta(hours=3)

        bloco = AvailabilityBlock.objects.create(
            usuario=self.formador,
            tipo="T",
            inicio=inicio,
            fim=fim,
        )
        self.assertEqual(bloco.status, "aprovado")

        # Tentar forçar status para pendente via update_fields bypass
        AvailabilityBlock.objects.filter(pk=bloco.pk).update(status="pendente")
        bloco.refresh_from_db()
        self.assertEqual(bloco.status, "pendente", "update() direto deve permitir pendente")

        # Mas ao chamar save(), deve auto-aprovar novamente
        bloco.save()
        self.assertEqual(
            bloco.status,
            "aprovado",
            "save() deve auto-aprovar mesmo em update",
        )

    def test_availability_block_differs_from_solicitacao_super(self) -> None:
        """Documenta diferença intencional: Block auto-aprova, Solicitacao SUPER não.

        Essa diferença existe porque:
        - Solicitacao SUPER: Requer aprovação gerencial (PA-01 a PA-07)
        - AvailabilityBlock: Informação factual do formador, não precisa aprovação
        """
        projeto_super = Projeto.objects.create(nome="Test SUPER Project", fluxo="SUPER")
        municipio = Municipio.objects.create(nome="Test City Block", uf="CE")
        tipo_evento = TipoEvento.objects.create(nome="Formação Block Test")

        inicio = timezone.now() + timedelta(days=4)
        fim = inicio + timedelta(hours=4)

        # Solicitacao SUPER NÃO auto-aprova
        solicitacao = Solicitacao.objects.create(
            usuario=self.formador,
            projeto=projeto_super,
            municipio=municipio,
            tipo_evento=tipo_evento,
            inicio=inicio,
            fim=fim,
        )

        # AvailabilityBlock SEMPRE auto-aprova
        bloco = AvailabilityBlock.objects.create(
            usuario=self.formador,
            tipo="T",
            inicio=inicio + timedelta(days=1),
            fim=fim + timedelta(days=1),
            status="pendente",
        )

        # Comportamentos diferentes por design
        self.assertEqual(
            solicitacao.status,
            "pendente",
            "Solicitacao SUPER NÃO deve auto-aprovar (PA-01)",
        )
        self.assertEqual(
            bloco.status,
            "aprovado",
            "AvailabilityBlock DEVE auto-aprovar (informação factual)",
        )
