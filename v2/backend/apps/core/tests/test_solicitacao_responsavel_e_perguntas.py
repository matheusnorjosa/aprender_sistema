"""
Nova Solicitação: coordenador responsável, "acompanha?" e "pretende avaliar o formador?".

Decisões do dono (05/10/2026):
- UM coordenador responsável por evento (`Solicitacao.coordenador`). Se quem cria é
  coordenador e não informa, é ele; se não é, o responsável é obrigatório. O responsável
  passa pelo mesmo escopo de setor dos formadores e recebe o convite do Google mesmo
  respondendo "Não".
- A lista "Coordenadores Acompanhantes" saiu: `coord_acompanha_ids/_emails` não são mais
  aceitos. No lugar, `coordenador_acompanha` (Sim/Não) é obrigatório na criação; null nunca
  vale como resposta.
- "Você pretende avaliar o formador nesse evento?" só se aplica quando a gerência do PROJETO
  pergunta (`Gerencia.pergunta_avaliar_formador`) e há na lista de formadores ao menos uma
  pessoa avaliável (função Formador sem a função Coordenador). Aplicável → obrigatória; "Sim"
  → `formador_avaliado` obrigatório e entre os avaliáveis. Não aplicável → resposta recusada.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

import itertools
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog, Compra, EquipeGerencia, Gerencia, Participation, Solicitacao
from apps.core.services.gcal.payload import build_attendees_for_solicitacao
from apps.core.tests.conftest import get_field_errors
from apps.core.tests.factories import MunicipioFactory, ProjetoFactory, TipoEventoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

_TZ = ZoneInfo("America/Fortaleza")
_INICIO = datetime(2031, 4, 7, 9, tzinfo=_TZ)
_FIM = datetime(2031, 4, 7, 11, tzinfo=_TZ)
_HASH = itertools.count(1)
_N = itertools.count(1)


def _pessoa(*grupos: str, gerencia=None, papel="FORMADOR"):
    n = next(_N)
    u = UsuarioFactory(
        username=f"perg_{n}",
        email=f"perg_{n}@example.invalid",
        first_name=f"Pessoa{n}",
        last_name="Ficticia",
        groups=list(grupos),
    )
    if gerencia is not None:
        EquipeGerencia.objects.create(usuario=u, gerencia=gerencia, papel=papel, ativo=True)
    return u


@pytest.fixture
def c():
    municipio = MunicipioFactory(nome="Municipio Ficticio Perguntas", uf="CE")
    pergunta = Gerencia.objects.create(nome="G-PERG-SIM", nome_setor="Setor Pergunta", setor_canonico="SetorP")
    nao_pergunta = Gerencia.objects.create(
        nome="G-PERG-NAO", nome_setor="Setor Sem Pergunta", setor_canonico="SetorP", pergunta_avaliar_formador=False
    )
    outro_setor = Gerencia.objects.create(nome="G-PERG-OUTRO", nome_setor="Outro", setor_canonico="SetorOutro")
    projetos = {}
    for chave, ger in (("pergunta", pergunta), ("nao_pergunta", nao_pergunta)):
        p = ProjetoFactory(
            nome=f"Projeto Ficticio {chave}", codigo=f"PF{chave[:6]}", fluxo="NAO_SUPER", gerencia=ger, setor="SetorP"
        )
        Compra.objects.create(
            codigo=f"C-PERG-{chave}",
            projeto=p,
            municipio=municipio,
            quantidade=1,
            data=date(2026, 3, 1),
            uso="teste",
            external_hash=f"{next(_HASH):064d}",
        )
        projetos[chave] = p
    return {
        "municipio": municipio,
        "tipo": TipoEventoFactory(nome="Formacao Ficticia Perguntas"),
        "projeto": projetos["pergunta"],
        "projeto_nao_pergunta": projetos["nao_pergunta"],
        "gerencia": pergunta,
        "outro_setor": outro_setor,
        "coord": _pessoa("Coordenador", gerencia=pergunta, papel="COORDENADOR"),
        "formador": _pessoa("Formador", gerencia=pergunta),
    }


def _client(user):
    cl = APIClient()
    cl.force_authenticate(user)
    return cl


def _payload(c, *, formadores=None, projeto=None, **extra: Any) -> dict[str, Any]:
    p: dict[str, Any] = {
        "municipio": c["municipio"].id,
        "projeto": (projeto or c["projeto"]).id,
        "tipo_evento": c["tipo"].id,
        "inicio": _INICIO.isoformat(),
        "fim": _FIM.isoformat(),
        "extra_participants": {"formador_ids": [f.id for f in (formadores or [c["formador"]])]},
    }
    p.update(extra)
    return p


def _post(user, payload):
    return _client(user).post("/api/solicitacoes/", payload, format="json")


# ---------------------------------------------------------------- acompanha


class TestCoordenadorAcompanhaObrigatorio:
    def test_sem_a_resposta_recusa(self, c):
        r = _post(c["coord"], _payload(c, pretende_avaliar_formador=False))
        assert r.status_code == 400, r.data
        assert "coordenador_acompanha" in get_field_errors(r)

    def test_null_nao_vale_como_resposta(self, c):
        r = _post(c["coord"], _payload(c, coordenador_acompanha=None, pretende_avaliar_formador=False))
        assert r.status_code == 400, r.data
        assert "coordenador_acompanha" in get_field_errors(r)

    @pytest.mark.parametrize("resposta", [True, False])
    def test_resposta_gravada(self, c, resposta):
        r = _post(c["coord"], _payload(c, coordenador_acompanha=resposta, pretende_avaliar_formador=False))
        assert r.status_code == 201, r.data
        assert Solicitacao.objects.get(pk=r.data["id"]).coordenador_acompanha is resposta

    def test_edicao_sem_mandar_a_resposta_mantem(self, c):
        r = _post(c["coord"], _payload(c, coordenador_acompanha=True, pretende_avaliar_formador=False))
        resp = _client(c["coord"]).patch(f"/api/solicitacoes/{r.data['id']}/", {"observacoes": "x"}, format="json")
        assert resp.status_code == 200, resp.data
        assert Solicitacao.objects.get(pk=r.data["id"]).coordenador_acompanha is True

    def test_lista_de_coordenadores_acompanhantes_saiu(self, c):
        outro = _pessoa("Coordenador", gerencia=c["gerencia"], papel="COORDENADOR")
        payload = _payload(c, coordenador_acompanha=False, pretende_avaliar_formador=False)
        payload["extra_participants"]["coord_acompanha_ids"] = [outro.id]
        r = _post(c["coord"], payload)
        assert r.status_code == 400, r.data
        assert "lista de formadores" in str(get_field_errors(r))
        assert not Participation.objects.filter(usuario=outro).exists()


# ---------------------------------------------------------------- responsável


class TestCoordenadorResponsavel:
    def test_coordenador_que_cria_vira_o_responsavel(self, c):
        r = _post(c["coord"], _payload(c, coordenador_acompanha=False, pretende_avaliar_formador=False))
        assert r.status_code == 201, r.data
        assert Solicitacao.objects.get(pk=r.data["id"]).coordenador_id == c["coord"].id

    def test_quem_nao_e_coordenador_precisa_informar(self, c):
        apoio = _pessoa("Apoio de Coordenação", gerencia=c["gerencia"], papel="APOIO")
        r = _post(apoio, _payload(c, coordenador_acompanha=False, pretende_avaliar_formador=False))
        assert r.status_code == 400, r.data
        assert "coordenador" in get_field_errors(r)

    def test_quem_nao_e_coordenador_informa_e_grava(self, c):
        apoio = _pessoa("Apoio de Coordenação", gerencia=c["gerencia"], papel="APOIO")
        r = _post(
            apoio,
            _payload(c, coordenador=c["coord"].id, coordenador_acompanha=False, pretende_avaliar_formador=False),
        )
        assert r.status_code == 201, r.data
        assert Solicitacao.objects.get(pk=r.data["id"]).coordenador_id == c["coord"].id

    def test_responsavel_de_outro_setor_recusado(self, c):
        """Crítica ALTA do desenho: o responsável passa a ocupar a agenda → mesmo escopo dos formadores."""
        apoio = _pessoa("Apoio de Coordenação", gerencia=c["gerencia"], papel="APOIO")
        de_fora = _pessoa("Coordenador", gerencia=c["outro_setor"], papel="COORDENADOR")
        r = _post(
            apoio, _payload(c, coordenador=de_fora.id, coordenador_acompanha=True, pretende_avaliar_formador=False)
        )
        assert r.status_code == 400, r.data
        assert "coordenador" in get_field_errors(r)

    def test_trocar_responsavel_para_outro_setor_na_edicao_recusado(self, c):
        r = _post(c["coord"], _payload(c, coordenador_acompanha=False, pretende_avaliar_formador=False))
        de_fora = _pessoa("Coordenador", gerencia=c["outro_setor"], papel="COORDENADOR")
        resp = _client(c["coord"]).patch(
            f"/api/solicitacoes/{r.data['id']}/", {"coordenador": de_fora.id}, format="json"
        )
        assert resp.status_code == 400, resp.data
        assert Solicitacao.objects.get(pk=r.data["id"]).coordenador_id == c["coord"].id

    def test_superusuario_pode_escolher_responsavel_de_qualquer_setor(self, c):
        su = UsuarioFactory(superuser=True, username="perg_su", email="perg_su@example.invalid")
        de_fora = _pessoa("Coordenador", gerencia=c["outro_setor"], papel="COORDENADOR")
        r = _post(su, _payload(c, coordenador=de_fora.id, coordenador_acompanha=True, pretende_avaliar_formador=False))
        assert r.status_code == 201, r.data

    def test_responsavel_que_nao_acompanha_recebe_o_convite(self, c):
        apoio = _pessoa("Apoio de Coordenação", gerencia=c["gerencia"], papel="APOIO")
        r = _post(
            apoio,
            _payload(c, coordenador=c["coord"].id, coordenador_acompanha=False, pretende_avaliar_formador=False),
        )
        assert r.status_code == 201, r.data
        emails = {a["email"] for a in build_attendees_for_solicitacao(Solicitacao.objects.get(pk=r.data["id"]))}
        assert c["coord"].email in emails
        assert c["formador"].email in emails
        assert apoio.email in emails, "quem criou continua convidado (o convite não encolhe)"


# ---------------------------------------------------------------- avaliar o formador


class TestPretendeAvaliarFormador:
    def test_sem_resposta_recusa(self, c):
        r = _post(c["coord"], _payload(c, coordenador_acompanha=False))
        assert r.status_code == 400, r.data
        assert "pretende_avaliar_formador" in get_field_errors(r)

    def test_null_recusa(self, c):
        r = _post(c["coord"], _payload(c, coordenador_acompanha=False, pretende_avaliar_formador=None))
        assert r.status_code == 400, r.data
        assert "pretende_avaliar_formador" in get_field_errors(r)

    def test_nao_grava_sem_formador(self, c):
        r = _post(c["coord"], _payload(c, coordenador_acompanha=False, pretende_avaliar_formador=False))
        assert r.status_code == 201, r.data
        sol = Solicitacao.objects.get(pk=r.data["id"])
        assert sol.pretende_avaliar_formador is False
        assert sol.formador_avaliado_id is None

    def test_sim_exige_escolher_o_formador(self, c):
        r = _post(c["coord"], _payload(c, coordenador_acompanha=False, pretende_avaliar_formador=True))
        assert r.status_code == 400, r.data
        assert "formador_avaliado" in get_field_errors(r)

    def test_sim_com_formador_avaliavel_grava_e_expoe(self, c):
        r = _post(
            c["coord"],
            _payload(
                c, coordenador_acompanha=False, pretende_avaliar_formador=True, formador_avaliado=c["formador"].id
            ),
        )
        assert r.status_code == 201, r.data
        got = _client(c["coord"]).get(f"/api/solicitacoes/{r.data['id']}/").data
        assert got["pretende_avaliar_formador"] is True
        assert got["formador_avaliado"] == c["formador"].id
        assert got["formador_avaliado_nome"] == c["formador"].get_full_name()

    def test_sim_com_pessoa_fora_da_lista_recusa(self, c):
        fora = _pessoa("Formador", gerencia=c["gerencia"])
        r = _post(
            c["coord"],
            _payload(c, coordenador_acompanha=False, pretende_avaliar_formador=True, formador_avaliado=fora.id),
        )
        assert r.status_code == 400, r.data
        assert "formador_avaliado" in get_field_errors(r)

    def test_formador_que_tambem_e_coordenador_nao_e_avaliavel(self, c):
        duplo = _pessoa("Formador", "Coordenador", gerencia=c["gerencia"])
        r = _post(
            c["coord"],
            _payload(
                c,
                formadores=[c["formador"], duplo],
                coordenador_acompanha=False,
                pretende_avaliar_formador=True,
                formador_avaliado=duplo.id,
            ),
        )
        assert r.status_code == 400, r.data
        assert "formador_avaliado" in get_field_errors(r)

    def test_so_coordenadores_na_lista_a_pergunta_nao_se_aplica(self, c):
        coord2 = _pessoa("Coordenador", gerencia=c["gerencia"], papel="COORDENADOR")
        r = _post(c["coord"], _payload(c, formadores=[coord2], coordenador_acompanha=False))
        assert r.status_code == 201, r.data
        assert Solicitacao.objects.get(pk=r.data["id"]).pretende_avaliar_formador is None
        r2 = _post(
            c["coord"], _payload(c, formadores=[coord2], coordenador_acompanha=False, pretende_avaliar_formador=False)
        )
        assert r2.status_code == 400, r2.data
        assert "pretende_avaliar_formador" in get_field_errors(r2)

    def test_gerencia_que_nao_pergunta_aceita_sem_resposta_e_recusa_resposta(self, c):
        proj = c["projeto_nao_pergunta"]

        def novo():  # um formador por evento: o mesmo horário não pode repetir formador
            return [_pessoa("Formador", gerencia=c["gerencia"])]

        r = _post(c["coord"], _payload(c, projeto=proj, formadores=novo(), coordenador_acompanha=False))
        assert r.status_code == 201, r.data
        assert Solicitacao.objects.get(pk=r.data["id"]).pretende_avaliar_formador is None
        r_null = _post(
            c["coord"],
            _payload(c, projeto=proj, formadores=novo(), coordenador_acompanha=False, pretende_avaliar_formador=None),
        )
        assert r_null.status_code == 201, r_null.data
        for resposta in (True, False):
            r2 = _post(
                c["coord"],
                _payload(
                    c, projeto=proj, formadores=novo(), coordenador_acompanha=False, pretende_avaliar_formador=resposta
                ),
            )
            assert r2.status_code == 400, r2.data
            assert "pretende_avaliar_formador" in get_field_errors(r2)

    def test_editar_tirando_o_formador_avaliado_recusa(self, c):
        """Escolha documentada: a edição RECUSA (não limpa em silêncio) e diz o que fazer."""
        outro = _pessoa("Formador", gerencia=c["gerencia"])
        r = _post(
            c["coord"],
            _payload(
                c,
                formadores=[c["formador"], outro],
                coordenador_acompanha=False,
                pretende_avaliar_formador=True,
                formador_avaliado=c["formador"].id,
            ),
        )
        assert r.status_code == 201, r.data
        resp = _client(c["coord"]).patch(
            f"/api/solicitacoes/{r.data['id']}/", {"extra_participants": {"formador_ids": [outro.id]}}, format="json"
        )
        assert resp.status_code == 400, resp.data
        assert "formador_avaliado" in get_field_errors(resp)
        assert Participation.objects.filter(solicitacao_id=r.data["id"], usuario=c["formador"]).exists()

    def test_editar_evento_antigo_sem_resposta_segue_sem_resposta(self, c):
        r = _post(c["coord"], _payload(c, coordenador_acompanha=False, pretende_avaliar_formador=False))
        Solicitacao.objects.filter(pk=r.data["id"]).update(pretende_avaliar_formador=None)
        resp = _client(c["coord"]).patch(f"/api/solicitacoes/{r.data['id']}/", {"observacoes": "y"}, format="json")
        assert resp.status_code == 200, resp.data
        assert Solicitacao.objects.get(pk=r.data["id"]).pretende_avaliar_formador is None

    def test_edicao_registra_as_respostas_na_trilha(self, c):
        r = _post(c["coord"], _payload(c, coordenador_acompanha=False, pretende_avaliar_formador=False))
        resp = _client(c["coord"]).patch(
            f"/api/solicitacoes/{r.data['id']}/",
            {"pretende_avaliar_formador": True, "formador_avaliado": c["formador"].id, "coordenador_acompanha": True},
            format="json",
        )
        assert resp.status_code == 200, resp.data
        log = AuditLog.objects.filter(action=AuditLog.Action.UPDATE, model_name="Solicitacao").latest("id")
        mudou = log.details["changed_fields"]
        assert mudou["pretende_avaliar_formador"] == {"old": False, "new": True}
        assert mudou["formador_avaliado_id"] == {"old": None, "new": c["formador"].id}
        assert mudou["coordenador_acompanha"] == {"old": False, "new": True}


# ---------------------------------------------------------------- lookups e gerência


class TestLookupsEGerencia:
    def test_lookup_de_projetos_diz_se_pergunta(self, c):
        data = _client(c["coord"]).get("/api/lookup/projetos/").data
        por_id = {p["id"]: p for p in data}
        assert por_id[c["projeto"].id]["pergunta_avaliar_formador"] is True
        assert por_id[c["projeto_nao_pergunta"].id]["pergunta_avaliar_formador"] is False

    def test_lookup_de_formadores_oferece_coordenadores_e_marca_avaliavel(self, c):
        duplo = _pessoa("Formador", "Coordenador", gerencia=c["gerencia"])
        data = _client(c["coord"]).get("/api/lookup/usuarios/", {"role": "Formador,Coordenador"}).data
        por_id = {u["id"]: u for u in data}
        assert c["coord"].id in por_id, "coordenador do setor pode ir como formador"
        assert por_id[c["formador"].id]["avaliavel"] is True
        assert por_id[duplo.id]["avaliavel"] is False
        assert por_id[c["coord"].id]["avaliavel"] is False

    def test_gerencia_expoe_e_grava_a_marca(self, c):
        su = UsuarioFactory(superuser=True, username="perg_su2", email="perg_su2@example.invalid")
        url = f"/api/gerencias/{c['gerencia'].id}/"
        assert _client(su).get(url).data["pergunta_avaliar_formador"] is True
        resp = _client(su).patch(url, {"pergunta_avaliar_formador": False}, format="json")
        assert resp.status_code == 200, resp.data
        c["gerencia"].refresh_from_db()
        assert c["gerencia"].pergunta_avaliar_formador is False

    def test_coordenador_nao_edita_gerencia(self, c):
        url = f"/api/gerencias/{c['gerencia'].id}/"
        resp = _client(c["coord"]).patch(url, {"pergunta_avaliar_formador": False}, format="json")
        assert resp.status_code == 403
