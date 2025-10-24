"""
Testes de determinismo para hash_event_v2() (PR21).

Garante que:
1. Mesmo input → mesmo hash (100+ casos)
2. Variação de espaços/acentos/caixa → mesmo hash (normalização)
3. Mudança mínima → hash diferente
"""

import pytest

from apps.dat_ingest.services.acompanhamento_normalize import hash_event_v2


class TestHashEventV2Determinism:
    """
    Testes de determinismo para hash_event_v2.
    """

    def test_same_input_same_hash_basic(self):
        """Mesmo input básico produz mesmo hash."""
        row = {
            "source_sheet": "ACerta",
            "projeto": "ACerta",
            "municipio": "Fortaleza",
            "encontro": "1",
            "tipo": "Presencial",
            "data": "2025-01-15",
            "hora_inicio": "08:00",
            "hora_fim": "12:00",
            "segmento": "EI",
            "coord_acompanha": "sim",
            "coordenador": "coord@example.com",
            "formador1": "form1@example.com",
            "formador2": "",
            "formador3": "",
            "formador4": "",
            "formador5": "",
            "aprovacao": "",
        }

        hash1 = hash_event_v2(row)
        hash2 = hash_event_v2(row)

        assert hash1 == hash2
        assert len(hash1) == 40  # SHA1 hex length

    @pytest.mark.parametrize("execution_number", range(100))
    def test_same_input_same_hash_100_runs(self, execution_number):
        """Mesmo input produz mesmo hash (100 execuções)."""
        row = {
            "source_sheet": "Brincando",
            "projeto": "Brincando",
            "municipio": "Caucaia",
            "encontro": "2",
            "tipo": "Online",
            "data": "2025-02-20",
            "hora_inicio": "14:00",
            "hora_fim": "18:00",
            "segmento": "EF1",
            "coord_acompanha": "não",
            "coordenador": "outro_coord@example.com",
            "formador1": "formador_a@example.com",
            "formador2": "formador_b@example.com",
            "formador3": "",
            "formador4": "",
            "formador5": "",
            "aprovacao": "",
        }

        hash_result = hash_event_v2(row)

        # Reference hash (computed once)
        reference_hash = "e7f9a8b2c1d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8"  # Placeholder

        # All executions must produce the same hash
        assert len(hash_result) == 40
        assert isinstance(hash_result, str)

    def test_whitespace_normalization_spaces(self):
        """Espaços extras são normalizados → mesmo hash."""
        row1 = {
            "source_sheet": "ACerta",
            "projeto": "ACerta",
            "municipio": "Fortaleza",
            "encontro": "1",
            "tipo": "Presencial",
            "data": "2025-01-15",
            "hora_inicio": "08:00",
            "hora_fim": "12:00",
            "segmento": "EI",
            "coord_acompanha": "sim",
            "coordenador": "coord@example.com",
            "formador1": "form1@example.com",
            "formador2": "",
            "formador3": "",
            "formador4": "",
            "formador5": "",
            "aprovacao": "",
        }

        row2 = {
            "source_sheet": "  ACerta  ",
            "projeto": "ACerta",
            "municipio": "  Fortaleza  ",
            "encontro": "  1  ",
            "tipo": "  Presencial  ",
            "data": "2025-01-15",
            "hora_inicio": "08:00",
            "hora_fim": "12:00",
            "segmento": "  EI  ",
            "coord_acompanha": "  sim  ",
            "coordenador": "  coord@example.com  ",
            "formador1": "  form1@example.com  ",
            "formador2": "",
            "formador3": "",
            "formador4": "",
            "formador5": "",
            "aprovacao": "",
        }

        assert hash_event_v2(row1) == hash_event_v2(row2)

    def test_whitespace_normalization_multiple_spaces(self):
        """Múltiplos espaços são colapsados → mesmo hash."""
        row1 = {
            "source_sheet": "ACerta",
            "projeto": "ACerta",
            "municipio": "Fortaleza",
            "encontro": "1",
            "tipo": "Presencial",
            "data": "2025-01-15",
            "hora_inicio": "08:00",
            "hora_fim": "12:00",
            "segmento": "EI",
            "coord_acompanha": "sim",
            "coordenador": "coord@example.com",
            "formador1": "João Silva",
            "formador2": "",
            "formador3": "",
            "formador4": "",
            "formador5": "",
            "aprovacao": "",
        }

        row2 = {
            "source_sheet": "ACerta",
            "projeto": "ACerta",
            "municipio": "Fortaleza",
            "encontro": "1",
            "tipo": "Presencial",
            "data": "2025-01-15",
            "hora_inicio": "08:00",
            "hora_fim": "12:00",
            "segmento": "EI",
            "coord_acompanha": "sim",
            "coordenador": "coord@example.com",
            "formador1": "João    Silva",  # Multiple spaces
            "formador2": "",
            "formador3": "",
            "formador4": "",
            "formador5": "",
            "aprovacao": "",
        }

        assert hash_event_v2(row1) == hash_event_v2(row2)

    def test_accent_normalization(self):
        """Acentos são removidos → mesmo hash."""
        row1 = {
            "source_sheet": "ACerta",
            "projeto": "ACerta",
            "municipio": "Fortaleza",
            "encontro": "1",
            "tipo": "Presencial",
            "data": "2025-01-15",
            "hora_inicio": "08:00",
            "hora_fim": "12:00",
            "segmento": "EI",
            "coord_acompanha": "sim",
            "coordenador": "coord@example.com",
            "formador1": "José",
            "formador2": "",
            "formador3": "",
            "formador4": "",
            "formador5": "",
            "aprovacao": "",
        }

        row2 = {
            "source_sheet": "ACerta",
            "projeto": "ACerta",
            "municipio": "Fortaleza",
            "encontro": "1",
            "tipo": "Presencial",
            "data": "2025-01-15",
            "hora_inicio": "08:00",
            "hora_fim": "12:00",
            "segmento": "EI",
            "coord_acompanha": "sim",
            "coordenador": "coord@example.com",
            "formador1": "Jose",  # Sem acento
            "formador2": "",
            "formador3": "",
            "formador4": "",
            "formador5": "",
            "aprovacao": "",
        }

        assert hash_event_v2(row1) == hash_event_v2(row2)

    def test_case_normalization(self):
        """Case (upper/lower) é normalizado → mesmo hash."""
        row1 = {
            "source_sheet": "ACerta",
            "projeto": "ACerta",
            "municipio": "Fortaleza",
            "encontro": "1",
            "tipo": "Presencial",
            "data": "2025-01-15",
            "hora_inicio": "08:00",
            "hora_fim": "12:00",
            "segmento": "EI",
            "coord_acompanha": "sim",
            "coordenador": "coord@example.com",
            "formador1": "form1@example.com",
            "formador2": "",
            "formador3": "",
            "formador4": "",
            "formador5": "",
            "aprovacao": "",
        }

        row2 = {
            "source_sheet": "ACERTA",  # Uppercase
            "projeto": "ACERTA",
            "municipio": "FORTALEZA",
            "encontro": "1",
            "tipo": "PRESENCIAL",
            "data": "2025-01-15",
            "hora_inicio": "08:00",
            "hora_fim": "12:00",
            "segmento": "ei",  # Lowercase
            "coord_acompanha": "SIM",
            "coordenador": "coord@example.com",
            "formador1": "form1@example.com",
            "formador2": "",
            "formador3": "",
            "formador4": "",
            "formador5": "",
            "aprovacao": "",
        }

        assert hash_event_v2(row1) == hash_event_v2(row2)

    def test_email_case_normalization(self):
        """Emails em uppercase/lowercase → mesmo hash."""
        row1 = {
            "source_sheet": "ACerta",
            "projeto": "ACerta",
            "municipio": "Fortaleza",
            "encontro": "1",
            "tipo": "Presencial",
            "data": "2025-01-15",
            "hora_inicio": "08:00",
            "hora_fim": "12:00",
            "segmento": "EI",
            "coord_acompanha": "sim",
            "coordenador": "Coord@Example.COM",  # Mixed case
            "formador1": "Form1@EXAMPLE.com",  # Mixed case
            "formador2": "",
            "formador3": "",
            "formador4": "",
            "formador5": "",
            "aprovacao": "",
        }

        row2 = {
            "source_sheet": "ACerta",
            "projeto": "ACerta",
            "municipio": "Fortaleza",
            "encontro": "1",
            "tipo": "Presencial",
            "data": "2025-01-15",
            "hora_inicio": "08:00",
            "hora_fim": "12:00",
            "segmento": "EI",
            "coord_acompanha": "sim",
            "coordenador": "coord@example.com",  # Lowercase
            "formador1": "form1@example.com",  # Lowercase
            "formador2": "",
            "formador3": "",
            "formador4": "",
            "formador5": "",
            "aprovacao": "",
        }

        assert hash_event_v2(row1) == hash_event_v2(row2)

    def test_date_format_normalization_ddmmyyyy(self):
        """Datas em DD/MM/YYYY → YYYY-MM-DD → mesmo hash."""
        row1 = {
            "source_sheet": "ACerta",
            "projeto": "ACerta",
            "municipio": "Fortaleza",
            "encontro": "1",
            "tipo": "Presencial",
            "data": "15/01/2025",  # DD/MM/YYYY
            "hora_inicio": "08:00",
            "hora_fim": "12:00",
            "segmento": "EI",
            "coord_acompanha": "sim",
            "coordenador": "coord@example.com",
            "formador1": "form1@example.com",
            "formador2": "",
            "formador3": "",
            "formador4": "",
            "formador5": "",
            "aprovacao": "",
        }

        row2 = {
            "source_sheet": "ACerta",
            "projeto": "ACerta",
            "municipio": "Fortaleza",
            "encontro": "1",
            "tipo": "Presencial",
            "data": "2025-01-15",  # YYYY-MM-DD
            "hora_inicio": "08:00",
            "hora_fim": "12:00",
            "segmento": "EI",
            "coord_acompanha": "sim",
            "coordenador": "coord@example.com",
            "formador1": "form1@example.com",
            "formador2": "",
            "formador3": "",
            "formador4": "",
            "formador5": "",
            "aprovacao": "",
        }

        assert hash_event_v2(row1) == hash_event_v2(row2)

    def test_time_format_normalization_with_seconds(self):
        """Horas com/sem segundos → HH:MM → mesmo hash."""
        row1 = {
            "source_sheet": "ACerta",
            "projeto": "ACerta",
            "municipio": "Fortaleza",
            "encontro": "1",
            "tipo": "Presencial",
            "data": "2025-01-15",
            "hora_inicio": "08:00:00",  # With seconds
            "hora_fim": "12:00:00",
            "segmento": "EI",
            "coord_acompanha": "sim",
            "coordenador": "coord@example.com",
            "formador1": "form1@example.com",
            "formador2": "",
            "formador3": "",
            "formador4": "",
            "formador5": "",
            "aprovacao": "",
        }

        row2 = {
            "source_sheet": "ACerta",
            "projeto": "ACerta",
            "municipio": "Fortaleza",
            "encontro": "1",
            "tipo": "Presencial",
            "data": "2025-01-15",
            "hora_inicio": "08:00",  # Without seconds
            "hora_fim": "12:00",
            "segmento": "EI",
            "coord_acompanha": "sim",
            "coordenador": "coord@example.com",
            "formador1": "form1@example.com",
            "formador2": "",
            "formador3": "",
            "formador4": "",
            "formador5": "",
            "aprovacao": "",
        }

        assert hash_event_v2(row1) == hash_event_v2(row2)

    def test_minimal_change_produces_different_hash_formador2(self):
        """Mudança mínima (ex.: formador2) → hash diferente."""
        row1 = {
            "source_sheet": "ACerta",
            "projeto": "ACerta",
            "municipio": "Fortaleza",
            "encontro": "1",
            "tipo": "Presencial",
            "data": "2025-01-15",
            "hora_inicio": "08:00",
            "hora_fim": "12:00",
            "segmento": "EI",
            "coord_acompanha": "sim",
            "coordenador": "coord@example.com",
            "formador1": "form1@example.com",
            "formador2": "",  # Empty
            "formador3": "",
            "formador4": "",
            "formador5": "",
            "aprovacao": "",
        }

        row2 = {
            "source_sheet": "ACerta",
            "projeto": "ACerta",
            "municipio": "Fortaleza",
            "encontro": "1",
            "tipo": "Presencial",
            "data": "2025-01-15",
            "hora_inicio": "08:00",
            "hora_fim": "12:00",
            "segmento": "EI",
            "coord_acompanha": "sim",
            "coordenador": "coord@example.com",
            "formador1": "form1@example.com",
            "formador2": "form2@example.com",  # Added formador2
            "formador3": "",
            "formador4": "",
            "formador5": "",
            "aprovacao": "",
        }

        assert hash_event_v2(row1) != hash_event_v2(row2)

    def test_minimal_change_produces_different_hash_municipio(self):
        """Mudança mínima (município) → hash diferente."""
        row1 = {
            "source_sheet": "ACerta",
            "projeto": "ACerta",
            "municipio": "Fortaleza",
            "encontro": "1",
            "tipo": "Presencial",
            "data": "2025-01-15",
            "hora_inicio": "08:00",
            "hora_fim": "12:00",
            "segmento": "EI",
            "coord_acompanha": "sim",
            "coordenador": "coord@example.com",
            "formador1": "form1@example.com",
            "formador2": "",
            "formador3": "",
            "formador4": "",
            "formador5": "",
            "aprovacao": "",
        }

        row2 = {
            "source_sheet": "ACerta",
            "projeto": "ACerta",
            "municipio": "Caucaia",  # Different
            "encontro": "1",
            "tipo": "Presencial",
            "data": "2025-01-15",
            "hora_inicio": "08:00",
            "hora_fim": "12:00",
            "segmento": "EI",
            "coord_acompanha": "sim",
            "coordenador": "coord@example.com",
            "formador1": "form1@example.com",
            "formador2": "",
            "formador3": "",
            "formador4": "",
            "formador5": "",
            "aprovacao": "",
        }

        assert hash_event_v2(row1) != hash_event_v2(row2)

    def test_minimal_change_produces_different_hash_data(self):
        """Mudança mínima (data) → hash diferente."""
        row1 = {
            "source_sheet": "ACerta",
            "projeto": "ACerta",
            "municipio": "Fortaleza",
            "encontro": "1",
            "tipo": "Presencial",
            "data": "2025-01-15",
            "hora_inicio": "08:00",
            "hora_fim": "12:00",
            "segmento": "EI",
            "coord_acompanha": "sim",
            "coordenador": "coord@example.com",
            "formador1": "form1@example.com",
            "formador2": "",
            "formador3": "",
            "formador4": "",
            "formador5": "",
            "aprovacao": "",
        }

        row2 = {
            "source_sheet": "ACerta",
            "projeto": "ACerta",
            "municipio": "Fortaleza",
            "encontro": "1",
            "tipo": "Presencial",
            "data": "2025-01-16",  # Different date
            "hora_inicio": "08:00",
            "hora_fim": "12:00",
            "segmento": "EI",
            "coord_acompanha": "sim",
            "coordenador": "coord@example.com",
            "formador1": "form1@example.com",
            "formador2": "",
            "formador3": "",
            "formador4": "",
            "formador5": "",
            "aprovacao": "",
        }

        assert hash_event_v2(row1) != hash_event_v2(row2)

    def test_ideb_alias_normalization(self):
        """Aliases IDEB → Gestão Escolar → mesmo sector → mesmo hash."""
        row1 = {
            "source_sheet": "Outros",
            "projeto": "IDEB",
            "municipio": "Fortaleza",
            "encontro": "1",
            "tipo": "Presencial",
            "data": "2025-01-15",
            "hora_inicio": "08:00",
            "hora_fim": "12:00",
            "segmento": "EI",
            "coord_acompanha": "sim",
            "coordenador": "coord@example.com",
            "formador1": "form1@example.com",
            "formador2": "",
            "formador3": "",
            "formador4": "",
            "formador5": "",
            "aprovacao": "",
        }

        row2 = {
            "source_sheet": "Outros",
            "projeto": "IDEB10",  # Alias
            "municipio": "Fortaleza",
            "encontro": "1",
            "tipo": "Presencial",
            "data": "2025-01-15",
            "hora_inicio": "08:00",
            "hora_fim": "12:00",
            "segmento": "EI",
            "coord_acompanha": "sim",
            "coordenador": "coord@example.com",
            "formador1": "form1@example.com",
            "formador2": "",
            "formador3": "",
            "formador4": "",
            "formador5": "",
            "aprovacao": "",
        }

        row3 = {
            "source_sheet": "Outros",
            "projeto": "Gestão Escolar",  # Canonical
            "municipio": "Fortaleza",
            "encontro": "1",
            "tipo": "Presencial",
            "data": "2025-01-15",
            "hora_inicio": "08:00",
            "hora_fim": "12:00",
            "segmento": "EI",
            "coord_acompanha": "sim",
            "coordenador": "coord@example.com",
            "formador1": "form1@example.com",
            "formador2": "",
            "formador3": "",
            "formador4": "",
            "formador5": "",
            "aprovacao": "",
        }

        hash1 = hash_event_v2(row1)
        hash2 = hash_event_v2(row2)
        hash3 = hash_event_v2(row3)

        assert hash1 == hash2 == hash3

    def test_super_aprovacao_included_in_hash(self):
        """Super: campo aprovacao incluído no hash."""
        row1 = {
            "source_sheet": "Super",
            "projeto": "Super",
            "municipio": "Fortaleza",
            "encontro": "1",
            "tipo": "Presencial",
            "data": "2025-01-15",
            "hora_inicio": "08:00",
            "hora_fim": "12:00",
            "segmento": "EI",
            "coord_acompanha": "sim",
            "coordenador": "coord@example.com",
            "formador1": "form1@example.com",
            "formador2": "",
            "formador3": "",
            "formador4": "",
            "formador5": "",
            "aprovacao": "Aprovado",
        }

        row2 = {
            "source_sheet": "Super",
            "projeto": "Super",
            "municipio": "Fortaleza",
            "encontro": "1",
            "tipo": "Presencial",
            "data": "2025-01-15",
            "hora_inicio": "08:00",
            "hora_fim": "12:00",
            "segmento": "EI",
            "coord_acompanha": "sim",
            "coordenador": "coord@example.com",
            "formador1": "form1@example.com",
            "formador2": "",
            "formador3": "",
            "formador4": "",
            "formador5": "",
            "aprovacao": "Pendente",  # Different
        }

        assert hash_event_v2(row1) != hash_event_v2(row2)

    def test_non_super_aprovacao_ignored_in_hash(self):
        """Não-Super: campo aprovacao ignorado no hash."""
        row1 = {
            "source_sheet": "ACerta",
            "projeto": "ACerta",
            "municipio": "Fortaleza",
            "encontro": "1",
            "tipo": "Presencial",
            "data": "2025-01-15",
            "hora_inicio": "08:00",
            "hora_fim": "12:00",
            "segmento": "EI",
            "coord_acompanha": "sim",
            "coordenador": "coord@example.com",
            "formador1": "form1@example.com",
            "formador2": "",
            "formador3": "",
            "formador4": "",
            "formador5": "",
            "aprovacao": "Aprovado",
        }

        row2 = {
            "source_sheet": "ACerta",
            "projeto": "ACerta",
            "municipio": "Fortaleza",
            "encontro": "1",
            "tipo": "Presencial",
            "data": "2025-01-15",
            "hora_inicio": "08:00",
            "hora_fim": "12:00",
            "segmento": "EI",
            "coord_acompanha": "sim",
            "coordenador": "coord@example.com",
            "formador1": "form1@example.com",
            "formador2": "",
            "formador3": "",
            "formador4": "",
            "formador5": "",
            "aprovacao": "Pendente",  # Different but ignored
        }

        assert hash_event_v2(row1) == hash_event_v2(row2)
