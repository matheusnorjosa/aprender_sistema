/**
 * Tests for useSessionMonitor hook.
 * Migrated from axios mock to fetchAPI mock (Epic #1039)
 */

import { renderHook, act } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';

const fetchAPIMock = vi.hoisted(() => vi.fn());

vi.mock('../../api/config', async (importOriginal) => {
  const actual = await importOriginal();
  return { ...actual, fetchAPI: fetchAPIMock };
});

import useSessionMonitor from '../useSessionMonitor';

/** Adianta o relógio e deixa as promessas do monitor (pergunta ao servidor) resolverem. */
async function passar(segundos: number): Promise<void> {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(segundos * 1000);
  });
}

/** Servidor falso: `/me/` responde conforme a sessão; o ping renova. */
function servidor(estado: { viva: boolean }): void {
  fetchAPIMock.mockImplementation((url: string) => {
    if (!estado.viva) {
      return Promise.reject({ status: 403, response: { status: 403, data: { code: 'NOT_AUTHENTICATED' } } });
    }
    return Promise.resolve(url === '/auth/ping/' ? { session_age: 7200 } : { id: 1 });
  });
}

const chamadasAoMe = (): number => fetchAPIMock.mock.calls.filter(([url]) => url === '/me/').length;

/** Servidor falso que imita o Django: a sessão vence 2 h depois do último request. */
function servidorComValidade(): { viva: () => boolean } {
  let venceEm = Date.now() + 7200 * 1000;
  fetchAPIMock.mockImplementation((url: string) => {
    if (Date.now() >= venceEm) {
      return Promise.reject({ status: 403, response: { status: 403, data: { code: 'NOT_AUTHENTICATED' } } });
    }
    venceEm = Date.now() + 7200 * 1000;
    return Promise.resolve(url === '/auth/ping/' ? { session_age: 7200 } : { id: 1 });
  });
  return { viva: () => Date.now() < venceEm };
}

/** Uma tecla a cada 30 s, sem nenhum request da tela; devolve se o aviso apareceu. */
async function digitarPor(minutos: number, aviso: () => boolean): Promise<boolean> {
  let avisoVisto = false;
  for (let s = 0; s < minutos * 60; s += 30) {
    await act(async () => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'a' }));
    });
    await passar(30);
    avisoVisto ||= aviso();
  }
  return avisoVisto;
}

