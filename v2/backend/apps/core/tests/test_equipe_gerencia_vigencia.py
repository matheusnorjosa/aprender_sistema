"""
Vigência (valid_from/valid_to) de EquipeGerencia.

Contrato:
- Toda linha nova nasce vigente hoje (valid_from=hoje, valid_to=NULL) — default do model.
- "vigente em D" = ativo=True AND valid_from<=D AND (valid_to IS NULL OR valid_to>=D).
- `ativo` continua kill-switch: ativo=False exclui mesmo com janela aberta.
- Helper SSOT: EquipeGerencia.objects.vigente_em(hoje=None) — `hoje` = timezone.localdate() (Fortaleza, RD-06).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportMissingParameterType=false, reportUnknownParameterType=false

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

import pytest

from apps.core.models import EquipeGerencia, Gerencia
from apps.core.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db

_COUNTER = {"i": 0}


def _next() -> int:
    _COUNTER["i"] += 1
    return _COUNTER["i"]


def _gerencia(setor: str = "Vidas Vig") -> Gerencia:
    n = _next()
    return Gerencia.objects.create(nome=f"GERENCIA VIG {n}", nome_setor=f"{setor} {n}")


def _membro(gerencia: Gerencia, papel: str = "FORMADOR", **kw) -> EquipeGerencia:
    n = _next()
    user = UsuarioFactory(username=f"vig_{n}", email=f"vig_{n}@ex.com", cpf=f"88877{n:06d}")
    return EquipeGerencia.objects.create(gerencia=gerencia, usuario=user, papel=papel, **kw)


class TestVigenteEmQuerySet:
    def test_new_link_defaults_to_vigente_today(self):
        m = _membro(_gerencia())  # sem valid_from/valid_to → default
        assert m.valid_from == timezone.localdate()
        assert m.valid_to is None
        assert EquipeGerencia.objects.vigente_em().filter(pk=m.pk).exists()

    def test_expired_link_excluded(self):
        hoje = timezone.localdate()  # entrou e saiu no passado (janela fechada)
        m = _membro(_gerencia(), valid_from=hoje - timedelta(days=30), valid_to=hoje - timedelta(days=1))
        assert not EquipeGerencia.objects.vigente_em().filter(pk=m.pk).exists()

    def test_future_start_excluded(self):
        amanha = timezone.localdate() + timedelta(days=1)
        m = _membro(_gerencia(), valid_from=amanha)
        assert not EquipeGerencia.objects.vigente_em().filter(pk=m.pk).exists()

    def test_inactive_overrides_open_window(self):
        m = _membro(_gerencia(), ativo=False)  # janela aberta, mas kill-switch manual
        assert not EquipeGerencia.objects.vigente_em().filter(pk=m.pk).exists()

    def test_valid_to_boundary_is_inclusive(self):
        hoje = timezone.localdate()
        m = _membro(_gerencia(), valid_to=hoje)  # termina hoje → ainda vigente hoje
        assert EquipeGerencia.objects.vigente_em().filter(pk=m.pk).exists()

    def test_vigente_em_accepts_explicit_date(self):
        hoje = timezone.localdate()
        m = _membro(_gerencia(), valid_from=hoje - timedelta(days=10), valid_to=hoje - timedelta(days=5))
        assert EquipeGerencia.objects.vigente_em(hoje - timedelta(days=7)).filter(pk=m.pk).exists()
        assert not EquipeGerencia.objects.vigente_em().filter(pk=m.pk).exists()


class TestScopeExcludesExpiredMember:
    """
    Ex-membro EXPIRADO perde acesso — o bug latente que a vigência fecha.
    Cobertura antes: ZERO (os read-sites só filtravam `ativo`, ou nem isso).
    """

    def test_user_gerencia_ids_excludes_expired_member(self):
        from apps.core.services.solicitacao_scope import _user_gerencia_ids

        g = _gerencia()
        hoje = timezone.localdate()
        m = _membro(g, papel="COORDENADOR", valid_from=hoje - timedelta(days=30), valid_to=hoje - timedelta(days=1))
        assert g.pk not in _user_gerencia_ids(m.usuario)

    def test_user_gerencia_ids_includes_current_member(self):
        from apps.core.services.solicitacao_scope import _user_gerencia_ids

        g = _gerencia()
        m = _membro(g, papel="COORDENADOR")  # vigente hoje (default)
        assert g.pk in _user_gerencia_ids(m.usuario)
