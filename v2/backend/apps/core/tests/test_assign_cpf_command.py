"""
Testes para comando assign_cpf_from_excel.

Valida:
- DRY-RUN: relata sem persistir
- APPLY: persiste no banco
- Idempotência: re-run não altera
- CPF inválido/mascarado → skipped
- Duplicidades/ambiguidades → conflicts
"""

import json
import pytest
from pathlib import Path
from openpyxl import Workbook
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import override_settings

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def users_db():
    """
    Cria usuários no banco com CPFs válidos temporários.

    CPFs no banco são diferentes dos CPFs na planilha para testar update.
    """
    u1 = User.objects.create_user(
        username="user1",
        email="user1@example.com",
        password="test123",
        first_name="João",
        last_name="Silva",
        cpf="11111111191",  # CPF válido temporário (será atualizado para 12345678901)
    )
    u2 = User.objects.create_user(
        username="user2",
        email="user2@example.com",
        password="test123",
        first_name="Maria",
        last_name="Santos",
        cpf="22222222280",  # CPF válido temporário (será atualizado para 98765432109)
    )
    u3 = User.objects.create_user(
        username="user3",
        email="ambiguo@example.com",
        password="test123",
        first_name="Pedro",
        last_name="Costa",
        cpf="33333333372",  # CPF válido temporário (email ambíguo → conflict)
    )
    # Duplicar email para criar ambiguidade
    u4 = User.objects.create_user(
        username="user4",
        email="ambiguo@example.com",  # Mesmo email que u3
        password="test123",
        first_name="Pedro",
        last_name="Costa Júnior",
        cpf="44444444453",  # CPF válido temporário (email ambíguo → conflict)
    )
    return {"u1": u1, "u2": u2, "u3": u3, "u4": u4}


