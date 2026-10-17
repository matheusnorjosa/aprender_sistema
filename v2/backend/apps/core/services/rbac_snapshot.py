"""
Retrato do poder de cada pessoa, para o simulador `rbac_diff` (PR 1, ADR-020). Somente leitura.

Antes de cada PR que muda poder, roda-se em produção e o dono vê quem ganha e quem perde.
Nada aqui grava no banco nem no cache: as capacidades de hoje vêm de consulta direta
(`rbac_permissions.capacidades_sem_cache`, a mesma função que a API usa por trás do cache), e as
policies são calculadas sobre essas capacidades (`resolve_public_policies(..., capacidades=...)`).

`fonte` (PR 12, o corte): simula o modo "uniao" ou "lotacao" de `settings.RBAC_FONTE` sem trocar a
setting do processo. Capacidades e telas de escopo recebem a fonte por parâmetro (nada de
`override_settings` em código de produção). None = o modo ativo.

Sem dado pessoal: a pessoa é só `u<id>`. Nunca username (é o CPF), nome, e-mail nem telefone.

`capacidades_de` é o ponto de extensão dos PRs seguintes: passa-se a fórmula nova e compara-se o
retrato simulado com o de hoje, contra o banco real.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from typing import Any

from django.db.models import Q, QuerySet

from apps.core.constants import SETOR_GROUPS
from apps.core.models import EquipeGerencia, Gerencia, PermissaoFuncional, Usuario
from apps.core.rbac.policies import resolve_public_policies
from apps.core.services.functional_permissions_seed import FUNCTIONAL_PERMISSIONS_SEED
from apps.core.services.rbac_pacotes import PERFIL_PERMITIDO
from apps.core.services.rbac_permissions import capacidades_sem_cache

Snapshot = dict[str, dict[str, Any]]

# Ordem fixa dos campos no diff e na saída do comando.
CAMPOS: tuple[str, ...] = ("superusuario", "grupos", "capacidades", "policies", "gerencias_escopo", "vinculos")


def capacidades_de_hoje(usuario: Any) -> set[str]:
    """Capacidades de hoje sem cache: a mesma função da API (pacote do perfil ∪ papel, ADR-020; no modo
    "uniao", também os grupos).

    A paridade com `get_user_functional_permissions` vem por construção; o teste
    `test_capacidades_de_hoje_igual_a_fonte_da_api` continua travando.
    """
    return capacidades_sem_cache(usuario.id)


def _uid(usuario_id: int) -> str:
    return f"u{usuario_id}"


def snapshot_de_poder(
    usuarios: QuerySet[Usuario] | None = None,
    capacidades_de: Callable[[Any], set[str]] | None = None,
    *,
    fonte: str | None = None,
) -> Snapshot:
    """Poder de cada pessoa ATIVA: superusuário, grupos, capacidades, policies, escopo e vínculos.

    `fonte`: "uniao" ou "lotacao" simula aquele modo (capacidades e telas); None = o modo ativo.
    """

    def da_fonte(usuario: Any) -> set[str]:
        return capacidades_sem_cache(usuario.id, fonte=fonte)

    calcular = capacidades_de or da_fonte
    qs = (usuarios if usuarios is not None else Usuario.objects.all()).filter(is_active=True)
    qs = qs.prefetch_related("groups").order_by("id")

    vinculos: dict[int, set[tuple[int, str]]] = {}
    escopo: dict[int, set[int]] = {}
    ids = list(qs.values_list("id", flat=True))
    for uid, gid, papel in (
        EquipeGerencia.vigentes_em().filter(usuario_id__in=ids).values_list("usuario_id", "gerencia_id", "papel")
    ):
        vinculos.setdefault(uid, set()).add((gid, papel))
    for uid, gid in (
        EquipeGerencia.vigentes_com_escopo_em().filter(usuario_id__in=ids).values_list("usuario_id", "gerencia_id")
    ):
        escopo.setdefault(uid, set()).add(gid)

    snapshot: Snapshot = {}
    for usuario in qs:
        capacidades = set(calcular(usuario))
        snapshot[_uid(usuario.id)] = {
            "superusuario": bool(usuario.is_superuser),
            "grupos": sorted(g.name for g in usuario.groups.all()),
            "capacidades": sorted(capacidades),
            "policies": resolve_public_policies(usuario, capacidades=capacidades, fonte=fonte),
            "gerencias_escopo": sorted(escopo.get(usuario.id, set())),
            "vinculos": [list(v) for v in sorted(vinculos.get(usuario.id, set()))],
        }
    return snapshot


def _itens(pessoa: dict[str, Any] | None, campo: str) -> set[Any]:
    """Conjunto comparável do campo; vínculo vira tupla e superusuário vira {"superusuario"}."""
    if pessoa is None:
        return set()
    valor = pessoa.get(campo)
    if campo == "superusuario":
        return {"superusuario"} if valor else set()
    if campo == "vinculos":
        return {tuple(v) for v in valor or []}
    return set(valor or [])


def _lista(itens: set[Any]) -> list[Any]:
    return [list(i) if isinstance(i, tuple) else i for i in sorted(itens)]


def _ordem(chave: str) -> tuple[int, str]:
    return (int(chave[1:]), chave) if chave[1:].isdigit() else (-1, chave)


def diff_snapshots(antes: Snapshot, depois: Snapshot) -> dict[str, Any]:
    """Ganhos e perdas por pessoa e por campo. Quem entra ganha tudo; quem sai perde tudo."""
    pessoas: dict[str, dict[str, dict[str, list[Any]]]] = {}
    ganhos = perdas = 0
    for chave in sorted(set(antes) | set(depois), key=_ordem):
        mudancas: dict[str, dict[str, list[Any]]] = {}
        for campo in CAMPOS:
            a, d = _itens(antes.get(chave), campo), _itens(depois.get(chave), campo)
            if a != d:
                mudancas[campo] = {"ganha": _lista(d - a), "perde": _lista(a - d)}
                ganhos += len(d - a)
                perdas += len(a - d)
        if mudancas:
            pessoas[chave] = mudancas
    entram = sorted(set(depois) - set(antes), key=_ordem)
    saem = sorted(set(antes) - set(depois), key=_ordem)
    return {
        "pessoas": pessoas,
        "entram": entram,
        "saem": saem,
        "resumo": {
            "ganhos": ganhos,
            "perdas": perdas,
            "pessoas_com_mudanca": len(pessoas),
            "entram": len(entram),
            "saem": len(saem),
        },
    }


# Grupo de setor → `Gerencia.nome` (código interno, único, ninguém altera pela tela) da(s) gerência(s)
# daquele setor. Fonte: comentários de `constants.SETOR_GROUPS` e o mapa medido em prod em 29/09
# (`definir_nome_exibicao_gerencias`: g17 GERENCIA BRINCANDO, g19 GERENCIA DAT). CONTROLE e DIRETORIA
# ainda não existem (PR 5 cria). Não serve `setor_canonico`: ele usa o vocabulário de produto
# (`SETORES_PRODUTO`, ex. "Brincando e Aprendendo"), não os 13 grupos. Setor fora daqui = sem gerência
# mapeada, e o diagnóstico não aponta ninguém dele como "sem vínculo".
GERENCIAS_DO_GRUPO_DE_SETOR: dict[str, tuple[str, ...]] = {
    "Superintendência": ("SUPERINTENDENCIA",),
    "Vidas": ("GERENCIA 2",),
    "Fluir": ("GERENCIA 3",),
    "ACerta": ("GERENCIA 4",),
    "Brincando": ("GERENCIA 5", "GERENCIA BRINCANDO"),
    "Sou da Paz": ("GERENCIA 6",),
    "DAT": ("GERENCIA DAT",),
    "Controle": ("CONTROLE",),
    "Diretoria": ("DIRETORIA",),
}


def diagnostico_de_lotacao() -> dict[str, Any]:
    """Medições do PR 1 (relatório de arquitetura de permissões, seção 4). Sem dado pessoal.

    "Grupo de setor sem vínculo": pessoa ativa num grupo de `SETOR_GROUPS` sem vínculo vigente
    (qualquer papel, inclusive EQUIPE) numa gerência daquele setor, pelo mapa
    `GERENCIAS_DO_GRUPO_DE_SETOR`. Setor sem mapa vai para `setores_sem_gerencia_mapeada` (só a contagem).
    """
    gerencias = list(Gerencia.objects.order_by("id").values_list("id", "setor_canonico"))
    id_por_nome = dict(Gerencia.objects.values_list("nome", "id"))
    gerencias_do_setor: dict[str, set[int]] = {
        setor: {id_por_nome[n] for n in nomes if n in id_por_nome}
        for setor, nomes in GERENCIAS_DO_GRUPO_DE_SETOR.items()
    }

    vigentes = list(
        EquipeGerencia.vigentes_em().filter(usuario__is_active=True).values_list("usuario_id", "gerencia_id")
    )
    por_pessoa = Counter(uid for uid, _ in vigentes)
    gerencias_por_pessoa: dict[int, set[int]] = {}
    for uid, gid in vigentes:
        gerencias_por_pessoa.setdefault(uid, set()).add(gid)

    sem_vinculo: dict[str, list[str]] = {}
    sem_mapa: dict[str, int] = {}
    for setor in SETOR_GROUPS:
        membros = set(Usuario.objects.filter(is_active=True, groups__name=setor).values_list("id", flat=True))
        if setor not in gerencias_do_setor:
            if membros:
                sem_mapa[setor] = len(membros)
            continue
        do_setor = gerencias_do_setor[setor]
        faltam = [_uid(uid) for uid in sorted(membros) if not gerencias_por_pessoa.get(uid, set()) & do_setor]
        if faltam:
            sem_vinculo[setor] = faltam

    return {
        "setor_canonico": {str(gid): setor or "" for gid, setor in gerencias},
        "gerencias_controle_diretoria": {
            nome: sorted(
                Gerencia.objects.filter(Q(nome__iexact=nome) | Q(setor_canonico__iexact=nome)).values_list(
                    "id", flat=True
                )
            )
            for nome in ("CONTROLE", "DIRETORIA")
        },
        "pessoas_com_mais_de_um_vinculo": sum(1 for n in por_pessoa.values() if n > 1),
        "pessoas_em_mais_de_uma_gerencia": sum(1 for gs in gerencias_por_pessoa.values() if len(gs) > 1),
        "gerencias_por_setor": {s: sorted(gs) for s, gs in gerencias_do_setor.items()},
        "grupo_de_setor_sem_vinculo": sem_vinculo,
        "setores_sem_gerencia_mapeada": sem_mapa,
    }


def auditoria_de_matriz() -> dict[str, list[list[str]]]:
    """`rbac_diff --auditar` (D4 do ADR-020): o que diverge do código. Só leitura, sem dado pessoal.

    - pares (grupo, capacidade) do banco × os do seed (`FUNCTIONAL_PERMISSIONS_SEED`, que é a matriz);
    - gerência com perfil ≠ PADRAO fora de `PERFIL_PERMITIDO` (pelo `nome`, que a tela não muda
      numa gerência com perfil).
    """
    do_banco = set(PermissaoFuncional.objects.filter(groups__isnull=False).values_list("groups__name", "codename"))
    do_seed = {(grupo, item.codename) for item in FUNCTIONAL_PERMISSIONS_SEED for grupo in item.group_names}
    perfis_fora = [
        [nome, perfil]
        for nome, perfil in Gerencia.objects.exclude(perfil=Gerencia.Perfil.PADRAO)
        .order_by("nome")
        .values_list("nome", "perfil")
        if PERFIL_PERMITIDO.get(nome) != perfil
    ]
    return {
        "so_no_banco": [list(par) for par in sorted(do_banco - do_seed)],
        "so_no_seed": [list(par) for par in sorted(do_seed - do_banco)],
        "perfis_fora_da_lista": perfis_fora,
    }
