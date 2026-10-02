/**
 * Excluir registro em uso (C2b, decisão do dono de 01/10).
 *
 * O backend recusa excluir registro em uso (FK `PROTECT`) com 409 e o motivo ("... está em uso
 * (Compras)."). Em vez de só um toast, a tela mostra o motivo e, se o registro está ativo, oferece
 * Desativar: PATCH `ativo=false` pelo mesmo cliente e permissão do Editar. Registro já inativo: só o
 * motivo. Usado por Municípios, Projetos, Gerências, Projetos Gerais e Produtos.
 * Gerências usa o mesmo diálogo antes do DELETE, quando a contagem de projetos ativos já diz que o
 * backend recusaria (`dialogoNaoPodeExcluir`).
 *
 * Um diálogo por vez: o do 409 abre no `afterClose` da confirmação de excluir, não no onOk dela.
 * Cada diálogo do rc-dialog guarda onde estava o foco quando abriu e o devolve ali ao fechar.
 * Com a confirmação ainda aberta, o do 409 guardava o "Sim, excluir" (que sai do DOM) e, quando a
 * confirmação terminava de fechar, o foco ia ao Excluir atrás da máscara e depois ao contêiner do
 * diálogo: o Cancelar perdia o foco, e fechar o deixava no body. Abrindo depois, o foco já voltou ao
 * Excluir da linha (ou ao "Mais ações"), o Cancelar o recebe, e fechar o devolve ali.
 * Medido no Chromium: e2e/checklist/excluir-em-uso-foco.spec.ts.
 *
 * Se a pessoa fecha a confirmação (Cancelar/Esc) com o DELETE em andamento, o `afterClose` já passou
 * quando o 409 chega: o diálogo abre na hora, em vez de o motivo sumir (`aposConfirmacaoFechar`).
 */
import { Modal, message } from 'antd';

import { mensagemDoErro } from './usuario_form_helpers';

interface SaidaDesativar {
  /** O registro na frase, com o artigo: `o município "Sobral - CE"`. */
  registro: string;
  ativo: boolean;
  /** O PATCH `ativo=false` do cliente da tela. */
  desativar: () => Promise<unknown>;
  /** Mensagem de sucesso: "Município desativado". */
  desativado: string;
  recarregar: () => void;
  /**
   * O que a pessoa vai ver na lista depois de desativar, no vocabulário da tela.
   * Padrão: a coluna "Situação" (Ativo/Inativo). Projetos mostra "Ativo" com Sim/Não.
   */
  aoDesativar?: string;
  /**
   * O que continua depois de desativar. Padrão: "o registro e os vínculos continuam no sistema".
   * Gerências troca: desativar tira a gerência da equipe e das listas, e o texto não pode prometer o contrário.
   */
  oQueFica?: string;
}

/**
 * Abre o diálogo do 409 quando a confirmação de excluir termina de fechar (um diálogo por vez).
 * Se ela já fechou quando o 409 chega (Cancelar/Esc com o DELETE em andamento), abre na hora.
 */
export function aposConfirmacaoFechar(): { afterClose: () => void; abrir: (dialogo: () => void) => void } {
  let fechou = false;
  let pendente: (() => void) | null = null;
  return {
    afterClose: () => {
      fechou = true;
      pendente?.();
      pendente = null;
    },
    abrir: (dialogo) => {
      if (fechou) dialogo();
      else pendente = dialogo;
    },
  };
}

/**
 * O diálogo do 409 de registro em uso, para o `afterClose` da confirmação de excluir abrir.
 * Devolve `null` para outro erro: a tela mostra o toast de sempre.
 */
export function dialogoDeExclusaoEmUso({ erro, ...saida }: SaidaDesativar & { erro: unknown }): (() => void) | null {
  if ((erro as { response?: { status?: number } }).response?.status !== 409) return null;
  return dialogoNaoPodeExcluir({ motivo: mensagemDoErro(erro), ...saida });
}

/** "Não é possível excluir": o motivo e, se o registro está ativo, Desativar (foco no Cancelar). */
export function dialogoNaoPodeExcluir({
  motivo,
  registro,
  ativo,
  desativar,
  desativado,
  recarregar,
  aoDesativar = 'a situação passa a Inativo',
  oQueFica = 'o registro e os vínculos continuam no sistema',
}: SaidaDesativar & { motivo: string }): () => void {
  if (!ativo) {
    return () => {
      Modal.info({ title: 'Não é possível excluir', content: `${motivo} O registro já está inativo.`, okText: 'Entendi' });
    };
  }

  return () => {
    Modal.confirm({
      title: 'Não é possível excluir',
      content:
        `${motivo} Você pode desativar ${registro}: ${oQueFica},` + ` ${aoDesativar} e dá para reativar em Editar.`,
      okText: 'Desativar',
      cancelText: 'Cancelar',
      // Quem acabou de confirmar "Sim, excluir" com Enter não desativa sem ler.
      autoFocusButton: 'cancel',
      onOk: async () => {
        // Não rejeita: o diálogo fecha, e o motivo fica no toast.
        try {
          await desativar();
          message.success(desativado);
          recarregar();
        } catch (falha) {
          message.error(`Erro ao desativar: ${mensagemDoErro(falha)}`);
        }
      },
    });
  };
}
