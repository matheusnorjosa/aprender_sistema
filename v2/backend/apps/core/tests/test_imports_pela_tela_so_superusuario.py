"""
Importação pela tela é só do superusuário (decisão do dono, 02/10/2026).

Nenhum perfil importa planilha pela tela na liberação: as cargas passam por script, com ensaio.
As 13 rotas de upload (12 endpoints + 1 alias) exigem ``SuperuserOnly``; nenhuma capability
(``import_spreadsheet``, ``manage_admin_registries``, ``run_daily_operations``) dá acesso. O command de terminal
``import_export_contract`` não passa por estes endpoints e não muda.

Substitui a matriz do PR-A1 DAT-Imports (2026-04-29), que fixava "DAT importa" em 6 deles.

Endpoints cobertos:
- POST /api/controle/import-compras/ e o alias /api/import-compras/
- POST /api/controle/import-acoes/
- POST /api/dat/import-cadastros/
- POST /api/disponibilidade/import-bloqueios/
- POST /api/deslocamentos/import/
- POST /api/solicitacoes/import/
- POST /api/usuarios/import/
- POST /api/produtos/import/
- POST /api/municipios/import/
- POST /api/colecoes/import/
- POST /api/equipe-gerencia/import/
- POST /api/imports/bloqueios/ (assíncrono, ASQ-005)

Cada perfil é testado contra todos os endpoints; a falha mostra o endpoint no id do parametrize.
A sentinela no fim cobra que view nova que receba arquivo entre aqui (os sinais estão em
``_recebe_arquivo``).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportMissingTypeStubs=false, reportUnusedFunction=false

from __future__ import annotations

import inspect
import io
import itertools

from django.urls import get_resolver, include, path
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.parsers import FileUploadParser, FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.routers import SimpleRouter
from rest_framework.serializers import FileField, Serializer
from rest_framework.test import APIClient
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

import pytest

from apps.core.models import Usuario
from apps.core.permissions import SuperuserOnly
from apps.core.tests.factories import GroupFactory, UsuarioFactory

pytestmark = pytest.mark.django_db


ENDPOINTS_DE_IMPORT: list[str] = [
    "/api/controle/import-compras/",
    "/api/import-compras/",
    "/api/controle/import-acoes/",
    "/api/dat/import-cadastros/",
    "/api/disponibilidade/import-bloqueios/",
    "/api/deslocamentos/import/",
    "/api/solicitacoes/import/",
    "/api/usuarios/import/",
    "/api/produtos/import/",
    "/api/municipios/import/",
    "/api/colecoes/import/",
    "/api/equipe-gerencia/import/",
    "/api/imports/bloqueios/",
]


# Atomic counter (memória `feedback_deterministic_unique_in_pytest.md`):
# evita colisão de CPF entre tests parametrizados, sem depender de hash().
_CPF_COUNTER = itertools.count(80000000000)


def _file(content: bytes = b"x", name: str = "f.csv") -> io.BytesIO:
    f = io.BytesIO(content)
    f.name = name
    return f


def _user_in_groups(*group_names: str, username: str = "u") -> Usuario:
    cpf = str(next(_CPF_COUNTER)).zfill(11)
    user = UsuarioFactory(
        username=f"{username}_{cpf}",
        email=f"{username}_{cpf}@x.com",
        password="x",
        cpf=cpf,
    )
    for name in group_names:
        group = GroupFactory(name=name)
        user.groups.add(group)
    return user


def _post(user: Usuario | None, endpoint: str):
    client = APIClient()
    if user is not None:
        client.force_authenticate(user=user)
    return client.post(endpoint + "?dry_run=true", {"file": _file()}, format="multipart")


# ============================================================================
# Todo perfil que não é superusuário → 403 (inclusive o DAT, que antes importava)
# ============================================================================


PERSONAS_FORBIDDEN: list[tuple[str, tuple[str, ...]]] = [
    ("dat", ("DAT",)),
    ("controle_puro", ("Controle",)),
    ("superintendencia", ("Superintendência",)),
    ("gerente", ("Gerente",)),
    ("coordenador", ("Coordenador",)),
    ("apoio", ("Apoio de Coordenação",)),
    ("formador", ("Formador",)),
    ("diretoria", ("Diretoria",)),
    ("controle_mais_gerente", ("Controle", "Gerente")),
    ("dat_mais_controle", ("DAT", "Controle")),
]


@pytest.mark.parametrize("endpoint", ENDPOINTS_DE_IMPORT)
@pytest.mark.parametrize("persona", PERSONAS_FORBIDDEN, ids=[p[0] for p in PERSONAS_FORBIDDEN])
def test_quem_nao_e_superusuario_recebe_403(endpoint: str, persona: tuple[str, tuple[str, ...]]):
    """Nenhuma capability dá acesso: o DAT tem `import_spreadsheet` e `manage_admin_registries` e recebe 403."""
    label, group_names = persona
    user = _user_in_groups(*group_names, username=f"{label}_import")

    response = _post(user, endpoint)

    assert (
        response.status_code == 403
    ), f"{label} ({group_names}) deveria receber 403 em {endpoint}, recebeu {response.status_code}."


def test_o_dat_do_403_tem_as_capacidades_que_antes_importavam():
    """Controle do teste acima: o 403 do DAT não é falta de seed (o grupo tem as capabilities)."""
    from apps.core.rbac.helpers import get_user_functional_permissions

    capacidades = get_user_functional_permissions(_user_in_groups("DAT", username="dat_caps"))

    assert {"import_spreadsheet", "manage_admin_registries"} <= set(capacidades)


# ============================================================================
# Anonymous → 401 ou 403
# ============================================================================


@pytest.mark.parametrize("endpoint", ENDPOINTS_DE_IMPORT)
def test_anonymous_request_is_rejected(endpoint: str):
    """Sem autenticação: backend retorna 401 (DRF default) ou 403 (config local)."""
    response = _post(None, endpoint)

    assert response.status_code in (
        401,
        403,
    ), f"Anonymous deveria ter sido rejeitado em {endpoint}, recebeu {response.status_code}."


# ============================================================================
# Superusuário → passa
# ============================================================================


@pytest.mark.parametrize("endpoint", ENDPOINTS_DE_IMPORT)
def test_superusuario_passa(endpoint: str):
    """O superusuário passa pelo gate; os demais status (200/202/400) dependem do arquivo."""
    cpf = str(next(_CPF_COUNTER)).zfill(11)
    user = UsuarioFactory(
        superuser=True,
        username=f"su_import_{cpf}",
        email=f"su_{cpf}@x.com",
        password="x",
        cpf=cpf,
    )

    response = _post(user, endpoint)

    assert response.status_code not in (401, 403), f"Superusuário recebeu {response.status_code} em {endpoint}."


# ============================================================================
# Sentinela: view de upload nova entra aqui, com o mesmo gate
# ============================================================================


_METODOS_DE_ESCRITA = ("post", "put", "patch")
_PARSERS_DE_ARQUIVO = (MultiPartParser, FileUploadParser)


def _recebe_arquivo(rota: str, dono: type, handlers: list, opcoes: dict) -> bool:
    """A rota recebe arquivo? Basta um sinal; nenhum deles depende do nome da rota, salvo o primeiro.

    1. a rota diz "import";
    2. parser de arquivo declarado na view ou na `@action` (o padrão do DRF não conta: toda view o tem);
    3. o código da view (APIView: a classe; `@api_view`: a função; ViewSet: o método da rota) lê `request.FILES`;
    4. o `serializer_class` tem campo de arquivo.

    Fica de fora a view que entrega `request` a uma função de outro módulo sem nenhum destes sinais.
    """
    if "import" in rota:
        return True
    parsers = opcoes.get("parser_classes", dono.parser_classes)
    if list(parsers) != list(APIView.parser_classes) and any(issubclass(p, _PARSERS_DE_ARQUIVO) for p in parsers):
        return True
    if any(".FILES" in inspect.getsource(h) for h in handlers):
        return True
    serializer = opcoes.get("serializer_class", getattr(dono, "serializer_class", None))
    return serializer is not None and any(isinstance(c, FileField) for c in serializer().fields.values())


def _views_de_upload(padroes=None) -> dict[str, list]:
    """Rota -> `permission_classes` de cada view do projeto que recebe arquivo por POST/PUT/PATCH.

    Cobre `APIView` (`callback.view_class`) e rota de `ViewSet`, inclusive `@action`
    (`callback.cls` + `callback.actions`, com as opções da ação em `callback.initkwargs`).
    """
    achadas: dict[str, list] = {}

    def percorrer(padroes, prefixo: str) -> None:
        for padrao in padroes:
            rota = prefixo + str(padrao.pattern)
            if hasattr(padrao, "url_patterns"):
                percorrer(padrao.url_patterns, rota)
                continue
            callback = padrao.callback
            opcoes = getattr(callback, "initkwargs", {})
            acoes = getattr(callback, "actions", None)
            if acoes:  # ViewSet: só os métodos que esta rota liga a verbo de escrita
                dono = callback.cls
                handlers = [getattr(dono, acoes[m]) for m in _METODOS_DE_ESCRITA if m in acoes]
            else:
                dono = getattr(callback, "view_class", None)
                if dono is None or not issubclass(dono, APIView):
                    continue
                metodos = [getattr(dono, m) for m in _METODOS_DE_ESCRITA if hasattr(dono, m)]
                # `@api_view` gera a classe em tempo de execução: o código é a função embrulhada.
                funcoes = [inspect.getclosurevars(m).nonlocals.get("func") for m in metodos]
                handlers = [f for f in funcoes if f] or ([dono] if metodos else [])
            if handlers and _recebe_arquivo(rota, dono, handlers, opcoes):
                permissoes = opcoes.get("permission_classes", dono.permission_classes)
                achadas["/" + rota.replace("api/v1/", "api/", 1)] = list(permissoes)

    percorrer(get_resolver().url_patterns if padroes is None else padroes, "")
    return achadas


def test_sentinela_toda_view_de_upload_de_planilha_exige_superusuario():
    views = _views_de_upload()

    assert sorted(views) == sorted(ENDPOINTS_DE_IMPORT), (
        "View que recebe arquivo nova (ou removida): atualize ENDPOINTS_DE_IMPORT. "
        "Importação pela tela é só do superusuário (decisão do dono, 02/10/2026)."
    )
    for rota, permissoes in views.items():
        assert permissoes == [IsAuthenticated, SuperuserOnly], rota


# ============================================================================
# A sentinela enxerga upload novo mesmo sem "import" na rota (prova com rotas de mentira)
# ============================================================================


class _CargaSemImportNaRota(APIView):
    """Lê o arquivo com os parsers padrão, numa rota que não diz "import"."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        return Response({"nome": request.FILES["file"].name})


