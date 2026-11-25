/**
 * Painel do ICA (DADOS SIMULADOS): cartões por estrato, barras sobre as faixas com a linha da média,
 * filtros, tabela com todos os componentes, aviso de dado incompleto e exportação.
 *
 * Números do gerador com a semente fixa e os pesos revisados (ver `dados/__tests__/gerador.test.ts`).
 */
import type { JSX } from 'react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, test, vi } from 'vitest';

import { definirLarguraTela } from '../../../../test/larguraTela';
import { gerarDadosSimulados } from '../../dados/gerador';
import { IntegraDemoProvider, useIntegraDemo } from '../../dados/IntegraDemoContext';
import { baixarCsv, imprimirPagina } from '../exportar';
import PainelIca from '../PainelIca';
import { renderTelaIca } from './telaIca';

vi.mock('../exportar', () => ({ baixarCsv: vi.fn(), imprimirPagina: vi.fn() }));

async function barras(): Promise<HTMLElement[]> {
  const lista = await screen.findByRole('list', { name: 'ICA por coordenador' });
  return within(lista).getAllByRole('listitem');
}

const PONTA_GROSSA = gerarDadosSimulados().base.municipios.find((m) => m.nome === 'Ponta Grossa')!.id;

/** Propõe, aprova e aplica Ponta Grossa-PR da Lucinéia (101) para a Heloísa (104), como o Simulador faria. */
function MoverPontaGrossa(): JSX.Element {
  const { proporRemanejamento, aprovarRemanejamento, aplicarRemanejamento } = useIntegraDemo();
  return (
    <button
      type="button"
      onClick={() => {
        const r = proporRemanejamento([{ municipioId: PONTA_GROSSA, deCoordenadorId: 101, paraCoordenadorId: 104 }], 'teste do painel');
        if (!r.ok) throw new Error(r.erros.join(' '));
        aprovarRemanejamento(r.id);
        aplicarRemanejamento(r.id);
      }}
    >
      mover Ponta Grossa
    </button>
  );
}

function renderPainelComMudanca(): void {
  render(
    <MemoryRouter initialEntries={['/integra/ica']}>
      <IntegraDemoProvider>
        <MoverPontaGrossa />
        <Routes>
          <Route path="/integra/ica" element={<PainelIca />} />
        </Routes>
      </IntegraDemoProvider>
    </MemoryRouter>,
  );
}

function itemDe(itens: HTMLElement[], nome: string): HTMLElement {
  return itens.find((li) => within(li).queryByRole('link', { name: nome })) as HTMLElement;
}

function resumo(): string[] {
  const lista = screen.getByRole('list', { name: 'Resumo do ICA' });
  return within(lista)
    .getAllByRole('listitem')
    .map((li) => li.textContent ?? '');
}

