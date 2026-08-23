/**
 * solicitacoes API client — exercised against MSW handlers.
 */
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { apiUrl } from '../../test/mocks/handlers';

vi.mock('../../services/syncChannel', () => ({
  syncChannel: { publish: vi.fn(), subscribe: vi.fn(() => () => {}) },
}));

import {
  approveSolicitacao,
  approveSolicitacoesBatch,
  cancelSolicitacao,
  createSolicitacao,
  deleteSolicitacao,
  getSolicitacao,
  listSolicitacoes,
  previewSolicitacao,
  publishSolicitacao,
  rejectSolicitacao,
  rejectSolicitacoesBatch,
  resyncSolicitacao,
  updateSolicitacao,
} from '../solicitacoes';

type RequestLog = { url: string; method: string; body?: unknown };

function captureGet(path: string, payload: unknown, log: RequestLog[]) {
  return http.get(apiUrl(path), ({ request }) => {
    log.push({ url: request.url, method: 'GET' });
    return HttpResponse.json(payload);
  });
}

function capturePost(path: string, payload: unknown, log: RequestLog[]) {
  return http.post(apiUrl(path), async ({ request }) => {
    log.push({ url: request.url, method: 'POST', body: await request.json() });
    return HttpResponse.json(payload);
  });
}

function capturePatch(path: string, payload: unknown, log: RequestLog[]) {
  return http.patch(apiUrl(path), async ({ request }) => {
    log.push({ url: request.url, method: 'PATCH', body: await request.json() });
    return HttpResponse.json(payload);
  });
}

function captureDelete(path: string, log: RequestLog[]) {
  return http.delete(apiUrl(path), ({ request }) => {
    log.push({ url: request.url, method: 'DELETE' });
    return new HttpResponse(null, { status: 204 });
  });
}

