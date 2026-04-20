/**
 * Tests: useTableFilters Hook (Issue #1116)
 *
 * Covers:
 * - initial state
 * - auto-fetch on mount
 * - filter → params mapping (default + custom buildParams)
 * - pagination changes
 * - stats endpoint (optional)
 * - handleClearFilters resets to defaultFilters
 * - error handling
 */

import { renderHook, act, waitFor } from '@testing-library/react';
import { describe, test, expect, vi, beforeEach } from 'vitest';
import { useTableFilters } from '../useTableFilters';

vi.mock('antd', () => ({
  message: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

import { message } from 'antd';

interface MockFilters extends Record<string, unknown> {
  search: string;
  uf: string | undefined;
  municipio: number | undefined;
}

interface MockRecord {
  id: number;
  nome: string;
}

interface MockStats {
  total: number;
}

const defaultFilters: MockFilters = {
  search: '',
  uf: undefined,
  municipio: undefined,
};

const mockData: MockRecord[] = [
  { id: 1, nome: 'A' },
  { id: 2, nome: 'B' },
];

const mockPaginated = { results: mockData, count: 50 };

describe('useTableFilters', () => {
  const mockListFn = vi.fn();
  const mockStatsFn = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockListFn.mockResolvedValue(mockPaginated);
    mockStatsFn.mockResolvedValue({ total: 50 });
  });

  test('starts with empty state and default filters', () => {
    const { result } = renderHook(() =>
      useTableFilters<MockFilters, MockRecord, MockStats>({
        defaultFilters,
        listFn: mockListFn,
        autoFetch: false,
      }),
    );

    expect(result.current.data).toEqual([]);
    expect(result.current.stats).toBeNull();
    expect(result.current.loading).toBe(false);
    expect(result.current.filters).toEqual(defaultFilters);
    expect(result.current.pagination).toEqual({ current: 1, pageSize: 15, total: 0 });
  });

  test('auto-fetches on mount by default and populates data', async () => {
    const { result } = renderHook(() =>
      useTableFilters<MockFilters, MockRecord, MockStats>({
        defaultFilters,
        listFn: mockListFn,
      }),
    );

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(mockListFn).toHaveBeenCalledTimes(1);
    expect(result.current.data).toEqual(mockData);
    expect(result.current.pagination.total).toBe(50);
  });

  test('autoFetch=false skips initial fetch', async () => {
    renderHook(() =>
      useTableFilters<MockFilters, MockRecord, MockStats>({
        defaultFilters,
        listFn: mockListFn,
        autoFetch: false,
      }),
    );
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(mockListFn).not.toHaveBeenCalled();
  });

  test('default buildParams strips undefined and empty string', async () => {
    const { result } = renderHook(() =>
      useTableFilters<MockFilters, MockRecord, MockStats>({
        defaultFilters,
        listFn: mockListFn,
      }),
    );

    await waitFor(() => expect(mockListFn).toHaveBeenCalled());
    const params = mockListFn.mock.calls[0][0];
    expect(params.search).toBeUndefined();
    expect(params.uf).toBeUndefined();
    expect(params.municipio).toBeUndefined();
    expect(params.page).toBe(1);
    expect(params.page_size).toBe(15);
  });

  test('default buildParams includes non-empty filter values', async () => {
    const { result } = renderHook(() =>
      useTableFilters<MockFilters, MockRecord, MockStats>({
        defaultFilters,
        listFn: mockListFn,
      }),
    );

    await waitFor(() => expect(mockListFn).toHaveBeenCalled());

    act(() => {
      result.current.setFilters({ search: 'abc', uf: 'CE', municipio: 42 });
    });

    await waitFor(() => expect(mockListFn).toHaveBeenCalledTimes(2));
    const params = mockListFn.mock.calls[1][0];
    expect(params.search).toBe('abc');
    expect(params.uf).toBe('CE');
    expect(params.municipio).toBe(42);
  });

  test('custom buildParams is used when provided', async () => {
    const buildParams = vi.fn((f: MockFilters) => ({
      q: f.search,
      ...(f.municipio ? { municipio_id: f.municipio } : {}),
    }));

    const { result } = renderHook(() =>
      useTableFilters<MockFilters, MockRecord, MockStats>({
        defaultFilters: { search: 'x', uf: undefined, municipio: 7 },
        listFn: mockListFn,
        buildParams,
      }),
    );

    await waitFor(() => expect(mockListFn).toHaveBeenCalled());
    const params = mockListFn.mock.calls[0][0];
    expect(params.q).toBe('x');
    expect(params.municipio_id).toBe(7);
    expect(buildParams).toHaveBeenCalled();
  });

  test('defaultOrdering is injected into params', async () => {
    renderHook(() =>
      useTableFilters<MockFilters, MockRecord, MockStats>({
        defaultFilters,
        listFn: mockListFn,
        defaultOrdering: '-updated_at',
      }),
    );

    await waitFor(() => expect(mockListFn).toHaveBeenCalled());
    expect(mockListFn.mock.calls[0][0].ordering).toBe('-updated_at');
  });

  test('statsFn is called when provided and result exposed via stats', async () => {
    const { result } = renderHook(() =>
      useTableFilters<MockFilters, MockRecord, MockStats>({
        defaultFilters,
        listFn: mockListFn,
        statsFn: mockStatsFn,
      }),
    );

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(mockStatsFn).toHaveBeenCalledTimes(1);
    expect(result.current.stats).toEqual({ total: 50 });
  });

  test('statsFn not called when not provided', async () => {
    renderHook(() =>
      useTableFilters<MockFilters, MockRecord, MockStats>({
        defaultFilters,
        listFn: mockListFn,
      }),
    );

    await waitFor(() => expect(mockListFn).toHaveBeenCalled());
    expect(mockStatsFn).not.toHaveBeenCalled();
  });

  test('handleTableChange updates pagination and fetches new page', async () => {
    const { result } = renderHook(() =>
      useTableFilters<MockFilters, MockRecord, MockStats>({
        defaultFilters,
        listFn: mockListFn,
      }),
    );

    await waitFor(() => expect(result.current.loading).toBe(false));

    act(() => {
      result.current.handleTableChange(3, 30);
    });

    await waitFor(() => expect(mockListFn).toHaveBeenCalledTimes(2));
    expect(mockListFn.mock.calls[1][0].page).toBe(3);
    expect(result.current.pagination.pageSize).toBe(30);
  });

  test('handleClearFilters resets to defaultFilters', async () => {
    const { result } = renderHook(() =>
      useTableFilters<MockFilters, MockRecord, MockStats>({
        defaultFilters,
        listFn: mockListFn,
        autoFetch: false,
      }),
    );

    act(() => {
      result.current.setFilters({ search: 'abc', uf: 'CE', municipio: 42 });
    });
    expect(result.current.filters.search).toBe('abc');

    act(() => {
      result.current.handleClearFilters();
    });
    expect(result.current.filters).toEqual(defaultFilters);
  });

  test('handles non-paginated array response', async () => {
    mockListFn.mockResolvedValueOnce(mockData);

    const { result } = renderHook(() =>
      useTableFilters<MockFilters, MockRecord, MockStats>({
        defaultFilters,
        listFn: mockListFn,
      }),
    );

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).toEqual(mockData);
    expect(result.current.pagination.total).toBe(mockData.length);
  });

  test('surfaces errors via message.error and keeps state sane', async () => {
    mockListFn.mockRejectedValueOnce(new Error('API down'));

    const { result } = renderHook(() =>
      useTableFilters<MockFilters, MockRecord, MockStats>({
        defaultFilters,
        listFn: mockListFn,
        entityName: 'ações',
      }),
    );

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(message.error).toHaveBeenCalledWith(
      expect.stringContaining('Erro ao carregar ações'),
    );
    expect(result.current.data).toEqual([]);
  });

  test('refresh re-fetches current page', async () => {
    const { result } = renderHook(() =>
      useTableFilters<MockFilters, MockRecord, MockStats>({
        defaultFilters,
        listFn: mockListFn,
      }),
    );

    await waitFor(() => expect(result.current.loading).toBe(false));

    act(() => {
      result.current.handleTableChange(2);
    });
    await waitFor(() => expect(result.current.pagination.current).toBe(2));

    await act(async () => {
      await result.current.refresh();
    });

    const lastCall = mockListFn.mock.calls[mockListFn.mock.calls.length - 1][0];
    expect(lastCall.page).toBe(2);
  });
});
