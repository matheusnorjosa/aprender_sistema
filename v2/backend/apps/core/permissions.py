"""
DRF Permissions for RBAC

PA-02 (Adaptada): Superintendência, DAT e Superusuários podem aprovar/reprovar solicitações.
"""

from __future__ import annotations

from rest_framework import permissions  # type: ignore[attr-defined]
from rest_framework.request import Request
from rest_framework.views import APIView


class IsSuperintendencia(permissions.BasePermission):  # type: ignore[misc]
    """
    Permissão: usuários dos grupos 'Superintendência', 'DAT' ou superusers podem executar.
    PA-02 (Adaptada): Aprovação/reprovação permitida para Superintendência, DAT e Superusuários.

    Nota: Superusers sempre têm acesso completo.
    """

    message = "Apenas usuários da Superintendência, DAT ou Superusuários podem realizar esta ação."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return (
            request.user
            and request.user.is_authenticated
            and (
                getattr(request.user, "is_superuser", False)
                or request.user.groups.filter(name__in=["Superintendência", "DAT"]).exists()  # type: ignore[attr-defined]
            )
        )


class IsGerenteSuperintendencia(permissions.BasePermission):  # type: ignore[misc]
    """
    Permissão: apenas Gerentes vinculados à Superintendência ou superusers.

    Requer AMBOS:
    - Função "Gerente" (grupo de função)
    - Setor "Superintendência" (grupo de setor)

    Usado para operações críticas como aprovação/reprovação em lote.
    Nota: Superusers sempre têm acesso completo.
    """

    message = "Apenas Gerentes da Superintendência podem realizar esta ação."

    def has_permission(self, request: Request, view: APIView) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False

        if getattr(request.user, "is_superuser", False):
            return True

        user_groups = set(request.user.groups.values_list("name", flat=True))  # type: ignore[attr-defined]
        has_gerente = "Gerente" in user_groups
        has_superintendencia = "Superintendência" in user_groups

        return has_gerente and has_superintendencia


class IsSuperintendenciaOnly(permissions.BasePermission):  # type: ignore[misc]
    """
    Permissão: APENAS usuários do grupo 'Superintendência' ou superusers podem executar.

    Diferença de IsSuperintendencia: NÃO inclui DAT.
    Usado para operações destrutivas (delete) que requerem maior privilégio.

    Nota: Superusers sempre têm acesso completo.
    """

    message = "Apenas usuários da Superintendência podem realizar esta ação."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return (
            request.user
            and request.user.is_authenticated
            and (
                getattr(request.user, "is_superuser", False)
                or request.user.groups.filter(name="Superintendência").exists()  # type: ignore[attr-defined]
            )
        )


class IsCoordenadorOrDAT(permissions.BasePermission):  # type: ignore[misc]
    """
    Permissão: Coordenadores, Apoio de Coordenação ou DAT podem criar solicitações.

    Apoio de Coordenação tem as mesmas permissões de Coordenador para auxiliar
    nas operações quando necessário.

    Nota: Superusers sempre têm acesso completo.
    """

    message = "Apenas Coordenadores, Apoio de Coordenação ou DAT podem criar solicitações."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return (
            request.user
            and request.user.is_authenticated
            and (
                getattr(request.user, "is_superuser", False)
                or request.user.groups.filter(name__in=["Coordenador", "Apoio de Coordenação", "DAT"]).exists()  # type: ignore[attr-defined]
            )
        )


class IsControleOrSuper(permissions.BasePermission):  # type: ignore[misc]
    """
    Permissão: apenas usuários do grupo 'Controle' ou 'Superintendência' podem executar.

    Usado para operações de importação e controle de dados.
    Nota: Superusers sempre têm acesso completo.
    """

    message = "Apenas Controle ou Superintendência podem realizar esta ação."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return (
            request.user
            and request.user.is_authenticated
            and (
                getattr(request.user, "is_superuser", False)
                or request.user.groups.filter(name__in=["Controle", "Superintendência"]).exists()  # type: ignore[attr-defined]
            )
        )


