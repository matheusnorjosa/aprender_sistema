#!/usr/bin/env python
import os
import sys

import django
from django.apps import apps
from django.db import connection, transaction

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
django.setup()


def get_database_type():
    """Identifica o tipo de banco"""
    return connection.vendor


def analyze_database_schema_sqlite():
    """Analisa o schema do SQLite"""
    print("=== ANÁLISE DO SCHEMA DO BANCO (SQLite) ===")

    with connection.cursor() as cursor:
        # Listar todas as tabelas no SQLite
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )

        tables = cursor.fetchall()
        print(f"Total de tabelas: {len(tables)}")

        schema_info = {
            "database_type": "SQLite",
            "total_tables": len(tables),
            "tables": [],
        }

        for (table_name,) in tables:
            # Obter informações de cada tabela
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()

            # Obter contagem de registros
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = cursor.fetchone()[0]
            except:
                row_count = 0

            table_info = {
                "name": table_name,
                "columns": len(columns),
                "rows": row_count,
                "column_details": [
                    {
                        "id": col[0],
                        "name": col[1],
                        "type": col[2],
                        "not_null": col[3] == 1,
                        "default": col[4],
                        "primary_key": col[5] == 1,
                    }
                    for col in columns
                ],
            }

            schema_info["tables"].append(table_info)
            print(
                f"Tabela: {table_name} - {len(columns)} colunas, {row_count} registros"
            )

        return schema_info


def analyze_indexes_sqlite():
    """Analisa índices do SQLite"""
    print("\n=== ANÁLISE DE ÍNDICES (SQLite) ===")

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index'"
        )

        indexes = cursor.fetchall()
        print(f"Total de índices: {len(indexes)}")

        index_info = {
            "database_type": "SQLite",
            "total_indexes": len(indexes),
            "indexes": [],
        }

        for idx in indexes:
            if idx[0] and not idx[0].startswith("sqlite_"):  # Skip system indexes
                index_info["indexes"].append(
                    {
                        "name": idx[0],
                        "table": idx[1],
                        "definition": idx[2] or "AUTO_INDEX",
                    }
                )

        return index_info


def check_foreign_keys_sqlite():
    """Verifica foreign keys no SQLite"""
    print("\n=== VERIFICAÇÃO DE FOREIGN KEYS (SQLite) ===")

    fk_info = {"database_type": "SQLite", "foreign_keys": [], "total_constraints": 0}

    with connection.cursor() as cursor:
        # Obter todas as tabelas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        for (table_name,) in tables:
            if not table_name.startswith("sqlite_"):
                try:
                    cursor.execute(f"PRAGMA foreign_key_list({table_name})")
                    fks = cursor.fetchall()

                    for fk in fks:
                        fk_info["foreign_keys"].append(
                            {
                                "table": table_name,
                                "column": fk[3],  # from column
                                "references_table": fk[2],  # to table
                                "references_column": fk[4],  # to column
                                "constraint_name": f"fk_{table_name}_{fk[3]}",
                            }
                        )
                        fk_info["total_constraints"] += 1
                except:
                    continue

    print(f'Foreign Keys encontradas: {fk_info["total_constraints"]}')
    return fk_info


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
        try:
            cursor.execute(
                "SELECT app, name, applied FROM django_migrations ORDER BY id"
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

        except Exception as e:
            print(f"Erro ao verificar migrações: {e}")
            migration_info = {"error": str(e)}

        return migration_info


def analyze_data_distribution():
    """Analisa distribuição de dados nas tabelas principais"""
    print("\n=== DISTRIBUIÇÃO DE DADOS ===")

    key_tables = [
        "core_usuario",
        "core_solicitacao",
        "core_projeto",
        "core_municipio",
        "core_formador",
    ]

    data_distribution = {}

    with connection.cursor() as cursor:
        for table in key_tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                data_distribution[table] = {
                    "count": count,
                    "status": "✅ OK" if count > 0 else "⚠️ VAZIO",
                }
                print(f"{table}: {count} registros")
            except Exception as e:
                data_distribution[table] = {
                    "count": 0,
                    "status": "❌ ERRO",
                    "error": str(e),
                }

    return data_distribution


if __name__ == "__main__":
    print("🗄️ INICIANDO ANÁLISE DO BANCO DE DADOS\n")

    try:
        db_type = get_database_type()
        print(f"Tipo de banco detectado: {db_type}")

        schema_analysis = analyze_database_schema_sqlite()
        index_analysis = analyze_indexes_sqlite()
        fk_analysis = check_foreign_keys_sqlite()
        models_analysis = analyze_models_vs_database()
        migration_analysis = check_migrations_status()
        data_analysis = analyze_data_distribution()

        # Compilar relatório final
        database_report = {
            "timestamp": "2025-08-30T15:45:00Z",
            "database_type": db_type,
            "schema_analysis": schema_analysis,
            "index_analysis": index_analysis,
            "foreign_key_analysis": fk_analysis,
            "models_analysis": models_analysis,
            "migration_analysis": migration_analysis,
            "data_distribution": data_analysis,
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
