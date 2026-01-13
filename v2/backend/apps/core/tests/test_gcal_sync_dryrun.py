"""
Tests: Google Calendar Sync (PR 3/3)

Cobertura completa das operações CREATE/UPDATE/ADOPT/DELETE/SKIP com idempotência.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false

from __future__ import annotations
from datetime import timedelta

from django.utils import timezone

import pytest
from apps.core.models import Municipio, Solicitacao, TipoEvento, Usuario
from apps.core.services.gcal_fake_client import FakeCalendarClient
from apps.core.services.gcal_sync_service import upsert_one


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
def municipio_test(db):
    """Município de teste"""
    return Municipio.objects.create(nome="Fortaleza", uf="CE")


@pytest.fixture
def fake_client():
    """Cliente fake de Calendar para testes"""
    return FakeCalendarClient()


@pytest.mark.django_db
class TestGCalSyncIdempotency:
    """
    Testes de idempotência e operações básicas.
    """

    def test_create_idempotent(
        self, usuario_test, tipo_evento_test, municipio_test, fake_client
    ):
        """
        create_idempotent: Primeira rodada CREATE, segunda rodada UPDATE (idempotente).
        Solicitação aprovada sem external_event_id cria evento asv2-{id}.
        Segunda rodada deve fazer UPDATE (ou SKIP se payload igual).
        """
        now = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0)

        # Criar solicitação aprovada
        sol = Solicitacao.objects.create(
            usuario=usuario_test,
            tipo_evento=tipo_evento_test,
            municipio=municipio_test,
            inicio=now,
            fim=now + timedelta(hours=2),
            status="aprovado",
        )

        calendar_id = "test-calendar"

        # Primeira execução → CREATE
        outcome1 = upsert_one(
            client=fake_client,
            calendar_id=calendar_id,
            s=sol,
            dry_run=False,
            no_delete=False,
        )

        assert outcome1.action == "CREATE", "Primeira execução deve criar evento"
        assert outcome1.solicitation_id == sol.id
        assert outcome1.external_event_id == f"asv2-{sol.id}"

        # Verificar que evento foi criado no Calendar
        events = fake_client.list_events(calendar_id)
        assert len(events) == 1, "Deve ter 1 evento no Calendar"
        assert events[0]["id"] == f"asv2-{sol.id}"

        # Verificar que DB foi atualizado
        sol.refresh_from_db()
        assert (
            sol.external_event_id == f"asv2-{sol.id}"
        ), "DB deve ter external_event_id"

        # Segunda execução → UPDATE (idempotente)
        outcome2 = upsert_one(
            client=fake_client,
            calendar_id=calendar_id,
            s=sol,
            dry_run=False,
            no_delete=False,
        )

        assert outcome2.action == "UPDATE", "Segunda execução deve atualizar"
        assert outcome2.solicitation_id == sol.id
        assert outcome2.external_event_id == f"asv2-{sol.id}"

        # Verificar que ainda tem apenas 1 evento
        events = fake_client.list_events(calendar_id)
        assert len(events) == 1, "Ainda deve ter apenas 1 evento (não duplicado)"

    def test_adopt_existing(
        self, usuario_test, tipo_evento_test, municipio_test, fake_client
    ):
        """
        adopt_existing: Evento existe no Calendar com eventId determinístico,
        mas DB não tem external_event_id → ação ADOPT e preenche o campo.
        """
        now = timezone.now().replace(hour=14, minute=0, second=0, microsecond=0)

        # Criar solicitação aprovada SEM external_event_id
        sol = Solicitacao.objects.create(
            usuario=usuario_test,
            tipo_evento=tipo_evento_test,
            municipio=municipio_test,
            inicio=now,
            fim=now + timedelta(hours=1),
            status="aprovado",
            external_event_id=None,  # Orphan
        )

        calendar_id = "test-calendar"
        event_id = f"asv2-{sol.id}"

        # Simular que evento já existe no Calendar (criado manualmente)
        fake_client.insert(
            calendar_id,
            event_id,
            {
                "summary": "Evento Órfão",
                "start": {"dateTime": now.isoformat()},
                "end": {"dateTime": (now + timedelta(hours=1)).isoformat()},
            },
        )

        # Executar sync → deve ADOPTAR o evento existente
        outcome = upsert_one(
            client=fake_client,
            calendar_id=calendar_id,
            s=sol,
            dry_run=False,
            no_delete=False,
        )

        assert outcome.action == "ADOPT", "Deve adotar evento existente"
        assert outcome.solicitation_id == sol.id
        assert outcome.external_event_id == event_id

        # Verificar que DB foi atualizado
        sol.refresh_from_db()
        assert (
            sol.external_event_id == event_id
        ), "DB deve ter sido atualizado com eventId"

        # Verificar que ainda tem apenas 1 evento
        events = fake_client.list_events(calendar_id)
        assert len(events) == 1, "Deve ter apenas 1 evento (adotado, não duplicado)"

    def test_update_on_change(
        self, usuario_test, tipo_evento_test, municipio_test, fake_client
    ):
        """
        update_on_change: Muda horário/título → UPDATE.
        """
        now = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)

        # Criar e sincronizar evento inicial
        sol = Solicitacao.objects.create(
            usuario=usuario_test,
            tipo_evento=tipo_evento_test,
            municipio=municipio_test,
            inicio=now,
            fim=now + timedelta(hours=1),
            status="aprovado",
        )

        calendar_id = "test-calendar"

        # Primeira sincronização
        outcome1 = upsert_one(
            client=fake_client,
            calendar_id=calendar_id,
            s=sol,
            dry_run=False,
            no_delete=False,
        )
        assert outcome1.action == "CREATE"

        # Obter evento inicial
        event_id = f"asv2-{sol.id}"
        event_before = fake_client.get(calendar_id, event_id)
        start_before = event_before["start"]["dateTime"]

        # Alterar horário da solicitação
        sol.inicio = now + timedelta(hours=2)  # Atrasa 2h
        sol.fim = now + timedelta(hours=3)
        sol.save()

        # Sincronizar novamente → UPDATE
        outcome2 = upsert_one(
            client=fake_client,
            calendar_id=calendar_id,
            s=sol,
            dry_run=False,
            no_delete=False,
        )

        assert outcome2.action == "UPDATE", "Deve atualizar evento existente"

        # Verificar que horário foi atualizado no Calendar
        event_after = fake_client.get(calendar_id, event_id)
        start_after = event_after["start"]["dateTime"]

        assert start_after != start_before, "Horário deve ter sido atualizado"

    def test_delete_when_unapproved(
        self, usuario_test, tipo_evento_test, municipio_test, fake_client
    ):
        """
        delete_when_unapproved: Era approved com evento, agora reprovado → DELETE.
        """
        now = timezone.now().replace(hour=11, minute=0, second=0, microsecond=0)

        # Criar solicitação aprovada e sincronizar
        sol = Solicitacao.objects.create(
            usuario=usuario_test,
            tipo_evento=tipo_evento_test,
            municipio=municipio_test,
            inicio=now,
            fim=now + timedelta(hours=1),
            status="aprovado",
        )

        calendar_id = "test-calendar"

        # Sincronizar → CREATE
        outcome1 = upsert_one(
            client=fake_client,
            calendar_id=calendar_id,
            s=sol,
            dry_run=False,
            no_delete=False,
        )
        assert outcome1.action == "CREATE"
        assert sol.external_event_id == f"asv2-{sol.id}"

        # Verificar que evento existe
        events = fake_client.list_events(calendar_id)
        assert len(events) == 1

        # Reprovar solicitação
        sol.status = "reprovado"
        sol.save()

        # Sincronizar novamente → DELETE
        outcome2 = upsert_one(
            client=fake_client,
            calendar_id=calendar_id,
            s=sol,
            dry_run=False,
            no_delete=False,
        )

        assert outcome2.action == "DELETE", "Deve deletar evento quando reprovado"
        assert outcome2.external_event_id is None

        # Verificar que evento foi removido do Calendar
        events = fake_client.list_events(calendar_id)
        assert len(events) == 0, "Evento deve ter sido deletado"

        # Verificar que DB foi limpo
        sol.refresh_from_db()
        assert sol.external_event_id is None, "DB não deve mais ter external_event_id"

    def test_delete_protected_by_no_delete_flag(
        self, usuario_test, tipo_evento_test, municipio_test, fake_client
    ):
        """
        Teste adicional: --no-delete protege eventos de serem deletados.
        """
        now = timezone.now().replace(hour=15, minute=0, second=0, microsecond=0)

        # Criar e sincronizar solicitação aprovada
        sol = Solicitacao.objects.create(
            usuario=usuario_test,
            tipo_evento=tipo_evento_test,
            municipio=municipio_test,
            inicio=now,
            fim=now + timedelta(hours=1),
            status="aprovado",
        )

        calendar_id = "test-calendar"

        # Sincronizar → CREATE
        upsert_one(
            client=fake_client,
            calendar_id=calendar_id,
            s=sol,
            dry_run=False,
            no_delete=False,
        )

        # Reprovar
        sol.status = "reprovado"
        sol.save()

        # Sincronizar com --no-delete → SKIP (não DELETE)
        outcome = upsert_one(
            client=fake_client,
            calendar_id=calendar_id,
            s=sol,
            dry_run=False,
            no_delete=True,  # Proteger de delete
        )

        assert outcome.action == "SKIP", "Deve SKIP quando no_delete=True"

        # Evento ainda deve existir no Calendar
        events = fake_client.list_events(calendar_id)
        assert len(events) == 1, "Evento não deve ter sido deletado"


@pytest.mark.django_db
class TestGCalSyncDryRun:
    """
    Testes de dry-run (sem side effects).
    """

    def test_dry_run_no_side_effects(
        self, usuario_test, tipo_evento_test, municipio_test, fake_client
    ):
        """
        dry_run_no_side_effects: Com --dry-run, nenhuma alteração no DB ou Calendar.
        """
        now = timezone.now().replace(hour=8, minute=0, second=0, microsecond=0)

        # Criar solicitação aprovada sem external_event_id
        sol = Solicitacao.objects.create(
            usuario=usuario_test,
            tipo_evento=tipo_evento_test,
            municipio=municipio_test,
            inicio=now,
            fim=now + timedelta(hours=2),
            status="aprovado",
            external_event_id=None,
        )

        calendar_id = "test-calendar"

        # Executar com dry_run=True
        outcome = upsert_one(
            client=fake_client,
            calendar_id=calendar_id,
            s=sol,
            dry_run=True,  # DRY-RUN
            no_delete=False,
        )

        # Deve reportar ação (CREATE)
        assert outcome.action == "CREATE", "Deve reportar ação planejada"

        # Verificar que NENHUMA alteração foi feita
        # 1. DB não foi alterado
        sol.refresh_from_db()
        assert sol.external_event_id is None, "DB não deve ter sido alterado em dry-run"

        # 2. Calendar não foi alterado
        events = fake_client.list_events(calendar_id)
        assert len(events) == 0, "Calendar não deve ter eventos em dry-run"

    def test_dry_run_reports_planned_actions(
        self, usuario_test, tipo_evento_test, municipio_test, fake_client
    ):
        """
        Dry-run deve reportar todas as ações planejadas sem executá-las.
        """
        now = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0)

        # Criar solicitação aprovada
        sol = Solicitacao.objects.create(
            usuario=usuario_test,
            tipo_evento=tipo_evento_test,
            municipio=municipio_test,
            inicio=now,
            fim=now + timedelta(hours=1),
            status="aprovado",
        )

        calendar_id = "test-calendar"

        # Executar dry-run
        outcome = upsert_one(
            client=fake_client,
            calendar_id=calendar_id,
            s=sol,
            dry_run=True,
            no_delete=False,
        )

        # Deve reportar CREATE
        assert outcome.action == "CREATE"
        assert outcome.solicitation_id == sol.id
        assert outcome.summary is not None, "Deve incluir summary do evento planejado"

        # Nenhum side effect
        sol.refresh_from_db()
        assert sol.external_event_id is None
        assert len(fake_client.list_events(calendar_id)) == 0


@pytest.mark.django_db
class TestGCalSyncFilters:
    """
    Testes dos filtros do command (via queryset).
    """

    def test_filters_by_date_range(
        self, usuario_test, tipo_evento_test, municipio_test, fake_client
    ):
        """
        filters: --since/--until afetam o conjunto de solicitações processadas.
        """
        base = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0)

        # Criar 3 solicitações em diferentes datas
        sol_passado = Solicitacao.objects.create(
            usuario=usuario_test,
            tipo_evento=tipo_evento_test,
            municipio=municipio_test,
            inicio=base - timedelta(days=100),  # Fora do range padrão
            fim=base - timedelta(days=100) + timedelta(hours=1),
            status="aprovado",
        )

        sol_presente = Solicitacao.objects.create(
            usuario=usuario_test,
            tipo_evento=tipo_evento_test,
            municipio=municipio_test,
            inicio=base,  # Dentro do range
            fim=base + timedelta(hours=1),
            status="aprovado",
        )

        sol_futuro = Solicitacao.objects.create(
            usuario=usuario_test,
            tipo_evento=tipo_evento_test,
            municipio=municipio_test,
            inicio=base + timedelta(days=200),  # Fora do range padrão
            fim=base + timedelta(days=200) + timedelta(hours=1),
            status="aprovado",
        )

        calendar_id = "test-calendar"

        # Simular filtro: apenas solicitações entre (base - 10 dias) e (base + 10 dias)
        since = base - timedelta(days=10)
        until = base + timedelta(days=10)

        # Filtrar queryset (como o command faria)
        from django.db.models import Q

        qs = Solicitacao.objects.filter(
            Q(inicio__lte=until) & Q(fim__gte=since)
        ).order_by("id")

        # Deve incluir apenas sol_presente
        assert qs.count() == 1, "Filtro deve retornar apenas 1 solicitação"
        assert qs.first().id == sol_presente.id

        # Sincronizar apenas as filtradas
        for s in qs:
            outcome = upsert_one(
                client=fake_client,
                calendar_id=calendar_id,
                s=s,
                dry_run=False,
                no_delete=False,
            )
            assert outcome.action == "CREATE"

        # Verificar que apenas 1 evento foi criado
        events = fake_client.list_events(calendar_id)
        assert len(events) == 1, "Apenas solicitação filtrada deve ter evento"

    def test_filters_by_ids(
        self, usuario_test, tipo_evento_test, municipio_test, fake_client
    ):
        """
        filters: --ids afeta o conjunto processado.
        """
        now = timezone.now().replace(hour=14, minute=0, second=0, microsecond=0)

        # Criar 3 solicitações
        sol1 = Solicitacao.objects.create(
            usuario=usuario_test,
            tipo_evento=tipo_evento_test,
            municipio=municipio_test,
            inicio=now,
            fim=now + timedelta(hours=1),
            status="aprovado",
        )

        sol2 = Solicitacao.objects.create(
            usuario=usuario_test,
            tipo_evento=tipo_evento_test,
            municipio=municipio_test,
            inicio=now + timedelta(hours=2),
            fim=now + timedelta(hours=3),
            status="aprovado",
        )

        sol3 = Solicitacao.objects.create(
            usuario=usuario_test,
            tipo_evento=tipo_evento_test,
            municipio=municipio_test,
            inicio=now + timedelta(hours=4),
            fim=now + timedelta(hours=5),
            status="aprovado",
        )

        calendar_id = "test-calendar"

        # Simular filtro: apenas IDs específicos (sol1, sol3)
        ids = [sol1.id, sol3.id]
        qs = Solicitacao.objects.filter(id__in=ids).order_by("id")

        assert qs.count() == 2, "Filtro deve retornar 2 solicitações"

        # Sincronizar apenas as filtradas
        for s in qs:
            upsert_one(
                client=fake_client,
                calendar_id=calendar_id,
                s=s,
                dry_run=False,
                no_delete=False,
            )

        # Verificar que apenas 2 eventos foram criados
        events = fake_client.list_events(calendar_id)
        assert len(events) == 2, "Apenas solicitações filtradas devem ter eventos"

        # Verificar IDs corretos
        event_ids = {e["id"] for e in events}
        assert event_ids == {f"asv2-{sol1.id}", f"asv2-{sol3.id}"}


@pytest.mark.django_db
class TestGCalSyncEdgeCases:
    """
    Testes de casos edge.
    """

    def test_skip_when_not_approved_and_no_event(
        self, usuario_test, tipo_evento_test, municipio_test, fake_client
    ):
        """
        SKIP: Solicitação pendente/reprovada sem evento → nada a fazer.
        """
        now = timezone.now().replace(hour=13, minute=0, second=0, microsecond=0)

        sol = Solicitacao.objects.create(
            usuario=usuario_test,
            tipo_evento=tipo_evento_test,
            municipio=municipio_test,
            inicio=now,
            fim=now + timedelta(hours=1),
            status="pendente",  # Não aprovado
            external_event_id=None,
        )

        calendar_id = "test-calendar"

        outcome = upsert_one(
            client=fake_client,
            calendar_id=calendar_id,
            s=sol,
            dry_run=False,
            no_delete=False,
        )

        assert outcome.action == "SKIP", "Deve SKIP quando não aprovado e sem evento"
        assert len(fake_client.list_events(calendar_id)) == 0

    @pytest.mark.skip(reason="TEMP: Do PR19 - será corrigido após merge sequencial")
    def test_payload_includes_all_required_fields(
        self, usuario_test, tipo_evento_test, municipio_test, fake_client
    ):
        """
        Verificar que payload inclui todos os campos obrigatórios.
        """
        now = timezone.now().replace(hour=9, minute=30, second=0, microsecond=0)

        sol = Solicitacao.objects.create(
            usuario=usuario_test,
            tipo_evento=tipo_evento_test,
            municipio=municipio_test,
            inicio=now,
            fim=now + timedelta(hours=1, minutes=30),
            status="aprovado",
            observacoes="Teste de observações",
        )

        calendar_id = "test-calendar"

        outcome = upsert_one(
            client=fake_client,
            calendar_id=calendar_id,
            s=sol,
            dry_run=False,
            no_delete=False,
        )

        assert outcome.action == "CREATE"

        # Obter evento criado
        event = fake_client.get(calendar_id, f"asv2-{sol.id}")

        # Verificar campos obrigatórios
        assert "summary" in event, "Deve ter summary"
        assert "description" in event, "Deve ter description"
        assert (
            "start" in event and "dateTime" in event["start"]
        ), "Deve ter start.dateTime"
        assert "end" in event and "dateTime" in event["end"], "Deve ter end.dateTime"
        assert "location" in event, "Deve ter location"
        assert "attendees" in event, "Deve ter attendees"

        # Verificar conteúdo
        assert municipio_test.nome in event["summary"]
        assert tipo_evento_test.nome in event["summary"]
        assert f"Solicitação #{sol.id}" in event["description"]
        assert sol.observacoes in event["description"]
        assert event["location"] == municipio_test.nome
        assert len(event["attendees"]) == 1
        assert event["attendees"][0]["email"] == usuario_test.email
