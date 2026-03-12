"""
Tests for Config API (Issue #187)

Endpoints:
- GET /api/config/ - Read config
- PUT /api/config/ - Update config

Test coverage:
1. test_config_get_endpoint - GET returns defaults correctly
2. test_config_put_endpoint - PUT saves + returns 200
3. test_config_rbac - 403 for non-DAT/Super
4. test_config_validation - 400 for invalid values
5. test_config_audit_log - AuditLog created on save
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false
from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog, Config

User = get_user_model()


@pytest.fixture
def client() -> APIClient:
    """Return DRF API client without session dependency for xdist safety."""
    return APIClient()


@pytest.fixture
def dat_user(db: Any) -> Any:
    """Create a DAT user."""
    user = User.objects.create_user(username="dat_user", email="dat@example.com", password="testpass123")
    dat_group, _ = Group.objects.get_or_create(name="DAT")
    user.groups.add(dat_group)
    return user


@pytest.fixture
def super_user(db: Any) -> Any:
    """Create a Superintendência user."""
    user = User.objects.create_user(username="super_user", email="super@example.com", password="testpass123")
    super_group, _ = Group.objects.get_or_create(name="Superintendência")
    user.groups.add(super_group)
    return user


@pytest.fixture
def coordenador_user(db: Any) -> Any:
    """Create a Coordenador user (no DAT/Super access)."""
    user = User.objects.create_user(username="coordenador", email="coord@example.com", password="testpass123")
    coord_group, _ = Group.objects.get_or_create(name="Coordenador")
    user.groups.add(coord_group)
    return user


@pytest.mark.django_db
def test_config_get_endpoint(client: APIClient, dat_user: Any) -> None:
    """
    Test 1: GET /api/config/ returns defaults correctly.

    Given: No Config entries exist
    When: DAT user calls GET /api/config/
    Then: Response is 200 with default values
    """
    # xdist safety: clear stale Config records and cache from parallel workers
    Config.objects.all().delete()
    from apps.core.services.config_service import bust_cfg

    for key in ("availability", "gcal_sync", "session", "features"):
        bust_cfg(key)

    client.force_authenticate(user=dat_user)

    url = reverse("core:config")
    response = client.get(url)

    assert response.status_code == 200
    data = response.json()

    # Check default values (from ConfigSerializer)
    assert data["TRAVEL_BUFFER_MINUTES"] == 120
    assert data["AVAILABILITY_DAILY_LIMIT_HOURS"] == 8
    assert data["ALLOW_ADJACENT_EVENTS"] is True
    assert data["BLOCK_AUTO_APPROVE"] is True
    assert data["BATCH_SIZE"] == 200
    assert data["LOCK_TTL_SECONDS"] == 300
    assert data["AUTO_RETRY_ON_ERROR"] is True
    assert data["MAX_RETRIES"] == 3
    assert data["SEND_UPDATES"] == "none"
    assert data["SESSION_COOKIE_AGE"] == 1800
    assert data["SESSION_WARNING_THRESHOLD"] == 300
    assert data["AUTOCOMPLETE_DEBOUNCE_MS"] == 300
    assert data["ENABLE_MULTI_CALENDAR"] is False
    assert data["ENABLE_BATCH_ACTIONS"] is False
    assert data["ENABLE_ADVANCED_FILTERS"] is False


@pytest.mark.django_db
def test_config_put_endpoint(client: APIClient, dat_user: Any) -> None:
    """
    Test 2: PUT /api/config/ saves + returns 200.

    Given: DAT user authenticated
    When: PUT /api/config/ with new values
    Then: Response is 200 with updated values
    And: Config entries are created in DB
    """
    client.force_authenticate(user=dat_user)

    url = reverse("core:config")
    payload = {
        "TRAVEL_BUFFER_MINUTES": 90,
        "AVAILABILITY_DAILY_LIMIT_HOURS": 10,
        "ALLOW_ADJACENT_EVENTS": False,
        "BLOCK_AUTO_APPROVE": False,
        "BATCH_SIZE": 150,
        "LOCK_TTL_SECONDS": 200,
        "AUTO_RETRY_ON_ERROR": False,
        "MAX_RETRIES": 2,
        "SEND_UPDATES": "all",
        "SESSION_COOKIE_AGE": 3600,
        "SESSION_WARNING_THRESHOLD": 600,
        "AUTOCOMPLETE_DEBOUNCE_MS": 500,
        "ENABLE_MULTI_CALENDAR": True,
        "ENABLE_BATCH_ACTIONS": True,
        "ENABLE_ADVANCED_FILTERS": True,
    }

    response = client.put(url, data=payload, format="json")

    assert response.status_code == 200
    data = response.json()

    # Check response matches payload
    assert data["TRAVEL_BUFFER_MINUTES"] == 90
    assert data["AVAILABILITY_DAILY_LIMIT_HOURS"] == 10
    assert data["ALLOW_ADJACENT_EVENTS"] is False
    assert data["BLOCK_AUTO_APPROVE"] is False
    assert data["BATCH_SIZE"] == 150
    assert data["LOCK_TTL_SECONDS"] == 200
    assert data["AUTO_RETRY_ON_ERROR"] is False
    assert data["MAX_RETRIES"] == 2
    assert data["SEND_UPDATES"] == "all"
    assert data["SESSION_COOKIE_AGE"] == 3600
    assert data["SESSION_WARNING_THRESHOLD"] == 600
    assert data["AUTOCOMPLETE_DEBOUNCE_MS"] == 500
    assert data["ENABLE_MULTI_CALENDAR"] is True
    assert data["ENABLE_BATCH_ACTIONS"] is True
    assert data["ENABLE_ADVANCED_FILTERS"] is True

    # Check DB entries
    availability_cfg = Config.objects.filter(key="availability").first()
    assert availability_cfg is not None
    assert availability_cfg.value["TRAVEL_BUFFER_MINUTES"] == 90
    assert availability_cfg.value["AVAILABILITY_DAILY_LIMIT_HOURS"] == 10

    gcal_cfg = Config.objects.filter(key="gcal_sync").first()
    assert gcal_cfg is not None
    assert gcal_cfg.value["BATCH_SIZE"] == 150
    assert gcal_cfg.value["LOCK_TTL_SECONDS"] == 200

    session_cfg = Config.objects.filter(key="session_settings").first()
    assert session_cfg is not None
    assert session_cfg.value["SESSION_COOKIE_AGE"] == 3600

    features_cfg = Config.objects.filter(key="features").first()
    assert features_cfg is not None
    assert features_cfg.value["ENABLE_MULTI_CALENDAR"] is True


@pytest.mark.django_db
def test_config_rbac(client: APIClient, coordenador_user: Any) -> None:
    """
    Test 3: 403 for non-DAT/Super users.

    Given: Coordenador user authenticated (no DAT/Super access)
    When: GET /api/config/
    Then: Response is 403 Forbidden
    """
    client.force_authenticate(user=coordenador_user)

    url = reverse("core:config")
    response = client.get(url)

    assert response.status_code == 403


@pytest.mark.django_db
def test_config_rbac_super(client: APIClient, super_user: Any) -> None:
    """
    Test 3b: Superintendência user can access config.

    Given: Superintendência user authenticated
    When: GET /api/config/
    Then: Response is 200 OK
    """
    client.force_authenticate(user=super_user)

    url = reverse("core:config")
    response = client.get(url)

    assert response.status_code == 200


@pytest.mark.django_db
def test_config_validation(client: APIClient, dat_user: Any) -> None:
    """
    Test 4: 400 for invalid values.

    Given: DAT user authenticated
    When: PUT /api/config/ with invalid values
    Then: Response is 400 Bad Request with error details
    """
    client.force_authenticate(user=dat_user)

    url = reverse("core:config")

    # Test 1: TRAVEL_BUFFER_MINUTES < 0
    payload = {
        "TRAVEL_BUFFER_MINUTES": -10,  # Invalid: min_value=0
        "AVAILABILITY_DAILY_LIMIT_HOURS": 8,
        "ALLOW_ADJACENT_EVENTS": True,
        "BLOCK_AUTO_APPROVE": True,
        "BATCH_SIZE": 200,
        "LOCK_TTL_SECONDS": 300,
        "AUTO_RETRY_ON_ERROR": True,
        "MAX_RETRIES": 3,
        "SEND_UPDATES": "none",
        "SESSION_COOKIE_AGE": 1800,
        "SESSION_WARNING_THRESHOLD": 300,
        "AUTOCOMPLETE_DEBOUNCE_MS": 300,
        "ENABLE_MULTI_CALENDAR": False,
        "ENABLE_BATCH_ACTIONS": False,
        "ENABLE_ADVANCED_FILTERS": False,
    }

    response = client.put(url, data=payload, format="json")

    assert response.status_code == 400
    errors = response.json()
    assert "TRAVEL_BUFFER_MINUTES" in errors

    # Test 2: AVAILABILITY_DAILY_LIMIT_HOURS > 12
    payload["TRAVEL_BUFFER_MINUTES"] = 120
    payload["AVAILABILITY_DAILY_LIMIT_HOURS"] = 15  # Invalid: max_value=12

    response = client.put(url, data=payload, format="json")

    assert response.status_code == 400
    errors = response.json()
    assert "AVAILABILITY_DAILY_LIMIT_HOURS" in errors

    # Test 3: BATCH_SIZE < 50
    payload["AVAILABILITY_DAILY_LIMIT_HOURS"] = 8
    payload["BATCH_SIZE"] = 10  # Invalid: min_value=50

    response = client.put(url, data=payload, format="json")

    assert response.status_code == 400
    errors = response.json()
    assert "BATCH_SIZE" in errors

    # Test 4: Invalid SEND_UPDATES choice
    payload["BATCH_SIZE"] = 200
    payload["SEND_UPDATES"] = "invalid_choice"  # Invalid: must be none/all/externalOnly

    response = client.put(url, data=payload, format="json")

    assert response.status_code == 400
    errors = response.json()
    assert "SEND_UPDATES" in errors


@pytest.mark.django_db
def test_config_audit_log(client: APIClient, dat_user: Any) -> None:
    """
    Test 5: AuditLog created on save.

    Given: DAT user authenticated
    When: PUT /api/config/ with new values
    Then: AuditLog entry is created with action="UPDATE_CONFIG"
    And: AuditLog.details contains changed_fields list
    """
    client.force_authenticate(user=dat_user)

    # Clear existing audit logs
    AuditLog.objects.all().delete()

    url = reverse("core:config")
    payload = {
        "TRAVEL_BUFFER_MINUTES": 100,
        "AVAILABILITY_DAILY_LIMIT_HOURS": 9,
        "ALLOW_ADJACENT_EVENTS": True,
        "BLOCK_AUTO_APPROVE": True,
        "BATCH_SIZE": 200,
        "LOCK_TTL_SECONDS": 300,
        "AUTO_RETRY_ON_ERROR": True,
        "MAX_RETRIES": 3,
        "SEND_UPDATES": "none",
        "SESSION_COOKIE_AGE": 1800,
        "SESSION_WARNING_THRESHOLD": 300,
        "AUTOCOMPLETE_DEBOUNCE_MS": 300,
        "ENABLE_MULTI_CALENDAR": False,
        "ENABLE_BATCH_ACTIONS": False,
        "ENABLE_ADVANCED_FILTERS": False,
    }

    response = client.put(url, data=payload, format="json")

    assert response.status_code == 200

    # Check AuditLog
    audit_log = AuditLog.objects.filter(action="UPDATE_CONFIG").first()
    assert audit_log is not None
    assert audit_log.usuario == dat_user
    assert audit_log.model_name == "Config"
    assert "changed_fields" in audit_log.details
    assert isinstance(audit_log.details["changed_fields"], list)
    assert len(audit_log.details["changed_fields"]) == 15  # All 15 config fields
    assert "TRAVEL_BUFFER_MINUTES" in audit_log.details["changed_fields"]
    assert "ip_address" in audit_log.details
    assert "user_agent" in audit_log.details