describe('useSessionMonitor', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('initializes with default values', () => {
    const { result } = renderHook(() => useSessionMonitor(vi.fn()));

    expect(result.current.sessionAge).toBe(7200);
    expect(result.current.showWarning).toBe(false);
    expect(result.current.timeLeft).toBeGreaterThan(0);
  });

  it('calculates timeLeft correctly', () => {
    const { result } = renderHook(() => useSessionMonitor(vi.fn()));

    expect(result.current.timeLeft).toBeLessThanOrEqual(7200);
    expect(result.current.timeLeft).toBeGreaterThan(7100);
  });

  it('renewSession updates session and returns true on success', async () => {
    fetchAPIMock.mockResolvedValue({ session_age: 7200 });

    const { result } = renderHook(() => useSessionMonitor(vi.fn()));

    let success;
    await act(async () => {
      success = await result.current.renewSession();
    });

    expect(success).toBe(true);
    expect(fetchAPIMock).toHaveBeenCalledWith('/auth/ping/', { method: 'POST' });
    expect(result.current.showWarning).toBe(false);
  });

  it('renewSession returns false on API error', async () => {
    fetchAPIMock.mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => useSessionMonitor(vi.fn()));

    let success;
    await act(async () => {
      success = await result.current.renewSession();
    });

    expect(success).toBe(false);
  });

  // O servidor disse que não há sessão: o App leva ao login (sem POST de logout).
  it('renewSession com 401 chama onExpired, sem mandar para /login', async () => {
    const onExpired = vi.fn();
    const hrefAntes = window.location.href;
    fetchAPIMock.mockRejectedValue({ response: { status: 401 } });

    const { result } = renderHook(() => useSessionMonitor(onExpired));

    let success;
    await act(async () => {
      success = await result.current.renewSession();
    });

    expect(success).toBe(false);
    expect(onExpired).toHaveBeenCalledTimes(1);
    expect(window.location.href).toBe(hrefAntes);
  });

  it('renewSession com erro de rede não encerra a sessão', async () => {
    const onExpired = vi.fn();
    fetchAPIMock.mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => useSessionMonitor(onExpired));

    await act(async () => {
      await result.current.renewSession();
    });

    expect(onExpired).not.toHaveBeenCalled();
  });

  // Auditoria UX 30/09, rodada 2 (MÉDIA): "Continuar logado" sem rede ou com 5xx era clique
  // mudo. O motivo fica em renewError (o aviso mostra) e some quando a renovação dá certo.
  it('renewSession sem rede guarda o motivo em renewError', async () => {
    fetchAPIMock.mockRejectedValue(new TypeError('Failed to fetch'));
    const { result } = renderHook(() => useSessionMonitor(vi.fn()));

    await act(async () => {
      await result.current.renewSession();
    });

    expect(result.current.renewError).toBe('Sem conexão com o servidor.');
  });

  it('renewSession com 5xx guarda a mensagem do servidor e limpa quando renova', async () => {
    fetchAPIMock.mockRejectedValueOnce(
      Object.assign(new Error('HTTP 502: Bad Gateway'), { status: 502, response: { status: 502 } }),
    );
    const { result } = renderHook(() => useSessionMonitor(vi.fn()));

    await act(async () => {
      await result.current.renewSession();
    });
    expect(result.current.renewError).toBe('HTTP 502: Bad Gateway');

    fetchAPIMock.mockResolvedValueOnce({ session_age: 7200 });
    await act(async () => {
      await result.current.renewSession();
    });
    expect(result.current.renewError).toBeNull();
  });

  // Auditoria UX 30/09, rodada 2 (ALTA): o relógio local é de cada aba, mas a sessão é do
  // navegador. Zerar o relógio de uma aba ociosa não encerra nada: pergunta ao servidor.
  it('relógio zerado e sessão viva no servidor: recomeça o relógio, sem encerrar', async () => {
    const onExpired = vi.fn();
    servidor({ viva: true });
    const { result } = renderHook(() => useSessionMonitor(onExpired));

    await passar(7260);

    expect(fetchAPIMock).toHaveBeenCalledWith('/me/');
    expect(onExpired).not.toHaveBeenCalled();
    expect(result.current.showWarning).toBe(false);
    expect(result.current.timeLeft).toBeGreaterThan(7100);
  });

  it('relógio zerado e servidor sem sessão (403): chama onExpired uma vez', async () => {
    const onExpired = vi.fn();
    servidor({ viva: false });
    const hrefAntes = window.location.href;
    renderHook(() => useSessionMonitor(onExpired));

    await passar(7260);

    expect(onExpired).toHaveBeenCalledTimes(1);
    expect(window.location.href).toBe(hrefAntes);
  });

  it('relógio zerado e servidor fora do ar: não encerra e pergunta de novo no minuto seguinte', async () => {
    const onExpired = vi.fn();
    fetchAPIMock.mockRejectedValue(new TypeError('Failed to fetch'));
    renderHook(() => useSessionMonitor(onExpired));

    await passar(7260);
    expect(chamadasAoMe()).toBe(1);
    await passar(60);

    expect(chamadasAoMe()).toBe(2);
    expect(onExpired).not.toHaveBeenCalled();
  });

  // A pergunta renova a sessão no servidor (SESSION_SAVE_EVERY_REQUEST). No zero exato, a
  // sessão de uma aba sozinha ainda não venceu lá (o último request veio depois do último
  // clique) e a pergunta a esticaria por mais 2 h: pergunta um minuto depois.
  it('só pergunta ao servidor um minuto depois do zero local', async () => {
    servidor({ viva: false });
    renderHook(() => useSessionMonitor(vi.fn()));

    await passar(7200);
    expect(chamadasAoMe()).toBe(0);
    await passar(60);
    expect(chamadasAoMe()).toBe(1);
  });

  // Rodada 5: o horário da última resposta do servidor é comum às abas (localStorage). A ociosa vê
  // a renovação da outra e nem pergunta; sem esse horário, a pergunta decide (testes acima).
  it('duas abas: a ociosa vê a renovação da que está em uso, não pergunta e não derruba a sessão', async () => {
    const estado = { viva: true };
    servidor(estado);
    const expirouA = vi.fn();
    const expirouB = vi.fn();

    const abaA = renderHook(() => useSessionMonitor(expirouA));
    await passar(3600);
    const abaB = renderHook(() => useSessionMonitor(expirouB)); // em uso 1 h depois
    await passar(3660 + 60);

    expect(chamadasAoMe()).toBe(0);
    expect(expirouA).not.toHaveBeenCalled();
    expect(expirouB).not.toHaveBeenCalled();
    expect(estado.viva).toBe(true);
    expect(abaA.result.current.showWarning).toBe(false);
    // Conta da renovação na outra aba (1 h depois da abertura desta): 7200 - 3720 = 3480 s.
    expect(abaA.result.current.timeLeft).toBe(3480);
    expect(abaB.result.current.showWarning).toBe(false);
  });

  // Auditoria UX 30/09 (ALTA): o mousedown no "Sair agora" contava como atividade e
  // fechava o aviso antes do click — o botão não fazia nada. Com o aviso aberto, só a
  // escolha explícita ("Continuar logado" ou "Sair agora") o fecha.
  // Rodada 2 (MÉDIA): e a atividade também não mexe no relógio — antes, um Tab até o botão
  // fazia o aviso "prestes a expirar" mostrar 120:00.
  it('atividade com o aviso aberto não fecha o aviso nem mexe no relógio', async () => {
    const { result } = renderHook(() => useSessionMonitor(vi.fn()));

    await passar(6960);
    expect(result.current.showWarning).toBe(true);
    expect(result.current.timeLeft).toBe(240);

    await act(async () => {
      window.dispatchEvent(new MouseEvent('mousedown'));
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab' }));
    });

    expect(result.current.showWarning).toBe(true);
    expect(result.current.timeLeft).toBe(240);
  });

  it('shows warning when time left is below threshold', async () => {
    const { result } = renderHook(() => useSessionMonitor(vi.fn()));

    await passar(6960);

    expect(result.current.showWarning).toBe(true);
  });

  // Rodada 3 (BAIXA): a contagem ficava parada em 5:00 até o aviso sumir.
  it('com o aviso aberto, a contagem anda segundo a segundo', async () => {
    const { result } = renderHook(() => useSessionMonitor(vi.fn()));

    await passar(6900);
    expect(result.current.showWarning).toBe(true);
    expect(result.current.timeLeft).toBe(300);

    await passar(1);
    expect(result.current.timeLeft).toBe(299);
    await passar(10);
    expect(result.current.timeLeft).toBe(289);
  });

  // Rodada 3 (MÉDIA): digitar e rolar não fazem request. A sessão vencia no servidor 2 h
  // depois do último request, sem aviso, e o próximo salvar caía no login perdendo o
  // formulário. A atividade renova a sessão no servidor (GET /api/me/, no máximo a cada
  // 10 min); o limite de 2 h passa a valer para inatividade real.
  it('digitando sem parar por mais de 2 h: a sessão segue viva no servidor e o aviso não aparece', async () => {
    const onExpired = vi.fn();
    const servidor = servidorComValidade();
    const { result } = renderHook(() => useSessionMonitor(onExpired));

    const avisoVisto = await digitarPor(130, () => result.current.showWarning);

    expect(servidor.viva()).toBe(true);
    expect(avisoVisto).toBe(false);
    expect(onExpired).not.toHaveBeenCalled();
  });

  it('parado por mais de 2 h: a sessão vence no servidor e a pergunta leva ao login', async () => {
    const onExpired = vi.fn();
    const servidor = servidorComValidade();
    renderHook(() => useSessionMonitor(onExpired));

    await passar(7260);

    expect(servidor.viva()).toBe(false);
    expect(onExpired).toHaveBeenCalledTimes(1);
  });

  it('a atividade renova a sessão no servidor no máximo a cada 10 min', async () => {
    servidorComValidade();
    renderHook(() => useSessionMonitor(vi.fn()));

    await digitarPor(25, () => false);

    expect(chamadasAoMe()).toBe(2); // aos 10 e aos 20 min
    expect(fetchAPIMock).not.toHaveBeenCalledWith('/auth/logout/', expect.anything());
  });

  it('uma rajada de atividade com a renovação em andamento faz um request só', async () => {
    fetchAPIMock.mockImplementation(() => new Promise(() => {})); // nunca responde
    renderHook(() => useSessionMonitor(vi.fn()));
    await passar(600);

    await act(async () => {
      for (let i = 0; i < 5; i++) window.dispatchEvent(new MouseEvent('mousedown'));
    });

    expect(chamadasAoMe()).toBe(1);
  });

  it('atividade sem conseguir renovar (sem rede) não esconde o aviso: a sessão vai vencer', async () => {
    const onExpired = vi.fn();
    fetchAPIMock.mockRejectedValue(new TypeError('Sem conexão com o servidor.'));
    const { result } = renderHook(() => useSessionMonitor(onExpired));

    const avisoVisto = await digitarPor(116, () => result.current.showWarning);

    expect(avisoVisto).toBe(true);
    expect(result.current.renewError).toBeNull(); // a renovação em segundo plano não mostra nada
    expect(onExpired).not.toHaveBeenCalled();
  });
});
