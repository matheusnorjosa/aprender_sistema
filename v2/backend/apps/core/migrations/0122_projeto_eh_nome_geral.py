"""Regra da compra (plano de 14/10/2026): marca `Projeto.eh_nome_geral`.

Projeto marcado aceita compra de qualquer projeto da mesma gerência, no mesmo município
(`services/compra_elegibilidade.py`). Só esquema: todo projeto nasce `False`, então nada muda até a
marca ser gravada (tela Projetos ou script com ensaio e OK do dono). A constraint impede série e
nome geral juntos.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0121_matriz_assistente_administrativo_e_dat"),
    ]

    operations = [
        migrations.AddField(
            model_name="projeto",
            name="eh_nome_geral",
            field=models.BooleanField(
                default=False,
                help_text="Nome geral: vale compra de qualquer projeto da mesma gerência (no mesmo município) para liberar este projeto na Nova Solicitação. Não combina com série. Editável na tela Projetos.",
            ),
        ),
        migrations.AddConstraint(
            model_name="projeto",
            constraint=models.CheckConstraint(
                condition=models.Q(("eh_nome_geral", True), ("eh_serie", True), _negated=True),
                name="projeto_serie_nao_e_nome_geral",
            ),
        ),
    ]
