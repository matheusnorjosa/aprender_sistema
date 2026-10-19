"""
PR 8 das permissões (15/10/2026): o cargo deixa de dar poder; vale o papel vigente na gerência.

Plano: `liberacao/relatorios/plano_permissoes_PR8_PR9_2026-10-15.md`, seção "PR 8". Decisões do
dono de 15/10: a delegação de deslocamento (P16) vale para GERENTE e COORDENADOR vigentes, para
alvo com vínculo FORMADOR vigente na mesma gerência (O8-5); a GERENTE não publica no Google (O8-4).

"Papel vigente" = vínculo `EquipeGerencia` vigente (`vigentes_em`) em gerência ativa
(`EquipeGerencia.gerencias_com_papel`). O grupo de função sozinho não dá nada.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportOptionalMemberAccess=false, reportIndexIssue=false, reportGeneralTypeIssues=false

from __future__ import annotations

import importlib
from datetime import date, timedelta
from typing import Any

from django.apps import apps as django_apps
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.constants import FUNCAO_GROUPS
from apps.core.models import (
    AuditLog,
    AvailabilityBlock,
    Deslocamento,
    EquipeGerencia,
    Gerencia,
    GroupClassificacao,
    PermissaoFuncional,
    Usuario,
)
from apps.core.rbac.policies import resolve_public_policies
from apps.core.services import rbac_pacotes
from apps.core.services.functional_permissions_seed import FUNCTIONAL_PERMISSIONS_SEED, _validate_seed
from apps.core.services.rbac_permissions import capacidades_sem_cache, get_user_functional_permissions
from apps.core.services.rbac_snapshot import snapshot_de_poder
from apps.core.services.solicitacao_scope import projeto_fora_do_alcance_da_restrita
from apps.core.tests.factories import (
    GerenciaFactory,
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
    liberar_par,
)

pytestmark = pytest.mark.django_db

CRIAR_E_EDITAR = {"create_solicitation", "edit_solicitation_as_owner_or_privileged"}


@pytest.fixture(autouse=True)
def _cache_limpo():
    cache.clear()
    yield
    cache.clear()


def _cliente(usuario: Usuario) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=usuario)
    return client


def _vinculo(usuario: Usuario, papel: str, gerencia: Gerencia | None = None, **extra: Any) -> EquipeGerencia:
    """Só o vínculo (sem grupo de função): o papel vigente sozinho."""
    gerencia = gerencia or GerenciaFactory()
    dados: dict[str, Any] = {"ativo": True, "valid_from": date(2000, 1, 1), **extra}
    if papel == "APOIO":
        supervisor = UsuarioFactory()
        EquipeGerencia.objects.create(gerencia=gerencia, usuario=supervisor, papel="COORDENADOR", ativo=True)
        dados["coordenador_supervisor"] = supervisor
    return EquipeGerencia.objects.create(gerencia=gerencia, usuario=usuario, papel=papel, **dados)


def _so_vinculo(papel: str, gerencia: Gerencia | None = None, **extra: Any) -> Usuario:
    usuario = UsuarioFactory()
    _vinculo(usuario, papel, gerencia, **extra)
    return usuario


def _so_grupo(*grupos: str) -> Usuario:
    return UsuarioFactory(groups=list(grupos), groups__vinculo=False)


def _so_aprovar() -> Usuario:
    """Só a capacidade `approve_solicitation`, por um grupo de teste. Era o grupo Superintendência até o
    PR 10 (a migration 0126 tirou dele as capacidades)."""
    grupo, _ = Group.objects.get_or_create(name="Teste so aprovar PR10")
    PermissaoFuncional.objects.get(codename="approve_solicitation").groups.add(grupo)
    user = UsuarioFactory()
    user.groups.add(grupo)
    return user


def _payload_solicitacao(gerencia_id: int | None = None, **extra: Any) -> dict[str, Any]:
    municipio = MunicipioFactory()
    projeto = ProjetoFactory(fluxo="SUPER", gerencia_id=gerencia_id)
    liberar_par(municipio, projeto)
    inicio = timezone.now() + timedelta(days=3)
    return {
        "municipio": municipio.id,
        "projeto": projeto.id,
        "tipo": "evento",
        "tipo_evento": TipoEventoFactory().id,
        "coordenador_acompanha": False,
        "inicio": inicio.isoformat(),
        "fim": (inicio + timedelta(hours=2)).isoformat(),
        **extra,
    }


def _cria(usuario: Usuario, **extra: Any):
    """POST de solicitação num projeto da gerência onde `usuario` atua (PR 9: o escopo é a gerência do projeto)."""
    gerencia_id = min(EquipeGerencia.gerencias_de_atuacao(usuario), default=None)
    return _cliente(usuario).post(
        "/api/solicitacoes/", _payload_solicitacao(gerencia_id=gerencia_id, **extra), format="json"
    )


# ============================================================================
# DIREITOS_PAPEL e capacidades
# ============================================================================


class TestDireitosDoPapel:
    def test_uma_linha_explicita_por_papel(self):
        DIREITOS_PAPEL = rbac_pacotes.DIREITOS_PAPEL
        assert set(DIREITOS_PAPEL) == {p for p, _ in EquipeGerencia.PAPEL_CHOICES}
        assert DIREITOS_PAPEL["FORMADOR"] == frozenset()
        assert DIREITOS_PAPEL["EQUIPE"] == frozenset()
        assert DIREITOS_PAPEL["COORDENADOR"] == CRIAR_E_EDITAR
        # O8-4: a GERENTE não publica no Google (paridade com o grupo Gerente de hoje).
        assert DIREITOS_PAPEL["GERENTE"] == CRIAR_E_EDITAR
        assert DIREITOS_PAPEL["APOIO"] == CRIAR_E_EDITAR | {"publish_setor_solicitacao"}

    def test_direitos_do_papel_sao_capacidades_do_seed(self):
        do_seed = {item.codename for item in FUNCTIONAL_PERMISSIONS_SEED}
        assert set().union(*rbac_pacotes.DIREITOS_PAPEL.values()) <= do_seed


# ============================================================================
# Criação e papel
# ============================================================================


class TestCriacaoPorPapel:
    def test_coordenador_por_vinculo_sem_grupo_cria(self):
        coord = _so_vinculo("COORDENADOR")
        assert not coord.groups.exists()
        response = _cria(coord)
        assert response.status_code == 201, response.data

    def test_grupo_coordenador_sem_vinculo_nao_cria(self):
        response = _cria(_so_grupo("Coordenador"))
        assert response.status_code == 403

    @pytest.mark.parametrize(
        "fora",
        ["vencido", "futuro", "desligado", "gerencia_inativa"],
    )
    def test_vinculo_vencido_futuro_ou_gerencia_inativa_nao_da_direito(self, fora):
        hoje = timezone.localdate()
        if fora == "vencido":
            coord = _so_vinculo("COORDENADOR", valid_from=hoje - timedelta(days=60), valid_to=hoje - timedelta(days=1))
        elif fora == "futuro":
            coord = _so_vinculo("COORDENADOR", valid_from=hoje + timedelta(days=1))
        elif fora == "desligado":
            coord = _so_vinculo("COORDENADOR", ativo=False)
        else:
            coord = _so_vinculo("COORDENADOR", GerenciaFactory(ativo=False))
        assert not CRIAR_E_EDITAR & capacidades_sem_cache(coord.id)
        assert _cria(coord).status_code == 403

    def test_controle_positivo_do_vinculo_vigente(self):
        """Mesma montagem do teste acima, vigente: dá o direito (o teste acima não passa por vazio)."""
        assert CRIAR_E_EDITAR <= capacidades_sem_cache(_so_vinculo("COORDENADOR").id)

    @pytest.mark.parametrize("papel", ["FORMADOR", "EQUIPE"])
    def test_formador_e_equipe_nao_criam(self, papel):
        assert _cria(_so_vinculo(papel)).status_code == 403

    def test_apoio_por_vinculo_publica(self):
        apoio = _so_vinculo("APOIO")
        policies = resolve_public_policies(apoio)
        assert "publish_setor_solicitacao" in policies
        assert "create_solicitation" in policies

    def test_grupo_apoio_sem_vinculo_nao_publica(self):
        policies = resolve_public_policies(_so_grupo("Apoio de Coordenação"))
        assert "publish_setor_solicitacao" not in policies
        assert "create_solicitation" not in policies

    def test_gerente_por_vinculo_nao_publica(self):
        """O8-4: paridade; o papel GERENTE não traz `publish_setor_solicitacao`."""
        assert "publish_setor_solicitacao" not in resolve_public_policies(_so_vinculo("GERENTE"))


# ============================================================================
# Gestora: ver, editar e excluir solicitação alheia da gerência
# ============================================================================


@pytest.fixture
def gerencia_com_alheia():
    gerencia = GerenciaFactory()
    projeto = ProjetoFactory(gerencia=gerencia, fluxo="NAO_SUPER")
    alheia = SolicitacaoFactory(projeto=projeto, local="Original")
    return gerencia, alheia


class TestGestoraPorPapel:
    def test_gerente_por_vinculo_edita_alheia_da_gerencia(self, gerencia_com_alheia):
        gerencia, alheia = gerencia_com_alheia
        gerente = _so_vinculo("GERENTE", gerencia)
        client = _cliente(gerente)
        assert client.get(f"/api/solicitacoes/{alheia.id}/").status_code == 200
        response = client.patch(f"/api/solicitacoes/{alheia.id}/", {"local": "Editado"}, format="json")
        assert response.status_code == 200, response.data

    def test_grupo_gerente_sem_vinculo_gerente_so_as_proprias(self, gerencia_com_alheia):
        """Grupo Gerente + vínculo COORDENADOR na gerência: hoje o grupo dava a gestão; agora só o papel."""
        gerencia, alheia = gerencia_com_alheia
        usuario = _so_grupo("Gerente")
        _vinculo(usuario, "COORDENADOR", gerencia)
        assert _cliente(usuario).get(f"/api/solicitacoes/{alheia.id}/").status_code == 404

    @pytest.mark.usefixtures("modo_uniao")  # grupo com capacidade: só vale no modo soma (PR 12)
    def test_superintendencia_pura_nao_edita_alheia(self, gerencia_com_alheia):
        """O8-11: vê (global por `approve_solicitation`), mas não edita."""
        _, alheia = gerencia_com_alheia
        client = _cliente(_so_aprovar())
        assert client.get(f"/api/solicitacoes/{alheia.id}/").status_code == 200
        response = client.patch(f"/api/solicitacoes/{alheia.id}/", {"local": "Editado"}, format="json")
        assert response.status_code == 403

    def test_aprovadora_restrita_com_2o_vinculo_gerente(self):
        """O8-9: GERENTE em g1 e GERENTE em outra gerência, sem o grupo Gerente: a 2ª entra no alcance."""
        g1, _ = Gerencia.objects.get_or_create(nome="SUPERINTENDENCIA", defaults={"nome_setor": "Super"})
        outra = GerenciaFactory()
        aprovadora = _so_vinculo("GERENTE", g1)
        _vinculo(aprovadora, "GERENTE", outra)
        projeto_da_outra = ProjetoFactory(gerencia=outra, fluxo="NAO_SUPER")
        projeto_sem_vinculo = ProjetoFactory(gerencia=GerenciaFactory(), fluxo="NAO_SUPER")
        assert not projeto_fora_do_alcance_da_restrita(aprovadora, projeto_da_outra)
        assert projeto_fora_do_alcance_da_restrita(aprovadora, projeto_sem_vinculo)


# ============================================================================
# Travas
# ============================================================================


# Os pares do seed anterior, escritos à mão (não lidos da migration): a reversa tem de recriar todos.
PARES_DO_SEED_ANTERIOR: tuple[tuple[str, str], ...] = (
    ("Coordenador", "create_solicitation"),
    ("Apoio de Coordenação", "create_solicitation"),
    ("Gerente", "create_solicitation"),
    ("Coordenador", "edit_solicitation_as_owner_or_privileged"),
    ("Apoio de Coordenação", "edit_solicitation_as_owner_or_privileged"),
    ("Gerente", "edit_solicitation_as_owner_or_privileged"),
    ("Apoio de Coordenação", "publish_setor_solicitacao"),
    ("Assistente Administrativo", "manage_purchases_and_materials"),
    ("Assistente Administrativo", "operate_preagenda"),
    ("Assistente Administrativo", "run_daily_operations"),
)


def _migration_0125():
    return importlib.import_module("apps.core.migrations.0125_funcoes_sem_capacidade")


class TestTravas:
    def test_funcoes_zero_capacidades_banco_seed_e_funcao_dinamica(self):
        """Trava contra a função voltar a dar poder: seed, banco e grupo de função dinâmico."""
        assert not [i.codename for i in FUNCTIONAL_PERMISSIONS_SEED if set(i.group_names) & set(FUNCAO_GROUPS)]
        assert not PermissaoFuncional.objects.filter(groups__name__in=FUNCAO_GROUPS).exists()

        dinamica = Group.objects.create(name="Função Dinâmica PR8")
        GroupClassificacao.objects.create(group=dinamica, tipo=GroupClassificacao.Tipo.FUNCAO)
        setor_dinamico = Group.objects.create(name="Setor Dinâmico PR8")
        GroupClassificacao.objects.create(group=setor_dinamico, tipo=GroupClassificacao.Tipo.SETOR)
        perm = PermissaoFuncional.objects.get(codename="create_solicitation")
        perm.groups.add(dinamica, setor_dinamico, Group.objects.get(name="Coordenador"))

        _migration_0125().forwards(django_apps, None)

        assert set(perm.groups.values_list("name", flat=True)) == {"Setor Dinâmico PR8"}

    def test_reversa_recria_os_pares_e_a_capacidade(self):
        migration = _migration_0125()
        migration.forwards(django_apps, None)
        migration.backwards(django_apps, None)
        batch = PermissaoFuncional.objects.get(codename="approve_solicitation_batch")
        assert set(batch.groups.values_list("name", flat=True)) == {"Gerente", "Superintendência"}
        for grupo, codename in PARES_DO_SEED_ANTERIOR:
            assert PermissaoFuncional.objects.filter(codename=codename, groups__name=grupo).exists(), (grupo, codename)
        migration.forwards(django_apps, None)
        assert not PermissaoFuncional.objects.filter(codename="approve_solicitation_batch").exists()

    def test_seed_tem_17_itens(self):
        _validate_seed()
        assert len(FUNCTIONAL_PERMISSIONS_SEED) == 17

    def test_approve_solicitation_batch_nao_existe(self):
        assert "approve_solicitation_batch" not in {i.codename for i in FUNCTIONAL_PERMISSIONS_SEED}
        assert not PermissaoFuncional.objects.filter(codename="approve_solicitation_batch").exists()

    def test_aprovadora_g1_checa_disponibilidade(self):
        g1, _ = Gerencia.objects.get_or_create(nome="SUPERINTENDENCIA", defaults={"nome_setor": "Super"})
        aprovadora = _so_vinculo("GERENTE", g1)
        alvo = UsuarioFactory()
        inicio = timezone.now() + timedelta(days=2)
        response = _cliente(aprovadora).get(
            "/api/availability/check/",
            {"usuario_id": alvo.id, "inicio": inicio.isoformat(), "fim": (inicio + timedelta(hours=1)).isoformat()},
        )
        assert response.status_code == 200

    @pytest.mark.usefixtures("modo_uniao")  # grupo com capacidade: só vale no modo soma (PR 12)
    def test_superintendencia_sem_gerente_checa_disponibilidade(self):
        """Sem papel C/A/G: consulta por `approve_solicitation` (o batch saiu)."""
        sup = _so_aprovar()
        alvo = UsuarioFactory()
        inicio = timezone.now() + timedelta(days=2)
        client = _cliente(sup)
        check = client.get(
            "/api/availability/check/",
            {"usuario_id": alvo.id, "inicio": inicio.isoformat(), "fim": (inicio + timedelta(hours=1)).isoformat()},
        )
        assert check.status_code == 200
        varios = client.post(
            "/api/availability/check-many/",
            {"usuarios_ids": [alvo.id], "inicio": inicio.isoformat(), "fim": (inicio + timedelta(hours=1)).isoformat()},
            format="json",
        )
        assert varios.status_code == 200


# ============================================================================
# P16: deslocamento em nome do formador da gerência (GERENTE e COORDENADOR, O8-5)
# ============================================================================


def _payload_deslocamento(**extra: Any) -> dict[str, Any]:
    return {
        "origem": "Fortaleza",
        "destino": "Sobral",
        "start_date": "2026-11-10",
        "end_date": "2026-11-12",
        **extra,
    }


@pytest.fixture
def duas_gerencias():
    return GerenciaFactory(), GerenciaFactory()


class TestP16Deslocamento:
    @pytest.mark.parametrize("papel", ["GERENTE", "COORDENADOR"])
    def test_registra_edita_e_exclui_o_do_formador_da_gerencia(self, papel, duas_gerencias):
        minha, _ = duas_gerencias
        gestora = _so_vinculo(papel, minha)
        formador = _so_vinculo("FORMADOR", minha)
        client = _cliente(gestora)

        criado = client.post("/api/deslocamentos/", _payload_deslocamento(usuario=formador.id), format="json")
        assert criado.status_code == 201, criado.data
        deslocamento = Deslocamento.objects.get(pk=criado.data["id"])
        assert deslocamento.usuario_id == formador.id
        log = AuditLog.objects.get(action=AuditLog.Action.CREATE_DESLOCAMENTO, details__deslocamento_id=deslocamento.id)
        assert log.details["delegated"] is True

        editado = client.patch(f"/api/deslocamentos/{deslocamento.id}/", {"destino": "Crato"}, format="json")
        assert editado.status_code == 200, editado.data
        assert client.delete(f"/api/deslocamentos/{deslocamento.id}/").status_code == 204

    @pytest.mark.parametrize("papel", ["GERENTE", "COORDENADOR"])
    def test_recusa_formador_de_outra_gerencia(self, papel, duas_gerencias):
        minha, outra = duas_gerencias
        gestora = _so_vinculo(papel, minha)
        formador_de_fora = _so_vinculo("FORMADOR", outra)
        response = _cliente(gestora).post(
            "/api/deslocamentos/", _payload_deslocamento(usuario=formador_de_fora.id), format="json"
        )
        assert response.status_code == 403

    def test_alvo_da_gerencia_sem_vinculo_formador_recusado(self, duas_gerencias):
        minha, _ = duas_gerencias
        gerente = _so_vinculo("GERENTE", minha)
        colega = _so_vinculo("COORDENADOR", minha)
        response = _cliente(gerente).post(
            "/api/deslocamentos/", _payload_deslocamento(usuario=colega.id), format="json"
        )
        assert response.status_code == 403

    def test_apoio_segue_so_com_o_proprio(self, duas_gerencias):
        minha, _ = duas_gerencias
        apoio = _so_vinculo("APOIO", minha)
        formador = _so_vinculo("FORMADOR", minha)
        response = _cliente(apoio).post(
            "/api/deslocamentos/", _payload_deslocamento(usuario=formador.id), format="json"
        )
        assert response.status_code == 403

    def test_grupo_gerente_sem_papel_nao_delega(self, duas_gerencias):
        minha, _ = duas_gerencias
        usuario = _so_grupo("Gerente", "Coordenador")
        _vinculo(usuario, "FORMADOR", minha)
        formador = _so_vinculo("FORMADOR", minha)
        response = _cliente(usuario).post(
            "/api/deslocamentos/", _payload_deslocamento(usuario=formador.id), format="json"
        )
        assert response.status_code == 403

    def test_reatribuir_para_formador_de_outra_gerencia_da_403(self, duas_gerencias):
        minha, outra = duas_gerencias
        gerente = _so_vinculo("GERENTE", minha)
        formador = _so_vinculo("FORMADOR", minha)
        formador_de_fora = _so_vinculo("FORMADOR", outra)
        deslocamento = Deslocamento.objects.create(usuario=formador, **_payload_deslocamento())
        response = _cliente(gerente).patch(
            f"/api/deslocamentos/{deslocamento.id}/", {"usuario": formador_de_fora.id}, format="json"
        )
        assert response.status_code == 403
        deslocamento.refresh_from_db()
        assert deslocamento.usuario_id == formador.id

    def test_ve_mas_nao_edita_nem_apaga_o_do_colega_coordenador(self, duas_gerencias):
        """Trava de alvo no PATCH/DELETE: o escopo de leitura entrega o colega, a delegação não."""
        minha, _ = duas_gerencias
        gerente = _so_vinculo("GERENTE", minha)
        colega = _so_vinculo("COORDENADOR", minha)
        deslocamento = Deslocamento.objects.create(usuario=colega, **_payload_deslocamento())
        client = _cliente(gerente)

        assert client.get(f"/api/deslocamentos/{deslocamento.id}/").status_code == 200
        editado = client.patch(f"/api/deslocamentos/{deslocamento.id}/", {"destino": "Crato"}, format="json")
        assert editado.status_code == 403
        assert client.delete(f"/api/deslocamentos/{deslocamento.id}/").status_code == 403
        deslocamento.refresh_from_db()
        assert deslocamento.destino == "Sobral"

    def test_gerente_em_a_e_formador_em_b_nao_edita_o_do_formador_de_b(self, duas_gerencias):
        """Caso u91: o papel em B (FORMADOR) não delega nem dá leitura (PR 9, P9-1: 404)."""
        minha, outra = duas_gerencias
        usuario = _so_vinculo("GERENTE", minha)
        _vinculo(usuario, "FORMADOR", outra)
        formador_de_b = _so_vinculo("FORMADOR", outra)
        deslocamento = Deslocamento.objects.create(usuario=formador_de_b, **_payload_deslocamento())
        client = _cliente(usuario)

        assert client.get(f"/api/deslocamentos/{deslocamento.id}/").status_code == 404
        editado = client.patch(f"/api/deslocamentos/{deslocamento.id}/", {"destino": "Crato"}, format="json")
        assert editado.status_code == 404
        assert client.delete(f"/api/deslocamentos/{deslocamento.id}/").status_code == 404
        assert Deslocamento.objects.filter(pk=deslocamento.id, destino="Sobral").exists()

    def test_alvos_do_seletor_sao_os_formadores_das_gerencias_dela(self, duas_gerencias):
        """O seletor da tela oferece a quem pode, e só esses formadores (decisão O8-5)."""
        minha, outra = duas_gerencias
        coord = _so_vinculo("COORDENADOR", minha)
        _vinculo(coord, "FORMADOR", outra)  # formadora em outra gerência: não dá alvo lá
        formador = _so_vinculo("FORMADOR", minha)
        _so_vinculo("FORMADOR", outra)
        _so_vinculo("APOIO", minha)
        response = _cliente(coord).get("/api/deslocamentos/alvos/")
        assert response.status_code == 200
        assert [u["id"] for u in response.data] == [formador.id]

    def test_quem_delega_de_qualquer_um_ve_os_formadores_do_setor(self, duas_gerencias):
        """Ramo global do seletor (`user_delega_deslocamento_de_qualquer_um`): formador de qualquer gerência."""
        _, outra = duas_gerencias
        formador = _so_vinculo("FORMADOR", outra)
        response = _cliente(UsuarioFactory(superuser=True)).get("/api/deslocamentos/alvos/")
        assert response.status_code == 200
        assert formador.id in [u["id"] for u in response.data]

    def test_sem_delegacao_alvos_vazio(self, duas_gerencias):
        minha, _ = duas_gerencias
        apoio = _so_vinculo("APOIO", minha)
        _so_vinculo("FORMADOR", minha)
        response = _cliente(apoio).get("/api/deslocamentos/alvos/")
        assert response.status_code == 200
        assert response.data == []


# ============================================================================
# Bloqueio em nome de formador
# ============================================================================


def _payload_bloqueio(usuario_id: int | None = None) -> dict[str, Any]:
    inicio = timezone.now() + timedelta(days=1)
    payload: dict[str, Any] = {
        "tipo": "T",
        "inicio": inicio.isoformat(),
        "fim": (inicio + timedelta(hours=2)).isoformat(),
        "motivo": "Teste",
    }
    if usuario_id is not None:
        payload["usuario_id"] = usuario_id
    return payload


def _bruno() -> Usuario:
    """Controle por pacote: EQUIPE na gerência de perfil CONTROLE, sem grupo."""
    controle, _ = Gerencia.objects.get_or_create(nome="CONTROLE", defaults={"nome_setor": "Controle"})
    controle.perfil = Gerencia.Perfil.CONTROLE
    controle.save()
    return _so_vinculo("EQUIPE", controle)


class TestBloqueioDelegado:
    def test_controle_por_pacote_cria_edita_apaga_bloqueio_alheio(self):
        bruno = _bruno()
        formador = _so_vinculo("FORMADOR")
        client = _cliente(bruno)
        criado = client.post("/api/availability-blocks/", _payload_bloqueio(formador.id), format="json")
        assert criado.status_code == 201, criado.data
        bloco = AvailabilityBlock.objects.get(pk=criado.data["id"])
        assert bloco.usuario_id == formador.id
        editado = client.patch(f"/api/availability-blocks/{bloco.id}/", {"motivo": "Outro"}, format="json")
        assert editado.status_code == 200, editado.data
        assert client.delete(f"/api/availability-blocks/{bloco.id}/").status_code == 204

    def test_assistente_adm_sem_controle_nao_delega(self):
        """Bloqueio e deslocamento: a função Assistente Administrativo sozinha não dá poder."""
        assistente = _so_grupo("Assistente Administrativo")
        formador = _so_vinculo("FORMADOR")
        client = _cliente(assistente)
        bloqueio = client.post("/api/availability-blocks/", _payload_bloqueio(formador.id), format="json")
        assert bloqueio.status_code == 403
        deslocamento = client.post("/api/deslocamentos/", _payload_deslocamento(usuario=formador.id), format="json")
        assert deslocamento.status_code == 403

    def test_alvo_sem_vinculo_formador_recusado(self):
        alvo = _so_grupo("Formador")
        response = _cliente(UsuarioFactory(superuser=True)).post(
            "/api/availability-blocks/", _payload_bloqueio(alvo.id), format="json"
        )
        assert response.status_code == 400
        assert "usuario_id" in str(response.data)

    def test_alvo_formador_em_gerencia_inativa_recusado(self):
        alvo = _so_vinculo("FORMADOR", GerenciaFactory(ativo=False))
        response = _cliente(UsuarioFactory(superuser=True)).post(
            "/api/availability-blocks/", _payload_bloqueio(alvo.id), format="json"
        )
        assert response.status_code == 400
        assert "usuario_id" in str(response.data)

    def test_alvo_com_vinculo_sem_grupo_aceito(self):
        alvo = _so_vinculo("FORMADOR")
        response = _cliente(UsuarioFactory(superuser=True)).post(
            "/api/availability-blocks/", _payload_bloqueio(alvo.id), format="json"
        )
        assert response.status_code == 201, response.data


# ============================================================================
# Telas, coordenador padrão, lookup, dashboard e cache
# ============================================================================


class TestTelasPadraoECache:
    def test_tela_bloqueios_abre_por_vinculo_formador(self):
        policies = resolve_public_policies(_so_vinculo("FORMADOR"))
        assert "access_availability_blocks" in policies
        assert "access_monthly_availability" not in policies
        assert "access_travel" not in policies

    def test_grupo_formador_sem_vinculo_nao_abre(self):
        assert "access_availability_blocks" not in resolve_public_policies(_so_grupo("Formador"))

    @pytest.mark.parametrize("grupo", ["Gerente", "Coordenador", "Apoio de Coordenação"])
    def test_grupo_de_funcao_sem_papel_nao_abre_grade_nem_deslocamentos(self, grupo):
        policies = resolve_public_policies(_so_grupo(grupo))
        assert "access_monthly_availability" not in policies
        assert "access_travel" not in policies

    def test_coordenador_padrao_vem_do_vinculo(self):
        coord = _so_vinculo("COORDENADOR")
        response = _cria(coord)
        assert response.status_code == 201, response.data
        assert response.data["coordenador"] == coord.id

    def test_grupo_coordenador_sem_vinculo_nao_vira_coordenador_padrao(self):
        """Pode criar pelo papel GERENTE; o grupo Coordenador sem o vínculo não o faz coordenador padrão."""
        gerente = _so_grupo("Coordenador")
        _vinculo(gerente, "GERENTE")
        response = _cria(gerente)
        assert response.status_code == 400
        assert "coordenador" in str(response.data)

    def test_apoio_por_vinculo_nao_vira_coordenador_padrao(self):
        """Só o papel COORDENADOR vira coordenador responsável por padrão; a APOIO cria, mas escolhe."""
        response = _cria(_so_vinculo("APOIO"))
        assert response.status_code == 400
        assert "coordenador" in str(response.data)

    def test_lookup_role_ignora_vinculo_em_gerencia_inativa(self):
        inativa = _so_vinculo("COORDENADOR", GerenciaFactory(ativo=False))
        ativa = _so_vinculo("COORDENADOR")
        response = _cliente(UsuarioFactory(superuser=True)).get("/api/lookup/usuarios/", {"role": "Coordenador"})
        assert response.status_code == 200
        ids = {item["id"] for item in response.data}
        assert ativa.id in ids
        assert inativa.id not in ids

    def test_lookup_role_coordenador_por_vinculo(self):
        por_vinculo = _so_vinculo("COORDENADOR")
        so_grupo = _so_grupo("Coordenador")
        response = _cliente(UsuarioFactory(superuser=True)).get("/api/lookup/usuarios/", {"role": "Coordenador"})
        assert response.status_code == 200
        ids = {item["id"] for item in response.data}
        assert por_vinculo.id in ids
        assert so_grupo.id not in ids

    def test_stats_is_formador_only_por_papel(self):
        """Grupo Formador + papel COORDENADOR vigente: não é "só formadora", vê os eventos da gerência."""
        gerencia = GerenciaFactory()
        usuario = UsuarioFactory(groups=["Formador"], groups__gerencia=gerencia)
        _vinculo(usuario, "COORDENADOR", gerencia)
        SolicitacaoFactory(
            projeto=ProjetoFactory(gerencia=gerencia),
            status="aprovado",
            inicio=timezone.now() + timedelta(days=5),
            fim=timezone.now() + timedelta(days=5, hours=2),
        )
        response = _cliente(usuario).get("/api/stats/home/")
        assert response.status_code == 200
        assert response.data["upcoming_events"] == 1

    def test_snapshot_e_me_refletem_direitos_do_papel(self):
        apoio = _so_vinculo("APOIO")
        me = _cliente(apoio).get("/api/me/").json()
        esperado = CRIAR_E_EDITAR | {"publish_setor_solicitacao"}
        assert esperado <= set(me["permissions"])
        retrato = snapshot_de_poder(Usuario.objects.filter(id=apoio.id))[f"u{apoio.id}"]
        assert esperado <= set(retrato["capacidades"])
        assert "publish_setor_solicitacao" in retrato["policies"]

    def test_cache_invalida_ao_encerrar_vinculo(self, django_capture_on_commit_callbacks):
        coord = UsuarioFactory()
        vinculo = _vinculo(coord, "COORDENADOR")
        assert CRIAR_E_EDITAR <= get_user_functional_permissions(coord)  # aquece o cache
        with django_capture_on_commit_callbacks(execute=True):
            vinculo.valid_to = timezone.localdate() - timedelta(days=1)
            vinculo.save()
        assert not CRIAR_E_EDITAR & get_user_functional_permissions(coord)
