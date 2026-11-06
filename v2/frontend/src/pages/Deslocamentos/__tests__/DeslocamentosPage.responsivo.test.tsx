/**
 * G30 (Programa C) — Deslocamentos sem rolagem horizontal: ResponsiveTable, sem `scroll.x` 1000 nem
 * coluna Ações fixa. Sempre na linha: o formador e as ações (AcoesLinha, "Editar: deslocamento de
 * <formador> em <data>"; no celular, o menu "Mais ações"). As demais sobem por largura: Data Início a
 * partir de sm, Destino e Data Fim de md, Origem de lg; a Observação (texto longo) só entra na linha
 * de xxl. O que some da linha vai para a linha expandida.
 */
import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Modal } from 'antd';
import { MemoryRouter } from 'react-router';
import { describe, expect, test, vi } from 'vitest';

import { ComAcesso } from '../../../test/comAcesso';
import { definirLarguraTela } from '../../../test/larguraTela';

const { LINHA } = vi.hoisted(() => ({
  LINHA: {
    id: 1,
    usuario: 1,
    usuario_nome: 'Fulano de Tal',
    pode_editar: true,
    origem: 'Fortaleza',
    destino: 'Sobral',
    start_date: '2026-11-10',
    end_date: '2026-11-12',
    observacao: 'Ida e volta com o material',
  },
}));

vi.mock('../../../api/deslocamentos', () => ({
  listDeslocamentos: vi.fn().mockResolvedValue({ count: 1, next: null, previous: null, results: [LINHA] }),
  listFormadoresDoSetor: vi.fn().mockResolvedValue([]),
  listAlvosDeslocamento: vi.fn().mockResolvedValue([]),
  createDeslocamento: vi.fn(),
  updateDeslocamento: vi.fn(),
  deleteDeslocamento: vi.fn(),
}));
vi.mock('../../../components/DatImportsCentralizedBanner', () => ({ default: () => null }));

import DeslocamentosPage from '../DeslocamentosPage';

vi.setConfig({ testTimeout: 20_000 });

const ALVO = 'deslocamento de Fulano de Tal em 10/11/2026';

function renderPage() {
  return render(
    <MemoryRouter>
      <ComAcesso policies={['access_travel']}>
        <DeslocamentosPage />
      </ComAcesso>
    </MemoryRouter>,
  );
}

function cabecalhos(): string[] {
  return screen
    .getAllByRole('columnheader')
    .filter((th) => !th.classList.contains('ant-table-row-expand-icon-cell'))
    .map((th) => th.textContent?.trim() ?? '')
    .filter(Boolean);
}

async function linha(acao: 'Editar' | 'Mais ações' = 'Editar'): Promise<HTMLElement> {
  const botao = await screen.findByRole('button', { name: `${acao}: ${ALVO}` }, { timeout: 15000 });
  const tr = botao.closest('tr');
  if (!tr) throw new Error('o botão não está numa linha da tabela');
  return tr;
}

describe('DeslocamentosPage sem rolagem horizontal (G30)', { timeout: 20000 }, () => {
  test('a 1280 px: colunas por prioridade, sem coluna fixa nem largura forçada', async () => {
    const { container } = renderPage();
    const tr = await linha();

    expect(cabecalhos()).toEqual(['Formador', 'Origem', 'Destino', 'Data Início', 'Data Fim', 'Ações']);
    expect(container.querySelector('.ant-table-cell-fix-right, .ant-table-cell-fix-left')).toBeNull();
    expect(container.querySelector('.ant-table-content')?.getAttribute('style') ?? '').not.toMatch(/overflow/);
    expect(container.querySelector('table')?.style.width ?? '').toBe('');
    expect(within(tr).getByRole('button', { name: `Excluir: ${ALVO}` })).toBeInTheDocument();
    // Origem e destino são texto livre: cortam com reticências; o formador (identidade) quebra linha.
    expect(within(tr).getByText('Fortaleza').closest('td')).toHaveClass('ant-table-cell-ellipsis');
    expect(within(tr).getByText('Fulano de Tal').closest('td')).not.toHaveClass('ant-table-cell-ellipsis');
    // A Observação só entra na linha de xxl: até lá, na linha expandida.
    expect(within(tr).queryByText(LINHA.observacao)).not.toBeInTheDocument();
  });

  test('a 360 px: só o formador e o menu de ações; o resto na linha expandida', async () => {
    definirLarguraTela(360);
    const user = userEvent.setup();
    renderPage();
    const tr = await linha('Mais ações');

    expect(cabecalhos()).toEqual(['Formador', 'Ações']);
    expect(within(tr).queryByRole('button', { name: `Editar: ${ALVO}` })).not.toBeInTheDocument();

    await user.click(within(tr).getByRole('button', { name: `Mais ações: ${ALVO}` }));
    expect(await screen.findByRole('menuitem', { name: 'Editar' })).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: 'Excluir' })).toBeInTheDocument();

    await user.click(within(tr).getByRole('button', { name: `Expandir linha de ${ALVO}` }));
    const expandida = within(document.querySelector<HTMLElement>('.ant-table-expanded-row')!);
    for (const texto of ['Fortaleza', 'Sobral', '10/11/2026', '12/11/2026', LINHA.observacao]) {
      expect(expandida.getByText(texto)).toBeInTheDocument();
    }
  });

  test('mudar a largura com a página aberta reorganiza as colunas', async () => {
    renderPage();
    await linha();

    act(() => definirLarguraTela(768));
    expect(cabecalhos()).toEqual(['Formador', 'Destino', 'Data Início', 'Data Fim', 'Ações']);
  });

  test('o cabeçalho da página quebra linha (o botão Novo Deslocamento não empurra a tela)', async () => {
    renderPage();
    await linha();

    const botao = screen.getByRole('button', { name: /Novo Deslocamento/ });
    expect(botao.closest('.flex')).toHaveClass('flex-wrap');
  });

  test('Excluir: a confirmação cita o deslocamento e começa no Cancelar', async () => {
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    const user = userEvent.setup();
    renderPage();
    const tr = await linha();

    await user.click(within(tr).getByRole('button', { name: `Excluir: ${ALVO}` }));
    expect(confirmar).toHaveBeenCalledTimes(1);
    expect(confirmar.mock.calls[0]![0]).toMatchObject({ autoFocusButton: 'cancel', title: 'Excluir este deslocamento?' });
    expect(String(confirmar.mock.calls[0]![0].content)).toContain('Fulano de Tal, de Fortaleza a Sobral');
    confirmar.mockRestore();
  });
});
