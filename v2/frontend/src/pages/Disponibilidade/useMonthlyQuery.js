/**
 * Hook para buscar grade mensal de disponibilidade.
 *
 * Encapsula a lógica de fetch, loading e error para reutilização.
 */

import { useState, useEffect, useCallback } from 'react';
import { getMonthly } from '../../api/availability';

/**
 * Hook para buscar grade mensal.
 *
 * @param {object} params - Parâmetros da query
 * @param {number} params.year - Ano (YYYY)
 * @param {number} params.month - Mês (1..12)
 * @param {string} params.role - Role ("FORMADOR" | "COORDENADOR")
 * @param {string} params.sector - Filtro por setor (opcional)
 * @param {string} params.q - Filtro por nome/email (opcional)
 * @returns {object} { data, loading, error, refetch }
 */
export default function useMonthlyQuery(params) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Desestruturar params para evitar loop infinito
  const { year, month, role, sector, q } = params;

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await getMonthly({ year, month, role, sector, q });
      setData(result);
    } catch (err) {
      setError(err.message || 'Erro ao carregar grade mensal');
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [year, month, role, sector, q]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    data,
    loading,
    error,
    refetch: fetchData,
  };
}
