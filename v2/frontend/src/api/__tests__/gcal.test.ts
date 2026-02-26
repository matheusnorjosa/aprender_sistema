import { beforeEach, describe, expect, test, vi } from 'vitest';

const { fetchAPIMock, buildUrlMock } = vi.hoisted(() => ({
  fetchAPIMock: vi.fn(),
  buildUrlMock: vi.fn(),
}));

vi.mock('../config', () => ({
  fetchAPI: fetchAPIMock,
  buildUrl: buildUrlMock,
}));

import {
  getStatusSummary,
  listApprovedWithGCalStatus,
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
});
