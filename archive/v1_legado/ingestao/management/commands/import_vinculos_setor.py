import csv

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

PAPEIS_VALIDOS = {"FORMADOR", "COORDENADOR", "CONTROLE", "SUPER", "GERENTE"}


class Command(BaseCommand):
    help = (
        "Importa vínculos usuário↔setor a partir de CSV (SSOT). "
        "Colunas: email|nome, setor_sigla|setor_nome, papel (FORMADOR/COORDENADOR/CONTROLE/SUPER/GERENTE), ativo (1/0). "
        "Idempotente por UNIQUE."
    )

    def add_arguments(self, parser):
        parser.add_argument("csv_path")
        parser.add_argument("--sep", default=",")
        parser.add_argument("--email-col", default="email")
        parser.add_argument("--nome-col", default="nome")
        parser.add_argument("--setor-sigla-col", default="setor_sigla")
        parser.add_argument("--setor-nome-col", default="setor_nome")
        parser.add_argument("--papel-col", default="papel")
        parser.add_argument("--ativo-col", default="ativo")
        parser.add_argument("--dry-run", action="store_true")

    @transaction.atomic
    def handle(self, *args, **opts):
        path = opts["csv_path"]
        sep = opts["sep"]
        dry = opts["dry_run"]
        email_col = opts["email_col"]
        nome_col = opts["nome_col"]
        sigla_col = opts["setor_sigla_col"]
        nome_setor_col = opts["setor_nome_col"]
        papel_col = opts["papel_col"]
        ativo_col = opts["ativo_col"]

        User = get_user_model()
        Setor = apps.get_model("core", "Setor")
        Vinculo = apps.get_model("core", "VinculoUsuarioSetor")

        created = updated = skipped = not_found_user = not_found_setor = (
            papel_invalido
        ) = 0

        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=sep)
            for row in reader:
                email = (row.get(email_col) or "").strip().lower()
                nome = (row.get(nome_col) or "").strip()
                sigla = (row.get(sigla_col) or "").strip()
                nome_setor = (row.get(nome_setor_col) or "").strip()
                papel = (row.get(papel_col) or "FORMADOR").strip().upper()
                ativo_str = str(row.get(ativo_col) or "1").strip().lower()
                ativo = ativo_str in {"1", "true", "t", "sim", "yes", "y", "ok", "x"}

                if papel not in PAPEIS_VALIDOS:
                    papel_invalido += 1
                    self.stdout.write(
                        f"[PAPEL INVALIDO] '{papel}' para email={email} nome={nome}"
                    )
                    continue

                user = None
                if email:
                    user = User.objects.filter(email__iexact=email).first()
                if not user and nome:
                    user = User.objects.filter(first_name__iexact=nome).first()

                if not user:
                    not_found_user += 1
                    self.stdout.write(
                        f"[USER NAO ENCONTRADO] email={email} nome={nome}"
                    )
                    continue

                setor = None
                if sigla:
                    setor = Setor.objects.filter(sigla__iexact=sigla).first()
                if not setor and nome_setor:
                    setor = Setor.objects.filter(nome__iexact=nome_setor).first()

                if not setor:
                    not_found_setor += 1
                    self.stdout.write(
                        f"[SETOR NAO ENCONTRADO] sigla={sigla} nome={nome_setor}"
                    )
                    continue

                # Idempotência por UNIQUE(usuario,setor,papel)
                if dry:
                    existing = Vinculo.objects.filter(
                        usuario=user, setor=setor, papel=papel
                    ).first()
                    if existing:
                        if existing.ativo != ativo:
                            updated += 1
                            self.stdout.write(
                                f"[DRY UPDATE] u={user.id} {user.email} -> {setor.sigla}/{setor.nome} papel={papel} ativo={existing.ativo}→{ativo}"
                            )
                        else:
                            skipped += 1
                    else:
                        created += 1
                        self.stdout.write(
                            f"[DRY CREATE] u={user.id} {user.email} -> {setor.sigla}/{setor.nome} papel={papel} ativo={ativo}"
                        )
                else:
                    obj, was_created = Vinculo.objects.get_or_create(
                        usuario=user,
                        setor=setor,
                        papel=papel,
                        defaults={"ativo": ativo},
                    )
                    if was_created:
                        created += 1
                    else:
                        if obj.ativo != ativo:
                            obj.ativo = ativo
                            obj.save(update_fields=["ativo"])
                            updated += 1
                        else:
                            skipped += 1

        if dry:
            self.stdout.write(
                self.style.WARNING(
                    f"[DRY-RUN] Vinculos: created={created} updated={updated} skipped={skipped} "
                    f"not_found_user={not_found_user} not_found_setor={not_found_setor} papel_invalido={papel_invalido}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Vinculos: created={created} updated={updated} skipped={skipped} "
                    f"not_found_user={not_found_user} not_found_setor={not_found_setor} papel_invalido={papel_invalido}"
                )
            )
