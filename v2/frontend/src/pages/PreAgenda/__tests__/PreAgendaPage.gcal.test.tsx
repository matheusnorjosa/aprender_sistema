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
  const actual = (await importOriginal()) as Record<string, unknown>;
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
  const actual = (await importOriginal()) as Record<string, unknown>;
  return { ...actual, fetchAPI: fetchAPIMock };
});

vi.mock('../../../api/availability', () => ({
  getMe: getMeMock,
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
  usePolling: vi.fn(),
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
    // "1 eventos" aparece na Tag de contagem e no total da paginação;
    // asserta especificamente a Tag (ant-tag) de quantidade.
    const countLabels = screen.getAllByText('1 eventos');
    expect(countLabels.some((el) => el.closest('.ant-tag'))).toBe(true);
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
