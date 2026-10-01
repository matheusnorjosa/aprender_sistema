/**
 * Auditoria UX 30/09, rodada 3 (MÉDIA): quem só digita perdia a sessão.
 *
 * Digitar e rolar não fazem request, e a sessão do Django vence 2 h depois do último request
 * (SESSION_ENGINE=cache, SESSION_SAVE_EVERY_REQUEST=True). A pessoa preenchia um formulário,
 * a sessão vencia no servidor sem aviso, e o salvar voltava 403: o App ia ao login e o texto
 * se perdia. Agora a atividade renova a sessão em segundo plano (GET /api/me/, no máximo a
 * cada 10 min); o limite de 2 h vale para inatividade real.
 *
 * Rodada 4 (MÉDIA): o relógio conta da última resposta do servidor a um request desta aba (o
 * Django renova a sessão em todo request), e a aba parada vai ao login 120-122 min depois dele.
 *
 * App, monitor, aviso e fetchAPI reais; o servidor falso imita o Django (a sessão vence 2 h
 * depois do último request; sem sessão, 403 NOT_AUTHENTICATED).
 */

import { render, screen, act, fireEvent } from '@testing-library/react';
import { useState, type JSX } from 'react';
import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { apagarAvisoDoLogin, lerAvisoDoLogin } from '../utils/storage';

vi.mock('../components/AppSidebar', () => ({ AppSidebar: () => <div>SIDEBAR</div> }));
vi.mock('../components/AppHeader', () => ({ AppHeader: () => <div>HEADER</div> }));
vi.mock('../pages/Auth/LoginPage', () => ({ default: () => <div>LOGIN_PAGE</div> }));
vi.mock('../hooks/useGCalAlertsPolling', () => ({
  useGCalAlertsPolling: () => ({ alerts: { errors: 0, warnings: 0 } }),
}));
vi.mock('../hooks/useUnreadNotificationsPolling', () => ({
  useUnreadNotificationsPolling: () => ({ unreadNotifications: 0 }),
}));
vi.mock('../services/preloadSearchData', () => ({ preloadSearchData: vi.fn().mockResolvedValue(undefined) }));
vi.mock('../services/swCache', () => ({ clearApiCaches: vi.fn().mockResolvedValue(undefined) }));

// A tela: um formulário que só digita (sem request) e salva com POST.
vi.mock('../components/AppRoutes', async () => {
  const { fetchAPI } = await import('../api/config');
  function Formulario(): JSX.Element {
    const [texto, setTexto] = useState('');
    const [salvo, setSalvo] = useState(false);
    return (
      <div>
        <textarea aria-label="Justificativa" value={texto} onChange={(e) => setTexto(e.target.value)} />
        <button
          onClick={() => {
            void fetchAPI('/solicitacoes/', { method: 'POST', body: JSON.stringify({ texto }) })
              .then(() => setSalvo(true))
              .catch(() => undefined);
          }}
        >
          Salvar
        </button>
        {salvo && <p>SALVO</p>}
      </div>
    );
  }
  return { AppRoutes: () => <Formulario /> };
});

import App from '../App';

const DUAS_HORAS_MS = 7200 * 1000;
const usuario = {
  id: 1,
  username: 'coord',
  email: 'coord@example.invalid',
  first_name: 'Coord',
  last_name: 'Teste',
  name: 'Coord Teste',
  groups: [],
  setores: [],
  funcoes: [],
  gerencias: [],
  is_superuser: false,
  is_superintendencia: false,
  can_approve_super: false,
  permissions: [],
};

const locationOriginal = window.location;
const reloadMock = vi.fn();

/** Servidor falso: a sessão vence 2 h depois do último request; registra os requests e as renovações. */
function servidor(): { viva: () => boolean; requests: string[]; renovacoes: number[] } {
  let venceEm = Date.now() + DUAS_HORAS_MS;
  const requests: string[] = [];
  const renovacoes: number[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const caminho = new URL(String(input), 'http://localhost').pathname;
      requests.push(`${init?.method ?? 'GET'} ${caminho}`);
      if (caminho === '/api/csrf/') return new Response(JSON.stringify({ csrfToken: 'tok' }), { status: 200 });
      if (Date.now() >= venceEm) {
        return new Response(JSON.stringify({ code: 'NOT_AUTHENTICATED', detail: 'Sem sessão.' }), { status: 403 });
      }
      venceEm = Date.now() + DUAS_HORAS_MS;
      renovacoes.push(Date.now());
      const corpo = caminho === '/api/me/' ? usuario : caminho === '/api/me/policies/' ? [] : { id: 9 };
      return new Response(JSON.stringify(corpo), { status: caminho === '/api/solicitacoes/' ? 201 : 200 });
    }),
  );
  return { viva: () => Date.now() < venceEm, requests, renovacoes };
}

