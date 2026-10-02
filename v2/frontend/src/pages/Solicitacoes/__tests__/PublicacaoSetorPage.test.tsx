/**
 * PublicacaoSetorPage — "Publicar na agenda" da Apoio de Coordenação (#1656).
 *
 * Ela (policy `publish_setor_solicitacao`, não `use_gcal`) conecta a PRÓPRIA conta
 * Google e publica/atualiza/remove, no calendário oficial da organização, os eventos
 * APROVADOS do próprio setor.
 *
 * Harness: `fetchAPI` mockado e roteado por URL (o cliente real `api/solicitacoes`
 * monta a query e o corpo — é esse contrato que os testes conferem);
 * `useGoogleIntegration` mockado (controla o status); o `GoogleIntegrationCard` é o
 * REAL (prova que a página o usa no modo `fixedCalendar`, sem `/calendars/`).
 * AntD: findByText + within + closest em vez de findByRole (lento).
 */
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router';
import { message } from 'antd';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

import { TIMING } from '../../../constants/timing';
import type { GoogleIntegrationStatus } from '../../../types/gcal';
import type { Solicitacao } from '../../../types';

const { fetchAPIMock, googleHook } = vi.hoisted(() => ({
  fetchAPIMock: vi.fn(),
  googleHook: {
    status: {} as GoogleIntegrationStatus, // definido no beforeEach
    loading: false,
    error: null as string | null,
    fetchStatus: vi.fn(),
    disconnect: vi.fn(),
  },
}));

vi.mock('../../../api/config', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../../api/config')>();
  return { ...actual, fetchAPI: fetchAPIMock };
});
vi.mock('../../../hooks/useGoogleIntegration', () => ({ default: () => googleHook }));
vi.mock('../../../services/syncChannel', () => ({
  syncChannel: { subscribe: () => () => {}, publish: vi.fn() },
}));

import PublicacaoSetorPage from '../PublicacaoSetorPage';

// ============================================================================
// Fixtures
// ============================================================================

const READY: GoogleIntegrationStatus = {
  connected: true,
  googleEmail: 'apoio@aprendereditora.com.br',
  tokenExpiry: '2026-09-28T13:00:00Z',
  expiresInDays: 0,
  isExpired: false,
  defaultCalendarId: null,
  publishReady: true,
  publishBlockReason: null,
};

const NOT_CONNECTED: GoogleIntegrationStatus = {
  connected: false,
  googleEmail: null,
  tokenExpiry: null,
  expiresInDays: null,
  isExpired: false,
  defaultCalendarId: null,
  publishReady: false,
  publishBlockReason: 'google_not_connected',
};

function makeSolic(overrides: Partial<Solicitacao> = {}): Solicitacao {
  return {
    id: 7,
    usuario: 3,
    usuario_username: 'coord.vidas',
    municipio: 5,
    municipio_nome: 'Sobral',
    projeto: 10,
    projeto_nome: 'Vidas Em Rede',
    tipo_evento: 2,
    tipo_evento_nome: 'Formação',
    tipo: null,
    encontro: null,
    segmento: null,
    coordenador_acompanha: false,
    coordenador: null,
    coordenador_username: null,
    coordenador_nome: 'Maria Coordenadora',
    inicio: '2026-10-10T12:00:00Z', // 09:00 em Fortaleza (UTC-3)
    fim: '2026-10-10T15:00:00Z',
    status: 'aprovado',
    observacoes: null,
    local: null,
    is_online: false,
    external_event_id: null,
    created_at: '2026-09-01T12:00:00Z',
    updated_at: '2026-09-01T12:00:00Z',
    participations: [],
    fluxo: 'NAO_SUPER',
    gcal_status: 'NONE',
    gcal_last_sync_at: null,
    gcal_last_error: null,
    meet_link: null,
    ...overrides,
  };
}

function pageOf(results: Solicitacao[], count = results.length) {
  return { count, next: null, previous: null, results };
}

/** Erro no formato que `fetchAPI` lança (status + response.data). */
function apiError(status: number, data: { code?: string; detail?: string } = {}) {
  return Object.assign(new Error(data.detail ?? `Erro ${status}`), {
    status,
    response: { status, data },
  });
}

let listResponse: ReturnType<typeof pageOf>;
let actionResult: (url: string) => Promise<unknown>;

