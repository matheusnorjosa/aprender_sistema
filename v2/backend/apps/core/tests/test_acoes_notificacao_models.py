"""
Tests: Acoes e Notificacoes Internas (models)
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from datetime import date

from django.core.exceptions import ValidationError
from django.db import IntegrityError

import pytest

from apps.core.models import (
    AcaoInstancia,
    AcaoTemplate,
    AcaoTemplateExecutor,
    CicloAcoes,
    NotificacaoInterna,
    RegistroAncora,
    RegistroConclusaoAcao,
    Usuario,
)
from apps.core.tests.factories import (
    GroupFactory,
    MunicipioFactory,
    ProjetoFactory,
    UsuarioFactory,
)


@pytest.fixture
def usuario_factory(db):
    counter = {"n": 0}

    def _create(prefix: str = "user") -> Usuario:
        counter["n"] += 1
        n = counter["n"]
        return UsuarioFactory(
            username=f"{prefix}{n}",
            email=f"{prefix}{n}@example.com",
            password="testpass123",
            cpf=f"{n:011d}",
        )

    return _create


@pytest.fixture
def projeto(db):
    return ProjetoFactory(nome="Projeto Teste Acoes")


@pytest.fixture
def municipio(db):
    return MunicipioFactory(nome="Municipio Teste Acoes", uf="CE")


@pytest.fixture
def acao_template(db):
    return AcaoTemplate.objects.create(
        ordem=101,
        nome="Entrega de Materiais",
        descricao_prazo="Até 21 dias úteis após ordem de fornecimento",
        tipo_ancora="EVENTO_EXTERNO",
        ref_evento_externo="ORDEM_FORNECIMENTO",
        dias_prazo_uteis=21,
    )


@pytest.fixture
def ciclo(projeto, municipio, usuario_factory):
    return CicloAcoes.objects.create(
        projeto=projeto,
        municipio=municipio,
        semestre="1S",
        ano=2026,
        created_by=usuario_factory("creator"),
    )


@pytest.fixture
def acao_instancia(ciclo, acao_template):
    return AcaoInstancia.objects.create(
        ciclo=ciclo,
        template=acao_template,
        ordem=101,
        estado="AGUARDANDO_ANCORA",
    )


@pytest.mark.django_db
def test_ciclo_acoes_unique_contexto(projeto, municipio, usuario_factory):
    created_by = usuario_factory("ctx")
    CicloAcoes.objects.create(
        projeto=projeto,
        municipio=municipio,
        semestre="1S",
        ano=2026,
        created_by=created_by,
    )

    with pytest.raises(IntegrityError):
        CicloAcoes.objects.create(
            projeto=projeto,
            municipio=municipio,
            semestre="1S",
            ano=2026,
            created_by=created_by,
        )


@pytest.mark.django_db
def test_acao_template_executor_unique_mapping(acao_template):
    group = GroupFactory(name="Comercial")
    AcaoTemplateExecutor.objects.create(acao_template=acao_template, group=group)

    with pytest.raises(IntegrityError):
        AcaoTemplateExecutor.objects.create(acao_template=acao_template, group=group)


@pytest.mark.django_db
def test_registrar_ancora_transita_para_em_andamento(acao_instancia, usuario_factory):
    # Anchor from today so the 21 business-day deadline is always in the
    # future — a hardcoded 2026-03 date would surface as ATRASADA once the
    # wall clock passed the deadline.
    data_ancora_recente = date.today()
    user = usuario_factory("ancora")
    registro = acao_instancia.registrar_ancora(
        data_ancora=data_ancora_recente,
        usuario=user,
        observacao="Material recebido",
    )

    acao_instancia.refresh_from_db()

    assert isinstance(registro, RegistroAncora)
    assert acao_instancia.estado == "EM_ANDAMENTO"
    assert acao_instancia.data_ancora == data_ancora_recente
    assert RegistroAncora.objects.filter(acao_instancia=acao_instancia).count() == 1


@pytest.mark.django_db
def test_concluir_acao_bloqueia_reabertura(acao_instancia, usuario_factory):
    user = usuario_factory("coord")
    acao_instancia.registrar_ancora(
        data_ancora=date(2026, 3, 16),
        usuario=user,
        observacao="Ancorada",
    )

    registro = acao_instancia.concluir(
        data_realizacao=date(2026, 3, 20),
        observacao="Ação realizada em campo",
        usuario=user,
    )

    acao_instancia.refresh_from_db()
    assert isinstance(registro, RegistroConclusaoAcao)
    assert acao_instancia.estado == "CONCLUIDA"
    assert acao_instancia.data_realizacao == date(2026, 3, 20)

    with pytest.raises(ValidationError):
        acao_instancia.concluir(
            data_realizacao=date(2026, 3, 21),
            observacao="Tentativa de reabrir",
            usuario=user,
        )


@pytest.mark.django_db
def test_acao_instancia_ordem_deve_bater_com_template(ciclo, acao_template):
    acao_instancia = AcaoInstancia(
        ciclo=ciclo,
        template=acao_template,
        ordem=99,
        estado="AGUARDANDO_ANCORA",
    )

    with pytest.raises(ValidationError):
        acao_instancia.full_clean()


@pytest.mark.django_db
def test_notificacao_interna_unique_scope(acao_instancia, usuario_factory):
    user = usuario_factory("notif")

    NotificacaoInterna.objects.create(
        destinatario=user,
        acao_instancia=acao_instancia,
        titulo="Prazo D-3",
        mensagem="A ação está perto do vencimento",
        tipo="LEMBRETE",
        nivel="RESPONSAVEL",
        prioridade="MEDIA",
        fase_disparo="D-3",
        referencia_data=date(2026, 3, 18),
    )

    with pytest.raises(IntegrityError):
        NotificacaoInterna.objects.create(
            destinatario=user,
            acao_instancia=acao_instancia,
            titulo="Prazo D-3 repetido",
            mensagem="Nao deve duplicar no mesmo escopo",
            tipo="LEMBRETE",
            nivel="RESPONSAVEL",
            prioridade="MEDIA",
            fase_disparo="D-3",
            referencia_data=date(2026, 3, 18),
        )