async function passar(segundos: number): Promise<void> {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(segundos * 1000);
  });
}

async function abrirLogado(): Promise<void> {
  render(<App />);
  for (let i = 0; i < 5; i++) await passar(0);
  expect(screen.getByLabelText('Justificativa')).toBeInTheDocument();
}

describe('App — sessão de quem está usando sem fazer request (rodada 3)', () => {
  beforeEach(() => {
    vi.useFakeTimers({ now: 0 });
    reloadMock.mockClear();
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { ...locationOriginal, reload: reloadMock },
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    Object.defineProperty(window, 'location', { configurable: true, value: locationOriginal });
    apagarAvisoDoLogin();
  });

  test('digitando sem parar por mais de 2 h: o salvar funciona, sem login e sem perder o texto', async () => {
    const s = servidor();
    await abrirLogado();
    const campo = screen.getByLabelText('Justificativa');

    for (let i = 1; i <= 260; i++) {
      // 2 h 10 min: uma tecla a cada 30 s
      await act(async () => {
        fireEvent.keyDown(campo, { key: 'a' });
        fireEvent.change(campo, { target: { value: 'a'.repeat(i) } });
      });
      await passar(30);
    }
    expect(screen.queryByText('Sua sessão está prestes a expirar')).not.toBeInTheDocument();

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Salvar' }));
    });
    await passar(0);

    expect(screen.getByText('SALVO')).toBeInTheDocument();
    expect(reloadMock).not.toHaveBeenCalled();
    expect(s.viva()).toBe(true);
    expect(s.requests).not.toContain('POST /api/auth/logout/');
  });

  test('parado por mais de 2 h: vai ao login com o motivo de inatividade, sem POST de logout', async () => {
    const s = servidor();
    await abrirLogado();

    await passar(7260);
    await passar(0);

    expect(reloadMock).toHaveBeenCalledTimes(1);
    expect(lerAvisoDoLogin()).toBe('Sua sessão expirou por inatividade. Entre de novo.');
    expect(s.requests).not.toContain('POST /api/auth/logout/');
  });

  // Rodada 4 (MÉDIA): o relógio contava só das renovações do próprio monitor. Um salvar entre
  // duas renovações deixava a sessão viva além do zero local, e a pergunta da aba parada a
  // esticava por mais 2 h (login ~239 min depois do último uso). O relógio conta agora da
  // última resposta do servidor a esta aba.
  test('usa, salva e larga a aba: vai ao login 120-122 min depois do último request, sem esticar a sessão', async () => {
    const s = servidor();
    await abrirLogado();
    const campo = screen.getByLabelText('Justificativa');
    for (let m = 1; m < 3; m++) {
      await passar(60);
      await act(async () => {
        fireEvent.keyDown(campo, { key: 'a' });
      });
    }
    await passar(60);
    const salvar = screen.getByRole('button', { name: 'Salvar' });
    await act(async () => {
      fireEvent.mouseDown(salvar);
      fireEvent.click(salvar);
    });
    await passar(0);
    expect(screen.getByText('SALVO')).toBeInTheDocument();
    const ultimoRequest = Date.now();

    let loginEm: number | null = null;
    for (let m = 0; m < 300 && loginEm === null; m++) {
      await passar(60);
      if (reloadMock.mock.calls.length > 0) loginEm = Date.now();
    }

    expect(loginEm).not.toBeNull();
    const inatividadeMin = ((loginEm ?? 0) - ultimoRequest) / 60000;
    expect(inatividadeMin).toBeGreaterThanOrEqual(120);
    expect(inatividadeMin).toBeLessThanOrEqual(122);
    expect(s.renovacoes.filter((t) => t > ultimoRequest)).toEqual([]);
    expect(lerAvisoDoLogin()).toBe('Sua sessão expirou por inatividade. Entre de novo.');
    expect(s.requests).not.toContain('POST /api/auth/logout/');
  });
});
