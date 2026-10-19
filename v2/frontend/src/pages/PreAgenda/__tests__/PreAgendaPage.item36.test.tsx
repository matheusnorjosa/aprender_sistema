/**
 * Pré-agenda — achados do item 36 (19/10/2026, telas de evento).
 *
 * - "Remover do Google" (antes "Cancelar evento", com "Sim, Cancelar Evento" e foco no OK) abre no
 *   Cancelar, cita o evento e diz que a solicitação continua aprovada.
 * - Status do Google em pt-BR (os rótulos de `gcalRowActions`) e, em ERROR, o motivo que o backend
 *   gravou (`gcal_last_error`): antes só a Tag com o código cru (ERROR/NONE/PENDING).
 *
 * Reusa o harness de mocks do PreAgendaPage.publish.test.tsx. Modal.confirm (estático) não monta
 * no jsdom deste projeto: o teste espia a chamada (padrão das telas AdminDAT).
 */
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { Modal } from 'antd';
import { beforeEach, describe, expect, test, vi } from 'vitest';

const { listSolicitacoesMock, getStatusSummaryMock } = vi.hoisted(() => ({
  listSolicitacoesMock: vi.fn(),
  getStatusSummaryMock: vi.fn(),
}));

vi.mock('../../../api/config', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../../api/config')>();
  return { ...actual, fetchAPI: vi.fn().mockResolvedValue({}) };
});
vi.mock('../../../api/availability', () => ({ getMe: vi.fn().mockResolvedValue(null), getGerencias: vi.fn().mockResolvedValue([]) }));
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

import { fetchAPI } from '../../../api/config';
import { definirLarguraTela } from '../../../test/larguraTela';
import PreAgendaPage from '../PreAgendaPage';

const FUTURO = { inicio: '2099-11-05T12:00:00Z', fim: '2099-11-05T15:00:00Z' };

const row = (overrides: Record<string, unknown> = {}) => ({
  id: 1,
  municipio_nome: 'Fortaleza',
  projeto_nome: 'Projeto Teste',
  tipo: 'Formação',
  gcal_status: 'NONE',
  external_event_id: null,
  meet_link: null,
  participations: [],
  ...FUTURO,
  ...overrides,
});

/** SUPER traz `superRows`, NAO_SUPER traz `naoRows` (uma tabela combinada). */
function mockRows(superRows: Array<Record<string, unknown>>, naoRows: Array<Record<string, unknown>> = []) {
  listSolicitacoesMock.mockImplementation((f: { flow: string }) =>
    Promise.resolve(
      f.flow === 'SUPER' ? { results: superRows, count: superRows.length } : { results: naoRows, count: naoRows.length },
    ),
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  listSolicitacoesMock.mockResolvedValue({ results: [], count: 0 });
  getStatusSummaryMock.mockResolvedValue({ counts: {}, total: 0 });
});

