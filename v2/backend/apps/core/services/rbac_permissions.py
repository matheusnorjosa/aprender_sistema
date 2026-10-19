"""
Servicos RBAC para permissoes funcionais com cache.

Formula (ADR-020): capacidades = pacote do perfil de cada gerencia onde a pessoa tem vinculo VIGENTE
com papel EQUIPE ou GERENTE ∪ direitos de evento de cada papel vigente em gerencia ativa
(`DIREITOS_PAPEL`, PR 8; `services/rbac_pacotes.py`). E o modo "lotacao", padrao desde o PR 12 (o
corte): o grupo Django nao da poder. `settings.RBAC_FONTE = "uniao"` e a volta de emergencia e soma
tambem os grupos (`grupos_dao_poder`). Uma so funcao calcula: `capacidades_sem_cache`, usada pela
API (com cache) e pelo simulador `rbac_diff`.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
from __future__ import annotations

from typing import Iterable

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache

from apps.core.models import EquipeGerencia, Gerencia, PermissaoFuncional
from apps.core.services.rbac_pacotes import DIREITOS_PAPEL, PACOTE, PAPEIS_COM_PACOTE

CACHE_TTL_SECONDS = 300
_CACHE_VERSION_KEY = "as2:funcperms:version"
FONTES = ("uniao", "lotacao")


def grupos_dao_poder(fonte: str | None = None) -> bool:
    """O grupo Django soma capacidade e abre tela? Só no modo "uniao" (a volta de emergência do PR 12).

    `fonte`: só para o simulador `rbac_diff` (`--simular-fonte`). None = `settings.RBAC_FONTE`.
    """
    return (fonte or settings.RBAC_FONTE) == "uniao"


def _ensure_cache_version() -> int:
    current = cache.get(_CACHE_VERSION_KEY)
    if isinstance(current, int) and current > 0:
        return current
    cache.set(_CACHE_VERSION_KEY, 1, None)
    return 1


def _cache_key_for_user(user_id: int, fonte: str | None = None) -> str:
    """A chave inclui a fonte: trocar `RBAC_FONTE` não serve, por até 300 s, o poder do modo anterior."""
    version = _ensure_cache_version()
    return f"as2:funcperms:{fonte or settings.RBAC_FONTE}:{version}:{user_id}"


def _cache_keys_for_user(user_id: int) -> list[str]:
    """As chaves dos dois modos: invalidar num modo não deixa o outro com o poder velho até a volta."""
    return [_cache_key_for_user(user_id, fonte) for fonte in FONTES]


def bump_functional_permissions_cache_version() -> int:
    """
    Invalida todos os caches de permissao funcional de uma vez.
    """

    current = _ensure_cache_version()
    next_version = current + 1
    cache.set(_CACHE_VERSION_KEY, next_version, None)
    return next_version


def invalidate_user_functional_permissions_cache(user_id: int) -> None:
    cache.delete_many(_cache_keys_for_user(user_id))


def invalidate_users_functional_permissions_cache(user_ids: Iterable[int]) -> None:
    keys = [key for user_id in set(user_ids) for key in _cache_keys_for_user(user_id)]
    if keys:
        cache.delete_many(keys)


def invalidate_group_functional_permissions_cache(group_ids: Iterable[int]) -> None:
    """
    Invalida cache dos usuarios que pertencem aos grupos informados.
    """

    normalized_ids = {int(group_id) for group_id in group_ids}
    if not normalized_ids:
        return

    User = get_user_model()
    impacted_user_ids = list(User.objects.filter(groups__id__in=normalized_ids).values_list("id", flat=True).distinct())
    invalidate_users_functional_permissions_cache(impacted_user_ids)


def capacidades_sem_cache(user_id: int, *, fonte: str | None = None) -> set[str]:
    """
    Capacidades efetivas, por consulta direta: pacote do perfil (ADR-020, D3) ∪ direitos do papel, mais os
    grupos só no modo "uniao" (`grupos_dao_poder`; `fonte` vale só para o simulador `rbac_diff`).

    O pacote vem de cada vinculo vigente (`EquipeGerencia.vigentes_em`) com papel em
    `PAPEIS_COM_PACOTE`, numa gerencia com perfil != PADRAO. Nao depende de `Gerencia.ativo`
    (mesmo criterio de `user_is_gerente_superintendencia`).

    Os direitos do papel (`DIREITOS_PAPEL`, PR 8) vem de cada papel vigente em gerencia ATIVA, em
    qualquer perfil: a regra de `EquipeGerencia.gerencias_com_papel` (e do `/api/me/`). Uma consulta
    so de vinculos serve as duas partes (o pacote ignora `Gerencia.ativo`; o papel exige).
    """

    capacidades: set[str] = set()
    if grupos_dao_poder(fonte):
        capacidades |= set(
            PermissaoFuncional.objects.filter(groups__user__id=user_id).order_by().values_list("codename", flat=True)
        )
    vinculos = (
        EquipeGerencia.vigentes_em()
        .filter(usuario_id=user_id)
        .order_by()
        .values_list("papel", "gerencia__perfil", "gerencia__ativo")
    )
    for papel, perfil, gerencia_ativa in vinculos:
        if papel in PAPEIS_COM_PACOTE and perfil != Gerencia.Perfil.PADRAO:
            capacidades |= PACOTE.get(perfil, frozenset())
        if gerencia_ativa:
            capacidades |= DIREITOS_PAPEL.get(papel, frozenset())
    return capacidades


def get_user_functional_permissions(user: object) -> set[str]:
    """
    Retorna codenames de permissao funcional efetivos para o usuario.
    """

    user_id = getattr(user, "id", None)
    if not isinstance(user_id, int):
        return set()

    cache_key = _cache_key_for_user(user_id)
    cached = cache.get(cache_key)
    if isinstance(cached, list):
        return set(str(item) for item in cached)

    codenames = capacidades_sem_cache(user_id)
    cache.set(cache_key, sorted(codenames), CACHE_TTL_SECONDS)
    return codenames
