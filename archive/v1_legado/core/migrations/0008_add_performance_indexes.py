# Generated manually for performance optimization

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_add_coordenador_permission'),
    ]

    operations = [
        # Adicionar índices compostos para otimizar queries da API dashboard
        migrations.RunSQL(
            # Criar índices
            [
                # Índice para filtro status + data_inicio (query principal)
                'CREATE INDEX IF NOT EXISTS "core_solicitacao_status_data_idx" ON "core_solicitacao" ("status", "data_inicio");',
                
                # Índice para filtro município + data_inicio 
                'CREATE INDEX IF NOT EXISTS "core_solicitacao_municipio_data_idx" ON "core_solicitacao" ("municipio_id", "data_inicio");',
                
                # Índice para filtro projeto + data_inicio
                'CREATE INDEX IF NOT EXISTS "core_solicitacao_projeto_data_idx" ON "core_solicitacao" ("projeto_id", "data_inicio");',
                
                # Índice composto para todos os filtros da API dashboard
                'CREATE INDEX IF NOT EXISTS "core_solicitacao_filtros_idx" ON "core_solicitacao" ("status", "projeto_id", "data_inicio");',
                
                # Índice para formadores ativos (query global)
                'CREATE INDEX IF NOT EXISTS "core_formador_ativo_idx" ON "core_formador" ("ativo");',
            ],
            # Remover índices (rollback)
            [
                'DROP INDEX IF EXISTS "core_solicitacao_status_data_idx";',
                'DROP INDEX IF EXISTS "core_solicitacao_municipio_data_idx";',
                'DROP INDEX IF EXISTS "core_solicitacao_projeto_data_idx";',
                'DROP INDEX IF EXISTS "core_solicitacao_filtros_idx";',
                'DROP INDEX IF EXISTS "core_formador_ativo_idx";',
            ]
        ),
    ]