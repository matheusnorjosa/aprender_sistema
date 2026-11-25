/**
 * Deslocamento — soma por coordenador: tempos REAIS sobre as carteiras FICTÍCIAS do gerador. É o mesmo
 * valor do componente "Tempo de deslocamento" do ICA; gráfico com o número escrito e tabela ao lado.
 */
import type { JSX } from 'react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, test } from 'vitest';

import { definirLarguraTela } from '../../../../test/larguraTela';
import { IntegraDemoProvider, useIntegraDemo } from '../../dados/IntegraDemoContext';
import { gerarDadosSimulados } from '../../dados/gerador';
import { calcularEquipe, formatarHoras, PESOS_REVISADOS } from '../../ica/calculo';
import { somaPorCoordenador } from '../contas';
import DeslocamentoRoutes from '../DeslocamentoRoutes';
import { renderTelaDeslocamento } from './telaDeslocamento';

const DADOS = gerarDadosSimulados();
const SOMAS = somaPorCoordenador(calcularEquipe(DADOS.base, PESOS_REVISADOS));

async function abrir(): Promise<void> {
  renderTelaDeslocamento('/integra/deslocamento/coordenadores');
  await screen.findByRole('heading', { level: 1, name: 'Soma por coordenador' });
}

describe('Deslocamento — soma por coordenador', { timeout: 20000 }, () => {
  test('explica a conta e avisa que os coordenadores são fictícios', async () => {
    await abrir();
    expect(screen.getByText(/Soma do tempo de ida e volta de cada município ativo/)).toHaveTextContent(
      /mesmo número do componente .Tempo de deslocamento. do ICA/,
    );
    expect(screen.getByText(/Coordenadores e carteiras fictícios/)).toBeInTheDocument();
  });

  test('gráfico: cada coordenador com o nome e a soma escritos, da maior para a menor', async () => {
    await abrir();
    const grafico = screen.getByRole('figure', { name: /Horas de ida e volta somadas/ });
    const itens = within(grafico).getAllByRole('listitem');
    expect(itens).toHaveLength(17);
    const primeiro = SOMAS[0]!;
    expect(itens[0]).toHaveTextContent(primeiro.coordenador.nome);
    expect(itens[0]).toHaveTextContent(`${formatarHoras(primeiro.somaHoras)} em ${primeiro.municipios} municípios`);
    expect(itens[16]).toHaveTextContent('Priscila Vasconcelos');
    expect(itens[16]).toHaveTextContent('Sem municípios');
  });

  test('tabela ao lado: municípios, soma, média, maior trajeto; link para a ficha do ICA', async () => {
    await abrir();
    const tabela = screen.getByRole('table', { name: 'Soma de ida e volta por coordenador' });
    const lucineia = SOMAS.find((s) => s.coordenador.id === 101)!;
    const linha = within(tabela).getByRole('link', { name: 'Lucinéia Barreto' }).closest('tr') as HTMLElement;
    expect(within(tabela).getByRole('link', { name: 'Lucinéia Barreto' })).toHaveAttribute('href', '/integra/ica/coordenador/101');
    expect(linha).toHaveTextContent(formatarHoras(lucineia.somaHoras));
    expect(linha).toHaveTextContent(formatarHoras(lucineia.mediaHoras));
    expect(linha).toHaveTextContent(`Guarapuava-PR (${formatarHoras(lucineia.maior!.horas)})`);
  });

  test('sem localidade entra com a mediana (estimado); suspenso fica fora, e a tela diz', async () => {
    await abrir();
    const tabela = screen.getByRole('table', { name: 'Soma de ida e volta por coordenador' });
    const rogerio = within(tabela).getByRole('link', { name: 'Rogério Assunção' }).closest('tr') as HTMLElement;
    expect(rogerio).toHaveTextContent('Amigos do Bem-CE com a mediana (estimado)');
    const jucelia = within(tabela).getByRole('link', { name: 'Jucélia Montenegro' }).closest('tr') as HTMLElement;
    expect(jucelia).toHaveTextContent('Fora da soma (suspenso): Capivari-SP');
  });

  test('acompanha a sessão: depois de um remanejamento, a soma muda', async () => {
    function MoverParaPriscila(): JSX.Element {
      const { base, proporRemanejamento, aprovarRemanejamento, aplicarRemanejamento } = useIntegraDemo();
      return (
        <button
          type="button"
          onClick={() => {
            const guarapuava = base.municipios.find((m) => m.nome === 'Guarapuava')!.id;
            const r = proporRemanejamento([{ municipioId: guarapuava, deCoordenadorId: 101, paraCoordenadorId: 117 }], 'teste');
            if (!r.ok) throw new Error(r.erros.join(' '));
            aprovarRemanejamento(r.id);
            aplicarRemanejamento(r.id);
          }}
        >
          mover Guarapuava
        </button>
      );
    }
    render(
      <MemoryRouter initialEntries={['/integra/deslocamento/coordenadores']}>
        <IntegraDemoProvider>
          <MoverParaPriscila />
          <Routes>
            <Route path="/integra/deslocamento/*" element={<DeslocamentoRoutes />} />
          </Routes>
        </IntegraDemoProvider>
      </MemoryRouter>,
    );
    await userEvent.click(await screen.findByRole('button', { name: 'mover Guarapuava' }));
    const tabela = screen.getByRole('table', { name: 'Soma de ida e volta por coordenador' });
    const priscila = within(tabela).getByRole('link', { name: 'Priscila Vasconcelos' }).closest('tr') as HTMLElement;
    expect(priscila).toHaveTextContent('26h30');
  });

  test('a 400 px a tabela manda colunas para a linha expandida (sem rolagem horizontal)', async () => {
    await abrir();
    act(() => definirLarguraTela(400));
    const tabela = screen.getByRole('table', { name: 'Soma de ida e volta por coordenador' });
    expect(within(tabela).queryByRole('columnheader', { name: 'Maior trajeto' })).not.toBeInTheDocument();
    expect(within(tabela).getByRole('button', { name: 'Expandir linha de Lucinéia Barreto' })).toBeInTheDocument();
  });
});
