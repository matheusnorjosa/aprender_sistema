"""
Feedback de uso da plataforma (pedido do dono, 11/11/2026).

Qualquer pessoa logada envia nota (1 a 5), tipo e comentário opcional pelo botão "Dar feedback";
o registro guarda quem enviou, a tela e a hora. Só o superusuário e o DAT leem e exportam, pela
capacidade `manage_admin_registries` (pacote ADMIN_OPERACIONAL).
"""

# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from rest_framework.test import APIClient

import pytest

from apps.core.models import Feedback, Usuario
from apps.core.rbac import user_has_any_perm
from apps.core.tests.factories import UsuarioFactory, com_pacote_do_controle, com_pacote_do_dat, com_papel

pytestmark = pytest.mark.django_db

URL = "/api/feedback/"
URL_EXPORTAR = "/api/feedback/exportar/"
FORTALEZA = ZoneInfo("America/Fortaleza")


def _cliente(usuario: Usuario | None = None) -> APIClient:
    client = APIClient()
    if usuario is not None:
        client.force_authenticate(user=usuario)
    return client


def _comum() -> Usuario:
    user = UsuarioFactory(first_name="Ana", last_name="Formadora")
    com_papel(user, "FORMADOR")
    assert not user_has_any_perm(user, "manage_admin_registries")
    return user


def _dat() -> Usuario:
    user = UsuarioFactory()
    com_pacote_do_dat(user)
    assert user_has_any_perm(user, "manage_admin_registries")
    return user


def _controle() -> Usuario:
    user = UsuarioFactory()
    com_pacote_do_controle(user)
    assert not user_has_any_perm(user, "manage_admin_registries")
    return user


def _valido(**extra: object) -> dict[str, object]:
    return {
        "nota": 4,
        "tipo": "SUGESTAO",
        "comentario": "Poderia filtrar por mês.",
        "pagina": "/solicitacoes/minhas",
        **extra,
    }


def _feedback(usuario: Usuario | None, quando: datetime, **extra: object) -> Feedback:
    dados: dict[str, object] = {"nota": 3, "tipo": "ELOGIO", "comentario": "", "pagina": "/", **extra}
    fb = Feedback.objects.create(usuario=usuario, **dados)
    Feedback.objects.filter(pk=fb.pk).update(created_at=quando)
    return fb


