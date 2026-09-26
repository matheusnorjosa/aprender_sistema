"""
Serviço de lotação (vínculo `EquipeGerencia`) para o cadastro de usuário.

Usado pelo `UsuarioAdminSerializer` (form "Novo Usuário") para criar/atualizar o
vínculo de gerência a partir da Gerência + Função escolhidas — o que o escopo da
Wave 1 (#1656) de fato usa (`EquipeGerencia -> Gerencia.setor_canonico`), e que o
form antes não fazia.

⚑ A lógica de upsert com vigência espelha o bloco canônico do importer
(`equipe_gerencia_import._process_row`, ~L423-458): reabre a MESMA linha ao
(re)ativar (`valid_to=None`) e fecha em `hoje` ao inativar; `valid_from` intocado.
Mantido idêntico de propósito; um refactor futuro pode unificar os dois.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from django.contrib.auth.models import Group
from django.utils import timezone

from apps.core.models import EquipeGerencia

# Função (grupo RBAC) -> papel na EquipeGerencia. "Assistente Administrativo" e
# demais funções não têm papel de gerência (não viram vínculo).
PAPEL_POR_FUNCAO: dict[str, str] = {
    "Formador": "FORMADOR",
    "Coordenador": "COORDENADOR",
    "Gerente": "GERENTE",
    "Apoio de Coordenação": "APOIO",
}


def papeis_de_grupos(groups: Iterable[Any]) -> set[str]:
    """Deriva o conjunto de papéis (EquipeGerencia) a partir dos grupos de FUNÇÃO."""
    return {PAPEL_POR_FUNCAO[g.name] for g in groups if g.name in PAPEL_POR_FUNCAO}


def setor_group_for(gerencia: Any) -> Group | None:
    """Grupo RBAC de setor cujo nome == `Gerencia.setor_canonico`, se existir.

    Os 13 grupos de setor são um vocabulário fixo; nem todo `setor_canonico` tem
    grupo correspondente (A Cor da Gente, ED Financeira, Superativar…). Nesses
    casos retorna None (a realidade atual — não inventa grupo).
    """
    setor = (getattr(gerencia, "setor_canonico", "") or "").strip()
    if not setor:
        return None
    return Group.objects.filter(name=setor).first()


def upsert_vinculo(gerencia: Any, usuario: Any, papel: str, *, ativo: bool = True, supervisor: Any = None) -> Any:
    """Cria ou reabre o vínculo (gerencia, usuario, papel), respeitando a vigência."""
    hoje = timezone.localdate()
    existing = EquipeGerencia.objects.filter(gerencia=gerencia, usuario=usuario, papel=papel).first()
    if existing:
        fields: list[str] = []
        if papel == "APOIO" and supervisor and existing.coordenador_supervisor_id != supervisor.id:
            existing.coordenador_supervisor = supervisor
            fields.append("coordenador_supervisor")
        if existing.ativo != ativo:
            existing.ativo = ativo
            existing.valid_to = None if ativo else hoje
            fields += ["ativo", "valid_to"]
        if fields:
            existing.save(update_fields=fields)
        return existing
    return EquipeGerencia.objects.create(
        gerencia=gerencia,
        usuario=usuario,
        papel=papel,
        coordenador_supervisor=supervisor if papel == "APOIO" else None,
        ativo=ativo,
        valid_from=hoje,
        valid_to=None if ativo else hoje,
    )


def sync_user_lotacao(usuario: Any, gerencia: Any, papeis: Iterable[str], *, supervisor: Any = None) -> None:
    """Torna (gerencia, papeis) a lotação ATIVA do usuário (form = SSOT da lotação).

    - Garante vínculo ativo para cada (gerencia, papel).
    - Encerra (ativo=False, valid_to=hoje) qualquer outro vínculo ATIVO do usuário
      que não seja o alvo (troca de gerência / de papel).
    - Sem papel derivável (papeis vazio): NÃO mexe (evita apagar lotação por engano).
    """
    papeis = set(papeis)
    if not papeis:
        return
    for papel in papeis:
        upsert_vinculo(gerencia, usuario, papel, ativo=True, supervisor=supervisor)
    hoje = timezone.localdate()
    outros = EquipeGerencia.objects.filter(usuario=usuario, ativo=True).exclude(gerencia=gerencia, papel__in=papeis)
    for v in outros:
        v.ativo = False
        v.valid_to = hoje
        v.save(update_fields=["ativo", "valid_to"])
