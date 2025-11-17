"""
Fix fluxo for projects that should be SUPER.

Based on Acompanhamento de Agenda _ 2025.xlsx aba "Super" mapping.

Projects corrected (4 total):
- LER OUVIR E CONTAR: NAO_SUPER → SUPER
- LER, OUVIR E CONTAR: NAO_SUPER → SUPER
- PROJETO CATAVENTO 2: NAO_SUPER → SUPER
- PROJETO CATAVENTO 3: NAO_SUPER → SUPER

Impact:
- Future Solicitacao for these projects will require manual approval (PA-01 to PA-07)
- Existing Solicitacao with status='aprovado' may have been auto-approved incorrectly
- No data loss, only business rule change

Audit recommendation:
Run this query to check potentially auto-approved solicitações:

  SELECT id, created_at, status, projeto_id
  FROM core_solicitacao
  WHERE projeto_id IN (
    SELECT id FROM core_projeto WHERE nome IN (
      'LER OUVIR E CONTAR',
      'LER, OUVIR E CONTAR',
      'PROJETO CATAVENTO 2',
      'PROJETO CATAVENTO 3'
    )
  )
  AND status = 'aprovado'
  ORDER BY created_at DESC;
"""

from django.db import migrations


def fix_superintendencia_fluxo(apps, schema_editor):
    """Update fluxo from NAO_SUPER to SUPER for 4 projects."""
    # Support both migration context and direct testing
    if apps is None:
        from apps.core.models import Projeto
    else:
        Projeto = apps.get_model("core", "Projeto")

    # Projects that should be SUPER (from aba "Super" in spreadsheet)
    PROJETOS_SUPER = [
        "LER OUVIR E CONTAR",
        "LER, OUVIR E CONTAR",
        "PROJETO CATAVENTO 2",
        "PROJETO CATAVENTO 3",
    ]

    updated_count = 0
    not_found = []

    for nome in PROJETOS_SUPER:
        try:
            projeto = Projeto.objects.get(nome=nome)

            # Only update if currently NAO_SUPER
            if projeto.fluxo == "NAO_SUPER":
                projeto.fluxo = "SUPER"
                projeto.save(update_fields=["fluxo"])
                updated_count += 1
                print(f"✅ Fixed: {nome:50s} NAO_SUPER → SUPER")
            else:
                print(f"⏭️  Skipped (already SUPER): {nome}")

        except Projeto.DoesNotExist:
            not_found.append(nome)
            print(f"⚠️  Not found: {nome}")

    print(f"\n📊 Summary:")
    print(f"  - Updated: {updated_count}/{len(PROJETOS_SUPER)}")
    if not_found:
        print(f"  - Not found: {len(not_found)} ({', '.join(not_found)})")


def reverse_superintendencia_fluxo(apps, schema_editor):
    """Reverse migration: revert fluxo from SUPER back to NAO_SUPER."""
    # Support both migration context and direct testing
    if apps is None:
        from apps.core.models import Projeto
    else:
        Projeto = apps.get_model("core", "Projeto")

    PROJETOS_SUPER = [
        "LER OUVIR E CONTAR",
        "LER, OUVIR E CONTAR",
        "PROJETO CATAVENTO 2",
        "PROJETO CATAVENTO 3",
    ]

    reverted_count = 0

    for nome in PROJETOS_SUPER:
        try:
            projeto = Projeto.objects.get(nome=nome)
            if projeto.fluxo == "SUPER":
                projeto.fluxo = "NAO_SUPER"
                projeto.save(update_fields=["fluxo"])
                reverted_count += 1
                print(f"⏪ Reverted: {nome:50s} SUPER → NAO_SUPER")
        except Projeto.DoesNotExist:
            pass

    print(f"\n📊 Revert summary: {reverted_count}/{len(PROJETOS_SUPER)} reverted")


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0036_consolidate_duplicate_projetos"),
    ]

    operations = [
        migrations.RunPython(
            fix_superintendencia_fluxo,
            reverse_code=reverse_superintendencia_fluxo,
        ),
    ]