class IsDATOrSuper(permissions.BasePermission):  # type: ignore[misc]
    """
    Permissão: apenas usuários do grupo 'DAT' ou superusers podem executar.

    Usado para operações de cadastro e gerenciamento de dados do DAT.
    Nota: Superusers sempre têm acesso completo.
    """

    message = "Apenas usuários do grupo DAT ou superusers podem realizar esta ação."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return (
            request.user
            and request.user.is_authenticated
            and (
                getattr(request.user, "is_superuser", False)
                or request.user.groups.filter(name="DAT").exists()  # type: ignore[attr-defined]
            )
        )


class IsDAT(permissions.BasePermission):  # type: ignore[misc]
    """
    Permissão: apenas usuários do grupo 'DAT' (sem incluir Super).

    Usado para operações específicas do DAT.
    Nota: Superusers sempre têm acesso completo.
    """

    message = "Apenas usuários do grupo DAT podem realizar esta ação."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return (
            request.user
            and request.user.is_authenticated
            and (
                getattr(request.user, "is_superuser", False)
                or request.user.groups.filter(name="DAT").exists()  # type: ignore[attr-defined]
            )
        )


class IsControleOrDAT(permissions.BasePermission):  # type: ignore[misc]
    """
    Permissão: apenas usuários dos grupos 'Controle' ou 'DAT' podem executar.

    Usado para operações de visualização e relatórios compartilhados.
    Nota: Superusers sempre têm acesso completo.
    """

    message = "Apenas Controle ou DAT podem realizar esta ação."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return (
            request.user
            and request.user.is_authenticated
            and (
                getattr(request.user, "is_superuser", False)
                or request.user.groups.filter(name__in=["Controle", "DAT", "Superintendência"]).exists()  # type: ignore[attr-defined]
            )
        )


class IsControle(permissions.BasePermission):  # type: ignore[misc]
    """
    Permissão: apenas usuários do grupo 'Controle' ou superusers podem executar.

    Usado para operações específicas de controle (métricas, dashboards).
    Nota: Superusers sempre têm acesso completo.
    """

    message = "Apenas usuários do grupo Controle podem realizar esta ação."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return (
            request.user
            and request.user.is_authenticated
            and (
                getattr(request.user, "is_superuser", False)
                or request.user.groups.filter(name="Controle").exists()  # type: ignore[attr-defined]
            )
        )


class IsGerencia(permissions.BasePermission):  # type: ignore[misc]
    """
    Permissão: usuários dos grupos 'Gerência', 'Superintendência' ou 'Diretoria' podem executar.

    Usado para operações de gerenciamento e métricas executivas.
    Nota: Superusers sempre têm acesso completo.
    """

    message = "Apenas usuários de Gerência, Superintendência ou Diretoria podem realizar esta ação."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return (
            request.user
            and request.user.is_authenticated
            and (
                getattr(request.user, "is_superuser", False)
                or request.user.groups.filter(
                    name__in=["Gerência", "Superintendência", "Diretoria"]
                ).exists()  # type: ignore[attr-defined]
            )
        )


class IsDashboardOverview(permissions.BasePermission):  # type: ignore[misc]
    """
    Permissão: apenas usuários com acesso ao dashboard geral.

    Grupos permitidos: Superintendência, Gerência, Diretoria.
    Nota: Superusers sempre têm acesso completo.
    """

    message = "Apenas usuários de Superintendência, Gerência ou Diretoria podem acessar o dashboard geral."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return (
            request.user
            and request.user.is_authenticated
            and (
                getattr(request.user, "is_superuser", False)
                or request.user.groups.filter(
                    name__in=["Superintendência", "Gerência", "Diretoria"]
                ).exists()  # type: ignore[attr-defined]
            )
        )


