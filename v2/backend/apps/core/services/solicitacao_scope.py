"""
M10-01 (#1623) — SSOT de escopo ator×gerência para Solicitacao.

Antes, quem tinha as caps `approve_solicitation` / `approve_solicitation_batch`
(concedidas ao grupo FUNÇÃO "Gerente" inteiro, não só ao aprovador composto)
via/editava/excluía solicitações de QUALQUER gerência — alcance nacional sem
escopo. Um Gerente pedagógico (não-Superintendência) não consegue aprovar (isso
exige o composite), mas conseguia ler/editar/excluir tudo. Desde o PR 8 (15/10/2026) a
gestora é o papel GERENTE vigente em gerência ativa (`_e_gestora`), não o grupo nem a
capacidade `approve_solicitation_batch` (apagada na migration 0125).

Regra:
- GLOBAL (vê tudo): superuser, Controle (`operate_preagenda`), DAT
  (`manage_admin_registries`) e quem aprova (`access_solicitation_approvals` =
  `solicitation_approval_basis`: gerente da Superintendência por vínculo ou a capacidade
  `approve_solicitation`, que o DAT e o Controle têm pelo pacote).
- GESTORA não-global (papel GERENTE vigente, `_e_gestora`): as gerências onde ela é GERENTE (PR 9; C9
  da auditoria) + as próprias.
- APOIO (`publish_setor_solicitacao`): as aprovadas das gerências onde é APOIO + as próprias (soma-se
  ao alcance da gestora, se ela também for GERENTE em outra gerência). Não edita a de outra pessoa;
  exclui só a que já está no Google (decisão do dono, 27/10: `EscritaEmSolicitacao.apoio_pode_excluir_do_google`).
- DEMAIS (Coordenador etc.): apenas as próprias (comportamento inalterado).

PR 9 (16/10/2026): o alcance é a gerência do PROJETO (`projeto.gerencia_id`), nunca o texto do setor
(o lint V006 proíbe o setor nos arquivos de escopo). Cada superfície conta só o papel vigente certo em
gerência ativa (`EquipeGerencia.gerencias_com_papel`); a falta de dado nega (fail-closed).

Consumido tanto pelo `get_queryset` do `SolicitacaoViewSet` quanto pelo
`IsOwnerOrPrivileged.has_object_permission` (mesma semântica em list e em objeto;
fora do escopo → 404, não distinguível de inexistente).

Exceção (regra do dono, 30/09): a aprovadora por vínculo (GERENTE em g1) é global para VER, mas só
escreve no alcance dela (`projeto_fora_do_alcance_da_restrita`): fluxo SUPER da Superintendência +
gerências de outro vínculo de GERENTE dela. Cria e move só para projeto desse alcance; edita e exclui
nele e nas próprias. Fora disso o objeto aparece e a escrita dá 403/400.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingTypeArgument=false

from __future__ import annotations

from collections.abc import Sequence
from functools import cached_property
from typing import Any

from django.db.models import Q, QuerySet

from apps.core.models import EquipeGerencia
from apps.core.rbac.helpers import GERENCIA_APROVADORA_NOME
from apps.core.rbac.policies import (
    ESCOPO_SUPERINTENDENCIA_PROJETO_Q,
    aprovadora_restrita_a_superintendencia,
    projeto_no_escopo_da_superintendencia,
    user_has_policy,
)
from apps.core.rbac_helpers import user_has_any_perm
from apps.core.services.rbac_permissions import get_user_functional_permissions
from apps.core.services.solicitacao_exclusao import esta_no_google

# `approve_solicitation` vem do pacote do DAT (PR 10) e do Controle (PR 11); nenhum grupo a tem —
# visão global legítima de quem aprova qualquer evento. `operate_preagenda`=Controle,
# `manage_admin_registries`=DAT. A gestora por gerência é o papel (`_e_gestora`).
_GLOBAL_CAPS = ("operate_preagenda", "manage_admin_registries", "approve_solicitation")


def user_is_solicitacao_global(user: Any) -> bool:
    """Autoridade que legitimamente enxerga TODAS as solicitações."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    if user_has_any_perm(user, *_GLOBAL_CAPS):
        return True
    # Quem aprova (`solicitation_approval_basis`): inclui a gerente da Superintendência por vínculo.
    return user_has_policy(user, "access_solicitation_approvals")


