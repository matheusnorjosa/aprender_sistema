"""
Testes para parser parse_fluir.py.

Valida:
- Estrutura de retorno
- Timezone awareness
- Geração de external_hash
- Tratamento de erros
"""


from __future__ import annotations
import pytest
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from django.conf import settings

from apps.dat_ingest.services.parse_fluir import parse_fluir_eventos, get_formadores_fluir


# Path to Fluir file (either Docker /app or CI path)
FLUIR_FILE = Path(settings.BASE_DIR).parent / "data" / "csv-import" / "Acompanhamento de Agenda _ Fluir (1).xlsx"


class TestParseFluir:
    """Testes para função parse_fluir_eventos()."""

    def test_get_formadores_fluir_returns_9(self) -> None:
        """Deve retornar lista com 9 formadores."""
        formadores = get_formadores_fluir()

        assert isinstance(formadores, list)
        assert len(formadores) == 9
        assert all(isinstance(nome, str) for nome in formadores)

    def test_parse_fluir_file_not_found(self) -> None:
        """Deve lançar FileNotFoundError se planilha não existir."""
        filepath = Path("/nonexistent/path/file.xlsx")

        with pytest.raises(FileNotFoundError):
            parse_fluir_eventos(filepath)

    @pytest.mark.skipif(
        not FLUIR_FILE.exists(),
        reason="Planilha Fluir não encontrada",
    )
    def test_parse_fluir_eventos_structure(self) -> None:
        """Deve retornar lista de dicts com estrutura correta."""
        filepath = FLUIR_FILE

        eventos = parse_fluir_eventos(filepath)

        assert isinstance(eventos, list)
        assert len(eventos) > 0, "Deve retornar ao menos 1 evento"

        # Validar estrutura do primeiro evento
        evento = eventos[0]
        required_keys = [
            "municipio_nome_uf",
            "projeto_nome",
            "tipo",
            "encontro",
            "inicio",
            "fim",
            "formadores",
            "tema",
            "turma",
            "is_online",
            "status",
            "src",
            "external_hash",
        ]

        for key in required_keys:
            assert key in evento, f"Campo obrigatório '{key}' ausente"

        # Validar tipos
        assert isinstance(evento["inicio"], datetime)
        assert isinstance(evento["fim"], datetime)
        assert isinstance(evento["formadores"], list)
        assert len(evento["formadores"]) == 1  # Fluir tem 1 formador por evento
        assert evento["projeto_nome"] == "FLUIR DAS EMOÇÕES"
        assert evento["src"] == "fluir/Acompanhamento"

    @pytest.mark.skipif(
        not FLUIR_FILE.exists(),
        reason="Planilha Fluir não encontrada",
    )
    def test_parse_fluir_timezone_aware(self) -> None:
        """Deve retornar datetimes timezone-aware (America/Fortaleza)."""
        filepath = FLUIR_FILE

        eventos = parse_fluir_eventos(filepath)

        assert len(eventos) > 0

        evento = eventos[0]
        assert evento["inicio"].tzinfo is not None, "inicio deve ser timezone-aware"
        assert evento["fim"].tzinfo is not None, "fim deve ser timezone-aware"

        # Verificar que é America/Fortaleza
        fortaleza_tz = ZoneInfo("America/Fortaleza")
        assert evento["inicio"].tzinfo == fortaleza_tz or str(evento["inicio"].tzinfo) == "America/Fortaleza"

    @pytest.mark.skipif(
        not FLUIR_FILE.exists(),
        reason="Planilha Fluir não encontrada",
    )
    def test_parse_fluir_external_hash_uniqueness(self) -> None:
        """Deve gerar external_hash único para cada evento."""
        filepath = FLUIR_FILE

        eventos = parse_fluir_eventos(filepath)

        assert len(eventos) > 0

        # Verificar que hashes são strings hexadecimais de 40 chars (SHA1)
        for evento in eventos:
            hash_val = evento["external_hash"]
            assert isinstance(hash_val, str)
            assert len(hash_val) == 40
            assert all(c in "0123456789abcdef" for c in hash_val.lower())

        # Verificar que não há duplicatas (assumindo eventos únicos)
        hashes = [e["external_hash"] for e in eventos]
        assert len(hashes) == len(set(hashes)), "Hashes devem ser únicos"
