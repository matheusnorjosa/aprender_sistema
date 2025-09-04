"""
URLs da API RESTful do Aprender Sistema.
Configura roteamento automático para todas as ViewSets DRF.
"""

from django.urls import include, path

from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from . import views

# Router principal da API
router = DefaultRouter()

# Registrar ViewSets
router.register(r"usuarios", views.UsuarioViewSet, basename="usuario")
router.register(r"projetos", views.ProjetoViewSet, basename="projeto")
router.register(r"municipios", views.MunicipioViewSet, basename="municipio")
router.register(r"tipos-evento", views.TipoEventoViewSet, basename="tipo-evento")
router.register(r"formadores", views.FormadorViewSet, basename="formador")
router.register(r"solicitacoes", views.SolicitacaoViewSet, basename="solicitacao")
router.register(r"aprovacoes", views.AprovacaoViewSet, basename="aprovacao")
router.register(
    r"eventos-google", views.EventoGoogleCalendarViewSet, basename="evento-google"
)
router.register(
    r"disponibilidade",
    views.DisponibilidadeFormadoresViewSet,
    basename="disponibilidade",
)
router.register(r"logs-auditoria", views.LogAuditoriaViewSet, basename="log-auditoria")
router.register(r"estatisticas", views.EstatisticasViewSet, basename="estatisticas")

app_name = "api"

urlpatterns = [
    # Roteamento automático da API
    path("v1/", include(router.urls)),
    # Autenticação por token
    path("auth/token/", obtain_auth_token, name="api_token_auth"),
    # Endpoint de API browsable (desenvolvimento)
    path("auth/", include("rest_framework.urls", namespace="rest_framework")),
]

"""
======================
ENDPOINTS DISPONÍVEIS
======================

BASE URL: /api/v1/

AUTENTICAÇÃO:
- POST /api/auth/token/           - Obter token de autenticação

USUÁRIOS:
- GET  /api/v1/usuarios/          - Listar usuários
- GET  /api/v1/usuarios/{id}/     - Detalhe do usuário
- GET  /api/v1/usuarios/me/       - Dados do usuário atual

REFERÊNCIAS:
- GET|POST|PUT|PATCH|DELETE /api/v1/projetos/
- GET|POST|PUT|PATCH|DELETE /api/v1/municipios/
- GET|POST|PUT|PATCH|DELETE /api/v1/tipos-evento/

FORMADORES:
- GET|POST|PUT|PATCH|DELETE /api/v1/formadores/
- GET /api/v1/formadores/{id}/disponibilidade/  - Disponibilidade do formador

SOLICITAÇÕES:
- GET|POST|PUT|PATCH|DELETE /api/v1/solicitacoes/
- GET /api/v1/solicitacoes/pendentes/           - Solicitações pendentes (superintendência)
- GET /api/v1/solicitacoes/minhas/              - Minhas solicitações

APROVAÇÕES:
- GET|POST|PUT|PATCH|DELETE /api/v1/aprovacoes/

EVENTOS GOOGLE CALENDAR:
- GET /api/v1/eventos-google/                   - Eventos sincronizados (apenas leitura)

DISPONIBILIDADE:
- GET|POST|PUT|PATCH|DELETE /api/v1/disponibilidade/
- GET /api/v1/disponibilidade/mapa-mensal/      - Mapa mensal de disponibilidade

AUDITORIA:
- GET /api/v1/logs-auditoria/                   - Logs de auditoria (apenas leitura)

ESTATÍSTICAS:
- GET /api/v1/estatisticas/                     - Estatísticas gerais do sistema
- GET /api/v1/estatisticas/por-periodo/         - Estatísticas por período

======================
PARÂMETROS DE FILTRO
======================

PAGINAÇÃO (todos os endpoints):
- ?page=N                        - Número da página
- ?page_size=N                   - Itens por página (max 100)

BUSCA (endpoints com search):
- ?search=termo                  - Busca textual

ORDENAÇÃO (endpoints com ordering):
- ?ordering=campo                - Ordenar por campo
- ?ordering=-campo               - Ordenar por campo (desc)

FILTROS ESPECÍFICOS:
- Solicitações: ?status=PENDENTE&projeto=uuid&municipio=uuid
- Formadores: ?ativo=true&municipios=uuid
- Disponibilidade: ?formador=uuid&data=2024-01-01
- Logs: ?usuario=uuid&acao=RF04

======================
CÓDIGOS DE RESPOSTA
======================

- 200: OK (GET, PUT, PATCH)
- 201: Created (POST)
- 204: No Content (DELETE)
- 400: Bad Request (dados inválidos)
- 401: Unauthorized (não autenticado)
- 403: Forbidden (sem permissão)
- 404: Not Found (recurso não encontrado)
- 500: Internal Server Error
"""