def tem_capacidade_global(user: Any) -> bool:
    """Controle, DAT ou Superintendência (`_GLOBAL_CAPS`; superusuário incluso): alcance de todas as gerências."""
    return user_has_any_perm(user, *_GLOBAL_CAPS)


def _gerencias_da_gestora(user: Any) -> set[int]:
    """Gerências onde `user` é GERENTE vigente em gerência ativa: o alcance da gestora (PR 8 e PR 9, C9)."""
    if not user or not getattr(user, "is_authenticated", False):
        return set()
    return EquipeGerencia.gerencias_com_papel(user, _PAPEIS_DE_GESTAO)


def _e_gestora(user: Any) -> bool:
    """Gestora de solicitação da gerência (PR 8): papel GERENTE vigente em gerência ativa."""
    return bool(_gerencias_da_gestora(user))


def scope_solicitacoes(qs: QuerySet, user: Any) -> QuerySet:
    """Restringe `qs` ao escopo do `user` (ver regra no módulo)."""
    if user_is_solicitacao_global(user):
        return qs
    filtro = Q(usuario=user)
    gestora = _gerencias_da_gestora(user)
    if gestora:
        filtro |= Q(projeto__gerencia_id__in=gestora)
    # #1656 Feature 2: Apoio de Coordenação com `publish_setor_solicitacao` enxerga
    # (para publicar/preview/resync/cancel) as solicitações APROVADAS das gerências onde é APOIO,
    # além das suas (estas em qualquer status, pois é dona). O ramo filtra `status="aprovado"` para
    # não expor PII de eventos pendentes/reprovados de terceiros. PR 9: a gerência do evento é
    # `projeto.gerencia_id` (antes era o texto do setor do projeto). Soma-se ao da gestora (GERENTE
    # em A e APOIO em B publica em B). Tier de LEITURA apenas: `user_can_access_solicitacao` (edição)
    # NÃO muda.
    if user_has_any_perm(user, "publish_setor_solicitacao"):
        apoio = _gerencias_de_apoio(user)
        if apoio:
            filtro |= Q(projeto__gerencia_id__in=apoio, status="aprovado")
    return qs.filter(filtro)


def _gerencias_de_apoio(user: Any) -> set[int]:
    """Gerências onde `user` é APOIO vigente em gerência ativa: o alcance de publicação no Google (PR 9)."""
    return EquipeGerencia.gerencias_com_papel(user, {"APOIO"})


def restrita_ao_escopo_da_superintendencia(user: Any) -> bool:
    """Regra do dono (30/09): cria, edita e exclui solicitação só no escopo da Superintendência?

    É a aprovadora por vínculo (`aprovadora_restrita_a_superintendencia`) cujo alcance global vem
    SÓ da policy de aprovação. Global por outra base (Controle, DAT, `approve_solicitation`) segue
    global: o vínculo em g1 não tira o que outra base dá.
    """
    return aprovadora_restrita_a_superintendencia(user) and not tem_capacidade_global(user)


# Papéis que dão o tier do 2º vínculo da restrita: só GERENTE. Coordenadora ou apoio comum não mexe
# em solicitação alheia da gerência; as próprias dela seguem pelo caminho de dona.
_PAPEIS_DE_GESTAO = ("GERENTE",)


def _gerencias_de_gestor_sem_g1(user: Any) -> set[int]:
    """Tier de gestor da restrita: gerências dos OUTROS vínculos de GERENTE dela (`_PAPEIS_DE_GESTAO`;
    g1 fora, senão o NAO_SUPER de g1 voltaria ao alcance). Vazio se ela não é gestora (`_e_gestora`)."""
    if not _e_gestora(user):
        return set()
    return set(
        EquipeGerencia.vigentes_com_escopo_em()
        .filter(usuario=user, papel__in=_PAPEIS_DE_GESTAO)
        .exclude(gerencia__nome=GERENCIA_APROVADORA_NOME)
        .values_list("gerencia_id", flat=True)
    )


