"""Preenche `Projeto.eh_serie` pela regra que os dropdowns usavam até aqui: nome terminado em número.

Sem exceção nenhuma: no deploy a marca é igual à regra antiga e nenhuma lista muda. As exceções
(projeto numerado que não é série, série sem número) são marcadas depois, por script de dados ou
pela tela Projetos.
"""

from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor


def marcar_series(apps: Apps, schema_editor: BaseDatabaseSchemaEditor | None) -> None:
    Projeto = apps.get_model("core", "Projeto")
    Projeto.objects.filter(nome__regex=r"[0-9]+$").update(eh_serie=True)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0113_projeto_eh_serie"),
    ]

    operations = [
        # Reverso sem efeito: a 0113 remove a coluna.
        migrations.RunPython(marcar_series, migrations.RunPython.noop),
    ]
