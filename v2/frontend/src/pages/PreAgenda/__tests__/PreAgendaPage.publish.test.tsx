/**
 * #1629 [M12-19] Pré-agenda — publicação: botão bloqueado em PENDING.
 *
 * (b) PENDING-republish: com a publicação já em voo (PENDING), o botão de
 *     publicar deve ficar disabled para não reenfileirar por cima. Antes só
 *     bloqueava em PUBLISHED.
 *
 * O resíduo (a) — não anunciar "publicado com sucesso" num retorno 202
 * (enfileiramento assíncrono) — é uma troca de copy no handler (message.info
 * em vez de message.success). Não há teste de UI para ele porque o fluxo passa
 * por Modal.confirm (API estática do antd v5), que não monta de forma confiável
 * no ambiente de teste sob React 19 (nenhum teste do projeto dirige modais).
 *
 * Reusa o harness de mocks do PreAgendaPage.lifecycle.test.tsx.
 */
import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';

const { getMeMock, listSolicitacoesMock, getStatusSummaryMock, fetchAPIMock } = vi.hoisted(() => ({
  getMeMock: vi.fn(),
  listSolicitacoesMock: vi.fn(),
  getStatusSummaryMock: vi.fn(),
  fetchAPIMock: vi.fn(),
}));

vi.mock('../../../api/config', async (importOriginal) => {
  const actual = (await importOriginal());
  return { ...actual, fetchAPI: fetchAPIMock };
});
vi.mock('../../../api/availability', () => ({ getMe: getMeMock, getGerencias: vi.fn().mockResolvedValue([]) }));
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
vi.mock('../../../hooks/usePolling', () => ({ usePolling: () => ({ pausado: false, pausar: () => {} }) }));
vi.mock('../../../services/syncChannel', () => ({
  syncChannel: { subscribe: () => () => {}, publish: vi.fn() },
}));
vi.mock('../../../components/google/GoogleIntegrationCard', () => ({
  default: () => <div data-testid="google-card" />,
}));

import { previewSolicitacao } from '../../../api/solicitacoes';
import { ComAcesso } from '../../../test/comAcesso';
import PreAgendaPage from '../PreAgendaPage';

const row = (overrides: Record<string, unknown> = {}) => ({
  id: 1,
  municipio_nome: 'Fortaleza',
  projeto_nome: 'Projeto',
  tipo: 'Formação',
  gcal_status: 'NONE',
  inicio: '2026-08-10T09:00:00',
  external_event_id: null,
  meet_link: null,
  ...overrides,
});

// SUPER traz as linhas; NAO_SUPER vazio (uma tabela combinada).
function mockRows(rows: Array<Record<string, unknown>>) {
  listSolicitacoesMock.mockImplementation((f: { flow: string }) =>
    Promise.resolve(f.flow === 'SUPER' ? { results: rows, count: rows.length } : { results: [], count: 0 }),
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  getMeMock.mockResolvedValue({ setores: ['Controle'], funcoes: [], is_superuser: false });
  listSolicitacoesMock.mockResolvedValue({ results: [], count: 0 });
  getStatusSummaryMock.mockResolvedValue({ counts: {}, total: 0 });
  fetchAPIMock.mockResolvedValue({});
});

describe('PreAgendaPage — publicação (M12-19 / #1629)', () => {
  test('botão publicar fica disabled quando gcal_status é PENDING', async () => {
    mockRows([row({ id: 20, municipio_nome: 'Sobral', gcal_status: 'PENDING' })]);
    render(<PreAgendaPage />);
    await screen.findByText('Sobral');
    expect(screen.getByLabelText('Publicar evento no Google Calendar: já publicado')).toBeDisabled();
  });

  test('botão publicar fica habilitado quando gcal_status é NONE', async () => {
    mockRows([row({ id: 30, municipio_nome: 'Caucaia', gcal_status: 'NONE' })]);
    render(<PreAgendaPage />);
    await screen.findByText('Caucaia');
    expect(screen.getByLabelText('Publicar evento no Google Calendar')).not.toBeDisabled();
  });
});

