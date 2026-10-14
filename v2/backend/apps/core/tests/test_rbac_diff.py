"""
PR 1 da arquitetura de permissões (06/10/2026): simulador `rbac_diff`, somente leitura.

Antes de cada PR que muda poder, o dono vê quem ganha e quem perde. O serviço
`rbac_snapshot` tira um retrato do poder de cada pessoa ATIVA a partir do banco real
(superusuário, grupos, capacidades, policies, gerências de escopo e vínculos) e compara
dois retratos. `capacidades_de` é o ponto em que os PRs seguintes simulam a fórmula nova.

Regras que estes testes travam:
- nada é gravado: nem banco, nem cache (o cache de permissão funcional fica intacto);
- nenhum dado pessoal sai: só `u<id>`, ids de gerência, nomes de grupo e codenames
  (username é o CPF em produção).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownLambdaType=false

from __future__ import annotations

import json
import re
from datetime import timedelta
from io import StringIO
from pathlib import Path
from typing import Any

from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.management import CommandError, call_command
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

import pytest

from apps.core.models import EquipeGerencia, Gerencia, Usuario
from apps.core.rbac.policies import PUBLIC_POLICY_KEYS, resolve_public_policies
from apps.core.services.rbac_permissions import get_user_functional_permissions
from apps.core.services.rbac_snapshot import (
    capacidades_de_hoje,
    diagnostico_de_lotacao,
    diff_snapshots,
    snapshot_de_poder,
)
from apps.core.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _cache_limpo():
    cache.clear()
    yield
    cache.clear()


def _so(*usuarios: Usuario):
    return Usuario.objects.filter(id__in=[u.id for u in usuarios])


def _gerencia(nome: str, setor: str) -> Gerencia:
    return Gerencia.objects.create(nome=nome, nome_setor=setor, setor_canonico=setor)


def _gerencia_real(nome: str, setor_canonico: str = "") -> Gerencia:
    """Gerência com o `nome` (código interno) de produção e o `setor_canonico` do vocabulário real."""
    g, _ = Gerencia.objects.get_or_create(nome=nome, defaults={"nome_setor": nome})
    g.setor_canonico = setor_canonico
    g.save(update_fields=["setor_canonico"])
    return g


def _vincula(usuario: Usuario, gerencia: Gerencia, papel: str, **extra: Any) -> EquipeGerencia:
    return EquipeGerencia.objects.create(usuario=usuario, gerencia=gerencia, papel=papel, ativo=True, **extra)


def _rbac_diff(*args: str) -> str:
    out = StringIO()
    call_command("rbac_diff", *args, stdout=out)
    return out.getvalue()


def _tem_uid(texto: str, usuario: Usuario) -> bool:
    return re.search(rf"\bu{usuario.id}\b", texto) is not None


def _pessoa(**campos: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "superusuario": False,
        "grupos": [],
        "capacidades": [],
        "policies": [],
        "gerencias_escopo": [],
        "vinculos": [],
    }
    base.update(campos)
    return base


class TestSnapshot:
    def test_usuario_de_grupo_tem_as_capacidades_e_policies_do_grupo(self):
        u = UsuarioFactory(groups=["DAT"])

        p = snapshot_de_poder(usuarios=_so(u))[f"u{u.id}"]

        assert p["superusuario"] is False
        assert p["grupos"] == ["DAT"]
        assert "manage_admin_registries" in p["capacidades"]
        assert p["capacidades"] == sorted(p["capacidades"])
        assert "manage_admin_registries" in p["policies"]
        # Sem simulação, as policies são as de hoje (mesma SSOT do /api/me/policies/).
        assert p["policies"] == resolve_public_policies(u)

    def test_superusuario_tem_todas_as_policies_publicas(self):
        u = UsuarioFactory(superuser=True)

        p = snapshot_de_poder(usuarios=_so(u))[f"u{u.id}"]

        assert p["superusuario"] is True
        assert p["policies"] == sorted(PUBLIC_POLICY_KEYS)

    def test_so_entram_usuarios_ativos(self):
        ativo = UsuarioFactory()
        inativo = UsuarioFactory(is_active=False)

        assert set(snapshot_de_poder(usuarios=_so(ativo, inativo))) == {f"u{ativo.id}"}
        tudo = snapshot_de_poder()
        assert f"u{ativo.id}" in tudo
        assert f"u{inativo.id}" not in tudo

    def test_vinculo_equipe_aparece_em_vinculos_mas_nao_no_escopo(self):
        dat = _gerencia("GER DAT SNAP", "DAT")
        vidas = _gerencia("GER VIDAS SNAP", "Vidas")
        u = UsuarioFactory()
        _vincula(u, dat, "EQUIPE")
        _vincula(u, vidas, "COORDENADOR")

        p = snapshot_de_poder(usuarios=_so(u))[f"u{u.id}"]

        assert p["vinculos"] == sorted([[dat.id, "EQUIPE"], [vidas.id, "COORDENADOR"]])
        assert p["gerencias_escopo"] == [vidas.id]

    def test_vinculo_vencido_fica_fora(self):
        vidas = _gerencia("GER VIDAS VENC", "Vidas")
        u = UsuarioFactory()
        ontem = timezone.localdate() - timedelta(days=1)
        _vincula(u, vidas, "FORMADOR", valid_from=ontem - timedelta(days=30), valid_to=ontem)

        p = snapshot_de_poder(usuarios=_so(u))[f"u{u.id}"]

        assert p["vinculos"] == []
        assert p["gerencias_escopo"] == []

    def test_capacidades_de_customizado_muda_capacidades_e_as_policies_que_dependem_delas(self):
        vidas = _gerencia("GER VIDAS SIM", "Vidas")
        u = UsuarioFactory(groups=["Formador"])
        _vincula(u, vidas, "FORMADOR")

        hoje = snapshot_de_poder(usuarios=_so(u))[f"u{u.id}"]
        simulado = snapshot_de_poder(usuarios=_so(u), capacidades_de=lambda _u: {"manage_admin_registries"})[f"u{u.id}"]

        assert simulado["capacidades"] == ["manage_admin_registries"]
        assert "manage_admin_registries" not in hoje["policies"]
        assert "manage_admin_registries" in simulado["policies"]
        for campo in ("superusuario", "grupos", "gerencias_escopo", "vinculos"):
            assert simulado[campo] == hoje[campo], campo

    def test_capacidades_de_hoje_igual_a_fonte_da_api(self):
        # Trava de paridade: se a fórmula de `get_user_functional_permissions` mudar (PR 11)
        # e o padrão do simulador não, o `--comparar` pós-deploy mostraria o poder antigo.
        # Desde o PR B as duas chamam `capacidades_sem_cache` (grupos ∪ pacote do perfil).
        vidas = _gerencia_real("GERENCIA 2", "Vidas")
        dat = _gerencia_real("GERENCIA DAT", "DAT")
        dat.perfil = Gerencia.Perfil.ADMIN_OPERACIONAL
        dat.save()
        com_grupo = UsuarioFactory(groups=["DAT", "Coordenador"])
        sem_grupo = UsuarioFactory()
        com_vinculo = UsuarioFactory(groups=["Formador"])
        com_pacote = UsuarioFactory()
        _vincula(com_vinculo, vidas, "FORMADOR")
        _vincula(sem_grupo, vidas, "EQUIPE")
        _vincula(com_pacote, dat, "EQUIPE")

        for u in (com_grupo, sem_grupo, com_vinculo, com_pacote):
            cache.clear()
            assert capacidades_de_hoje(u) == get_user_functional_permissions(u), u.id
        assert capacidades_de_hoje(com_grupo)
        assert capacidades_de_hoje(com_pacote)


class TestDiff:
    def test_detecta_ganho_e_perda_por_campo(self):
        antes = {"u1": _pessoa(capacidades=["a", "b"], vinculos=[[3, "FORMADOR"]], grupos=["DAT"])}
        depois = {"u1": _pessoa(capacidades=["b", "c"], vinculos=[[3, "EQUIPE"]], grupos=["DAT"])}

        d = diff_snapshots(antes, depois)

        assert d["pessoas"]["u1"]["capacidades"] == {"ganha": ["c"], "perde": ["a"]}
        assert d["pessoas"]["u1"]["vinculos"] == {"ganha": [[3, "EQUIPE"]], "perde": [[3, "FORMADOR"]]}
        assert "grupos" not in d["pessoas"]["u1"]
        assert d["resumo"] == {"ganhos": 2, "perdas": 2, "pessoas_com_mudanca": 1, "entram": 0, "saem": 0}

    def test_sem_diferenca(self):
        snap = {"u1": _pessoa(capacidades=["a"]), "u2": _pessoa(superusuario=True)}

        d = diff_snapshots(snap, json.loads(json.dumps(snap)))

        assert d["pessoas"] == {}
        assert d["resumo"] == {"ganhos": 0, "perdas": 0, "pessoas_com_mudanca": 0, "entram": 0, "saem": 0}

    def test_quem_entra_ganha_tudo_e_quem_sai_perde_tudo(self):
        antes = {"u1": _pessoa(grupos=["Controle"], gerencias_escopo=[7])}
        depois = {"u2": _pessoa(capacidades=["a"], policies=["p"])}

        d = diff_snapshots(antes, depois)

        assert d["entram"] == ["u2"]
        assert d["saem"] == ["u1"]
        assert d["pessoas"]["u2"] == {
            "capacidades": {"ganha": ["a"], "perde": []},
            "policies": {"ganha": ["p"], "perde": []},
        }
        assert d["pessoas"]["u1"] == {
            "grupos": {"ganha": [], "perde": ["Controle"]},
            "gerencias_escopo": {"ganha": [], "perde": [7]},
        }
        assert d["resumo"]["ganhos"] == 2
        assert d["resumo"]["perdas"] == 2

    def test_virar_superusuario_e_ganho(self):
        d = diff_snapshots({"u1": _pessoa()}, {"u1": _pessoa(superusuario=True)})

        assert d["pessoas"]["u1"]["superusuario"] == {"ganha": ["superusuario"], "perde": []}

    def test_pessoas_em_ordem_numerica(self):
        antes: dict[str, Any] = {}
        depois = {"u10": _pessoa(grupos=["DAT"]), "u9": _pessoa(grupos=["DAT"])}

        assert list(diff_snapshots(antes, depois)["pessoas"]) == ["u9", "u10"]


class TestDiagnostico:
    def test_lista_quem_tem_grupo_de_setor_sem_vinculo_na_gerencia_do_setor(self):
        dat = _gerencia_real("GERENCIA DAT")
        vidas = _gerencia_real("GERENCIA 2", "Vidas")
        com_vinculo = UsuarioFactory(groups=["DAT"])
        _vincula(com_vinculo, dat, "EQUIPE")
        sem_vinculo = UsuarioFactory(groups=["DAT"])
        vinculo_noutro_setor = UsuarioFactory(groups=["DAT"])
        _vincula(vinculo_noutro_setor, vidas, "FORMADOR")
        inativo = UsuarioFactory(groups=["DAT"], is_active=False)

        sem = diagnostico_de_lotacao()["grupo_de_setor_sem_vinculo"]["DAT"]

        assert f"u{sem_vinculo.id}" in sem
        assert f"u{vinculo_noutro_setor.id}" in sem
        assert f"u{com_vinculo.id}" not in sem
        assert f"u{inativo.id}" not in sem

    def test_setor_sem_gerencia_lista_todos_do_grupo(self):
        controle = UsuarioFactory(groups=["Controle"])

        diag = diagnostico_de_lotacao()

        assert f"u{controle.id}" in diag["grupo_de_setor_sem_vinculo"]["Controle"]

    def test_brincando_casa_com_a_gerencia_pelo_nome_e_nao_pelo_setor_canonico(self):
        # setor_canonico usa o vocabulário de produto ("Brincando e Aprendendo"), não o nome do grupo.
        brincando = _gerencia_real("GERENCIA BRINCANDO", "Brincando e Aprendendo")
        lotado = UsuarioFactory(groups=["Brincando"])
        _vincula(lotado, brincando, "FORMADOR")
        solto = UsuarioFactory(groups=["Brincando"])

        diag = diagnostico_de_lotacao()

        sem = diag["grupo_de_setor_sem_vinculo"].get("Brincando", [])
        assert f"u{lotado.id}" not in sem
        assert f"u{solto.id}" in sem
        assert brincando.id in diag["gerencias_por_setor"]["Brincando"]

    def test_dat_casa_com_a_gerencia_dat_mesmo_com_setor_canonico_vazio(self):
        dat = _gerencia_real("GERENCIA DAT", "")
        lotado = UsuarioFactory(groups=["DAT"])
        _vincula(lotado, dat, "EQUIPE")

        diag = diagnostico_de_lotacao()

        assert f"u{lotado.id}" not in diag["grupo_de_setor_sem_vinculo"].get("DAT", [])
        assert diag["gerencias_por_setor"]["DAT"] == [dat.id]

    def test_setor_sem_gerencia_mapeada_nao_lista_ninguem_como_sem_vinculo(self):
        comercial = UsuarioFactory(groups=["Comercial"])

        diag = diagnostico_de_lotacao()

        assert "Comercial" not in diag["grupo_de_setor_sem_vinculo"]
        assert diag["setores_sem_gerencia_mapeada"]["Comercial"] >= 1
        assert f"u{comercial.id}" not in json.dumps(diag)

    def test_setor_canonico_das_gerencias_e_controle_diretoria(self):
        dat = _gerencia("GER DAT SETOR", "DAT")
        sem_setor = Gerencia.objects.create(nome="GER SEM SETOR", nome_setor="X")

        diag = diagnostico_de_lotacao()

        assert diag["setor_canonico"][str(dat.id)] == "DAT"
        assert diag["setor_canonico"][str(sem_setor.id)] == ""
        assert diag["gerencias_controle_diretoria"]["CONTROLE"] == []
        controle = Gerencia.objects.create(nome="CONTROLE", nome_setor="Controle")
        assert diagnostico_de_lotacao()["gerencias_controle_diretoria"]["CONTROLE"] == [controle.id]

    def test_conta_pessoas_com_mais_de_um_vinculo_vigente(self):
        g_a = _gerencia("GER A MULTI", "Vidas")
        g_b = _gerencia("GER B MULTI", "Fluir")
        antes = diagnostico_de_lotacao()
        duas_gerencias = UsuarioFactory()
        _vincula(duas_gerencias, g_a, "COORDENADOR")
        _vincula(duas_gerencias, g_b, "FORMADOR")
        dois_papeis = UsuarioFactory()
        _vincula(dois_papeis, g_a, "GERENTE")
        _vincula(dois_papeis, g_a, "FORMADOR")
        _vincula(UsuarioFactory(), g_a, "FORMADOR")

        diag = diagnostico_de_lotacao()

        assert diag["pessoas_com_mais_de_um_vinculo"] == antes["pessoas_com_mais_de_um_vinculo"] + 2
        assert diag["pessoas_em_mais_de_uma_gerencia"] == antes["pessoas_em_mais_de_uma_gerencia"] + 1


class TestComando:
    def test_salvar_e_comparar_sem_mudanca(self, tmp_path: Path):
        u = UsuarioFactory(groups=["DAT"])
        arq = tmp_path / "antes.json"

        saida = _rbac_diff("--salvar", str(arq))

        dados = json.loads(arq.read_text(encoding="utf-8"))
        assert f"u{u.id}" in dados
        assert "gravado" in saida
        assert "rbac_diff: 0 ganhos, 0 perdas" in _rbac_diff("--comparar", str(arq))

    def test_arquivo_e_estavel(self, tmp_path: Path):
        UsuarioFactory(groups=["DAT"])
        a, b = tmp_path / "a.json", tmp_path / "b.json"

        _rbac_diff("--salvar", str(a))
        _rbac_diff("--salvar", str(b))

        assert a.read_bytes() == b.read_bytes()

    def test_comparar_com_o_banco_mostra_quem_ganha_e_quem_perde(self, tmp_path: Path):
        ganha = UsuarioFactory()
        perde = UsuarioFactory(groups=["Diretoria"])
        parado = UsuarioFactory(groups=["DAT"])
        arq = tmp_path / "antes.json"
        _rbac_diff("--salvar", str(arq))
        ganha.groups.add(Group.objects.get(name="DAT"))
        perde.groups.clear()

        saida = _rbac_diff("--comparar", str(arq))

        assert _tem_uid(saida, ganha)
        assert _tem_uid(saida, perde)
        assert not _tem_uid(saida, parado)
        assert "+ grupos: DAT" in saida
        assert "− grupos: Diretoria" in saida
        assert "rbac_diff: 0 ganhos, 0 perdas" not in saida

    def test_salvar_em_lugar_sem_escrita_da_erro_legivel(self, tmp_path: Path):
        # Em prod a raiz do container é só leitura (só /tmp aceita escrita): sem traceback cru.
        destino = tmp_path / "nao_existe" / "antes.json"

        with pytest.raises(CommandError, match="não consegui gravar"):
            _rbac_diff("--salvar", str(destino))

    def test_comparar_dois_arquivos(self, tmp_path: Path):
        antes, depois = tmp_path / "antes.json", tmp_path / "depois.json"
        antes.write_text(json.dumps({"u1": _pessoa()}), encoding="utf-8")
        depois.write_text(json.dumps({"u1": _pessoa(capacidades=["approve_solicitation"])}), encoding="utf-8")

        saida = _rbac_diff("--comparar", str(antes), "--depois", str(depois))

        assert "u1" in saida
        assert "+ capacidades: approve_solicitation" in saida
        assert "rbac_diff: 1 ganhos, 0 perdas" in saida

    def test_diagnostico_imprime_as_medicoes(self):
        dat = _gerencia_real("GERENCIA DAT", "DAT")
        sem_vinculo = UsuarioFactory(groups=["DAT"])
        UsuarioFactory(groups=["Comercial"])

        saida = _rbac_diff("--diagnostico")

        assert f"g{dat.id}: DAT" in saida
        assert "CONTROLE: não existe" in saida
        assert "DIRETORIA: não existe" in saida
        assert "mais de um vínculo vigente" in saida
        linha_dat = next(linha for linha in saida.splitlines() if linha.strip().startswith("DAT ("))
        assert f"g{dat.id}" in linha_dat
        assert _tem_uid(linha_dat, sem_vinculo)
        linha_comercial = next(linha for linha in saida.splitlines() if linha.strip().startswith("Comercial"))
        assert "sem gerência mapeada" in linha_comercial


class TestSomenteLeituraESemDadoPessoal:
    def test_nenhum_dado_pessoal_nas_saidas(self, tmp_path: Path):
        dat = _gerencia("GER DAT PII", "DAT")
        u = UsuarioFactory(
            username="98765432100",
            cpf="98765432100",
            email="pessoa.secreta@example.com",
            first_name="Fulana",
            last_name="Sigilosa",
            telefone="85911112222",
            groups=["DAT"],
        )
        _vincula(u, dat, "EQUIPE")
        arq = tmp_path / "antes.json"

        saidas = [
            json.dumps(snapshot_de_poder(), ensure_ascii=False),
            _rbac_diff("--salvar", str(arq)),
            arq.read_text(encoding="utf-8"),
            _rbac_diff("--diagnostico"),
        ]
        u.groups.clear()
        saidas.append(_rbac_diff("--comparar", str(arq)))

        tudo = "\n".join(saidas)
        assert _tem_uid(tudo, u)
        for dado in ("98765432100", "pessoa.secreta", "Fulana", "Sigilosa", "85911112222"):
            assert dado not in tudo, dado

    def test_nada_e_gravado_no_banco_nem_no_cache(self, tmp_path: Path):
        dat = _gerencia("GER DAT RO", "DAT")
        u = UsuarioFactory(groups=["DAT"])
        _vincula(u, dat, "EQUIPE")
        UsuarioFactory(superuser=True)
        arq = tmp_path / "antes.json"
        cache.clear()

        with CaptureQueriesContext(connection) as ctx:
            snap = snapshot_de_poder()
            diff_snapshots(snap, snap)
            diagnostico_de_lotacao()
            _rbac_diff("--salvar", str(arq))
            _rbac_diff("--comparar", str(arq))
            _rbac_diff("--diagnostico")

        escritas = [q["sql"] for q in ctx.captured_queries if re.match(r"\s*(INSERT|UPDATE|DELETE)\b", q["sql"], re.I)]
        assert escritas == []
        assert cache.keys("*") == []