const isList = (url: unknown) => String(url).startsWith('/solicitacoes/?');
const listCalls = () => fetchAPIMock.mock.calls.filter(([url]) => isList(url));
const actionCalls = () =>
  fetchAPIMock.mock.calls.filter(([url]) => /^\/solicitacoes\/\d+\/[a-z-]+\/$/.test(String(url)));

function LocationProbe() {
  const location = useLocation();
  return <output data-testid="location">{location.pathname + location.search}</output>;
}

function renderPage(url = '/solicitacoes/publicacao') {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <PublicacaoSetorPage />
      <LocationProbe />
    </MemoryRouter>,
  );
}

/** Clica na ação da linha (por aria-label) e confirma no Popconfirm. */
async function confirmAction(buttonLabel: RegExp, popTitle: string, okText: string) {
  fireEvent.click(await screen.findByLabelText(buttonLabel));
  const title = await screen.findByText(popTitle);
  const popover = title.closest('.ant-popover') as HTMLElement;
  fireEvent.click(within(popover).getByText(okText));
}

const originalLocation = window.location;

beforeEach(() => {
  vi.clearAllMocks();
  googleHook.status = READY;
  googleHook.loading = false;
  googleHook.error = null;
  googleHook.disconnect.mockResolvedValue({ success: true });
  listResponse = pageOf([]);
  actionResult = () => Promise.resolve({ detail: 'ok', solicitacao_id: 7 });
  fetchAPIMock.mockImplementation((url: string) => {
    if (isList(url)) return Promise.resolve(listResponse);
    if (/^\/solicitacoes\/\d+\/[a-z-]+\/$/.test(url)) return actionResult(url);
    return Promise.reject(new Error(`URL inesperada no teste: ${url}`));
  });
  vi.spyOn(message, 'success').mockImplementation(vi.fn());
  vi.spyOn(message, 'error').mockImplementation(vi.fn());
  vi.spyOn(message, 'warning').mockImplementation(vi.fn());
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
  Object.defineProperty(window, 'location', { configurable: true, value: originalLocation });
});

// ============================================================================
// Testes
// ============================================================================