def projeto_fora_do_alcance_da_restrita(user: Any, projeto: Any) -> bool:
    """True sse `user` é restrita ao escopo da Superintendência e `projeto` está fora do alcance dela.

    Alcance = projeto do fluxo SUPER de g1, ou projeto de outra gerência onde ela tem vínculo de
    GERENTE (COORDENADOR, APOIO e FORMADOR não contam). Projeto None → fora (fail-closed). Usado para
    editar/excluir (objeto) e para criar ou mover solicitação (write-path).
    """
    return EscritaEmSolicitacao(user).fora_do_alcance_da_restrita(projeto)


def user_can_access_solicitacao(user: Any, obj: Any) -> bool:
    """True sse `user` pode editar/excluir a Solicitacao `obj` (mesma regra do queryset, salvo a
    aprovadora restrita: vê tudo, mas só escreve nas próprias e no alcance dela)."""
    return EscritaEmSolicitacao(user).no_escopo(obj)


class EscritaEmSolicitacao:
    """A regra de objeto de quem escreve (edita ou exclui) numa solicitação, com os fatos de `user`
    lidos uma vez.

    Cada fato é uma consulta preguiçosa (`cached_property`): para um objeto, o custo é o de antes; a
    lista reusa a mesma instância na página inteira (campo `pode_excluir`), e a consulta sai uma vez por
    request. Quem edita e quem exclui (`IsOwnerOrPrivileged`, `PodeExcluirSolicitacao`) leem daqui.
    """

    def __init__(self, user: Any) -> None:
        self.user = user

    @cached_property
    def capacidades(self) -> set[str]:
        return get_user_functional_permissions(self.user)

    @cached_property
    def restrita(self) -> bool:
        return restrita_ao_escopo_da_superintendencia(self.user)

    @cached_property
    def _global(self) -> bool:
        return user_is_solicitacao_global(self.user)

    @cached_property
    def _gerencias_da_gestora(self) -> set[int]:
        return _gerencias_da_gestora(self.user)

    @cached_property
    def _gerencias_de_gestor_sem_g1(self) -> set[int]:
        return _gerencias_de_gestor_sem_g1(self.user)

    @cached_property
    def _gerencias_de_apoio(self) -> set[int]:
        if not user_has_any_perm(self.user, "publish_setor_solicitacao"):
            return set()
        return _gerencias_de_apoio(self.user)

    def fora_do_alcance_da_restrita(self, projeto: Any) -> bool:
        """`projeto_fora_do_alcance_da_restrita`."""
        if not self.restrita:
            return False
        if projeto_no_escopo_da_superintendencia(projeto):
            return False
        gerencia_id = getattr(projeto, "gerencia_id", None)
        return gerencia_id is None or gerencia_id not in self._gerencias_de_gestor_sem_g1

    def no_escopo(self, obj: Any) -> bool:
        """`user_can_access_solicitacao`."""
        user = self.user
        if not user or not getattr(user, "is_authenticated", False):
            return False
        if getattr(obj, "usuario_id", None) == getattr(user, "id", None):
            return True
        if self._global:
            return not self.fora_do_alcance_da_restrita(getattr(obj, "projeto", None))
        gerencia_id = getattr(getattr(obj, "projeto", None), "gerencia_id", None)
        return gerencia_id is not None and gerencia_id in self._gerencias_da_gestora

    def apoio_pode_excluir_do_google(self, obj: Any) -> bool:
        """A Apoio exclui o evento de outra pessoa que já está no Google (decisão do dono, 27/10/2026).

        Só quando (a) o projeto é de uma gerência onde ela é APOIO vigente (com `publish_setor_solicitacao`,
        o mesmo alcance de quem tira do Google), (b) o evento está no Google (`esta_no_google`) e (c) não
        é `publicado_fora_do_sistema`, e (d) está `aprovado`. Pedido fora do Google ou não aprovado (ex.: SUPER
        pendente esperando a gerente) continua fora; editar não muda. As recusas do `perform_destroy` valem por cima.
        """
        user = self.user
        if not user or not getattr(user, "is_authenticated", False):
            return False
        if getattr(obj, "publicado_fora_do_sistema", False) or not esta_no_google(obj):
            return False
        # Só o aprovado: quem é global para ver e também é Apoio (a aprovadora da Superintendência)
        # passaria só por aqui num pendente com Event ID adotado.
        if getattr(obj, "status", None) != "aprovado":
            return False
        gerencia_id = getattr(getattr(obj, "projeto", None), "gerencia_id", None)
        return gerencia_id is not None and gerencia_id in self._gerencias_de_apoio


