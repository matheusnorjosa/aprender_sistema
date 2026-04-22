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

  linhaSolicitacao(solicitacaoId: number | string): Locator {
    return this.tabelaPendentes.getByRole('row').filter({ hasText: String(solicitacaoId) });
  }

  btnAprovar(solicitacaoId: number | string): Locator {
    return this.linhaSolicitacao(solicitacaoId).getByRole('button', { name: /aprovar/i });
  }

  btnReprovar(solicitacaoId: number | string): Locator {
    return this.linhaSolicitacao(solicitacaoId).getByRole('button', { name: /reprovar|rejeitar/i });
  }

  /** Campo de motivo no dialog de reprovação (PA-04). */
  get campoMotivoReprovacao(): Locator {
    return this.page.getByRole('dialog').getByLabel(/motivo|justificativa/i);
  }

  get btnConfirmarReprovacao(): Locator {
    return this.page.getByRole('dialog').getByRole('button', { name: /confirmar|reprovar/i });
  }
}