@pytest.fixture
def excel_file(tmp_path, users_db):
    """Cria planilha Excel temporária com CPFs."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Ativos"

    # Header
    ws.append(["Nome", "Nome Completo", "Email", "CPF"])

    # Dados
    ws.append(["João", "João Silva", "user1@example.com", "123.456.789-01"])  # CPF com máscara
    ws.append(["Maria", "Maria Santos", "user2@example.com", "98765432109"])  # CPF sem máscara
    ws.append(["Pedro", "Pedro Costa", "ambiguo@example.com", "11111111111"])  # Email ambíguo
    ws.append(["Novo", "Novo Usuário", "novo@example.com", "22222222222"])  # Não existe no banco
    ws.append(["Inválido", "CPF Inválido", "invalido@example.com", "abc123"])  # CPF inválido

    path = tmp_path / "usuarios.xlsx"
    wb.save(path)
    return path


def test_dry_run_email_match(excel_file, users_db, tmp_path):
    """DRY-RUN: email match 1:1 → updated (não persiste)."""
    out_dir = tmp_path / "out_etl"
    out_dir.mkdir()

    call_command(
        "assign_cpf_from_excel",
        path=str(excel_file),
        sheet="Ativos",
        out=str(out_dir),
    )  # Sem --apply = DRY-RUN

    # Verificar relatório
    report_path = out_dir / "assign_cpf_report.json"
    assert report_path.exists()

    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    assert report["mode"] == "DRY-RUN"
    assert report["totals"]["updated"] == 2  # user1, user2
    assert report["totals"]["skipped"] >= 1  # Novo usuário, CPF inválido
    assert report["totals"]["conflicts"] >= 1  # Email ambíguo

    # Verificar que não persistiu no banco (mantém CPF original)
    users_db["u1"].refresh_from_db()
    assert users_db["u1"].cpf == "11111111191"  # Não foi alterado (DRY-RUN)


def test_apply_persists_and_idempotent(excel_file, users_db, tmp_path):
    """APPLY: persiste no banco; re-run é idempotente."""
    out_dir = tmp_path / "out_etl"
    out_dir.mkdir()

    # Primeira rodada: APPLY
    call_command(
        "assign_cpf_from_excel",
        path=str(excel_file),
        sheet="Ativos",
        out=str(out_dir),
        apply=True,
    )

    # Verificar persistência
    users_db["u1"].refresh_from_db()
    assert users_db["u1"].cpf == "12345678901"  # Máscara removida

    users_db["u2"].refresh_from_db()
    assert users_db["u2"].cpf == "98765432109"

    # Verificar relatório
    with open(out_dir / "assign_cpf_report.json", "r", encoding="utf-8") as f:
        report1 = json.load(f)

    assert report1["mode"] == "APPLY"
    assert report1["totals"]["updated"] == 2

    # Segunda rodada: idempotência (sem mudanças)
    call_command(
        "assign_cpf_from_excel",
        path=str(excel_file),
        sheet="Ativos",
        out=str(out_dir),
        apply=True,
    )

    with open(out_dir / "assign_cpf_report.json", "r", encoding="utf-8") as f:
        report2 = json.load(f)

    # Deve continuar relatando 2 updated (mas sem alterar nada, pois CPF já é igual)
    assert report2["totals"]["updated"] == 2

    # Verificar que não houve mudança
    users_db["u1"].refresh_from_db()
    assert users_db["u1"].cpf == "12345678901"


def test_cpf_invalido_skipped(excel_file, users_db, tmp_path):
    """CPF inválido/mascarado → skipped."""
    out_dir = tmp_path / "out_etl"
    out_dir.mkdir()

    call_command(
        "assign_cpf_from_excel",
        path=str(excel_file),
        sheet="Ativos",
        out=str(out_dir),
    )

    with open(out_dir / "assign_cpf_report.json", "r", encoding="utf-8") as f:
        report = json.load(f)

    # Verificar que CPF inválido foi pulado
    skipped_cpfs = [s.get("cpf_raw") for s in report["skipped"]]
    assert "abc123" in skipped_cpfs


def test_email_ambiguo_conflict(excel_file, users_db, tmp_path):
    """Email ambíguo (múltiplos usuários) → conflicts."""
    out_dir = tmp_path / "out_etl"
    out_dir.mkdir()

    call_command(
        "assign_cpf_from_excel",
        path=str(excel_file),
        sheet="Ativos",
        out=str(out_dir),
    )

    with open(out_dir / "assign_cpf_report.json", "r", encoding="utf-8") as f:
        report = json.load(f)

    # Verificar que email ambíguo foi reportado como conflito
    assert report["totals"]["conflicts"] >= 1
    conflict_reasons = [c.get("reason") for c in report["conflicts"]]
    assert any("ambíguo" in r.lower() for r in conflict_reasons)


def test_cpf_duplicado_na_planilha(tmp_path, users_db):
    """CPF duplicado na planilha → conflicts."""
    # Criar planilha com CPF duplicado
    wb = Workbook()
    ws = wb.active
    ws.title = "Ativos"
    ws.append(["Nome", "Nome Completo", "Email", "CPF"])
    ws.append(["João", "João Silva", "user1@example.com", "12345678901"])
    ws.append(["Maria", "Maria Santos", "user2@example.com", "12345678901"])  # CPF duplicado

    path = tmp_path / "usuarios_dup.xlsx"
    wb.save(path)

    out_dir = tmp_path / "out_etl"
    out_dir.mkdir()

    call_command(
        "assign_cpf_from_excel",
        path=str(path),
        sheet="Ativos",
        out=str(out_dir),
    )

    with open(out_dir / "assign_cpf_report.json", "r", encoding="utf-8") as f:
        report = json.load(f)

    # Ambos devem ser conflicts (CPF duplicado na planilha)
    assert report["totals"]["conflicts"] == 2
    assert all("duplicado na planilha" in c["reason"] for c in report["conflicts"])


def test_cpf_divergente_banco_planilha(tmp_path, users_db):
    """CPF divergente (banco != planilha) → conflicts."""
    # Atribuir CPF diferente no banco
    users_db["u1"].cpf = "99999999999"
    users_db["u1"].save()

    # Criar planilha com CPF diferente
    wb = Workbook()
    ws = wb.active
    ws.title = "Ativos"
    ws.append(["Nome", "Nome Completo", "Email", "CPF"])
    ws.append(["João", "João Silva", "user1@example.com", "12345678901"])  # Diferente do banco

    path = tmp_path / "usuarios_div.xlsx"
    wb.save(path)

    out_dir = tmp_path / "out_etl"
    out_dir.mkdir()

    call_command(
        "assign_cpf_from_excel",
        path=str(path),
        sheet="Ativos",
        out=str(out_dir),
    )

    with open(out_dir / "assign_cpf_report.json", "r", encoding="utf-8") as f:
        report = json.load(f)

    # Deve ser conflict (CPF divergente)
    assert report["totals"]["conflicts"] == 1
    assert "divergente" in report["conflicts"][0]["reason"].lower()


def test_etl_output_dir_from_settings(excel_file, users_db, tmp_path):
    """
    Testa que comando respeita settings.ETL_OUTPUT_DIR quando --out não é fornecido.

    Issue #53: Configuração de diretórios ETL via settings.
    """
    custom_out = tmp_path / "custom_output"
    custom_out.mkdir()

    # Override settings para usar diretório customizado
    with override_settings(ETL_OUTPUT_DIR=str(custom_out)):
        # Chamar comando SEM --out (deve usar settings.ETL_OUTPUT_DIR)
        call_command(
            "assign_cpf_from_excel",
            path=str(excel_file),
            sheet="Ativos",
            # Nota: sem parâmetro --out, deve usar settings.ETL_OUTPUT_DIR
        )

    # Verificar que relatório foi gerado no diretório customizado
    report_path = custom_out / "assign_cpf_report.json"
    assert report_path.exists(), f"Report should exist in {custom_out}"

    # Verificar conteúdo do relatório
    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    assert report["mode"] == "DRY-RUN"
    assert "updated" in report["totals"]
