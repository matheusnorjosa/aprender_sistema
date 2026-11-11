/**
 * Feedbacks (11/11/2026): lista o que as pessoas enviaram, filtra por tipo e nota (a API filtra) e
 * exporta CSV com os mesmos filtros.
 */
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfigProvider } from 'antd';
import ptBR from 'antd/locale/pt_BR';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';

const { FEEDBACK } = vi.hoisted(() => ({
  FEEDBACK: {
    id: 7,
    pessoa: 'Ana Formadora',
    nota: 2,
    tipo: 'PROBLEMA' as const,
    comentario: 'A grade não carrega no celular quando escolho outro mês.',
    pagina: '/solicitacoes/disponibilidade',
    created_at: '2026-11-10T12:05:00Z',
  },
}));

vi.mock('../../../api/feedback', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../../../api/feedback')>()),
  listFeedbacks: vi.fn(),
  exportarFeedbacks: vi.fn(),
}));

import { exportarFeedbacks, listFeedbacks } from '../../../api/feedback';
import FeedbacksPage from '../FeedbacksPage';

function renderPage() {
  return render(
    <ConfigProvider locale={ptBR}>
      <MemoryRouter>
        <FeedbacksPage />
      </MemoryRouter>
    </ConfigProvider>,
  );
}

async function escolher(user: ReturnType<typeof userEvent.setup>, rotulo: string, opcao: string): Promise<void> {
  await user.click(screen.getByRole('combobox', { name: rotulo }));
  const lista = document.querySelector<HTMLElement>('.ant-select-dropdown:not(.ant-select-dropdown-hidden)')!;
  await user.click(within(lista).getByText(opcao));
}

describe('FeedbacksPage', { timeout: 20000 }, () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(listFeedbacks).mockResolvedValue({ results: [FEEDBACK], count: 1, next: null, previous: null });
  });

  test('lista com data de Fortaleza, pessoa, nota, tipo, tela e comentário', async () => {
    renderPage();

    const linha = (await screen.findByText('Ana Formadora', { selector: 'td, td *' })).closest('tr')!;
    expect(within(linha).getByText('10/11/2026 09:05')).toBeInTheDocument();
    expect(within(linha).getByText('Problema')).toBeInTheDocument();
    expect(within(linha).getByText('/solicitacoes/disponibilidade')).toBeInTheDocument();
    expect(within(linha).getByText(FEEDBACK.comentario)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Feedbacks (1)' })).toBeInTheDocument();
    expect(listFeedbacks).toHaveBeenCalledWith({ page: 1, page_size: expect.any(Number) });
  });

  test('o comentário inteiro fica na linha expandida', async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole('button', { name: 'Expandir linha de Ana Formadora em 10/11/2026 09:05' }));

    expect(await screen.findByText('Comentário completo')).toBeInTheDocument();
  });

  test('filtro de tipo e de nota chamam a API com o filtro, voltando à página 1', async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText('Ana Formadora', { selector: 'td, td *' });

    await escolher(user, 'Filtrar por tipo', 'Problema');
    await waitFor(() =>
      expect(listFeedbacks).toHaveBeenLastCalledWith(expect.objectContaining({ tipo: 'PROBLEMA', page: 1 })),
    );

    await escolher(user, 'Filtrar por nota', 'Nota 2');
    await waitFor(() =>
      expect(listFeedbacks).toHaveBeenLastCalledWith(expect.objectContaining({ tipo: 'PROBLEMA', nota: 2, page: 1 })),
    );
  });

  test('exportar CSV leva os filtros da tela', async () => {
    const user = userEvent.setup();
    vi.mocked(exportarFeedbacks).mockResolvedValue(new Blob(['Data'], { type: 'text/csv' }));
    const criarUrl = vi.fn(() => 'blob:feedbacks');
    Object.assign(URL, { createObjectURL: criarUrl, revokeObjectURL: vi.fn() });
    renderPage();
    await screen.findByText('Ana Formadora', { selector: 'td, td *' });

    await escolher(user, 'Filtrar por tipo', 'Elogio');
    await user.click(screen.getByRole('button', { name: /Exportar CSV/ }));

    await waitFor(() => expect(exportarFeedbacks).toHaveBeenCalledWith(expect.objectContaining({ tipo: 'ELOGIO' })));
    expect(criarUrl).toHaveBeenCalled();
  });

  test('vazio sem filtro e erro com o motivo', async () => {
    vi.mocked(listFeedbacks).mockResolvedValueOnce({ results: [], count: 0, next: null, previous: null });
    const { unmount } = renderPage();
    expect(await screen.findByText('Nenhum feedback recebido ainda.')).toBeInTheDocument();
    unmount();

    vi.mocked(listFeedbacks).mockRejectedValueOnce(new Error('Sem conexão com o servidor.'));
    renderPage();
    expect(await screen.findByText('Sem conexão com o servidor.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Tentar de novo' })).toBeInTheDocument();
  });
});
