/**
 * Simulador de remanejamento (DADOS SIMULADOS): escolher municípios e o destino, ver antes e depois de
 * cada envolvido, a mudança de estrato e a nova dispersão; depois propor → aprovar → aplicar, no
 * estado da sessão (IntegraDemoContext). Nada é gravado.
 */
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, test } from 'vitest';

import { carregarDadosIntegra } from '../../dados/fonte';
import { PESOS_REVISADOS, simularRemanejamento } from '../calculo';
import { textoDoEstrato } from '../componentes/EtiquetaEstrato';
import { renderTelaIca } from './telaIca';

const LUCINEIA = 101;
const PRISCILA = 117;
const BELEM = 1;

type Usuario = ReturnType<typeof userEvent.setup>;

async function montarMovimento(user: Usuario): Promise<void> {
  renderTelaIca('/integra/ica/simulador');
  await screen.findByRole('heading', { level: 1, name: 'Simulador de remanejamento' });
  await user.selectOptions(screen.getByLabelText('Coordenador de origem'), String(LUCINEIA));
  await user.click(screen.getByRole('checkbox', { name: 'Belém-PA' }));
  await user.selectOptions(screen.getByLabelText('Coordenador de destino'), String(PRISCILA));
  await user.click(screen.getByRole('button', { name: 'Adicionar à simulação' }));
}

