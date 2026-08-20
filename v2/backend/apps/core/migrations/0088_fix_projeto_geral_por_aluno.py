"""Data migration: corrige `tipo_calculo_codigos` dos 3 ProjetoGeral por-aluno.

A migration 0045 semeia A COR DA GENTE / ECS / ED FINANCEIRA como `por_aluno` (get_or_create),
mas em bancos onde esses PGs foram criados ANTES por outro caminho — o importer, quando a linha do
contrato nao trazia `tipo_calculo_codigos` — eles herdaram o default do model (`por_professor`), e o
get_or_create create-only da 0045 encontrou-os existentes e nunca corrigiu. O contrato v6
(`projeto_geral.csv`) confirma o valor certo: `aluno_div_divisor`, divisor 20.

Forward-only: `.update()` e idempotente e no-op num banco ja correto (fresh via 0045); corretivo
onde o valor vazou como `por_professor` (ex.: golden dev). Reverse = noop (reverter reintroduziria o
valor errado). Alinha com o calculo per-compra de nr_codigos (#1788): o metodo do PG gateia qual
`compra.tipo` conta — PG so-de-aluno precisa ser `por_aluno` senao o calculo zera os codigos.
"""

from django.db import migrations

# Nomes canonicos (uppercase) exatamente como a 0045 os semeia.
PG_POR_ALUNO = ["A COR DA GENTE", "ECS", "ED FINANCEIRA"]


def fix_por_aluno(apps, schema_editor):
    ProjetoGeral = apps.get_model("core", "ProjetoGeral")
    ProjetoGeral.objects.filter(nome__in=PG_POR_ALUNO).update(
        tipo_calculo_codigos="por_aluno",
        divisor_aluno=20,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0087_add_dat_compra_tipo_conta_para_codigos"),
    ]

    operations = [
        migrations.RunPython(fix_por_aluno, migrations.RunPython.noop),
    ]
