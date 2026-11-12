"""
Management command — importer do export-contract (dry-run-first).

Uso:
    # dry-run (padrão, não escreve):
    python manage.py import_export_contract --path /caminho/export-contract-2026-06-02-fix1

    # apply create-only de entidades EXPLICITAMENTE permitidas (futuro):
    python manage.py import_export_contract --path ... --apply --allow-entity dat_area

    # contas antes dos eventos, numa execução própria: dry-run, OK do dono, depois o apply de usuario
    python manage.py import_export_contract --path ... --apply --allow-entity usuario

    # produto antes das compras, numa execução própria (create-only): dry-run, o dono aprova a lista
    # `would_create_codigos`, apply de produto, dry-run de novo e só então o apply de dat_compra
    python manage.py import_export_contract --path ... --apply --allow-entity produto
    python manage.py import_export_contract --path ... --apply --allow-entity dat_compra --as-user <cpf>

    # carga da virada (uma só): dry-run, depois apply com solicitacao + participation
    python manage.py import_export_contract --path ... --mode virada
    python manage.py import_export_contract --path ... --mode virada --apply \
        --allow-entity solicitacao --allow-entity participation
    # adoção do Event ID do Google (depois do A5), sozinha, com o arquivo da conferência no Google:
    python manage.py conferir_gcal_adocao --path ... --saida /tmp/conferido.json --operador <id>
    python manage.py import_export_contract --path ... --mode virada --apply --allow-entity gcal_adocao \
        --gcal-verificado /tmp/conferido.json

Segurança:
- sem `--apply` → dry-run (só classifica).
- `--apply` sem `--allow-entity` → BLOQUEADO (nada escrito).
- modo `create-only`: só insere would_create; nunca atualiza; nunca sobrescreve campo protegido.
- modo `virada`: atualiza o evento existente que ninguém mexeu pela tela (plano de 16/10/2026); exige
  `solicitacao` e `participation` juntos, ou `gcal_adocao` sozinha. A carga nunca chama o Google.
- contas primeiro (#2035): a entidade `usuario` entra antes, numa execução própria (dry-run → OK →
  `--apply --allow-entity usuario`), e só depois o ensaio e a carga de `solicitacao` + `participation`. O
  dry-run dos eventos só conhece as contas que já estão no banco; nessa ordem ele bate com o apply.
- produto antes das compras (lote E2, 07/11/2026): `produto` roda sozinho (com outra entidade é erro) e cria só
  o produto real (id curto com `codigo_erp` vazio); a linha do ERP é pulada. O dry-run de `dat_compra` só
  conhece o produto que já está no banco, por isso a ligação das compras sem produto vem numa execução depois.
- `gcal_adocao --apply` exige `--gcal-verificado` (decisão D63): só adota o id que o
  `conferir_gcal_adocao` achou confirmado e na mesma data no Google há menos de 24 h; o resto fica travado.
- pacote fora do contrato (CON-12): arquivo ou coluna obrigatória que falta sai numa linha de ERRO, nada é
  gravado e o comando termina com erro, também no dry-run e com --json (depois de imprimir o relatório).
  `contrato_versao` do manifest só é mostrado, não conferido.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportUnknownArgumentType=false

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from django.core.management.base import BaseCommand, CommandError

from apps.core.services.export_contract_importer import APPLIABLE, ExportContractImporter

if TYPE_CHECKING:
    from argparse import ArgumentParser

# Contagens do lote E2 (produto e ligação das compras), impressas quando não são zero.
# Mensagens do importador para cadastro com chave repetida (ISS-1658): viram CommandError, sem traceback.
_CADASTRO_REPETIDO = (
    "município repetido no cadastro",
    "tipo de evento repetido no cadastro",
    "área do DAT repetida no cadastro",
)

_CONTADORES_DO_PRODUTO = (
    "erp_ja_no_banco",
    "gemeo_no_catalogo",
    "produto_projeto_sem_colecao",
    "produto_de_outro_projeto",
    "produto_nao_resolvido",
    "would_ligar_produto",
    "ligacao_outro_projeto",
    "ligacao_produto_nao_resolvido",
    "sem_produto_fora_do_csv",
    "nk_repetida_no_banco",
    "produto_nao_resolvido_motivos",
)


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
        parser.add_argument(
            "--gcal-verificado",
            dest="gcal_verificado",
            default=None,
            help="JSON do conferir_gcal_adocao. Obrigatório no --apply de gcal_adocao (vale 24 h).",
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

    def _ler_verificado(self, caminho: str | None) -> dict[str, Any] | None:
        """Lê o arquivo do conferir_gcal_adocao ({solicitacao_id: {event_id, verificado_em, ...}})."""
        if not caminho:
            return None
        try:
            with open(caminho, encoding="utf-8") as f:
                dados = json.load(f)
        except (OSError, ValueError) as e:
            raise CommandError(f"--gcal-verificado ilegível: {type(e).__name__}") from e
        if not isinstance(dados, dict):
            raise CommandError("--gcal-verificado: o arquivo tem de ser um objeto JSON")
        return dados

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
            if opts["apply"] and not opts.get("gcal_verificado"):
                raise CommandError(
                    "--allow-entity gcal_adocao --apply exige --gcal-verificado <arquivo>: rode antes"
                    + " o conferir_gcal_adocao, que confere cada Event ID no Google (decisão D63)."
                )
        elif opts["mode"] == "virada" and opts["apply"] and not {"solicitacao", "participation"} <= allow:
            raise CommandError(
                "--mode virada --apply exige --allow-entity solicitacao e --allow-entity participation"
                + " (ou gcal_adocao sozinha)."
            )
        # Lote E2 (F7): o dry-run de dat_compra só enxerga o produto que já está no banco, e o de produto só o
        # projeto que já está no banco. Junto de outra entidade, o apply faria mais do que o dry-run mostrou.
        if "produto" in allow and len(allow) > 1:
            raise CommandError(
                "--allow-entity produto roda sozinha (create-only): primeiro o produto, depois um dry-run novo"
                + " e só então dat_compra."
            )
        actor = self._resolve_actor(opts.get("as_user"))
        importer = ExportContractImporter(
            path=opts["path"],
            mode=opts["mode"],
            apply=opts["apply"],
            allow=tuple(opts["allow"]),
            actor=actor,
            gcal_verificado=self._ler_verificado(opts.get("gcal_verificado")),
        )
        try:
            report = importer.run()
        except ValueError as e:
            # ISS-1658 (#2210): cadastro com chave repetida (município, tipo de evento, área do DAT) para a carga;
            # quem roda lê a mensagem, sem traceback.
            if str(e).startswith(_CADASTRO_REPETIDO):
                raise CommandError(str(e)) from e
            raise

        if opts["json"]:
            self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2))
            _recusar_fora_do_contrato(report)
            return

        self.stdout.write(self.style.MIGRATE_HEADING("Import export-contract"))
        self.stdout.write(f"  path={opts['path']}  mode={report['mode']}  apply={report['apply']}")
        # CON-12: só mostra a versão; conferir o valor depende do combinado com o sheets.banco.
        self.stdout.write(f"  contrato_versao={report['manifest'].get('contrato_versao') or 'ausente'}")
        falta = report["contrato_faltando"]
        for arquivo in falta["arquivos"]:
            self.stdout.write(self.style.ERROR(f"  ERRO: falta o arquivo {arquivo}"))
        for ent, cols in falta["colunas"].items():
            self.stdout.write(self.style.ERROR(f"  ERRO: [{ent}] falta coluna obrigatória: {', '.join(cols)}"))
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
                for chave in _CONTADORES_DO_PRODUTO:
                    if v.get(chave):
                        self.stdout.write(f"    {chave}={v[chave]}")
                for item in v.get("would_create_codigos") or []:
                    # lote E2: a lista que o dono aprova (catálogo, sem dado pessoal)
                    self.stdout.write(f"    would_create_codigos: {item}")
                if v.get("projetos_nao_resolvidos"):
                    self.stdout.write(f"    projetos_nao_resolvidos={v['projetos_nao_resolvidos']}")
                if v.get("solicitante_cpf_sem_cadastro_eventos"):
                    # #2035: evento novo de dono sem conta, para o dono decidir no ensaio (só o evento_id)
                    self.stdout.write(
                        f"    solicitante_cpf_sem_cadastro_eventos={v['solicitante_cpf_sem_cadastro_eventos']}"
                    )
                if v.get("conjunto_incompleto_eventos"):
                    # #2036: evento de dois projetos que fica com um, com o motivo (só evento_id ou s<id>)
                    self.stdout.write(f"    conjunto_incompleto_eventos={v['conjunto_incompleto_eventos']}")
                if v.get("lotacao_perdida_contas"):
                    # #1658: quem a regra antiga lotaria e a nova deixa de fora (só u<id>), para o dono no ensaio
                    self.stdout.write(f"    lotacao_perdida_contas={v['lotacao_perdida_contas']}")
        for ent in ("solicitacao", "gcal_adocao"):
            v = report["por_entidade"].get(ent) or {}
            if v.get("virada"):
                self.stdout.write(f"    [{ent}] virada={v['virada']}")
            if v.get("existente_fora_do_csv"):
                self.stdout.write(f"    [{ent}] existente_fora_do_csv={v['existente_fora_do_csv']}")
        if report["participante_email_cpf_divergente"] or report["participante_cpf_sem_cadastro"]:
            # #2035: pessoa pelo CPF; só ids e contagens, para o dono conferir antes do --apply
            self.stdout.write(
                f"  participante_email_cpf_divergente={report['participante_email_cpf_divergente']}"
                + f" pares={report['participante_email_cpf_divergente_pares']}"
                + f" participante_cpf_sem_cadastro={report['participante_cpf_sem_cadastro']}"
                + f" (e-mail resolveria {report['participante_cpf_sem_cadastro_email_resolveria']}:"
                + f" {report['participante_cpf_sem_cadastro_email_contas']})"
            )
        if report["applied"]:
            self.stdout.write(self.style.SUCCESS(f"  applied({report['mode']})={report['applied']}"))
        if report["apply_solicitante_cpf_sem_cadastro_eventos"]:
            # #2035: o que o apply não criou porque o dono tem CPF válido sem cadastro (só o evento_id)
            self.stdout.write(
                f"  apply_solicitante_cpf_sem_cadastro_eventos={report['apply_solicitante_cpf_sem_cadastro_eventos']}"
            )
        if report["apply_conjunto_incompleto_eventos"]:
            # #2036: o que o apply deixou com um projeto só, para o dono (só evento_id ou s<id>)
            self.stdout.write(f"  apply_conjunto_incompleto_eventos={report['apply_conjunto_incompleto_eventos']}")
        _recusar_fora_do_contrato(report)


def _recusar_fora_do_contrato(report: dict[str, Any]) -> None:
    """CON-12: com arquivo ou coluna faltando, o comando termina com erro (o serviço já não gravou nada)."""
    falta = report["contrato_faltando"]
    partes = [f"falta {a}" for a in falta["arquivos"]]
    partes += [f"{ent}: {', '.join(cols)}" for ent, cols in falta["colunas"].items()]
    if partes:
        fim = "nada gravado" if report["apply"] else "o --apply recusa"
        raise CommandError(f"pacote fora do contrato: {'; '.join(partes)}; {fim}")
