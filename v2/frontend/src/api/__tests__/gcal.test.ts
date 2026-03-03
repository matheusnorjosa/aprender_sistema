import { beforeEach, describe, expect, test, vi } from 'vitest';

const { fetchAPIMock, buildUrlMock } = vi.hoisted(() => ({
  fetchAPIMock: vi.fn(),
  buildUrlMock: vi.fn(),
}));

vi.mock('../config', () => ({
  fetchAPI: fetchAPIMock,
  buildUrl: buildUrlMock,
  API_BASE: '/api',
}));

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

describe('gcal API endpoints', () => {
  beforeEach(() => {
    fetchAPIMock.mockReset();
    buildUrlMock.mockReset();
    buildUrlMock.mockImplementation((path: string) => path);
  });

  test('getStatusSummary uses /gcal/status-summary/', async () => {
    fetchAPIMock.mockResolvedValue({ counts: {}, total: 0 });

    await getStatusSummary({ status: 'approved' });

    expect(buildUrlMock).toHaveBeenCalledWith('/gcal/status-summary/', { status: 'approved' });
    expect(fetchAPIMock).toHaveBeenCalledWith('/gcal/status-summary/');
  });

  test('listApprovedWithGCalStatus uses /gcal/list/ (implemented backend endpoint)', async () => {
    fetchAPIMock.mockResolvedValue({ count: 0, next: null, previous: null, results: [] });

    await listApprovedWithGCalStatus({ q: 'teste' });

    expect(buildUrlMock).toHaveBeenCalledWith('/gcal/list/', { q: 'teste' });
    expect(fetchAPIMock).toHaveBeenCalledWith('/gcal/list/');
  });

  test('publishBatch posts to /gcal/publish-batch/', async () => {
    fetchAPIMock.mockResolvedValue({ queued: 1, errors: [] });

    await publishBatch({ solicitacao_ids: [1], dry_run: true, apply_blocked: true });

    expect(fetchAPIMock).toHaveBeenCalledWith('/gcal/publish-batch/', {
      method: 'POST',
      body: JSON.stringify({ solicitacao_ids: [1], dry_run: true, apply_blocked: true }),
    });
  });

  test('reapplyBatch posts to /gcal/dashboard/batch/reapply/', async () => {
    fetchAPIMock.mockResolvedValue({ queued: 1, errors: [] });

    await reapplyBatch({ ids: [10], dry_run: false, apply_blocked: true });

    expect(fetchAPIMock).toHaveBeenCalledWith('/gcal/dashboard/batch/reapply/', {
      method: 'POST',
      body: JSON.stringify({ ids: [10], dry_run: false, apply_blocked: true }),
    });
  });

  test('resyncBatch posts to /gcal/dashboard/batch/resync/', async () => {
    fetchAPIMock.mockResolvedValue({ queued: 1, errors: [] });

    await resyncBatch({ ids: [20], dry_run: true, apply_blocked: false });

    expect(fetchAPIMock).toHaveBeenCalledWith('/gcal/dashboard/batch/resync/', {
      method: 'POST',
      body: JSON.stringify({ ids: [20], dry_run: true, apply_blocked: false }),
    });
  });

  test('getDashboardMetrics uses /gcal/dashboard/metrics/', async () => {
    fetchAPIMock.mockResolvedValue({ counts: {}, recent_errors: [] });

    await getDashboardMetrics({ start: '2026-01-01', end: '2026-01-31' });

    expect(buildUrlMock).toHaveBeenCalledWith('/gcal/dashboard/metrics/', {
      start: '2026-01-01',
      end: '2026-01-31',
    });
    expect(fetchAPIMock).toHaveBeenCalledWith('/gcal/dashboard/metrics/');
  });

  test('listDashboardEvents uses /gcal/dashboard/events/', async () => {
    fetchAPIMock.mockResolvedValue({ count: 0, next: null, previous: null, results: [] });

    await listDashboardEvents({ page: 2, page_size: 50, status: 'ERROR' });

    expect(buildUrlMock).toHaveBeenCalledWith('/gcal/dashboard/events/', {
      page: 2,
      page_size: 50,
      status: 'ERROR',
    });
    expect(fetchAPIMock).toHaveBeenCalledWith('/gcal/dashboard/events/');
  });

  test('getDashboardSuccessRate uses /gcal/dashboard/insights/success-rate/', async () => {
    fetchAPIMock.mockResolvedValue({ rate: 0, published: 0, error: 0, pending: 0, none: 0 });

    await getDashboardSuccessRate({ start: '2026-02-01', end: '2026-02-28' });

    expect(buildUrlMock).toHaveBeenCalledWith('/gcal/dashboard/insights/success-rate/', {
      start: '2026-02-01',
      end: '2026-02-28',
    });
    expect(fetchAPIMock).toHaveBeenCalledWith('/gcal/dashboard/insights/success-rate/');
  });

  test('getDashboardTopInsights uses /gcal/dashboard/insights/top/', async () => {
    fetchAPIMock.mockResolvedValue({ items: [], metric: 'municipios', limit: 5 });

    await getDashboardTopInsights({ metric: 'municipios', limit: 5, start: '2026-02-01' });

    expect(buildUrlMock).toHaveBeenCalledWith('/gcal/dashboard/insights/top/', {
      metric: 'municipios',
      limit: 5,
      start: '2026-02-01',
    });
    expect(fetchAPIMock).toHaveBeenCalledWith('/gcal/dashboard/insights/top/');
  });

  test('getDashboardEventDetail uses event detail endpoint', async () => {
    fetchAPIMock.mockResolvedValue({ id: 123 });

    await getDashboardEventDetail(123);

    expect(fetchAPIMock).toHaveBeenCalledWith('/gcal/dashboard/events/123/detail/');
  });

  test('getAlertsSummary uses alerts summary endpoint', async () => {
    fetchAPIMock.mockResolvedValue({ errors: 0, pending: 0, published: 0, none: 0 });

    await getAlertsSummary();

    expect(fetchAPIMock).toHaveBeenCalledWith('/gcal/dashboard/alerts/summary/');
  });

  test('buildDashboardEventsExportUrl builds API_BASE absolute url', () => {
    buildUrlMock.mockReturnValue('/gcal/dashboard/events/export/?export_format=csv');

    const url = buildDashboardEventsExportUrl({
      export_format: 'csv',
      start: '2026-03-01',
      end: '2026-03-02',
      status: 'ERROR',
    });

    expect(buildUrlMock).toHaveBeenCalledWith('/gcal/dashboard/events/export/', {
      export_format: 'csv',
      start: '2026-03-01',
      end: '2026-03-02',
      status: 'ERROR',
    });
    expect(url).toBe('/api/gcal/dashboard/events/export/?export_format=csv');
  });
});
