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
import { fireEvent, render, screen, within } from '@testing-library/react';
import { Modal } from 'antd';
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

// Tela pesada (AntD + ResponsiveTable): na CI, cerca de 4x mais lenta que local e com cobertura, casos passam dos
// 5 s padrão. Só o limite de tempo muda, nenhuma asserção.
vi.setConfig({ testTimeout: 20_000 });

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
      row({ id: 62, municipio_nome: 'JaPublicado', gcal_status: 'PUBLISHED', ...FUTURO }),
    ]);
    render(<PreAgendaPage />);
    await screen.findByText('JaPublicado');
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

// D64: evento que já terminou não se reenvia (o backend recusa com `evento_passado`, como no lote).
describe('PreAgendaPage — Reenviar e Remover em evento passado', () => {
  const FUTURO = { inicio: '2099-11-05T09:00:00-03:00', fim: '2099-11-05T12:00:00-03:00' };
  const PASSADO = { inicio: '2020-01-10T09:00:00-03:00', fim: '2020-01-10T12:00:00-03:00' };
  const REENVIAR = 'Reenviar evento (forçar atualização)';

  test('Reenviar some no evento passado, publicado ou com erro, e segue no futuro', async () => {
    mockRows([
      row({ id: 70, municipio_nome: 'PassouPub', gcal_status: 'PUBLISHED', external_event_id: 'e70', ...PASSADO }),
      row({ id: 71, municipio_nome: 'PassouErro', gcal_status: 'ERROR', ...PASSADO }),
      row({ id: 72, municipio_nome: 'FuturoPub', gcal_status: 'PUBLISHED', external_event_id: 'e72', ...FUTURO }),
      row({ id: 73, municipio_nome: 'FuturoErro', gcal_status: 'ERROR', ...FUTURO }),
    ]);
    render(<PreAgendaPage />);
    const linha = async (nome: string) => (await screen.findByText(nome)).closest('tr') as HTMLElement;
    expect(within(await linha('PassouPub')).queryByLabelText(REENVIAR)).not.toBeInTheDocument();
    expect(within(await linha('PassouErro')).queryByLabelText(REENVIAR)).not.toBeInTheDocument();
    expect(within(await linha('FuturoPub')).getByLabelText(REENVIAR)).toBeInTheDocument();
    expect(within(await linha('FuturoErro')).getByLabelText(REENVIAR)).toBeInTheDocument();
  });

  async function textoDaConfirmacaoDeRemover(datas: { inicio: string; fim: string }): Promise<string> {
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    mockRows([row({ id: 80, municipio_nome: 'Russas', gcal_status: 'PUBLISHED', external_event_id: 'e80', ...datas })]);
    render(<PreAgendaPage />);
    await screen.findByText('Russas');
    fireEvent.click(screen.getByLabelText(/^Remover do Google Agenda:/));
    const { container } = render(<>{confirmar.mock.calls[0]![0].content}</>);
    confirmar.mockRestore();
    return container.textContent ?? '';
  }

  test('a confirmação de Remover não promete publicar de novo o evento que já terminou', async () => {
    const texto = await textoDaConfirmacaoDeRemover(PASSADO);
    expect(texto).toContain(
      'A solicitação continua aprovada no sistema, mas o evento já terminou: ele não poderá ser publicado de novo.',
    );
    expect(texto).not.toContain('e pode ser publicado de novo');
  });

  test('no evento futuro, a confirmação de Remover diz que pode publicar de novo', async () => {
    const texto = await textoDaConfirmacaoDeRemover(FUTURO);
    expect(texto).toContain('A solicitação continua aprovada no sistema e pode ser publicada de novo.');
  });
});

// Textos em português, sem jargão (B#17).
describe('PreAgendaPage — textos sem jargão', () => {
  test('resumo e ações do lote em português', async () => {
    mockRows([row({ id: 90, municipio_nome: 'Aracati', gcal_status: 'PUBLISHED', external_event_id: 'e90' })]);
    render(<PreAgendaPage />);
    await screen.findByText('Aracati');
    expect(screen.getByText('Resumo no Google Agenda')).toBeInTheDocument();
    expect(screen.queryByText('Resumo de Status GCal')).not.toBeInTheDocument();
    fireEvent.click(screen.getByLabelText('Selecionar evento'));
    expect(await screen.findByText('Reaplicar selecionados')).toBeInTheDocument();
    expect(screen.getByText('Reenviar selecionados')).toBeInTheDocument();
    expect(screen.queryByText(/Reapply|Resync/)).not.toBeInTheDocument();
  });

  test('a prévia diz Código do evento, Link do Meet e a resposta do convidado em português', async () => {
    mockRows([row({ id: 91, municipio_nome: 'Icó' })]);
    vi.mocked(previewSolicitacao).mockResolvedValue({
      preview: {
        payload: {
          summary: 'Evento de teste',
          attendees: [
            { email: 'a@example.invalid', responseStatus: 'accepted' },
            { email: 'b@example.invalid', responseStatus: 'declined' },
            { email: 'c@example.invalid', responseStatus: 'tentative' },
            { email: 'd@example.invalid', responseStatus: 'needsAction' },
          ],
        },
        event_id: 'evt-1',
        meet_link: null,
        payload_hash: 'hash-1',
      },
    } as unknown as Awaited<ReturnType<typeof previewSolicitacao>>);
    render(<PreAgendaPage />);
    await screen.findByText('Icó');
    fireEvent.click(screen.getByLabelText('Visualizar preview do evento'));
    await screen.findByText('Evento de teste');
    expect(screen.getByText('Prévia do evento no Google')).toBeInTheDocument();
    expect(screen.getByText('Código do evento')).toBeInTheDocument();
    expect(screen.getByText('Link do Meet')).toBeInTheDocument();
    for (const resposta of ['Aceitou', 'Recusou', 'Talvez', 'Aguardando resposta']) {
      expect(screen.getByText(resposta)).toBeInTheDocument();
    }
    for (const cru of ['Event ID', 'Meet Link', 'accepted', 'declined', 'tentative']) {
      expect(screen.queryByText(cru)).not.toBeInTheDocument();
    }
  });
});
