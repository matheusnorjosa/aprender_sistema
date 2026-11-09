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

from drf_spectacular.utils import extend_schema_field

from apps.core.models import AuditLog, Participation, Projeto, Solicitacao, Usuario
from apps.core.pii import email_sem_cpf, redact_cpf_deep
from apps.core.rbac.permissions import PodeExcluirSolicitacao
from apps.core.rbac.policies import user_has_policy
from apps.core.serializers.usuario import UserSlimSerializer
from apps.core.services.avaliacao_formador import formadores_avaliaveis_ids, gerencia_pergunta
from apps.core.services.compra_elegibilidade import (
    MSG_PROJETO_EM_ESPERA,
    isento_da_regra_da_compra,
    par_liberado,
    projeto_em_espera,
    solicitacoes_com_par_liberado,
)
from apps.core.services.solicitacao_approval import DECISAO_IMPEDIDA, decisoes_impedidas_na_lista
from apps.core.services.solicitacao_exclusao import ids_ja_decididas, motivo_que_impede_excluir
from apps.core.services.solicitacao_projetos import (
    MSG_SEGUNDO_SEM_PRIMEIRO,
    ids_dos_projetos,
    par_de_projetos_invalido,
    projetos_do_evento,
    rotulo_dos_projetos,
)
from apps.core.services.solicitacao_scope import EscritaEmSolicitacao, scope_publishable_solicitacoes


