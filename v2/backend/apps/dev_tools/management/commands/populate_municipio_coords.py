"""
Management command to populate Municipio coordinates from CSV file.

Usage:
    python manage.py populate_municipio_coords --dry-run
    python manage.py populate_municipio_coords --apply
"""
import csv
from decimal import Decimal
from pathlib import Path
from typing import Any
from unicodedata import normalize

from django.core.management.base import BaseCommand, CommandParser
from apps.core.models import Municipio


def remove_accents(text: str) -> str:
    """Remove accents from text for fuzzy matching."""
    if not text:
        return ""
    return normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')


class Command(BaseCommand):
    help = "Populate latitude/longitude for Municipio from CSV file"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without saving",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply changes to database",
        )
        parser.add_argument(
            "--csv",
            type=str,
            default="data/municipios_coordenadas.csv",
            help="Path to CSV file with coordinates (relative to backend/)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run: bool = options["dry_run"]
        apply_mode: bool = options["apply"]
        csv_path: str = options["csv"]

        if not dry_run and not apply_mode:
            self.stdout.write(self.style.ERROR("Must specify --dry-run or --apply"))
            return

        mode = "DRY-RUN" if dry_run else "APPLY"
        self.stdout.write(self.style.WARNING(f"Mode: {mode}"))

        # Load CSV coordinates
        base_path = Path(__file__).resolve().parent.parent.parent.parent.parent
        csv_file = base_path / csv_path

        if not csv_file.exists():
            self.stdout.write(self.style.ERROR(f"CSV file not found: {csv_file}"))
            return

        # Read CSV into dict: {(nome_normalized, uf): (lat_decimal, lng_decimal)}
        coords_map: dict[tuple[str, str], tuple[Decimal, Decimal]] = {}
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                nome_str = row.get('nome', '').strip()
                uf_str = row.get('uf', '').strip().upper()
                lat_str = row.get('latitude', '').strip()
                lng_str = row.get('longitude', '').strip()

                # Convert to Decimal immediately
                lat_dec = Decimal(lat_str)
                lng_dec = Decimal(lng_str)

                # Normalize nome for matching (remove accents, lowercase)
                nome_normalized: str = remove_accents(nome_str).lower()
                coords_map[(nome_normalized, uf_str)] = (lat_dec, lng_dec)

        self.stdout.write(f"Loaded {len(coords_map)} coordinates from CSV")

        # Fetch municipalities without coordinates
        municipios = Municipio.objects.filter(
            latitude__isnull=True,
            longitude__isnull=True,
        )

        total = municipios.count()
        self.stdout.write(f"Found {total} municipalities without coordinates")

        success_count: int = 0
        not_found_count: int = 0
        error_count: int = 0
        not_found_list: list[str] = []
        errors: list[str] = []

        for i, municipio in enumerate(municipios, start=1):
            # Skip if no UF
            if not municipio.uf:
                not_found_count += 1
                not_found_list.append(f"{municipio.nome} (No UF)")
                continue

            # Normalize municipio name for matching
            nome_normalized = remove_accents(municipio.nome).lower()
            uf_normalized = municipio.uf.upper()
            key = (nome_normalized, uf_normalized)

            # Try to find coordinates in CSV
            if key in coords_map:
                try:
                    lat_dec, lng_dec = coords_map[key]

                    self.stdout.write(
                        f"[{i}/{total}] ✓ {municipio.nome}-{municipio.uf}: "
                        f"{lat_dec}, {lng_dec}"
                    )

                    if apply_mode:
                        municipio.latitude = lat_dec
                        municipio.longitude = lng_dec
                        municipio.save(update_fields=["latitude", "longitude"])

                    success_count += 1

                except Exception as e:
                    error_count += 1
                    error_msg: str = f"{municipio.nome}-{municipio.uf}: {str(e)}"
                    errors.append(error_msg)
                    self.stdout.write(self.style.ERROR(f"  ✗ {str(e)}"))
            else:
                # Not found in CSV
                not_found_count += 1
                not_found_list.append(f"{municipio.nome}-{municipio.uf}")

        # Summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS(f"✓ Success: {success_count}"))
        self.stdout.write(self.style.WARNING(f"⚠ Not found in CSV: {not_found_count}"))
        self.stdout.write(self.style.ERROR(f"✗ Errors: {error_count}"))

        if not_found_list and not_found_count <= 20:
            self.stdout.write("\nNot found in CSV:")
            for name in not_found_list:
                self.stdout.write(f"  - {name}")

        if errors:
            self.stdout.write("\nErrors:")
            for error in errors:
                self.stdout.write(f"  - {error}")

        if dry_run:
            self.stdout.write(
                self.style.WARNING("\nDRY-RUN: No changes saved to database")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"\nAPPLY: {success_count} coordinates saved")
            )
