"""
Testes da Issue #714: choices e normalização de tipo_acao em AcaoDAT.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

import importlib

import pytest

from apps.core.models import AcaoDAT, Municipio, Projeto, TipoAcaoDAT
from apps.core.serializers.workflow import AcaoDATCreateSerializer

pytestmark = pytest.mark.django_db

migration_module = importlib.import_module("apps.core.migrations.0057_normalize_acao_dat_tipo_acao_choices")
normalize_acao_dat_tipo_acao = migration_module.normalize_acao_dat_tipo_acao


def test_todos_tipos_validos_aceitos():
    """Todos os valores canônicos de TipoAcaoDAT devem passar no serializer de criação."""
    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
    projeto = Projeto.objects.create(nome="ACerta", ativo=True)

    for tipo in TipoAcaoDAT.values:
        serializer = AcaoDATCreateSerializer(
            data={
                "municipio": municipio.id,
                "projeto": projeto.id,
                "tipo_acao": tipo,
            }
        )
        assert serializer.is_valid(), serializer.errors


def test_data_migration_normaliza_existentes():
    """Data migration deve normalizar variantes históricas para o valor canônico."""
    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
    projeto = Projeto.objects.create(nome="ACerta", ativo=True)

    acao_curso = AcaoDAT.objects.create(
        municipio=municipio,
        projeto=projeto,
        tipo_acao="FORMAR-Criação de Curso",
    )
    acao_codigos = AcaoDAT.objects.create(
        municipio=municipio,
        projeto=projeto,
        tipo_acao="codigo enviado",
    )

    normalize_acao_dat_tipo_acao(None, None)

    acao_curso.refresh_from_db()
    acao_codigos.refresh_from_db()
    assert acao_curso.tipo_acao == TipoAcaoDAT.CRIACAO_CURSO
    assert acao_codigos.tipo_acao == TipoAcaoDAT.CODIGOS_ENVIADOS
