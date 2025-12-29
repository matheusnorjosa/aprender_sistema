/**
 * AS v2 — useGoogleIntegration Hook (Sprint 1 - Issue #1)
 *
 * Hook para gerenciar estado da integração OAuth Google Calendar.
 *
 * State:
 * - connected: bool
 * - googleEmail: string | null
 * - tokenExpiry: string (ISO 8601) | null
 * - expiresInDays: number | null
 * - isExpired: bool
 * - loading: bool
 * - error: string | null
 *
 * Methods:
 * - fetchStatus(): Carrega status atual do backend
 * - disconnect(): Desconecta conta Google
 *
 * Refs:
 * - Sprint 1 (Issue #1): Frontend Hook
 * - PA-06: Controle explícito (ISO 9241-110)
 */

import { useState, useEffect, useCallback } from 'react';
import api from '../api';
import logger from '../utils/logger';

const useGoogleIntegration = () => {
  const [status, setStatus] = useState({
    connected: false,
    googleEmail: null,
    tokenExpiry: null,
    expiresInDays: null,
    isExpired: false,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  /**
   * Carrega status da integração do backend.
   */
  const fetchStatus = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await api.get('/integrations/google/status/');
      setStatus(response.data);
    } catch (err) {
      logger.error('Erro ao carregar status Google:', err);
      setError(err.response?.data?.error || 'Erro ao carregar status da integração');
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Desconecta conta Google (revoga refresh_token).
   */
  const disconnect = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      await api.post('/integrations/google/disconnect/');

      // Atualizar estado local
      setStatus({
        connected: false,
        googleEmail: null,
        tokenExpiry: null,
        expiresInDays: null,
        isExpired: false,
      });

      return { success: true };
    } catch (err) {
      logger.error('Erro ao desconectar Google:', err);
      setError(err.response?.data?.error || 'Erro ao desconectar conta Google');
      return { success: false, error: err.response?.data?.error };
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Carrega status ao montar o componente.
   */
  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  return {
    status,
    loading,
    error,
    fetchStatus,
    disconnect,
  };
};

export default useGoogleIntegration;
