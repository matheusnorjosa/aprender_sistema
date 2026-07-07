"""Throttle dos endpoints de import (upload pesado) e export do dashboard.

Contexto (Onda 4, pos-incidente 2026-07-06): os endpoints de upload/import e o export do
dashboard NAO tinham rate-limit proprio — so o global `user: 1000/hour`. Cada import faz
parse de arquivo + writes SINCRONOS segurando o worker do gunicorn; uma rajada podia
saturar os workers (mesma familia de causa do incidente). PR-B adiciona os scopes
`import` (30/min prod, 300/min dev) e liga o `export` (10/min prod) ja existente, ambos
via `ScopedRateThrottle` (que ja esta em DEFAULT_THROTTLE_CLASSES) — basta `throttle_scope`.

Estrategia de teste (mesma licao de test_login_throttle_simple.py): o 429 ponta-a-ponta
pelo APIClient flaka no CI paralelo (pytest-xdist limpa o cache de throttle entre testes),
entao validamos em DUAS camadas deterministas + validacao manual em staging do fluxo real:
  1. WIRING (regressao): cada view de import declara `throttle_scope = "import"` e o export
     declara `"export"` — um endpoint de import novo sem throttle REPROVA aqui.
  2. COMPORTAMENTAL isolado: `ScopedRateThrottle` com rate forcado baixo bloqueia de fato
     apos o limite para o scope `import` — prova que a mecanica atua em runtime, sem
     depender do lifecycle de cache que flaka (cache dedicado + ident unico + clear).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportMissingParameterType=false, reportUnknownParameterType=false, reportArgumentType=false

from __future__ import annotations

import importlib

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIRequestFactory
from rest_framework.throttling import ScopedRateThrottle

import pytest

# (modulo, classe) de cada endpoint de import (POST). Ao criar um novo endpoint de
# import, adicione-o aqui — o wiring test abaixo forca que ele carregue o throttle.
IMPORT_VIEWS: list[tuple[str, str]] = [
    ("apps.core.views_import_bloqueios", "ImportBloqueiosView"),
    ("apps.core.views_import_eventos", "ImportEventosView"),
    ("apps.core.views_import_produtos", "ImportProdutosView"),
    ("apps.core.views_import_deslocamentos", "ImportDeslocamentosView"),
    ("apps.core.views_import_usuarios", "ImportUsuariosView"),
    ("apps.core.views_import_colecoes", "ImportColecoesView"),
    ("apps.core.views_import_equipe_gerencia", "ImportEquipeGerenciaView"),
    ("apps.core.views_import_municipios", "ImportMunicipiosView"),
    ("apps.core.views_controle_imports", "ImportComprasView"),
    ("apps.core.views_imports", "ControleImportAcoesView"),
    ("apps.core.views_imports", "DATImportCadastrosView"),
    ("apps.core.views.imports", "ImportJobBloqueiosUploadView"),
]


def _load(module: str, name: str) -> type:
    return getattr(importlib.import_module(module), name)


@pytest.mark.parametrize("module,name", IMPORT_VIEWS)
def test_endpoint_de_import_declara_throttle_scope_import(module: str, name: str) -> None:
    view = _load(module, name)
    assert (
        getattr(view, "throttle_scope", None) == "import"
    ), f"{name} deve ter throttle_scope='import' — upload pesado nao pode ficar sem rate-limit proprio."


def test_export_view_declara_throttle_scope_export() -> None:
    view = _load("apps.core.views_gcal.detail", "DashboardEventsExportView")
    assert getattr(view, "throttle_scope", None) == "export"


def test_rates_import_e_export_definidos_com_formato_valido() -> None:
    rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
    assert "import" in rates and "/" in rates["import"], "scope 'import' precisa de rate em DEFAULT_THROTTLE_RATES"
    assert "export" in rates and "/" in rates["export"], "scope 'export' precisa de rate em DEFAULT_THROTTLE_RATES"


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "throttle-import-behavioral",
        }
    }
)
def test_scoped_throttle_import_bloqueia_apos_o_limite() -> None:
    """Comportamental isolado: apos o limite, o scope `import` bloqueia (base do 429).

    Nao passa pelo APIClient (que flaka no xdist): dirige o proprio ScopedRateThrottle com
    cache dedicado + ident unico. Rate forcado 2/min (distintivo do default 30/min).
    """
    cache.clear()  # cache locmem dedicado deste teste
    factory = APIRequestFactory()
    view = type("_ImportViewStub", (), {"throttle_scope": "import"})()
    throttle = ScopedRateThrottle()
    throttle.THROTTLE_RATES = {"import": "2/min"}  # rate baixo e distintivo do default

    decisions: list[bool] = []
    for _ in range(3):
        request = factory.post("/api/import-stub/")
        request.user = AnonymousUser()  # nao-autenticado -> ident = IP
        request.META["REMOTE_ADDR"] = "203.0.113.201"
        decisions.append(throttle.allow_request(request, view))

    assert decisions == [True, True, False], f"esperava 2 permitidas + 1 bloqueada, veio {decisions}"
