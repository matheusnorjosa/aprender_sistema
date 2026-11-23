"""
Evento de mais de um projeto (#2036, decisões do dono de 08/11/2026; VIR-17, de 23/11/2026: até três).
SSOT da regra e das leituras.

O evento tem até três projetos, nas vagas `Solicitacao.projeto`, `projeto_2` e `projeto_3`. As vagas valem igual
para a regra; a ordem delas é a do rótulo "A / B / C". O banco garante que o 2º só existe com o 1º,
o 3º só com o 2º, e que nenhum se repete (constraints `solicitacao_projeto_2_valido` e
`solicitacao_projeto_3_valido`). A aplicação garante o resto:

- **Regra 2:** os projetos do evento são no máximo três, diferentes, da mesma gerência e do mesmo fluxo
  (`grupo_de_projetos_invalido`). Gerência vazia não conta como "a mesma" (fail-closed). Por isso o poder
  (escopo, aprovação, publicação) pode ler só `projeto`: gerência e fluxo são iguais em todas as vagas.
- **Regra 10:** mudar a gerência ou o fluxo de um projeto que está em evento com outro fica bloqueado,
  em qualquer evento, de qualquer status (`mudanca_de_grupo_bloqueada`). Quem chama: `ProjetoSerializer`
  e `ProjetoAdminForm`.

Leituras de identidade (busca, contagem por projeto, rótulo) passam por todas as vagas, sempre por estes
helpers. A contagem por projeto conta o evento em cada projeto; os totais (eventos, gerência, fluxo) contam uma vez.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from django.db.models import Count, Q, QuerySet

from apps.core.models import Projeto, Solicitacao

VAGAS = ("projeto", "projeto_2", "projeto_3")

MSG_MESMO_PROJETO = "O mesmo projeto está em duas vagas do evento: escolha outro ou deixe a vaga vazia."
MSG_SEM_GERENCIA = "Projeto sem gerência não entra em evento de mais de um projeto."
MSG_GERENCIA_DIFERENTE = "Os projetos do evento precisam ser da mesma gerência."
MSG_FLUXO_DIFERENTE = "Os projetos do evento precisam ter o mesmo fluxo de aprovação."
MSG_MAIS_DE_TRES = "O evento tem no máximo três projetos."
MSG_SEGUNDO_SEM_PRIMEIRO = "Este evento tem mais de um projeto: o projeto não pode ficar vazio."


def projetos_do_evento(s: Solicitacao) -> list[Projeto]:
    """Os projetos do evento, na ordem das vagas (0 a 3)."""
    return [p for p in (s.projeto, s.projeto_2, s.projeto_3) if p is not None]


def ids_dos_projetos(s: Solicitacao) -> frozenset[int]:
    """Conjunto dos ids: trocar a ordem das vagas não muda nada. Não consulta o banco."""
    ids = (getattr(s, f"{vaga}_id") for vaga in VAGAS)
    return frozenset(pk for pk in ids if pk is not None)


def grupo_de_projetos_invalido(*projetos: Projeto) -> str | None:
    """Regra 2: a mensagem do motivo, ou None quando os projetos podem ficar no mesmo evento."""
    if len(projetos) > len(VAGAS):
        return MSG_MAIS_DE_TRES
    ids: set[int] = {p.pk for p in projetos}
    if len(ids) < len(projetos):
        return MSG_MESMO_PROJETO
    if len(projetos) < 2:
        return None
    gerencias: set[int | None] = {p.gerencia_id for p in projetos}  # type: ignore[attr-defined]
    if None in gerencias:
        return MSG_SEM_GERENCIA
    if len(gerencias) > 1:
        return MSG_GERENCIA_DIFERENTE
    if len({p.fluxo for p in projetos}) > 1:
        return MSG_FLUXO_DIFERENTE
    return None


def par_de_projetos_invalido(a: Projeto, b: Projeto) -> str | None:
    """Regra 2 para o par (gravação pela API e carga, até a entrega B do VIR-17 passar a conferir o grupo)."""
    return grupo_de_projetos_invalido(a, b)


def q_tem_projeto(**lookup: Any) -> Q:
    """Evento com projeto que casa `lookup` em qualquer vaga. Ex.: `q_tem_projeto(pk=5)`."""
    q = Q()
    for vaga in VAGAS:
        q |= Q(**{f"{vaga}__{campo}": valor for campo, valor in lookup.items()})
    return q


# Como a planilha escreve o combo ("UNI DUNI TÊ / Cataventos"; v40, 26 eventos): na ordem das vagas,
# separados por " / ". Vale para a tela, a descrição e o título do Google (PR 6, 09/11/2026).
SEPARADOR_DOS_PROJETOS = " / "


def rotulo_dos_projetos(s: Solicitacao) -> str | None:
    """Nome para a tela: "A / B" na ordem das vagas, como a planilha. Projeto único: o nome."""
    nomes = [p.nome for p in projetos_do_evento(s)]
    return SEPARADOR_DOS_PROJETOS.join(nomes) if nomes else None


def _na_vaga(qs: QuerySet[Solicitacao], vaga: str, so_projeto: int | None) -> QuerySet[Solicitacao]:
    """Eventos com a vaga preenchida; com `so_projeto`, só os que têm esse projeto nela."""
    return qs.filter(**({f"{vaga}_id": so_projeto} if so_projeto is not None else {f"{vaga}__isnull": False}))


def contar_por_projeto(
    qs: QuerySet[Solicitacao], campo: str = "nome", *, so_projeto: int | None = None, **aggs: Any
) -> dict[Any, dict[str, int]]:
    """Agrega por projeto em todas as vagas e soma: o evento de mais de um projeto conta em cada um.

    `campo` é o campo do projeto que vira a chave (padrão `nome`). `aggs` são as anotações (padrão
    `count=Count("id")`). Vaga vazia não entra (sem balde nulo). Ordenar e cortar o top N depois da soma.
    `so_projeto` (o filtro de projeto da tela) conta só esse projeto: o parceiro do combo fica de fora.
    """
    aggs = aggs or {"count": Count("id")}
    soma: defaultdict[Any, Counter[str]] = defaultdict(Counter)
    for vaga in VAGAS:
        chave = f"{vaga}__{campo}"
        linhas = _na_vaga(qs, vaga, so_projeto).order_by().values(chave).annotate(**aggs)
        for linha in linhas:
            soma[linha[chave]].update({nome: linha[nome] for nome in aggs})
    return {chave: dict(valores) for chave, valores in soma.items()}


def projetos_distintos_por(qs: QuerySet[Solicitacao], chave: str, *, so_projeto: int | None = None) -> Counter[Any]:
    """Quantos projetos distintos há em cada valor de `chave` (ex.: `municipio_id`), unindo as vagas.

    O projeto que está na vaga 1 de um evento e na vaga 2 de outro conta uma vez. Uma consulta por vaga.
    `so_projeto` (o filtro de projeto da tela) conta só esse projeto: o parceiro do combo fica de fora.
    """
    pares: set[tuple[Any, int]] = set()
    for vaga in VAGAS:
        pares.update(_na_vaga(qs, vaga, so_projeto).order_by().values_list(chave, f"{vaga}_id").distinct())
    return Counter(valor for valor, _ in pares)


def eventos_conjuntos_do_projeto(projeto: Projeto) -> int:
    """Quantos eventos de mais de um projeto têm este projeto, em qualquer vaga e qualquer status.

    O 3º só existe com o 2º (constraint), então "1º com 2º" já cobre o trio pela vaga 1.
    """
    return Solicitacao.objects.filter(
        Q(projeto=projeto, projeto_2__isnull=False) | Q(projeto_2=projeto) | Q(projeto_3=projeto)
    ).count()


def mudanca_de_grupo_bloqueada(projeto: Projeto, *, gerencia_id: int | None, fluxo: str | None) -> str | None:
    """Regra 10: a mensagem do bloqueio quando o **valor** da gerência ou do fluxo muda e o projeto está em
    evento com outro; senão None. Salvar com os mesmos valores passa.

    Eventos reprovados, publicados ou antigos não se editam, e a troca só funciona nos projetos do evento juntos.
    Por isso a mensagem manda ao administrador do sistema, e não ao evento.
    """
    if projeto.pk is None or (gerencia_id == projeto.gerencia_id and fluxo == projeto.fluxo):  # type: ignore[attr-defined]
        return None
    n = eventos_conjuntos_do_projeto(projeto)
    if not n:
        return None
    eventos = "1 evento" if n == 1 else f"{n} eventos"
    return (
        f"Este projeto está em {eventos} junto com outro projeto, e os projetos do evento precisam ter a mesma "
        "gerência e o mesmo fluxo. A troca tem de ser feita nos projetos juntos: peça ao administrador do sistema."
    )
