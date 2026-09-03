"""Coordenador do PlanoFormacoes vira relação N:N (co-liderança).

Um plano pode ter N coordenadores conduzindo o MESMO ciclo (co-liderança); a chave natural
(municipio, projeto, ano) continua identificando UM plano — o coordenador passa de FK única a M2M.
Motivação: a fonte tem 2 grupos de UNIÃO DOS PALMARES e 33 de VIDA E MATEMÁTICA ("Elienai & Silvio")
que hoje colapsam porque diferem só no coordenador. A medição do sheets.banco (RELAY 32/34) confirmou
co-liderança da mesma formação; expandir a chave inflaria a CH — a leitura fiel é 1 plano, N coordenadores.

Ordem das operações (importa): libera o related_name do FK antigo → remove o índice que referencia a
coluna do FK → adiciona o M2M → backfill FK→M2M (na MESMA migração, antes de dropar o FK) → remove o FK.
"""

from django.conf import settings
from django.db import migrations, models


def backfill_coordenadores(apps, schema_editor):
    """Copia o coordenador (FK única) para o M2M, preservando o dado existente."""
    PlanoFormacoes = apps.get_model("core", "PlanoFormacoes")
    for plano in PlanoFormacoes.objects.filter(coordenador__isnull=False).iterator():
        plano.coordenadores.add(plano.coordenador_id)


def reverse_backfill(apps, schema_editor):
    """Reverso best-effort: o primeiro coordenador do M2M volta para o FK (perde os demais)."""
    PlanoFormacoes = apps.get_model("core", "PlanoFormacoes")
    for plano in PlanoFormacoes.objects.iterator():
        first = plano.coordenadores.first()
        if first is not None:
            plano.coordenador_id = first.id
            plano.save(update_fields=["coordenador"])


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0104_solicitante_procedencia_relax_apoio"),
    ]

    operations = [
        # 1. Libera o related_name "planos_coordenados" para o M2M reusar (o FK será removido no fim).
        migrations.AlterField(
            model_name="planoformacoes",
            name="coordenador",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="planos_coordenados_legacy",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Coordenador Responsavel",
            ),
        ),
        # 2. Remove o índice composto que referencia a coluna do FK (M2M não tem coluna local).
        migrations.RemoveIndex(
            model_name="planoformacoes",
            name="core_plano__coorden_739349_idx",
        ),
        # 3. Adiciona o M2M.
        migrations.AddField(
            model_name="planoformacoes",
            name="coordenadores",
            field=models.ManyToManyField(
                blank=True,
                related_name="planos_coordenados",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Coordenadores",
            ),
        ),
        # 4. Backfill FK → M2M (antes de dropar o FK).
        migrations.RunPython(backfill_coordenadores, reverse_backfill),
        # 5. Remove o FK antigo.
        migrations.RemoveField(
            model_name="planoformacoes",
            name="coordenador",
        ),
    ]
