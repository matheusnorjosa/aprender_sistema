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

import { updateCadastroEtapa } from '../datModule';

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
});
