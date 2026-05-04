# pyright: reportAttributeAccessIssue=false, reportUnknownMemberType=false, reportUnknownArgumentType=false

"""
PR 14 hardening RBAC (2026-05-04): mantém `v2/docs/rbac_authorization_matrix.md`
sincronizado com `apps/core/rbac/matrix.py`.

A matriz canônica vive em dois lugares por design:
- **Executável** (`apps/core/rbac/matrix.py:ACCESS_MATRIX`): SSOT consumida
  por tests parametrizados (PR 8 #1313) e snapshot literal (PR 9 #1314).
- **Humana** (`v2/docs/rbac_authorization_matrix.md` §3): prosa para review
  de stakeholder, decisões D1-D17, motivo legítimo de acesso.

Antes do PR 14, a tabela da §3 era editada manualmente — drift silencioso
entre Python e Markdown era possível. Este comando regenera o bloco
delimitado por `<!-- BEGIN AUTOGEN: ACCESS_MATRIX -->` /
`<!-- END AUTOGEN: ACCESS_MATRIX -->` a partir da matriz Python.

Modos:
- `--check` (default): retorna exit 1 se o bloco do doc divergir.
- `--write`: regenera o bloco no doc (idempotente).

A renderização é determinística: ordem de `ACTORS` e `RESOURCES` em
`matrix.py` define o leiaute. Mudar uma célula em ACCESS_MATRIX exige
rodar `--write` para atualizar a doc.

Decisões humanas (D1-D17, prosa de §1/§2/§5/§6/§7) **não** entram no
auto-sync — continuam editáveis manualmente.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.core.rbac.matrix import (
    ACCESS_MATRIX,
    ACTORS,
    ALLOW,
    ALLOW_PAYLOAD_INVALID,
    DENY,
    RESOURCES,
)

BEGIN_MARKER = "<!-- BEGIN AUTOGEN: ACCESS_MATRIX -->"
END_MARKER = "<!-- END AUTOGEN: ACCESS_MATRIX -->"


def _default_doc_path() -> Path:
    """Caminho canônico do doc (resolve relativo a BASE_DIR/.. para
    funcionar tanto em dev quanto em CI)."""
    base = Path(getattr(settings, "BASE_DIR", Path.cwd()))
    return (base.parent / "docs" / "rbac_authorization_matrix.md").resolve()


def _status_cell(status: int) -> str:
    """Mapeia status code → glifo para a célula da tabela."""
    if status == ALLOW:
        return "✅"
    if status == DENY:
        return "🔒"
    if status == ALLOW_PAYLOAD_INVALID:
        return "⚠️ 400"
    return f"❓ ({status})"


def render_matrix_block() -> str:
    """
    Renderiza o bloco markdown autogerado a partir de ACCESS_MATRIX.

    Formato:
    - Header com legenda (status codes canônicos).
    - Tabela: linhas = recursos (em ordem de RESOURCES), colunas = atores
      (em ordem de ACTORS).
    - Cada célula é o status code esperado do gate, mapeado por
      `_status_cell`.
    - Footer com pista de regeneração.

    Determinístico: mesma ACCESS_MATRIX → mesmo output. Idempotente.
    """
    lines: list[str] = []
    lines.append(BEGIN_MARKER)
    lines.append("")
    lines.append(
        "<!-- Bloco autogerado por `python manage.py rbac_matrix_doc --write`. "
        "Não editar manualmente — atualize `apps/core/rbac/matrix.py` -->"
    )
    lines.append("")
    lines.append("Legenda dos status codes (matriz executável):")
    lines.append("")
    lines.append("- ✅ — `ALLOW` (HTTP 200) — gate aprova")
    lines.append("- 🔒 — `DENY` (HTTP 403) — gate nega")
    lines.append(
        "- ⚠️ 400 — `ALLOW_PAYLOAD_INVALID` (HTTP 400) — gate aprova; serviço "
        "rejeita payload por motivo não-RBAC (ex: `ids: []` em batch-approve)"
    )
    lines.append("")

    # Header da tabela.
    header_cells = ["Recurso (método URL)"] + list(ACTORS)
    lines.append("| " + " | ".join(header_cells) + " |")
    lines.append("|" + "|".join(["---"] * len(header_cells)) + "|")

    # Linhas: uma por recurso, ordem de RESOURCES.
    for resource in RESOURCES:
        actor_map = ACCESS_MATRIX.get(resource.name)
        if actor_map is None:
            raise CommandError(
                f"Recurso '{resource.name}' está em RESOURCES mas não em " f"ACCESS_MATRIX. Corrija matrix.py."
            )
        label = f"**{resource.name}** (`{resource.method} {resource.url}`)"
        cells = [label]
        for actor in ACTORS:
            if actor not in actor_map:
                raise CommandError(
                    f"Ator '{actor}' não tem entry para recurso "
                    f"'{resource.name}' em ACCESS_MATRIX. Corrija matrix.py."
                )
            cells.append(_status_cell(actor_map[actor]))
        lines.append("| " + " | ".join(cells) + " |")

    lines.append("")
    lines.append(
        "*Para atualizar este bloco: edite `apps/core/rbac/matrix.py` e rode "
        "`python manage.py rbac_matrix_doc --write` no container backend.*"
    )
    lines.append("")
    lines.append(END_MARKER)
    return "\n".join(lines)


def _split_doc(content: str) -> tuple[str, str, str]:
    """
    Divide o doc em (antes, bloco_atual, depois) usando os marcadores.
    Levanta CommandError se os marcadores estiverem ausentes ou pareados
    incorretamente. O bloco retornado inclui os próprios marcadores.
    """
    begin = content.find(BEGIN_MARKER)
    end = content.find(END_MARKER)
    if begin == -1 or end == -1:
        raise CommandError(
            f"Marcadores autogen ausentes no doc. Esperado:\n" f"  {BEGIN_MARKER}\n  ...\n  {END_MARKER}"
        )
    if end < begin:
        raise CommandError("Marcador END está antes do BEGIN no doc. Verifique manualmente.")
    end_full = end + len(END_MARKER)
    return content[:begin], content[begin:end_full], content[end_full:]


def replace_block(doc_content: str, new_block: str) -> str:
    """Substitui o bloco autogen por `new_block` preservando o resto."""
    before, _, after = _split_doc(doc_content)
    return before + new_block + after


class Command(BaseCommand):
    help = (
        "Sincroniza o bloco autogenerado de v2/docs/rbac_authorization_matrix.md "
        "com apps/core/rbac/matrix.py. Use --check em CI para falhar quando "
        "houver drift; use --write localmente para regenerar."
    )

    def add_arguments(self, parser: Any) -> None:
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--check",
            action="store_true",
            default=True,
            help=(
                "Validar sincronização (default). Exit 1 se o bloco do doc " "divergir do que ACCESS_MATRIX produziria."
            ),
        )
        group.add_argument(
            "--write",
            action="store_true",
            help="Regenerar o bloco no doc (idempotente).",
        )
        parser.add_argument(
            "--doc-path",
            type=str,
            default=None,
            help=(
                "Caminho do doc Markdown. Default resolvido a partir de "
                "BASE_DIR. Útil em testes para apontar arquivo temporário."
            ),
        )

    def handle(self, *args: Any, **options: Any) -> None:
        doc_path = Path(options["doc_path"]).resolve() if options.get("doc_path") else _default_doc_path()
        if not doc_path.exists():
            raise CommandError(f"Doc não encontrado: {doc_path}")

        current_content = doc_path.read_text(encoding="utf-8")
        new_block = render_matrix_block()
        expected_content = replace_block(current_content, new_block)

        if options["write"]:
            if expected_content == current_content:
                self.stdout.write(self.style.SUCCESS(f"OK — doc já estava em sync: {doc_path}"))
                return
            doc_path.write_text(expected_content, encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(f"Bloco atualizado em: {doc_path}"))
            return

        # --check (default)
        if expected_content == current_content:
            self.stdout.write(self.style.SUCCESS(f"OK — doc em sync: {doc_path}"))
            return

        self.stderr.write(
            self.style.ERROR(
                "DRIFT: bloco autogen do doc divergiu de ACCESS_MATRIX.\n"
                f"Doc: {doc_path}\n"
                f"Para corrigir: python manage.py rbac_matrix_doc --write"
            )
        )
        raise CommandError("rbac_matrix_doc --check falhou (drift detectado).")
