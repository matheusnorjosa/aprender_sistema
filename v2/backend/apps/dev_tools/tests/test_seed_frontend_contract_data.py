"""Tests for seed_frontend_contract_data deterministic behavior."""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from io import StringIO

from django.core.management import call_command

import pytest

from apps.core.models import (
    AcaoInstancia,
    AvailabilityBlock,
    Compra,
    DATAcao,
    DATCadastro,
    DATCompra,
    DATRegistro,
    Deslocamento,
    Gerencia,
    Municipio,
    NotificacaoInterna,
    Participation,
    PermissaoFuncional,
    PlanoFormacoes,
    Produto,
    Projeto,
    ProjetoGeral,
    Solicitacao,
    TipoEvento,
    Usuario,
)

SEED_EXTERNAL_HASH = "9" * 64
SEED_COMPRA_CODE = "MATRIX-PEND-001"
SEED_DAT_DESCRICAO = "KIT MATRIX CONTRACT"
SEED_DAT_USERNAME = "dat_matrix@test.com"
SEED_CONTROLE_USERNAME = "controle_e2e@test.com"


@pytest.fixture
def clean_contract_seed_state(db):
    """Keep seed_frontend_contract_data tests deterministic and independent.

    Also ensures RBAC seed data exists (xdist-safe: PermissaoFuncional
    may not have been created in this worker's DB state).
    """
    from django.core.management import call_command as _call

    # Ensure RBAC baseline exists (creates PermissaoFuncional records)
    _call("seed_rbac", verbosity=0)

    DATCompra.objects.filter(descricao_produto=SEED_DAT_DESCRICAO, ano_uso=2026).delete()
    Compra.objects.filter(external_hash=SEED_EXTERNAL_HASH).delete()
    Municipio.objects.filter(nome="Matrizopolis", uf="BA").delete()
    Usuario.objects.filter(username__in=[SEED_DAT_USERNAME, SEED_CONTROLE_USERNAME]).delete()
    yield
    DATCompra.objects.filter(descricao_produto=SEED_DAT_DESCRICAO, ano_uso=2026).delete()
    Compra.objects.filter(external_hash=SEED_EXTERNAL_HASH).delete()
    Municipio.objects.filter(nome="Matrizopolis", uf="BA").delete()
    Usuario.objects.filter(username__in=[SEED_DAT_USERNAME, SEED_CONTROLE_USERNAME]).delete()


def _run_seed_command() -> str:
    out = StringIO()
    call_command("seed_frontend_contract_data", stdout=out)
    return out.getvalue()


@pytest.mark.django_db
class TestSeedFrontendContractDataCommand:
    def test_seed_frontend_contract_data_is_idempotent(self, clean_contract_seed_state):
        """Running command twice should keep deterministic single rows."""
        output_first = _run_seed_command()
        output_second = _run_seed_command()

        assert "Seed funcional da matriz concluido" in output_first
        assert "Seed funcional da matriz concluido" in output_second

        projeto = Projeto.objects.get(codigo="E2E")
        municipio = Municipio.objects.get(nome="Matrizopolis", uf="BA")

        assert Compra.objects.filter(external_hash=SEED_EXTERNAL_HASH).count() == 1
        compra = Compra.objects.get(external_hash=SEED_EXTERNAL_HASH)
        assert compra.codigo == SEED_COMPRA_CODE
        assert compra.quantidade == 15
        assert compra.projeto_id == projeto.id
        assert compra.municipio_id == municipio.id

        assert (
            DATCompra.objects.filter(
                municipio=municipio,
                projeto=projeto,
                descricao_produto=SEED_DAT_DESCRICAO,
                ano_uso=2026,
            ).count()
            == 1
        )
        dat_compra = DATCompra.objects.get(
            municipio=municipio,
            projeto=projeto,
            descricao_produto=SEED_DAT_DESCRICAO,
            ano_uso=2026,
        )
        assert dat_compra.quantidade == 77
        assert dat_compra.ativo is True

        dat_user = Usuario.objects.get(username=SEED_DAT_USERNAME)
        assert dat_user.check_password("testpass123")
        assert set(dat_user.groups.values_list("name", flat=True)) == {"DAT"}
        assert PermissaoFuncional.objects.get(codename="view_compras_dashboard").groups.filter(name="DAT").exists()

        assert Usuario.objects.filter(username=SEED_CONTROLE_USERNAME).exists()


# Programa C (C0): a medição "sem rolagem horizontal" precisa de linhas com texto longo
# em toda tabela — tabela vazia nunca estoura largura e daria falso verde.
TEXTO_LONGO_MIN = 80


def _maior_texto(valores) -> int:
    return max((len(v or "") for v in valores), default=0)


