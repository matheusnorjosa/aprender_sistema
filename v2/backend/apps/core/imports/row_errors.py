"""Tratamento uniforme de erros inesperados por linha nos importers.

CodeQL `py/stack-trace-exposure`: a mensagem crua de uma excecao inesperada
(erro de banco, integridade, parse do arquivo) NAO pode voltar ao cliente —
ela pode carregar nome de constraint, coluna interna, caminho de arquivo, etc.

Os importers ja tratam as falhas ESPERADAS (campo obrigatorio ausente, valor
invalido) com mensagens controladas e amigaveis. Este helper cobre so o
catch-all do inesperado: registra a excecao no log (com traceback, para
diagnostico) e devolve ao cliente uma mensagem generica e estavel.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("apps.core.imports")

# Mensagem unica devolvida ao cliente quando uma linha falha por erro inesperado.
# Mantida generica de proposito: o detalhe real vai para o log, nunca para a resposta.
MENSAGEM_ERRO_LINHA = "Erro interno ao processar a linha; verifique o formato dos dados."


def registrar_erro_import(*, importer: str, linha: int) -> str:
    """Loga a excecao corrente e devolve a mensagem segura para o cliente.

    DEVE ser chamada de dentro de um bloco ``except`` — usa o contexto de
    excecao ativo (``logging.exception``) para capturar o traceback completo
    no log. O valor de retorno e' a unica coisa que pode chegar ao cliente;
    nunca inclui ``str(excecao)``.

    Args:
        importer: nome curto do importer (ex.: "municipios") para rastrear no log.
        linha: numero da linha do arquivo que falhou (1-based).

    Returns:
        Mensagem generica e estavel, segura para exibir ao usuario.
    """
    logger.exception("Erro inesperado no import '%s' (linha %d)", importer, linha)
    return MENSAGEM_ERRO_LINHA