describe('PreAgendaPage — status do Google em pt-BR, com o motivo do erro', () => {
  test('ERROR mostra "Erro" e o motivo gravado pelo backend; NONE/PUBLISHED com rótulo, sem o código cru', async () => {
    const motivo = 'Sua conta Google não tem acesso ao calendário da organização. Peça ao Controle o compartilhamento.';
    mockRows([
      row({ id: 1, municipio_nome: 'Crato', gcal_status: 'ERROR', gcal_last_error: motivo }),
      row({ id: 2, municipio_nome: 'Sobral', gcal_status: 'NONE' }),
      row({ id: 3, municipio_nome: 'Iguatu', gcal_status: 'PUBLISHED', external_event_id: 'asv3' }),
    ]);
    render(<PreAgendaPage />);

    const erro = (await screen.findByText('Crato')).closest('tr') as HTMLElement;
    expect(within(erro).getByText('Erro')).toBeInTheDocument();
    expect(within(erro).getByText(motivo)).toBeInTheDocument();
    expect(within(screen.getByText('Sobral').closest('tr') as HTMLElement).getByText('Não publicado')).toBeInTheDocument();
    expect(within(screen.getByText('Iguatu').closest('tr') as HTMLElement).getByText('Publicado')).toBeInTheDocument();
    for (const codigo of ['ERROR', 'NONE', 'PUBLISHED']) {
      expect(screen.queryByText(codigo)).not.toBeInTheDocument();
    }
  });

  test('Publicado, Publicando… e Erro, e o motivo do erro, com contraste AA (4,5:1)', async () => {
    // O preset do AntD pinta a cor 6 sobre a cor 1 (2,21, 3,66 e 2,99:1); o Text danger dá 3,27:1.
    mockRows([
      row({ id: 1, municipio_nome: 'Crato', gcal_status: 'ERROR', gcal_last_error: 'Motivo do Google.' }),
      row({ id: 2, municipio_nome: 'Sobral', gcal_status: 'PENDING' }),
      row({ id: 3, municipio_nome: 'Iguatu', gcal_status: 'PUBLISHED', external_event_id: 'asv3' }),
    ]);
    render(<PreAgendaPage />);

    const erro = (await screen.findByText('Crato')).closest('tr') as HTMLElement;
    expect(within(erro).getByText('Erro')).toHaveStyle({ color: '#b32430' });
    expect(within(erro).getByText('Motivo do Google.')).toHaveStyle({ color: '#b32430' });
    expect(within(screen.getByText('Sobral').closest('tr') as HTMLElement).getByText('Publicando…')).toHaveStyle({ color: '#0958d9' });
    expect(within(screen.getByText('Iguatu').closest('tr') as HTMLElement).getByText('Publicado')).toHaveStyle({ color: '#237804' });
  });

  test('resumo, Reenviar e "Reapply Selecionados" sem o gold-6/green-6 (1,90 e 2,27:1 no branco)', async () => {
    mockRows([row({ id: 1, municipio_nome: 'Crato', gcal_status: 'PUBLISHED', external_event_id: 'asv1' })]);
    render(<PreAgendaPage />);
    const linha = (await screen.findByText('Crato')).closest('tr') as HTMLElement;

    const valorDo = (titulo: string) =>
      screen.getByText(titulo).closest('.ant-statistic')!.querySelector('.ant-statistic-content') as HTMLElement;
    expect(valorDo('Pendentes')).toHaveStyle({ color: '#ad4e00' }); // orange-8: 5,43:1
    expect(valorDo('Publicados')).toHaveStyle({ color: '#237804' }); // green-8: 5,59:1
    expect(within(linha).getByRole('button', { name: 'Reenviar evento (forçar atualização)' })).toHaveStyle({
      color: '#ad4e00',
      borderColor: '#ad4e00',
    });

    fireEvent.click(within(linha).getByRole('checkbox'));
    // 4,99:1 sobre o bg-blue-50 da barra do lote
    expect(await screen.findByRole('button', { name: /Reapply Selecionados/ })).toHaveStyle({ color: '#ad4e00' });
  });
});

describe('PreAgendaPage — remover do Google começa no Cancelar e cita o evento', () => {
  const semModal = (): { destroy: () => void; update: () => void } => ({ destroy: vi.fn(), update: vi.fn() });
  const EVENTO = '05/11/2099 09:00 · Juazeiro · Projeto Teste';

  test('a confirmação abre no Cancelar, cita o evento e diz que a solicitação continua aprovada', async () => {
    mockRows([row({ id: 9, municipio_nome: 'Juazeiro', gcal_status: 'PUBLISHED', external_event_id: 'asv9' })]);
    render(<PreAgendaPage />);
    await screen.findByText('Juazeiro');
    const confirmacao = vi.spyOn(Modal, 'confirm').mockImplementation(semModal);

    fireEvent.click(screen.getByRole('button', { name: `Remover do Google Agenda: ${EVENTO}` }));

    await waitFor(() => expect(confirmacao).toHaveBeenCalledTimes(1));
    const config = confirmacao.mock.calls[0]?.[0];
    expect(config).toMatchObject({
      autoFocusButton: 'cancel',
      title: `Remover do Google Agenda: ${EVENTO}?`,
      okText: 'Remover do Google',
      cancelText: 'Cancelar',
    });
    const { container } = render(<>{config?.content}</>);
    expect(container.textContent).toMatch(/continua aprovada/);
    expect(container.textContent).not.toMatch(/event_id|meet_link/);
    await act(async () => {});
  });
});

