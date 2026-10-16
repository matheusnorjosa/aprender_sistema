"""
Tests for seed_gerentes management command.

F5 (scan de segurança, 16/10/2026): a lista de gerentes NÃO mora no código. O operador passa um
arquivo JSON fora do git (`--arquivo`); aqui os dados são sintéticos: CPFs que FALHAM no dígito
verificador, nomes genéricos e e-mails @example.invalid.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

import json
import re
from io import StringIO
from pathlib import Path

from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import CommandError

import pytest

from apps.core.models import EquipeGerencia, Gerencia, Usuario
from apps.core.validators import is_valid_cpf

# 4 na Superintendência (a primeira vira Gerencia.gerente), 1 em Brincando, ACerta e Vidas.
GERENTES_SINTETICOS = [
    {
        "first_name": "Gerente",
        "last_name": "Super Um",
        "cpf": "10000000001",
        "email": "gerente.super1@example.invalid",
        "gerencia_setor": "Super",
    },
    {
        "first_name": "Gerente",
        "last_name": "Brincando",
        "cpf": "10000000002",
        "email": "gerente.brincando@example.invalid",
        "gerencia_setor": "Brincando",
    },
    {
        "first_name": "Gerente",
        "last_name": "Acerta",
        "cpf": "10000000003",
        "email": "gerente.acerta@example.invalid",
        "gerencia_setor": "ACerta",
    },
    {
        "first_name": "Gerente",
        "last_name": "Super Dois",
        "cpf": "10000000004",
        "email": "gerente.super2@example.invalid",
        "gerencia_setor": "Super",
    },
    {
        "first_name": "Gerente",
        "last_name": "Super Tres",
        "cpf": "10000000005",
        "email": "gerente.super3@example.invalid",
        "gerencia_setor": "Super",
    },
    {
        "first_name": "Gerente",
        "last_name": "Vidas",
        "cpf": "10000000006",
        "email": "gerente.vidas@example.invalid",
        "gerencia_setor": "Vidas",
    },
    {
        "first_name": "Gerente",
        "last_name": "Super Quatro",
        "cpf": "10000000007",
        "email": "gerente.super4@example.invalid",
        "gerencia_setor": "Super",
    },
]

_SUPER_EMAILS = [g["email"] for g in GERENTES_SINTETICOS if g["gerencia_setor"] == "Super"]


@pytest.fixture
def arquivo(tmp_path: Path) -> str:
    """Arquivo do operador (fora do git) com a lista sintética."""
    caminho = tmp_path / "gerentes.json"
    caminho.write_text(json.dumps(GERENTES_SINTETICOS), encoding="utf-8")
    return str(caminho)


@pytest.fixture
def clean_gerencias(db):
    """Ensure Gerencias exist and have no gerente assigned."""
    Gerencia.objects.all().update(gerente=None)
    call_command("seed_gerencias")
    yield
    Gerencia.objects.all().update(gerente=None)


@pytest.fixture
def clean_gerentes(db):
    """Remove gerentes from DB and Group."""
    try:
        Group.objects.get(name="Gerente").user_set.clear()
    except Group.DoesNotExist:
        pass
    EquipeGerencia.objects.filter(papel="GERENTE").delete()
    Usuario.objects.filter(cargo="Gerente").delete()
    yield
    try:
        Group.objects.get(name="Gerente").user_set.clear()
    except Group.DoesNotExist:
        pass
    EquipeGerencia.objects.filter(papel="GERENTE").delete()
    Usuario.objects.filter(cargo="Gerente").delete()


def test_dados_sinteticos_falham_no_digito_verificador():
    """Guarda do próprio teste: nenhum CPF daqui pode ser de gente de verdade."""
    assert not any(is_valid_cpf(g["cpf"]) for g in GERENTES_SINTETICOS)


def test_codigo_do_comando_nao_traz_dado_pessoal():
    """F5: o comando não traz CPF que passe no dígito verificador nem e-mail da empresa."""
    fonte = (Path(__file__).resolve().parents[1] / "management" / "commands" / "seed_gerentes.py").read_text(
        encoding="utf-8"
    )
    # Conta, não lista: a mensagem do assert não pode repetir o CPF.
    assert sum(1 for c in re.findall(r"\d{11}", fonte) if is_valid_cpf(c)) == 0
    assert "@aprendereditora" not in fonte


@pytest.mark.django_db
class TestSeedGerentesCommand:
    """Tests for seed_gerentes management command."""

    def test_sem_arquivo_recusa(self, clean_gerencias, clean_gerentes):
        """Sem `--arquivo` não há lista: o comando para em vez de semear dado embutido."""
        with pytest.raises(CommandError):
            call_command("seed_gerentes")
        assert Usuario.objects.filter(cargo="Gerente").count() == 0

    def test_arquivo_inexistente_recusa(self, clean_gerencias, clean_gerentes, tmp_path):
        with pytest.raises(CommandError):
            call_command("seed_gerentes", "--arquivo", str(tmp_path / "nao-existe.json"))

    def test_arquivo_sem_campo_obrigatorio_recusa(self, clean_gerencias, clean_gerentes, tmp_path):
        caminho = tmp_path / "incompleto.json"
        caminho.write_text(json.dumps([{"first_name": "Gerente", "cpf": "10000000001"}]), encoding="utf-8")
        with pytest.raises(CommandError):
            call_command("seed_gerentes", "--arquivo", str(caminho))
        assert Usuario.objects.filter(cargo="Gerente").count() == 0

    def test_saida_nao_traz_nome_nem_cpf(self, clean_gerencias, clean_gerentes, arquivo):
        """A saída identifica a conta por u<id>, sem nome, CPF ou e-mail."""
        out = StringIO()
        call_command("seed_gerentes", "--arquivo", arquivo, stdout=out)
        saida = out.getvalue()
        for g in GERENTES_SINTETICOS:
            assert g["cpf"] not in saida
            assert g["email"] not in saida
            assert f'{g["first_name"]} {g["last_name"]}' not in saida

    def test_seed_gerentes_creates_group_if_not_exists(self, clean_gerencias, clean_gerentes, arquivo):
        """Test that command creates canonical função group 'Gerente' if it doesn't exist."""
        existing = Group.objects.filter(name="Gerente").first()
        if existing is not None:
            existing.name = "Gerente (temp)"
            existing.save(update_fields=["name"])

        out = StringIO()
        call_command("seed_gerentes", "--arquivo", arquivo, stdout=out)

        assert Group.objects.filter(name="Gerente").exists()
        assert "Created Django Group: Gerente" in out.getvalue()

    def test_seed_gerentes_does_not_use_legacy_gerencia_group(self, clean_gerencias, clean_gerentes, arquivo):
        """Regression C2-B1: gerentes vão para grupo canônico 'Gerente', não para o legado 'Gerência'."""
        call_command("seed_gerentes", "--arquivo", arquivo)

        gerentes = Usuario.objects.filter(cargo="Gerente")
        assert gerentes.exists()
        for usuario in gerentes:
            assert usuario.groups.filter(name="Gerente").exists()
            assert not usuario.groups.filter(name="Gerência").exists()

    def test_seed_gerentes_creates_missing_usuarios(self, clean_gerencias, clean_gerentes, arquivo):
        """Cria as contas da lista do arquivo."""
        assert Usuario.objects.filter(cargo="Gerente").count() == 0

        call_command("seed_gerentes", "--arquivo", arquivo, stdout=StringIO())

        gerentes = Usuario.objects.filter(cargo="Gerente")
        assert gerentes.count() == 7
        assert set(gerentes.values_list("cpf", flat=True)) == {g["cpf"] for g in GERENTES_SINTETICOS}

    def test_seed_gerentes_adds_usuarios_to_group(self, clean_gerencias, clean_gerentes, arquivo):
        """Test that all 7 gerentes are added to canonical 'Gerente' group."""
        call_command("seed_gerentes", "--arquivo", arquivo)

        gerente_group = Group.objects.get(name="Gerente")
        assert gerente_group.user_set.count() == 7
        for usuario in Usuario.objects.filter(cargo="Gerente"):
            assert gerente_group in usuario.groups.all()

    def test_seed_gerentes_creates_equipe_gerencia_gerente(self, clean_gerencias, clean_gerentes, arquivo):
        """C2-B1: command must create EquipeGerencia.papel=GERENTE for each resolved gerente."""
        call_command("seed_gerentes", "--arquivo", arquivo)

        assert EquipeGerencia.objects.filter(papel="GERENTE").count() == 7
        for usuario in Usuario.objects.filter(cargo="Gerente"):
            assert EquipeGerencia.objects.filter(usuario=usuario, papel="GERENTE").count() == 1

    def test_seed_gerentes_equipe_gerencia_idempotent(self, clean_gerencias, clean_gerentes, arquivo):
        """C2-B1: running twice must not duplicate EquipeGerencia GERENTE rows."""
        call_command("seed_gerentes", "--arquivo", arquivo)
        first = EquipeGerencia.objects.filter(papel="GERENTE").count()
        call_command("seed_gerentes", "--arquivo", arquivo)
        second = EquipeGerencia.objects.filter(papel="GERENTE").count()
        assert first == second == 7

    def test_seed_gerentes_links_gerencia_fk(self, clean_gerencias, clean_gerentes, arquivo):
        """Liga Gerencia.gerente: 4 gerências, a Superintendência com a primeira da lista."""
        call_command("seed_gerentes", "--arquivo", arquivo)

        assert Gerencia.objects.filter(gerente__isnull=False).count() == 4

        esperado = {
            "SUPERINTENDENCIA": "Super Um",
            "GERENCIA 2": "Vidas",
            "GERENCIA 4": "Acerta",
            "GERENCIA 5": "Brincando",
        }
        for nome, last_name in esperado.items():
            gerencia = Gerencia.objects.get(nome=nome)
            assert gerencia.gerente is not None
            assert gerencia.gerente.last_name == last_name

    def test_seed_gerentes_idempotent(self, clean_gerencias, clean_gerentes, arquivo):
        """Test that running command twice doesn't create duplicates."""
        call_command("seed_gerentes", "--arquivo", arquivo, stdout=StringIO())

        first_gerentes_count = Usuario.objects.filter(cargo="Gerente").count()
        first_group_count = Group.objects.get(name="Gerente").user_set.count()
        first_gerencia_links = Gerencia.objects.filter(gerente__isnull=False).count()
        assert (first_gerentes_count, first_group_count, first_gerencia_links) == (7, 7, 4)

        out2 = StringIO()
        call_command("seed_gerentes", "--arquivo", arquivo, stdout=out2)

        assert Usuario.objects.filter(cargo="Gerente").count() == first_gerentes_count
        assert Group.objects.get(name="Gerente").user_set.count() == first_group_count
        assert Gerencia.objects.filter(gerente__isnull=False).count() == first_gerencia_links
        assert "already exists" in out2.getvalue().lower()

    def test_seed_gerentes_dry_run_does_not_commit(self, clean_gerencias, clean_gerentes, arquivo):
        """Test that --dry-run doesn't commit changes."""
        out = StringIO()
        call_command("seed_gerentes", "--arquivo", arquivo, "--dry-run", stdout=out)

        assert Usuario.objects.filter(cargo="Gerente").count() == 0
        output = out.getvalue()
        assert "DRY RUN" in output
        assert "Rolling back" in output

    def test_seed_gerentes_handles_existing_usuarios(self, clean_gerencias, clean_gerentes, arquivo):
        """Conta já existente (mesmo CPF) é reaproveitada."""
        g = GERENTES_SINTETICOS[5]
        Usuario.objects.create(
            cpf=g["cpf"],
            username="gerente.vidas",
            first_name=g["first_name"],
            last_name=g["last_name"],
            email=g["email"],
            cargo="Gerente",
        )
        assert Usuario.objects.filter(cargo="Gerente").count() == 1

        out = StringIO()
        call_command("seed_gerentes", "--arquivo", arquivo, stdout=out)

        assert Usuario.objects.filter(cargo="Gerente").count() == 7
        assert "already exists" in out.getvalue().lower()

    def test_seed_gerentes_handles_superintendencia_multiple_managers(self, clean_gerencias, clean_gerentes, arquivo):
        """SUPERINTENDENCIA com 4 gerentes liga só a primeira; as 4 entram no grupo."""
        out = StringIO()
        call_command("seed_gerentes", "--arquivo", arquivo, stdout=out)

        assert Gerencia.objects.get(nome="SUPERINTENDENCIA").gerente is not None

        gerente_group = Group.objects.get(name="Gerente")
        super_managers = Usuario.objects.filter(cargo="Gerente", email__in=_SUPER_EMAILS)
        assert super_managers.count() == 4
        for manager in super_managers:
            assert gerente_group in manager.groups.all()

        output = out.getvalue()
        assert "Linked" in output or "already linked" in output

    def test_generate_username_function(self):
        """Test username generation from names."""
        from apps.dev_tools.management.commands.seed_gerentes import generate_username

        assert generate_username("Ana", "Lima Sousa") == "ana.sousa"
        assert generate_username("Ana Clara", "Lima de Sousa") == "ana.sousa"
        assert generate_username("Lúcia", "Mota de Araújo") == "lucia.araujo"
        assert generate_username("João", "Conceição") == "joao.conceicao"
