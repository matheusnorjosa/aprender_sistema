/**
 * POM da Nova Solicitação (`/solicitacoes/nova`).
 *
 * Página única desde 28/10/2026 (era um wizard de 4 passos; o nome da classe ficou): cada evento é
 * um cartão ("Evento 1") com os campos lado a lado, "Mais detalhes" recolhido e um botão no fim
 * ("Criar solicitação" com 1 evento, "Criar N eventos" com mais). "+ Adicionar outro evento" põe
 * outro cartão (até 10). O POM expõe acessos semânticos aos campos e ações; validações granulares
 * (ex: valor exato de campo) ficam no spec.
 */
import type { Locator } from '@playwright/test';
import { BasePage } from './BasePage';

export class SolicitacaoWizardPage extends BasePage {
  readonly path = '/solicitacoes/nova';

  /** O cartão do evento N: a região nomeada pelo título "Evento N" (ou "Evento N com problema"). */
  cartao(numero = 1): Locator {
    return this.page.getByRole('region', { name: new RegExp(`^Evento ${numero}( com problema)?$`) });
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

  /** O botão final com N eventos ("Criar N eventos"). */
  btnCriarEventos(n: number): Locator {
    return this.page.getByRole('button', { name: `Criar ${n} eventos` });
  }

  get btnAdicionarEvento(): Locator {
    return this.page.getByRole('button', { name: /Adicionar outro evento|Limite de 10 eventos por vez/ });
  }

  /**
   * Preenche o cartão N com o mínimo para criar: projeto, tipo (o primeiro da lista), município,
   * data e horário, um formador e "não acompanha". `projeto` e `formador` são o texto a digitar
   * e o nome da opção (o projeto casa pelo fim do rótulo "CÓDIGO - NOME").
   */
  async preencherEvento(
    numero: number,
    dados: { projeto: string; municipio: string; data: string; inicio: string; fim: string; formador: string },
  ): Promise<void> {
    const cartao = this.cartao(numero);
    await this.escolher(cartao.getByLabel('Projeto', { exact: true }), dados.projeto, new RegExp(`(^| - )${dados.projeto}$`));
    await this.escolher(cartao.getByLabel('Tipo de Evento', { exact: true }), '', /./);
    await this.escolher(cartao.getByLabel('Município', { exact: true }), dados.municipio, new RegExp(dados.municipio));

    await this.digitarData(cartao.getByLabel('Data:'), dados.data);
    await this.digitarData(cartao.getByLabel('Início:'), dados.inicio);
    await this.digitarData(cartao.getByLabel('Fim:'), dados.fim);

    await this.escolher(cartao.getByRole('combobox', { name: /Formadores/ }), dados.formador, new RegExp(dados.formador));
    await cartao.getByRole('radiogroup', { name: /vai acompanhar o evento/ }).getByLabel('Não').check();
    // Formador avaliável e gerência que pergunta: a pergunta de avaliar é obrigatória.
    const avaliar = cartao.getByRole('radiogroup', { name: /pretende avaliar o formador/ });
    if (await avaliar.isVisible()) await avaliar.getByLabel('Não').check();
  }

  /** Busca e escolhe uma opção num ComboBox/AutoComplete do antd (a lista abre fora do cartão). */
  private async escolher(campo: Locator, busca: string, opcao: RegExp): Promise<void> {
    await campo.click();
    if (busca) await campo.fill(busca);
    const abertas = this.page.locator('.ant-select-dropdown:visible');
    await abertas.locator('.ant-select-item-option').filter({ hasText: opcao }).first().click();
    // A lista fecha com animação: a próxima busca só começa sem nenhuma aberta (senão a opção
    // seria procurada na lista que ainda está saindo).
    await this.page.waitForFunction(
      () => document.querySelectorAll('.ant-select-dropdown:not(.ant-select-dropdown-hidden)').length === 0,
    );
  }

  /** DatePicker/TimePicker do antd: digita no formato da tela e confirma com Enter. */
  private async digitarData(campo: Locator, valor: string): Promise<void> {
    await campo.click();
    await campo.fill(valor);
    await campo.press('Enter');
  }

  /** Resumo do que falta, no topo, depois de um clique em "Criar solicitação" com problema. */
  get resumoDeErros(): Locator {
    return this.page.getByRole('alert').filter({ hasText: 'Corrija antes de criar a solicitação' });
  }

  /** A região viva do topo: o resumo de problemas (da tela ou do servidor) e os anúncios. */
  get regiaoViva(): Locator {
    return this.page.getByRole('alert');
  }

  /** Navegação de volta para a listagem. */
  get btnVoltarListagem(): Locator {
    return this.page.getByRole('button', { name: 'Voltar para Minhas Solicitações' });
  }
}
