"""
Drop legacy dat_ingest staging tables (#967, #972).

These tables were used by the removed ETL module (apps.dat_ingest).
They contain only temporary staging data — never used in production.

Tables dropped:
- dat_import_log (ETL run tracking)
- stg_usuario (staging users)
- stg_municipio (staging municipalities)
- stg_municipio_ref (staging municipality references)
- stg_projeto (staging projects)
- stg_tipo_evento (staging event types)

Also removes the dat_ingest entries from django_migrations table.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0069_merge_0067_groupclassificacao_0068_clear_default_funcperm_group_links"),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                "DROP TABLE IF EXISTS dat_import_log CASCADE;",
                "DROP TABLE IF EXISTS stg_usuario CASCADE;",
                "DROP TABLE IF EXISTS stg_municipio CASCADE;",
                "DROP TABLE IF EXISTS stg_municipio_ref CASCADE;",
                "DROP TABLE IF EXISTS stg_projeto CASCADE;",
                "DROP TABLE IF EXISTS stg_tipo_evento CASCADE;",
                # Clean up migration history for removed app
                "DELETE FROM django_migrations WHERE app = 'dat_ingest';",
            ],
            reverse_sql=[
                # No reverse — tables were staging-only, data not recoverable
                # To rollback: restore from DB backup
            ],
        ),
    ]
