from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Aplica dicionário de aliases à tabela de staging agregada, preenchendo matched_user_id quando possível."

    def add_arguments(self, parser):
        parser.add_argument(
            "--staging",
            required=True,
            help="Tabela staging agregada (ex.: disp_staging_agregada)",
        )
        parser.add_argument(
            "--user-col", default="raw_user", help="Coluna texto do usuário na staging"
        )

    def handle(self, *args, **opts):
        staging = opts["staging"]
        user_col = opts["user_col"]

        sql = f"""
        UPDATE {staging} s
        SET matched_user_id = ua.usuario_id
        FROM core_usuarioalias ua
        WHERE s.matched_user_id IS NULL
          AND LOWER(TRIM(s.{user_col})) = LOWER(TRIM(ua.alias));
        """

        with connection.cursor() as cur:
            cur.execute(sql)

        self.stdout.write(self.style.SUCCESS(f"Aliases aplicados em {staging}"))
