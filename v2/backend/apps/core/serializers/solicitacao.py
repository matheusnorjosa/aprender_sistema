"""
AS v2 — Solicitacao Serializers

Serializers para Solicitacao, Participation e EventDetail.
Clausulas Petreas: PA-01 a PA-07.
Type-checked with Pyright (strict mode).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportUntypedBaseClass=false

from __future__ import annotations

from typing import Any, cast

from rest_framework import serializers  # type: ignore[attr-defined]

from apps.core.models import AuditLog, Participation, Solicitacao, Usuario
from apps.core.pii import email_sem_cpf, redact_cpf_deep
from apps.core.rbac.policies import user_has_policy
from apps.core.serializers.usuario import UserSlimSerializer
from apps.core.services.avaliacao_formador import formadores_avaliaveis_ids, gerencia_pergunta
from apps.core.services.compra_elegibilidade import isento_da_regra_da_compra, par_liberado
from apps.core.services.solicitacao_approval import DECISAO_IMPEDIDA, decisoes_impedidas


class ParticipationNestedSerializer(serializers.ModelSerializer):
    """
    Serializer aninhado para Participation (read-only).
    Usado em SolicitacaoSerializer para expor participations.
    """

    usuario = UserSlimSerializer(read_only=True)
    guest_email = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()

    class Meta:
        model = Participation
        fields = ("usuario", "guest_email", "guest_nome", "email", "role", "ch_horas", "observacao")

    def get_guest_email(self, obj: Participation) -> str | None:
        # S5: o convidado sem conta também pode ter o e-mail de reserva ou um e-mail com CPF.
        return email_sem_cpf(getattr(obj, "guest_email", None))

    def get_email(self, obj: Participation) -> str | None:
        user_email = getattr(getattr(obj, "usuario", None), "email", None)
        # S5: sem o e-mail de reserva `<cpf>@placeholder.local` nem e-mail que leve CPF.
        return email_sem_cpf(user_email or getattr(obj, "guest_email", None))


class SolicitacaoSerializer(serializers.ModelSerializer):
    """
    Serializer for Solicitacao model.
    PA-01: Status sempre começa pendente.

    Inclui campo participations (read-only, aninhado) para expor
    múltiplos participantes com seus papéis.
    """

    participations = ParticipationNestedSerializer(many=True, read_only=True)
    fluxo = serializers.SerializerMethodField()

    # Campos legíveis para exibição (além dos IDs). S5 (auditoria 14/10, C10): sem o login, que é
    # o CPF; o nome sai em `coordenador_nome` e `str(usuario)` (nome ou "Usuario #id").
    coordenador_nome = serializers.SerializerMethodField()
    municipio_nome = serializers.CharField(source="municipio.nome", read_only=True)
    projeto_nome = serializers.CharField(source="projeto.nome", read_only=True)
    projeto_geral_nome = serializers.CharField(source="projeto.projeto_geral.nome", read_only=True, allow_null=True)
    tipo_evento_nome = serializers.CharField(source="tipo_evento.nome", read_only=True)
    # Decisão do dono (05/10/2026): a resposta "pretende avaliar o formador" é lida por outro
    # sistema interno; o nome sai junto para a tela não precisar de outra chamada.
    formador_avaliado_nome = serializers.SerializerMethodField()
    # Para a tela de edição decidir se mostra a pergunta (mesma regra do backend). Só no
    # detalhe de UM evento (null na lista): na lista custaria consultas por linha.
    avaliaveis_ids = serializers.SerializerMethodField()
    projeto_pergunta_avaliar_formador = serializers.SerializerMethodField()
    # PA-02 (PR 10): por que quem lê NÃO decide esta pendente ("propria", "conta_alterada",
    # "editada_pelo_ator"); null quando decide ou não aprova. A tela de Aprovações esconde os botões.
    decisao_impedida = serializers.SerializerMethodField()

    class Meta:
        model = Solicitacao
        fields = [
            "id",
            "usuario",
            "municipio",
            "municipio_nome",
            "projeto",
            "projeto_nome",
            "projeto_geral_nome",
            "tipo_evento",
            "tipo_evento_nome",
            "tipo",
            "encontro",
            "segmento",
            "segmento_norm",
            "segmento_norm_confianca",
            "coordenador_acompanha",
            "coordenador",
            "coordenador_nome",
            "pretende_avaliar_formador",
            "formador_avaliado",
            "formador_avaliado_nome",
            "avaliaveis_ids",
            "projeto_pergunta_avaliar_formador",
            "decisao_impedida",
            "inicio",
            "fim",
            "status",
            "observacoes",
            "local",
            # PR19: Modalidade online/presencial (gera Meet apenas quando online)
            "is_online",
            "external_event_id",
            "created_at",
            "updated_at",
            "participations",
            "fluxo",
            # PR14: Campos GCal para rastreamento de sincronização
            "gcal_status",
            "gcal_last_sync_at",
            "gcal_last_error",
            # Virada (16/10/2026): no Google pela planilha e não adotado → a tela não oferece Publicar.
            "publicado_fora_do_sistema",
            # gcal_payload_hash removed: internal implementation detail
            # PR19/RF06: Google Meet link
            "meet_link",
        ]
        read_only_fields = [
            "id",
            "usuario",
            "status",
            "external_event_id",
            "created_at",
            "updated_at",
            # #1896: segmento_norm/confianca vêm do de-para do import (sem entrada-direta) → read-only
            "segmento_norm",
            "segmento_norm_confianca",
            # PR14: Campos GCal são gerenciados pelo sistema
            "gcal_status",
            "gcal_last_sync_at",
            "gcal_last_error",
            "publicado_fora_do_sistema",
            # gcal_payload_hash removed: internal implementation detail
            # PR19/RF06: Google Meet link (gerado automaticamente)
            "meet_link",
        ]

    def get_fluxo(self, obj: Solicitacao) -> str:
        """Retorna fluxo do projeto (SUPER ou NAO_SUPER), fallback para NAO_SUPER."""
        if obj.projeto:
            return obj.projeto.fluxo
        return "NAO_SUPER"  # PR15: Fallback para solicitações sem projeto

    def get_coordenador_nome(self, obj: Solicitacao) -> str | None:
        """
        Retorna nome completo do coordenador (first_name + last_name).
        Prioriza: coordenador field -> usuario (fallback para ETL imports).
        """
        user = cast("Usuario | None", obj.coordenador or obj.usuario)
        return str(user) if user else None

    def get_formador_avaliado_nome(self, obj: Solicitacao) -> str | None:
        user = obj.formador_avaliado
        if user is None:
            return None
        return str(user)

    def _um_evento(self) -> bool:
        """True fora de listagem (detalhe, criar, editar): os campos de apoio à tela só saem aqui."""
        view = cast(object, self.context.get("view"))
        parent: object = getattr(self, "parent", None)
        return getattr(view, "action", None) != "list" and not isinstance(parent, serializers.ListSerializer)

    def get_avaliaveis_ids(self, obj: Solicitacao) -> list[int] | None:
        return sorted(formadores_avaliaveis_ids(obj)) if self._um_evento() else None

    def get_projeto_pergunta_avaliar_formador(self, obj: Solicitacao) -> bool | None:
        return gerencia_pergunta(obj) if self._um_evento() else None

    def get_decisao_impedida(self, obj: Solicitacao) -> str | None:
        """Impedimento de decisão de quem lê (PA-02), calculado uma vez para a página inteira.

        Só para quem aprova e não é superusuário, e só em pendente. A lista calcula todos os ids da
        página de uma vez (`decisoes_impedidas`, número de consultas constante), guardados no contexto.
        """
        if obj.status != Solicitacao.Status.PENDENTE:
            return None
        request: Any = self.context.get("request")
        user: Any = getattr(request, "user", None)
        if user is None or getattr(user, "is_superuser", False):
            return None
        calculados: dict[int, str | None] | None = cast(Any, self.context.get("_decisao_impedida"))
        if calculados is None or obj.pk not in calculados:
            calculados = calculados or {}
            parent: object = getattr(self, "parent", None)
            pagina: Any = getattr(parent, "instance", None) if isinstance(parent, serializers.ListSerializer) else None
            ids: set[int] = {int(o.pk) for o in pagina} if pagina is not None else set()
            ids.add(obj.pk)
            impedidos: dict[int, str] = {}
            if user_has_policy(user, "access_solicitation_approvals"):
                impedidos = decisoes_impedidas(user, Solicitacao.objects.filter(id__in=ids))
            calculados.update({sol_id: DECISAO_IMPEDIDA.get(impedidos.get(sol_id, "")) for sol_id in ids})
            self.context["_decisao_impedida"] = calculados
        return calculados[obj.pk]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """
        Validações para criação e edição de solicitações.

        Regras:
        1. Permite PATCH parcial: se apenas um dos campos vier no payload,
           usa o valor atual da instância para validar o intervalo.
        2. Bloqueia edição de solicitações já publicadas no Google Calendar
           (gcal_status == 'PUBLISHED') para evitar drift.
        3. Bloqueia edição de solicitações reprovadas.
        4. Exige compra que libere o par município+projeto (regra única em
           `services/compra_elegibilidade`) na criação e quando o VALOR de município ou de
           projeto muda na edição. Isentos: superuser e a capacidade de isenção.
        5. Na criação, `coordenador_acompanha` é obrigatório (decisão do dono, 05/10/2026):
           o padrão do model (False) esconderia a falta da resposta. Null o campo já recusa.
        """
        instance = getattr(self, "instance", None)

        # Regra 2: Bloquear edição durante a sincronização com o GCal.
        if instance is not None:
            if getattr(instance, "gcal_status", None) == "PUBLISHED":
                raise serializers.ValidationError(
                    {
                        "non_field_errors": [
                            "Não é possível editar uma solicitação já publicada no Google Calendar. "
                            "Cancele o evento primeiro se precisar fazer alterações."
                        ]
                    }
                )

            # M10-03 (#1625): PENDING = task Celery de publish/resync/cancel já
            # enfileirada. Editar nessa janela faz a task publicar o conteúdo
            # corrente em vez do snapshot aprovado (TOCTOU / drift).
            if getattr(instance, "gcal_status", None) == "PENDING":
                raise serializers.ValidationError(
                    {
                        "non_field_errors": [
                            "Não é possível editar enquanto a sincronização com o Google Calendar está "
                            "em andamento. Aguarde a conclusão da publicação."
                        ]
                    }
                )

            # Regra 3: Bloquear edição de solicitações reprovadas
            if getattr(instance, "status", None) == "reprovado":
                raise serializers.ValidationError(
                    {
                        "non_field_errors": [
                            "Não é possível editar uma solicitação reprovada. "
                            "Crie uma nova solicitação se necessário."
                        ]
                    }
                )

        # Regra 4: Elegibilidade de compra por município+projeto.
        # Aplica na criação e quando o VALOR de município ou de projeto muda num
        # update. (#1738: a checagem era create-only, então um PATCH trocando o par
        # para um sem compra contornava a regra.) Compara valor, não presença da
        # chave: a tela de edição manda os dois campos em todo salvamento, e salvar
        # com o mesmo par não é reatribuição — preserva a edição de solicitações
        # antigas cujo par não tem compra. A regra (DATCompra, coleção, nome geral) e a isenção
        # (superuser ou capacidade) moram em `compra_elegibilidade`.
        request = cast(Any, self.context.get("request"))
        user = getattr(request, "user", None)
        if not isento_da_regra_da_compra(user):
            municipio = attrs.get("municipio", getattr(instance, "municipio", None))
            projeto = attrs.get("projeto", getattr(instance, "projeto", None))
            reatribui_par = (
                instance is None
                or getattr(municipio, "pk", None) != instance.municipio_id
                or getattr(projeto, "pk", None) != instance.projeto_id
            )
            if reatribui_par and municipio is not None and projeto is not None:
                if not par_liberado(municipio.pk, projeto):
                    raise serializers.ValidationError(
                        {
                            "municipio": (
                                f"O município '{municipio.nome} - {municipio.uf}' não tem compra que libere "
                                f"o projeto '{projeto.nome}'. Registre a compra antes de vincular esse par."
                            )
                        }
                    )

        # Regra 1: Validação de intervalo (fim > inicio)
        inicio = attrs.get("inicio", getattr(instance, "inicio", None))
        fim = attrs.get("fim", getattr(instance, "fim", None))

        # só valida se os dois forem conhecidos
        if inicio is not None and fim is not None:
            if fim <= inicio:
                raise serializers.ValidationError({"fim": "O fim do evento deve ser posterior ao início."})

        # Regra 5
        if instance is None and "coordenador_acompanha" not in getattr(self, "initial_data", {}):
            raise serializers.ValidationError(
                {"coordenador_acompanha": ["Informe se o coordenador responsável vai acompanhar o evento."]}
            )

        return super().validate(attrs)


# ================================================================
# Issue #98 - Event Detail with AuditLog Timeline
# ================================================================


class AuditLogTimelineSerializer(serializers.ModelSerializer):
    """
    Serializer para AuditLog na timeline de eventos.

    Expõe apenas campos relevantes para exibição no Drawer:
    - id, action, details, created_at
    - usuario (nome completo ou "Sistema")

    Usado em EventDetailSerializer para timeline.
    """

    usuario_nome = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "action",
            "usuario_nome",
            "details",
            "created_at",
        ]
        read_only_fields = fields

    def get_usuario_nome(self, obj: AuditLog) -> str:
        """Retorna nome do usuário ou 'Sistema' se null."""
        return str(obj.usuario) if obj.usuario else "Sistema"

    def to_representation(self, instance: AuditLog) -> dict[str, Any]:
        # S5: quem vê a timeline não administra contas; o `error` de linha antiga levava o login (CPF).
        data = cast(dict[str, Any], super().to_representation(instance))
        data["details"] = redact_cpf_deep(data["details"])
        return data


class EventDetailSerializer(serializers.ModelSerializer):
    """
    Serializer para detalhes completos de um evento GCal (Issue #98).

    Campos expostos:
    - Dados do evento: id, municipio_nome, projeto_nome, tipo_evento_nome,
      inicio, fim, usuario_nome, coordenador_nome, fluxo (nomes; nunca o login, que é o CPF)
    - Dados GCal: gcal_status, external_event_id, gcal_last_sync_at,
      gcal_last_error, meet_link, updated_at
    - participations: Lista de participantes (read-only)
    - timeline: Últimos 20 AuditLog relacionados (actions GCal), ordenado desc

    Note: gcal_payload_hash removed (internal implementation detail)

    Permissions: CanUseGcal (policy `use_gcal`)
    Endpoint: GET /api/gcal/dashboard/events/{id}/detail/
    """

    # Campos legíveis (nomes em vez de IDs)
    municipio_nome = serializers.CharField(source="municipio.nome", read_only=True)
    projeto_nome = serializers.CharField(source="projeto.nome", read_only=True)
    tipo_evento_nome = serializers.CharField(source="tipo_evento.nome", read_only=True)
    usuario_nome = serializers.SerializerMethodField()
    coordenador_nome = serializers.SerializerMethodField()
    fluxo = serializers.SerializerMethodField()

    # Participations (aninhado)
    participations = ParticipationNestedSerializer(many=True, read_only=True)

    # Timeline de AuditLog (últimos 20, ordenado desc)
    timeline = serializers.SerializerMethodField()

    class Meta:
        model = Solicitacao
        fields = [
            "id",
            "municipio_nome",
            "projeto_nome",
            "tipo_evento_nome",
            "inicio",
            "fim",
            "usuario_nome",
            "coordenador_nome",
            "fluxo",
            "gcal_status",
            "external_event_id",
            "gcal_last_sync_at",
            "gcal_last_error",
            "meet_link",
            # gcal_payload_hash removed: internal implementation detail
            "updated_at",
            "participations",
            "timeline",
        ]
        read_only_fields = fields

    def get_usuario_nome(self, obj: Solicitacao) -> str | None:
        """Nome de quem criou a solicitação (ou "Usuario #id")."""
        usuario = cast("Usuario | None", obj.usuario)
        return str(usuario) if usuario else None

    def get_coordenador_nome(self, obj: Solicitacao) -> str | None:
        """Nome do coordenador (ou de quem criou, se o coordenador é nulo)."""
        user = cast("Usuario | None", obj.coordenador or obj.usuario)
        return str(user) if user else None

    def get_fluxo(self, obj: Solicitacao) -> str:
        """Retorna fluxo do projeto (SUPER ou NAO_SUPER)."""
        return obj.projeto.fluxo if obj.projeto else "NAO_SUPER"

    def get_timeline(self, obj: Solicitacao) -> list[dict[str, Any]]:
        """
        Retorna últimos 20 AuditLog relacionados ao evento.

        Filtro por actions GCal relevantes:
        - PUBLISH_GCAL_REQUESTED
        - PUBLISH_GCAL
        - PUBLISH_GCAL_ERROR
        - CANCEL_GCAL
        - CANCEL_GCAL_REQUESTED
        - RESYNC_GCAL_REQUESTED
        - GOOGLE_CONNECT
        - GOOGLE_DISCONNECT
        - GOOGLE_REFRESH_TOKEN

        Ordenado por created_at desc (mais recentes primeiro).
        Limite: 20 registros.
        """
        # Ações GCal relevantes para timeline
        gcal_actions = [
            "PUBLISH_GCAL_REQUESTED",
            "PUBLISH_GCAL",
            "PUBLISH_GCAL_ERROR",
            "CANCEL_GCAL",
            "CANCEL_GCAL_REQUESTED",
            "RESYNC_GCAL_REQUESTED",
            "GOOGLE_CONNECT",
            "GOOGLE_DISCONNECT",
            "GOOGLE_REFRESH_TOKEN",
        ]

        # Buscar logs relacionados ao evento (via details.solicitacao_id ou model_name)
        logs = (
            AuditLog.objects.filter(action__in=gcal_actions, details__solicitacao_id=obj.id)
            .select_related("usuario")
            .order_by("-created_at")[:20]
        )

        # Serializar — `.data` em DRF retorna ReturnList | ReturnDict | Any;
        # com many=True é sempre ReturnList (subclasse de list).
        return cast(list[dict[str, Any]], AuditLogTimelineSerializer(logs, many=True).data)