class TestEnviar:
    def test_usuario_comum_envia_e_grava_quem_e_onde(self) -> None:
        user = _comum()
        resp = _cliente(user).post(URL, _valido(), format="json")

        assert resp.status_code == 201, resp.content
        fb = Feedback.objects.get()
        assert fb.usuario_id == user.pk
        assert fb.pagina == "/solicitacoes/minhas"
        assert (fb.nota, fb.tipo, fb.comentario) == (4, "SUGESTAO", "Poderia filtrar por mês.")
        assert fb.created_at is not None

    def test_comentario_e_opcional(self) -> None:
        resp = _cliente(_comum()).post(URL, _valido(comentario=""), format="json")
        assert resp.status_code == 201, resp.content
        resp = _cliente(_comum()).post(URL, {"nota": 5, "tipo": "ELOGIO", "pagina": "/"}, format="json")
        assert resp.status_code == 201, resp.content

    def test_usuario_do_corpo_e_ignorado(self) -> None:
        user = _comum()
        outro = UsuarioFactory()
        resp = _cliente(user).post(URL, _valido(usuario=outro.pk), format="json")
        assert resp.status_code == 201
        assert Feedback.objects.get().usuario_id == user.pk

    def test_pagina_sem_query_string_e_truncada(self) -> None:
        user = _comum()
        resp = _cliente(user).post(URL, _valido(pagina="/dat/registros?cpf=123#topo"), format="json")
        assert resp.status_code == 201, resp.content
        assert Feedback.objects.get().pagina == "/dat/registros"

        longa = "/" + "a" * 500
        resp = _cliente(user).post(URL, _valido(pagina=longa), format="json")
        assert resp.status_code == 201, resp.content
        assert Feedback.objects.latest("id").pagina == longa[:200]

    @pytest.mark.parametrize("pagina", ["", "solicitacoes", "https://evil.example/x"])
    def test_pagina_tem_de_ser_rota(self, pagina: str) -> None:
        resp = _cliente(_comum()).post(URL, _valido(pagina=pagina), format="json")
        assert resp.status_code == 400
        assert not Feedback.objects.exists()

    @pytest.mark.parametrize("nota", [0, 6, -1, None, "x"])
    def test_nota_fora_de_1_a_5(self, nota: object) -> None:
        resp = _cliente(_comum()).post(URL, _valido(nota=nota), format="json")
        assert resp.status_code == 400
        assert not Feedback.objects.exists()

    def test_nota_obrigatoria(self) -> None:
        dados = _valido()
        del dados["nota"]
        assert _cliente(_comum()).post(URL, dados, format="json").status_code == 400

    @pytest.mark.parametrize("tipo", ["", "RECLAMACAO", "elogio", None])
    def test_tipo_invalido(self, tipo: object) -> None:
        resp = _cliente(_comum()).post(URL, _valido(tipo=tipo), format="json")
        assert resp.status_code == 400
        assert not Feedback.objects.exists()

    def test_comentario_ate_2000(self) -> None:
        user = _comum()
        assert _cliente(user).post(URL, _valido(comentario="a" * 2000), format="json").status_code == 201
        assert _cliente(user).post(URL, _valido(comentario="a" * 2001), format="json").status_code == 400
        assert Feedback.objects.count() == 1

    def test_sem_sessao_nao_envia(self) -> None:
        resp = _cliente().post(URL, _valido(), format="json")
        assert resp.status_code in (401, 403)
        assert not Feedback.objects.exists()

    def test_nota_fora_da_faixa_barrada_tambem_no_banco(self) -> None:
        from django.db import IntegrityError, transaction

        with pytest.raises(IntegrityError), transaction.atomic():
            Feedback.objects.create(usuario=None, nota=6, tipo="ELOGIO", pagina="/")


class TestQuemVe:
    @pytest.mark.parametrize("url", [URL, URL_EXPORTAR])
    def test_usuario_comum_nao_ve(self, url: str) -> None:
        assert _cliente(_comum()).get(url).status_code == 403

    @pytest.mark.parametrize("url", [URL, URL_EXPORTAR])
    def test_controle_nao_ve(self, url: str) -> None:
        # O pacote CONTROLE administra compras, não a plataforma.
        assert _cliente(_controle()).get(url).status_code == 403

    @pytest.mark.parametrize("url", [URL, URL_EXPORTAR])
    def test_sem_sessao_nao_ve(self, url: str) -> None:
        assert _cliente().get(url).status_code in (401, 403)

    @pytest.mark.parametrize("url", [URL, URL_EXPORTAR])
    def test_dat_ve(self, url: str) -> None:
        assert _cliente(_dat()).get(url).status_code == 200

    @pytest.mark.parametrize("url", [URL, URL_EXPORTAR])
    def test_superusuario_ve(self, url: str) -> None:
        assert _cliente(UsuarioFactory(superuser=True)).get(url).status_code == 200


