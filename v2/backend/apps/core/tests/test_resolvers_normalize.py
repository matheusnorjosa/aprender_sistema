"""
Testes para normalize_projeto_name e resolve_projeto (Issue #712).

Garante que prefixos de ano (ex: "2026 ") e variantes de nível
são normalizados antes do lookup em Projeto.
"""

import pytest

from apps.core.services.resolvers import normalize_projeto_name, resolve_projeto
from apps.core.tests.factories import ProjetoFactory

# ---------------------------------------------------------------------------
# normalize_projeto_name — unit tests (sem DB)
# ---------------------------------------------------------------------------


class TestNormalizeProjetoName:
    """Testa a normalização de nomes de projeto sem tocar no banco."""

    def test_strip_year_prefix_2026(self):
        assert normalize_projeto_name("2026 Novo Lendo") == "Novo Lendo"

    def test_strip_year_prefix_2025(self):
        assert normalize_projeto_name("2025 Sou da Paz") == "Sou da Paz"

    def test_strip_year_prefix_any_4digit_year(self):
        assert normalize_projeto_name("2027 Sou da Paz") == "Sou da Paz"

    def test_no_prefix_unchanged(self):
        assert normalize_projeto_name("Sou da Paz") == "Sou da Paz"

    def test_strip_prefix_with_extra_spaces(self):
        assert normalize_projeto_name("2026  Novo Lendo") == "Novo Lendo"

    def test_fluir_nivel_1_normalized(self):
        assert normalize_projeto_name("2026 Fluir das Emoções Nível 1") == "Fluir das Emoções N1"

    def test_fluir_nivel_2_normalized(self):
        assert normalize_projeto_name("Fluir das Emoções Nível 2") == "Fluir das Emoções N2"

    def test_fluir_nivel_3_normalized(self):
        assert normalize_projeto_name("2026 Fluir das Emoções Nível 3") == "Fluir das Emoções N3"

    def test_avancando_juntos_variants(self):
        assert normalize_projeto_name("2026 Avançando Juntos Língua Portuguesa") == "AVANÇANDO JUNTOS PORTUGUÊS"

    def test_vida_ciencias_variant(self):
        assert normalize_projeto_name("2026 Vida & Ciências") == "VIDA E CIÊNCIAS"

    def test_empty_string_unchanged(self):
        assert normalize_projeto_name("") == ""

    def test_only_year_no_name(self):
        # "2026 " com espaço final mas sem nome — strip resulta em "2026" (sem nome)
        result = normalize_projeto_name("2026 ")
        # Após strip, sobra apenas "2026" ou string vazia — nenhum nome de projeto válido
        assert result in ("", "2026", "2026 ")

    def test_year_in_middle_not_stripped(self):
        # Ano no meio do nome NÃO deve ser removido
        result = normalize_projeto_name("Projeto 2026 Especial")
        assert "2026" in result


# ---------------------------------------------------------------------------
# resolve_projeto com prefixo de ano — integration tests (com DB)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestResolveProjetoWithYearPrefix:
    """Testa que resolve_projeto encontra projetos mesmo com prefixo de ano."""

    @pytest.fixture(autouse=True)
    def create_projetos(self, db: None) -> None:
        ProjetoFactory(nome="Novo Lendo", fluxo="NAO_SUPER", ativo=True)
        ProjetoFactory(nome="Fluir das Emoções N1", fluxo="SUPER", ativo=True)
        ProjetoFactory(nome="Sou da Paz", fluxo="NAO_SUPER", ativo=True)

    def test_resolve_com_prefixo_2026(self):
        projeto = resolve_projeto("2026 Novo Lendo")
        assert projeto is not None
        assert projeto.nome == "Novo Lendo"

    def test_resolve_sem_prefixo_funciona_normalmente(self):
        projeto = resolve_projeto("Novo Lendo")
        assert projeto is not None
        assert projeto.nome == "Novo Lendo"

    def test_resolve_fluir_nivel_com_prefixo(self):
        projeto = resolve_projeto("2026 Fluir das Emoções Nível 1")
        assert projeto is not None
        assert projeto.nome == "Fluir das Emoções N1"

    def test_resolve_case_insensitive_com_prefixo(self):
        projeto = resolve_projeto("2026 NOVO LENDO")
        assert projeto is not None
        assert projeto.nome == "Novo Lendo"

    def test_resolve_inexistente_retorna_none(self):
        projeto = resolve_projeto("2026 Projeto Inexistente XYZ")
        assert projeto is None

    def test_resolve_prefixo_2025(self):
        projeto = resolve_projeto("2025 Sou da Paz")
        assert projeto is not None
        assert projeto.nome == "Sou da Paz"


# ---------------------------------------------------------------------------
# Projeto renomeado no catálogo (decisão do dono, 02/10): a agenda continua
# mandando "FLUIR DAS EMOÇÕES" e o projeto vira "Fluir das Emoções (Antigo)"
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestResolveProjetoRenomeado:
    def test_antes_do_rename_resolve_pelo_nome(self):
        ProjetoFactory(nome="Fluir das Emoções", fluxo="SUPER")
        ProjetoFactory(nome="Fluir das Emoções 1", fluxo="SUPER")
        for bruto in ("FLUIR DAS EMOÇÕES", "2026 Fluir das Emoções"):
            projeto = resolve_projeto(bruto)
            assert projeto is not None, bruto
            assert projeto.nome == "Fluir das Emoções"

    def test_depois_do_rename_resolve_para_o_antigo(self):
        ProjetoFactory(nome="Fluir das Emoções (Antigo)", fluxo="SUPER")
        ProjetoFactory(nome="Fluir das Emoções 1", fluxo="SUPER")
        for bruto in ("FLUIR DAS EMOÇÕES", "2026 Fluir das Emoções", "fluir das emocoes"):
            projeto = resolve_projeto(bruto)
            assert projeto is not None, bruto
            assert projeto.nome == "Fluir das Emoções (Antigo)"

    def test_numerado_nao_cai_no_antigo(self):
        ProjetoFactory(nome="Fluir das Emoções (Antigo)", fluxo="SUPER")
        numerado = ProjetoFactory(nome="Fluir das Emoções 1", fluxo="SUPER")
        assert resolve_projeto("FLUIR DAS EMOÇÕES 1") == numerado
