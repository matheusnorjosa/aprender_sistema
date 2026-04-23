/**
 * POM da página de Aprovações (`/aprovacoes`).
 *
 * Usada por Superintendência / DAT / superuser para aprovar/reprovar
 * solicitações pendentes (fluxo PA-01..PA-07).
 */
import type { Locator } from '@playwright/test';
import { BasePage } from './BasePage';

export class AprovacoesPage extends BasePage {
  readonly path = '/aprovacoes';

  get tabelaPendentes(): Locator {
    return this.page.getByRole('table').first();
  }

  /**
   * Localiza a linha de uma solicitação na tabela.
   *
   * A tabela de aprovações mostra colunas como data/hora, município, projeto
   * — não expõe ID numérico. Ao invés do ID, aceite o texto-chave que a
   * linha contém (ex: data formatada `DD/MM/YYYY HH:mm` via
   * `formatInicioForTable(solicitacao.inicio)` do helpers/wait).
   */
  linhaSolicitacao(textoChave: string): Locator {
    return this.tabelaPendentes.getByRole('row').filter({ hasText: textoChave });
  }

  btnAprovar(textoChave: string): Locator {
    return this.linhaSolicitacao(textoChave).getByRole('button', { name: /aprovar/i });
  }

  btnReprovar(textoChave: string): Locator {
    return this.linhaSolicitacao(textoChave).getByRole('button', { name: /reprovar|rejeitar/i });
  }

  /** Campo de motivo no dialog de reprovação (PA-04). */
  get campoMotivoReprovacao(): Locator {
    return this.page.getByRole('dialog').getByLabel(/motivo|justificativa/i);
  }

  get btnConfirmarReprovacao(): Locator {
    return this.page.getByRole('dialog').getByRole('button', { name: /confirmar|reprovar/i });
  }
}
