"""
Tests: Config Service — Cache & Invalidation

Testes:
- test_fallback_when_no_config: Retorna default quando Config não existe
- test_ordering_effective_at_updated_at: Usa config mais recente (effective_at → updated_at)
- test_cache_invalidation_on_save: Cache invalidado automaticamente via signal

Cobertura: 100% dos fluxos principais de config_service.py
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone

import pytest

from apps.core.models import Config
from apps.core.services.config_service import bust_cfg, get_cfg


@pytest.mark.django_db
class TestConfigService:
    """
    Testes do Config Service (cache + invalidation).
    """

    def test_fallback_when_no_config(self):
        """
        fallback: Quando Config não existe, retorna default.
        """
        # Limpar cache para garantir estado limpo
        cache.clear()

        # Buscar config inexistente
        result = get_cfg("nonexistent_key", {"DEFAULT_VALUE": 999})

        # Deve retornar default
        assert result == {"DEFAULT_VALUE": 999}

    def test_ordering_effective_at_updated_at(self):
        """
        ordering: Usa config mais recente (effective_at DESC, updated_at DESC).
        """
        # Limpar cache
        cache.clear()

        now = timezone.now()

        # Criar config antiga
        Config.objects.create(
            key="test_ordering",
            value={"VALUE": 100},
            effective_at=now - timedelta(days=10),
        )

        # Criar config mais recente
        Config.objects.create(
            key="test_ordering",
            value={"VALUE": 200},
            effective_at=now - timedelta(days=5),
        )

        # Buscar config
        result = get_cfg("test_ordering", {})

        # Deve retornar config mais recente
        assert result == {"VALUE": 200}

    def test_cache_invalidation_on_save(self):
        """
        cache_invalidation: Cache invalidado automaticamente via signal post_save.
        """
        # Limpar cache
        cache.clear()

        # Criar config inicial
        config = Config.objects.create(
            key="test_invalidation",
            value={"VALUE": 300},
            effective_at=timezone.now(),
        )

        # Primeira leitura (popula cache)
        result1 = get_cfg("test_invalidation", {})
        assert result1 == {"VALUE": 300}

        # Atualizar config (deve invalidar cache automaticamente via signal)
        config.value = {"VALUE": 400}
        config.save()

        # Segunda leitura (deve buscar novo valor do DB, não cache)
        result2 = get_cfg("test_invalidation", {})
        assert result2 == {"VALUE": 400}

    def test_cache_hit_performance(self):
        """
        performance: Segunda leitura usa cache (sem query ao DB).
        """
        # Limpar cache
        cache.clear()

        # Criar config
        Config.objects.create(
            key="test_cache",
            value={"VALUE": 500},
            effective_at=timezone.now(),
        )

        # Primeira leitura (miss, busca do DB)
        result1 = get_cfg("test_cache", {})
        assert result1 == {"VALUE": 500}

        # Deletar config do DB
        Config.objects.filter(key="test_cache").delete()

        # Segunda leitura (hit, ainda retorna do cache)
        result2 = get_cfg("test_cache", {})
        assert result2 == {"VALUE": 500}, "Deve retornar do cache mesmo após delete no DB"

    def test_bust_cfg_manual(self):
        """
        bust_cfg: Invalida cache manualmente.
        """
        # Limpar cache
        cache.clear()

        # Criar config
        Config.objects.create(
            key="test_bust",
            value={"VALUE": 600},
            effective_at=timezone.now(),
        )

        # Primeira leitura (popula cache)
        result1 = get_cfg("test_bust", {})
        assert result1 == {"VALUE": 600}

        # Invalidar cache manualmente
        bust_cfg("test_bust")

        # Deletar config do DB
        Config.objects.filter(key="test_bust").delete()

        # Segunda leitura (miss, deve retornar default)
        result2 = get_cfg("test_bust", {"DEFAULT": 700})
        assert result2 == {"DEFAULT": 700}, "Após bust_cfg, deve buscar do DB (que está vazio)"

    def test_availability_config_usage(self):
        """
        real_usage: Exemplo de uso real para RD-04/RD-05.
        """
        # Limpar cache
        cache.clear()

        # Criar config para availability
        Config.objects.create(
            key="availability",
            value={
                "TRAVEL_BUFFER_MINUTES": 90,
                "AVAILABILITY_DAILY_LIMIT_HOURS": 6,
            },
            effective_at=timezone.now(),
        )

        # Buscar config (como availability_service.py faz)
        cfg = get_cfg("availability", {})
        buffer_min = cfg.get("TRAVEL_BUFFER_MINUTES", 120)
        daily_limit_h = cfg.get("AVAILABILITY_DAILY_LIMIT_HOURS", 8)

        # Verificar valores
        assert buffer_min == 90
        assert daily_limit_h == 6
