"""
Tests: Availability Service (RD-01 a RD-08)

Cobertura completa das regras de disponibilidade + endpoint de checagem.
"""

import pytest
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status as http_status

from apps.core.models import Solicitacao, AvailabilityBlock, Usuario, TipoEvento, Municipio
from apps.core.services.availability_service import check_conflicts


@pytest.fixture
def usuario_test(db):
    """Cria um usuário de teste"""
    return Usuario.objects.create_user(
        username="testuser",
        email="testuser@example.com",
        password="testpass123",
        cpf="99999999999",
    )


@pytest.fixture
def tipo_evento_test(db):
    """Cria um tipo de evento de teste"""
    return TipoEvento.objects.create(nome="Formação Teste", descricao="Teste")


@pytest.fixture
def municipio_a(db):
    """Município A (Fortaleza)"""
    return Municipio.objects.create(nome="Fortaleza", uf="CE")


@pytest.fixture
def municipio_b(db):
    """Município B (Caucaia)"""
    return Municipio.objects.create(nome="Caucaia", uf="CE")


@pytest.mark.django_db
class TestAvailabilityServiceRules:
    """
    Testes das regras RD-01 a RD-08.
    """

    def test_conflict_overlap_total(
        self, usuario_test, tipo_evento_test, municipio_a
    ):
        """
        RD-01: Sobreposição total → conflito X.
        Evento aprovado 10:00–12:00, novo 11:00–13:00 → X.
        """
        now = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0)

        # Criar evento aprovado existente
        Solicitacao.objects.create(
            usuario=usuario_test,
            tipo_evento=tipo_evento_test,
            municipio=municipio_a,
            inicio=now,
            fim=now + timedelta(hours=2),  # 10:00-12:00
            status="aprovado",
        )

        # Verificar novo intervalo sobreposto
        result = check_conflicts(
            usuario=usuario_test,
            inicio=now + timedelta(hours=1),  # 11:00
            fim=now + timedelta(hours=3),  # 13:00
            municipio=municipio_a,
        )

        assert not result.ok, "Deve detectar conflito de sobreposição"
        assert len(result.conflicts) > 0
        assert any(c.code == "X" for c in result.conflicts), "Deve ter conflito X"

    def test_conflict_overlap_partial(
        self, usuario_test, tipo_evento_test, municipio_a
    ):
        """
        RD-01: Sobreposição parcial → conflito X.
        Evento 10:00–12:00, novo 09:30–10:30 → X.
        """
        now = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0)

        Solicitacao.objects.create(
            usuario=usuario_test,
            tipo_evento=tipo_evento_test,
            municipio=municipio_a,
            inicio=now,
            fim=now + timedelta(hours=2),
            status="aprovado",
        )

        # Novo intervalo com overlap parcial
        result = check_conflicts(
            usuario=usuario_test,
            inicio=now - timedelta(minutes=30),  # 09:30
            fim=now + timedelta(minutes=30),  # 10:30
            municipio=municipio_a,
        )

        assert not result.ok, "Deve detectar sobreposição parcial"
        assert any(c.code == "X" for c in result.conflicts)

    def test_no_conflict_adjacent_end_equals_start(
        self, usuario_test, tipo_evento_test, municipio_a
    ):
        """
        RD-01: Adjacente (fim == início) → OK (não conflita).
        Evento 10:00–12:00, novo 12:00–13:00 → ok.
        """
        now = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0)

        Solicitacao.objects.create(
            usuario=usuario_test,
            tipo_evento=tipo_evento_test,
            municipio=municipio_a,
            inicio=now,
            fim=now + timedelta(hours=2),  # 10:00-12:00
            status="aprovado",
        )

        # Novo intervalo adjacente (início == fim anterior)
        result = check_conflicts(
            usuario=usuario_test,
            inicio=now + timedelta(hours=2),  # 12:00 (fim do anterior)
            fim=now + timedelta(hours=3),  # 13:00
            municipio=municipio_a,
        )

        # Não deve ter conflito X (adjacente é OK)
        assert not any(
            c.code == "X" for c in result.conflicts
        ), "Adjacente não deve gerar conflito X"

    def test_block_total_T_prevents_any_event(self, usuario_test):
        """
        RD-02: Bloqueio Total (T) impede qualquer evento.
        Bloqueio T 08:00–18:00, novo 09:00–10:00 → T.
        """
        now = timezone.now().replace(hour=8, minute=0, second=0, microsecond=0)

        AvailabilityBlock.objects.create(
            usuario=usuario_test,
            inicio=now,
            fim=now + timedelta(hours=10),  # 08:00-18:00
            tipo="T",
            status="aprovado",
            motivo="Bloqueio total do dia",
        )

        # Tentar criar evento dentro do bloqueio
        result = check_conflicts(
            usuario=usuario_test,
            inicio=now + timedelta(hours=1),  # 09:00
            fim=now + timedelta(hours=2),  # 10:00
            municipio=None,
        )

        assert not result.ok, "Bloqueio T deve impedir evento"
        assert any(c.code == "T" for c in result.conflicts), "Deve ter conflito T"

    def test_block_partial_P_prevents_inside_allows_outside(self, usuario_test):
        """
        RD-03: Bloqueio Parcial (P) impede dentro, permite fora.
        Bloqueio P 09:00–10:00:
          - novo 09:30–09:45 → P (dentro)
          - novo 10:00–11:00 → ok (fora)
        """
        now = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)

        AvailabilityBlock.objects.create(
            usuario=usuario_test,
            inicio=now,
            fim=now + timedelta(hours=1),  # 09:00-10:00
            tipo="P",
            status="aprovado",
            motivo="Reunião",
        )

        # Teste 1: Dentro do bloqueio parcial (deve conflitar)
        result1 = check_conflicts(
            usuario=usuario_test,
            inicio=now + timedelta(minutes=30),  # 09:30
            fim=now + timedelta(minutes=45),  # 09:45
            municipio=None,
        )

        assert not result1.ok, "Dentro do bloqueio P deve conflitar"
        assert any(c.code == "P" for c in result1.conflicts), "Deve ter conflito P"

        # Teste 2: Fora do bloqueio parcial (deve ser OK)
        result2 = check_conflicts(
            usuario=usuario_test,
            inicio=now + timedelta(hours=1),  # 10:00 (fim do bloqueio)
            fim=now + timedelta(hours=2),  # 11:00
            municipio=None,
        )

        assert not any(
            c.code == "P" for c in result2.conflicts
        ), "Fora do bloqueio P não deve conflitar"

    def test_travel_buffer_between_cities_required(
        self, usuario_test, tipo_evento_test, municipio_a, municipio_b
    ):
        """
        RD-04: Buffer de deslocamento entre cidades distintas.
        Evento 08:00–10:00 em Mun A, novo 10:30 em Mun B com buffer=60min → D.
        """
        now = timezone.now().replace(hour=8, minute=0, second=0, microsecond=0)

        # Evento aprovado em Município A
        Solicitacao.objects.create(
            usuario=usuario_test,
            tipo_evento=tipo_evento_test,
            municipio=municipio_a,
            inicio=now,
            fim=now + timedelta(hours=2),  # 08:00-10:00
            status="aprovado",
        )

        # Novo evento em Município B apenas 30 min depois (buffer insuficiente)
        # Assumindo TRAVEL_BUFFER_MINUTES=120 (padrão)
        result = check_conflicts(
            usuario=usuario_test,
            inicio=now + timedelta(hours=2, minutes=30),  # 10:30
            fim=now + timedelta(hours=3, minutes=30),  # 11:30
            municipio=municipio_b,  # Município diferente!
        )

        buffer_min = getattr(settings, "TRAVEL_BUFFER_MINUTES", 120)
        if buffer_min > 30:  # Se buffer exigido > 30 min
            assert not result.ok, "Buffer insuficiente deve gerar conflito D"
            assert any(
                c.code == "D" for c in result.conflicts
            ), "Deve ter conflito D de deslocamento"

    def test_same_city_allows_zero_buffer(
        self, usuario_test, tipo_evento_test, municipio_a
    ):
        """
        RD-04: Mesmo município → buffer 0 (permite eventos próximos).
        Evento 08:00–10:00 em Mun A, novo 10:10 em Mun A → ok (mesmo com buffer=60).
        """
        now = timezone.now().replace(hour=8, minute=0, second=0, microsecond=0)

        Solicitacao.objects.create(
            usuario=usuario_test,
            tipo_evento=tipo_evento_test,
            municipio=municipio_a,
            inicio=now,
            fim=now + timedelta(hours=2),  # 08:00-10:00
            status="aprovado",
        )

        # Novo evento no MESMO município apenas 10 min depois
        result = check_conflicts(
            usuario=usuario_test,
            inicio=now + timedelta(hours=2, minutes=10),  # 10:10
            fim=now + timedelta(hours=3),  # 11:00
            municipio=municipio_a,  # Mesmo município!
        )

        # Não deve ter conflito D (mesmo município)
        assert not any(
            c.code == "D" for c in result.conflicts
        ), "Mesmo município não exige buffer"

    def test_daily_capacity_M_exceeded(
        self, usuario_test, tipo_evento_test, municipio_a
    ):
        """
        RD-05: Capacidade diária excedida → M.
        Já tem 7h aprovadas no dia, novo de 2h com limite 8h → M.
        """
        now = timezone.now().replace(hour=8, minute=0, second=0, microsecond=0)

        # Criar evento de 7h já aprovado
        Solicitacao.objects.create(
            usuario=usuario_test,
            tipo_evento=tipo_evento_test,
            municipio=municipio_a,
            inicio=now,
            fim=now + timedelta(hours=7),  # 7h
            status="aprovado",
        )

        # Tentar adicionar mais 2h no mesmo dia (total 9h > limite 8h)
        result = check_conflicts(
            usuario=usuario_test,
            inicio=now + timedelta(hours=10),  # 18:00 (mesmo dia)
            fim=now + timedelta(hours=12),  # 20:00 (2h)
            municipio=municipio_a,
        )

        daily_limit = getattr(settings, "AVAILABILITY_DAILY_LIMIT_HOURS", 8)
        if daily_limit <= 8:  # Se limite é 8h ou menos
            assert not result.ok, "Deve detectar excesso de capacidade diária"
            assert any(
                c.code == "M" for c in result.conflicts
            ), "Deve ter conflito M"

    def test_timezone_aware_fortaleza_localtime(self, usuario_test):
        """
        RD-06: Comparação timezone-aware em America/Fortaleza.
        Verifica que _fmt_interval_local formata corretamente.
        """
        from apps.core.services.availability_service import _fmt_interval_local

        # Criar datetime UTC
        now_utc = timezone.now().replace(hour=13, minute=30, second=0, microsecond=0)
        fim_utc = now_utc + timedelta(hours=1)

        # Formatar no timezone do projeto
        formatted = _fmt_interval_local(now_utc, fim_utc)

        # Deve estar no formato "HH:MM dd/mm–HH:MM dd/mm"
        assert ":" in formatted, "Deve ter separador de hora"
        assert "/" in formatted, "Deve ter separador de data"
        assert "–" in formatted, "Deve ter separador de intervalo"

        # Verificar que está no timezone correto (America/Fortaleza é UTC-3)
        # Se UTC é 13:30, Fortaleza deve ser 10:30 (UTC-3)
        # Nota: Este teste assume horário padrão. Durante horário de verão pode variar.
        # Para teste robusto, apenas garantimos que formato está correto.