describe('PublicacaoSetorPage — estrutura e lista', () => {
  test('é uma <section> rotulada pelo h2 "Publicar na agenda do Google"', async () => {
    renderPage();
    const heading = await screen.findByText('Publicar na agenda do Google');
    expect(heading.tagName).toBe('H2');
    const section = heading.closest('section');
    expect(section).not.toBeNull();
    expect(section?.getAttribute('aria-labelledby')).toBe(heading.id);
  });

  test('(a) pede só as publicáveis: aprovadas, publishable, a partir de hoje em Fortaleza, por início, 20/página — sem mine/sector', async () => {
    vi.useFakeTimers({ toFake: ['Date'] });
    // 02:00 UTC de 01/10 = 23:00 de 30/09 em Fortaleza (RD-06): "hoje" é 30/09.
    vi.setSystemTime(new Date('2026-10-01T02:00:00Z'));

    renderPage();

    await waitFor(() => expect(listCalls()).toHaveLength(1));
    const params = new URL(String(listCalls()[0]?.[0]), 'https://x').searchParams;
    expect(params.get('status')).toBe('aprovado');
    expect(params.get('publishable')).toBe('true');
    expect(params.get('date_from')).toBe('2026-09-30');
    expect(params.get('ordering')).toBe('inicio');
    expect(params.get('page')).toBe('1');
    expect(params.get('page_size')).toBe('20');
    expect(params.has('mine')).toBe(false);
    expect(params.has('sector')).toBe(false);
  });

  test('colunas: data/hora em Fortaleza, projeto, município, tipo, coordenador, status GCal e Meet — sem username (pode ser CPF)', async () => {
    listResponse = pageOf([
      makeSolic({
        usuario_username: '12345678901',
        gcal_status: 'ERROR',
        gcal_last_error: 'O Google recusou o acesso ao calendário da organização.',
        meet_link: 'https://meet.google.com/abc-defg-hij',
      }),
    ]);
    renderPage();

    expect(await screen.findByText('10/10/2026 09:00')).toBeInTheDocument();
    expect(screen.getByText('Vidas Em Rede')).toBeInTheDocument();
    expect(screen.getByText('Sobral')).toBeInTheDocument();
    expect(screen.getByText('Formação')).toBeInTheDocument();
    expect(screen.getByText('Maria Coordenadora')).toBeInTheDocument();
    expect(screen.getByText('Erro')).toBeInTheDocument();
    // O erro do Google fica visível na linha (não só em tooltip).
    expect(
      screen.getByText('O Google recusou o acesso ao calendário da organização.'),
    ).toBeInTheDocument();
    expect(screen.getByText('Entrar na reunião')).toBeInTheDocument();
    // LGPD: username de login pode ser o CPF (import) — nunca exibido.
    expect(screen.queryByText('12345678901')).not.toBeInTheDocument();
  });

  test('(i) lista vazia mostra a copy do estado vazio com link para Nova Solicitação', async () => {
    renderPage();
    const empty = await screen.findByText(/Nenhum evento aprovado do seu setor a partir de hoje\./);
    expect(empty.textContent).toContain(
      'Eventos criados em Nova Solicitação aparecem aqui depois de aprovados.',
    );
    expect(within(empty).getByText('Nova Solicitação').closest('a')?.getAttribute('href')).toBe(
      '/solicitacoes/nova',
    );
  });

  test('paginação no servidor: trocar de página pede page=2 com os mesmos filtros', async () => {
    listResponse = pageOf([makeSolic()], 25);
    renderPage();
    await screen.findByText('Vidas Em Rede');

    fireEvent.click(screen.getByTitle('2'));

    await waitFor(() => expect(listCalls()).toHaveLength(2));
    const params = new URL(String(listCalls()[1]?.[0]), 'https://x').searchParams;
    expect(params.get('page')).toBe('2');
    expect(params.get('publishable')).toBe('true');
    expect(params.get('page_size')).toBe('20');
  });

  test('latest-wins: resposta obsoleta não sobrescreve a mais recente', async () => {
    const pending: Array<(value: unknown) => void> = [];
    fetchAPIMock.mockImplementation((url: string) =>
      isList(url) ? new Promise((resolve) => pending.push(resolve)) : Promise.reject(new Error(url)),
    );
    renderPage();
    await waitFor(() => expect(pending).toHaveLength(1));
    await act(async () => {
      pending[0]?.(pageOf([makeSolic({ municipio_nome: 'Carga inicial' })], 25));
    });
    await screen.findByText('Carga inicial');

    // Duas cargas concorrentes: página 2 (obsoleta) e volta à página 1 (a mais nova).
    fireEvent.click(screen.getByTitle('2'));
    fireEvent.click(screen.getByTitle('1'));
    await waitFor(() => expect(pending).toHaveLength(3));

    await act(async () => {
      pending[2]?.(pageOf([makeSolic({ municipio_nome: 'Resposta nova' })], 25));
    });
    await screen.findByText('Resposta nova');
    await act(async () => {
      pending[1]?.(pageOf([makeSolic({ municipio_nome: 'Resposta velha' })], 25));
    });

    expect(screen.getByText('Resposta nova')).toBeInTheDocument();
    expect(screen.queryByText('Resposta velha')).not.toBeInTheDocument();
  });
});

