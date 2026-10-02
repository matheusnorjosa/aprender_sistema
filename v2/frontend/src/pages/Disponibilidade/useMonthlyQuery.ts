/**
 * Hook para buscar grade mensal de disponibilidade.
 *
 * Encapsula a lógica de fetch, loading e error para reutilização.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { getMonthlyAvailability } from '../../api/availability';
import type { MonthlyGridResponse } from '../../types/availability';
import { TIMING } from '../../constants/timing';
import { usePolling } from '../../hooks/usePolling';
import { syncChannel } from '../../services/syncChannel';
import { mesmosDados } from '../../utils/mesmosDados';
import { pausaDo429Ms } from '../../utils/retryAfter';

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
 * Monthly grid data returned by the hook — a shape real da API de grade mensal
 * (`getMonthlyAvailability` já retorna `MonthlyGridResponse`).
 */
type MonthlyGridData = MonthlyGridResponse;

/**
 * Return type for the monthly query hook
 */
interface UseMonthlyQueryResult {
  data: MonthlyGridData | null;
  /** Só na primeira carga e na troca de filtro; a atualização automática não liga. */
  loading: boolean;
  error: string | null;
  lastUpdated: number | null;
  /** O servidor respondeu 429: a atualização automática está suspensa por um prazo. */
  pollingPausado: boolean;
  /** Atualiza em segundo plano (a grade continua na tela). */
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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<number | null>(null);

  // Desestruturar params para evitar loop infinito
  const { year, month, role, sector, q, gerenciaId } = params;

  // Latest-wins: troca de filtro e polling disparam cargas concorrentes; só a mais
  // recente grava na tela (a resposta atrasada de outro mês é descartada).
  const seqRef = useRef(0);
  /** Há grade na tela para o filtro atual (a falha em segundo plano não a derruba). */
  const temGradeRef = useRef(false);

  // RT-02: polling para sincronizar entre dispositivos (#1032); intervalo em
  // constants/timing.ts. immediate:false: a carga inicial é do efeito abaixo.
  const fetchRef = useRef<(silencioso?: boolean) => Promise<void>>(() => Promise.resolve());
  const { pausado: pollingPausado, pausar: pausarPolling } = usePolling(() => fetchRef.current(true), {
    enabled: true,
    intervalMs: TIMING.GRADE_POLL_INTERVAL_MS,
    immediate: false,
    events: ['availability:refresh'],
  });

  /**
   * `silencioso`: atualização em segundo plano (polling, outra aba, botão de atualizar).
   * Não liga `loading` (a página desmontaria as grades e piscaria "Carregando...") e, se
   * falhar, a grade que está na tela fica. Sem `silencioso` é carga nova (mount ou troca
   * de filtro): limpa os dados do filtro anterior e mostra carregamento.
   */
  const fetchData = useCallback(async (silencioso = false): Promise<void> => {
    const seq = ++seqRef.current;
    if (!silencioso) {
      setLoading(true);
      setError(null);
      setData(null);
      temGradeRef.current = false;
    }

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
      if (seq !== seqRef.current) return;
      // Só troca os dados se algo mudou: resposta igual não redesenha as grades.
      setData((atual) => (mesmosDados(atual, result) ? atual : result));
      temGradeRef.current = true;
      setError(null);
      setLastUpdated(Date.now());
    } catch (err) {
      if (seq !== seqRef.current) return;
      // 429 (muitas requisições): pausa o polling pelo tempo pedido; a página avisa.
      const pausa = pausaDo429Ms(err);
      if (pausa !== null) pausarPolling(pausa);
      const errorMessage =
        err instanceof Error ? err.message : 'Erro ao carregar grade mensal';
      // Com grade na tela, a falha em segundo plano não a derruba: a próxima tentativa
      // atualiza. Sem grade (primeira carga), mostra o erro.
      if (!temGradeRef.current) setError(errorMessage);
    } finally {
      if (seq === seqRef.current) setLoading(false);
    }
  }, [year, month, role, sector, q, gerenciaId, pausarPolling]);
  fetchRef.current = fetchData;

  useEffect(() => {
    void fetchData();
  }, [fetchData]);

  // RT-02: BroadcastChannel for instant cross-tab sync
  useEffect(() => {
    const unsub = syncChannel.subscribe('availability', () => {
      void fetchData(true);
    });
    return unsub;
  }, [fetchData]);

  const refetch = useCallback((): Promise<void> => fetchData(true), [fetchData]);

  return {
    data,
    loading,
    error,
    lastUpdated,
    pollingPausado,
    refetch,
  };
}
