/**
 * POM da Nova Solicitação (`/solicitacoes/nova`).
 *
 * Página única desde 28/10/2026 (era um wizard de 4 passos; o nome da classe ficou): cada evento é
 * um cartão ("Evento 1") com os campos lado a lado, "Mais detalhes" recolhido e um botão "Criar
 * solicitação" no fim. O POM expõe acessos semânticos aos campos e ações; validações granulares
 * (ex: valor exato de campo) ficam no spec.
 */
import type { Locator } from '@playwright/test';
import { BasePage } from './BasePage';

export class SolicitacaoWizardPage extends BasePage {
  readonly path = '/solicitacoes/nova';

  /** O cartão do evento N: a região nomeada pelo título "Evento N". */
  cartao(numero = 1): Locator {
    return this.page.getByRole('region', { name: `Evento ${numero}` });
  }

  get projetoSelect(): Locator {
    return this.cartao().getByLabel(/projeto/i).first();
  }

  get municipioSelect(): Locator {
    return this.cartao().getByLabel(/munic[ií]pio/i).first();
  }

  get tipoEventoSelect(): Locator {
    return this.cartao().getByLabel(/tipo de evento/i).first();
  }

  get dataInicio(): Locator {
    return this.cartao().getByLabel(/in[ií]cio/i).first();
  }

  get dataFim(): Locator {
    return this.cartao().getByLabel(/fim|t[eé]rmino/i).first();
  }

  /** Cabeçalho da seção recolhida dos campos opcionais (tem `aria-expanded`). */
  get maisDetalhes(): Locator {
    return this.cartao().getByRole('button', { name: /mais detalhes/i });
  }

  get btnCriar(): Locator {
    return this.page.getByRole('button', { name: 'Criar solicitação' });
  }

  /** Resumo do que falta, no topo, depois de um clique em "Criar solicitação" com problema. */
  get resumoDeErros(): Locator {
    return this.page.getByRole('alert').filter({ hasText: 'Corrija antes de criar a solicitação' });
  }

  /** Navegação de volta para a listagem. */
  get btnVoltarListagem(): Locator {
    return this.page.getByRole('button', { name: 'Voltar para Minhas Solicitações' });
  }
}
