/**
 * deslocamentos API client — exercised against MSW handlers (issue #849, phase 2).
 */
import { beforeEach, describe, expect, test } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { apiUrl } from '../../test/mocks/handlers';

import {
  createDeslocamento,
  deleteDeslocamento,
  listDeslocamentos,
  listFormadoresDoSetor,
  updateDeslocamento,
} from '../deslocamentos';

type RequestLog = { url: string; method: string; body?: unknown };

describe('deslocamentos API (MSW)', () => {
  let requests: RequestLog[];

  beforeEach(() => {
    requests = [];
  });

  test('listDeslocamentos usa GET /deslocamentos/ com filtros na query', async () => {
    server.use(
      http.get(apiUrl('/deslocamentos/'), ({ request }) => {
        requests.push({ url: request.url, method: request.method });
        return HttpResponse.json({ count: 0, next: null, previous: null, results: [] });
      }),
    );

    await listDeslocamentos({
      usuario_id: 5,
      data_inicio: '2026-01-01',
      data_fim: '2026-01-31',
      origem: 'Fortaleza',
      destino: 'Sobral',
      page: 2,
    });

    expect(requests).toHaveLength(1);
    expect(requests[0].method).toBe('GET');
    const u = new URL(requests[0].url);
    expect(u.pathname).toBe('/api/deslocamentos/');
    expect(u.searchParams.get('usuario_id')).toBe('5');
    expect(u.searchParams.get('data_inicio')).toBe('2026-01-01');
    expect(u.searchParams.get('data_fim')).toBe('2026-01-31');
    expect(u.searchParams.get('origem')).toBe('Fortaleza');
    expect(u.searchParams.get('destino')).toBe('Sobral');
    expect(u.searchParams.get('page')).toBe('2');
  });

  test('listFormadoresDoSetor usa GET /options/formadores-do-setor/', async () => {
    server.use(
      http.get(apiUrl('/options/formadores-do-setor/'), ({ request }) => {
        requests.push({ url: request.url, method: request.method });
        return HttpResponse.json([{ id: 1, first_name: 'Ana', last_name: 'Silva' }]);
      }),
    );

    const result = await listFormadoresDoSetor();

    expect(result).toEqual([{ id: 1, first_name: 'Ana', last_name: 'Silva' }]);
    expect(requests).toHaveLength(1);
    expect(requests[0].method).toBe('GET');
    expect(new URL(requests[0].url).pathname).toBe('/api/options/formadores-do-setor/');
  });

  test('createDeslocamento faz POST /deslocamentos/ com o payload', async () => {
    const payload = {
      origem: 'Fortaleza',
      destino: 'Sobral',
      start_date: '2026-02-01',
      end_date: '2026-02-03',
      observacao: 'ida e volta',
    };
    server.use(
      http.post(apiUrl('/deslocamentos/'), async ({ request }) => {
        requests.push({ url: request.url, method: request.method, body: await request.json() });
        return HttpResponse.json({ id: 10, usuario: 5, usuario_nome: 'Ana', ...payload });
      }),
    );

    const record = await createDeslocamento(payload);

    expect(record.id).toBe(10);
    expect(requests).toHaveLength(1);
    expect(requests[0].method).toBe('POST');
    expect(new URL(requests[0].url).pathname).toBe('/api/deslocamentos/');
    expect(requests[0].body).toEqual(payload);
  });

  test('updateDeslocamento faz PUT /deslocamentos/{id}/ com o payload', async () => {
    const payload = {
      usuario: 5,
      origem: 'Sobral',
      destino: 'Fortaleza',
      start_date: '2026-03-01',
      end_date: '2026-03-02',
    };
    server.use(
      http.put(apiUrl('/deslocamentos/10/'), async ({ request }) => {
        requests.push({ url: request.url, method: request.method, body: await request.json() });
        return HttpResponse.json({ id: 10, usuario_nome: 'Ana', ...payload });
      }),
    );

    await updateDeslocamento(10, payload);

    expect(requests).toHaveLength(1);
    expect(requests[0].method).toBe('PUT');
    expect(new URL(requests[0].url).pathname).toBe('/api/deslocamentos/10/');
    expect(requests[0].body).toEqual(payload);
  });

  test('deleteDeslocamento faz DELETE /deslocamentos/{id}/ e resolve vazio', async () => {
    server.use(
      http.delete(apiUrl('/deslocamentos/10/'), ({ request }) => {
        requests.push({ url: request.url, method: request.method });
        return new HttpResponse(null, { status: 204 });
      }),
    );

    const result = await deleteDeslocamento(10);

    expect(result).toBeUndefined();
    expect(requests).toHaveLength(1);
    expect(requests[0].method).toBe('DELETE');
    expect(new URL(requests[0].url).pathname).toBe('/api/deslocamentos/10/');
  });

  test('createDeslocamento propaga a mensagem de erro do backend', async () => {
    server.use(
      http.post(apiUrl('/deslocamentos/'), () =>
        HttpResponse.json({ detail: 'end_date deve ser posterior a start_date' }, { status: 400 }),
      ),
    );

    await expect(
      createDeslocamento({
        origem: 'Fortaleza',
        destino: 'Sobral',
        start_date: '2026-02-03',
        end_date: '2026-02-01',
      }),
    ).rejects.toThrow('end_date deve ser posterior a start_date');
  });
});
