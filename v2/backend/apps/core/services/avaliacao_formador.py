"""
"Você pretende avaliar o formador nesse evento?" — regra da pergunta (decisão do dono, 05/10/2026).

A pergunta só se aplica quando:
(a) a gerência do PROJETO do evento pergunta (`Gerencia.pergunta_avaliar_formador`; projeto ou
    gerência ausente = pergunta), e
(b) há na lista de formadores do evento ao menos uma pessoa AVALIÁVEL: função Formador sem a
    função Coordenador (`rbac.helpers.filtrar_formadores_avaliaveis`).

Aplicável → resposta obrigatória na criação (null nunca vale); "Sim" → `formador_avaliado`
obrigatório e entre os avaliáveis. Não aplicável → resposta não nula recusada.

Na edição a resposta só é exigida de quem já tinha respondido (evento antigo segue "não
informado"). Tirar da lista o formador escolhido RECUSA a edição com o motivo — escolha
documentada: limpar em silêncio apagaria uma resposta dada por quem criou.

Roda depois de gravar as participações (a lista de formadores é a da tabela), dentro da
transação do criar/editar: a recusa desfaz tudo.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false

from __future__ import annotations

from apps.core.exceptions import ValidationAPIError
from apps.core.models import Participation, Solicitacao, Usuario
from apps.core.rbac.helpers import filtrar_formadores_avaliaveis

MSG_INFORME = "Informe se você pretende avaliar o formador neste evento."
MSG_NAO_SE_APLICA = (
    "A pergunta sobre avaliar o formador não se aplica a este evento: a gerência do projeto não usa a "
    "pergunta ou não há formador avaliável na lista. Deixe a resposta em branco."
)
MSG_ESCOLHA = "Escolha qual formador você pretende avaliar."
MSG_FORA_DA_LISTA = (
    "O formador escolhido para avaliação não está entre os formadores avaliáveis do evento "
    "(função Formador, sem a função Coordenador). Escolha outro formador da lista ou responda Não."
)
MSG_SO_COM_SIM = "Só escolha o formador a avaliar quando a resposta for Sim."


def _erro(campo: str, mensagem: str) -> ValidationAPIError:
    """400 no padrão da API: a mensagem em `detail` e no campo, em `errors`."""
    return ValidationAPIError(message=mensagem, details={campo: [mensagem]})


def gerencia_pergunta(solicitacao: Solicitacao) -> bool:
    """A gerência do projeto usa a pergunta? Sem projeto ou sem gerência: usa (nada a desligá-la)."""
    gerencia = getattr(getattr(solicitacao, "projeto", None), "gerencia", None)
    return gerencia is None or bool(gerencia.pergunta_avaliar_formador)


def formadores_avaliaveis_ids(solicitacao: Solicitacao) -> set[int]:
    """Ids dos formadores AVALIÁVEIS gravados no evento (papel FORMADOR com conta)."""
    formador_ids = Participation.objects.filter(
        solicitacao=solicitacao, role=Participation.Role.FORMADOR, usuario__isnull=False
    ).values_list("usuario_id", flat=True)
    return set(filtrar_formadores_avaliaveis(Usuario.objects.filter(id__in=formador_ids)).values_list("id", flat=True))


def validar_avaliacao_formador(solicitacao: Solicitacao, *, criando: bool, resposta_anterior: bool | None) -> None:
    """Confere a resposta gravada contra a regra; levanta 400 (`ValidationAPIError`) se não fecha."""
    pretende = solicitacao.pretende_avaliar_formador
    avaliado_id = solicitacao.formador_avaliado_id
    avaliaveis = formadores_avaliaveis_ids(solicitacao)

    if not (gerencia_pergunta(solicitacao) and avaliaveis):
        if pretende is not None:
            raise _erro("pretende_avaliar_formador", MSG_NAO_SE_APLICA)
        if avaliado_id is not None:
            raise _erro("formador_avaliado", MSG_SO_COM_SIM)
        return

    if pretende is None and (criando or resposta_anterior is not None):
        raise _erro("pretende_avaliar_formador", MSG_INFORME)
    if pretende is True:
        if avaliado_id is None:
            raise _erro("formador_avaliado", MSG_ESCOLHA)
        if avaliado_id not in avaliaveis:
            raise _erro("formador_avaliado", MSG_FORA_DA_LISTA)
    elif avaliado_id is not None:
        raise _erro("formador_avaliado", MSG_SO_COM_SIM)
