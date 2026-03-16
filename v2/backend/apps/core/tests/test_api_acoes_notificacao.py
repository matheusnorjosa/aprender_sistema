"""
API tests for acoes/notificacoes endpoints (issue #872).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from datetime import date

from django.contrib.auth.models import Group
from rest_framework.test import APIClient

import pytest

from apps.core.models import (
    AcaoInstancia,
    AcaoTemplate,
    AcaoTemplateExecutor,
    AuditLog,
    CicloAcoes,
    Municipio,
    NotificacaoInterna,
    Projeto,
    Usuario,
)
from apps.core.services.prazo_engine_service import PrazoEngineService


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user_factory(db):
    counter = {"n": 0}

    def _create(*, prefix: str, groups: list[str]) -> Usuario:
        counter["n"] += 1
        idx = counter["n"]
        user = Usuario.objects.create_user(
            username=f"{prefix}_{idx}",
            email=f"{prefix}_{idx}@example.com",
            password="testpass123",
            cpf=f"{idx:011d}",
        )
        for group_name in groups:
            group, _ = Group.objects.get_or_create(name=group_name)
            user.groups.add(group)
        return user

    return _create


@pytest.fixture
def base_entities(db):
    projeto = Projeto.objects.create(nome="Projeto API Acoes")
    municipio = Municipio.objects.create(nome="Municipio API Acoes", uf="CE")
    return {"projeto": projeto, "municipio": municipio}


@pytest.fixture
def ciclo_com_acao(base_entities, user_factory):
    creator = user_factory(prefix="creator", groups=["DAT"])
    ciclo = CicloAcoes.objects.create(
        projeto=base_entities["projeto"],
        municipio=base_entities["municipio"],
        semestre="1S",
        ano=2026,
        created_by=creator,
    )
    template = AcaoTemplate.objects.create(
        ordem=801,
        nome="Acao API Teste",
        descricao_prazo="Teste API",
        tipo_ancora="EVENTO_EXTERNO",
        ref_evento_externo="EVENT_API",
        dias_prazo_uteis=1,
    )
    comercial, _ = Group.objects.get_or_create(name="Comercial")
    AcaoTemplateExecutor.objects.create(acao_template=template, group=comercial, ativo=True)
    action = AcaoInstancia.objects.create(
        ciclo=ciclo,
        template=template,
        ordem=801,
        estado="EM_ANDAMENTO",
        data_ancora=date(2026, 3, 12),
    )
    PrazoEngineService.recalculate_action(action, reference_date=date(2026, 3, 12), save=True)
    return {"ciclo": ciclo, "acao": action}


@pytest.mark.django_db
def test_ciclo_create_auto_instantiates_actions(api_client, user_factory, base_entities):
    template = AcaoTemplate.objects.create(
        ordem=701,
        nome="Acao Seed Ciclo",
        descricao_prazo="Seed para create ciclo",
        tipo_ancora="EVENTO_EXTERNO",
        ref_evento_externo="EVENT_CREATE",
        dias_prazo_uteis=2,
    )
    comercial, _ = Group.objects.get_or_create(name="Comercial")
    AcaoTemplateExecutor.objects.create(acao_template=template, group=comercial, ativo=True)

    gerente = user_factory(prefix="gerente", groups=["Gerente", "Comercial"])
    api_client.force_authenticate(user=gerente)

    payload = {
        "projeto_id": base_entities["projeto"].id,
        "municipio_id": base_entities["municipio"].id,
        "semestre": "2S",
        "ano": 2026,
    }
    response = api_client.post("/api/ciclos-acoes/", payload, format="json")
    assert response.status_code == 201

    ciclo_id = response.data["id"]
    assert AcaoInstancia.objects.filter(ciclo_id=ciclo_id).count() > 0
    assert AuditLog.objects.filter(action="CICLO_ACOES_CREATE", details__ciclo_id=ciclo_id).exists()


@pytest.mark.django_db
def test_ciclo_list_visibility_dat_global_and_setor_restrito(api_client, user_factory, ciclo_com_acao):
    ciclo = ciclo_com_acao["ciclo"]
    dat_user = user_factory(prefix="dat", groups=["DAT"])
    coord = user_factory(prefix="coord", groups=["Comercial", "Coordenador"])
    outsider = user_factory(prefix="outsider", groups=["Vidas", "Coordenador"])

    api_client.force_authenticate(user=dat_user)
    dat_response = api_client.get("/api/ciclos-acoes/")
    assert dat_response.status_code == 200
    dat_ids = {item["id"] for item in dat_response.data["results"]}
    assert ciclo.id in dat_ids

    api_client.force_authenticate(user=coord)
    coord_response = api_client.get("/api/ciclos-acoes/")
    assert coord_response.status_code == 200
    coord_ids = {item["id"] for item in coord_response.data["results"]}
    assert ciclo.id in coord_ids

    api_client.force_authenticate(user=outsider)
    outsider_response = api_client.get("/api/ciclos-acoes/")
    assert outsider_response.status_code == 200
    outsider_ids = {item["id"] for item in outsider_response.data["results"]}
    assert ciclo.id not in outsider_ids


@pytest.mark.django_db
def test_registrar_ancora_permission_matrix_and_audit(api_client, user_factory, ciclo_com_acao):
    action = ciclo_com_acao["acao"]
    dat_user = user_factory(prefix="dat", groups=["DAT"])
    gerente = user_factory(prefix="gerente", groups=["Comercial", "Gerente"])
    coord = user_factory(prefix="coord", groups=["Comercial", "Coordenador"])
    apoio = user_factory(prefix="apoio", groups=["Comercial", "Apoio de Coordenação"])

    payload = {"data_ancora": "2026-03-15", "observacao": "ancora via API"}

    api_client.force_authenticate(user=dat_user)
    dat_response = api_client.post(f"/api/acoes-instancia/{action.id}/registrar-ancora/", payload, format="json")
    assert dat_response.status_code == 200

    api_client.force_authenticate(user=gerente)
    gerente_response = api_client.post(
        f"/api/acoes-instancia/{action.id}/registrar-ancora/",
        payload,
        format="json",
    )
    assert gerente_response.status_code == 200

    api_client.force_authenticate(user=coord)
    coord_response = api_client.post(
        f"/api/acoes-instancia/{action.id}/registrar-ancora/",
        payload,
        format="json",
    )
    assert coord_response.status_code == 200

    api_client.force_authenticate(user=apoio)
    apoio_response = api_client.post(f"/api/acoes-instancia/{action.id}/registrar-ancora/", payload, format="json")
    assert apoio_response.status_code == 403

    assert AuditLog.objects.filter(action="ACAO_REGISTRAR_ANCORA", details__acao_instancia_id=action.id).exists()


@pytest.mark.django_db
def test_concluir_permission_matrix_and_reopen_blocked(api_client, user_factory, ciclo_com_acao):
    action = ciclo_com_acao["acao"]
    dat_user = user_factory(prefix="dat", groups=["DAT"])
    gerente = user_factory(prefix="gerente", groups=["Comercial", "Gerente"])
    coord = user_factory(prefix="coord", groups=["Comercial", "Coordenador"])
    outsider = user_factory(prefix="outsider", groups=["Vidas"])

    payload = {"data_realizacao": "2026-03-16", "observacao": "conclusao via API"}

    api_client.force_authenticate(user=dat_user)
    dat_response = api_client.post(f"/api/acoes-instancia/{action.id}/concluir/", payload, format="json")
    assert dat_response.status_code == 403

    api_client.force_authenticate(user=outsider)
    outsider_response = api_client.post(f"/api/acoes-instancia/{action.id}/concluir/", payload, format="json")
    assert outsider_response.status_code == 403

    # Coordenador pode concluir
    api_client.force_authenticate(user=coord)
    coord_response = api_client.post(f"/api/acoes-instancia/{action.id}/concluir/", payload, format="json")
    assert coord_response.status_code == 200

    # Reabertura bloqueada
    api_client.force_authenticate(user=gerente)
    reopen_response = api_client.post(f"/api/acoes-instancia/{action.id}/concluir/", payload, format="json")
    assert reopen_response.status_code == 400

    assert AuditLog.objects.filter(action="ACAO_CONCLUIR", details__acao_instancia_id=action.id).exists()


@pytest.mark.django_db
def test_notificacao_inbox_list_and_mark_read(api_client, user_factory, ciclo_com_acao):
    action = ciclo_com_acao["acao"]
    coord = user_factory(prefix="coord", groups=["Comercial", "Coordenador"])
    other = user_factory(prefix="other", groups=["Comercial", "Gerente"])

    own_notif = NotificacaoInterna.objects.create(
        destinatario=coord,
        acao_instancia=action,
        titulo="Teste inbox",
        mensagem="Mensagem de teste",
        tipo="LEMBRETE",
        nivel="RESPONSAVEL",
        prioridade="MEDIA",
        fase_disparo="D-3",
        referencia_data=date(2026, 3, 10),
    )
    NotificacaoInterna.objects.create(
        destinatario=other,
        acao_instancia=action,
        titulo="Outro usuario",
        mensagem="Nao deve aparecer",
        tipo="LEMBRETE",
        nivel="RESPONSAVEL",
        prioridade="MEDIA",
        fase_disparo="D-3",
        referencia_data=date(2026, 3, 10),
    )

    api_client.force_authenticate(user=coord)
    list_response = api_client.get("/api/notificacoes-internas/")
    assert list_response.status_code == 200
    assert len(list_response.data["results"]) == 1
    assert list_response.data["results"][0]["id"] == own_notif.id

    mark_response = api_client.post(f"/api/notificacoes-internas/{own_notif.id}/marcar-lida/", {}, format="json")
    assert mark_response.status_code == 200
    own_notif.refresh_from_db()
    assert own_notif.lida is True
