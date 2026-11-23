"""
VIR-17, entrega A — evento com até três projetos: a 3ª vaga no banco e a regra do grupo.

Decisões do dono (23/11/2026): o evento tem até três projetos, no máximo três. A 3ª vaga (`projeto_3`) é igual
à 2ª: só existe com a 2ª, e os três são diferentes, da mesma gerência e do mesmo fluxo. A regra 10 (não mudar
gerência nem fluxo de projeto em evento conjunto) olha a 3ª vaga. O merge de projetos não deixa vaga vazia no
meio nem projeto repetido. Gravar pela API, pela tela e pela carga fica para as entregas seguintes: aqui a API
ainda não escreve `projeto_3`.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

import importlib
import json
from io import StringIO

from django.core.management import call_command
from django.db import IntegrityError, connection, models, transaction
from django.db.migrations.operations import AddConstraint, AddField, AlterField, RunPython
from django.db.models import ProtectedError
from django.test.utils import CaptureQueriesContext
from rest_framework import serializers
from rest_framework.test import APIClient

import pytest

from apps.core.models import Gerencia, Projeto, Solicitacao
from apps.core.services.projeto_merge import merge_projeto_duplicates
from apps.core.services.solicitacao_projetos import (
    MSG_FLUXO_DIFERENTE,
    MSG_GERENCIA_DIFERENTE,
    MSG_MAIS_DE_TRES,
    MSG_MESMO_PROJETO,
    MSG_SEM_GERENCIA,
    MSG_TERCEIRO_SEM_SEGUNDO,
    VAGAS,
    contar_por_projeto,
    eventos_conjuntos_do_projeto,
    grupo_de_projetos_invalido,
    ids_dos_projetos,
    projetos_distintos_por,
    projetos_do_evento,
    q_tem_projeto,
    rotulo_dos_projetos,
)
from apps.core.tests.factories import (
    GerenciaFactory,
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def gerencia() -> Gerencia:
    return GerenciaFactory()


@pytest.fixture
def trio(gerencia):
    """Três projetos NAO_SUPER da mesma gerência (grupo válido)."""
    return (
        ProjetoFactory(nome="Uni Duni Teste", gerencia=gerencia),
        ProjetoFactory(nome="Cataventos Teste", gerencia=gerencia),
        ProjetoFactory(nome="Miudezas Teste", gerencia=gerencia),
    )


@pytest.fixture
def dat() -> APIClient:
    client = APIClient()
    client.force_authenticate(user=UsuarioFactory(groups=["DAT"]))
    return client


def _trio(a: Projeto, b: Projeto | None, c: Projeto | None, **extra) -> Solicitacao:
    return SolicitacaoFactory(projeto=a, projeto_2=b, projeto_3=c, **extra)


def _vagas(s: Solicitacao) -> tuple[int | None, int | None, int | None]:
    s.refresh_from_db()
    return (s.projeto_id, s.projeto_2_id, s.projeto_3_id)


# =============================================================================
# Modelo: campo, constraint e PROTECT
# =============================================================================


def test_campo_projeto_3_e_igual_ao_2():
    campo = Solicitacao._meta.get_field("projeto_3")
    vaga_2 = Solicitacao._meta.get_field("projeto_2")

    assert campo.null and campo.blank
    assert campo.default is models.NOT_PROVIDED, "sem default no Python: o código antigo segue gravando"
    assert campo.remote_field.on_delete is vaga_2.remote_field.on_delete
    assert campo.remote_field.related_name == "solicitacoes_3"


def test_constraint_aceita_o_trio(trio):
    evento = _trio(*trio)

    assert _vagas(evento) == tuple(p.pk for p in trio)


def test_constraint_recusa_terceiro_sem_o_segundo(trio):
    a, _, c = trio
    with pytest.raises(IntegrityError), transaction.atomic():
        _trio(a, None, c)


def test_constraint_recusa_terceiro_sem_nenhum(trio):
    _, _, c = trio
    with pytest.raises(IntegrityError), transaction.atomic():
        _trio(None, None, c)


@pytest.mark.parametrize("repete", ["primeiro", "segundo"])
def test_constraint_recusa_terceiro_repetido(trio, repete):
    a, b, _ = trio
    with pytest.raises(IntegrityError), transaction.atomic():
        _trio(a, b, a if repete == "primeiro" else b)


def test_apagar_projeto_da_vaga_3_da_protected_error(trio):
    _trio(*trio)
    with pytest.raises(ProtectedError), transaction.atomic():
        trio[2].delete()


# =============================================================================
# Regra do grupo e leituras (services/solicitacao_projetos.py)
# =============================================================================


def test_vagas_inclui_a_terceira():
    assert VAGAS == ("projeto", "projeto_2", "projeto_3")


def test_grupo_valido_de_um_dois_e_tres(trio):
    a, b, c = trio
    assert grupo_de_projetos_invalido(a) is None
    assert grupo_de_projetos_invalido(a, b) is None
    assert grupo_de_projetos_invalido(a, b, c) is None


@pytest.mark.parametrize("repetido", [0, 1])
def test_grupo_recusa_terceiro_repetido(trio, repetido):
    a, b, _ = trio
    assert grupo_de_projetos_invalido(a, b, (a, b)[repetido]) == MSG_MESMO_PROJETO


def test_grupo_recusa_terceiro_de_outra_gerencia(trio):
    a, b, _ = trio
    assert grupo_de_projetos_invalido(a, b, ProjetoFactory(gerencia=GerenciaFactory())) == MSG_GERENCIA_DIFERENTE


def test_grupo_recusa_terceiro_de_outro_fluxo(trio, gerencia):
    a, b, _ = trio
    assert grupo_de_projetos_invalido(a, b, ProjetoFactory(gerencia=gerencia, fluxo="SUPER")) == MSG_FLUXO_DIFERENTE


def test_grupo_recusa_terceiro_sem_gerencia_fail_closed(trio):
    a, b, _ = trio
    assert grupo_de_projetos_invalido(a, b, ProjetoFactory(gerencia=None)) == MSG_SEM_GERENCIA


def test_grupo_recusa_mais_de_tres(trio, gerencia):
    assert grupo_de_projetos_invalido(*trio, ProjetoFactory(gerencia=gerencia)) == MSG_MAIS_DE_TRES


def test_projetos_ids_e_rotulo_do_trio_na_ordem_das_vagas(trio):
    a, b, c = trio
    evento = _trio(a, b, c)

    assert projetos_do_evento(evento) == [a, b, c]
    assert ids_dos_projetos(evento) == ids_dos_projetos(_trio(c, a, b)) == frozenset({a.pk, b.pk, c.pk})
    assert rotulo_dos_projetos(evento) == f"{a.nome} / {b.nome} / {c.nome}"


def test_q_tem_projeto_acha_pela_vaga_3_uma_vez(trio):
    evento = _trio(*trio)
    SolicitacaoFactory(projeto=ProjetoFactory())

    assert list(Solicitacao.objects.filter(q_tem_projeto(pk=trio[2].pk))) == [evento]
    assert list(Solicitacao.objects.filter(q_tem_projeto(nome__in=[p.nome for p in trio]))) == [evento]


def test_contar_por_projeto_conta_o_trio_nos_tres(trio):
    a, b, c = trio
    _trio(a, b, c)
    SolicitacaoFactory(projeto=c)

    assert contar_por_projeto(Solicitacao.objects.all()) == {
        a.nome: {"count": 1},
        b.nome: {"count": 1},
        c.nome: {"count": 2},
    }


def test_projetos_distintos_por_conta_a_vaga_3(trio):
    a, b, c = trio
    municipio = MunicipioFactory()
    _trio(a, b, c, municipio=municipio)
    qs = Solicitacao.objects.all()

    assert projetos_distintos_por(qs, "municipio_id") == {municipio.pk: 3}
    assert projetos_distintos_por(qs, "municipio_id", so_projeto=c.pk) == {municipio.pk: 1}


def test_eventos_conjuntos_conta_a_vaga_3(trio):
    a, b, c = trio
    _trio(a, b, c)
    SolicitacaoFactory(projeto=c)

    assert [eventos_conjuntos_do_projeto(p) for p in trio] == [1, 1, 1]


# =============================================================================
# Regra 10: projeto só na 3ª vaga também fica preso (API e admin)
# =============================================================================


def test_api_bloqueia_mudar_gerencia_de_projeto_na_vaga_3(dat, trio):
    a, b, c = trio
    _trio(a, b, c, status="reprovado")

    resp = dat.patch(f"/api/projetos/{c.id}/", {"gerencia": GerenciaFactory().id}, format="json")

    assert resp.status_code == 400, resp.content
    assert "1 evento" in resp.json()["errors"]["gerencia"][0]
    c.refresh_from_db()
    assert c.gerencia_id == a.gerencia_id


def test_admin_bloqueia_mudar_gerencia_de_projeto_na_vaga_3(trio):
    from apps.core.admin import ProjetoAdminForm

    _trio(*trio)
    c = trio[2]
    data = {
        "nome": c.nome,
        "codigo": c.codigo,
        "fluxo": c.fluxo,
        "ativo": True,
        "is_test": False,
        "descricao": "",
        "setor": "",
        "gerencia": GerenciaFactory().id,
    }

    form = ProjetoAdminForm(data=data, instance=c)

    assert not form.is_valid()
    assert "1 evento" in form.errors["gerencia"][0]


# =============================================================================
# Admin da Solicitacao
# =============================================================================


def test_admin_solicitacao_projeto_3_somente_leitura():
    from apps.core.admin import SolicitacaoAdmin

    assert "projeto_3" in SolicitacaoAdmin.readonly_fields


def _solicitacao_admin_form(sol: Solicitacao, projeto: Projeto | None):
    from apps.core.admin import SolicitacaoAdminForm

    return SolicitacaoAdminForm(data={"projeto": projeto.pk if projeto else ""}, instance=sol)


def test_admin_solicitacao_recusa_projeto_igual_ao_3(trio):
    form = _solicitacao_admin_form(_trio(*trio), trio[2])

    assert form.errors["projeto"] == [MSG_MESMO_PROJETO]


def test_admin_solicitacao_confere_a_gerencia_do_3_gravado(trio, gerencia):
    """O novo `projeto` combina com o 2º, mas não com o 3º (data-fix o pôs em outra gerência). Só o clean que
    lê a 3ª vaga recusa; o clean antigo, que conferia o par (projeto, projeto_2), deixava passar."""
    evento = _trio(*trio)
    Projeto.objects.filter(pk=trio[2].pk).update(gerencia=GerenciaFactory())

    form = _solicitacao_admin_form(Solicitacao.objects.get(pk=evento.pk), ProjetoFactory(gerencia=gerencia))

    assert form.errors["projeto"] == [MSG_GERENCIA_DIFERENTE]


def test_admin_solicitacao_aceita_trocar_por_projeto_compativel_no_trio(trio, gerencia):
    form = _solicitacao_admin_form(_trio(*trio), ProjetoFactory(gerencia=gerencia))

    assert "projeto" not in form.errors


# =============================================================================
# A API ainda não escreve a 3ª vaga (entrega B)
# =============================================================================


def _serializers_de_solicitacao() -> list[type[serializers.ModelSerializer]]:
    import apps.core.urls  # noqa: F401 — carrega views e serializers de todas as rotas

    achados, fila = [], list(serializers.ModelSerializer.__subclasses__())
    while fila:
        cls = fila.pop()
        fila.extend(cls.__subclasses__())
        meta = getattr(cls, "Meta", None)
        if meta is not None and getattr(meta, "model", None) is Solicitacao:
            achados.append(cls)
    return achados


def test_nenhum_serializer_de_solicitacao_escreve_projeto_3():
    encontrados = _serializers_de_solicitacao()
    assert encontrados, "a busca por serializers de Solicitacao não achou nenhum"
    for cls in encontrados:
        campo = cls().fields.get("projeto_3")
        assert campo is None or campo.read_only, f"{cls.__name__} aceita projeto_3"


# =============================================================================
# Edição pela API de evento com trio já gravado (VIR17A-R1): a regra vê o estado final, com o 3º gravado
# =============================================================================


@pytest.fixture
def admin_api() -> APIClient:
    client = APIClient()
    client.force_authenticate(user=UsuarioFactory(is_superuser=True, is_staff=True))
    return client


def _patch_trio(client: APIClient, evento: Solicitacao, dados: dict) -> tuple[int, dict]:
    resp = client.patch(f"/api/solicitacoes/{evento.pk}/", dados, format="json")
    return resp.status_code, resp.json()


@pytest.mark.parametrize(
    ("caso", "esperado"),
    [
        ("tira_o_2", MSG_TERCEIRO_SEM_SEGUNDO),
        ("1_vira_o_3", MSG_MESMO_PROJETO),
        ("2_vira_o_3", MSG_MESMO_PROJETO),
        ("inverte_1_e_3", MSG_MESMO_PROJETO),
        ("1_de_outra_gerencia", MSG_GERENCIA_DIFERENTE),
        ("par_de_outra_gerencia", MSG_GERENCIA_DIFERENTE),
        ("par_de_outro_fluxo", MSG_FLUXO_DIFERENTE),
    ],
)
def test_api_edicao_do_trio_gravado_da_400_e_nao_grava(admin_api, trio, gerencia, caso, esperado):
    a, b, c = trio
    outra = GerenciaFactory()
    fora = ProjetoFactory(gerencia=outra), ProjetoFactory(gerencia=outra)
    super_ = ProjetoFactory(gerencia=gerencia, fluxo="SUPER"), ProjetoFactory(gerencia=gerencia, fluxo="SUPER")
    dados = {
        "tira_o_2": {"projeto_2": None},
        "1_vira_o_3": {"projeto": c.pk},
        "2_vira_o_3": {"projeto_2": c.pk},
        "inverte_1_e_3": {"projeto": c.pk, "projeto_2": b.pk},
        "1_de_outra_gerencia": {"projeto": fora[0].pk},
        "par_de_outra_gerencia": {"projeto": fora[0].pk, "projeto_2": fora[1].pk},
        "par_de_outro_fluxo": {"projeto": super_[0].pk, "projeto_2": super_[1].pk},
    }[caso]
    evento = _trio(a, b, c)

    status, corpo = _patch_trio(admin_api, evento, dados)

    assert status == 400, corpo
    assert corpo["errors"]["projeto_2"] == [esperado]
    assert _vagas(evento) == (a.pk, b.pk, c.pk)


def test_api_edicao_do_trio_sem_mexer_nos_projetos_segue(admin_api, trio):
    evento = _trio(*trio)

    status, corpo = _patch_trio(admin_api, evento, {"observacoes": "Sala 2"})

    assert status == 200, corpo
    evento.refresh_from_db()
    assert evento.observacoes == "Sala 2"
    assert _vagas(evento) == tuple(p.pk for p in trio)


def test_api_edicao_do_trio_inverter_1_e_2_nao_muda_nada(admin_api, trio):
    a, b, c = trio
    evento = _trio(a, b, c)

    status, corpo = _patch_trio(admin_api, evento, {"projeto": b.pk, "projeto_2": a.pk})

    assert status == 200, corpo
    assert _vagas(evento) == (a.pk, b.pk, c.pk)


# =============================================================================
# Merge de projetos: sem vaga vazia no meio, sem projeto repetido
# =============================================================================

PAR_MERGE = [("CANONICO TRIO", "Canonico & Trio")]


@pytest.fixture
def merge(gerencia):
    survivor = ProjetoFactory(nome="CANONICO TRIO", gerencia=gerencia)
    dup = ProjetoFactory(nome="Canonico & Trio", gerencia=gerencia)
    return survivor, dup


@pytest.mark.parametrize(
    ("ordem", "esperado"),
    [
        # Duplicata e sobrevivente em cada par de vagas (as 6 ordens do trio): o sobrevivente fica na vaga mais à
        # frente entre a dele e a da duplicata, a outra sai e as de trás sobem.
        (("dup", "s", "x"), ("s", "x", None)),
        (("s", "dup", "x"), ("s", "x", None)),
        (("dup", "x", "s"), ("s", "x", None)),
        (("s", "x", "dup"), ("s", "x", None)),
        (("x", "dup", "s"), ("x", "s", None)),
        (("x", "s", "dup"), ("x", "s", None)),
        # No par, o mesmo: sobra o sobrevivente na vaga 1.
        (("dup", "s", None), ("s", None, None)),
        (("s", "dup", None), ("s", None, None)),
    ],
)
def test_merge_com_sobrevivente_no_evento_sobe_as_vagas(merge, gerencia, ordem, esperado):
    survivor, dup = merge
    x = ProjetoFactory(gerencia=gerencia)
    nomes = {"s": survivor, "dup": dup, "x": x, None: None}
    evento = _trio(*(nomes[n] for n in ordem))

    report = merge_projeto_duplicates(pairs=PAR_MERGE, apply=True)

    assert _vagas(evento) == tuple(nomes[n].pk if n else None for n in esperado)
    entry = report["pairs"][0]
    assert entry["conjunto_desfeito"] == 1
    assert "Solicitacao" not in entry["reparented"]


@pytest.mark.parametrize("dup_na_vaga", [1, 2, 3])
def test_merge_no_trio_sem_sobrevivente_so_troca_a_vaga(merge, gerencia, dup_na_vaga):
    survivor, dup = merge
    x, y = ProjetoFactory(gerencia=gerencia), ProjetoFactory(gerencia=gerencia)
    vagas = [x, y]
    vagas.insert(dup_na_vaga - 1, dup)
    evento = _trio(*vagas)

    report = merge_projeto_duplicates(pairs=PAR_MERGE, apply=True)

    assert _vagas(evento) == tuple(survivor.pk if p is dup else p.pk for p in vagas)
    entry = report["pairs"][0]
    assert entry["conjunto_desfeito"] == 0
    assert entry["reparented"]["Solicitacao"] == 1


def test_merge_recusa_quando_quebraria_o_trio(trio):
    """A duplicata no trio, o sobrevivente de outra gerência: gravaria um grupo inválido. Recusa sem mudar nada."""
    a, b, _ = trio
    ProjetoFactory(nome="CANONICO TRIO", gerencia=GerenciaFactory())  # o sobrevivente, de outra gerência
    dup = ProjetoFactory(nome="Canonico & Trio", gerencia=a.gerencia, fluxo=a.fluxo)
    evento = _trio(a, b, dup)

    with pytest.raises(ValueError, match="trio"):
        merge_projeto_duplicates(pairs=PAR_MERGE, apply=True)

    assert _vagas(evento) == (a.pk, b.pk, dup.pk)
    assert Projeto.objects.filter(pk=dup.pk).exists()


def test_merge_com_apply_le_os_eventos_com_lock(merge, gerencia):
    """VIR17A-M5: o UPDATE regrava as três vagas com o que leu; sem lock, um PATCH no meio se perderia."""
    survivor, dup = merge
    _trio(dup, ProjetoFactory(gerencia=gerencia), survivor)

    with CaptureQueriesContext(connection) as consultas:
        merge_projeto_duplicates(pairs=PAR_MERGE, apply=True)

    leituras = [
        q["sql"]
        for q in consultas
        if q["sql"].startswith("SELECT") and 'FROM "core_solicitacao" LEFT OUTER JOIN "core_projeto"' in q["sql"]
    ]
    assert leituras, "o merge não leu os eventos da duplicata"
    assert all("FOR UPDATE" in sql for sql in leituras), leituras


def test_merge_dry_run_no_trio_conta_e_nao_muda(merge, gerencia):
    survivor, dup = merge
    x = ProjetoFactory(gerencia=gerencia)
    evento = _trio(survivor, x, dup)

    report = merge_projeto_duplicates(pairs=PAR_MERGE)

    assert _vagas(evento) == (survivor.pk, x.pk, dup.pk)
    assert report["pairs"][0]["conjunto_desfeito"] == 1


# =============================================================================
# compliance_audit confere as três vagas
# =============================================================================


def _check_grupo() -> dict:
    out = StringIO()
    call_command("compliance_audit", "--format=json", stdout=out)
    report = json.loads(out.getvalue())
    return next(c for c in report["checks"] if c["rule"] == "EVENTO-2-PROJETOS")


def test_compliance_audit_trio_valido_passa(trio):
    _trio(*trio)

    check = _check_grupo()

    assert check["status"] == "PASS"
    assert check["violations"] == 0


@pytest.mark.parametrize("campo", ["gerencia", "fluxo"])
def test_compliance_audit_acusa_terceiro_quebrado_por_data_fix(trio, campo):
    evento = _trio(*trio)
    mudanca = {"gerencia": GerenciaFactory()} if campo == "gerencia" else {"fluxo": "SUPER"}
    Projeto.objects.filter(pk=trio[2].pk).update(**mudanca)  # data-fix fura a regra só na 3ª vaga

    check = _check_grupo()

    assert check["status"] == "FAIL"
    assert check["violations"] == 1
    assert check["details"].endswith(f"ids: [{evento.pk}]")


# =============================================================================
# Migração 0138
# =============================================================================


@pytest.mark.migrations
def test_migracao_0138_so_schema():
    """AddField nulo + AddConstraint (+ o texto de ajuda das vagas 1 e 2, sem SQL), sem RunPython: nenhum
    evento muda na ida. Este teste NÃO roda a volta: voltar para a 0137 apaga a coluna e, com ela, o 3º projeto
    dos trios gravados (VIR17A-M2). Por isso a volta de versão só vale antes de existir qualquer trio."""
    migracao = importlib.import_module("apps.core.migrations.0138_solicitacao_projeto_3").Migration
    ops = migracao.operations

    assert not any(isinstance(op, RunPython) for op in ops)
    assert {type(op) for op in ops} == {AddField, AddConstraint, AlterField}
    assert sorted(op.name for op in ops if isinstance(op, AlterField)) == ["projeto", "projeto_2"]
    [add_field] = [op for op in ops if isinstance(op, AddField)]
    assert add_field.name == "projeto_3" and add_field.field.null
    assert add_field.field.default is models.NOT_PROVIDED
    assert [op.constraint.name for op in ops if isinstance(op, AddConstraint)] == ["solicitacao_projeto_3_valido"]

    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(cursor, Solicitacao._meta.db_table)
    assert "solicitacao_projeto_3_valido" in constraints