// A lista lê no máximo 100 aprovados por fluxo. Pedia sem ordem (o padrão do servidor é -inicio):
// vinham os 100 mais distantes no futuro e os desta semana sumiam, sem aviso.
describe('PreAgendaPage — os mais próximos primeiro, e aviso quando a lista é cortada', () => {
  const dataDaLinha = (tr: Element): string => tr.querySelector('td:nth-child(2)')?.textContent ?? '';

  test('pede os dois fluxos do mais próximo ao mais distante e intercala as duas listas', async () => {
    mockRows(
      [row({ id: 1, municipio_nome: 'SuperLonge', inicio: '2099-12-20T12:00:00Z', fim: '2099-12-20T15:00:00Z' })],
      [row({ id: 2, municipio_nome: 'NaoSuperPerto', inicio: '2099-01-10T12:00:00Z', fim: '2099-01-10T15:00:00Z' })],
    );
    render(<PreAgendaPage />);
    await screen.findByText('SuperLonge');

    for (const flow of ['SUPER', 'NAO_SUPER']) {
      expect(listSolicitacoesMock).toHaveBeenCalledWith(expect.objectContaining({ flow, ordering: 'proximidade' }));
    }
    const linhas = Array.from(document.querySelectorAll('tr.ant-table-row'));
    expect(linhas.map((tr) => tr.textContent?.includes('NaoSuperPerto'))).toEqual([true, false]);
    expect(dataDaLinha(linhas[0] as Element)).toContain('10/01/2099');
  });

  test('servidor tem mais do que veio: avisa quantos estão na tela e como achar o resto', async () => {
    listSolicitacoesMock.mockImplementation((f: { flow: string }) =>
      Promise.resolve(f.flow === 'SUPER' ? { results: [row({ id: 1, municipio_nome: 'Crato' })], count: 140 } : { results: [], count: 0 }),
    );
    render(<PreAgendaPage />);
    await screen.findByText('Crato');

    const aviso = screen.getByText(/Mostrando 1 de 140 eventos aprovados/);
    expect(aviso.closest('[role="status"]')).not.toBeNull();
    expect(aviso.textContent).toMatch(/filtre por data, gerência ou busca/i);
  });

  // Cada fluxo é cortado no servidor de forma independente. Se o SUPER veio cortado no dia 20, um
  // NAO_SUPER do dia 25 não pode aparecer: os SUPER dos dias 21 a 30 ficaram de fora, e a lista
  // deixaria de ser "os mais próximos de hoje".
  test('um fluxo cortado: a lista juntada para no último evento dele, sem buraco no meio', async () => {
    const dia = (d: number) => ({ inicio: `2099-03-${d}T12:00:00Z`, fim: `2099-03-${d}T15:00:00Z` });
    listSolicitacoesMock.mockImplementation((f: { flow: string }) =>
      Promise.resolve(
        f.flow === 'SUPER'
          ? {
              results: [
                row({ id: 1, municipio_nome: 'SuperDia10', ...dia(10) }),
                row({ id: 2, municipio_nome: 'SuperDia20', ...dia(20) }),
              ],
              count: 150,
            }
          : {
              results: [
                row({ id: 3, municipio_nome: 'NaoSuperDia15', ...dia(15) }),
                row({ id: 4, municipio_nome: 'NaoSuperDia25', ...dia(25) }),
              ],
              count: 2,
            },
      ),
    );
    render(<PreAgendaPage />);
    await screen.findByText('SuperDia20');

    expect(screen.getByText('NaoSuperDia15')).toBeInTheDocument();
    expect(screen.queryByText('NaoSuperDia25')).not.toBeInTheDocument();
    expect(screen.getByText(/Mostrando 3 de 152 eventos aprovados, os mais próximos de hoje/)).toBeInTheDocument();
  });

  test('sem corte, sem aviso', async () => {
    mockRows([row({ id: 1, municipio_nome: 'Crato' })]);
    render(<PreAgendaPage />);
    await screen.findByText('Crato');

    expect(screen.queryByText(/Mostrando \d+ de/)).not.toBeInTheDocument();
  });
});

