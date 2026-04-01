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
import { fetchAPI } from '../api/config';
import logger from '../utils/logger';

/**
 * Google integration status
 */
export interface GoogleIntegrationStatus {
  connected: boolean;
  googleEmail: string | null;
  tokenExpiry: string | null;
  expiresInDays: number | null;
  isExpired: boolean;
}

/**
 * Disconnect result
 */
export interface DisconnectResult {
  success: boolean;
  error?: string;
}

/**
 * Return type for useGoogleIntegration
 */
export interface UseGoogleIntegrationReturn {
  status: GoogleIntegrationStatus;
  loading: boolean;
  error: string | null;
  fetchStatus: () => Promise<void>;
  disconnect: () => Promise<DisconnectResult>;
}

const useGoogleIntegration = (): UseGoogleIntegrationReturn => {
  const [status, setStatus] = useState<GoogleIntegrationStatus>({
    connected: false,
    googleEmail: null,
    tokenExpiry: null,
    expiresInDays: null,
    isExpired: false,
  });
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Carrega status da integração do backend.
   */
  const fetchStatus = useCallback(async (): Promise<void> => {
    setLoading(true);
    setError(null);

    try {
      const data = await fetchAPI<GoogleIntegrationStatus>('/integrations/google/status/');
      setStatus(data);
    } catch (err) {
      logger.error('Erro ao carregar status Google:', err);
      const axiosError = err as { response?: { data?: { error?: string } } };
      setError(axiosError.response?.data?.error || 'Erro ao carregar status da integração');
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Desconecta conta Google (revoga refresh_token).
   */
  const disconnect = useCallback(async (): Promise<DisconnectResult> => {
    setLoading(true);
    setError(null);

    try {
      await fetchAPI('/integrations/google/disconnect/', { method: 'POST' });

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
      const axiosError = err as { response?: { data?: { error?: string } } };
      const errorMessage = axiosError.response?.data?.error || 'Erro ao desconectar conta Google';
      setError(errorMessage);
      return { success: false, error: errorMessage };
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
