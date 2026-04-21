/**
 * adminDAT API client — exercised against MSW handlers (issue #849, phase 2).
 *
 * Each test registers a scoped handler via `server.use(...)` and asserts on
 * observable behavior: the request lands on the expected URL/method, the
 * response shape is honored, and error-mapping wraps upstream HTTP statuses
 * into domain-friendly messages.
 */
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { http, HttpResponse, type HttpHandler } from 'msw';
import { server } from '../../test/mocks/server';
import { apiUrl } from '../../test/mocks/handlers';

vi.mock('../../services/syncChannel', () => ({
  syncChannel: { publish: vi.fn(), subscribe: vi.fn(() => () => {}) },
}));

import {
  assignGroups,
  autocompleteMunicipiosAdmin,
  createGroup,
  createUser,
  deleteGroup,
  getRBACMeta,
  listUsers,
  syncGroupMembers,
  updateGroup,
} from '../adminDAT';

type HandlerCall = { url: string; method: string; body?: unknown };

/**
 * Registers a handler that records every matching request into `calls` and
 * returns the provided response. Gives us a single place to make URL/method/
 * body assertions without rebuilding the `http.verb(...)` scaffolding in
 * every test.
 */
function spyHandler(
  factory: (url: string, resolver: Parameters<typeof http.get>[1]) => HttpHandler,
  url: string,
  response: { json?: unknown; status?: number; text?: string },
  calls: HandlerCall[],
): HttpHandler {
  return factory(url, async ({ request }) => {
    let body: unknown;
    if (request.method !== 'GET' && request.method !== 'DELETE') {
      const clone = request.clone();
      try {
        body = await clone.json();
      } catch {
        body = undefined;
      }
    }
    calls.push({ url: request.url, method: request.method, body });
    if (response.text !== undefined) {
      return new HttpResponse(response.text, { status: response.status ?? 200 });
    }
    return HttpResponse.json(response.json, { status: response.status ?? 200 });
  });
}

