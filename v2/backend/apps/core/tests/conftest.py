"""
Fixtures centralizados para todos os testes de apps.core.

Issue #105: Fixtures para eliminar 403 RBAC failures sem alterar endpoints.
"""
import pytest
from django.conf import settings
from django.core.cache import cache


@pytest.fixture(autouse=True)
def force_service_account_mode():
    """
    Remove GCAL_AUTH_MODE from settings to force service_account default.

    Issue #105: Testes falhavam com 403 porque Docker tem GCAL_AUTH_MODE=oauth
    e usuários de teste não têm GoogleOAuthCredential. Esta fixture remove o
    atributo para que getattr(settings, "GCAL_AUTH_MODE", "service_account")
    retorne o default "service_account".

    Aplicado a TODOS os testes via autouse=True para garantir comportamento
    consistente em testes de publish, preview, e outros endpoints GCal.
    """
    original_value = getattr(settings, 'GCAL_AUTH_MODE', None)

    # Remove o atributo para forçar uso do default
    if hasattr(settings, 'GCAL_AUTH_MODE'):
        delattr(settings, 'GCAL_AUTH_MODE')

    yield

    # Restore original value
    if original_value is not None:
        settings.GCAL_AUTH_MODE = original_value


@pytest.fixture(autouse=True)
def clear_cache_before_test():
    """
    Limpa cache Redis antes de cada teste para garantir isolamento.

    Issue #105 (CI fix): Teste test_status_counts_cache_works falhava no CI
    devido a cache residual de outros testes. Esta fixture garante que cada
    teste comece com cache limpo, prevenindo test isolation issues.

    Aplicado a TODOS os testes via autouse=True.
    """
    cache.clear()
    yield
    # Opcional: limpar também após o teste
    cache.clear()
