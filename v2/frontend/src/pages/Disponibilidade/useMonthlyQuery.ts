/**
 * Hook para buscar grade mensal de disponibilidade.
 *
 * Encapsula a lógica de fetch, loading e error para reutilização.
 */

import { useState, useEffect, useCallback } from 'react';
import { getMonthlyAvailability } from '../../api/availability';
import { TIMING } from '../../constants/timing';
import { usePolling } from '../../hooks/usePolling';
import { syncChannel } from '../../services/syncChannel';

/**
 * Parameters for the monthly query hook
 */
interface UseMonthlyQueryParams {
  year: number;
  month: number;
  role: string;
  sector?: string;
  q?: string;
  gerenciaId?: number | null;
}

/**
 * Monthly grid data returned by the hook
 * Uses generic types to allow flexibility in page implementations
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type MonthlyGridData = any;

/**
 * Return type for the monthly query hook
 */
interface UseMonthlyQueryResult {
  data: MonthlyGridData | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

/**
 * Hook para buscar grade mensal.
 *
 * @param params - Parâmetros da query
 * @param params.year - Ano (YYYY)
 * @param params.month - Mês (1..12)
 * @param params.role - Role ("FORMADOR" | "COORDENADOR")
 * @param params.sector - Filtro por setor (opcional)
 * @param params.q - Filtro por nome/email (opcional)
 * @param params.gerenciaId - ID da gerência (opcional)
 * @returns { data, loading, error, refetch }
 */
export default function useMonthlyQuery(
  params: UseMonthlyQueryParams
): UseMonthlyQueryResult {
  const [data, setData] = useState<MonthlyGridData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Desestruturar params para evitar loop infinito
  const { year, month, role, sector, q, gerenciaId } = params;

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const queryParams = {
        year,
        month,
        role: role as 'FORMADOR' | 'COORDENADOR',
        sector,
        q,
        gerencia_id: gerenciaId,
      };
      const result = await getMonthlyAvailability(queryParams);
      setData(result);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Erro ao carregar grade mensal';
      setError(errorMessage);
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [year, month, role, sector, q, gerenciaId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // RT-02: Polling 5s for cross-device sync (#1032)
  usePolling(fetchData, {
    enabled: true,
    intervalMs: TIMING.SYNC_POLL_INTERVAL_MS,
    events: ['availability:refresh'],
  });

  // RT-02: BroadcastChannel for instant cross-tab sync
  useEffect(() => {
    const unsub = syncChannel.subscribe('availability', () => {
      fetchData();
    });
    return unsub;
  }, [fetchData]);

  return {
    data,
    loading,
    error,
    refetch: fetchData,
  };
}