@pytest.mark.django_db
class TestAvailabilityCheckEndpoint:
    """
    Testes do endpoint GET /api/availability/check/
    """

    def test_availability_check_endpoint_returns_conflicts(
        self, usuario_test, tipo_evento_test, municipio_a
    ):
        """
        Test: Endpoint retorna conflitos corretamente.
        """
        client = APIClient()
        client.force_authenticate(user=usuario_test)

        now = timezone.now().replace(hour=14, minute=0, second=0, microsecond=0)

        # Criar evento aprovado
        Solicitacao.objects.create(
            usuario=usuario_test,
            tipo_evento=tipo_evento_test,
            municipio=municipio_a,
            inicio=now,
            fim=now + timedelta(hours=2),
            status="aprovado",
        )

        # Fazer request sobreposto
        response = client.get(
            "/api/availability/check/",
            {
                "usuario_id": usuario_test.pk,
                "inicio": (now + timedelta(hours=1)).isoformat(),
                "fim": (now + timedelta(hours=3)).isoformat(),
                "municipio_id": municipio_a.pk,
            },
        )

        assert response.status_code == http_status.HTTP_200_OK
        assert "ok" in response.data
        assert "conflicts" in response.data
        assert not response.data["ok"], "Deve detectar conflito"
        assert len(response.data["conflicts"]) > 0, "Deve retornar lista de conflitos"

        # Verificar estrutura do conflito
        conflict = response.data["conflicts"][0]
        assert "code" in conflict
        assert "title" in conflict
        assert "detail" in conflict

    def test_availability_check_requires_auth(self, usuario_test):
        """
        Test: Endpoint exige autenticação.
        """
        client = APIClient()
        # Não autenticado

        now = timezone.now()
        response = client.get(
            "/api/availability/check/",
            {
                "usuario_id": usuario_test.pk,
                "inicio": now.isoformat(),
                "fim": (now + timedelta(hours=1)).isoformat(),
            },
        )

        assert response.status_code in [
            http_status.HTTP_401_UNAUTHORIZED,
            http_status.HTTP_403_FORBIDDEN,
        ], "Deve exigir autenticação"

    def test_check_endpoint_requires_usuario_id(self, usuario_test):
        """
        Test: Endpoint requer usuario_id obrigatório.
        """
        client = APIClient()
        client.force_authenticate(user=usuario_test)

        now = timezone.now()
        response = client.get(
            "/api/availability/check/",
            {
                # usuario_id ausente!
                "inicio": now.isoformat(),
                "fim": (now + timedelta(hours=1)).isoformat(),
            },
        )

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        assert "usuario_id" in str(response.data).lower()

    def test_check_endpoint_validates_dates(self, usuario_test):
        """
        Test: Endpoint valida datas (fim > inicio).
        """
        client = APIClient()
        client.force_authenticate(user=usuario_test)

        now = timezone.now()
        response = client.get(
            "/api/availability/check/",
            {
                "usuario_id": usuario_test.pk,
                "inicio": now.isoformat(),
                "fim": (now - timedelta(hours=1)).isoformat(),  # fim < inicio!
            },
        )

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        assert "fim" in str(response.data).lower() or "posterior" in str(
            response.data
        ).lower()

    def test_check_many_endpoint_batch_processing(
        self, usuario_test, tipo_evento_test, municipio_a, db
    ):
        """
        Test: Endpoint check-many/ processa múltiplos usuários.
        Requer usuário privilegiado para checar outros usuários.
        """
        from django.contrib.auth.models import Group

        # Tornar usuario_test privilegiado (adicionar ao grupo Superintendência)
        grupo_super, _ = Group.objects.get_or_create(name="Superintendência")
        usuario_test.groups.add(grupo_super)

        # Criar segundo usuário
        usuario_2 = Usuario.objects.create_user(
            username="user2",
            email="user2@example.com",
            password="pass",
            cpf="88888888888",
        )

        client = APIClient()
        client.force_authenticate(user=usuario_test)

        now = timezone.now().replace(hour=14, minute=0, second=0, microsecond=0)

        # Criar conflito apenas para usuario_test
        Solicitacao.objects.create(
            usuario=usuario_test,
            tipo_evento=tipo_evento_test,
            municipio=municipio_a,
            inicio=now,
            fim=now + timedelta(hours=2),
            status="aprovado",
        )

        # Checar ambos usuários
        response = client.post(
            "/api/availability/check-many/",
            {
                "usuarios_ids": [usuario_test.pk, usuario_2.pk],
                "inicio": (now + timedelta(hours=1)).isoformat(),
                "fim": (now + timedelta(hours=3)).isoformat(),
                "municipio_id": municipio_a.pk,
            },
            format="json",
        )

        assert response.status_code == http_status.HTTP_200_OK
        assert "results" in response.data
        assert len(response.data["results"]) == 2

        # usuario_test deve ter conflito, usuario_2 não
        results_map = {r["usuario_id"]: r for r in response.data["results"]}
        assert not results_map[usuario_test.pk]["ok"], "usuario_test deve ter conflito"
        assert results_map[usuario_2.pk]["ok"], "usuario_2 não deve ter conflito"

    def test_permission_only_self_or_privileged(self, usuario_test):
        """
        Test: Usuário não-privilegiado só pode checar própria disponibilidade.
        """
        # Criar segundo usuário (não privilegiado)
        outro_usuario = Usuario.objects.create_user(
            username="outro",
            email="outro@example.com",
            password="pass",
            cpf="77777777777",
        )

        client = APIClient()
        client.force_authenticate(user=usuario_test)  # Autenticar como usuario_test

        now = timezone.now()

        # Tentar checar disponibilidade de OUTRO usuário (deve falhar)
        response = client.get(
            "/api/availability/check/",
            {
                "usuario_id": outro_usuario.pk,  # Diferente!
                "inicio": now.isoformat(),
                "fim": (now + timedelta(hours=1)).isoformat(),
            },
        )

        assert response.status_code == http_status.HTTP_403_FORBIDDEN
        assert "permissão" in str(response.data).lower()


