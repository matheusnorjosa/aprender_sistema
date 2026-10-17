"""
Simulador `rbac_diff` (PR 1, ADR-020): quem ganha e quem perde poder. SOMENTE LEITURA.

Todo PR que muda poder roda isto em produção antes e mostra ao dono o resultado. Não grava
no banco nem no cache, e não imprime dado pessoal: a pessoa aparece só como `u<id>`.

Uso:
    python manage.py rbac_diff --salvar antes.json
    python manage.py rbac_diff --salvar uniao.json --simular-fonte uniao   # o que a volta daria (PR 12)
    python manage.py rbac_diff --comparar antes.json                 # contra o banco de agora
    python manage.py rbac_diff --comparar antes.json --depois depois.json
    python manage.py rbac_diff --diagnostico
    python manage.py rbac_diff --auditar                             # exit 1 se divergir do código

Em produção a raiz do container é só leitura e /tmp (tmpfs) some quando o deploy recria o
container. Por isso o retrato sai do container antes do deploy e volta depois (o JSON não tem
dado pessoal, pode ficar no host da VM). `--salvar -` não serve: o settings imprime uma linha no
stdout ao carregar e sujaria o JSON.
    docker exec <web> python manage.py rbac_diff --salvar /tmp/antes.json
    docker exec <web> cat /tmp/antes.json > antes.json                    # antes do deploy
    docker exec -i <web> sh -c 'cat > /tmp/antes.json' < antes.json       # depois do deploy
    docker exec <web> python manage.py rbac_diff --comparar /tmp/antes.json

Exit 0 quando roda: é relatório, não gate. Arquivo que não dá para ler ou gravar sai com
mensagem legível e exit 1 (CommandError).

`--simular-fonte {uniao,lotacao}` (PR 12, o corte) grava o retrato no modo pedido sem trocar
`RBAC_FONTE`: antes de virar a volta (`RBAC_FONTE=uniao`), compare o retrato de agora com o de
`--simular-fonte uniao`. Quem entrou num grupo DAT, Controle ou Diretoria depois do corte aparece com `+`.
O `--diagnostico` imprime a fonte ativa no cabeçalho.

`--auditar` (D4 do ADR-020) é a exceção que sai com exit 1: quando os pares (grupo, capacidade)
do banco diferem dos do seed (`functional_permissions_seed.py`, que é a matriz) ou quando há
gerência com perfil ≠ PADRAO fora de `PERFIL_PERMITIDO` (`services/rbac_pacotes.py`). Roda no
checklist pós-deploy, junto do `--comparar` (`DEPLOY_CHECKLIST.md`).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.core.services.rbac_permissions import FONTES
from apps.core.services.rbac_snapshot import (
    CAMPOS,
    auditoria_de_matriz,
    diagnostico_de_lotacao,
    diff_snapshots,
    snapshot_de_poder,
)

if TYPE_CHECKING:
    from argparse import ArgumentParser


def _ler(caminho: str) -> dict[str, Any]:
    try:
        return json.loads(Path(caminho).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CommandError(f"rbac_diff: não consegui ler {caminho}: {exc}") from exc


def _item(campo: str, valor: Any) -> str:
    if campo == "vinculos":
        return f"g{valor[0]}:{valor[1]}"
    if campo == "gerencias_escopo":
        return f"g{valor}"
    return str(valor)


class Command(BaseCommand):
    help = "Somente leitura: retrato do poder de cada pessoa e o que cada uma ganha ou perde (sem dado pessoal)"

    def add_arguments(self, parser: ArgumentParser) -> None:
        modo = parser.add_mutually_exclusive_group(required=True)
        modo.add_argument("--salvar", metavar="ARQ.json", help="Grava o retrato de agora em arquivo")
        modo.add_argument("--comparar", metavar="ANTES.json", help="Compara ANTES com DEPOIS (ou com o banco)")
        modo.add_argument("--diagnostico", action="store_true", help="Medições do PR 1 (lotação × grupos)")
        modo.add_argument(
            "--auditar", action="store_true", help="Matriz do banco × seed e perfis de gerência (exit 1 se divergir)"
        )
        parser.add_argument("--depois", metavar="DEPOIS.json", help="Com --comparar: retrato de depois")
        parser.add_argument(
            "--simular-fonte",
            choices=FONTES,
            help="Com --salvar: retrato no modo pedido (uniao = a volta; lotacao = o corte), sem trocar RBAC_FONTE",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if options["depois"] and not options["comparar"]:
            raise CommandError("rbac_diff: --depois só vale com --comparar")
        if options["simular_fonte"] and not options["salvar"]:
            raise CommandError("rbac_diff: --simular-fonte só vale com --salvar")
        if options["salvar"]:
            self._salvar(options["salvar"], options["simular_fonte"])
        elif options["comparar"]:
            antes = _ler(options["comparar"])
            depois = _ler(options["depois"]) if options["depois"] else snapshot_de_poder()
            self.stdout.write(self._texto_diff(diff_snapshots(antes, depois)))
        elif options["auditar"]:
            self._auditar()
        else:
            self.stdout.write(self._texto_diagnostico(diagnostico_de_lotacao()))

    def _auditar(self) -> None:
        auditoria = auditoria_de_matriz()
        rotulos = {
            "so_no_banco": "par (grupo, capacidade) no banco e fora do seed",
            "so_no_seed": "par (grupo, capacidade) no seed e fora do banco",
            "perfis_fora_da_lista": "gerência com perfil fora de PERFIL_PERMITIDO",
        }
        total = 0
        for chave, rotulo in rotulos.items():
            for a, b in auditoria[chave]:
                self.stdout.write(f"  {rotulo}: {a} / {b}")
                total += 1
        resumo = f"rbac_diff --auditar: {total} divergência(s)"
        if total:
            raise CommandError(resumo)
        self.stdout.write(resumo)

    def _salvar(self, caminho: str, fonte: str | None = None) -> None:
        snapshot = snapshot_de_poder(fonte=fonte)
        texto = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        try:
            Path(caminho).write_text(texto, encoding="utf-8")
        except OSError as exc:
            raise CommandError(f"rbac_diff: não consegui gravar {caminho}: {exc} (em prod, use /tmp)") from exc
        self.stdout.write(
            f"rbac_diff: retrato de {len(snapshot)} pessoa(s) ativa(s) gravado em {caminho} "
            f"(fonte: {fonte or settings.RBAC_FONTE}{', simulada' if fonte else ''})"
        )

    @staticmethod
    def _texto_diff(diff: dict[str, Any]) -> str:
        linhas: list[str] = []
        for chave, mudancas in diff["pessoas"].items():
            linhas.append(chave)
            for campo in CAMPOS:
                if campo not in mudancas:
                    continue
                for sinal, lado in (("+", "ganha"), ("−", "perde")):
                    itens = mudancas[campo][lado]
                    if itens:
                        linhas.append(f"  {sinal} {campo}: {', '.join(_item(campo, i) for i in itens)}")
        if diff["entram"]:
            linhas.append(f"entram no retrato: {', '.join(diff['entram'])}")
        if diff["saem"]:
            linhas.append(f"saem do retrato: {', '.join(diff['saem'])}")
        r = diff["resumo"]
        resumo = f"rbac_diff: {r['ganhos']} ganhos, {r['perdas']} perdas"
        if r["pessoas_com_mudanca"]:
            resumo += f" em {r['pessoas_com_mudanca']} pessoa(s)"
        linhas.append(resumo)
        return "\n".join(linhas)

    @staticmethod
    def _texto_diagnostico(diag: dict[str, Any]) -> str:
        linhas = [
            "rbac_diff --diagnostico (somente leitura)",
            f"fonte ativa: {settings.RBAC_FONTE}",
            "",
            "1. setor_canonico de cada gerência:",
        ]
        for gid, setor in diag["setor_canonico"].items():
            linhas.append(f"   g{gid}: {setor or '(vazio)'}")
        linhas.append("2. Gerências CONTROLE e DIRETORIA (por nome ou setor_canonico):")
        for nome, ids in diag["gerencias_controle_diretoria"].items():
            situacao = f"existe ({', '.join(f'g{i}' for i in ids)})" if ids else "não existe"
            linhas.append(f"   {nome}: {situacao}")
        multi, em_varias = diag["pessoas_com_mais_de_um_vinculo"], diag["pessoas_em_mais_de_uma_gerencia"]
        linhas.append(
            f"3. Pessoas ativas com mais de um vínculo vigente: {multi} (em mais de uma gerência: {em_varias})"
        )
        linhas.append("4. Grupo de setor sem vínculo vigente numa gerência do setor:")
        sem = diag["grupo_de_setor_sem_vinculo"]
        if not sem:
            linhas.append("   nenhum")
        for setor, pessoas in sem.items():
            gerencias = ", ".join(f"g{i}" for i in diag["gerencias_por_setor"][setor]) or "nenhuma gerência"
            linhas.append(f"   {setor} ({gerencias}): {len(pessoas)} — {', '.join(pessoas)}")
        for setor, n in diag["setores_sem_gerencia_mapeada"].items():
            linhas.append(f"   {setor}: setor sem gerência mapeada ({n} pessoa(s) no grupo, não avaliadas)")
        return "\n".join(linhas)
