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
const SEMESTRE_ANTERIOR = DADOS.historico.at(-2)!;
const PESOS_ANTERIOR = DADOS.versoes_pesos.find((v) => v.id === SEMESTRE_ANTERIOR.versao_pesos)!.pesos;
const ALERTAS = gerarAlertas(DADOS.base, calcularEquipe(DADOS.base, PESOS_REVISADOS), {
  gerencias: DADOS.gerencias,
  pessoas: DADOS.pessoas,
  colecoes: DADOS.colecoes,
  anterior: calcularEquipe(SEMESTRE_ANTERIOR.base, PESOS_ANTERIOR),
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

  test('cada alerta com data, situação e "seria enviado para"', async () => {
    renderizar();
    const titulo = await screen.findByText('Lucinéia Barreto está fora da meta (169)');
    const cartao = titulo.closest('li') as HTMLElement;
    expect(cartao).toHaveTextContent('Data: 17/11/2026');
    expect(cartao).toHaveTextContent(/Situação: Aberto/);
    expect(cartao).toHaveTextContent('Seria enviado para: SPE');
    expect(within(cartao).getByRole('link', { name: /Ver a ficha de Lucinéia Barreto/ })).toHaveAttribute(
      'href',
      '/integra/ica/coordenador/101',
    );
  });

  test('"Entrou em Sobrecarga" só para quem não estava no semestre anterior (PDF, seção 6), e a tela explica', async () => {
    renderizar();
    await screen.findByRole('heading', { level: 1, name: 'Alertas' });
    expect(screen.queryByText(/Lucinéia Barreto (está|entrou) em Sobrecarga/)).not.toBeInTheDocument();
    expect(screen.getByText(/já estava em Sobrecarga no cálculo anterior/)).toHaveTextContent(
      /semestre anterior \(2026\.1\).*remanejamento ou de uma troca de pesos.*publicado de 2026\.2/,
    );
  });

  test('contrato sem coordenador: Rio Branco-AC, para a gestora operacional e a SPE', async () => {
    renderizar();
    // Com a coleção no título: dois contratos sem coordenador no mesmo município não ficam iguais.
    const cartao = (await screen.findByText(/^Contrato sem coordenador em Rio Branco-AC \([A-Z ]+\)$/)).closest('li') as HTMLElement;
    expect(cartao).toHaveTextContent('Seria enviado para: Gestora operacional, SPE');
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

  test('o texto da regra diz que 130 exato fica dentro da meta e sem alerta', async () => {
    renderizar();
    expect(await screen.findByText(/continua em .Fora da meta. quando passa de 130/)).toHaveTextContent(
      /Com 130 exato, fica dentro da meta e sem alerta/,
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
    expect(cabecalho).toContain('Seria enviado para');
    expect(linhas).toHaveLength(ALERTAS.length);
  });
});
