/**
 * Meio de transporte do deslocamento (decisão do dono, 11/11/2026, lista aprovada).
 *
 * - O formulário tem o Select "Meio de transporte" (opcional, lista do dono) e envia o valor (`AVIAO`,
 *   `ONIBUS`...); vazio vai como `null` (registro antigo segue sem meio).
 * - A lista mostra o rótulo ("Uber/Táxi"), não o valor. Sem rolagem horizontal: a coluna só entra
 *   na linha a partir de xxl, como a Observação; abaixo disso, na linha expandida.
 */
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { message } from 'antd';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';

import { ComAcesso } from '../../../test/comAcesso';
import { definirLarguraTela } from '../../../test/larguraTela';

const { listDeslocamentosMock, updateMock } = vi.hoisted(() => ({
  listDeslocamentosMock: vi.fn(),
  updateMock: vi.fn(),
}));

vi.mock('../../../api/deslocamentos', () => ({
  listDeslocamentos: listDeslocamentosMock,
  listFormadoresDoSetor: vi.fn().mockResolvedValue([]),
  listAlvosDeslocamento: vi.fn().mockResolvedValue([]),
  createDeslocamento: vi.fn(),
  updateDeslocamento: updateMock,
  deleteDeslocamento: vi.fn(),
}));
vi.mock('../../../components/DatImportsCentralizedBanner', () => ({ default: () => null }));

import DeslocamentosPage from '../DeslocamentosPage';

vi.setConfig({ testTimeout: 20_000 });

const LINHA = {
  id: 1,
  usuario: 1,
  usuario_nome: 'Fulano de Tal',
  pode_editar: true,
  origem: 'Fortaleza',
  destino: 'Sobral',
  start_date: '2026-11-10',
  end_date: '2026-11-12',
  observacao: '',
  meio_transporte: 'UBER_TAXI',
};
const ALVO = 'deslocamento de Fulano de Tal em 10/11/2026';

async function renderPage(): Promise<HTMLElement> {
  render(
    <MemoryRouter>
      <ComAcesso policies={['access_travel']}>
        <DeslocamentosPage />
      </ComAcesso>
    </MemoryRouter>,
  );
  const botao = await screen.findByRole('button', { name: `Editar: ${ALVO}` }, { timeout: 15000 });
  return botao.closest('tr')!;
}

async function escolherMeio(dialogo: HTMLElement, rotulo: string): Promise<void> {
  fireEvent.mouseDown(within(dialogo).getByLabelText('Meio de transporte'));
  const opcao = await screen.findByTitle(rotulo);
  fireEvent.click(opcao);
}

describe('DeslocamentosPage — meio de transporte', { timeout: 20000 }, () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listDeslocamentosMock.mockResolvedValue({ count: 1, next: null, previous: null, results: [LINHA] });
    vi.spyOn(message, 'success').mockImplementation(() => (() => undefined) as never);
  });

  test('novo deslocamento: o Select "Meio de transporte" oferece a lista do dono, na ordem', async () => {
    await renderPage();
    fireEvent.click(screen.getByRole('button', { name: /Novo Deslocamento/ }));
    const dialogo = await screen.findByRole('dialog', {}, { timeout: 8000 });

    fireEvent.mouseDown(within(dialogo).getByLabelText('Meio de transporte'));
    await screen.findByTitle('Avião');
    const opcoes = [...document.querySelectorAll('.ant-select-item-option')].map((o) => o.getAttribute('title'));
    expect(opcoes).toEqual(['Avião', 'Ônibus', 'Carro próprio', 'Carro da empresa', 'Uber/Táxi', 'Outro']);
    fireEvent.click(screen.getByTitle('Ônibus'));
    await waitFor(() => expect(within(dialogo).getByTitle('Ônibus')).toBeInTheDocument());
  });

  test('editar: vem com o meio gravado, troca e envia o novo valor', async () => {
    updateMock.mockResolvedValue(LINHA);
    const tr = await renderPage();
    fireEvent.click(within(tr).getByRole('button', { name: `Editar: ${ALVO}` }));
    const dialogo = await screen.findByRole('dialog', {}, { timeout: 8000 });
    expect(within(dialogo).getByTitle('Uber/Táxi')).toBeInTheDocument();

    await escolherMeio(dialogo, 'Avião');
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Salvar' }));

    await waitFor(() => expect(updateMock).toHaveBeenCalledTimes(1), { timeout: 8000 });
    expect(updateMock).toHaveBeenCalledWith(1, expect.objectContaining({ meio_transporte: 'AVIAO' }));
  });

  test('editar registro antigo sem meio: envia null', async () => {
    listDeslocamentosMock.mockResolvedValue({
      count: 1,
      next: null,
      previous: null,
      results: [{ ...LINHA, meio_transporte: null }],
    });
    updateMock.mockResolvedValue(LINHA);
    const tr = await renderPage();
    fireEvent.click(within(tr).getByRole('button', { name: `Editar: ${ALVO}` }));
    const dialogo = await screen.findByRole('dialog', {}, { timeout: 8000 });
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Salvar' }));

    await waitFor(() => expect(updateMock).toHaveBeenCalledTimes(1), { timeout: 8000 });
    expect(updateMock).toHaveBeenCalledWith(1, expect.objectContaining({ meio_transporte: null }));
  });

  test('a lista mostra o rótulo: na linha só a partir de xxl; abaixo, na linha expandida', async () => {
    const tr = await renderPage();
    expect(screen.queryByRole('columnheader', { name: 'Meio de transporte' })).not.toBeInTheDocument();
    expect(within(tr).queryByText('Uber/Táxi')).not.toBeInTheDocument();

    fireEvent.click(within(tr).getByRole('button', { name: `Expandir linha de ${ALVO}` }));
    const expandida = within(document.querySelector<HTMLElement>('.ant-table-expanded-row')!);
    expect(expandida.getByText('Meio de transporte')).toBeInTheDocument();
    expect(expandida.getByText('Uber/Táxi')).toBeInTheDocument();

    act(() => definirLarguraTela(1600));
    expect(await screen.findByRole('columnheader', { name: 'Meio de transporte' })).toBeInTheDocument();
    expect(within(screen.getByText('Fulano de Tal').closest('tr')!).getByText('Uber/Táxi')).toBeInTheDocument();
  });
});
