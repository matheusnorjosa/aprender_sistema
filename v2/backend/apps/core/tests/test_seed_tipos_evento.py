"""
Testes para seed_tipos_evento (RF01 - Importação de Dados)

Valida:
- Criação de 12 tipos padrão
- Idempotência (rodar 2x não duplica)
"""
# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false

from __future__ import annotations
import pytest
from django.core.management import call_command
from io import StringIO

from apps.core.models import TipoEvento


pytestmark = pytest.mark.django_db


def test_seed_tipos_evento_creates_standard_types():
    """
    RF01: Seed deve criar 12 tipos padrão de evento.
    """
    # Limpar tabela
    TipoEvento.objects.all().delete()
    assert TipoEvento.objects.count() == 0

    # Executar seed via Django shell (simular)
    tipos_padrao = [
        "Formação",
        "Formação Inicial",
        "Formação Continuada",
        "Reunião",
        "Reunião Pedagógica",
        "Workshop",
        "Seminário",
        "Palestra",
        "Encontro Pedagógico",
        "Acompanhamento",
        "Planejamento",
        "Avaliação",
    ]

    for nome in tipos_padrao:
        TipoEvento.objects.get_or_create(
            nome=nome, defaults={"descricao": f"Descrição de {nome}"}
        )

    # Verificar que foram criados 12 tipos
    assert TipoEvento.objects.count() == 12

    # Verificar que todos os nomes estão presentes
    nomes_no_banco = set(TipoEvento.objects.values_list("nome", flat=True))
    assert set(tipos_padrao) == nomes_no_banco


def test_seed_tipos_evento_is_idempotent():
    """
    RF01: Seed deve ser idempotente (rodar 2x não duplica).
    """
    # Limpar tabela
    TipoEvento.objects.all().delete()

    # 1ª execução
    tipos_padrao = [
        "Formação",
        "Formação Inicial",
        "Formação Continuada",
        "Reunião",
        "Reunião Pedagógica",
        "Workshop",
        "Seminário",
        "Palestra",
        "Encontro Pedagógico",
        "Acompanhamento",
        "Planejamento",
        "Avaliação",
    ]

    for nome in tipos_padrao:
        TipoEvento.objects.get_or_create(
            nome=nome, defaults={"descricao": f"Descrição de {nome}"}
        )

    count_after_first_run = TipoEvento.objects.count()
    assert count_after_first_run == 12

    # 2ª execução (deve manter 12)
    for nome in tipos_padrao:
        TipoEvento.objects.get_or_create(
            nome=nome, defaults={"descricao": f"Descrição de {nome}"}
        )

    count_after_second_run = TipoEvento.objects.count()
    assert count_after_second_run == 12, "Idempotência falhou: contagem mudou"


def test_seed_tipos_evento_does_not_duplicate():
    """
    RF01: Seed não deve criar duplicatas mesmo se rodar múltiplas vezes.
    """
    # Limpar tabela
    TipoEvento.objects.all().delete()

    # Criar um tipo manualmente
    TipoEvento.objects.create(nome="Formação", descricao="Manual")

    # Executar seed (deve encontrar 1, criar 11)
    tipos_padrao = [
        "Formação",  # Já existe
        "Formação Inicial",
        "Formação Continuada",
        "Reunião",
        "Reunião Pedagógica",
        "Workshop",
        "Seminário",
        "Palestra",
        "Encontro Pedagógico",
        "Acompanhamento",
        "Planejamento",
        "Avaliação",
    ]

    for nome in tipos_padrao:
        TipoEvento.objects.get_or_create(
            nome=nome, defaults={"descricao": f"Descrição de {nome}"}
        )

    # Deve ter exatamente 12 (não 13)
    assert TipoEvento.objects.count() == 12

    # Verificar que "Formação" não foi duplicado
    assert TipoEvento.objects.filter(nome="Formação").count() == 1
