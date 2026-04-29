/**
 * useTableFilters Hook — Standardized filters + pagination state for list pages
 *
 * Issue #1116 (Epic #1112): Reduce code duplication in DATModule pages
 *
 * Encapsulates: filters state, pagination state, loading state, and the
 * fetch-with-filters-and-optional-stats pattern used across 7 DATModule pages.
 *
 * Usage:
 *   const {
 *     data, stats, loading, filters, setFilters,
 *     pagination, handleTableChange, handleClearFilters, refresh,
 *   } = useTableFilters<AcoesFilters, AcaoRecord, AcoesStats>({
 *     defaultFilters: { search: '', uf: undefined, municipio: undefined, ... },
 *     listFn: listAcoes,
 *     statsFn: getAcoesStats,
 *     buildParams: (f) => ({
 *       ...(f.search && { search: f.search }),
 *       ...(f.municipio && { municipio_id: f.municipio }),
 *     }),
 *     defaultOrdering: '-updated_at',
 *   });
 */

import { useState, useCallback, useEffect, useRef, type Dispatch, type SetStateAction } from 'react';
import { message } from 'antd';
import type { PaginatedResponse } from '../types';
import type { PaginationState } from './useCrudOperations';

/**
 * Query params produced by the hook for the list/stats endpoints.
 * Matches the shape expected by the DAT module API clients (FilterParams).
 */
export type TableFilterParams = Record<string, string | number | boolean | undefined>;

export type BuildParams<F> = (filters: F, pagination: PaginationState) => TableFilterParams;

export interface UseTableFiltersConfig<F extends object, T, S = unknown> {
  /** Initial filter state; also used as target for handleClearFilters. */
  defaultFilters: F;
  /** Paginated list endpoint. */
  listFn: (params: TableFilterParams) => Promise<PaginatedResponse<T> | T[]>;
  /** Optional stats endpoint; receives the same params as listFn. */
  statsFn?: (params: TableFilterParams) => Promise<S>;
  /**
   * Maps the raw filter object to API query params. Receives current filters
   * and pagination. Defaults to stripping undefined/empty-string values 1:1.
   */
  buildParams?: BuildParams<F>;
  /** Default `ordering` query param injected into every request. */
  defaultOrdering?: string;
  /** Page size; defaults to 15. */
  pageSize?: number;
  /** Label used in error messages. */
  entityName?: string;
  /** Auto-fetch on mount and whenever filters change. Defaults to true. */
  autoFetch?: boolean;
}

export interface UseTableFiltersReturn<F, T, S> {
  data: T[];
  setData: Dispatch<SetStateAction<T[]>>;
  stats: S | null;
  loading: boolean;
  filters: F;
  setFilters: Dispatch<SetStateAction<F>>;
  pagination: PaginationState;
  setPagination: Dispatch<SetStateAction<PaginationState>>;
  fetchData: (page?: number, pageSize?: number) => Promise<void>;
  handleClearFilters: () => void;
  handleTableChange: (page: number, newPageSize?: number) => void;
  refresh: () => Promise<void>;
}

function defaultBuildParams<F extends object>(filters: F): TableFilterParams {
  const out: TableFilterParams = {};
  for (const [k, v] of Object.entries(filters as Record<string, unknown>)) {
    if (v === undefined || v === null || v === '') continue;
    if (typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean') {
      out[k] = v;
    }
  }
  return out;
}

export function useTableFilters<F extends object, T, S = unknown>({
  defaultFilters,
  listFn,
  statsFn,
  buildParams,
  defaultOrdering,
  pageSize = 15,
  entityName = 'dados',
  autoFetch = true,
}: UseTableFiltersConfig<F, T, S>): UseTableFiltersReturn<F, T, S> {
  const [data, setData] = useState<T[]>([]);
  const [stats, setStats] = useState<S | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [filters, setFilters] = useState<F>(defaultFilters);
  const [pagination, setPagination] = useState<PaginationState>({
    current: 1,
    pageSize,
    total: 0,
  });

  // Keep a ref to defaultFilters so handleClearFilters stays stable
  // even if the caller rebuilds the object identity on each render.
  const defaultFiltersRef = useRef(defaultFilters);
  defaultFiltersRef.current = defaultFilters;

  const fetchData = useCallback(
    async (page = 1, pageSizeOverride?: number): Promise<void> => {
      setLoading(true);
      try {
        const requestPageSize = pageSizeOverride ?? pagination.pageSize;
        const requestPagination = {
          ...pagination,
          current: page,
          pageSize: requestPageSize,
        };
        const mapped = buildParams
          ? buildParams(filters, requestPagination)
          : defaultBuildParams(filters);
        const params: TableFilterParams = {
          page,
          page_size: requestPageSize,
          ...(defaultOrdering ? { ordering: defaultOrdering } : {}),
          ...mapped,
        };

        const [listResp, statsResp] = await Promise.all([
          listFn(params),
          statsFn ? statsFn(params) : Promise.resolve(undefined),
        ]);

        const results =
          (listResp as PaginatedResponse<T>).results ??
          (Array.isArray(listResp) ? (listResp as T[]) : []);
        const total = (listResp as PaginatedResponse<T>).count ?? results.length;

        setData(results);
        setPagination((prev) => ({ ...prev, current: page, pageSize: requestPageSize, total }));

        if (statsFn) {
          setStats((statsResp as S) ?? null);
        }
      } catch (error) {
        const err = error as Error;
        message.error(`Erro ao carregar ${entityName}: ${err.message}`);
      } finally {
        setLoading(false);
      }
    },
    [buildParams, filters, listFn, statsFn, defaultOrdering, entityName, pagination.pageSize],
  );

  // Auto-fetch on mount and whenever filters change. Pagination changes are
  // driven by handleTableChange (or manual fetchData calls), not this effect —
  // otherwise changing pageSize would re-fire fetchData via the closure.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!autoFetch) return;
    void fetchData(1);
  }, [autoFetch, filters]);

  const handleClearFilters = useCallback((): void => {
    setFilters(defaultFiltersRef.current);
  }, []);

  const handleTableChange = useCallback(
    (page: number, newPageSize?: number): void => {
      fetchData(page, newPageSize);
    },
    [fetchData],
  );

  const refresh = useCallback((): Promise<void> => {
    return fetchData(pagination.current, pagination.pageSize);
  }, [fetchData, pagination.current, pagination.pageSize]);

  return {
    data,
    setData,
    stats,
    loading,
    filters,
    setFilters,
    pagination,
    setPagination,
    fetchData,
    handleClearFilters,
    handleTableChange,
    refresh,
  };
}

export default useTableFilters;