class _UploadComParserDeArquivo(APIView):
    """Declara parser de arquivo e delega a leitura (o corpo da view não cita o arquivo)."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        return Response({})


class _CadastroComAcaoDeUpload(ViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request):
        return Response({})

    @action(detail=False, methods=["post"], url_path="enviar-planilha", parser_classes=[MultiPartParser])
    def enviar_planilha(self, request):
        return Response({})

    @action(detail=False, methods=["post"], url_path="recalcular")
    def recalcular(self, request):
        return Response({})


class _ArquivoNoSerializer(Serializer):
    anexo = FileField()


class _UploadPeloSerializer(APIView):
    """O arquivo entra pelo serializer: sem parser declarado e sem `request.FILES`."""

    permission_classes = [IsAuthenticated]
    serializer_class = _ArquivoNoSerializer

    def post(self, request):
        return Response({})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def _carga_por_funcao(request):
    return Response({"nome": request.FILES["file"].name})


class _SoJson(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return Response({"ok": request.data.get("ok")})


def _rotas_de_prova() -> list:
    router = SimpleRouter()
    router.register("cadastros", _CadastroComAcaoDeUpload, basename="prova-cadastro")
    return [
        path("api/compras/carga-planilha/", _CargaSemImportNaRota.as_view()),
        path("api/compras/upload/", _UploadComParserDeArquivo.as_view()),
        path("api/anexos/", _UploadPeloSerializer.as_view()),
        path("api/carga-por-funcao/", _carga_por_funcao),
        path("api/so-json/", _SoJson.as_view()),
        path("api/", include(router.urls)),
    ]


def test_sentinela_enxerga_upload_sem_import_na_rota():
    achadas = _views_de_upload(_rotas_de_prova())

    assert sorted(achadas) == [
        "/api/^cadastros/enviar-planilha/$",
        "/api/anexos/",
        "/api/carga-por-funcao/",
        "/api/compras/carga-planilha/",
        "/api/compras/upload/",
    ]


def test_sentinela_le_a_permissao_da_propria_acao_do_viewset():
    achadas = _views_de_upload(_rotas_de_prova())

    assert achadas["/api/^cadastros/enviar-planilha/$"] == [IsAuthenticated]
