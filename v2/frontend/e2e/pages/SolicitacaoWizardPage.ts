/**
 * POM do wizard de nova solicitação (`/solicitacoes/nova`).
 *
 * Wizard multi-step — o POM expõe acessos semânticos aos campos e ações.
 * Validações granulares (ex: valor exato de campo) ficam no spec.
 */
import type { Locator } from '@playwright/test';
import { BasePage } from './BasePage';

export class SolicitacaoWizardPage extends BasePage {
  readonly path = '/solicitacoes/nova';

  get projetoSelect(): Locator {
    return this.page.getByLabel(/projeto/i).first();
  }

  get municipioSelect(): Locator {
    return this.page.getByLabel(/munic[ií]pio/i).first();
  }

  get tipoEventoSelect(): Locator {
    return this.page.getByLabel(/tipo de evento/i).first();
  }

  get dataInicio(): Locator {
    return this.page.getByLabel(/in[ií]cio/i).first();
  }

  get dataFim(): Locator {
    return this.page.getByLabel(/fim|t[eé]rmino/i).first();
  }

  get btnProximo(): Locator {
    return this.page.getByRole('button', { name: /pr[oó]ximo|avan[cç]ar/i });
  }

  get btnVoltar(): Locator {
    return this.page.getByRole('button', { name: /voltar/i });
  }

  get btnSubmeter(): Locator {
    return this.page.getByRole('button', { name: /submeter|enviar|criar/i });
  }
}