// Virada (16/10/2026): a tela segue o `motivo_nao_publicavel` do backend.
describe('PreAgendaPage — evento passado e publicado fora do sistema', () => {
  const FUTURO = { inicio: '2099-11-05T09:00:00-03:00', fim: '2099-11-05T12:00:00-03:00' };
  const PASSADO = { inicio: '2020-01-10T09:00:00-03:00', fim: '2020-01-10T12:00:00-03:00' };

  test('Publicar fica desabilitado no evento passado, com o motivo no nome acessível', async () => {
    mockRows([row({ id: 50, municipio_nome: 'Crato', ...PASSADO })]);
    render(<PreAgendaPage />);
    await screen.findByText('Crato');
    expect(screen.getByLabelText('Publicar evento no Google Calendar: o evento já terminou')).toBeDisabled();
  });

  test('Publicar fica desabilitado no evento que está no Google pela planilha', async () => {
    mockRows([row({ id: 51, municipio_nome: 'Juazeiro', publicado_fora_do_sistema: true, ...FUTURO })]);
    render(<PreAgendaPage />);
    await screen.findByText('Juazeiro');
    expect(
      screen.getByLabelText('Publicar evento no Google Calendar: já está no Google Agenda pela planilha'),
    ).toBeDisabled();
  });

  test('Publicar segue habilitado no evento futuro não publicado', async () => {
    mockRows([row({ id: 52, municipio_nome: 'Quixadá', ...FUTURO })]);
    render(<PreAgendaPage />);
    await screen.findByText('Quixadá');
    expect(screen.getByLabelText('Publicar evento no Google Calendar')).not.toBeDisabled();
  });

  test('a seleção para Reaplicar/Reenviar só deixa marcar o que já foi ao Google e não terminou', async () => {
    mockRows([
      row({ id: 60, municipio_nome: 'Nunca', ...FUTURO }),
      row({ id: 61, municipio_nome: 'Passou', gcal_status: 'PUBLISHED', ...PASSADO }),
      row({ id: 62, municipio_nome: 'Publicado', gcal_status: 'PUBLISHED', ...FUTURO }),
    ]);
    render(<PreAgendaPage />);
    await screen.findByText('Publicado');
    expect(screen.getByLabelText('Selecionar evento: ainda não publicado')).toBeDisabled();
    expect(screen.getByLabelText('Selecionar evento: o evento já terminou')).toBeDisabled();
    expect(screen.getByLabelText('Selecionar evento')).not.toBeDisabled();
  });
});

// Widget de debug do preview ("Informações Técnicas"): a regra É o superusuário (ehSuperusuario).
describe('PreAgendaPage — Informações Técnicas do preview', () => {
  async function abrirPreview(superusuario: boolean): Promise<void> {
    mockRows([row({ id: 40, municipio_nome: 'Iguatu' })]);
    vi.mocked(previewSolicitacao).mockResolvedValue({
      preview: { payload: { summary: 'Evento de teste' }, event_id: 'evt-1', meet_link: null, payload_hash: 'hash-1' },
    } as unknown as Awaited<ReturnType<typeof previewSolicitacao>>);
    render(
      <ComAcesso policies={['access_controle_section']} superusuario={superusuario}>
        <PreAgendaPage />
      </ComAcesso>,
    );
    await screen.findByText('Iguatu');
    fireEvent.click(screen.getByLabelText('Visualizar preview do evento'));
    await screen.findByText('Evento de teste');
  }

  test('superusuário vê o widget', async () => {
    await abrirPreview(true);
    expect(screen.getByText('Informações Técnicas (JSON)')).toBeInTheDocument();
  });

  test('quem não é superusuário não vê', async () => {
    await abrirPreview(false);
    expect(screen.queryByText('Informações Técnicas (JSON)')).not.toBeInTheDocument();
  });
});