describe('solicitacoes API (MSW)', () => {
  let requests: RequestLog[];

  beforeEach(() => {
    requests = [];
  });

  test('listSolicitacoes usa GET e mapeia status inglês→pt', async () => {
    server.use(
      captureGet(
        '/solicitacoes/',
        { count: 0, next: null, previous: null, results: [] },
        requests,
      ),
    );

    await listSolicitacoes({ status: 'pending', q: 'sobral', page: 2, mine: 'true' });

    expect(requests).toHaveLength(1);
    const u = new URL(requests[0].url);
    expect(u.pathname).toBe('/api/solicitacoes/');
    expect(u.searchParams.get('status')).toBe('pendente');
    expect(u.searchParams.get('q')).toBe('sobral');
    expect(u.searchParams.get('page')).toBe('2');
    expect(u.searchParams.get('mine')).toBe('true');
  });

  test('createSolicitacao posta em /solicitacoes/ com body', async () => {
    const payload = { id: 1, status: 'pendente' };
    server.use(capturePost('/solicitacoes/', payload, requests));

    const body = {
      municipio: 3,
      projeto: 4,
      inicio: '2026-09-01T09:00:00-03:00',
      fim: '2026-09-01T11:00:00-03:00',
    };
    const response = await createSolicitacao(body);

    expect(response).toEqual(payload);
    expect(requests).toHaveLength(1);
    expect(new URL(requests[0].url).pathname).toBe('/api/solicitacoes/');
    expect(requests[0].method).toBe('POST');
    expect(requests[0].body).toEqual(body);
  });

  test('createSolicitacao propaga erro 400 com detail', async () => {
    server.use(
      http.post(apiUrl('/solicitacoes/'), () =>
        HttpResponse.json({ detail: 'Município é obrigatório.' }, { status: 400 }),
      ),
    );

    await expect(createSolicitacao({ projeto: 4 })).rejects.toThrow(
      'Município é obrigatório.',
    );
  });

  test('approveSolicitacao usa PATCH em approve/ com motivo', async () => {
    server.use(capturePatch('/solicitacoes/5/approve/', { id: 5, status: 'aprovado' }, requests));

    await approveSolicitacao(5, 'ok');

    expect(requests).toHaveLength(1);
    expect(new URL(requests[0].url).pathname).toBe('/api/solicitacoes/5/approve/');
    expect(requests[0].method).toBe('PATCH');
    expect(requests[0].body).toEqual({ reason: 'ok' });
  });

  test('approveSolicitacao sem motivo envia body vazio', async () => {
    server.use(capturePatch('/solicitacoes/6/approve/', { id: 6, status: 'aprovado' }, requests));

    await approveSolicitacao(6);

    expect(requests).toHaveLength(1);
    expect(requests[0].body).toEqual({});
  });

  test('rejectSolicitacao usa PATCH em reject/ com motivo', async () => {
    server.use(capturePatch('/solicitacoes/7/reject/', { id: 7, status: 'reprovado' }, requests));

    await rejectSolicitacao(7, 'fora de prazo');

    expect(requests).toHaveLength(1);
    expect(new URL(requests[0].url).pathname).toBe('/api/solicitacoes/7/reject/');
    expect(requests[0].method).toBe('PATCH');
    expect(requests[0].body).toEqual({ reason: 'fora de prazo' });
  });

  test('getSolicitacao usa GET no detalhe', async () => {
    server.use(captureGet('/solicitacoes/9/', { id: 9 }, requests));

    const response = await getSolicitacao(9);

    expect(response).toEqual({ id: 9 });
    expect(requests).toHaveLength(1);
    expect(requests[0].method).toBe('GET');
    expect(new URL(requests[0].url).pathname).toBe('/api/solicitacoes/9/');
  });

  test('updateSolicitacao usa PATCH no detalhe com body parcial', async () => {
    server.use(capturePatch('/solicitacoes/11/', { id: 11 }, requests));

    await updateSolicitacao(11, { observacoes: 'nova obs' });

    expect(requests).toHaveLength(1);
    expect(new URL(requests[0].url).pathname).toBe('/api/solicitacoes/11/');
    expect(requests[0].method).toBe('PATCH');
    expect(requests[0].body).toEqual({ observacoes: 'nova obs' });
  });

  test('deleteSolicitacao usa DELETE e retorna void em 204', async () => {
    server.use(captureDelete('/solicitacoes/13/', requests));

    const response = await deleteSolicitacao(13);

    expect(response).toBeUndefined();
    expect(requests).toHaveLength(1);
    expect(requests[0].method).toBe('DELETE');
    expect(new URL(requests[0].url).pathname).toBe('/api/solicitacoes/13/');
  });

  test('previewSolicitacao posta em preview-gcal/ com body vazio', async () => {
    server.use(
      capturePost(
        '/solicitacoes/15/preview-gcal/',
        { summary: '', description: '', start: {}, end: {}, attendees: [] },
        requests,
      ),
    );

    await previewSolicitacao(15);

    expect(requests).toHaveLength(1);
    expect(new URL(requests[0].url).pathname).toBe('/api/solicitacoes/15/preview-gcal/');
    expect(requests[0].method).toBe('POST');
    expect(requests[0].body).toEqual({});
  });

  test('publishSolicitacao posta em publish/ com opções', async () => {
    server.use(capturePost('/solicitacoes/17/publish/', { detail: 'ok', solicitacao_id: 17 }, requests));

    await publishSolicitacao(17, { dry_run: true, apply_blocked: false });

    expect(requests).toHaveLength(1);
    expect(new URL(requests[0].url).pathname).toBe('/api/solicitacoes/17/publish/');
    expect(requests[0].method).toBe('POST');
    expect(requests[0].body).toEqual({ dry_run: true, apply_blocked: false });
  });

  test('resyncSolicitacao posta em resync-gcal/ com body vazio', async () => {
    server.use(capturePost('/solicitacoes/19/resync-gcal/', { detail: 'ok', solicitacao_id: 19 }, requests));

    await resyncSolicitacao(19);

    expect(requests).toHaveLength(1);
    expect(new URL(requests[0].url).pathname).toBe('/api/solicitacoes/19/resync-gcal/');
    expect(requests[0].method).toBe('POST');
    expect(requests[0].body).toEqual({});
  });

  test('cancelSolicitacao posta em cancel-gcal/ com body vazio', async () => {
    server.use(capturePost('/solicitacoes/21/cancel-gcal/', { detail: 'ok', solicitacao_id: 21 }, requests));

    await cancelSolicitacao(21);

    expect(requests).toHaveLength(1);
    expect(new URL(requests[0].url).pathname).toBe('/api/solicitacoes/21/cancel-gcal/');
    expect(requests[0].method).toBe('POST');
    expect(requests[0].body).toEqual({});
  });

  test('approveSolicitacoesBatch posta em batch-approve/ com ids', async () => {
    server.use(capturePost('/solicitacoes/batch-approve/', { approved: 2, errors: [] }, requests));

    await approveSolicitacoesBatch([23, 24]);

    expect(requests).toHaveLength(1);
    expect(new URL(requests[0].url).pathname).toBe('/api/solicitacoes/batch-approve/');
    expect(requests[0].method).toBe('POST');
    expect(requests[0].body).toEqual({ ids: [23, 24] });
  });

  test('rejectSolicitacoesBatch posta em batch-reject/ com ids', async () => {
    server.use(capturePost('/solicitacoes/batch-reject/', { rejected: 1, errors: [] }, requests));

    await rejectSolicitacoesBatch([25]);

    expect(requests).toHaveLength(1);
    expect(new URL(requests[0].url).pathname).toBe('/api/solicitacoes/batch-reject/');
    expect(requests[0].method).toBe('POST');
    expect(requests[0].body).toEqual({ ids: [25] });
  });
});
