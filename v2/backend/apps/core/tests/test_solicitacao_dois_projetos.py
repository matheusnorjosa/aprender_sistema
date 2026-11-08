"""
#2036, PR 1 — evento de dois projetos: modelo e regra.

Decisões do dono (08/11/2026): o evento tem até 2 projetos, iguais (sem principal), da mesma gerência e do
mesmo fluxo. Mudar a gerência ou o fluxo de um projeto que está em evento com outro fica bloqueado, com
aviso, em qualquer evento (regra 10). A contagem por projeto conta o evento nos dois; os totais contam uma
vez. Helpers em `services/solicitacao_projetos.py`.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

import importlib
import json
from io import StringIO

from django.core.management import call_command
from django.db import IntegrityError, connection, transaction
from django.db.migrations.operations import AddConstraint, AddField, AlterField, RunPython
from django.db.models import Count, ProtectedError, Q
from rest_framework.test import APIClient

import pytest

from apps.core.models import Gerencia, Projeto, Solicitacao
from apps.core.services.projeto_merge import merge_projeto_duplicates
from apps.core.services.solicitacao_projetos import (
    MSG_FLUXO_DIFERENTE,
    MSG_GERENCIA_DIFERENTE,
    MSG_MESMO_PROJETO,
    MSG_SEM_GERENCIA,
    contar_por_projeto,
    eventos_conjuntos_do_projeto,
    ids_dos_projetos,
    par_de_projetos_invalido,
    projetos_do_evento,
    q_tem_projeto,
    rotulo_dos_projetos,
)
from apps.core.tests.factories import GerenciaFactory, ProjetoFactory, SolicitacaoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def gerencia() -> Gerencia:
    return GerenciaFactory()


@pytest.fixture
def par(gerencia):
    """Dois projetos NAO_SUPER da mesma gerência (par válido)."""
    return (
        ProjetoFactory(nome="Uni Duni Teste", gerencia=gerencia),
        ProjetoFactory(nome="Cataventos Teste", gerencia=gerencia),
    )


@pytest.fixture
def g1() -> Gerencia:
    gerencia, _ = Gerencia.objects.get_or_create(nome="SUPERINTENDENCIA", defaults={"nome_setor": "Super"})
    return gerencia


@pytest.fixture
def dat() -> APIClient:
    client = APIClient()
    client.force_authenticate(user=UsuarioFactory(groups=["DAT"]))
    return client


def _combo(a: Projeto, b: Projeto, **extra) -> Solicitacao:
    return SolicitacaoFactory(projeto=a, projeto_2=b, **extra)


# =============================================================================
# Modelo: constraint e PROTECT
# =============================================================================


def test_constraint_recusa_o_mesmo_projeto_nas_duas_vagas(par):
    a, _ = par
    with pytest.raises(IntegrityError), transaction.atomic():
        _combo(a, a)


def test_constraint_recusa_segundo_sem_o_primeiro(par):
    _, b = par
    with pytest.raises(IntegrityError), transaction.atomic():
        SolicitacaoFactory(projeto=None, projeto_2=b)


def test_constraint_aceita_par_e_projeto_unico(par):
    a, b = par
    _combo(a, b)
    SolicitacaoFactory(projeto=a)
    SolicitacaoFactory(projeto=None)


def test_apagar_projeto_da_vaga_2_da_protected_error(par):
    a, b = par
    _combo(a, b)
    with pytest.raises(ProtectedError), transaction.atomic():
        b.delete()


# =============================================================================
# Helpers (services/solicitacao_projetos.py)
# =============================================================================


def test_par_valido_nao_tem_erro(par):
    assert par_de_projetos_invalido(*par) is None


def test_par_recusa_o_mesmo_projeto(par):
    a, _ = par
    assert par_de_projetos_invalido(a, a) == MSG_MESMO_PROJETO


def test_par_recusa_outra_gerencia(par):
    a, _ = par
    outro = ProjetoFactory(gerencia=GerenciaFactory())
    assert par_de_projetos_invalido(a, outro) == MSG_GERENCIA_DIFERENTE


def test_par_recusa_outro_fluxo(par, gerencia):
    a, _ = par
    outro = ProjetoFactory(gerencia=gerencia, fluxo="SUPER")
    assert par_de_projetos_invalido(a, outro) == MSG_FLUXO_DIFERENTE


@pytest.mark.parametrize("qual", ["primeiro", "segundo", "os_dois"])
def test_par_recusa_projeto_sem_gerencia_fail_closed(par, qual):
    """Gerência NULL nas duas vagas não é "a mesma gerência" (cético, furo 13)."""
    a, b = par
    if qual in ("primeiro", "os_dois"):
        a = ProjetoFactory(gerencia=None)
    if qual in ("segundo", "os_dois"):
        b = ProjetoFactory(gerencia=None)
    assert par_de_projetos_invalido(a, b) == MSG_SEM_GERENCIA


def test_rotulo_de_projeto_unico_e_o_nome(par):
    a, _ = par
    assert rotulo_dos_projetos(SolicitacaoFactory(projeto=a)) == a.nome


def test_rotulo_sem_projeto_e_none():
    assert rotulo_dos_projetos(SolicitacaoFactory(projeto=None)) is None


def test_rotulo_do_combo_nao_depende_da_vaga(par):
    a, b = par
    assert rotulo_dos_projetos(_combo(a, b)) == rotulo_dos_projetos(_combo(b, a)) == "Cataventos Teste + Uni Duni Teste"


def test_projetos_e_ids_do_evento(par):
    a, b = par
    combo = _combo(a, b)
    assert projetos_do_evento(combo) == [a, b]
    assert ids_dos_projetos(combo) == ids_dos_projetos(_combo(b, a)) == frozenset({a.pk, b.pk})
    assert ids_dos_projetos(SolicitacaoFactory(projeto=a)) == frozenset({a.pk})
    assert ids_dos_projetos(SolicitacaoFactory(projeto=None)) == frozenset()


def test_q_tem_projeto_acha_pela_vaga_2_uma_vez(par):
    a, b = par
    combo = _combo(a, b)
    SolicitacaoFactory(projeto=ProjetoFactory())

    achados = list(Solicitacao.objects.filter(q_tem_projeto(pk=b.pk)))

    assert achados == [combo]
    assert list(Solicitacao.objects.filter(q_tem_projeto(nome__in=[a.nome, b.nome]))) == [combo]


def test_contar_por_projeto_conta_o_combo_nos_dois_e_o_total_uma_vez(par):
    a, b = par
    _combo(a, b)
    SolicitacaoFactory(projeto=a)
    SolicitacaoFactory(projeto=None)
    qs = Solicitacao.objects.all()

    contagem = contar_por_projeto(qs)

    assert contagem == {a.nome: {"count": 2}, b.nome: {"count": 1}}
    assert None not in contagem, "evento de projeto único não cria balde nulo na vaga 2"
    assert qs.count() == 3, "o total de eventos não muda"


def test_contar_por_projeto_soma_varias_anotacoes(par):
    a, b = par
    _combo(a, b, gcal_status="ERROR")
    SolicitacaoFactory(projeto=b, gcal_status="PUBLISHED")

    contagem = contar_por_projeto(
        Solicitacao.objects.all(),
        "pk",
        count=Count("id"),
        error=Count("id", filter=Q(gcal_status="ERROR")),
    )

    assert contagem == {a.pk: {"count": 1, "error": 1}, b.pk: {"count": 2, "error": 1}}


def test_eventos_conjuntos_conta_as_duas_vagas(par):
    a, b = par
    _combo(a, b)
    _combo(b, a, status="reprovado")
    SolicitacaoFactory(projeto=a)

    assert eventos_conjuntos_do_projeto(a) == 2
    assert eventos_conjuntos_do_projeto(b) == 2
    assert eventos_conjuntos_do_projeto(ProjetoFactory()) == 0


# =============================================================================
# Regra 10: gerência e fluxo de projeto em evento conjunto ficam presos (API e admin)
# =============================================================================


def test_api_bloqueia_mudar_gerencia_de_projeto_em_combo(dat, par):
    a, b = par
    _combo(a, b, status="reprovado")  # decisão do dono: vale para todos os eventos
    outra = GerenciaFactory()

    resp = dat.patch(f"/api/projetos/{a.id}/", {"gerencia": outra.id}, format="json")

    assert resp.status_code == 400, resp.content
    [msg] = resp.json()["errors"]["gerencia"]
    assert "1 evento" in msg
    a.refresh_from_db()
    assert a.gerencia_id == b.gerencia_id


def test_api_bloqueia_mudar_fluxo_de_projeto_em_combo(dat, g1):
    a = ProjetoFactory(gerencia=g1, fluxo="SUPER")
    b = ProjetoFactory(gerencia=g1, fluxo="SUPER")
    _combo(b, a)  # na vaga 2 também vale

    resp = dat.patch(f"/api/projetos/{a.id}/", {"fluxo": "NAO_SUPER"}, format="json")

    assert resp.status_code == 400, resp.content
    assert "gerencia" in resp.json()["errors"]
    a.refresh_from_db()
    assert a.fluxo == "SUPER"


def test_api_salvar_com_os_mesmos_valores_passa(dat, par, gerencia):
    a, b = par
    _combo(a, b)

    resp = dat.patch(
        f"/api/projetos/{a.id}/", {"nome": "Renomeado", "fluxo": "NAO_SUPER", "gerencia": gerencia.id}, format="json"
    )

    assert resp.status_code == 200, resp.content


def test_api_projeto_fora_de_combo_muda_gerencia(dat, par):
    a, _ = par
    SolicitacaoFactory(projeto=a)
    outra = GerenciaFactory()

    resp = dat.patch(f"/api/projetos/{a.id}/", {"gerencia": outra.id}, format="json")

    assert resp.status_code == 200, resp.content


def _projeto_admin_form(projeto: Projeto, **mudar):
    from apps.core.admin import ProjetoAdminForm

    data = {
        "nome": projeto.nome,
        "codigo": projeto.codigo,
        "fluxo": projeto.fluxo,
        "ativo": True,
        "is_test": False,
        "descricao": "",
        "setor": "",
        "gerencia": projeto.gerencia_id or "",
        **mudar,
    }
    return ProjetoAdminForm(data=data, instance=projeto)


def test_admin_bloqueia_mudar_gerencia_de_projeto_em_combo(par):
    a, b = par
    _combo(a, b)

    form = _projeto_admin_form(a, gerencia=GerenciaFactory().id)

    assert not form.is_valid()
    assert "1 evento" in form.errors["gerencia"][0]


def test_admin_bloqueia_mudar_fluxo_de_projeto_em_combo(g1):
    a = ProjetoFactory(gerencia=g1, fluxo="SUPER")
    _combo(a, ProjetoFactory(gerencia=g1, fluxo="SUPER"))

    form = _projeto_admin_form(a, fluxo="NAO_SUPER")

    assert not form.is_valid()
    assert "1 evento" in form.errors["fluxo"][0]


def test_admin_mesmos_valores_passa(par):
    a, b = par
    _combo(a, b)

    form = _projeto_admin_form(a, nome="Renomeado no admin")

    assert form.is_valid(), form.errors


# =============================================================================
# Admin da Solicitacao (cético, furo 8)
# =============================================================================


def test_admin_solicitacao_projeto_2_somente_leitura():
    from apps.core.admin import SolicitacaoAdmin

    assert "projeto_2" in SolicitacaoAdmin.readonly_fields


def _solicitacao_admin_form(sol: Solicitacao, projeto: Projeto | None):
    from apps.core.admin import SolicitacaoAdminForm

    return SolicitacaoAdminForm(data={"projeto": projeto.pk if projeto else ""}, instance=sol)


def test_admin_solicitacao_recusa_projeto_igual_ao_2(par):
    a, b = par
    form = _solicitacao_admin_form(_combo(a, b), b)

    assert not form.is_valid()
    assert form.errors["projeto"] == [MSG_MESMO_PROJETO]


def test_admin_solicitacao_recusa_projeto_de_outra_gerencia(par):
    a, b = par
    form = _solicitacao_admin_form(_combo(a, b), ProjetoFactory(gerencia=GerenciaFactory()))

    assert form.errors["projeto"] == [MSG_GERENCIA_DIFERENTE]


def test_admin_solicitacao_recusa_tirar_o_primeiro_com_o_2(par):
    a, b = par
    form = _solicitacao_admin_form(_combo(a, b), None)

    assert "projeto" in form.errors


def test_admin_solicitacao_aceita_trocar_por_projeto_compativel(par, gerencia):
    a, b = par
    form = _solicitacao_admin_form(_combo(a, b), ProjetoFactory(gerencia=gerencia))

    assert "projeto" not in form.errors


# =============================================================================
# Merge de projetos (as duas direções)
# =============================================================================


@pytest.mark.parametrize("dup_na_vaga", [1, 2])
def test_merge_desfaz_o_par_survivor_dup_sem_integrity_error(par, gerencia, dup_na_vaga):
    survivor = ProjetoFactory(nome="CANONICO COMBO", gerencia=gerencia)
    dup = ProjetoFactory(nome="Canonico & Combo", gerencia=gerencia)
    combo = _combo(dup, survivor) if dup_na_vaga == 1 else _combo(survivor, dup)
    _, b = par
    outro = _combo(dup, b)  # dup com outro projeto: só reparenta

    report = merge_projeto_duplicates(pairs=[("CANONICO COMBO", "Canonico & Combo")], apply=True)

    combo.refresh_from_db()
    outro.refresh_from_db()
    assert (combo.projeto_id, combo.projeto_2_id) == (survivor.pk, None)
    assert (outro.projeto_id, outro.projeto_2_id) == (survivor.pk, b.pk)
    entry = report["pairs"][0]
    assert entry["status"] == "merged"
    assert entry["conjunto_desfeito"] == 1
    assert not Projeto.objects.filter(pk=dup.pk).exists()


@pytest.mark.parametrize("dup_na_vaga", [1, 2])
def test_merge_recusa_quando_quebraria_o_par_com_um_terceiro(par, dup_na_vaga):
    """Revisão do PR 1: a duplicata em par com um terceiro X; o sobrevivente é de outra gerência. Reparentar
    gravaria um par inválido (pior caso: fluxo divergente escapa da PA-01). O merge recusa e não muda nada."""
    a, _ = par
    survivor = ProjetoFactory(nome="CANONICO COMBO", gerencia=GerenciaFactory())
    dup = ProjetoFactory(nome="Canonico & Combo", gerencia=a.gerencia, fluxo=a.fluxo)
    evento = _combo(dup, a) if dup_na_vaga == 1 else _combo(a, dup)

    with pytest.raises(ValueError, match="par"):
        merge_projeto_duplicates(pairs=[("CANONICO COMBO", "Canonico & Combo")], apply=True)

    evento.refresh_from_db()
    assert dup.pk in (evento.projeto_id, evento.projeto_2_id)
    assert Projeto.objects.filter(pk=dup.pk).exists()


def test_merge_dry_run_conta_o_par_e_nao_muda(gerencia):
    survivor = ProjetoFactory(nome="CANONICO COMBO", gerencia=gerencia)
    dup = ProjetoFactory(nome="Canonico & Combo", gerencia=gerencia)
    combo = _combo(survivor, dup)

    report = merge_projeto_duplicates(pairs=[("CANONICO COMBO", "Canonico & Combo")])

    combo.refresh_from_db()
    assert combo.projeto_2_id == dup.pk
    entry = report["pairs"][0]
    assert entry["conjunto_desfeito"] == 1
    assert "Solicitacao" not in entry["reparented"], "o par é desfeito, não reparentado"


# =============================================================================
# Sanidade no compliance_audit
# =============================================================================


def _check_dois_projetos() -> dict:
    out = StringIO()
    call_command("compliance_audit", "--format=json", stdout=out)
    report = json.loads(out.getvalue())
    return next(c for c in report["checks"] if c["rule"] == "EVENTO-2-PROJETOS")


def test_compliance_audit_sem_par_quebrado_passa(par):
    _combo(*par)

    check = _check_dois_projetos()

    assert check["status"] == "PASS"
    assert check["violations"] == 0


def test_compliance_audit_acusa_par_quebrado_por_data_fix(par):
    a, b = par
    combo = _combo(a, b)
    Projeto.objects.filter(pk=b.pk).update(gerencia=GerenciaFactory())  # data-fix fura a regra 2

    check = _check_dois_projetos()

    assert check["status"] == "FAIL"
    assert check["violations"] == 1
    assert str(combo.pk) in check["details"]


def test_compliance_audit_acusa_fluxo_divergente_que_escapa_da_aprovacao_super(g1):
    """Vaga 1 NAO_SUPER e vaga 2 SUPER: o poder lê só `projeto` e trata o evento como NAO_SUPER (falha aberta
    da PA-01 para o projeto SUPER). Quem pega é o `compliance_audit`."""
    a = ProjetoFactory(nome="Vaga Um Teste", gerencia=g1, fluxo="NAO_SUPER")
    b = ProjetoFactory(nome="Vaga Dois Teste", gerencia=g1, fluxo="NAO_SUPER")
    combo = _combo(a, b)
    Projeto.objects.filter(pk=b.pk).update(fluxo="SUPER")  # data-fix fura a regra 2 só no fluxo

    check = _check_dois_projetos()

    assert check["status"] == "FAIL"
    assert check["violations"] == 1
    assert str(combo.pk) in check["details"]


# =============================================================================
# Migração 0134
# =============================================================================


@pytest.mark.migrations
def test_migracao_0134_so_schema_e_reversivel():
    """AddField nulo + AddConstraint, sem RunPython: todo evento fica com projeto_2 NULL e a volta é limpa
    (antes da carga da virada; depois dela, a volta apaga os 2º projetos e exige backup)."""
    migracao = importlib.import_module("apps.core.migrations.0134_solicitacao_projeto_2").Migration
    ops = migracao.operations

    assert not any(isinstance(op, RunPython) for op in ops)
    assert all(op.reversible for op in ops)
    [add_field] = [op for op in ops if isinstance(op, AddField)]
    assert add_field.name == "projeto_2" and add_field.field.null
    assert [op.constraint.name for op in ops if isinstance(op, AddConstraint)] == ["solicitacao_projeto_2_valido"]
    assert all(op.name == "projeto" for op in ops if isinstance(op, AlterField))

    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(cursor, Solicitacao._meta.db_table)
    assert "solicitacao_projeto_2_valido" in constraints
