"""
PR 9 das permissões (16/10/2026): cada pessoa vê e mexe só na gerência onde tem o papel certo.

Plano: `liberacao/relatorios/plano_permissoes_PR8_PR9_2026-10-15.md`, seção "PR 9". O alcance é a
gerência do PROJETO (`projeto.gerencia_id`), não o texto do setor, e cada superfície conta só o papel
vigente certo em gerência ativa (`EquipeGerencia.gerencias_com_papel`). Falta de dado nega.

Decisões do dono de 15/10:
- P9-5: num evento da gerência A só entram pessoas da A (o filtro é a gerência do projeto do evento,
  não a união das gerências de quem cria). Caso real: GERENTE em uma gerência e FORMADOR em outra.
- P9-1: a formadora vê só os próprios bloqueios e deslocamentos. Gerente, coordenadora e apoio veem
  os da gerência pelo papel; Controle, DAT e globais veem tudo.
- Ajuste da análise de impacto: o projeto só é checado quando MUDA (a tela Editar manda o projeto em
  todo salvamento).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportOptionalMemberAccess=false, reportIndexIssue=false, reportGeneralTypeIssues=false

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import AvailabilityBlock, Deslocamento, EquipeGerencia, Gerencia, Solicitacao, Usuario
from apps.core.services import solicitacao_scope
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


@pytest.fixture(autouse=True)
def _cache_limpo():
    cache.clear()
    yield
    cache.clear()


def _cliente(usuario: Usuario) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=usuario)
    return client


def _vinculo(usuario: Usuario, papel: str, gerencia: Gerencia) -> EquipeGerencia:
    """Só o vínculo vigente (sem grupo de função): o papel na gerência."""
    dados: dict[str, Any] = {"ativo": True, "valid_from": date(2000, 1, 1)}
    if papel == "APOIO":
        supervisor = UsuarioFactory()
        EquipeGerencia.objects.create(gerencia=gerencia, usuario=supervisor, papel="COORDENADOR", **dados)
        dados["coordenador_supervisor"] = supervisor
    return EquipeGerencia.objects.create(gerencia=gerencia, usuario=usuario, papel=papel, **dados)


def _pessoa(*vinculos: tuple[str, Gerencia]) -> Usuario:
    usuario = UsuarioFactory()
    for papel, gerencia in vinculos:
        _vinculo(usuario, papel, gerencia)
    return usuario


def _ids(response) -> set[int]:
    dados = response.data
    if isinstance(dados, dict) and "results" in dados:
        dados = dados["results"]
    return {item["id"] for item in dados}


def _erros(response) -> dict[str, Any]:
    """Campos com erro de um 400 (o handler embrulha em `errors`)."""
    return response.data.get("errors", response.data)


def _projeto(gerencia: Gerencia | None, **extra: Any):
    return ProjetoFactory(gerencia=gerencia, fluxo="NAO_SUPER", **extra)


def _payload(projeto, **extra: Any) -> dict[str, Any]:
    municipio = MunicipioFactory()
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


def _cria(usuario: Usuario, projeto, **extra: Any):
    return _cliente(usuario).post("/api/solicitacoes/", _payload(projeto, **extra), format="json")


@pytest.fixture
def a_b():
    """Duas gerências ativas: A (onde a pessoa gere) e B (onde ela só é formadora)."""
    return GerenciaFactory(), GerenciaFactory()


@pytest.fixture
def u91(a_b):
    """Persona do caso real: GERENTE em A; FORMADOR em A e em B."""
    a, b = a_b
    return _pessoa(("GERENTE", a), ("FORMADOR", a), ("FORMADOR", b))


# ============================================================================
# GERENTE em A, FORMADOR em B (u91; C9 da auditoria de segurança)
# ============================================================================


class TestGerenteEmAFormadorEmB:
    def test_c9_nao_ve_edita_exclui_alheia_de_B(self, a_b, u91):
        _, b = a_b
        alheia = SolicitacaoFactory(projeto=_projeto(b))
        cliente = _cliente(u91)
        assert alheia.id not in _ids(cliente.get("/api/solicitacoes/"))
        assert cliente.patch(f"/api/solicitacoes/{alheia.id}/", {"local": "x"}, format="json").status_code == 404
        assert cliente.delete(f"/api/solicitacoes/{alheia.id}/").status_code == 404

    def test_c9_continua_gestora_em_A(self, a_b, u91):
        a, _ = a_b
        alheia = SolicitacaoFactory(projeto=_projeto(a), local="Antes")
        cliente = _cliente(u91)
        assert alheia.id in _ids(cliente.get("/api/solicitacoes/"))
        response = cliente.patch(f"/api/solicitacoes/{alheia.id}/", {"local": "Depois"}, format="json")
        assert response.status_code == 200, response.data

    def test_c9_nao_cria_em_projeto_de_B(self, a_b, u91):
        _, b = a_b
        coord_b = _pessoa(("COORDENADOR", b))
        response = _cria(u91, _projeto(b), coordenador=coord_b.id)
        assert response.status_code == 400
        assert "projeto" in _erros(response)

    def test_c9_cria_em_projeto_de_A(self, a_b, u91):
        a, _ = a_b
        coord_a = _pessoa(("COORDENADOR", a))
        response = _cria(u91, _projeto(a), coordenador=coord_a.id)
        assert response.status_code == 201, response.data

    def test_c9_aparece_como_participante_em_B(self, a_b, u91):
        _, b = a_b
        coord_b = _pessoa(("COORDENADOR", b))
        response = _cria(coord_b, _projeto(b), extra_participants={"formador_ids": [u91.id]})
        assert response.status_code == 201, response.data

    def test_c9_opcoes_formadores_sem_B(self, a_b, u91):
        a, b = a_b
        formador_a = _pessoa(("FORMADOR", a))
        formador_b = _pessoa(("FORMADOR", b))
        ids = _ids(_cliente(u91).get("/api/options/formadores-do-setor/"))
        assert formador_a.id in ids
        assert formador_b.id not in ids

    def test_c9_dashboard_sem_B(self, a_b, u91):
        a, b = a_b
        futuro = timezone.now() + timedelta(days=5)
        for gerencia in (a, b):
            SolicitacaoFactory(
                projeto=_projeto(gerencia), status="aprovado", inicio=futuro, fim=futuro + timedelta(hours=2)
            )
        response = _cliente(u91).get("/api/stats/home/")
        assert response.status_code == 200
        assert response.data["upcoming_events"] == 1

    def test_c9_grade_de_B_403_e_de_A_200(self, a_b, u91):
        a, b = a_b
        base = "/api/availability/monthly/?year=2026&month=11&role=FORMADOR"
        cliente = _cliente(u91)
        assert cliente.get(f"{base}&gerencia_id={a.id}").status_code == 200
        assert cliente.get(f"{base}&gerencia_id={b.id}").status_code == 403

    def test_c9_edita_a_propria_de_B_sem_trocar_projeto(self, a_b, u91):
        """Ajuste da análise de impacto (grupo 3): a tela Editar manda o mesmo projeto em todo salvamento."""
        _, b = a_b
        projeto_b = _projeto(b)
        propria = SolicitacaoFactory(usuario=u91, projeto=projeto_b, local="Antes")
        response = _cliente(u91).patch(
            f"/api/solicitacoes/{propria.id}/", {"local": "Depois", "projeto": projeto_b.id}, format="json"
        )
        assert response.status_code == 200, response.data

    def test_c9_nao_move_a_propria_para_outro_projeto_de_B(self, a_b, u91):
        _, b = a_b
        propria = SolicitacaoFactory(usuario=u91, projeto=_projeto(b))
        outro = _projeto(b)
        liberar_par(propria.municipio, outro)
        response = _cliente(u91).patch(f"/api/solicitacoes/{propria.id}/", {"projeto": outro.id}, format="json")
        assert response.status_code == 400
        assert "projeto" in _erros(response)

    def test_c9_nao_poe_participante_na_propria_de_B(self, a_b, u91):
        _, b = a_b
        propria = SolicitacaoFactory(usuario=u91, projeto=_projeto(b))
        formador_b = _pessoa(("FORMADOR", b))
        response = _cliente(u91).patch(
            f"/api/solicitacoes/{propria.id}/",
            {"extra_participants": {"formador_ids": [formador_b.id]}},
            format="json",
        )
        assert response.status_code == 400
        assert "extra_participants" in _erros(response)


# ============================================================================
# P9-5: o evento da gerência A só aceita pessoas da A
# ============================================================================


@pytest.fixture
def coord_a_e_b(a_b):
    a, b = a_b
    return _pessoa(("COORDENADOR", a), ("COORDENADOR", b))


class TestGerenciaDoProjeto:
    def test_participante_de_B_em_evento_de_A_400(self, a_b, coord_a_e_b):
        a, b = a_b
        formador_b = _pessoa(("FORMADOR", b))
        response = _cria(
            coord_a_e_b,
            _projeto(a),
            extra_participants={"formador_ids": [formador_b.id]},
        )
        assert response.status_code == 400
        assert "extra_participants" in _erros(response)

    def test_participante_de_A_em_evento_de_A_201(self, a_b, coord_a_e_b):
        a, _ = a_b
        formador_a = _pessoa(("FORMADOR", a))
        response = _cria(
            coord_a_e_b,
            _projeto(a),
            extra_participants={"formador_ids": [formador_a.id]},
        )
        assert response.status_code == 201, response.data

    def test_coordenador_responsavel_de_B_em_evento_de_A_400(self, a_b):
        a, b = a_b
        gerente = _pessoa(("GERENTE", a), ("GERENTE", b))
        coord_b = _pessoa(("COORDENADOR", b))
        response = _cria(gerente, _projeto(a), coordenador=coord_b.id)
        assert response.status_code == 400
        assert "coordenador" in _erros(response)

    def test_lookup_de_usuarios_com_projeto_so_traz_a_gerencia_do_projeto(self, a_b, coord_a_e_b):
        a, b = a_b
        formador_a = _pessoa(("FORMADOR", a))
        formador_b = _pessoa(("FORMADOR", b))
        projeto_a = _projeto(a)
        ids = _ids(_cliente(coord_a_e_b).get(f"/api/lookup/usuarios/?role=Formador&projeto_id={projeto_a.id}"))
        assert formador_a.id in ids
        assert formador_b.id not in ids

    def test_trocar_projeto_e_participante_no_mesmo_patch_usa_o_projeto_novo(self, a_b, coord_a_e_b):
        a, b = a_b
        propria = SolicitacaoFactory(usuario=coord_a_e_b, projeto=_projeto(a), coordenador=coord_a_e_b)
        coord_b = _pessoa(("COORDENADOR", b))
        projeto_b = _projeto(b)
        liberar_par(propria.municipio, projeto_b)
        response = _cliente(coord_a_e_b).patch(
            f"/api/solicitacoes/{propria.id}/", {"projeto": projeto_b.id, "coordenador": coord_b.id}, format="json"
        )
        assert response.status_code == 200, response.data


# ============================================================================
# Coordenador responsável: só quem tem o papel COORDENADOR na gerência do projeto
# ============================================================================


class TestCoordenadorResponsavel:
    def test_formadora_como_responsavel_400(self, a_b):
        a, _ = a_b
        gerente = _pessoa(("GERENTE", a))
        formadora = _pessoa(("FORMADOR", a))
        response = _cria(gerente, _projeto(a), coordenador=formadora.id)
        assert response.status_code == 400
        assert "coordenador" in _erros(response)

    def test_coordenadora_da_gerencia_como_responsavel_201(self, a_b):
        a, _ = a_b
        gerente = _pessoa(("GERENTE", a))
        coordenadora = _pessoa(("COORDENADOR", a))
        response = _cria(gerente, _projeto(a), coordenador=coordenadora.id)
        assert response.status_code == 201, response.data


# ============================================================================
# Publicação no Google (ramo Apoio) e gerências
# ============================================================================


class TestPublicacaoEGerencias:
    def test_apoio_em_A_coordenador_em_B_nao_publica_em_B(self, a_b):
        a, b = a_b
        pessoa = _pessoa(("APOIO", a), ("COORDENADOR", b))
        aprovada_a = SolicitacaoFactory(projeto=_projeto(a), status="aprovado")
        aprovada_b = SolicitacaoFactory(projeto=_projeto(b), status="aprovado")
        assert solicitacao_scope.can_publish_solicitacao(pessoa, aprovada_a) is True
        assert solicitacao_scope.can_publish_solicitacao(pessoa, aprovada_b) is False
        publicaveis = set(
            solicitacao_scope.scope_publishable_solicitacoes(Solicitacao.objects.all(), pessoa).values_list(
                "id", flat=True
            )
        )
        assert publicaveis == {aprovada_a.id}
        vistas = set(
            solicitacao_scope.scope_solicitacoes(Solicitacao.objects.all(), pessoa).values_list("id", flat=True)
        )
        assert vistas == {aprovada_a.id}
        assert solicitacao_scope.has_publish_scope(pessoa) is True

    def test_coordenadora_sem_apoio_nao_tem_escopo_de_publicacao(self, a_b):
        a, _ = a_b
        assert solicitacao_scope.has_publish_scope(_pessoa(("COORDENADOR", a))) is False

    def test_duas_gerencias_mesmo_setor_canonico_nao_compartilham(self):
        """D5: o setor é texto; duas gerências do mesmo setor são escopos distintos."""
        g1 = GerenciaFactory(setor_canonico="Vidas")
        g2 = GerenciaFactory(setor_canonico="Vidas")
        coord = _pessoa(("COORDENADOR", g1))
        projeto_g2 = _projeto(g2, setor="Vidas")
        response = _cria(coord, projeto_g2)
        assert response.status_code == 400
        assert "projeto" in _erros(response)
        ids = _ids(_cliente(coord).get("/api/lookup/projetos/"))
        assert projeto_g2.id not in ids

    def test_gerencia_inativa_nao_da_escopo(self, a_b):
        a, b = a_b
        gerente = _pessoa(("GERENTE", a), ("GERENTE", b))
        Gerencia.objects.filter(pk=b.pk).update(ativo=False)
        alheia_a = SolicitacaoFactory(projeto=_projeto(a))
        alheia_b = SolicitacaoFactory(projeto=_projeto(b))
        ids = _ids(_cliente(gerente).get("/api/solicitacoes/"))
        assert alheia_a.id in ids
        assert alheia_b.id not in ids


# ============================================================================
# Fail-closed
# ============================================================================


class TestFailClosed:
    def test_projeto_sem_gerencia_fail_closed(self, a_b):
        a, _ = a_b
        coord = _pessoa(("COORDENADOR", a))
        sem_gerencia = _projeto(None)
        response = _cria(coord, sem_gerencia)
        assert response.status_code == 400
        assert "projeto" in _erros(response)
        assert sem_gerencia.id not in _ids(_cliente(coord).get("/api/lookup/projetos/"))

    def test_criador_sem_vinculo_CAG_fail_closed(self, a_b):
        a, _ = a_b
        formadora = _pessoa(("FORMADOR", a))
        _projeto(a)
        _pessoa(("FORMADOR", a))
        from apps.core.models import Projeto

        assert not solicitacao_scope.scope_projetos_por_gerencia(Projeto.objects.all(), formadora).exists()
        assert not solicitacao_scope.scope_usuarios_por_gerencia(Usuario.objects.all(), formadora).exists()

    def test_sem_vinculo_CAG_edita_propria_mas_nao_troca_projeto(self, a_b):
        a, _ = a_b
        formadora = _pessoa(("FORMADOR", a))
        projeto = _projeto(a)
        propria = SolicitacaoFactory(usuario=formadora, projeto=projeto, local="Antes")
        cliente = _cliente(formadora)
        response = cliente.patch(
            f"/api/solicitacoes/{propria.id}/", {"local": "Depois", "projeto": projeto.id}, format="json"
        )
        assert response.status_code == 200, response.data
        outro = _projeto(a)
        liberar_par(propria.municipio, outro)
        response = cliente.patch(f"/api/solicitacoes/{propria.id}/", {"projeto": outro.id}, format="json")
        assert response.status_code == 400
        assert "projeto" in _erros(response)


# ============================================================================
# Grade e opções de formador
# ============================================================================


class TestGradeEOpcoes:
    def test_grade_api_formador_sem_gestao_403(self, a_b):
        a, _ = a_b
        formador = _pessoa(("FORMADOR", a))
        base = "/api/availability/monthly/?year=2026&month=11&role=FORMADOR"
        cliente = _cliente(formador)
        assert cliente.get(base).status_code == 403
        assert cliente.get(f"{base}&gerencia_id={a.id}").status_code == 403

    def test_grade_api_coordenadora_200(self, a_b):
        a, _ = a_b
        coord = _pessoa(("COORDENADOR", a))
        base = "/api/availability/monthly/?year=2026&month=11&role=FORMADOR"
        cliente = _cliente(coord)
        assert cliente.get(base).status_code == 200
        assert cliente.get(f"{base}&gerencia_id={a.id}").status_code == 200

    def test_opcoes_formadores_global_controle(self, a_b):
        a, b = a_b
        controle, _ = Gerencia.objects.get_or_create(nome="CONTROLE", defaults={"nome_setor": "Controle"})
        controle.perfil = Gerencia.Perfil.CONTROLE
        controle.save()
        operador = _pessoa(("EQUIPE", controle))
        formador_a = _pessoa(("FORMADOR", a))
        formador_b = _pessoa(("FORMADOR", b))
        ids = _ids(_cliente(operador).get("/api/options/formadores-do-setor/"))
        assert {formador_a.id, formador_b.id} <= ids

    def test_opcoes_formadores_formadora_sem_gestao_vazia(self, a_b):
        a, _ = a_b
        formadora = _pessoa(("FORMADOR", a))
        _pessoa(("FORMADOR", a))
        response = _cliente(formadora).get("/api/options/formadores-do-setor/")
        assert response.status_code == 200
        assert response.data == []


# ============================================================================
# P9-1: a formadora vê só os próprios bloqueios e deslocamentos
# ============================================================================


def _bloqueio(usuario: Usuario) -> AvailabilityBlock:
    inicio = timezone.now() + timedelta(days=2)
    return AvailabilityBlock.objects.create(
        usuario=usuario, created_by=usuario, inicio=inicio, fim=inicio + timedelta(hours=2), status="aprovado"
    )


def _deslocamento(usuario: Usuario) -> Deslocamento:
    return Deslocamento.objects.create(
        usuario=usuario,
        origem="Fortaleza",
        destino="Sobral",
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 12),
    )


class TestBloqueiosEDeslocamentosP91:
    def test_formadora_ve_so_os_proprios_bloqueios(self, a_b):
        a, _ = a_b
        formadora, colega = _pessoa(("FORMADOR", a)), _pessoa(("FORMADOR", a))
        meu, do_colega = _bloqueio(formadora), _bloqueio(colega)
        ids = _ids(_cliente(formadora).get("/api/availability-blocks/"))
        assert meu.id in ids
        assert do_colega.id not in ids

    def test_coordenadora_ve_os_bloqueios_da_gerencia(self, a_b):
        a, _ = a_b
        coord, formadora = _pessoa(("COORDENADOR", a)), _pessoa(("FORMADOR", a))
        do_formador = _bloqueio(formadora)
        assert do_formador.id in _ids(_cliente(coord).get("/api/availability-blocks/"))

    def test_formadora_ve_so_os_proprios_deslocamentos(self, a_b):
        a, _ = a_b
        formadora, colega = _pessoa(("FORMADOR", a)), _pessoa(("FORMADOR", a))
        meu, do_colega = _deslocamento(formadora), _deslocamento(colega)
        ids = _ids(_cliente(formadora).get("/api/deslocamentos/"))
        assert meu.id in ids
        assert do_colega.id not in ids

    def test_coordenadora_ve_os_deslocamentos_da_gerencia(self, a_b):
        a, _ = a_b
        coord, formadora = _pessoa(("COORDENADOR", a)), _pessoa(("FORMADOR", a))
        do_formador = _deslocamento(formadora)
        assert do_formador.id in _ids(_cliente(coord).get("/api/deslocamentos/"))

    def test_gerente_em_A_nao_ve_os_de_B_onde_e_formadora(self, a_b, u91):
        _, b = a_b
        colega_b = _pessoa(("FORMADOR", b))
        bloqueio, deslocamento = _bloqueio(colega_b), _deslocamento(colega_b)
        cliente = _cliente(u91)
        assert bloqueio.id not in _ids(cliente.get("/api/availability-blocks/"))
        assert deslocamento.id not in _ids(cliente.get("/api/deslocamentos/"))
