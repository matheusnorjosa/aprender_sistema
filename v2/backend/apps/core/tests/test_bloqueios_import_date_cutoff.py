"""
Decisão do dono (2026-09-14): no import de bloqueios, o alvo é validado pela DATA do
bloqueio (campo `inicio`):
- ANTES de 2026-07-31 → cria para QUALQUER usuário (dados históricos);
- A PARTIR de 31/07/2026 → só Formador ATIVO (senão vira pendência).

⚑ o cutoff é a data do BLOQUEIO (`inicio`), não a data do import. Complementa o #2011
(created_by + AuditLog). A regra pode ser mais estrita que a operação histórica sem
quebrá-la — o histórico (pré-cutoff) segue aceitando qualquer usuário.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from apps.core.models import AvailabilityBlock
from apps.core.services.bloqueios_import import import_bloqueios_from_file
from apps.core.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db


def _csv(nome: str, inicio: str, fim: str) -> str:
    content = f"usuario,inicio,fim,tipo,motivo\n{nome},{inicio},{fim},T,Teste\n"
    temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    temp.write(content)
    temp.close()
    return temp.name


class TestBloqueiosImportDateCutoff:
    def test_pos_cutoff_nao_formador_vira_pendencia(self):
        alvo = UsuarioFactory(username="ncf", cpf="90000000001", first_name="Naoformador", last_name="Alfa")
        path = _csv("Naoformador Alfa", "2026-08-01 08:00", "2026-08-01 12:00")
        try:
            result = import_bloqueios_from_file(path=path, dry_run=False)
        finally:
            Path(path).unlink(missing_ok=True)

        assert result["stats"]["created"] == 0
        assert result["stats"]["skipped"]["usuario"] == 1
        assert not AvailabilityBlock.objects.filter(usuario=alvo).exists()

    def test_pos_cutoff_formador_ativo_cria(self):
        alvo = UsuarioFactory(
            username="fa", cpf="90000000002", first_name="Formador", last_name="Beta", groups=["Formador"]
        )
        path = _csv("Formador Beta", "2026-08-01 08:00", "2026-08-01 12:00")
        try:
            result = import_bloqueios_from_file(path=path, dry_run=False)
        finally:
            Path(path).unlink(missing_ok=True)

        assert result["stats"]["created"] == 1
        assert AvailabilityBlock.objects.filter(usuario=alvo).exists()

    def test_pos_cutoff_formador_inativo_vira_pendencia(self):
        alvo = UsuarioFactory(
            username="fi",
            cpf="90000000003",
            first_name="Formador",
            last_name="Gama",
            groups=["Formador"],
            is_active=False,
        )
        path = _csv("Formador Gama", "2026-08-01 08:00", "2026-08-01 12:00")
        try:
            result = import_bloqueios_from_file(path=path, dry_run=False)
        finally:
            Path(path).unlink(missing_ok=True)

        assert result["stats"]["created"] == 0
        assert result["stats"]["skipped"]["usuario"] == 1
        assert not AvailabilityBlock.objects.filter(usuario=alvo).exists()

    def test_pre_cutoff_qualquer_usuario_cria(self):
        alvo = UsuarioFactory(username="hist", cpf="90000000004", first_name="Historico", last_name="Delta")
        path = _csv("Historico Delta", "2026-03-01 08:00", "2026-03-01 12:00")
        try:
            result = import_bloqueios_from_file(path=path, dry_run=False)
        finally:
            Path(path).unlink(missing_ok=True)

        assert result["stats"]["created"] == 1
        assert AvailabilityBlock.objects.filter(usuario=alvo).exists()
