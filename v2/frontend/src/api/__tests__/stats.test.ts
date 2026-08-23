/**
 * stats API client — exercised against MSW handlers (issue #849, phase 2).
 */
import { beforeEach, describe, expect, test } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { apiUrl } from '../../test/mocks/handlers';

import { getHomeStats } from '../stats';

type RequestLog = { url: string; method: string };

describe('stats API (MSW)', () => {
  let requests: RequestLog[];

  beforeEach(() => {
    requests = [];
  });

  test('getHomeStats usa GET em /stats/home/', async () => {
    const payload = { pending_approvals: 3, upcoming_events: 5, my_requests: 2 };
    server.use(
      http.get(apiUrl('/stats/home/'), ({ request }) => {
        requests.push({ url: request.url, method: request.method });
        return HttpResponse.json(payload);
      }),
    );

    const response = await getHomeStats();

    expect(response).toEqual(payload);
    expect(requests).toHaveLength(1);
    expect(requests[0].method).toBe('GET');
    expect(new URL(requests[0].url).pathname).toBe('/api/stats/home/');
  });

  test('getHomeStats propaga a mensagem de erro do backend', async () => {
    server.use(
      http.get(apiUrl('/stats/home/'), () =>
        HttpResponse.json({ detail: 'Falha ao calcular estatísticas.' }, { status: 500 }),
      ),
    );

    await expect(getHomeStats()).rejects.toThrow('Falha ao calcular estatísticas.');
  });
});
