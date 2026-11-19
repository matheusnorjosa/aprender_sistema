"""
DEF-32 + ISS-1970 — o pedido de operação no Google (publicar, reenviar, reaplicar, cancelar).

Antes, a entrada marcava PENDING sem trava e sem transação, e a tarefa agia sobre o que achasse na linha:
um pedido antigo podia desfazer um mais novo, a marca de erro apagava o resultado de outra operação e a
fila fora do ar deixava a linha em PENDING sem tarefa. Agora cada pedido grava um identificador
(`Solicitacao.gcal_pedido`) com a linha travada, na mesma transação que enfileira a tarefa, e a tarefa só
age se o identificador dela ainda é o da linha.

O Google é sempre simulado; nada sai da máquina.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from django.db import connection

import pytest

from apps.core.models import Solicitacao
from apps.core.tests.factories import SolicitacaoFactory

# =============================================================================
# O campo
# =============================================================================


@pytest.mark.django_db
def test_gcal_pedido_fica_fora_dos_formularios():
    """O admin usa `fields="__all__"`: campo editável entraria no formulário, e salvar por lá regravaria o
    identificador lido antes."""
    assert Solicitacao._meta.get_field("gcal_pedido").editable is False


@pytest.mark.django_db
def test_insert_sem_a_coluna_gcal_pedido_nasce_vazio_pelo_default_do_banco():
    """Deploy: a migration roda antes da troca do container; o código antigo não conhece a coluna.

    O INSERT dele (sem `gcal_pedido`) precisa passar pelo DEFAULT do banco (`db_default`), senão falha com
    NOT NULL ao criar Solicitação durante o deploy.
    """
    base = SolicitacaoFactory()
    with connection.cursor() as cursor:
        colunas = [
            c.name
            for c in connection.introspection.get_table_description(cursor, Solicitacao._meta.db_table)
            if c.name not in {"id", "gcal_pedido"}
        ]
        lista = ", ".join(connection.ops.quote_name(c) for c in colunas)
        tabela = connection.ops.quote_name(Solicitacao._meta.db_table)
        cursor.execute(
            f"INSERT INTO {tabela} ({lista}) SELECT {lista} FROM {tabela} WHERE id = %s RETURNING id",  # noqa: S608  # nosec B608 (nomes da introspecção; valor parametrizado)
            [base.pk],
        )
        linha = cursor.fetchone()
    assert linha is not None
    assert Solicitacao.objects.get(pk=linha[0]).gcal_pedido == ""
