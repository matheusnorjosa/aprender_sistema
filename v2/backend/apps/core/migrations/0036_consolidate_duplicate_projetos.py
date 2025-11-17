"""
Consolidate duplicate Projeto records.

Issue: #150

Merges:
1. "LEIO ESCREVO E CALCULO" → "LEIO, ESCREVO E CALCULO"
2. "Gestão Escolar" → "GESTÃO ESCOLAR"
3. "LER OUVIR E CONTAR" → "LER, OUVIR E CONTAR"

Process:
- Update FK references (Solicitacao, AcaoControle, AcaoDAT, Compra) to canonical project
- Delete duplicate project records
- Preserve all related data

Reversible: No (data consolidation is permanent)
"""

from django.db import migrations


def consolidate_projetos(apps, schema_editor):
    """Consolidate duplicate Projeto records to canonical names."""
    Projeto = apps.get_model("core", "Projeto")
    Solicitacao = apps.get_model("core", "Solicitacao")

    # Try to get optional models (may not exist in all DB states)
    try:
        AcaoControle = apps.get_model("core", "AcaoControle")
    except LookupError:
        AcaoControle = None

    try:
        AcaoDAT = apps.get_model("core", "AcaoDAT")
    except LookupError:
        AcaoDAT = None

    try:
        Compra = apps.get_model("core", "Compra")
    except LookupError:
        Compra = None

    # Consolidation map: canonical_name -> list of duplicate names
    CONSOLIDATIONS = [
        {
            "canonical": "LEIO, ESCREVO E CALCULO",
            "duplicates": ["LEIO ESCREVO E CALCULO"],
            "fluxo": "NAO_SUPER",
        },
        {
            "canonical": "GESTÃO ESCOLAR",
            "duplicates": ["Gestão Escolar"],
            "fluxo": "NAO_SUPER",
        },
        {
            "canonical": "LER, OUVIR E CONTAR",
            "duplicates": ["LER OUVIR E CONTAR"],
            "fluxo": "NAO_SUPER",
        },
    ]

    for consolidation in CONSOLIDATIONS:
        canonical_name = consolidation["canonical"]
        duplicates = consolidation["duplicates"]
        fluxo = consolidation["fluxo"]

        # Get or create canonical project
        canonical, created = Projeto.objects.get_or_create(
            nome=canonical_name,
            defaults={"fluxo": fluxo, "ativo": True}
        )

        if created:
            print(f"✅ Created canonical project: '{canonical_name}'")
        else:
            print(f"ℹ️  Canonical project already exists: '{canonical_name}' (ID: {canonical.id})")

        # Process each duplicate
        for dup_name in duplicates:
            try:
                dup_project = Projeto.objects.get(nome=dup_name)
                print(f"🔄 Processing duplicate: '{dup_name}' (ID: {dup_project.id})")

                # Update FK references
                solicitacao_count = Solicitacao.objects.filter(projeto=dup_project).update(projeto=canonical)
                print(f"   → Updated {solicitacao_count} Solicitacao records")

                if AcaoControle:
                    controle_count = AcaoControle.objects.filter(projeto=dup_project).update(projeto=canonical)
                    print(f"   → Updated {controle_count} AcaoControle records")

                if AcaoDAT:
                    dat_count = AcaoDAT.objects.filter(projeto=dup_project).update(projeto=canonical)
                    print(f"   → Updated {dat_count} AcaoDAT records")

                if Compra:
                    compra_count = Compra.objects.filter(projeto=dup_project).update(projeto=canonical)
                    print(f"   → Updated {compra_count} Compra records")

                # Delete duplicate project
                dup_project.delete()
                print(f"   ✅ Deleted duplicate project: '{dup_name}'")

            except Projeto.DoesNotExist:
                print(f"   ⚠️  Duplicate '{dup_name}' not found in database, skipping")
                continue

    print("\n🎉 Consolidation complete!")


class Migration(migrations.Migration):
    """Data migration to consolidate duplicate projetos."""

    dependencies = [
        ("core", "0035_add_gerencia_model"),
    ]

    operations = [
        migrations.RunPython(consolidate_projetos, migrations.RunPython.noop),
    ]
