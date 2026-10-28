/**
 * PreAgendaPage — modo "Eventos Google Calendar" (#1294 / #1295 / #1296)
 *
 * Cobre a separação de estado do filtro de datas entre os dois view modes e o
 * empty-state contextual do modo gcal-events.
 *
 * NOTA sobre o RangePicker (gotcha conhecido do antd inline em jsdom):
 * dirigir células reais do antd RangePicker é frágil em jsdom, então mockamos
 * `DatePicker.RangePicker` — análogo ao harness de referência
 * (NewSolicitacaoWizard.test.tsx), que mocka o componente `DateTimeRange`.
 * O mock dispara o MESMO `onChange` que a produção liga a cada estado
 * (`setDateRange` no modo Solicitações, `setGcalDateRange` no modo eventos),
 * então as asserções exercitam o comportamento real: qual estado o picker
 * escreve e como esse estado flui para a URL de `/integrations/google/events/`
 * e para as deps de `loadData`. Não testamos a renderização das células do
 * antd (isso é responsabilidade do antd).
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';

const { fetchAPIMock, getMeMock, listSolicitacoesMock, getStatusSummaryMock } = vi.hoisted(() => ({
  fetchAPIMock: vi.fn(),
  getMeMock: vi.fn(),
  listSolicitacoesMock: vi.fn(),
  getStatusSummaryMock: vi.fn(),
}));

// antd: substitui apenas DatePicker.RangePicker por um botão controlável.
// O restante do antd (Table, Card, Segmented, Empty, Tag, ...) permanece real.
vi.mock('antd', async (importOriginal) => {
  const actual = (await importOriginal());
  const dayjsLib = (await import('dayjs')).default;
  const MockRangePicker = ({ onChange }: { onChange?: (dates: unknown[]) => void }) => (
    <button
      type="button"
      data-testid="mock-rangepicker"
      onClick={() => onChange?.([dayjsLib('2026-08-01'), dayjsLib('2026-08-31')])}
    >
      set-range
    </button>
  );
  const DatePicker = { ...(actual.DatePicker as object), RangePicker: MockRangePicker };
  return { ...actual, DatePicker };
});

// config: mantém buildUrl/API_BASE reais (evita quebrar imports transitivos),
// mas troca fetchAPI pelo mock roteável.
vi.mock('../../../api/config', async (importOriginal) => {
  const actual = (await importOriginal());
  return { ...actual, fetchAPI: fetchAPIMock };
});

vi.mock('../../../api/availability', () => ({
  getMe: getMeMock,
  // PR A: o filtro de gerência carrega as gerências ativas no mount.
  getGerencias: vi.fn().mockResolvedValue([]),
}));

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
    status: {
      connected: true,
      isExpired: false,
      googleEmail: 'x@y.br',
      tokenExpiry: null,
      expiresInDays: null,
    },
    disconnect: vi.fn(),
    loading: false,
    error: null,
    fetchStatus: vi.fn(),
  }),
}));

vi.mock('../../../hooks/useGoogleGuard', () => ({
  default: () => ({
    requireGoogleConnection: () => true,
    handleGoogleError: () => false,
    isConnected: true,
  }),
}));

vi.mock('../../../hooks/usePolling', () => ({
  usePolling: vi.fn(() => ({ pausado: false, pausar: () => {} })),
}));

vi.mock('../../../services/syncChannel', () => ({
  syncChannel: {
    subscribe: () => () => {},
    publish: vi.fn(),
  },
}));

// Stub: senão o mount do card real dispara fetchAPI('/integrations/google/calendars/').
vi.mock('../../../components/google/GoogleIntegrationCard', () => ({
  default: () => <div data-testid="google-card" />,
}));

import PreAgendaPage from '../PreAgendaPage';

// Tela pesada (AntD + ResponsiveTable): na CI, cerca de 4x mais lenta que local e com cobertura, casos passam dos
// 5 s padrão. Só o limite de tempo muda, nenhuma asserção.
vi.setConfig({ testTimeout: 20_000 });

type EventsResponse = {
  events: Array<Record<string, unknown>>;
  calendar_id: string;
  count: number;
};

let eventsResponse: EventsResponse;

const sampleEvent = {
  id: 'e1',
  summary: 'Formação Sobral',
  start: '2026-08-10T09:00:00',
  end: '2026-08-10T11:00:00',
  status: 'confirmed',
  htmlLink: 'https://calendar.google.com/e1',
  location: 'Sobral - CE',
  creator: 'coord@aprender.br',
};

beforeEach(() => {
  vi.clearAllMocks();
  eventsResponse = { events: [], calendar_id: 'agenda@aprender.br', count: 0 };

  getMeMock.mockResolvedValue({
    setores: ['Controle'],
    funcoes: [],
    is_superuser: false,
  });
  listSolicitacoesMock.mockResolvedValue({ results: [], count: 0 });
  getStatusSummaryMock.mockResolvedValue({ counts: {}, total: 0 });

  fetchAPIMock.mockImplementation((url: string) => {
    if (String(url).includes('/integrations/google/events/')) {
      return Promise.resolve(eventsResponse);
    }
    return Promise.resolve({});
  });
});

/** Reverse-find the most recent GCal events request URL. */
function lastEventsUrl(): string | undefined {
  const call = [...fetchAPIMock.mock.calls]
    .reverse()
    .find((c) => String(c[0]).includes('/integrations/google/events/'));
  return call ? String(call[0]) : undefined;
}

