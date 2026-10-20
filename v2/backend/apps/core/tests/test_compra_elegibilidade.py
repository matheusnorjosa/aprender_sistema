"""
Regra da compra: uma regra só, em `services/compra_elegibilidade.py` (plano de 14/10/2026).

Decisões do dono (02/10 e 14/10/2026):
- conta a `DATCompra` com `ativo=True` e `quantidade > 0`, de qualquer ano de uso e de qualquer tipo;
- vale a compra do mesmo projeto ou de qualquer projeto da mesma coleção (`projeto_geral`);
- num projeto marcado `eh_nome_geral`, vale também a compra de qualquer projeto da mesma gerência
  (sempre no mesmo município);
- projeto sem compra que o libere fica "em espera": some das listas de operação (Nova Solicitação,
  edição e Plano Anual) e volta sozinho quando a compra entra;
- superusuário isento; a capacidade `create_solicitation_without_purchase` também isenta, mas nasce
  sem grupo nenhum (entra no pacote do DAT num PR próprio);
- combo (20/10/2026): a compra de um projeto da coleção `NL E AMMA PORT E MAT` libera, no mesmo
  município, os projetos das coleções NOVO LENDO e PROJETO AMMA (`compra_elegibilidade.COMBOS`).

Cada POST e PATCH isola a regra: data fixa em dia útil (Fortaleza), formador sem agenda,
`coordenador_acompanha` informado, projeto sem setor (o escopo #1656 não dá 400 no lugar da regra) e
gerência que não faz a pergunta de avaliar o formador.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

import ast
import itertools
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from django.contrib.auth.models import Group
from django.core.cache import cache
from django.db import IntegrityError, transaction
from rest_framework.test import APIClient

import pytest

from apps.core.models import EquipeGerencia, Gerencia, Municipio, PermissaoFuncional, Projeto, ProjetoGeral, Solicitacao
from apps.core.tests.conftest import get_field_errors
from apps.core.tests.factories import (
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
    liberar_par,
)

pytestmark = pytest.mark.django_db

_TZ = ZoneInfo("America/Fortaleza")
_INICIO = datetime(2031, 4, 7, 9, tzinfo=_TZ)  # segunda-feira
_FIM = datetime(2031, 4, 7, 11, tzinfo=_TZ)
_N = itertools.count(1)
_CORE = Path(__file__).resolve().parents[1]


def _pessoa(*grupos: str, gerencia=None, papel="FORMADOR"):
    n = next(_N)
    u = UsuarioFactory(
        username=f"regra_compra_{n}",
        email=f"regra_compra_{n}@example.invalid",
        first_name=f"Pessoa{n}",
        last_name="Ficticia",
        groups=list(grupos),
    )
    if gerencia is not None:
        EquipeGerencia.objects.create(usuario=u, gerencia=gerencia, papel=papel, ativo=True)
    return u


@pytest.fixture
def c():
    ga = Gerencia.objects.create(nome="G-COMPRA-A", nome_setor="Setor Compra A", pergunta_avaliar_formador=False)
    gb = Gerencia.objects.create(nome="G-COMPRA-B", nome_setor="Setor Compra B", pergunta_avaliar_formador=False)
    col_x = ProjetoGeral.objects.create(nome="Colecao Ficticia X")
    col_y = ProjetoGeral.objects.create(nome="Colecao Ficticia Y")
    return {
        "ga": ga,
        "gb": gb,
        "m1": MunicipioFactory(nome="Municipio Compra Um", uf="CE"),
        "m2": MunicipioFactory(nome="Municipio Compra Dois", uf="CE"),
        "m3": MunicipioFactory(nome="Municipio Compra Tres", uf="CE"),
        "tipo": TipoEventoFactory(nome="Formacao Ficticia Compra"),
        # coleção X: o projeto-família e a série "X 3"
        "familia_x": ProjetoFactory(nome="Ficticio X", gerencia=ga, projeto_geral=col_x),
        "serie_x3": ProjetoFactory(nome="Ficticio X 3", gerencia=ga, projeto_geral=col_x, eh_serie=True),
        # outra coleção da mesma gerência
        "outro_y": ProjetoFactory(nome="Ficticio Y", gerencia=ga, projeto_geral=col_y),
        # candidato a nome geral (marcado só nos testes que precisam da marca)
        "geral_a": ProjetoFactory(nome="Ficticio Geral A", gerencia=ga),
        "geral_b": ProjetoFactory(nome="Ficticio Geral B", gerencia=gb),
        # sem coleção e sem gerência (a armadilha do IS NULL)
        "solto_1": ProjetoFactory(nome="Ficticio Solto 1"),
        "solto_2": ProjetoFactory(nome="Ficticio Solto 2"),
        "coord": _pessoa("Coordenador", gerencia=ga, papel="COORDENADOR"),
        "formador": _pessoa("Formador", gerencia=ga),
    }


def _marcar_nome_geral(*projetos: Projeto) -> None:
    Projeto.objects.filter(pk__in=[p.pk for p in projetos]).update(eh_nome_geral=True)
    for p in projetos:
        p.refresh_from_db()


def _client(user) -> APIClient:
    cl = APIClient()
    cl.force_authenticate(user)
    return cl


def _post(c, user, municipio, projeto):
    payload: dict[str, Any] = {
        "municipio": municipio.id,
        "projeto": projeto.id,
        "tipo_evento": c["tipo"].id,
        "inicio": _INICIO.isoformat(),
        "fim": _FIM.isoformat(),
        "extra_participants": {"formador_ids": [c["formador"].id]},
        "coordenador": c["coord"].id,
        "coordenador_acompanha": False,
    }
    if projeto.gerencia_id is None:  # projeto sem gerência faz a pergunta de avaliar o formador
        payload["pretende_avaliar_formador"] = False
    return _client(user).post("/api/solicitacoes/", payload, format="json")


def _ids(resp) -> set[int]:
    assert resp.status_code == 200, resp.data
    return {item["id"] for item in resp.data}


def _municipios(user, **params) -> set[int]:
    return _ids(_client(user).get("/api/lookup/municipios/", params))


def _projetos(user, **params) -> set[int]:
    return _ids(_client(user).get("/api/lookup/projetos/", params))


def _validate(c, user, municipio, projeto):
    payload = {
        "municipio": {"id": municipio.id},
        "projeto": {"id": projeto.id},
        "tipo_evento": {"id": c["tipo"].id},
        "date": "2031-04-07",
        "start": "09:00",
        "end": "11:00",
        "participants": {},
    }
    return _client(user).post("/api/solicitacoes/validate/", payload, format="json")


_ERRO_VALIDATE = "Município e projeto sem compra que os libere"


def _solicitacao(c, municipio, projeto) -> Solicitacao:
    return SolicitacaoFactory(
        usuario=c["coord"],
        coordenador=c["coord"],
        municipio=municipio,
        projeto=projeto,
        tipo_evento=c["tipo"],
        inicio=_INICIO,
        fim=_FIM,
        status="pendente",
        gcal_status="NONE",
    )


# ============================================================================ RED na main de 14/10


class TestRegraUnica:
    def test_datcompra_ativa_com_quantidade_libera_o_par(self, c):
        from apps.core.services.compra_elegibilidade import par_liberado

        liberar_par(c["m1"], c["familia_x"])
        assert par_liberado(c["m1"].id, c["familia_x"]) is True
        r = _post(c, c["coord"], c["m1"], c["familia_x"])
        assert r.status_code == 201, r.data

    def test_compra_de_serie_libera_o_projeto_da_colecao(self, c):
        liberar_par(c["m1"], c["serie_x3"])
        r = _post(c, c["coord"], c["m1"], c["familia_x"])
        assert r.status_code == 201, r.data

    def test_nome_geral_marcado_libera_por_compra_da_mesma_gerencia(self, c):
        _marcar_nome_geral(c["geral_a"])
        liberar_par(c["m1"], c["outro_y"])
        r = _post(c, c["coord"], c["m1"], c["geral_a"])
        assert r.status_code == 201, r.data

    @pytest.mark.parametrize(("ano_uso", "tipo"), [(None, None), (2025, "Aluno"), (2027, "Professor")])
    def test_qualquer_ano_de_uso_e_tipo_liberam(self, c, ano_uso, tipo):
        liberar_par(c["m1"], c["familia_x"], ano_uso=ano_uso, tipo=tipo)
        assert c["m1"].id in _municipios(c["coord"], com_compra="true", projeto_id=c["familia_x"].id)

    def test_edicao_trocando_para_par_liberado_pela_colecao_200(self, c):
        s = _solicitacao(c, c["m1"], c["outro_y"])
        liberar_par(c["m1"], c["serie_x3"])
        r = _client(c["coord"]).patch(f"/api/solicitacoes/{s.id}/", {"projeto": c["familia_x"].id}, format="json")
        assert r.status_code == 200, r.data
        s.refresh_from_db()
        assert s.projeto_id == c["familia_x"].id

    def test_lookup_municipios_projeto_id_segue_a_regra_unica(self, c):
        liberar_par(c["m1"], c["serie_x3"])
        liberar_par(c["m2"], c["outro_y"])
        assert _municipios(c["coord"], com_compra="true", projeto_id=c["familia_x"].id) == {c["m1"].id}
        # com_compra sem projeto: município com alguma compra válida
        assert {c["m1"].id, c["m2"].id} <= _municipios(c["coord"], com_compra="true")
        assert c["m3"].id not in _municipios(c["coord"], com_compra="true")

    def test_lookup_projetos_com_compra_esconde_projeto_em_espera(self, c):
        liberar_par(c["m1"], c["serie_x3"])
        ids = _projetos(c["coord"], com_compra="true")
        assert c["familia_x"].id in ids
        assert c["outro_y"].id not in ids  # em espera
        assert c["solto_1"].id not in ids  # em espera
        # sem o filtro, o projeto em espera continua no catálogo
        assert c["outro_y"].id in _projetos(c["coord"])

    def test_lookup_projetos_por_municipio_segue_a_regra_unica(self, c):
        liberar_par(c["m1"], c["serie_x3"])
        liberar_par(c["m2"], c["outro_y"])
        ids = _projetos(c["coord"], municipio_id=c["m1"].id)
        assert c["familia_x"].id in ids
        assert c["outro_y"].id not in ids

    def test_validate_usa_a_regra_unica(self, c):
        liberar_par(c["m1"], c["serie_x3"])
        ok = _validate(c, c["coord"], c["m1"], c["familia_x"]).json()
        assert ok["ok"] is True, ok
        recusado = _validate(c, c["coord"], c["m2"], c["familia_x"]).json()
        assert recusado["ok"] is False
        assert any(_ERRO_VALIDATE in e for e in recusado["errors"])

    def test_as_tres_consultas_concordam(self, c):
        """Grade 3 municípios × 7 projetos: par_liberado = pertencer às duas listas."""
        from apps.core.services.compra_elegibilidade import municipios_liberados, par_liberado, projetos_liberados

        _marcar_nome_geral(c["geral_a"], c["geral_b"])
        liberar_par(c["m1"], c["serie_x3"])  # coleção X na gerência A
        liberar_par(c["m2"], c["solto_2"])  # projeto sem coleção e sem gerência
        liberar_par(c["m2"], c["geral_b"])  # mesmo projeto (gerência B)
        nomes = ("familia_x", "serie_x3", "outro_y", "geral_a", "geral_b", "solto_1", "solto_2")
        municipios = (c["m1"], c["m2"], c["m3"])
        esperado = {
            ("m1", "familia_x"),  # coleção
            ("m1", "serie_x3"),  # mesmo projeto
            ("m1", "geral_a"),  # nome geral, mesma gerência
            ("m2", "solto_2"),  # mesmo projeto
            ("m2", "geral_b"),  # mesmo projeto
        }
        chave = {c["m1"].id: "m1", c["m2"].id: "m2", c["m3"].id: "m3"}
        todos_m = Municipio.objects.filter(pk__in=chave)
        todos_p = Projeto.objects.filter(pk__in=[c[n].pk for n in nomes])
        for m in municipios:
            no_projeto = set(projetos_liberados(todos_p, m.id).values_list("pk", flat=True))
            for n in nomes:
                p = c[n]
                por_par = par_liberado(m.id, p)
                por_municipio = municipios_liberados(todos_m, p).filter(pk=m.pk).exists()
                assert por_par == por_municipio == (p.pk in no_projeto), (chave[m.id], n)
                assert por_par == ((chave[m.id], n) in esperado), (chave[m.id], n)
        # "em espera" (sem município): só quem não tem compra que libere em lugar nenhum
        em_operacao = set(projetos_liberados(todos_p).values_list("pk", flat=True))
        assert em_operacao == {c[n].pk for n in ("familia_x", "serie_x3", "geral_a", "geral_b", "solto_2")}

    def test_eh_serie_e_eh_nome_geral_juntos_violam_constraint(self, c):
        with pytest.raises(IntegrityError), transaction.atomic():
            Projeto.objects.filter(pk=c["serie_x3"].pk).update(eh_nome_geral=True)

    def test_tela_projetos_recusa_serie_com_nome_geral(self, c):
        admin = UsuarioFactory(superuser=True)
        r = _client(admin).patch(f"/api/projetos/{c['serie_x3'].id}/", {"eh_nome_geral": True}, format="json")
        assert r.status_code == 400, r.data
        r = _client(admin).patch(f"/api/projetos/{c['geral_a'].id}/", {"eh_nome_geral": True}, format="json")
        assert r.status_code == 200, r.data
        assert r.data["eh_nome_geral"] is True

    def test_plano_anual_esconde_projeto_em_espera(self, c):
        liberar_par(c["m1"], c["serie_x3"])
        url = "/api/options/projetos/"
        params = {"exclude_kits": "true", "com_compra": "true"}
        cache.clear()
        # o superusuário vê tudo e a resposta dele não pode vazar para quem segue a regra (cache)
        admin_ids = _ids(_client(UsuarioFactory(superuser=True)).get(url, params))
        assert c["outro_y"].id in admin_ids
        ids = _ids(_client(c["coord"]).get(url, params))
        assert c["familia_x"].id in ids
        assert c["outro_y"].id not in ids
        assert c["solto_1"].id not in ids
        # sem com_compra (Compras, Ações, cadastros) nada muda
        assert c["outro_y"].id in _ids(_client(c["coord"]).get(url, {"exclude_kits": "true"}))

    def test_isento_ve_tudo_nas_listas(self, c):
        admin = UsuarioFactory(superuser=True)
        assert c["m3"].id in _municipios(admin, com_compra="true", projeto_id=c["familia_x"].id)
        assert c["outro_y"].id in _projetos(admin, com_compra="true")

    @pytest.mark.usefixtures("modo_uniao")  # grupo com capacidade: só vale no modo soma (PR 12)
    def test_capacidade_isenta_quem_a_tem(self, c):
        grupo = Group.objects.create(name="Teste Isencao Compra")
        PermissaoFuncional.objects.get(codename="create_solicitation_without_purchase").groups.add(grupo)
        c["coord"].groups.add(grupo)
        r = _post(c, c["coord"], c["m3"], c["outro_y"])
        assert r.status_code == 201, r.data
        assert c["m3"].id in _municipios(c["coord"], com_compra="true", projeto_id=c["outro_y"].id)
        assert _validate(c, c["coord"], c["m3"], c["outro_y"]).json()["ok"] is True

    def test_capacidade_nasce_sem_grupo(self):
        from apps.core.services.functional_permissions_seed import FUNCTIONAL_PERMISSIONS_SEED

        item = next(i for i in FUNCTIONAL_PERMISSIONS_SEED if i.codename == "create_solicitation_without_purchase")
        assert item.group_names == ()
        perm = PermissaoFuncional.objects.get(codename="create_solicitation_without_purchase")
        assert not perm.groups.exists()

    def test_pontos_da_regra_usam_o_service(self):
        """Sentinela estreita: os módulos da regra não leem nenhuma lista de compras por conta própria."""
        modulos = ("serializers/solicitacao.py", "views_validate.py", "views_lookup.py", "views_options.py")
        for rel in modulos:
            fonte = (_CORE / rel).read_text(encoding="utf-8")
            assert "compras__" not in fonte, rel
            for no in ast.walk(ast.parse(fonte)):
                if isinstance(no, ast.ImportFrom):
                    nomes = {a.name for a in no.names}
                    assert not nomes & {"Compra", "DATCompra"}, rel
            assert "compra_elegibilidade" in fonte, rel


# ============================================================================ guardas (já passam na main)


class TestGuardas:
    def test_lookup_municipios_projeto_inexistente_devolve_vazio(self, c):
        liberar_par(c["m1"], c["familia_x"])
        assert _municipios(c["coord"], com_compra="true", projeto_id=999_999) == set()

    def test_datcompra_inativa_nao_libera(self, c):
        liberar_par(c["m1"], c["familia_x"], ativo=False)
        r = _post(c, c["coord"], c["m1"], c["familia_x"])
        assert r.status_code == 400, r.data
        assert "municipio" in get_field_errors(r)

    def test_datcompra_quantidade_zero_nao_libera(self, c):
        liberar_par(c["m1"], c["familia_x"], quantidade=0)
        r = _post(c, c["coord"], c["m1"], c["familia_x"])
        assert r.status_code == 400, r.data
        assert "municipio" in get_field_errors(r)

    def test_compra_de_outra_colecao_da_mesma_gerencia_nao_libera_projeto_sem_marca(self, c):
        liberar_par(c["m1"], c["outro_y"])
        r = _post(c, c["coord"], c["m1"], c["familia_x"])
        assert r.status_code == 400, r.data
        assert "municipio" in get_field_errors(r)
        assert c["m1"].id not in _municipios(c["coord"], com_compra="true", projeto_id=c["familia_x"].id)

    def test_nome_geral_nao_libera_por_compra_de_outra_gerencia(self, c):
        Projeto.objects.filter(pk=c["geral_a"].pk).update(**_marca_se_existir())
        liberar_par(c["m1"], c["geral_b"])  # gerência B
        r = _post(c, c["coord"], c["m1"], c["geral_a"])
        assert r.status_code == 400, r.data
        assert "municipio" in get_field_errors(r)

    def test_projeto_sem_colecao_nao_e_liberado_por_compra_de_outro_projeto_sem_colecao(self, c):
        liberar_par(c["m1"], c["solto_2"])
        r = _post(c, c["coord"], c["m1"], c["solto_1"])
        assert r.status_code == 400, r.data
        assert "municipio" in get_field_errors(r)
        assert c["m1"].id not in _municipios(c["coord"], com_compra="true", projeto_id=c["solto_1"].id)
        assert c["solto_1"].id not in _projetos(c["coord"], com_compra="true")

    def test_nome_geral_sem_gerencia_nao_libera_por_compra_de_projeto_sem_gerencia(self, c):
        Projeto.objects.filter(pk=c["solto_1"].pk).update(**_marca_se_existir())
        liberar_par(c["m1"], c["solto_2"])
        r = _post(c, c["coord"], c["m1"], c["solto_1"])
        assert r.status_code == 400, r.data
        assert "municipio" in get_field_errors(r)
        assert c["solto_1"].id not in _projetos(c["coord"], com_compra="true")

    def test_edicao_trocando_para_par_sem_compra_400(self, c):
        liberar_par(c["m1"], c["familia_x"])
        s = _solicitacao(c, c["m1"], c["familia_x"])
        r = _client(c["coord"]).patch(f"/api/solicitacoes/{s.id}/", {"projeto": c["outro_y"].id}, format="json")
        assert r.status_code == 400, r.data
        assert "municipio" in get_field_errors(r)

    def test_edicao_mesmo_par_sem_compra_200(self, c):
        s = _solicitacao(c, c["m1"], c["outro_y"])
        r = _client(c["coord"]).patch(
            f"/api/solicitacoes/{s.id}/",
            {"municipio": c["m1"].id, "projeto": c["outro_y"].id, "observacoes": "mesmo par"},
            format="json",
        )
        assert r.status_code == 200, r.data

    def test_superusuario_continua_isento(self, c):
        admin = UsuarioFactory(superuser=True)
        r = _post(c, admin, c["m3"], c["outro_y"])
        assert r.status_code == 201, r.data
        assert _validate(c, admin, c["m3"], c["outro_y"]).json()["ok"] is True


def _marca_se_existir() -> dict[str, bool]:
    """A marca `eh_nome_geral` só existe depois deste PR; na main a guarda roda sem ela."""
    return {"eh_nome_geral": True} if any(f.name == "eh_nome_geral" for f in Projeto._meta.get_fields()) else {}


# ============================================================================ combo NL E AMMA (decisão do dono de 20/10)


@pytest.fixture
def combo(c):
    """As três coleções com os nomes reais (a migração 0045 já cria NOVO LENDO e PROJETO AMMA)."""
    col_combo, _ = ProjetoGeral.objects.get_or_create(nome="NL E AMMA PORT E MAT")
    col_nl, _ = ProjetoGeral.objects.get_or_create(nome="NOVO LENDO")
    col_amma, _ = ProjetoGeral.objects.get_or_create(nome="PROJETO AMMA")
    ga = c["ga"]
    return {
        "combo_1": ProjetoFactory(nome="Combo Ficticio 1", gerencia=ga, projeto_geral=col_combo, eh_serie=True),
        "novo_lendo": ProjetoFactory(nome="Novo Lendo Ficticio", gerencia=ga, projeto_geral=col_nl),
        "nl_1": ProjetoFactory(nome="Novo Lendo Ficticio 1", gerencia=ga, projeto_geral=col_nl, eh_serie=True),
        "amma": ProjetoFactory(nome="Projeto Amma Ficticio", gerencia=ga, projeto_geral=col_amma),
    }


class TestCombo:
    def test_tabela_tem_so_o_combo_decidido(self):
        from apps.core.services.compra_elegibilidade import COMBOS

        assert COMBOS == {"NL E AMMA PORT E MAT": ("NOVO LENDO", "PROJETO AMMA")}

    def test_compra_do_combo_libera_novo_lendo_e_amma_no_municipio(self, c, combo):
        from apps.core.services.compra_elegibilidade import par_liberado

        liberar_par(c["m1"], combo["combo_1"])
        for nome in ("novo_lendo", "nl_1", "amma"):
            assert par_liberado(c["m1"].id, combo[nome]) is True, nome
        r = _post(c, c["coord"], c["m1"], combo["novo_lendo"])
        assert r.status_code == 201, r.data
        # o segundo evento no mesmo horário daria conflito de agenda: o Amma vai pelo validate
        assert _validate(c, c["coord"], c["m1"], combo["amma"]).json()["ok"] is True

    def test_compra_do_combo_nao_libera_outro_municipio(self, c, combo):
        liberar_par(c["m1"], combo["combo_1"])
        r = _post(c, c["coord"], c["m2"], combo["novo_lendo"])
        assert r.status_code == 400, r.data
        assert "municipio" in get_field_errors(r)
        assert _municipios(c["coord"], com_compra="true", projeto_id=combo["amma"].id) == {c["m1"].id}

    def test_compra_do_combo_nao_libera_outros_projetos(self, c, combo):
        liberar_par(c["m1"], combo["combo_1"])
        r = _post(c, c["coord"], c["m1"], c["familia_x"])
        assert r.status_code == 400, r.data
        ids = _projetos(c["coord"], municipio_id=c["m1"].id)
        assert {combo["novo_lendo"].id, combo["amma"].id} <= ids
        assert not ids & {c[n].id for n in ("familia_x", "outro_y", "geral_a", "solto_1", "solto_2")}

    def test_combo_e_mao_unica(self, c, combo):
        """A compra de Novo Lendo não libera o Projeto Amma (nem o inverso pela coleção do combo)."""
        from apps.core.services.compra_elegibilidade import par_liberado

        liberar_par(c["m1"], combo["nl_1"])
        assert par_liberado(c["m1"].id, combo["novo_lendo"]) is True
        assert par_liberado(c["m1"].id, combo["amma"]) is False

    def test_as_tres_consultas_concordam_com_o_combo(self, c, combo):
        from apps.core.services.compra_elegibilidade import municipios_liberados, par_liberado, projetos_liberados

        liberar_par(c["m1"], combo["combo_1"])
        liberar_par(c["m2"], c["serie_x3"])
        esperado = {
            ("m1", "combo_1"),
            ("m1", "novo_lendo"),
            ("m1", "nl_1"),
            ("m1", "amma"),
            ("m2", "serie_x3"),
            ("m2", "familia_x"),
        }
        todos = {**combo, "familia_x": c["familia_x"], "serie_x3": c["serie_x3"], "outro_y": c["outro_y"]}
        chave = {c["m1"].id: "m1", c["m2"].id: "m2", c["m3"].id: "m3"}
        todos_m = Municipio.objects.filter(pk__in=chave)
        todos_p = Projeto.objects.filter(pk__in=[p.pk for p in todos.values()])
        for m in (c["m1"], c["m2"], c["m3"]):
            no_projeto = set(projetos_liberados(todos_p, m.id).values_list("pk", flat=True))
            for n, p in todos.items():
                por_par = par_liberado(m.id, p)
                por_municipio = municipios_liberados(todos_m, p).filter(pk=m.pk).exists()
                assert por_par == por_municipio == (p.pk in no_projeto), (chave[m.id], n)
                assert por_par == ((chave[m.id], n) in esperado), (chave[m.id], n)
        em_operacao = set(projetos_liberados(todos_p).values_list("pk", flat=True))
        assert em_operacao == {todos[n].pk for _, n in esperado}
