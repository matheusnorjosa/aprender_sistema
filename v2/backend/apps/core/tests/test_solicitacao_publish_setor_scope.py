"""#1656 Feature 2 — publish/preview/resync/cancel GCal ESCOPADO por gerência.

Uma "Apoio de Coordenação" (papel APOIO vigente em gerência ativa) pode VER e
PUBLICAR/prever/resincronizar/cancelar no Google Calendar os eventos APROVADOS das
gerências onde é APOIO — de qualquer criador — SEM virar global e SEM poder
editar/excluir eventos alheios. PR 9 (16/10/2026): a gerência do evento é
`projeto.gerencia_id`; `Projeto.setor` e `Gerencia.setor_canonico` não dão escopo.

Garantias travadas aqui:
- ✅ Apoio publica evento aprovado da sua gerência criado por TERCEIRO → 202 (o coração).
- ✅ Apoio publica a própria aprovada → 202; preview/resync/cancel da gerência → ok.
- ✅ Evento de OUTRA gerência → 404 (fora do escopo do get_object; indistinguível de inexistente).
- ⚑ SEGURANÇA: PATCH/DELETE de evento da gerência que não é dela → 403/404
  (`user_can_access_solicitacao` intacto; IsOwnerOrPrivileged barra a edição).
- ⚑ CONTENÇÃO: não ganhou `use_gcal` → 403 nos endpoints GCal em lote.
- ⚑ SENTINELA: `user_is_solicitacao_global(apoio) is False`; `scope_solicitacoes`
  não retorna evento de outra gerência.
- Regressão: Controle/Super publicam qualquer evento; escopo de Gerente inalterado.
- Vigência: EquipeGerencia expirada → sem papel APOIO vigente → não publica.
- Fail-closed: projeto sem gerência → ninguém (exceto global) publica, nem a própria.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from datetime import timedelta
from unittest.mock import Mock, patch

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.core.models import EquipeGerencia, Gerencia, Solicitacao
from apps.core.services.solicitacao_scope import scope_solicitacoes, user_is_solicitacao_global
from apps.core.tests.factories import (
    GroupFactory,
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _mock_task_result(task_id: str = "fake-task-id"):
    result = Mock()
    result.id = task_id
    return result


def _aprovada(owner, projeto, *, municipio=None, tipo_evento=None, **extra) -> Solicitacao:
    inicio = timezone.now() + timedelta(days=3)
    return SolicitacaoFactory(
        usuario=owner,
        municipio=municipio or MunicipioFactory(),
        projeto=projeto,
        tipo_evento=tipo_evento or TipoEventoFactory(nome="Formacao PSS"),
        inicio=inicio,
        fim=inicio + timedelta(hours=2),
        status="aprovado",
        **extra,
    )


@pytest.fixture
def gerencia_fluir():
    return Gerencia.objects.create(nome="GERENCIA 3 PSS", nome_setor="Fluir", setor_canonico="Fluir", ativo=True)


@pytest.fixture
def gerencia_vidas():
    return Gerencia.objects.create(nome="GERENCIA 2 PSS", nome_setor="Vidas", setor_canonico="Vidas", ativo=True)


@pytest.fixture
def apoio_fluir(gerencia_fluir):
    """Apoio de Coordenação: papel APOIO vigente na gerência do Fluir."""
    user = UsuarioFactory(username="apoio_fluir_pss", cpf="63000000001")
    user.groups.add(GroupFactory(name="Apoio de Coordenação"))
    EquipeGerencia.objects.create(usuario=user, gerencia=gerencia_fluir, papel="APOIO")
    return user


@pytest.fixture
def outro_usuario():
    """Criador terceiro (Coordenador comum), dono dos eventos do setor."""
    user = UsuarioFactory(username="coord_terceiro_pss", cpf="63000000002")
    user.groups.add(GroupFactory(name="Coordenador"))
    return user


@pytest.fixture
def projeto_fluir(gerencia_fluir):
    return ProjetoFactory(nome="Projeto Fluir PSS", setor="Fluir", gerencia=gerencia_fluir)


@pytest.fixture
def projeto_vidas(gerencia_vidas):
    return ProjetoFactory(nome="Projeto Vidas PSS", setor="Vidas", gerencia=gerencia_vidas)


@pytest.fixture
def sol_fluir_terceiro(outro_usuario, projeto_fluir):
    """Evento APROVADO do Fluir criado por terceiro (o coração da feature)."""
    return _aprovada(outro_usuario, projeto_fluir)


@pytest.fixture
def sol_fluir_propria(apoio_fluir, projeto_fluir):
    return _aprovada(apoio_fluir, projeto_fluir)


@pytest.fixture
def sol_vidas_terceiro(outro_usuario, projeto_vidas):
    return _aprovada(outro_usuario, projeto_vidas)


def _publish(client: APIClient, pk: int):
    return client.post(
        f"/api/solicitacoes/{pk}/publish/",
        {"dry_run": False, "apply_blocked": True},
        format="json",
    )


# ---------------------------------------------------------------------------
# A. Coração da feature — publish escopado por setor
# ---------------------------------------------------------------------------


class TestPublishSetorScope:
    @patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay")
    @patch("django.conf.settings.GCAL_CLIENT", "fake")
    @patch("rest_framework.throttling.AnonRateThrottle.allow_request", return_value=True)
    @patch("rest_framework.throttling.UserRateThrottle.allow_request", return_value=True)
    def test_apoio_publica_evento_do_setor_criado_por_terceiro(
        self, _t1, _t2, mock_task, apoio_fluir, sol_fluir_terceiro
    ):
        """CENTRAL: Apoio publica evento APROVADO do Fluir criado por terceiro → 202."""
        mock_task.return_value = _mock_task_result()
        client = APIClient()
        client.force_authenticate(apoio_fluir)

        resp = _publish(client, sol_fluir_terceiro.id)

        assert resp.status_code == status.HTTP_202_ACCEPTED
        mock_task.assert_called_once()

    @patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay")
    @patch("django.conf.settings.GCAL_CLIENT", "fake")
    @patch("rest_framework.throttling.AnonRateThrottle.allow_request", return_value=True)
    @patch("rest_framework.throttling.UserRateThrottle.allow_request", return_value=True)
    def test_apoio_publica_a_propria_aprovada(self, _t1, _t2, mock_task, apoio_fluir, sol_fluir_propria):
        mock_task.return_value = _mock_task_result()
        client = APIClient()
        client.force_authenticate(apoio_fluir)

        resp = _publish(client, sol_fluir_propria.id)

        assert resp.status_code == status.HTTP_202_ACCEPTED

    @patch("rest_framework.throttling.AnonRateThrottle.allow_request", return_value=True)
    @patch("rest_framework.throttling.UserRateThrottle.allow_request", return_value=True)
    def test_apoio_publica_evento_de_outro_setor_404(self, _t1, _t2, apoio_fluir, sol_vidas_terceiro):
        """Evento de OUTRO setor sai do escopo do get_object → 404 (não 403)."""
        client = APIClient()
        client.force_authenticate(apoio_fluir)

        resp = _publish(client, sol_vidas_terceiro.id)

        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# B. preview / resync / cancel — mesmo escopo
# ---------------------------------------------------------------------------


class TestPreviewResyncCancelSetorScope:
    @patch("rest_framework.throttling.AnonRateThrottle.allow_request", return_value=True)
    @patch("rest_framework.throttling.UserRateThrottle.allow_request", return_value=True)
    def test_preview_do_setor_ok(self, _t1, _t2, apoio_fluir, sol_fluir_terceiro):
        client = APIClient()
        client.force_authenticate(apoio_fluir)
        resp = client.post(f"/api/solicitacoes/{sol_fluir_terceiro.id}/preview-gcal/", format="json")
        assert resp.status_code == status.HTTP_200_OK

    @patch("rest_framework.throttling.AnonRateThrottle.allow_request", return_value=True)
    @patch("rest_framework.throttling.UserRateThrottle.allow_request", return_value=True)
    def test_preview_outro_setor_404(self, _t1, _t2, apoio_fluir, sol_vidas_terceiro):
        client = APIClient()
        client.force_authenticate(apoio_fluir)
        resp = client.post(f"/api/solicitacoes/{sol_vidas_terceiro.id}/preview-gcal/", format="json")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    @patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay")
    @patch("django.conf.settings.GCAL_CLIENT", "fake")
    @patch("rest_framework.throttling.AnonRateThrottle.allow_request", return_value=True)
    @patch("rest_framework.throttling.UserRateThrottle.allow_request", return_value=True)
    def test_resync_do_setor_ok(self, _t1, _t2, mock_task, apoio_fluir, sol_fluir_terceiro):
        mock_task.return_value = _mock_task_result("resync-task")
        client = APIClient()
        client.force_authenticate(apoio_fluir)
        resp = client.post(f"/api/solicitacoes/{sol_fluir_terceiro.id}/resync-gcal/", format="json")
        assert resp.status_code == status.HTTP_202_ACCEPTED

    @patch("rest_framework.throttling.AnonRateThrottle.allow_request", return_value=True)
    @patch("rest_framework.throttling.UserRateThrottle.allow_request", return_value=True)
    def test_resync_outro_setor_404(self, _t1, _t2, apoio_fluir, sol_vidas_terceiro):
        client = APIClient()
        client.force_authenticate(apoio_fluir)
        resp = client.post(f"/api/solicitacoes/{sol_vidas_terceiro.id}/resync-gcal/", format="json")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    @patch("apps.core.tasks.task_cancel_solicitacao_from_gcal.delay")
    @patch("django.conf.settings.GCAL_CLIENT", "fake")
    @patch("rest_framework.throttling.AnonRateThrottle.allow_request", return_value=True)
    @patch("rest_framework.throttling.UserRateThrottle.allow_request", return_value=True)
    def test_cancel_do_setor_ok(self, _t1, _t2, mock_task, apoio_fluir, outro_usuario, projeto_fluir):
        mock_task.return_value = _mock_task_result("cancel-task")
        sol = _aprovada(
            outro_usuario,
            projeto_fluir,
            gcal_status=Solicitacao.GCalStatus.PUBLISHED,
            external_event_id="asv2pss",
        )
        client = APIClient()
        client.force_authenticate(apoio_fluir)
        resp = client.post(f"/api/solicitacoes/{sol.id}/cancel-gcal/", format="json")
        assert resp.status_code == status.HTTP_202_ACCEPTED

    @patch("rest_framework.throttling.AnonRateThrottle.allow_request", return_value=True)
    @patch("rest_framework.throttling.UserRateThrottle.allow_request", return_value=True)
    def test_cancel_outro_setor_404(self, _t1, _t2, apoio_fluir, outro_usuario, projeto_vidas):
        sol = _aprovada(
            outro_usuario,
            projeto_vidas,
            gcal_status=Solicitacao.GCalStatus.PUBLISHED,
            external_event_id="asv2pssvidas",
        )
        client = APIClient()
        client.force_authenticate(apoio_fluir)
        resp = client.post(f"/api/solicitacoes/{sol.id}/cancel-gcal/", format="json")
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# C. SEGURANÇA — edição não vaza (user_can_access_solicitacao intacto)
# ---------------------------------------------------------------------------


class TestEdicaoNaoVaza:
    @patch("rest_framework.throttling.AnonRateThrottle.allow_request", return_value=True)
    @patch("rest_framework.throttling.UserRateThrottle.allow_request", return_value=True)
    def test_apoio_patch_evento_do_setor_de_terceiro_barrado(self, _t1, _t2, apoio_fluir, sol_fluir_terceiro):
        """Vê o setor (get_object acha), mas IsOwnerOrPrivileged barra a edição → 403/404."""
        client = APIClient()
        client.force_authenticate(apoio_fluir)
        resp = client.patch(f"/api/solicitacoes/{sol_fluir_terceiro.id}/", {"observacoes": "invadido"}, format="json")
        assert resp.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)
        sol_fluir_terceiro.refresh_from_db()
        assert sol_fluir_terceiro.observacoes != "invadido"

    @patch("rest_framework.throttling.AnonRateThrottle.allow_request", return_value=True)
    @patch("rest_framework.throttling.UserRateThrottle.allow_request", return_value=True)
    def test_apoio_delete_evento_do_setor_de_terceiro_barrado(self, _t1, _t2, apoio_fluir, sol_fluir_terceiro):
        client = APIClient()
        client.force_authenticate(apoio_fluir)
        resp = client.delete(f"/api/solicitacoes/{sol_fluir_terceiro.id}/")
        assert resp.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)
        assert Solicitacao.objects.filter(pk=sol_fluir_terceiro.id).exists()


# ---------------------------------------------------------------------------
# D. CONTENÇÃO — não virou global (sem use_gcal)
# ---------------------------------------------------------------------------


class TestContencaoNaoGanhouUseGcal:
    @patch("rest_framework.throttling.AnonRateThrottle.allow_request", return_value=True)
    @patch("rest_framework.throttling.UserRateThrottle.allow_request", return_value=True)
    def test_apoio_nao_acessa_gcal_list(self, _t1, _t2, apoio_fluir):
        client = APIClient()
        client.force_authenticate(apoio_fluir)
        resp = client.get("/api/gcal/list/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    @patch("rest_framework.throttling.AnonRateThrottle.allow_request", return_value=True)
    @patch("rest_framework.throttling.UserRateThrottle.allow_request", return_value=True)
    def test_apoio_nao_acessa_gcal_publish_batch(self, _t1, _t2, apoio_fluir):
        client = APIClient()
        client.force_authenticate(apoio_fluir)
        resp = client.post("/api/gcal/publish-batch/", {"ids": []}, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# E. SENTINELA — escopo/global helpers
# ---------------------------------------------------------------------------


class TestSentinela:
    def test_apoio_nao_e_global(self, apoio_fluir):
        assert user_is_solicitacao_global(apoio_fluir) is False

    def test_scope_inclui_setor_exclui_outro(
        self, apoio_fluir, sol_fluir_terceiro, sol_fluir_propria, sol_vidas_terceiro
    ):
        ids = set(scope_solicitacoes(Solicitacao.objects.all(), apoio_fluir).values_list("id", flat=True))
        assert sol_fluir_terceiro.id in ids
        assert sol_fluir_propria.id in ids
        assert sol_vidas_terceiro.id not in ids


# ---------------------------------------------------------------------------
# F. Regressão — Controle / Super / Gerente
# ---------------------------------------------------------------------------


class TestRegressao:
    @patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay")
    @patch("django.conf.settings.GCAL_CLIENT", "fake")
    @patch("rest_framework.throttling.AnonRateThrottle.allow_request", return_value=True)
    @patch("rest_framework.throttling.UserRateThrottle.allow_request", return_value=True)
    def test_controle_publica_qualquer_evento(self, _t1, _t2, mock_task, sol_vidas_terceiro):
        mock_task.return_value = _mock_task_result()
        controle = UsuarioFactory(username="controle_pss", cpf="63000000003")
        controle.groups.add(GroupFactory(name="Controle"))
        client = APIClient()
        client.force_authenticate(controle)
        resp = _publish(client, sol_vidas_terceiro.id)
        assert resp.status_code == status.HTTP_202_ACCEPTED

    @patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay")
    @patch("django.conf.settings.GCAL_CLIENT", "fake")
    @patch("rest_framework.throttling.AnonRateThrottle.allow_request", return_value=True)
    @patch("rest_framework.throttling.UserRateThrottle.allow_request", return_value=True)
    def test_super_publica_qualquer_evento(self, _t1, _t2, mock_task, sol_vidas_terceiro):
        mock_task.return_value = _mock_task_result()
        sup = UsuarioFactory(username="super_pss", cpf="63000000004")
        sup.groups.add(GroupFactory(name="Superintendência"))
        client = APIClient()
        client.force_authenticate(sup)
        resp = _publish(client, sol_vidas_terceiro.id)
        assert resp.status_code == status.HTTP_202_ACCEPTED

    def test_gerente_escopo_por_gerencia_inalterado(
        self, gerencia_fluir, gerencia_vidas, sol_fluir_terceiro, sol_vidas_terceiro
    ):
        """Gerente (papel GERENTE vigente, PR 8) segue escopado por gerencia_id, não por setor."""
        gerente = UsuarioFactory(username="gerente_pss", cpf="63000000005")
        gerente.groups.add(GroupFactory(name="Gerente"))
        EquipeGerencia.objects.create(usuario=gerente, gerencia=gerencia_fluir, papel="GERENTE")
        ids = set(scope_solicitacoes(Solicitacao.objects.all(), gerente).values_list("id", flat=True))
        assert sol_fluir_terceiro.id in ids
        assert sol_vidas_terceiro.id not in ids


# ---------------------------------------------------------------------------
# G. Vigência — vínculo expirado ou APOIO de outra gerência → não publica
# ---------------------------------------------------------------------------


class TestVigenciaExpirada:
    @pytest.fixture
    def apoio_expirada(self, gerencia_fluir):
        user = UsuarioFactory(username="apoio_expirada_pss", cpf="63000000006")
        user.groups.add(GroupFactory(name="Apoio de Coordenação"))
        hoje = timezone.localdate()
        EquipeGerencia.objects.create(
            usuario=user,
            gerencia=gerencia_fluir,
            papel="APOIO",
            valid_from=hoje - timedelta(days=30),
            valid_to=hoje - timedelta(days=1),
        )
        return user

    @pytest.fixture
    def apoio_sem_setor(self):
        """Papel APOIO VIGENTE numa gerência que não é a do projeto: tem o direito de publicar (PR 8),
        mas nenhum projeto no alcance."""
        sem_setor = Gerencia.objects.create(nome="GERENCIA SEM SETOR PSS", nome_setor="Sem setor", ativo=True)
        user = UsuarioFactory(username="apoio_sem_setor_pss", cpf="63000000016")
        user.groups.add(GroupFactory(name="Apoio de Coordenação"))
        EquipeGerencia.objects.create(usuario=user, gerencia=sem_setor, papel="APOIO")
        return user

    @patch("rest_framework.throttling.AnonRateThrottle.allow_request", return_value=True)
    @patch("rest_framework.throttling.UserRateThrottle.allow_request", return_value=True)
    def test_expirada_nao_publica_evento_do_setor_de_terceiro(self, _t1, _t2, apoio_expirada, sol_fluir_terceiro):
        """PR 8: o papel APOIO vencido não dá `publish_setor_solicitacao`; o gate recusa antes do objeto (403)."""
        client = APIClient()
        client.force_authenticate(apoio_expirada)
        resp = _publish(client, sol_fluir_terceiro.id)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    @patch("rest_framework.throttling.AnonRateThrottle.allow_request", return_value=True)
    @patch("rest_framework.throttling.UserRateThrottle.allow_request", return_value=True)
    def test_expirada_nao_publica_nem_a_propria(self, _t1, _t2, apoio_expirada, projeto_fluir):
        """#1656 F2 (fix review): publish exige o papel APOIO VIGENTE. Apoio com
        vínculo expirado NÃO publica — nem a própria. Desde o PR 8 o gate já recusa (403): o
        direito de publicar vem do papel vigente."""
        propria = _aprovada(apoio_expirada, projeto_fluir)
        client = APIClient()
        client.force_authenticate(apoio_expirada)
        resp = _publish(client, propria.id)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    @patch("rest_framework.throttling.AnonRateThrottle.allow_request", return_value=True)
    @patch("rest_framework.throttling.UserRateThrottle.allow_request", return_value=True)
    def test_sem_setor_nao_publica_evento_do_setor_de_terceiro(self, _t1, _t2, apoio_sem_setor, sol_fluir_terceiro):
        """Papel vigente em outra gerência: passa o gate, mas o escopo não alcança o evento (404)."""
        client = APIClient()
        client.force_authenticate(apoio_sem_setor)
        resp = _publish(client, sol_fluir_terceiro.id)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    @patch("rest_framework.throttling.AnonRateThrottle.allow_request", return_value=True)
    @patch("rest_framework.throttling.UserRateThrottle.allow_request", return_value=True)
    def test_sem_setor_nao_publica_nem_a_propria(self, _t1, _t2, apoio_sem_setor, projeto_fluir):
        """Guarda de objeto `can_publish_solicitacao`: sem APOIO na gerência do projeto, nem a própria
        (caso-limite do F2)."""
        propria = _aprovada(apoio_sem_setor, projeto_fluir)
        client = APIClient()
        client.force_authenticate(apoio_sem_setor)
        resp = _publish(client, propria.id)
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# H. Status — só APROVADOS do setor (fix review finding 1: não vaza pendente/reprovado)
# ---------------------------------------------------------------------------


def _pendente(owner, projeto, **extra) -> Solicitacao:
    inicio = timezone.now() + timedelta(days=3)
    return SolicitacaoFactory(
        usuario=owner,
        municipio=MunicipioFactory(),
        projeto=projeto,
        tipo_evento=TipoEventoFactory(nome="Formacao PSS pend"),
        inicio=inicio,
        fim=inicio + timedelta(hours=2),
        status="pendente",
        **extra,
    )


class TestSetorSomenteAprovados:
    def test_scope_exclui_pendente_do_setor_de_terceiro(self, apoio_fluir, outro_usuario, projeto_fluir):
        """PENDENTE do setor de terceiro NÃO entra no escopo da Apoio (só APROVADOS do
        setor) — não expõe PII de eventos ainda não aprovados."""
        pend = _pendente(outro_usuario, projeto_fluir)
        ids = set(scope_solicitacoes(Solicitacao.objects.all(), apoio_fluir).values_list("id", flat=True))
        assert pend.id not in ids

    def test_scope_inclui_a_propria_pendente(self, apoio_fluir, projeto_fluir):
        """A Apoio continua vendo as PRÓPRIAS em qualquer status (é dona)."""
        propria_pend = _pendente(apoio_fluir, projeto_fluir)
        ids = set(scope_solicitacoes(Solicitacao.objects.all(), apoio_fluir).values_list("id", flat=True))
        assert propria_pend.id in ids

    @patch("rest_framework.throttling.AnonRateThrottle.allow_request", return_value=True)
    @patch("rest_framework.throttling.UserRateThrottle.allow_request", return_value=True)
    def test_preview_pendente_do_setor_de_terceiro_404(self, _t1, _t2, apoio_fluir, outro_usuario, projeto_fluir):
        """Preview de PENDENTE do setor de terceiro → 404 (preview não tem guarda de
        status; a raiz é o escopo aprovados-only)."""
        pend = _pendente(outro_usuario, projeto_fluir)
        client = APIClient()
        client.force_authenticate(apoio_fluir)
        resp = client.post(f"/api/solicitacoes/{pend.id}/preview-gcal/", format="json")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_can_publish_barra_evento_proprio_de_outro_setor(self, apoio_fluir, projeto_vidas):
        """fix review finding 2: evento PRÓPRIO caído em OUTRA gerência não é publicável pela
        Apoio (guarda de objeto; o evento antigo pode ter sido criado antes do gate de projeto)."""
        from apps.core.services.solicitacao_scope import can_publish_solicitacao

        propria_vidas = _aprovada(apoio_fluir, projeto_vidas)
        assert can_publish_solicitacao(apoio_fluir, propria_vidas) is False


# ---------------------------------------------------------------------------
# I. A gerência do EVENTO vem de `projeto.gerencia_id` (PR 9), não de `Projeto.setor`
# ---------------------------------------------------------------------------


@pytest.fixture
def projeto_fluir_sem_gerencia():
    """Forma antiga de prod (2026-09-28): `Projeto.setor` preenchido e `gerencia` NULL."""
    return ProjetoFactory(nome="Fluir das Emocoes PSS", setor="Fluir", gerencia=None)


class TestGerenciaVemDoProjeto:
    """PR 9: o alcance da Apoio é a gerência do projeto (`projeto.gerencia_id`). Antes (#2043) valia
    `Projeto.setor` contra `Gerencia.setor_canonico`; agora o texto do setor não dá escopo e o projeto
    sem gerência não é de ninguém (fail-closed), o mesmo SSOT do escopo de projeto
    (`scope_projetos_por_gerencia`/`projeto_fora_da_gerencia`)."""

    def test_scope_exclui_aprovada_de_projeto_sem_gerencia(
        self, apoio_fluir, outro_usuario, projeto_fluir_sem_gerencia
    ):
        sol = _aprovada(outro_usuario, projeto_fluir_sem_gerencia)
        ids = set(scope_solicitacoes(Solicitacao.objects.all(), apoio_fluir).values_list("id", flat=True))
        assert sol.id not in ids

    @patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay")
    @patch("django.conf.settings.GCAL_CLIENT", "fake")
    @patch("rest_framework.throttling.AnonRateThrottle.allow_request", return_value=True)
    @patch("rest_framework.throttling.UserRateThrottle.allow_request", return_value=True)
    def test_apoio_nao_publica_a_propria_sem_gerencia_no_projeto(
        self, _t1, _t2, mock_task, apoio_fluir, projeto_fluir_sem_gerencia
    ):
        """Fail-closed: nem a própria, se o projeto não tem gerência (antes o setor do projeto bastava)."""
        mock_task.return_value = _mock_task_result()
        propria = _aprovada(apoio_fluir, projeto_fluir_sem_gerencia)
        client = APIClient()
        client.force_authenticate(apoio_fluir)

        resp = _publish(client, propria.id)

        assert resp.status_code == status.HTTP_404_NOT_FOUND
        mock_task.assert_not_called()

    @patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay")
    @patch("django.conf.settings.GCAL_CLIENT", "fake")
    @patch("rest_framework.throttling.AnonRateThrottle.allow_request", return_value=True)
    @patch("rest_framework.throttling.UserRateThrottle.allow_request", return_value=True)
    def test_apoio_nao_publica_de_terceiro_sem_gerencia_no_projeto(
        self, _t1, _t2, mock_task, apoio_fluir, outro_usuario, projeto_fluir_sem_gerencia
    ):
        mock_task.return_value = _mock_task_result()
        sol = _aprovada(outro_usuario, projeto_fluir_sem_gerencia)
        client = APIClient()
        client.force_authenticate(apoio_fluir)

        resp = _publish(client, sol.id)

        assert resp.status_code == status.HTTP_404_NOT_FOUND
        mock_task.assert_not_called()

    def test_gerencia_vence_o_setor_do_projeto(self, apoio_fluir, outro_usuario, gerencia_fluir):
        """Projeto rotulado Vidas mas pendurado na gerência do Fluir: vale `projeto.gerencia_id`."""
        from apps.core.services.solicitacao_scope import can_publish_solicitacao

        projeto = ProjetoFactory(nome="Vidas com gerencia Fluir PSS", setor="Vidas", gerencia=gerencia_fluir)
        sol = _aprovada(outro_usuario, projeto)

        ids = set(scope_solicitacoes(Solicitacao.objects.all(), apoio_fluir).values_list("id", flat=True))
        assert sol.id in ids
        assert can_publish_solicitacao(apoio_fluir, sol) is True

    def test_projeto_sem_setor_nao_publica(self, apoio_fluir):
        """Guarda (fail-closed): evento próprio num projeto sem setor e sem gerência não é publicável."""
        from apps.core.services.solicitacao_scope import can_publish_solicitacao

        projeto = ProjetoFactory(nome="Sem setor PSS", setor="", gerencia=None)
        propria = _aprovada(apoio_fluir, projeto)
        assert can_publish_solicitacao(apoio_fluir, propria) is False

    def test_setor_igual_nao_alcanca_gerencia_divergente(self, apoio_fluir, outro_usuario, gerencia_vidas):
        """Projeto rotulado Fluir mas pendurado na gerência do Vidas: fora do alcance da Apoio do Fluir.
        O texto do setor não dá escopo."""
        from apps.core.services.solicitacao_scope import can_publish_solicitacao

        projeto = ProjetoFactory(nome="Fluir com gerencia Vidas PSS", setor="Fluir", gerencia=gerencia_vidas)
        sol = _aprovada(outro_usuario, projeto)

        ids = set(scope_solicitacoes(Solicitacao.objects.all(), apoio_fluir).values_list("id", flat=True))
        assert sol.id not in ids
        assert can_publish_solicitacao(apoio_fluir, sol) is False


class TestPublishGlobalSoComUseGcal:
    """O "global" do PUBLISH é `use_gcal`, não o "global" de VISIBILIDADE.

    `user_is_solicitacao_global` inclui a DAT (`manage_admin_registries`) para VER tudo. Se
    ele também valesse para publicar, uma pessoa da DAT que fosse Apoio passaria a classe
    pela cap da Apoio e publicaria/cancelaria evento de QUALQUER setor sem ter `use_gcal`.
    """

    @patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay")
    @patch("django.conf.settings.GCAL_CLIENT", "fake")
    @patch("rest_framework.throttling.AnonRateThrottle.allow_request", return_value=True)
    @patch("rest_framework.throttling.UserRateThrottle.allow_request", return_value=True)
    def test_dat_que_tambem_e_apoio_nao_publica_evento_de_outro_setor(
        self, _t1, _t2, mock_task, gerencia_fluir, sol_vidas_terceiro
    ):
        mock_task.return_value = _mock_task_result()
        user = UsuarioFactory(username="dat_apoio_pss", cpf="63000000009")
        user.groups.add(GroupFactory(name="DAT"), GroupFactory(name="Apoio de Coordenação"))
        EquipeGerencia.objects.create(usuario=user, gerencia=gerencia_fluir, papel="APOIO")
        assert user_is_solicitacao_global(user) is True  # premissa: a DAT VÊ tudo
        client = APIClient()
        client.force_authenticate(user)

        resp = _publish(client, sol_vidas_terceiro.id)

        assert resp.status_code == status.HTTP_404_NOT_FOUND
        mock_task.assert_not_called()