describe('PreAgendaPage — modo Eventos Google Calendar', () => {
  test('trocar o Segmented busca /integrations/google/events/ e renderiza tabela + Tag de contagem', async () => {
    eventsResponse = { events: [sampleEvent], calendar_id: 'agenda@aprender.br', count: 1 };

    render(<PreAgendaPage />);

    fireEvent.click(await screen.findByText('Eventos Google Calendar'));

    await waitFor(() => expect(lastEventsUrl()).toBeTruthy());
    expect(await screen.findByText('Formação Sobral')).toBeInTheDocument();
    // "1 evento" (no singular) aparece na Tag de contagem e no total da paginação.
    const countLabels = screen.getAllByText('1 evento');
    expect(countLabels.some((el) => el.closest('.ant-tag'))).toBe(true);
    expect(countLabels.some((el) => el.closest('.ant-pagination'))).toBe(true);
    expect(screen.queryByText('1 eventos')).toBeNull();
  });

  // Ensaio r3 (28/10/2026): servidor sem a configuração OAuth do Google. O /events/ devolvia 500 e a
  // tela soltava o toast genérico; agora o 409 `google_calendar_not_configured` traz a mensagem, e ela
  // fica no lugar dos eventos: um toast some em 3 s e deixava "Nenhum evento encontrado neste
  // calendário", "0 eventos" e "Calendário: <e-mail>", como se o calendário tivesse sido lido.
  test('servidor sem a configuração do Google: a mensagem do 409 fica no lugar dos eventos', async () => {
    const MENSAGEM =
      'A conexão com o Google Agenda ainda não foi configurada no sistema. Avise a administração do sistema.';
    fetchAPIMock.mockImplementation((url: string) => {
      if (String(url).includes('/integrations/google/events/')) {
        return Promise.reject(Object.assign(new Error(MENSAGEM), {
          status: 409,
          response: { status: 409, data: { detail: MENSAGEM, code: 'google_calendar_not_configured' } },
        }));
      }
      return Promise.resolve({});
    });

    render(<PreAgendaPage />);
    fireEvent.click(await screen.findByText('Eventos Google Calendar'));

    expect(await screen.findByText(MENSAGEM)).toBeInTheDocument();
    expect(screen.queryByText('Nenhum evento encontrado neste calendário')).toBeNull();
    expect(screen.queryByText('0 eventos')).toBeNull();
    expect(screen.queryByText(/Calendário:/)).toBeNull();

    // Com o filtro de datas, a orientação continua a mensagem do 409, não "Ajuste o filtro de datas".
    fireEvent.click(screen.getByTestId('mock-rangepicker'));
    await waitFor(() => expect(lastEventsUrl()).toContain('time_min'));
    expect(await screen.findByText(MENSAGEM)).toBeInTheDocument();
    expect(screen.queryByText(/ajuste o filtro/i)).toBeNull();
  });

  // Revisão: o "Tentar de novo" ligava o carregando, o Spin tomava o lugar da tabela e levava o botão
  // focado; o foco caía no body e quem usa teclado voltava ao início da página.
  test('"Tentar de novo" nos eventos do Google: o foco não cai no body, falhe ou carregue', async () => {
    const MENSAGEM = 'Erro ao carregar eventos do Google Calendar';
    let falhar = true;
    fetchAPIMock.mockImplementation((url: string) => {
      if (String(url).includes('/integrations/google/events/')) {
        if (falhar) return Promise.reject(new Error('falhou'));
        return Promise.resolve({ events: [sampleEvent], calendar_id: 'agenda@aprender.br', count: 1 });
      }
      return Promise.resolve({});
    });

    render(<PreAgendaPage />);
    fireEvent.click(await screen.findByText('Eventos Google Calendar'));
    expect(await screen.findByText(MENSAGEM)).toBeInTheDocument();

    // Falha de novo: o aviso continua e o foco fica no botão.
    const botao = screen.getByRole('button', { name: 'Tentar de novo' });
    botao.focus();
    const chamadas = fetchAPIMock.mock.calls.length;
    fireEvent.click(botao);
    await waitFor(() => expect(fetchAPIMock.mock.calls.length).toBeGreaterThan(chamadas));
    await waitFor(() => expect(document.querySelector('.ant-spin-spinning')).toBeNull());
    expect(screen.getByText(MENSAGEM)).toBeInTheDocument();
    expect(document.activeElement).not.toBe(document.body);
    expect(screen.getByRole('button', { name: 'Tentar de novo' })).toHaveFocus();

    // Carrega: as linhas tomam o lugar do aviso e o foco vai para a tabela.
    falhar = false;
    fireEvent.click(screen.getByRole('button', { name: 'Tentar de novo' }));
    expect(await screen.findByText('Formação Sobral')).toBeInTheDocument();
    expect(document.activeElement).not.toBe(document.body);
    expect(document.activeElement).toContainElement(screen.getByRole('table'));
  });

  test('vazio COM filtro de data no modo gcal mostra copy contextual, não a genérica', async () => {
    eventsResponse = { events: [], calendar_id: 'agenda@aprender.br', count: 0 };

    render(<PreAgendaPage />);
    fireEvent.click(await screen.findByText('Eventos Google Calendar'));

    // Sem filtro: copy genérica.
    expect(
      await screen.findByText('Nenhum evento encontrado neste calendário')
    ).toBeInTheDocument();

    // Aplica filtro de data no picker do modo gcal (único mock-rangepicker na tela).
    fireEvent.click(screen.getByTestId('mock-rangepicker'));

    await waitFor(() => {
      expect(screen.getByText(/período selecionado/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/ajuste o filtro/i)).toBeInTheDocument();
    expect(screen.queryByText('Nenhum evento encontrado neste calendário')).toBeNull();
  });

  test('anti-contaminação: filtro de Solicitações não vaza para eventos; filtro gcal não refaz Solicitações', async () => {
    eventsResponse = { events: [], calendar_id: 'agenda@aprender.br', count: 0 };

    render(<PreAgendaPage />);
    // Garante mount completo (usuário carregado).
    await screen.findByText('Eventos Google Calendar');

    // Modo preagenda (default): aplica período no RangePicker de Solicitações.
    fireEvent.click(screen.getByTestId('mock-rangepicker'));

    // Troca para a aba de eventos → dispara loadGcalEvents.
    fireEvent.click(screen.getByText('Eventos Google Calendar'));
    await waitFor(() => expect(lastEventsUrl()).toBeTruthy());

    // Primário: o período das Solicitações NÃO pode vazar como time_min/time_max.
    const urlAfterTabSwitch = lastEventsUrl();
    expect(urlAfterTabSwitch).not.toContain('time_min');
    expect(urlAfterTabSwitch).not.toContain('time_max');

    // Secundário: aplicar filtro na aba gcal não refaz as requests de Solicitações.
    const solCountBefore = listSolicitacoesMock.mock.calls.length;
    fireEvent.click(screen.getByTestId('mock-rangepicker'));

    await waitFor(() => {
      // Novo request de eventos AGORA com a janela do próprio modo gcal.
      expect(lastEventsUrl()).toContain('time_min');
    });
    expect(listSolicitacoesMock.mock.calls.length).toBe(solCountBefore);
  });
});

describe('PreAgendaPage — volta da conexão com o Google', () => {
  test('?google=connected: mostra o sucesso e limpa a URL', async () => {
    window.history.pushState({}, '', '/pre-agenda?google=connected');
    render(<PreAgendaPage />);

    const ok = await screen.findByText('Conta Google conectada.');
    expect(ok.closest('[role="status"]')).not.toBeNull();
    expect(window.location.search).toBe('');
  });

  test('?google=error&reason=server_error: diz que o Google não respondeu e limpa a URL', async () => {
    window.history.pushState({}, '', '/pre-agenda?google=error&reason=server_error');
    render(<PreAgendaPage />);

    const err = await screen.findByText(
      'Não foi possível falar com o Google agora. Tente conectar de novo em alguns minutos.',
    );
    expect(err.closest('[role="alert"]')).not.toBeNull();
    expect(window.location.search).toBe('');
    window.history.pushState({}, '', '/');
  });
});