def can_publish_solicitacao(user: Any, obj: Any) -> bool:
    """True sse `user` pode publicar/prever/resincronizar/cancelar o evento GCal `obj`.

    Guarda de OBJETO das 4 @actions GCal (#1656 Feature 2). Separa "publicabilidade"
    de "visibilidade": o `scope_solicitacoes` deixa a Apoio VER as próprias (qualquer
    status) + as APROVADAS da gerência; mas PUBLICAR exige que o evento seja de uma gerência
    onde ela é APOIO, inclusive o próprio.

    - Global (`use_gcal`: superuser / Controle / Superintendência) → qualquer evento.
      ⚑ É o `use_gcal`, NÃO `user_is_solicitacao_global`: este inclui a DAT para VER tudo,
      e uma pessoa da DAT que também fosse Apoio publicaria evento de qualquer gerência.
    - `publish_setor_solicitacao` (Apoio) → só evento cujo `projeto.gerencia_id` está entre as
      gerências onde ela é APOIO vigente (PR 9). Projeto sem gerência → False (fail-closed).
    """
    is_global, gerencias = _publish_tier(user)
    if is_global:
        return True
    gerencia_id = getattr(getattr(obj, "projeto", None), "gerencia_id", None)
    return gerencia_id is not None and gerencia_id in gerencias


