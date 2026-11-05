/**
 * G27 (decisão do dono, 05/11/2026): o DAT exclui pela Pré-agenda o evento de outra pessoa.
 *
 * O servidor já deixava (o `destroy` e o `pode_excluir` da lista), mas nenhuma tela oferecia:
 * a Pré-agenda só tinha "Remover do Google". Excluir aparece só para o DAT (e o superusuário),
 * só na linha em que o servidor diz que dá (`pode_excluir`), e tira dos dois lados com a mesma
 * confirmação de Publicar na agenda. O Controle continua só com "Remover do Google".
 *
 * Atores: DAT e Controle de `test/atoresRbac.ts` (as policies medidas no backend).
 */
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { Modal, message } from 'antd';
import { beforeEach, describe, expect, test, vi } from 'vitest';

const { getMeMock, listSolicitacoesMock, deleteSolicitacaoMock } = vi.hoisted(() => ({
  getMeMock: vi.fn(),
  listSolicitacoesMock: vi.fn(),
  deleteSolicitacaoMock: vi.fn(),
}));

vi.mock('../../../api/config', async (importOriginal) => {
  const actual = (await importOriginal());
  return { ...actual, fetchAPI: vi.fn().mockResolvedValue({}) };
});
vi.mock('../../../api/availability', () => ({ getMe: getMeMock, getGerencias: vi.fn().mockResolvedValue([]) }));
vi.mock('../../../api/solicitacoes', () => ({
  listSolicitacoes: listSolicitacoesMock,
  previewSolicitacao: vi.fn(),
  publishSolicitacao: vi.fn(),
  resyncSolicitacao: vi.fn(),
  cancelSolicitacao: vi.fn(),
  deleteSolicitacao: deleteSolicitacaoMock,
}));
vi.mock('../../../api/gcal', () => ({
  getStatusSummary: vi.fn().mockResolvedValue({ counts: {}, total: 0 }),
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
vi.mock('../../../hooks/usePolling', () => ({ usePolling: () => ({ pausado: false, pausar: () => {} }) }));
vi.mock('../../../services/syncChannel', () => ({
  syncChannel: { subscribe: () => () => {}, publish: vi.fn() },
}));
vi.mock('../../../components/google/GoogleIntegrationCard', () => ({
  default: () => <div data-testid="google-card" />,
}));

import { ComAcesso } from '../../../test/comAcesso';
import { atorRbac } from '../../../test/atoresRbac';
import PreAgendaPage from '../PreAgendaPage';

// Tela pesada (AntD + ResponsiveTable): na CI os casos passam dos 5 s padrão.
vi.setConfig({ testTimeout: 20_000 });

const DAT = atorRbac('DAT').policies;
const CONTROLE = atorRbac('Controle').policies;
const FUTURO = { inicio: '2099-11-05T09:00:00-03:00', fim: '2099-11-05T12:00:00-03:00' };
const EXCLUIR = /^Excluir evento:/;

const row = (overrides: Record<string, unknown> = {}) => ({
  id: 1,
  municipio_nome: 'Fortaleza',
  projeto_nome: 'Projeto',
  tipo: 'Formação',
  gcal_status: 'PUBLISHED',
  external_event_id: 'evt-1',
  meet_link: null,
  pode_excluir: true,
  ...FUTURO,
  ...overrides,
});

function mockRows(rows: Array<Record<string, unknown>>) {
  listSolicitacoesMock.mockImplementation((f: { flow: string }) =>
    Promise.resolve(f.flow === 'SUPER' ? { results: rows, count: rows.length } : { results: [], count: 0 }),
  );
}

function renderComo(policies: readonly string[]): void {
  render(
    <ComAcesso policies={policies}>
      <PreAgendaPage />
    </ComAcesso>,
  );
}

async function linha(nome: string): Promise<HTMLElement> {
  return (await screen.findByText(nome)).closest('tr') as HTMLElement;
}

beforeEach(() => {
  vi.clearAllMocks();
  getMeMock.mockResolvedValue({ setores: ['DAT'], funcoes: [], is_superuser: false });
  listSolicitacoesMock.mockResolvedValue({ results: [], count: 0 });
  deleteSolicitacaoMock.mockResolvedValue(undefined);
});

describe('PreAgendaPage — Excluir (G27)', () => {
  test('o DAT vê Excluir, ao lado de Remover do Google, só onde o servidor deixa', async () => {
    mockRows([
      row({ id: 1, municipio_nome: 'Sobral', pode_excluir: true }),
      row({ id: 2, municipio_nome: 'Crato', pode_excluir: false }),
    ]);
    renderComo(DAT);
    const sobral = await linha('Sobral');
    expect(within(sobral).getByLabelText(EXCLUIR)).toBeInTheDocument();
    expect(within(sobral).getByLabelText(/^Remover do Google Agenda:/)).toBeInTheDocument();
    expect(within(await linha('Crato')).queryByLabelText(EXCLUIR)).not.toBeInTheDocument();
  });

  test('o Controle não vê Excluir, mesmo quando o servidor deixaria: continua só com Remover do Google', async () => {
    mockRows([row({ id: 3, municipio_nome: 'Iguatu', pode_excluir: true })]);
    renderComo(CONTROLE);
    const iguatu = await linha('Iguatu');
    expect(within(iguatu).queryByLabelText(EXCLUIR)).not.toBeInTheDocument();
    expect(within(iguatu).getByLabelText(/^Remover do Google Agenda:/)).toBeInTheDocument();
  });

  test('a confirmação é a de Publicar na agenda: cita o evento, diz que sai dos dois lados e exclui', async () => {
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    mockRows([row({ id: 4, municipio_nome: 'Russas', meet_link: 'https://meet.google.com/abc' })]);
    renderComo(DAT);
    fireEvent.click(within(await linha('Russas')).getByLabelText(EXCLUIR));
    const config = confirmar.mock.calls[0]![0];
    confirmar.mockRestore();
    expect(config.title).toBe('Excluir evento?');
    expect(config.content).toBe(
      '05/11/2099 09:00 · Russas · Projeto. Ele sai do sistema e do Google Agenda, junto com o link do Meet. Não dá para desfazer.',
    );
    expect(config.okText).toBe('Sim, excluir');
    expect(config.autoFocusButton).toBe('cancel');
    const sucesso = vi.spyOn(message, 'success');
    await config.onOk!();
    expect(deleteSolicitacaoMock).toHaveBeenCalledWith(4);
    expect(sucesso).toHaveBeenCalledWith('Evento excluído do sistema e do Google Agenda.');
    sucesso.mockRestore();
  });

  test('o evento que não está no Google: a confirmação não fala do Google', async () => {
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    mockRows([row({ id: 5, municipio_nome: 'Aracati', gcal_status: 'NONE', external_event_id: null })]);
    renderComo(DAT);
    fireEvent.click(within(await linha('Aracati')).getByLabelText(EXCLUIR));
    const config = confirmar.mock.calls[0]![0];
    confirmar.mockRestore();
    expect(config.title).toBe('Excluir solicitação?');
    expect(config.content).toBe('05/11/2099 09:00 · Aracati · Projeto. Esta ação não pode ser desfeita.');
  });

  test('a recusa do servidor aparece inteira e a lista recarrega', async () => {
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    const detail = 'Esta solicitação já foi aprovada e não pode ser excluída.';
    deleteSolicitacaoMock.mockRejectedValue(
      Object.assign(new Error('HTTP 400'), { status: 400, response: { status: 400, data: { detail } } }),
    );
    mockRows([row({ id: 6, municipio_nome: 'Icó' })]);
    renderComo(DAT);
    fireEvent.click(within(await linha('Icó')).getByLabelText(EXCLUIR));
    const config = confirmar.mock.calls[0]![0];
    confirmar.mockRestore();
    const erro = vi.spyOn(message, 'error');
    const cargasAntes = listSolicitacoesMock.mock.calls.length;
    await config.onOk!();
    expect(erro).toHaveBeenCalledWith(detail);
    await waitFor(() => expect(listSolicitacoesMock.mock.calls.length).toBeGreaterThan(cargasAntes));
    erro.mockRestore();
  });
});
