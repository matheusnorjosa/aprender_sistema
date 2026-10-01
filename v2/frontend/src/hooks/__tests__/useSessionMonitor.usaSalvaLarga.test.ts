/**
 * Auditoria UX 30/09, rodada 4 (MÉDIA): a aba usada e largada esticava a própria sessão.
 *
 * O Django renova a sessão em todo request que atende (SESSION_SAVE_EVERY_REQUEST; só o 5xx não
 * renova) e a vence 2 h depois do último. Na rodada 3 o relógio da aba contava só das renovações
 * do próprio monitor: um salvar entre duas renovações deixava a sessão viva além do zero local,
 * e a pergunta da aba ociosa (GET /api/me/) a achava viva e a esticava por mais 2 h (login
 * ~239 min depois do último uso). Agora o relógio conta da última resposta do servidor a um
 * request desta aba (o fetchAPI avisa) e a pergunta chega depois do vencimento.
 *
 * Hook e fetchAPI reais; o servidor falso imita o Django.
 *
 * Rodada 5 (MÉDIA): com duas abas, cada uma contava só dos requests dela e perguntava 121 min
 * depois. A pergunta de uma achava a sessão viva por causa da outra e a renovava, e vice-versa:
 * com os últimos requests das duas separados por mais de ~2 min, nenhuma ia ao login, nunca.
 */
import { renderHook, act } from '@testing-library/react';
import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { ensureCsrfToken, fetchAPI, SERVIDOR_RESPONDEU } from '../../api/config';
import useSessionMonitor from '../useSessionMonitor';

const DUAS_HORAS_MS = 7200 * 1000;
const minutos = (): number => Date.now() / 60000;

/**
 * Servidor falso = Django: todo request atendido com sessão (status < 500) a renova por 2 h;
 * vencida, 403 NOT_AUTHENTICATED. O /api/csrf/ é aberto (AllowAny). Registra as renovações.
 */
function servidor(statusDoSalvar: number): { renovacoes: number[] } {
  let venceEm = Date.now() + DUAS_HORAS_MS;
  const renovacoes: number[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const caminho = new URL(String(input), 'http://localhost').pathname;
      const viva = Date.now() < venceEm;
      if (viva) {
        venceEm = Date.now() + DUAS_HORAS_MS;
        renovacoes.push(minutos());
      }
      if (caminho === '/api/csrf/') return new Response(JSON.stringify({ csrfToken: 'tok' }), { status: 200 });
      if (!viva) {
        return new Response(JSON.stringify({ code: 'NOT_AUTHENTICATED', detail: 'Sem sessão.' }), { status: 403 });
      }
      if (caminho === '/api/solicitacoes/') {
        const corpo = statusDoSalvar === 400 ? { justificativa: ['Campo obrigatório.'] } : { id: 9 };
        return new Response(JSON.stringify(corpo), { status: statusDoSalvar });
      }
      return new Response(JSON.stringify({ id: 1 }), { status: 200 });
    }),
  );
  return { renovacoes };
}

async function passar(segundos: number): Promise<void> {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(segundos * 1000);
  });
}

async function tecla(): Promise<void> {
  await act(async () => {
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'a' }));
  });
}

/** Boot do App: o GET /api/me/ que acha o usuário vem antes do monitor existir. */
async function abrir(onExpired: () => void): Promise<void> {
  await act(async () => {
    await fetchAPI('/me/');
  });
  renderHook(() => useSessionMonitor(onExpired));
}

