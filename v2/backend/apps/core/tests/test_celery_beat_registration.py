# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportMissingTypeStubs=false
"""Sentinela: toda task agendada no beat DEVE existir no registro do worker.

Por que num subprocesso, e nao com um `import` simples:

Producao passou meses sem backup automatico. O `beat` despachava
`backup.perform_database_backup` todo dia as 02:00 e o worker respondia
`NotRegistered` — porque `app.autodiscover_tasks()` importa apenas o modulo
`tasks` de cada app instalada, e a task mora em `tasks_backup.py` (#1455).

A suite de testes nunca pegou isso: `test_celery_backup.py` e
`test_tasks_mp5.py` importam `apps.core.tasks_backup` diretamente, e o decorator
`@shared_task` registra a task NO PROCESSO DO PYTEST. O registro vazava, o teste
ficava verde e o worker de verdade seguia sem conhecer a task.

Um teste que importe qualquer coisa antes de olhar o registro herda essa mentira.
Por isso a sonda roda num INTERPRETADOR NOVO e chama
`app.loader.import_default_modules()` — literalmente o que o worker faz ao subir.
E a unica forma de observar o que o worker enxerga, e nao o que o pytest montou.
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

# Reproduz o boot do worker: django.setup() -> app -> import_default_modules().
_SONDA = """
import json, os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from config.celery import app

app.loader.import_default_modules()  # o worker faz exatamente isto ao subir

agendadas = sorted({entry["task"] for entry in app.conf.beat_schedule.values()})
print("__SONDA__" + json.dumps({"agendadas": agendadas, "registradas": sorted(app.tasks)}))
"""


def _sondar() -> dict[str, list[str]]:
    proc = subprocess.run(
        [sys.executable, "-c", _SONDA],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if proc.returncode != 0:
        pytest.fail(f"a sonda falhou (rc={proc.returncode}):\n{proc.stderr}")

    # django.setup() imprime banner; pega so a linha marcada.
    for linha in proc.stdout.splitlines():
        if linha.startswith("__SONDA__"):
            return json.loads(linha[len("__SONDA__") :])
    pytest.fail(f"a sonda nao emitiu resultado:\nstdout={proc.stdout}\nstderr={proc.stderr}")


def test_toda_task_agendada_no_beat_esta_registrada() -> None:
    """Uma task agendada e nao registrada e um no-op silencioso: o beat despacha,
    o worker recusa com NotRegistered e nada acontece — todo dia, sem alarme."""
    dados = _sondar()
    faltando = [t for t in dados["agendadas"] if t not in dados["registradas"]]
    assert not faltando, (
        "tasks no beat_schedule que o worker NAO registra: "
        f"{faltando}. O beat vai despachar e o worker responder NotRegistered. "
        "Registre o modulo (ver config/celery.py: autodiscover_tasks so pega `tasks.py`)."
    )


def test_beat_agenda_o_backup_diario() -> None:
    """Guarda o proprio agendamento: se alguem remover a entrada, o teste acima
    passaria vazio e a ausencia de backup voltaria a ser invisivel."""
    dados = _sondar()
    assert "backup.perform_database_backup" in dados["agendadas"]
    assert "backup.verify_backup_health" in dados["agendadas"]
