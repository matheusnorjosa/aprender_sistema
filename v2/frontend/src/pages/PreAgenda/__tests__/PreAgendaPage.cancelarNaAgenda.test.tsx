/**
 * CON-08 B: "Cancelar evento" de formação na Pré-agenda (decisão do dono, 23/11/2026: ao lado do Remover).
 *
 * O título do evento no Google ganha "(CANCELADO) " e a linha nunca mais se publica. Na linha marcada,
 * Publicar fica desabilitado com o motivo, Remover some e o Cancelar só volta no erro (para refazer: Publicar
 * na agenda só lista de hoje em diante). O Excluir de formação diz que o evento fica no Google cancelado.
 */
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { Modal, message } from 'antd';
import { beforeEach, describe, expect, test, vi } from 'vitest';

const { getMeMock, listSolicitacoesMock, deleteSolicitacaoMock, cancelarNaAgendaMock } = vi.hoisted(() => ({
  getMeMock: vi.fn(),
  listSolicitacoesMock: vi.fn(),
  deleteSolicitacaoMock: vi.fn(),
  cancelarNaAgendaMock: vi.fn(),
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
  cancelarNaAgenda: cancelarNaAgendaMock,
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
const FUTURO = { inicio: '2099-11-05T09:00:00-03:00', fim: '2099-11-05T12:00:00-03:00' };
const EXCLUIR = /^Excluir evento:/;
const CANCELAR = /^Cancelar evento:/;
const REMOVER = /^Remover do Google Agenda:/;
const PUBLICAR = /^Publicar evento no Google Calendar/;

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
  cancelarNaAgendaMock.mockResolvedValue({ detail: 'ok' });
});

describe('PreAgendaPage — Cancelar evento de formação (CON-08)', { timeout: 20000 }, () => {
  test('formação publicada: Cancelar evento ao lado do Remover; outro tipo não tem', async () => {
    mockRows([
      row({ id: 1, municipio_nome: 'Sobral', tipo_evento_de_formacao: true }),
      row({ id: 2, municipio_nome: 'Crato', tipo_evento_de_formacao: false }),
    ]);
    renderComo(DAT);
    const sobral = await linha('Sobral');
    expect(within(sobral).getByLabelText(CANCELAR)).toBeInTheDocument();
    expect(within(sobral).getByLabelText(REMOVER)).toBeInTheDocument();
    expect(within(await linha('Crato')).queryByLabelText(CANCELAR)).not.toBeInTheDocument();
  });

  test('linha cancelada: Publicar desabilitado com o motivo, Remover e Cancelar escondidos', async () => {
    mockRows([row({ id: 3, municipio_nome: 'Iguatu', tipo_evento_de_formacao: true, cancelado_na_agenda: true })]);
    renderComo(DAT);
    const iguatu = await linha('Iguatu');
    const publicar = within(iguatu).getByLabelText(PUBLICAR);
    expect(publicar).toBeDisabled();
    expect(publicar).toHaveAccessibleName('Publicar evento no Google Calendar: foi cancelado na agenda');
    expect(within(iguatu).queryByLabelText(REMOVER)).not.toBeInTheDocument();
    expect(within(iguatu).queryByLabelText(CANCELAR)).not.toBeInTheDocument();
    expect(within(iguatu).queryByLabelText(/^Reenviar evento/)).not.toBeInTheDocument();
  });

  test('cancelamento que falhou (ERROR marcado): o Cancelar volta, para refazer', async () => {
    mockRows([
      row({ id: 4, municipio_nome: 'Russas', gcal_status: 'ERROR', tipo_evento_de_formacao: true, cancelado_na_agenda: true }),
    ]);
    renderComo(DAT);
    const russas = await linha('Russas');
    expect(within(russas).getByLabelText(CANCELAR)).toBeInTheDocument();
    expect(within(russas).queryByLabelText(REMOVER)).not.toBeInTheDocument();
  });

  test('Cancelar que não achou o evento (ERROR sem a marca, com id): o Remover que o erro manda usar está lá, também no evento que já terminou', async () => {
    const erro =
      'O evento não foi achado no Google pelo Event ID guardado (pode ter sido apagado de vez ou estar em outro ' +
      'calendário). Nada foi marcado e o evento não foi cancelado na agenda. Confira no Google Agenda; se ele não ' +
      'existe mais, use Tirar só do Google (na Pré-agenda, o botão Remover do Google Agenda).';
    mockRows([
      row({ id: 9, municipio_nome: 'Crateús', gcal_status: 'ERROR', tipo_evento_de_formacao: true, gcal_last_error: erro }),
      row({
        id: 10,
        municipio_nome: 'Jaguaribe',
        gcal_status: 'ERROR',
        tipo_evento_de_formacao: true,
        gcal_last_error: erro,
        inicio: '2020-03-10T09:00:00-03:00',
        fim: '2020-03-10T12:00:00-03:00',
      }),
    ]);
    renderComo(DAT);
    for (const nome of ['Crateús', 'Jaguaribe']) {
      const tr = await linha(nome);
      expect(within(tr).getByLabelText(REMOVER)).toBeInTheDocument();
      expect(within(tr).queryByLabelText(CANCELAR)).not.toBeInTheDocument();
    }
  });

  test('refazer o Cancelar da linha marcada não depende de o tipo ainda ser de formação (tipo renomeado)', async () => {
    mockRows([
      row({ id: 7, municipio_nome: 'Quixadá', gcal_status: 'ERROR', tipo_evento_de_formacao: false, cancelado_na_agenda: true }),
    ]);
    renderComo(DAT);
    expect(within(await linha('Quixadá')).getByLabelText(CANCELAR)).toBeInTheDocument();
  });

  test('os dois botões vermelhos de ícone dizem o que fazem ao passar o mouse', async () => {
    mockRows([row({ id: 8, municipio_nome: 'Tauá', tipo_evento_de_formacao: true })]);
    renderComo(DAT);
    const taua = await linha('Tauá');
    expect(within(taua).getByLabelText(CANCELAR)).toHaveAttribute('title', 'Cancelar evento');
    expect(within(taua).getByLabelText(REMOVER)).toHaveAttribute('title', 'Remover do Google Agenda');
  });

  test('a confirmação cita o evento, explica o (CANCELADO) e chama o endpoint novo', async () => {
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    mockRows([row({ id: 5, municipio_nome: 'Aracati', tipo_evento_de_formacao: true })]);
    renderComo(DAT);
    fireEvent.click(within(await linha('Aracati')).getByLabelText(CANCELAR));
    const config = confirmar.mock.calls[0]![0];
    confirmar.mockRestore();
    expect(String(config.title)).toMatch(/^Cancelar evento: .*Aracati/);
    expect(config.okText).toBe('Sim, cancelar evento');
    expect(config.cancelText).toBe('Voltar');
    expect(config.autoFocusButton).toBe('cancel');
    render(<>{config.content}</>);
    expect(screen.getByText(/ganha \(CANCELADO\) na frente/)).toBeInTheDocument();
    const sucesso = vi.spyOn(message, 'success');
    await config.onOk!();
    expect(cancelarNaAgendaMock).toHaveBeenCalledWith(5);
    expect(sucesso).toHaveBeenCalledWith(
      'Pedido enviado: o título do evento no Google Agenda ganha (CANCELADO) em alguns segundos.',
    );
    sucesso.mockRestore();
  });

  test('Excluir de formação: a confirmação e o aviso dizem que ele fica no Google com (CANCELADO)', async () => {
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    mockRows([row({ id: 6, municipio_nome: 'Icó', tipo_evento_de_formacao: true })]);
    renderComo(DAT);
    fireEvent.click(within(await linha('Icó')).getByLabelText(EXCLUIR));
    const config = confirmar.mock.calls[0]![0];
    confirmar.mockRestore();
    expect(config.content).toBe(
      '05/11/2099 09:00 · Icó · Projeto. Ele sai do sistema e fica no Google Agenda com (CANCELADO) no título. Não dá para desfazer.',
    );
    const sucesso = vi.spyOn(message, 'success');
    await config.onOk!();
    expect(sucesso).toHaveBeenCalledWith('Evento excluído do sistema; no Google Agenda ele fica com (CANCELADO) no título.');
    sucesso.mockRestore();
    await waitFor(() => expect(deleteSolicitacaoMock).toHaveBeenCalledWith(6));
  });
});
