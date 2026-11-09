"""
Evento de dois projetos (#2036; decisões do dono de 08/11/2026). SSOT da regra e das leituras.

O evento tem até dois projetos, nas vagas `Solicitacao.projeto` e `Solicitacao.projeto_2`. As duas valem
igual: não há projeto principal. O banco garante que o 2º só existe com o 1º e é diferente dele
(constraint `solicitacao_projeto_2_valido`). A aplicação garante o resto:

- **Regra 2:** os dois projetos são da mesma gerência e do mesmo fluxo (`par_de_projetos_invalido`).
  Gerência vazia não conta como "a mesma" (fail-closed). Por isso o poder (escopo, aprovação, publicação)
  pode ler só `projeto`: gerência e fluxo são iguais nas duas vagas.
- **Regra 10:** mudar a gerência ou o fluxo de um projeto que está em evento com outro fica bloqueado,
  em qualquer evento, de qualquer status (`mudanca_de_grupo_bloqueada`). Quem chama: `ProjetoSerializer`
  e `ProjetoAdminForm`.

Leituras de identidade (busca, contagem por projeto, rótulo) passam pelas duas vagas, sempre por estes
helpers. A contagem por projeto conta o evento nos dois; os totais (eventos, gerência, fluxo) contam uma vez.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from django.db.models import Count, Q, QuerySet

from apps.core.models import Projeto, Solicitacao

VAGAS = ("projeto", "projeto_2")

MSG_MESMO_PROJETO = "Os dois projetos do evento são o mesmo: escolha outro ou deixe só um."
MSG_SEM_GERENCIA = "Projeto sem gerência não entra em evento de dois projetos."
MSG_GERENCIA_DIFERENTE = "Os dois projetos do evento precisam ser da mesma gerência."
MSG_FLUXO_DIFERENTE = "Os dois projetos do evento precisam ter o mesmo fluxo de aprovação."
MSG_SEGUNDO_SEM_PRIMEIRO = "Este evento tem dois projetos: o projeto não pode ficar vazio."


def projetos_do_evento(s: Solicitacao) -> list[Projeto]:
    """Os projetos do evento, na ordem das vagas (0, 1 ou 2)."""
    return [p for p in (s.projeto, s.projeto_2) if p is not None]


def ids_dos_projetos(s: Solicitacao) -> frozenset[int]:
    """Conjunto dos ids: inverter as vagas não muda nada. Não consulta o banco."""
    return frozenset(pk for pk in (s.projeto_id, s.projeto_2_id) if pk is not None)  # type: ignore[attr-defined]


def par_de_projetos_invalido(a: Projeto, b: Projeto) -> str | None:
    """Regra 2: a mensagem do motivo, ou None quando o par pode ficar no mesmo evento."""
    if a.pk == b.pk:
        return MSG_MESMO_PROJETO
    if a.gerencia_id is None or b.gerencia_id is None:  # type: ignore[attr-defined]
        return MSG_SEM_GERENCIA
    if a.gerencia_id != b.gerencia_id:  # type: ignore[attr-defined]
        return MSG_GERENCIA_DIFERENTE
    if a.fluxo != b.fluxo:
        return MSG_FLUXO_DIFERENTE
    return None


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
    """Agrega por projeto nas duas vagas e soma: o evento de dois projetos conta nos dois.

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
    """Quantos projetos distintos há em cada valor de `chave` (ex.: `municipio_id`), unindo as duas vagas.

    O projeto que está na vaga 1 de um evento e na vaga 2 de outro conta uma vez. Duas consultas.
    `so_projeto` (o filtro de projeto da tela) conta só esse projeto: o parceiro do combo fica de fora.
    """
    pares: set[tuple[Any, int]] = set()
    for vaga in VAGAS:
        pares.update(_na_vaga(qs, vaga, so_projeto).order_by().values_list(chave, f"{vaga}_id").distinct())
    return Counter(valor for valor, _ in pares)


def eventos_conjuntos_do_projeto(projeto: Projeto) -> int:
    """Quantos eventos de dois projetos têm este projeto, em qualquer vaga e qualquer status."""
    return Solicitacao.objects.filter(Q(projeto=projeto, projeto_2__isnull=False) | Q(projeto_2=projeto)).count()


def mudanca_de_grupo_bloqueada(projeto: Projeto, *, gerencia_id: int | None, fluxo: str | None) -> str | None:
    """Regra 10: a mensagem do bloqueio quando o **valor** da gerência ou do fluxo muda e o projeto está em
    evento com outro; senão None. Salvar com os mesmos valores passa.

    Eventos reprovados, publicados ou antigos não se editam, e a troca só funciona nos projetos do par juntos.
    Por isso a mensagem manda ao administrador do sistema, e não ao evento.
    """
    if projeto.pk is None or (gerencia_id == projeto.gerencia_id and fluxo == projeto.fluxo):  # type: ignore[attr-defined]
        return None
    n = eventos_conjuntos_do_projeto(projeto)
    if not n:
        return None
    eventos = "1 evento" if n == 1 else f"{n} eventos"
    return (
        f"Este projeto está em {eventos} junto com outro projeto, e os dois precisam ter a mesma gerência e o "
        "mesmo fluxo. A troca tem de ser feita nos projetos juntos: peça ao administrador do sistema."
    )
