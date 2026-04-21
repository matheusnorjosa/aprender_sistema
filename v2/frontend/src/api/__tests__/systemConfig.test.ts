/**
 * systemConfig API client — exercised against MSW handlers (issue #849, phase 2).
 */
import { beforeEach, describe, expect, test } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { apiUrl } from '../../test/mocks/handlers';
import { getSystemConfig, updateSystemConfig } from '../systemConfig';

type RequestLog = { method: string; body?: unknown };

describe('systemConfig API wrappers (MSW)', () => {
  let requests: RequestLog[];

  beforeEach(() => {
    requests = [];
  });

  test('getSystemConfig calls /config/', async () => {
    server.use(
      http.get(apiUrl('/config/'), ({ request }) => {
        requests.push({ method: request.method });
        return HttpResponse.json({ TRAVEL_BUFFER_MINUTES: 120 });
      }),
    );

    const result = await getSystemConfig();

    expect(result).toEqual({ TRAVEL_BUFFER_MINUTES: 120 });
    expect(requests).toHaveLength(1);
    expect(requests[0].method).toBe('GET');
  });

  test('updateSystemConfig sends PUT /config/ with JSON body', async () => {
    const payload = { TRAVEL_BUFFER_MINUTES: 90 };
    server.use(
      http.put(apiUrl('/config/'), async ({ request }) => {
        requests.push({ method: request.method, body: await request.json() });
        return HttpResponse.json(payload);
      }),
    );

    const result = await updateSystemConfig(payload);

    expect(result).toEqual(payload);
    expect(requests).toHaveLength(1);
    expect(requests[0].method).toBe('PUT');
    expect(requests[0].body).toEqual(payload);
  });
});
