/**
 * Pilot for MSW-based API tests (#849).
 *
 * Instead of mocking `fetchAPI`/`buildUrl` at module level, we let the real
 * `fetchAPI` run and intercept the HTTP call with MSW. The test then asserts
 * on observable behavior (request URL hit, response shape honored) rather
 * than on implementation details (how many times `fetchAPI` was called).
 *
 * See v2/docs/TESTING_MSW.md for the rollout guidance.
 */
import { beforeEach, describe, expect, test } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { apiUrl } from '../../test/mocks/handlers';
import { getMe } from '../availability';

const validCurrentUserPayload = {
  id: 1,
  username: 'admin',
  email: 'admin@test.com',
  first_name: 'Admin',
  last_name: 'User',
  name: 'Admin User',
  groups: ['DAT'],
  setores: ['DAT'],
  funcoes: ['Coordenador'],
  is_superuser: true,
  is_superintendencia: false,
  can_approve_super: true,
  permissions: ['pode_operar_dat'],
};

describe('availability API — getMe (MSW)', () => {
  beforeEach(() => {
    // Each test registers its own /me/ handler, so resetHandlers() between
    // tests (wired in setup.js) keeps scenarios isolated.
  });

  test('returns parsed user when /api/me/ payload matches contract', async () => {
    server.use(
      http.get(apiUrl('/me/'), () => HttpResponse.json(validCurrentUserPayload)),
    );

    const user = await getMe();

    expect(user).toEqual(validCurrentUserPayload);
  });

  test('throws when /api/me/ payload drifts from expected shape', async () => {
    server.use(
      http.get(apiUrl('/me/'), () =>
        HttpResponse.json({
          id: 1,
          username: 'admin',
          // missing mandatory contract fields
        }),
      ),
    );

    await expect(getMe()).rejects.toThrow('Invalid /api/me payload shape');
  });
});
