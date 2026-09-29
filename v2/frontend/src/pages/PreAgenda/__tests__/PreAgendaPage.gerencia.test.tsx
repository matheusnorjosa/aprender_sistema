/**
 * PR A — PreAgenda filtra lista e KPIs pela mesma gerência (`gerencia_id`).
 *
 * Antes: campo de texto "setor/projeto" mandava `sector`, que a lista casava com
 * `projeto.gerencia.nome_setor` e o resumo com `projeto.nome` (conjuntos diferentes).
 * Agora: Select das gerências ATIVAS (rótulo de tela, valor = id) manda `gerencia_id`
 * nas duas chamadas. E o resumo não recebe o `status` da lista: lá `status` é o
 * `gcal_status` (o resumo já conta só aprovados) — com `status=approved` os KPIs zeravam.
 *
 * Reusa o harness de mocks do PreAgendaPage.lifecycle.test.tsx.
 */
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, test, vi } from 'vitest';

const { getMeMock, getGerenciasMock, listSolicitacoesMock, getStatusSummaryMock, fetchAPIMock } = vi.hoisted(() => ({
  getMeMock: vi.fn(),
  getGerenciasMock: vi.fn(),
  listSolicitacoesMock: vi.fn(),
  getStatusSummaryMock: vi.fn(),
  fetchAPIMock: vi.fn(),
}));

vi.mock('../../../api/config', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../../api/config')>();
  return { ...actual, fetchAPI: fetchAPIMock };
});
vi.mock('../../../api/availability', () => ({ getMe: getMeMock, getGerencias: getGerenciasMock }));
vi.mock('../../../api/solicitacoes', () => ({
  listSolicitacoes: listSolicitacoesMock,
  previewSolicitacao: vi.fn(),
  publishSolicitacao: vi.fn(),
  resyncSolicitacao: vi.fn(),
  cancelSolicitacao: vi.fn(),
}));
vi.mock('../../../api/gcal', () => ({
  getStatusSummary: getStatusSummaryMock,
  reapplyBatch: vi.fn(),
  resyncBatch: vi.fn(),
}));
vi.mock('../../../hooks/useGoogleIntegration', () => ({
  default: () => ({
    status: { connected: true, isExpired: false, googleEmail: 'x@y.br', tokenExpiry: null, expiresInDays: null },
    disconnect: vi.fn(),
    loading: false,
    error: null,
    fetchStatus: vi.fn(),
  }),
}));
vi.mock('../../../hooks/useGoogleGuard', () => ({
  default: () => ({ requireGoogleConnection: () => true, handleGoogleError: () => false, isConnected: true }),
}));
vi.mock('../../../hooks/usePolling', () => ({ usePolling: () => {} }));
vi.mock('../../../services/syncChannel', () => ({
  syncChannel: { subscribe: () => () => {}, publish: vi.fn() },
}));
vi.mock('../../../components/google/GoogleIntegrationCard', () => ({
  default: () => <div data-testid="google-card" />,
}));

import PreAgendaPage from '../PreAgendaPage';

beforeEach(() => {
  vi.clearAllMocks();
  getMeMock.mockResolvedValue({ setores: ['Controle'], funcoes: [], gerencias: [], is_superuser: false });
  getGerenciasMock.mockResolvedValue([
    { id: 2, nome: 'GERENCIA 2', nome_setor: 'Vidas', nome_exibicao: '', rotulo: 'Vidas', ativo: true },
    { id: 4, nome: 'GERENCIA 4', nome_setor: 'ACerta', nome_exibicao: 'Superativar', rotulo: 'Superativar', ativo: true },
  ]);
  listSolicitacoesMock.mockResolvedValue({ results: [], count: 0 });
  getStatusSummaryMock.mockResolvedValue({ counts: {}, total: 0 });
  fetchAPIMock.mockResolvedValue({});
});

describe('PreAgendaPage — filtro por gerência (PR A)', () => {
  test('o Select lista as gerências ativas pelo rótulo e manda gerencia_id na lista e no resumo', async () => {
    const user = userEvent.setup();
    render(<PreAgendaPage />);

    await waitFor(() => expect(getGerenciasMock).toHaveBeenCalledWith({ ativo: true }));
    await user.click(screen.getByRole('combobox', { name: 'Filtrar por gerência' }));
    await user.click(await screen.findByTitle('Superativar'));

    await waitFor(
      () => {
        expect(listSolicitacoesMock).toHaveBeenCalledWith(expect.objectContaining({ gerencia_id: '4', flow: 'SUPER' }));
        expect(listSolicitacoesMock).toHaveBeenCalledWith(expect.objectContaining({ gerencia_id: '4', flow: 'NAO_SUPER' }));
        expect(getStatusSummaryMock).toHaveBeenCalledWith(expect.objectContaining({ gerencia_id: '4' }));
      },
      { timeout: 5000 },
    );
    expect(screen.queryByText('GERENCIA 4')).not.toBeInTheDocument();
  }, 20000);

  test('filtros quebram linha e o Select é responsivo (sem rolagem horizontal no celular)', async () => {
    render(<PreAgendaPage />);

    const combobox = await screen.findByRole('combobox', { name: 'Filtrar por gerência' });
    const select = combobox.closest('.ant-select') as HTMLElement;
    // 100% no celular, 200px a partir de sm — sem largura fixa inline.
    expect(select.className).toContain('w-full');
    expect(select.className).toContain('sm:w-[200px]');
    expect(select.style.width).toBe('');
    // A linha de filtros quebra em vez de empurrar para a direita.
    const linha = select.closest('.ant-space') as HTMLElement;
    expect(linha.style.flexWrap).toBe('wrap');
  });

  test('o resumo (KPIs) não recebe o status da lista', async () => {
    render(<PreAgendaPage />);

    await waitFor(() => expect(getStatusSummaryMock).toHaveBeenCalled());
    expect(listSolicitacoesMock).toHaveBeenCalledWith(expect.objectContaining({ status: 'approved' }));
    for (const [filtros] of getStatusSummaryMock.mock.calls) {
      expect(filtros).not.toHaveProperty('status');
    }
  });
});
