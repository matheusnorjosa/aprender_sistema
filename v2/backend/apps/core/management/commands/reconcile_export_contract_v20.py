"""
Management command — reconcile v16→v20 (dry-run-first).

Aplica `reconcile__v16_para_v20.csv` (RELAY-40/41): corrige em prod o que o import
create-only não conserta (reatribuir pessoa, repontar/limpar família, etc.).

Uso:
    # dry-run (padrão, não escreve) — relatório por classe/status:
    python manage.py reconcile_export_contract_v20 --path /tmp/export-contract-v16

    # apply de classes EXPLICITAMENTE permitidas:
    python manage.py reconcile_export_contract_v20 --path ... --apply \
        --allow-class FAMILIA_CORRIGIDA --allow-class FAMILIA_INEXISTENTE

Segurança:
- sem `--apply` → dry-run (só classifica/relata).
- `--apply` só escreve as classes em `--allow-class` (allowlist).
- guardas estritas: lookup determinístico; ambíguo/não-encontrado → skip + report (nunca chuta).
- LINHA_NAO_EMITIDA fica em `manual` (deleção por contagem → decisão humana, não auto-deleta).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportUnknownArgumentType=false

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from django.core.management.base import BaseCommand, CommandError

from apps.core.services.export_contract_v20_reconciler import (
    IMPLEMENTED_CLASSES,
    ExportContractV20Reconciler,
)

if TYPE_CHECKING:
    from argparse import ArgumentParser


class Command(BaseCommand):
    help = "Reconcile v16→v20 (dry-run por padrão; --apply exige --allow-class)."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--path", required=True, help="Diretório com reconcile__v16_para_v20.csv.")
        parser.add_argument(
            "--apply", action="store_true", default=False, help="Executa writes (só das classes em --allow-class)."
        )
        parser.add_argument(
            "--allow-class",
            action="append",
            default=[],
            dest="allow",
            help="Classe permitida para apply (repetível). Sem isto, --apply não escreve.",
        )
        parser.add_argument("--as-user", dest="as_user", default=None, help="CPF do ator (auditoria; opcional).")
        parser.add_argument("--json", action="store_true", default=False, help="Saída em JSON.")

    def _resolve_actor(self, cpf_raw: str | None) -> Any:
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
        bad = sorted(c for c in (opts.get("allow") or []) if c not in IMPLEMENTED_CLASSES)
        if bad:
            raise CommandError(
                f"--allow-class inválida: {', '.join(bad)}. Escrivíveis: {', '.join(sorted(IMPLEMENTED_CLASSES))}."
            )
        actor = self._resolve_actor(opts.get("as_user"))
        reconciler = ExportContractV20Reconciler(
            path=opts["path"],
            apply=opts["apply"],
            allow=tuple(opts["allow"]),
            actor=actor,
        )
        report = reconciler.run()

        if opts["json"]:
            self.stdout.write(json.dumps({s: dict(c) for s, c in report.items()}, ensure_ascii=False, indent=2))
            return

        self.stdout.write(self.style.MIGRATE_HEADING("Reconcile export-contract v16→v20"))
        self.stdout.write(f"  path={opts['path']}  apply={opts['apply']}  allow={sorted(opts['allow'])}")
        for status in sorted(report):
            by_classe = {k: v for k, v in report[status].items() if v}
            if by_classe:
                total = sum(by_classe.values())
                self.stdout.write(f"  [{status}] total={total}  {by_classe}")
        if opts["apply"]:
            applied = sum(report["applied"].values())
            self.stdout.write(self.style.SUCCESS(f"  applied total={applied}"))
        else:
            self.stdout.write(self.style.WARNING("  DRY-RUN: nada escrito. Use --apply --allow-class <classe>."))
