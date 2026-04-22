/**
 * POM da grade mensal de disponibilidade (`/disponibilidade`).
 *
 * Visão agregada do setor (via `EquipeGerencia` + `HasSectorAccess`).
 * Regras RD-01..RD-08 se refletem aqui.
 */
import type { Locator } from '@playwright/test';
import { BasePage } from './BasePage';

export class DisponibilidadePage extends BasePage {
  readonly path = '/disponibilidade';

  get seletorMes(): Locator {
    return this.page.getByLabel(/m[eê]s/i).first();
  }

  get seletorAno(): Locator {
    return this.page.getByLabel(/ano/i).first();
  }

  get seletorGerencia(): Locator {
    return this.page.getByLabel(/ger[êe]ncia|setor/i).first();
  }

  get gradeMensal(): Locator {
    return this.page.getByRole('table').first();
  }

  linhaPessoa(nomeOuUsername: string): Locator {
    return this.gradeMensal.getByRole('row').filter({ hasText: nomeOuUsername });
  }

  /** Células da grade em um dia específico. */
  celulasDia(dia: number): Locator {
    return this.gradeMensal.getByRole('cell').filter({ hasText: new RegExp(`^\\s*${dia}\\s*$`) });
  }
}
