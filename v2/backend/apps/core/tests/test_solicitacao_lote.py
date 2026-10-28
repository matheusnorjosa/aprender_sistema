"""
Testes: POST /api/solicitacoes/lote/ — criar vários eventos de uma vez (decisões do dono de 28/10).

- até `MAX_EVENTOS_LOTE` (10) eventos; cada um é o mesmo payload do POST de 1 evento;
- tudo ou nada: qualquer evento com problema → 400 `lote_invalido`, nada é criado, e o erro vem
  por evento em `errors.itens` (formato do batch-approve: `blocked_participants` no topo do item);
- dois eventos do lote com a mesma pessoa no mesmo horário são erro mesmo se ambos SUPER pendentes
  (o D entre eles também);
- quem já cria evento, sem poder novo: mesma capability e mesmo escopo por evento;
- nada vai ao Google na criação (PA-03).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false, reportPrivateUsage=false

from __future__ import annotations

from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from unittest.mock import patch

from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog, AvailabilityBlock, Participation, Solicitacao
from apps.core.services import solicitacao_availability as guard_module
from apps.core.services.config_service import bust_cfg
from apps.core.tests.factories import (
    GerenciaFactory,
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
    com_papel,
    liberar_par,
)
from apps.core.views_solicitacao import MAX_EVENTOS_LOTE

pytestmark = pytest.mark.django_db

URL = "/api/solicitacoes/lote/"


def _utc(hora: int, minuto: int = 0, dia: int = 10) -> datetime:
    """Março de 2027, em UTC — Fortaleza é UTC-3, tudo no mesmo dia local."""
    return datetime(2027, 3, dia, hora, minuto, tzinfo=dt_timezone.utc)


@pytest.fixture(autouse=True)
def _parametros(settings):
    settings.TRAVEL_BUFFER_MINUTES = 120
    bust_cfg("availability")


@pytest.fixture
def gerencia():
    """Sem a pergunta "pretende avaliar o formador?": ela não é o assunto aqui."""
    return GerenciaFactory(pergunta_avaliar_formador=False)


@pytest.fixture
def cidade_a():
    return MunicipioFactory(nome="Cidade A Lote", uf="CE")


@pytest.fixture
def cidade_b():
    return MunicipioFactory(nome="Cidade B Lote", uf="CE")


@pytest.fixture
def tipo_evento():
    return TipoEventoFactory(nome="Formação Lote")


@pytest.fixture
def nao_super(gerencia, cidade_a, cidade_b):
    projeto = ProjetoFactory(nome="Projeto NAO_SUPER Lote", gerencia=gerencia)
    liberar_par(cidade_a, projeto)
    liberar_par(cidade_b, projeto)
    return projeto


@pytest.fixture
def super_(gerencia, cidade_a, cidade_b):
    projeto = ProjetoFactory(nome="Projeto SUPER Lote", fluxo="SUPER", gerencia=gerencia)
    liberar_par(cidade_a, projeto)
    liberar_par(cidade_b, projeto)
    return projeto


@pytest.fixture
def coordenador(gerencia):
    """Quem cria: papel COORDENADOR na gerência dá `create_solicitation` e o escopo do PR 9."""
    user = UsuarioFactory(username="coord_lote", first_name="Ana", last_name="Coordenadora")
    com_papel(user, "COORDENADOR", gerencia)
    return user


@pytest.fixture
def formador(gerencia):
    user = UsuarioFactory(username="formador_lote", first_name="Bruno", last_name="Formador")
    com_papel(user, "FORMADOR", gerencia)
    return user


@pytest.fixture
def formadora(gerencia):
    user = UsuarioFactory(username="formadora_lote", first_name="Clara", last_name="Formadora")
    com_papel(user, "FORMADOR", gerencia)
    return user


def _client(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _item(projeto, municipio, tipo_evento, inicio, fim, *, formadores=(), **extra):
    item = {
        "projeto": projeto.pk,
        "municipio": municipio.pk,
        "tipo_evento": tipo_evento.pk,
        "coordenador_acompanha": False,
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat(),
    }
    if formadores:
        item["extra_participants"] = {"formador_ids": [f.pk for f in formadores]}
    item.update(extra)
    return item


def _contagens():
    return (Solicitacao.objects.count(), Participation.objects.count(), AuditLog.objects.count())


def _itens(response):
    assert response.status_code == 400, response.data
    assert response.data["code"] == "lote_invalido"
    assert "Nada foi criado" in response.data["detail"]
    return {i["indice"]: i for i in response.data["errors"]["itens"]}


# ============================================================================
# Quem pode
# ============================================================================


class TestPermissao:
    def test_sem_a_capability_de_criar_recebe_403(self, gerencia, nao_super, cidade_a, tipo_evento):
        sem_papel = UsuarioFactory(username="sem_papel_lote")
        antes = _contagens()

        response = _client(sem_papel).post(
            URL, {"eventos": [_item(nao_super, cidade_a, tipo_evento, _utc(12), _utc(14))]}, format="json"
        )

        assert response.status_code == 403
        assert _contagens() == antes

    def test_anonimo_nao_cria(self, nao_super, cidade_a, tipo_evento):
        response = APIClient().post(
            URL, {"eventos": [_item(nao_super, cidade_a, tipo_evento, _utc(12), _utc(14))]}, format="json"
        )

        assert response.status_code in (401, 403)
        assert Solicitacao.objects.count() == 0


# ============================================================================
# Sucesso
# ============================================================================


class TestCriaTudo:
    def test_nao_super_nasce_aprovado_e_super_pendente(
        self, coordenador, formador, formadora, nao_super, super_, cidade_a, tipo_evento
    ):
        response = _client(coordenador).post(
            URL,
            {
                "eventos": [
                    _item(nao_super, cidade_a, tipo_evento, _utc(12), _utc(14), formadores=[formador]),
                    _item(super_, cidade_a, tipo_evento, _utc(12), _utc(14), formadores=[formadora]),
                ]
            },
            format="json",
        )

        assert response.status_code == 201, response.data
        eventos = response.data["eventos"]
        assert [(e["indice"], e["status"]) for e in eventos] == [(0, "aprovado"), (1, "pendente")]
        criados = {e["indice"]: Solicitacao.objects.get(pk=e["id"]) for e in eventos}
        assert criados[0].projeto_id == nao_super.pk and criados[0].status == "aprovado"
        assert criados[1].projeto_id == super_.pk and criados[1].status == "pendente"
        assert all(s.usuario_id == coordenador.pk and s.coordenador_id == coordenador.pk for s in criados.values())

    def test_formadores_de_cada_evento_vao_para_o_evento_certo(
        self, coordenador, formador, formadora, nao_super, cidade_a, tipo_evento
    ):
        response = _client(coordenador).post(
            URL,
            {
                "eventos": [
                    _item(nao_super, cidade_a, tipo_evento, _utc(12), _utc(14), formadores=[formador]),
                    _item(nao_super, cidade_a, tipo_evento, _utc(12), _utc(14), formadores=[formadora]),
                ]
            },
            format="json",
        )

        assert response.status_code == 201, response.data
        ids = [e["id"] for e in response.data["eventos"]]

        def formadores_de(pk):
            return set(
                Participation.objects.filter(solicitacao_id=pk, role="FORMADOR").values_list("usuario_id", flat=True)
            )

        assert formadores_de(ids[0]) == {formador.pk}
        assert formadores_de(ids[1]) == {formadora.pk}

    def test_mesmo_horario_sem_pessoa_em_comum_cria(
        self, coordenador, formador, formadora, super_, cidade_a, tipo_evento
    ):
        response = _client(coordenador).post(
            URL,
            {
                "eventos": [
                    _item(super_, cidade_a, tipo_evento, _utc(12), _utc(14), formadores=[formador]),
                    _item(super_, cidade_a, tipo_evento, _utc(12), _utc(14), formadores=[formadora]),
                ]
            },
            format="json",
        )

        assert response.status_code == 201, response.data
        assert Solicitacao.objects.filter(status="pendente").count() == 2

    def test_auditlog_so_para_quem_nasce_aprovado_marcado_lote(
        self, coordenador, formador, formadora, nao_super, super_, cidade_a, tipo_evento
    ):
        response = _client(coordenador).post(
            URL,
            {
                "eventos": [
                    _item(super_, cidade_a, tipo_evento, _utc(12), _utc(14), formadores=[formador]),
                    _item(nao_super, cidade_a, tipo_evento, _utc(12), _utc(14), formadores=[formadora]),
                ]
            },
            format="json",
        )

        assert response.status_code == 201, response.data
        aprovado_id = response.data["eventos"][1]["id"]
        logs = AuditLog.objects.filter(model_name="Solicitacao", action=AuditLog.Action.CREATE)
        assert [log.details["solicitacao_id"] for log in logs] == [aprovado_id]
        assert logs[0].details["lote"] is True
        assert logs[0].details["auto_aprovada_por_fluxo"] == "NAO_SUPER"

    def test_teto_de_eventos_cabe(self, coordenador, nao_super, cidade_a, tipo_evento):
        eventos = [
            _item(nao_super, cidade_a, tipo_evento, _utc(12, dia=d), _utc(14, dia=d))
            for d in range(1, MAX_EVENTOS_LOTE + 1)
        ]

        response = _client(coordenador).post(URL, {"eventos": eventos}, format="json")

        assert MAX_EVENTOS_LOTE == 10
        assert response.status_code == 201, response.data
        assert len(response.data["eventos"]) == MAX_EVENTOS_LOTE

    @patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay")
    @patch("apps.core.views_solicitacao.publish_to_gcal")
    def test_nada_vai_ao_google(self, publish, task, coordenador, formador, nao_super, cidade_a, tipo_evento):
        """PA-03: a criação não publica; nem o evento que nasce aprovado (NAO_SUPER)."""
        response = _client(coordenador).post(
            URL,
            {"eventos": [_item(nao_super, cidade_a, tipo_evento, _utc(12), _utc(14), formadores=[formador])]},
            format="json",
        )

        assert response.status_code == 201, response.data
        publish.assert_not_called()
        task.assert_not_called()

    def test_trava_a_agenda_uma_vez_com_todos_os_participantes(
        self, coordenador, formador, formadora, super_, cidade_a, tipo_evento
    ):
        with patch.object(guard_module, "lock_participants", wraps=guard_module.lock_participants) as lock:
            response = _client(coordenador).post(
                URL,
                {
                    "eventos": [
                        _item(super_, cidade_a, tipo_evento, _utc(12), _utc(14), formadores=[formadora]),
                        _item(super_, cidade_a, tipo_evento, _utc(15), _utc(16), formadores=[formador, formadora]),
                    ]
                },
                format="json",
            )

        assert response.status_code == 201, response.data
        lock.assert_called_once()
        assert list(lock.call_args.args[0]) == sorted({formador.pk, formadora.pk})

    def test_cada_evento_e_checado_com_o_lote_completo(
        self, coordenador, formador, formadora, super_, cidade_a, tipo_evento
    ):
        with patch.object(
            guard_module, "check_solicitacao_availability", wraps=guard_module.check_solicitacao_availability
        ) as check:
            response = _client(coordenador).post(
                URL,
                {
                    "eventos": [
                        _item(super_, cidade_a, tipo_evento, _utc(12), _utc(14), formadores=[formador]),
                        _item(super_, cidade_a, tipo_evento, _utc(12), _utc(14), formadores=[formadora]),
                    ]
                },
                format="json",
            )

        assert response.status_code == 201, response.data
        ids = [e["id"] for e in response.data["eventos"]]
        completo = {ids[0]: 1, ids[1]: 2}
        assert [dict(c.kwargs["lote"]) for c in check.call_args_list] == [completo, completo]
        assert all(c.kwargs["lock"] is False for c in check.call_args_list)


# ============================================================================
# Tudo ou nada: o erro vem por evento e nada é criado
# ============================================================================


class TestRecusaPorEvento:
    def test_projeto_fora_da_gerencia(self, coordenador, nao_super, cidade_a, tipo_evento):
        outro = ProjetoFactory(nome="Projeto de outra gerência", gerencia=GerenciaFactory())
        liberar_par(cidade_a, outro)
        antes = _contagens()

        response = _client(coordenador).post(
            URL,
            {
                "eventos": [
                    _item(nao_super, cidade_a, tipo_evento, _utc(12), _utc(14)),
                    _item(outro, cidade_a, tipo_evento, _utc(15), _utc(16)),
                ]
            },
            format="json",
        )

        itens = _itens(response)
        assert list(itens) == [1]
        assert "projeto" in itens[1]["errors"]
        assert itens[1]["code"] == "VALIDATION_ERROR"
        assert _contagens() == antes

    def test_compra_faltando_recusa_e_o_isento_passa(self, coordenador, gerencia, cidade_a, tipo_evento):
        sem_compra = ProjetoFactory(nome="Projeto sem compra", gerencia=gerencia)
        payload = {"eventos": [_item(sem_compra, cidade_a, tipo_evento, _utc(12), _utc(14))]}

        itens = _itens(_client(coordenador).post(URL, payload, format="json"))
        assert "municipio" in itens[0]["errors"]
        assert Solicitacao.objects.count() == 0

        isento = UsuarioFactory(superuser=True)
        payload["eventos"][0]["coordenador"] = coordenador.pk
        response = _client(isento).post(URL, payload, format="json")
        assert response.status_code == 201, response.data

    def test_coordenador_acompanha_faltando_so_no_segundo(self, coordenador, nao_super, cidade_a, tipo_evento):
        """Pega a regressão de `many=True`: a Regra 5 lê o `initial_data` de CADA evento."""
        segundo = _item(nao_super, cidade_a, tipo_evento, _utc(15), _utc(16))
        del segundo["coordenador_acompanha"]
        antes = _contagens()

        response = _client(coordenador).post(
            URL, {"eventos": [_item(nao_super, cidade_a, tipo_evento, _utc(12), _utc(14)), segundo]}, format="json"
        )

        itens = _itens(response)
        assert list(itens) == [1]
        assert "coordenador_acompanha" in itens[1]["errors"]
        assert _contagens() == antes

    def test_conflito_com_aprovado_do_banco(self, coordenador, formador, nao_super, cidade_a, tipo_evento):
        aprovado = SolicitacaoFactory(
            usuario=formador, municipio=cidade_a, inicio=_utc(12), fim=_utc(14), status="aprovado"
        )
        Participation.objects.create(solicitacao=aprovado, usuario=formador, role="FORMADOR")
        antes = _contagens()

        response = _client(coordenador).post(
            URL,
            {
                "eventos": [
                    _item(nao_super, cidade_a, tipo_evento, _utc(8), _utc(9)),
                    _item(nao_super, cidade_a, tipo_evento, _utc(13), _utc(15), formadores=[formador]),
                ]
            },
            format="json",
        )

        itens = _itens(response)
        assert list(itens) == [1]
        assert itens[1]["code"] == "availability_conflict"
        assert "tem outro evento aprovado neste horário" in itens[1]["detail"]
        assert [p["usuario_id"] for p in itens[1]["blocked_participants"]] == [formador.pk]
        assert "errors" not in itens[1]
        assert _contagens() == antes

    def test_super_mais_super_com_a_mesma_pessoa_marca_os_dois(
        self, coordenador, formador, super_, cidade_a, tipo_evento
    ):
        antes = _contagens()

        response = _client(coordenador).post(
            URL,
            {
                "eventos": [
                    _item(super_, cidade_a, tipo_evento, _utc(12), _utc(14), formadores=[formador]),
                    _item(super_, cidade_a, tipo_evento, _utc(13), _utc(15), formadores=[formador]),
                ]
            },
            format="json",
        )

        itens = _itens(response)
        assert sorted(itens) == [0, 1]
        assert all(i["code"] == "availability_conflict" for i in itens.values())
        assert "evento 2 desta lista" in itens[0]["blocked_participants"][0]["conflicts"][0]["detail"]
        assert "evento 1 desta lista" in itens[1]["blocked_participants"][0]["conflicts"][0]["detail"]
        assert all("aprovado" not in i["detail"] for i in itens.values())
        assert response.data["detail"] == "2 de 2 eventos têm problema. Nada foi criado."
        assert _contagens() == antes

    @pytest.mark.parametrize("ordem", ["super_primeiro", "nao_super_primeiro"])
    def test_super_e_nao_super_com_a_mesma_pessoa(
        self, ordem, coordenador, formador, super_, nao_super, cidade_a, tipo_evento
    ):
        projetos = [super_, nao_super] if ordem == "super_primeiro" else [nao_super, super_]
        antes = _contagens()

        response = _client(coordenador).post(
            URL,
            {"eventos": [_item(p, cidade_a, tipo_evento, _utc(12), _utc(14), formadores=[formador]) for p in projetos]},
            format="json",
        )

        itens = _itens(response)
        assert sorted(itens) == [0, 1]
        assert _contagens() == antes

    def test_deslocamento_entre_eventos_do_lote(self, coordenador, formador, super_, cidade_a, cidade_b, tipo_evento):
        antes = _contagens()

        response = _client(coordenador).post(
            URL,
            {
                "eventos": [
                    _item(super_, cidade_a, tipo_evento, _utc(9), _utc(10), formadores=[formador]),
                    _item(super_, cidade_b, tipo_evento, _utc(10, 30), _utc(11, 30), formadores=[formador]),
                ]
            },
            format="json",
        )

        itens = _itens(response)
        assert sorted(itens) == [0, 1]
        codigos = {c["code"] for i in itens.values() for c in i["blocked_participants"][0]["conflicts"]}
        assert codigos == {"D"}
        assert _contagens() == antes

    def test_responsavel_que_acompanha_choca_com_o_formador_do_outro_evento(
        self, coordenador, formador, super_, cidade_a, tipo_evento
    ):
        """Quem ocupa a agenda é a regra de sempre (`ocupa_agenda_q`): o responsável que acompanha um
        evento e é formador de outro, no mesmo horário, barra os dois."""
        response = _client(coordenador).post(
            URL,
            {
                "eventos": [
                    _item(super_, cidade_a, tipo_evento, _utc(12), _utc(14), coordenador_acompanha=True),
                    _item(super_, cidade_a, tipo_evento, _utc(13), _utc(15), formadores=[formador, coordenador]),
                ]
            },
            format="json",
        )

        itens = _itens(response)
        assert sorted(itens) == [0, 1]
        assert [p["usuario_id"] for p in itens[0]["blocked_participants"]] == [coordenador.pk]

    def test_bloqueio_de_agenda_barra_so_o_evento_dele_e_nada_e_criado(
        self, coordenador, formador, formadora, super_, cidade_a, tipo_evento
    ):
        AvailabilityBlock.objects.create(
            usuario=formadora, inicio=_utc(15), fim=_utc(16), tipo="T", status="aprovado", motivo="Folga"
        )
        antes = _contagens()

        response = _client(coordenador).post(
            URL,
            {
                "eventos": [
                    _item(super_, cidade_a, tipo_evento, _utc(12), _utc(14), formadores=[formador]),
                    _item(super_, cidade_a, tipo_evento, _utc(15), _utc(16), formadores=[formadora]),
                ]
            },
            format="json",
        )

        itens = _itens(response)
        assert list(itens) == [1]
        assert itens[1]["blocked_participants"][0]["conflicts"][0]["code"] == "T"
        assert _contagens() == antes

    def test_devolve_todos_os_erros_de_uma_vez(self, coordenador, formador, super_, nao_super, cidade_a, tipo_evento):
        """Erro de campo num evento e choque entre outros dois: os três vêm na mesma resposta."""
        sem_acompanha = _item(nao_super, cidade_a, tipo_evento, _utc(8), _utc(9))
        del sem_acompanha["coordenador_acompanha"]

        response = _client(coordenador).post(
            URL,
            {
                "eventos": [
                    sem_acompanha,
                    _item(super_, cidade_a, tipo_evento, _utc(12), _utc(14), formadores=[formador]),
                    _item(super_, cidade_a, tipo_evento, _utc(12), _utc(14), formadores=[formador]),
                ]
            },
            format="json",
        )

        itens = _itens(response)
        assert {i: itens[i]["code"] for i in itens} == {
            0: "VALIDATION_ERROR",
            1: "availability_conflict",
            2: "availability_conflict",
        }
        assert response.data["detail"] == "3 de 3 eventos têm problema. Nada foi criado."

    def test_recusa_parcial_com_um_ok_nao_deixa_nada(self, coordenador, formador, nao_super, cidade_a, tipo_evento):
        """O evento válido (NAO_SUPER, nasce aprovado) foi gravado antes do erro do outro: tudo volta."""
        antes = _contagens()

        response = _client(coordenador).post(
            URL,
            {
                "eventos": [
                    _item(nao_super, cidade_a, tipo_evento, _utc(8), _utc(9), formadores=[formador]),
                    _item(nao_super, cidade_a, tipo_evento, _utc(12), _utc(11)),
                ]
            },
            format="json",
        )

        itens = _itens(response)
        assert list(itens) == [1]
        assert "fim" in itens[1]["errors"]
        assert _contagens() == antes

    def test_extra_participants_malformado_vira_erro_do_evento(self, coordenador, nao_super, cidade_a, tipo_evento):
        response = _client(coordenador).post(
            URL,
            {
                "eventos": [
                    _item(nao_super, cidade_a, tipo_evento, _utc(12), _utc(14), extra_participants=[1, 2]),
                ]
            },
            format="json",
        )

        itens = _itens(response)
        assert list(itens) == [0]
        assert Solicitacao.objects.count() == 0


# ============================================================================
# Entrada malformada: 400, nunca 500
# ============================================================================


class TestEntradaMalformada:
    @pytest.mark.parametrize(
        "corpo",
        [
            {},
            {"eventos": []},
            {"eventos": None},
            {"eventos": "texto"},
            {"eventos": {"a": 1}},
            {"eventos": [1]},
            {"eventos": ["texto"]},
            {"eventos": [[]]},
            [{"eventos": []}],
            "texto",
            {"eventos": [{"projeto": {"id": 1}, "inicio": [], "extra_participants": "x"}]},
        ],
    )
    def test_formato_errado_da_400(self, corpo, coordenador):
        response = _client(coordenador).post(URL, corpo, format="json")

        assert response.status_code == 400, response.data
        assert Solicitacao.objects.count() == 0

    def test_acima_do_teto_da_400_sem_criar(self, coordenador, nao_super, cidade_a, tipo_evento):
        eventos = [
            _item(nao_super, cidade_a, tipo_evento, _utc(12, dia=d), _utc(14, dia=d))
            for d in range(1, MAX_EVENTOS_LOTE + 2)
        ]

        response = _client(coordenador).post(URL, {"eventos": eventos}, format="json")

        assert response.status_code == 400, response.data
        assert "eventos" in response.data["errors"]
        assert Solicitacao.objects.count() == 0


# ============================================================================
# Log sem dado pessoal
# ============================================================================


class TestLog:
    def test_log_do_criado_e_do_recusado(self, coordenador, formador, super_, cidade_a, tipo_evento):
        cliente = _client(coordenador)
        with patch("apps.core.views_solicitacao.logger") as logger:
            cliente.post(
                URL,
                {"eventos": [_item(super_, cidade_a, tipo_evento, _utc(12), _utc(14), formadores=[formador])]},
                format="json",
            )
            cliente.post(
                URL,
                {
                    "eventos": [
                        _item(super_, cidade_a, tipo_evento, _utc(16), _utc(18), formadores=[formador]),
                        _item(super_, cidade_a, tipo_evento, _utc(17), _utc(19), formadores=[formador]),
                    ]
                },
                format="json",
            )

        eventos = {c.args[0]: c.kwargs["extra"] for c in logger.info.call_args_list}
        criado = eventos["solicitacao_lote_criado"]
        recusado = eventos["solicitacao_lote_recusado"]
        assert criado["user_id"] == coordenador.pk and criado["n"] == 1 and len(criado["ids"]) == 1
        assert recusado["n"] == 2 and recusado["indices"] == [0, 1]
        assert recusado["codes"] == ["availability_conflict", "availability_conflict"]
        texto = repr(criado) + repr(recusado)
        assert "Bruno" not in texto and "Ana" not in texto and coordenador.cpf not in texto


# ============================================================================
# Contrato OpenAPI
# ============================================================================


def test_openapi_documenta_o_lote():
    superuser = UsuarioFactory(superuser=True)
    schema = _client(superuser).get("/api/schema/?format=json").json()

    operacao = schema["paths"]["/api/solicitacoes/lote/"]["post"]
    assert {"201", "400"} <= set(operacao["responses"])
    assert operacao["requestBody"]["content"]["application/json"]["schema"]