class TestLista:
    def test_lista_mostra_nome_e_nunca_cpf(self) -> None:
        autor = _comum()
        _feedback(autor, datetime(2026, 11, 10, 9, 0, tzinfo=FORTALEZA), comentario="Tela clara")

        resp = _cliente(_dat()).get(URL)

        assert resp.status_code == 200
        item = resp.json()["results"][0]
        assert item["pessoa"] == "Ana Formadora"
        assert item["comentario"] == "Tela clara"
        assert set(item) == {"id", "pessoa", "nota", "tipo", "comentario", "pagina", "created_at"}
        assert autor.cpf not in resp.content.decode()
        assert autor.username not in resp.content.decode()

    def test_mais_recente_primeiro(self) -> None:
        antigo = _feedback(None, datetime(2026, 11, 1, 9, 0, tzinfo=FORTALEZA))
        novo = _feedback(None, datetime(2026, 11, 10, 9, 0, tzinfo=FORTALEZA))
        ids = [r["id"] for r in _cliente(_dat()).get(URL).json()["results"]]
        assert ids == [novo.pk, antigo.pk]

    def test_pessoa_removida(self) -> None:
        _feedback(None, datetime(2026, 11, 10, 9, 0, tzinfo=FORTALEZA))
        assert _cliente(_dat()).get(URL).json()["results"][0]["pessoa"] == "Usuário removido"

    def test_filtros_tipo_e_nota(self) -> None:
        quando = datetime(2026, 11, 10, 9, 0, tzinfo=FORTALEZA)
        alvo = _feedback(None, quando, tipo="PROBLEMA", nota=1)
        _feedback(None, quando, tipo="PROBLEMA", nota=5)
        _feedback(None, quando, tipo="ELOGIO", nota=1)

        resp = _cliente(_dat()).get(URL, {"tipo": "PROBLEMA", "nota": 1})

        assert [r["id"] for r in resp.json()["results"]] == [alvo.pk]

    def test_filtro_periodo_pelo_dia_de_fortaleza(self) -> None:
        # 23:30 de 09/11 em Fortaleza já é 10/11 em UTC: conta como dia 09.
        dia_9 = _feedback(None, datetime(2026, 11, 9, 23, 30, tzinfo=FORTALEZA))
        dia_10 = _feedback(None, datetime(2026, 11, 10, 8, 0, tzinfo=FORTALEZA))
        _feedback(None, datetime(2026, 11, 11, 0, 30, tzinfo=FORTALEZA))
        _feedback(None, datetime(2026, 11, 8, 12, 0, tzinfo=FORTALEZA))

        resp = _cliente(_dat()).get(URL, {"desde": "2026-11-09", "ate": "2026-11-10"})

        assert sorted(r["id"] for r in resp.json()["results"]) == sorted([dia_9.pk, dia_10.pk])


class TestExportar:
    def test_csv_com_nome_sem_cpf_e_sanitizado(self) -> None:
        autor = _comum()
        _feedback(
            autor,
            datetime(2026, 11, 10, 9, 5, tzinfo=FORTALEZA),
            tipo="DUVIDA",
            nota=2,
            comentario='=HYPERLINK("http://x")',
            pagina="/dat/registros",
        )

        resp = _cliente(UsuarioFactory(superuser=True)).get(URL_EXPORTAR)

        assert resp.status_code == 200
        assert resp["Content-Type"].startswith("text/csv")
        assert "attachment" in resp["Content-Disposition"]
        texto = resp.content.decode("utf-8-sig")
        linhas = texto.strip().splitlines()
        assert linhas[0] == "Data,Pessoa,Nota,Tipo,Tela,Comentário"
        assert linhas[1].startswith("10/11/2026 09:05,Ana Formadora,2,Dúvida,/dat/registros,")
        assert "'=HYPERLINK" in linhas[1]
        assert autor.cpf not in texto
        assert autor.username not in texto

    def test_csv_respeita_filtros(self) -> None:
        quando = datetime(2026, 11, 10, 9, 0, tzinfo=FORTALEZA)
        _feedback(None, quando, tipo="ELOGIO", comentario="gostei")
        _feedback(None, quando, tipo="PROBLEMA", comentario="quebrou")

        texto = _cliente(_dat()).get(URL_EXPORTAR, {"tipo": "PROBLEMA"}).content.decode("utf-8-sig")

        assert "quebrou" in texto
        assert "gostei" not in texto
