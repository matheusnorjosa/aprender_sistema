/**
 * G30 (Programa C) — Meus Bloqueios sem rolagem horizontal: ResponsiveTable, sem `scroll.x` 800 nem
 * coluna Ações fixa. Sempre na linha: o início, o status e as ações (AcoesLinha, "Excluir: bloqueio de
 * <início>"). O Fim sobe a partir de sm (abaixo disso, o status vai junto do início); Tipo e Motivo, de
 * md. O que some da linha vai para a linha expandida. Na página, o cartão da lista só divide a largura
 * com o formulário a partir de xxl: na metade da tela, as 6 colunas não cabiam.
 */
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Modal } from 'antd';
import { describe, expect, test, vi } from 'vitest';

import { definirLarguraTela } from '../../test/larguraTela';
import MyBlocksTable, { type BlockRecord } from '../MyBlocksTable';

const BLOQUEIO: BlockRecord = {
  id: 1,
  inicio: '2026-09-15T12:00:00Z',
  fim: '2026-09-15T18:00:00Z',
  tipo: 'P',
  status: 'aprovado',
  motivo: 'Participação no seminário estadual',
};
const ALVO = 'bloqueio de 15/09/2026 09:00';

function renderTabela(onDelete = vi.fn()) {
  return render(<MyBlocksTable blocks={[BLOQUEIO]} onDelete={onDelete} loading={false} />);
}

function cabecalhos(): string[] {
  return screen
    .getAllByRole('columnheader')
    .filter((th) => !th.classList.contains('ant-table-row-expand-icon-cell'))
    .map((th) => th.textContent?.trim() ?? '')
    .filter(Boolean);
}

function linha(): HTMLElement {
  const tr = screen.getByText('15/09/2026 09:00').closest('tr');
  if (!tr) throw new Error('o início não está numa linha da tabela');
  return tr;
}

describe('MyBlocksTable sem rolagem horizontal (G30)', () => {
  test('a 1280 px: todas as colunas, sem coluna fixa nem largura forçada; Excluir pelo nome do bloqueio', () => {
    const { container } = renderTabela();

    expect(cabecalhos()).toEqual(['Início', 'Fim', 'Tipo', 'Status', 'Motivo', 'Ações']);
    expect(container.querySelector('.ant-table-cell-fix-right, .ant-table-cell-fix-left')).toBeNull();
    expect(container.querySelector('.ant-table-content')?.getAttribute('style') ?? '').not.toMatch(/overflow/);
    expect(container.querySelector('table')?.style.width ?? '').toBe('');
    expect(within(linha()).getByRole('button', { name: `Excluir: ${ALVO}` })).toBeInTheDocument();
    // O motivo é texto livre: corta com reticências.
    expect(within(linha()).getByText(BLOQUEIO.motivo!).closest('td')).toHaveClass('ant-table-cell-ellipsis');
  });

  test('a 768 px: Tipo e Motivo continuam na linha', () => {
    definirLarguraTela(768);
    renderTabela();

    expect(cabecalhos()).toEqual(['Início', 'Fim', 'Tipo', 'Status', 'Motivo', 'Ações']);
  });

  test('a 576 px: Tipo e Motivo vão para a linha expandida', async () => {
    definirLarguraTela(576);
    const user = userEvent.setup();
    renderTabela();

    expect(cabecalhos()).toEqual(['Início', 'Fim', 'Status', 'Ações']);
    await user.click(within(linha()).getByRole('button', { name: `Expandir linha de ${ALVO}` }));
    const expandida = within(document.querySelector<HTMLElement>('.ant-table-expanded-row')!);
    expect(expandida.getByText('Parcial')).toBeInTheDocument();
    expect(expandida.getByText(BLOQUEIO.motivo!)).toBeInTheDocument();
  });

  test('a 360 px: início com o status e o menu de ações; Excluir está no menu', async () => {
    definirLarguraTela(360);
    const user = userEvent.setup();
    renderTabela();

    expect(cabecalhos()).toEqual(['Início', 'Ações']);
    expect(within(linha()).getByText('APROVADO')).toBeInTheDocument();
    expect(within(linha()).queryByRole('button', { name: `Excluir: ${ALVO}` })).not.toBeInTheDocument();

    await user.click(within(linha()).getByRole('button', { name: `Mais ações: ${ALVO}` }));
    expect(await screen.findByRole('menuitem', { name: 'Excluir' })).toBeInTheDocument();

    await user.click(within(linha()).getByRole('button', { name: `Expandir linha de ${ALVO}` }));
    const expandida = within(document.querySelector<HTMLElement>('.ant-table-expanded-row')!);
    for (const texto of ['15/09/2026 15:00', 'Parcial', BLOQUEIO.motivo!]) {
      expect(expandida.getByText(texto)).toBeInTheDocument();
    }
  });

  test('Excluir: a confirmação cita o bloqueio, começa no Cancelar e só o OK exclui', async () => {
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    const onDelete = vi.fn();
    const user = userEvent.setup();
    renderTabela(onDelete);

    await user.click(screen.getByRole('button', { name: `Excluir: ${ALVO}` }));
    expect(confirmar).toHaveBeenCalledTimes(1);
    const opcoes = confirmar.mock.calls[0]![0];
    expect(opcoes).toMatchObject({ autoFocusButton: 'cancel', okText: 'Sim, excluir', cancelText: 'Cancelar' });
    expect(String(opcoes.content)).toContain('15/09/2026 09:00 a 15/09/2026 15:00');
    expect(onDelete).not.toHaveBeenCalled();
    void opcoes.onOk?.();
    expect(onDelete).toHaveBeenCalledWith(1);
    confirmar.mockRestore();
  });
});
