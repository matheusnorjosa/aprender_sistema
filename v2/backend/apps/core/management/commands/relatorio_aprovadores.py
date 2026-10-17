"""
Relatório SOMENTE LEITURA de quem aprova solicitações, por base (PR B1; reescrito no PR 11).

É o retrato de `solicitation_approval_basis`, a fonte única de quem aprova: para cada conta, a base
(`superuser`, `gerente_superintendencia` ou `capacidade_aprovar`). Prova o critério da Onda 2 ("os
aprovadores são exatamente os esperados"). Rodar antes e depois do deploy de mudança de poder e conferir
os ids na tela Usuários.

A base `capacidade_aprovar` é calculada sem cache (`capacidades_sem_cache`): o relatório não depende do
`bump_functional_permissions_cache_version()` do deploy nem enche o cache de produção. Não grava nada e
não imprime nome, CPF, e-mail, telefone nem username (username é o CPF em produção): só `u<id>`.

Informações:
1. quantas `Gerencia(nome=GERENCIA_APROVADORA_NOME)` existem (esperado 1) e os ids;
2. os GERENTEs vigentes nela: id, se a conta está ativa e os outros papéis vigentes;
3. a comparação com `Gerencia.gerente` dessa gerência;
4. os aprovadores por base (contas ativas) e as contas inativas que aprovariam se reativadas;
5. as pendentes por fluxo (SUPER, NAO_SUPER, sem projeto) e quantas foram criadas pelos aprovadores
   (que não podem decidi-las — segregação).

Uso:
    python manage.py relatorio_aprovadores
    python manage.py relatorio_aprovadores --json
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, get_args

from django.core.management.base import BaseCommand
from django.db.models import Count, Q, QuerySet

from apps.core.models import EquipeGerencia, Gerencia, Solicitacao, Usuario
from apps.core.rbac.helpers import GERENCIA_APROVADORA_NOME
from apps.core.rbac.policies import SolicitationApprovalBasis, solicitation_approval_basis
from apps.core.services.rbac_permissions import capacidades_sem_cache

if TYPE_CHECKING:
    from argparse import ArgumentParser


def _por_fluxo(qs: QuerySet[Solicitacao]) -> dict[str, int]:
    agg = qs.aggregate(
        SUPER=Count("id", filter=Q(projeto__fluxo="SUPER")),
        NAO_SUPER=Count("id", filter=Q(projeto__fluxo="NAO_SUPER")),
        sem_projeto=Count("id", filter=Q(projeto__isnull=True)),
    )
    return {chave: int(valor or 0) for chave, valor in agg.items()}


def _base(user: Usuario) -> SolicitationApprovalBasis | None:
    return solicitation_approval_basis(user, capacidades=capacidades_sem_cache(user.pk))


class Command(BaseCommand):
    help = "Relatório somente leitura de quem aprova solicitações, por base (só u<id>)"

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
        gerentes = {v.usuario_id: v.usuario for v in vinculos}

        outros: dict[int, list[str]] = {uid: [] for uid in gerentes}
        outros_vinculos = (
            EquipeGerencia.vigentes_em()
            .filter(usuario_id__in=gerentes)
            .exclude(gerencia__nome=GERENCIA_APROVADORA_NOME, papel="GERENTE")
            .select_related("gerencia")
            .order_by("gerencia__nome", "papel")
        )
        for v in outros_vinculos:
            outros[v.usuario_id].append(f"{v.papel} em {v.gerencia.nome}")

        gerente_cadastrado: dict[str, Any] | None = None
        if len(gerencias) == 1 and gerencias[0].gerente_id is not None:
            gerente_cadastrado = {
                "id": gerencias[0].gerente_id,
                "entre_os_gerentes_vigentes": gerencias[0].gerente_id in gerentes,
            }

        por_base: dict[str, list[int]] = {base: [] for base in get_args(SolicitationApprovalBasis)}
        inativas: list[int] = []
        for user in Usuario.objects.order_by("id"):
            base = _base(user)
            if base is None:
                continue
            if user.is_active:
                por_base[base].append(user.pk)
            else:
                inativas.append(user.pk)
        aprovadores = [uid for ids in por_base.values() for uid in ids]

        pendentes = Solicitacao.objects.filter(status="pendente")
        return {
            "gerencia_aprovadora": {
                "nome": GERENCIA_APROVADORA_NOME,
                "quantidade": len(gerencias),
                "ids": [g.pk for g in gerencias],
            },
            "gerentes_vigentes": [
                {"id": uid, "conta_ativa": user.is_active, "outros_papeis": outros[uid]}
                for uid, user in gerentes.items()
            ],
            "gerente_cadastrado": gerente_cadastrado,
            "aprovadores_por_base": por_base,
            "inativas_que_aprovariam_se_reativadas": inativas,
            "pendentes_por_fluxo": _por_fluxo(pendentes),
            "pendentes_criadas_por_aprovadores": _por_fluxo(pendentes.filter(usuario_id__in=aprovadores)),
        }

    @staticmethod
    def _texto(dados: dict[str, Any]) -> str:
        def ids(lista: list[int]) -> str:
            return ", ".join(f"u{uid}" for uid in lista) or "nenhum"

        ger = dados["gerencia_aprovadora"]
        linhas = ["RELATÓRIO DE APROVADORES — somente leitura (fonte: solicitation_approval_basis)", ""]
        linhas.append(f"1. Gerência '{ger['nome']}': {ger['quantidade']} registro(s), ids {ger['ids']} (esperado: 1)")
        if ger["quantidade"] == 0:
            linhas.append(
                "   Nenhuma gerência com esse nome: a base por vínculo falha fechada, ninguém aprova por ela."
            )
        linhas.append(f"2. GERENTEs vigentes: {len(dados['gerentes_vigentes'])}")
        for g in dados["gerentes_vigentes"]:
            ativa = "" if g["conta_ativa"] else " [conta inativa]"
            papeis = "; ".join(g["outros_papeis"]) or "nenhum"
            linhas.append(f"   - u{g['id']}{ativa} — outros papéis: {papeis}")
        cad = dados["gerente_cadastrado"]
        if cad is None:
            linhas.append("3. Gerencia.gerente: não cadastrado")
        else:
            situacao = "está" if cad["entre_os_gerentes_vigentes"] else "NÃO está"
            linhas.append(f"3. Gerencia.gerente: u{cad['id']} — {situacao} entre os GERENTEs vigentes")
        linhas.append("4. Aprovadores por base (contas ativas):")
        for base, lista in dados["aprovadores_por_base"].items():
            linhas.append(f"   - {base}: {len(lista)} — {ids(lista)}")
        inativas = dados["inativas_que_aprovariam_se_reativadas"]
        linhas.append(f"   Contas inativas que aprovariam se reativadas: {len(inativas)} — {ids(inativas)}")
        linhas.append(f"5. Pendentes por fluxo: {dados['pendentes_por_fluxo']}")
        linhas.append(f"   Criadas pelos aprovadores: {dados['pendentes_criadas_por_aprovadores']}")
        return "\n".join(linhas)
