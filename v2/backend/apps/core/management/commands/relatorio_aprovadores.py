"""
Relatório SOMENTE LEITURA de quem passa a aprovar solicitações com o PR B1.

No deploy do B1, todo GERENTE com vínculo vigente na gerência `GERENCIA_APROVADORA_NOME`
passa a aprovar. Rodar ANTES do deploy e conferir a lista nome por nome
(PLANOS_LIBERACAO_2026-09-29 §3, "Dado de produção"). Não grava nada e não imprime
CPF, e-mail, telefone nem username (username é o CPF em produção).

Informações:
1. quantas `Gerencia(nome=GERENCIA_APROVADORA_NOME)` existem (esperado 1) e os ids;
2. os GERENTEs vigentes nela: id, nome, se a conta está ativa e os outros papéis vigentes;
3. a comparação com `Gerencia.gerente` dessa gerência;
4. quantas pessoas aprovam só pelo composite de grupos (Superintendência + Gerente);
5. as pendentes por fluxo (SUPER, NAO_SUPER, sem projeto) e quantas foram criadas pelos
   futuros aprovadores (que não poderão decidi-las — segregação).

Uso:
    python manage.py relatorio_aprovadores
    python manage.py relatorio_aprovadores --json
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from django.core.management.base import BaseCommand
from django.db.models import Count, Q, QuerySet

from apps.core.models import EquipeGerencia, Gerencia, Solicitacao, Usuario
from apps.core.rbac.helpers import APPROVER_COMPOSITES, GERENCIA_APROVADORA_NOME

if TYPE_CHECKING:
    from argparse import ArgumentParser


def _nome(user: Any) -> str:
    """Nome de exibição; NUNCA o username (é o CPF em produção)."""
    return user.get_full_name() or f"#{user.pk}"


def _por_fluxo(qs: QuerySet[Solicitacao]) -> dict[str, int]:
    agg = qs.aggregate(
        SUPER=Count("id", filter=Q(projeto__fluxo="SUPER")),
        NAO_SUPER=Count("id", filter=Q(projeto__fluxo="NAO_SUPER")),
        sem_projeto=Count("id", filter=Q(projeto__isnull=True)),
    )
    return {chave: int(valor or 0) for chave, valor in agg.items()}


class Command(BaseCommand):
    help = "Relatório somente leitura dos aprovadores do PR B1 (sem CPF/e-mail/telefone)"

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--json", action="store_true", help="Saída em JSON")

    def handle(self, *args: Any, **options: Any) -> None:
        dados = self._coletar()
        if options["json"]:
            self.stdout.write(json.dumps(dados, ensure_ascii=False, indent=2))
        else:
            self.stdout.write(self._texto(dados))

    def _coletar(self) -> dict[str, Any]:
        gerencias = list(Gerencia.objects.filter(nome=GERENCIA_APROVADORA_NOME).order_by("id"))
        vinculos = (
            EquipeGerencia.vigentes_em()
            .filter(gerencia__nome=GERENCIA_APROVADORA_NOME, papel="GERENTE")
            .select_related("usuario")
            .order_by("usuario_id")
        )
        aprovadores = {v.usuario_id: v.usuario for v in vinculos}

        outros: dict[int, list[str]] = {uid: [] for uid in aprovadores}
        outros_vinculos = (
            EquipeGerencia.vigentes_em()
            .filter(usuario_id__in=aprovadores)
            .exclude(gerencia__nome=GERENCIA_APROVADORA_NOME, papel="GERENTE")
            .select_related("gerencia")
            .order_by("gerencia__nome", "papel")
        )
        for v in outros_vinculos:
            outros[v.usuario_id].append(f"{v.papel} em {v.gerencia.nome}")

        gerente_cadastrado: dict[str, Any] | None = None
        if len(gerencias) == 1 and gerencias[0].gerente_id is not None:
            gerente = gerencias[0].gerente
            gerente_cadastrado = {
                "id": gerente.pk,
                "nome": _nome(gerente),
                "entre_os_gerentes_vigentes": gerente.pk in aprovadores,
            }

        setor, funcao = APPROVER_COMPOSITES[0]
        so_composite = list(
            Usuario.objects.filter(groups__name=setor)
            .filter(groups__name=funcao)
            .exclude(id__in=aprovadores)
            .order_by("id")
            .values_list("id", flat=True)
            .distinct()
        )

        pendentes = Solicitacao.objects.filter(status="pendente")
        return {
            "gerencia_aprovadora": {
                "nome": GERENCIA_APROVADORA_NOME,
                "quantidade": len(gerencias),
                "ids": [g.pk for g in gerencias],
            },
            "gerentes_vigentes": [
                {
                    "id": uid,
                    "nome": _nome(user),
                    "conta_ativa": user.is_active,
                    "outros_papeis": outros[uid],
                }
                for uid, user in aprovadores.items()
            ],
            "gerente_cadastrado": gerente_cadastrado,
            "so_composite_de_grupos": {"quantidade": len(so_composite), "ids": so_composite},
            "pendentes_por_fluxo": _por_fluxo(pendentes),
            "pendentes_criadas_por_futuros_aprovadores": _por_fluxo(pendentes.filter(usuario_id__in=aprovadores)),
        }

    @staticmethod
    def _texto(dados: dict[str, Any]) -> str:
        ger = dados["gerencia_aprovadora"]
        linhas = ["RELATÓRIO DE APROVADORES (PR B1) — somente leitura", ""]
        linhas.append(f"1. Gerência '{ger['nome']}': {ger['quantidade']} registro(s), ids {ger['ids']} (esperado: 1)")
        if ger["quantidade"] == 0:
            linhas.append("   Nenhuma gerência com esse nome: a regra falha fechada, ninguém novo aprova.")
        linhas.append(f"2. GERENTEs vigentes: {len(dados['gerentes_vigentes'])}")
        for g in dados["gerentes_vigentes"]:
            ativa = "" if g["conta_ativa"] else " [conta inativa]"
            papeis = "; ".join(g["outros_papeis"]) or "nenhum"
            linhas.append(f"   - id {g['id']}: {g['nome']}{ativa} — outros papéis: {papeis}")
        cad = dados["gerente_cadastrado"]
        if cad is None:
            linhas.append("3. Gerencia.gerente: não cadastrado")
        else:
            situacao = "está" if cad["entre_os_gerentes_vigentes"] else "NÃO está"
            linhas.append(
                f"3. Gerencia.gerente: id {cad['id']} ({cad['nome']}) — {situacao} entre os GERENTEs vigentes"
            )
        so = dados["so_composite_de_grupos"]
        linhas.append(f"4. Só no composite de grupos (esperado 0): {so['quantidade']} — ids {so['ids']}")
        linhas.append(f"5. Pendentes por fluxo: {dados['pendentes_por_fluxo']}")
        linhas.append(f"   Criadas pelos futuros aprovadores: {dados['pendentes_criadas_por_futuros_aprovadores']}")
        return "\n".join(linhas)
