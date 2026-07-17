"""
Testes para endpoint batch /api/availability/check-many/.

Issue #251: Garantir cobertura de teste para verificação de disponibilidade em lote.

Cenários testados:
- Todos os formadores disponíveis (ok=True para todos)
- Um formador bloqueado por AvailabilityBlock (T)
- Lista vazia de usuários (400)
- ID de usuário inválido (handled gracefully)
- Usuário não-privilegiado não pode checar outros (403)
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.core.models import AvailabilityBlock, Participation, Solicitacao
from apps.core.services.availability_service import check_conflicts
from apps.core.tests.factories import (
    GroupFactory,
    MunicipioFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def grupo_controle():
    """Grupo Controle (permissão para check-many)."""
    grupo = GroupFactory(name="Controle")
    return grupo


@pytest.fixture
def grupo_superintendencia():
    """Grupo Superintendência (permissão para check-many)."""
    grupo = GroupFactory(name="Superintendência")
    return grupo


@pytest.fixture
def user_controle(grupo_controle):
    """Usuário do grupo Controle com permissão para check-many."""
    uid = uuid4().hex[:8]
    user = UsuarioFactory(
        username=f"controle_batch_{uid}",
        email=f"controle_batch_{uid}@test.com",
        password="testpass123",
        cpf=str(uuid4().int % 10**11).zfill(11),
    )
    user.groups.add(grupo_controle)
    return user


@pytest.fixture
def user_formador():
    """Usuário formador comum (sem permissão para check-many de outros)."""
    uid = uuid4().hex[:8]
    return UsuarioFactory(
        username=f"formador_batch_{uid}",
        email=f"formador_batch_{uid}@test.com",
        password="testpass123",
        cpf=str(uuid4().int % 10**11).zfill(11),
    )


@pytest.fixture
def formador_1():
    """Primeiro formador para testes batch."""
    uid = uuid4().hex[:8]
    return UsuarioFactory(
        username=f"formador1_{uid}",
        email=f"formador1_{uid}@test.com",
        password="testpass123",
        cpf=str(uuid4().int % 10**11).zfill(11),
    )


@pytest.fixture
def formador_2():
    """Segundo formador para testes batch."""
    uid = uuid4().hex[:8]
    return UsuarioFactory(
        username=f"formador2_{uid}",
        email=f"formador2_{uid}@test.com",
        password="testpass123",
        cpf=str(uuid4().int % 10**11).zfill(11),
    )


@pytest.fixture
def municipio():
    """Município para testes."""
    uid = uuid4().hex[:8]
    return MunicipioFactory(nome=f"Cidade Batch {uid}", uf="CE")


class TestAvailabilityCheckManyEndpoint:
    """Testes para endpoint batch /api/availability/check-many/."""

    def test_check_many_all_available(self, user_controle, formador_1, formador_2, municipio):
        """Todos os formadores disponíveis retorna ok=True.

        Cenário: Nenhum bloqueio ou conflito existe para os formadores.
        Resultado esperado: ok=True para cada formador e ok=True global.
        """
        client = APIClient()
        client.force_authenticate(user=user_controle)

        inicio = timezone.now() + timedelta(days=1)
        fim = inicio + timedelta(hours=4)

        response = client.post(
            "/api/availability/check-many/",
            {
                "usuarios_ids": [formador_1.id, formador_2.id],
                "inicio": inicio.isoformat(),
                "fim": fim.isoformat(),
                "municipio_id": municipio.id,
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["ok"] is True, "Global ok should be True when all available"
        assert len(data["results"]) == 2

        # Cada formador deve estar disponível
        for result in data["results"]:
            assert result["ok"] is True, f"Formador {result['usuario_id']} should be available"
            assert len(result["conflicts"]) == 0

    def test_check_many_one_blocked_by_availability_block(self, user_controle, formador_1, formador_2, municipio):
        """Um formador bloqueado por AvailabilityBlock retorna ok=False.

        Cenário: formador_1 tem AvailabilityBlock tipo T no período.
        Resultado esperado: ok=False global, formador_1 tem conflito, formador_2 OK.
        """
        client = APIClient()
        client.force_authenticate(user=user_controle)

        inicio = timezone.now() + timedelta(days=2)
        fim = inicio + timedelta(hours=4)

        # Criar bloqueio total para formador_1
        AvailabilityBlock.objects.create(
            usuario=formador_1,
            tipo="T",
            inicio=inicio - timedelta(hours=1),  # Começa antes
            fim=fim + timedelta(hours=1),  # Termina depois
            motivo="Bloqueio de teste",
        )

        response = client.post(
            "/api/availability/check-many/",
            {
                "usuarios_ids": [formador_1.id, formador_2.id],
                "inicio": inicio.isoformat(),
                "fim": fim.isoformat(),
                "municipio_id": municipio.id,
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["ok"] is False, "Global ok should be False when any has conflict"

        results_map = {r["usuario_id"]: r for r in data["results"]}

        # formador_1 deve ter conflito (bloqueado)
        assert results_map[formador_1.id]["ok"] is False
        assert len(results_map[formador_1.id]["conflicts"]) > 0
        # Verificar que é conflito tipo T (bloqueio total)
        conflict_codes = [c["code"] for c in results_map[formador_1.id]["conflicts"]]
        assert "T" in conflict_codes, "Should have T (total block) conflict"

        # formador_2 deve estar disponível
        assert results_map[formador_2.id]["ok"] is True
        assert len(results_map[formador_2.id]["conflicts"]) == 0

    def test_check_many_empty_list_returns_error(self, user_controle, municipio):
        """Lista vazia de usuários retorna erro 400.

        Validação de entrada: usuarios_ids não pode ser lista vazia.
        """
        client = APIClient()
        client.force_authenticate(user=user_controle)

        inicio = timezone.now() + timedelta(days=1)
        fim = inicio + timedelta(hours=4)

        response = client.post(
            "/api/availability/check-many/",
            {
                "usuarios_ids": [],
                "inicio": inicio.isoformat(),
                "fim": fim.isoformat(),
                "municipio_id": municipio.id,
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "usuarios_ids" in str(response.data).lower()

    def test_check_many_invalid_user_id_handled_gracefully(self, user_controle, formador_1, municipio):
        """ID de usuário inválido é tratado graciosamente.

        O endpoint retorna ok=False para usuário inexistente com código X,
        mas continua processando os demais usuários.
        """
        client = APIClient()
        client.force_authenticate(user=user_controle)

        inicio = timezone.now() + timedelta(days=1)
        fim = inicio + timedelta(hours=4)

        invalid_id = 99999999  # ID que não existe

        response = client.post(
            "/api/availability/check-many/",
            {
                "usuarios_ids": [formador_1.id, invalid_id],
                "inicio": inicio.isoformat(),
                "fim": fim.isoformat(),
                "municipio_id": municipio.id,
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["ok"] is False, "Global ok should be False due to invalid user"
        assert len(data["results"]) == 2

        results_map = {r["usuario_id"]: r for r in data["results"]}

        # formador_1 deve estar disponível
        assert results_map[formador_1.id]["ok"] is True

        # Usuário inválido deve ter conflito tipo X
        assert results_map[invalid_id]["ok"] is False
        assert len(results_map[invalid_id]["conflicts"]) > 0
        conflict_codes = [c["code"] for c in results_map[invalid_id]["conflicts"]]
        assert "X" in conflict_codes, "Should have X (user not found) conflict"

    def test_check_many_non_privileged_cannot_check_others(self, user_formador, formador_1, municipio):
        """Usuário não-privilegiado não pode checar disponibilidade de outros.

        PA-02: Apenas Controle/Superintendência podem checar múltiplos usuários.
        """
        client = APIClient()
        client.force_authenticate(user=user_formador)  # Formador comum, sem permissão

        inicio = timezone.now() + timedelta(days=1)
        fim = inicio + timedelta(hours=4)

        response = client.post(
            "/api/availability/check-many/",
            {
                "usuarios_ids": [formador_1.id],  # Tentando checar outro usuário
                "inicio": inicio.isoformat(),
                "fim": fim.isoformat(),
                "municipio_id": municipio.id,
            },
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_check_many_missing_dates_returns_error(self, user_controle, formador_1):
        """Datas faltando retorna erro 400."""
        client = APIClient()
        client.force_authenticate(user=user_controle)

        # Sem inicio
        response = client.post(
            "/api/availability/check-many/",
            {
                "usuarios_ids": [formador_1.id],
                "fim": (timezone.now() + timedelta(hours=4)).isoformat(),
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "inicio" in str(response.data).lower() or "obrigat" in str(response.data).lower()

    def test_check_many_fim_before_inicio_returns_error(self, user_controle, formador_1, municipio):
        """fim antes de inicio retorna erro 400."""
        client = APIClient()
        client.force_authenticate(user=user_controle)

        now = timezone.now()

        response = client.post(
            "/api/availability/check-many/",
            {
                "usuarios_ids": [formador_1.id],
                "inicio": (now + timedelta(hours=4)).isoformat(),  # Depois
                "fim": now.isoformat(),  # Antes
                "municipio_id": municipio.id,
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "fim" in str(response.data).lower() or "posterior" in str(response.data).lower()

    def test_check_many_le_sem_cache_ve_evento_de_participante_recem_criado(self, user_controle, formador_1, municipio):
        """#1452: check-many lê SEM cache e enxerga um evento onde o formador entra
        como participante, mesmo quando o caminho cacheado ainda diria 'livre'.

        Reproduz o gap: a invalidação de cache só cobre `Solicitacao.usuario_id` (o
        criador); não há signal em `Participation`. Então, quando o coordenador cria o
        evento e o formador entra só como participante, o cache do formador não é
        invalidado. Um preview cacheado mentiria 'livre' e o botão do wizard seria
        liberado para um evento que o backend recusa.
        """
        client = APIClient()
        client.force_authenticate(user=user_controle)

        inicio = timezone.now() + timedelta(days=3, hours=9)
        fim = inicio + timedelta(hours=2)

        # 1) Prima o cache: sem eventos, o caminho cacheado registra "livre" p/ o formador.
        primed = check_conflicts(usuario=formador_1, inicio=inicio, fim=fim, municipio=municipio)
        assert primed.ok is True

        # 2) O coordenador cria o evento; o formador entra como PARTICIPANTE (não como
        #    criador). O signal de invalidação bumpa o cache do coordenador — nunca o
        #    do formador (não existe receiver em Participation).
        coordenador = UsuarioFactory(username=f"coord_{uuid4().hex[:8]}", cpf=str(uuid4().int % 10**11).zfill(11))
        evento = SolicitacaoFactory(
            usuario=coordenador,
            municipio=municipio,
            tipo_evento=TipoEventoFactory(nome="Formação batch cache"),
            projeto=None,
            inicio=inicio,
            fim=fim,
            status=Solicitacao.Status.APROVADO,
        )
        Participation.objects.create(solicitacao=evento, usuario=formador_1, role=Participation.Role.FORMADOR)

        # 3) O caminho CACHEADO ainda mente "livre" (cache do formador não foi invalidado).
        stale = check_conflicts(usuario=formador_1, inicio=inicio, fim=fim, municipio=municipio)
        assert stale.ok is True, "pré-condição: o cache do formador está obsoleto (é o bug que motiva o uncached)"

        # 4) check-many, por ler SEM cache, enxerga o conflito na hora.
        response = client.post(
            "/api/availability/check-many/",
            {
                "usuarios_ids": [formador_1.id],
                "inicio": inicio.isoformat(),
                "fim": fim.isoformat(),
                "municipio_id": municipio.id,
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["ok"] is False, "check-many precisa ver o evento recém-criado (sem cache)"
        assert data["results"][0]["ok"] is False
        assert "X" in [c["code"] for c in data["results"][0]["conflicts"]]
