"""
PR A — comando `definir_nome_exibicao_gerencias` (PLANOS_LIBERACAO_2026-09-29 §2, "Dado de produção").

- Dry-run por padrão; só grava com `--apply`.
- As 13 tuplas `(id, nome esperado, nome_exibicao)` são fixas (medidas em prod em 29/09).
  Id faltando ou `nome` divergente aborta TUDO sem gravar (proteção contra ambiente errado).
- Grava só `nome_exibicao` (`update_fields`) num `atomic`, com `registrar_auditoria` por mudança.
- Idempotente: a segunda execução dá 0 alterações.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError

import pytest

from apps.core.models import AuditLog, Gerencia

pytestmark = pytest.mark.django_db

# Mapa do dono (literal de propósito: trocar o mapa no comando exige trocar aqui também).
MAPA_DO_DONO = [
    (1, "SUPERINTENDENCIA", "Superintendência"),
    (2, "GERENCIA 2", "Vidas"),
    (3, "GERENCIA 3", "Fluir"),
    (4, "GERENCIA 4", "Superativar"),
    (6, "GERENCIA 6", "Sou da Paz"),
    (8, "INDIVIDUAL - A COR DA GENTE", "A Cor da Gente"),
    (9, "INDIVIDUAL - ED FINANCEIRA", "Educação Financeira"),
    (11, "INDIVIDUAL - MY COMPANION", "My Companion"),
    (12, "INDIVIDUAL - TRÂNSITO LEGAL", "Trânsito Legal"),
    (16, "GERENCIA IDEB 10", "Gestão Escolar"),
    (17, "GERENCIA BRINCANDO", "Brincando e Aprendendo"),
    (19, "GERENCIA DAT", "DAT"),
    (22, "LER, OUVIR E CONTAR", "Ler, Ouvir e Contar"),
]


@pytest.fixture
def gerencias_de_prod() -> dict[int, Gerencia]:
    """As 13 ativas com os ids/nomes de prod, mais uma inativa (g5) que fica fora do mapa."""
    criadas = {
        gid: Gerencia.objects.create(id=gid, nome=nome, nome_setor=f"Planilha {gid}") for gid, nome, _ in MAPA_DO_DONO
    }
    criadas[5] = Gerencia.objects.create(id=5, nome="GERENCIA 5", nome_setor="Planilha 5", ativo=False)
    return criadas


def _rodar(*args: str) -> str:
    out = StringIO()
    call_command("definir_nome_exibicao_gerencias", *args, stdout=out)
    return out.getvalue()


def _nomes_exibicao() -> dict[int, str]:
    return dict(Gerencia.objects.values_list("id", "nome_exibicao"))


def _audits() -> int:
    return AuditLog.objects.filter(model_name="Gerencia", action=AuditLog.Action.UPDATE).count()


def test_dry_run_por_padrao_nao_grava(gerencias_de_prod, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        saida = _rodar()

    assert set(_nomes_exibicao().values()) == {""}
    assert _audits() == 0
    assert "DRY-RUN" in saida
    assert "GERENCIA 4" in saida and "Superativar" in saida
    assert "13 a alterar" in saida


def test_apply_grava_so_nome_exibicao_e_audita(gerencias_de_prod, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        saida = _rodar("--apply")

    for gid, nome, nome_exibicao in MAPA_DO_DONO:
        g = Gerencia.objects.get(pk=gid)
        assert g.nome_exibicao == nome_exibicao
        assert g.nome == nome
        assert g.nome_setor == f"Planilha {gid}"
    assert Gerencia.objects.get(pk=5).nome_exibicao == ""  # inativa fora do mapa
    assert _audits() == 13
    assert "13 alteradas" in saida


def test_nome_divergente_aborta_sem_gravar(gerencias_de_prod, django_capture_on_commit_callbacks):
    Gerencia.objects.filter(pk=4).update(nome="GERENCIA ACERTA")

    with django_capture_on_commit_callbacks(execute=True), pytest.raises(CommandError, match="GERENCIA ACERTA"):
        _rodar("--apply")

    assert set(_nomes_exibicao().values()) == {""}
    assert _audits() == 0


def test_id_faltando_aborta_sem_gravar(gerencias_de_prod, django_capture_on_commit_callbacks):
    Gerencia.objects.filter(pk=22).delete()

    with django_capture_on_commit_callbacks(execute=True), pytest.raises(CommandError, match="22"):
        _rodar("--apply")

    assert set(_nomes_exibicao().values()) == {""}
    assert _audits() == 0


def test_segunda_execucao_da_zero_alteracoes(gerencias_de_prod, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        _rodar("--apply")
    with django_capture_on_commit_callbacks(execute=True):
        saida = _rodar("--apply")

    assert "0 alteradas" in saida
    assert "13 iguais" in saida
    assert _audits() == 13
