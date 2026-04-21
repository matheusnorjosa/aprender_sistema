/**
 * datModule API client — exercised against MSW handlers (issue #849, phase 2).
 */
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { apiUrl } from '../../test/mocks/handlers';

vi.mock('../../services/syncChannel', () => ({
  syncChannel: { publish: vi.fn(), subscribe: vi.fn(() => () => {}) },
}));

import {
  createProdutoDAT,
  deleteProdutoDAT,
  getProdutoDAT,
  listProdutosDAT,
  updateCadastroEtapa,
  updateProdutoDAT,
} from '../datModule';

type RequestLog = { url: string; method: string; body?: unknown };

describe('datModule API (MSW)', () => {
  let requests: RequestLog[];

  beforeEach(() => {
    requests = [];
  });

  test('updateCadastroEtapa uses POST on /dat/cadastros/{id}/etapa/', async () => {
    const payload = { id: 7, etapa: 'chaves', status: 'concluido' };
    server.use(
      http.post(apiUrl('/dat/cadastros/7/etapa/'), async ({ request }) => {
        requests.push({ url: request.url, method: request.method, body: await request.json() });
        return HttpResponse.json(payload);
      }),
    );

    const response = await updateCadastroEtapa(7, 'chaves', 'concluido');

    expect(response).toEqual(payload);
    expect(requests).toHaveLength(1);
    expect(requests[0].body).toEqual({ etapa: 'chaves', status: 'concluido' });
  });

  test('produto endpoints use /produtos/ base path with expected methods', async () => {
    server.use(
      http.get(apiUrl('/produtos/'), ({ request }) => {
        requests.push({ url: request.url, method: 'GET' });
        return HttpResponse.json({ count: 0, results: [] });
      }),
      http.get(apiUrl('/produtos/5/'), ({ request }) => {
        requests.push({ url: request.url, method: 'GET' });
        return HttpResponse.json({ id: 5, nome: 'Produto X' });
      }),
      http.post(apiUrl('/produtos/'), async ({ request }) => {
        requests.push({ url: request.url, method: 'POST', body: await request.json() });
        return HttpResponse.json({ id: 6, nome: 'Produto Novo' }, { status: 201 });
      }),
      http.patch(apiUrl('/produtos/5/'), async ({ request }) => {
        requests.push({ url: request.url, method: 'PATCH', body: await request.json() });
        return HttpResponse.json({ id: 5, nome: 'Produto Atualizado' });
      }),
      http.delete(apiUrl('/produtos/5/'), ({ request }) => {
        requests.push({ url: request.url, method: 'DELETE' });
        // NOTE: see adminDAT.test.ts — fetchAPI doesn't handle 204 empty body,
        // so return {} with 200 for now.
        return HttpResponse.json({});
      }),
    );

    await listProdutosDAT({ search: 'abc' });
    await getProdutoDAT(5);
    await createProdutoDAT({ nome: 'Produto Novo' });
    await updateProdutoDAT(5, { nome: 'Produto Atualizado' });
    await deleteProdutoDAT(5);

    expect(requests).toHaveLength(5);
    expect(requests.map((r) => r.method)).toEqual(['GET', 'GET', 'POST', 'PATCH', 'DELETE']);
    expect(new URL(requests[0].url).searchParams.get('search')).toBe('abc');
    expect(requests[2].body).toEqual({ nome: 'Produto Novo' });
    expect(requests[3].body).toEqual({ nome: 'Produto Atualizado' });
  });
});
