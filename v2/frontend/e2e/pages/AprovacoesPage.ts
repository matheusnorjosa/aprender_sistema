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
   * Localiza a linha de uma solicitação na tabela via AntD `data-row-key`.
   *
   * AntD `<Table rowKey="id">` renderiza cada `<tr>` com `data-row-key={id}`.
   * Isso é mais robusto que filtrar por `hasText(data formatada)` — a coluna
   * "Data/Horário" na `ApprovalsPage` quebra data e hora em elementos
   * separados (`DD/MM/YYYY` acima, `HH:mm - HH:mm` embaixo), então um
   * `hasText("DD/MM/YYYY HH:mm")` concatenado não casa.
   */
  linhaPorId(id: number): Locator {
    return this.page.locator(`tr[data-row-key="${id}"]`);
  }

  /**
   * Variante legacy aceitando texto livre. Use `linhaPorId` quando possível.
   */
  linhaSolicitacao(textoChave: string): Locator {
    return this.tabelaPendentes.getByRole('row').filter({ hasText: textoChave });
  }

  btnAprovarPorId(id: number): Locator {
    return this.linhaPorId(id).getByRole('button', { name: /aprovar/i });
  }

  btnReprovarPorId(id: number): Locator {
    return this.linhaPorId(id).getByRole('button', { name: /reprovar|rejeitar/i });
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
