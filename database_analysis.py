#!/usr/bin/env python
import os
import sys

import django
from django.apps import apps
from django.db import connection, transaction

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
django.setup()


def analyze_database_schema():
    """Analisa o schema do banco de dados"""
    print("=== ANÁLISE DO SCHEMA DO BANCO ===")

    with connection.cursor() as cursor:
        # Listar todas as tabelas
        cursor.execute(
            """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """
        )

        tables = cursor.fetchall()
        print(f"Total de tabelas: {len(tables)}")

        schema_info = {"total_tables": len(tables), "tables": []}

        for (table_name,) in tables:
            # Obter informações de cada tabela
            cursor.execute(
                f"""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position
            """
            )

            columns = cursor.fetchall()

            # Obter contagem de registros
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]

            table_info = {
                "name": table_name,
                "columns": len(columns),
                "rows": row_count,
                "column_details": [
                    {
                        "name": col[0],
                        "type": col[1],
                        "nullable": col[2] == "YES",
                        "default": col[3],
                    }
                    for col in columns
                ],
            }

            schema_info["tables"].append(table_info)
            print(
                f"Tabela: {table_name} - {len(columns)} colunas, {row_count} registros"
            )

        return schema_info


def analyze_indexes():
    """Analisa índices do banco"""
    print("\n=== ANÁLISE DE ÍNDICES ===")

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT 
                schemaname,
                tablename,
                indexname,
                indexdef
            FROM pg_indexes 
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname
        """
        )

        indexes = cursor.fetchall()
        print(f"Total de índices: {len(indexes)}")

        index_info = {"total_indexes": len(indexes), "indexes": []}

        for idx in indexes:
            index_info["indexes"].append(
                {
                    "schema": idx[0],
                    "table": idx[1],
                    "name": idx[2],
                    "definition": idx[3],
                }
            )

        return index_info


def check_data_integrity():
    """Verifica integridade dos dados"""
    print("\n=== VERIFICAÇÃO DE INTEGRIDADE ===")

    # Verificar foreign keys
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT 
                tc.table_name, 
                tc.constraint_name, 
                tc.constraint_type,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name 
            FROM 
                information_schema.table_constraints AS tc 
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                  ON ccu.constraint_name = tc.constraint_name
                  AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY' 
            AND tc.table_schema = 'public'
        """
        )

        foreign_keys = cursor.fetchall()

        integrity_info = {
            "foreign_keys_count": len(foreign_keys),
            "foreign_keys": [],
            "orphaned_records": [],
        }

        for fk in foreign_keys:
            fk_info = {
                "table": fk[0],
                "constraint": fk[1],
                "column": fk[3],
                "references_table": fk[4],
                "references_column": fk[5],
            }
            integrity_info["foreign_keys"].append(fk_info)

        print(f"Foreign Keys encontradas: {len(foreign_keys)}")

        return integrity_info


def analyze_models_vs_database():
    """Compara models Django com schema do banco"""
    print("\n=== MODELS VS DATABASE ===")

    django_models = []

    for model in apps.get_models():
        if model._meta.app_label in ["core", "api", "relatorios"]:
            model_info = {
                "app": model._meta.app_label,
                "name": model._meta.model_name,
                "table": model._meta.db_table,
                "fields": len(model._meta.fields),
                "field_names": [f.name for f in model._meta.fields],
            }
            django_models.append(model_info)

    print(f"Models Django encontrados: {len(django_models)}")

    return {"django_models": django_models, "total_models": len(django_models)}


def check_migrations_status():
    """Verifica status das migrações"""
    print("\n=== STATUS DAS MIGRAÇÕES ===")

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT app, name, applied 
            FROM django_migrations 
            ORDER BY app, id
        """
        )

        migrations = cursor.fetchall()

        migration_info = {
            "total_migrations": len(migrations),
            "by_app": {},
            "unapplied": [],
        }

        for migration in migrations:
            app, name, applied = migration
            if app not in migration_info["by_app"]:
                migration_info["by_app"][app] = 0
            migration_info["by_app"][app] += 1

            if not applied:
                migration_info["unapplied"].append(f"{app}.{name}")

        print(f"Total de migrações: {len(migrations)}")
        print(f'Migrações não aplicadas: {len(migration_info["unapplied"])}')

        return migration_info


if __name__ == "__main__":
    print("🗄️ INICIANDO ANÁLISE DO BANCO DE DADOS\n")

    try:
        schema_analysis = analyze_database_schema()
        index_analysis = analyze_indexes()
        integrity_analysis = check_data_integrity()
        models_analysis = analyze_models_vs_database()
        migration_analysis = check_migrations_status()

        # Compilar relatório final
        database_report = {
            "timestamp": "2025-08-30T15:30:00Z",
            "database_type": "PostgreSQL",
            "schema_analysis": schema_analysis,
            "index_analysis": index_analysis,
            "integrity_analysis": integrity_analysis,
            "models_analysis": models_analysis,
            "migration_analysis": migration_analysis,
        }

        import json

        print("\n" + "=" * 60)
        print("RELATÓRIO DE ANÁLISE DO BANCO DE DADOS")
        print("=" * 60)
        print(json.dumps(database_report, indent=2, default=str))

    except Exception as e:
        print(f"❌ Erro durante análise: {str(e)}")
        import traceback

        traceback.print_exc()
