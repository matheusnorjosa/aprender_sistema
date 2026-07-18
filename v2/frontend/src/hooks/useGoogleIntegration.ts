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
import type { GoogleIntegrationStatus, GoogleIntegrationStatusRaw } from '../types/gcal';

// Re-export do tipo de domínio (SSOT em types/gcal) por conveniência dos consumidores.
export type { GoogleIntegrationStatus } from '../types/gcal';

/**
 * Estado de domínio para o estado inicial / reset (desconectado).
 *
 * Defaults defensivos: qualquer campo ausente/nulo no payload cai para um
 * valor seguro. `connected` e `isExpired` defaultam para `false`; os demais
 * para `null`.
 */
const EMPTY_STATUS: GoogleIntegrationStatus = {
  connected: false,
  googleEmail: null,
  tokenExpiry: null,
  expiresInDays: null,
  isExpired: false,
  defaultCalendarId: null,
};

/**
 * Normaliza o payload RAW snake_case do backend para o tipo de domínio
 * camelCase.
 *
 * O endpoint `/integrations/google/status/` responde SEMPRE em snake_case
 * (apps/core/views_oauth.py). Sem esta normalização, `fetchAPI<T>` faria
 * apenas um cast não-verificado e os campos camelCase ficariam `undefined`
 * em runtime. Função PURA: mesma entrada → mesma saída, sem efeitos.
 */
export function normalizeGoogleStatus(
  raw: Partial<GoogleIntegrationStatusRaw> | null | undefined
): GoogleIntegrationStatus {
  if (!raw) {
    return { ...EMPTY_STATUS };
  }
  return {
    connected: raw.connected ?? false,
    googleEmail: raw.google_email ?? null,
    tokenExpiry: raw.token_expiry ?? null,
    expiresInDays: raw.expires_in_days ?? null,
    isExpired: raw.is_expired ?? false,
    defaultCalendarId: raw.default_calendar_id ?? null,
  };
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
  const [status, setStatus] = useState<GoogleIntegrationStatus>({ ...EMPTY_STATUS });
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Carrega status da integração do backend.
   */
  const fetchStatus = useCallback(async (): Promise<void> => {
    setLoading(true);
    setError(null);

    try {
      const data = await fetchAPI<GoogleIntegrationStatusRaw>('/integrations/google/status/');
      setStatus(normalizeGoogleStatus(data));
    } catch (err) {
      logger.error('Erro ao carregar status Google:', err);
      const httpError = err as { response?: { data?: { error?: string } } };
      setError(httpError.response?.data?.error || 'Erro ao carregar status da integração');
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
      setStatus({ ...EMPTY_STATUS });

      return { success: true };
    } catch (err) {
      logger.error('Erro ao desconectar Google:', err);
      const httpError = err as { response?: { data?: { error?: string } } };
      const errorMessage = httpError.response?.data?.error || 'Erro ao desconectar conta Google';
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