// A tabela rolava na horizontal nas 4 larguras (scroll.x max-content).
describe('PreAgendaPage — sem rolagem horizontal', () => {
  function cabecalhos(): string[] {
    return screen
      .getAllByRole('columnheader')
      .filter((th) => !th.classList.contains('ant-table-row-expand-icon-cell') && !th.classList.contains('ant-table-selection-column'))
      .map((th) => th.textContent?.trim() ?? '')
      .filter(Boolean);
  }

  test('a 1280 px: o Evento (data, município, projeto, Google Agenda) e as ações, sem rolagem', async () => {
    mockRows([row({ id: 1, municipio_nome: 'Crato', meet_link: 'https://meet.google.com/abc-defg-hij' })]);
    const { container } = render(<PreAgendaPage />);
    const linha = (await screen.findByText('Crato')).closest('tr') as HTMLElement;

    expect(cabecalhos()).toEqual(['Evento', 'Tipo', 'Formadores', 'Meet', 'Ações']);
    for (const texto of ['05/11/2099 09:00', 'Projeto Teste', 'Não publicado']) {
      expect(within(linha).getByText(texto)).toBeInTheDocument();
    }
    expect(container.querySelector('.ant-table-content')?.getAttribute('style') ?? '').not.toMatch(/overflow/);
  });

  test('a 360 px: só o Evento e as ações; o resto na linha expandida', async () => {
    definirLarguraTela(360);
    mockRows([row({ id: 1, municipio_nome: 'Crato' })]);
    render(<PreAgendaPage />);
    const linha = (await screen.findByText('Crato')).closest('tr') as HTMLElement;

    expect(cabecalhos()).toEqual(['Evento', 'Ações']);
    expect(within(linha).getByLabelText('Publicar evento no Google Calendar')).toBeInTheDocument();
    fireEvent.click(within(linha).getByRole('button', { name: /^Expandir linha de 05\/11\/2099 09:00 · Crato/ }));
    const expandida = within(document.querySelector<HTMLElement>('.ant-table-expanded-row')!);
    expect(expandida.getByText('Formação')).toBeInTheDocument();
  });

  // Eventos do Google a 360 px: Início (150) e Link (70) na linha deixavam ~36 px para o Evento,
  // cortado em reticências; o nome só no `title`, que no toque não aparece.
  test('a 360 px, Eventos do Google: o nome inteiro na linha; o link vai para a linha expandida', async () => {
    const NOME = 'Formação de professores — Superativar Linguagens 3 (Crato)';
    vi.mocked(fetchAPI).mockImplementation((url: string) =>
      Promise.resolve(
        url.startsWith('/integrations/google/events/')
          ? {
              calendar_id: 'agenda@x.br',
              count: 1,
              events: [
                {
                  id: 'g1',
                  summary: NOME,
                  start: '2099-11-05T12:00:00Z',
                  end: '2099-11-05T15:00:00Z',
                  status: 'confirmed',
                  htmlLink: 'https://calendar.google.com/event?eid=g1',
                  location: 'Crato',
                  creator: 'x@y.br',
                },
              ],
            }
          : {},
      ),
    );
    definirLarguraTela(360);
    render(<PreAgendaPage />);
    fireEvent.click(await screen.findByText('Eventos Google Calendar'));

    const celula = await screen.findByText(NOME);
    expect(celula.closest('td')?.classList.contains('ant-table-cell-ellipsis')).toBe(false);
    expect(cabecalhos()).toEqual(['Evento', 'Início']);

    const linha = celula.closest('tr') as HTMLElement;
    fireEvent.click(within(linha).getByRole('button', { name: `Expandir linha de ${NOME}` }));
    const expandida = within(document.querySelector<HTMLElement>('.ant-table-expanded-row')!);
    expect(expandida.getByRole('link', { name: 'Abrir no Google Agenda' })).toHaveAttribute(
      'href',
      'https://calendar.google.com/event?eid=g1',
    );
  });

  test('a barra do lote quebra linha', async () => {
    mockRows([row({ id: 1, municipio_nome: 'Crato', gcal_status: 'PUBLISHED', external_event_id: 'asv1' })]);
    render(<PreAgendaPage />);
    const linha = (await screen.findByText('Crato')).closest('tr') as HTMLElement;

    fireEvent.click(within(linha).getByRole('checkbox'));

    const barra = (await screen.findByText('1 evento(s) selecionado(s)')).closest('.ant-space') as HTMLElement;
    expect(barra).toHaveStyle({ flexWrap: 'wrap' });
  });
});

// A falha da carga só virava um toast de 3 s, e a tabela ficava no vazio padrão.
describe('PreAgendaPage — lista que não carregou', () => {
  test('o motivo e "Tentar de novo" no lugar das linhas', async () => {
    listSolicitacoesMock.mockRejectedValue(Object.assign(new Error('Erro interno do servidor.'), { status: 500 }));
    render(<PreAgendaPage />);

    const aviso = await screen.findByText('Não foi possível carregar a lista.');
    expect(aviso.closest('[role="alert"]')).not.toBeNull();
    expect(screen.getByText('Erro interno do servidor.')).toBeInTheDocument();

    mockRows([row({ id: 1, municipio_nome: 'Crato' })]);
    fireEvent.click(screen.getByRole('button', { name: 'Tentar de novo' }));

    expect(await screen.findByText('Crato')).toBeInTheDocument();
    expect(screen.queryByText('Não foi possível carregar a lista.')).not.toBeInTheDocument();
  });
});
