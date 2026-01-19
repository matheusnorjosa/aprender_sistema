/**
 * AS v2 — useDebouncedOptions Hook (CP5 - Issue #164)
 *
 * Hook genérico para otimizar chamadas de options/lookup com:
 * - Debounce de 300ms (evita requests excessivos)
 * - Cache em sessionStorage (reduz chamadas ao backend)
 * - TTL de 5 min (sincronizado com cache backend)
 *
 * Uso:
 * ```jsx
 * import useDebouncedOptions from '../hooks/useDebouncedOptions';
 *
 * function MyComponent() {
 *   const { options, loading } = useDebouncedOptions('/options/municipios/');
 *
 *   return (
 *     <Select loading={loading} options={options} />
 *   );
 * }
 * ```
 *
 * Refs:
 * - CP5 (Issue #164): Autocomplete optimization
 * - CP3: Backend cache 5 min
 */

import { useState, useEffect, useCallback, useRef } from 'prop-types';
import api from '../api';
import { TIMING } from '../constants';

const CACHE_TTL = 300000; // 5 minutos em ms (sincronizado com backend)

const useDebouncedOptions = (endpoint, params = {}) => {
  const [options, setOptions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const debounceTimerRef = useRef(null);

  /**
   * Gera cache key baseado no endpoint e params.
   */
  const getCacheKey = useCallback((url, queryParams) => {
    const paramString = Object.keys(queryParams).length
      ? JSON.stringify(queryParams)
      : '';
    return `options_cache:${url}:${paramString}`;
  }, []);

  /**
   * Verifica cache no sessionStorage.
   */
  const getFromCache = useCallback((key) => {
    try {
      const cached = sessionStorage.getItem(key);
      if (!cached) return null;

      const { data, timestamp } = JSON.parse(cached);
      const age = Date.now() - timestamp;

      // Cache expirado?
      if (age > CACHE_TTL) {
        sessionStorage.removeItem(key);
        return null;
      }

      return data;
    } catch {
      return null;
    }
  }, []);

  /**
   * Salva no cache (sessionStorage).
   */
  const saveToCache = useCallback((key, data) => {
    try {
      sessionStorage.setItem(
        key,
        JSON.stringify({
          data,
          timestamp: Date.now(),
        })
      );
    } catch {
      // Falha silenciosa ao salvar cache (não crítico)
    }
  }, []);

  /**
   * Busca options do backend com debounce.
   */
  const fetchOptions = useCallback(async () => {
    const cacheKey = getCacheKey(endpoint, params);

    // 1. Tentar cache primeiro
    const cachedData = getFromCache(cacheKey);
    if (cachedData) {
      setOptions(cachedData);
      return;
    }

    // 2. Cache miss: fetch do backend
    setLoading(true);
    setError(null);

    try {
      const response = await api.get(endpoint, { params });
      const data = response.data;

      setOptions(data);
      saveToCache(cacheKey, data);
    } catch (err) {
      setError(err.response?.data?.error || 'Erro ao carregar opções');
      setOptions([]);
    } finally {
      setLoading(false);
    }
  }, [endpoint, params, getCacheKey, getFromCache, saveToCache]);

  /**
   * Effect com debounce para fetch.
   */
  useEffect(() => {
    // Limpar timer anterior
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    // Agendar fetch com debounce
    debounceTimerRef.current = setTimeout(() => {
      fetchOptions();
    }, TIMING.DEBOUNCE_DEFAULT_MS);

    // Cleanup
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [fetchOptions]);

  return {
    options,
    loading,
    error,
    refetch: fetchOptions, // Permite refetch manual
  };
};

export default useDebouncedOptions;