describe('Simulador de remanejamento', { timeout: 20000 }, () => {
  test('antes e depois de cada envolvido, mudança de estrato e nova dispersão', async () => {
    const user = userEvent.setup();
    await montarMovimento(user);

    const movimentos = screen.getByRole('list', { name: 'Movimentos da simulação' });
    expect(within(movimentos).getByText('Belém-PA: de Lucinéia Barreto para Priscila Vasconcelos')).toBeInTheDocument();

    const esperado = simularRemanejamento(carregarDadosIntegra().base, PESOS_REVISADOS, [
      { municipioId: BELEM, deCoordenadorId: LUCINEIA, paraCoordenadorId: PRISCILA },
    ]);
    const cartoes = within(screen.getByRole('list', { name: 'Antes e depois de cada envolvido' })).getAllByRole('listitem');
    expect(cartoes).toHaveLength(2);
    const [origem, destino] = esperado.envolvidos;
    expect(cartoes[0]).toHaveTextContent('Lucinéia Barreto');
    expect(cartoes[0]).toHaveTextContent(`Antes: ${textoDoEstrato(origem!.antes.conta.estrato, origem!.antes.conta.icaExibido)}`);
    expect(cartoes[0]).toHaveTextContent(`Depois: ${textoDoEstrato(origem!.depois.conta.estrato, origem!.depois.conta.icaExibido)}`);
    expect(cartoes[1]).toHaveTextContent('Priscila Vasconcelos');
    expect(cartoes[1]).toHaveTextContent('Antes: 0 · Sem municípios');
    expect(cartoes[1]).toHaveTextContent(`Depois: ${textoDoEstrato(destino!.depois.conta.estrato, destino!.depois.conta.icaExibido)}`);
    expect(cartoes[0]).toHaveTextContent(origem!.mudouEstrato ? /Muda de estrato/ : /Continua em/);
    expect(cartoes[1]).toHaveTextContent(/Passa a ter carteira e entra na média da equipe/);

    expect(screen.getByText(/Dispersão da equipe: desvio 30,8 →/)).toBeInTheDocument();
  });

  test('adicionar sem município avisa; tirar um movimento volta ao início', async () => {
    const user = userEvent.setup();
    renderTelaIca('/integra/ica/simulador');
    await screen.findByRole('heading', { level: 1, name: 'Simulador de remanejamento' });
    await user.selectOptions(screen.getByLabelText('Coordenador de origem'), String(LUCINEIA));
    await user.selectOptions(screen.getByLabelText('Coordenador de destino'), String(PRISCILA));
    await user.click(screen.getByRole('button', { name: 'Adicionar à simulação' }));
    expect(screen.getByText('Escolha pelo menos um município para mover.')).toBeInTheDocument();

    await user.click(screen.getByRole('checkbox', { name: 'Belém-PA' }));
    await user.click(screen.getByRole('button', { name: 'Adicionar à simulação' }));
    await user.click(screen.getByRole('button', { name: 'Tirar Belém-PA da simulação' }));
    expect(screen.queryByRole('list', { name: 'Antes e depois de cada envolvido' })).not.toBeInTheDocument();
  });

  test('adicionar que deu certo anuncia na região viva o que entrou e onde ver; o foco fica no botão', async () => {
    const user = userEvent.setup();
    renderTelaIca('/integra/ica/simulador');
    await screen.findByRole('heading', { level: 1, name: 'Simulador de remanejamento' });
    const aviso = screen.getByRole('status');
    expect(aviso).toBeEmptyDOMElement();

    await user.selectOptions(screen.getByLabelText('Coordenador de origem'), String(LUCINEIA));
    await user.click(screen.getByRole('checkbox', { name: 'Belém-PA' }));
    await user.selectOptions(screen.getByLabelText('Coordenador de destino'), String(PRISCILA));
    const adicionar = screen.getByRole('button', { name: 'Adicionar à simulação' });
    await user.click(adicionar);
    expect(screen.getByRole('status')).toBe(aviso);
    expect(aviso).toHaveTextContent(
      'Belém-PA adicionado à simulação, de Lucinéia Barreto para Priscila Vasconcelos. Veja o resultado em "Antes e depois", logo abaixo.',
    );
    expect(adicionar).toHaveFocus();

    // Vários de uma vez: plural e a lista com "e".
    await user.click(screen.getByRole('checkbox', { name: 'Santarém-PA' }));
    await user.click(screen.getByRole('checkbox', { name: 'Manaus-AM' }));
    await user.click(adicionar);
    expect(aviso).toHaveTextContent(
      'Santarém-PA e Manaus-AM adicionados à simulação, de Lucinéia Barreto para Priscila Vasconcelos. Veja o resultado em "Antes e depois", logo abaixo.',
    );
  });

  test('propor exige justificativa: o erro fica junto do campo, ligado a ele, e o foco vai para o campo', async () => {
    const user = userEvent.setup();
    await montarMovimento(user);
    await user.click(screen.getByRole('button', { name: 'Propor remanejamento' }));
    const campo = screen.getByLabelText('Justificativa');
    expect(campo).toHaveAttribute('aria-invalid', 'true');
    expect(campo).toHaveAccessibleDescription(/Escreva a justificativa do remanejamento\./);
    expect(campo).toHaveFocus();
    // Não aparece lá em cima, em "Montar a simulação", longe do botão.
    const montar = screen.getByRole('region', { name: 'Montar a simulação' });
    expect(within(montar).queryByText('Escreva a justificativa do remanejamento.')).not.toBeInTheDocument();

    await user.type(campo, 'Agora com justificativa.');
    await user.click(screen.getByRole('button', { name: 'Propor remanejamento' }));
    expect(screen.queryByText('Escreva a justificativa do remanejamento.')).not.toBeInTheDocument();
  });

  test('foco do teclado depois de propor, aprovar e aplicar; o aviso fica numa região viva sempre montada', async () => {
    const user = userEvent.setup();
    await montarMovimento(user);
    const aviso = screen.getByRole('status');
    expect(aviso).toHaveTextContent(/adicionado à simulação/);

    await user.type(screen.getByLabelText('Justificativa'), 'Dar carteira a quem chegou.');
    await user.click(screen.getByRole('button', { name: 'Propor remanejamento' }));
    expect(screen.getByRole('status')).toBe(aviso);
    expect(aviso).toHaveTextContent(/Proposta registrada/);
    expect(aviso).toHaveFocus();

    const proposta = within(screen.getByRole('list', { name: 'Propostas desta sessão' })).getAllByRole('listitem')[0] as HTMLElement;
    await user.click(within(proposta).getByRole('button', { name: 'Aprovar (Líder do NFP)' }));
    expect(within(proposta).getByRole('button', { name: 'Aplicar' })).toHaveFocus();
    expect(aviso).toHaveTextContent(/Proposta aprovada/);

    await user.click(within(proposta).getByRole('button', { name: 'Aplicar' }));
    expect(proposta).toHaveFocus();
    expect(aviso).toHaveTextContent(/Remanejamento aplicado/);
  });

  test('tirar um movimento leva o foco ao próximo "Tirar"; tirar o último leva ao aviso', async () => {
    const user = userEvent.setup();
    await montarMovimento(user);
    await user.selectOptions(screen.getByLabelText('Coordenador de origem'), String(LUCINEIA));
    await user.click(screen.getByRole('checkbox', { name: 'Santarém-PA' }));
    await user.selectOptions(screen.getByLabelText('Coordenador de destino'), String(PRISCILA));
    await user.click(screen.getByRole('button', { name: 'Adicionar à simulação' }));

    await user.click(screen.getByRole('button', { name: 'Tirar Belém-PA da simulação' }));
    expect(screen.getByRole('button', { name: 'Tirar Santarém-PA da simulação' })).toHaveFocus();

    await user.click(screen.getByRole('button', { name: 'Tirar Santarém-PA da simulação' }));
    expect(screen.getByRole('status')).toHaveTextContent(/simulação ficou vazia/);
    expect(screen.getByRole('status')).toHaveFocus();
  });

  test('aplicar proposta que ficou velha: nada muda, o erro fica na proposta e o foco vai para ele', async () => {
    const user = userEvent.setup();
    // Duas propostas para Belém-PA: para a Priscila e para a Heloísa (104).
    for (const destino of [PRISCILA, 104]) {
      if (destino === PRISCILA) await montarMovimento(user);
      else {
        await user.selectOptions(screen.getByLabelText('Coordenador de origem'), String(LUCINEIA));
        await user.click(screen.getByRole('checkbox', { name: 'Belém-PA' }));
        await user.selectOptions(screen.getByLabelText('Coordenador de destino'), String(destino));
        await user.click(screen.getByRole('button', { name: 'Adicionar à simulação' }));
      }
      await user.type(screen.getByLabelText('Justificativa'), 'Teste.');
      await user.click(screen.getByRole('button', { name: 'Propor remanejamento' }));
    }
    const propostas = (): HTMLElement[] =>
      within(screen.getByRole('list', { name: 'Propostas desta sessão' })).getAllByRole('listitem').filter((li) => li.id !== '');
    // A lista mostra a mais nova primeiro: [para a Heloísa, para a Priscila].
    for (const p of propostas()) await user.click(within(p).getByRole('button', { name: 'Aprovar (Líder do NFP)' }));
    await user.click(within(propostas()[1]!).getByRole('button', { name: 'Aplicar' }));
    const velha = propostas()[0]!;
    await user.click(within(velha).getByRole('button', { name: 'Aplicar' }));

    expect(within(velha).getByText('Aprovada')).toBeInTheDocument();
    const erro = within(velha).getByText(/Esta proposta ficou velha: Belém-PA já não está com Lucinéia Barreto/);
    expect(erro.closest('[tabindex="-1"]')).toHaveFocus();
    expect(screen.getByRole('status')).not.toHaveTextContent(/Remanejamento aplicado/);
  });

  test('propor → aprovar (Líder do NFP, a validar) → aplicar com data de vigência; a carteira muda', async () => {
    const user = userEvent.setup();
    await montarMovimento(user);
    await user.type(screen.getByLabelText('Justificativa'), 'Dar carteira a quem chegou.');
    await user.click(screen.getByRole('button', { name: 'Propor remanejamento' }));

    expect(screen.getByText(/a validar no dia 7: na ata, a Líder do NFP só dá parecer/i)).toBeInTheDocument();
    const propostas = screen.getByRole('list', { name: 'Propostas desta sessão' });
    const proposta = within(propostas).getAllByRole('listitem')[0] as HTMLElement;
    expect(within(proposta).getByText('Proposta')).toBeInTheDocument();
    expect(proposta).toHaveTextContent('Dar carteira a quem chegou.');

    await user.click(within(proposta).getByRole('button', { name: 'Aprovar (Líder do NFP)' }));
    expect(within(proposta).getByText('Aprovada')).toBeInTheDocument();
    expect(proposta).toHaveTextContent('Aprovada por Você (demonstração)');
    expect(proposta).toHaveTextContent('Data de vigência: semestre 2026.2');

    await user.click(within(proposta).getByRole('button', { name: 'Aplicar' }));
    expect(within(proposta).getByText('Aplicada')).toBeInTheDocument();
    expect(proposta).toHaveTextContent(/Aplicada em \d{2}\/\d{2}\/\d{4}/);

    // A carteira de origem já não tem Belém.
    await user.selectOptions(screen.getByLabelText('Coordenador de origem'), String(LUCINEIA));
    expect(screen.queryByRole('checkbox', { name: 'Belém-PA' })).not.toBeInTheDocument();
  });
});
