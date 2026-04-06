"""
Celery test fixtures using celery.contrib.pytest.

Provides configured celery app and worker fixtures for testing
task execution, retry, and error handling.

Usage:
    @pytest.mark.celery
    def test_task_executes(celery_app, celery_worker):
        result = my_task.delay()
        assert result.get(timeout=5) == expected

Refs: Issue #846
"""

import pytest


@pytest.fixture(scope="session")
def celery_config():
    """Celery configuration for tests — in-memory broker/backend."""
    return {
        "broker_url": "memory://",
        "result_backend": "cache+memory://",
        "task_always_eager": False,
        "task_eager_propagates": True,
        "accept_content": ["json"],
        "task_serializer": "json",
        "result_serializer": "json",
    }


@pytest.fixture(scope="session")
def celery_includes():
    """Tasks to register in the test celery app."""
    return [
        "apps.core.tasks",
        "apps.core.tasks_backup",
    ]