describe('useSessionMonitor — usa, salva e larga a aba (rodada 4)', () => {
  beforeEach(() => {
    vi.useFakeTimers({ now: 0 });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  test.each([
    { salvarEm: 3, status: 201 },
    { salvarEm: 25, status: 201 },
    { salvarEm: 3, status: 400 },
  ])(
    'usa até $salvarEm min, o salvar responde $status e a aba fica parada: login 120-122 min depois do último request',
    async ({ salvarEm, status }) => {
      const s = servidor(status);
      let loginEm: number | null = null;
      await abrir(() => {
        loginEm ??= minutos();
      });

      // Uma tecla por minuto (renova em segundo plano aos 10 e 20 min) e o salvar, que é o
      // último request: o 400 de validação também renova a sessão no Django.
      for (let m = 1; m < salvarEm; m++) {
        await passar(60);
        await tecla();
      }
      await passar(60);
      await act(async () => {
        window.dispatchEvent(new MouseEvent('mousedown'));
        await fetchAPI('/solicitacoes/', { method: 'POST', body: '{}' }).catch(() => undefined);
      });
      const ultimoRequest = minutos();

      for (let m = 0; m < 300 && loginEm === null; m++) await passar(60);

      expect(loginEm).not.toBeNull();
      const inatividade = (loginEm ?? 0) - ultimoRequest;
      expect(inatividade).toBeGreaterThanOrEqual(120);
      expect(inatividade).toBeLessThanOrEqual(122);
      // A aba parada não renovou a sessão nenhuma vez depois do último uso.
      expect(s.renovacoes.filter((t) => t > ultimoRequest)).toEqual([]);
    },
  );

  test('aviso aberto e um request desta aba atendido pelo servidor: o aviso fecha (a sessão foi renovada lá)', async () => {
    servidor(201);
    const { result } = renderHook(() => useSessionMonitor(vi.fn()));

    await passar(6960);
    expect(result.current.showWarning).toBe(true);

    await act(async () => {
      await fetchAPI('/notificacoes/'); // ex.: uma tela que atualiza sozinha
    });
    await passar(60);

    expect(result.current.showWarning).toBe(false);
    expect(result.current.timeLeft).toBeGreaterThan(7000);
  });
});

type Aba = 'A' | 'B';
/** Eventos que o monitor ouve no `window`: no navegador, cada aba tem o seu. */
const EVENTOS_DA_ABA = new Set<string>([SERVIDOR_RESPONDEU, 'mousedown', 'keydown', 'scroll', 'touchstart']);

/**
 * No jsdom as abas dividem um `window`. Os listeners desses eventos ficam com a aba que estava
 * montando, e cada evento só chega à aba que o originou: a de `emAba`. Fora dela, quem faz request
 * é só o monitor, na conferência de 60 s: as de A caem em minutos cheios e as de B, que abre 30 s
 * depois de um minuto cheio, no meio do minuto; a aba sai do horário. O localStorage fica um só,
 * como entre as abas da mesma origem.
 */
function isolarAbas(): { emAba: (aba: Aba, fn: () => unknown) => Promise<void>; montar: (aba: Aba, fn: () => void) => void } {
  let abaAtual: Aba | null = null;
  let ouvintes: Array<{ aba: Aba; tipo: string; l: EventListenerOrEventListenerObject }> = [];
  const add = window.addEventListener.bind(window);
  const remove = window.removeEventListener.bind(window);
  const dispatch = window.dispatchEvent.bind(window);
  vi.spyOn(window, 'addEventListener').mockImplementation(((tipo: string, l: EventListenerOrEventListenerObject, o?: AddEventListenerOptions) => {
    if (!EVENTOS_DA_ABA.has(tipo)) return add(tipo, l, o);
    if (!abaAtual) throw new Error(`listener de ${tipo} registrado fora de uma aba`);
    ouvintes.push({ aba: abaAtual, tipo, l });
  }) as typeof window.addEventListener);
  vi.spyOn(window, 'removeEventListener').mockImplementation(((tipo: string, l: EventListenerOrEventListenerObject, o?: EventListenerOptions) => {
    if (!EVENTOS_DA_ABA.has(tipo)) return remove(tipo, l, o);
    ouvintes = ouvintes.filter((x) => x.tipo !== tipo || x.l !== l);
  }) as typeof window.removeEventListener);
  vi.spyOn(window, 'dispatchEvent').mockImplementation((ev: Event) => {
    if (!EVENTOS_DA_ABA.has(ev.type)) return dispatch(ev);
    const origem = abaAtual ?? (Number.isInteger(minutos()) ? 'A' : 'B');
    for (const { aba, tipo, l } of ouvintes) {
      if (aba !== origem || tipo !== ev.type) continue;
      if (typeof l === 'function') l(ev);
      else l.handleEvent(ev);
    }
    return true;
  });
  return {
    emAba: async (aba, fn) => {
      abaAtual = aba;
      try {
        await act(async () => {
          await fn();
        });
        await passar(0);
      } finally {
        abaAtual = null;
      }
    },
    montar: (aba, fn) => {
      abaAtual = aba;
      try {
        fn();
      } finally {
        abaAtual = null;
      }
    },
  };
}

describe('useSessionMonitor — duas abas, cada uma com o seu window (rodada 5)', () => {
  beforeEach(() => {
    vi.useFakeTimers({ now: 0 });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  // B abre 30 s depois de um minuto cheio: as conferências de 60 s das duas abas ficam
  // desencontradas, como no navegador. A que vai ao login primeiro recarrega na tela de login,
  // que faz requests sem sessão (o /api/csrf/ responde 200): eles não podem recomeçar o relógio
  // da outra, nem o 403 da pergunta dela.
  test.each([
    { cenario: 'B aberta 60,5 min depois de A e ninguém usa', abreB: 60.5, usaAAte: 0 },
    { cenario: 'B aberta e largada, A usada (uma tecla por minuto) e salva aos 90 min', abreB: 0.5, usaAAte: 90 },
    { cenario: 'B aberta e largada, A usada e salva aos 45 min', abreB: 0.5, usaAAte: 45 },
  ])(
    '$cenario: as duas vão ao login 120-122 min depois do último uso, sem renovar a sessão depois dele',
    async ({ abreB, usaAAte }) => {
      const s = servidor(201);
      const abas = isolarAbas();
      const loginEm: Record<Aba, number | null> = { A: null, B: null };
      const desmontar: Partial<Record<Aba, () => void>> = {};
      const paraRecarregar = new Set<Aba>();
      /** Boot do App na aba: o GET /api/me/ que acha o usuário e o monitor montado depois. */
      const abrir = async (aba: Aba): Promise<void> => {
        await abas.emAba(aba, () => fetchAPI('/me/'));
        const aoExpirar = (): void => {
          loginEm[aba] ??= minutos();
          paraRecarregar.add(aba);
        };
        abas.montar(aba, () => {
          desmontar[aba] = renderHook(() => useSessionMonitor(aoExpirar)).unmount;
        });
      };
      /** O App recarrega na tela de login: sem monitor, o boot pergunta quem é e busca o CSRF. */
      const recarregarNoLogin = async (): Promise<void> => {
        for (const aba of paraRecarregar) {
          paraRecarregar.delete(aba);
          desmontar[aba]?.();
          await abas.emAba(aba, async () => {
            await fetchAPI('/me/').catch(() => undefined);
            await ensureCsrfToken(true);
          });
        }
      };

      await abrir('A');
      let ultimoUso = 0;
      for (let meios = 1; meios <= 2 * Math.max(abreB, usaAAte); meios++) {
        await passar(30);
        const m = meios / 2;
        if (m === abreB) {
          await abrir('B');
          ultimoUso = minutos();
        }
        if (Number.isInteger(m) && m <= usaAAte) {
          // Uma tecla (renova em segundo plano a cada 10 min) e, no último minuto, o salvar.
          await abas.emAba('A', async () => {
            window.dispatchEvent(new KeyboardEvent('keydown', { key: 'a' }));
            if (m === usaAAte) await fetchAPI('/solicitacoes/', { method: 'POST', body: '{}' });
          });
          ultimoUso = minutos();
        }
      }
      for (let meios = 0; meios < 1200 && (loginEm.A === null || loginEm.B === null); meios++) {
        await passar(30);
        await recarregarNoLogin();
      }

      const log = `renovações (min): ${s.renovacoes.map((t) => t.toFixed(1)).join(' ')}`;
      for (const aba of ['A', 'B'] as const) {
        expect(loginEm[aba], `aba ${aba} nunca foi ao login; ${log}`).not.toBeNull();
        const inatividade = (loginEm[aba] ?? 0) - ultimoUso;
        expect(inatividade, `aba ${aba}; ${log}`).toBeGreaterThanOrEqual(120);
        expect(inatividade, `aba ${aba}; ${log}`).toBeLessThanOrEqual(122);
      }
      // Nenhuma das duas renovou a sessão depois do último uso.
      expect(s.renovacoes.filter((t) => t > ultimoUso)).toEqual([]);
    },
  );
});
