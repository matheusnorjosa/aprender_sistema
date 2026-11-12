/**
 * DEF-27 (relato do dono, 12/11/2026): com o servidor fora, abrir uma página mostrava o JSON
 * {"error":{"code":"OFFLINE",...}} em vez da página amigável `offline.html`. O service worker usava, para a
 * navegação, a mesma resposta de "offline" das chamadas à API.
 *
 * Roda o `public/sw.js` real num contexto isolado (vm) com `self`, `caches` e `fetch` falsos.
 */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { runInNewContext } from 'node:vm';
import { describe, expect, test } from 'vitest';

type Handler = (event: unknown) => void;

function carregarSw(): Handler {
  const handlers: Record<string, Handler> = {};
  const paginaOffline = new Response('<html>Você está sem conexão</html>', {
    headers: { 'Content-Type': 'text/html' },
  });
  const contexto = {
    self: {
      addEventListener: (nome: string, fn: Handler) => {
        handlers[nome] = fn;
      },
      skipWaiting: () => undefined,
      clients: { claim: () => undefined },
    },
    caches: {
      match: (req: unknown) => Promise.resolve(req === '/offline.html' ? paginaOffline.clone() : undefined),
      open: () => Promise.resolve({ put: () => undefined, addAll: () => Promise.resolve() }),
      keys: () => Promise.resolve([]),
      delete: () => Promise.resolve(true),
    },
    fetch: () => Promise.reject(new TypeError('Failed to fetch')),
    Response,
    URL,
    console: { log: () => undefined, error: () => undefined },
  };
  runInNewContext(readFileSync(resolve(__dirname, '../../public/sw.js'), 'utf-8'), contexto);
  return handlers.fetch!;
}

async function responder(fetchHandler: Handler, url: string, mode: string): Promise<Response> {
  let resposta: Promise<Response> | undefined;
  fetchHandler({ request: { url, mode, method: 'GET' }, respondWith: (p: Promise<Response>) => (resposta = p) });
  return resposta!;
}

describe('service worker sem conexão (DEF-27)', () => {
  test('abrir uma página mostra a página amigável offline.html, não o JSON da API', async () => {
    const r = await responder(carregarSw(), 'https://aprendersistema.com.br/home', 'navigate');

    expect(r.headers.get('Content-Type')).toContain('text/html');
    expect(await r.text()).toContain('sem conexão');
  });

  test('chamada à API continua recebendo o JSON OFFLINE com 503', async () => {
    const r = await responder(carregarSw(), 'https://aprendersistema.com.br/api/solicitacoes/', 'cors');

    expect(r.status).toBe(503);
    expect(await r.json()).toEqual(expect.objectContaining({ error: expect.objectContaining({ code: 'OFFLINE' }) }));
  });
});