@pytest.mark.django_db
class TestSeedFrontendContractDataTextosLongos:
    """Cada campo que aparece em tabela tem uma linha com 80+ caracteres, visível ao perfil que mede a tela."""

    @pytest.fixture(autouse=True)
    def _seed(self, clean_contract_seed_state):
        _run_seed_command()

    def test_superusuario_das_rotas_sem_grupo_existe(self):
        admin = Usuario.objects.get(username="admin_matrix@test.com")
        assert admin.is_superuser
        assert admin.check_password("testpass123")

    @pytest.mark.parametrize(
        ("rotulo", "valores"),
        [
            ("Municipio.nome", lambda: Municipio.objects.values_list("nome", flat=True)),
            ("Projeto.nome", lambda: Projeto.objects.values_list("nome", flat=True)),
            ("ProjetoGeral.nome", lambda: ProjetoGeral.objects.values_list("nome", flat=True)),
            ("Produto.nome", lambda: Produto.objects.values_list("nome", flat=True)),
            ("TipoEvento.nome", lambda: TipoEvento.objects.values_list("nome", flat=True)),
            ("Gerencia.nome_setor", lambda: Gerencia.objects.values_list("nome_setor", flat=True)),
            (
                "Usuario nome completo",
                lambda: [f"{u.first_name} {u.last_name}" for u in Usuario.objects.filter(is_superuser=False)],
            ),
            ("Usuario.cargo", lambda: Usuario.objects.values_list("cargo", flat=True)),
            (
                "Compra pendente (município)",
                lambda: Compra.objects.values_list("municipio__nome", flat=True),
            ),
            (
                "DATCompra com Produto (coluna Produto)",
                lambda: DATCompra.objects.filter(produto__isnull=False).values_list("produto__nome", flat=True),
            ),
            (
                "Solicitação pendente SUPER de coord_vidas (Minhas, Aprovações, Editar)",
                lambda: Solicitacao.objects.filter(
                    usuario__username="coord_vidas@test.com", status="pendente", projeto__fluxo="SUPER"
                ).values_list("encontro", flat=True),
            ),
            (
                "Solicitação aprovada com coord_vidas participando (Meus eventos)",
                lambda: Solicitacao.objects.filter(
                    status="aprovado", participations__usuario__username="coord_vidas@test.com"
                ).values_list("local", flat=True),
            ),
            (
                "Formador com usuário numa aprovada (Grade, Equipe)",
                lambda: [
                    f"{p.usuario.first_name} {p.usuario.last_name}"
                    for p in Participation.objects.filter(
                        role="FORMADOR", usuario__isnull=False, solicitacao__status="aprovado"
                    ).select_related("usuario")
                ],
            ),
            (
                "Bloqueio de coord_vidas (motivo)",
                lambda: AvailabilityBlock.objects.filter(usuario__username="coord_vidas@test.com").values_list(
                    "motivo", flat=True
                ),
            ),
            ("Deslocamento.origem", lambda: Deslocamento.objects.values_list("origem", flat=True)),
            (
                "DATAcao com coordenador",
                lambda: DATAcao.objects.filter(coordenador__isnull=False).values_list("coordenador__nome", flat=True),
            ),
            (
                "PlanoFormacoes com coordenador",
                lambda: [
                    f"{u.first_name} {u.last_name}"
                    for plano in PlanoFormacoes.objects.all()
                    for u in plano.coordenadores.all()
                ],
            ),
            (
                "DATCadastro FORMAR (aba padrão)",
                lambda: DATCadastro.objects.filter(plataforma="FORMAR").values_list("municipio__nome", flat=True),
            ),
            ("DATRegistro.obs_formar", lambda: DATRegistro.objects.values_list("obs_formar", flat=True)),
            (
                "Ação do ciclo (template)",
                lambda: AcaoInstancia.objects.values_list("template__nome", flat=True),
            ),
            (
                "Notificação interna do superusuário",
                lambda: NotificacaoInterna.objects.filter(destinatario__username="admin_matrix@test.com").values_list(
                    "titulo", flat=True
                ),
            ),
        ],
    )
    def test_campo_de_tabela_tem_texto_longo(self, rotulo, valores):
        assert _maior_texto(valores()) >= TEXTO_LONGO_MIN, f"{rotulo}: nenhuma linha com {TEXTO_LONGO_MIN}+ caracteres"

    def test_aprovada_futura_para_publicacao_e_dashboards(self):
        """Publicação lista aprovadas com início >= hoje; dashboards olham hoje±30."""
        from django.utils import timezone

        hoje = timezone.localdate()
        assert Solicitacao.objects.filter(status="aprovado", inicio__date__gte=hoje).exists()

    def test_formador_de_nome_longo_aparece_no_painel_de_equipe(self):
        """O painel de Equipe conta eventos pelo início nos últimos `days` dias (padrão da tela: 7)."""
        from rest_framework.test import APIClient

        client = APIClient()
        client.force_authenticate(user=Usuario.objects.get(username="admin_matrix@test.com"))
        resposta = client.get("/api/metrics/team/formadores/", {"days": 7})
        assert resposta.status_code == 200, resposta.data
        nomes = [f["nome"] for f in resposta.json()["formadores"]]
        assert any(nome.startswith("Aaa Maria Aparecida da Conceição") for nome in nomes), nomes

    def test_municipio_longo_tem_coordenadas_para_a_lista_do_mapa(self):
        """O Mapa (vista Lista) só mostra município com latitude e longitude."""
        municipio = Municipio.objects.get(nome__startswith="Aaa ", uf="BA")
        assert municipio.latitude is not None
        assert municipio.longitude is not None

    def test_matrizopolis_segue_pendente_no_dashboard(self):
        """O contrato funcional espera Matrizopolis nas pendências (sem solicitação ativa)."""
        assert not Solicitacao.objects.filter(
            municipio__nome="Matrizopolis", status__in=["pendente", "aprovado"]
        ).exists()
