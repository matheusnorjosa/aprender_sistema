from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Atualiza materialized views de disponibilidades."

    def handle(self, *args, **opts):
        with connection.cursor() as cur:
            # Sem CONCURRENTLY (requer índice UNIQUE sem WHERE)
            cur.execute("REFRESH MATERIALIZED VIEW mvw_disp_normalizada;")
        self.stdout.write(self.style.SUCCESS("MVW atualizada: mvw_disp_normalizada"))
