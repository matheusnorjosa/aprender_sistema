"""
Mark test projects with is_test=True.

Test projects (8 total):
- SMOKE SUPER
- SMOKE NAO_SUPER
- TESTE E2E
- Test Detail
- Test Proj
- Test Project
- Teste Auto SUPER
- Teste Auto NAO_SUPER

Impact:
- These projects will be excluded from production listings by default
- Can be included via query param ?include_test=true
- Existing Solicitacao for these projects remain intact
- Only affects visibility in endpoints/dashboards
"""

from django.db import migrations


def mark_test_projects(apps, schema_editor):
    """Mark 8 test projects with is_test=True."""
    # Support both migration context and direct testing
    if apps is None:
        from apps.core.models import Projeto
    else:
        Projeto = apps.get_model("core", "Projeto")

    # Test projects to be hidden from production listings
    TEST_PROJECTS = [
        "SMOKE SUPER",
        "SMOKE NAO_SUPER",
        "TESTE E2E",
        "Test Detail",
        "Test Proj",
        "Test Project",
        "Teste Auto SUPER",
        "Teste Auto NAO_SUPER",
    ]

    marked_count = 0
    not_found = []

    for nome in TEST_PROJECTS:
        try:
            projeto = Projeto.objects.get(nome=nome)

            # Only update if currently is_test=False
            if not projeto.is_test:
                projeto.is_test = True
                projeto.save(update_fields=["is_test"])
                marked_count += 1
                print(f"✅ Marked as test: {nome}")
            else:
                print(f"⏭️  Already test: {nome}")

        except Projeto.DoesNotExist:
            not_found.append(nome)
            print(f"⚠️  Not found: {nome}")

    print(f"\n📊 Summary:")
    print(f"  - Marked: {marked_count}/{len(TEST_PROJECTS)}")
    if not_found:
        print(f"  - Not found: {len(not_found)} ({', '.join(not_found)})")


def unmark_test_projects(apps, schema_editor):
    """Reverse migration: unmark test projects (is_test=True → False)."""
    # Support both migration context and direct testing
    if apps is None:
        from apps.core.models import Projeto
    else:
        Projeto = apps.get_model("core", "Projeto")

    TEST_PROJECTS = [
        "SMOKE SUPER",
        "SMOKE NAO_SUPER",
        "TESTE E2E",
        "Test Detail",
        "Test Proj",
        "Test Project",
        "Teste Auto SUPER",
        "Teste Auto NAO_SUPER",
    ]

    unmarked_count = 0

    for nome in TEST_PROJECTS:
        try:
            projeto = Projeto.objects.get(nome=nome)
            if projeto.is_test:
                projeto.is_test = False
                projeto.save(update_fields=["is_test"])
                unmarked_count += 1
                print(f"⏪ Unmarked test: {nome}")
        except Projeto.DoesNotExist:
            pass

    print(f"\n📊 Revert summary: {unmarked_count}/{len(TEST_PROJECTS)} unmarked")


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0037_fix_superintendencia_fluxo"),
    ]

    operations = [
        migrations.RunPython(
            mark_test_projects,
            reverse_code=unmark_test_projects,
        ),
    ]
