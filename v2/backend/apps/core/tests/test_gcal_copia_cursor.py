"""Cursor da cópia Google → Sistema (PR-A): um por calendário, desligado e em `observar` por padrão."""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false

from __future__ import annotations

from django.db import IntegrityError

import pytest

from apps.core.models import GCalCopiaCursor


@pytest.mark.django_db
def test_defaults_do_cursor():
    cursor = GCalCopiaCursor.objects.create(calendar_id="cal-org")
    cursor.refresh_from_db()

    assert cursor.sync_token is None
    assert cursor.ativo is False
    assert cursor.modo == "observar"
    assert cursor.operador is None
    assert cursor.adiados == []
    assert cursor.resumo == {}
    assert cursor.ultimo_sucesso_em is None
    assert cursor.ultimo_erro == ""
    assert cursor.created_at is not None and cursor.updated_at is not None


@pytest.mark.django_db
def test_um_cursor_por_calendario():
    GCalCopiaCursor.objects.create(calendar_id="cal-org")

    with pytest.raises(IntegrityError):
        GCalCopiaCursor.objects.create(calendar_id="cal-org")


def test_modos_validos():
    assert {valor for valor, _ in GCalCopiaCursor._meta.get_field("modo").choices} == {"observar", "copiar"}