class IsMapMetrics(permissions.BasePermission):  # type: ignore[misc]
    """
    Permissão: usuários com acesso ao Mapa Brasil (métricas geográficas).

    Grupos permitidos: Controle, DAT, Superintendência, Gerência, Diretoria.
    Nota: Superusers sempre têm acesso completo.
    """

    message = "Apenas usuários autorizados podem acessar métricas do mapa."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return (
            request.user
            and request.user.is_authenticated
            and (
                getattr(request.user, "is_superuser", False)
                or request.user.groups.filter(
                    name__in=["Controle", "DAT", "Superintendência", "Gerência", "Diretoria"]
                ).exists()  # type: ignore[attr-defined]
            )
        )


class IsOwnerOrPrivileged(permissions.BasePermission):  # type: ignore[misc]
    """
    Permissão para edição de solicitações.

    Permite acesso se:
    - Usuário é superuser, OU
    - Usuário pertence a grupo privilegiado (Superintendência, DAT), OU
    - Usuário é o criador (owner) da solicitação

    Usado para controlar quem pode editar uma solicitação existente.
    """

    message = "Você só pode editar suas próprias solicitações ou ser membro da Superintendência/DAT."

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Verifica permissão básica de autenticação."""
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request: Request, view: APIView, obj: object) -> bool:
        """
        Verifica permissão no objeto (Solicitacao).

        Permite se:
        - Superuser
        - Grupo privilegiado (Superintendência, DAT)
        - Owner (usuario da solicitação)
        """
        if not request.user or not request.user.is_authenticated:
            return False

        # Superuser sempre pode
        if getattr(request.user, "is_superuser", False):
            return True

        # Grupos privilegiados podem editar qualquer solicitação
        privileged_groups = ["Superintendência", "DAT"]
        if request.user.groups.filter(name__in=privileged_groups).exists():  # type: ignore[attr-defined]
            return True

        # Owner pode editar sua própria solicitação
        obj_usuario = getattr(obj, "usuario", None)
        return obj_usuario == request.user


class HasSectorAccess(permissions.BasePermission):  # type: ignore[misc]
    """
    Permissão para acesso à grade mensal de disponibilidade por setor.

    Regras (conforme PLAN_multi_sector_availability.md):
    - Superusers: acesso a todos os setores
    - Grupo "Controle": BLOQUEADO (não tem acesso à grade mensal)
    - Sem gerencia_id: permite (assume SUPER - comportamento atual)
    - Com gerencia_id: verifica se usuário pertence à gerência via EquipeGerencia

    Usado em: MonthlyAvailabilityView
    """

    message = "Você não tem acesso a este setor."

    def has_permission(self, request: Request, view: APIView) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False

        # Superusers sempre podem acessar tudo
        if getattr(request.user, "is_superuser", False):
            return True

        # Grupo "Controle" não tem acesso à grade mensal
        if request.user.groups.filter(name="Controle").exists():  # type: ignore[attr-defined]
            self.message = "O grupo Controle não tem acesso à grade mensal de disponibilidade."
            return False

        # Obter gerencia_id da URL (via kwargs) ou query params
        gerencia_id_raw = view.kwargs.get("gerencia_id")  # type: ignore[attr-defined]
        if gerencia_id_raw is None:
            gerencia_id_raw = request.query_params.get("gerencia_id")

        # Sem gerencia_id = comportamento SUPER (permitido para todos autenticados)
        if gerencia_id_raw is None:
            return True

        # Hardening: evitar ValueError em query params inválidos
        try:
            gerencia_id = int(gerencia_id_raw)
        except (TypeError, ValueError):
            # Deixar o view validar e retornar 400 quando aplicável
            return True

        # Com gerencia_id = verificar se usuário pertence à gerência
        from apps.core.models import EquipeGerencia

        has_access = EquipeGerencia.objects.filter(
            usuario=request.user,
            gerencia_id=gerencia_id,
        ).exists()

        if not has_access:
            self.message = "Você não tem acesso a este setor."

        return has_access
