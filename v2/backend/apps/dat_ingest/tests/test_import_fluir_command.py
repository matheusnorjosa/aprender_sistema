"""
Testes para command import_fluir_eventos.

Valida:
- Dry-run mode (não persiste)
- Apply mode (persiste)
- Idempotência (external_hash)
- Quality gates (min eventos, formadores, projeto)
"""


from __future__ import annotations
import pytest
from io import StringIO
from unittest.mock import patch, MagicMock
from datetime import datetime
from zoneinfo import ZoneInfo

from django.core.management import call_command
from django.contrib.auth.models import Group

from apps.core.models import Solicitacao, Projeto, Municipio, Usuario, Participation, TipoEvento


@pytest.mark.django_db
class TestImportFluirCommand:
    """Testes para command import_fluir_eventos."""

    @pytest.fixture
    def setup_data(self) -> dict:
        """Setup dados necessários para testes."""
        # Criar tipo de evento
        tipo_evento = TipoEvento.objects.create(
            nome="Evento Teste",
        )

        # Criar projeto Fluir
        projeto = Projeto.objects.create(
            nome="FLUIR DAS EMOÇÕES",
            fluxo="NAO_SUPER",
            ativo=True,
        )

        # Criar município
        municipio = Municipio.objects.create(
            nome="Cubatão",
            uf="SP",
            ativo=True,
        )

        # Criar TODOS os 9 formadores Fluir (Gate 3 exige)
        grupo_formador, _ = Group.objects.get_or_create(name="Formador")
        formadores_nomes = [
            "Adeliana Mówima Falcao Machado",
            "Fernanda Matthews Jucá",
            "Janaína Bezerra de Aquino Faria",
            "Jennifer Kerolly de Oliveira Barros Bathaus",
            "Juliana Cruz Maciel",
            "Jéssica Nunes Apolonio",
            "Natália de Araújo Loiola",
            "Priscilla Laysa Mota Pereira",
            "Talitha Lousada Teixeira",
        ]

        formadores = []
        for idx, nome_completo in enumerate(formadores_nomes, 1):
            # Normalizar username
            username = self._normalize_username(nome_completo)
            formador = Usuario.objects.create(
                username=username,
                cpf=f"999{idx:08d}",
                email=f"{username}@aprender.local",
                first_name=nome_completo.split()[0],
                last_name=" ".join(nome_completo.split()[1:]),
                cargo="Formador",
            )
            formador.groups.add(grupo_formador)
            formadores.append(formador)

        return {
            "tipo_evento": tipo_evento,
            "projeto": projeto,
            "municipio": municipio,
            "formador": formadores[1],  # Fernanda (índice 1)
        }

    def _normalize_username(self, nome_completo: str) -> str:
        """Normaliza nome completo para username."""
        import unicodedata
        nome_sem_acento = "".join(
            c for c in unicodedata.normalize("NFD", nome_completo)
            if unicodedata.category(c) != "Mn"
        )
        username = nome_sem_acento.lower().replace(" ", "_")
        return username

    def test_command_requires_mode_flag(self) -> None:
        """Deve exigir --dry-run ou --apply."""
        out = StringIO()

        with patch("apps.dat_ingest.management.commands.import_fluir_eventos.parse_fluir_eventos"):
            call_command("import_fluir_eventos", stdout=out, stderr=out)

        output = out.getvalue()
        assert "ERRO" in output or "Especifique" in output

    @patch("apps.dat_ingest.management.commands.import_fluir_eventos.parse_fluir_eventos")
    def test_command_dry_run_does_not_persist(self, mock_parse: MagicMock, setup_data: dict) -> None:
        """Dry-run não deve criar registros no banco."""
        # Mock parse retorna 1 evento
        mock_evento = {
            "municipio_nome_uf": "Cubatão-SP",
            "projeto_nome": "FLUIR DAS EMOÇÕES",
            "tipo": "evento",
            "encontro": "1",
            "inicio": datetime(2025, 1, 15, 14, 0, tzinfo=ZoneInfo("America/Fortaleza")),
            "fim": datetime(2025, 1, 15, 17, 0, tzinfo=ZoneInfo("America/Fortaleza")),
            "formadores": ["Fernanda Matthews Jucá"],
            "tema": "Tema teste",
            "turma": "Turma A",
            "is_online": False,
            "status": "aprovado",
            "src": "fluir/Acompanhamento",
            "external_hash": "abc123def456",
        }
        mock_parse.return_value = [mock_evento]

        # Contar registros antes
        count_before = Solicitacao.objects.count()

        out = StringIO()
        call_command("import_fluir_eventos", "--dry-run", "--min-eventos=1", stdout=out, stderr=out)

        # Não deve ter criado nada
        count_after = Solicitacao.objects.count()
        assert count_after == count_before, "Dry-run não deve persistir"

        output = out.getvalue()
        assert "DRY-RUN" in output

    @patch("apps.dat_ingest.management.commands.import_fluir_eventos.parse_fluir_eventos")
    def test_command_apply_creates_solicitacao(self, mock_parse: MagicMock, setup_data: dict) -> None:
        """Apply deve criar Solicitacao no banco."""
        # Mock parse retorna 1 evento
        mock_evento = {
            "municipio_nome_uf": "Cubatão-SP",
            "projeto_nome": "FLUIR DAS EMOÇÕES",
            "tipo": "evento",
            "encontro": "1",
            "inicio": datetime(2025, 1, 15, 14, 0, tzinfo=ZoneInfo("America/Fortaleza")),
            "fim": datetime(2025, 1, 15, 17, 0, tzinfo=ZoneInfo("America/Fortaleza")),
            "formadores": ["Fernanda Matthews Jucá"],
            "tema": "Tema teste",
            "turma": "Turma A",
            "is_online": False,
            "status": "aprovado",
            "src": "fluir/Acompanhamento",
            "external_hash": "abc123def456",
        }
        mock_parse.return_value = [mock_evento]

        # Contar registros antes
        count_before = Solicitacao.objects.count()

        out = StringIO()
        call_command("import_fluir_eventos", "--apply", "--min-eventos=1", stdout=out, stderr=out)

        # Deve ter criado 1 registro
        count_after = Solicitacao.objects.count()
        assert count_after == count_before + 1, "Apply deve criar 1 Solicitacao"

        # Verificar dados
        solicitacao = Solicitacao.objects.get(external_hash="abc123def456")
        assert solicitacao.projeto.nome == "FLUIR DAS EMOÇÕES"
        assert solicitacao.municipio.nome == "Cubatão"
        assert solicitacao.status == "aprovado"

        # Verificar Participation
        assert Participation.objects.filter(solicitacao=solicitacao).count() == 1

    @patch("apps.dat_ingest.management.commands.import_fluir_eventos.parse_fluir_eventos")
    def test_command_idempotence_skips_duplicates(self, mock_parse: MagicMock, setup_data: dict) -> None:
        """Deve pular eventos duplicados (mesmo external_hash)."""
        # Criar evento manualmente
        solicitacao_existente = Solicitacao.objects.create(
            usuario=setup_data["formador"],
            projeto=setup_data["projeto"],
            municipio=setup_data["municipio"],
            tipo_evento=setup_data["tipo_evento"],
            status="aprovado",
            inicio=datetime(2025, 1, 15, 14, 0, tzinfo=ZoneInfo("America/Fortaleza")),
            fim=datetime(2025, 1, 15, 17, 0, tzinfo=ZoneInfo("America/Fortaleza")),
            external_hash="duplicate_hash_123",
        )

        # Mock parse retorna evento com mesmo hash
        mock_evento = {
            "municipio_nome_uf": "Cubatão-SP",
            "projeto_nome": "FLUIR DAS EMOÇÕES",
            "tipo": "evento",
            "encontro": "1",
            "inicio": datetime(2025, 1, 15, 14, 0, tzinfo=ZoneInfo("America/Fortaleza")),
            "fim": datetime(2025, 1, 15, 17, 0, tzinfo=ZoneInfo("America/Fortaleza")),
            "formadores": ["Fernanda Matthews Jucá"],
            "tema": "Tema teste",
            "turma": "Turma A",
            "is_online": False,
            "status": "aprovado",
            "src": "fluir/Acompanhamento",
            "external_hash": "duplicate_hash_123",  # Mesmo hash!
        }
        mock_parse.return_value = [mock_evento]

        count_before = Solicitacao.objects.count()

        out = StringIO()
        call_command("import_fluir_eventos", "--apply", "--min-eventos=1", stdout=out, stderr=out)

        # Não deve ter criado novo registro
        count_after = Solicitacao.objects.count()
        assert count_after == count_before, "Não deve criar duplicata"

        output = out.getvalue()
        assert "skipped" in output.lower() or "existe" in output.lower()

    @patch("apps.dat_ingest.management.commands.import_fluir_eventos.parse_fluir_eventos")
    def test_command_quality_gate_min_eventos(self, mock_parse: MagicMock, setup_data: dict) -> None:
        """Deve abortar se menos de min_eventos."""
        # Mock retorna apenas 50 eventos (menos que threshold default 100)
        mock_parse.return_value = [{"fake": "data"}] * 50

        out = StringIO()
        call_command("import_fluir_eventos", "--dry-run", stdout=out, stderr=out)

        output = out.getvalue()
        assert "GATE 1 FALHOU" in output or "Menos de" in output

    def test_command_quality_gate_projeto_missing(self) -> None:
        """Deve abortar se projeto 'FLUIR DAS EMOÇÕES' não existir."""
        # Garantir que projeto não existe
        Projeto.objects.filter(nome="FLUIR DAS EMOÇÕES").delete()

        with patch("apps.dat_ingest.management.commands.import_fluir_eventos.parse_fluir_eventos") as mock_parse:
            mock_parse.return_value = [{"fake": "data"}] * 100

            out = StringIO()
            call_command("import_fluir_eventos", "--dry-run", stdout=out, stderr=out)

            output = out.getvalue()
            assert "GATE 2 FALHOU" in output or "não existe" in output
