"""
PR16: Views de Autocomplete/Lookup para frontend

Endpoints:
- /api/lookup/municipios/?q=...
- /api/lookup/projetos/?q=...
- /api/lookup/tipos-evento/?q=...
- /api/lookup/usuarios/?q=...

Retorna: [{id, label, kind, alias?}]
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations

from typing import Any

from django.db.models import Q, QuerySet
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.auth_normalize import normalize_login_identifier
from apps.core.permissions import HasPerm
from apps.core.pii import busca_por_nome
from apps.core.rbac.helpers import filtrar_formadores_avaliaveis, user_has_any_perm
from apps.core.services.compra_elegibilidade import (
    isento_da_regra_da_compra,
    municipios_com_marca_sem_compra,
    municipios_liberados,
    projeto_em_espera,
    projetos_liberados,
)
from apps.core.services.normalize import norm_text
from apps.core.services.solicitacao_scope import (
    scope_projetos_por_gerencia,
    scope_usuarios_por_gerencia,
    user_is_solicitacao_global,
)

from .models import EquipeGerencia, Municipio, Projeto, TipoEvento, Usuario

# PR 8 das permissões: o filtro `role` do picker é o papel vigente (gerência ativa), não o grupo.
# Nome aceito (sem caixa) → papel de `EquipeGerencia`. Nome fora daqui não casa ninguém.
_PAPEL_DO_ROLE: dict[str, str] = {
    "formador": "FORMADOR",
    "coordenador": "COORDENADOR",
    "apoio de coordenação": "APOIO",
    "gerente": "GERENTE",
}


def _projeto_do_parametro(valor: str) -> Projeto | None:
    """`projeto_id` da query (P9-5: o seletor de pessoas do evento é o da gerência do projeto). Inválido → None."""
    try:
        projeto_id = int(valor)
    except ValueError:
        return None
    return Projeto.objects.filter(pk=projeto_id).first()


def dedup_by_id(items):
    """Remove duplicatas mantendo primeiro elemento por ID"""
    seen = set()
    result = []
    for item in items:
        if item["id"] not in seen:
            seen.add(item["id"])
            result.append(item)
    return result


class MunicipioLookup(APIView):
    """
    GET /api/lookup/municipios/?q=fortaleza

    Query params adicionais:
    - com_compra=true|false: só municípios com alguma compra válida (regra única em
      `services/compra_elegibilidade`)
    - projeto_id=<id>: só municípios liberados para o projeto (mesmo projeto, coleção ou, se o
      projeto é nome geral, gerência); projeto inexistente devolve lista vazia
    - marcar_sem_compra=true (com projeto_id; Nova Solicitação e edição): em vez de filtrar, devolve
      também os municípios sem compra para o projeto, com compra primeiro, e cada item leva
      `sem_compra` (o evento ali vai para aprovação; pedido do dono, 03/11/2026) e `projeto_em_espera`
      (o projeto não tem compra em município nenhum: a criação e a edição o recusam)
    - municipio_id=<id>: só esse município (a edição reconfere a marca do par ao trocar o projeto)
    - projeto_2_id=<id> (com projeto_id): evento de dois projetos (#2036). O filtro pede compra que libere
      os dois; com `marcar_sem_compra`, `sem_compra` e `projeto_em_espera` valem se valem para qualquer um
      dos dois. Projeto inexistente devolve lista vazia

    Os filtros de compra não valem para quem é isento da regra (superuser ou a capacidade); com
    `marcar_sem_compra`, o isento recebe `sem_compra: false` em tudo (ele cria sem aprovação).

    Retorna: [{id, label, kind: "municipio", sem_compra?}]
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        q = request.GET.get("q", "").strip()
        com_compra = request.GET.get("com_compra", "false").lower() in {"1", "true", "t", "yes", "y"}
        include_hubs = request.GET.get("include_hubs", "false").lower() in {"1", "true", "t", "yes", "y"}
        projeto_id_raw = request.GET.get("projeto_id", "").strip()
        marcar_sem_compra = request.GET.get("marcar_sem_compra", "false").lower() in {"1", "true", "t", "yes", "y"}

        projeto_id: int | None = None
        try:
            if projeto_id_raw:
                projeto_id = int(projeto_id_raw)
        except ValueError:
            projeto_id = None
        projeto_2_raw = request.GET.get("projeto_2_id", "").strip()
        projeto_2: Projeto | None = _projeto_do_parametro(projeto_2_raw) if projeto_2_raw else None
        projeto_2_invalido = bool(projeto_2_raw) and projeto_2 is None

        qs: QuerySet[Municipio] = Municipio.objects.filter(ativo=True)
        # Hubs de viagem têm UF vazia (origem/destino de deslocamento, não local de evento). Fora do
        # dropdown de solicitação por padrão; `include_hubs=true` reexpõe (fluxo de deslocamento).
        if not include_hubs:
            qs = qs.exclude(uf="")
        # Reconferir um município (o do evento gravado pode estar inativo ou ser hub): ele vem com a
        # marca mesmo fora da lista normal, porque o servidor confere o par do mesmo jeito no salvar.
        municipio_id_raw = request.GET.get("municipio_id", "").strip()
        if municipio_id_raw:
            qs = Municipio.objects.filter(pk=int(municipio_id_raw)) if municipio_id_raw.isdecimal() else qs.none()
        ordem: tuple[str, ...] = ("nome",)
        em_espera = False  # o projeto não recebe evento (sem compra em município nenhum): a tela avisa
        if marcar_sem_compra and projeto_id is not None:
            projeto = Projeto.objects.filter(pk=projeto_id).first()
            if projeto is None or projeto_2_invalido:
                qs = qs.none()
            elif not isento_da_regra_da_compra(request.user):
                # Com compra primeiro: o teto da lista sem busca não esconde o município com compra.
                qs = municipios_com_marca_sem_compra(qs, projeto, projeto_2)
                ordem = ("sem_compra", "nome")
                em_espera = projeto_em_espera(projeto) or (projeto_2 is not None and projeto_em_espera(projeto_2))
        elif (com_compra or projeto_id is not None) and not isento_da_regra_da_compra(request.user):
            if projeto_id is None:
                qs = municipios_liberados(qs, None)
            else:
                projeto = Projeto.objects.filter(pk=projeto_id).first()
                qs = municipios_liberados(qs, projeto) if projeto is not None and not projeto_2_invalido else qs.none()
                if projeto_2 is not None:
                    qs = municipios_liberados(qs, projeto_2)

        if not q:
            # Retornar municípios (max 100)
            qs = qs.order_by(*ordem)[:100]
        else:
            # Normalizar query
            _q_norm = norm_text(q)  # noqa: F841 - reserved for future normalized search

            # Buscar por nome ou UF
            qs = qs.filter(Q(nome__icontains=q) | Q(uf__icontains=q)).order_by(*ordem)[:50]

        results = []
        for mun in qs:
            # Sem traço sobrando quando a UF é vazia (hub de viagem): "Fortaleza", não "Fortaleza-".
            label = f"{mun.nome}-{mun.uf}" if mun.uf else mun.nome
            item: dict[str, Any] = {"id": mun.id, "label": label, "kind": "municipio"}
            if marcar_sem_compra and projeto_id is not None:
                item["sem_compra"] = bool(getattr(mun, "sem_compra", False))
                item["projeto_em_espera"] = em_espera
            results.append(item)

        return Response(dedup_by_id(results))


class ProjetoLookup(APIView):
    """
    GET /api/lookup/projetos/?q=acerta

    Query params adicionais:
    - com_compra=true|false: esconde o projeto "em espera" (sem compra que o libere em município
      nenhum; regra única em `services/compra_elegibilidade`)
    - municipio_id=<id>: só projetos liberados no município informado
    - mesmo_grupo_de=<id>: evento de dois projetos (#2036). Só os projetos que podem ser o outro projeto
      do evento: mesma gerência e mesmo fluxo (`par_de_projetos_invalido`), sem o próprio. Projeto sem
      gerência, inexistente ou id inválido devolve lista vazia

    Os filtros de compra não valem para quem é isento da regra (superuser ou a capacidade).

    Retorna: [{id, label, kind: "projeto", fluxo, pergunta_avaliar_formador, responsavel_padrao}]

    `pergunta_avaliar_formador` = a gerência do projeto usa a pergunta "Você pretende avaliar o
    formador?" (projeto sem gerência: True). Decisão do dono, 05/10/2026.

    `responsavel_padrao` = deixar o "Coordenador responsável" vazio faz de quem busca a responsável
    pelo evento do projeto (mesma regra de `SolicitacaoViewSet._resolver_coordenador_responsavel`):
    papel COORDENADOR vigente na gerência do projeto; global/privilegiado, em qualquer gerência (PR 9).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        q = request.GET.get("q", "").strip()
        com_compra = request.GET.get("com_compra", "false").lower() in {"1", "true", "t", "yes", "y"}
        include_kits = request.GET.get("include_kits", "false").lower() in {"1", "true", "t", "yes", "y"}
        municipio_id_raw = request.GET.get("municipio_id", "").strip()

        municipio_id: int | None = None
        try:
            if municipio_id_raw:
                municipio_id = int(municipio_id_raw)
        except ValueError:
            municipio_id = None

        qs: QuerySet[Projeto] = Projeto.objects.filter(ativo=True).select_related("gerencia")
        mesmo_grupo_raw = request.GET.get("mesmo_grupo_de", "").strip()
        if mesmo_grupo_raw:
            par = _projeto_do_parametro(mesmo_grupo_raw)
            if par is None or par.gerencia_id is None:
                qs = qs.none()
            else:
                qs = qs.filter(gerencia_id=par.gerencia_id, fluxo=par.fluxo).exclude(pk=par.pk)
        if (com_compra or municipio_id is not None) and not isento_da_regra_da_compra(request.user):
            qs = projetos_liberados(qs, municipio_id)
        # Os EVENTOS usam o nome-família (ex.: "A COR DA GENTE"); as séries ("A COR DA GENTE 3") são
        # os kits das coleções e NÃO entram no dropdown de solicitação por padrão (decisão do dono).
        # Quem diz o que é série é a marca `Projeto.eh_serie` (editável na tela Projetos), não o
        # nome. `include_kits=true` reexpõe.
        if not include_kits:
            qs = qs.exclude(eh_serie=True)
        # PR 9: só projetos das gerências onde a pessoa tem papel G/C/A vigente (projeto sem
        # gerência nunca entra). Global/privilegiado isento.
        qs = scope_projetos_por_gerencia(qs, request.user)
        qs = qs.distinct()

        # Teto amplo: com os kits fora, o catálogo de projetos-evento cabe na lista (a busca `q`
        # ainda filtra ao digitar). Antes era 50 → cortava projetos alfabeticamente ao fim.
        if not q:
            qs = qs.order_by("nome")[:200]
        else:
            _q_norm = norm_text(q)  # noqa: F841 - reserved for future normalized search
            qs = qs.filter(Q(nome__icontains=q) | Q(codigo__icontains=q)).order_by("nome")[:200]

        coordena = EquipeGerencia.gerencias_com_papel(request.user, {"COORDENADOR"})
        coordena_em_qualquer = bool(coordena) and user_is_solicitacao_global(request.user)

        results = []
        for proj in qs:
            # Label = nome puro. O `codigo` do catálogo é um slug do próprio nome (Á/ç/ê→"_"), então
            # "A_COR_DA_GENTE - A COR DA GENTE" era ruído redundante — não desambigua nada.
            results.append(
                {
                    "id": proj.id,
                    "label": proj.nome,
                    "kind": "projeto",
                    "fluxo": proj.fluxo,
                    "pergunta_avaliar_formador": proj.gerencia is None or proj.gerencia.pergunta_avaliar_formador,
                    "responsavel_padrao": coordena_em_qualquer or proj.gerencia_id in coordena,
                }
            )

        return Response(dedup_by_id(results))


class TipoEventoLookup(APIView):
    """
    GET /api/lookup/tipos-evento/?q=formacao
    Retorna: [{id, label, kind: "tipo_evento"}]
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        q = request.GET.get("q", "").strip()

        if not q:
            qs = TipoEvento.objects.all().order_by("nome")[:50]
        else:
            qs = TipoEvento.objects.filter(nome__icontains=q)[:50]

        results = []
        for tipo in qs:
            results.append(
                {
                    "id": tipo.id,
                    "label": tipo.nome,
                    "kind": "tipo_evento",
                }
            )

        return Response(dedup_by_id(results))


class UsuarioLookup(APIView):
    """
    GET /api/lookup/usuarios/?q=maria&role=formador&projeto_id=12
    Retorna: [{id, label, kind: "usuario", avaliavel}]

    `projeto_id` (PR 9, P9-5): só pessoas da gerência do projeto do evento. Sem ele, as das gerências
    onde quem busca tem papel G/C/A (`scope_usuarios_por_gerencia`).

    `role` aceita vários papéis separados por vírgula (`Formador,Coordenador,Gerente`): a lista de
    formadores da Nova Solicitação oferece também os coordenadores do setor (decisão do dono,
    05/10/2026: coordenador que atua no evento entra como formador) e os gerentes (11/11/2026). `avaliavel` = função
    Formador sem a função Coordenador (`filtrar_formadores_avaliaveis`).

    PR 5 hardening RBAC (2026-04-30):
    - Capability gate: somente perfis com motivo legítimo (criar
      solicitação OU administrar cadastros) listam usuários.
    - Não usa hardcode de grupos.

    SEC-ENUM-01: email permanece fora do payload (anti-enumeração).
    SEC-ENUM-02 / S5 (auditoria 14/10, C6): o login é o CPF desde 29/09, então a busca
    é por nome para todos (e pelo e-mail só se o termo não tem dígito: acha "Conceição" por
    "conceicao" sem testar pedaço de CPF). Quem administra cadastros (`manage_admin_registries`) ou o
    superusuário acha também pelo CPF (cru ou formatado) ou pelo e-mail, mas só com o valor
    EXATO: pedaço de CPF ou de e-mail com dígito não casa ninguém (senão o lookup vira oráculo de CPF).

    Consumidores legítimos confirmados (auditoria 2026-04-30):
    - `NewSolicitacaoWizard` (Coord/Apoio/Gerente cria) →
      `create_solicitation`
    - `EditSolicitacaoPage` (owner ou privileged edita) →
      `create_solicitation`
    - DAT admin (admin geral / suporte) → `manage_admin_registries`

    Aprovações, Controle/Operação e dashboards executivos não consomem
    este endpoint, portanto as capacidades de aprovação e
    `operate_preagenda` ficam fora do gate.
    """

    permission_classes = [HasPerm("create_solicitation") | HasPerm("manage_admin_registries")]

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        q = request.GET.get("q", "").strip()
        role = request.GET.get("role", "").strip()

        # Começar com queryset base
        qs = Usuario.objects.filter(is_active=True)

        # Aplicar filtro de busca: nome para todos (e e-mail se o termo não tem dígito); CPF/e-mail
        # exatos só para quem administra contas.
        if q:
            busca = busca_por_nome(q)
            if request.user.is_superuser or user_has_any_perm(request.user, "manage_admin_registries"):
                busca |= Q(username=normalize_login_identifier(q)) | Q(email__iexact=q)
            qs = qs.filter(busca)

        # Filtrar por papel vigente ANTES do slice (vários papéis separados por vírgula = OU)
        roles = [p.strip().lower() for p in role.split(",") if p.strip()]
        papeis: frozenset[str] = frozenset()
        if roles:
            papeis = frozenset(_PAPEL_DO_ROLE[r] for r in roles if r in _PAPEL_DO_ROLE)
            vigentes = EquipeGerencia.vigentes_em().filter(papel__in=papeis, gerencia__ativo=True)
            qs = qs.filter(id__in=vigentes.values("usuario_id"))

        # PR 9: só pessoas das gerências onde quem busca tem papel G/C/A vigente; com `projeto_id`,
        # só da gerência do projeto (P9-5), e o papel pedido tem que ser NESSA gerência (o mesmo
        # papel na mesma gerência que o write-path exige do responsável). O seletor da Nova
        # Solicitação consome este lookup → FE já filtrado, sem 400. Global/privilegiado
        # (superuser, Superintendência, Controle, DAT) isento.
        qs = scope_usuarios_por_gerencia(
            qs, request.user, _projeto_do_parametro(request.GET.get("projeto_id", "")), papeis
        )

        # Aplicar ordenação e limite
        usuarios = list(qs.order_by("-id")[: 50 if q else 20])
        avaliaveis = set(
            filtrar_formadores_avaliaveis(Usuario.objects.filter(id__in=[u.id for u in usuarios])).values_list(
                "id", flat=True
            )
        )

        results = []
        for user in usuarios:
            label = str(user)  # nome, ou "Usuario #id": nunca o login (CPF)
            results.append(
                {
                    "id": user.id,
                    "label": label,
                    "kind": "usuario",
                    "avaliavel": user.id in avaliaveis,
                }
            )

        return Response(dedup_by_id(results))
