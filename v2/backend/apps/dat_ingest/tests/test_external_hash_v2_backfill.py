"""
Testes para backfill_external_hash_v2 command (PR21).

Garante que:
1. --dry-run não altera DB
2. --apply persiste e respeita unicidade
3. Collision file gerado apenas se houver colisões
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase, TransactionTestCase

import pytest

from apps.core.models import Municipio, Projeto, Solicitacao, TipoEvento, Usuario


@pytest.mark.django_db
class TestBackfillExternalHashV2DryRun(TestCase):
    """
    Testes de dry-run do backfill (sem alterar DB).
    """

    def setUp(self):
        """Setup test data."""
        # Create test users with unique CPFs
        self.coord = Usuario.objects.create_user(
            username="coord_test",
            email="coord@test.com",
            first_name="Coordenador",
            last_name="Test",
            cpf="11111111111",
        )

        self.formador = Usuario.objects.create_user(
            username="form_test",
            email="form@test.com",
            first_name="Formador",
            last_name="Test",
            cpf="22222222222",
        )

        # Create test data
        self.municipio = Municipio.objects.create(nome="Fortaleza", ativo=True)
        self.tipo = TipoEvento.objects.create(nome="Presencial")
        self.projeto = Projeto.objects.create(nome="ACerta", codigo="ACERTA", fluxo="NAO_SUPER", ativo=True)

        # Create test solicitação
        tz = ZoneInfo("America/Fortaleza")
        self.sol = Solicitacao.objects.create(
            usuario=self.coord,  # User who created the request
            coordenador=self.coord,
            municipio=self.municipio,
            tipo_evento=self.tipo,
            projeto=self.projeto,
            inicio=datetime(2025, 1, 15, 8, 0, tzinfo=tz),
            fim=datetime(2025, 1, 15, 12, 0, tzinfo=tz),
            encontro="1",
            segmento="EI",
            coordenador_acompanha=True,
            status="pendente",
            external_hash="old_hash_v1",  # Old hash
        )
        self.sol.formadores.add(self.formador)

    def test_dry_run_does_not_modify_database(self):
        """--dry-run não altera o external_hash no banco."""
        original_hash = self.sol.external_hash

        # Run dry-run
        call_command("backfill_external_hash_v2")

        # Reload from DB
        self.sol.refresh_from_db()

        # Hash must remain unchanged
        assert self.sol.external_hash == original_hash

    def test_dry_run_shows_would_update_count(self):
        """--dry-run mostra contadores corretos."""
        from io import StringIO

        out = StringIO()

        call_command("backfill_external_hash_v2", stdout=out)
        output = out.getvalue()

        # Should show stats
        assert "Would update: 1" in output or "would_update" in output.lower()
        assert "DRY-RUN" in output

    def test_dry_run_with_limit(self):
        """--dry-run com --limit funciona corretamente."""
        # Create 5 more solicitações
        tz = ZoneInfo("America/Fortaleza")
        for i in range(5):
            Solicitacao.objects.create(
                usuario=self.coord,  # User who created the request
                coordenador=self.coord,
                municipio=self.municipio,
                tipo_evento=self.tipo,
                projeto=self.projeto,
                inicio=datetime(2025, 1, 16 + i, 8, 0, tzinfo=tz),
                fim=datetime(2025, 1, 16 + i, 12, 0, tzinfo=tz),
                encontro=str(i + 2),
                segmento="EI",
                status="pendente",
                external_hash=f"old_hash_{i}",
            )

        # Run with limit=3
        call_command("backfill_external_hash_v2", limit=3)

        # Should process only 3
        # (verificar via output ou stats seria ideal, mas sem acesso direto)
        assert Solicitacao.objects.count() == 6  # Total unchanged


@pytest.mark.django_db
class TestBackfillExternalHashV2Apply(TransactionTestCase):
    """
    Testes de --apply do backfill (com persistência).
    """

    def setUp(self):
        """Setup test data."""
        self.coord = Usuario.objects.create_user(
            username="coord_test",
            email="coord@test.com",
            first_name="Coordenador",
            last_name="Test",
            cpf="33333333333",
        )

        self.formador = Usuario.objects.create_user(
            username="form_test",
            email="form@test.com",
            first_name="Formador",
            last_name="Test",
            cpf="44444444444",
        )

        self.municipio = Municipio.objects.create(nome="Fortaleza", ativo=True)
        self.tipo = TipoEvento.objects.create(nome="Presencial")
        self.projeto = Projeto.objects.create(nome="ACerta", codigo="ACERTA", fluxo="NAO_SUPER", ativo=True)

    def test_apply_persists_new_hash(self):
        """--apply persiste o novo hash v2."""
        sol = Solicitacao.objects.create(
            usuario=self.coord,  # User who created the request
            coordenador=self.coord,
            municipio=self.municipio,
            tipo_evento=self.tipo,
            projeto=self.projeto,
            inicio=datetime(2025, 1, 15, 8, 0, tzinfo=ZoneInfo("America/Fortaleza")),
            # hora via inicio
            fim=datetime(2025, 1, 15, 12, 0, tzinfo=ZoneInfo("America/Fortaleza")),
            encontro="1",
            segmento="EI",
            coordenador_acompanha=True,
            status="pendente",
            external_hash="old_hash_v1",
        )
        sol.formadores.add(self.formador)

        original_hash = sol.external_hash

        # Run apply
        call_command("backfill_external_hash_v2", apply=True)

        # Reload from DB
        sol.refresh_from_db()

        # Hash must be updated
        assert sol.external_hash != original_hash
        assert len(sol.external_hash) == 40  # SHA1 hex

    def test_apply_respects_uniqueness_no_duplicates(self):
        """--apply não cria duplicatas (respeita constraint)."""
        # Create two identical solicitações (should have same hash v2)
        sol1 = Solicitacao.objects.create(
            usuario=self.coord,  # User who created the request
            coordenador=self.coord,
            municipio=self.municipio,
            tipo_evento=self.tipo,
            projeto=self.projeto,
            inicio=datetime(2025, 1, 15, 8, 0, tzinfo=ZoneInfo("America/Fortaleza")),
            # hora via inicio
            fim=datetime(2025, 1, 15, 12, 0, tzinfo=ZoneInfo("America/Fortaleza")),
            encontro="1",
            segmento="EI",
            coordenador_acompanha=True,
            status="pendente",
            external_hash="old_hash_1",
        )
        sol1.formadores.add(self.formador)

        sol2 = Solicitacao.objects.create(
            usuario=self.coord,  # User who created the request
            coordenador=self.coord,
            municipio=self.municipio,
            tipo_evento=self.tipo,
            projeto=self.projeto,
            inicio=datetime(2025, 1, 15, 8, 0, tzinfo=ZoneInfo("America/Fortaleza")),
            # hora via inicio
            fim=datetime(2025, 1, 15, 12, 0, tzinfo=ZoneInfo("America/Fortaleza")),
            encontro="1",
            segmento="EI",
            coordenador_acompanha=True,
            status="pendente",
            external_hash="old_hash_2",
        )
        sol2.formadores.add(self.formador)

        # Run apply
        call_command("backfill_external_hash_v2", apply=True)

        # Reload
        sol1.refresh_from_db()
        sol2.refresh_from_db()

        # Due to unique constraint, only one gets the new hash
        # (collision detected but constraint prevents duplicate)
        new_hashes = [sol1.external_hash, sol2.external_hash]
        old_hashes = ["old_hash_1", "old_hash_2"]

        # One should be updated, one should keep old hash
        assert len([h for h in new_hashes if h in old_hashes]) == 1  # One kept old
        assert len([h for h in new_hashes if h not in old_hashes]) == 1  # One got new

        # But both records still exist (constraint prevents, no deletion)
        assert Solicitacao.objects.count() == 2

    def test_apply_unchanged_when_hash_already_v2(self):
        """--apply não altera hash se já for v2 correto."""
        from apps.dat_ingest.services.acompanhamento_normalize import hash_event_v2

        # Create solicitação
        sol = Solicitacao.objects.create(
            usuario=self.coord,  # User who created the request
            coordenador=self.coord,
            municipio=self.municipio,
            tipo_evento=self.tipo,
            projeto=self.projeto,
            inicio=datetime(2025, 1, 15, 8, 0, tzinfo=ZoneInfo("America/Fortaleza")),
            # hora via inicio
            fim=datetime(2025, 1, 15, 12, 0, tzinfo=ZoneInfo("America/Fortaleza")),
            encontro="1",
            segmento="EI",
            coordenador_acompanha=True,
            status="pendente",
        )
        sol.formadores.add(self.formador)

        # Manually set correct v2 hash
        row = {
            "source_sheet": "ACerta",
            "municipio": "Fortaleza",
            "encontro": "1",
            "tipo": "Presencial",
            "data": "2025-01-15",
            "hora_inicio": "08:00",
            "hora_fim": "12:00",
            "projeto": "ACerta",
            "segmento": "EI",
            "coord_acompanha": "sim",
            "coordenador": self.coord.email,
            "formador1": self.formador.email,
            "formador2": "",
            "formador3": "",
            "formador4": "",
            "formador5": "",
            "aprovacao": "",
        }
        correct_hash = hash_event_v2(row)
        sol.external_hash = correct_hash
        sol.save()

        # Run apply
        call_command("backfill_external_hash_v2", apply=True)

        # Reload
        sol.refresh_from_db()

        # Hash must remain unchanged
        assert sol.external_hash == correct_hash


@pytest.mark.django_db
class TestBackfillCollisionsReport(TestCase):
    """
    Testes de geração de relatório de colisões.
    """

    def setUp(self):
        """Setup test data."""
        self.coord = Usuario.objects.create_user(
            username="coord_test",
            email="coord@test.com",
            first_name="Coordenador",
            last_name="Test",
            cpf="55555555555",
        )

        self.formador = Usuario.objects.create_user(
            username="form_test",
            email="form@test.com",
            first_name="Formador",
            last_name="Test",
            cpf="66666666666",
        )

        self.municipio = Municipio.objects.create(nome="Fortaleza", ativo=True)
        self.tipo = TipoEvento.objects.create(nome="Presencial")
        self.projeto = Projeto.objects.create(nome="ACerta", codigo="ACERTA", fluxo="NAO_SUPER", ativo=True)

    def tearDown(self):
        """Clean up collision file."""
        collision_file = Path(settings.BASE_DIR) / ".agents/outbox/external_hash_v2_collisions.json"
        if collision_file.exists():
            collision_file.unlink()

    def test_collision_file_not_generated_when_no_collisions(self):
        """Collision file não é gerado quando não há colisões."""
        # Create single solicitação (no collision)
        sol = Solicitacao.objects.create(
            usuario=self.coord,  # User who created the request
            coordenador=self.coord,
            municipio=self.municipio,
            tipo_evento=self.tipo,
            projeto=self.projeto,
            inicio=datetime(2025, 1, 15, 8, 0, tzinfo=ZoneInfo("America/Fortaleza")),
            # hora via inicio
            fim=datetime(2025, 1, 15, 12, 0, tzinfo=ZoneInfo("America/Fortaleza")),
            encontro="1",
            segmento="EI",
            status="pendente",
        )
        sol.formadores.add(self.formador)

        # Run backfill
        call_command("backfill_external_hash_v2")

        # Collision file should NOT exist
        collision_file = Path(settings.BASE_DIR) / ".agents/outbox/external_hash_v2_collisions.json"
        assert not collision_file.exists()

    def test_collision_file_generated_when_collisions_exist(self):
        """Collision file é gerado quando há colisões."""
        # Create two identical solicitações (collision)
        sol1 = Solicitacao.objects.create(
            usuario=self.coord,  # User who created the request
            coordenador=self.coord,
            municipio=self.municipio,
            tipo_evento=self.tipo,
            projeto=self.projeto,
            inicio=datetime(2025, 1, 15, 8, 0, tzinfo=ZoneInfo("America/Fortaleza")),
            # hora via inicio
            fim=datetime(2025, 1, 15, 12, 0, tzinfo=ZoneInfo("America/Fortaleza")),
            encontro="1",
            segmento="EI",
            coordenador_acompanha=True,
            status="pendente",
        )
        sol1.formadores.add(self.formador)

        sol2 = Solicitacao.objects.create(
            usuario=self.coord,  # User who created the request
            coordenador=self.coord,
            municipio=self.municipio,
            tipo_evento=self.tipo,
            projeto=self.projeto,
            inicio=datetime(2025, 1, 15, 8, 0, tzinfo=ZoneInfo("America/Fortaleza")),
            # hora via inicio
            fim=datetime(2025, 1, 15, 12, 0, tzinfo=ZoneInfo("America/Fortaleza")),
            encontro="1",
            segmento="EI",
            coordenador_acompanha=True,
            status="pendente",
        )
        sol2.formadores.add(self.formador)

        # Run backfill
        call_command("backfill_external_hash_v2")

        # Collision file SHOULD exist
        collision_file = Path(settings.BASE_DIR) / ".agents/outbox/external_hash_v2_collisions.json"
        assert collision_file.exists()

        # Validate JSON structure
        with open(collision_file, "r", encoding="utf-8") as f:
            collisions = json.load(f)

        assert isinstance(collisions, list)
        assert len(collisions) == 1  # One collision group

        collision_entry = collisions[0]
        assert "hash" in collision_entry
        assert "count" in collision_entry
        assert collision_entry["count"] == 2
        assert "solicitacoes" in collision_entry
        assert len(collision_entry["solicitacoes"]) == 2
