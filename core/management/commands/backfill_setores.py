import csv

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Backfill de setores e vínculos a partir de CSV. Colunas: "
        "email|nome, setor_sigla|setor_nome, papel(opcional: FORMADOR/COORDENADOR/CONTROLE/SUPER), ativo(1/0)."
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
        parser.add_argument(
            "--update-user-fk",
            action="store_true",
            help="Se existir user.setor, atualizar também",
        )
        parser.add_argument("--dry-run", action="store_true")

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
        update_user_fk = opts["update_user_fk"]

        User = get_user_model()
        Setor = apps.get_model("core", "Setor")
        Vinculo = apps.get_model("core", "VinculoUsuarioSetor")

        created = 0
        updated = 0
        not_found_user = 0
        not_found_setor = 0

        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=sep)
            for row in reader:
                email = (row.get(email_col) or "").strip().lower()
                nome = (row.get(nome_col) or "").strip()
                sigla = (row.get(sigla_col) or "").strip()
                nome_setor = (row.get(nome_setor_col) or "").strip()
                papel = (row.get(papel_col) or "FORMADOR").strip().upper()
                ativo = (row.get(ativo_col) or "1").strip() in {
                    "1",
                    "true",
                    "t",
                    "sim",
                    "yes",
                    "y",
                    "ok",
                    "x",
                }

                user = User.objects.filter(email=email).first() if email else None
                if not user and nome:
                    user = User.objects.filter(first_name__iexact=nome).first()
                if not user:
                    not_found_user += 1
                    self.stdout.write(f"USER NOT FOUND: email={email} nome={nome}")
                    continue

                setor = None
                if sigla:
                    setor = Setor.objects.filter(sigla__iexact=sigla).first()
                if not setor and nome_setor:
                    setor = Setor.objects.filter(nome__iexact=nome_setor).first()
                if not setor:
                    not_found_setor += 1
                    self.stdout.write(
                        f"SETOR NOT FOUND: sigla={sigla} nome={nome_setor}"
                    )
                    continue

                if dry:
                    self.stdout.write(
                        f"DRY: vincular {user.id} -> {setor.sigla}/{setor.nome} papel={papel} ativo={ativo}"
                    )
                    continue

                obj, created_flag = Vinculo.objects.get_or_create(
                    usuario=user, setor=setor, papel=papel, defaults={"ativo": ativo}
                )
                if not created_flag:
                    if obj.ativo != ativo:
                        obj.ativo = ativo
                        obj.save(update_fields=["ativo"])
                        updated += 1
                else:
                    created += 1

                if (
                    update_user_fk
                    and hasattr(user, "setor_id")
                    and (user.setor_id != setor.id)
                ):
                    type(user).objects.filter(pk=user.pk).update(setor_id=setor.id)

        self.stdout.write(
            self.style.SUCCESS(
                f"Backfill: created={created} updated={updated} not_found_user={not_found_user} not_found_setor={not_found_setor}"
            )
        )