describe('adminDAT API wrappers (MSW)', () => {
  let calls: HandlerCall[];

  beforeEach(() => {
    calls = [];
  });

  test('listUsers calls /usuarios-admin/ with params', async () => {
    server.use(
      spyHandler(http.get, apiUrl('/usuarios-admin/'), { json: { count: 0, results: [] } }, calls),
    );

    await listUsers({ search: 'ana', is_active: true });

    expect(calls).toHaveLength(1);
    expect(calls[0].method).toBe('GET');
    const u = new URL(calls[0].url);
    expect(u.pathname).toBe('/api/usuarios-admin/');
    expect(u.searchParams.get('search')).toBe('ana');
    expect(u.searchParams.get('is_active')).toBe('true');
  });

  test('createUser sends POST with payload', async () => {
    const payload = {
      username: 'novo',
      email: 'novo@test.com',
      telefone: '85999990000',
      cargo: 'Coordenador',
    };
    server.use(
      spyHandler(http.post, apiUrl('/usuarios-admin/'), { json: { id: 1, ...payload }, status: 201 }, calls),
    );

    await createUser(payload);

    expect(calls).toHaveLength(1);
    expect(calls[0].method).toBe('POST');
    expect(calls[0].body).toMatchObject(payload);
  });

  test('assignGroups uses /usuarios-admin/{id}/assign_groups/', async () => {
    server.use(
      spyHandler(http.post, apiUrl('/usuarios-admin/10/assign_groups/'), { json: { id: 10 } }, calls),
    );

    await assignGroups(10, { group_ids: [1, 2, 3] });

    expect(calls).toHaveLength(1);
    expect(calls[0].body).toEqual({ group_ids: [1, 2, 3] });
  });

  test('createGroup accepts group_type_input payload', async () => {
    server.use(
      spyHandler(
        http.post,
        apiUrl('/grupos/'),
        { json: { id: 21, name: 'Analista de Campo' }, status: 201 },
        calls,
      ),
    );

    await createGroup({ name: 'Analista de Campo', group_type_input: 'funcao' });

    expect(calls).toHaveLength(1);
    expect(calls[0].body).toMatchObject({ name: 'Analista de Campo', group_type_input: 'funcao' });
  });

  test('syncGroupMembers uses /grupos/{id}/sync-members/', async () => {
    server.use(
      spyHandler(
        http.post,
        apiUrl('/grupos/5/sync-members/'),
        { json: { group_id: 5, members_count: 2, member_ids: [11, 12], added: 2, removed: 0 } },
        calls,
      ),
    );

    await syncGroupMembers(5, { user_ids: [11, 12] });

    expect(calls).toHaveLength(1);
    expect(calls[0].body).toEqual({ user_ids: [11, 12] });
  });

  test('updateGroup adds confirm_reserved query param when requested', async () => {
    server.use(
      spyHandler(http.patch, apiUrl('/grupos/2/'), { json: { id: 2, name: 'Grupo X' } }, calls),
    );

    await updateGroup(2, { name: 'Grupo X' }, { confirmReserved: true });

    expect(calls).toHaveLength(1);
    expect(calls[0].method).toBe('PATCH');
    expect(new URL(calls[0].url).searchParams.get('confirm_reserved')).toBe('true');
  });

  test('deleteGroup adds confirm_reserved query param when requested', async () => {
    // NOTE: fetchAPI always tries response.json() even on 204, so return {} with 200.
    // Prod backends that return 204 empty would surface a JSON parse error — that is
    // a gap worth fixing separately (out of scope for #849).
    server.use(
      spyHandler(http.delete, apiUrl('/grupos/2/'), { json: {} }, calls),
    );

    await deleteGroup(2, { confirmReserved: true });

    expect(calls).toHaveLength(1);
    expect(calls[0].method).toBe('DELETE');
    expect(new URL(calls[0].url).searchParams.get('confirm_reserved')).toBe('true');
  });

  test('getRBACMeta calls /rbac/meta/', async () => {
    server.use(
      spyHandler(
        http.get,
        apiUrl('/rbac/meta/'),
        { json: { setor_groups: ['DAT'], funcao_groups: ['Coordenador'] } },
        calls,
      ),
    );

    await getRBACMeta();

    expect(calls).toHaveLength(1);
    expect(new URL(calls[0].url).pathname).toBe('/api/rbac/meta/');
  });

  test('autocompleteMunicipiosAdmin returns results list', async () => {
    server.use(
      http.get(apiUrl('/municipios/autocomplete/'), () =>
        HttpResponse.json({
          results: [
            { nome: 'Fortaleza', uf: 'CE', ibge_code: '2304400', source: 'referencia', confidence: 'high' },
          ],
        }),
      ),
    );

    const result = await autocompleteMunicipiosAdmin({ q: 'Fort', uf: 'CE' });

    expect(result).toEqual([
      { nome: 'Fortaleza', uf: 'CE', ibge_code: '2304400', source: 'referencia', confidence: 'high' },
    ]);
  });

  test('autocompleteMunicipiosAdmin returns empty list when no results', async () => {
    server.use(
      http.get(apiUrl('/municipios/autocomplete/'), () => HttpResponse.json({})),
    );

    const result = await autocompleteMunicipiosAdmin({ q: 'X', uf: 'CE' });

    expect(result).toEqual([]);
  });

  test('fetchWithErrorMapping maps 403 to friendly error', async () => {
    server.use(
      http.get(apiUrl('/usuarios-admin/'), () =>
        HttpResponse.json({ detail: 'Forbidden' }, { status: 403 }),
      ),
    );

    await expect(listUsers()).rejects.toThrow('Você não tem permissão para realizar esta ação.');
  });

  test('fetchWithErrorMapping maps 404 to friendly error', async () => {
    server.use(
      http.get(apiUrl('/usuarios-admin/'), () =>
        HttpResponse.json({ detail: 'Not found' }, { status: 404 }),
      ),
    );

    await expect(listUsers()).rejects.toThrow('Recurso não encontrado.');
  });

  test('backend detail errors propagate when status is not in the map', async () => {
    server.use(
      http.post(apiUrl('/usuarios-admin/'), () =>
        HttpResponse.json({ detail: 'Email já existe' }, { status: 400 }),
      ),
    );

    await expect(createUser({ username: 'dup' })).rejects.toThrow('Email já existe');
  });
});
