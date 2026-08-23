/**
 * me API client — exercised against MSW handlers (issue #849, phase 2).
 */
import { beforeEach, describe, expect, test } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { apiUrl } from '../../test/mocks/handlers';

import {
  changeMyPassword,
  exportMyData,
  getMyEvents,
  getMyPolicies,
  updateMyContact,
} from '../me';

type RequestLog = { url: string; method: string; body?: unknown };

describe('me API (MSW)', () => {
  let requests: RequestLog[];

  beforeEach(() => {
    requests = [];
  });

  test('getMyEvents lista /me/events/ com paginação', async () => {
    const payload = { count: 0, next: null, previous: null, results: [] };
    server.use(
      http.get(apiUrl('/me/events/'), ({ request }) => {
        requests.push({ url: request.url, method: request.method });
        return HttpResponse.json(payload);
      }),
    );

    const response = await getMyEvents({ page: 2, page_size: 50 });

    expect(response).toEqual(payload);
    expect(requests).toHaveLength(1);
    const u = new URL(requests[0].url);
    expect(u.pathname).toBe('/api/me/events/');
    expect(requests[0].method).toBe('GET');
    expect(u.searchParams.get('page')).toBe('2');
    expect(u.searchParams.get('page_size')).toBe('50');
  });

  test('getMyPolicies usa GET /me/policies/', async () => {
    const payload = ['ver_dashboard', 'aprovar_solicitacao'];
    server.use(
      http.get(apiUrl('/me/policies/'), ({ request }) => {
        requests.push({ url: request.url, method: request.method });
        return HttpResponse.json(payload);
      }),
    );

    const response = await getMyPolicies();

    expect(response).toEqual(payload);
    expect(requests).toHaveLength(1);
    expect(new URL(requests[0].url).pathname).toBe('/api/me/policies/');
    expect(requests[0].method).toBe('GET');
  });

  test('changeMyPassword faz POST em /me/change-password/', async () => {
    const payload = { old_password: 'antiga123', new_password: 'nova456' };
    server.use(
      http.post(apiUrl('/me/change-password/'), async ({ request }) => {
        requests.push({
          url: request.url,
          method: request.method,
          body: await request.json(),
        });
        return HttpResponse.json({ detail: 'Senha alterada com sucesso.' });
      }),
    );

    const response = await changeMyPassword(payload);

    expect(response).toEqual({ detail: 'Senha alterada com sucesso.' });
    expect(requests).toHaveLength(1);
    expect(new URL(requests[0].url).pathname).toBe('/api/me/change-password/');
    expect(requests[0].method).toBe('POST');
    expect(requests[0].body).toEqual(payload);
  });

  test('updateMyContact faz PATCH em /me/ só com telefone', async () => {
    const payload = { telefone: '85999990000' };
    server.use(
      http.patch(apiUrl('/me/'), async ({ request }) => {
        requests.push({
          url: request.url,
          method: request.method,
          body: await request.json(),
        });
        return HttpResponse.json({ id: 1, telefone: '85999990000' });
      }),
    );

    const response = await updateMyContact(payload);

    expect(response).toEqual({ id: 1, telefone: '85999990000' });
    expect(requests).toHaveLength(1);
    expect(new URL(requests[0].url).pathname).toBe('/api/me/');
    expect(requests[0].method).toBe('PATCH');
    expect(requests[0].body).toEqual(payload);
  });

  test('exportMyData baixa Blob de /me/export/', async () => {
    server.use(
      http.get(apiUrl('/me/export/'), ({ request }) => {
        requests.push({ url: request.url, method: request.method });
        return HttpResponse.json({ titular: 'dossie' });
      }),
    );

    const blob = await exportMyData();

    // O ambiente de teste tem dois construtores Blob (undici do fetch vs jsdom),
    // então `instanceof Blob` é frágil cross-realm — asserta o shape do Blob.
    expect(blob.size).toBeGreaterThan(0);
    expect(typeof blob.arrayBuffer).toBe('function');
    expect(requests).toHaveLength(1);
    expect(new URL(requests[0].url).pathname).toBe('/api/me/export/');
    expect(requests[0].method).toBe('GET');
  });

  test('changeMyPassword propaga mensagem de erro do backend', async () => {
    server.use(
      http.post(apiUrl('/me/change-password/'), () =>
        HttpResponse.json({ detail: 'Senha atual incorreta.' }, { status: 400 }),
      ),
    );

    await expect(
      changeMyPassword({ old_password: 'errada', new_password: 'nova456' }),
    ).rejects.toThrow('Senha atual incorreta.');
  });

  test('exportMyData lança em resposta não-ok', async () => {
    server.use(
      http.get(apiUrl('/me/export/'), () =>
        HttpResponse.json({ detail: 'erro' }, { status: 500 }),
      ),
    );

    await expect(exportMyData()).rejects.toThrow('Export failed: HTTP 500');
  });
});
