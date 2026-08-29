"""
#1915 — re-chaveia o external_hash das Solicitacoes importadas para incluir o `segmento`.

Ate aqui `_compute_external_hash` (eventos_import.py) omitia o segmento: duas turmas no
mesmo slot (municipio/projeto/tipo/data/hora) diferindo so no segmento geravam o MESMO
hash e o `update_or_create(external_hash=...)` sobrescrevia a primeira em silencio. O fix
acrescenta o segmento a chave; esta migracao recomputa o hash das linhas ja persistidas
para que um proximo import reconheca as mesmas (idempotencia), em vez de trata-las como
novas e duplicar.

ADR-012 congela o ALGORITMO (SHA-1/encoding/delimitador), nao a composicao de campos — por
isso o recipe abaixo e reproduzido INLINE (pinado no tempo desta migracao) e so o helper
congelado `stable_import_hash` e importado.

TIMEZONE TRAP (medido): o hash usa os campos LOCAIS de Fortaleza (data/hora ANTES do
make_aware), mas o banco guarda `inicio`/`fim` em UTC. Recomputar a partir de UTC geraria
um hash diferente do que o importer produz num import futuro -> duplicacao em massa. Por
isso convertemos `inicio`/`fim` de volta para America/Fortaleza antes de extrair data/HH:MM.
"""

from __future__ import annotations

import zoneinfo

from django.db import migrations

TZ = zoneinfo.ZoneInfo("America/Fortaleza")


def _rehash_forward(apps, schema_editor):
    Solicitacao = apps.get_model("core", "Solicitacao")
    # Import do helper congelado (ADR-012) — o algoritmo do digest nao muda.
    from apps.core.imports.hashing import stable_import_hash

    for sol in Solicitacao.objects.exclude(external_hash__isnull=True).iterator():
        if sol.inicio is None or sol.fim is None:
            continue
        # UTC -> Fortaleza: reproduz os campos locais que o importer hasheia.
        local_inicio = sol.inicio.astimezone(TZ)
        local_fim = sol.fim.astimezone(TZ)
        segmento = (sol.segmento or "").strip()
        parts = [
            str(sol.municipio_id),
            str(sol.projeto_id),
            str(sol.tipo_evento_id),
            local_inicio.date().isoformat(),
            local_inicio.strftime("%H:%M"),
            local_fim.strftime("%H:%M"),
            segmento,
        ]
        new_hash = stable_import_hash(*parts)
        if new_hash != sol.external_hash:
            sol.external_hash = new_hash
            sol.save(update_fields=["external_hash"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0100_alter_gerencia_setor_canonico_alter_projeto_setor"),
    ]

    operations = [
        # Reverse = noop: recomputar com a formula antiga (6 campos) faria linhas que so
        # diferem no segmento colidirem no mesmo hash -> IntegrityError no unique. Os hashes
        # novos permanecem identificadores unicos validos; downgrade nao precisa desfaze-los.
        migrations.RunPython(_rehash_forward, migrations.RunPython.noop),
    ]