class ProjetoDoEventoSerializer(serializers.Serializer):
    """Um projeto do evento (#2036): `projetos` lista os dois, na ordem das vagas."""

    id = serializers.IntegerField()
    nome = serializers.CharField()


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
    # Evento de dois projetos (#2036): `projeto_nome` é o rótulo "A / B" (o nome, com um projeto só) e
    # `projetos` lista os dois. `projeto_2` é opcional na escrita (regra do par em `validate`); o PATCH sem a
    # chave não mexe nele.
    projeto_nome = serializers.SerializerMethodField()
    projeto_2 = serializers.PrimaryKeyRelatedField(queryset=Projeto.objects.all(), required=False, allow_null=True)
    projetos = serializers.SerializerMethodField()
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
    # Quem lê pode tirar este evento do Google (`can_publish_solicitacao`)? Minhas Solicitações só
    # mostra Excluir de evento no Google a quem pode as duas coisas (a exclusão tira de lá também).
    pode_tirar_do_google = serializers.SerializerMethodField()
    # Quem lê pode excluir esta linha? A regra do DELETE: quem (`PodeExcluirSolicitacao`, com a Apoio no
    # evento de outra pessoa que está no Google) e as recusas que se sabem sem o Google
    # (`motivo_que_impede_excluir`). Publicar na agenda só mostra Excluir com ele.
    pode_excluir = serializers.SerializerMethodField()
    # Por que esta linha não se exclui, quando a recusa se sabe sem o Google (`motivo_que_impede_excluir`,
    # texto fixo, sem dado pessoal); null quando não há recusa. Minhas Solicitações mostra o motivo.
    motivo_de_nao_excluir = serializers.SerializerMethodField()
    # O par (município, projeto) não tem compra que o libere (`compra_elegibilidade`); a tela de
    # Aprovações marca a linha "Sem compra" (pedido do dono, 03/11/2026). Uma consulta para a página.
    sem_compra = serializers.SerializerMethodField()

    class Meta:
        model = Solicitacao
        fields = [
            "id",
            "usuario",
            "municipio",
            "municipio_nome",
            "projeto",
            "projeto_nome",
            "projeto_2",
            "projetos",
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
            "pode_tirar_do_google",
            "pode_excluir",
            "motivo_de_nao_excluir",
            "sem_compra",
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
        # Projeto obrigatório na escrita (revisão do #2149): sem ele o evento nascia pendente e pulava
        # a regra da compra e o escopo de gerência do projeto. O FK segue `null=True` por causa do dado
        # legado e dos importadores, que gravam pelo ORM. PATCH sem a chave não é afetado.
        # Município idem, para todos (isentos inclusive): sem ele a Regra 4 não tinha par para conferir.
        extra_kwargs = {
            "projeto": {
                "required": True,
                "allow_null": False,
                "error_messages": {
                    "required": "Informe o projeto do evento.",
                    "null": "Informe o projeto do evento.",
                },
            },
            "municipio": {
                "required": True,
                "allow_null": False,
                "error_messages": {
                    "required": "Informe o município do evento.",
                    "null": "Informe o município do evento.",
                },
            },
        }

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

    def get_projeto_nome(self, obj: Solicitacao) -> str | None:
        return rotulo_dos_projetos(obj)

    @extend_schema_field(ProjetoDoEventoSerializer(many=True))
    def get_projetos(self, obj: Solicitacao) -> list[dict[str, Any]]:
        return [{"id": p.pk, "nome": p.nome} for p in projetos_do_evento(obj)]

    def get_projeto_pergunta_avaliar_formador(self, obj: Solicitacao) -> bool | None:
        return gerencia_pergunta(obj) if self._um_evento() else None

    def get_decisao_impedida(self, obj: Solicitacao) -> str | None:
        """Impedimento de decisão de quem lê (PA-02), calculado uma vez para a página inteira.

        Só para quem aprova e não é superusuário, e só em pendente. A lista calcula todos os ids da
        página de uma vez (`decisoes_impedidas_na_lista`: a segregação e, para a aprovadora por vínculo,
        o que está fora do escopo dela; número de consultas constante), guardados no contexto.
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
            ids = self._ids_da_pagina(obj)
            impedidos: dict[int, str] = {}
            if user_has_policy(user, "access_solicitation_approvals"):
                impedidos = decisoes_impedidas_na_lista(user, Solicitacao.objects.filter(id__in=ids))
            calculados.update({sol_id: DECISAO_IMPEDIDA.get(impedidos.get(sol_id, "")) for sol_id in ids})
            self.context["_decisao_impedida"] = calculados
        return calculados[obj.pk]

    def _ids_da_pagina(self, obj: Solicitacao) -> set[int]:
        """Ids da página que está sendo serializada (só `obj` fora de listagem)."""
        return {int(o.pk) for o in self._pagina(obj)}

    def _pagina(self, obj: Solicitacao) -> list[Solicitacao]:
        """Solicitações da página que está sendo serializada, com `obj` (só ele fora de listagem)."""
        parent: object = getattr(self, "parent", None)
        pagina: Any = getattr(parent, "instance", None) if isinstance(parent, serializers.ListSerializer) else None
        objs: list[Solicitacao] = list(pagina) if pagina is not None else []
        if all(o.pk != obj.pk for o in objs):
            objs.append(obj)
        return objs

    def get_pode_tirar_do_google(self, obj: Solicitacao) -> bool:
        """`can_publish_solicitacao` de quem lê, para a página inteira numa consulta só.

        Lê a mesma regra da guarda de objeto (`scope_publishable_solicitacoes`, que usa o mesmo
        `_publish_tier`): o escopo de publicação sai uma vez por request, guardado no contexto.
        """
        calculados: dict[int, bool] | None = cast(Any, self.context.get("_pode_tirar_do_google"))
        if calculados is None or obj.pk not in calculados:
            calculados = calculados or {}
            request: Any = self.context.get("request")
            ids = self._ids_da_pagina(obj)
            ids_publicaveis: Any = scope_publishable_solicitacoes(
                Solicitacao.objects.filter(id__in=ids), getattr(request, "user", None)
            ).values_list("id", flat=True)
            publicaveis: set[int] = set(ids_publicaveis)
            calculados.update({sol_id: sol_id in publicaveis for sol_id in ids})
            self.context["_pode_tirar_do_google"] = calculados
        return calculados[obj.pk]

    def get_pode_excluir(self, obj: Solicitacao) -> bool:
        """O DELETE de quem lê daria certo (salvo o Google recusar)? Para a página inteira de uma vez.

        Mesma regra do `destroy`: `PodeExcluirSolicitacao.permite` com uma `EscritaEmSolicitacao` só (os
        fatos de quem lê saem uma vez) e `motivo_que_impede_excluir`, com a aprovação da página numa
        consulta (`ids_ja_decididas`) e o `pode_tirar_do_google` já calculado.
        """
        calculados: dict[int, bool] | None = cast(Any, self.context.get("_pode_excluir"))
        if calculados is None or obj.pk not in calculados:
            calculados = calculados or {}
            request: Any = self.context.get("request")
            user: Any = getattr(request, "user", None)
            pagina = self._pagina(obj)
            motivos: dict[int, str | None] = cast(Any, self.context.setdefault("_motivo_de_nao_excluir", {}))
            if user is None or not getattr(user, "is_authenticated", False):
                calculados.update({o.pk: False for o in pagina})
                motivos.update({o.pk: None for o in pagina})
            else:
                permissao = PodeExcluirSolicitacao()
                escrita = EscritaEmSolicitacao(user)
                decididas = ids_ja_decididas(o.pk for o in pagina)
                for o in pagina:
                    motivo = motivo_que_impede_excluir(
                        o, ja_decidida=o.pk in decididas, pode_tirar_do_google=self.get_pode_tirar_do_google(o)
                    )
                    calculados[o.pk] = motivo is None and permissao.permite(user, o, escrita)
                    motivos[o.pk] = motivo
            self.context["_pode_excluir"] = calculados
        return calculados[obj.pk]

    def get_motivo_de_nao_excluir(self, obj: Solicitacao) -> str | None:
        """Calculado junto com `pode_excluir`, para a página inteira."""
        self.get_pode_excluir(obj)
        return cast(dict[int, str | None], self.context["_motivo_de_nao_excluir"])[obj.pk]

    def get_sem_compra(self, obj: Solicitacao) -> bool:
        """O evento foi para aprovação por falta de compra (pela última marca) ou, sem marca, o par de hoje.

        A marca é o último `AuditLog` `CREATE`/`UPDATE` com `details.sem_compra` (true ou false: a criação e
        toda edição que muda o par a gravam). A compra que entra antes da decisão não apaga a explicação da
        fila, e a edição para um par com compra a apaga. Sem marca (evento antigo), vale o par de hoje
        (`solicitacoes_com_par_liberado`; sem município ou sem projeto não há par). Duas consultas por página.
        """
        calculados: dict[int, bool] | None = cast(Any, self.context.get("_sem_compra"))
        if calculados is None or obj.pk not in calculados:
            calculados = calculados or {}
            pagina = self._pagina(obj)
            com_par = {o.pk for o in pagina if o.municipio_id is not None and o.projeto_id is not None}
            liberados: set[int] = set(
                solicitacoes_com_par_liberado(Solicitacao.objects.filter(pk__in=com_par)).values_list("pk", flat=True)
            )
            marcas: dict[int, bool] = {}
            for sol_id, marca in (
                AuditLog.objects.filter(
                    model_name="Solicitacao",
                    action__in=(AuditLog.Action.CREATE, AuditLog.Action.UPDATE),
                    details__solicitacao_id__in=[o.pk for o in pagina],
                    details__has_key="sem_compra",
                )
                .order_by("created_at", "pk")
                .values_list("details__solicitacao_id", "details__sem_compra")
            ):
                marcas[int(sol_id)] = marca is True  # a última vence
            calculados.update({o.pk: marcas.get(o.pk, o.pk in com_par and o.pk not in liberados) for o in pagina})
            self.context["_sem_compra"] = calculados
        return calculados[obj.pk]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """
        Validações para criação e edição de solicitações.

        Regras:
        1. Permite PATCH parcial: se apenas um dos campos vier no payload,
           usa o valor atual da instância para validar o intervalo.
        2. Bloqueia edição de solicitações já publicadas no Google Calendar
           (gcal_status == 'PUBLISHED') para evitar drift, e das que estão lá pela planilha
           (`publicado_fora_do_sistema`, mesma regra).
        3. Bloqueia edição de solicitações reprovadas.
        4. Confere a compra que libera o par município+projeto (regra única em
           `services/compra_elegibilidade`) na criação e quando o VALOR de município ou de
           projeto muda na edição. Par sem compra não é mais recusado (pedido do dono, 03/11/2026):
           fica marcado em `self.par_sem_compra`, e a view manda o evento para aprovação. O projeto
           "em espera" (sem compra em município nenhum) segue sem receber evento: 400 em `projeto`. Isentos
           (superuser e a capacidade de isenção) não são conferidos nem marcados. Para quem não é
           isento, município vazio não pula a regra: o campo é obrigatório na escrita (Meta) e o
           evento antigo sem município não troca de projeto sem informar o município.
        5. Na criação, `coordenador_acompanha` é obrigatório (decisão do dono, 05/10/2026):
           o padrão do model (False) esconderia a falta da resposta. Null o campo já recusa.
        6. Evento de dois projetos (#2036): a regra do par (`_conferir_projetos`) e, na Regra 4, o conjunto
           dos projetos no lugar do projeto (os dois cobertos; o 2º "em espera" dá 400 em `projeto_2`).
        """
        instance = getattr(self, "instance", None)

        # Regra 2: Bloquear edição durante a sincronização com o GCal.
        if instance is not None:
            # Evento no Google pela planilha (carga da virada): segue a regra do publicado pelo
            # sistema, e mudar aqui não muda a agenda (decisão do dono, 19/10/2026).
            if getattr(instance, "publicado_fora_do_sistema", False):
                raise serializers.ValidationError(
                    {
                        "non_field_errors": [
                            "Este evento está no Google Agenda pela planilha e o sistema não o adotou: mudar aqui não "
                            "muda a agenda. Ajuste no Google, ou peça a adoção."
                        ]
                    }
                )
            if getattr(instance, "gcal_status", None) == "PUBLISHED":
                raise serializers.ValidationError(
                    {
                        "non_field_errors": [
                            # D25: quem pediu não cancela o evento; o Apoio ou o Controle o tira só do Google.
                            "Este evento já está no Google Agenda. Para editar, peça ao Apoio de Coordenação da "
                            "sua gerência, na tela Publicar na agenda, ou ao Controle, na Pré-agenda, que tire o "
                            "evento só do Google; depois disso, você consegue editar aqui."
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
        # (superuser ou capacidade) moram em `compra_elegibilidade`. Sem compra não recusa: marca
        # (`par_sem_compra`) para a view mandar o evento para aprovação (pedido do dono, 03/11/2026).
        projeto, projeto_2 = self._conferir_projetos(attrs, instance)
        self.par_sem_compra = False
        self.par_conferido = False  # o par foi conferido (quem não é isento, par novo): a view grava a marca
        request = cast(Any, self.context.get("request"))
        user = getattr(request, "user", None)
        if not isento_da_regra_da_compra(user):
            municipio = attrs.get("municipio", getattr(instance, "municipio", None))
            # Evento de dois projetos (#2036): o par muda quando muda o CONJUNTO de projetos (inverter as
            # vagas não é reatribuir), e o evento só sai sem a marca com os dois cobertos (a leitura da lista,
            # `solicitacoes_com_par_liberado`, diz o mesmo; decisão do dono de 08/11/2026).
            projetos = [p for p in (projeto, projeto_2) if p is not None]
            reatribui_par = (
                instance is None
                or getattr(municipio, "pk", None) != instance.municipio_id
                or frozenset(p.pk for p in projetos) != ids_dos_projetos(instance)
            )
            if reatribui_par and projeto is not None:
                # Evento antigo sem município (gravado pelo ORM) num PATCH que só troca o projeto:
                # sem o par não há o que conferir, então não pula a regra.
                if municipio is None:
                    raise serializers.ValidationError({"municipio": "Informe o município do evento."})
                for campo, p in (("projeto", projeto), ("projeto_2", projeto_2)):
                    if p is not None and projeto_em_espera(p):
                        raise serializers.ValidationError({campo: MSG_PROJETO_EM_ESPERA})
                self.par_sem_compra = not all(par_liberado(municipio.pk, p) for p in projetos)
                self.par_conferido = True

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

    def _conferir_projetos(self, attrs: dict[str, Any], instance: Any) -> tuple[Any, Any]:
        """Evento de dois projetos (#2036; decisões do dono de 08/11/2026): os projetos finais, conferidos.

        - Inverter as vagas não muda nada: o conjunto é o mesmo, e a ordem gravada fica (sem `changed_fields`
          falso, que impediria quem salvou de decidir, PA-02).
        - Quando o valor de alguma vaga muda, o 2º passa pela regra do par (`par_de_projetos_invalido`: o mesmo
          projeto, gerência vazia, outra gerência ou outro fluxo) e não fica sem o 1º. Erro em `projeto_2`.
          Vale também para quem é isento da regra da compra.
        """
        projeto = attrs.get("projeto", getattr(instance, "projeto", None))
        projeto_2 = attrs.get("projeto_2", getattr(instance, "projeto_2", None))
        if instance is None:
            mudou = projeto_2 is not None
        else:
            if (
                projeto_2 is not None
                and getattr(projeto, "pk", None) == instance.projeto_2_id
                and projeto_2.pk == instance.projeto_id
            ):
                attrs["projeto"], attrs["projeto_2"] = instance.projeto, instance.projeto_2
                return instance.projeto, instance.projeto_2
            mudou = (getattr(projeto, "pk", None), getattr(projeto_2, "pk", None)) != (
                instance.projeto_id,
                instance.projeto_2_id,
            )
        if mudou and projeto_2 is not None:
            motivo = MSG_SEGUNDO_SEM_PRIMEIRO if projeto is None else par_de_projetos_invalido(projeto, projeto_2)
            if motivo:
                raise serializers.ValidationError({"projeto_2": motivo})
        return projeto, projeto_2


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

    # Campos legíveis (nomes em vez de IDs). `projeto_nome`: o rótulo "A / B" do evento de dois projetos.
    municipio_nome = serializers.CharField(source="municipio.nome", read_only=True)
    projeto_nome = serializers.SerializerMethodField()
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

    def get_projeto_nome(self, obj: Solicitacao) -> str | None:
        return rotulo_dos_projetos(obj)

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
        - GCAL_COPIA_GOOGLE (horário ou cancelamento copiado do Google)

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
            "GCAL_COPIA_GOOGLE",
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