describe('PublicacaoSetorPage — conexão e prontidão', () => {
  test('usa o card no modo de calendário fixo (sem /calendars/)', async () => {
    renderPage();
    expect(
      await screen.findByText('Os eventos são publicados no calendário oficial da organização.'),
    ).toBeInTheDocument();
    expect(fetchAPIMock).not.toHaveBeenCalledWith('/integrations/google/calendars/');
  });

  test('(b) sem conexão: ações desabilitadas com o motivo visível; Conectar vai ao OAuth com return_to codificado', async () => {
    const fakeLocation = { href: '' };
    Object.defineProperty(window, 'location', { configurable: true, value: fakeLocation });
    googleHook.status = NOT_CONNECTED;
    listResponse = pageOf([makeSolic()]);
    renderPage();

    expect(await screen.findByLabelText(/^Publicar: Vidas Em Rede/)).toBeDisabled();
    expect(screen.getByText('Conecte sua conta Google para publicar os eventos.')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Conectar conta Google'));
    expect(fakeLocation.href).toBe(
      '/api/oauth/google/start/?return_to=%2Fsolicitacoes%2Fpublicacao',
    );
  });

  test('(b2) conexão removida pelo sistema: só o aviso do card, sem repetir o da página', async () => {
    googleHook.status = { ...NOT_CONNECTED, reconnectRequired: true };
    listResponse = pageOf([makeSolic()]);
    renderPage();

    expect(await screen.findByLabelText(/^Publicar: Vidas Em Rede/)).toBeDisabled();
    expect(screen.getByText(/O Google revogou o acesso da sua conta/)).toBeInTheDocument();
    expect(screen.queryByText('Conecte sua conta Google para publicar os eventos.')).not.toBeInTheDocument();
  });

  test('(b3) conexão removida pelo sistema E sem setor: o alerta da DAT continua (o card não aparece)', async () => {
    googleHook.status = { ...NOT_CONNECTED, publishBlockReason: 'no_setor_scope', reconnectRequired: true };
    renderPage();

    expect(await screen.findByText(/não tem setor vigente/)).toBeInTheDocument();
  });

  test('(f) sem setor vigente: alerta da DAT e nenhum botão de conectar', async () => {
    googleHook.status = { ...NOT_CONNECTED, publishBlockReason: 'no_setor_scope' };
    renderPage();

    expect(
      await screen.findByText(
        'Seu cadastro não tem setor vigente. Peça à DAT para cadastrar seu vínculo de gerência.',
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText('Conectar conta Google')).not.toBeInTheDocument();
    expect(screen.queryByText('Integração Google Calendar')).not.toBeInTheDocument();
  });

  test('(g) agenda da organização não configurada: alerta e ações desabilitadas', async () => {
    googleHook.status = {
      ...READY,
      publishReady: false,
      publishBlockReason: 'google_calendar_not_configured',
    };
    listResponse = pageOf([makeSolic()]);
    renderPage();

    const alertText = await screen.findByText(
      'A agenda da organização ainda não foi configurada no sistema. Avise o Controle.',
    );
    expect(alertText.closest('[role="alert"]')).not.toBeNull();
    expect(await screen.findByLabelText(/^Publicar: Vidas Em Rede/)).toBeDisabled();
  });

  test('(e) volta do OAuth com ?google=connected: sucesso (role=status), limpa a query e recarrega o status', async () => {
    renderPage('/solicitacoes/publicacao?google=connected');

    const ok = await screen.findByText(
      'Conta Google conectada. Você já pode publicar os eventos do seu setor.',
    );
    expect(ok.closest('[role="status"]')).not.toBeNull();
    await waitFor(() =>
      expect(screen.getByTestId('location').textContent).toBe('/solicitacoes/publicacao'),
    );
    expect(googleHook.fetchStatus).toHaveBeenCalled();
  });

  test('(e) volta do OAuth com ?google=error&reason=access_denied: copy mapeada (role=alert) e query limpa', async () => {
    renderPage('/solicitacoes/publicacao?google=error&reason=access_denied');

    const err = await screen.findByText(
      'Você não autorizou o acesso à sua conta Google. Para publicar, conecte de novo e aceite as permissões.',
    );
    expect(err.closest('[role="alert"]')).not.toBeNull();
    await waitFor(() =>
      expect(screen.getByTestId('location').textContent).toBe('/solicitacoes/publicacao'),
    );
  });

  test('(e) motivo desconhecido cai na copy genérica', async () => {
    renderPage('/solicitacoes/publicacao?google=error&reason=server_error');
    expect(
      await screen.findByText(
        'Não foi possível conectar sua conta Google. Tente de novo; se o erro continuar, avise o Controle.',
      ),
    ).toBeInTheDocument();
  });
});

describe('PublicacaoSetorPage — ações', () => {
  test('(c) confirmar o Popconfirm faz UM POST em /publish/ com corpo {} e recarrega', async () => {
    listResponse = pageOf([makeSolic()]);
    renderPage();

    await confirmAction(/^Publicar: Vidas Em Rede, 10\/10\/2026 09:00/, 'Publicar este evento na agenda da organização?', 'Publicar');

    await waitFor(() => expect(actionCalls()).toHaveLength(1));
    const [url, options] = actionCalls()[0] ?? [];
    expect(url).toBe('/solicitacoes/7/publish/');
    // Nunca dry_run/apply_blocked: corpo vazio.
    expect(options).toMatchObject({ method: 'POST', body: '{}' });
    await waitFor(() => expect(listCalls()).toHaveLength(2));
    expect(message.success).toHaveBeenCalledWith('Publicação enviada; o status muda em alguns segundos.');
  });

  test.each([
    {
      caso: 'PUBLISHED → Atualizar no Google = /resync-gcal/',
      row: { gcal_status: 'PUBLISHED' as const, external_event_id: 'asv27' },
      label: /^Atualizar no Google: Vidas Em Rede/,
      popTitle: 'Atualizar este evento no Google Agenda?',
      ok: 'Atualizar',
      endpoint: '/solicitacoes/7/resync-gcal/',
    },
    {
      caso: 'PUBLISHED → Remover do Google = /cancel-gcal/',
      row: { gcal_status: 'PUBLISHED' as const, external_event_id: 'asv27' },
      label: /^Remover do Google: Vidas Em Rede/,
      popTitle: 'Remover este evento do Google Agenda?',
      ok: 'Remover',
      endpoint: '/solicitacoes/7/cancel-gcal/',
    },
    {
      caso: 'ERROR sem id → Tentar de novo = /publish/',
      row: { gcal_status: 'ERROR' as const, external_event_id: null },
      label: /^Tentar de novo: Vidas Em Rede/,
      popTitle: 'Tentar publicar este evento de novo?',
      ok: 'Tentar de novo',
      endpoint: '/solicitacoes/7/publish/',
    },
  ])('$caso', async ({ row, label, popTitle, ok, endpoint }) => {
    listResponse = pageOf([makeSolic(row)]);
    renderPage();

    await confirmAction(label, popTitle, ok);

    await waitFor(() => expect(actionCalls()).toHaveLength(1));
    expect(actionCalls()[0]?.[0]).toBe(endpoint);
    await waitFor(() => expect(listCalls()).toHaveLength(2));
  });

  test('linha PENDING não oferece ação (publicação em voo)', async () => {
    listResponse = pageOf([makeSolic({ gcal_status: 'PENDING' })]);
    renderPage();
    expect(await screen.findByText('Publicando…')).toBeInTheDocument();
    expect(screen.queryByLabelText(/^Publicar:/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/^Atualizar no Google:/)).not.toBeInTheDocument();
  });

  test('(h) 403 google_not_connected: recarrega o status e pede para conectar', async () => {
    listResponse = pageOf([makeSolic()]);
    actionResult = () => Promise.reject(apiError(403, { code: 'google_not_connected' }));
    renderPage();

    await confirmAction(/^Publicar: Vidas Em Rede/, 'Publicar este evento na agenda da organização?', 'Publicar');

    await waitFor(() => expect(googleHook.fetchStatus).toHaveBeenCalled());
    expect(message.warning).toHaveBeenCalledWith(
      'Sua conta Google não está conectada. Conecte-a para publicar.',
    );
    expect(listCalls()).toHaveLength(1);
  });

  test('(h) 404: avisa que o evento não está mais disponível e recarrega a lista', async () => {
    listResponse = pageOf([makeSolic()]);
    actionResult = () => Promise.reject(apiError(404, { detail: 'Não encontrado.' }));
    renderPage();

    await confirmAction(/^Publicar: Vidas Em Rede/, 'Publicar este evento na agenda da organização?', 'Publicar');

    await waitFor(() =>
      expect(message.error).toHaveBeenCalledWith('Este evento não está mais disponível para você.'),
    );
    await waitFor(() => expect(listCalls()).toHaveLength(2));
  });

  test('(h) 409: mostra a mensagem do backend', async () => {
    listResponse = pageOf([makeSolic({ gcal_status: 'PUBLISHED', external_event_id: 'asv27' })]);
    actionResult = () =>
      Promise.reject(apiError(409, { code: 'CONFLICT', detail: 'Evento não está publicado.' }));
    renderPage();

    await confirmAction(/^Remover do Google: Vidas Em Rede/, 'Remover este evento do Google Agenda?', 'Remover');

    await waitFor(() => expect(message.error).toHaveBeenCalledWith('Evento não está publicado.'));
  });

  test('(h) 409 google_calendar_not_configured: mostra a mensagem e recarrega o status', async () => {
    listResponse = pageOf([makeSolic()]);
    actionResult = () =>
      Promise.reject(
        apiError(409, {
          code: 'google_calendar_not_configured',
          detail: 'A agenda da organização ainda não foi configurada no sistema. Avise o Controle.',
        }),
      );
    renderPage();

    await confirmAction(/^Publicar: Vidas Em Rede/, 'Publicar este evento na agenda da organização?', 'Publicar');

    await waitFor(() =>
      expect(message.error).toHaveBeenCalledWith(
        'A agenda da organização ainda não foi configurada no sistema. Avise o Controle.',
      ),
    );
    expect(googleHook.fetchStatus).toHaveBeenCalled();
  });

  test('(h) 429: pede para aguardar um minuto', async () => {
    listResponse = pageOf([makeSolic()]);
    actionResult = () => Promise.reject(apiError(429, { detail: 'Request was throttled.' }));
    renderPage();

    await confirmAction(/^Publicar: Vidas Em Rede/, 'Publicar este evento na agenda da organização?', 'Publicar');

    await waitFor(() =>
      expect(message.error).toHaveBeenCalledWith('Muitas ações seguidas; aguarde um minuto.'),
    );
  });
});

describe('PublicacaoSetorPage — polling (d)', () => {
  test('sem linha PENDING não há polling', async () => {
    vi.useFakeTimers();
    listResponse = pageOf([makeSolic({ gcal_status: 'NONE' })]);
    renderPage();
    await vi.advanceTimersByTimeAsync(0);
    expect(listCalls()).toHaveLength(1);

    await vi.advanceTimersByTimeAsync(TIMING.PUBLICACAO_PENDENTE_POLL_MS * 3);

    expect(listCalls()).toHaveLength(1);
  });

  test('com linha PENDING recarrega a cada intervalo e para quando nada mais está PENDING', async () => {
    vi.useFakeTimers();
    listResponse = pageOf([makeSolic({ gcal_status: 'PENDING' })]);
    renderPage();
    await vi.advanceTimersByTimeAsync(0);
    expect(listCalls()).toHaveLength(1);

    // O worker terminou: a próxima carga já vem PUBLISHED.
    listResponse = pageOf([makeSolic({ gcal_status: 'PUBLISHED', external_event_id: 'asv27' })]);
    await vi.advanceTimersByTimeAsync(TIMING.PUBLICACAO_PENDENTE_POLL_MS);
    expect(listCalls()).toHaveLength(2);

    await vi.advanceTimersByTimeAsync(TIMING.PUBLICACAO_PENDENTE_POLL_MS * 3);
    expect(listCalls()).toHaveLength(2);
  });

  const avancar = async (ms: number): Promise<void> => {
    await act(async () => { await vi.advanceTimersByTimeAsync(ms); });
  };

  test('o tick não liga o carregamento da tabela (sem piscar a cada 5 s)', async () => {
    vi.useFakeTimers();
    listResponse = pageOf([makeSolic({ gcal_status: 'PENDING' })]);
    const { container } = renderPage();
    await avancar(0);
    expect(container.querySelector('.ant-spin-spinning')).toBeNull();

    // A carga do tick fica em voo.
    fetchAPIMock.mockImplementation(() => new Promise(() => undefined));
    await avancar(TIMING.PUBLICACAO_PENDENTE_POLL_MS);
    // O Spin do antd liga com um setTimeout: dá tempo de ele aparecer antes de conferir.
    await avancar(100);

    expect(listCalls()).toHaveLength(2);
    expect(container.querySelector('.ant-spin-spinning')).toBeNull();
    expect(screen.getByText('Vidas Em Rede')).toBeInTheDocument();
  });

  test('429 no tick: pausa pelo Retry-After, UM aviso (role=status) e nenhum erro por tick', async () => {
    vi.useFakeTimers();
    listResponse = pageOf([makeSolic({ gcal_status: 'PENDING' })]);
    renderPage();
    await avancar(0);

    fetchAPIMock.mockImplementation(() =>
      Promise.reject(Object.assign(apiError(429, { detail: 'Limite excedido.' }), { retryAfterSeconds: 30 })));
    await avancar(TIMING.PUBLICACAO_PENDENTE_POLL_MS);
    expect(listCalls()).toHaveLength(2);

    const avisos = screen.getAllByText('Atualização automática pausada por alguns instantes.');
    expect(avisos).toHaveLength(1);
    expect(avisos[0]?.closest('[role="status"]')).not.toBeNull();
    expect(message.error).not.toHaveBeenCalled();

    // Durante a pausa (30 s) passam vários ticks de 5 s: nenhum pedido.
    await avancar(29_000);
    expect(listCalls()).toHaveLength(2);

    await avancar(1_000);
    expect(listCalls()).toHaveLength(3);
  });

  test('429 na primeira carga: diz que a lista não carregou (role=alert)', async () => {
    vi.useFakeTimers();
    fetchAPIMock.mockImplementation(() => Promise.reject(apiError(429, { detail: 'Limite excedido.' })));
    renderPage();
    await avancar(0);

    const aviso = screen.getByText(/Não foi possível carregar agora/);
    expect(aviso.closest('[role="alert"]')).not.toBeNull();
  });
});
