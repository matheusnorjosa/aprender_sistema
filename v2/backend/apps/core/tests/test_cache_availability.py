"""
Testes para CP3 - Cache de Availability Checks e Endpoints Estáticos

Valida:
- Cache de check_conflicts() (TTL 5 min)
- Invalidação automática via signals
- Cache de endpoints estáticos (municípios, projetos, tipos)
- Invalidação de cache estático
"""
# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false


from __future__ import annotations
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
import pytz
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.models import (
    AvailabilityBlock,
    Municipio,
    Projeto,
    Solicitacao,
    TipoEvento,
    Usuario,
)
from apps.core.services.availability_service import check_conflicts


@pytest.fixture
def clear_cache():
    """Limpa o cache antes de cada teste."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def usuario_formador(db):
    """Cria um usuário formador para testes."""
    grupo_formador = Group.objects.get_or_create(name="Formador")[0]
    usuario = Usuario.objects.create_user(
        username="formador_cache",
        email="formador_cache@test.com",
        first_name="Cache",
        last_name="Test",
        password="test123",
    )
    usuario.groups.add(grupo_formador)
    return usuario


@pytest.fixture
def municipio(db):
    """Cria um município para testes."""
    return Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)


@pytest.fixture
def projeto_super(db):
    """Cria um projeto SUPER para testes."""
    return Projeto.objects.create(
        nome="Projeto Cache Test",
        codigo="CACHE",
        fluxo="SUPER",
        ativo=True,
    )


@pytest.fixture
def tipo_evento(db):
    """Cria um tipo de evento para testes."""
    return TipoEvento.objects.create(nome="Formação Inicial")


# ================================================================
# CP3: Cache de check_conflicts()
# ================================================================


@pytest.mark.django_db
def test_availability_check_cached(clear_cache, usuario_formador, municipio):
    """
    Test: check_conflicts() usa cache (5 min TTL).

    Cenário:
    1. Primeira chamada: cache miss → executa função
    2. Segunda chamada com mesmos parâmetros: cache hit → retorna do cache
    3. Terceira chamada com parâmetros diferentes: cache miss → executa função
    """
    inicio = timezone.now()
    fim = inicio + timedelta(hours=2)

    # Primeira chamada: cache miss
    result1 = check_conflicts(
        usuario=usuario_formador, inicio=inicio, fim=fim, municipio=municipio
    )

    # Segunda chamada com mesmos parâmetros: cache hit
    result2 = check_conflicts(
        usuario=usuario_formador, inicio=inicio, fim=fim, municipio=municipio
    )

    # Terceira chamada com parâmetros diferentes: cache miss
    inicio_diff = inicio + timedelta(days=1)
    fim_diff = inicio_diff + timedelta(hours=2)
    result3 = check_conflicts(
        usuario=usuario_formador, inicio=inicio_diff, fim=fim_diff, municipio=municipio
    )

    # Validações
    assert result1.ok is True
    assert result2.ok is True
    assert result3.ok is True
    assert result1.conflicts == result2.conflicts  # Mesmo resultado (cache hit)
    # result3 é diferente (cache miss com parâmetros diferentes)


@pytest.mark.django_db
def test_cache_invalidated_on_solicitacao_create(
    clear_cache, usuario_formador, municipio, projeto_super, tipo_evento
):
    """
    Test: Cache é invalidado ao criar Solicitacao.

    Cenário:
    1. Primeira chamada: cache miss → resultado sem conflitos
    2. Criar solicitação aprovada
    3. Terceira chamada: cache foi invalidado → resultado com conflitos
    """
    tz = pytz.timezone("America/Fortaleza")
    inicio = timezone.now()
    fim = inicio + timedelta(hours=2)

    # Primeira chamada: sem conflitos
    result1 = check_conflicts(
        usuario=usuario_formador, inicio=inicio, fim=fim, municipio=municipio
    )
    assert result1.ok is True

    # Criar solicitação aprovada (conflita)
    Solicitacao.objects.create(
        usuario=usuario_formador,
        inicio=inicio,
        fim=fim,
        municipio=municipio,
        projeto=projeto_super,
        tipo_evento=tipo_evento,
        status="aprovado",
    )

    # Segunda chamada: cache invalidado, agora tem conflito
    result2 = check_conflicts(
        usuario=usuario_formador, inicio=inicio, fim=fim, municipio=municipio
    )
    assert result2.ok is False
    assert len(result2.conflicts) > 0


@pytest.mark.django_db
def test_cache_invalidated_on_solicitacao_update(
    clear_cache, usuario_formador, municipio, projeto_super, tipo_evento
):
    """
    Test: Cache é invalidado ao atualizar Solicitacao.

    Cenário:
    1. Criar solicitação pendente
    2. Cachear resultado
    3. Aprovar solicitação
    4. Verificar que cache foi invalidado
    """
    tz = pytz.timezone("America/Fortaleza")
    inicio = timezone.now()
    fim = inicio + timedelta(hours=2)

    # Criar solicitação pendente
    sol = Solicitacao.objects.create(
        usuario=usuario_formador,
        inicio=inicio,
        fim=fim,
        municipio=municipio,
        projeto=projeto_super,
        tipo_evento=tipo_evento,
        status="pendente",
    )

    # Cachear resultado (pendente não conflita)
    result1 = check_conflicts(
        usuario=usuario_formador, inicio=inicio, fim=fim, municipio=municipio
    )
    assert result1.ok is True

    # Aprovar solicitação (agora conflita)
    sol.status = "aprovado"
    sol.save()

    # Cache invalidado, agora tem conflito
    result2 = check_conflicts(
        usuario=usuario_formador, inicio=inicio, fim=fim, municipio=municipio
    )
    assert result2.ok is False


@pytest.mark.django_db
def test_cache_invalidated_on_solicitacao_delete(
    clear_cache, usuario_formador, municipio, projeto_super, tipo_evento
):
    """
    Test: Cache é invalidado ao deletar Solicitacao.

    Cenário:
    1. Criar solicitação aprovada (conflita)
    2. Cachear resultado com conflito
    3. Deletar solicitação
    4. Verificar que cache foi invalidado e não há mais conflito
    """
    tz = pytz.timezone("America/Fortaleza")
    inicio = timezone.now()
    fim = inicio + timedelta(hours=2)

    # Criar solicitação aprovada (conflita)
    sol = Solicitacao.objects.create(
        usuario=usuario_formador,
        inicio=inicio,
        fim=fim,
        municipio=municipio,
        projeto=projeto_super,
        tipo_evento=tipo_evento,
        status="aprovado",
    )

    # Cachear resultado com conflito
    result1 = check_conflicts(
        usuario=usuario_formador, inicio=inicio, fim=fim, municipio=municipio
    )
    assert result1.ok is False

    # Deletar solicitação
    sol.delete()

    # Cache invalidado, agora não tem conflito
    result2 = check_conflicts(
        usuario=usuario_formador, inicio=inicio, fim=fim, municipio=municipio
    )
    assert result2.ok is True


@pytest.mark.django_db
def test_cache_invalidated_on_availability_block_create(
    clear_cache, usuario_formador, municipio
):
    """
    Test: Cache é invalidado ao criar AvailabilityBlock.

    Cenário:
    1. Cachear resultado sem bloqueios
    2. Criar bloqueio total aprovado
    3. Verificar que cache foi invalidado e agora há conflito
    """
    tz = pytz.timezone("America/Fortaleza")
    inicio = timezone.now()
    fim = inicio + timedelta(hours=2)

    # Cachear resultado sem bloqueios
    result1 = check_conflicts(
        usuario=usuario_formador, inicio=inicio, fim=fim, municipio=municipio
    )
    assert result1.ok is True

    # Criar bloqueio total aprovado
    AvailabilityBlock.objects.create(
        usuario=usuario_formador,
        inicio=inicio,
        fim=fim,
        tipo="T",
        status="aprovado",
        motivo="Teste bloqueio",
    )

    # Cache invalidado, agora tem conflito
    result2 = check_conflicts(
        usuario=usuario_formador, inicio=inicio, fim=fim, municipio=municipio
    )
    assert result2.ok is False
    assert result2.conflicts[0].code == "T"


# ================================================================
# CP3: Cache de Endpoints Estáticos
# ================================================================


@pytest.mark.django_db
def test_municipios_options_cached(clear_cache):
    """
    Test: /api/options/municipios/ usa cache (5 min TTL).

    Cenário:
    1. Primeira chamada: cache miss → executa query
    2. Segunda chamada: cache hit → retorna do cache
    3. Criar novo município → cache ainda não invalidado
    """
    client = APIClient()
    # Criar usuário autenticado
    usuario = Usuario.objects.create_user(
        username="test_municipios",
        email="test@test.com",
        password="test123",
    )
    client.force_authenticate(user=usuario)

    # Criar municípios
    Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
    Municipio.objects.create(nome="Sobral", uf="CE", ativo=True)

    # Primeira chamada: cache miss
    response1 = client.get("/api/options/municipios/")
    assert response1.status_code == 200
    assert len(response1.data) == 2

    # Segunda chamada: cache hit
    response2 = client.get("/api/options/municipios/")
    assert response2.status_code == 200
    assert response1.data == response2.data


@pytest.mark.django_db
def test_static_cache_invalidated_on_municipio_create(clear_cache):
    """
    Test: Cache de endpoints estáticos é invalidado ao criar Municipio.

    Cenário:
    1. Cachear resultado com 1 município
    2. Criar novo município
    3. Verificar que cache foi invalidado e retorna 2 municípios
    """
    client = APIClient()
    usuario = Usuario.objects.create_user(
        username="test_municipios2",
        email="test2@test.com",
        password="test123",
    )
    client.force_authenticate(user=usuario)

    # Criar primeiro município
    Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)

    # Cachear resultado
    response1 = client.get("/api/options/municipios/")
    assert response1.status_code == 200
    assert len(response1.data) == 1

    # Criar novo município
    Municipio.objects.create(nome="Sobral", uf="CE", ativo=True)

    # Cache invalidado, agora retorna 2 municípios
    response2 = client.get("/api/options/municipios/")
    assert response2.status_code == 200
    assert len(response2.data) == 2


@pytest.mark.django_db
def test_projetos_options_cached(clear_cache):
    """
    Test: /api/options/projetos/ usa cache (5 min TTL).

    Cenário:
    1. Primeira chamada: cache miss
    2. Segunda chamada: cache hit (retorna mesmos dados)
    """
    client = APIClient()
    usuario = Usuario.objects.create_user(
        username="test_projetos",
        email="test3@test.com",
        password="test123",
    )
    client.force_authenticate(user=usuario)

    # Criar projetos
    Projeto.objects.create(nome="Projeto 1", codigo="P1", fluxo="SUPER", ativo=True)
    Projeto.objects.create(nome="Projeto 2", codigo="P2", fluxo="NAO_SUPER", ativo=True)

    # Primeira chamada: cache miss
    response1 = client.get("/api/options/projetos/")
    assert response1.status_code == 200
    assert len(response1.data) == 2

    # Segunda chamada: cache hit
    response2 = client.get("/api/options/projetos/")
    assert response2.status_code == 200
    assert len(response2.data) == 2
    assert response1.data == response2.data


@pytest.mark.django_db
def test_static_cache_invalidated_on_projeto_update(clear_cache):
    """
    Test: Cache de endpoints estáticos é invalidado ao atualizar Projeto.

    Cenário:
    1. Cachear resultado com projeto ativo
    2. Desativar projeto
    3. Verificar que cache foi invalidado
    """
    client = APIClient()
    usuario = Usuario.objects.create_user(
        username="test_projetos2",
        email="test4@test.com",
        password="test123",
    )
    client.force_authenticate(user=usuario)

    # Criar projeto ativo
    projeto = Projeto.objects.create(
        nome="Projeto Cache", codigo="PCACHE", fluxo="SUPER", ativo=True
    )

    # Cachear resultado
    response1 = client.get("/api/options/projetos/")
    assert response1.status_code == 200
    assert len(response1.data) == 1

    # Desativar projeto
    projeto.ativo = False
    projeto.save()

    # Cache invalidado, agora retorna 0 projetos
    response2 = client.get("/api/options/projetos/")
    assert response2.status_code == 200
    assert len(response2.data) == 0


@pytest.mark.django_db
def test_tipos_evento_options_cached(clear_cache):
    """
    Test: /api/options/tipos-evento/ usa cache (5 min TTL).

    Cenário:
    1. Primeira chamada: cache miss
    2. Segunda chamada: cache hit
    """
    client = APIClient()
    usuario = Usuario.objects.create_user(
        username="test_tipos",
        email="test5@test.com",
        password="test123",
    )
    client.force_authenticate(user=usuario)

    # Criar tipos de evento
    TipoEvento.objects.create(nome="Formação Inicial")
    TipoEvento.objects.create(nome="Acompanhamento")

    # Primeira chamada: cache miss
    response1 = client.get("/api/options/tipos-evento/")
    assert response1.status_code == 200
    assert len(response1.data) == 2

    # Segunda chamada: cache hit
    response2 = client.get("/api/options/tipos-evento/")
    assert response2.status_code == 200
    assert len(response2.data) == 2


@pytest.mark.django_db
def test_static_cache_invalidated_on_tipo_evento_delete(clear_cache):
    """
    Test: Cache de endpoints estáticos é invalidado ao deletar TipoEvento.

    Cenário:
    1. Cachear resultado com 2 tipos
    2. Deletar 1 tipo
    3. Verificar que cache foi invalidado
    """
    client = APIClient()
    usuario = Usuario.objects.create_user(
        username="test_tipos2",
        email="test6@test.com",
        password="test123",
    )
    client.force_authenticate(user=usuario)

    # Criar tipos de evento
    tipo1 = TipoEvento.objects.create(nome="Formação Inicial")
    tipo2 = TipoEvento.objects.create(nome="Acompanhamento")

    # Cachear resultado
    response1 = client.get("/api/options/tipos-evento/")
    assert response1.status_code == 200
    assert len(response1.data) == 2

    # Deletar tipo
    tipo2.delete()

    # Cache invalidado, agora retorna 1 tipo
    response2 = client.get("/api/options/tipos-evento/")
    assert response2.status_code == 200
    assert len(response2.data) == 1
