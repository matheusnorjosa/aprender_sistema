/** ICA — Alertas (PDF do ICA, seção 6), com DADOS SIMULADOS do gerador. Nada é enviado. */
import { MemoryRouter } from 'react-router';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, test, vi } from 'vitest';

import { IntegraDemoProvider } from '../../dados/IntegraDemoContext';
import { gerarDadosSimulados } from '../../dados/gerador';
import { calcularEquipe, gerarAlertas, PESOS_REVISADOS } from '../calculo';
import AlertasIca from '../AlertasIca';
import * as exportar from '../exportar';

const DADOS = gerarDadosSimulados();
const ALERTAS = gerarAlertas(DADOS.base, calcularEquipe(DADOS.base, PESOS_REVISADOS), {
  gerencias: DADOS.gerencias,
  pessoas: DADOS.pessoas,
  colecoes: DADOS.colecoes,
});

function renderizar(): void {
  render(
    <MemoryRouter>
      <IntegraDemoProvider dados={gerarDadosSimulados()}>
        <AlertasIca />
      </IntegraDemoProvider>
    </MemoryRouter>,
  );
}

const cartoes = (): HTMLElement[] => {
  const lista = screen.getByRole('list', { name: 'Lista de alertas' });
  return within(lista)
    .getAllByRole('listitem')
    .filter((li) => li.parentElement === lista);
};

describe('ICA — Alertas', { timeout: 20000 }, () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  test('avisa que nada é enviado e lista todos os alertas', async () => {
    renderizar();
    expect(await screen.findByRole('heading', { level: 1, name: 'Alertas' })).toBeInTheDocument();
    expect(screen.getByText(/Nada é enviado/)).toBeInTheDocument();
    expect(cartoes()).toHaveLength(ALERTAS.length);
    for (const a of ALERTAS) expect(screen.getByText(a.titulo)).toBeInTheDocument();
  });

  test('cada alerta com data, situação e para quem seria enviado, no sistema e por e-mail institucional (decisão 83)', async () => {
    renderizar();
    const titulo = await screen.findByText('Lucinéia Barreto está em Sobrecarga (167)');
    const cartao = titulo.closest('li') as HTMLElement;
    expect(cartao).toHaveTextContent('Data: 17/11/2026');
    expect(cartao).toHaveTextContent(/Situação: Aberto/);
    expect(cartao).toHaveTextContent(
      /Seria enviado no sistema e por e-mail institucional para: SPE, Gestora pedagógica \(.+\), Líder do NFP/,
    );
    expect(screen.getByText(/Nada é enviado/).closest('p')).toHaveTextContent(
      /Na versão real, cada um iria no sistema e por e-mail institucional para as pessoas/,
    );
    expect(within(cartao).getByRole('link', { name: /Ver a ficha de Lucinéia Barreto/ })).toHaveAttribute(
      'href',
      '/integra/ica/coordenador/101',
    );
  });

  test('decisão 69: "Está em Sobrecarga" sai a cada recálculo para quem continua na faixa, sem o "Fora da meta" junto', async () => {
    renderizar();
    await screen.findByRole('heading', { level: 1, name: 'Alertas' });
    // Lucinéia já estava em Sobrecarga em 2026.1 e recebe o alerta de novo.
    expect(screen.getByText('Lucinéia Barreto está em Sobrecarga (167)')).toBeInTheDocument();
    expect(screen.queryByText(/Lucinéia Barreto está fora da meta/)).not.toBeInTheDocument();
    expect(screen.getByText(/sai a cada recálculo/)).toHaveTextContent(
      /enquanto o ICA estiver em 130 ou mais, e não só quando ele chega lá \(decisão 69\)/,
    );
    expect(within(screen.getByLabelText('Mostrar')).getByRole('option', { name: /^Está em Sobrecarga \(3\)$/ })).toBeInTheDocument();
    // Um nome só para cada cargo: o mesmo da página Para validar (decisões 69 e 87).
    expect(screen.getByText(/sai a cada recálculo/)).toHaveTextContent(/para a SPE, a gestora pedagógica dele e a Líder do NFP/);
    expect(document.body).not.toHaveTextContent(/gestora técnica|gestora operacional/i);
  });

  test('projeto sem coordenador: Itaquiraí-MS, para a Gerente Operacional e a SPE', async () => {
    renderizar();
    // Com a coleção no título: dois projetos sem coordenador no mesmo município não ficam iguais.
    // Decisão 46: a palavra é "projeto", não "contrato".
    const cartao = (await screen.findByText(/^Projeto sem coordenador em Itaquiraí-MS \([A-Z ]+\)$/)).closest('li') as HTMLElement;
    expect(cartao).toHaveTextContent('Seria enviado no sistema e por e-mail institucional para: Gerente Operacional, SPE');
    expect(cartao).toHaveTextContent('Aberto: sai quando o projeto tiver um coordenador definido.');
    expect(within(screen.getByLabelText('Mostrar')).getByRole('option', { name: /^Projeto sem coordenador \(\d+\)$/ })).toBeInTheDocument();
    expect(document.body).not.toHaveTextContent(/contrato/i);
  });

  test('no papel, uma linha diz o que a lista filtrada mostra', async () => {
    const user = userEvent.setup();
    renderizar();
    await user.selectOptions(await screen.findByLabelText('Mostrar'), 'dado_incompleto');
    const esperados = ALERTAS.filter((a) => a.tipo === 'dado_incompleto').length;
    const linha = screen.getByText(/^Mostrando:/);
    expect(linha).toHaveClass('hidden', 'print:block');
    expect(linha).toHaveTextContent(`Mostrando: Dado incompleto, ${esperados} de ${ALERTAS.length}`);
  });

  test('o texto da regra diz que quem está em Sobrecarga não recebe também o "Fora da meta"', async () => {
    renderizar();
    expect(await screen.findByText(/sai a cada recálculo/)).toHaveTextContent(
      /Quem está em Sobrecarga não recebe também o .Fora da meta., que fica para quem está abaixo de 70/,
    );
  });

  test('filtrar por tipo mostra só aquele tipo', async () => {
    renderizar();
    await userEvent.selectOptions(await screen.findByLabelText('Mostrar'), 'dado_incompleto');
    const esperados = ALERTAS.filter((a) => a.tipo === 'dado_incompleto');
    expect(cartoes()).toHaveLength(esperados.length);
    expect(screen.getByText(esperados[0]!.titulo)).toBeInTheDocument();
  });

  test('baixar planilha: os alertas mostrados, com quem receberia', async () => {
    const baixar = vi.spyOn(exportar, 'baixarCsv').mockImplementation(() => undefined);
    renderizar();
    await userEvent.click(await screen.findByRole('button', { name: /Baixar planilha/i }));
    const [nome, cabecalho, linhas] = baixar.mock.calls[0]!;
    expect(nome).toBe('ica_alertas.csv');
    expect(cabecalho).toContain('Seria enviado no sistema e por e-mail institucional para');
    expect(linhas).toHaveLength(ALERTAS.length);
  });
});
