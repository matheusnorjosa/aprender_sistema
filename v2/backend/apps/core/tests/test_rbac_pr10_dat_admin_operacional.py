"""
PR 10 das permissões (16/10/2026): o DAT vira o administrador operacional da plataforma.

Decisões do dono que estes testes travam (plano `plano_permissoes_PR10_S4_2026-10-16.md`, seção
final "Decisões do dono"):

- pacote `ADMIN_OPERACIONAL` final: aprova (base 5, `capacidade_aprovar`), cria, edita e exclui em
  qualquer projeto, isento da regra da compra, painel do Google, Pré-agenda e seção Controle; perde
  `import_spreadsheet`. O grupo Superintendência (0 membros) perde as duas capacidades que tinha;
- D2: quem alterou a conta do autor não decide as solicitações dele por 30 dias, contados da decisão
  ou da criação do evento, o que vier antes; o superusuário decide, marcado no AuditLog;
- quem editou campo material de uma pendente não a decide;
- S4: o DAT altera todas as contas menos a de superusuário; a senha redefinida fica no AuditLog e
  obriga a troca no próximo acesso;
- a troca de fluxo do projeto fica no AuditLog, e o evento auto-aprovado pelo fluxo fica marcado.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportIndexIssue=false, reportOptionalSubscript=false, reportCallIssue=false

from __future__ import annotations

import importlib
import json
from datetime import timedelta
from io import StringIO
from typing import Any
from unittest.mock import patch

from django.apps import apps as django_apps
from django.core.cache import cache
from django.core.management import call_command
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog, Gerencia, PermissaoFuncional, Solicitacao, Usuario
from apps.core.rbac.policies import (
    aprovadora_restrita_a_superintendencia,
    can_admin_mutate_target,
    resolve_public_policies,
    solicitation_approval_basis,
    solicitation_approval_basis_for,
    user_has_policy,
)
from apps.core.services import solicitacao_approval
from apps.core.services.functional_permissions_seed import FUNCTIONAL_PERMISSIONS_SEED
from apps.core.services.rbac_pacotes import PACOTE, TECNICAS
from apps.core.services.rbac_permissions import get_user_functional_permissions
from apps.core.tests.factories import (
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
    com_papel,
    liberar_par,
)

pytestmark = pytest.mark.django_db

PACOTE_FINAL = frozenset(
    {
        "manage_admin_registries",
        "manage_purchases_and_materials",
        "view_all_availability",
        "view_map_metrics",
        "create_solicitation",
        "edit_solicitation_as_owner_or_privileged",
        "approve_solicitation",
        "execute_restricted_operations",
        "operate_preagenda",
        "run_daily_operations",
        "create_solicitation_without_purchase",
    }
)

ALTERED = "altered_account_approval_forbidden"
EDITED = "edited_by_approver_forbidden"
SELF = "self_approval_forbidden"


@pytest.fixture(autouse=True)
def _cache_limpo():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def g19() -> Gerencia:
    g, _ = Gerencia.objects.get_or_create(nome="GERENCIA DAT", defaults={"nome_setor": "DAT"})
    g.perfil = Gerencia.Perfil.ADMIN_OPERACIONAL
    g.save()
    return g


@pytest.fixture
def g1() -> Gerencia:
    g, _ = Gerencia.objects.get_or_create(nome="SUPERINTENDENCIA", defaults={"nome_setor": "Superintendência"})
    return g


@pytest.fixture
def g27() -> Gerencia:
    g, _ = Gerencia.objects.get_or_create(nome="CONTROLE", defaults={"nome_setor": "Controle"})
    g.perfil = Gerencia.Perfil.CONTROLE
    g.save()
    return g


@pytest.fixture
def root() -> Usuario:
    return UsuarioFactory(superuser=True)


def _dat(g19: Gerencia, papel: str = "EQUIPE", grupo: bool = True) -> Usuario:
    """Pessoa do DAT como em produção: grupo DAT + vínculo EQUIPE (ou GERENTE) na gerência DAT."""
    user = UsuarioFactory(groups=["DAT"] if grupo else None)
    com_papel(user, papel, g19)
    cache.clear()
    return user


def _gerente_g1(g1: Gerencia) -> Usuario:
    user = UsuarioFactory()
    com_papel(user, "GERENTE", g1)
    return user


def _par_controle() -> Usuario:
    return UsuarioFactory(groups=["Controle", "Assistente Administrativo"], groups__vinculo=False)


def _pendente_super(g1: Gerencia, autor: Usuario | None = None, **extra: Any) -> Solicitacao:
    projeto = ProjetoFactory(super=True, gerencia=g1)
    return SolicitacaoFactory(usuario=autor or UsuarioFactory(), projeto=projeto, **extra)


def _client(user: Usuario) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _approve(user: Usuario, sol: Solicitacao):
    return _client(user).patch(f"/api/solicitacoes/{sol.id}/approve/", {}, format="json")


def _reject(user: Usuario, sol: Solicitacao):
    return _client(user).patch(f"/api/solicitacoes/{sol.id}/reject/", {"justificativa": "x"}, format="json")


def _alterou(ator: Usuario, alvo: Usuario, quando=None, action: str = AuditLog.Action.UPDATE) -> AuditLog:
    """Registro de alteração da conta `alvo` por `ator` (o que a tela de Usuários grava)."""
    return AuditLog.objects.create(
        usuario=ator,
        action=action,
        model_name="Usuario",
        details={"target_user_id": alvo.pk, "campos": ["first_name"]},
        created_at=quando or timezone.now(),
    )


def _decisoes(sol: Solicitacao) -> int:
    return AuditLog.objects.filter(
        model_name="Solicitacao",
        details__solicitacao_id=sol.id,
        action__in=[AuditLog.Action.APPROVE, AuditLog.Action.REJECT],
    ).count()


# ============================================================================
# 4.1 Pacote e união
# ============================================================================


class TestPacote:
    def test_pacote_admin_operacional_e_o_final(self):
        assert PACOTE["ADMIN_OPERACIONAL"] == PACOTE_FINAL

    def test_grupo_dat_menos_tecnicas_contido_no_pacote(self):
        """Invariante do PR 12: quando o grupo deixar de contar, o DAT não perde nada."""
        do_grupo = {item.codename for item in FUNCTIONAL_PERMISSIONS_SEED if "DAT" in item.group_names}
        assert do_grupo - TECNICAS <= PACOTE["ADMIN_OPERACIONAL"]

    def test_seed_sem_import_spreadsheet_no_dat_e_sem_capacidades_na_superintendencia(self):
        grupos = {item.codename: set(item.group_names) for item in FUNCTIONAL_PERMISSIONS_SEED}
        assert "DAT" not in grupos["import_spreadsheet"]
        assert "Superintendência" not in grupos["approve_solicitation"]
        assert "Superintendência" not in grupos["execute_restricted_operations"]

    def test_migration_0126_aplica_e_desfaz(self):
        modulo = importlib.import_module("apps.core.migrations.0126_dat_admin_operacional_grupos")
        through = PermissaoFuncional.groups.through
        pares = {
            ("DAT", "import_spreadsheet"),
            ("Superintendência", "approve_solicitation"),
            ("Superintendência", "execute_restricted_operations"),
        }

        def presentes() -> set[tuple[str, str]]:
            return (
                set(
                    through.objects.filter(
                        group__name__in=["DAT", "Superintendência"],
                        permissaofuncional__codename__in=[c for _, c in pares],
                    ).values_list("group__name", "permissaofuncional__codename")
                )
                & pares
            )

        modulo.backwards(django_apps, None)
        assert presentes() == pares
        modulo.forwards(django_apps, None)
        assert presentes() == set()

    def test_equipe_na_g19_sem_grupo_recebe_o_pacote(self, g19):
        user = _dat(g19, grupo=False)
        assert get_user_functional_permissions(user) >= PACOTE_FINAL
        assert "import_spreadsheet" not in get_user_functional_permissions(user)

    @pytest.mark.parametrize("papel", ["FORMADOR", "COORDENADOR", "APOIO"])
    def test_formador_coordenador_apoio_na_g19_nao_aprovam(self, g19, g1, papel):
        user = UsuarioFactory()
        com_papel(user, papel, g19)
        cache.clear()
        assert solicitation_approval_basis(user) is None
        assert _approve(user, _pendente_super(g1)).status_code == 403

    def test_grupo_dat_sem_vinculo_nao_aprova(self, g1):
        user = UsuarioFactory(groups=["DAT"])
        assert solicitation_approval_basis(user) is None
        assert _approve(user, _pendente_super(g1)).status_code == 403

    def test_grupo_superintendencia_sozinho_nao_aprova(self, g1):
        user = UsuarioFactory(groups=["Superintendência"])
        assert "approve_solicitation" not in get_user_functional_permissions(user)
        assert solicitation_approval_basis(user) is None
        assert _approve(user, _pendente_super(g1)).status_code == 403


# ============================================================================
# 4.2 Aprovação (base 5)
# ============================================================================


class TestAprovacaoDoDat:
    def test_dat_aprova_e_reprova_individual_e_lote_com_autoridade_capacidade_aprovar(self, g19, g1):
        dat = _dat(g19)
        assert solicitation_approval_basis(dat) == "capacidade_aprovar"
        a, b, c, d = (_pendente_super(g1) for _ in range(4))

        assert _approve(dat, a).status_code == 200
        assert _reject(dat, b).status_code == 200
        resp = _client(dat).post("/api/solicitacoes/batch-approve/", {"ids": [c.id]}, format="json")
        assert resp.status_code == 200 and resp.data["approved"] == 1, resp.data
        resp = _client(dat).post("/api/solicitacoes/batch-reject/", {"ids": [d.id]}, format="json")
        assert resp.status_code == 200 and resp.data["rejected"] == 1, resp.data

        logs = AuditLog.objects.filter(model_name="Solicitacao", usuario=dat)
        assert {log.details["autoridade"] for log in logs} == {"capacidade_aprovar"}
        assert logs.count() == 4

    def test_dat_decide_projeto_de_qualquer_gerencia_e_fluxo(self, g19):
        dat = _dat(g19)
        outra = Gerencia.objects.create(nome="GERENCIA VIDAS PR10", nome_setor="Vidas")
        nao_super = SolicitacaoFactory(projeto=ProjetoFactory(gerencia=outra))
        sem_projeto = SolicitacaoFactory(projeto=None)
        assert _approve(dat, nao_super).status_code == 200
        assert _approve(dat, sem_projeto).status_code == 200

    def test_dat_nao_decide_a_propria(self, g19, g1):
        dat = _dat(g19)
        propria = _pendente_super(g1, autor=dat)
        resp = _approve(dat, propria)
        assert resp.status_code == 403 and resp.data["code"] == SELF
        resp = _client(dat).post("/api/solicitacoes/batch-approve/", {"ids": [propria.id]}, format="json")
        assert resp.data["errors"][0]["code"] == SELF

    def test_bases_existentes_inalteradas(self, g1, root):
        legado = UsuarioFactory(groups=["Superintendência", "Gerente"], groups__vinculo=False)
        assert solicitation_approval_basis(root) == "superuser"
        assert solicitation_approval_basis(_gerente_g1(g1)) == "gerente_superintendencia"
        assert solicitation_approval_basis(_par_controle()) == "asst_admin_controle"
        assert solicitation_approval_basis(legado) == "grupo_superintendencia_gerente"

    def test_gerente_g1_e_dat_fora_do_escopo_decide_como_capacidade_aprovar(self, g19, g1):
        user = _gerente_g1(g1)
        com_papel(user, "EQUIPE", g19)
        cache.clear()
        fora = SolicitacaoFactory(projeto=ProjetoFactory())
        assert solicitation_approval_basis(user) == "gerente_superintendencia"
        assert solicitation_approval_basis_for(user, fora) == "capacidade_aprovar"
        assert aprovadora_restrita_a_superintendencia(user) is False

    def test_lotar_equipe_na_g19_audita_autoridade_com_cache_preenchido(self, root, g19):
        alvo = UsuarioFactory()
        get_user_functional_permissions(alvo)  # cache preenchido antes do salvar
        client = _client(root)

        def logs() -> list[str]:
            return list(
                AuditLog.objects.filter(
                    model_name="Usuario", details__target_user_id=alvo.id, details__has_key="autoridade_aprovacao"
                )
                .order_by("id")
                .values_list("details__autoridade_aprovacao", flat=True)
            )

        resp = client.patch(
            f"/api/usuarios-admin/{alvo.id}/",
            {"equipe_administrativa": True, "gerencia_id": g19.id},
            format="json",
        )
        assert resp.status_code == 200, resp.content
        assert logs() == ["concedida"]
        get_user_functional_permissions(alvo)
        resp = client.patch(f"/api/usuarios-admin/{alvo.id}/", {"equipe_administrativa": False}, format="json")
        assert resp.status_code == 200, resp.content
        assert logs() == ["concedida", "revogada"]


# ============================================================================
# 4.3 D2: quem alterou a conta do autor não decide
# ============================================================================


class TestSegregacaoPorHistorico:
    @pytest.mark.parametrize(
        "acao", ["ASSIGN_GROUPS", "CREATE", "RESET_PASSWORD", "UPDATE", "USER_ANONYMIZE", "USER_PRIVILEGE_CHANGED"]
    )
    def test_d2_bloqueia_aprovar_e_reprovar(self, g19, g1, acao):
        dat = _dat(g19)
        autor = UsuarioFactory()
        _alterou(dat, autor, action=acao)
        sol = _pendente_super(g1, autor=autor)

        for resp in (_approve(dat, sol), _reject(dat, sol)):
            assert resp.status_code == 403, resp.data
            assert resp.data["code"] == ALTERED
        sol.refresh_from_db()
        assert sol.status == "pendente"
        assert _decisoes(sol) == 0

    def test_acoes_que_alteram_conta(self):
        assert solicitacao_approval.ACOES_QUE_ALTERAM_CONTA == frozenset(
            {"CREATE", "UPDATE", "RESET_PASSWORD", "USER_PRIVILEGE_CHANGED", "ASSIGN_GROUPS", "USER_ANONYMIZE"}
        )

    @pytest.mark.parametrize(("dias", "bloqueia"), [(29, True), (30, True), (31, False)])
    def test_d2_janela_conta_da_decisao(self, g19, g1, dias, bloqueia):
        dat = _dat(g19)
        autor = UsuarioFactory()
        agora = timezone.now()
        _alterou(dat, autor, quando=agora - timedelta(days=dias) + timedelta(seconds=30 if dias == 30 else 0))
        sol = _pendente_super(g1, autor=autor, created_at=agora)
        resp = _approve(dat, sol)
        assert (resp.status_code == 403) is bloqueia, resp.data

    def test_d2_janela_conta_da_criacao_quando_vem_antes(self, g19, g1):
        """6(b): alteração 31 dias antes da decisão mas 10 antes da criação do evento bloqueia."""
        dat = _dat(g19)
        autor = UsuarioFactory()
        agora = timezone.now()
        _alterou(dat, autor, quando=agora - timedelta(days=31))
        sol = _pendente_super(g1, autor=autor, created_at=agora - timedelta(days=21))
        resp = _approve(dat, sol)
        assert resp.status_code == 403 and resp.data["code"] == ALTERED

    def test_d2_alteracao_bem_antes_da_criacao_nao_conta(self, g19, g1):
        dat = _dat(g19)
        autor = UsuarioFactory()
        agora = timezone.now()
        _alterou(dat, autor, quando=agora - timedelta(days=80))
        sol = _pendente_super(g1, autor=autor, created_at=agora - timedelta(days=40))
        assert _approve(dat, sol).status_code == 200

    def test_d2_pela_api_corrigir_o_nome_bloqueia(self, g19, g1):
        """Decisão 1: qualquer alteração pela tela de Usuários conta, até corrigir o nome."""
        dat = _dat(g19)
        autor = UsuarioFactory(first_name="Nome")
        resp = _client(dat).patch(f"/api/usuarios-admin/{autor.id}/", {"first_name": "Nome Certo"}, format="json")
        assert resp.status_code == 200, resp.content
        resp = _approve(dat, _pendente_super(g1, autor=autor))
        assert resp.status_code == 403 and resp.data["code"] == ALTERED

    def test_d2_criar_a_conta_bloqueia(self, g19, g1):
        dat = _dat(g19)
        resp = _client(dat).post(
            "/api/usuarios-admin/",
            {"username": "nova_pr10", "email": "nova_pr10@example.invalid", "cpf": "52998224725"},
            format="json",
        )
        assert resp.status_code == 201, resp.content
        autor = Usuario.objects.get(username="nova_pr10")
        resp = _approve(dat, _pendente_super(g1, autor=autor))
        assert resp.status_code == 403 and resp.data["code"] == ALTERED

    def test_update_usuario_grava_so_campos_que_mudaram(self, g19):
        dat = _dat(g19)
        alvo = UsuarioFactory(first_name="Ana", last_name="Lima")
        client = _client(dat)
        resp = client.patch(
            f"/api/usuarios-admin/{alvo.id}/", {"first_name": "Ana", "last_name": "Lima"}, format="json"
        )
        assert resp.status_code == 200, resp.content
        assert not AuditLog.objects.filter(action="UPDATE", model_name="Usuario", details__target_user_id=alvo.id)
        resp = client.patch(
            f"/api/usuarios-admin/{alvo.id}/", {"first_name": "Ana", "last_name": "Souza"}, format="json"
        )
        assert resp.status_code == 200, resp.content
        (log,) = AuditLog.objects.filter(action="UPDATE", model_name="Usuario", details__target_user_id=alvo.id)
        assert log.details["campos"] == ["last_name"]

    def test_audit_da_conta_na_mesma_transacao(self, g19):
        """Se o registro da alteração falha, a alteração não fica (a D2 não pode falhar aberta)."""
        dat = _dat(g19)
        alvo = UsuarioFactory(first_name="Antes")
        original = AuditLog.objects.create

        def falha(**kwargs):
            if kwargs.get("model_name") == "Usuario":
                raise RuntimeError("insert do AuditLog falhou")
            return original(**kwargs)

        with patch.object(AuditLog.objects, "create", side_effect=falha), pytest.raises(RuntimeError):
            _client(dat).patch(f"/api/usuarios-admin/{alvo.id}/", {"first_name": "Depois"}, format="json")
        alvo.refresh_from_db()
        assert alvo.first_name == "Antes"

    def test_d2_lote_errors_e_resto_segue(self, g19, g1):
        dat = _dat(g19)
        alterado = UsuarioFactory()
        _alterou(dat, alterado)
        bloqueada = _pendente_super(g1, autor=alterado)
        livre = _pendente_super(g1)
        resp = _client(dat).post("/api/solicitacoes/batch-approve/", {"ids": [bloqueada.id, livre.id]}, format="json")
        assert resp.status_code == 200
        assert resp.data["approved"] == 1
        assert resp.data["errors"] == [
            {"id": bloqueada.id, "code": ALTERED, "detail": solicitacao_approval.mensagem_impedida(ALTERED, "aprovar")}
        ]
        resp = _client(dat).post("/api/solicitacoes/batch-reject/", {"ids": [bloqueada.id]}, format="json")
        assert resp.data["errors"][0]["code"] == ALTERED

    def test_d2_lote_numero_de_queries_constante(self, g19, g1):
        dat = _dat(g19)

        def consultas(n: int) -> int:
            autores = [UsuarioFactory() for _ in range(n)]
            for autor in autores:
                _alterou(dat, autor)
            ids = [_pendente_super(g1, autor=a).id for a in autores]
            cache.clear()
            get_user_functional_permissions(dat)
            with CaptureQueriesContext(connection) as ctx:
                solicitacao_approval.decisoes_impedidas(dat, Solicitacao.objects.filter(id__in=ids))
            return len(ctx.captured_queries)

        assert consultas(1) == consultas(8)

    def test_d2_log_de_outro_model_nao_conta(self, g19, g1):
        dat = _dat(g19)
        autor = UsuarioFactory()
        AuditLog.objects.create(
            usuario=dat,
            action=AuditLog.Action.DELEGATE_BLOCK_CREATE,
            model_name="AvailabilityBlock",
            details={"target_user_id": autor.pk},
        )
        assert _approve(dat, _pendente_super(g1, autor=autor)).status_code == 200

    def test_d2_outro_dat_que_nao_alterou_decide(self, g19, g1):
        quem_alterou, outro = _dat(g19), _dat(g19)
        autor = UsuarioFactory()
        _alterou(quem_alterou, autor)
        assert _approve(outro, _pendente_super(g1, autor=autor)).status_code == 200

    def test_d2_superusuario_decide_e_marca_conta_alterada_pelo_ator(self, root, g1):
        autor = UsuarioFactory()
        _alterou(root, autor, action=AuditLog.Action.RESET_PASSWORD)
        sol = _pendente_super(g1, autor=autor)
        assert _approve(root, sol).status_code == 200
        log = AuditLog.objects.get(action="APPROVE", details__solicitacao_id=sol.id)
        assert log.details["conta_alterada_pelo_ator"] is True

    def test_decisao_comum_marca_false(self, g19, g1):
        dat = _dat(g19)
        sol = _pendente_super(g1)
        assert _approve(dat, sol).status_code == 200
        log = AuditLog.objects.get(action="APPROVE", details__solicitacao_id=sol.id)
        assert log.details["conta_alterada_pelo_ator"] is False
        assert log.details["editada_pelo_ator"] is False

    def test_d2_home_nao_conta(self, g19, g1):
        dat = _dat(g19)
        alterado = UsuarioFactory()
        _alterou(dat, alterado)
        _pendente_super(g1, autor=alterado)
        _pendente_super(g1)
        resp = _client(dat).get("/api/stats/home/")
        assert resp.status_code == 200
        assert resp.data["pending_approvals"] == 1

    def test_d2_lista_marca_decisao_impedida(self, g19, g1):
        dat = _dat(g19)
        alterado = UsuarioFactory()
        _alterou(dat, alterado)
        bloqueada = _pendente_super(g1, autor=alterado)
        livre = _pendente_super(g1)
        propria = _pendente_super(g1, autor=dat)
        resp = _client(dat).get("/api/solicitacoes/?flow=SUPER&status=pendente&page_size=50")
        assert resp.status_code == 200
        marcas = {item["id"]: item["decisao_impedida"] for item in resp.data["results"]}
        assert marcas[bloqueada.id] == "conta_alterada"
        assert marcas[livre.id] is None
        assert marcas[propria.id] == "propria"

    def test_lista_sem_poder_de_aprovar_nao_marca(self, g1):
        coord = UsuarioFactory()
        com_papel(coord, "COORDENADOR", g1)
        propria = _pendente_super(g1, autor=coord)
        resp = _client(coord).get(f"/api/solicitacoes/{propria.id}/")
        assert resp.status_code == 200
        assert resp.data["decisao_impedida"] is None

    def test_compliance_audit_acusa_d2(self, g19, g1):
        dat = _dat(g19)
        autor = UsuarioFactory()
        sol = _pendente_super(g1, autor=autor)
        assert _approve(dat, sol).status_code == 200
        # Alteração registrada antes da decisão, como se a trava tivesse falhado.
        _alterou(dat, autor, quando=timezone.now() - timedelta(days=1))
        out = StringIO()
        call_command("compliance_audit", "--format=json", stdout=out)
        checks = {c["rule"]: c for c in json.loads(out.getvalue())["checks"]}
        assert checks["PA-02 (segregação D2)"]["status"] == "FAIL"
        assert checks["PA-02 (segregação D2)"]["violations"] == 1


class TestPa07:
    def test_segregacao_conta_alterada_bloqueia_decisao_existe(self):
        from apps.core.tests import test_approval_policy_PA as pa

        assert callable(getattr(pa, "test_segregacao_conta_alterada_bloqueia_decisao", None))


# ============================================================================
# Decisão 4: quem editou campo material de uma pendente não a decide
# ============================================================================


def _editar(user: Usuario, sol: Solicitacao, dados: dict[str, Any]):
    return _client(user).patch(f"/api/solicitacoes/{sol.id}/", dados, format="json")


class TestQuemEditouNaoDecide:
    def test_editou_campo_material_nao_decide(self, g19, g1):
        dat = _dat(g19)
        sol = _pendente_super(g1)
        resp = _editar(dat, sol, {"municipio": MunicipioFactory().id})
        assert resp.status_code == 200, resp.content
        resp = _approve(dat, sol)
        assert resp.status_code == 403 and resp.data["code"] == EDITED
        resp = _client(dat).post("/api/solicitacoes/batch-approve/", {"ids": [sol.id]}, format="json")
        assert resp.data["errors"][0]["code"] == EDITED
        # Outra aprovadora decide.
        assert _approve(_dat(g19), sol).status_code == 200

    def test_editou_so_observacao_decide(self, g19, g1):
        dat = _dat(g19)
        sol = _pendente_super(g1)
        assert _editar(dat, sol, {"observacoes": "só um recado"}).status_code == 200
        assert _approve(dat, sol).status_code == 200

    def test_aprovacao_anterior_zera_a_trava(self, g19, g1):
        dat = _dat(g19)
        sol = _pendente_super(g1)
        antes = timezone.now() - timedelta(days=2)
        AuditLog.objects.create(
            usuario=dat,
            action=AuditLog.Action.UPDATE,
            model_name="Solicitacao",
            details={"solicitacao_id": sol.id, "changed_fields": {"inicio": {"old": "a", "new": "b"}}},
            created_at=antes,
        )
        AuditLog.objects.create(
            usuario=_gerente_g1(g1),
            action=AuditLog.Action.APPROVE,
            model_name="Solicitacao",
            details={"solicitacao_id": sol.id},
            created_at=antes + timedelta(hours=1),
        )
        assert _approve(dat, sol).status_code == 200

    def test_edicao_pela_conta_alterada_conta(self, g19, g1):
        """Fantoche: o DAT altera a conta de X e edita pela conta de X."""
        dat = _dat(g19)
        fantoche = UsuarioFactory()
        _alterou(dat, fantoche)
        sol = _pendente_super(g1)
        AuditLog.objects.create(
            usuario=fantoche,
            action=AuditLog.Action.UPDATE,
            model_name="Solicitacao",
            details={"solicitacao_id": sol.id, "changed_fields": {"formador_ids": {"old": [], "new": [1]}}},
        )
        resp = _approve(dat, sol)
        assert resp.status_code == 403 and resp.data["code"] == EDITED

    def test_superusuario_decide_e_marca_editada_pelo_ator(self, root, g1):
        sol = _pendente_super(g1)
        assert _editar(root, sol, {"municipio": MunicipioFactory().id}).status_code == 200
        assert _approve(root, sol).status_code == 200
        log = AuditLog.objects.get(action="APPROVE", details__solicitacao_id=sol.id)
        assert log.details["editada_pelo_ator"] is True

    def test_paridade_chaves_materiais(self, g1):
        from apps.core.views_solicitacao import _campos_materiais

        sol = _pendente_super(g1)
        assert set(solicitacao_approval.CAMPOS_MATERIAIS_NO_AUDITLOG.values()) == set(_campos_materiais(sol, set()))

    def test_audit_update_solicitacao_dentro_do_atomic(self, g19, g1):
        dat = _dat(g19)
        sol = _pendente_super(g1)
        municipio_antes = sol.municipio_id
        original = AuditLog.objects.create

        def falha(**kwargs):
            if kwargs.get("model_name") == "Solicitacao":
                raise RuntimeError("insert do AuditLog falhou")
            return original(**kwargs)

        with patch.object(AuditLog.objects, "create", side_effect=falha), pytest.raises(RuntimeError):
            _editar(dat, sol, {"municipio": MunicipioFactory().id})
        sol.refresh_from_db()
        assert sol.municipio_id == municipio_antes


# ============================================================================
# S4 (decisão do dono de 16/10): o DAT altera todas as contas, menos a de superusuário
# ============================================================================


def _alvos(g19: Gerencia, g1: Gerencia, g27: Gerencia) -> dict[str, Usuario]:
    apoio = UsuarioFactory()
    com_papel(apoio, "APOIO")
    controle_pacote = UsuarioFactory()
    com_papel(controle_pacote, "EQUIPE", g27)
    return {
        "comum": UsuarioFactory(),
        "apoio": apoio,
        "controle pelo pacote": controle_pacote,
        "controle pelo grupo": UsuarioFactory(groups=["Controle"]),
        "diretoria": UsuarioFactory(groups=["Diretoria"]),
        "outro DAT": _dat(g19),
        "gerente g1": _gerente_g1(g1),
        "par controle": _par_controle(),
    }


class TestS4:
    @pytest.mark.parametrize(
        "classe",
        [
            "comum",
            "apoio",
            "controle pelo pacote",
            "controle pelo grupo",
            "diretoria",
            "outro DAT",
            "gerente g1",
            "par controle",
        ],
    )
    def test_dat_redefine_senha_de_qualquer_conta_com_registro_e_troca_obrigatoria(self, g19, g1, g27, classe):
        dat = _dat(g19)
        alvo = _alvos(g19, g1, g27)[classe]
        assert can_admin_mutate_target(dat, alvo) is True
        resp = _client(dat).patch(f"/api/usuarios-admin/{alvo.id}/", {"password": "NovaSenha!pr10x"}, format="json")
        assert resp.status_code == 200, resp.content
        alvo.refresh_from_db()
        assert alvo.check_password("NovaSenha!pr10x")
        assert alvo.deve_trocar_senha is True
        assert AuditLog.objects.filter(
            usuario=dat, action=AuditLog.Action.RESET_PASSWORD, details__target_user_id=alvo.id
        ).exists()

    def test_dat_desativa_e_reativa_aprovadora(self, g19, g1):
        dat = _dat(g19)
        alvo = _gerente_g1(g1)
        client = _client(dat)
        assert client.patch(f"/api/usuarios-admin/{alvo.id}/", {"is_active": False}, format="json").status_code == 200
        assert client.patch(f"/api/usuarios-admin/{alvo.id}/", {"is_active": True}, format="json").status_code == 200

    def test_conta_de_superusuario_continua_protegida(self, g19):
        dat = _dat(g19)
        alvo = UsuarioFactory(superuser=True)
        assert can_admin_mutate_target(dat, alvo) is False
        resp = _client(dat).patch(f"/api/usuarios-admin/{alvo.id}/", {"password": "NovaSenha!pr10x"}, format="json")
        assert resp.status_code == 404

    def test_superusuario_altera_todas(self, root, g19):
        assert can_admin_mutate_target(root, _dat(g19)) is True
        assert can_admin_mutate_target(root, UsuarioFactory(superuser=True)) is True


# ============================================================================
# Decisão 5: trocar o fluxo do projeto, com registro
# ============================================================================


class TestTrocaDeFluxo:
    def test_dat_troca_fluxo_e_fica_no_auditlog(self, g19, g1):
        dat = _dat(g19)
        projeto = ProjetoFactory(super=True, gerencia=g1)
        resp = _client(dat).patch(f"/api/projetos/{projeto.id}/", {"fluxo": "NAO_SUPER"}, format="json")
        assert resp.status_code == 200, resp.content
        (log,) = AuditLog.objects.filter(model_name="Projeto", details__projeto_id=projeto.id)
        assert log.usuario_id == dat.id
        assert log.action == AuditLog.Action.UPDATE
        assert log.details["fluxo"] == {"old": "SUPER", "new": "NAO_SUPER"}

    def test_salvar_sem_trocar_fluxo_nao_registra(self, g19, g1):
        dat = _dat(g19)
        projeto = ProjetoFactory(super=True, gerencia=g1)
        resp = _client(dat).patch(f"/api/projetos/{projeto.id}/", {"fluxo": "SUPER", "nome": "Outro"}, format="json")
        assert resp.status_code == 200, resp.content
        assert not AuditLog.objects.filter(model_name="Projeto", details__projeto_id=projeto.id).exists()

    def test_evento_auto_aprovado_pelo_fluxo_fica_marcado(self, g19, g1):
        dat = _dat(g19)
        projeto = ProjetoFactory(gerencia=g1)
        municipio = MunicipioFactory()
        liberar_par(municipio, projeto)
        coordenador = UsuarioFactory()
        com_papel(coordenador, "COORDENADOR", g1)
        inicio = timezone.now() + timedelta(days=5)
        resp = _client(dat).post(
            "/api/solicitacoes/",
            {
                "projeto": projeto.id,
                "municipio": municipio.id,
                "tipo_evento": TipoEventoFactory().id,
                "inicio": inicio.isoformat(),
                "fim": (inicio + timedelta(hours=2)).isoformat(),
                "coordenador": coordenador.id,
                "coordenador_acompanha": False,
            },
            format="json",
        )
        assert resp.status_code == 201, resp.content
        sol = Solicitacao.objects.get(pk=resp.data["id"])
        assert sol.status == "aprovado"
        (log,) = AuditLog.objects.filter(
            model_name="Solicitacao", action=AuditLog.Action.CREATE, details__solicitacao_id=sol.id
        )
        assert log.details["auto_aprovada_por_fluxo"] == "NAO_SUPER"
        assert log.details["projeto_id"] == projeto.id


# ============================================================================
# 4.5 Telas, P17, P18, regra da compra
# ============================================================================


class TestTelas:
    def test_me_policies_do_dat_real(self, g19):
        antes = set(resolve_public_policies(UsuarioFactory(groups=["DAT"])))
        depois = set(resolve_public_policies(_dat(g19)))
        assert depois >= {
            "access_solicitation_approvals",
            "use_gcal",
            "manage_solicitacao_status",
            "access_controle_section",
            "execute_restricted_operations",
            "create_solicitation_without_purchase",
            "create_solicitation",
        }
        assert antes - depois == set()

    def test_painel_gcal_responde_para_dat_equipe(self, g19):
        resp = _client(_dat(g19, grupo=False)).get("/api/gcal/dashboard/metrics/")
        assert resp.status_code == 200, resp.content

    def test_diretoria_sem_view_gcal_dashboard(self):
        assert user_has_policy(UsuarioFactory(groups=["Diretoria"]), "view_gcal_dashboard") is False

    def test_dat_exclui_cadastro_e_controle_nao(self, g19):
        assert user_has_policy(_dat(g19), "execute_restricted_operations") is True
        assert user_has_policy(UsuarioFactory(groups=["Controle"]), "execute_restricted_operations") is False

    def test_dat_isento_da_regra_da_compra(self, g19):
        assert user_has_policy(_dat(g19), "create_solicitation_without_purchase") is True

    def test_grupo_dat_sem_vinculo_sem_import_generico(self):
        assert user_has_policy(UsuarioFactory(groups=["DAT"]), "import_generic_spreadsheet") is False
