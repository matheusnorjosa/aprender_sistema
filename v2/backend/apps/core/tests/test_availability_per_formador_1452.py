"""
Testes: disponibilidade validada por participante, não só por quem cria (#1452).

O bug: `check_conflicts` só rodava para `request.user`. Como o coordenador que cria
tipicamente não é o formador que atende, as regras RD-01..RD-08 eram avaliadas na pessoa
errada e o formador podia ser alocado em dois eventos simultâneos.

Cobre os 4 boundaries que gravam/aprovam/publicam evento, mais as decisões de negócio
(2026-07-16): bloqueio duro, CONVIDADO fora da checagem, gerente coberto via COORDENADOR/
COORD_ACOMPANHA.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from datetime import date, timedelta

from django.utils import timezone
from rest_framework import status as http_status
from rest_framework.test import APIClient

import pytest

from apps.core.models import Compra, Participation, Solicitacao
from apps.core.tests.factories import (
    GroupFactory,
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def municipio():
    return MunicipioFactory(nome="Fortaleza 1452", uf="CE")


@pytest.fixture
def tipo_evento():
    return TipoEventoFactory(nome="Formação 1452")


@pytest.fixture
def projeto_super(municipio):
    """
    Fluxo SUPER: fica pendente na criação (PA-04), permitindo testar a aprovação.

    A Compra é obrigatória: o serializer recusa solicitação para (município, projeto) sem
    compra registrada. Os testes de criação usam `projeto=None` e não precisam dela.
    """
    projeto = ProjetoFactory(nome="Projeto SUPER 1452", fluxo="SUPER")
    Compra.objects.create(
        codigo="COMP-1452",
        projeto=projeto,
        municipio=municipio,
        quantidade=10,
        data=date(2026, 1, 10),
        uso="Fixture #1452",
        external_hash="compra-1452-hash",
    )
    return projeto


@pytest.fixture
def coordenador():
    """Quem cria o evento. Não é o formador — é justamente esse o ponto do #1452."""
    user = UsuarioFactory(username="coord_1452", first_name="Ana", last_name="Coordenadora")
    user.groups.add(GroupFactory(name="Coordenador"))
    return user


@pytest.fixture
def formador():
    return UsuarioFactory(username="formador_1452", first_name="Bruno", last_name="Formador")


@pytest.fixture
def aprovador():
    """Gerente da Superintendência — único perfil que aprova além do superuser (PA-02)."""
    user = UsuarioFactory(username="gerente_1452", first_name="Carla", last_name="Gerente")
    user.groups.add(GroupFactory(name="Superintendência"), GroupFactory(name="Gerente"))
    return user


