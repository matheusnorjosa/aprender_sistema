"""
S2 / C3 (auditoria de segurança 14/10/2026) — editar uma SUPER aprovada exige nova aprovação.

Decisão do dono (14/10/2026): uma solicitação de fluxo SUPER **aprovada** volta para **pendente**
quando mudar data, horário (início ou fim), município ou formadores. Observação, local exato e
evento online não voltam. É a mesma regra do M10-02 (#1624, troca de projeto), estendida: a
aprovação da Superintendência (CP-02/PA-01) vale para o evento aprovado, não para outro que o
editor monte depois.

Contrato:
- SUPER aprovada + campo material mudou → `pendente`, com AuditLog(UPDATE) do editor mostrando
  `status` aprovado→pendente e `details.reaprovacao.campos` com o que mudou;
- campo não material, mesmo valor reenviado, NAO_SUPER e pendente → status não muda;
- vale para qualquer editor (dono, DAT, Controle).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

from datetime import timedelta
from zoneinfo import ZoneInfo

from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog, Participation
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


@pytest.fixture
def gerencia():
    """Gerência do projeto SUPER, do coordenador e dos formadores (PR 9: escopo pela gerência do projeto)."""
    return GerenciaFactory()


@pytest.fixture
def coordenador(gerencia):
    return UsuarioFactory(groups=["Coordenador"], groups__gerencia=gerencia)


@pytest.fixture
def formadores(gerencia):
    return [UsuarioFactory(groups=["Formador"], groups__gerencia=gerencia) for _ in range(3)]


@pytest.fixture
def municipio():
    return MunicipioFactory(nome="Municipio Reaprovacao", uf="CE", ativo=True)


@pytest.fixture
def projeto_super(municipio, gerencia):
    projeto = ProjetoFactory(nome="Super Reaprovacao", fluxo="SUPER", gerencia=gerencia)
    liberar_par(municipio, projeto)
    return projeto


@pytest.fixture
def projeto_nao_super(municipio):
    projeto = ProjetoFactory(nome="NaoSuper Reaprovacao", fluxo="NAO_SUPER")
    liberar_par(municipio, projeto)
    return projeto


def _solicitacao(coordenador, municipio, projeto, formadores, status="aprovado"):
    inicio = (timezone.now() + timedelta(days=10)).replace(hour=12, minute=0, second=0, microsecond=0)
    sol = SolicitacaoFactory(
        usuario=coordenador,
        coordenador=coordenador,
        municipio=municipio,
        projeto=projeto,
        tipo_evento=TipoEventoFactory(nome="Formacao Reaprovacao"),
        inicio=inicio,
        fim=inicio + timedelta(hours=3),
        status=status,
        observacoes="obs original",
        local="Escola A",
    )
    Participation.objects.create(solicitacao=sol, usuario=coordenador, role="COORDENADOR")
    for formador in formadores:
        Participation.objects.create(solicitacao=sol, usuario=formador, role="FORMADOR")
    return sol


def _client(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def _patch(user, sol, payload):
    resp = _client(user).patch(f"/api/solicitacoes/{sol.id}/", payload, format="json")
    assert resp.status_code == 200, resp.data
    sol.refresh_from_db()
    return resp


def _ultimo_log(sol):
    return AuditLog.objects.filter(action="UPDATE", model_name="Solicitacao", details__solicitacao_id=sol.id).latest(
        "created_at"
    )


def _payload_material(nome, sol, formadores):
    """Payload que muda UM campo material. `formadores[0]` está no evento; os outros não."""
    if nome == "data":
        return {
            "inicio": (sol.inicio + timedelta(days=1)).isoformat(),
            "fim": (sol.fim + timedelta(days=1)).isoformat(),
        }
    if nome == "hora_inicio":
        return {"inicio": (sol.inicio - timedelta(hours=1)).isoformat()}
    if nome == "hora_fim":
        return {"fim": (sol.fim + timedelta(hours=1)).isoformat()}
    if nome == "municipio":
        outro = MunicipioFactory(nome="Outro Municipio Reaprovacao", uf="CE", ativo=True)
        liberar_par(outro, sol.projeto)
        return {"municipio": outro.id}
    if nome == "formador_adicionado":
        return {"extra_participants": {"formador_ids": [formadores[0].id, formadores[1].id]}}
    if nome == "formador_removido":
        return {"extra_participants": {"formador_ids": []}}
    if nome == "formador_trocado":
        return {"extra_participants": {"formador_ids": [formadores[2].id]}}
    raise AssertionError(nome)


_CAMPO_ESPERADO = {
    "data": {"inicio", "fim"},
    "hora_inicio": {"inicio"},
    "hora_fim": {"fim"},
    "municipio": {"municipio"},
    "formador_adicionado": {"formadores"},
    "formador_removido": {"formadores"},
    "formador_trocado": {"formadores"},
}


class TestCampoMaterialRebaixaSuperAprovada:
    @pytest.mark.parametrize("campo", list(_CAMPO_ESPERADO))
    def test_dono_muda_campo_material_volta_para_pendente(
        self, campo, coordenador, municipio, projeto_super, formadores
    ):
        sol = _solicitacao(coordenador, municipio, projeto_super, [formadores[0]])

        _patch(coordenador, sol, _payload_material(campo, sol, formadores))

        assert sol.status == "pendente"
        log = _ultimo_log(sol)
        assert log.usuario_id == coordenador.id
        assert log.details["changed_fields"]["status"] == {"old": "aprovado", "new": "pendente"}
        assert set(log.details["reaprovacao"]["campos"]) == _CAMPO_ESPERADO[campo]

    @pytest.mark.parametrize("setor", ["DAT", "Controle"])
    @pytest.mark.parametrize("campo", ["data", "municipio", "formador_trocado"])
    def test_editor_global_muda_campo_material_tambem_rebaixa(
        self, setor, campo, coordenador, municipio, projeto_super, formadores
    ):
        """Quem edita a solicitação alheia (DAT, Controle) passa pela mesma regra."""
        editor = UsuarioFactory(groups=["Gerente", setor])
        sol = _solicitacao(coordenador, municipio, projeto_super, [formadores[0]])

        _patch(editor, sol, _payload_material(campo, sol, formadores))

        assert sol.status == "pendente"
        log = _ultimo_log(sol)
        assert log.usuario_id == editor.id
        assert log.details["changed_fields"]["status"] == {"old": "aprovado", "new": "pendente"}


class TestEdicaoQueNaoRebaixa:
    @pytest.mark.parametrize(
        "payload",
        [
            pytest.param({"observacoes": "obs nova"}, id="observacao"),
            pytest.param({"local": "Escola B"}, id="local"),
            pytest.param({"is_online": True}, id="online"),
        ],
    )
    def test_campo_nao_material_mantem_aprovada(self, payload, coordenador, municipio, projeto_super, formadores):
        sol = _solicitacao(coordenador, municipio, projeto_super, [formadores[0]])

        _patch(coordenador, sol, payload)

        assert sol.status == "aprovado"
        assert "reaprovacao" not in _ultimo_log(sol).details

    @pytest.mark.parametrize(
        "campo",
        ["coordenador", "tipo_evento", "coordenador_acompanha", "encontro", "segmento"],
    )
    def test_outros_campos_mantem_aprovada(self, campo, coordenador, municipio, projeto_super, formadores):
        """Decisão do dono: só projeto, data, horário, município e formadores são materiais."""
        sol = _solicitacao(coordenador, municipio, projeto_super, [formadores[0]])
        if campo == "coordenador":
            valor = UsuarioFactory(groups=["Coordenador"], groups__gerencia=projeto_super.gerencia).id
        elif campo == "tipo_evento":
            valor = TipoEventoFactory(nome="Outro Tipo Reaprovacao").id
        elif campo == "coordenador_acompanha":
            valor = not sol.coordenador_acompanha
        else:
            valor = f"{campo} novo"

        _patch(coordenador, sol, {campo: valor})

        log = _ultimo_log(sol)
        assert {campo, f"{campo}_id"} & log.details["changed_fields"].keys()  # a edição gravou
        assert sol.status == "aprovado"
        assert "reaprovacao" not in log.details

    def test_reenviar_mesmos_valores_mantem_aprovada(self, coordenador, municipio, projeto_super, formadores):
        """A tela manda tudo em todo salvar: mesmo instante em outro fuso e a mesma lista não são mudança."""
        sol = _solicitacao(coordenador, municipio, projeto_super, [formadores[0]])
        fortaleza = ZoneInfo("America/Fortaleza")

        _patch(
            coordenador,
            sol,
            {
                "projeto": projeto_super.id,
                "municipio": municipio.id,
                "inicio": sol.inicio.astimezone(fortaleza).isoformat(),
                "fim": sol.fim.astimezone(fortaleza).isoformat(),
                "observacoes": "obs nova",
                "extra_participants": {"formador_ids": [formadores[0].id]},
            },
        )

        assert sol.status == "aprovado"

    def test_nao_super_aprovada_nao_muda(self, coordenador, municipio, projeto_nao_super, formadores):
        sol = _solicitacao(coordenador, municipio, projeto_nao_super, [formadores[0]])

        _patch(coordenador, sol, _payload_material("data", sol, formadores))

        assert sol.status == "aprovado"

    def test_aprovada_sem_projeto_nao_muda(self, coordenador, municipio, formadores):
        """Sem projeto o fluxo é NAO_SUPER (`get_fluxo`): mudar data não pede aprovação."""
        sol = _solicitacao(coordenador, municipio, None, [formadores[0]])

        _patch(coordenador, sol, _payload_material("hora_fim", sol, formadores))

        assert sol.status == "aprovado"
        assert "reaprovacao" not in _ultimo_log(sol).details

    def test_tirar_o_projeto_da_super_aprovada_rebaixa(self, coordenador, municipio, projeto_super, formadores):
        """M10-02 como na main: o projeto mudou e o fluxo novo (sem projeto) não é NAO_SUPER."""
        sol = _solicitacao(coordenador, municipio, projeto_super, [formadores[0]])

        _patch(coordenador, sol, {"projeto": None})

        assert sol.status == "pendente"
        assert _ultimo_log(sol).details["reaprovacao"]["campos"] == ["projeto"]

    def test_super_pendente_continua_pendente(self, coordenador, municipio, projeto_super, formadores):
        sol = _solicitacao(coordenador, municipio, projeto_super, [formadores[0]], status="pendente")

        _patch(coordenador, sol, _payload_material("formador_trocado", sol, formadores))

        assert sol.status == "pendente"
        assert "reaprovacao" not in _ultimo_log(sol).details

    def test_rebaixamento_nao_mexe_no_google_agenda(self, coordenador, municipio, projeto_super, formadores):
        """Como no M10-02: o rebaixamento só troca o status. Publicada nem chega aqui (400 no serializer)."""
        sol = _solicitacao(coordenador, municipio, projeto_super, [formadores[0]])

        _patch(coordenador, sol, _payload_material("hora_fim", sol, formadores))

        assert sol.status == "pendente"
        assert sol.gcal_status == "NONE"