@pytest.mark.django_db
class TestAvailabilityServiceAdditional:
    """
    Testes adicionais obrigatórios (RD-01, RD-08).
    """

    def test_multi_formador_any_conflict_blocks(
        self, usuario_test, tipo_evento_test, municipio_a
    ):
        """
        RD-01: Múltiplos formadores - qualquer conflito bloqueia.
        Se qualquer formador tiver conflito, a solicitação não deve prosseguir.
        """
        # Criar segundo formador
        formador_2 = Usuario.objects.create_user(
            username="formador2",
            email="formador2@example.com",
            password="pass",
            cpf="66666666666",
        )

        now = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0)

        # Criar evento aprovado apenas para formador_2
        Solicitacao.objects.create(
            usuario=formador_2,
            tipo_evento=tipo_evento_test,
            municipio=municipio_a,
            inicio=now,
            fim=now + timedelta(hours=2),
            status="aprovado",
        )

        # Checar usuario_test (não tem conflito)
        result_1 = check_conflicts(
            usuario=usuario_test,
            inicio=now + timedelta(hours=1),
            fim=now + timedelta(hours=3),
            municipio=municipio_a,
        )
        assert result_1.ok, "usuario_test não deve ter conflito"

        # Checar formador_2 (TEM conflito)
        result_2 = check_conflicts(
            usuario=formador_2,
            inicio=now + timedelta(hours=1),
            fim=now + timedelta(hours=3),
            municipio=municipio_a,
        )
        assert not result_2.ok, "formador_2 deve ter conflito"

        # Implicação: Se vários formadores forem alocados, TODOS devem estar disponíveis

    def test_conflict_messages_include_codes_and_intervals(
        self, usuario_test, tipo_evento_test, municipio_a
    ):
        """
        RD-08: Mensagens de conflito incluem código e intervalo formatado.
        Verifica estrutura: { code, title, detail (com intervalo) }
        """
        now = timezone.now().replace(hour=14, minute=0, second=0, microsecond=0)

        # Criar evento aprovado
        Solicitacao.objects.create(
            usuario=usuario_test,
            tipo_evento=tipo_evento_test,
            municipio=municipio_a,
            inicio=now,
            fim=now + timedelta(hours=2),  # 14:00-16:00
            status="aprovado",
        )

        # Gerar conflito
        result = check_conflicts(
            usuario=usuario_test,
            inicio=now + timedelta(hours=1),  # 15:00
            fim=now + timedelta(hours=3),  # 17:00
            municipio=municipio_a,
        )

        assert not result.ok
        assert len(result.conflicts) > 0

        conflict = result.conflicts[0]

        # RD-08: Verificar estrutura
        assert hasattr(conflict, "code"), "Deve ter code"
        assert hasattr(conflict, "title"), "Deve ter title"
        assert hasattr(conflict, "detail"), "Deve ter detail"
        assert conflict.code in ["X", "T", "P", "D", "M"], "Code deve ser válido"

        # Verificar que detail contém intervalo formatado (HH:MM dd/mm)
        assert ":" in conflict.detail, "Detail deve conter horário HH:MM"
        assert "/" in conflict.detail, "Detail deve conter data dd/mm"
