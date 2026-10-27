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
import { definirLarguraTela } from '../../../test/larguraTela';
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

// Tela pesada (AntD + ResponsiveTable): na CI, cerca de 4x mais lenta que local e com cobertura, casos passam dos
// 5 s padrão. Só o limite de tempo muda, nenhuma asserção.
vi.setConfig({ testTimeout: 20_000 });

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
let deleteResult: (url: string) => Promise<unknown>;

const isList = (url: unknown) => String(url).startsWith('/solicitacoes/?');
const listCalls = () => fetchAPIMock.mock.calls.filter(([url]) => isList(url));
const actionCalls = () =>
  fetchAPIMock.mock.calls.filter(([url]) => /^\/solicitacoes\/\d+\/[a-z-]+\/$/.test(String(url)));
const isDelete = (url: unknown) => /^\/solicitacoes\/\d+\/$/.test(String(url));
const deleteCalls = () => fetchAPIMock.mock.calls.filter(([url]) => isDelete(url));

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

/**
 * Clica na ação da linha (por aria-label) e confirma no diálogo. O diálogo é um modal de verdade
 * (role=dialog, foco preso), não um Popconfirm: o balão não recebia o foco (achado do item 36).
 */
async function confirmAction(buttonLabel: RegExp, popTitle: string, okText: string) {
  fireEvent.click(await screen.findByLabelText(buttonLabel));
  const dialogo = await screen.findByRole('dialog');
  // O AntD repete o título (um oculto, que nomeia o diálogo): daí o getAll.
  expect(within(dialogo).getAllByText(popTitle, { exact: false }).length).toBeGreaterThan(0);
  fireEvent.click(within(dialogo).getByRole('button', { name: okText }));
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
  deleteResult = () => Promise.resolve(undefined);
  fetchAPIMock.mockImplementation((url: string) => {
    if (isList(url)) return Promise.resolve(listResponse);
    if (isDelete(url)) return deleteResult(url);
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

  test('colunas: data/hora em Fortaleza, projeto, município, tipo, coordenador, status GCal e Meet', async () => {
    listResponse = pageOf([
      makeSolic({
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
  });

  test('Publicado, Publicando… e Erro, e o motivo do erro, com contraste AA (4,5:1)', async () => {
    // O preset do AntD pinta a cor 6 sobre a cor 1 (2,21, 3,66 e 2,99:1); o Text danger dá 3,27:1.
    listResponse = pageOf([
      makeSolic({ id: 1, municipio_nome: 'Crato', gcal_status: 'ERROR', gcal_last_error: 'Motivo do Google.' }),
      makeSolic({ id: 2, municipio_nome: 'Iguatu', gcal_status: 'PENDING' }),
      makeSolic({ id: 3, municipio_nome: 'Quixadá', gcal_status: 'PUBLISHED', external_event_id: 'asv3' }),
    ]);
    renderPage();

    const erro = (await screen.findByText('Crato')).closest('tr') as HTMLElement;
    expect(within(erro).getByText('Erro')).toHaveStyle({ color: '#b32430' });
    expect(within(erro).getByText('Motivo do Google.')).toHaveStyle({ color: '#b32430' });
    expect(within(screen.getByText('Iguatu').closest('tr') as HTMLElement).getByText('Publicando…')).toHaveStyle({ color: '#0958d9' });
    expect(within(screen.getByText('Quixadá').closest('tr') as HTMLElement).getByText('Publicado')).toHaveStyle({ color: '#237804' });
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

  // Achado do item 36 (19/10/2026): a falha virava "Nenhum evento aprovado do seu setor".
  test('falha ao carregar: o motivo e "Tentar de novo" no lugar do vazio que mandava criar solicitação', async () => {
    fetchAPIMock.mockImplementation((url: string) =>
      isList(url) ? Promise.reject(apiError(500, { detail: 'Erro interno do servidor.' })) : Promise.reject(new Error(url)),
    );
    renderPage();

    const aviso = await screen.findByText('Não foi possível carregar a lista.');
    expect(aviso.closest('[role="alert"]')).not.toBeNull();
    expect(screen.getByText('Erro interno do servidor.')).toBeInTheDocument();
    expect(screen.queryByText(/Nenhum evento aprovado do seu setor/)).not.toBeInTheDocument();

    fetchAPIMock.mockImplementation((url: string) =>
      isList(url) ? Promise.resolve(pageOf([makeSolic()])) : Promise.reject(new Error(url)),
    );
    fireEvent.click(screen.getByRole('button', { name: 'Tentar de novo' }));

    expect(await screen.findByText('Vidas Em Rede')).toBeInTheDocument();
    expect(screen.queryByText('Não foi possível carregar a lista.')).not.toBeInTheDocument();
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

  // A lista encolheu com a pessoa na página 2 (evento cancelado, virada do dia): o DRF responde 404
  // "Página inválida". Sem recuo, o erro tirava a paginação e o "Tentar de novo" repetia o 404.
  test('página que deixou de existir (404): volta uma página em vez de travar no erro', async () => {
    listResponse = pageOf([makeSolic()], 25);
    renderPage();
    await screen.findByText('Vidas Em Rede');

    fetchAPIMock.mockImplementation((url: string) => {
      if (!isList(url)) return Promise.reject(new Error(url));
      const pagina = new URL(url, 'https://x').searchParams.get('page');
      return pagina === '2'
        ? Promise.reject(apiError(404, { detail: 'Página inválida.' }))
        : Promise.resolve(pageOf([makeSolic({ municipio_nome: 'Crato' })], 20));
    });
    fireEvent.click(screen.getByTitle('2'));

    expect(await screen.findByText('Crato')).toBeInTheDocument();
    const ultima = new URL(String(listCalls().at(-1)?.[0]), 'https://x').searchParams;
    expect(ultima.get('page')).toBe('1');
    expect(screen.queryByText('Não foi possível carregar a lista.')).not.toBeInTheDocument();
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

  test('(e) volta do start com ?google=error&reason=server_error: diz que o Google não respondeu', async () => {
    renderPage('/solicitacoes/publicacao?google=error&reason=server_error');

    const err = await screen.findByText(
      'Não foi possível falar com o Google agora. Tente conectar de novo em alguns minutos.',
    );
    expect(err.closest('[role="alert"]')).not.toBeNull();
  });

  test('(e) item 38: volta do start com ?google=error&reason=no_setor_scope diz por que não conectou, sem mandar tentar de novo', async () => {
    googleHook.status = { ...NOT_CONNECTED, publishBlockReason: 'no_setor_scope' };
    renderPage('/solicitacoes/publicacao?google=error&reason=no_setor_scope');

    const err = await screen.findByText(
      'A conta Google não foi conectada porque seu cadastro não tem setor vigente.',
    );
    expect(err.closest('[role="alert"]')).not.toBeNull();
    expect(
      screen.getByText(
        'Seu cadastro não tem setor vigente. Peça à DAT para cadastrar seu vínculo de gerência.',
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Tente de novo/)).not.toBeInTheDocument();
  });

  test('(e) motivo desconhecido cai na copy genérica', async () => {
    renderPage('/solicitacoes/publicacao?google=error&reason=motivo_que_a_tela_nao_conhece');
    expect(
      await screen.findByText(
        'Não foi possível conectar sua conta Google. Tente de novo; se o erro continuar, avise o Controle.',
      ),
    ).toBeInTheDocument();
  });
});

describe('PublicacaoSetorPage — ações', () => {
  test('(c) confirmar o diálogo faz UM POST em /publish/ com corpo {} e recarrega', async () => {
    listResponse = pageOf([makeSolic()]);
    renderPage();

    await confirmAction(/^Publicar: Vidas Em Rede, 10\/10\/2026 09:00/, 'Publicar na agenda da organização', 'Publicar');

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
      popTitle: 'Atualizar no Google Agenda',
      ok: 'Atualizar',
      endpoint: '/solicitacoes/7/resync-gcal/',
    },
    {
      caso: 'PUBLISHED → Tirar só do Google = /cancel-gcal/',
      row: { gcal_status: 'PUBLISHED' as const, external_event_id: 'asv27' },
      label: /^Tirar só do Google: Vidas Em Rede/,
      popTitle: 'Tirar do Google Agenda',
      ok: 'Tirar do Google',
      endpoint: '/solicitacoes/7/cancel-gcal/',
    },
    {
      caso: 'ERROR sem id → Tentar de novo = /publish/',
      row: { gcal_status: 'ERROR' as const, external_event_id: null },
      label: /^Tentar de novo: Vidas Em Rede/,
      popTitle: 'Tentar publicar de novo',
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
    if (endpoint.endsWith('/cancel-gcal/')) {
      // Sem "Remoção", a palavra ambígua que o rótulo novo tirou.
      expect(message.success).toHaveBeenCalledWith(
        'Pedido enviado: o evento sai do Google Agenda em alguns segundos e continua no sistema.'
      );
    }
  });

  test.each([
    {
      acao: 'Publicar',
      row: {},
      titulo: 'Publicar na agenda da organização: Vidas Em Rede, 10/10/2026 09:00?',
      texto: 'O evento é criado no calendário oficial da organização.',
    },
    {
      acao: 'Tirar só do Google',
      row: { gcal_status: 'PUBLISHED' as const, external_event_id: 'asv27' },
      titulo: 'Tirar do Google Agenda: Vidas Em Rede, 10/10/2026 09:00?',
      // Tirar do Google não apaga: diz que o evento fica no sistema (sem mandar a Apoio procurar
      // em Minhas Solicitações, que só lista os eventos de quem está logado).
      texto: 'O evento sai só da agenda da organização e continua no sistema.',
    },
  ])('$acao: a confirmação é um diálogo que cita o evento, abre no Cancelar e devolve o foco', async ({ acao, row, titulo, texto }) => {
    listResponse = pageOf([makeSolic(row)]);
    renderPage();

    const botao = await screen.findByLabelText(new RegExp(`^${acao}: Vidas Em Rede`));
    botao.focus();
    fireEvent.click(botao);

    const dialogo = await screen.findByRole('dialog');
    expect(dialogo).toHaveAccessibleName(titulo);
    expect(dialogo).toHaveTextContent(texto);
    const cancelar = within(dialogo).getByRole('button', { name: 'Cancelar' });
    await waitFor(() => expect(cancelar).toHaveFocus());

    // Cancelar não publica nada e o foco volta ao botão da linha.
    fireEvent.click(cancelar);
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(actionCalls()).toHaveLength(0);
    await waitFor(() => expect(botao).toHaveFocus());
  });

  test.each([
    { acao: 'Publicar', row: {}, ok: 'Publicar' },
    { acao: 'Tirar só do Google', row: { gcal_status: 'PUBLISHED' as const, external_event_id: 'asv27' }, ok: 'Tirar do Google' },
  ])('$acao confirmado: a linha recarrega sem o botão e o foco vai para a tabela, não para o body', async ({ acao, row, ok }) => {
    listResponse = pageOf([makeSolic(row)]);
    // Depois da ação a linha volta em voo (PENDING): sem ação nenhuma, o botão da linha sai do DOM.
    actionResult = () => {
      listResponse = pageOf([makeSolic({ gcal_status: 'PENDING' })]);
      return Promise.resolve({ detail: 'ok', solicitacao_id: 7 });
    };
    renderPage();

    const botao = await screen.findByLabelText(new RegExp(`^${acao}: Vidas Em Rede`));
    botao.focus();
    fireEvent.click(botao);
    const dialogo = await screen.findByRole('dialog');
    fireEvent.click(within(dialogo).getByRole('button', { name: ok }));

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    const linhaEmVoo = await screen.findByText('Publicando…');
    expect(botao).not.toBeInTheDocument();
    await waitFor(() => expect(document.activeElement).not.toBe(document.body));
    expect(document.activeElement?.contains(linhaEmVoo)).toBe(true);
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

    await confirmAction(/^Publicar: Vidas Em Rede/, 'Publicar na agenda da organização', 'Publicar');

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

    await confirmAction(/^Publicar: Vidas Em Rede/, 'Publicar na agenda da organização', 'Publicar');

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

    await confirmAction(/^Tirar só do Google: Vidas Em Rede/, 'Tirar do Google Agenda', 'Tirar do Google');

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

    await confirmAction(/^Publicar: Vidas Em Rede/, 'Publicar na agenda da organização', 'Publicar');

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

    await confirmAction(/^Publicar: Vidas Em Rede/, 'Publicar na agenda da organização', 'Publicar');

    await waitFor(() =>
      expect(message.error).toHaveBeenCalledWith('Muitas ações seguidas; aguarde um minuto.'),
    );
  });
});

describe('PublicacaoSetorPage — excluir evento que está no Google (decisão do dono, 27/10)', () => {
  const NO_GOOGLE = { gcal_status: 'PUBLISHED' as const, external_event_id: 'asv27' };

  test('Excluir só aparece na linha que está no Google e que o servidor diz que dá para excluir', async () => {
    listResponse = pageOf([
      makeSolic({ id: 7, projeto_nome: 'Pode Excluir', ...NO_GOOGLE, pode_excluir: true }),
      makeSolic({ id: 8, projeto_nome: 'Sem Poder', ...NO_GOOGLE, pode_excluir: false }),
      makeSolic({ id: 9, projeto_nome: 'Fora do Google', pode_excluir: true }),
      makeSolic({ id: 10, projeto_nome: 'Erro Com Id', gcal_status: 'ERROR', external_event_id: 'asv28', pode_excluir: true }),
      makeSolic({ id: 11, projeto_nome: 'Campo Ausente', ...NO_GOOGLE }),
    ]);
    renderPage();
    await screen.findByText('Pode Excluir');

    expect(screen.getByLabelText(/^Excluir: Pode Excluir, 10\/10\/2026 09:00/)).toHaveTextContent(/^Excluir$/);
    expect(screen.getByLabelText(/^Excluir: Erro Com Id/)).toBeInTheDocument();
    expect(screen.queryByLabelText(/^Excluir: Sem Poder/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/^Excluir: Fora do Google/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/^Excluir: Campo Ausente/)).not.toBeInTheDocument();
    // "Tirar só do Google" continua ao lado: as duas saídas são diferentes.
    expect(screen.getByLabelText(/^Tirar só do Google: Pode Excluir/)).toBeInTheDocument();
  });

  test('sem conexão com o Google, Excluir fica desabilitado como as outras ações', async () => {
    googleHook.status = NOT_CONNECTED;
    listResponse = pageOf([makeSolic({ ...NO_GOOGLE, pode_excluir: true })]);
    renderPage();

    expect(await screen.findByLabelText(/^Excluir: Vidas Em Rede/)).toBeDisabled();
  });

  test.each([
    {
      caso: 'publicado com Meet',
      row: { ...NO_GOOGLE, meet_link: 'https://meet.google.com/abc-defg-hij' },
      texto:
        '10/10/2026 09:00 · Sobral · Vidas Em Rede. Ele sai do sistema e do Google Agenda, junto com o link do Meet. Não dá para desfazer.',
    },
    {
      caso: 'erro (pode não estar lá)',
      row: { gcal_status: 'ERROR' as const, external_event_id: 'asv27' },
      texto: '10/10/2026 09:00 · Sobral · Vidas Em Rede. Ele sai do sistema e do Google Agenda, se estiver lá. Não dá para desfazer.',
    },
  ])('$caso: a confirmação é a de Minhas Solicitações, abre no Cancelar e Cancelar não exclui', async ({ row, texto }) => {
    listResponse = pageOf([makeSolic({ ...row, pode_excluir: true })]);
    renderPage();

    const botao = await screen.findByLabelText(/^Excluir: Vidas Em Rede/);
    botao.focus();
    fireEvent.click(botao);

    const dialogo = await screen.findByRole('dialog');
    expect(within(dialogo).getAllByText('Excluir evento?').length).toBeGreaterThan(0);
    expect(dialogo).toHaveTextContent(texto);
    const cancelar = within(dialogo).getByRole('button', { name: 'Cancelar' });
    await waitFor(() => expect(cancelar).toHaveFocus());
    expect(within(dialogo).getByRole('button', { name: 'Sim, excluir' })).toBeInTheDocument();

    fireEvent.click(cancelar);
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(deleteCalls()).toHaveLength(0);
    await waitFor(() => expect(botao).toHaveFocus());
  });

  test('"Sim, excluir" faz UM DELETE do evento, avisa e recarrega a lista; o foco vai para a tabela', async () => {
    listResponse = pageOf([makeSolic({ ...NO_GOOGLE, pode_excluir: true })]);
    deleteResult = () => {
      listResponse = pageOf([]);
      return Promise.resolve(undefined);
    };
    renderPage();

    const botao = await screen.findByLabelText(/^Excluir: Vidas Em Rede/);
    botao.focus();
    fireEvent.click(botao);
    const dialogo = await screen.findByRole('dialog');
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Sim, excluir' }));

    await waitFor(() => expect(deleteCalls()).toHaveLength(1));
    const [url, options] = deleteCalls()[0] ?? [];
    expect(url).toBe('/solicitacoes/7/');
    expect(options).toMatchObject({ method: 'DELETE' });
    await waitFor(() => expect(listCalls()).toHaveLength(2));
    expect(message.success).toHaveBeenCalledWith('Evento excluído do sistema e do Google Agenda.');
    expect(actionCalls()).toHaveLength(0);
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(botao).not.toBeInTheDocument();
    await waitFor(() => expect(document.activeElement).not.toBe(document.body));
  });

  test('recusa do servidor: mostra o motivo dele e a linha fica', async () => {
    listResponse = pageOf([makeSolic({ ...NO_GOOGLE, pode_excluir: true })]);
    const motivo = 'Não foi possível tirar o evento do Google Agenda: nada foi excluído. Tente excluir de novo em alguns minutos.';
    deleteResult = () => Promise.reject(apiError(400, { detail: motivo }));
    renderPage();

    await confirmAction(/^Excluir: Vidas Em Rede/, 'Excluir evento?', 'Sim, excluir');

    await waitFor(() => expect(message.error).toHaveBeenCalledWith(motivo));
    expect(message.success).not.toHaveBeenCalled();
    expect(screen.getByLabelText(/^Excluir: Vidas Em Rede/)).toBeInTheDocument();
  });

  test('a explicação do topo diz a diferença entre tirar só do Google e excluir', async () => {
    renderPage();
    const titulo = await screen.findByText('Publicar na agenda do Google');
    const topo = titulo.closest('header') as HTMLElement;
    expect(topo).toHaveTextContent('Tirar só do Google deixa o evento no sistema; Excluir tira dos dois lados.');
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

  // Revisão do item 36: uma falha passageira do polling (429, rede do celular) trocava a lista certa
  // pelo erro, tirava os botões da linha (o foco caía no body) e a tabela piscava no tick seguinte.
  test('falha de um tick do polling: a lista que estava na tela fica, com um aviso só', async () => {
    vi.useFakeTimers();
    listResponse = pageOf([makeSolic({ gcal_status: 'PENDING' })]);
    renderPage();
    await vi.advanceTimersByTimeAsync(0);
    expect(screen.getByText('Vidas Em Rede')).toBeInTheDocument();

    fetchAPIMock.mockImplementation((url: string) =>
      isList(url) ? Promise.reject(apiError(429, { detail: 'Muitas requisições.' })) : Promise.reject(new Error(url)),
    );
    await act(() => vi.advanceTimersByTimeAsync(TIMING.PUBLICACAO_PENDENTE_POLL_MS));
    expect(listCalls()).toHaveLength(2);

    expect(screen.queryByText('Não foi possível carregar a lista.')).not.toBeInTheDocument();
    expect(screen.getByText('Vidas Em Rede')).toBeInTheDocument();
    expect(message.error).toHaveBeenCalledWith(expect.objectContaining({ key: expect.any(String) }));
  });
});

// Achado do item 36 (19/10/2026): a tabela rolava na horizontal (scroll.x max-content) e, no
// celular, os botões ficavam fora da tela; a mensagem de erro do Google virava uma linha só.
describe('PublicacaoSetorPage — sem rolagem horizontal', () => {
  /** Títulos das colunas de dados (sem a do botão de expandir). */
  function cabecalhos(): string[] {
    return screen
      .getAllByRole('columnheader')
      .filter((th) => !th.classList.contains('ant-table-row-expand-icon-cell'))
      .map((th) => th.textContent?.trim() ?? '')
      .filter(Boolean);
  }

  test('a 1280 px: o evento (data, projeto, município, Google Agenda) e as ações; sem rolagem nem coluna fixa', async () => {
    listResponse = pageOf([makeSolic({ meet_link: 'https://meet.google.com/abc-defg-hij' })]);
    const { container } = renderPage();
    await screen.findByText('Vidas Em Rede');

    expect(cabecalhos()).toEqual(['Evento', 'Tipo', 'Coordenador', 'Meet', 'Ações']);
    const linha = screen.getByText('Vidas Em Rede').closest('tr') as HTMLElement;
    expect(within(linha).getByText('10/10/2026 09:00')).toBeInTheDocument();
    expect(within(linha).getByText('Sobral')).toBeInTheDocument();
    expect(within(linha).getByText('Não publicado')).toBeInTheDocument();
    expect(container.querySelector('.ant-table-content')?.getAttribute('style') ?? '').not.toMatch(/overflow/);
  });

  test('a 360 px: só o evento e as ações, com rótulo curto; o resto na linha expandida', async () => {
    definirLarguraTela(360);
    listResponse = pageOf([makeSolic({ gcal_status: 'PUBLISHED', external_event_id: 'asv27', pode_excluir: true })]);
    const { container } = renderPage();
    await screen.findByText('Vidas Em Rede');

    expect(cabecalhos()).toEqual(['Evento', 'Ações']);
    expect(container.querySelector('.ant-table-content')?.getAttribute('style') ?? '').not.toMatch(/overflow/);
    const linha = screen.getByText('Vidas Em Rede').closest('tr') as HTMLElement;
    expect(within(linha).getByText('Sobral')).toBeInTheDocument();
    // Texto visível curto; o nome acessível continua completo e começa por ele (WCAG 2.5.3).
    const atualizar = within(linha).getByLabelText(/^Atualizar no Google: Vidas Em Rede/);
    expect(atualizar).toHaveTextContent(/^Atualizar$/);
    // "Remover" sozinho parecia apagar o evento: no celular também diz que só sai do Google.
    expect(within(linha).getByLabelText(/^Tirar só do Google: Vidas Em Rede/)).toHaveTextContent(/^Tirar só do Google$/);
    // Excluir cabe na coluna de 116 px: o botão quebra linha em vez de alargá-la.
    const excluir = within(linha).getByLabelText(/^Excluir: Vidas Em Rede/);
    expect(excluir).toHaveTextContent(/^Excluir$/);
    expect(excluir).toHaveStyle({ whiteSpace: 'normal' });

    fireEvent.click(within(linha).getByRole('button', { name: /^Expandir linha de Vidas Em Rede/ }));
    const expandida = within(document.querySelector<HTMLElement>('.ant-table-expanded-row')!);
    for (const texto of ['Formação', 'Maria Coordenadora']) {
      expect(expandida.getByText(texto)).toBeInTheDocument();
    }
  });

  test('a mensagem de erro do Google quebra linha na célula (não estica a tabela)', async () => {
    const longa = 'O Google recusou o acesso ao calendário da organização. '.repeat(6).trim();
    listResponse = pageOf([makeSolic({ gcal_status: 'ERROR', gcal_last_error: longa })]);
    renderPage();

    const erro = await screen.findByText(longa);
    expect(erro).toHaveStyle({ overflowWrap: 'anywhere', whiteSpace: 'normal' });
  });
});