def _publish_tier(user: Any) -> tuple[bool, frozenset[int]]:
    """(global?, gerências de APOIO) de quem publica no GCal — SSOT da guarda de objeto e da lista.

    `can_publish_solicitacao` (objeto) e `scope_publishable_solicitacoes` (lista) leem
    daqui, então a lista nunca mostra evento que as 4 ações recusariam.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return False, frozenset()
    if user_has_policy(user, "use_gcal"):
        return True, frozenset()
    if user_has_any_perm(user, "publish_setor_solicitacao"):
        return False, frozenset(_gerencias_de_apoio(user))
    return False, frozenset()


def scope_publishable_solicitacoes(qs: QuerySet, user: Any) -> QuerySet:
    """Restringe `qs` ao que `user` pode publicar no GCal (`?publishable=true`, #1656).

    Global → tudo; Apoio → eventos das gerências onde ela é APOIO vigente; sem gerência de APOIO,
    ou sem nenhuma das duas permissões → vazio. Mesma regra da guarda de objeto.
    """
    is_global, gerencias = _publish_tier(user)
    if is_global:
        return qs
    if not gerencias:
        return qs.none()
    return qs.filter(projeto__gerencia_id__in=gerencias)


def has_publish_scope(user: Any) -> bool:
    """True sse `user` pode publicar ALGUM evento (global, ou APOIO vigente em alguma gerência)."""
    is_global, gerencias = _publish_tier(user)
    return is_global or bool(gerencias)


def _gerencia_do_evento(creator: Any, projeto: Any) -> int | None:
    """Gerência do `projeto` do evento, se `creator` atua nela (papel G/C/A vigente); senão None.

    P9-5 (decisão do dono, 15/10/2026): num evento da gerência A só entram pessoas da A. Quem não atua
    na gerência do projeto (inclusive a dona de evento antigo que perdeu o papel lá) não põe ninguém.
    """
    gerencia_id = getattr(projeto, "gerencia_id", None)
    if gerencia_id is None or gerencia_id not in EquipeGerencia.gerencias_de_atuacao(creator):
        return None
    return gerencia_id


def _isento_do_escopo(creator: Any) -> bool:
    """Sem ator (chamada interna sem `request`) ou global/privilegiado: o escopo de gerência não se aplica."""
    if not creator or not getattr(creator, "is_authenticated", False):
        return True
    return user_is_solicitacao_global(creator)


def participantes_fora_da_gerencia(
    creator: Any, projeto: Any, users: Sequence[Any], papeis: frozenset[str] | None = None
) -> list[Any]:
    """Os `users` que NÃO podem entrar no evento de `projeto` criado ou editado por `creator`.

    Pode entrar quem tem vínculo vigente com escopo (papel ≠ EQUIPE; ou um dos `papeis`, se vierem) na
    gerência do projeto, desde que `creator` atue nela (`_gerencia_do_evento`). Fail-closed: projeto
    sem gerência, ou criador sem papel G/C/A lá → todos ficam fora.

    Criador global/privilegiado (`user_is_solicitacao_global`: superuser, Superintendência, Controle,
    DAT) ou ausente → isento → lista vazia.
    """
    if not users or _isento_do_escopo(creator):
        return []
    gerencia_id = _gerencia_do_evento(creator, projeto)
    if gerencia_id is None:
        return list(users)
    vinculos = EquipeGerencia.vigentes_com_escopo_em().filter(
        gerencia_id=gerencia_id, usuario_id__in=[u.id for u in users]
    )
    if papeis is not None:
        vinculos = vinculos.filter(papel__in=list(papeis))
    dentro = set(vinculos.values_list("usuario_id", flat=True))
    return [u for u in users if u.id not in dentro]


def scope_usuarios_por_gerencia(
    qs: QuerySet, user: Any, projeto: Any = None, papeis: frozenset[str] | None = None
) -> QuerySet:
    """Restringe um queryset de `Usuario` às pessoas que `user` pode pôr num evento.

    Espelho de LEITURA do `participantes_fora_da_gerencia` (write-path): alimenta o
    `/lookup/usuarios/` para o seletor da Nova Solicitação oferecer só quem o backend aceita.

    - Global/privilegiado (`user_is_solicitacao_global`) → sem filtro.
    - Com `projeto`: só a gerência do projeto, se `user` atua nela (P9-5); com `papeis`, só quem tem
      um deles NESSA gerência (o responsável é COORDENADOR da gerência do projeto, como no write-path).
    - Sem `projeto`: as gerências onde `user` tem papel G/C/A vigente.
    - Sem gerência de atuação → vazio (fail-closed).
    """
    if user_is_solicitacao_global(user):
        return qs
    if projeto is not None:
        gerencia_id = _gerencia_do_evento(user, projeto)
        gerencias = set() if gerencia_id is None else {gerencia_id}
    else:
        gerencias = EquipeGerencia.gerencias_de_atuacao(user)
    if not gerencias:
        return qs.none()
    vigentes = EquipeGerencia.vigentes_com_escopo_em().filter(gerencia_id__in=gerencias)
    if projeto is not None and papeis:
        vigentes = vigentes.filter(papel__in=list(papeis))
    return qs.filter(id__in=vigentes.values("usuario_id"))


def scope_projetos_por_gerencia(qs: QuerySet, user: Any) -> QuerySet:
    """Restringe um queryset de `Projeto` aos das gerências onde `user` tem papel G/C/A vigente.

    Alimenta o `/lookup/projetos/` da Nova Solicitação e da tela Editar.
    - Global/privilegiado (`user_is_solicitacao_global`) → sem filtro, salvo a aprovadora restrita
      (regra do dono, 30/09): só o alcance dela, o mesmo de `projeto_fora_do_alcance_da_restrita`.
    - Sem gerência de atuação → vazio; projeto sem gerência nunca entra (fail-closed).
    """
    if user_is_solicitacao_global(user):
        if restrita_ao_escopo_da_superintendencia(user):
            return qs.filter(ESCOPO_SUPERINTENDENCIA_PROJETO_Q | Q(gerencia_id__in=_gerencias_de_gestor_sem_g1(user)))
        return qs
    return qs.filter(gerencia_id__in=EquipeGerencia.gerencias_de_atuacao(user))


def projeto_fora_da_gerencia(creator: Any, projeto: Any) -> bool:
    """True sse `creator` não pode criar evento em `projeto` nem mover um evento para ele.

    Write-path do `scope_projetos_por_gerencia`. Fica fora o projeto sem gerência ou de gerência onde o
    criador não tem papel G/C/A vigente. Isentos: criador global/privilegiado, criador ausente e
    `projeto` None (o serializer cuida do obrigatório).
    """
    if projeto is None or _isento_do_escopo(creator):
        return False
    return _gerencia_do_evento(creator, projeto) is None
