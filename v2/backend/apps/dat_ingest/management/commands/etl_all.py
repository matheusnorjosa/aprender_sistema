"""
ETL Command: Orchestrator (etl_load_xlsx → etl_upsert_core + direct imports)
"""

from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import (
    AvailabilityBlock,
    Deslocamento,
    Municipio,
    Participation,
    Projeto,
    Solicitacao,
    TipoEvento,
    Usuario,
)
from apps.dat_ingest.services.parse_acompanhamento import parse_todas_abas_acompanhamento
from apps.dat_ingest.services.parse_bloqueios import parse_bloqueios
from apps.dat_ingest.services.parse_deslocamentos import parse_deslocamentos


class Command(BaseCommand):
    help = "Run full ETL pipeline: load xlsx → upsert to SSOT (idempotent)"

    # ========== HELPER METHODS FOR FK RESOLUTION ==========

    def find_usuario(self, nome: str) -> Usuario | None:
        """
        Find Usuario by name (fuzzy matching)
        Tries: first_name + last_name, then first_name only
        """
        if not nome:
            return None

        nome = nome.strip()
        partes = nome.split()

        if len(partes) >= 2:
            # Try exact match: first_name + last_name
            primeiro = partes[0]
            resto = " ".join(partes[1:])
            usuario = Usuario.objects.filter(
                first_name__iexact=primeiro, last_name__icontains=resto
            ).first()
            if usuario:
                return usuario

        # Try first_name only
        return Usuario.objects.filter(first_name__icontains=nome).first()

    def find_municipio(self, nome_uf: str) -> Municipio | None:
        """
        Find Municipio by "NOME - UF" format
        Examples: "SOBRAL - CE", "FORTALEZA - CE", "AMIGOS DO BEM"
        """
        if not nome_uf:
            return None

        nome_uf = nome_uf.strip()

        # Try split "NOME - UF"
        if " - " in nome_uf:
            partes = nome_uf.split(" - ", 1)
            nome = partes[0].strip()
            uf = partes[1].strip() if len(partes) > 1 else ""

            return Municipio.objects.filter(nome__iexact=nome, uf__iexact=uf).first()

        # Try nome only (without UF)
        return Municipio.objects.filter(nome__iexact=nome_uf).first()

    def find_projeto(self, nome: str) -> Projeto | None:
        """
        Find Projeto by nome (case-insensitive with fuzzy matching)
        Handles common variations:
        - "ACerta" → "ACERTA MATEMÁTICA" or "ACERTA PORTUGUÊS"
        - "Superativar" → "SUPERATIVAR - LINGUAGENS" or "SUPERATIVAR - MATEMÁTICA"
        - "Vida & X" → "VIDA E X"
        - "LEIO ESCREVO E CALCULO" → "LEIO, ESCREVO E CALCULO"
        - "Escrever Comunicar e Ser" → "ECS"
        """
        if not nome:
            return None

        nome_original = nome.strip()

        # Try exact match first
        projeto = Projeto.objects.filter(nome__iexact=nome_original).first()
        if projeto:
            return projeto

        # Normalize nome for fuzzy matching
        nome_norm = nome_original.upper()

        # Map common variations
        if "ACERTA" in nome_norm:
            # Try ACERTA MATEMÁTICA first (more common)
            projeto = Projeto.objects.filter(nome__icontains="ACERTA").first()
            if projeto:
                return projeto

        if "SUPERATIVAR" in nome_norm:
            # Try any SUPERATIVAR variant
            projeto = Projeto.objects.filter(nome__icontains="SUPERATIVAR").first()
            if projeto:
                return projeto

        if "VIDA &" in nome_norm or "VIDA E" in nome_norm:
            # Replace & with E
            nome_norm = nome_norm.replace(" & ", " E ")
            projeto = Projeto.objects.filter(nome__iexact=nome_norm).first()
            if projeto:
                return projeto

        if nome_norm == "LEIO ESCREVO E CALCULO":
            return Projeto.objects.filter(nome__iexact="LEIO, ESCREVO E CALCULO").first()

        if "ESCREVER COMUNICAR" in nome_norm:
            return Projeto.objects.filter(nome__iexact="ECS").first()

        if "IDEB10" in nome_norm or "IDEB 10" in nome_norm:
            return Projeto.objects.filter(nome__iexact="GESTÃO ESCOLAR").first()

        # Try partial match as last resort
        return Projeto.objects.filter(nome__icontains=nome_original).first()

    # ========== IMPORTER METHODS ==========

    def import_bloqueios(self, data_dir: Path, dry_run: bool = False, force: bool = False):
        """Import availability blocks from Disponibilidade spreadsheet"""
        filepath = data_dir / "Cópia de Disponibilidade _ 2025.xlsx"

        if not filepath.exists():
            self.stdout.write(self.style.WARNING(f"  [SKIP] File not found: {filepath.name}"))
            return

        self.stdout.write(f"\n[Bloqueios] Parsing {filepath.name}...")
        bloqueios_data = parse_bloqueios(filepath)
        self.stdout.write(f"  Found {len(bloqueios_data)} bloqueios")

        created = 0
        skipped = 0
        errors = 0

        for b in bloqueios_data:
            formador = self.find_usuario(b["formador_nome"])

            if not formador:
                errors += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"  ⚠ Formador not found: {b['formador_nome']} (row {b['rownum']})"
                    )
                )
                continue

            if dry_run:
                created += 1
                continue

            try:
                # Check if already exists (idempotency)
                exists = AvailabilityBlock.objects.filter(
                    usuario=formador, tipo=b["tipo"], inicio=b["inicio"], fim=b["fim"]
                ).exists()

                if exists and not force:
                    skipped += 1
                    continue

                AvailabilityBlock.objects.create(
                    usuario=formador,
                    tipo=b["tipo"],
                    inicio=b["inicio"],
                    fim=b["fim"],
                    motivo=b["motivo"],
                )
                created += 1

            except Exception as e:
                errors += 1
                self.stdout.write(
                    self.style.ERROR(f"  ✗ Error creating bloqueio (row {b['rownum']}): {e}")
                )

        self.stdout.write(
            f"  Bloqueios: {created} created, {skipped} skipped, {errors} errors"
        )

    def import_deslocamentos(self, data_dir: Path, dry_run: bool = False, force: bool = False):
        """Import travel/displacement records from Disponibilidade spreadsheet"""
        filepath = data_dir / "Cópia de Disponibilidade _ 2025.xlsx"

        if not filepath.exists():
            self.stdout.write(self.style.WARNING(f"  [SKIP] File not found: {filepath.name}"))
            return

        self.stdout.write(f"\n[Deslocamentos] Parsing {filepath.name}...")
        deslocamentos_data = parse_deslocamentos(filepath)
        self.stdout.write(f"  Found {len(deslocamentos_data)} deslocamentos")

        created = 0
        skipped = 0
        errors = 0

        for d in deslocamentos_data:
            formador = self.find_usuario(d["formador_nome"])
            origem = self.find_municipio(d["origem_nome_uf"])
            destino = self.find_municipio(d["destino_nome_uf"])

            if not formador:
                errors += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"  ⚠ Formador not found: {d['formador_nome']} (row {d['rownum']})"
                    )
                )
                continue

            if not origem:
                errors += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"  ⚠ Origem not found: {d['origem_nome_uf']} (row {d['rownum']})"
                    )
                )
                continue

            if not destino:
                errors += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"  ⚠ Destino not found: {d['destino_nome_uf']} (row {d['rownum']})"
                    )
                )
                continue

            if dry_run:
                created += 1
                continue

            try:
                # Check if already exists (idempotency)
                exists = Deslocamento.objects.filter(
                    usuario=formador,
                    origem=origem.nome,
                    destino=destino.nome,
                    start_date=d["saida"].date(),
                    end_date=d["chegada"].date(),
                ).exists()

                if exists and not force:
                    skipped += 1
                    continue

                Deslocamento.objects.create(
                    usuario=formador,
                    origem=origem.nome,
                    destino=destino.nome,
                    start_date=d["saida"].date(),
                    end_date=d["chegada"].date(),
                    duracao_minutos=d["duracao_minutos"],
                    meio_transporte=d["meio_transporte"],
                )
                created += 1

            except Exception as e:
                errors += 1
                self.stdout.write(
                    self.style.ERROR(f"  ✗ Error creating deslocamento (row {d['rownum']}): {e}")
                )

        self.stdout.write(
            f"  Deslocamentos: {created} created, {skipped} skipped, {errors} errors"
        )

    def import_solicitacoes(self, data_dir: Path, dry_run: bool = False, force: bool = False):
        """Import solicitações from Acompanhamento spreadsheet (5 tabs)"""
        filepath = data_dir / "Cópia de Acompanhamento de Agenda _ 2025.xlsx"

        if not filepath.exists():
            self.stdout.write(self.style.WARNING(f"  [SKIP] File not found: {filepath.name}"))
            return

        # Get or create default TipoEvento for imports
        tipo_evento_default, _ = TipoEvento.objects.get_or_create(
            nome="Evento Genérico", defaults={"descricao": "Tipo padrão para eventos importados", "cor": "#808080"}
        )

        # Get or create default Usuario for imports (coordenador missing/not found)
        usuario_default, _ = Usuario.objects.get_or_create(
            username="etl_import_default",
            defaults={
                "email": "etl.import@aprender.system",
                "first_name": "ETL",
                "last_name": "Import",
                "cpf": "99999999999",
                "is_active": False,  # Not a real user
            },
        )

        self.stdout.write(f"\n[Solicitações] Parsing {filepath.name}...")
        solicitacoes_data = parse_todas_abas_acompanhamento(filepath)
        self.stdout.write(f"  Found {len(solicitacoes_data)} solicitações")

        created_solicitacoes = 0
        created_participations = 0
        skipped = 0
        errors = 0

        for s in solicitacoes_data:
            municipio = self.find_municipio(s["municipio_nome_uf"])
            projeto = self.find_projeto(s["projeto_nome"])
            coordenador = self.find_usuario(s["coordenador_nome"]) if s["coordenador_nome"] else None

            if not municipio:
                errors += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"  ⚠ Município not found: {s['municipio_nome_uf']} (row {s['rownum']})"
                    )
                )
                continue

            if not projeto:
                errors += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"  ⚠ Projeto not found: {s['projeto_nome']} (row {s['rownum']})"
                    )
                )
                continue

            if dry_run:
                created_solicitacoes += 1
                created_participations += len(s["formadores"])
                continue

            try:
                # Check if already exists (idempotency by municipio + projeto + inicio + fim)
                solicitacao = Solicitacao.objects.filter(
                    municipio=municipio,
                    projeto=projeto,
                    inicio=s["inicio"],
                    fim=s["fim"],
                ).first()

                if solicitacao and not force:
                    skipped += 1
                    # Even if solicitação exists, create missing participations
                    for formador_nome in s["formadores"]:
                        formador = self.find_usuario(formador_nome)
                        if formador:
                            # Check if participation already exists
                            if not Participation.objects.filter(
                                solicitacao=solicitacao, usuario=formador, role="FORMADOR"
                            ).exists():
                                Participation.objects.create(
                                    solicitacao=solicitacao, usuario=formador, role="FORMADOR"
                                )
                                created_participations += 1
                    continue

                # Create Solicitacao (use default user if coordenador not found)
                solicitacao = Solicitacao.objects.create(
                    usuario=coordenador or usuario_default,
                    municipio=municipio,
                    projeto=projeto,
                    tipo_evento=tipo_evento_default,
                    tipo=s["tipo"],
                    encontro=s["encontro"],
                    segmento=s["segmento"],
                    coordenador_acompanha=s["coordenador_acompanha"],
                    coordenador=coordenador,
                    inicio=s["inicio"],
                    fim=s["fim"],
                    status=s["status"],
                )
                created_solicitacoes += 1

                # Create Participations for each formador
                for formador_nome in s["formadores"]:
                    formador = self.find_usuario(formador_nome)
                    if formador:
                        Participation.objects.create(
                            solicitacao=solicitacao, usuario=formador, role="FORMADOR"
                        )
                        created_participations += 1
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  ⚠ Formador not found for participation: {formador_nome}"
                            )
                        )

            except Exception as e:
                errors += 1
                self.stdout.write(
                    self.style.ERROR(f"  ✗ Error creating solicitação (row {s['rownum']}): {e}")
                )

        self.stdout.write(
            f"  Solicitações: {created_solicitacoes} created, {skipped} skipped, {errors} errors"
        )
        self.stdout.write(f"  Participations: {created_participations} created")

    # ========== MAIN HANDLER ==========

    def add_arguments(self, parser):
        parser.add_argument(
            "--dir",
            type=str,
            default=getattr(settings, "DATA_IMPORT_DIR", "/app/data/csv-import"),
            help="Directory with .xlsx files",
        )
        parser.add_argument("--dry-run", action="store_true", help="Simulate without writing to DB")
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force re-import even if records already exist (skip idempotency check)",
        )
        parser.add_argument(
            "--only",
            choices=["usuarios", "municipios", "projetos", "tipos"],
            help="Process only specific entity type",
        )

    def handle(self, *args, **options):
        directory = Path(options["dir"])
        dry_run = options["dry_run"]
        only = options["only"]
        force = options.get("force", False)

        if dry_run:
            self.stdout.write(self.style.WARNING("\n[DRY-RUN MODE] No changes will be saved\n"))

        if not directory.exists():
            self.stdout.write(self.style.ERROR(f"Directory not found: {directory}"))
            return

        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(self.style.SUCCESS("ETL PIPELINE START"))
        self.stdout.write(self.style.SUCCESS("=" * 80))

        # Step 1: Load .xlsx → staging tables
        self.stdout.write(
            self.style.SUCCESS("\n[STEP 1/5] Loading .xlsx files to staging tables...")
        )
        call_command(
            "etl_load_xlsx",
            dir=str(directory),
            dry_run=dry_run,
            only=only,
        )

        # Step 2: Upsert staging → SSOT tables
        self.stdout.write(
            self.style.SUCCESS("\n[STEP 2/5] Upserting staging → SSOT tables...")
        )
        call_command(
            "etl_upsert_core",
            dry_run=dry_run,
            only=only,
        )

        # Step 3: Import Solicitações (direct to core, no staging)
        self.stdout.write(self.style.SUCCESS("\n[STEP 3/5] Importing Solicitações..."))
        self.import_solicitacoes(directory, dry_run=dry_run, force=force)

        # Step 4: Import Bloqueios (direct to core, no staging)
        self.stdout.write(self.style.SUCCESS("\n[STEP 4/5] Importing Bloqueios..."))
        self.import_bloqueios(directory, dry_run=dry_run, force=force)

        # Step 5: Import Deslocamentos (direct to core, no staging)
        self.stdout.write(self.style.SUCCESS("\n[STEP 5/5] Importing Deslocamentos..."))
        self.import_deslocamentos(directory, dry_run=dry_run, force=force)

        self.stdout.write(self.style.SUCCESS("\n" + "=" * 80))
        self.stdout.write(self.style.SUCCESS("ETL PIPELINE COMPLETE"))
        self.stdout.write(self.style.SUCCESS("=" * 80))
