/**
 * SEG-54: o service worker guardava no navegador as respostas de `/api/options/` e `/api/config/`, sem separar
 * por pessoa. O cache só era apagado no "Sair"; se a sessão vencia com o navegador fechado, quem entrava depois
 * no mesmo computador recebia, sem rede, as listas da pessoa anterior (por exemplo, os formadores do setor).
 *
 * Regra: o service worker não guarda nem serve resposta de API. Só páginas e arquivos estáticos.
 *
 * Roda o `public/sw.js` real num contexto isolado (vm) com um Cache Storage falso que registra o que entra.
 */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { runInNewContext } from 'node:vm';
import { describe, expect, test } from 'vitest';

type Evento = { waitUntil?: (p: Promise<unknown>) => void } & Record<string, unknown>;
type Handler = (event: Evento) => void;

const ORIGEM = 'https://aprendersistema.com.br';

interface Ambiente {
  handlers: Record<string, Handler>;
  /** nome do cache → URLs gravadas */
  gravados: Map<string, string[]>;
  rede: { online: boolean };
}

function carregarSw(cachesIniciais: Record<string, Record<string, string>> = {}): Ambiente {
  const handlers: Record<string, Handler> = {};
  const conteudo = new Map<string, Map<string, string>>(
    Object.entries(cachesIniciais).map(([nome, itens]) => [nome, new Map(Object.entries(itens))]),
  );
  const gravados = new Map<string, string[]>();
  const rede = { online: true };
  const urlDe = (req: unknown): string => (typeof req === 'string' ? req : (req as { url: string }).url);

  const contexto = {
    self: {
      addEventListener: (nome: string, fn: Handler) => {
        handlers[nome] = fn;
      },
      skipWaiting: () => undefined,
      clients: { claim: () => undefined },
    },
    caches: {
      match: (req: unknown) => {
        for (const itens of conteudo.values()) {
          const corpo = itens.get(urlDe(req));
          if (corpo !== undefined) return Promise.resolve(new Response(corpo));
        }
        return Promise.resolve(undefined);
      },
      open: (nome: string) => {
        if (!conteudo.has(nome)) conteudo.set(nome, new Map());
        return Promise.resolve({
          put: (req: unknown, resp: Response) => {
            gravados.set(nome, [...(gravados.get(nome) ?? []), urlDe(req)]);
            return resp.text().then((corpo) => void conteudo.get(nome)!.set(urlDe(req), corpo));
          },
          addAll: () => Promise.resolve(),
        });
      },
      keys: () => Promise.resolve([...conteudo.keys()]),
      delete: (nome: string) => Promise.resolve(conteudo.delete(nome)),
    },
    fetch: (req: unknown) =>
      rede.online
        ? Promise.resolve(new Response(JSON.stringify({ de: 'rede', url: urlDe(req) }), { status: 200 }))
        : Promise.reject(new TypeError('Failed to fetch')),
    Response,
    URL,
    console: { log: () => undefined, error: () => undefined },
  };
  runInNewContext(readFileSync(resolve(__dirname, '../../public/sw.js'), 'utf-8'), contexto);
  return { handlers, gravados, rede };
}

async function pedir(amb: Ambiente, caminho: string, mode = 'cors'): Promise<Response> {
  let resposta: Promise<Response> | undefined;
  amb.handlers.fetch!({
    request: { url: `${ORIGEM}${caminho}`, mode, method: 'GET' },
    respondWith: (p: Promise<Response>) => (resposta = p),
  });
  const r = await resposta!;
  await new Promise((ok) => setTimeout(ok, 0)); // deixa um `cache.put` sem await terminar
  return r;
}

async function ativar(amb: Ambiente): Promise<void> {
  let espera: Promise<unknown> = Promise.resolve();
  amb.handlers.activate!({ waitUntil: (p) => (espera = p) });
  await espera;
}

describe('service worker não guarda resposta de API (SEG-54)', () => {
  test.each(['/api/options/formadores-do-setor/', '/api/options/usuarios/', '/api/config/'])(
    'GET %s com 200 não grava nada no navegador',
    async (caminho) => {
      const amb = carregarSw();

      const r = await pedir(amb, caminho);

      expect(r.status).toBe(200);
      expect([...amb.gravados.values()].flat()).toEqual([]);
    },
  );

  test('sem rede, a lista que a pessoa anterior carregou não volta: vem o OFFLINE 503', async () => {
    const amb = carregarSw();
    await pedir(amb, '/api/options/formadores-do-setor/'); // a pessoa anterior, com rede
    amb.rede.online = false;

    const r = await pedir(amb, '/api/options/formadores-do-setor/'); // a pessoa seguinte, sem rede

    expect(r.status).toBe(503);
    expect(await r.json()).toEqual(expect.objectContaining({ error: expect.objectContaining({ code: 'OFFLINE' }) }));
  });

  test('cópia de API deixada por uma versão antiga não é servida', async () => {
    const amb = carregarSw({
      'aprender-v2-api-v4': { [`${ORIGEM}/api/options/formadores-do-setor/`]: '["formador da pessoa anterior"]' },
    });
    amb.rede.online = false;

    const r = await pedir(amb, '/api/options/formadores-do-setor/');

    expect(r.status).toBe(503);
  });

  test('ao ativar, apaga os caches de API de qualquer versão', async () => {
    const amb = carregarSw({
      'aprender-v2-api-v4': { [`${ORIGEM}/api/config/`]: '{}' },
      'aprender-v2-api-v5': { [`${ORIGEM}/api/config/`]: '{}' },
      'aprender-v2-static-v4': { [`${ORIGEM}/logo.svg`]: 'svg' },
    });

    await ativar(amb);
    amb.rede.online = false;

    expect((await pedir(amb, '/api/config/')).status).toBe(503);
    expect((await pedir(amb, '/logo.svg', 'no-cors')).status).toBe(503); // estático de versão antiga também sai
  });

  test('arquivo estático continua guardado e servido sem rede', async () => {
    const amb = carregarSw();
    await pedir(amb, '/assets/app.js', 'no-cors');
    amb.rede.online = false;

    const r = await pedir(amb, '/assets/app.js', 'no-cors');

    expect(r.status).toBe(200);
    expect([...amb.gravados.values()].flat()).toEqual([`${ORIGEM}/assets/app.js`]);
  });
});
