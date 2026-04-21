/**
 * gcal API client — exercised against MSW handlers (issue #849, phase 2).
 */
import { beforeEach, describe, expect, test } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { apiUrl } from '../../test/mocks/handlers';

import {
  buildDashboardEventsExportUrl,
  getAlertsSummary,
  getDashboardEventDetail,
  getDashboardMetrics,
  getDashboardSuccessRate,
  getDashboardTopInsights,
  getStatusSummary,
  listApprovedWithGCalStatus,
  listDashboardEvents,
  publishBatch,
  reapplyBatch,
  resyncBatch,
} from '../gcal';

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

describe('gcal API endpoints (MSW)', () => {
  let requests: RequestLog[];

  beforeEach(() => {
    requests = [];
  });

  test('getStatusSummary uses /gcal/status-summary/', async () => {
    server.use(captureGet('/gcal/status-summary/', { counts: {}, total: 0 }, requests));

    await getStatusSummary({ status: 'approved' });

    expect(requests).toHaveLength(1);
    const u = new URL(requests[0].url);
    expect(u.pathname).toBe('/api/gcal/status-summary/');
    expect(u.searchParams.get('status')).toBe('approved');
  });

  test('listApprovedWithGCalStatus uses /gcal/list/', async () => {
    server.use(
      captureGet('/gcal/list/', { count: 0, next: null, previous: null, results: [] }, requests),
    );

    await listApprovedWithGCalStatus({ q: 'teste' });

    expect(requests).toHaveLength(1);
    const u = new URL(requests[0].url);
    expect(u.pathname).toBe('/api/gcal/list/');
    expect(u.searchParams.get('q')).toBe('teste');
  });

  test('publishBatch posts to /gcal/publish-batch/', async () => {
    server.use(capturePost('/gcal/publish-batch/', { queued: 1, errors: [] }, requests));

    await publishBatch({ solicitacao_ids: [1], dry_run: true, apply_blocked: true });

    expect(requests).toHaveLength(1);
    expect(requests[0].body).toEqual({
      solicitacao_ids: [1],
      dry_run: true,
      apply_blocked: true,
    });
  });

  test('reapplyBatch posts to /gcal/dashboard/batch/reapply/', async () => {
    server.use(capturePost('/gcal/dashboard/batch/reapply/', { queued: 1, errors: [] }, requests));

    await reapplyBatch({ ids: [10], dry_run: false, apply_blocked: true });

    expect(requests).toHaveLength(1);
    expect(requests[0].body).toEqual({ ids: [10], dry_run: false, apply_blocked: true });
  });

  test('resyncBatch posts to /gcal/dashboard/batch/resync/', async () => {
    server.use(capturePost('/gcal/dashboard/batch/resync/', { queued: 1, errors: [] }, requests));

    await resyncBatch({ ids: [20], dry_run: true, apply_blocked: false });

    expect(requests).toHaveLength(1);
    expect(requests[0].body).toEqual({ ids: [20], dry_run: true, apply_blocked: false });
  });

  test('getDashboardMetrics uses /gcal/dashboard/metrics/', async () => {
    server.use(
      captureGet('/gcal/dashboard/metrics/', { counts: {}, recent_errors: [] }, requests),
    );

    await getDashboardMetrics({ start: '2026-01-01', end: '2026-01-31' });

    expect(requests).toHaveLength(1);
    const u = new URL(requests[0].url);
    expect(u.pathname).toBe('/api/gcal/dashboard/metrics/');
    expect(u.searchParams.get('start')).toBe('2026-01-01');
    expect(u.searchParams.get('end')).toBe('2026-01-31');
  });

  test('listDashboardEvents uses /gcal/dashboard/events/', async () => {
    server.use(
      captureGet(
        '/gcal/dashboard/events/',
        { count: 0, next: null, previous: null, results: [] },
        requests,
      ),
    );

    await listDashboardEvents({ page: 2, page_size: 50, status: 'ERROR' });

    expect(requests).toHaveLength(1);
    const u = new URL(requests[0].url);
    expect(u.pathname).toBe('/api/gcal/dashboard/events/');
    expect(u.searchParams.get('page')).toBe('2');
    expect(u.searchParams.get('page_size')).toBe('50');
    expect(u.searchParams.get('status')).toBe('ERROR');
  });

  test('getDashboardSuccessRate uses /gcal/dashboard/insights/success-rate/', async () => {
    server.use(
      captureGet(
        '/gcal/dashboard/insights/success-rate/',
        { rate: 0, published: 0, error: 0, pending: 0, none: 0 },
        requests,
      ),
    );

    await getDashboardSuccessRate({ start: '2026-02-01', end: '2026-02-28' });

    expect(requests).toHaveLength(1);
    const u = new URL(requests[0].url);
    expect(u.pathname).toBe('/api/gcal/dashboard/insights/success-rate/');
  });

  test('getDashboardTopInsights uses /gcal/dashboard/insights/top/', async () => {
    server.use(
      captureGet(
        '/gcal/dashboard/insights/top/',
        { items: [], metric: 'municipios', limit: 5 },
        requests,
      ),
    );

    await getDashboardTopInsights({ metric: 'municipios', limit: 5, start: '2026-02-01' });

    expect(requests).toHaveLength(1);
    const u = new URL(requests[0].url);
    expect(u.pathname).toBe('/api/gcal/dashboard/insights/top/');
    expect(u.searchParams.get('metric')).toBe('municipios');
    expect(u.searchParams.get('limit')).toBe('5');
  });

  test('getDashboardEventDetail uses event detail endpoint', async () => {
    server.use(captureGet('/gcal/dashboard/events/123/detail/', { id: 123 }, requests));

    await getDashboardEventDetail(123);

    expect(requests).toHaveLength(1);
    expect(new URL(requests[0].url).pathname).toBe('/api/gcal/dashboard/events/123/detail/');
  });

  test('getAlertsSummary uses alerts summary endpoint', async () => {
    server.use(
      captureGet(
        '/gcal/dashboard/alerts/summary/',
        { errors: 0, pending: 0, published: 0, none: 0 },
        requests,
      ),
    );

    await getAlertsSummary();

    expect(requests).toHaveLength(1);
    expect(new URL(requests[0].url).pathname).toBe('/api/gcal/dashboard/alerts/summary/');
  });

  test('buildDashboardEventsExportUrl builds API_BASE absolute url', () => {
    // Pure helper — no HTTP involved, stays as a unit test.
    const url = buildDashboardEventsExportUrl({
      export_format: 'csv',
      start: '2026-03-01',
      end: '2026-03-02',
      status: 'ERROR',
    });

    const parsed = new URL(url, 'http://localhost');
    expect(parsed.pathname).toBe('/api/gcal/dashboard/events/export/');
    expect(parsed.searchParams.get('export_format')).toBe('csv');
    expect(parsed.searchParams.get('start')).toBe('2026-03-01');
    expect(parsed.searchParams.get('end')).toBe('2026-03-02');
    expect(parsed.searchParams.get('status')).toBe('ERROR');
  });
});