@pytest.fixture
def horario():
    """Janela base: amanhã, 09:00–11:00 (UTC)."""
    inicio = (timezone.now() + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    return inicio, inicio + timedelta(hours=2)


def _evento_aprovado_para(usuario, municipio, tipo_evento, inicio, fim, projeto=None):
    """Evento já aprovado ocupando a agenda do usuário (participa como FORMADOR)."""
    solicitacao = SolicitacaoFactory(
        usuario=usuario,
        municipio=municipio,
        tipo_evento=tipo_evento,
        projeto=projeto,
        inicio=inicio,
        fim=fim,
        status=Solicitacao.Status.APROVADO,
    )
    Participation.objects.create(solicitacao=solicitacao, usuario=usuario, role=Participation.Role.FORMADOR)
    return solicitacao


def _payload(municipio, tipo_evento, inicio, fim, projeto=None, **extra):
    payload = {
        "municipio": municipio.pk,
        "tipo_evento": tipo_evento.pk,
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat(),
    }
    if projeto is not None:
        payload["projeto"] = projeto.pk
    payload.update(extra)
    return payload


# ============================================================================
# O bug do #1452: a regra rodava na pessoa errada
# ============================================================================


class TestCreateChecaFormador:
    def test_bloqueia_quando_formador_ja_alocado_mesmo_com_coordenador_livre(
        self, coordenador, formador, municipio, tipo_evento, horario
    ):
        """
        O coração do #1452: coordenador com agenda livre, formador já alocado.

        Antes da correção retornava 201 — a checagem rodava no coordenador, que estava
        livre, e o formador era gravado depois, sem passar por regra nenhuma.
        """
        inicio, fim = horario
        _evento_aprovado_para(formador, municipio, tipo_evento, inicio, fim)

        client = APIClient()
        client.force_authenticate(user=coordenador)
        response = client.post(
            "/api/solicitacoes/",
            _payload(
                municipio,
                tipo_evento,
                inicio + timedelta(minutes=30),
                fim + timedelta(minutes=30),
                extra_participants={"formador_ids": [formador.pk]},
            ),
            format="json",
        )

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "availability_conflict"
        assert "Bruno Formador" in response.data["detail"]

        bloqueados = response.data["errors"]["blocked_participants"]
        assert [p["usuario_id"] for p in bloqueados] == [formador.pk]

    def test_conflito_desfaz_o_evento_inteiro(self, coordenador, formador, municipio, tipo_evento, horario):
        """Bloqueio precisa reverter a solicitação e as participações já gravadas."""
        inicio, fim = horario
        _evento_aprovado_para(formador, municipio, tipo_evento, inicio, fim)
        solicitacoes_antes = Solicitacao.objects.count()
        participations_antes = Participation.objects.count()

        client = APIClient()
        client.force_authenticate(user=coordenador)
        client.post(
            "/api/solicitacoes/",
            _payload(
                municipio,
                tipo_evento,
                inicio,
                fim,
                extra_participants={"formador_ids": [formador.pk]},
            ),
            format="json",
        )

        assert Solicitacao.objects.count() == solicitacoes_antes
        assert Participation.objects.count() == participations_antes

    def test_permite_quando_formador_esta_livre(self, coordenador, formador, municipio, tipo_evento, horario):
        """Guarda contra o oposto: bloquear tudo também seria bug."""
        inicio, fim = horario

        client = APIClient()
        client.force_authenticate(user=coordenador)
        response = client.post(
            "/api/solicitacoes/",
            _payload(
                municipio,
                tipo_evento,
                inicio,
                fim,
                extra_participants={"formador_ids": [formador.pk]},
            ),
            format="json",
        )

        assert response.status_code == http_status.HTTP_201_CREATED
        assert Participation.objects.filter(
            solicitacao_id=response.data["id"], usuario=formador, role=Participation.Role.FORMADOR
        ).exists()

    def test_evento_adjacente_nao_conflita(self, coordenador, formador, municipio, tipo_evento, horario):
        """RD-01: `fim == inicio` é encosto, não sobreposição."""
        inicio, fim = horario
        _evento_aprovado_para(formador, municipio, tipo_evento, inicio, fim)

        client = APIClient()
        client.force_authenticate(user=coordenador)
        response = client.post(
            "/api/solicitacoes/",
            _payload(
                municipio,
                tipo_evento,
                fim,  # começa exatamente quando o outro termina
                fim + timedelta(hours=1),
                extra_participants={"formador_ids": [formador.pk]},
            ),
            format="json",
        )

        assert response.status_code == http_status.HTTP_201_CREATED

    def test_coord_acompanha_tambem_e_checado(self, coordenador, municipio, tipo_evento, horario):
        """
        COORD_ACOMPANHA ocupa a agenda como qualquer outro recurso.

        Também é por aqui que o gerente entra: "Gerente" é função RBAC, não papel de
        Participation — um gerente que participa é gravado como COORDENADOR ou
        COORD_ACOMPANHA, então já está coberto.
        """
        inicio, fim = horario
        acompanhante = UsuarioFactory(username="acompanha_1452", first_name="Dora", last_name="Acompanha")
        _evento_aprovado_para(acompanhante, municipio, tipo_evento, inicio, fim)

        client = APIClient()
        client.force_authenticate(user=coordenador)
        response = client.post(
            "/api/solicitacoes/",
            _payload(
                municipio,
                tipo_evento,
                inicio,
                fim,
                extra_participants={"coord_acompanha_ids": [acompanhante.pk]},
            ),
            format="json",
        )

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "availability_conflict"

    def test_convidado_nao_e_checado(self, coordenador, municipio, tipo_evento, horario):
        """
        CONVIDADO é audiência, não recurso alocado (decisão de negócio 2026-07-16).

        Checá-lo estouraria a capacidade diária (RD-05) de quem é convidado a vários
        eventos no mesmo dia, bloqueando todos.
        """
        inicio, fim = horario
        convidado = UsuarioFactory(username="convidado_1452")
        _evento_aprovado_para(convidado, municipio, tipo_evento, inicio, fim)

        client = APIClient()
        client.force_authenticate(user=coordenador)
        response = client.post(
            "/api/solicitacoes/",
            _payload(municipio, tipo_evento, inicio, fim),
            format="json",
        )
        assert response.status_code == http_status.HTTP_201_CREATED

        Participation.objects.create(
            solicitacao_id=response.data["id"], usuario=convidado, role=Participation.Role.CONVIDADO
        )

        from apps.core.services.solicitacao_availability import check_solicitacao_availability

        guard = check_solicitacao_availability(Solicitacao.objects.get(pk=response.data["id"]), lock=False)
        assert guard.ok
        assert convidado.pk not in guard.checked_usuario_ids

    def test_coordenador_que_tambem_e_formador_conta_uma_vez(self, coordenador, municipio, tipo_evento):
        """
        Dedup por usuario_id: o coordenador é sempre gravado como COORDENADOR e pode
        também vir em formador_ids. Sem dedup, as horas dele contariam 2x no RD-05 e um
        evento de 5h estouraria sozinho o limite diário de 8h.
        """
        inicio = (timezone.now() + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
        fim = inicio + timedelta(hours=5)

        client = APIClient()
        client.force_authenticate(user=coordenador)
        response = client.post(
            "/api/solicitacoes/",
            _payload(
                municipio,
                tipo_evento,
                inicio,
                fim,
                extra_participants={"formador_ids": [coordenador.pk]},
            ),
            format="json",
        )

        assert response.status_code == http_status.HTTP_201_CREATED

        from apps.core.services.solicitacao_availability import check_solicitacao_availability

        guard = check_solicitacao_availability(Solicitacao.objects.get(pk=response.data["id"]), lock=False)
        assert guard.checked_usuario_ids == [coordenador.pk]

    def test_convidado_externo_sem_cadastro_e_reportado_nao_ignorado(
        self, coordenador, municipio, tipo_evento, horario
    ):
        """
        Guest sem Usuario não tem agenda para checar. O que não pode é o pulo ser
        silencioso — precisa aparecer em `skipped_guests` (PA-05).
        """
        inicio, fim = horario

        client = APIClient()
        client.force_authenticate(user=coordenador)
        response = client.post(
            "/api/solicitacoes/",
            _payload(
                municipio,
                tipo_evento,
                inicio,
                fim,
                extra_participants={"formador_emails": ["externo@fora.com"]},
            ),
            format="json",
        )
        assert response.status_code == http_status.HTTP_201_CREATED

        from apps.core.services.solicitacao_availability import check_solicitacao_availability

        guard = check_solicitacao_availability(Solicitacao.objects.get(pk=response.data["id"]), lock=False)
        assert guard.skipped_guests == ["externo@fora.com"]


# ============================================================================
# Boundary 2: edição
# ============================================================================


class TestUpdateChecaFormador:
    def test_mover_evento_para_horario_ocupado_do_formador_bloqueia(
        self, coordenador, formador, municipio, tipo_evento, horario
    ):
        """`perform_update` não tinha checagem nenhuma: dava para editar até o conflito."""
        inicio, fim = horario
        _evento_aprovado_para(formador, municipio, tipo_evento, inicio, fim)

        client = APIClient()
        client.force_authenticate(user=coordenador)
        criado = client.post(
            "/api/solicitacoes/",
            _payload(
                municipio,
                tipo_evento,
                fim + timedelta(days=2),
                fim + timedelta(days=2, hours=2),
                extra_participants={"formador_ids": [formador.pk]},
            ),
            format="json",
        )
        assert criado.status_code == http_status.HTTP_201_CREATED
        solicitacao_id = criado.data["id"]

        response = client.patch(
            f"/api/solicitacoes/{solicitacao_id}/",
            {"inicio": inicio.isoformat(), "fim": fim.isoformat()},
            format="json",
        )

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "availability_conflict"

        solicitacao = Solicitacao.objects.get(pk=solicitacao_id)
        assert solicitacao.inicio != inicio, "edição bloqueada não pode ter sido persistida"

    def test_editar_sem_mover_nao_conflita_consigo_mesmo(self, coordenador, formador, municipio, tipo_evento, horario):
        """
        `exclude_solicitacao_id`: o evento sendo editado não pode entrar na própria
        checagem — senão qualquer edição de evento aprovado seria bloqueada por ele mesmo.
        """
        inicio, fim = horario

        client = APIClient()
        client.force_authenticate(user=coordenador)
        criado = client.post(
            "/api/solicitacoes/",
            _payload(
                municipio,
                tipo_evento,
                inicio,
                fim,
                extra_participants={"formador_ids": [formador.pk]},
            ),
            format="json",
        )
        assert criado.status_code == http_status.HTTP_201_CREATED

        response = client.patch(
            f"/api/solicitacoes/{criado.data['id']}/",
            {"observacoes": "ajuste de texto"},
            format="json",
        )

        assert response.status_code == http_status.HTTP_200_OK


# ============================================================================
# Boundary 3: aprovação (TOCTOU)
# ============================================================================


class TestApproveRevalida:
    def test_aprovar_revalida_conflito_surgido_depois(
        self, coordenador, formador, aprovador, municipio, tipo_evento, projeto_super, horario
    ):
        """
        SUPER fica pendente e pode ficar dias na fila. Se a agenda do formador foi
        ocupada nesse meio-tempo, aprovar sem revalidar cria o double-booking.
        """
        inicio, fim = horario

        client = APIClient()
        client.force_authenticate(user=coordenador)
        criado = client.post(
            "/api/solicitacoes/",
            _payload(
                municipio,
                tipo_evento,
                inicio,
                fim,
                projeto=projeto_super,
                extra_participants={"formador_ids": [formador.pk]},
            ),
            format="json",
        )
        assert criado.status_code == http_status.HTTP_201_CREATED, criado.data
        assert criado.data["status"] == "pendente"

        # Agenda do formador é ocupada depois da criação
        _evento_aprovado_para(formador, municipio, tipo_evento, inicio, fim)

        approver_client = APIClient()
        approver_client.force_authenticate(user=aprovador)
        response = approver_client.patch(f"/api/solicitacoes/{criado.data['id']}/approve/", {}, format="json")

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "availability_conflict"
        assert Solicitacao.objects.get(pk=criado.data["id"]).status == "pendente"

    def test_batch_aprova_a_primeira_e_barra_a_conflitante(
        self, coordenador, formador, aprovador, municipio, tipo_evento, projeto_super, horario
    ):
        """
        Duas pendentes do mesmo formador no mesmo horário, aprovadas no mesmo lote.

        `select_for_update` não resolve: cada uma tranca a própria linha, e `pendente` é
        invisível para a checagem (que só olha aprovados). Como revalidamos item a item
        dentro da transação, a segunda já enxerga a primeira como aprovada.
        """
        inicio, fim = horario

        client = APIClient()
        client.force_authenticate(user=coordenador)
        ids = []
        for _ in range(2):
            criado = client.post(
                "/api/solicitacoes/",
                _payload(
                    municipio,
                    tipo_evento,
                    inicio,
                    fim,
                    projeto=projeto_super,
                    extra_participants={"formador_ids": [formador.pk]},
                ),
                format="json",
            )
            assert criado.status_code == http_status.HTTP_201_CREATED
            ids.append(criado.data["id"])

        approver_client = APIClient()
        approver_client.force_authenticate(user=aprovador)
        response = approver_client.post("/api/solicitacoes/batch-approve/", {"ids": ids}, format="json")

        assert response.status_code == http_status.HTTP_200_OK
        aprovadas = Solicitacao.objects.filter(id__in=ids, status="aprovado").count()
        assert aprovadas == 1, "o lote não pode aprovar dois eventos conflitantes do mesmo formador"
        assert Solicitacao.objects.filter(id__in=ids, status="pendente").count() == 1


# ============================================================================
# Cache: enforcement não pode ler resultado velho nem envenenar a chave
# ============================================================================


class TestCacheSplit:
    def test_check_conflicts_nao_aceita_exclude_solicitacao_id(self, formador, municipio, horario):
        """
        A chave de cache é montada a partir de uma whitelist fixa. Um kwarg extra mudaria
        o resultado sem mudar a chave — a próxima chamada com a mesma chave receberia a
        resposta errada. Quem precisa excluir usa a versão sem cache.
        """
        from apps.core.services.availability_service import check_conflicts

        inicio, fim = horario
        with pytest.raises(TypeError):
            check_conflicts(  # type: ignore[call-arg]
                usuario=formador,
                inicio=inicio,
                fim=fim,
                municipio=municipio,
                exclude_solicitacao_id=1,
            )

    def test_check_conflicts_uncached_enxerga_evento_recem_criado(self, formador, municipio, tipo_evento, horario):
        """
        Enforcement lê sempre do banco: um resultado com até 5 min de atraso deixaria
        passar exatamente o double-booking que o lock existe para impedir.
        """
        from apps.core.services.availability_service import check_conflicts, check_conflicts_uncached

        inicio, fim = horario

        assert check_conflicts(usuario=formador, inicio=inicio, fim=fim, municipio=municipio).ok
        _evento_aprovado_para(formador, municipio, tipo_evento, inicio, fim)

        assert not check_conflicts_uncached(usuario=formador, inicio=inicio, fim=fim, municipio=municipio).ok

    def test_exclude_solicitacao_id_tambem_tira_do_limite_diario(self, formador, municipio, tipo_evento):
        """
        A exclusão precisa valer na origem da query, não como filtro por `ref_id` depois:
        o conflito de capacidade diária (M, RD-05) não tem `ref_id` e somaria as horas do
        próprio evento em dobro.
        """
        from apps.core.services.availability_service import check_conflicts_uncached

        inicio = (timezone.now() + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
        fim = inicio + timedelta(hours=5)
        solicitacao = _evento_aprovado_para(formador, municipio, tipo_evento, inicio, fim)

        # 5h já gravadas + 5h do mesmo evento = 10h > limite de 8h/dia
        sem_exclusao = check_conflicts_uncached(usuario=formador, inicio=inicio, fim=fim, municipio=municipio)
        assert [c.code for c in sem_exclusao.conflicts].count("M") == 1

        com_exclusao = check_conflicts_uncached(
            usuario=formador,
            inicio=inicio,
            fim=fim,
            municipio=municipio,
            exclude_solicitacao_id=solicitacao.pk,
        )
        assert com_exclusao.ok