describe('Painel do ICA', { timeout: 20000 }, () => {
  beforeEach(() => {
    vi.mocked(baixarCsv).mockClear();
    vi.mocked(imprimirPagina).mockClear();
  });

  test('cartões: total, um por estrato, média e dispersão', async () => {
    renderTelaIca('/integra/ica');
    await barras();
    expect(resumo()).toEqual([
      '17 coordenadores',
      '3 em Sobrecarga',
      '2 em Atenção',
      '6 em Adequada',
      '5 em Capacidade disponível',
      '1 sem municípios',
      'Média: 100',
      'Dispersão: desvio 30,9 · menor 58 · maior 169',
    ]);
  });

  test('barras do maior para o menor, com número e nome do estrato; sem municípios no fim', async () => {
    renderTelaIca('/integra/ica');
    const itens = await barras();
    expect(itens).toHaveLength(17);
    expect(itens[0]).toHaveTextContent('Lucinéia Barreto');
    expect(itens[0]).toHaveTextContent('169 · Sobrecarga');
    expect(itens[16]).toHaveTextContent('Priscila Vasconcelos');
    expect(itens[16]).toHaveTextContent('0 · Sem municípios');
    expect(screen.getByText(/Linha vertical = média da equipe \(100\)/)).toBeInTheDocument();
    expect(screen.getByRole('list', { name: 'Faixas do ICA' })).toBeInTheDocument();
  });

  test('filtro de gerência e de estrato', async () => {
    const user = userEvent.setup();
    renderTelaIca('/integra/ica');
    await barras();
    await user.selectOptions(screen.getByLabelText('Gerência'), 'Gerência 2 (Rejane Tavares)');
    const daGerencia = await barras();
    expect(daGerencia.map((li) => within(li).getByRole('link').textContent)).toEqual([
      'Otávio Rangel',
      'Ivonete Sampaio',
      'Marlene Fontenele',
      'Valdir Maciel',
      'Socorro Bezerra Lins',
      'Neide Carvalhedo',
    ]);
    expect(resumo()[0]).toBe('6 coordenadores');

    await user.selectOptions(screen.getByLabelText('Gerência'), 'Todas');
    await user.selectOptions(screen.getByLabelText('Estrato'), 'Sobrecarga');
    expect(await barras()).toHaveLength(3);

    // Quem não tem municípios não está em estrato nenhum: tem a opção própria.
    await user.selectOptions(screen.getByLabelText('Estrato'), 'Capacidade disponível');
    const capacidade = (await barras()).map((li) => within(li).getByRole('link').textContent);
    expect(capacidade).toHaveLength(5);
    expect(capacidade).not.toContain('Priscila Vasconcelos');
    await user.selectOptions(screen.getByLabelText('Estrato'), 'Sem municípios');
    expect((await barras()).map((li) => within(li).getByRole('link').textContent)).toEqual(['Priscila Vasconcelos']);
  });

  test('filtro de atuação', async () => {
    const user = userEvent.setup();
    renderTelaIca('/integra/ica');
    await barras();
    await user.selectOptions(screen.getByLabelText('Atuação'), 'AMMA');
    const nomes = (await barras()).map((li) => within(li).getByRole('link').textContent);
    expect(nomes).toEqual(['Rosimeire Cavalcante', 'Jucélia Montenegro', 'Socorro Bezerra Lins', 'Joelma Furtado']);
  });

  test('semestre anterior: o retrato calculado com a versão de pesos daquele semestre', async () => {
    const user = userEvent.setup();
    renderTelaIca('/integra/ica');
    await barras();
    await user.selectOptions(screen.getByLabelText('Semestre'), '2026.1');
    const itens = await barras();
    expect(itens).toHaveLength(16);
    expect(itens[0]).toHaveTextContent('191 · Sobrecarga');
    expect(screen.getByText(/Retrato de 2026\.1, calculado em 15\/06\/2026/)).toHaveTextContent(/proposta v5/);
  });

  test('aviso de dado incompleto no topo e na linha da tabela', async () => {
    renderTelaIca('/integra/ica');
    await barras();
    expect(screen.getByText(/Dado incompleto: Rogério Assunção/)).toBeInTheDocument();
    const tabela = screen.getByRole('table');
    const linha = within(tabela).getByText('Rogério Assunção').closest('tr') as HTMLElement;
    expect(within(linha).getByText('Dado incompleto')).toBeInTheDocument();
  });

  test('tabela com todos os componentes', async () => {
    renderTelaIca('/integra/ica');
    await barras();
    const tabela = screen.getByRole('table');
    for (const coluna of ['Coordenador', 'ICA', 'Municípios', 'Frentes', 'Turmas', 'Professores', 'Deslocamento']) {
      expect(within(tabela).getByRole('columnheader', { name: coluna })).toBeInTheDocument();
    }
  });

  test('no papel, a tabela dá lugar a uma lista com todos os componentes, sem depender da largura da tela', async () => {
    renderTelaIca('/integra/ica');
    await barras();
    // Notebook de 1366 px: na tela, Estados, Gerência e Atuação só aparecem a partir de 1600 px.
    act(() => definirLarguraTela(1366));
    const tabela = screen.getByRole('table');
    expect(within(tabela).queryByRole('columnheader', { name: 'Gerência' })).not.toBeInTheDocument();
    // A tabela some na impressão (Tailwind `print:hidden`) e a lista só aparece nela (`hidden print:block`).
    expect(tabela.closest('.print\\:hidden')).not.toBeNull();
    const papel = screen.getByRole('list', { name: 'Todos os componentes, por coordenador' });
    expect(papel.closest('.hidden.print\\:block')).not.toBeNull();

    const itens = within(papel).getAllByRole('listitem');
    expect(itens).toHaveLength(17);
    const primeiro = itens[0] as HTMLElement;
    expect(within(primeiro).getByText('Lucinéia Barreto')).toBeInTheDocument();
    expect(primeiro).toHaveTextContent('169 · Sobrecarga');
    const rotulos = within(primeiro)
      .getAllByRole('term')
      .map((dt) => dt.textContent);
    expect(rotulos).toEqual(['ICA', 'Municípios', 'Frentes', 'Turmas', 'Professores', 'Deslocamento', 'Estados', 'Gerência', 'Atuação']);
    expect(within(papel).queryByRole('button')).not.toBeInTheDocument();
    expect(within(papel).queryByRole('link')).not.toBeInTheDocument();
    // Os avisos da linha também vão para o papel.
    const rogerio = itens.find((li) => within(li).queryByText('Rogério Assunção')) as HTMLElement;
    expect(within(rogerio).getByText('Dado incompleto')).toBeInTheDocument();
  });

  test('clicar no nome abre a ficha do coordenador', async () => {
    const user = userEvent.setup();
    renderTelaIca('/integra/ica');
    const [primeira] = await barras();
    await user.click(within(primeira as HTMLElement).getByRole('link', { name: 'Lucinéia Barreto' }));
    expect(await screen.findByRole('heading', { level: 1, name: 'Ficha do coordenador' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: 'Lucinéia Barreto' })).toBeInTheDocument();
  });

  test('com um coordenador só, o cartão diz "1 coordenador"', async () => {
    const user = userEvent.setup();
    renderTelaIca('/integra/ica');
    await barras();
    await user.selectOptions(screen.getByLabelText('Estrato'), 'Sem municípios');
    expect(resumo()[0]).toBe('1 coordenador');
  });

  test('no papel, uma linha diz quais filtros estão aplicados (os campos não saem na impressão)', async () => {
    const user = userEvent.setup();
    renderTelaIca('/integra/ica');
    await barras();
    const linha = screen.getByText(/^Filtros:/);
    expect(linha).toHaveClass('hidden', 'print:block');
    expect(linha).toHaveTextContent('Filtros: Gerência: todas · Atuação: todas · Estrato: todos · Semestre: 2026.2 (atual)');
    await user.selectOptions(screen.getByLabelText('Gerência'), 'Gerência 2 (Rejane Tavares)');
    await user.selectOptions(screen.getByLabelText('Estrato'), 'Sobrecarga');
    expect(screen.getByText(/^Filtros:/)).toHaveTextContent(
      'Filtros: Gerência: Gerência 2 (Rejane Tavares) · Atuação: todas · Estrato: Sobrecarga · Semestre: 2026.2 (atual)',
    );
  });

  test('os filtros voltam com "Voltar ao painel": ficam no endereço e a ficha leva de volta', async () => {
    const user = userEvent.setup();
    renderTelaIca('/integra/ica');
    await barras();
    await user.selectOptions(screen.getByLabelText('Gerência'), 'Gerência 2 (Rejane Tavares)');
    await user.selectOptions(screen.getByLabelText('Estrato'), 'Sobrecarga');
    await user.selectOptions(screen.getByLabelText('Semestre'), '2026.1');
    const [primeira] = await barras();
    await user.click(within(primeira as HTMLElement).getByRole('link'));
    await screen.findByRole('heading', { level: 1, name: 'Ficha do coordenador' });
    await user.click(screen.getByRole('link', { name: 'Voltar ao painel' }));
    await screen.findByRole('heading', { level: 1, name: 'Painel do ICA' });
    expect(screen.getByLabelText('Gerência')).toHaveValue('2');
    expect(screen.getByLabelText('Estrato')).toHaveValue('sobrecarga');
    expect(screen.getByLabelText('Semestre')).toHaveValue('2026.1');
    expect(screen.getByLabelText('Atuação')).toHaveValue('');
  });

  test('exportar planilha (o que está filtrado) e imprimir', async () => {
    const user = userEvent.setup();
    renderTelaIca('/integra/ica');
    await barras();
    await user.selectOptions(screen.getByLabelText('Estrato'), 'Sobrecarga');
    await user.click(screen.getByRole('button', { name: /Baixar planilha/ }));
    expect(baixarCsv).toHaveBeenCalledTimes(1);
    const [nome, cabecalho, linhas] = vi.mocked(baixarCsv).mock.calls[0] as Parameters<typeof baixarCsv>;
    expect(nome).toBe('ica_painel_2026-2.csv');
    expect(cabecalho).toContain('Coordenador');
    expect(cabecalho).toContain('Estrato');
    expect(linhas).toHaveLength(3);
    expect(linhas[0]?.[0]).toBe('Lucinéia Barreto');

    await user.click(screen.getByRole('button', { name: /Imprimir \/ salvar PDF/ }));
    expect(imprimirPagina).toHaveBeenCalledTimes(1);
  });

  test('depois de uma mudança na sessão, o painel abre em "Agora (nesta demonstração)" e diz isso', async () => {
    const user = userEvent.setup();
    renderPainelComMudanca();
    await barras();
    await user.click(screen.getByRole('button', { name: 'mover Ponta Grossa' }));

    const semestre = screen.getByLabelText('Semestre');
    expect(within(semestre).getAllByRole('option').map((o) => o.textContent)).toEqual([
      'Agora (nesta demonstração)',
      '2026.2',
      '2026.1',
      '2025.2',
    ]);
    expect(within(semestre).getByRole('option', { name: 'Agora (nesta demonstração)' })).toHaveProperty('selected', true);
    const itens = await barras();
    expect(itemDe(itens, 'Heloísa Pimentel')).toHaveTextContent('136 · Sobrecarga');
    expect(itemDe(itens, 'Lucinéia Barreto')).toHaveTextContent('157 · Sobrecarga');
    expect(screen.getByText(/O ICA compara a carga/)).toHaveTextContent(/nesta demonstração/);
    expect(screen.getByText(/O ICA compara a carga/)).not.toHaveTextContent(/\(atual\)/);
    expect(screen.getByText(/^Filtros:/)).toHaveTextContent('Semestre: Agora (nesta demonstração)');

    await user.click(screen.getByRole('button', { name: /Baixar planilha/ }));
    const [nome, , linhas] = vi.mocked(baixarCsv).mock.calls[0] as Parameters<typeof baixarCsv>;
    expect(nome).toBe('ica_painel_2026-2_nesta-demonstracao.csv');
    expect(linhas.find((l) => l[0] === 'Heloísa Pimentel')?.[3]).toBe(136);
  });

  test('depois de uma mudança na sessão, 2026.2 mostra o retrato publicado, como a Ficha e o Histórico', async () => {
    const user = userEvent.setup();
    renderPainelComMudanca();
    await barras();
    await user.click(screen.getByRole('button', { name: 'mover Ponta Grossa' }));
    await user.selectOptions(screen.getByLabelText('Semestre'), '2026.2');

    const itens = await barras();
    expect(itemDe(itens, 'Heloísa Pimentel')).toHaveTextContent('124 · Atenção');
    expect(itemDe(itens, 'Lucinéia Barreto')).toHaveTextContent('169 · Sobrecarga');
    expect(screen.getByText(/Retrato de 2026\.2, calculado em/)).toHaveTextContent(/Configuração revisada/);
    expect(screen.getByText(/^Filtros:/)).toHaveTextContent(/Semestre: 2026\.2$/);

    await user.click(screen.getByRole('button', { name: /Baixar planilha/ }));
    const [nome, , linhas] = vi.mocked(baixarCsv).mock.calls[0] as Parameters<typeof baixarCsv>;
    expect(nome).toBe('ica_painel_2026-2.csv');
    expect(linhas.find((l) => l[0] === 'Heloísa Pimentel')?.[3]).toBe(124);

    // E volta para o recálculo da sessão.
    await user.selectOptions(screen.getByLabelText('Semestre'), 'Agora (nesta demonstração)');
    expect(itemDe(await barras(), 'Heloísa Pimentel')).toHaveTextContent('136 · Sobrecarga');
  });

  test('a 400 px a tabela manda colunas para a linha expandida (sem rolagem horizontal)', async () => {
    renderTelaIca('/integra/ica');
    await barras();
    act(() => definirLarguraTela(400));
    const tabela = screen.getByRole('table');
    expect(within(tabela).queryByRole('columnheader', { name: 'Professores' })).not.toBeInTheDocument();
    expect(within(tabela).getByRole('button', { name: 'Expandir linha de Lucinéia Barreto' })).toBeInTheDocument();
  });
});
