"""
Management command — importer do export-contract (dry-run-first).

Uso:
    # dry-run (padrão, não escreve):
    python manage.py import_export_contract --path /caminho/export-contract-2026-06-02-fix1

    # apply create-only de entidades EXPLICITAMENTE permitidas (futuro):
    python manage.py import_export_contract --path ... --apply --allow-entity dat_area

    # carga da virada (uma só): dry-run, depois apply com solicitacao + participation
    python manage.py import_export_contract --path ... --mode virada
    python manage.py import_export_contract --path ... --mode virada --apply \
        --allow-entity solicitacao --allow-entity participation
    # adoção do Event ID do Google (depois do A5), sozinha
    python manage.py import_export_contract --path ... --mode virada --apply --allow-entity gcal_adocao

Segurança:
- sem `--apply` → dry-run (só classifica).
- `--apply` sem `--allow-entity` → BLOQUEADO (nada escrito).
- modo `create-only`: só insere would_create; nunca atualiza; nunca sobrescreve campo protegido.
- modo `virada`: atualiza o evento existente que ninguém mexeu pela tela (plano de 16/10/2026); exige
  `solicitacao` e `participation` juntos, ou `gcal_adocao` sozinha. A carga nunca chama o Google.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportUnknownArgumentType=false

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from django.core.management.base import BaseCommand, CommandError

from apps.core.services.export_contract_importer import APPLIABLE, ExportContractImporter

if TYPE_CHECKING:
    from argparse import ArgumentParser


class Command(BaseCommand):
    help = "Importer do export-contract (dry-run por padrão; --apply exige --allow-entity)."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--path", required=True, help="Diretório do export-contract (com manifest.json).")
        parser.add_argument(
            "--mode",
            default="create-only",
            choices=["create-only", "virada"],
            help="create-only (padrão) ou virada (carga única: atualiza o evento não mexido pela tela).",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            default=False,
            help="Executa writes. Exige --allow-entity; sem allowlist é bloqueado.",
        )
        parser.add_argument(
            "--allow-entity",
            action="append",
            default=[],
            dest="allow",
            help="Entidade permitida para apply (repetível). Sem isto, --apply não escreve.",
        )
        parser.add_argument("--json", action="store_true", default=False, help="Saída em JSON.")
        parser.add_argument(
            "--as-user",
            dest="as_user",
            default=None,
            help="CPF do usuário-ator (created_by) para apply de dat_cadastro/dat_registro.",
        )

    def _resolve_actor(self, cpf_raw: str | None) -> Any:
        """Resolve o Usuario-ator (created_by) pelo CPF. None se não informado."""
        if not cpf_raw:
            return None
        from apps.core.imports.normalization import normalize_cpf_digits
        from apps.core.models import Usuario

        digits = normalize_cpf_digits(cpf_raw)
        actor = Usuario.objects.filter(username=digits).first() or Usuario.objects.filter(cpf=digits).first()
        if actor is None:
            raise CommandError(f"--as-user: usuário com CPF {cpf_raw} não encontrado.")
        return actor

    def handle(self, *args: Any, **opts: Any) -> None:
        # CR-03: barra --allow-entity que aponta entidade não-escrivível (classifica mas não tem apply)
        # ANTES de tocar arquivos — senão o apply mentiria "applied=0" em silêncio.
        bad = sorted(name for name in (opts.get("allow") or []) if name not in APPLIABLE)
        if bad:
            raise CommandError(
                f"--allow-entity não-escrivível: {', '.join(bad)}. " f"Escrivíveis: {', '.join(sorted(APPLIABLE))}."
            )
        # IMP-2: participation só vincula a evento criado na mesma execução; sem solicitacao seria um apply
        # que não grava nada (ou, se mudar, que mexe em evento existente). Barra antes de tocar arquivos.
        allow = set(opts.get("allow") or [])
        if "participation" in allow and "solicitacao" not in allow:
            raise CommandError(
                "--allow-entity participation exige --allow-entity solicitacao na mesma execução"
                + " (participação só vincula a evento criado nesta carga)."
            )
        # Virada: a adoção do Event ID roda sozinha, depois do A5 (gravar Event ID em evento ainda pendente
        # faria o sync apagá-lo no Google). A carga troca formadores dentro da fase da solicitação, então
        # `solicitacao` sem `participation` seria uma carga pela metade.
        if "gcal_adocao" in allow:
            if opts["mode"] != "virada":
                raise CommandError("--allow-entity gcal_adocao exige --mode virada.")
            if allow & {"solicitacao", "participation"}:
                raise CommandError(
                    "--allow-entity gcal_adocao roda sozinha: primeiro a carga (solicitacao + participation),"
                    + " depois o A5, e só então a adoção."
                )
        elif opts["mode"] == "virada" and opts["apply"] and not {"solicitacao", "participation"} <= allow:
            raise CommandError(
                "--mode virada --apply exige --allow-entity solicitacao e --allow-entity participation"
                + " (ou gcal_adocao sozinha)."
            )
        actor = self._resolve_actor(opts.get("as_user"))
        importer = ExportContractImporter(
            path=opts["path"],
            mode=opts["mode"],
            apply=opts["apply"],
            allow=tuple(opts["allow"]),
            actor=actor,
        )
        report = importer.run()

        if opts["json"]:
            self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2))
            return

        self.stdout.write(self.style.MIGRATE_HEADING("Import export-contract"))
        self.stdout.write(f"  path={opts['path']}  mode={report['mode']}  apply={report['apply']}")
        if report["apply_blocked"]:
            self.stdout.write(self.style.WARNING("  ⚠️  --apply BLOQUEADO: forneça --allow-entity. Nada escrito."))
        for ent, v in report["por_entidade"].items():
            if v.get("status") == "not_implemented":
                self.stdout.write(f"  [{ent}] NOT_IMPLEMENTED (rows={v['export_rows']})")
            else:
                linha = (
                    f"  [{ent}] rows={v['export_rows']} create={v['would_create']}"
                    + f" update={v['would_update']} skip={v['would_skip_same']}"
                    + f" protected_diff={v['protected_diff']} reject={v['would_reject']}"
                )
                if v.get("nota"):
                    linha += f" ({v['nota']})"
                self.stdout.write(linha)
                motivos = {k: n for k, n in (v.get("reject_reasons") or {}).items() if n}
                if motivos:
                    self.stdout.write(f"    reject_reasons={motivos}")
                pulos = {k: n for k, n in (v.get("skip_reasons") or {}).items() if n}
                if pulos:
                    self.stdout.write(f"    skip_reasons={pulos}")
                if "would_rekey" in v:
                    self.stdout.write(
                        f"    rekey={v['would_rekey']} rekey_contraditorio={v.get('rekey_contraditorio', 0)}"
                        + f" canceladas_reprovadas={v.get('would_create_cancelada', 0)}"
                    )
                if v.get("projetos_nao_resolvidos"):
                    self.stdout.write(f"    projetos_nao_resolvidos={v['projetos_nao_resolvidos']}")
        for ent in ("solicitacao", "gcal_adocao"):
            v = report["por_entidade"].get(ent) or {}
            if v.get("virada"):
                self.stdout.write(f"    [{ent}] virada={v['virada']}")
            if v.get("existente_fora_do_csv"):
                self.stdout.write(f"    [{ent}] existente_fora_do_csv={v['existente_fora_do_csv']}")
        if report["applied"]:
            self.stdout.write(self.style.SUCCESS(f"  applied({report['mode']})={report['applied']}"))
